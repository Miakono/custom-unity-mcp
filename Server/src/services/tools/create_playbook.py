"""Tool for creating playbooks from pipelines or step definitions."""
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
    """Ensure built-in playbooks directory and templates exist."""
    BUILT_IN_PLAYBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create built-in playbooks if they don't exist
    _create_basic_player_controller_playbook()
    _create_ui_canvas_setup_playbook()
    _create_scene_lighting_setup_playbook()


def _create_basic_player_controller_playbook():
    """Create the basic_player_controller playbook."""
    playbook_path = BUILT_IN_PLAYBOOKS_DIR / "basic_player_controller.json"
    if playbook_path.exists():
        return
    
    playbook = {
        "metadata": {
            "name": "basic_player_controller",
            "description": "Creates a player GameObject with movement script and basic setup",
            "version": "1.0",
            "author": "unity-mcp",
            "tags": ["player", "controller", "movement", "starter"],
            "category": "gameplay",
        },
        "steps": [
            {
                "tool": "manage_gameobject",
                "action": "create",
                "params": {
                    "name": "Player",
                    "primitive": "Capsule",
                    "position": [0, 1, 0],
                },
            },
            {
                "tool": "manage_components",
                "action": "add",
                "params": {
                    "target": "Player",
                    "components": ["CharacterController"],
                },
            },
            {
                "tool": "manage_script",
                "action": "create",
                "params": {
                    "name": "PlayerMovement",
                    "template": "MonoBehaviour",
                    "content": '''using UnityEngine;

[RequireComponent(typeof(CharacterController))]
public class PlayerMovement : MonoBehaviour
{
    public float moveSpeed = 5f;
    public float rotationSpeed = 10f;
    private CharacterController controller;
    
    void Start()
    {
        controller = GetComponent<CharacterController>();
    }
    
    void Update()
    {
        float horizontal = Input.GetAxis("Horizontal");
        float vertical = Input.GetAxis("Vertical");
        
        Vector3 movement = new Vector3(horizontal, 0f, vertical);
        
        if (movement.magnitude > 0)
        {
            movement.Normalize();
            controller.Move(movement * moveSpeed * Time.deltaTime);
            
            Quaternion targetRotation = Quaternion.LookRotation(movement);
            transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, rotationSpeed * Time.deltaTime);
        }
    }
}''',
                },
            },
            {
                "tool": "manage_components",
                "action": "add",
                "params": {
                    "target": "Player",
                    "components": ["PlayerMovement"],
                },
            },
        ],
        "parameters": {
            "player_name": {
                "description": "Name of the player GameObject",
                "default": "Player",
                "type": "string",
            },
            "move_speed": {
                "description": "Player movement speed",
                "default": 5.0,
                "type": "float",
            },
        },
    }
    
    with open(playbook_path, "w", encoding="utf-8") as f:
        json.dump(playbook, f, indent=2)


def _create_ui_canvas_setup_playbook():
    """Create the ui_canvas_setup playbook."""
    playbook_path = BUILT_IN_PLAYBOOKS_DIR / "ui_canvas_setup.json"
    if playbook_path.exists():
        return
    
    playbook = {
        "metadata": {
            "name": "ui_canvas_setup",
            "description": "Creates a canvas with event system for UI",
            "version": "1.0",
            "author": "unity-mcp",
            "tags": ["ui", "canvas", "event-system", "starter"],
            "category": "ui",
        },
        "steps": [
            {
                "tool": "manage_gameobject",
                "action": "create",
                "params": {
                    "name": "Canvas",
                },
            },
            {
                "tool": "manage_ui",
                "action": "setup_canvas",
                "params": {
                    "target": "Canvas",
                    "render_mode": "ScreenSpaceOverlay",
                },
            },
            {
                "tool": "manage_gameobject",
                "action": "create",
                "params": {
                    "name": "EventSystem",
                },
            },
            {
                "tool": "manage_components",
                "action": "add",
                "params": {
                    "target": "EventSystem",
                    "components": ["EventSystem", "StandaloneInputModule"],
                },
            },
        ],
        "parameters": {
            "canvas_name": {
                "description": "Name of the canvas GameObject",
                "default": "Canvas",
                "type": "string",
            },
            "render_mode": {
                "description": "Canvas render mode (ScreenSpaceOverlay, ScreenSpaceCamera, WorldSpace)",
                "default": "ScreenSpaceOverlay",
                "type": "string",
            },
        },
    }
    
    with open(playbook_path, "w", encoding="utf-8") as f:
        json.dump(playbook, f, indent=2)


