"""Fixture replay tool for deterministic Unity response simulation.

This module replays captured fixtures without requiring a live Unity connection,
enabling deterministic testing and development workflows.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Callable

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool


@dataclass
class ReplaySession:
    """A fixture replay session."""
    session_id: str
    fixtures: list[dict[str, Any]]
    started_at: datetime
    speed_multiplier: float = 1.0
    current_index: int = 0
    is_active: bool = True
    inject_errors: list[str] = field(default_factory=list)
    scenario_overrides: dict[str, Any] = field(default_factory=dict)


# In-memory replay sessions
_replay_sessions: dict[str, ReplaySession] = {}


def _load_fixture(fixture_id: str) -> dict[str, Any] | None:
    """Load a fixture by ID from the capture module's in-memory store."""
    try:
        from services.tools.capture_unity_fixture import _fixtures, _fixture_to_dict
    except Exception:
        return None

    fixture = _fixtures.get(fixture_id)
    return _fixture_to_dict(fixture) if fixture is not None else None


def _load_fixture_from_file(fixture_path: str) -> dict[str, Any] | None:
    """Load a fixture from disk."""
    path = Path(fixture_path)
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _find_matching_fixture(
    tool: str,
    params: dict[str, Any],
    fixtures: list[dict[str, Any]],
    fuzzy_match: bool = True,
) -> dict[str, Any] | None:
    """Find a fixture matching the tool and parameters.
    
    Args:
        tool: Tool name
        params: Request parameters
        fixtures: Available fixtures
        fuzzy_match: Allow partial parameter matching
        
    Returns:
        Matching fixture or None
    """
    # First try exact match
    for fixture in fixtures:
        if fixture["tool"] != tool:
            continue
        
        fixture_params = fixture.get("request", {})
        
        # Exact match
        if fixture_params == params:
            return fixture
        
        # Fuzzy match - all provided params match
        if fuzzy_match:
            match = True
            for key, value in params.items():
                if key not in fixture_params or fixture_params[key] != value:
                    match = False
                    break
            if match:
                return fixture
    
    # Tool-only match as fallback
    for fixture in fixtures:
        if fixture["tool"] == tool:
            return fixture
    
    return None


