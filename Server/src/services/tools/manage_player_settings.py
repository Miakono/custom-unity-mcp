from __future__ import annotations

"""
Manage Unity Player Settings including company info, product info, version, and resolution.

Actions:
- get_player_settings: Read player settings (company, product, version, etc.)
- set_player_settings: Update player settings
- get_resolution_settings: Resolution and display settings
- set_resolution_settings: Update resolution settings
- get_publishing_settings: Publishing configuration

Safety:
- Changes to player settings may require reimport or rebuild
- Version and bundle identifier changes affect build output
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
        "Manage Unity Player Settings including company info, product info, version, resolution, "
        "and publishing configuration. "
        "Read-only actions: get_player_settings, get_resolution_settings, get_publishing_settings. "
        "Modifying actions: set_player_settings, set_resolution_settings."
    ),
    annotations=ToolAnnotations(
        title="Manage Player Settings",
        destructiveHint=True,
    ),
)
async def manage_player_settings(
    ctx: Context,
    action: Annotated[
        Literal[
            "get_player_settings",
            "get_settings",
            "set_player_settings",
            "set_settings",
            "get_resolution_settings",
            "set_resolution_settings",
            "get_publishing_settings",
            "get_splash_settings",
            "get_icon_settings",
        ],
        "Action to perform: get_player_settings (read general settings), set_player_settings (update settings), "
        "get_resolution_settings (read display settings), set_resolution_settings (update display settings), "
        "get_publishing_settings (read publishing config)"
    ],
    settings: Annotated[
        dict[str, Any] | None,
        "Player settings key-value pairs to update (for set_player_settings/set_resolution_settings actions)"
    ] = None,
    platform: Annotated[
        str | None,
        "Target platform for platform-specific settings (e.g., 'Standalone', 'Android', 'iOS', 'WebGL')"
    ] = None,
    resolution: Annotated[
        dict[str, Any] | None,
        "Alias for a resolution settings payload."
    ] = None,
) -> dict[str, Any]:
    """
    Manage Unity Player Settings and configuration.
    
    This tool provides access to player settings including:
    - General settings: company name, product name, version, bundle identifier
    - Resolution and presentation: default resolution, fullscreen mode, orientation
    - Splash screen and icons
    - Publishing settings
    - Platform-specific settings
    
    Settings Categories:
    - General: companyName, productName, bundleVersion, bundleIdentifier
    - Resolution: defaultResolution, fullscreenMode, resizableWindow, allowFullscreenSwitch
    - Splash: showUnitySplashScreen, splashScreenStyle, splashScreenLogos
    - Icon: icons (platform-specific icon arrays)
    
    Safety Notes:
    - Changes to bundle identifier or version may affect app store submissions
    - Resolution settings affect runtime behavior
    - Some settings are platform-specific and require the platform parameter
    
    Examples:
    - Get general settings: action="get_player_settings"
    - Get Android settings: action="get_player_settings", platform="Android"
    - Update version: action="set_player_settings", settings={"bundleVersion": "1.2.0"}
    - Get resolution settings: action="get_resolution_settings"
    - Set resolution: action="set_resolution_settings", settings={"defaultResolution": "1920x1080"}
    - Get publishing settings: action="get_publishing_settings"
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "manage_player_settings", action=action)
    if gate is not None:
        return gate.model_dump()
    
    try:
        action_aliases = {
            "get_settings": "get_player_settings",
            "set_settings": "set_player_settings",
        }
        resolved_action = action_aliases.get(action, action)
        params: dict[str, Any] = {"action": resolved_action}
        
        effective_settings = settings or resolution
        if effective_settings:
            params["settings"] = effective_settings
        if platform:
            params["platform"] = platform
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_player_settings",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Player settings operation '{resolved_action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error managing player settings: {e!s}"}
