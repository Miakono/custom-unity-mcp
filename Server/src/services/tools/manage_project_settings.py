"""
Manage Unity project settings including Player Settings, Build Settings,
and other project-wide configurations.

Actions:
- get_settings: Read project settings (Player Settings, etc.)
- update_settings: Update project settings
- get_build_settings: Read build configuration
- update_build_settings: Update build configuration
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
    group="project_config",
    description=(
        "Manage Unity project settings and build configuration. "
        "Read-only actions: get_settings, get_build_settings. "
        "Modifying actions: update_settings, update_build_settings. "
        "Provides access to Player Settings, project metadata, and build configuration."
    ),
    annotations=ToolAnnotations(
        title="Manage Project Settings",
        destructiveHint=True,
    ),
)
async def manage_project_settings(
    ctx: Context,
    action: Annotated[
        Literal["get_settings", "update_settings", "get_build_settings", "update_build_settings"],
        "Action to perform: get_settings (read project settings), update_settings (modify settings), "
        "get_build_settings (read build config), update_build_settings (modify build config)"
    ],
    settings_category: Annotated[
        str | None,
        "Category of settings to read/update (e.g., 'player', 'audio', 'physics', 'graphics', 'time', 'input')"
    ] = None,
    settings: Annotated[
        dict[str, Any] | None,
        "Settings key-value pairs to update (for update_settings/update_build_settings actions)"
    ] = None,
    platform: Annotated[
        str | None,
        "Target platform for build settings (e.g., 'StandaloneWindows64', 'Android', 'iOS', 'WebGL')"
    ] = None,
) -> dict[str, Any]:
    """
    Manage Unity project settings and build configuration.
    
    This tool provides access to:
    - Player Settings (company name, product name, version, icons, etc.)
    - Build Settings (scenes in build, target platform, build options)
    - Other project-wide settings (audio, physics, graphics, etc.)
    
    Examples:
    - Get player settings: action="get_settings", settings_category="player"
    - Get build settings: action="get_build_settings"
    - Update player settings: action="update_settings", settings_category="player", 
      settings={"companyName": "My Company", "productName": "My Game"}
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "manage_project_settings", action=action)
    if gate is not None:
        return gate.model_dump()
    
    try:
        params: dict[str, Any] = {"action": action}
        
        if settings_category:
            params["settingsCategory"] = settings_category
        if settings:
            params["settings"] = settings
        if platform:
            params["platform"] = platform
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_project_settings",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Project settings operation '{action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error managing project settings: {e!s}"}
