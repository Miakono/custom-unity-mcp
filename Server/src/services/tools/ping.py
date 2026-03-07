"""Simple connectivity check tool for the MCP server."""

from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    unity_target=None,
    description=(
        "Simple connectivity check. Returns server status and optionally pings Unity. "
        "Use this to verify the MCP server is running and responsive. "
        "Set ping_unity=true to also check Unity connection."
    ),
    annotations=ToolAnnotations(
        title="Ping",
        destructiveHint=False,
    ),
)
async def ping(
    ctx: Context,
    ping_unity: Annotated[
        bool,
        "If true, also ping Unity to verify connection. Default false."
    ] | None = None,
) -> dict[str, Any]:
    """Simple connectivity check.

    Args:
        ctx: FastMCP context
        ping_unity: Whether to also ping Unity

    Returns:
        dict with server status and Unity connection status
    """
    result: dict[str, Any] = {
        "success": True,
        "message": "MCP server is running",
        "server_status": "running",
    }

    if ping_unity:
        try:
            unity_instance = await get_unity_instance_from_context(ctx)
            response = await send_with_unity_instance(
                async_send_command_with_retry, unity_instance, "ping", {}
            )
            result["unity_status"] = "connected"
            result["unity_response"] = response if isinstance(response, dict) else {"message": str(response)}
        except Exception as exc:
            result["unity_status"] = "disconnected"
            result["unity_error"] = str(exc)
    else:
        result["unity_status"] = "not_checked"

    return result
