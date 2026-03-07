from __future__ import annotations

"""Tool for navigating the Unity Editor and directing user attention.

This is the main navigation tool that provides comprehensive editor navigation
capabilities including revealing assets, focusing hierarchy, framing objects,
opening inspectors, and managing editor context.
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
        "Navigates the Unity Editor to direct user attention. "
        "Navigation types: reveal_in_project (ping/highlight asset in Project window), "
        "focus_hierarchy (focus and expand GameObject in Hierarchy), "
        "frame_in_scene (frame object in Scene view camera), "
        "open_inspector (open object in Inspector), "
        "open_script (open script at specific line/symbol), "
        "open_asset (open asset at path in appropriate editor), "
        "get_context (return current editor state without navigation). "
        "Use restore_context with previous_context to restore editor state."
    ),
    annotations=ToolAnnotations(
        title="Navigate Editor",
        destructiveHint=False,
    ),
)
async def navigate_editor(
    ctx: Context,
    navigation_type: Annotated[
        Literal[
            "reveal_in_project",
            "focus_hierarchy", 
            "frame_in_scene",
            "open_inspector",
            "open_script",
            "open_asset",
            "get_context",
            "restore_context",
        ],
        "Type of navigation action to perform."
    ],
    target: Annotated[
        str | int | dict[str, Any] | None,
        "Target for navigation. Can be asset path (str), GameObject instance ID (int), "
        "or dict with 'path', 'instance_id', 'guid', or 'name' keys."
    ] = None,
    line_number: Annotated[
        int | None,
        "For open_script: line number to navigate to (1-based)."
    ] = None,
    column_number: Annotated[
        int | None,
        "For open_script: column number to navigate to (1-based)."
    ] = None,
    symbol_name: Annotated[
        str | None,
        "For open_script: specific symbol/method name to navigate to."
    ] = None,
    expand_hierarchy: Annotated[
        bool,
        "For focus_hierarchy: whether to expand the target's hierarchy. Default true."
    ] = True,
    frame_selected: Annotated[
        bool,
        "For frame_in_scene: whether to frame currently selected objects. Default true."
    ] = True,
    lock_inspector: Annotated[
        bool,
        "For open_inspector: whether to lock the inspector to this object. Default false."
    ] = False,
    previous_context: Annotated[
        dict[str, Any] | None,
        "For restore_context: the context dict previously returned by get_context or a navigation action."
    ] = None,
    wait_for_completion: Annotated[
        bool,
        "If true, waits for navigation to complete before returning. Default true."
    ] = True,
) -> dict[str, Any]:
    """Navigate the Unity Editor to direct user attention.

    Args:
        ctx: FastMCP context
        navigation_type: Type of navigation to perform
        target: Target object/path for navigation
        line_number: Line number for script navigation (1-based)
        column_number: Column number for script navigation (1-based)
        symbol_name: Symbol name for script navigation
        expand_hierarchy: Whether to expand hierarchy when focusing
        frame_selected: Whether to frame selected objects
        lock_inspector: Whether to lock inspector to object
        previous_context: Context to restore (for restore_context)
        wait_for_completion: Whether to wait for operation to complete

    Returns:
        Navigation result with navigation_id, action, target, result, and editor_state
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    # Preflight check
    gate = await maybe_run_tool_preflight(ctx, "navigate_editor", action=navigation_type)
    if gate is not None:
        return gate.model_dump()

    try:
        # Build command parameters
        params: dict[str, Any] = {
            "navigationType": navigation_type,
            "waitForCompletion": wait_for_completion,
        }

        # Add target if provided
        if target is not None:
            if isinstance(target, dict):
                params["target"] = target
            elif isinstance(target, int):
                params["target"] = {"instance_id": target}
            else:
                params["target"] = {"path": target}

        # Add navigation-specific parameters
        if line_number is not None:
            params["lineNumber"] = line_number
        if column_number is not None:
            params["columnNumber"] = column_number
        if symbol_name is not None:
            params["symbolName"] = symbol_name
        if expand_hierarchy is not None:
            params["expandHierarchy"] = expand_hierarchy
        if frame_selected is not None:
            params["frameSelected"] = frame_selected
        if lock_inspector is not None:
            params["lockInspector"] = lock_inspector
        if previous_context is not None:
            params["previousContext"] = previous_context

        # Send command to Unity
        response = await send_with_unity_instance(
            async_send_command_with_retry, unity_instance, "navigate_editor", params
        )

        # Return Unity response directly; ensure success field exists
        if hasattr(response, 'model_dump'):
            result = response.model_dump()
        elif isinstance(response, dict):
            result = response
            if "success" not in result:
                result["success"] = False
        else:
            return {
                "success": False,
                "message": f"Unexpected response type: {type(response).__name__}"
            }

        # Ensure standard navigation result format
        if result.get("success") and "navigation_id" not in result:
            # Unity didn't return full navigation format, wrap it
            result = {
                "navigation_id": f"nav_{navigation_type}_{id(target) if target else 'none'}",
                "action": navigation_type,
                "target": target if isinstance(target, dict) else {"path": str(target) if target else None},
                "result": {
                    "success": True,
                    "message": result.get("message", "Navigation completed"),
                },
                "editor_state": result.get("editor_state", {}),
                **result
            }

        return result

    except TimeoutError:
        return {
            "success": False,
            "navigation_id": None,
            "action": navigation_type,
            "target": target,
            "result": {
                "success": False,
                "message": "Unity connection timeout. Please check if Unity is running and responsive."
            },
            "editor_state": {}
        }
    except Exception as exc:
        return {
            "success": False,
            "navigation_id": None,
            "action": navigation_type,
            "target": target,
            "result": {
                "success": False,
                "message": f"Error navigating editor: {exc}"
            },
            "editor_state": {}
        }
