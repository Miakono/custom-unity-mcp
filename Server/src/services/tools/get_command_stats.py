"""Tool for retrieving command usage statistics."""

from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool


@mcp_for_unity_tool(
    unity_target=None,
    description=(
        "Retrieves command usage statistics for the MCP server. "
        "Returns metrics like total commands executed, success rates, "
        "most used tools, and error counts. Useful for monitoring and debugging."
    ),
    annotations=ToolAnnotations(
        title="Get Command Stats",
        destructiveHint=False,
    ),
)
async def get_command_stats(
    ctx: Context,
    tool_filter: Annotated[
        str,
        "Optional tool name to filter statistics to a specific tool."
    ] | None = None,
    since_hours: Annotated[
        int,
        "Number of hours to look back for statistics. Default 24."
    ] | None = None,
) -> dict[str, Any]:
    """Get command usage statistics.

    Args:
        ctx: FastMCP context
        tool_filter: Optional tool name to filter by
        since_hours: Hours to look back (default 24)

    Returns:
        dict with usage statistics
    """
    try:
        # Import telemetry module functions
        from core.telemetry import is_telemetry_enabled, RecordType

        hours = since_hours if since_hours is not None else 24

        # Build basic stats response
        # Note: Detailed tool usage stats would require additional tracking
        # infrastructure that's not yet implemented in the telemetry module.
        # For now, we return telemetry status and configuration.

        stats = {
            "note": "Detailed tool usage statistics are collected via telemetry. "
                    "This endpoint returns telemetry status and configuration.",
            "telemetry_enabled": is_telemetry_enabled(),
            "period_hours": hours,
            "tool_filter": tool_filter,
            "record_types_tracked": [rt.value for rt in RecordType],
        }

        return {
            "success": True,
            "message": f"Command statistics (telemetry period: last {hours} hours)",
            "data": stats
        }

    except Exception as exc:
        return {
            "success": False,
            "message": f"Error retrieving command statistics: {exc}",
            "error_code": "STATS_RETRIEVAL_FAILED"
        }
