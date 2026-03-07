from __future__ import annotations

"""Resource for retrieving editor navigation context.

Provides current editor navigation state including inspector target,
hierarchy selection, scene view camera pose, and project browser focus.
"""

from pydantic import BaseModel
from fastmcp import Context
from typing import Any

from models import MCPResponse
from models.unity_response import parse_resource_response
from services.registry import mcp_for_unity_resource
from services.tools import get_unity_instance_from_context
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


class InspectorTargetInfo(BaseModel):
    """Information about the current Inspector target."""
    name: str | None = None
    type: str | None = None
    instance_id: int | None = None
    path: str | None = None
    guid: str | None = None
    is_locked: bool = False
    mode: str = "normal"  # normal, debug, debug_internal


class HierarchySelectionInfo(BaseModel):
    """Information about the current Hierarchy selection."""
    active_gameobject: str | None = None
    active_instance_id: int | None = None
    selected_count: int = 0
    selected_paths: list[str] = []
    selected_instance_ids: list[int] = []


class CameraPoseInfo(BaseModel):
    """Information about the Scene view camera pose."""
    position: dict[str, float] = {"x": 0.0, "y": 0.0, "z": 0.0}
    rotation: dict[str, float] = {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
    euler_angles: dict[str, float] = {"x": 0.0, "y": 0.0, "z": 0.0}
    orthographic: bool = False
    size: float = 5.0
    field_of_view: float = 60.0
    near_clip: float = 0.01
    far_clip: float = 1000.0


class SceneViewInfo(BaseModel):
    """Information about the Scene view state."""
    camera_pose: CameraPoseInfo = CameraPoseInfo()
    is_2d_mode: bool = False
    is_scene_lighting_on: bool = True
    is_audio_on: bool = False
    pivot: dict[str, float] = {"x": 0.0, "y": 0.0, "z": 0.0}


class ProjectBrowserFocusInfo(BaseModel):
    """Information about the Project browser focus."""
    active_folder: str = "Assets"
    selected_assets: list[str] = []
    selected_guids: list[str] = []


class EditorContextData(BaseModel):
    """Complete editor navigation context data."""
    inspector_target: InspectorTargetInfo = InspectorTargetInfo()
    hierarchy_selection: HierarchySelectionInfo = HierarchySelectionInfo()
    scene_view: SceneViewInfo = SceneViewInfo()
    project_browser: ProjectBrowserFocusInfo = ProjectBrowserFocusInfo()
    active_window: str | None = None


class EditorNavigationContextResponse(MCPResponse):
    """Response containing current editor navigation context."""
    data: EditorContextData = EditorContextData()


@mcp_for_unity_resource(
    uri="mcpforunity://editor/navigation_context",
    name="editor_navigation_context",
    description=(
        "Current editor navigation context including inspector target, "
        "hierarchy selection, scene view camera pose, and project browser focus. "
        "Use this to understand the current editor state before navigating.\n\n"
        "URI: mcpforunity://editor/navigation_context"
    ),
)
async def get_editor_navigation_context(ctx: Context) -> EditorNavigationContextResponse | MCPResponse:
    """Get the current editor navigation context.
    
    Returns information about:
    - Current Inspector target (what's being inspected)
    - Hierarchy selection (selected GameObjects)
    - Scene view camera pose (position, rotation, mode)
    - Project browser focus (selected assets/folders)
    - Active window
    
    Returns:
        EditorNavigationContextResponse with full context data
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    response = await send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "get_editor_navigation_context",
        {},
    )
    
    return parse_resource_response(response, EditorNavigationContextResponse)


@mcp_for_unity_resource(
    uri="mcpforunity://editor/inspector_target",
    name="editor_inspector_target",
    description=(
        "Current Inspector target information. "
        "Returns the object currently being inspected, including name, type, "
        "instance ID, path, and lock state.\n\n"
        "URI: mcpforunity://editor/inspector_target"
    ),
)
async def get_inspector_target(ctx: Context) -> MCPResponse:
    """Get the current Inspector target.
    
    Returns:
        MCPResponse with inspector target info
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    response = await send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "get_inspector_target",
        {},
    )
    
    if isinstance(response, dict) and response.get("success"):
        return MCPResponse(
            success=True,
            message="Retrieved inspector target",
            data=response.get("data", response)
        )
    return parse_resource_response(response, MCPResponse)


@mcp_for_unity_resource(
    uri="mcpforunity://editor/scene_view_camera",
    name="editor_scene_view_camera",
    description=(
        "Current Scene view camera pose. "
        "Returns position, rotation, orthographic mode, field of view, "
        "and other camera settings.\n\n"
        "URI: mcpforunity://editor/scene_view_camera"
    ),
)
async def get_scene_view_camera(ctx: Context) -> MCPResponse:
    """Get the current Scene view camera pose.
    
    Returns:
        MCPResponse with camera pose info
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    response = await send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "get_scene_view_camera",
        {},
    )
    
    if isinstance(response, dict) and response.get("success"):
        return MCPResponse(
            success=True,
            message="Retrieved scene view camera",
            data=response.get("data", response)
        )
    return parse_resource_response(response, MCPResponse)


@mcp_for_unity_resource(
    uri="mcpforunity://editor/project_browser_focus",
    name="editor_project_browser_focus",
    description=(
        "Current Project browser focus. "
        "Returns the active folder path and selected asset GUIDs.\n\n"
        "URI: mcpforunity://editor/project_browser_focus"
    ),
)
async def get_project_browser_focus(ctx: Context) -> MCPResponse:
    """Get the current Project browser focus.
    
    Returns:
        MCPResponse with project browser focus info
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    response = await send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "get_project_browser_focus",
        {},
    )
    
    if isinstance(response, dict) and response.get("success"):
        return MCPResponse(
            success=True,
            message="Retrieved project browser focus",
            data=response.get("data", response)
        )
    return parse_resource_response(response, MCPResponse)


@mcp_for_unity_resource(
    uri="mcpforunity://editor/active_context",
    name="editor_active_context",
    description=(
        "Overall active editor context. "
        "Returns which window is currently active (Scene, Game, Inspector, Hierarchy, "
        "Project, Console, etc.) and contextual state.\n\n"
        "URI: mcpforunity://editor/active_context"
    ),
)
async def get_active_editor_context(ctx: Context) -> MCPResponse:
    """Get the overall active editor context.
    
    Returns:
        MCPResponse with active context info
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    response = await send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "get_active_editor_context",
        {},
    )
    
    if isinstance(response, dict) and response.get("success"):
        return MCPResponse(
            success=True,
            message="Retrieved active editor context",
            data=response.get("data", response)
        )
    return parse_resource_response(response, MCPResponse)
