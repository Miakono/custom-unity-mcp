"""
Screenshot capture tool for AI vision/multimodal support.
Part of Phase 2: Vision & Multimodal gap closure.
"""

from typing import Dict, List, Literal, Optional, Union
from pydantic import Field

from mcpforunityserver.decorators import mcp_for_unity_tool
from mcpforunityserver.types import JObject
from mcpforunityserver.unity_connection import get_unity_instance


@mcp_for_unity_tool(group="visual")
async def manage_screenshot(
    action: Literal[
        "capture_game_view",
        "capture_scene_view", 
        "capture_object_preview",
        "get_last_screenshot"
    ] = Field(description="Screenshot action to perform"),
    width: int = Field(default=1920, description="Image width in pixels"),
    height: int = Field(default=1080, description="Image height in pixels"),
    format: Literal["base64", "path"] = Field(
        default="base64", 
        description="Output format: base64 string or file path"
    ),
    target_object: Optional[str] = Field(
        default=None,
        description="For object_preview: GameObject path or name"
    ),
    camera_position: Optional[List[float]] = Field(
        default=None,
        description="For scene_view: [x, y, z] camera position"
    ),
    camera_rotation: Optional[List[float]] = Field(
        default=None,
        description="For scene_view: [x, y, z] euler angles"
    ),
    background_color: Optional[Union[str, List[float]]] = Field(
        default=None,
        description="For object_preview: hex string (#RRGGBB) or [r, g, b, a]"
    )
) -> Dict:
    """
    Capture screenshots of Game view, Scene view, or specific objects.
    
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
    """
    unity = get_unity_instance()
    
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
    result = await unity.send_command("manage_screenshot", params)
    
    # Validate response has image data
    if not result.get("success"):
        return result
    
    # If base64 format, ensure it's properly formatted for AI clients
    if format == "base64" and "image_base64" in result:
        # Ensure data URI format for direct rendering
        if "data_uri" not in result:
            result["data_uri"] = f"data:image/png;base64,{result['image_base64']}"
    
    return result
