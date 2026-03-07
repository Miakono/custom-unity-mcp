from __future__ import annotations

"""
Manage Unity Build Settings including scenes, target platform, and build configuration.

Actions:
- get_build_settings: Read current build configuration
- set_build_settings: Update build settings
- add_scene_to_build: Add scene to build list
- remove_scene_from_build: Remove scene from build
- set_build_platform: Switch target platform
- get_scenes_in_build: List scenes in build

Safety:
- Platform switching requires explicit confirmation (high-risk operation)
- Scene modifications are gated by preflight checks
"""
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    group="pipeline_control",
    description=(
        "Manage Unity Build Settings including scenes, target platform, and build configuration. "
        "Read-only actions: get_build_settings, get_scenes_in_build. "
        "Modifying actions: set_build_settings, add_scene_to_build, remove_scene_from_build, "
        "set_build_platform (high-risk). Platform switching requires explicit confirmation."
    ),
    annotations=ToolAnnotations(
        title="Manage Build Settings",
        destructiveHint=True,
    ),
)
async def manage_build_settings(
    ctx: Context,
    action: Annotated[
        Literal[
            "get_build_settings",
            "set_build_settings",
            "add_scene_to_build",
            "remove_scene_from_build",
            "set_build_platform",
            "get_scenes_in_build",
        ],
        "Action to perform: get_build_settings (read config), set_build_settings (update config), "
        "add_scene_to_build (add scene), remove_scene_from_build (remove scene), "
        "set_build_platform (switch platform - high-risk), get_scenes_in_build (list scenes)"
    ],
    scene_path: Annotated[
        str | None,
        "Path to the scene asset (for add_scene_to_build/remove_scene_from_build actions)"
    ] = None,
    scene_enabled: Annotated[
        bool | None,
        "Whether the scene should be enabled in the build (for add_scene_to_build action)"
    ] = None,
    settings: Annotated[
        dict[str, Any] | None,
        "Build settings key-value pairs to update (for set_build_settings action)"
    ] = None,
    target_platform: Annotated[
        str | None,
        "Target platform to switch to (for set_build_platform action). "
        "Examples: 'StandaloneWindows64', 'Android', 'iOS', 'WebGL', 'StandaloneOSX', 'StandaloneLinux64'"
    ] = None,
    output_path: Annotated[
        str | None,
        "Build output path (for set_build_settings action)"
    ] = None,
) -> dict[str, Any]:
    """
    Manage Unity Build Settings and build configuration.
    
    This tool provides comprehensive control over Unity's build settings:
    - Scene management (add/remove scenes from build list)
    - Platform switching (Standalone, Mobile, WebGL, etc.)
    - Build options and configuration
    
    Safety Notes:
    - Platform switching is a high-risk operation that may trigger lengthy reimporting
    - Always use get_build_settings first to understand current configuration
    - Scene paths are relative to the project Assets folder (e.g., "Assets/Scenes/MainScene.unity")
    
    Examples:
    - Get current build settings: action="get_build_settings"
    - List scenes in build: action="get_scenes_in_build"
    - Add scene to build: action="add_scene_to_build", scene_path="Assets/Scenes/Level1.unity", scene_enabled=True
    - Remove scene: action="remove_scene_from_build", scene_path="Assets/Scenes/OldScene.unity"
    - Switch platform: action="set_build_platform", target_platform="Android"
    - Update settings: action="set_build_settings", settings={"developmentBuild": true}
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "manage_build_settings", action=action)
    if gate is not None:
        return gate.model_dump()
    
    try:
        params: dict[str, Any] = {"action": action}
        
        if scene_path:
            params["scenePath"] = scene_path
        if scene_enabled is not None:
            params["sceneEnabled"] = scene_enabled
        if settings:
            params["settings"] = settings
        if target_platform:
            params["targetPlatform"] = target_platform
        if output_path:
            params["outputPath"] = output_path
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_build_settings",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Build settings operation '{action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error managing build settings: {e!s}"}
