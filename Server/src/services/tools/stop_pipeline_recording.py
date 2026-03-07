"""Tool for stopping pipeline recording and saving/discard results."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool


# Import recording state from record_pipeline
def _get_recording_state():
    """Get recording state from record_pipeline module."""
    from services.tools.record_pipeline import get_recording_state
    return get_recording_state()


def _clear_recording_state():
    """Clear the recording state."""
    import services.tools.record_pipeline as rp_module
    rp_module._recording_state = {
        "is_recording": False,
        "recording_start_time": None,
        "recorded_actions": [],
        "pipeline_name": None,
        "pipeline_description": None,
        "filter": None,
    }
    
    # Clear session file
    try:
        session_file = Path.home() / ".unity-mcp" / "recordings" / "current_session.json"
        if session_file.exists():
            session_file.unlink()
    except Exception:
        pass


def _get_pipelines_directory() -> Path:
    """Get the directory for storing pipelines."""
    project_root = Path.cwd()
    potential_roots = [
        project_root,
        project_root.parent,
        project_root.parent.parent,
    ]
    
    for root in potential_roots:
        if (root / "Assets").exists() or (root / "ProjectSettings").exists():
            project_pipelines = root / "Pipelines"
            project_pipelines.mkdir(parents=True, exist_ok=True)
            return project_pipelines
    
    # Fallback to user config
    user_config = Path.home() / ".unity-mcp" / "pipelines"
    user_config.mkdir(parents=True, exist_ok=True)
    return user_config


@mcp_for_unity_tool(
    name="stop_pipeline_recording",
    unity_target=None,
    description=(
        "Stop recording a pipeline and optionally save the results. "
        "Returns the recorded actions for review. "
        "Use 'save' action to persist, 'discard' to cancel without saving. "
        "Saved pipelines can be replayed with replay_pipeline."
    ),
    annotations=ToolAnnotations(
        title="Stop Pipeline Recording",
        destructiveHint=True,
    ),
    group="pipeline",
)
async def stop_pipeline_recording(
    ctx: Context,
    action: Annotated[
        Literal["stop", "discard"],
        "Action to perform: 'stop' and return/save recording, or 'discard' to cancel"
    ] = "stop",
    save: Annotated[bool, "Whether to save the recorded pipeline to disk"] = True,
    path: Annotated[str | None, "Custom path to save the pipeline (optional)"] = None,
    author: Annotated[str | None, "Pipeline author metadata"] = None,
    tags: Annotated[list[str] | None, "Tags for the pipeline"] = None,
) -> dict[str, Any]:
    """Stop recording and optionally save the pipeline."""
    try:
        # Get current recording state
        from services.tools.record_pipeline import get_recording_state
        recording_state = get_recording_state()
        
        if not recording_state["is_recording"]:
            return {
                "success": False,
                "message": "Not currently recording a pipeline",
            }
        
        recorded_actions = recording_state["recorded_actions"]
        pipeline_name = recording_state["pipeline_name"]
        pipeline_description = recording_state["pipeline_description"]
        duration = time.time() - recording_state["recording_start_time"]
        
        if action == "discard":
            _clear_recording_state()
            return {
                "success": True,
                "message": "Recording discarded",
                "actions_discarded": len(recorded_actions),
                "duration_seconds": round(duration, 1),
            }
        
        # Stop action - prepare the pipeline data
        if not recorded_actions:
            _clear_recording_state()
            return {
                "success": False,
                "message": "No actions were recorded",
                "pipeline_name": pipeline_name,
            }
        
        # Convert recorded actions to pipeline steps
        steps = []
        for action_data in recorded_actions:
            step = {
                "tool": action_data["tool"],
            }
            if "action" in action_data:
                step["action"] = action_data["action"]
            if "params" in action_data:
                step["params"] = action_data["params"]
            steps.append(step)
        
        pipeline_data = {
            "metadata": {
                "name": pipeline_name,
                "version": "1.0",
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "recording_duration_seconds": round(duration, 1),
                "recorded_actions_count": len(recorded_actions),
            },
            "steps": steps,
        }
        
        if pipeline_description:
            pipeline_data["metadata"]["description"] = pipeline_description
        if author:
            pipeline_data["metadata"]["author"] = author
        if tags:
            pipeline_data["metadata"]["tags"] = tags
        
        result = {
            "success": True,
            "message": f"Recording stopped. Captured {len(steps)} step(s).",
            "pipeline_name": pipeline_name,
            "duration_seconds": round(duration, 1),
            "steps_captured": len(steps),
            "pipeline_preview": pipeline_data,
        }
        
        # Save to disk if requested
        if save:
            if path:
                save_path = Path(path)
            else:
                # Use default location
                pipelines_dir = _get_pipelines_directory()
                safe_name = "".join(c for c in pipeline_name if c.isalnum() or c in "_-").strip()
                if not safe_name:
                    safe_name = "recorded_pipeline"
                save_path = pipelines_dir / f"{safe_name}.json"
            
            # Ensure parent directory exists
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(pipeline_data, f, indent=2)
            
            result["saved"] = True
            result["saved_path"] = str(save_path)
            result["message"] = f"Recording saved to {save_path}"
        else:
            result["saved"] = False
        
        # Clear recording state
        _clear_recording_state()
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to stop recording: {str(e)}",
        }
