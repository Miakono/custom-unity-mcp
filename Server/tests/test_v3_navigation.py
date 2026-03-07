"""Validation tests for V3 Navigation tools (Phase 5).

Tests for:
- navigate_editor
- reveal_asset
- focus_hierarchy
- frame_scene_target
- open_inspector_target
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.tools.navigate_editor import navigate_editor
from services.tools.reveal_asset import reveal_asset
from services.tools.focus_hierarchy import focus_hierarchy
from services.tools.frame_scene_target import frame_scene_target
from services.tools.open_inspector_target import open_inspector_target
from tests.integration.test_helpers import DummyContext


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def ctx():
    """Provide a dummy context for testing."""
    return DummyContext()


@pytest.fixture
def mock_navigation_response():
    """Provide mock navigation response."""
    return {
        "success": True,
        "navigation_id": "nav_123",
        "action": "reveal_in_project",
        "target": {"path": "Assets/Prefabs/Character.prefab"},
        "result": {"success": True, "message": "Asset revealed in Project window"},
        "editor_state": {"active_window": "Project"}
    }


# =============================================================================
# Phase 5: Navigation - navigate_editor
# =============================================================================

@pytest.mark.asyncio
class TestNavigateEditor:
    """Tests for the navigate_editor tool."""

    async def test_navigate_to_object(self, ctx, mock_navigation_response):
        """test_navigate_to_object: Navigates to GameObject in editor."""
        mock_response = {
            **mock_navigation_response,
            "action": "focus_hierarchy",
            "target": {"instance_id": 12345, "name": "Player"}
        }
        
        with patch("services.tools.navigate_editor.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await navigate_editor(
                ctx, 
                navigation_type="focus_hierarchy",
                target=12345
            )
        
        assert result["success"] is True
        assert result["action"] == "focus_hierarchy"

    async def test_navigate_to_asset(self, ctx, mock_navigation_response):
        """test_navigate_to_asset: Navigates to asset by path."""
        mock_response = {
            **mock_navigation_response,
            "action": "reveal_in_project"
        }
        
        with patch("services.tools.navigate_editor.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await navigate_editor(
                ctx, 
                navigation_type="reveal_in_project",
                target="Assets/Prefabs/Character.prefab"
            )
        
        assert result["success"] is True
        assert result["action"] == "reveal_in_project"

    async def test_navigate_open_script(self, ctx):
        """test_navigate_editor: Opens script at specific line."""
        mock_response = {
            "success": True,
            "navigation_id": "nav_456",
            "action": "open_script",
            "target": {"path": "Assets/Scripts/PlayerController.cs"},
            "result": {"success": True}
        }
        
        with patch("services.tools.navigate_editor.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await navigate_editor(
                ctx, 
                navigation_type="open_script",
                target="Assets/Scripts/PlayerController.cs",
                line_number=42,
                column_number=10
            )
        
        assert result["success"] is True
        assert result["action"] == "open_script"

    async def test_navigate_open_asset(self, ctx):
        """test_navigate_editor: Opens asset in appropriate editor."""
        mock_response = {
            "success": True,
            "navigation_id": "nav_789",
            "action": "open_asset",
            "target": {"path": "Assets/Scenes/Main.unity"},
            "result": {"success": True}
        }
        
        with patch("services.tools.navigate_editor.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await navigate_editor(
                ctx, 
                navigation_type="open_asset",
                target="Assets/Scenes/Main.unity"
            )
        
        assert result["success"] is True

    async def test_navigate_get_context(self, ctx):
        """test_navigate_editor: Gets current editor context."""
        mock_response = {
            "success": True,
            "navigation_id": "nav_context",
            "action": "get_context",
            "editor_state": {
                "active_scene": "Main",
                "selected_objects": ["Player", "Enemy"],
                "play_mode": "stopped"
            }
        }
        
        with patch("services.tools.navigate_editor.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await navigate_editor(
                ctx, 
                navigation_type="get_context"
            )
        
        assert result["success"] is True
        assert "editor_state" in result

    async def test_navigate_restore_context(self, ctx):
        """test_navigate_editor: Restores previous editor context."""
        mock_response = {
            "success": True,
            "navigation_id": "nav_restore",
            "action": "restore_context",
            "result": {"success": True}
        }
        
        previous_context = {
            "active_scene": "Level1",
            "selected_objects": ["OldSelection"]
        }
        
        with patch("services.tools.navigate_editor.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await navigate_editor(
                ctx, 
                navigation_type="restore_context",
                previous_context=previous_context
            )
        
        assert result["success"] is True

    async def test_navigate_with_dict_target(self, ctx, mock_navigation_response):
        """test_navigate_editor: Accepts dict as target."""
        mock_response = {
            **mock_navigation_response,
            "target": {"guid": "abc123", "name": "TestAsset"}
        }
        
        with patch("services.tools.navigate_editor.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await navigate_editor(
                ctx, 
                navigation_type="reveal_in_project",
                target={"guid": "abc123"}
            )
        
        assert result["success"] is True

    async def test_navigate_wait_for_completion(self, ctx, mock_navigation_response):
        """test_navigate_editor: Waits for completion when requested."""
        with patch("services.tools.navigate_editor.send_with_unity_instance",
                   AsyncMock(return_value=mock_navigation_response)):
            result = await navigate_editor(
                ctx, 
                navigation_type="reveal_in_project",
                target="Assets/Test.prefab",
                wait_for_completion=True
            )
        
        assert result["success"] is True

    async def test_navigate_timeout(self, ctx):
        """test_navigate_editor: Handles timeout."""
        with patch("services.tools.navigate_editor.send_with_unity_instance",
                   AsyncMock(side_effect=TimeoutError("Connection timeout"))):
            result = await navigate_editor(
                ctx, 
                navigation_type="reveal_in_project",
                target="Assets/Test.prefab"
            )
        
        assert result["success"] is False
        assert "timeout" in result["result"]["message"].lower()


# =============================================================================
# Phase 5: Navigation - reveal_asset
# =============================================================================

@pytest.mark.asyncio
class TestRevealAsset:
    """Tests for the reveal_asset tool."""

    async def test_reveal_in_project(self, ctx):
        """test_reveal_in_project: Reveals and pings asset in Project window."""
        mock_response = {
            "success": True,
            "data": {"revealed": True, "path": "Assets/Prefabs/Character.prefab"}
        }
        
        with patch("services.tools.reveal_asset.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await reveal_asset(
                ctx, 
                asset_path="Assets/Prefabs/Character.prefab"
            )
        
        assert result["success"] is True
        assert result["data"]["revealed"] is True

    async def test_reveal_by_guid(self, ctx):
        """test_reveal_in_project: Reveals asset by GUID."""
        mock_response = {
            "success": True,
            "data": {"revealed": True, "guid": "abc123"}
        }
        
        with patch("services.tools.reveal_asset.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await reveal_asset(ctx, asset_guid="abc123")
        
        assert result["success"] is True

    async def test_reveal_requires_path_or_guid(self, ctx):
        """test_reveal_in_project: Requires asset_path or asset_guid."""
        result = await reveal_asset(ctx)
        
        assert result["success"] is False

    async def test_reveal_not_found(self, ctx):
        """test_reveal_in_project: Handles missing asset."""
        mock_response = {
            "success": False,
            "message": "Asset not found"
        }
        
        with patch("services.tools.reveal_asset.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await reveal_asset(ctx, asset_path="Assets/Missing.prefab")
        
        assert result["success"] is False


# =============================================================================
# Phase 5: Navigation - focus_hierarchy
# =============================================================================

@pytest.mark.asyncio
class TestFocusHierarchy:
    """Tests for the focus_hierarchy tool."""

    async def test_focus_selection(self, ctx):
        """test_focus_selection: Focuses currently selected objects."""
        mock_response = {
            "success": True,
            "data": {"focused": True, "target_count": 2}
        }
        
        with patch("services.tools.focus_hierarchy.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await focus_hierarchy(ctx)
        
        assert result["success"] is True
        assert result["data"]["focused"] is True

    async def test_focus_specific_object(self, ctx):
        """test_focus_selection: Focuses specific GameObject."""
        mock_response = {
            "success": True,
            "data": {"focused": True, "target": "Player", "expanded": True}
        }
        
        with patch("services.tools.focus_hierarchy.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await focus_hierarchy(ctx, target_name="Player")
        
        assert result["success"] is True

    async def test_focus_with_expand(self, ctx):
        """test_focus_selection: Expands hierarchy when focusing."""
        mock_response = {
            "success": True,
            "data": {"focused": True, "expanded": True}
        }
        
        with patch("services.tools.focus_hierarchy.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await focus_hierarchy(ctx, target_name="Player", expand=True)
        
        assert result["success"] is True
        assert result["data"]["expanded"] is True

    async def test_focus_by_instance_id(self, ctx):
        """test_focus_selection: Can focus by instance ID."""
        mock_response = {
            "success": True,
            "data": {"focused": True, "instance_id": 12345}
        }
        
        with patch("services.tools.focus_hierarchy.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await focus_hierarchy(ctx, instance_id=12345)
        
        assert result["success"] is True

    async def test_focus_by_path(self, ctx):
        """test_focus_selection: Can focus by hierarchy path."""
        mock_response = {
            "success": True,
            "data": {"focused": True, "path": "Environment/Buildings/House1"}
        }
        
        with patch("services.tools.focus_hierarchy.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await focus_hierarchy(ctx, hierarchy_path="Environment/Buildings/House1")
        
        assert result["success"] is True


# =============================================================================
# Phase 5: Navigation - frame_scene_target
# =============================================================================

@pytest.mark.asyncio
class TestFrameSceneTarget:
    """Tests for the frame_scene_target tool."""

    async def test_frame_object(self, ctx):
        """test_frame_object: Frames specific object in Scene view."""
        mock_response = {
            "success": True,
            "data": {"framed": True, "target": "Player"}
        }
        
        with patch("services.tools.frame_scene_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await frame_scene_target(ctx, target_name="Player")
        
        assert result["success"] is True
        assert result["data"]["framed"] is True

    async def test_frame_bounds(self, ctx):
        """test_frame_bounds: Frames specific bounds in Scene view."""
        mock_response = {
            "success": True,
            "data": {"framed": True, "bounds": {"center": [0, 0, 0], "size": [10, 10, 10]}}
        }
        
        with patch("services.tools.frame_scene_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await frame_scene_target(
                ctx, 
                bounds_center=[0, 0, 0],
                bounds_size=[10, 10, 10]
            )
        
        assert result["success"] is True

    async def test_frame_selected(self, ctx):
        """test_frame_object: Frames currently selected objects."""
        mock_response = {
            "success": True,
            "data": {"framed": True, "selection_count": 3}
        }
        
        with patch("services.tools.frame_scene_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await frame_scene_target(ctx, frame_selected=True)
        
        assert result["success"] is True

    async def test_frame_with_camera_settings(self, ctx):
        """test_frame_bounds: Supports camera distance and angle."""
        mock_response = {
            "success": True,
            "data": {"framed": True, "camera_distance": 15.0, "view_angle": 45}
        }
        
        with patch("services.tools.frame_scene_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await frame_scene_target(
                ctx, 
                target_name="Player",
                camera_distance=15.0,
                view_angle=45
            )
        
        assert result["success"] is True

    async def test_frame_in_2d_mode(self, ctx):
        """test_frame_bounds: Supports 2D mode framing."""
        mock_response = {
            "success": True,
            "data": {"framed": True, "mode": "2d"}
        }
        
        with patch("services.tools.frame_scene_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await frame_scene_target(
                ctx, 
                target_name="UI_Canvas",
                mode="2d"
            )
        
        assert result["success"] is True

    async def test_frame_by_instance_id(self, ctx):
        """test_frame_object: Can frame by instance ID."""
        mock_response = {
            "success": True,
            "data": {"framed": True, "instance_id": 12345}
        }
        
        with patch("services.tools.frame_scene_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await frame_scene_target(ctx, instance_id=12345)
        
        assert result["success"] is True


# =============================================================================
# Phase 5: Navigation - open_inspector_target
# =============================================================================

@pytest.mark.asyncio
class TestOpenInspectorTarget:
    """Tests for the open_inspector_target tool."""

    async def test_open_inspector(self, ctx):
        """test_open_inspector: Opens object in Inspector window."""
        mock_response = {
            "success": True,
            "data": {"opened": True, "target": "Player"}
        }
        
        with patch("services.tools.open_inspector_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await open_inspector_target(ctx, target_name="Player")
        
        assert result["success"] is True
        assert result["data"]["opened"] is True

    async def test_open_inspector_with_lock(self, ctx):
        """test_open_inspector: Locks inspector to object."""
        mock_response = {
            "success": True,
            "data": {"opened": True, "locked": True}
        }
        
        with patch("services.tools.open_inspector_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await open_inspector_target(ctx, target_name="Player", lock=True)
        
        assert result["success"] is True
        assert result["data"]["locked"] is True

    async def test_open_inspector_by_instance_id(self, ctx):
        """test_open_inspector: Opens by instance ID."""
        mock_response = {
            "success": True,
            "data": {"opened": True, "instance_id": 12345}
        }
        
        with patch("services.tools.open_inspector_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await open_inspector_target(ctx, instance_id=12345)
        
        assert result["success"] is True

    async def test_open_inspector_by_guid(self, ctx):
        """test_open_inspector: Opens asset by GUID."""
        mock_response = {
            "success": True,
            "data": {"opened": True, "guid": "abc123"}
        }
        
        with patch("services.tools.open_inspector_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await open_inspector_target(ctx, asset_guid="abc123")
        
        assert result["success"] is True

    async def test_open_inspector_by_path(self, ctx):
        """test_open_inspector: Opens asset by path."""
        mock_response = {
            "success": True,
            "data": {"opened": True, "path": "Assets/Materials/Player.mat"}
        }
        
        with patch("services.tools.open_inspector_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await open_inspector_target(ctx, asset_path="Assets/Materials/Player.mat")
        
        assert result["success"] is True

    async def test_open_inspector_multi_selection(self, ctx):
        """test_open_inspector: Supports multi-selection."""
        mock_response = {
            "success": True,
            "data": {"opened": True, "selection_count": 3}
        }
        
        with patch("services.tools.open_inspector_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await open_inspector_target(
                ctx, 
                target_names=["Player", "Enemy", "NPC"]
            )
        
        assert result["success"] is True

    async def test_open_inspector_with_component_focus(self, ctx):
        """test_open_inspector: Focuses specific component."""
        mock_response = {
            "success": True,
            "data": {"opened": True, "focused_component": "Rigidbody"}
        }
        
        with patch("services.tools.open_inspector_target.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await open_inspector_target(
                ctx, 
                target_name="Player",
                focus_component="Rigidbody"
            )
        
        assert result["success"] is True
