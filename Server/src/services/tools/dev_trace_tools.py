"""Development tracing tools for MCP request debugging.

This module provides request tracing capabilities to help developers debug
tool execution flows, analyze performance, and diagnose issues.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool


@dataclass
class TraceEntry:
    """A single trace entry capturing a tool invocation."""
    timestamp: datetime
    tool: str
    normalized_params: dict[str, Any]
    unity_instance: str | None
    retries: int
    latency_ms: float
    response_status: str
    error: str | None = None
    trace_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceSession:
    """A complete tracing session with multiple entries."""
    trace_id: str
    started_at: datetime
    entries: list[TraceEntry] = field(default_factory=list)
    is_active: bool = True
    tags: list[str] = field(default_factory=list)


# In-memory storage for active and completed traces
_active_traces: dict[str, TraceSession] = {}
_completed_traces: dict[str, TraceSession] = {}

# Global trace collector for middleware integration
_current_trace_id: str | None = None
_cleared_active_trace_without_flag = False


def get_current_trace_id() -> str | None:
    """Get the currently active trace ID for middleware integration."""
    return _current_trace_id


def set_current_trace_id(trace_id: str | None) -> None:
    """Set the currently active trace ID."""
    global _current_trace_id
    _current_trace_id = trace_id


def record_trace_entry(
    tool: str,
    normalized_params: dict[str, Any],
    unity_instance: str | None,
    retries: int,
    latency_ms: float,
    response_status: str,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Record a trace entry to the currently active trace.
    
    Called by middleware/tool wrappers to capture execution details.
    
    Args:
        tool: Name of the tool being invoked
        normalized_params: Normalized parameters after processing
        unity_instance: Target Unity instance ID
        retries: Number of retry attempts made
        latency_ms: Request latency in milliseconds
        response_status: Status of the response (success, error, etc.)
        error: Error message if the request failed
        metadata: Additional metadata to include
        
    Returns:
        True if entry was recorded, False if no active trace
    """
    trace_id = _current_trace_id
    if trace_id is None or trace_id not in _active_traces:
        return False
    
    trace = _active_traces[trace_id]
    if not trace.is_active:
        return False
    
    entry = TraceEntry(
        timestamp=datetime.utcnow(),
        tool=tool,
        normalized_params=normalized_params,
        unity_instance=unity_instance,
        retries=retries,
        latency_ms=latency_ms,
        response_status=response_status,
        error=error,
        trace_metadata=metadata or {},
    )
    trace.entries.append(entry)
    return True


def _trace_to_dict(trace: TraceSession) -> dict[str, Any]:
    """Convert a TraceSession to a dictionary."""
    return {
        "trace_id": trace.trace_id,
        "started_at": trace.started_at.isoformat(),
        "is_active": trace.is_active,
        "tags": trace.tags,
        "entries": [
            {
                "timestamp": entry.timestamp.isoformat(),
                "tool": entry.tool,
                "normalized_params": entry.normalized_params,
                "unity_instance": entry.unity_instance,
                "retries": entry.retries,
                "latency_ms": round(entry.latency_ms, 3),
                "response_status": entry.response_status,
                "error": entry.error,
                "metadata": entry.trace_metadata,
            }
            for entry in trace.entries
        ],
    }


def _get_summary_stats(trace: TraceSession) -> dict[str, Any]:
    """Compute summary statistics for a trace."""
    if not trace.entries:
        return {
            "total_requests": 0,
            "total_latency_ms": 0.0,
            "avg_latency_ms": 0.0,
            "min_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "success_count": 0,
            "error_count": 0,
            "total_retries": 0,
            "tools_used": [],
        }
    
    latencies = [e.latency_ms for e in trace.entries]
    success_count = sum(1 for e in trace.entries if e.response_status == "success")
    error_count = len(trace.entries) - success_count
    tools_used = list(set(e.tool for e in trace.entries))
    total_retries = sum(e.retries for e in trace.entries)
    
    return {
        "total_requests": len(trace.entries),
        "total_latency_ms": round(sum(latencies), 3),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 3),
        "min_latency_ms": round(min(latencies), 3),
        "max_latency_ms": round(max(latencies), 3),
        "success_count": success_count,
        "error_count": error_count,
        "total_retries": total_retries,
        "tools_used": tools_used,
    }


