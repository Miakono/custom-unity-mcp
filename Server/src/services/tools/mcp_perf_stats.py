"""
mcp_perf_stats — surface in-process Unity-side perf counters.

Exposes per-tool latency, compile-trigger count, idle/active editor ticks, and
the top-N slowest tools by cumulative cost from the always-on PerfMetrics sink.
Complements the sampled Python-side traces (start_trace / get_trace_summary)
with allocation-free hot-path counters that run continuously in the editor.
"""
from typing import Annotated, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from models import MCPResponse
from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    description=(
        "Read or reset Unity-side performance counters. Action 'snapshot' (default) "
        "returns per-tool latency, compile-trigger count, idle/active ticks, and the "
        "top-N slowest tools by cumulative cost. Action 'reset' clears all counters. "
        "Always-on, allocation-free; use freely between tool calls to spot regressions."
    ),
    annotations=ToolAnnotations(
        title="MCP Performance Stats",
        destructiveHint=False,
    ),
    group="profiling",
)
async def mcp_perf_stats(
    ctx: Context,
    action: Annotated[
        Literal["snapshot", "reset"],
        "snapshot returns counters; reset clears them.",
    ] = "snapshot",
    top_n: Annotated[
        int,
        "How many top-slow tools to include in snapshot.top_tools.",
    ] = 20,
) -> MCPResponse:
    gate = await maybe_run_tool_preflight(ctx, "mcp_perf_stats")
    if gate is not None:
        return MCPResponse(**gate.model_dump())

    unity_instance = await get_unity_instance_from_context(ctx)
    params: dict = {"action": action, "top_n": top_n}
    result = await send_with_unity_instance(
        async_send_command_with_retry, unity_instance, "mcp_perf_stats", params
    )
    return MCPResponse(**result) if isinstance(result, dict) else result
