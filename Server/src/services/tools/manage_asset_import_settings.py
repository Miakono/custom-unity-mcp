"""
Manage Unity asset import settings for different asset types.

Actions:
- get_import_settings: Read import settings for an asset
- update_import_settings: Update import settings for an asset

Different asset types have different import settings:
- Textures: compression, format, mipmaps, sprite settings
- Models: scale, animation, materials, colliders
- Audio: compression, format, load type
- Video: transcode, dimensions
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
        "Manage Unity asset import settings for different asset types. "
        "Read-only actions: get_import_settings. "
        "Modifying actions: update_import_settings. "
        "Supports textures, models, audio, video, and other asset types."
    ),
    annotations=ToolAnnotations(
        title="Manage Asset Import Settings",
        destructiveHint=True,
    ),
)
async def manage_asset_import_settings(
    ctx: Context,
    action: Annotated[
        Literal["get_import_settings", "update_import_settings"],
        "Action to perform: get_import_settings (read), update_import_settings (modify)"
    ],
    asset_path: Annotated[
        str,
        "Path to the asset (e.g., 'Assets/Textures/MyTexture.png', 'Assets/Models/Character.fbx')"
    ],
    importer_type: Annotated[
        str | None,
        "Type of importer (texture, model, audio, video, etc.). Auto-detected if not specified."
    ] = None,
    settings: Annotated[
        dict[str, Any] | None,
        "Import settings key-value pairs to update (for update_import_settings action)"
    ] = None,
    platform: Annotated[
        str | None,
        "Target platform for platform-specific settings (e.g., 'Standalone', 'Android', 'iOS')"
    ] = None,
) -> dict[str, Any]:
    """
    Manage Unity asset import settings for different asset types.
    
    Each asset type has specific import settings that control how Unity
    processes and imports the asset:
    
    Textures:
    - TextureType: Default, Normal map, Sprite, etc.
    - WrapMode: Clamp, Repeat
    - FilterMode: Point, Bilinear, Trilinear
    - MaxSize, Format, Compression
    - Sprite settings for UI sprites
    
    Models (FBX, etc.):
    - ScaleFactor, ConvertUnits
    - ImportAnimation, ImportMaterials
    - GenerateColliders, GenerateLightmapUVs
    
    Audio:
    - LoadType: DecompressOnLoad, CompressedInMemory, Streaming
    - CompressionFormat: PCM, Vorbis, ADPCM
    - Quality, SampleRateSetting
    
    Examples:
    - Get texture settings: action="get_import_settings", asset_path="Assets/Textures/Sprite.png"
    - Update texture: action="update_import_settings", asset_path="Assets/Textures/Sprite.png",
      settings={"textureType": "Sprite (2D and UI)", "spriteMeshType": "FullRect"}
    - Update model: action="update_import_settings", asset_path="Assets/Models/Char.fbx",
      settings={"scaleFactor": 0.01, "importAnimation": false}
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "manage_asset_import_settings", action=action)
    if gate is not None:
        return gate.model_dump()
    
    if not asset_path:
        return {
            "success": False,
            "message": "asset_path parameter is required."
        }
    
    try:
        params: dict[str, Any] = {
            "action": action,
            "assetPath": asset_path,
        }
        
        if importer_type:
            params["importerType"] = importer_type
        if settings:
            params["settings"] = settings
        if platform:
            params["platform"] = platform
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_asset_import_settings",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Import settings operation '{action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error managing asset import settings: {e!s}"}
