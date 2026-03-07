"""Tool for recording editor actions into a pipeline."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool


# In-memory storage for recording state
_recording_state: dict[str, Any] = {
    "is_recording": False,
    "recording_start_time": None,
    "recorded_actions": [],
    "pipeline_name": None,
    "pipeline_description": None,
    "filter": None,
}

# Storage for recorded pipelines
_pipeline_drafts: dict[str, dict[str, Any]] = {}


def _get_recording_session_file() -> Path:
    """Get the file path for the current recording session."""
    user_config = Path.home() / ".unity-mcp" / "recordings"
    user_config.mkdir(parents=True, exist_ok=True)
    return user_config / "current_session.json"


@mcp_for_unity_tool(
    name="record_pipeline",
    unity_target=None,
    description=(
        "Start recording editor actions into a pipeline or get recording status. "
        "Records MCP tool calls made during the session for later replay. "
        "Use stop_pipeline_recording to finish and save. "
        "Note: Recording captures tool calls at the MCP server level, not Unity editor UI interactions."
    ),
    annotations=ToolAnnotations(
        title="Record Pipeline",
        destructiveHint=False,
    ),
    group="pipeline",
)
async def record_pipeline(
    ctx: Context,
    action: Annotated[
        Literal["start", "status"],
        "Action to perform: 'start' recording or get 'status'"
    ] = "status",
    name: Annotated[str | None, "Pipeline name (required for 'start' action)"] = None,
    description: Annotated[str | None, "Optional pipeline description"] = None,
    filter: Annotated[list[str] | None, "Which action types to record (e.g., ['manage_gameobject', 'manage_components'])"] = None,
) -> dict[str, Any]:
    """Start recording or get recording status."""
    global _recording_state
    
    try:
        if action == "start":
            if not name:
                return {
                    "success": False,
                    "message": "Pipeline name is required to start recording",
                }
            
            # Check if already recording
            if _recording_state["is_recording"]:
                return {
                    "success": False,
                    "message": f"Already recording pipeline '{_recording_state['pipeline_name']}'. Use stop_pipeline_recording first.",
                    "current_recording": {
                        "name": _recording_state["pipeline_name"],
                        "started_at": _recording_state["recording_start_time"],
                        "actions_recorded": len(_recording_state["recorded_actions"]),
                    },
                }
            
            # Start new recording
            _recording_state = {
                "is_recording": True,
                "recording_start_time": time.time(),
                "recorded_actions": [],
                "pipeline_name": name,
                "pipeline_description": description,
                "filter": filter or [],
            }
            
            # Save session to disk for persistence
            session_file = _get_recording_session_file()
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump({
                    "is_recording": True,
                    "pipeline_name": name,
                    "pipeline_description": description,
                    "filter": filter or [],
                    "started_at": _recording_state["recording_start_time"],
                }, f, indent=2)
            
            return {
                "success": True,
                "message": f"Started recording pipeline '{name}'",
                "pipeline_name": name,
                "description": description,
                "filter": filter or [],
                "note": "Recording captures MCP tool calls. Not all editor actions may be recorded.",
            }
        
        else:  # status action
            if _recording_state["is_recording"]:
                duration = time.time() - _recording_state["recording_start_time"]
                return {
                    "success": True,
                    "message": f"Currently recording pipeline '{_recording_state['pipeline_name']}'",
                    "status": "recording",
                    "pipeline_name": _recording_state["pipeline_name"],
                    "description": _recording_state["pipeline_description"],
                    "duration_seconds": round(duration, 1),
                    "actions_recorded": len(_recording_state["recorded_actions"]),
                    "filter": _recording_state["filter"],
                }
            else:
                # Check for saved session
                session_file = _get_recording_session_file()
                if session_file.exists():
                    try:
                        with open(session_file, "r", encoding="utf-8") as f:
                            saved_session = json.load(f)
                        
                        if saved_session.get("is_recording"):
                            return {
                                "success": True,
                                "message": "Found saved recording session (but not active in memory)",
                                "status": "saved_session",
                                "saved_session": saved_session,
                            }
                    except (json.JSONDecodeError, IOError):
                        pass
                
                return {
                    "success": True,
                    "message": "Not currently recording",
                    "status": "idle",
                }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to manage recording: {str(e)}",
        }


def record_action(tool_name: str, action_params: dict[str, Any]) -> None:
    """Record an action during pipeline recording.
    
    This function is called by the middleware to record tool calls.
    """
    global _recording_state
    
    if not _recording_state["is_recording"]:
        return
    
    # Apply filter if specified
    filter_list = _recording_state.get("filter", [])
    if filter_list and tool_name not in filter_list:
        return
    
    # Record the action
    recorded_action = {
        "tool": tool_name,
        "timestamp": time.time(),
    }
    
    # Extract action and params
    if "action" in action_params:
        recorded_action["action"] = action_params["action"]
        recorded_action["params"] = {k: v for k, v in action_params.items() if k != "action"}
    else:
        recorded_action["params"] = action_params
    
    _recording_state["recorded_actions"].append(recorded_action)
    
    # Update session file with action count
    try:
        session_file = _get_recording_session_file()
        if session_file.exists():
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            session_data["actions_recorded"] = len(_recording_state["recorded_actions"])
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2)
    except Exception:
        pass


def get_recording_state() -> dict[str, Any]:
    """Get the current recording state."""
    return _recording_state.copy()
