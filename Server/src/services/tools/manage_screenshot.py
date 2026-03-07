"""Screenshot capture tool for AI vision and visual QA flows."""

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    group="visual_qa",
    description=(
        "Capture screenshots of the Unity Game view, Scene view, object previews, or the full editor window. "
        "Actions: capture_game_view, capture_scene_view, capture_object_preview, capture_editor_window, "
        "get_last_screenshot. Returns base64 or path output suitable for visual QA workflows."
    ),
    annotations=ToolAnnotations(
        title="Manage Screenshot",
        destructiveHint=False,
    ),
)
async def manage_screenshot(
    ctx: Context,
    action: Annotated[Literal[
        "capture_game_view",
        "capture_scene_view",
        "capture_object_preview",
        "capture_editor_window",
        "get_last_screenshot",
    ], "Screenshot action to perform."],
    width: Annotated[int, "Image width in pixels."] = 1920,
    height: Annotated[int, "Image height in pixels."] = 1080,
    format: Annotated[Literal["base64", "path"], "Output format."] = "base64",
    target_object: Annotated[str | None, "For object preview: GameObject path or name."] = None,
    camera_position: Annotated[list[float] | None, "For scene view: [x, y, z] camera position."] = None,
    camera_rotation: Annotated[list[float] | None, "For scene view: [x, y, z] euler angles."] = None,
    background_color: Annotated[
        str | list[float] | None,
        "For object preview: hex string (#RRGGBB) or [r, g, b, a].",
    ] = None,
) -> dict[str, Any]:
    """
    Capture screenshots of Game view, Scene view, the full editor window, or specific objects.
    Also supports returning the last captured screenshot payload.
    
    Enables AI assistants to 'see' the Unity Editor state for debugging,
    visual validation, and multimodal interaction.
    
    Examples:
        # Capture current Game view
        manage_screenshot(action="capture_game_view")
        
        # Capture Scene view from custom angle
        manage_screenshot(
            action="capture_scene_view",
            camera_position=[10, 10, -10],
            camera_rotation=[30, -45, 0],
            width=1920,
            height=1080
        )
        
        # Render object preview with transparent background
        manage_screenshot(
            action="capture_object_preview",
            target_object="Player",
            width=512,
            height=512,
            background_color="#00000000"
        )

        # Capture full Unity editor window (Hierarchy/Scene/Inspector/Console)
        manage_screenshot(
            action="capture_editor_window",
            format="base64"
        )
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    # Build command parameters
    params = {
        "action": action,
        "width": width,
        "height": height,
        "format": format
    }
    
    if target_object:
        params["target_object"] = target_object
    if camera_position:
        params["camera_position"] = camera_position
    if camera_rotation:
        params["camera_rotation"] = camera_rotation
    if background_color:
        params["background_color"] = background_color
    
    # Send to Unity
    result = await send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "manage_screenshot",
        params,
    )
    
    # Validate response has image data
    if not result.get("success"):
        return result
    
    # If base64 format, ensure it's properly formatted for AI clients
    if format == "base64" and "image_base64" in result:
        # Ensure data URI format for direct rendering
        if "data_uri" not in result:
            result["data_uri"] = f"data:image/png;base64,{result['image_base64']}"
    
    return result if isinstance(result, dict) else {"success": False, "message": str(result)}