def _create_scene_lighting_setup_playbook():
    """Create the scene_lighting_setup playbook."""
    playbook_path = BUILT_IN_PLAYBOOKS_DIR / "scene_lighting_setup.json"
    if playbook_path.exists():
        return
    
    playbook = {
        "metadata": {
            "name": "scene_lighting_setup",
            "description": "Sets up basic scene lighting with directional light and ambient",
            "version": "1.0",
            "author": "unity-mcp",
            "tags": ["lighting", "directional-light", "ambient", "starter"],
            "category": "lighting",
        },
        "steps": [
            {
                "tool": "manage_gameobject",
                "action": "create",
                "params": {
                    "name": "Directional Light",
                },
            },
            {
                "tool": "manage_components",
                "action": "add",
                "params": {
                    "target": "Directional Light",
                    "components": ["Light"],
                },
            },
            {
                "tool": "manage_gameobject",
                "action": "modify",
                "params": {
                    "target": "Directional Light",
                    "rotation": [50, -30, 0],
                },
            },
            {
                "tool": "manage_project_settings",
                "action": "set",
                "params": {
                    "category": "rendering",
                    "ambient_mode": "Gradient",
                    "ambient_sky_color": [0.2, 0.4, 0.8],
                    "ambient_equator_color": [0.4, 0.4, 0.4],
                    "ambient_ground_color": [0.1, 0.1, 0.1],
                },
            },
        ],
        "parameters": {
            "light_rotation": {
                "description": "Directional light rotation as [x, y, z] euler angles",
                "default": [50, -30, 0],
                "type": "vector3",
            },
            "light_intensity": {
                "description": "Directional light intensity",
                "default": 1.0,
                "type": "float",
            },
        },
    }
    
    with open(playbook_path, "w", encoding="utf-8") as f:
        json.dump(playbook, f, indent=2)


@mcp_for_unity_tool(
    name="create_playbook",
    unity_target=None,
    description=(
        "Create a playbook from a pipeline or step definitions. "
        "Playbooks are reusable templates for common Unity workflows. "
        "Can create from existing pipelines or define steps directly. "
        "Built-in playbooks: basic_player_controller, ui_canvas_setup, scene_lighting_setup"
    ),
    annotations=ToolAnnotations(
        title="Create Playbook",
        destructiveHint=False,
    ),
    group="pipeline",
)
async def create_playbook(
    ctx: Context,
    action: Annotated[
        Literal["from_pipeline", "from_steps"],
        "How to create the playbook: from an existing pipeline or from step definitions"
    ],
    name: Annotated[str, "Playbook name"],
    description: Annotated[str | None, "Playbook description"] = None,
    # For from_pipeline action
    pipeline_name: Annotated[str | None, "Source pipeline name (for from_pipeline)"] = None,
    # For from_steps action
    steps: Annotated[list[dict[str, Any]] | None, "Step definitions (for from_steps)"] = None,
    # Common parameters
    category: Annotated[str, "Playbook category (e.g., 'ui', 'gameplay', 'lighting')"] = "general",
    tags: Annotated[list[str] | None, "Tags for the playbook"] = None,
    parameters: Annotated[dict[str, Any] | None, "Parameter definitions for the playbook"] = None,
    overwrite: Annotated[bool, "Overwrite existing playbook"] = False,
) -> dict[str, Any]:
    """Create a playbook from a pipeline or step definitions."""
    try:
        _ensure_built_in_playbooks()
        
        # Determine target path
        playbook_path = BUILT_IN_PLAYBOOKS_DIR / f"{name}.json"
        
        # Check for existing
        if playbook_path.exists() and not overwrite:
            return {
                "success": False,
                "message": f"Playbook '{name}' already exists. Use overwrite=True to replace.",
            }
        
        if action == "from_pipeline":
            if not pipeline_name:
                return {
                    "success": False,
                    "message": "pipeline_name is required for from_pipeline action",
                }
            
            # Import here to avoid circular dependency
            from services.tools.list_pipelines import _get_pipelines_directories
            
            # Find the pipeline
            pipeline_data = None
            for pipelines_dir in _get_pipelines_directories():
                file_path = pipelines_dir / f"{pipeline_name}.json"
                if file_path.exists():
                    with open(file_path, "r", encoding="utf-8") as f:
                        pipeline_data = json.load(f)
                    break
            
            if not pipeline_data:
                return {
                    "success": False,
                    "message": f"Pipeline '{pipeline_name}' not found",
                }
            
            # Create playbook from pipeline
            playbook = {
                "metadata": {
                    "name": name,
                    "description": description or pipeline_data.get("metadata", {}).get("description", ""),
                    "version": "1.0",
                    "author": pipeline_data.get("metadata", {}).get("author", "unknown"),
                    "tags": tags or pipeline_data.get("metadata", {}).get("tags", []),
                    "category": category,
                },
                "steps": pipeline_data.get("steps", []),
            }
            
            if parameters:
                playbook["parameters"] = parameters
        
        elif action == "from_steps":
            if not steps:
                return {
                    "success": False,
                    "message": "steps are required for from_steps action",
                }
            
            playbook = {
                "metadata": {
                    "name": name,
                    "description": description or "",
                    "version": "1.0",
                    "author": "custom",
                    "tags": tags or [],
                    "category": category,
                },
                "steps": steps,
            }
            
            if parameters:
                playbook["parameters"] = parameters
        
        else:
            return {
                "success": False,
                "message": f"Unknown action: {action}",
            }
        
        # Write playbook
        with open(playbook_path, "w", encoding="utf-8") as f:
            json.dump(playbook, f, indent=2)
        
        return {
            "success": True,
            "message": f"Playbook '{name}' created successfully",
            "path": str(playbook_path),
            "step_count": len(playbook["steps"]),
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create playbook: {str(e)}",
        }
