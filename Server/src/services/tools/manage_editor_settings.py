"""
Manage Unity Editor preferences and settings.

Actions:
- get_preferences: Read editor preferences
- update_preferences: Update preferences (safe ones only)

Provides access to editor preferences that are safe to modify programmatically.
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
        "Manage Unity Editor preferences and settings. "
        "Read-only actions: get_preferences. "
        "Modifying actions: update_preferences (safe settings only). "
        "Provides access to editor preferences that can be safely read and modified."
    ),
    annotations=ToolAnnotations(
        title="Manage Editor Settings",
        destructiveHint=False,
    ),
)
async def manage_editor_settings(
    ctx: Context,
    action: Annotated[
        Literal["get_preferences", "update_preferences"],
        "Action to perform: get_preferences (read settings), update_preferences (modify safe settings)"
    ],
    preference_category: Annotated[
        str | None,
        "Category of preferences to read/update (e.g., 'general', 'external_tools', 'colors', 'scene_view')"
    ] = None,
    preferences: Annotated[
        dict[str, Any] | None,
        "Preference key-value pairs to update (for update_preferences action)"
    ] = None,
) -> dict[str, Any]:
    """
    Manage Unity Editor preferences and settings.
    
    This tool provides access to editor preferences that are safe to read and modify:
    - General preferences (auto-save, auto-refresh, etc.)
    - External Tools preferences
    - Color preferences
    - Scene View preferences
    - And other safe editor settings
    
    Note: Only safe, non-destructive preferences can be modified. Critical settings
    that could break the editor are read-only.
    
    Examples:
    - Get all preferences: action="get_preferences"
    - Get specific category: action="get_preferences", preference_category="general"
    - Update preferences: action="update_preferences", preference_category="general",
      preferences={"autoRefresh": true}
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "manage_editor_settings", action=action)
    if gate is not None:
        return gate.model_dump()
    
    try:
        params: dict[str, Any] = {"action": action}
        
        if preference_category:
            params["preferenceCategory"] = preference_category
        if preferences:
            params["preferences"] = preferences
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_editor_settings",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Editor settings operation '{action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error managing editor settings: {e!s}"}
