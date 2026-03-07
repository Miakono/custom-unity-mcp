from __future__ import annotations

"""
Generate intelligent summaries of Unity assets.

Provides high-level understanding of asset purpose, properties,
usage patterns, and relationships. Helps answer "what is this asset
and how is it used?" without manual inspection.

Summary Types:
- Brief: Quick overview for rapid scanning
- Standard: Balanced detail for most use cases
- Detailed: Comprehensive analysis for deep understanding
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
        "Generate intelligent summaries of Unity assets. Provides high-level "
        "understanding of asset purpose, key properties, usage statistics, "
        "and relationships. Helps answer 'what is this asset and how is it used?'"
    ),
    annotations=ToolAnnotations(
        title="Summarize Asset",
        readOnlyHint=True,
    ),
)
async def summarize_asset(
    ctx: Context,
    asset_path: Annotated[
        str | None,
        "Path to the asset (e.g., 'Assets/Prefabs/Player.prefab')"
    ] = None,
    asset_guid: Annotated[
        str | None,
        "GUID of the asset (alternative to asset_path)"
    ] = None,
    detail_level: Annotated[
        Literal["brief", "standard", "detailed"],
        "Level of detail:\n"
        "- brief: Quick overview (1-2 sentences)\n"
        "- standard: Balanced detail (default)\n"
        "- detailed: Comprehensive analysis"
    ] = "standard",
    include_dependencies: Annotated[
        bool,
        "Include dependency summary. Default: true"
    ] = True,
    include_dependents: Annotated[
        bool,
        "Include dependent assets summary. Default: true"
    ] = True,
    include_usage_stats: Annotated[
        bool,
        "Include usage statistics. Default: true"
    ] = True,
    include_properties: Annotated[
        bool,
        "Include key properties summary. Default: true"
    ] = True,
    max_related_assets: Annotated[
        int,
        "Maximum number of related assets to include. Default: 10"
    ] = 10,
    include_size_details: Annotated[
        bool | None,
        "Include size details when provided by Unity."
    ] = None,
) -> dict[str, Any]:
    """
    Generate intelligent summaries of Unity assets.
    
    This tool provides high-level understanding of assets without requiring
    manual inspection. It's ideal for onboarding, documentation, and
    quickly understanding unfamiliar project assets.
    
    Summary Components:
    
    1. Description:
       Natural language description of the asset's purpose and role in the project.
       Generated from asset type, name, location, and configuration.
    
    2. Key Properties:
       Important asset-specific properties extracted and summarized:
       - Materials: Shader, textures, colors, rendering mode
       - Prefabs: Components, scripts, child objects
       - Scenes: Root objects, lighting settings, render settings
       - Scripts: Class type, inheritance, key attributes
       - Textures: Dimensions, format, compression, usage
       - Audio: Format, length, compression, 3D settings
    
    3. Usage Statistics:
       Quantitative information about how the asset is used:
       - Direct references count
       - Indirect references count
       - Scenes where used
       - Prefabs where referenced
       - Scripts that reference it
       - Estimated usage frequency
    
    4. Relationship Summary:
       Key dependencies and dependents:
       - What this asset requires to function
       - What would break if this asset is deleted
       - Related assets in the same category
       - Parent/child relationships
    
    Detail Levels:
    
    - brief:
      Single paragraph overview suitable for lists and quick scans.
      Includes asset type, primary purpose, and one key statistic.
    
    - standard (default):
      Balanced summary with description, key properties, usage stats,
      and top 5 related assets. Suitable for most use cases.
    
    - detailed:
      Comprehensive analysis including all available information.
      Includes extended property lists, full dependency chains,
      usage context, and technical details.
    
    Examples:
    - Quick overview:
      asset_path="Assets/Prefabs/Player.prefab", detail_level="brief"
    
    - Standard summary:
      asset_path="Assets/Materials/Enemy.mat"
    
    - Detailed analysis:
      asset_path="Assets/Scripts/GameManager.cs", detail_level="detailed"
    
    - Usage focus:
      asset_path="Assets/Textures/UI/SplashScreen.png",
      include_usage_stats=true, include_dependencies=false
    
    Returns:
        Dictionary with asset summary including:
        - success: Boolean indicating success
        - message: Human-readable status
        - asset: Basic asset info (path, guid, type, size)
        - summary: Natural language description
        - key_properties: Important asset-specific properties
        - usage_stats: Quantitative usage information
        - relationships: Dependencies and dependents summary
        - recommendations: Suggested actions or considerations
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "summarize_asset")
    if gate is not None:
        return gate.model_dump()
    
    # Validate required parameters
    if not asset_path and not asset_guid:
        return {
            "success": False,
            "message": "Either asset_path or asset_guid parameter is required.",
        }
    
    try:
        # Build parameters
        params: dict[str, Any] = {
            "detailLevel": detail_level,
            "includeDependencies": include_dependencies,
            "includeDependents": include_dependents,
            "includeUsageStats": include_usage_stats,
            "includeProperties": include_properties,
            "maxRelatedAssets": max(1, min(max_related_assets, 50)),  # Clamp 1-50
        }
        
        if asset_path:
            params["assetPath"] = asset_path
        if asset_guid:
            params["assetGuid"] = asset_guid
        
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "summarize_asset",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            
            return {
                "success": True,
                "message": response.get("message", "Asset summary generated successfully."),
                "data": data,
                "asset": {
                    "path": data.get("path", asset_path or "Unknown"),
                    "guid": data.get("guid", asset_guid or "Unknown"),
                    "type": data.get("type", "Unknown"),
                    "size_bytes": data.get("sizeBytes", 0),
                    "modified_time": data.get("modifiedTime"),
                },
                "summary": {
                    "description": data.get("description", "No description available."),
                    "purpose": data.get("purpose", "Unknown"),
                    "category": data.get("category", "Uncategorized"),
                },
                "key_properties": data.get("keyProperties", {}),
                "usage_stats": data.get("usageStats", {
                    "direct_references": 0,
                    "indirect_references": 0,
                    "scenes_using": 0,
                    "prefabs_using": 0,
                    "estimated_frequency": "unknown",
                }),
                "relationships": {
                    "dependencies": data.get("dependencies", []),
                    "dependents": data.get("dependents", []),
                    "related_assets": data.get("relatedAssets", []),
                },
                "size_details": (data.get("size_details") or data.get("sizeDetails")) if include_size_details else None,
                "recommendations": data.get("recommendations", []),
            }
        
        return response if isinstance(response, dict) else {
            "success": False,
            "message": str(response),
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating asset summary: {e!s}",
        }
