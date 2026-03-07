"""Fixture capture tool for recording Unity responses.

This module captures real Unity responses for later replay in tests,
enabling regression testing and deterministic development workflows.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@dataclass
class Fixture:
    """A captured fixture containing request/response pair."""
    fixture_id: str
    scenario: str
    tool: str
    request: dict[str, Any]
    response: dict[str, Any]
    captured_at: datetime
    unity_version: str | None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# In-memory fixture storage
_fixtures: dict[str, Fixture] = {}
_capture_active: bool = False
_current_scenario: str = "default"
_capture_filters: dict[str, Any] = {}


def _sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    return re.sub(r'[^\w\-_.]', '_', name)


def _fixture_to_dict(fixture: Fixture) -> dict[str, Any]:
    """Convert a Fixture to a dictionary."""
    return {
        "fixture_id": fixture.fixture_id,
        "scenario": fixture.scenario,
        "tool": fixture.tool,
        "request": fixture.request,
        "response": fixture.response,
        "captured_at": fixture.captured_at.isoformat(),
        "unity_version": fixture.unity_version,
        "tags": fixture.tags,
        "metadata": fixture.metadata,
    }


def _matches_filter(tool: str, params: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Check if a tool invocation matches the capture filter.
    
    Args:
        tool: Tool name
        params: Tool parameters
        filters: Filter configuration
        
    Returns:
        True if should capture, False to skip
    """
    # Include filter
    include_tools = filters.get("include_tools")
    if include_tools and tool not in include_tools:
        return False
    
    # Exclude filter
    exclude_tools = filters.get("exclude_tools", [])
    if tool in exclude_tools:
        return False
    
    # Parameter filter
    param_filter = filters.get("params")
    if param_filter:
        for key, value in param_filter.items():
            if key not in params or params[key] != value:
                return False
    
    return True


