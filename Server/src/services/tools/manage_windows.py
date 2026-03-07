"""Tool for managing Unity Editor windows and tools."""

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    description=(
        "Manages Unity Editor windows and tools. "
        "Actions: list_windows, open_window, focus_window, close_window, get_active_tool, set_active_tool. "
        "Use list_windows to see all open editor windows with their IDs. "
        "Use open_window with window_type (e.g., 'Console', 'Inspector', 'Scene', 'Game', 'Hierarchy'). "
        "Use focus_window to bring a window to front. "
        "Use set_active_tool to change transform tools: View, Move, Rotate, Scale, Rect, Transform, Custom."
    ),
    annotations=ToolAnnotations(
        title="Manage Windows",
        destructiveHint=False,
    ),
)
async def manage_windows(
    ctx: Context,
    action: Annotated[
        Literal[
            "list_windows",
            "open_window",
            "focus_window",
            "close_window",
            "get_active_tool",
            "set_active_tool",
        ],
        "Window operation to perform.",
    ],
    window_type: Annotated[
        str,
        "Window type/name to open. Common values: Console, Inspector, Scene, Game, Hierarchy, Project, Animation, Animator."
    ] | None = None,
    window_id: Annotated[
        int,
        "Window ID for focus/close operations (from list_windows)."
    ] | None = None,
    window_title: Annotated[
        str,
        "Window title to match for focus/close operations."
    ] | None = None,
    tool_name: Annotated[
        str,
        "Tool name for set_active_tool. Values: View, Move, Rotate, Scale, Rect, Transform, Custom."
    ] | None = None,
) -> dict[str, Any]:
    """Manage Unity Editor windows and tools.

    Args:
        ctx: FastMCP context
        action: Window operation to perform
        window_type: Window type/name to open
        window_id: Window ID for focus/close operations
        window_title: Window title to match
        tool_name: Tool name for set_active_tool

    Returns:
        dict with success status and message/data
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    # Preflight check
    gate = await maybe_run_tool_preflight(ctx, "manage_windows", action=action)
    if gate is not None:
        return gate.model_dump()

    try:
        # Build parameters dictionary
        params: dict[str, Any] = {"action": action}

        if window_type is not None:
            params["windowType"] = window_type
        if window_id is not None:
            params["windowId"] = window_id
        if window_title is not None:
            params["windowTitle"] = window_title
        if tool_name is not None:
            params["toolName"] = tool_name

        # Send command to Unity
        response = await send_with_unity_instance(
            async_send_command_with_retry, unity_instance, "manage_windows", params
        )

        # Return Unity response directly; ensure success field exists
        if hasattr(response, 'model_dump'):
            return response.model_dump()
        if isinstance(response, dict):
            if "success" not in response:
                response["success"] = False
            return response
        return {
            "success": False,
            "message": f"Unexpected response type: {type(response).__name__}"
        }

    except TimeoutError:
        return {
            "success": False,
            "message": "Unity connection timeout. Please check if Unity is running and responsive."
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"Error managing windows: {exc}"
        }
