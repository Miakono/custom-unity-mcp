"""Unity mock/simulator for server development and testing.

This module provides a Unity simulator that can respond to MCP tool calls
without requiring a live Unity Editor connection. Supports various failure
scenarios for robust error handling testing.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Any, Callable

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from services.registry import mcp_for_unity_tool, mcp_for_unity_resource
from models import MCPResponse


class MockUnityState(BaseModel):
    """State representation of a mock Unity instance."""
    instance_id: str = "mock-unity-001"
    unity_version: str = "2022.3.20f1"
    project_name: str = "MockProject"
    project_path: str = "/Mock/Project/Path"
    platform: str = "StandaloneWindows64"
    
    # Play mode state
    is_playing: bool = False
    is_paused: bool = False
    is_compiling: bool = False
    is_domain_reload_pending: bool = False
    is_refresh_in_progress: bool = False
    
    # Scene state
    active_scene: str = "Assets/Scenes/SampleScene.unity"
    scene_objects: list[dict[str, Any]] = field(default_factory=list)
    
    # Asset state
    assets: dict[str, dict[str, Any]] = field(default_factory=dict)
    
    # Console
    console_logs: list[dict[str, Any]] = field(default_factory=list)


class MockFailureConfig(BaseModel):
    """Configuration for failure injection."""
    enabled: bool = False
    failure_mode: str | None = None  # compile_in_progress, domain_reload, dropped_transport, stale_state, locked_asset
    failure_rate: float = 0.0  # 0.0 to 1.0
    latency_ms: int = 50
    latency_variance_ms: int = 20


# Global mock state
_mock_state = MockUnityState()
_failure_config = MockFailureConfig()
_mock_active: bool = False


# Simulated assets for realistic responses
_DEFAULT_ASSETS: dict[str, dict[str, Any]] = {
    "Assets/Scripts/Player.cs": {
        "type": "Script",
        "guid": "abc123",
        "size": 2048,
        "last_modified": "2024-01-15T10:30:00Z",
    },
    "Assets/Prefabs/Player.prefab": {
        "type": "Prefab",
        "guid": "def456",
        "size": 4096,
        "last_modified": "2024-01-15T11:00:00Z",
    },
    "Assets/Scenes/SampleScene.unity": {
        "type": "Scene",
        "guid": "ghi789",
        "size": 10240,
        "last_modified": "2024-01-15T12:00:00Z",
    },
}

_DEFAULT_SCENE_OBJECTS: list[dict[str, Any]] = [
    {
        "instanceId": 1000,
        "name": "Main Camera",
        "active": True,
        "tag": "MainCamera",
        "layer": 0,
        "components": ["Transform", "Camera", "AudioListener"],
    },
    {
        "instanceId": 1001,
        "name": "Directional Light",
        "active": True,
        "tag": "Untagged",
        "layer": 0,
        "components": ["Transform", "Light"],
    },
    {
        "instanceId": 1002,
        "name": "Player",
        "active": True,
        "tag": "Player",
        "layer": 8,
        "components": ["Transform", "CharacterController", "PlayerScript"],
    },
]


def _should_inject_failure() -> tuple[bool, str | None]:
    """Check if a failure should be injected.
    
    Returns:
        Tuple of (should_fail, failure_reason)
    """
    if not _failure_config.enabled:
        return False, None
    
    if _failure_config.failure_rate > 0 and random.random() < _failure_config.failure_rate:
        return True, _failure_config.failure_mode or "random_failure"
    
    # Check specific failure modes based on state
    if _failure_config.failure_mode == "compile_in_progress" and _mock_state.is_compiling:
        return True, "Compilation in progress"
    
    if _failure_config.failure_mode == "domain_reload" and _mock_state.is_domain_reload_pending:
        return True, "Domain reload pending"
    
    if _failure_config.failure_mode == "stale_state" and _mock_state.is_refresh_in_progress:
        return True, "Editor state is stale"
    
    return False, None


def _simulate_latency() -> None:
    """Simulate network latency."""
    base = _failure_config.latency_ms / 1000.0
    variance = _failure_config.latency_variance_ms / 1000.0
    delay = base + random.uniform(-variance, variance)
    if delay > 0:
        time.sleep(delay)


def _handle_tool_command(command: str, params: dict[str, Any]) -> dict[str, Any]:
    """Handle a simulated Unity tool command.
    
    Args:
        command: Tool command name
        params: Command parameters
        
    Returns:
        Simulated response
    """
    global _mock_state
    
    # Check for failure injection
    should_fail, failure_reason = _should_inject_failure()
    if should_fail:
        return {
            "success": False,
            "error": _failure_config.failure_mode or "mock_failure",
            "message": failure_reason or "Injected failure for testing",
            "hint": "retry" if _failure_config.failure_mode in ["compile_in_progress", "domain_reload"] else None,
        }
    
    # Handle specific commands
    handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
        "ping": lambda p: {"success": True, "message": "Mock Unity is responding", "data": {"mock": True}},
        "get_editor_state": _handle_get_editor_state,
        "get_scene_hierarchy": lambda p: {"success": True, "data": {"objects": _mock_state.scene_objects}},
        "get_gameobject": _handle_get_gameobject,
        "create_gameobject": _handle_create_gameobject,
        "delete_gameobject": _handle_delete_gameobject,
        "select_objects": lambda p: {"success": True, "data": {"selection": [1000]}},
        "get_selected_objects": lambda p: {"success": True, "data": {"objects": [_mock_state.scene_objects[0]]}},
        "execute_menu_item": _handle_execute_menu_item,
        "refresh_asset_database": _handle_refresh,
        "save_scene": lambda p: {"success": True, "message": "Scene saved", "data": {"path": _mock_state.active_scene}},
        "compile_scripts": _handle_compile,
        "enter_play_mode": lambda p: _set_play_mode(True),
        "exit_play_mode": lambda p: _set_play_mode(False),
    }
    
    handler = handlers.get(command)
    if handler:
        return handler(params)
    
    # Generic fallback
    return {
        "success": True,
        "message": f"Mock handler for {command}",
        "data": {"mock": True, "command": command, "params": params},
    }


def _handle_get_editor_state(params: dict[str, Any]) -> dict[str, Any]:
    """Handle get_editor_state command."""
    return {
        "success": True,
        "data": {
            "schema_version": "unity-mcp/editor_state@2",
            "observed_at_unix_ms": int(time.time() * 1000),
            "sequence": 1,
            "unity": {
                "instance_id": _mock_state.instance_id,
                "unity_version": _mock_state.unity_version,
                "project_id": str(uuid.uuid4()),
                "platform": _mock_state.platform,
                "is_batch_mode": False,
            },
            "editor": {
                "is_focused": True,
                "play_mode": {
                    "is_playing": _mock_state.is_playing,
                    "is_paused": _mock_state.is_paused,
                    "is_changing": False,
                },
                "active_scene": {
                    "path": _mock_state.active_scene,
                    "guid": "scene-guid-001",
                    "name": _mock_state.active_scene.split("/")[-1].replace(".unity", ""),
                },
            },
            "compilation": {
                "is_compiling": _mock_state.is_compiling,
                "is_domain_reload_pending": _mock_state.is_domain_reload_pending,
            },
            "assets": {
                "is_updating": _mock_state.is_refresh_in_progress,
                "refresh": {
                    "is_refresh_in_progress": _mock_state.is_refresh_in_progress,
                },
            },
            "transport": {
                "unity_bridge_connected": True,
                "last_message_unix_ms": int(time.time() * 1000),
            },
        },
    }


def _handle_get_gameobject(params: dict[str, Any]) -> dict[str, Any]:
    """Handle get_gameobject command."""
    instance_id = params.get("instanceId") or params.get("instance_id")
    
    for obj in _mock_state.scene_objects:
        if obj.get("instanceId") == instance_id:
            return {"success": True, "data": obj}
    
    return {"success": False, "error": "gameobject_not_found", "message": f"GameObject {instance_id} not found"}


def _handle_create_gameobject(params: dict[str, Any]) -> dict[str, Any]:
    """Handle create_gameobject command."""
    name = params.get("name", "New GameObject")
    new_id = max([obj.get("instanceId", 0) for obj in _mock_state.scene_objects], default=1000) + 1
    
    new_obj = {
        "instanceId": new_id,
        "name": name,
        "active": True,
        "tag": "Untagged",
        "layer": 0,
        "components": ["Transform"],
    }
    
    _mock_state.scene_objects.append(new_obj)
    
    return {"success": True, "message": f"Created GameObject: {name}", "data": new_obj}


def _handle_delete_gameobject(params: dict[str, Any]) -> dict[str, Any]:
    """Handle delete_gameobject command."""
    instance_id = params.get("instanceId") or params.get("instance_id")
    
    for i, obj in enumerate(_mock_state.scene_objects):
        if obj.get("instanceId") == instance_id:
            del _mock_state.scene_objects[i]
            return {"success": True, "message": f"Deleted GameObject: {instance_id}"}
    
    return {"success": False, "error": "gameobject_not_found", "message": f"GameObject {instance_id} not found"}


def _handle_execute_menu_item(params: dict[str, Any]) -> dict[str, Any]:
    """Handle execute_menu_item command."""
    menu_path = params.get("menuPath", "")
    
    # Simulate some menu items
    if "Play" in menu_path and not _mock_state.is_playing:
        _mock_state.is_playing = True
        return {"success": True, "message": "Entered play mode"}
    
    if "Save" in menu_path:
        return {"success": True, "message": "Saved assets"}
    
    return {"success": True, "message": f"Executed menu: {menu_path}"}


def _handle_refresh(params: dict[str, Any]) -> dict[str, Any]:
    """Handle refresh command."""
    _mock_state.is_refresh_in_progress = True
    # Simulate async completion
    _mock_state.is_refresh_in_progress = False
    return {"success": True, "message": "Asset database refreshed"}


def _handle_compile(params: dict[str, Any]) -> dict[str, Any]:
    """Handle compile command."""
    _mock_state.is_compiling = True
    # Simulate compilation
    time.sleep(0.5)
    _mock_state.is_compiling = False
    return {"success": True, "message": "Scripts compiled successfully"}


def _set_play_mode(playing: bool) -> dict[str, Any]:
    """Set play mode state."""
    _mock_state.is_playing = playing
    return {
        "success": True,
        "message": f"{'Entered' if playing else 'Exited'} play mode",
        "data": {"is_playing": playing},
    }


@mcp_for_unity_tool(
    name="enable_mock_unity",
    description=(
        "Enable the Unity mock/simulator for server development. "
        "Allows testing MCP tools without a live Unity Editor. "
        "Supports various failure injection scenarios."
    ),
    annotations=ToolAnnotations(
        title="Enable Mock Unity",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def enable_mock_unity(
    ctx: Context,
    unity_version: Annotated[
        str,
        "Simulated Unity version"
    ] = "2022.3.20f1",
    project_name: Annotated[
        str,
        "Simulated project name"
    ] = "MockProject",
    failure_mode: Annotated[
        str | None,
        "Failure mode to inject: compile_in_progress, domain_reload, dropped_transport, stale_state, locked_asset"
    ] = None,
    failure_rate: Annotated[
        float,
        "Rate of failure injection (0.0 to 1.0)"
    ] = 0.0,
    latency_ms: Annotated[
        int,
        "Simulated latency in milliseconds"
    ] = 50,
) -> dict[str, Any]:
    """Enable the Unity mock simulator.
    
    Args:
        ctx: FastMCP context
        unity_version: Simulated Unity version
        project_name: Simulated project name
        failure_mode: Failure injection mode
        failure_rate: Failure rate (0-1)
        latency_ms: Simulated latency
        
    Returns:
        Mock configuration
    """
    global _mock_active, _mock_state, _failure_config
    
    _mock_active = True
    _mock_state = MockUnityState(
        instance_id=f"mock-{uuid.uuid4().hex[:8]}",
        unity_version=unity_version,
        project_name=project_name,
        assets=_DEFAULT_ASSETS.copy(),
        scene_objects=_DEFAULT_SCENE_OBJECTS.copy(),
    )
    
    _failure_config = MockFailureConfig(
        enabled=failure_mode is not None or failure_rate > 0,
        failure_mode=failure_mode,
        failure_rate=failure_rate,
        latency_ms=latency_ms,
    )
    
    await ctx.info(f"Mock Unity enabled: {project_name} ({unity_version})")
    
    if failure_mode:
        await ctx.info(f"Failure injection: {failure_mode} @ {failure_rate:.0%}")
    
    return {
        "success": True,
        "message": "Mock Unity enabled",
        "mock": {
            "instance_id": _mock_state.instance_id,
            "unity_version": unity_version,
            "project_name": project_name,
            "failure_mode": failure_mode,
            "failure_rate": failure_rate,
            "latency_ms": latency_ms,
        },
    }


@mcp_for_unity_tool(
    name="disable_mock_unity",
    description=(
        "Disable the Unity mock/simulator and restore live Unity connections."
    ),
    annotations=ToolAnnotations(
        title="Disable Mock Unity",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def disable_mock_unity(
    ctx: Context,
) -> dict[str, Any]:
    """Disable the Unity mock simulator.
    
    Args:
        ctx: FastMCP context
        
    Returns:
        Status
    """
    global _mock_active
    
    was_active = _mock_active
    _mock_active = False
    
    await ctx.info("Mock Unity disabled")
    
    return {
        "success": True,
        "message": "Mock Unity disabled",
        "was_active": was_active,
    }


@mcp_for_unity_tool(
    name="configure_mock_failure",
    description=(
        "Configure failure injection scenarios for the Unity mock. "
        "Useful for testing error handling and recovery logic."
    ),
    annotations=ToolAnnotations(
        title="Configure Mock Failure",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def configure_mock_failure(
    ctx: Context,
    failure_mode: Annotated[
        str | None,
        "Failure mode: compile_in_progress, domain_reload, dropped_transport, stale_state, locked_asset, or None to disable"
    ] = None,
    failure_rate: Annotated[
        float,
        "Failure injection rate (0.0 to 1.0)"
    ] = 0.0,
    set_compiling: Annotated[
        bool | None,
        "Set compiling state (for compile_in_progress mode)"
    ] = None,
    set_domain_reload: Annotated[
        bool | None,
        "Set domain reload pending state"
    ] = None,
) -> dict[str, Any]:
    """Configure failure injection for the mock.
    
    Args:
        ctx: FastMCP context
        failure_mode: Failure mode to inject
        failure_rate: Rate of injection
        set_compiling: Set compiling state
        set_domain_reload: Set domain reload state
        
    Returns:
        Configuration status
    """
    global _failure_config, _mock_state
    
    if failure_mode is not None:
        _failure_config.enabled = True
        _failure_config.failure_mode = failure_mode
        _failure_config.failure_rate = max(0.0, min(1.0, failure_rate))
    else:
        _failure_config.enabled = False
        _failure_config.failure_mode = None
        _failure_config.failure_rate = 0.0
    
    # Update state flags
    if set_compiling is not None:
        _mock_state.is_compiling = set_compiling
    if set_domain_reload is not None:
        _mock_state.is_domain_reload_pending = set_domain_reload
    
    await ctx.info(
        f"Mock failure config: mode={failure_mode}, rate={failure_rate:.0%}"
    )
    
    return {
        "success": True,
        "failure_mode": failure_mode,
        "failure_rate": _failure_config.failure_rate,
        "enabled": _failure_config.enabled,
        "state": {
            "is_compiling": _mock_state.is_compiling,
            "is_domain_reload_pending": _mock_state.is_domain_reload_pending,
        },
    }


@mcp_for_unity_tool(
    name="get_mock_state",
    description=(
        "Get the current state of the mock Unity instance. "
        "Shows play mode, compilation state, scene objects, and more."
    ),
    annotations=ToolAnnotations(
        title="Get Mock State",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def get_mock_state(
    ctx: Context,
) -> dict[str, Any]:
    """Get mock Unity state.
    
    Args:
        ctx: FastMCP context
        
    Returns:
        Mock state
    """
    if not _mock_active:
        return {
            "success": False,
            "error": "mock_not_active",
            "message": "Mock Unity is not enabled. Call enable_mock_unity first.",
        }
    
    return {
        "success": True,
        "mock_active": _mock_active,
        "state": {
            "instance_id": _mock_state.instance_id,
            "unity_version": _mock_state.unity_version,
            "project_name": _mock_state.project_name,
            "is_playing": _mock_state.is_playing,
            "is_paused": _mock_state.is_paused,
            "is_compiling": _mock_state.is_compiling,
            "is_domain_reload_pending": _mock_state.is_domain_reload_pending,
            "is_refresh_in_progress": _mock_state.is_refresh_in_progress,
            "active_scene": _mock_state.active_scene,
            "scene_object_count": len(_mock_state.scene_objects),
            "asset_count": len(_mock_state.assets),
        },
        "failure_config": {
            "enabled": _failure_config.enabled,
            "mode": _failure_config.failure_mode,
            "rate": _failure_config.failure_rate,
        },
    }


@mcp_for_unity_tool(
    name="simulate_mock_command",
    description=(
        "Send a command directly to the mock Unity simulator. "
        "Useful for testing specific responses and scenarios."
    ),
    annotations=ToolAnnotations(
        title="Simulate Mock Command",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def simulate_mock_command(
    ctx: Context,
    command: Annotated[
        str,
        "Command to simulate"
    ],
    params: Annotated[
        dict[str, Any],
        "Command parameters"
    ] = None,
) -> dict[str, Any]:
    """Simulate a command on the mock Unity.
    
    Args:
        ctx: FastMCP context
        command: Command name
        params: Command parameters
        
    Returns:
        Simulated response
    """
    if not _mock_active:
        return {
            "success": False,
            "error": "mock_not_active",
            "message": "Mock Unity is not enabled.",
        }
    
    _simulate_latency()
    
    response = _handle_tool_command(command, params or {})
    
    await ctx.info(f"Mock command: {command} -> {response.get('success')}")
    
    return response


@mcp_for_unity_resource(
    uri="mcpforunity://mock/state",
    name="mock_unity_state",
    description="Current state of the mock Unity simulator (if enabled).",
)
async def get_mock_unity_resource(ctx: Context) -> MCPResponse:
    """Resource providing mock Unity state.
    
    Args:
        ctx: FastMCP context
        
    Returns:
        Mock state as MCPResponse
    """
    if not _mock_active:
        return MCPResponse(
            success=False,
            error="mock_not_active",
            message="Mock Unity is not enabled.",
        )
    
    return MCPResponse(
        success=True,
        message="Mock Unity state",
        data={
            "instance_id": _mock_state.instance_id,
            "unity_version": _mock_state.unity_version,
            "project_name": _mock_state.project_name,
            "platform": _mock_state.platform,
            "is_playing": _mock_state.is_playing,
            "is_compiling": _mock_state.is_compiling,
            "scene_objects": _mock_state.scene_objects,
            "assets": _mock_state.assets,
        },
    )


# Public API for transport layer integration
def is_mock_active() -> bool:
    """Check if mock Unity is active."""
    return _mock_active


def mock_send_command(command: str, params: dict[str, Any]) -> dict[str, Any]:
    """Send a command to the mock Unity (for transport layer integration).
    
    Args:
        command: Command name
        params: Command parameters
        
    Returns:
        Simulated response
    """
    if not _mock_active:
        return {
            "success": False,
            "error": "mock_not_active",
            "message": "Mock Unity is not enabled.",
        }
    
    _simulate_latency()
    return _handle_tool_command(command, params)
