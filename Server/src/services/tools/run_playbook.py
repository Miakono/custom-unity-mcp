"""Tool for executing playbooks."""
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


# Built-in playbook templates directory
BUILT_IN_PLAYBOOKS_DIR = Path(__file__).parent / "playbooks"


def _ensure_built_in_playbooks() -> None:
    try:
        from services.tools import create_playbook as cp_module

        cp_module._ensure_built_in_playbooks()
    except Exception:
        pass


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


def _apply_parameter_overrides(
    steps: list[dict[str, Any]],
    parameters: dict[str, Any] | None,
    playbook_params: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Apply parameter overrides to playbook steps."""
    if not parameters:
        return steps
    
    # Merge with playbook parameter defaults
    effective_params = {}
    if playbook_params:
        for key, param_def in playbook_params.items():
            if isinstance(param_def, dict):
                effective_params[key] = param_def.get("default")
            else:
                effective_params[key] = param_def
    
    # Apply user overrides
    effective_params.update(parameters)
    
    # Deep copy steps and apply parameter substitution
    import copy
    processed_steps = copy.deepcopy(steps)
    
    def substitute_params(obj: Any) -> Any:
        """Recursively substitute parameter placeholders."""
        if isinstance(obj, str):
            # Simple placeholder substitution: {{param_name}}
            result = obj
            for key, value in effective_params.items():
                placeholder = f"{{{{{key}}}}}"
                if placeholder in result:
                    result = result.replace(placeholder, str(value))
            return result
        elif isinstance(obj, list):
            return [substitute_params(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: substitute_params(v) for k, v in obj.items()}
        return obj
    
    return substitute_params(processed_steps)


@mcp_for_unity_tool(
    name="run_playbook",
    unity_target=None,
    description=(
        "Execute a playbook (reusable template for Unity workflows). "
        "Playbooks contain predefined steps that automate common tasks. "
        "Built-in playbooks: basic_player_controller, ui_canvas_setup, scene_lighting_setup. "
        "Supports parameter overrides for customization."
    ),
    annotations=ToolAnnotations(
        title="Run Playbook",
        destructiveHint=True,
    ),
    group="pipeline",
)
async def run_playbook(
    ctx: Context,
    playbook_id: Annotated[str, "ID/name of the playbook to execute"],
    context: Annotated[dict[str, Any] | None, "Context variables and parameter overrides"] = None,
    dry_run: Annotated[bool, "Preview playbook without executing"] = False,
    stop_on_error: Annotated[bool, "Stop execution if a step fails"] = True,
) -> dict[str, Any]:
    """Execute a playbook."""
    try:
        # Find the playbook
        playbook_data, file_path = _find_playbook(playbook_id)
        
        if not playbook_data:
            return {
                "success": False,
                "message": f"Playbook '{playbook_id}' not found. Use list_playbooks to see available playbooks.",
            }
        
        metadata = playbook_data.get("metadata", {})
        steps = playbook_data.get("steps", [])
        playbook_params = playbook_data.get("parameters", {})
        
        if not steps:
            return {
                "success": False,
                "message": f"Playbook '{playbook_id}' has no steps",
            }
        
        # Get parameter overrides from context
        parameters = context.get("parameters", {}) if context else None
        
        # Apply parameter overrides and substitution
        processed_steps = _apply_parameter_overrides(steps, parameters, playbook_params)
        
        # Dry run - just return what would be executed
        if dry_run:
            return {
                "success": True,
                "message": f"Playbook '{playbook_id}' dry run - would execute {len(steps)} step(s)",
                "playbook_name": metadata.get("name", playbook_id),
                "description": metadata.get("description"),
                "steps_preview": [
                    {
                        "step": i + 1,
                        "tool": step.get("tool"),
                        "action": step.get("action"),
                        "params_preview": list(step.get("params", {}).keys()) if step.get("params") else None,
                    }
                    for i, step in enumerate(processed_steps)
                ],
                "parameter_overrides": parameters,
                "available_parameters": list(playbook_params.keys()) if playbook_params else None,
            }
        
        # Execute the playbook
        unity_instance = await get_unity_instance_from_context(ctx)
        
        results = []
        executed = 0
        failed = 0
        
        for i, step in enumerate(processed_steps):
            step_num = i + 1
            tool_name = step.get("tool")
            action = step.get("action")
            step_params = step.get("params", {})
            
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
            "message": f"Playbook '{playbook_id}' execution complete: {executed} executed, {failed} failed",
            "executed_steps": executed,
            "failed_steps": failed,
            "total_steps": len(steps),
            "stopped_early": failed > 0 and stop_on_error and executed < len(steps),
            "results": results,
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to run playbook: {str(e)}",
        }
