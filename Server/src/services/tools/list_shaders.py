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
        "Helps discover available shaders for materials and understand their properties. "
        "Defaults to a small page (50) and properties-off to keep payloads bounded; "
        "use summary_only=true for just counts and category breakdown when you don't "
        "need the full list."
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
        "Include shader properties in the output. Default: false (much smaller payload). "
        "Set true only when you need the property list for a specific shader."
    ] = False,
    folder_path: Annotated[
        str | None,
        "Limit custom shader search to a specific folder (e.g., 'Assets/Shaders')"
    ] = None,
    max_results: Annotated[
        int,
        "Max shaders returned for list actions. Default 50 (caps payload). "
        "Set 0 for unlimited, or use summary_only=true for just counts."
    ] = 50,
    offset: Annotated[
        int,
        "Number of results to skip (for paging through long lists)."
    ] = 0,
    summary_only: Annotated[
        bool,
        "Return only counts + top categories instead of the full shader list. "
        "Use this for discovery questions like 'how many URP shaders are in the project'."
    ] = False,
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
            data = response.get("data") or {}

            # Server-side trim for the list_* actions. Unity returns the full enumerated
            # list (the C# tool currently has no max_results param of its own); we cap it
            # here so the JSON returned to the model stays bounded. get_shader_info is a
            # single-shader lookup so it's not affected.
            shaders = data.get("shaders") if isinstance(data, dict) else None
            if isinstance(shaders, list) and action != "get_shader_info":
                total = len(shaders)

                if summary_only:
                    # Group by namespace prefix (text before the first '/') for a quick
                    # categorical view that's useful in discovery without dumping names.
                    categories: dict[str, int] = {}
                    for s in shaders:
                        name = s.get("name", "") if isinstance(s, dict) else ""
                        prefix = name.split("/", 1)[0] if name else "(unnamed)"
                        categories[prefix] = categories.get(prefix, 0) + 1
                    top_categories = sorted(
                        ({"category": k, "count": v} for k, v in categories.items()),
                        key=lambda c: c["count"], reverse=True,
                    )[:15]
                    return {
                        "success": True,
                        "message": f"Shader summary for '{action}' ({total} total).",
                        "data": {
                            "total_results": total,
                            "summary_only": True,
                            "top_categories": top_categories,
                        },
                    }

                # Apply offset + max_results paging. max_results=0 means "no cap".
                start = max(0, offset)
                end = total if max_results <= 0 else min(total, start + max_results)
                paged = shaders[start:end]
                next_offset = end if end < total else None

                return {
                    "success": True,
                    "message": response.get("message", f"Shader listing '{action}' successful."),
                    "data": {
                        **{k: v for k, v in data.items() if k != "shaders"},
                        "shaders": paged,
                        "total_results": total,
                        "returned": len(paged),
                        "offset": start,
                        "max_results": max_results,
                        "next_offset": next_offset,
                        "truncated": next_offset is not None,
                    },
                }

            return {
                "success": True,
                "message": response.get("message", f"Shader listing '{action}' successful."),
                "data": data,
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}

    except Exception as e:
        return {"success": False, "message": f"Error listing shaders: {e!s}"}