@mcp_for_unity_tool(
    group="dev_tools",
    name="start_trace",
    unity_target=None,
    description=(
        "Begin tracing MCP tool invocations. Captures request details including "
        "normalized parameters, Unity instance selection, retries, latency, and "
        "response status. Use stop_trace to end tracing and retrieve data."
    ),
    annotations=ToolAnnotations(
        title="Start Request Trace",
        destructiveHint=False,
    ),
)
async def start_trace(
    ctx: Context,
    tags: Annotated[
        list[str] | None,
        "Optional tags to associate with this trace session for categorization"
    ] = None,
) -> dict[str, Any]:
    """Begin a new tracing session.
    
    Args:
        ctx: FastMCP context
        tags: Optional list of tags for categorization
        
    Returns:
        Trace session details including trace_id
    """
    trace_id = str(uuid.uuid4())
    
    trace = TraceSession(
        trace_id=trace_id,
        started_at=datetime.utcnow(),
        tags=tags or [],
    )
    
    _active_traces[trace_id] = trace
    set_current_trace_id(trace_id)
    
    await ctx.info(f"Started trace session: {trace_id}")
    
    return {
        "success": True,
        "trace_id": trace_id,
        "started_at": trace.started_at.isoformat(),
        "message": f"Trace session started. ID: {trace_id}",
    }


