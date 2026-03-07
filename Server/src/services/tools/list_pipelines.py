"""Tool for listing and retrieving saved pipelines."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool


def _get_pipelines_directories() -> list[Path]:
    """Get all directories that may contain pipelines."""
    dirs = []
    
    # Check for project-specific pipelines directory
    project_root = Path.cwd()
    potential_roots = [
        project_root,
        project_root.parent,
        project_root.parent.parent,
    ]
    
    for root in potential_roots:
        if (root / "Assets").exists() or (root / "ProjectSettings").exists():
            project_pipelines = root / "Pipelines"
            if project_pipelines.exists():
                dirs.append(project_pipelines)
            break
    
    # Also check current working directory
    cwd_pipelines = project_root / "Pipelines"
    if cwd_pipelines.exists() and cwd_pipelines not in dirs:
        dirs.append(cwd_pipelines)
    
    # User config directory
    user_config = Path.home() / ".unity-mcp" / "pipelines"
    if user_config.exists():
        dirs.append(user_config)
    
    return dirs


@mcp_for_unity_tool(
    name="list_pipelines",
    unity_target=None,
    description=(
        "List saved pipelines or get details of a specific pipeline. "
        "Pipelines are searched in ProjectRoot/Pipelines/ and ~/.unity-mcp/pipelines/. "
        "Use to discover available automation workflows before replaying them."
    ),
    annotations=ToolAnnotations(
        title="List Pipelines",
        destructiveHint=False,
    ),
    group="pipeline",
)
async def list_pipelines(
    ctx: Context,
    action: Annotated[
        Literal["list", "get"],
        "Action to perform: 'list' all pipelines or 'get' a specific one"
    ] = "list",
    name: Annotated[str | None, "Pipeline name to retrieve (required for 'get' action)"] = None,
    filter_tags: Annotated[list[str] | None, "Filter pipelines by tags (for 'list' action)"] = None,
    filter_author: Annotated[str | None, "Filter pipelines by author (for 'list' action)"] = None,
) -> dict[str, Any]:
    """List or retrieve saved pipelines."""
    try:
        if action == "get":
            if not name:
                return {
                    "success": False,
                    "message": "Pipeline name is required for 'get' action",
                }
            
            # Search for the pipeline in all directories
            for pipelines_dir in _get_pipelines_directories():
                file_path = pipelines_dir / f"{name}.json"
                if file_path.exists():
                    with open(file_path, "r", encoding="utf-8") as f:
                        pipeline_data = json.load(f)
                    
                    return {
                        "success": True,
                        "message": f"Pipeline '{name}' retrieved",
                        "pipeline": pipeline_data,
                        "path": str(file_path),
                    }
            
            return {
                "success": False,
                "message": f"Pipeline '{name}' not found",
            }
        
        else:  # list action
            pipelines = []
            seen_names = set()
            
            for pipelines_dir in _get_pipelines_directories():
                if not pipelines_dir.exists():
                    continue
                
                for file_path in pipelines_dir.glob("*.json"):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            pipeline_data = json.load(f)
                        
                        metadata = pipeline_data.get("metadata", {})
                        pipeline_name = metadata.get("name", file_path.stem)
                        
                        # Skip duplicates (prefer earlier directories)
                        if pipeline_name in seen_names:
                            continue
                        seen_names.add(pipeline_name)
                        
                        # Apply filters
                        if filter_tags:
                            pipeline_tags = metadata.get("tags", [])
                            if not any(tag in pipeline_tags for tag in filter_tags):
                                continue
                        
                        if filter_author:
                            if metadata.get("author") != filter_author:
                                continue
                        
                        pipelines.append({
                            "name": pipeline_name,
                            "version": metadata.get("version", "unknown"),
                            "description": metadata.get("description"),
                            "author": metadata.get("author"),
                            "tags": metadata.get("tags", []),
                            "step_count": len(pipeline_data.get("steps", [])),
                            "path": str(file_path),
                        })
                        
                    except (json.JSONDecodeError, IOError):
                        # Skip invalid files
                        continue
            
            # Sort by name
            pipelines.sort(key=lambda p: p["name"])
            
            return {
                "success": True,
                "message": f"Found {len(pipelines)} pipeline(s)",
                "pipelines": pipelines,
                "search_paths": [str(d) for d in _get_pipelines_directories()],
            }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to list pipelines: {str(e)}",
        }
