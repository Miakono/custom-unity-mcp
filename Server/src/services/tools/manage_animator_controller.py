"""
AnimatorController state-machine management: states, transitions, parameters, layers,
default state, copy-from, AnimatorOverrideControllers.

Complements `manage_animation` (which owns AnimationClip authoring) — this tool owns
the controller graph that wires those clips together via parameters and transitions.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from services.tools.utils import coerce_float, coerce_int
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    group="animation",
    description=(
        "Read and edit AnimatorController state machines and AnimatorOverrideControllers.\n"
        "Read actions: get, list_states, list_transitions, list_parameters, list_layers, "
        "list_overrides.\n"
        "Mutating actions: add_parameter, remove_parameter, add_state, remove_state, "
        "add_transition, set_default_state, set_transition_property, "
        "add_any_state_transition, copy_layer_from, create_override, set_override_clip, "
        "clear_override, add_layer, remove_layer, rename_layer, set_layer_property, "
        "set_state_property.\n"
        "controllerPath is required for most actions and must point at a .controller asset under Assets/. "
        "Override actions take overrideControllerPath instead. copy_layer_from takes sourceController + "
        "targetController.\n"
        "Batch shapes: pass `parameters: [{name,type,default?},...]` to add_parameter, "
        "`states: [{name,clipPath?},...]` to add_state, or `controllers: [path1,path2,...]` "
        "at the top level to apply the action against multiple controllers in one call. "
        "list_transitions returns Any-State transitions under a separate `state_machine_transitions` "
        "array alongside per-state `transitions`. set_layer_property covers iKPass / defaultWeight / "
        "blendingMode / avatarMaskPath / syncedLayerIndex / syncedLayerAffectsTiming. "
        "set_state_property covers speed / cycleOffset / mirror / writeDefaultValues / tag / iKOnFeet / motion."
    ),
    annotations=ToolAnnotations(
        title="Manage Animator Controller",
        destructiveHint=True,
    ),
)
async def manage_animator_controller(
    ctx: Context,
    action: Annotated[
        Literal[
            "get",
            "list_states",
            "list_transitions",
            "list_parameters",
            "list_layers",
            "add_parameter",
            "remove_parameter",
            "add_state",
            "remove_state",
            "add_transition",
            "set_default_state",
            "set_transition_property",
            "add_any_state_transition",
            "copy_layer_from",
            "create_override",
            "list_overrides",
            "set_override_clip",
            "clear_override",
            "add_layer",
            "remove_layer",
            "rename_layer",
            "set_layer_property",
            "set_state_property",
        ],
        "Operation to perform. add_*/remove_*/set_*/copy_*/create_*/clear_*/rename_* are mutating; "
        "everything else is read-only."
    ],
    controller_path: Annotated[
        str | None,
        "AnimatorController asset path (Assets/.../*.controller). Required for most actions; "
        "ignored by override-controller and copy_layer_from actions which use their own paths."
    ] = None,
    layer_index: Annotated[
        int | str | None,
        "Layer index (default 0) for state/transition operations."
    ] = None,
    state_name: Annotated[
        str | None,
        "State name for add_state / remove_state / set_default_state. Accepts a bare name "
        "or a dotted path like 'Base Layer.SubMachine.Idle' for nested state machines."
    ] = None,
    state_path: Annotated[
        str | None,
        "Alias for state_name when targeting a nested sub-state-machine."
    ] = None,
    clip_path: Annotated[
        str | None,
        "Optional AnimationClip path to attach when adding a state."
    ] = None,
    from_state: Annotated[
        str | None,
        "Source state name for add_transition / set_transition_property "
        "(or filter for list_transitions). Pass 'any_state' (or omit) to target any-state "
        "transitions in set_transition_property."
    ] = None,
    to_state: Annotated[
        str | None,
        "Destination state name for add_transition / set_transition_property."
    ] = None,
    destination_state: Annotated[
        str | None,
        "Destination state name for add_any_state_transition (alias of to_state)."
    ] = None,
    transition_index: Annotated[
        int | str | None,
        "Index among transitions matching (fromState, toState) — use when multiple "
        "transitions share the same source/destination pair."
    ] = None,
    duration: Annotated[
        float | str | None,
        "Transition duration (seconds). Optional on add_transition / set_transition_property / "
        "add_any_state_transition."
    ] = None,
    has_exit_time: Annotated[
        bool | str | None,
        "Whether the transition uses exit time. Hit-reactions usually want true."
    ] = None,
    exit_time: Annotated[
        float | str | None,
        "Exit-time fraction (0-1) when has_exit_time=true. e.g. 0.9."
    ] = None,
    offset: Annotated[
        float | str | None,
        "Transition offset (0-1)."
    ] = None,
    interruption_source: Annotated[
        Literal["None", "Source", "Destination", "SourceThenDestination", "DestinationThenSource"] | None,
        "TransitionInterruptionSource for transition interruption behavior."
    ] = None,
    ordered_interruption: Annotated[
        bool | str | None,
        "Whether interrupting transitions are ordered."
    ] = None,
    can_transition_to_self: Annotated[
        bool | str | None,
        "Whether an any-state transition can interrupt to its own destination."
    ] = None,
    parameter_name: Annotated[
        str | None,
        "Parameter name for add_parameter / remove_parameter."
    ] = None,
    parameter_type: Annotated[
        Literal["Bool", "Float", "Int", "Trigger"] | None,
        "Parameter type for add_parameter."
    ] = None,
    default_value: Annotated[
        str | None,
        "Default value for add_parameter (parsed by type — 'true'/'1.5'/'42'; ignored for Trigger)."
    ] = None,
    parameters: Annotated[
        list[dict[str, Any]] | str | None,
        "Batch shape for add_parameter: [{name, type, default?}, ...]. When provided, the "
        "single parameter_name/parameter_type/default_value fields are ignored."
    ] = None,
    states: Annotated[
        list[dict[str, Any]] | str | None,
        "Batch shape for add_state: [{name, clipPath?}, ...]. When provided, the single "
        "state_name/clip_path fields are ignored."
    ] = None,
    controllers: Annotated[
        list[str] | str | None,
        "Batch shape: apply the action across multiple controllers. Each entry is an "
        "Assets/.../*.controller path. Server-side loop — saves per-controller round trips."
    ] = None,
    condition_parameter: Annotated[
        str | None,
        "Single-condition shorthand for add_transition. Pair with condition_mode."
    ] = None,
    condition_mode: Annotated[
        Literal["If", "IfNot", "Greater", "Less", "Equals", "NotEqual"] | None,
        "Condition mode for add_transition (single-condition shorthand)."
    ] = None,
    condition_threshold: Annotated[
        float | str | None,
        "Threshold for the single-condition shorthand (used by Greater/Less/Equals)."
    ] = None,
    conditions: Annotated[
        list[dict[str, Any]] | str | None,
        "Conditions array: [{parameter, mode, threshold?}, ...]. When provided on "
        "set_transition_property, replaces existing conditions wholesale."
    ] = None,
    source_controller: Annotated[
        str | None,
        "copy_layer_from: source AnimatorController asset path."
    ] = None,
    source_layer_index: Annotated[
        int | str | None,
        "copy_layer_from: source layer index (default 0)."
    ] = None,
    target_controller: Annotated[
        str | None,
        "copy_layer_from: target AnimatorController asset path."
    ] = None,
    target_layer_index: Annotated[
        int | str | None,
        "copy_layer_from: target layer index (default 0). Layer is created if it does not exist."
    ] = None,
    remap_clips: Annotated[
        bool | str | None,
        "copy_layer_from: try to find same-named clips in the target controller's clip pool."
    ] = None,
    overwrite: Annotated[
        bool | str | None,
        "copy_layer_from: replace target layer contents if non-empty."
    ] = None,
    override_controller_path: Annotated[
        str | None,
        "Override-controller actions: path to the .overrideController asset."
    ] = None,
    output_path: Annotated[
        str | None,
        "create_override: output path for the new .overrideController asset."
    ] = None,
    base_controller: Annotated[
        str | None,
        "create_override: base AnimatorController path (the controller this override extends)."
    ] = None,
    original_clip_name: Annotated[
        str | None,
        "set_override_clip / clear_override: name of the clip in the base controller to override."
    ] = None,
    override_clip: Annotated[
        str | None,
        "set_override_clip: AnimationClip path used as the override."
    ] = None,
    # ─── layer CRUD + property writes ───────────────────────────────────────────
    layer_name: Annotated[
        str | None,
        "add_layer / remove_layer / rename_layer / set_layer_property: layer name. "
        "Use as a lookup alternative to layer_index."
    ] = None,
    new_layer_name: Annotated[
        str | None,
        "rename_layer: new name for the layer."
    ] = None,
    force: Annotated[
        bool | str | None,
        "remove_layer: required true to remove layer 0 (the base layer)."
    ] = None,
    default_weight: Annotated[
        float | str | None,
        "set_layer_property / add_layer: layer weight (0-1)."
    ] = None,
    ik_pass: Annotated[
        bool | str | None,
        "set_layer_property / add_layer: enable IK Pass on the layer (the 'IK Pass' Inspector checkbox)."
    ] = None,
    blending_mode: Annotated[
        Literal["Override", "Additive"] | None,
        "set_layer_property / add_layer: layer blending mode."
    ] = None,
    avatar_mask_path: Annotated[
        str | None,
        "set_layer_property / add_layer: AvatarMask asset path. Pass '' to clear."
    ] = None,
    synced_layer_index: Annotated[
        int | str | None,
        "set_layer_property / add_layer: source layer for syncing. -1 = not synced."
    ] = None,
    synced_layer_affects_timing: Annotated[
        bool | str | None,
        "set_layer_property / add_layer: whether synced layer affects timing."
    ] = None,
    # ─── state property writes ──────────────────────────────────────────────────
    speed: Annotated[
        float | str | None,
        "set_state_property: playback speed multiplier."
    ] = None,
    cycle_offset: Annotated[
        float | str | None,
        "set_state_property: cycle offset (0-1)."
    ] = None,
    mirror: Annotated[
        bool | str | None,
        "set_state_property: humanoid mirror flag."
    ] = None,
    write_default_values: Annotated[
        bool | str | None,
        "set_state_property: whether the state writes default values for unwritten properties."
    ] = None,
    tag: Annotated[
        str | None,
        "set_state_property: state tag (used by Animator.GetCurrentAnimatorStateInfo etc)."
    ] = None,
    ik_on_feet: Annotated[
        bool | str | None,
        "set_state_property: per-state Foot IK enable."
    ] = None,
    motion: Annotated[
        str | None,
        "set_state_property: AnimationClip path for the state's motion. Pass '' to clear."
    ] = None,
    clear_motion: Annotated[
        bool | str | None,
        "set_state_property: explicit alternative to motion='' for clearing the motion reference."
    ] = None,
) -> dict[str, Any]:
    """Drive AnimatorController operations through the Unity Editor."""
    unity_instance = await get_unity_instance_from_context(ctx)

    gate = await maybe_run_tool_preflight(ctx, "manage_animator_controller", action=action)
    if gate is not None:
        return gate.model_dump()

    params: dict[str, Any] = {"action": action}
    if controller_path is not None:
        params["controllerPath"] = controller_path
    if layer_index is not None:
        params["layerIndex"] = coerce_int(layer_index, default=0)
    if state_name is not None:
        params["stateName"] = state_name
    if state_path is not None:
        params["statePath"] = state_path
    if clip_path is not None:
        params["clipPath"] = clip_path
    if from_state is not None:
        params["fromState"] = from_state
    if to_state is not None:
        params["toState"] = to_state
    if destination_state is not None:
        params["destinationState"] = destination_state
    if transition_index is not None:
        params["transitionIndex"] = coerce_int(transition_index, default=0)
    if duration is not None:
        params["duration"] = coerce_float(duration, default=0.0)
    if has_exit_time is not None:
        params["hasExitTime"] = _coerce_bool(has_exit_time)
    if exit_time is not None:
        params["exitTime"] = coerce_float(exit_time, default=0.0)
    if offset is not None:
        params["offset"] = coerce_float(offset, default=0.0)
    if interruption_source is not None:
        params["interruptionSource"] = interruption_source
    if ordered_interruption is not None:
        params["orderedInterruption"] = _coerce_bool(ordered_interruption)
    if can_transition_to_self is not None:
        params["canTransitionToSelf"] = _coerce_bool(can_transition_to_self)
    if parameter_name is not None:
        params["parameterName"] = parameter_name
    if parameter_type is not None:
        params["parameterType"] = parameter_type
    if default_value is not None:
        params["defaultValue"] = default_value
    if parameters is not None:
        params["parameters"] = parameters
    if states is not None:
        params["states"] = states
    if controllers is not None:
        params["controllers"] = controllers
    if condition_parameter is not None:
        params["conditionParameter"] = condition_parameter
    if condition_mode is not None:
        params["conditionMode"] = condition_mode
    if condition_threshold is not None:
        params["conditionThreshold"] = coerce_float(condition_threshold, default=0.0)
    if conditions is not None:
        params["conditions"] = conditions
    if source_controller is not None:
        params["sourceController"] = source_controller
    if source_layer_index is not None:
        params["sourceLayerIndex"] = coerce_int(source_layer_index, default=0)
    if target_controller is not None:
        params["targetController"] = target_controller
    if target_layer_index is not None:
        params["targetLayerIndex"] = coerce_int(target_layer_index, default=0)
    if remap_clips is not None:
        params["remapClips"] = _coerce_bool(remap_clips)
    if overwrite is not None:
        params["overwrite"] = _coerce_bool(overwrite)
    if override_controller_path is not None:
        params["overrideControllerPath"] = override_controller_path
    if output_path is not None:
        params["outputPath"] = output_path
    if base_controller is not None:
        params["baseController"] = base_controller
    if original_clip_name is not None:
        params["originalClipName"] = original_clip_name
    if override_clip is not None:
        params["overrideClip"] = override_clip
    if layer_name is not None:
        params["layerName"] = layer_name
    if new_layer_name is not None:
        params["newLayerName"] = new_layer_name
    if force is not None:
        params["force"] = _coerce_bool(force)
    if default_weight is not None:
        params["defaultWeight"] = coerce_float(default_weight, default=0.0)
    if ik_pass is not None:
        params["iKPass"] = _coerce_bool(ik_pass)
    if blending_mode is not None:
        params["blendingMode"] = blending_mode
    if avatar_mask_path is not None:
        params["avatarMaskPath"] = avatar_mask_path
    if synced_layer_index is not None:
        params["syncedLayerIndex"] = coerce_int(synced_layer_index, default=-1)
    if synced_layer_affects_timing is not None:
        params["syncedLayerAffectsTiming"] = _coerce_bool(synced_layer_affects_timing)
    if speed is not None:
        params["speed"] = coerce_float(speed, default=1.0)
    if cycle_offset is not None:
        params["cycleOffset"] = coerce_float(cycle_offset, default=0.0)
    if mirror is not None:
        params["mirror"] = _coerce_bool(mirror)
    if write_default_values is not None:
        params["writeDefaultValues"] = _coerce_bool(write_default_values)
    if tag is not None:
        params["tag"] = tag
    if ik_on_feet is not None:
        params["iKOnFeet"] = _coerce_bool(ik_on_feet)
    if motion is not None:
        params["motion"] = motion
    if clear_motion is not None:
        params["clearMotion"] = _coerce_bool(clear_motion)

    try:
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_animator_controller",
            params,
        )
        if isinstance(response, dict):
            return response
        return {"success": False, "message": str(response)}
    except Exception as e:
        return {"success": False, "message": f"manage_animator_controller {action} error: {e!s}"}


def _coerce_bool(value: Any) -> bool:
    """Loose bool coercion matching the C# ToolParams.GetBool behavior."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        return s in ("true", "1", "yes", "y", "on")
    return bool(value)
