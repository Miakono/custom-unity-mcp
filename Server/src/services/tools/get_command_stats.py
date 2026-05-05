"""Tool for retrieving command usage statistics."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool


@mcp_for_unity_tool(
    unity_target=None,
    description=(
        "Retrieves command usage statistics aggregated from active and recently-completed "
        "trace sessions. Returns total commands, success/error counts, latency percentiles, "
        "and the top tools by call count and slowest mean latency. To capture stats, run "
        "start_trace before exercising tools (the most recent ~50 completed traces are also "
        "aggregated by default). Filterable by tool name and time window."
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
    """Aggregate per-tool stats from the dev_trace_tools session store.

    The trace store is the source of truth for live request data — it's already populated
    by send_with_unity_instance, so this endpoint just summarises it. Fall back to
    telemetry-config status only when no trace data is available.
    """
    try:
        from services.tools.dev_trace_tools import _active_traces, _completed_traces
        from core.telemetry import is_telemetry_enabled, RecordType

        hours = since_hours if since_hours is not None else 24
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Collect all entries from active + completed traces inside the time window.
        all_entries = []
        for trace in list(_active_traces.values()) + list(_completed_traces.values()):
            for entry in trace.entries:
                if entry.timestamp < cutoff:
                    continue
                if tool_filter and entry.tool != tool_filter:
                    continue
                all_entries.append(entry)

        if not all_entries:
            return {
                "success": True,
                "message": (
                    f"No trace data in the last {hours} hours. Run start_trace before "
                    "exercising tools to capture stats, or widen since_hours."
                ),
                "data": {
                    "total_commands": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "period_hours": hours,
                    "tool_filter": tool_filter,
                    "telemetry_enabled": is_telemetry_enabled(),
                    "record_types_tracked": [rt.value for rt in RecordType],
                    "by_tool": {},
                    "top_tools_by_calls": [],
                    "slowest_tools_by_mean_latency": [],
                },
            }

        success_count = sum(1 for e in all_entries if e.response_status == "success")
        error_count = len(all_entries) - success_count

        # Per-tool aggregates.
        by_tool: dict[str, dict[str, Any]] = {}
        for entry in all_entries:
            stats = by_tool.setdefault(entry.tool, {
                "calls": 0, "errors": 0, "_latencies": []
            })
            stats["calls"] += 1
            if entry.response_status != "success":
                stats["errors"] += 1
            stats["_latencies"].append(entry.latency_ms)

        for tool, stats in by_tool.items():
            lats = sorted(stats.pop("_latencies"))
            stats["mean_ms"] = round(sum(lats) / len(lats), 3)
            stats["min_ms"] = round(lats[0], 3)
            stats["max_ms"] = round(lats[-1], 3)
            # P95 — index = ceil(0.95 * n) - 1, clamped.
            p95_idx = max(0, min(len(lats) - 1, int(0.95 * len(lats))))
            stats["p95_ms"] = round(lats[p95_idx], 3)
            stats["error_rate"] = round(stats["errors"] / stats["calls"], 4)

        top_by_calls = sorted(
            ({"tool": t, **s} for t, s in by_tool.items()),
            key=lambda x: x["calls"], reverse=True,
        )[:10]
        slowest_by_mean = sorted(
            ({"tool": t, **s} for t, s in by_tool.items()),
            key=lambda x: x["mean_ms"], reverse=True,
        )[:10]

        return {
            "success": True,
            "message": (
                f"Aggregated {len(all_entries)} trace entries from the last {hours} hours."
            ),
            "data": {
                "total_commands": len(all_entries),
                "success_count": success_count,
                "error_count": error_count,
                "error_rate": round(error_count / len(all_entries), 4) if all_entries else 0,
                "unique_tools": len(by_tool),
                "period_hours": hours,
                "tool_filter": tool_filter,
                "telemetry_enabled": is_telemetry_enabled(),
                "by_tool": by_tool,
                "top_tools_by_calls": top_by_calls,
                "slowest_tools_by_mean_latency": slowest_by_mean,
            },
        }

    except Exception as exc:
        return {
            "success": False,
            "message": f"Error retrieving command statistics: {exc}",
            "error_code": "STATS_RETRIEVAL_FAILED",
        }
