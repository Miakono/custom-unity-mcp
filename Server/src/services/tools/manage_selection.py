"""Tool for managing Unity Editor selection."""

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
        "Manages Unity Editor selection. "
        "Actions: set_selection (set selected objects by path/ID), "
        "frame_selection (frame selected objects in scene view), "
        "get_selection (get currently selected objects). "
        "Use set_selection with clear=true to clear selection, "
        "or add=true to add to existing selection."
    ),
    annotations=ToolAnnotations(
        title="Manage Selection",
        destructiveHint=False,
    ),
)
async def manage_selection(
    ctx: Context,
    action: Annotated[
        Literal["set_selection", "frame_selection", "get_selection"],
        "Selection operation to perform.",
    ],
    target: Annotated[
        str | int | list[str | int],
        "Target object(s) to select. Can be GameObject name, path, instance ID, or list of these."
    ] | None = None,
    clear: Annotated[
        bool,
        "If true, clear existing selection before selecting new objects. Default true for set_selection."
    ] | None = None,
    add: Annotated[
        bool,
        "If true, add to existing selection instead of replacing. Default false."
    ] | None = None,
    frame_selected: Annotated[
        bool,
        "For frame_selection: if true, frame all currently selected objects. Default true."
    ] | None = None,
) -> dict[str, Any]:
    """Manage Unity Editor selection.

    Args:
        ctx: FastMCP context
        action: Selection operation to perform
        target: Target object(s) to select
        clear: Whether to clear existing selection
        add: Whether to add to existing selection
        frame_selected: Whether to frame selected objects

    Returns:
        dict with success status and message
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    # Preflight check
    gate = await maybe_run_tool_preflight(ctx, "manage_selection", action=action)
    if gate is not None:
        return gate.model_dump()

    try:
        # Build parameters dictionary
        params: dict[str, Any] = {"action": action}

        if target is not None:
            params["target"] = target
        if clear is not None:
            params["clear"] = clear
        if add is not None:
            params["add"] = add
        if frame_selected is not None:
            params["frameSelected"] = frame_selected

        # Send command to Unity
        response = await send_with_unity_instance(
            async_send_command_with_retry, unity_instance, "manage_selection", params
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
            "message": f"Error managing selection: {exc}"
        }
