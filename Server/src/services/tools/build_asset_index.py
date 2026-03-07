from __future__ import annotations

"""
Build and maintain a searchable index of Unity project assets.

The asset index enables fast asset discovery and relationship analysis
without requiring repeated Unity Editor queries. It persists to disk
for fast reload across sessions and supports incremental updates.

Index Features:
- Full asset metadata (GUID, path, type, labels, import settings)
- Dependency tracking (what each asset depends on)
- Reference tracking (what references each asset)
- Usage sites (where assets are used in scenes/prefabs)
- File metadata (size, modification time, hash)

Actions:
- build: Create full index from scratch
- update: Incremental update for changed assets only
- validate: Check index freshness and integrity
- clear: Remove the index
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
        "Build and maintain a searchable index of Unity project assets. "
        "Supports full rebuilds, incremental updates, and index persistence. "
        "The index enables fast asset discovery without repeated Unity queries."
    ),
    annotations=ToolAnnotations(
        title="Build Asset Index",
        readOnlyHint=False,
        destructiveHint=True,
    ),
)
async def build_asset_index(
    ctx: Context,
    action: Annotated[
        Literal["build", "update", "validate", "clear"],
        "Action to perform: 'build' (full rebuild), 'update' (incremental), "
        "'validate' (check freshness), 'clear' (remove index)"
    ],
    scope: Annotated[
        str | None,
        "Limit indexing to specific folder (e.g., 'Assets/Scripts'). Default: entire project"
    ] = None,
    include_types: Annotated[
        list[str] | None,
        "Asset types to include. Default: all types"
    ] = None,
    exclude_paths: Annotated[
        list[str] | None,
        "Paths to exclude from indexing (e.g., ['Assets/Plugins', 'Assets/ThirdParty'])"
    ] = None,
    include_dependencies: Annotated[
        bool,
        "Include dependency information in the index. Default: true"
    ] = True,
    include_references: Annotated[
        bool,
        "Include reference information (what references each asset). Default: true"
    ] = True,
    include_import_settings: Annotated[
        bool,
        "Include import settings metadata. Default: true"
    ] = True,
    max_depth: Annotated[
        int | None,
        "Maximum depth for dependency/reference traversal. Default: 10"
    ] = None,
    force_rebuild: Annotated[
        bool,
        "Force full rebuild even if incremental update would suffice. Default: false"
    ] = False,
    force: Annotated[
        bool | None,
        "Alias for force_rebuild."
    ] = None,
    path_filter: Annotated[
        str | None,
        "Alias for scope."
    ] = None,
) -> dict[str, Any]:
    """
    Build and maintain a searchable index of Unity project assets.
    
    The asset index provides fast, structured access to project assets
    without requiring repeated Unity Editor queries. It tracks:
    
    Asset Metadata:
    - asset_id: Unique identifier for the index entry
    - guid: Unity GUID for the asset
    - path: Asset path in the project
    - type: Asset type classification
    - labels: Unity labels assigned to the asset
    
    Import Settings:
    - importer_type: Type of asset importer
    - settings: Type-specific import settings
    
    Relationships:
    - dependencies: GUIDs this asset depends on
    - referenced_by: GUIDs that reference this asset
    - usage_sites: Where asset is used (scene/prefab paths)
    
    File Information:
    - file_size: Size in bytes
    - modified_time: Last modification timestamp (ISO format)
    - hash: Content hash for change detection
    
    Actions:
    - build: Creates a full index from scratch. Use for first-time indexing
      or when the existing index is significantly out of date.
    
    - update: Performs an incremental update, only processing assets that
      have changed since the last index build. Much faster than full build.
    
    - validate: Checks the index freshness without modifying it. Reports:
      * Total indexed assets
      * Assets needing update (modified since last build)
      * Missing assets (deleted since last build)
      * New assets (created since last build)
    
    - clear: Removes the index from disk and memory. Use when switching
      projects or if the index becomes corrupted.
    
    Examples:
    - First-time index build:
      action="build", include_dependencies=true, include_references=true
    
    - Quick incremental update:
      action="update"
    
    - Index specific folder only:
      action="build", scope="Assets/Characters"
    
    - Check if index is stale:
      action="validate"
    
    - Exclude third-party assets:
      action="build", exclude_paths=["Assets/Plugins", "Assets/ThirdParty"]
    
    Returns:
        Dictionary with operation results including:
        - success: Boolean indicating success
        - message: Human-readable status message
        - action: The action that was performed
        - stats: Index statistics (asset counts, timing, etc.)
        - index_path: Path where index is persisted (if applicable)
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    # Preflight checks for destructive operations
    if action in ("build", "clear"):
        gate = await maybe_run_tool_preflight(ctx, "build_asset_index", action=action)
        if gate is not None:
            return gate.model_dump()
    
    try:
        effective_force = force_rebuild if force is None else bool(force)
        effective_scope = path_filter or scope

        # Build parameters
        params: dict[str, Any] = {
            "action": action,
            "includeDependencies": include_dependencies,
            "includeReferences": include_references,
            "includeImportSettings": include_import_settings,
            "forceRebuild": effective_force,
        }
        
        if effective_scope:
            params["scope"] = effective_scope
        if include_types:
            params["includeTypes"] = include_types
        if exclude_paths:
            params["excludePaths"] = exclude_paths
        if max_depth is not None:
            params["maxDepth"] = max_depth
        
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "build_asset_index",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            base_result = {
                "success": True,
                "message": response.get("message", f"Asset index {action} completed successfully."),
                "action": action,
                "data": data,
            }
            
            # Format the response based on action
            if action == "validate":
                return {
                    **base_result,
                    "is_fresh": data.get("isFresh", False),
                    "index_exists": data.get("indexExists", False),
                    "stats": {
                        "total_indexed": data.get("totalIndexed", 0),
                        "assets_needing_update": data.get("assetsNeedingUpdate", 0),
                        "missing_assets": data.get("missingAssets", 0),
                        "new_assets": data.get("newAssets", 0),
                        "last_build_time": data.get("lastBuildTime"),
                        "coverage_percentage": data.get("coveragePercentage", 0),
                    },
                }
            else:
                return {
                    **base_result,
                    "stats": {
                        "assets_indexed": data.get("assetsIndexed", 0),
                        "dependencies_tracked": data.get("dependenciesTracked", 0),
                        "references_tracked": data.get("referencesTracked", 0),
                        "duration_seconds": data.get("durationSeconds", 0),
                        "index_size_mb": data.get("indexSizeMb", 0),
                    },
                    "index_path": data.get("indexPath"),
                }
        
        return response if isinstance(response, dict) else {
            "success": False,
            "message": str(response),
            "action": action,
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error {action}ing asset index: {e!s}",
            "action": action,
        }
