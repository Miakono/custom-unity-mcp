from __future__ import annotations

"""
Advanced asset search with structured filtering and rich metadata.

Supports complex queries combining multiple criteria:
- Asset types (scenes, prefabs, materials, shaders, textures, audio, etc.)
- Labels and tags
- Import settings criteria
- Dependencies and references
- Custom criteria (size, date, usage)

Examples:
- Search for all materials with "Player" label: type="material", labels=["Player"]
- Find large textures: type="texture", min_size_mb=10
- Find unused assets: referenced_by=[] (empty)
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
        "Advanced asset search with structured filtering and rich metadata. "
        "Supports filtering by type, labels, import settings, dependencies, "
        "and custom criteria like size and date. Returns structured metadata "
        "suitable for further tool calls."
    ),
    annotations=ToolAnnotations(
        title="Search Assets Advanced",
        readOnlyHint=True,
    ),
)
async def search_assets_advanced(
    ctx: Context,
    asset_types: Annotated[
        list[str] | None,
        "Filter by asset types. Supported: 'scenes', 'prefabs', 'materials', "
        "'shaders', 'textures', 'audio', 'scriptable_objects', 'animations', "
        "'models', 'fonts', 'sprites', 'folders'"
    ] = None,
    labels: Annotated[
        list[str] | None,
        "Filter by asset labels/tags. Assets must have ALL specified labels."
    ] = None,
    search_path: Annotated[
        str | None,
        "Limit search to specific folder path (e.g., 'Assets/Characters')"
    ] = None,
    has_dependencies: Annotated[
        list[str] | None,
        "Find assets that depend on these GUIDs (assets referencing these)"
    ] = None,
    referenced_by: Annotated[
        list[str] | None,
        "Find assets referenced by these GUIDs (dependencies of these assets)"
    ] = None,
    import_settings: Annotated[
        dict[str, Any] | None,
        "Filter by import settings criteria. Example: {'textureType': 'Sprite', 'maxTextureSize': 1024}"
    ] = None,
    importer_type: Annotated[
        str | None,
        "Filter by importer type (e.g., 'TextureImporter', 'ModelImporter', 'AudioImporter')"
    ] = None,
    min_size_bytes: Annotated[
        int | None,
        "Minimum file size in bytes"
    ] = None,
    max_size_bytes: Annotated[
        int | None,
        "Maximum file size in bytes"
    ] = None,
    modified_after: Annotated[
        str | None,
        "Only assets modified after this date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
    ] = None,
    modified_before: Annotated[
        str | None,
        "Only assets modified before this date (ISO format)"
    ] = None,
    unused_only: Annotated[
        bool,
        "Only return assets with no references (potentially unused). Default: false"
    ] = False,
    name_pattern: Annotated[
        str | None,
        "Search by asset name pattern (supports * and ? wildcards)"
    ] = None,
    sort_by: Annotated[
        Literal["name", "path", "type", "size", "modified_time", "relevance"],
        "Sort field. Default: 'relevance'"
    ] = "relevance",
    sort_order: Annotated[
        Literal["asc", "desc"],
        "Sort order. Default: 'desc' for relevance, 'asc' for others"
    ] = "asc",
    page: Annotated[
        int,
        "Page number (1-based). Default: 1"
    ] = 1,
    page_size: Annotated[
        int,
        "Results per page (max 100). Default: 25"
    ] = 25,
    include_metadata: Annotated[
        bool,
        "Include full metadata for each asset. Default: true"
    ] = True,
) -> dict[str, Any]:
    """
    Advanced asset search with structured filtering and rich metadata.
    
    This tool enables powerful asset discovery without brute-force traversal.
    It searches the project's asset database with multiple filter criteria
    and returns structured metadata suitable for further tool calls.
    
    Search Capabilities:
    - Type filtering: Find assets by type (textures, materials, prefabs, etc.)
    - Label filtering: Filter by Unity labels/tags
    - Dependency analysis: Find assets based on their relationships
    - Import settings: Filter by importer configuration
    - Custom criteria: Size, modification date, usage patterns
    
    Asset Types Supported:
    - scenes: Unity scene files (.unity)
    - prefabs: Prefab assets (.prefab)
    - materials: Material assets (.mat)
    - shaders: Shader files (.shader, .shadergraph)
    - textures: Texture assets (.png, .jpg, .tga, etc.)
    - audio: Audio clips (.mp3, .wav, .ogg)
    - scriptable_objects: ScriptableObject assets
    - animations: Animation clips and controllers
    - models: 3D models (.fbx, .obj, etc.)
    - sprites: Sprite assets
    - fonts: Font assets
    - folders: Folder assets
    
    Examples:
    - Find all character materials:
      asset_types=["materials"], search_path="Assets/Characters"
    
    - Find large textures (>10MB):
      asset_types=["textures"], min_size_bytes=10485760, sort_by="size"
    
    - Find recently modified prefabs:
      asset_types=["prefabs"], modified_after="2024-01-01", sort_by="modified_time"
    
    - Find assets referencing a specific material:
      has_dependencies=["guid-of-material"]
    
    - Find potentially unused assets:
      unused_only=true, search_path="Assets/Old"
    
    Returns:
        Dictionary with search results including:
        - success: Boolean indicating if search succeeded
        - message: Human-readable status message
        - total_count: Total number of matching assets
        - page: Current page number
        - page_size: Results per page
        - assets: List of asset metadata dictionaries
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "search_assets_advanced")
    if gate is not None:
        return gate.model_dump()
    
    try:
        # Build search parameters
        params: dict[str, Any] = {
            "sortBy": sort_by,
            "sortOrder": sort_order,
            "page": page,
            "pageSize": min(page_size, 100),  # Enforce max
            "includeMetadata": include_metadata,
        }
        
        # Add optional filters
        if asset_types:
            params["assetTypes"] = asset_types
        if labels:
            params["labels"] = labels
        if search_path:
            params["searchPath"] = search_path
        if has_dependencies:
            params["hasDependencies"] = has_dependencies
        if referenced_by:
            params["referencedBy"] = referenced_by
        if import_settings:
            params["importSettings"] = import_settings
        if importer_type:
            params["importerType"] = importer_type
        if min_size_bytes is not None:
            params["minSizeBytes"] = min_size_bytes
        if max_size_bytes is not None:
            params["maxSizeBytes"] = max_size_bytes
        if modified_after:
            params["modifiedAfter"] = modified_after
        if modified_before:
            params["modifiedBefore"] = modified_before
        if unused_only:
            params["unusedOnly"] = unused_only
        if name_pattern:
            params["namePattern"] = name_pattern
        
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "search_assets_advanced",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            return {
                "success": True,
                "message": response.get("message", f"Found {data.get('totalCount', 0)} assets matching criteria."),
                "total_count": data.get("totalCount", 0),
                "page": data.get("page", page),
                "page_size": min(page_size, 100),
                "assets": data.get("assets", []),
            }
        
        return response if isinstance(response, dict) else {
            "success": False,
            "message": str(response),
            "total_count": 0,
            "page": page,
            "page_size": page_size,
            "assets": [],
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error searching assets: {e!s}",
            "total_count": 0,
            "page": page,
            "page_size": page_size,
            "assets": [],
        }
