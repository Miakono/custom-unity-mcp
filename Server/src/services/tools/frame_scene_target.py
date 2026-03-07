from __future__ import annotations

"""Tool for framing/targeting objects in the Unity Scene view.

Provides Scene view camera control to frame specific GameObjects,
adjust camera position, and query current camera state.
"""

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from services.tools.utils import normalize_vector3
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    group="navigation",
    description=(
        "Frames a target in the Unity Scene view camera. "
        "Can frame selected objects, a specific GameObject, or a world position. "
        "Also supports querying the current Scene view camera pose. "
        "Use this to direct user attention to specific areas of the scene."
    ),
    annotations=ToolAnnotations(
        title="Frame Scene Target",
        destructiveHint=False,
    ),
)
async def frame_scene_target(
    ctx: Context,
    target_type: Annotated[
        Literal["selection", "gameobject", "position", "query_camera"],
        "Type of target to frame. 'selection' frames current selection, "
        "'gameobject' frames a specific GameObject, 'position' frames a world position, "
        "'query_camera' returns current camera pose without framing."
    ] = "selection",
    target: Annotated[
        str | int | dict[str, Any] | None,
        "Target to frame. For gameobject: name (str), instance ID (int), or dict. "
        "For position: dict with 'x', 'y', 'z' keys or [x, y, z] list. "
        "Not used for selection or query_camera."
    ] = None,
    view_angle: Annotated[
        Literal["front", "back", "left", "right", "top", "bottom", "perspective", "current"],
        "Camera angle to use for framing. Default 'current' preserves current angle."
    ] = "current",
    distance: Annotated[
        float | None,
        "Override distance from target. None uses auto-calculated distance."
    ] = None,
    orthographic: Annotated[
        bool | None,
        "Whether to use orthographic camera mode. None preserves current mode."
    ] = None,
    duration: Annotated[
        float,
        "Animation duration for camera movement in seconds. 0 = instant. Default 0.5."
    ] = 0.5,
    target_name: Annotated[
        str | None,
        "Alias for a GameObject name target."
    ] = None,
    instance_id: Annotated[
        int | None,
        "Alias for an instance ID target."
    ] = None,
    bounds_center: Annotated[
        list[float] | dict[str, float] | None,
        "Optional bounds center to frame."
    ] = None,
    bounds_size: Annotated[
        list[float] | dict[str, float] | None,
        "Optional bounds size to frame."
    ] = None,
    camera_distance: Annotated[
        float | None,
        "Alias for distance."
    ] = None,
    mode: Annotated[
        str | None,
        "Optional scene view mode alias."
    ] = None,
    frame_selected: Annotated[
        bool,
        "Alias for explicitly framing the current selection. Default true."
    ] = True,
) -> dict[str, Any]:
    """Frame a target in the Unity Scene view camera.

    Args:
        ctx: FastMCP context
        target_type: Type of target to frame
        target: Target specification (GameObject name/ID or position)
        view_angle: Camera angle for framing
        distance: Override distance from target
        orthographic: Override orthographic mode
        duration: Camera animation duration in seconds

    Returns:
        Frame result with camera pose and target info
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    # Preflight check
    gate = await maybe_run_tool_preflight(ctx, "frame_scene_target", action="frame")
    if gate is not None:
        return gate.model_dump()

    try:
        resolved_target_type = target_type
        resolved_target = target
        if target_name is not None:
            resolved_target_type = "gameobject"
            resolved_target = target_name
        elif instance_id is not None:
            resolved_target_type = "gameobject"
            resolved_target = instance_id
        elif bounds_center is not None or bounds_size is not None:
            resolved_target_type = "position"
            resolved_target = bounds_center
        elif frame_selected:
            resolved_target_type = "selection"

        # Build parameters
        params: dict[str, Any] = {
            "navigationType": "frame_in_scene",
            "targetType": resolved_target_type,
            "viewAngle": view_angle,
            "duration": duration,
        }

        # Add target if provided
        if resolved_target is not None:
            if resolved_target_type == "position":
                # Normalize position to dict format
                if isinstance(resolved_target, dict) and all(k in resolved_target for k in ("x", "y", "z")):
                    params["target"] = resolved_target
                elif isinstance(resolved_target, (list, tuple)) and len(resolved_target) == 3:
                    params["target"] = {"x": resolved_target[0], "y": resolved_target[1], "z": resolved_target[2]}
                else:
                    vec, err = normalize_vector3(resolved_target, "target position")
                    if err:
                        return {"success": False, "message": err}
                    if vec:
                        params["target"] = {"x": vec[0], "y": vec[1], "z": vec[2]}
            elif isinstance(resolved_target, dict):
                params["target"] = resolved_target
            elif isinstance(resolved_target, int):
                params["target"] = {"instance_id": resolved_target}
            else:
                params["target"] = {"name": resolved_target}

        if bounds_center is not None:
            params["boundsCenter"] = bounds_center
        if bounds_size is not None:
            params["boundsSize"] = bounds_size
        if mode is not None:
            params["mode"] = mode

        # Add optional parameters
        if camera_distance is not None:
            params["distance"] = camera_distance
        elif distance is not None:
            params["distance"] = distance
        if orthographic is not None:
            params["orthographic"] = orthographic

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
            "message": result.get("message", "Scene framing completed"),
            "data": result.get("data", {}),
            "navigation_id": result.get("navigation_id"),
            "action": "frame_in_scene",
            "target_type": resolved_target_type,
            "target": params.get("target", {}),
            "result": result.get("result", {}),
            "editor_state": result.get("editor_state", {}),
            "camera_pose": result.get("camera_pose", {}),
        }

    except TimeoutError:
        return {
            "success": False,
            "message": "Unity connection timeout. Please check if Unity is running and responsive."
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"Error framing scene target: {exc}"
        }
