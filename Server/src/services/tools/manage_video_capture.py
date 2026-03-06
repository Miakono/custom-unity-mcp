"""
Video capture tool for recording gameplay and capturing GIF animations.

Works in both Editor and Play mode using Unity's frame capture system.
Supports MP4 video recording and GIF animation capture.
"""
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight, tool_action_is_mutating
from services.tools.refresh_unity import send_mutation
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    group="core",
    description=(
        "Record video and capture GIF animations from Unity gameplay. "
        "Works in both Editor and Play mode. "
        "Actions: start (begin recording), stop (end and save), get_status (recording info), "
        "capture_gif (short animated GIF), set_settings (configure fps/quality/resolution). "
        "\n\nWorkflow:\n"
        "1. Use set_settings to configure capture quality and format\n"
        "2. Use start to begin recording (MP4 or frame sequence)\n"
        "3. Use get_status to monitor recording progress\n"
        "4. Use stop to end recording and save the file\n"
        "5. Use capture_gif for short animated clips (auto-stops when duration reached)"
    ),
    annotations=ToolAnnotations(
        title="Manage Video Capture",
        destructiveHint=False,
    ),
)
async def manage_video_capture(
    ctx: Context,
    action: Annotated[Literal[
        "start",
        "stop",
        "get_status",
        "capture_gif",
        "set_settings",
    ], "Action to perform."],
    # start/stop params
    output_path: Annotated[str | None,
                           "Output file path (relative to Assets folder, e.g., 'Recordings/gameplay.mp4'). "
                           "For start and capture_gif." ] = None,
    duration_seconds: Annotated[float | None,
                                 "Maximum recording duration in seconds. For capture_gif (default: 5.0)."] = None,
    # set_settings params
    fps: Annotated[int | None,
                   "Target frames per second for recording (default: 30)."] = None,
    quality: Annotated[Literal["low", "medium", "high", "ultra"] | None,
                       "Recording quality preset (default: high)."] = None,
    resolution: Annotated[dict[str, int] | None,
                          "Target resolution as {width, height}. Null uses screen size."] = None,
    format: Annotated[Literal["mp4", "gif", "frames"] | None,
                      "Output format: mp4 (video), gif (animation), or frames (PNG sequence). "
                      "For set_settings."] = None,
    include_audio: Annotated[bool | None,
                             "Include audio in recording (default: false)."] = None,
    # capture_gif params
    loop_count: Annotated[int | None,
                          "Number of times GIF loops (0 = infinite, default: 0)."] = None,
    frame_skip: Annotated[int | None,
                          "Capture every Nth frame for smaller GIFs (default: 1 = all frames)."] = None,
) -> dict[str, Any]:
    """
    Manage video recording and GIF capture in Unity.
    """
    action_lower = action.lower()
    uses_mutation_transport = tool_action_is_mutating("manage_video_capture", action=action_lower)

    gate = await maybe_run_tool_preflight(ctx, "manage_video_capture", action=action_lower)
    if gate is not None:
        return gate.model_dump()

    unity_instance = await get_unity_instance_from_context(ctx)

    # Build params dict
    params_dict: dict[str, Any] = {"action": action_lower}

    if output_path is not None:
        params_dict["outputPath"] = output_path
    if duration_seconds is not None:
        params_dict["durationSeconds"] = duration_seconds
    if fps is not None:
        params_dict["fps"] = fps
    if quality is not None:
        params_dict["quality"] = quality
    if resolution is not None:
        params_dict["resolution"] = resolution
    if format is not None:
        params_dict["format"] = format
    if include_audio is not None:
        params_dict["includeAudio"] = include_audio
    if loop_count is not None:
        params_dict["loopCount"] = loop_count
    if frame_skip is not None:
        params_dict["frameSkip"] = frame_skip

    # Route to Unity
    if uses_mutation_transport:
        result = await send_mutation(
            ctx, unity_instance, "manage_video_capture", params_dict,
        )
    else:
        result = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_video_capture",
            params_dict,
        )

    return result if isinstance(result, dict) else {"success": False, "message": str(result)}
