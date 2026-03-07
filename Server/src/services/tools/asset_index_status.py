from __future__ import annotations

"""
Check the status of the asset index without modifying it.

Provides information about:
- Index existence and location
- Freshness relative to project assets
- Coverage statistics
- Performance metrics

Use this tool to determine if the index needs to be rebuilt
before performing asset searches or analysis operations.
"""
from typing import Annotated, Any

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
        "Check the status of the asset index without modifying it. "
        "Reports index freshness, coverage statistics, and whether "
        "the index needs to be rebuilt before searching."
    ),
    annotations=ToolAnnotations(
        title="Asset Index Status",
        readOnlyHint=True,
    ),
)
async def asset_index_status(
    ctx: Context,
    detailed: Annotated[
        bool,
        "Include detailed breakdown by asset type. Default: false"
    ] = False,
    include_statistics: Annotated[
        bool | None,
        "Alias for detailed output."
    ] = None,
) -> dict[str, Any]:
    """
    Check the status of the asset index without modifying it.
    
    This read-only tool provides information about the current state
    of the asset index, helping you determine if it's safe to use
    for searches or if it needs to be rebuilt.
    
    Information Provided:
    - Index existence: Whether an index exists on disk
    - Index location: File path where index is stored
    - Freshness: Whether the index is up-to-date with project assets
    - Coverage: Percentage of project assets included in index
    - Statistics: Asset counts, size, build time
    
    Freshness Indicators:
    - FRESH: Index is up-to-date and ready for use
    - STALE: Some assets have changed since last build
    - MISSING: Index doesn't exist or is corrupted
    
    When to Rebuild:
    - Status is STALE and stale asset count is high
    - Coverage percentage is below 90%
    - Last build was more than a day ago in active projects
    
    Examples:
    - Quick status check:
      asset_index_status()
    
    - Detailed status with type breakdown:
      detailed=true
    
    Returns:
        Dictionary with index status including:
        - success: Boolean indicating if status check succeeded
        - message: Human-readable status summary
        - index_exists: Whether an index file exists
        - freshness: "fresh", "stale", or "missing"
        - is_ready: Boolean indicating if index is ready for searches
        - stats: Detailed statistics object
        - recommendations: Suggested actions based on status
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "asset_index_status")
    if gate is not None:
        return gate.model_dump()
    
    try:
        effective_detailed = detailed if include_statistics is None else bool(include_statistics)
        params: dict[str, Any] = {
            "detailed": effective_detailed,
        }
        
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "asset_index_status",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            
            # Determine readiness and recommendations
            freshness = data.get("freshness", "missing")
            coverage = data.get("coveragePercentage", 0)
            stale_count = data.get("staleAssets", 0)
            
            is_ready = freshness == "fresh" and coverage >= 90
            recommendations = []
            
            if freshness == "missing":
                recommendations.append("Build the index using build_asset_index(action='build')")
            elif freshness == "stale":
                if stale_count > 100:
                    recommendations.append("Many assets have changed. Consider a full rebuild.")
                else:
                    recommendations.append("Run build_asset_index(action='update') for incremental update")
            elif coverage < 90:
                recommendations.append(f"Coverage is low ({coverage:.1f}%). Consider rebuilding index.")
            else:
                recommendations.append("Index is ready for use")
            
            result = {
                "success": True,
                "message": response.get("message", "Asset index status retrieved."),
                "data": data,
                "index_exists": data.get("indexExists", False),
                "freshness": freshness,
                "is_ready": is_ready,
                "stats": {
                    "total_assets_indexed": data.get("totalAssetsIndexed", 0),
                    "total_project_assets": data.get("totalProjectAssets", 0),
                    "coverage_percentage": coverage,
                    "stale_assets": stale_count,
                    "missing_assets": data.get("missingAssets", 0),
                    "new_assets": data.get("newAssets", 0),
                    "index_size_mb": data.get("indexSizeMb", 0),
                    "last_build_time": data.get("lastBuildTime"),
                    "index_path": data.get("indexPath"),
                },
                "recommendations": recommendations,
            }
            
            # Add detailed breakdown if requested
            if effective_detailed and "typeBreakdown" in data:
                result["type_breakdown"] = data["typeBreakdown"]
            
            return result
        
        return response if isinstance(response, dict) else {
            "success": False,
            "message": str(response),
            "index_exists": False,
            "freshness": "unknown",
            "is_ready": False,
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error checking asset index status: {e!s}",
            "index_exists": False,
            "freshness": "unknown",
            "is_ready": False,
        }
