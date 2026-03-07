"""
List and get information about Unity shaders.

Actions:
- list_builtin: List built-in shaders available in Unity
- list_custom: List custom shaders in the project
- get_shader_info: Get detailed information about a specific shader

Helps discover available shaders for materials and understand their properties.
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
        "List and get information about Unity shaders. "
        "Read-only actions: list_builtin, list_custom, get_shader_info. "
        "Helps discover available shaders for materials and understand their properties."
    ),
    annotations=ToolAnnotations(
        title="List Shaders",
        readOnlyHint=True,
    ),
)
async def list_shaders(
    ctx: Context,
    action: Annotated[
        Literal["list_builtin", "list_custom", "get_shader_info"],
        "Action to perform: list_builtin, list_custom, get_shader_info"
    ],
    shader_name: Annotated[
        str | None,
        "Name or path of the shader (required for get_shader_info)"
    ] = None,
    search_pattern: Annotated[
        str | None,
        "Optional search pattern to filter shaders (e.g., 'Standard', 'Sprite', 'UI')"
    ] = None,
    include_properties: Annotated[
        bool,
        "Include shader properties in the output (default: true)"
    ] = True,
    folder_path: Annotated[
        str | None,
        "Limit custom shader search to a specific folder (e.g., 'Assets/Shaders')"
    ] = None,
) -> dict[str, Any]:
    """
    List and get information about Unity shaders.
    
    Shaders are essential for rendering in Unity. This tool helps:
    - Discover built-in shaders (Standard, UI, Sprites, Particles, etc.)
    - Find custom shaders in your project
    - Get detailed information about shader properties and keywords
    
    Common built-in shaders:
    - Standard: PBR shader for most 3D objects
    - Unlit: No lighting calculations, fastest
    - Sprites/Default, Sprites/Mask: For 2D sprites
    - UI/Default, UI/Unlit: For UI elements
    - Particles/Standard: For particle effects
    
    Examples:
    - List all built-in shaders: action="list_builtin"
    - Find UI shaders: action="list_builtin", search_pattern="UI"
    - List custom shaders: action="list_custom", folder_path="Assets/Shaders"
    - Get shader info: action="get_shader_info", shader_name="Standard"
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "list_shaders", action=action)
    if gate is not None:
        return gate.model_dump()
    
    # Validate required parameters
    if action == "get_shader_info" and not shader_name:
        return {
            "success": False,
            "message": "Action 'get_shader_info' requires shader_name parameter."
        }
    
    try:
        params: dict[str, Any] = {
            "action": action,
            "includeProperties": include_properties,
        }
        
        if shader_name:
            params["shaderName"] = shader_name
        if search_pattern:
            params["searchPattern"] = search_pattern
        if folder_path:
            params["folderPath"] = folder_path
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "list_shaders",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Shader listing '{action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error listing shaders: {e!s}"}
