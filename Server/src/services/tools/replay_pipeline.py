"""Tool for replaying saved pipelines."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


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


def _find_pipeline(name: str) -> tuple[dict[str, Any] | None, Path | None]:
    """Find a pipeline by name across all directories."""
    for pipelines_dir in _get_pipelines_directories():
        file_path = pipelines_dir / f"{name}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f), file_path
            except (json.JSONDecodeError, IOError):
                continue
    return None, None


@mcp_for_unity_tool(
    name="replay_pipeline",
    unity_target=None,
    description=(
        "Execute a saved pipeline (sequence of tool operations). "
        "Replays each step in the pipeline sequentially. "
        "Supports dry-run mode to preview without executing. "
        "Can override parameters at replay time. "
        "Use for automating repetitive workflows and standardizing procedures."
    ),
    annotations=ToolAnnotations(
        title="Replay Pipeline",
        destructiveHint=True,
    ),
    group="pipeline",
)
async def replay_pipeline(
    ctx: Context,
    name: Annotated[str, "Name of the pipeline to replay"],
    parameters: Annotated[dict[str, Any] | None, "Parameter overrides for the pipeline"] = None,
    dry_run: Annotated[bool, "Preview pipeline without executing"] = False,
    stop_on_error: Annotated[bool, "Stop execution if a step fails"] = True,
) -> dict[str, Any]:
    """Replay a saved pipeline."""
    try:
        # Find the pipeline
        pipeline_data, file_path = _find_pipeline(name)
        
        if not pipeline_data:
            return {
                "success": False,
                "message": f"Pipeline '{name}' not found",
            }
        
        steps = pipeline_data.get("steps", [])
        metadata = pipeline_data.get("metadata", {})
        
        if not steps:
            return {
                "success": False,
                "message": f"Pipeline '{name}' has no steps",
            }
        
        # Dry run - just return what would be executed
        if dry_run:
            return {
                "success": True,
                "message": f"Pipeline '{name}' dry run - would execute {len(steps)} step(s)",
                "pipeline_name": metadata.get("name", name),
                "description": metadata.get("description"),
                "steps_preview": [
                    {
                        "step": i + 1,
                        "tool": step.get("tool"),
                        "action": step.get("action"),
                        "params_preview": list(step.get("params", {}).keys()) if step.get("params") else None,
                    }
                    for i, step in enumerate(steps)
                ],
                "parameter_overrides": parameters,
            }
        
        # Execute the pipeline
        unity_instance = await get_unity_instance_from_context(ctx)
        
        results = []
        executed = 0
        failed = 0
        
        for i, step in enumerate(steps):
            step_num = i + 1
            tool_name = step.get("tool")
            action = step.get("action")
            step_params = step.get("params", {})
            
            # Apply parameter overrides
            if parameters:
                step_params = {**step_params, **parameters}
            
            try:
                # Execute the step
                response = await send_with_unity_instance(
                    async_send_command_with_retry,
                    unity_instance,
                    tool_name,
                    {"action": action, **step_params} if action else step_params,
                )
                
                step_result = {
                    "step": step_num,
                    "tool": tool_name,
                    "success": isinstance(response, dict) and response.get("success", True),
                    "response": response if isinstance(response, dict) else {"data": str(response)},
                }
                results.append(step_result)
                executed += 1
                
                if not step_result["success"] and stop_on_error:
                    failed += 1
                    break
                    
            except Exception as e:
                step_result = {
                    "step": step_num,
                    "tool": tool_name,
                    "success": False,
                    "error": str(e),
                }
                results.append(step_result)
                failed += 1
                
                if stop_on_error:
                    break
        
        return {
            "success": failed == 0,
            "message": f"Pipeline '{name}' execution complete: {executed} executed, {failed} failed",
            "executed_steps": executed,
            "failed_steps": failed,
            "total_steps": len(steps),
            "stopped_early": failed > 0 and stop_on_error and executed < len(steps),
            "results": results,
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to replay pipeline: {str(e)}",
        }