def _apply_response_overrides(
    response: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """Apply scenario overrides to a response.
    
    Args:
        response: Original response
        overrides: Overrides to apply
        
    Returns:
        Modified response
    """
    result = response.copy()
    
    # Override success/error status
    if "force_success" in overrides:
        result["success"] = overrides["force_success"]
    
    if "force_error" in overrides:
        result["success"] = False
        result["error"] = overrides["force_error"]
    
    # Inject latency
    if "inject_latency_ms" in overrides:
        time.sleep(overrides["inject_latency_ms"] / 1000.0)
    
    # Modify data
    if "data_overrides" in overrides:
        if result.get("data") is None:
            result["data"] = {}
        if isinstance(result["data"], dict):
            result["data"].update(overrides["data_overrides"])
    
    return result


@mcp_for_unity_tool(
    group="dev_tools",
    name="start_fixture_replay",
    unity_target=None,
    description=(
        "Start a fixture replay session for deterministic testing without live Unity. "
        "Loads fixtures and replays responses based on tool/parameter matching."
    ),
    annotations=ToolAnnotations(
        title="Start Fixture Replay",
        destructiveHint=False,
    ),
)
async def start_fixture_replay(
    ctx: Context,
    fixtures: Annotated[
        list[dict[str, Any]],
        "List of fixtures to replay (from get_captured_fixtures)"
    ],
    speed_multiplier: Annotated[
        float,
        "Speed multiplier for replay timing (1.0 = normal, 2.0 = 2x faster, 0.5 = half speed)"
    ] = 1.0,
    deterministic: Annotated[
        bool,
        "Use deterministic random seed for consistent replay"
    ] = True,
    inject_errors: Annotated[
        list[str],
        "List of error scenarios to inject (e.g., ['timeout', 'connection_lost'])"
    ] = None,
) -> dict[str, Any]:
    """Start a fixture replay session.
    
    Args:
        ctx: FastMCP context
        fixtures: Fixtures to replay
        speed_multiplier: Playback speed multiplier
        deterministic: Use deterministic random
        inject_errors: Error scenarios to inject
        
    Returns:
        Replay session details
    """
    import uuid
    
    session_id = f"replay_{uuid.uuid4().hex[:8]}"
    
    if deterministic:
        random.seed(42)
    
    session = ReplaySession(
        session_id=session_id,
        fixtures=fixtures,
        started_at=datetime.utcnow(),
        speed_multiplier=speed_multiplier,
        inject_errors=inject_errors or [],
    )
    
    _replay_sessions[session_id] = session
    
    await ctx.info(
        f"Started fixture replay session: {session_id} "
        f"({len(fixtures)} fixtures, {speed_multiplier}x speed)"
    )
    
    return {
        "success": True,
        "session_id": session_id,
        "fixture_count": len(fixtures),
        "speed_multiplier": speed_multiplier,
        "deterministic": deterministic,
    }


@mcp_for_unity_tool(
    name="replay_request",
    unity_target=None,
    description=(
        "Replay a captured response for a given tool and parameters. "
        "Must have an active replay session. Returns the captured response "
        "with optional modifications based on replay configuration."
    ),
    annotations=ToolAnnotations(
        title="Replay Request",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def replay_request(
    ctx: Context,
    session_id: Annotated[
        str,
        "Replay session ID"
    ],
    tool: Annotated[
        str,
        "Tool name to replay"
    ],
    params: Annotated[
        dict[str, Any],
        "Tool parameters to match"
    ],
    fuzzy_match: Annotated[
        bool,
        "Allow fuzzy parameter matching"
    ] = True,
) -> dict[str, Any]:
    """Replay a captured response.
    
    Args:
        ctx: FastMCP context
        session_id: Active replay session
        tool: Tool name
        params: Request parameters
        fuzzy_match: Allow fuzzy matching
        
    Returns:
        Captured response or error
    """
    if session_id not in _replay_sessions:
        return {
            "success": False,
            "error": "session_not_found",
            "message": f"Replay session {session_id} not found.",
        }
    
    session = _replay_sessions[session_id]
    if not session.is_active:
        return {
            "success": False,
            "error": "session_inactive",
            "message": f"Replay session {session_id} is not active.",
        }
    
    # Find matching fixture
    fixture = _find_matching_fixture(tool, params, session.fixtures, fuzzy_match)
    
    if fixture is None:
        return {
            "success": False,
            "error": "fixture_not_found",
            "message": f"No fixture found for tool: {tool}",
            "available_tools": list(set(f["tool"] for f in session.fixtures)),
        }
    
    # Apply speed multiplier delay (simulate network latency)
    base_latency = fixture.get("metadata", {}).get("latency_ms", 50)
    delay = (base_latency / 1000.0) / session.speed_multiplier
    if delay > 0:
        await asyncio.sleep(delay)
    
    # Get response
    response = fixture.get("response", {}).copy()
    
    # Apply scenario overrides
    response = _apply_response_overrides(response, session.scenario_overrides)
    
    # Increment index for deterministic iteration
    session.current_index = (session.current_index + 1) % len(session.fixtures)
    
    await ctx.info(f"Replayed {tool} from fixture: {fixture.get('fixture_id', 'unknown')}")
    
    return {
        "success": True,
        "replay": True,
        "fixture_id": fixture.get("fixture_id"),
        "response": response,
    }


@mcp_for_unity_tool(
    name="stop_fixture_replay",
    unity_target=None,
    description=(
        "Stop an active fixture replay session and return replay statistics."
    ),
    annotations=ToolAnnotations(
        title="Stop Fixture Replay",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def stop_fixture_replay(
    ctx: Context,
    session_id: Annotated[
        str,
        "Replay session ID to stop"
    ],
) -> dict[str, Any]:
    """Stop a replay session.
    
    Args:
        ctx: FastMCP context
        session_id: Session to stop
        
    Returns:
        Session statistics
    """
    if session_id not in _replay_sessions:
        return {
            "success": False,
            "error": "session_not_found",
            "message": f"Replay session {session_id} not found.",
        }
    
    session = _replay_sessions.pop(session_id)
    session.is_active = False
    
    duration = (datetime.utcnow() - session.started_at).total_seconds()
    
    await ctx.info(f"Stopped replay session: {session_id}")
    
    return {
        "success": True,
        "session_id": session_id,
        "duration_seconds": duration,
        "requests_replayed": session.current_index,
        "total_fixtures": len(session.fixtures),
    }


@mcp_for_unity_tool(
    name="configure_replay_scenario",
    unity_target=None,
    description=(
        "Configure scenario injection for replay sessions. "
        "Modify replay behavior with error injection, latency, or data overrides."
    ),
    annotations=ToolAnnotations(
        title="Configure Replay Scenario",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def configure_replay_scenario(
    ctx: Context,
    session_id: Annotated[
        str,
        "Replay session ID"
    ],
    force_success: Annotated[
        bool | None,
        "Force all responses to succeed"
    ] = None,
    force_error: Annotated[
        str | None,
        "Force all responses to fail with this error"
    ] = None,
    inject_latency_ms: Annotated[
        int,
        "Add fixed latency to all responses"
    ] = 0,
    data_overrides: Annotated[
        dict[str, Any],
        "Override specific data fields in responses"
    ] = None,
) -> dict[str, Any]:
    """Configure replay scenario overrides.
    
    Args:
        ctx: FastMCP context
        session_id: Target replay session
        force_success: Force success status
        force_error: Force error message
        inject_latency_ms: Add latency
        data_overrides: Override response data
        
    Returns:
        Configuration result
    """
    if session_id not in _replay_sessions:
        return {
            "success": False,
            "error": "session_not_found",
            "message": f"Replay session {session_id} not found.",
        }
    
    session = _replay_sessions[session_id]
    
    # Build overrides
    overrides: dict[str, Any] = {}
    if force_success is not None:
        overrides["force_success"] = force_success
    if force_error is not None:
        overrides["force_error"] = force_error
    if inject_latency_ms > 0:
        overrides["inject_latency_ms"] = inject_latency_ms
    if data_overrides:
        overrides["data_overrides"] = data_overrides
    
    session.scenario_overrides.update(overrides)
    
    await ctx.info(f"Configured scenario for session {session_id}: {list(overrides.keys())}")
    
    return {
        "success": True,
        "session_id": session_id,
        "overrides": list(overrides.keys()),
    }


@mcp_for_unity_tool(
    name="list_replay_sessions",
    unity_target=None,
    description=(
        "List all active replay sessions with their status and configuration."
    ),
    annotations=ToolAnnotations(
        title="List Replay Sessions",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def list_replay_sessions(
    ctx: Context,
) -> dict[str, Any]:
    """List all active replay sessions.
    
    Args:
        ctx: FastMCP context
        
    Returns:
        List of active sessions
    """
    sessions = []
    for session in _replay_sessions.values():
        sessions.append({
            "session_id": session.session_id,
            "is_active": session.is_active,
            "started_at": session.started_at.isoformat(),
            "fixture_count": len(session.fixtures),
            "current_index": session.current_index,
            "speed_multiplier": session.speed_multiplier,
            "has_overrides": bool(session.scenario_overrides),
        })
    
    return {
        "success": True,
        "sessions": sessions,
        "active_count": len(_replay_sessions),
    }


# Convenience function for tool wrappers to use replay
def try_replay_response(
    tool: str,
    params: dict[str, Any],
    active_session_id: str | None = None,
) -> dict[str, Any] | None:
    """Try to get a replay response for a tool invocation.
    
    Args:
        tool: Tool name
        params: Request parameters
        active_session_id: Specific session to use, or None for any active
        
    Returns:
        Replay response if available, None otherwise
    """
    if not _replay_sessions:
        return None
    
    # Use specified session or first active
    if active_session_id:
        if active_session_id not in _replay_sessions:
            return None
        sessions = {active_session_id: _replay_sessions[active_session_id]}
    else:
        sessions = _replay_sessions
    
    # Find first matching response
    for session in sessions.values():
        if not session.is_active:
            continue
        
        fixture = _find_matching_fixture(tool, params, session.fixtures)
        if fixture:
            response = fixture.get("response", {}).copy()
            return _apply_response_overrides(response, session.scenario_overrides)
    
    return None


async def replay_unity_fixture(
    ctx: Context,
    fixture_id: str | None = None,
    fixture_path: str | None = None,
    mock_mode: bool = False,
    transform: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay a single captured fixture without manually managing sessions."""
    fixture: dict[str, Any] | None = None
    if fixture_id:
        fixture = _load_fixture(fixture_id)
    elif fixture_path:
        fixture = _load_fixture_from_file(fixture_path)

    if fixture is None:
        return {
            "success": False,
            "error": "fixture_not_found",
            "message": "Fixture could not be loaded.",
        }

    response = fixture.get("response", {}).copy()

    if transform and isinstance(response.get("data"), dict):
        if "multiply_count" in transform and isinstance(response["data"].get("count"), (int, float)):
            response["data"]["count"] *= transform["multiply_count"]

    await ctx.info(f"Replayed fixture for tool: {fixture.get('tool', 'unknown')}")
    return {
        "success": True,
        "replayed": True,
        "mock_mode": mock_mode,
        "response": response,
        "fixture": fixture,
    }
