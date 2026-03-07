"""
Find and search Unity built-in assets.

Actions:
- search: Search built-in assets by name/type
- list_by_type: List assets of a specific type (textures, meshes, materials, etc.)

Unity includes many built-in assets that can be useful:
- Default materials and textures
- Primitive meshes (cube, sphere, cylinder, etc.)
- Built-in editor textures and icons
- Default shaders and materials
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
        "Find and search Unity built-in assets. "
        "Read-only actions: search, list_by_type. "
        "Find built-in textures, meshes, materials, and other default assets."
    ),
    annotations=ToolAnnotations(
        title="Find Built-in Assets",
        readOnlyHint=True,
    ),
)
async def find_builtin_assets(
    ctx: Context,
    action: Annotated[
        Literal["search", "list_by_type"],
        "Action to perform: search (by name/pattern), list_by_type (filter by asset type)"
    ],
    search_pattern: Annotated[
        str | None,
        "Name or pattern to search for (e.g., 'Default', 'Sprite', 'Quad')"
    ] = None,
    asset_type: Annotated[
        str | None,
        "Type of built-in asset to find (texture, mesh, material, shader, sprite, font, etc.)"
    ] = None,
    max_results: Annotated[
        int,
        "Maximum number of results to return (default: 50)"
    ] = 50,
    include_preview: Annotated[
        bool,
        "Include preview/thumbnail information (default: false)"
    ] = False,
) -> dict[str, Any]:
    """
    Find and search Unity built-in assets.
    
    Unity provides many built-in assets that are useful for prototyping and
    sometimes for production:
    
    Textures:
    - Default textures (white, black, normal maps)
    - Editor UI textures and icons
    - Built-in particle textures
    
    Meshes:
    - Primitives: Cube, Sphere, Cylinder, Capsule, Plane, Quad
    - Default models and reference meshes
    
    Materials:
    - Default materials for different purposes
    - Built-in sprite and UI materials
    
    Examples:
    - Search for defaults: action="search", search_pattern="Default"
    - List all meshes: action="list_by_type", asset_type="mesh"
    - Find textures: action="list_by_type", asset_type="texture", max_results=20
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "find_builtin_assets", action=action)
    if gate is not None:
        return gate.model_dump()
    
    try:
        params: dict[str, Any] = {
            "action": action,
            "maxResults": max(max_results, 1),
            "includePreview": include_preview,
        }
        
        if search_pattern:
            params["searchPattern"] = search_pattern
        if asset_type:
            params["assetType"] = asset_type
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "find_builtin_assets",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Built-in asset search '{action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error finding built-in assets: {e!s}"}
