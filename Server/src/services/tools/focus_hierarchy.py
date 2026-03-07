from __future__ import annotations

"""Tool for focusing and expanding GameObjects in the Unity Hierarchy window.

Provides hierarchy navigation functionality to focus on specific GameObjects,
expand their hierarchy tree, and manage visibility in the Hierarchy panel.
"""

from typing import Annotated, Any

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
        "Focuses and expands a GameObject in the Unity Hierarchy window. "
        "Scrolls to make the GameObject visible, optionally expands its children, "
        "and can select the object. Use this to direct user attention to specific "
        "GameObjects in the scene hierarchy."
    ),
    annotations=ToolAnnotations(
        title="Focus Hierarchy",
        destructiveHint=False,
    ),
)
async def focus_hierarchy(
    ctx: Context,
    target: Annotated[
        str | int | dict[str, Any] | None,
        "Target GameObject to focus. Can be: GameObject name (str), "
        "instance ID (int), or dict with 'name', 'path', or 'instance_id' keys. "
        "Path format: 'Parent/Child/GrandChild'"
    ] = None,
    target_name: Annotated[
        str | None,
        "Alias for a GameObject name target."
    ] = None,
    instance_id: Annotated[
        int | None,
        "Alias for an instance ID target."
    ] = None,
    hierarchy_path: Annotated[
        str | None,
        "Alias for a hierarchy path target."
    ] = None,
    expand: Annotated[
        bool,
        "If true, expand the target GameObject's hierarchy to show children. Default true."
    ] = True,
    expand_depth: Annotated[
        int | None,
        "Number of levels to expand when expand=true. None means expand all children."
    ] = None,
    select: Annotated[
        bool,
        "If true, select the target GameObject. Default true."
    ] = True,
    frame_in_scene: Annotated[
        bool,
        "If true, also frame the object in the Scene view. Default false."
    ] = False,
    highlight: Annotated[
        bool,
        "If true, briefly highlight the GameObject row in Hierarchy. Default true."
    ] = True,
) -> dict[str, Any]:
    """Focus and expand a GameObject in the Unity Hierarchy window.

    Args:
        ctx: FastMCP context
        target: Target GameObject to focus (name, instance ID, or dict)
        expand: Whether to expand the GameObject's hierarchy
        expand_depth: How many levels deep to expand
        select: Whether to select the GameObject
        frame_in_scene: Whether to also frame in Scene view
        highlight: Whether to highlight the GameObject row

    Returns:
        Focus result with GameObject info and hierarchy state
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    # Preflight check
    gate = await maybe_run_tool_preflight(ctx, "focus_hierarchy", action="focus")
    if gate is not None:
        return gate.model_dump()

    try:
        resolved_target = target
        if resolved_target is None and target_name is not None:
            resolved_target = target_name
        if resolved_target is None and instance_id is not None:
            resolved_target = instance_id
        if resolved_target is None and hierarchy_path is not None:
            resolved_target = {"path": hierarchy_path}

        # Normalize target to dict format
        target_dict: dict[str, Any]
        if isinstance(resolved_target, dict):
            target_dict = resolved_target
        elif isinstance(resolved_target, int):
            target_dict = {"instance_id": resolved_target}
        elif isinstance(resolved_target, str):
            target_dict = {"name": resolved_target}
        else:
            target_dict = {}

        # Build parameters
        params: dict[str, Any] = {
            "navigationType": "focus_hierarchy",
            "expandHierarchy": expand,
            "select": select,
            "highlight": highlight,
            "frameInScene": frame_in_scene,
        }
        if target_dict:
            params["target"] = target_dict
        if expand_depth is not None:
            params["expandDepth"] = expand_depth

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
        return {
            "success": result.get("success", False),
            "message": result.get("message", "Hierarchy focus completed"),
            "data": result.get("data", {}),
            "navigation_id": result.get("navigation_id"),
            "action": "focus_hierarchy",
            "target": target_dict,
            "result": result.get("result", {}),
            "editor_state": result.get("editor_state", {}),
            "gameobject_info": result.get("gameobject_info", {}),
            "hierarchy_state": result.get("hierarchy_state", {}),
        }

    except TimeoutError:
        return {
            "success": False,
            "message": "Unity connection timeout. Please check if Unity is running and responsive."
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"Error focusing hierarchy: {exc}"
        }