def capture_fixture(
    tool: str,
    request: dict[str, Any],
    response: dict[str, Any],
    unity_version: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """Capture a fixture (called by middleware/tool wrappers).
    
    Args:
        tool: Tool name
        request: Request parameters
        response: Unity response
        unity_version: Unity version if available
        metadata: Additional capture metadata
        
    Returns:
        Fixture ID if captured, None if skipped
    """
    global _capture_active, _current_scenario, _capture_filters
    
    if not _capture_active:
        return None
    
    # Apply filters
    if not _matches_filter(tool, request, _capture_filters):
        return None
    
    fixture_id = str(uuid.uuid4())
    tags = list(_capture_filters.get("tags", []))
    
    fixture = Fixture(
        fixture_id=fixture_id,
        scenario=_current_scenario,
        tool=tool,
        request=request.copy(),
        response=response.copy(),
        captured_at=datetime.utcnow(),
        unity_version=unity_version,
        tags=tags,
        metadata=metadata or {},
    )
    
    _fixtures[fixture_id] = fixture
    return fixture_id


async def capture_unity_fixture(
    ctx: Context,
    tool_name: str,
    params: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    save_path: str | None = None,
) -> dict[str, Any]:
    """Capture a single live Unity response as a replay fixture.

    This convenience wrapper is intentionally separate from the session-oriented
    start/stop capture flow. It is used by tests and development workflows that
    want one-shot capture behavior.
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    response = await send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        tool_name,
        params,
    )

    response_dict = response if isinstance(response, dict) else {"success": False, "message": str(response)}
    fixture_id = str(uuid.uuid4())
    fixture_data = {
        "fixture_id": fixture_id,
        "tool": tool_name,
        "params": params,
        "request": params,
        "response": response_dict,
        "captured_at": datetime.utcnow().isoformat(),
        "metadata": metadata or {},
    }

    if save_path:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(fixture_data, handle, indent=2)
        fixture_data["saved_to"] = str(path)

    return {
        "success": True,
        "fixture_id": fixture_id,
        "tool": tool_name,
        "captured_response": response_dict,
        **({"saved_to": fixture_data["saved_to"]} if "saved_to" in fixture_data else {}),
    }


@mcp_for_unity_tool(
    group="dev_tools",
    name="start_fixture_capture",
    unity_target=None,
    description=(
        "Start capturing Unity responses as fixtures for replay testing. "
        "Captures request/response pairs with scenario tags and metadata."
    ),
    annotations=ToolAnnotations(
        title="Start Fixture Capture",
        destructiveHint=False,
    ),
)
async def start_fixture_capture(
    ctx: Context,
    scenario: Annotated[
        str,
        "Scenario name for tagging captured fixtures"
    ] = "default",
    include_tools: Annotated[
        list[str] | None,
        "Only capture these tools (None = capture all)"
    ] = None,
    exclude_tools: Annotated[
        list[str],
        "Tools to exclude from capture"
    ] = None,
    tags: Annotated[
        list[str],
        "Tags to apply to all captured fixtures"
    ] = None,
) -> dict[str, Any]:
    """Start capturing Unity responses as fixtures.
    
    Args:
        ctx: FastMCP context
        scenario: Scenario name for tagging
        include_tools: Optional whitelist of tools to capture
        exclude_tools: List of tools to exclude
        tags: Additional tags for all fixtures
        
    Returns:
        Capture session status
    """
    global _capture_active, _current_scenario, _capture_filters
    
    _capture_active = True
    _current_scenario = scenario
    _capture_filters = {
        "include_tools": include_tools,
        "exclude_tools": exclude_tools or [],
        "tags": tags or [],
    }
    
    await ctx.info(f"Started fixture capture for scenario: {scenario}")
    
    return {
        "success": True,
        "scenario": scenario,
        "filters": _capture_filters,
        "message": f"Fixture capture started. Scenario: {scenario}",
    }


@mcp_for_unity_tool(
    name="stop_fixture_capture",
    unity_target=None,
    description=(
        "Stop capturing fixtures and return capture summary. "
        "Optionally export captured fixtures to a file."
    ),
    annotations=ToolAnnotations(
        title="Stop Fixture Capture",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def stop_fixture_capture(
    ctx: Context,
    export_path: Annotated[
        str | None,
        "Optional path to export fixtures as JSON"
    ] = None,
) -> dict[str, Any]:
    """Stop capturing fixtures.
    
    Args:
        ctx: FastMCP context
        export_path: Optional file path to export fixtures
        
    Returns:
        Capture summary with fixture count and optional export path
    """
    global _capture_active
    
    _capture_active = False
    
    # Get fixtures for the current scenario
    scenario_fixtures = [
        f for f in _fixtures.values() if f.scenario == _current_scenario
    ]
    
    result: dict[str, Any] = {
        "success": True,
        "scenario": _current_scenario,
        "captured_count": len(scenario_fixtures),
        "total_fixtures": len(_fixtures),
    }
    
    # Export if requested
    if export_path and scenario_fixtures:
        try:
            path = Path(export_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                "scenario": _current_scenario,
                "exported_at": datetime.utcnow().isoformat(),
                "fixtures": [_fixture_to_dict(f) for f in scenario_fixtures],
            }
            
            with open(path, "w") as f:
                json.dump(export_data, f, indent=2)
            
            result["export_path"] = str(path.absolute())
            result["exported_count"] = len(scenario_fixtures)
            await ctx.info(f"Exported {len(scenario_fixtures)} fixtures to {path}")
        except Exception as e:
            result["export_error"] = str(e)
    
    await ctx.info(
        f"Stopped fixture capture. Captured {len(scenario_fixtures)} fixtures "
        f"for scenario: {_current_scenario}"
    )
    
    return result


@mcp_for_unity_tool(
    name="get_captured_fixtures",
    unity_target=None,
    description=(
        "Get captured fixtures with optional filtering by scenario, tool, or tags. "
        "Returns fixture data including request/response pairs."
    ),
    annotations=ToolAnnotations(
        title="Get Captured Fixtures",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def get_captured_fixtures(
    ctx: Context,
    scenario: Annotated[
        str | None,
        "Filter by scenario name"
    ] = None,
    tool: Annotated[
        str | None,
        "Filter by tool name"
    ] = None,
    tags: Annotated[
        list[str] | None,
        "Filter by tags (all must match)"
    ] = None,
    limit: Annotated[
        int,
        "Maximum number of fixtures to return"
    ] = 100,
) -> dict[str, Any]:
    """Get captured fixtures with optional filtering.
    
    Args:
        ctx: FastMCP context
        scenario: Filter by scenario
        tool: Filter by tool name
        tags: Filter by tags (all must match)
        limit: Maximum results
        
    Returns:
        Filtered fixtures
    """
    fixtures = list(_fixtures.values())
    
    # Apply filters
    if scenario:
        fixtures = [f for f in fixtures if f.scenario == scenario]
    if tool:
        fixtures = [f for f in fixtures if f.tool == tool]
    if tags:
        fixtures = [f for f in fixtures if all(t in f.tags for t in tags)]
    
    # Sort by capture time (newest first)
    fixtures.sort(key=lambda f: f.captured_at, reverse=True)
    
    # Apply limit
    fixtures = fixtures[:limit]
    
    return {
        "success": True,
        "count": len(fixtures),
        "filters": {
            "scenario": scenario,
            "tool": tool,
            "tags": tags,
            "limit": limit,
        },
        "fixtures": [_fixture_to_dict(f) for f in fixtures],
    }


@mcp_for_unity_tool(
    name="import_fixtures",
    unity_target=None,
    description=(
        "Import fixtures from a JSON file. Useful for sharing fixtures "
        "between team members or loading pre-recorded scenarios."
    ),
    annotations=ToolAnnotations(
        title="Import Fixtures",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def import_fixtures(
    ctx: Context,
    import_path: Annotated[
        str,
        "Path to JSON file containing fixtures"
    ],
    merge_scenario: Annotated[
        str | None,
        "Override scenario name for imported fixtures"
    ] = None,
) -> dict[str, Any]:
    """Import fixtures from a JSON file.
    
    Args:
        ctx: FastMCP context
        import_path: Path to JSON file
        merge_scenario: Optional scenario name override
        
    Returns:
        Import result with counts
    """
    try:
        path = Path(import_path)
        if not path.exists():
            return {
                "success": False,
                "error": "file_not_found",
                "message": f"File not found: {import_path}",
            }
        
        with open(path, "r") as f:
            data = json.load(f)
        
        fixtures_data = data.get("fixtures", [])
        imported_count = 0
        
        for fixture_data in fixtures_data:
            fixture_id = str(uuid.uuid4())
            scenario = merge_scenario or fixture_data.get("scenario", "imported")
            
            fixture = Fixture(
                fixture_id=fixture_id,
                scenario=scenario,
                tool=fixture_data["tool"],
                request=fixture_data["request"],
                response=fixture_data["response"],
                captured_at=datetime.fromisoformat(fixture_data["captured_at"]),
                unity_version=fixture_data.get("unity_version"),
                tags=fixture_data.get("tags", ["imported"]),
                metadata=fixture_data.get("metadata", {}),
            )
            
            _fixtures[fixture_id] = fixture
            imported_count += 1
        
        await ctx.info(f"Imported {imported_count} fixtures from {path}")
        
        return {
            "success": True,
            "imported_count": imported_count,
            "source": str(path.absolute()),
            "total_fixtures": len(_fixtures),
        }
        
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": "invalid_json",
            "message": f"Invalid JSON in fixture file: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": "import_failed",
            "message": str(e),
        }


@mcp_for_unity_tool(
    name="delete_fixture",
    unity_target=None,
    description=(
        "Delete a specific fixture by ID or delete all fixtures matching filters."
    ),
    annotations=ToolAnnotations(
        title="Delete Fixture",
        destructiveHint=True,
    ),
    group=None,  # Always visible (meta-tool)
)
async def delete_fixture(
    ctx: Context,
    fixture_id: Annotated[
        str | None,
        "Specific fixture ID to delete"
    ] = None,
    scenario: Annotated[
        str | None,
        "Delete all fixtures in this scenario"
    ] = None,
) -> dict[str, Any]:
    """Delete fixtures.
    
    Args:
        ctx: FastMCP context
        fixture_id: Specific fixture to delete
        scenario: Delete all fixtures in scenario
        
    Returns:
        Deletion result
    """
    if fixture_id:
        if fixture_id not in _fixtures:
            return {
                "success": False,
                "error": "fixture_not_found",
                "message": f"Fixture {fixture_id} not found.",
            }
        del _fixtures[fixture_id]
        return {
            "success": True,
            "message": f"Deleted fixture: {fixture_id}",
            "deleted_count": 1,
        }
    
    if scenario:
        to_delete = [fid for fid, f in _fixtures.items() if f.scenario == scenario]
        for fid in to_delete:
            del _fixtures[fid]
        return {
            "success": True,
            "message": f"Deleted {len(to_delete)} fixtures from scenario: {scenario}",
            "deleted_count": len(to_delete),
        }
    
    return {
        "success": False,
        "error": "no_filter",
        "message": "Specify fixture_id or scenario to delete.",
    }