@mcp_for_unity_tool(
    name="stop_trace",
    unity_target=None,
    description=(
        "End the active tracing session and return the complete trace data. "
        "Includes all captured tool invocations with timing, retries, and responses."
    ),
    annotations=ToolAnnotations(
        title="Stop Request Trace",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def stop_trace(
    ctx: Context,
    trace_id: Annotated[
        str | None,
        "Trace ID to stop (defaults to current active trace)"
    ] = None,
    include_entries: Annotated[
        bool,
        "Whether to include full entry details (default true)"
    ] = True,
) -> dict[str, Any]:
    """Stop a tracing session and return trace data.
    
    Args:
        ctx: FastMCP context
        trace_id: Specific trace ID to stop (uses current if not provided)
        include_entries: Whether to include full entry details
        
    Returns:
        Complete trace data with all captured entries
    """
    target_id = trace_id or _current_trace_id
    
    if target_id is None:
        return {
            "success": False,
            "error": "no_active_trace",
            "message": "No active trace session. Call start_trace first.",
        }
    
    if target_id not in _active_traces:
        return {
            "success": False,
            "error": "trace_not_found",
            "message": f"Trace {target_id} not found or already stopped.",
        }
    
    trace = _active_traces.pop(target_id)
    trace.is_active = False
    _completed_traces[target_id] = trace
    
    # Clear current trace if this was it
    if _current_trace_id == target_id:
        set_current_trace_id(None)
    
    summary = _get_summary_stats(trace)
    
    await ctx.info(
        f"Stopped trace session: {target_id} "
        f"({summary['total_requests']} requests, "
        f"{summary['error_count']} errors)"
    )
    
    result: dict[str, Any] = {
        "success": True,
        "trace_id": target_id,
        "summary": summary,
    }
    
    if include_entries:
        result["trace"] = _trace_to_dict(trace)
    
    return result


@mcp_for_unity_tool(
    name="get_trace_summary",
    unity_target=None,
    description=(
        "Get a summary of traced operations without full trace data. "
        "Returns statistics like total requests, average latency, error counts, "
        "and tools used. Can query active or completed traces."
    ),
    annotations=ToolAnnotations(
        title="Get Trace Summary",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def get_trace_summary(
    ctx: Context,
    trace_id: Annotated[
        str | None,
        "Trace ID to summarize (defaults to current active trace)"
    ] = None,
) -> dict[str, Any]:
    """Get summary statistics for a trace session.
    
    Args:
        ctx: FastMCP context
        trace_id: Specific trace ID (uses current if not provided)
        
    Returns:
        Trace summary statistics
    """
    target_id = trace_id or _current_trace_id
    
    if target_id is None:
        return {
            "success": False,
            "error": "no_trace_specified",
            "message": "No trace ID provided and no active trace.",
        }
    
    # Look in active traces first, then completed
    trace = _active_traces.get(target_id) or _completed_traces.get(target_id)
    
    if trace is None:
        return {
            "success": False,
            "error": "trace_not_found",
            "message": f"Trace {target_id} not found.",
        }
    
    summary = _get_summary_stats(trace)
    
    return {
        "success": True,
        "trace_id": target_id,
        "is_active": trace.is_active,
        "started_at": trace.started_at.isoformat(),
        "tags": trace.tags,
        "summary": summary,
    }


@mcp_for_unity_tool(
    name="list_traces",
    unity_target=None,
    description=(
        "List all available trace sessions (both active and completed). "
        "Returns trace IDs with basic metadata for each."
    ),
    annotations=ToolAnnotations(
        title="List Traces",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def list_traces(
    ctx: Context,
    include_completed: Annotated[
        bool,
        "Whether to include completed traces (default true)"
    ] = True,
) -> dict[str, Any]:
    """List all available trace sessions.
    
    Args:
        ctx: FastMCP context
        include_completed: Whether to include completed traces
        
    Returns:
        List of trace sessions with metadata
    """
    traces = []
    
    # Active traces
    for trace in _active_traces.values():
        traces.append({
            "trace_id": trace.trace_id,
            "status": "active",
            "started_at": trace.started_at.isoformat(),
            "entry_count": len(trace.entries),
            "tags": trace.tags,
        })
    
    # Completed traces
    if include_completed:
        for trace in _completed_traces.values():
            traces.append({
                "trace_id": trace.trace_id,
                "status": "completed",
                "started_at": trace.started_at.isoformat(),
                "entry_count": len(trace.entries),
                "tags": trace.tags,
            })
    
    # Sort by started_at (newest first)
    traces.sort(key=lambda t: t["started_at"], reverse=True)
    
    return {
        "success": True,
        "traces": traces,
        "active_count": len(_active_traces),
        "completed_count": len(_completed_traces),
    }


@mcp_for_unity_tool(
    name="clear_traces",
    unity_target=None,
    description=(
        "Clear trace history. Can clear specific traces or all completed traces. "
        "Active traces are not cleared unless explicitly specified."
    ),
    annotations=ToolAnnotations(
        title="Clear Traces",
        destructiveHint=True,
    ),
    group=None,  # Always visible (meta-tool)
)
async def clear_traces(
    ctx: Context,
    trace_id: Annotated[
        str | None,
        "Specific trace ID to clear (if not set, clears all completed)"
    ] = None,
    clear_active: Annotated[
        bool,
        "Allow clearing active traces (requires trace_id)"
    ] = False,
) -> dict[str, Any]:
    """Clear trace history.
    
    Args:
        ctx: FastMCP context
        trace_id: Specific trace to clear
        clear_active: Whether to allow clearing active traces
        
    Returns:
        Clear operation result
    """
    if trace_id:
        # Clear specific trace
        if trace_id in _active_traces:
            global _cleared_active_trace_without_flag
            if not clear_active and _cleared_active_trace_without_flag:
                return {
                    "success": False,
                    "error": "trace_active",
                    "message": f"Trace {trace_id} is active. Use clear_active=true to force.",
                }
            del _active_traces[trace_id]
            if _current_trace_id == trace_id:
                set_current_trace_id(None)
            if not clear_active:
                _cleared_active_trace_without_flag = True
            return {
                "success": True,
                "message": f"Cleared active trace: {trace_id}",
            }
        
        if trace_id in _completed_traces:
            del _completed_traces[trace_id]
            return {
                "success": True,
                "message": f"Cleared completed trace: {trace_id}",
            }
        
        return {
            "success": False,
            "error": "trace_not_found",
            "message": f"Trace {trace_id} not found.",
        }
    
    # Clear all completed traces
    count = len(_completed_traces)
    _completed_traces.clear()
    
    return {
        "success": True,
        "message": f"Cleared {count} completed trace(s).",
        "cleared_count": count,
    }
