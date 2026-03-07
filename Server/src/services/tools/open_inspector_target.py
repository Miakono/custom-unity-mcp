from __future__ import annotations

"""Tool for opening and navigating targets in the Unity Inspector.

Provides Inspector window control to open GameObjects, assets, or components
in the Inspector, with support for locking, multi-object editing, and
component expansion.
"""

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    group="navigation",
    description=(
        "Opens a target in the Unity Inspector window. "
        "Supports opening GameObjects, assets, components, or specific component types. "
        "Can lock the inspector, expand specific components, and manage multi-object editing. "
        "Also supports querying the current Inspector target. "
        "Use this to direct user attention to specific properties and settings."
    ),
    annotations=ToolAnnotations(
        title="Open Inspector Target",
        destructiveHint=False,
    ),
)
async def open_inspector_target(
    ctx: Context,
    action: Annotated[
        Literal["open", "open_component", "lock", "unlock", "get_target", "clear"],
        "Inspector action to perform. 'open' opens target in Inspector, "
        "'open_component' opens specific component, 'lock'/'unlock' controls inspector lock, "
        "'get_target' returns current Inspector target, 'clear' clears the Inspector."
    ] = "open",
    target: Annotated[
        str | int | list[str | int] | dict[str, Any] | None,
        "Target to open. Can be: path (str), instance ID (int), list for multi-edit, "
        "or dict with 'path', 'instance_id', 'guid', or 'name' keys. "
        "Not used for get_target, lock, unlock, or clear actions."
    ] = None,
    component_type: Annotated[
        str | None,
        "For open_component: the component type name to open (e.g., 'Transform', 'MeshRenderer')."
    ] = None,
    component_index: Annotated[
        int | None,
        "For open_component: index of component if multiple of same type exist. Default 0."
    ] = None,
    expand_component: Annotated[
        bool,
        "If true, expand the component foldout in Inspector. Default true."
    ] = True,
    lock: Annotated[
        bool,
        "For open/open_component: if true, lock the inspector to this target. Default false."
    ] = False,
    mode: Annotated[
        Literal["normal", "debug", "debug_internal"],
        "Inspector mode to use. Default 'normal'."
    ] = "normal",
    target_name: Annotated[
        str | None,
        "Alias for a single target name."
    ] = None,
    target_names: Annotated[
        list[str] | None,
        "Alias for multi-selection target names."
    ] = None,
    instance_id: Annotated[
        int | None,
        "Alias for a target instance ID."
    ] = None,
    asset_guid: Annotated[
        str | None,
        "Alias for a target GUID."
    ] = None,
    asset_path: Annotated[
        str | None,
        "Alias for a target asset path."
    ] = None,
    focus_component: Annotated[
        str | None,
        "Alias for component_type."
    ] = None,
) -> dict[str, Any]:
    """Open a target in the Unity Inspector window.

    Args:
        ctx: FastMCP context
        action: Inspector action to perform
        target: Target object(s) to open
        component_type: Component type name for open_component action
        component_index: Component index for open_component action
        expand_component: Whether to expand component foldout
        lock: Whether to lock the inspector
        mode: Inspector mode (normal, debug, debug_internal)

    Returns:
        Inspector operation result with target info
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    # Preflight check
    gate = await maybe_run_tool_preflight(ctx, "open_inspector_target", action=action)
    if gate is not None:
        return gate.model_dump()

    try:
        resolved_action = action
        resolved_target = target
        if resolved_target is None and target_names is not None:
            resolved_target = target_names
        elif resolved_target is None and target_name is not None:
            resolved_target = target_name
        elif resolved_target is None and instance_id is not None:
            resolved_target = instance_id
        elif resolved_target is None and asset_guid is not None:
            resolved_target = {"guid": asset_guid}
        elif resolved_target is None and asset_path is not None:
            resolved_target = {"path": asset_path}

        resolved_component_type = focus_component or component_type
        if resolved_component_type and resolved_action == "open":
            resolved_action = "open_component"

        # Build parameters
        params: dict[str, Any] = {
            "navigationType": "open_inspector",
            "inspectorAction": resolved_action,
            "inspectorMode": mode,
        }

        # Add target if provided and applicable
        if resolved_target is not None and resolved_action not in ("get_target", "lock", "unlock", "clear"):
            if isinstance(resolved_target, list):
                # Multi-object edit
                target_list = []
                for t in resolved_target:
                    if isinstance(t, dict):
                        target_list.append(t)
                    elif isinstance(t, int):
                        target_list.append({"instance_id": t})
                    else:
                        target_list.append({"name": t})
                params["target"] = {"multi": True, "objects": target_list}
            elif isinstance(resolved_target, dict):
                params["target"] = resolved_target
            elif isinstance(resolved_target, int):
                params["target"] = {"instance_id": resolved_target}
            else:
                params["target"] = {"name": resolved_target}

        # Add component-specific parameters
        if resolved_component_type is not None:
            params["componentType"] = resolved_component_type
        if component_index is not None:
            params["componentIndex"] = component_index
        if expand_component is not None:
            params["expandComponent"] = expand_component
        if lock is not None:
            params["lockInspector"] = lock

        # Send command to Unity
        response = await send_with_unity_instance(
            async_send_command_with_retry, unity_instance, "navigate_editor", params
        )

        # Process response
        if hasattr(response, 'model_dump'):
            result = response.model_dump()
        elif isinstance(response, dict):
            result = response
        else:
            return {
                "success": False,
                "message": f"Unexpected response type: {type(response).__name__}"
            }

        # Standardize response format
        target_info = result.get("target_info", {})
        if resolved_target is not None and not target_info:
            if isinstance(resolved_target, dict):
                target_info = resolved_target
            elif isinstance(resolved_target, int):
                target_info = {"instance_id": resolved_target}
            elif isinstance(resolved_target, list):
                target_info = {"multi": True, "count": len(resolved_target)}
            else:
                target_info = {"name": resolved_target}

        return {
            "success": result.get("success", False),
            "message": result.get("message", "Inspector navigation completed"),
            "data": result.get("data", {}),
            "navigation_id": result.get("navigation_id"),
            "action": "open_inspector",
            "inspector_action": resolved_action,
            "target": target_info,
            "result": result.get("result", {}),
            "editor_state": result.get("editor_state", {}),
            "inspector_state": result.get("inspector_state", {}),
            "target_info": target_info,
        }

    except TimeoutError:
        return {
            "success": False,
            "message": "Unity connection timeout. Please check if Unity is running and responsive."
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"Error opening inspector target: {exc}"
        }
