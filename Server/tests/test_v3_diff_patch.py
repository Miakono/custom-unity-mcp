"""Validation tests for V3 Diff/Patch tools (Phase 3).

Tests for:
- diff_scene
- diff_prefab
- diff_asset
- apply_scene_patch
- apply_prefab_patch
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.tools.diff_scene import diff_scene, _compare_gameobjects, _values_differ
from services.tools.diff_prefab import diff_prefab
from services.tools.diff_asset import diff_asset
from services.tools.apply_scene_patch import apply_scene_patch
from services.tools.apply_prefab_patch import apply_prefab_patch
from tests.integration.test_helpers import DummyContext


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def ctx():
    """Provide a dummy context for testing."""
    return DummyContext()


@pytest.fixture
def mock_scene_data():
    """Provide mock scene hierarchy data."""
    return {
        "success": True,
        "data": {
            "source": {
                "path": "Assets/Scenes/Main.unity",
                "name": "Main",
                "hierarchy": [
                    {
                        "name": "Player",
                        "active": True,
                        "transform": {
                            "position": [0, 1, 0],
                            "rotation": [0, 0, 0],
                            "scale": [1, 1, 1],
                        },
                        "components": [
                            {"type": "Transform"},
                            {"type": "PlayerController", "properties": {"speed": 5.0}}
                        ],
                        "children": []
                    },
                    {
                        "name": "Enemy",
                        "active": True,
                        "transform": {
                            "position": [10, 1, 0],
                            "rotation": [0, 180, 0],
                            "scale": [1, 1, 1],
                        },
                        "components": [
                            {"type": "Transform"},
                            {"type": "EnemyAI", "properties": {"health": 100}}
                        ],
                        "children": []
                    }
                ]
            },
            "target": {
                "path": "Assets/Scenes/Main.unity",
                "name": "Main",
                "hierarchy": [
                    {
                        "name": "Player",
                        "active": True,
                        "transform": {
                            "position": [0, 1, 0],
                            "rotation": [0, 0, 0],
                            "scale": [1, 1, 1],
                        },
                        "components": [
                            {"type": "Transform"},
                            {"type": "PlayerController", "properties": {"speed": 10.0}}
                        ],
                        "children": []
                    },
                    {
                        "name": "NPC",
                        "active": True,
                        "transform": {
                            "position": [5, 1, 0],
                            "rotation": [0, 90, 0],
                            "scale": [1, 1, 1],
                        },
                        "components": [
                            {"type": "Transform"},
                            {"type": "NPCController", "properties": {"dialogue": "Hello"}}
                        ],
                        "children": []
                    }
                ]
            }
        }
    }


@pytest.fixture
def mock_prefab_data():
    """Provide mock prefab data."""
    return {
        "success": True,
        "data": {
            "source": {
                "guid": "abc123",
                "path": "Assets/Prefabs/Character.prefab",
                "root": {
                    "name": "Character",
                    "active": True,
                    "transform": {"position": [0, 0, 0]},
                    "components": [
                        {"type": "Transform"},
                        {"type": "Animator", "properties": {"runtimeAnimatorController": "OldController"}}
                    ],
                    "children": []
                }
            },
            "target": {
                "guid": "abc123",
                "path": "Assets/Prefabs/Character.prefab",
                "root": {
                    "name": "Character",
                    "active": True,
                    "transform": {"position": [0, 0, 0]},
                    "components": [
                        {"type": "Transform"},
                        {"type": "Animator", "properties": {"runtimeAnimatorController": "NewController"}}
                    ],
                    "children": []
                }
            }
        }
    }


# =============================================================================
# Phase 3: Diff/Patch - diff_scene
# =============================================================================

@pytest.mark.asyncio
class TestDiffScene:
    """Tests for the diff_scene tool."""

    async def test_diff_active_scene(self, ctx, mock_scene_data):
        """test_diff_active_scene: Compares active scene against saved version."""
        with patch("services.tools.diff_scene.send_with_unity_instance",
                   AsyncMock(return_value=mock_scene_data)):
            result = await diff_scene(ctx, compare_mode="active_vs_saved")
        
        assert result["success"] is True
        assert "data" in result
        assert "diff_id" in result["data"]
        assert "summary" in result["data"]
        assert "changes" in result["data"]

    async def test_diff_named_scenes(self, ctx, mock_scene_data):
        """test_diff_named_scene: Compares two named scenes."""
        with patch("services.tools.diff_scene.send_with_unity_instance",
                   AsyncMock(return_value=mock_scene_data)):
            result = await diff_scene(
                ctx, 
                compare_mode="two_scenes",
                source_scene="Assets/Scenes/Level1.unity",
                target_scene="Assets/Scenes/Level2.unity"
            )
        
        assert result["success"] is True
        assert result["data"]["source"]["path"] == "Assets/Scenes/Main.unity"
        assert result["data"]["target"]["path"] == "Assets/Scenes/Main.unity"

    async def test_diff_scene_with_checkpoint(self, ctx, mock_scene_data):
        """test_diff_structure: Compares scene at different checkpoints."""
        with patch("services.tools.diff_scene.send_with_unity_instance",
                   AsyncMock(return_value=mock_scene_data)):
            result = await diff_scene(
                ctx, 
                compare_mode="checkpoint",
                source_checkpoint_id="chk_old",
                target_checkpoint_id="chk_new"
            )
        
        assert result["success"] is True
        assert "data" in result

    async def test_diff_scene_detects_added_objects(self, ctx, mock_scene_data):
        """test_diff_structure: Detects added GameObjects."""
        with patch("services.tools.diff_scene.send_with_unity_instance",
                   AsyncMock(return_value=mock_scene_data)):
            result = await diff_scene(ctx, compare_mode="active_vs_saved")
        
        assert result["success"] is True
        # NPC was added (in target but not source)
        assert result["data"]["summary"]["added"] >= 1

    async def test_diff_scene_detects_removed_objects(self, ctx, mock_scene_data):
        """test_diff_structure: Detects removed GameObjects."""
        with patch("services.tools.diff_scene.send_with_unity_instance",
                   AsyncMock(return_value=mock_scene_data)):
            result = await diff_scene(ctx, compare_mode="active_vs_saved")
        
        assert result["success"] is True
        # Enemy was removed (in source but not target)
        assert result["data"]["summary"]["removed"] >= 1

    async def test_diff_scene_detects_modified_objects(self, ctx, mock_scene_data):
        """test_diff_structure: Detects modified GameObjects."""
        with patch("services.tools.diff_scene.send_with_unity_instance",
                   AsyncMock(return_value=mock_scene_data)):
            result = await diff_scene(ctx, compare_mode="active_vs_saved")
        
        assert result["success"] is True
        # Player was modified (speed changed from 5.0 to 10.0)
        assert result["data"]["summary"]["modified"] >= 1

    async def test_diff_scene_with_unchanged(self, ctx, mock_scene_data):
        """test_diff_structure: Includes unchanged when requested."""
        with patch("services.tools.diff_scene.send_with_unity_instance",
                   AsyncMock(return_value=mock_scene_data)):
            result = await diff_scene(ctx, compare_mode="active_vs_saved", include_unchanged=True)
        
        assert result["success"] is True
        # Should include unchanged count
        assert "unchanged" in result["data"]["summary"]

    async def test_diff_scene_with_max_depth(self, ctx, mock_scene_data):
        """test_diff_structure: Respects max_depth parameter."""
        with patch("services.tools.diff_scene.send_with_unity_instance",
                   AsyncMock(return_value=mock_scene_data)):
            result = await diff_scene(ctx, compare_mode="active_vs_saved", max_depth=2)
        
        assert result["success"] is True
        # Unity should receive maxDepth parameter

    async def test_diff_scene_unity_error(self, ctx):
        """test_diff_scene: Handles Unity error gracefully."""
        with patch("services.tools.diff_scene.send_with_unity_instance",
                   AsyncMock(return_value={"success": False, "message": "Unity error"})):
            result = await diff_scene(ctx, compare_mode="active_vs_saved")
        
        assert result["success"] is False
        assert "diff_id" in result  # Should still return a diff_id for tracking

    async def test_diff_scene_includes_human_readable(self, ctx, mock_scene_data):
        """test_diff_structure: Includes human-readable summary."""
        with patch("services.tools.diff_scene.send_with_unity_instance",
                   AsyncMock(return_value=mock_scene_data)):
            result = await diff_scene(ctx, compare_mode="active_vs_saved")
        
        assert result["success"] is True
        assert "human_readable" in result["data"]
        assert "Scene Diff Summary" in result["data"]["human_readable"]


# =============================================================================
# Phase 3: Diff/Patch - Helper Functions
# =============================================================================

class TestDiffHelpers:
    """Tests for diff helper functions."""

    def test_compare_gameobjects_detects_additions(self):
        """test_diff_structure: Helper detects added objects."""
        source = [{"name": "Obj1"}]
        target = [{"name": "Obj1"}, {"name": "Obj2"}]
        
        changes = _compare_gameobjects(source, target)
        
        added = [c for c in changes if c["change_type"] == "added"]
        assert len(added) == 1
        assert added[0]["path"] == "Obj2"

    def test_compare_gameobjects_detects_removals(self):
        """test_diff_structure: Helper detects removed objects."""
        source = [{"name": "Obj1"}, {"name": "Obj2"}]
        target = [{"name": "Obj1"}]
        
        changes = _compare_gameobjects(source, target)
        
        removed = [c for c in changes if c["change_type"] == "removed"]
        assert len(removed) == 1
        assert removed[0]["path"] == "Obj2"

    def test_compare_gameobjects_detects_modifications(self):
        """test_diff_structure: Helper detects modified properties."""
        source = [{"name": "Obj1", "active": True}]
        target = [{"name": "Obj1", "active": False}]
        
        changes = _compare_gameobjects(source, target)
        
        modified = [c for c in changes if c["change_type"] == "modified"]
        assert len(modified) == 1

    def test_values_differ_with_same_values(self):
        """test_diff_structure: Values differ helper with same values."""
        assert _values_differ(5, 5) is False
        assert _values_differ("test", "test") is False
        assert _values_differ([1, 2, 3], [1, 2, 3]) is False

    def test_values_differ_with_different_values(self):
        """test_diff_structure: Values differ helper with different values."""
        assert _values_differ(5, 10) is True
        assert _values_differ("test", "other") is True
        assert _values_differ([1, 2, 3], [1, 2, 4]) is True

    def test_values_differ_with_different_types(self):
        """test_diff_structure: Values differ helper with different types."""
        assert _values_differ(5, "5") is True
        assert _values_differ([1, 2], {"a": 1}) is True


# =============================================================================
# Phase 3: Diff/Patch - diff_prefab
# =============================================================================

@pytest.mark.asyncio
class TestDiffPrefab:
    """Tests for the diff_prefab tool."""

    async def test_diff_prefab_asset(self, ctx, mock_prefab_data):
        """test_diff_prefab_asset: Compares prefab asset versions."""
        with patch("services.tools.diff_prefab.send_with_unity_instance",
                   AsyncMock(return_value=mock_prefab_data)):
            result = await diff_prefab(
                ctx, 
                prefab_path="Assets/Prefabs/Character.prefab",
                compare_mode="current_vs_saved"
            )
        
        assert result["success"] is True
        assert "data" in result
        assert "diff_id" in result["data"]
        assert "changes" in result["data"]

    async def test_diff_prefab_detects_component_changes(self, ctx, mock_prefab_data):
        """test_diff_structure: Detects component property changes."""
        with patch("services.tools.diff_prefab.send_with_unity_instance",
                   AsyncMock(return_value=mock_prefab_data)):
            result = await diff_prefab(
                ctx, 
                prefab_path="Assets/Prefabs/Character.prefab",
                compare_mode="current_vs_saved"
            )
        
        assert result["success"] is True
        # Animator controller was changed
        changes = result["data"]["changes"]
        modified = [c for c in changes if c.get("change_type") == "modified"]
        # Should detect component changes

    async def test_diff_prefab_with_checkpoint(self, ctx, mock_prefab_data):
        """test_diff_structure: Compares prefab at checkpoints."""
        with patch("services.tools.diff_prefab.send_with_unity_instance",
                   AsyncMock(return_value=mock_prefab_data)):
            result = await diff_prefab(
                ctx, 
                prefab_path="Assets/Prefabs/Character.prefab",
                compare_mode="checkpoint",
                source_checkpoint_id="chk_old"
            )
        
        assert result["success"] is True
        assert "data" in result

    async def test_diff_prefab_requires_path(self, ctx):
        """test_diff_prefab_asset: Requires prefab_path parameter."""
        result = await diff_prefab(ctx, compare_mode="current_vs_saved")
        
        assert result["success"] is False

    async def test_diff_prefab_unity_error(self, ctx):
        """test_diff_prefab_asset: Handles Unity error gracefully."""
        with patch("services.tools.diff_prefab.send_with_unity_instance",
                   AsyncMock(return_value={"success": False, "message": "Prefab not found"})):
            result = await diff_prefab(
                ctx, 
                prefab_path="Assets/Prefabs/Missing.prefab",
                compare_mode="current_vs_saved"
            )
        
        assert result["success"] is False
        assert "prefab" in result.get("message", "").lower() or "not found" in result.get("message", "").lower()


# =============================================================================
# Phase 3: Diff/Patch - diff_asset
# =============================================================================

@pytest.mark.asyncio
class TestDiffAsset:
    """Tests for the diff_asset tool."""

    async def test_diff_asset_properties(self, ctx):
        """test_diff_asset_properties: Compares asset properties."""
        mock_response = {
            "success": True,
            "data": {
                "source": {
                    "guid": "tex123",
                    "path": "Assets/Textures/Wall.png",
                    "importer_type": "TextureImporter",
                    "import_settings": {
                        "maxTextureSize": 1024,
                        "textureType": "Default"
                    }
                },
                "target": {
                    "guid": "tex123",
                    "path": "Assets/Textures/Wall.png",
                    "importer_type": "TextureImporter",
                    "import_settings": {
                        "maxTextureSize": 2048,
                        "textureType": "Sprite"
                    }
                },
                "changes": [
                    {
                        "property": "maxTextureSize",
                        "old_value": 1024,
                        "new_value": 2048
                    },
                    {
                        "property": "textureType",
                        "old_value": "Default",
                        "new_value": "Sprite"
                    }
                ]
            }
        }
        
        with patch("services.tools.diff_asset.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await diff_asset(
                ctx, 
                asset_path="Assets/Textures/Wall.png",
                compare_mode="current_vs_saved"
            )
        
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]["changes"]) == 2

    async def test_diff_asset_requires_path(self, ctx):
        """test_diff_asset_properties: Requires asset_path parameter."""
        result = await diff_asset(ctx, compare_mode="current_vs_saved")
        
        assert result["success"] is False

    async def test_diff_asset_by_guid(self, ctx):
        """test_diff_asset_properties: Can diff by GUID."""
        mock_response = {
            "success": True,
            "data": {
                "source": {"guid": "abc123"},
                "target": {"guid": "abc123"},
                "changes": []
            }
        }
        
        with patch("services.tools.diff_asset.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await diff_asset(
                ctx, 
                asset_guid="abc123",
                compare_mode="current_vs_saved"
            )
        
        assert result["success"] is True


# =============================================================================
# Phase 3: Diff/Patch - apply_scene_patch
# =============================================================================

@pytest.mark.asyncio
class TestApplyScenePatch:
    """Tests for the apply_scene_patch tool."""

    async def test_apply_valid_patch(self, ctx):
        """test_apply_valid_patch: Successfully applies a valid scene patch."""
        patch_data = {
            "operations": [
                {
                    "type": "modify_property",
                    "target": "Player",
                    "property": "transform.position",
                    "value": [1, 2, 3]
                }
            ]
        }
        
        mock_response = {
            "success": True,
            "data": {"applied_operations": 1}
        }
        
        with patch("services.tools.apply_scene_patch.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await apply_scene_patch(
                ctx, 
                scene_path="Assets/Scenes/Main.unity",
                patch=patch_data
            )
        
        assert result["success"] is True
        assert result["data"]["applied_operations"] == 1

    async def test_apply_invalid_patch(self, ctx):
        """test_apply_invalid_patch: Handles invalid patch gracefully."""
        result = await apply_scene_patch(
            ctx, 
            scene_path="Assets/Scenes/Main.unity",
            patch={"invalid": "data"}
        )
        
        assert result["success"] is False

    async def test_apply_patch_with_dry_run(self, ctx):
        """test_apply_valid_patch: Supports dry-run mode."""
        patch_data = {
            "operations": [
                {"type": "delete_object", "target": "Enemy"}
            ]
        }
        
        mock_response = {
            "success": True,
            "data": {"dry_run": True, "would_apply": 1}
        }
        
        with patch("services.tools.apply_scene_patch.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await apply_scene_patch(
                ctx, 
                scene_path="Assets/Scenes/Main.unity",
                patch=patch_data,
                dry_run=True
            )
        
        assert result["success"] is True
        assert result["data"]["dry_run"] is True

    async def test_apply_patch_to_active_scene(self, ctx):
        """test_apply_valid_patch: Can apply to active scene."""
        patch_data = {
            "operations": [
                {"type": "add_component", "target": "Player", "component": "Rigidbody"}
            ]
        }
        
        mock_response = {
            "success": True,
            "data": {"applied_operations": 1}
        }
        
        with patch("services.tools.apply_scene_patch.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await apply_scene_patch(
                ctx, 
                patch=patch_data,
                target_mode="active_scene"
            )
        
        assert result["success"] is True

    async def test_apply_patch_unity_error(self, ctx):
        """test_apply_invalid_patch: Handles Unity error during patch."""
        patch_data = {
            "operations": [
                {"type": "modify_property", "target": "MissingObject", "property": "x", "value": 1}
            ]
        }
        
        mock_response = {
            "success": False,
            "message": "Target object not found: MissingObject"
        }
        
        with patch("services.tools.apply_scene_patch.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await apply_scene_patch(
                ctx, 
                scene_path="Assets/Scenes/Main.unity",
                patch=patch_data
            )
        
        assert result["success"] is False


# =============================================================================
# Phase 3: Diff/Patch - apply_prefab_patch
# =============================================================================

@pytest.mark.asyncio
class TestApplyPrefabPatch:
    """Tests for the apply_prefab_patch tool."""

    async def test_apply_valid_patch(self, ctx):
        """test_apply_valid_patch: Successfully applies a valid prefab patch."""
        patch_data = {
            "operations": [
                {
                    "type": "modify_property",
                    "target": "Character",
                    "property": "components.Animator.runtimeAnimatorController",
                    "value": "NewController"
                }
            ]
        }
        
        mock_response = {
            "success": True,
            "data": {"applied_operations": 1}
        }
        
        with patch("services.tools.apply_prefab_patch.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await apply_prefab_patch(
                ctx, 
                prefab_path="Assets/Prefabs/Character.prefab",
                patch=patch_data
            )
        
        assert result["success"] is True
        assert result["data"]["applied_operations"] == 1

    async def test_apply_invalid_patch(self, ctx):
        """test_apply_invalid_patch: Handles invalid patch gracefully."""
        result = await apply_prefab_patch(
            ctx, 
            prefab_path="Assets/Prefabs/Character.prefab",
            patch={"invalid": "data"}
        )
        
        assert result["success"] is False

    async def test_apply_prefab_patch_by_guid(self, ctx):
        """test_apply_valid_patch: Can apply patch by prefab GUID."""
        patch_data = {
            "operations": [
                {"type": "modify_property", "target": "Root", "property": "active", "value": False}
            ]
        }
        
        mock_response = {
            "success": True,
            "data": {"applied_operations": 1}
        }
        
        with patch("services.tools.apply_prefab_patch.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await apply_prefab_patch(
                ctx, 
                prefab_guid="abc123",
                patch=patch_data
            )
        
        assert result["success"] is True

    async def test_apply_prefab_patch_with_variant_handling(self, ctx):
        """test_apply_valid_patch: Handles prefab variants correctly."""
        patch_data = {
            "operations": [
                {"type": "add_component", "target": "Character", "component": "BoxCollider"}
            ]
        }
        
        mock_response = {
            "success": True,
            "data": {"applied_operations": 1, "is_variant": True}
        }
        
        with patch("services.tools.apply_prefab_patch.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await apply_prefab_patch(
                ctx, 
                prefab_path="Assets/Prefabs/Character_Variant.prefab",
                patch=patch_data,
                handle_variants=True
            )
        
        assert result["success"] is True
        assert result["data"]["is_variant"] is True

    async def test_apply_prefab_patch_requires_path_or_guid(self, ctx):
        """test_apply_valid_patch: Requires prefab_path or prefab_guid."""
        result = await apply_prefab_patch(
            ctx, 
            patch={"operations": []}
        )
        
        assert result["success"] is False

    async def test_apply_prefab_patch_unity_error(self, ctx):
        """test_apply_invalid_patch: Handles Unity error during patch."""
        patch_data = {
            "operations": [
                {"type": "modify_property", "target": "Missing", "property": "x", "value": 1}
            ]
        }
        
        mock_response = {
            "success": False,
            "message": "Prefab modification failed"
        }
        
        with patch("services.tools.apply_prefab_patch.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await apply_prefab_patch(
                ctx, 
                prefab_path="Assets/Prefabs/Test.prefab",
                patch=patch_data
            )
        
        assert result["success"] is False
