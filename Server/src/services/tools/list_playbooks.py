"""Tool for listing and retrieving playbooks."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool


# Built-in playbook templates directory
BUILT_IN_PLAYBOOKS_DIR = Path(__file__).parent / "playbooks"


def _ensure_built_in_playbooks():
    """Ensure built-in playbooks are created."""
    # Import create_playbook to trigger playbook creation
    try:
        from services.tools import create_playbook as cp_module
        cp_module._ensure_built_in_playbooks()
    except Exception:
        pass


def _get_all_playbooks() -> list[dict[str, Any]]:
    """Get all available playbooks (built-in and custom)."""
    _ensure_built_in_playbooks()
    
    playbooks = []
    seen_names = set()
    
    # Built-in playbooks
    if BUILT_IN_PLAYBOOKS_DIR.exists():
        for file_path in BUILT_IN_PLAYBOOKS_DIR.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    playbook_data = json.load(f)
                
                metadata = playbook_data.get("metadata", {})
                name = metadata.get("name", file_path.stem)
                
                playbooks.append({
                    "name": name,
                    "description": metadata.get("description"),
                    "version": metadata.get("version", "1.0"),
                    "author": metadata.get("author", "unity-mcp"),
                    "tags": metadata.get("tags", []),
                    "category": metadata.get("category", "general"),
                    "step_count": len(playbook_data.get("steps", [])),
                    "has_parameters": "parameters" in playbook_data,
                    "built_in": True,
                    "path": str(file_path),
                })
                seen_names.add(name)
                
            except (json.JSONDecodeError, IOError):
                continue
    
    # User playbooks from pipelines directory
    from services.tools.list_pipelines import _get_pipelines_directories
    
    for pipelines_dir in _get_pipelines_directories():
        playbooks_subdir = pipelines_dir / "playbooks"
        if playbooks_subdir.exists():
            for file_path in playbooks_subdir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        playbook_data = json.load(f)
                    
                    metadata = playbook_data.get("metadata", {})
                    name = metadata.get("name", file_path.stem)
                    
                    # Skip duplicates
                    if name in seen_names:
                        continue
                    
                    playbooks.append({
                        "name": name,
                        "description": metadata.get("description"),
                        "version": metadata.get("version", "1.0"),
                        "author": metadata.get("author", "custom"),
                        "tags": metadata.get("tags", []),
                        "category": metadata.get("category", "general"),
                        "step_count": len(playbook_data.get("steps", [])),
                        "has_parameters": "parameters" in playbook_data,
                        "built_in": False,
                        "path": str(file_path),
                    })
                    seen_names.add(name)
                    
                except (json.JSONDecodeError, IOError):
                    continue
    
    # Sort by name
    playbooks.sort(key=lambda p: (not p["built_in"], p["name"]))
    
    return playbooks


def _find_playbook(name: str) -> tuple[dict[str, Any] | None, Path | None]:
    """Find a playbook by name."""
    _ensure_built_in_playbooks()
    
    # Check built-in first
    built_in_path = BUILT_IN_PLAYBOOKS_DIR / f"{name}.json"
    if built_in_path.exists():
        try:
            with open(built_in_path, "r", encoding="utf-8") as f:
                return json.load(f), built_in_path
        except (json.JSONDecodeError, IOError):
            pass
    
    # Check user playbooks
    from services.tools.list_pipelines import _get_pipelines_directories
    
    for pipelines_dir in _get_pipelines_directories():
        playbooks_subdir = pipelines_dir / "playbooks"
        user_path = playbooks_subdir / f"{name}.json"
        if user_path.exists():
            try:
                with open(user_path, "r", encoding="utf-8") as f:
                    return json.load(f), user_path
            except (json.JSONDecodeError, IOError):
                continue
    
    return None, None


@mcp_for_unity_tool(
    name="list_playbooks",
    unity_target=None,
    description=(
        "List available playbooks or get details of a specific playbook. "
        "Playbooks are reusable templates for common Unity workflows. "
        "Built-in playbooks include: basic_player_controller, ui_canvas_setup, scene_lighting_setup. "
        "Use run_playbook to execute them."
    ),
    annotations=ToolAnnotations(
        title="List Playbooks",
        destructiveHint=False,
    ),
    group="pipeline",
)
async def list_playbooks(
    ctx: Context,
    action: Annotated[
        Literal["list", "get"],
        "Action to perform: 'list' all playbooks or 'get' a specific one"
    ] = "list",
    playbook_id: Annotated[str | None, "Playbook ID/name to retrieve (required for 'get' action)"] = None,
    filter_category: Annotated[str | None, "Filter by category (for 'list' action)"] = None,
    filter_tags: Annotated[list[str] | None, "Filter by tags (for 'list' action)"] = None,
) -> dict[str, Any]:
    """List or retrieve available playbooks."""
    try:
        if action == "get":
            if not playbook_id:
                return {
                    "success": False,
                    "message": "playbook_id is required for 'get' action",
                }
            
            playbook_data, file_path = _find_playbook(playbook_id)
            
            if not playbook_data:
                return {
                    "success": False,
                    "message": f"Playbook '{playbook_id}' not found",
                }
            
            return {
                "success": True,
                "message": f"Playbook '{playbook_id}' retrieved",
                "playbook": playbook_data,
                "path": str(file_path) if file_path else None,
            }
        
        else:  # list action
            playbooks = _get_all_playbooks()
            
            # Apply filters
            if filter_category:
                playbooks = [p for p in playbooks if p["category"] == filter_category]
            
            if filter_tags:
                playbooks = [p for p in playbooks if any(tag in p["tags"] for tag in filter_tags)]
            
            # Group by built-in vs custom
            built_in = [p for p in playbooks if p["built_in"]]
            custom = [p for p in playbooks if not p["built_in"]]
            
            return {
                "success": True,
                "message": f"Found {len(playbooks)} playbook(s): {len(built_in)} built-in, {len(custom)} custom",
                "playbooks": playbooks,
                "categories": sorted(set(p["category"] for p in playbooks)),
                "all_tags": sorted(set(tag for p in playbooks for tag in p["tags"])),
            }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to list playbooks: {str(e)}",
        }
