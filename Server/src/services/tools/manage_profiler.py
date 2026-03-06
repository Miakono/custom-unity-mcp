"""
Profiler management tool for Unity's Profiler system.
Supports profiling sessions, snapshots, and capture file management.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from models import MCPResponse
from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from services.tools.utils import coerce_bool, coerce_int, parse_json_payload
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry

logger = logging.getLogger(__name__)


class ProfilerStartData(BaseModel):
    """Data returned when starting a profiling session."""
    intervalFrames: int
    deepProfiling: bool
    isRecording: bool


class ProfilerStartResponse(MCPResponse):
    """Response for start profiling action."""
    data: ProfilerStartData | None = None


class ProfilerStatusData(BaseModel):
    """Profiler status information."""
    isRecording: bool
    snapshotCount: int
    profilerEnabled: bool
    deepProfiling: bool
    supportedCategories: list[str]
    enabledCategories: list[str]
    unityVersion: str
    isEditor: bool
    isPlaying: bool
    currentFrame: int


class ProfilerStatusResponse(MCPResponse):
    """Response for get_status action."""
    data: ProfilerStatusData | None = None


class ProfilerSnapshotData(BaseModel):
    """Data from a profiler snapshot."""
    timestamp: int
    frameIndex: int
    frameTimeMs: float
    fps: float
    cpu: dict[str, Any]
    gpu: dict[str, Any]
    memory: dict[str, Any]
    rendering: dict[str, Any]
    audio: dict[str, Any]


class AggregatedStats(BaseModel):
    """Aggregated statistics from multiple snapshots."""
    sampleCount: int
    avgFrameTimeMs: float
    minFrameTimeMs: float
    maxFrameTimeMs: float
    avgFps: float
    minFps: float
    maxFps: float
    avgMemoryBytes: int
    maxMemoryBytes: int
    avgMemoryMB: float
    maxMemoryMB: float
    avgDrawCalls: float
    maxDrawCalls: int


class ProfilerSnapshotResponse(MCPResponse):
    """Response for get_snapshot action."""
    data: dict[str, Any] | None = None


@mcp_for_unity_tool(
    group="profiling",
    description=(
        "Manages Unity Profiler sessions and data collection. "
        "Actions: start/stop (mutating) control profiling sessions; "
        "get_status, get_snapshot (read-only) query current state; "
        "get_memory, get_cpu, get_rendering, get_audio (read-only) get detailed breakdowns; "
        "clear (mutating) removes collected data; "
        "save_capture, load_capture (mutating) manage capture files; "
        "set_categories (mutating) enable/disable profiler categories."
    ),
    annotations=ToolAnnotations(
        title="Manage Profiler",
        destructiveHint=True,  # start/stop/clear/save/load are mutating
    ),
)
async def manage_profiler(
    ctx: Context,
    action: Annotated[
        Literal[
            "start", "stop", "get_status", "get_snapshot",
            "get_memory", "get_cpu", "get_rendering", "get_audio",
            "clear", "save_capture", "load_capture", "set_categories"
        ],
        "Profiler action to perform. start/stop/clear/save_capture/load_capture/set_categories are mutating."
    ],
    # start parameters
    interval_frames: Annotated[
        int | str,
        "Frames between snapshots when starting (default: 10)"
    ] | None = None,
    deep_profiling: Annotated[
        bool | str,
        "Enable deep profiling when starting (default: false)"
    ] | None = None,
    # save_capture parameters
    file_path: Annotated[
        str,
        "File path for save_capture or load_capture"
    ] | None = None,
    # set_categories parameters
    categories: Annotated[
        list[str] | str,
        "List of category names for set_categories"
    ] | None = None,
    enable: Annotated[
        bool | str,
        "Enable/disable categories for set_categories (default: true)"
    ] | None = None,
    wait_for_completion: Annotated[
        bool | str,
        "Wait for action to complete (default: true)"
    ] | None = None,
) -> dict[str, Any]:
    """Manage Unity Profiler sessions and capture performance data."""
    unity_instance = await get_unity_instance_from_context(ctx)

    # Determine if this action requires preflight (mutating actions)
    mutating_actions = {"start", "stop", "clear", "save_capture", "load_capture", "set_categories"}
    is_mutating = action in mutating_actions

    if is_mutating:
        gate = await maybe_run_tool_preflight(ctx, "manage_profiler", action=action)
        if gate is not None:
            return gate.model_dump()

    # Coerce parameters
    coerced_interval_frames = coerce_int(interval_frames, default=10)
    coerced_deep_profiling = coerce_bool(deep_profiling, default=False)
    coerced_enable = coerce_bool(enable, default=True)
    coerced_wait = coerce_bool(wait_for_completion, default=True)

    # Parse categories if provided as JSON string
    parsed_categories: list[str] | None = None
    if isinstance(categories, str):
        parsed_categories = parse_json_payload(categories)
        if not isinstance(parsed_categories, list):
            return {
                "success": False,
                "message": "categories must be a list of strings"
            }
    elif isinstance(categories, list):
        parsed_categories = categories

    # Build parameters
    params: dict[str, Any] = {"action": action}

    if action == "start":
        params["intervalFrames"] = coerced_interval_frames
        params["deepProfiling"] = coerced_deep_profiling

    if action in ("save_capture", "load_capture") and file_path:
        params["filePath"] = file_path

    if action == "set_categories":
        if parsed_categories:
            params["categories"] = parsed_categories
        params["enable"] = coerced_enable

    params["waitForCompletion"] = coerced_wait

    try:
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_profiler",
            params,
        )

        if not isinstance(response, dict):
            return MCPResponse(success=False, error=str(response)).model_dump()

        if not response.get("success", True):
            return MCPResponse(**response).model_dump()

        # Return successful response with data
        return response

    except Exception as e:
        logger.error(f"Profiler action '{action}' failed: {e}")
        return MCPResponse(
            success=False,
            error=f"Profiler operation failed: {str(e)}"
        ).model_dump()


@mcp_for_unity_tool(
    group="profiling",
    description=(
        "Continuously records profiler data for a specified duration. "
        "This is a long-running job that collects snapshots at regular intervals "
        "and returns aggregated statistics. Use for performance testing and regression detection."
    ),
    annotations=ToolAnnotations(
        title="Record Profiler Session",
        destructiveHint=True,
    ),
)
async def record_profiler_session(
    ctx: Context,
    duration_seconds: Annotated[
        int | str,
        "Duration to record in seconds (default: 30, max: 300)"
    ] = 30,
    interval_frames: Annotated[
        int | str,
        "Frames between snapshots (default: 10)"
    ] = 10,
    include_memory: Annotated[
        bool | str,
        "Include detailed memory data (default: true)"
    ] = True,
    include_rendering: Annotated[
        bool | str,
        "Include rendering statistics (default: true)"
    ] = True,
    auto_save: Annotated[
        bool | str,
        "Automatically save capture file when done (default: false)"
    ] = False,
    save_path: Annotated[
        str | None,
        "Optional path for auto-save (uses default if not specified)"
    ] = None,
) -> dict[str, Any]:
    """Record a profiler session for a specified duration.

    This tool starts profiling, waits for the specified duration while collecting
    snapshots, then stops and returns aggregated statistics. It's designed for
    performance testing scenarios.
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    # Coerce parameters
    duration = min(coerce_int(duration_seconds, default=30), 300)  # Max 5 minutes
    interval = coerce_int(interval_frames, default=10)
    include_mem = coerce_bool(include_memory, default=True)
    include_rend = coerce_bool(include_rendering, default=True)
    should_auto_save = coerce_bool(auto_save, default=False)

    gate = await maybe_run_tool_preflight(ctx, "record_profiler_session")
    if gate is not None:
        return gate.model_dump()

    try:
        # Start profiling
        start_response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_profiler",
            {
                "action": "start",
                "intervalFrames": interval,
                "deepProfiling": False,
                "waitForCompletion": True,
            },
        )

        if not isinstance(start_response, dict) or not start_response.get("success"):
            error_msg = (
                start_response.get("message", "Unknown error")
                if isinstance(start_response, dict)
                else str(start_response)
            )
            return MCPResponse(
                success=False,
                error=f"Failed to start profiling: {error_msg}"
            ).model_dump()

        logger.info(f"Started profiler recording for {duration} seconds")

        # Wait for the recording duration
        await asyncio.sleep(duration)

        # Get a snapshot before stopping
        snapshot_response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_profiler",
            {"action": "get_snapshot"},
        )

        # Stop profiling
        stop_response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_profiler",
            {"action": "stop", "waitForCompletion": True},
        )

        # Extract data
        snapshot_data = (
            snapshot_response.get("data", {})
            if isinstance(snapshot_response, dict)
            else {}
        )
        aggregated_stats = snapshot_data.get("aggregatedStats", {})

        result = {
            "success": True,
            "message": f"Profiler session recorded for {duration} seconds",
            "data": {
                "durationSeconds": duration,
                "intervalFrames": interval,
                "snapshotCount": snapshot_data.get("totalSnapshots", 0),
                "isRecording": False,
                "performance": {
                    "avgFrameTimeMs": aggregated_stats.get("avgFrameTimeMs", 0),
                    "minFrameTimeMs": aggregated_stats.get("minFrameTimeMs", 0),
                    "maxFrameTimeMs": aggregated_stats.get("maxFrameTimeMs", 0),
                    "avgFps": aggregated_stats.get("avgFps", 0),
                    "minFps": aggregated_stats.get("minFps", 0),
                    "maxFps": aggregated_stats.get("maxFps", 0),
                },
                "memory": {
                    "avgMemoryMB": aggregated_stats.get("avgMemoryMB", 0),
                    "maxMemoryMB": aggregated_stats.get("maxMemoryMB", 0),
                } if include_mem else None,
                "rendering": {
                    "avgDrawCalls": aggregated_stats.get("avgDrawCalls", 0),
                    "maxDrawCalls": aggregated_stats.get("maxDrawCalls", 0),
                } if include_rend else None,
            }
        }

        # Auto-save if requested
        if should_auto_save:
            save_params: dict[str, Any] = {"action": "save_capture"}
            if save_path:
                save_params["filePath"] = save_path

            save_response = await send_with_unity_instance(
                async_send_command_with_retry,
                unity_instance,
                "manage_profiler",
                save_params,
            )

            if isinstance(save_response, dict) and save_response.get("success"):
                save_data = save_response.get("data", {})
                result["data"]["captureFile"] = {
                    "path": save_data.get("filePath"),
                    "size": save_data.get("fileSize"),
                }

        return result

    except asyncio.CancelledError:
        # Ensure profiling is stopped if task is cancelled
        try:
            await send_with_unity_instance(
                async_send_command_with_retry,
                unity_instance,
                "manage_profiler",
                {"action": "stop"},
            )
        except Exception:
            pass
        raise

    except Exception as e:
        logger.error(f"Record profiler session failed: {e}")
        # Try to stop profiling on error
        try:
            await send_with_unity_instance(
                async_send_command_with_retry,
                unity_instance,
                "manage_profiler",
                {"action": "stop"},
            )
        except Exception:
            pass

        return MCPResponse(
            success=False,
            error=f"Failed to record profiler session: {str(e)}"
        ).model_dump()
