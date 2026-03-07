"""
Wait tool for blocking until specific Unity editor conditions are met.

Supports configurable timeouts and cancellation for long-running workflows.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from models import MCPResponse
from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
import transport.unity_transport as unity_transport
from transport.legacy.unity_connection import async_send_command_with_retry

logger = logging.getLogger(__name__)

# Default timeout in seconds
DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 300  # 5 minutes max


class WaitConditionResult(BaseModel):
    condition_met: bool
    condition_type: str
    wait_duration_ms: int
    timed_out: bool
    details: dict[str, Any] | None = None


class WaitConditionResponse(MCPResponse):
    data: WaitConditionResult | None = None


@mcp_for_unity_tool(
    group="events",
    unity_target=None,
    description=(
        "Waits for a specific Unity editor condition to be met. "
        "Useful for long workflows that need to wait for compilation, scene loading, or play mode changes. "
        "Supports configurable timeout with default 30s. Can be cancelled."
    ),
    annotations=ToolAnnotations(
        title="Wait for Editor Condition",
        readOnlyHint=True,
    ),
)
async def wait_for_editor_condition(
    ctx: Context,
    condition: Annotated[
        Literal[
            "compile_idle",
            "asset_import_complete",
            "scene_load_complete",
            "play_mode_state",
            "prefab_stage_state",
            "object_exists",
        ],
        "The condition to wait for. "
        "compile_idle: Wait for compilation to complete. "
        "asset_import_complete: Wait for asset import queue to empty. "
        "scene_load_complete: Wait for scene to finish loading. "
        "play_mode_state: Wait for play mode (playing/paused/stopped). "
        "prefab_stage_state: Wait for prefab stage to open/close. "
        "object_exists: Wait for GameObject/asset to exist."
    ],
    timeout_seconds: Annotated[
        int | float | str | None,
        "Maximum time to wait in seconds (default: 30, max: 300). "
        "Accepts int, float, or string that can be parsed as number."
    ] = None,
    poll_interval_seconds: Annotated[
        float | str | None,
        "How often to check the condition in seconds (default: 0.5, min: 0.1, max: 5.0). "
        "Accepts float or string that can be parsed as float."
    ] = None,
    # play_mode_state specific parameters
    play_mode_target: Annotated[
        Literal["playing", "paused", "stopped"] | None,
        "Target play mode state (required when condition=play_mode_state)"
    ] = None,
    # prefab_stage_state specific parameters  
    prefab_stage_target: Annotated[
        Literal["open", "closed"] | None,
        "Target prefab stage state (required when condition=prefab_stage_state)"
    ] = None,
    prefab_path: Annotated[
        str | None,
        "Prefab asset path (optional when condition=prefab_stage_state)"
    ] = None,
    # object_exists specific parameters
    object_name: Annotated[
        str | None,
        "GameObject name to search for (required when condition=object_exists)"
    ] = None,
    object_guid: Annotated[
        str | None,
        "Asset GUID to search for (alternative to object_name for assets)"
    ] = None,
    # scene_load_complete specific parameters
    scene_path: Annotated[
        str | None,
        "Expected scene path (optional when condition=scene_load_complete)"
    ] = None,
    scene_name: Annotated[
        str | None,
        "Expected scene name (optional when condition=scene_load_complete)"
    ] = None,
) -> WaitConditionResponse | MCPResponse:
    """
    Wait for a specific Unity editor condition to be met.
    
    This tool polls the Unity editor state until the specified condition
    is satisfied or the timeout is reached.
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    gate = await maybe_run_tool_preflight(ctx, "wait_for_editor_condition")
    if isinstance(gate, MCPResponse):
        return gate

    # Parse and validate timeout
    timeout = _parse_float(timeout_seconds, DEFAULT_TIMEOUT_SECONDS)
    timeout = max(1.0, min(float(timeout), MAX_TIMEOUT_SECONDS))

    # Parse and validate poll interval
    poll_interval = _parse_float(poll_interval_seconds, 0.5)
    poll_interval = max(0.1, min(float(poll_interval), 5.0))

    # Validate condition-specific parameters
    validation_error = _validate_condition_params(condition, play_mode_target, 
                                                   prefab_stage_target, object_name, 
                                                   object_guid)
    if validation_error:
        return MCPResponse(success=False, error="invalid_parameters", message=validation_error)

    start_time = time.time()
    deadline = start_time + timeout
    
    logger.info(
        f"Starting wait for condition '{condition}' with timeout {timeout}s "
        f"and poll interval {poll_interval}s"
    )

    try:
        while True:
            # Check if we've exceeded the timeout
            now = time.time()
            if now >= deadline:
                duration_ms = int((now - start_time) * 1000)
                logger.warning(
                    f"Timeout waiting for condition '{condition}' after {duration_ms}ms"
                )
                result = WaitConditionResult(
                    condition_met=False,
                    condition_type=condition,
                    wait_duration_ms=duration_ms,
                    timed_out=True,
                    details={"timeout_seconds": timeout}
                )
                return WaitConditionResponse(
                    success=False,
                    error="timeout",
                    message=f"Condition '{condition}' not met within {timeout} seconds",
                    data=result
                )

            # Check the current condition state
            is_met, details = await _check_condition(
                ctx,
                unity_instance,
                condition,
                play_mode_target=play_mode_target,
                prefab_stage_target=prefab_stage_target,
                prefab_path=prefab_path,
                object_name=object_name,
                object_guid=object_guid,
                scene_path=scene_path,
                scene_name=scene_name,
            )

            if is_met:
                duration_ms = int((now - start_time) * 1000)
                logger.info(
                    f"Condition '{condition}' met after {duration_ms}ms"
                )
                result = WaitConditionResult(
                    condition_met=True,
                    condition_type=condition,
                    wait_duration_ms=duration_ms,
                    timed_out=False,
                    details=details
                )
                return WaitConditionResponse(
                    success=True,
                    message=f"Condition '{condition}' met",
                    data=result
                )

            # Wait before next poll
            # Use asyncio.wait_for to allow cancellation
            remaining = deadline - time.time()
            sleep_duration = min(poll_interval, max(0.1, remaining))
            await asyncio.sleep(sleep_duration)

    except asyncio.CancelledError:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"Wait for condition '{condition}' cancelled after {duration_ms}ms"
        )
        result = WaitConditionResult(
            condition_met=False,
            condition_type=condition,
            wait_duration_ms=duration_ms,
            timed_out=False,
            details={"cancelled": True}
        )
        raise  # Re-raise to propagate cancellation

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(
            f"Error waiting for condition '{condition}': {e}", exc_info=True
        )
        return MCPResponse(
            success=False,
            error="wait_error",
            message=f"Error waiting for condition: {str(e)}"
        )


