"""
Analyze asset dependencies and relationships in the Unity project.

Actions:
- get_dependencies: Get assets that a target asset depends on
- get_dependents: Find what assets depend on a target asset
- analyze_circular: Detect circular dependencies in the project

This tool helps understand asset relationships and identify potential
issues like circular dependencies or unused assets.
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
        "Analyze asset dependencies and relationships. "
        "Read-only actions: get_dependencies, get_dependents, analyze_circular. "
        "Helps understand asset relationships, find what depends on what, "
        "and detect circular dependencies that can cause issues."
    ),
    annotations=ToolAnnotations(
        title="Analyze Asset Dependencies",
        readOnlyHint=True,
    ),
)
async def analyze_asset_dependencies(
    ctx: Context,
    action: Annotated[
        Literal["get_dependencies", "get_dependents", "analyze_circular"],
        "Action to perform: get_dependencies (what asset depends on), "
        "get_dependents (what depends on asset), analyze_circular (find circular deps)"
    ],
    asset_path: Annotated[
        str | None,
        "Path to the target asset (e.g., 'Assets/Scripts/MyScript.cs' or 'Assets/Prefabs/Player.prefab')"
    ] = None,
    asset_guid: Annotated[
        str | None,
        "GUID of the target asset (alternative to asset_path)"
    ] = None,
    include_indirect: Annotated[
        bool,
        "Include indirect/transitive dependencies (default: false for direct only)"
    ] = False,
    max_depth: Annotated[
        int | None,
        "Maximum depth for dependency traversal (default: 10)"
    ] = None,
    search_scope: Annotated[
        str | None,
        "Folder path to limit search scope (e.g., 'Assets/Scripts')"
    ] = None,
) -> dict[str, Any]:
    """
    Analyze asset dependencies and relationships in the Unity project.
    
    This tool helps understand how assets relate to each other:
    - get_dependencies: Find what assets a given asset depends on (its requirements)
    - get_dependents: Find what assets depend on a given asset (its consumers)
    - analyze_circular: Detect circular dependency chains in the project
    
    Understanding dependencies is crucial for:
    - Safe asset deletion (know what might break)
    - Refactoring (understand impact of changes)
    - Build optimization (understand asset bundles)
    - Identifying unused assets
    
    Examples:
    - Get dependencies: action="get_dependencies", asset_path="Assets/Prefabs/Player.prefab"
    - Get dependents: action="get_dependents", asset_path="Assets/Scripts/PlayerController.cs"
    - Analyze circular deps: action="analyze_circular", search_scope="Assets/Scripts"
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "analyze_asset_dependencies", action=action)
    if gate is not None:
        return gate.model_dump()
    
    # Validate required parameters
    if action in ("get_dependencies", "get_dependents"):
        if not asset_path and not asset_guid:
            return {
                "success": False,
                "message": f"Action '{action}' requires either asset_path or asset_guid parameter."
            }
    
    try:
        params: dict[str, Any] = {
            "action": action,
            "includeIndirect": include_indirect,
        }
        
        if asset_path:
            params["assetPath"] = asset_path
        if asset_guid:
            params["assetGuid"] = asset_guid
        if max_depth is not None:
            params["maxDepth"] = max_depth
        if search_scope:
            params["searchScope"] = search_scope
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "analyze_asset_dependencies",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Dependency analysis '{action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error analyzing asset dependencies: {e!s}"}
