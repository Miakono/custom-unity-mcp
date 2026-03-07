"""
Find object references in Unity scenes and assets.

Actions:
- get_references: Get objects that reference the target
- get_referenced_by: Get objects that the target references

This tool helps understand object relationships in scenes and prefabs,
useful for refactoring, debugging, and understanding complex setups.
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
        "Find object references in Unity scenes and assets. "
        "Read-only actions: get_references, get_referenced_by. "
        "Helps understand object relationships in scenes and prefabs."
    ),
    annotations=ToolAnnotations(
        title="Get Object References",
        readOnlyHint=True,
    ),
)
async def get_object_references(
    ctx: Context,
    action: Annotated[
        Literal["get_references", "get_referenced_by"],
        "Action to perform: get_references (what references target), get_referenced_by (what target references)"
    ],
    target: Annotated[
        str,
        "Target object identifier (GameObject name, asset path, or instance ID)"
    ],
    search_scope: Annotated[
        str | None,
        "Where to search: 'scene' (current), 'project' (all assets), or specific folder path"
    ] = None,
    reference_type: Annotated[
        str | None,
        "Filter by reference type (e.g., 'component', 'material', 'prefab', 'script')"
    ] = None,
    max_results: Annotated[
        int,
        "Maximum number of results (default: 100)"
    ] = 100,
    include_inactive: Annotated[
        bool,
        "Include inactive GameObjects in search (default: true)"
    ] = True,
) -> dict[str, Any]:
    """
    Find object references in Unity scenes and assets.
    
    Understanding object references is crucial for:
    - Refactoring: Know what will break if you delete or move something
    - Debugging: Find why something is behaving unexpectedly
    - Optimization: Understand complex object relationships
    - Documentation: Map out scene and prefab structures
    
    Two directions of reference search:
    - get_references: Find what objects reference the target (incoming references)
      Example: "What GameObjects use this Material?"
    - get_referenced_by: Find what objects the target references (outgoing references)
      Example: "What components does this GameObject have?"
    
    Examples:
    - Find material users: action="get_references", target="Assets/Materials/Red.mat"
    - Find what a prefab uses: action="get_referenced_by", target="Assets/Prefabs/Player.prefab"
    - Find script references: action="get_references", target="PlayerController", search_scope="scene"
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "get_object_references", action=action)
    if gate is not None:
        return gate.model_dump()
    
    if not target:
        return {
            "success": False,
            "message": "target parameter is required."
        }
    
    try:
        params: dict[str, Any] = {
            "action": action,
            "target": target,
            "maxResults": max(max_results, 1),
            "includeInactive": include_inactive,
        }
        
        if search_scope:
            params["searchScope"] = search_scope
        if reference_type:
            params["referenceType"] = reference_type
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "get_object_references",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Object reference operation '{action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error getting object references: {e!s}"}