def _parse_float(value: int | float | str | None, default: float) -> float:
    """Parse a value that could be int, float, or string to float."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return default


def _validate_condition_params(
    condition: str,
    play_mode_target: str | None,
    prefab_stage_target: str | None,
    object_name: str | None,
    object_guid: str | None,
) -> str | None:
    """Validate condition-specific required parameters."""
    if condition == "play_mode_state" and play_mode_target is None:
        return "play_mode_target is required when condition='play_mode_state'"
    if condition == "prefab_stage_state" and prefab_stage_target is None:
        return "prefab_stage_target is required when condition='prefab_stage_state'"
    if condition == "object_exists":
        if object_name is None and object_guid is None:
            return "Either object_name or object_guid is required when condition='object_exists'"
    return None


async def _check_condition(
    ctx: Context,
    unity_instance: str | None,
    condition: str,
    play_mode_target: str | None = None,
    prefab_stage_target: str | None = None,
    prefab_path: str | None = None,
    object_name: str | None = None,
    object_guid: str | None = None,
    scene_path: str | None = None,
    scene_name: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """
    Check if the specified condition is met.
    
    Returns:
        Tuple of (is_met, details_dict)
    """
    if condition == "compile_idle":
        return await _check_compile_idle(unity_instance)
    elif condition == "asset_import_complete":
        return await _check_asset_import_complete(unity_instance)
    elif condition == "scene_load_complete":
        return await _check_scene_load_complete(
            unity_instance, scene_path, scene_name
        )
    elif condition == "play_mode_state":
        return await _check_play_mode_state(unity_instance, play_mode_target)
    elif condition == "prefab_stage_state":
        return await _check_prefab_stage_state(
            unity_instance, prefab_stage_target, prefab_path
        )
    elif condition == "object_exists":
        return await _check_object_exists(
            unity_instance, object_name, object_guid
        )
    else:
        return False, {"error": f"Unknown condition: {condition}"}


async def _check_compile_idle(unity_instance: str | None) -> tuple[bool, dict[str, Any]]:
    """Check if Unity is not compiling and no domain reload is pending."""
    response = await unity_transport.send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "get_editor_state",
        {},
    )
    
    if not isinstance(response, dict) or not response.get("success"):
        return False, {"error": "Failed to get editor state"}
    
    data = response.get("data", {})
    compilation = data.get("compilation", {})
    
    is_compiling = compilation.get("is_compiling", False)
    is_domain_reload_pending = compilation.get("is_domain_reload_pending", False)
    
    is_idle = not is_compiling and not is_domain_reload_pending
    
    return is_idle, {
        "is_compiling": is_compiling,
        "is_domain_reload_pending": is_domain_reload_pending,
    }


async def _check_asset_import_complete(
    unity_instance: str | None
) -> tuple[bool, dict[str, Any]]:
    """Check if asset import queue is empty."""
    response = await unity_transport.send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "get_editor_state",
        {},
    )
    
    if not isinstance(response, dict) or not response.get("success"):
        return False, {"error": "Failed to get editor state"}
    
    data = response.get("data", {})
    assets = data.get("assets", {})
    refresh = assets.get("refresh", {})
    
    is_refresh_in_progress = refresh.get("is_refresh_in_progress", False)
    is_updating = assets.get("is_updating", False)
    
    is_complete = not is_refresh_in_progress and not is_updating
    
    return is_complete, {
        "is_refresh_in_progress": is_refresh_in_progress,
        "is_updating": is_updating,
    }


async def _check_scene_load_complete(
    unity_instance: str | None,
    scene_path: str | None,
    scene_name: str | None,
) -> tuple[bool, dict[str, Any]]:
    """Check if scene has finished loading."""
    response = await unity_transport.send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "get_editor_state",
        {},
    )
    
    if not isinstance(response, dict) or not response.get("success"):
        return False, {"error": "Failed to get editor state"}
    
    data = response.get("data", {})
    editor = data.get("editor", {})
    activity = data.get("activity", {})
    active_scene = editor.get("active_scene", {})
    
    # Check if we're still in a loading phase
    current_phase = activity.get("phase", "")
    is_loading = current_phase in ("scene_loading", "scene_opening")
    
    # If specific scene path/name provided, verify it matches
    current_scene_path = active_scene.get("path", "")
    current_scene_name = active_scene.get("name", "")
    
    scene_matches = True
    if scene_path and scene_path != current_scene_path:
        scene_matches = False
    if scene_name and scene_name != current_scene_name:
        scene_matches = False
    
    is_complete = not is_loading and scene_matches
    
    return is_complete, {
        "current_phase": current_phase,
        "active_scene_path": current_scene_path,
        "active_scene_name": current_scene_name,
        "scene_matches": scene_matches,
    }


async def _check_play_mode_state(
    unity_instance: str | None,
    target_state: str | None,
) -> tuple[bool, dict[str, Any]]:
    """Check if play mode matches the target state."""
    response = await unity_transport.send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "get_editor_state",
        {},
    )
    
    if not isinstance(response, dict) or not response.get("success"):
        return False, {"error": "Failed to get editor state"}
    
    data = response.get("data", {})
    editor = data.get("editor", {})
    play_mode = editor.get("play_mode", {})
    
    is_playing = play_mode.get("is_playing", False)
    is_paused = play_mode.get("is_paused", False)
    is_changing = play_mode.get("is_changing", False)
    
    # Determine current state
    if is_changing:
        current_state = "changing"
    elif is_playing and is_paused:
        current_state = "paused"
    elif is_playing:
        current_state = "playing"
    else:
        current_state = "stopped"
    
    is_match = current_state == target_state
    
    return is_match, {
        "current_state": current_state,
        "target_state": target_state,
        "is_playing": is_playing,
        "is_paused": is_paused,
        "is_changing": is_changing,
    }


async def _check_prefab_stage_state(
    unity_instance: str | None,
    target_state: str | None,
    prefab_path: str | None,
) -> tuple[bool, dict[str, Any]]:
    """Check if prefab stage matches the target state."""
    params: dict[str, Any] = {}
    if prefab_path:
        params["prefab_path"] = prefab_path
    
    response = await unity_transport.send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "get_prefab_stage_state",
        params,
    )
    
    if not isinstance(response, dict):
        return False, {"error": "Failed to get prefab stage state"}
    
    # If command not supported, try alternative via editor state
    if not response.get("success"):
        error_msg = str(response.get("error", "")).lower()
        if "unknown" in error_msg or "unsupported" in error_msg:
            # Fallback: use prefab_stage resource
            return await _check_prefab_stage_via_resource(
                unity_instance, target_state, prefab_path
            )
    
    data = response.get("data", {})
    is_open = data.get("is_open", False)
    current_prefab_path = data.get("prefab_path", "")
    
    # Determine current state
    current_state = "open" if is_open else "closed"
    
    # If prefab path specified, check it matches
    path_matches = True
    if prefab_path and current_prefab_path != prefab_path:
        path_matches = False
    
    is_match = current_state == target_state and path_matches
    
    return is_match, {
        "current_state": current_state,
        "target_state": target_state,
        "prefab_path": current_prefab_path,
        "path_matches": path_matches,
    }


async def _check_prefab_stage_via_resource(
    unity_instance: str | None,
    target_state: str | None,
    prefab_path: str | None,
) -> tuple[bool, dict[str, Any]]:
    """Fallback: Check prefab stage using prefab_stage resource."""
    from services.resources.prefab_stage import get_prefab_stage
    from fastmcp import Context
    
    # Create a minimal context for the resource call
    # Note: This is a workaround since we don't have the original context
    ctx = Context()
    
    try:
        result = await get_prefab_stage(ctx)
        if hasattr(result, "model_dump"):
            data = result.model_dump().get("data", {})
        else:
            data = result.get("data", {}) if isinstance(result, dict) else {}
        
        is_in_prefab_stage = data.get("is_in_prefab_stage", False)
        current_path = data.get("asset_path", "")
        
        current_state = "open" if is_in_prefab_stage else "closed"
        path_matches = not prefab_path or current_path == prefab_path
        
        is_match = current_state == target_state and path_matches
        
        return is_match, {
            "current_state": current_state,
            "target_state": target_state,
            "prefab_path": current_path,
            "path_matches": path_matches,
            "source": "resource_fallback",
        }
    except Exception as e:
        return False, {"error": f"Fallback check failed: {e}"}


async def _check_object_exists(
    unity_instance: str | None,
    object_name: str | None,
    object_guid: str | None,
) -> tuple[bool, dict[str, Any]]:
    """Check if a GameObject or asset exists."""
    params: dict[str, Any] = {}
    if object_name:
        params["object_name"] = object_name
    if object_guid:
        params["object_guid"] = object_guid
    
    response = await unity_transport.send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "check_object_exists",
        params,
    )
    
    if not isinstance(response, dict):
        return False, {"error": "Failed to check object existence"}
    
    # If command not supported, fallback to find_gameobjects
    if not response.get("success"):
        error_msg = str(response.get("error", "")).lower()
        if "unknown" in error_msg or "unsupported" in error_msg:
            return await _check_object_exists_via_find(
                unity_instance, object_name, object_guid
            )
    
    data = response.get("data", {})
    exists = data.get("exists", False)
    
    return exists, {
        "exists": exists,
        "object_name": object_name,
        "object_guid": object_guid,
    }


async def _check_object_exists_via_find(
    unity_instance: str | None,
    object_name: str | None,
    object_guid: str | None,
) -> tuple[bool, dict[str, Any]]:
    """Fallback: Check object existence using find_gameobjects tool."""
    from services.tools.find_gameobjects import find_gameobjects
    from fastmcp import Context
    
    try:
        if object_name:
            # Search by name
            ctx = Context()
            result = await find_gameobjects(ctx, name=object_name, max_results=1)
            
            if hasattr(result, "model_dump"):
                data = result.model_dump().get("data", {})
            else:
                data = result.get("data", {}) if isinstance(result, dict) else {}
            
            objects = data.get("objects", [])
            exists = len(objects) > 0
            
            return exists, {
                "exists": exists,
                "object_name": object_name,
                "match_count": len(objects),
                "source": "find_gameobjects_fallback",
            }
        elif object_guid:
            # For GUID-based lookup, we'd need a different approach
            # This is a simplified fallback
            return False, {
                "error": "GUID-based lookup not supported in fallback mode",
                "object_guid": object_guid,
            }
        
        return False, {"error": "No search criteria provided"}
    except Exception as e:
        return False, {"error": f"Fallback check failed: {e}"}
