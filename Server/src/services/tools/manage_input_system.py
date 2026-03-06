"""
Manage Unity Input System - Action Maps, Actions, Bindings, and Control Schemes.

This tool provides comprehensive management of Unity's new Input System package:
- Configure Input Action assets (Editor mode)
- Simulate input at runtime (Play mode)
- Read current input state

Action prefixes:
- actionmap_*: Manage action maps (get, create, delete)
- action_*: Manage actions within action maps (get, create, delete)
- binding_*: Manage bindings for actions (get, add, remove, modify)
- scheme_*: Manage control schemes (get, create, delete)
- asset_*: Manage Input Action assets (get list)
- simulate_*: Runtime input simulation (editor/play mode)
- state_*: Get current input state
"""

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry

# Action map management
ACTION_MAP_ACTIONS = [
    "actionmap_get_all",
    "actionmap_get",
    "actionmap_create",
    "actionmap_delete",
]

# Action management
ACTION_ACTIONS = [
    "action_get_all",
    "action_get",
    "action_create",
    "action_delete",
]

# Binding management
BINDING_ACTIONS = [
    "binding_get_all",
    "binding_add",
    "binding_remove",
    "binding_modify",
]

# Control scheme management
SCHEME_ACTIONS = [
    "scheme_get_all",
    "scheme_create",
    "scheme_delete",
]

# Asset management
ASSET_ACTIONS = [
    "asset_get_all",
    "asset_get_info",
]

# Runtime simulation (marked as high-risk)
SIMULATION_ACTIONS = [
    "simulate_key_press",
    "simulate_key_hold",
    "simulate_key_release",
    "simulate_button_press",
    "simulate_axis",
    "simulate_vector2",
    "simulate_mouse_move",
    "simulate_mouse_click",
    "simulate_touch",
]

# Input state reading
STATE_ACTIONS = [
    "state_get_action_value",
    "state_get_all_actions",
    "state_is_action_pressed",
    "state_get_control_value",
]

ALL_ACTIONS = (
    ACTION_MAP_ACTIONS
    + ACTION_ACTIONS
    + BINDING_ACTIONS
    + SCHEME_ACTIONS
    + ASSET_ACTIONS
    + SIMULATION_ACTIONS
    + STATE_ACTIONS
)

# Read-only actions don't require preflight
READ_ONLY_ACTIONS = {
    "actionmap_get_all",
    "actionmap_get",
    "action_get_all",
    "action_get",
    "binding_get_all",
    "scheme_get_all",
    "asset_get_all",
    "asset_get_info",
    "state_get_action_value",
    "state_get_all_actions",
    "state_is_action_pressed",
    "state_get_control_value",
}

# Runtime-only actions require play mode
RUNTIME_ONLY_ACTIONS = set(SIMULATION_ACTIONS + STATE_ACTIONS)


def _get_action_category(action: str) -> str:
    """Get the category for an action."""
    if action.startswith("actionmap_"):
        return "action map"
    elif action.startswith("action_"):
        return "action"
    elif action.startswith("binding_"):
        return "binding"
    elif action.startswith("scheme_"):
        return "control scheme"
    elif action.startswith("asset_"):
        return "asset"
    elif action.startswith("simulate_"):
        return "simulation"
    elif action.startswith("state_"):
        return "state"
    return "unknown"


@mcp_for_unity_tool(
    group="input",
    description=(
        "Manage Unity Input System - Action Maps, Actions, Bindings, Control Schemes, "
        "and Runtime Simulation. "
        "Action prefixes: actionmap_* (manage maps), action_* (manage actions), "
        "binding_* (manage bindings), scheme_* (control schemes), "
        "asset_* (Input Action assets), simulate_* (runtime input simulation - high risk), "
        "state_* (read input state). "
        "Runtime simulation actions require play mode and are marked as high risk."
    ),
    annotations=ToolAnnotations(
        title="Manage Input System",
        destructiveHint=True,
        openWorldHint=False,
    ),
)
async def manage_input_system(
    ctx: Context,
    action: Annotated[
        str,
        "Action to perform. Categories: "
        "actionmap_* (get_all, get, create, delete), "
        "action_* (get_all, get, create, delete), "
        "binding_* (get_all, add, remove, modify), "
        "scheme_* (get_all, create, delete), "
        "asset_* (get_all, get_info), "
        "simulate_* (key_press, key_hold, key_release, button_press, axis, vector2, mouse_move, mouse_click, touch), "
        "state_* (get_action_value, get_all_actions, is_action_pressed, get_control_value)."
    ],
    asset_path: Annotated[
        str | None,
        "Path to Input Action asset (e.g., 'Assets/Input/Player.inputactions')."
    ] = None,
    action_map: Annotated[
        str | None,
        "Name of the action map to operate on."
    ] = None,
    action_name: Annotated[
        str | None,
        "Name of the action to operate on."
    ] = None,
    properties: Annotated[
        dict[str, Any] | str | None,
        "Action-specific parameters (dict or JSON string). "
        "Common properties: bindingPath, controlScheme, actionType, compositeParts, etc."
    ] = None,
) -> dict[str, Any]:
    """Unified Input System management tool."""
    
    action_normalized = action.lower()
    
    # Validate action
    if action_normalized not in ALL_ACTIONS:
        prefix = action_normalized.split("_")[0] + "_" if "_" in action_normalized else ""
        available_by_prefix = {
            "actionmap_": ACTION_MAP_ACTIONS,
            "action_": ACTION_ACTIONS,
            "binding_": BINDING_ACTIONS,
            "scheme_": SCHEME_ACTIONS,
            "asset_": ASSET_ACTIONS,
            "simulate_": SIMULATION_ACTIONS,
            "state_": STATE_ACTIONS,
        }
        suggestions = available_by_prefix.get(prefix, [])
        if suggestions:
            return {
                "success": False,
                "message": f"Unknown action '{action}'. Available {prefix}* actions: {', '.join(suggestions)}",
            }
        else:
            return {
                "success": False,
                "message": (
                    f"Unknown action '{action}'. Use prefixes: "
                    "actionmap_*, action_*, binding_*, scheme_*, asset_*, simulate_*, state_*"
                ),
            }
    
    # Skip preflight for read-only actions
    if action_normalized not in READ_ONLY_ACTIONS:
        gate = await maybe_run_tool_preflight(ctx, "manage_input_system", action=action_normalized)
        if gate is not None:
            return gate.model_dump()
    
    unity_instance = await get_unity_instance_from_context(ctx)
    
    # Build params dict
    params_dict: dict[str, Any] = {"action": action_normalized}
    
    if asset_path is not None:
        params_dict["assetPath"] = asset_path
    if action_map is not None:
        params_dict["actionMap"] = action_map
    if action_name is not None:
        params_dict["actionName"] = action_name
    if properties is not None:
        params_dict["properties"] = properties
    
    # Add runtime warning for simulation/state actions
    if action_normalized in RUNTIME_ONLY_ACTIONS:
        params_dict["_runtimeOnly"] = True
    
    params_dict = {k: v for k, v in params_dict.items() if v is not None}
    
    # Send to Unity
    result = await send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "manage_input_system",
        params_dict,
    )
    
    return result if isinstance(result, dict) else {"success": False, "message": str(result)}


