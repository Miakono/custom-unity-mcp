"""Tool for saving pipelines to disk."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool


def _get_pipelines_directory() -> Path:
    """Get the directory for storing pipelines.
    
    Checks for ProjectRoot/Pipelines first, then falls back to user config.
    """
    # Check for project-specific pipelines directory
    project_root = Path.cwd()
    project_pipelines = project_root / "Pipelines"
    
    # Also check common Unity project locations
    potential_roots = [
        project_root,
        project_root.parent,
        project_root.parent.parent,
    ]
    
    for root in potential_roots:
        if (root / "Assets").exists() or (root / "ProjectSettings").exists():
            project_pipelines = root / "Pipelines"
            break
    
    if project_pipelines.exists() or os.access(project_root, os.W_OK):
        project_pipelines.mkdir(parents=True, exist_ok=True)
        return project_pipelines
    
    # Fallback to user config directory
    user_config = Path.home() / ".unity-mcp" / "pipelines"
    user_config.mkdir(parents=True, exist_ok=True)
    return user_config


@mcp_for_unity_tool(
    name="save_pipeline",
    unity_target=None,
    description=(
        "Save a pipeline (sequence of tool operations) to disk for later replay. "
        "Pipelines can be stored in the project (ProjectRoot/Pipelines/) or user config. "
        "Saved pipelines can be replayed with replay_pipeline. "
        "Useful for automating repetitive workflows and sharing procedures."
    ),
    annotations=ToolAnnotations(
        title="Save Pipeline",
        destructiveHint=False,
    ),
    group="pipeline",
)
async def save_pipeline(
    ctx: Context,
    name: Annotated[str, "Pipeline name (used as filename)"],
    steps: Annotated[list[dict[str, Any]], "Array of pipeline steps with 'tool', 'action', and 'params' keys"],
    description: Annotated[str | None, "Optional pipeline description"] = None,
    author: Annotated[str | None, "Pipeline author"] = None,
    tags: Annotated[list[str] | None, "Tags for categorizing the pipeline"] = None,
    version: Annotated[str, "Pipeline version"] = "1.0",
    overwrite: Annotated[bool, "Whether to overwrite existing pipeline"] = False,
) -> dict[str, Any]:
    """Save a pipeline to disk."""
    try:
        # Validate inputs
        if not name or not isinstance(name, str):
            return {
                "success": False,
                "message": "Pipeline name is required and must be a string",
            }
        
        if not steps or not isinstance(steps, list):
            return {
                "success": False,
                "message": "Pipeline steps must be a non-empty list",
            }
        
        # Validate each step has required fields
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                return {
                    "success": False,
                    "message": f"Step {i} must be an object with 'tool', 'action', and 'params'",
                }
            if "tool" not in step:
                return {
                    "success": False,
                    "message": f"Step {i} is missing required 'tool' field",
                }
            if "action" not in step and "params" not in step:
                return {
                    "success": False,
                    "message": f"Step {i} must have either 'action' or 'params' field",
                }
        
        # Get storage location
        pipelines_dir = _get_pipelines_directory()
        
        # Sanitize filename
        safe_name = "".join(c for c in name if c.isalnum() or c in "_-").strip()
        if not safe_name:
            safe_name = "pipeline"
        
        file_path = pipelines_dir / f"{safe_name}.json"
        
        # Check for existing file
        if file_path.exists() and not overwrite:
            return {
                "success": False,
                "message": f"Pipeline '{name}' already exists. Use overwrite=True to replace it.",
                "path": str(file_path),
            }
        
        # Build pipeline document
        pipeline_data = {
            "metadata": {
                "name": name,
                "version": version,
                "created_at": datetime.now().isoformat(),
            },
            "steps": steps,
        }
        
        if description:
            pipeline_data["metadata"]["description"] = description
        if author:
            pipeline_data["metadata"]["author"] = author
        if tags:
            pipeline_data["metadata"]["tags"] = tags
        
        # Write to disk
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(pipeline_data, f, indent=2)
        
        return {
            "success": True,
            "message": f"Pipeline '{name}' saved successfully",
            "path": str(file_path),
            "step_count": len(steps),
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to save pipeline: {str(e)}",
        }
