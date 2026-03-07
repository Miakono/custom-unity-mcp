from __future__ import annotations

"""
Find asset references bidirectionally in the Unity project.

This tool enables understanding of asset relationships by finding:
- What assets a target asset references (dependencies)
- What assets reference the target asset (dependents)
- Reference paths between two assets
- Impact analysis for asset modification/deletion

Use Cases:
- Safe asset deletion: Know what will break if you delete an asset
- Refactoring impact: Understand scope of changes
- Dependency auditing: Track asset relationships
- Circular dependency detection: Find problematic reference cycles
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
    group="asset_intelligence",
    description=(
        "Find asset references bidirectionally. Discover what assets reference "
        "a target asset (dependents) and what assets the target references "
        "(dependencies). Includes reference path finding and impact analysis."
    ),
    annotations=ToolAnnotations(
        title="Find Asset References",
        readOnlyHint=True,
    ),
)
async def find_asset_references(
    ctx: Context,
    action: Annotated[
        Literal["find_dependencies", "find_dependents", "find_path", "analyze_impact", "find_circular"],
        "Action to perform:\n"
        "- find_dependencies: Assets that the target references\n"
        "- find_dependents: Assets that reference the target\n"
        "- find_path: Find reference path between two assets\n"
        "- analyze_impact: Analyze impact of modifying/deleting asset\n"
        "- find_circular: Find circular reference chains"
    ] | None = None,
    asset_path: Annotated[
        str | None,
        "Path to the target asset (e.g., 'Assets/Materials/Player.mat')"
    ] = None,
    asset_guid: Annotated[
        str | None,
        "GUID of the target asset (alternative to asset_path)"
    ] = None,
    target_asset_path: Annotated[
        str | None,
        "For 'find_path' action: destination asset path"
    ] = None,
    target_asset_guid: Annotated[
        str | None,
        "For 'find_path' action: destination asset GUID"
    ] = None,
    direction: Annotated[
        Literal["upstream", "downstream", "both", "referenced_by", "depends_on"],
        "Reference direction:\n"
        "- upstream: Assets that reference the target (dependents)\n"
        "- downstream: Assets the target references (dependencies)\n"
        "- both: Both directions"
    ] = "both",
    max_depth: Annotated[
        int,
        "Maximum depth for reference traversal (1-20). Default: 5"
    ] = 5,
    include_indirect: Annotated[
        bool,
        "Include indirect references (transitive). Default: true"
    ] = True,
    filter_types: Annotated[
        list[str] | None,
        "Limit results to specific asset types (e.g., ['scenes', 'prefabs'])"
    ] = None,
    search_scope: Annotated[
        str | None,
        "Limit search to specific folder (e.g., 'Assets/Scripts')"
    ] = None,
    include_usage_context: Annotated[
        bool,
        "Include context of how asset is referenced. Default: true"
    ] = True,
    include_usage_details: Annotated[
        bool | None,
        "Alias for include_usage_context."
    ] = None,
    recursive: Annotated[
        bool,
        "Alias for include_indirect."
    ] = False,
    detect_circular: Annotated[
        bool,
        "Infer find_circular action when true."
    ] = False,
) -> dict[str, Any]:
    """
    Find asset references bidirectionally in the Unity project.
    
    This tool provides comprehensive understanding of asset relationships,
    enabling safe refactoring, deletion, and optimization decisions.
    
    Actions:
    
    1. find_dependencies (downstream):
       Find all assets that the target asset directly or indirectly references.
       Use this to understand what an asset needs to function.
       
       Example: What textures and materials does Player.prefab use?
    
    2. find_dependents (upstream):
       Find all assets that directly or indirectly reference the target.
       Use this to understand the impact of modifying or deleting an asset.
       
       Example: Which scenes use Player.prefab?
    
    3. find_path:
       Find the reference chain/path between two specific assets.
       Useful for understanding how two seemingly unrelated assets connect.
       
       Example: How does the MainMenu scene reference BossEnemy.prefab?
    
    4. analyze_impact:
       Comprehensive impact analysis for modifying or deleting an asset.
       Returns categorized lists of affected assets with risk assessment.
       
       Example: What will break if I delete this material?
    
    5. find_circular:
       Detect circular reference chains in the project or search scope.
       Circular dependencies can cause issues with asset bundles and builds.
       
       Example: Prefab A references Prefab B which references Prefab A
    
    Reference Direction:
    - upstream: Assets that reference the target (dependents/consumers)
    - downstream: Assets the target references (dependencies/requirements)
    - both: Complete reference graph in both directions
    
    Examples:
    - Find what depends on a material:
      action="find_dependents", asset_path="Assets/Materials/Player.mat"
    
    - Find dependencies of a prefab:
      action="find_dependencies", asset_path="Assets/Prefabs/Player.prefab", max_depth=3
    
    - Find reference path:
      action="find_path", asset_path="Assets/Scenes/Main.unity", target_asset_path="Assets/Prefabs/Enemy.prefab"
    
    - Analyze deletion impact:
      action="analyze_impact", asset_path="Assets/Scripts/PlayerController.cs"
    
    - Find circular dependencies:
      action="find_circular", search_scope="Assets/Prefabs"
    
    Returns:
        Dictionary with reference information including:
        - success: Boolean indicating success
        - message: Human-readable summary
        - action: The action performed
        - asset: Target asset info (path, guid, type)
        - references: List of referenced assets or reference graph
        - stats: Traversal statistics (depth, count, etc.)
        - For analyze_impact: categorized impact assessment with risk levels
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    effective_action = action
    if effective_action is None:
        if detect_circular:
            effective_action = "find_circular"
        elif direction in ("referenced_by", "upstream"):
            effective_action = "find_dependents"
        elif direction in ("depends_on", "downstream"):
            effective_action = "find_dependencies"
        else:
            effective_action = "find_dependents"

    effective_direction = direction
    if direction == "referenced_by":
        effective_direction = "upstream"
    elif direction == "depends_on":
        effective_direction = "downstream"

    effective_include_usage = include_usage_context if include_usage_details is None else bool(include_usage_details)
    effective_include_indirect = include_indirect or recursive

    gate = await maybe_run_tool_preflight(ctx, "find_asset_references", action=effective_action)
    if gate is not None:
        return gate.model_dump()
    
    # Validate required parameters
    if effective_action in ("find_dependencies", "find_dependents", "analyze_impact"):
        if not asset_path and not asset_guid:
            return {
                "success": False,
                "message": f"Action '{effective_action}' requires either asset_path or asset_guid parameter.",
                "action": effective_action,
            }
    
    if effective_action == "find_path":
        if not (asset_path or asset_guid) or not (target_asset_path or target_asset_guid):
            return {
                "success": False,
                "message": "Action 'find_path' requires both source and target asset identifiers.",
                "action": effective_action,
            }
    
    try:
        # Build parameters
        params: dict[str, Any] = {
            "action": effective_action,
            "direction": effective_direction,
            "maxDepth": min(max(max_depth, 1), 20),  # Clamp to 1-20
            "includeIndirect": effective_include_indirect,
            "includeUsageContext": effective_include_usage,
        }
        
        if asset_path:
            params["assetPath"] = asset_path
        if asset_guid:
            params["assetGuid"] = asset_guid
        if target_asset_path:
            params["targetAssetPath"] = target_asset_path
        if target_asset_guid:
            params["targetAssetGuid"] = target_asset_guid
        if filter_types:
            params["filterTypes"] = filter_types
        if search_scope:
            params["searchScope"] = search_scope
        
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "find_asset_references",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            
            result = {
                "success": True,
                "message": response.get("message", f"Reference analysis '{effective_action}' completed."),
                "action": effective_action,
                "data": data,
                "asset": data.get("asset", {}),
                "stats": data.get("stats", {}),
            }
            
            # Add action-specific fields
            if effective_action == "find_dependencies":
                result["dependencies"] = data.get("dependencies", [])
                result["direct_count"] = data.get("directCount", 0)
                result["indirect_count"] = data.get("indirectCount", 0)
            
            elif effective_action == "find_dependents":
                result["dependents"] = data.get("dependents", [])
                result["direct_count"] = data.get("directCount", 0)
                result["indirect_count"] = data.get("indirectCount", 0)
            
            elif effective_action == "find_path":
                result["path_found"] = data.get("pathFound", False)
                result["reference_path"] = data.get("referencePath", [])
                result["path_length"] = data.get("pathLength", 0)
            
            elif effective_action == "analyze_impact":
                result["impact_assessment"] = data.get("impactAssessment", {})
                result["risk_level"] = data.get("riskLevel", "unknown")
                result["affected_assets"] = data.get("affectedAssets", [])
                result["safe_to_delete"] = data.get("safeToDelete", False)
            
            elif effective_action == "find_circular":
                result["circular_chains"] = data.get("circularChains", [])
                result["chain_count"] = data.get("chainCount", 0)
            
            return result
        
        return response if isinstance(response, dict) else {
            "success": False,
            "message": str(response),
            "action": effective_action,
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error finding asset references: {e!s}",
            "action": effective_action,
        }
