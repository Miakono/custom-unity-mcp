"""Validation tests for V3 Asset Intelligence tools (Phase 4).

Tests for:
- search_assets_advanced
- build_asset_index
- asset_index_status
- find_asset_references
- summarize_asset
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.tools.search_assets_advanced import search_assets_advanced
from services.tools.build_asset_index import build_asset_index
from services.tools.asset_index_status import asset_index_status
from services.tools.find_asset_references import find_asset_references
from services.tools.summarize_asset import summarize_asset
from tests.integration.test_helpers import DummyContext


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def ctx():
    """Provide a dummy context for testing."""
    return DummyContext()


@pytest.fixture
def mock_search_results():
    """Provide mock asset search results."""
    return {
        "success": True,
        "data": {
            "totalCount": 3,
            "page": 1,
            "pageSize": 25,
            "assets": [
                {
                    "guid": "mat001",
                    "path": "Assets/Materials/Player.mat",
                    "name": "Player",
                    "type": "material",
                    "labels": ["character", "player"],
                    "size_bytes": 2048,
                    "modified_time": "2024-01-15T10:30:00Z"
                },
                {
                    "guid": "mat002",
                    "path": "Assets/Materials/Enemy.mat",
                    "name": "Enemy",
                    "type": "material",
                    "labels": ["character", "enemy"],
                    "size_bytes": 1536,
                    "modified_time": "2024-01-14T09:00:00Z"
                },
                {
                    "guid": "tex001",
                    "path": "Assets/Textures/Player_Diffuse.png",
                    "name": "Player_Diffuse",
                    "type": "texture",
                    "labels": ["character", "texture"],
                    "size_bytes": 1048576,
                    "modified_time": "2024-01-15T10:00:00Z"
                }
            ]
        }
    }


@pytest.fixture
def mock_asset_summary():
    """Provide mock asset summary data."""
    return {
        "success": True,
        "data": {
            "guid": "prefab001",
            "path": "Assets/Prefabs/Character.prefab",
            "type": "prefab",
            "summary": {
                "root_object": "Character",
                "child_count": 5,
                "component_count": 8,
                "mesh_count": 2,
                "material_count": 3,
                "total_vertices": 1250,
                "total_triangles": 2400
            },
            "structure": {
                "name": "Character",
                "components": ["Transform", "Animator", "CharacterController"],
                "children": [
                    {"name": "Body", "components": ["Transform", "SkinnedMeshRenderer"]},
                    {"name": "Weapon", "components": ["Transform", "MeshRenderer"]}
                ]
            },
            "dependencies": [
                {"type": "material", "path": "Assets/Materials/Character.mat"},
                {"type": "mesh", "path": "Assets/Models/Character.fbx"},
                {"type": "animation", "path": "Assets/Animations/Character.controller"}
            ]
        }
    }


# =============================================================================
# Phase 4: Asset Intelligence - search_assets_advanced
# =============================================================================

@pytest.mark.asyncio
class TestSearchAssetsAdvanced:
    """Tests for the search_assets_advanced tool."""

    async def test_search_by_type(self, ctx, mock_search_results):
        """test_search_by_type: Searches assets by type."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(ctx, asset_types=["materials"])
        
        assert result["success"] is True
        assert result["total_count"] == 3
        assert len(result["assets"]) == 3

    async def test_search_by_label(self, ctx, mock_search_results):
        """test_search_by_label: Searches assets by labels."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(ctx, labels=["character"])
        
        assert result["success"] is True
        # Should return assets with "character" label

    async def test_search_with_multiple_labels(self, ctx, mock_search_results):
        """test_search_by_label: Searches with multiple labels (AND logic)."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(ctx, labels=["character", "player"])
        
        assert result["success"] is True
        # Should return assets with both labels

    async def test_search_by_name_pattern(self, ctx, mock_search_results):
        """test_search_with_filters: Searches by name pattern."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(ctx, name_pattern="Player*")
        
        assert result["success"] is True

    async def test_search_by_path(self, ctx, mock_search_results):
        """test_search_with_filters: Limits search to specific path."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(ctx, search_path="Assets/Materials")
        
        assert result["success"] is True

    async def test_search_with_size_filter(self, ctx, mock_search_results):
        """test_search_with_filters: Filters by file size."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(
                ctx, 
                asset_types=["textures"],
                min_size_bytes=1024,
                max_size_bytes=2097152
            )
        
        assert result["success"] is True

    async def test_search_with_date_filter(self, ctx, mock_search_results):
        """test_search_with_filters: Filters by modification date."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(
                ctx, 
                modified_after="2024-01-01",
                modified_before="2024-12-31"
            )
        
        assert result["success"] is True

    async def test_search_unused_only(self, ctx, mock_search_results):
        """test_search_with_filters: Finds unused assets."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(ctx, unused_only=True)
        
        assert result["success"] is True

    async def test_search_by_import_settings(self, ctx, mock_search_results):
        """test_search_with_filters: Filters by import settings."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(
                ctx, 
                asset_types=["textures"],
                import_settings={"textureType": "Sprite"}
            )
        
        assert result["success"] is True

    async def test_search_by_importer_type(self, ctx, mock_search_results):
        """test_search_with_filters: Filters by importer type."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(
                ctx, 
                importer_type="TextureImporter"
            )
        
        assert result["success"] is True

    async def test_search_with_sorting(self, ctx, mock_search_results):
        """test_search_with_filters: Supports sorting options."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(
                ctx, 
                sort_by="size",
                sort_order="desc"
            )
        
        assert result["success"] is True

    async def test_search_with_pagination(self, ctx, mock_search_results):
        """test_search_with_filters: Supports pagination."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(
                ctx, 
                page=1,
                page_size=10
            )
        
        assert result["success"] is True
        assert result["page"] == 1
        assert result["page_size"] == 10

    async def test_search_with_dependencies(self, ctx, mock_search_results):
        """test_search_with_filters: Finds assets with dependencies."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(
                ctx, 
                has_dependencies=["guid-of-material"]
            )
        
        assert result["success"] is True

    async def test_search_by_referenced_by(self, ctx, mock_search_results):
        """test_search_with_filters: Finds assets referenced by others."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(
                ctx, 
                referenced_by=["guid-of-prefab"]
            )
        
        assert result["success"] is True

    async def test_search_without_metadata(self, ctx, mock_search_results):
        """test_search_with_filters: Can exclude metadata for faster results."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value=mock_search_results)):
            result = await search_assets_advanced(ctx, include_metadata=False)
        
        assert result["success"] is True

    async def test_search_unity_error(self, ctx):
        """test_search_by_type: Handles Unity error gracefully."""
        with patch("services.tools.search_assets_advanced.send_with_unity_instance",
                   AsyncMock(return_value={"success": False, "message": "Search failed"})):
            result = await search_assets_advanced(ctx, asset_types=["materials"])
        
        assert result["success"] is False


# =============================================================================
# Phase 4: Asset Intelligence - build_asset_index
# =============================================================================

@pytest.mark.asyncio
class TestBuildAssetIndex:
    """Tests for the build_asset_index tool."""

    async def test_build_index(self, ctx):
        """test_build_index: Builds complete asset index."""
        mock_response = {
            "success": True,
            "data": {
                "indexed_count": 150,
                "duration_ms": 2500,
                "index_version": "2024.1.1"
            }
        }
        
        with patch("services.tools.build_asset_index.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await build_asset_index(ctx, action="build")
        
        assert result["success"] is True
        assert result["data"]["indexed_count"] == 150

    async def test_incremental_update(self, ctx):
        """test_incremental_update: Performs incremental index update."""
        mock_response = {
            "success": True,
            "data": {
                "updated_count": 15,
                "added_count": 3,
                "removed_count": 2,
                "duration_ms": 300
            }
        }
        
        with patch("services.tools.build_asset_index.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await build_asset_index(ctx, action="update")
        
        assert result["success"] is True
        assert result["data"]["updated_count"] == 15

    async def test_build_index_with_force_rebuild(self, ctx):
        """test_build_index: Supports force rebuild."""
        mock_response = {
            "success": True,
            "data": {"indexed_count": 150, "rebuilt": True}
        }
        
        with patch("services.tools.build_asset_index.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await build_asset_index(ctx, action="build", force=True)
        
        assert result["success"] is True

    async def test_build_index_with_path_filter(self, ctx):
        """test_build_index: Can limit to specific path."""
        mock_response = {
            "success": True,
            "data": {"indexed_count": 25}
        }
        
        with patch("services.tools.build_asset_index.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await build_asset_index(
                ctx, 
                action="build",
                path_filter="Assets/Characters"
            )
        
        assert result["success"] is True


# =============================================================================
# Phase 4: Asset Intelligence - asset_index_status
# =============================================================================

@pytest.mark.asyncio
class TestAssetIndexStatus:
    """Tests for the asset_index_status tool."""

    async def test_get_status(self, ctx):
        """test_get_status: Returns current index status."""
        mock_response = {
            "success": True,
            "data": {
                "is_indexed": True,
                "index_version": "2024.1.1",
                "total_assets": 150,
                "last_updated": "2024-01-15T12:00:00Z",
                "is_outdated": False,
                "coverage_percent": 98.5
            }
        }
        
        with patch("services.tools.asset_index_status.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await asset_index_status(ctx)
        
        assert result["success"] is True
        assert result["data"]["is_indexed"] is True
        assert result["data"]["total_assets"] == 150

    async def test_get_status_not_indexed(self, ctx):
        """test_get_status: Reports when not indexed."""
        mock_response = {
            "success": True,
            "data": {
                "is_indexed": False,
                "total_assets": 0
            }
        }
        
        with patch("services.tools.asset_index_status.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await asset_index_status(ctx)
        
        assert result["success"] is True
        assert result["data"]["is_indexed"] is False

    async def test_get_status_with_statistics(self, ctx):
        """test_get_status: Returns detailed statistics."""
        mock_response = {
            "success": True,
            "data": {
                "is_indexed": True,
                "total_assets": 150,
                "by_type": {
                    "textures": 45,
                    "materials": 30,
                    "prefabs": 25,
                    "scenes": 10
                }
            }
        }
        
        with patch("services.tools.asset_index_status.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await asset_index_status(ctx, include_statistics=True)
        
        assert result["success"] is True
        assert "by_type" in result["data"]


# =============================================================================
# Phase 4: Asset Intelligence - find_asset_references
# =============================================================================

@pytest.mark.asyncio
class TestFindAssetReferences:
    """Tests for the find_asset_references tool."""

    async def test_find_references_to_asset(self, ctx):
        """test_find_references_to_asset: Finds assets referencing target."""
        mock_response = {
            "success": True,
            "data": {
                "target_guid": "mat001",
                "target_path": "Assets/Materials/Player.mat",
                "reference_count": 5,
                "references": [
                    {"guid": "prefab001", "path": "Assets/Prefabs/Player.prefab", "type": "prefab"},
                    {"guid": "scene001", "path": "Assets/Scenes/Level1.unity", "type": "scene"},
                ]
            }
        }
        
        with patch("services.tools.find_asset_references.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await find_asset_references(
                ctx, 
                asset_guid="mat001",
                direction="referenced_by"
            )
        
        assert result["success"] is True
        assert result["data"]["reference_count"] == 5

    async def test_find_usage_sites(self, ctx):
        """test_find_usage_sites: Finds specific usage locations."""
        mock_response = {
            "success": True,
            "data": {
                "target_guid": "tex001",
                "usages": [
                    {
                        "container_guid": "mat001",
                        "container_path": "Assets/Materials/Player.mat",
                        "property_path": "m_MainTexture",
                        "component": None
                    },
                    {
                        "container_guid": "prefab001",
                        "container_path": "Assets/Prefabs/Character.prefab",
                        "property_path": "m_Materials.Array.data[0]",
                        "component": "MeshRenderer"
                    }
                ]
            }
        }
        
        with patch("services.tools.find_asset_references.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await find_asset_references(
                ctx, 
                asset_guid="tex001",
                direction="referenced_by",
                include_usage_details=True
            )
        
        assert result["success"] is True
        assert len(result["data"]["usages"]) == 2

    async def test_find_dependencies_of_asset(self, ctx):
        """test_find_references_to_asset: Finds assets target depends on."""
        mock_response = {
            "success": True,
            "data": {
                "target_guid": "prefab001",
                "target_path": "Assets/Prefabs/Character.prefab",
                "dependency_count": 3,
                "dependencies": [
                    {"guid": "mat001", "path": "Assets/Materials/Player.mat", "type": "material"},
                    {"guid": "mesh001", "path": "Assets/Models/Character.fbx", "type": "model"},
                ]
            }
        }
        
        with patch("services.tools.find_asset_references.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await find_asset_references(
                ctx, 
                asset_guid="prefab001",
                direction="depends_on"
            )
        
        assert result["success"] is True
        assert result["data"]["dependency_count"] == 3

    async def test_find_references_by_path(self, ctx):
        """test_find_references_to_asset: Can search by path instead of GUID."""
        mock_response = {
            "success": True,
            "data": {
                "target_path": "Assets/Materials/Player.mat",
                "reference_count": 2
            }
        }
        
        with patch("services.tools.find_asset_references.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await find_asset_references(
                ctx, 
                asset_path="Assets/Materials/Player.mat"
            )
        
        assert result["success"] is True

    async def test_find_references_recursive(self, ctx):
        """test_find_references_to_asset: Supports recursive reference search."""
        mock_response = {
            "success": True,
            "data": {
                "target_guid": "mat001",
                "reference_count": 10,
                "recursive": True,
                "depth": 3
            }
        }
        
        with patch("services.tools.find_asset_references.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await find_asset_references(
                ctx, 
                asset_guid="mat001",
                recursive=True,
                max_depth=3
            )
        
        assert result["success"] is True
        assert result["data"]["recursive"] is True

    async def test_find_circular_references(self, ctx):
        """test_find_references_to_asset: Can detect circular references."""
        mock_response = {
            "success": True,
            "data": {
                "target_guid": "prefab001",
                "circular_references": [
                    ["prefab001", "prefab002", "prefab001"]
                ]
            }
        }
        
        with patch("services.tools.find_asset_references.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await find_asset_references(
                ctx, 
                asset_guid="prefab001",
                detect_circular=True
            )
        
        assert result["success"] is True
        assert "circular_references" in result["data"]


# =============================================================================
# Phase 4: Asset Intelligence - summarize_asset
# =============================================================================

@pytest.mark.asyncio
class TestSummarizeAsset:
    """Tests for the summarize_asset tool."""

    async def test_summarize_prefab(self, ctx, mock_asset_summary):
        """test_summarize_prefab: Generates prefab summary."""
        with patch("services.tools.summarize_asset.send_with_unity_instance",
                   AsyncMock(return_value=mock_asset_summary)):
            result = await summarize_asset(
                ctx, 
                asset_path="Assets/Prefabs/Character.prefab"
            )
        
        assert result["success"] is True
        assert result["data"]["type"] == "prefab"
        assert "summary" in result["data"]
        assert result["data"]["summary"]["child_count"] == 5

    async def test_summarize_material(self, ctx):
        """test_summarize_material: Generates material summary."""
        mock_response = {
            "success": True,
            "data": {
                "guid": "mat001",
                "path": "Assets/Materials/Player.mat",
                "type": "material",
                "summary": {
                    "shader": "Standard",
                    "property_count": 12,
                    "texture_count": 3,
                    "render_queue": 2000
                },
                "properties": {
                    "_Color": {"r": 1, "g": 1, "b": 1, "a": 1},
                    "_MainTex": {"guid": "tex001"}
                }
            }
        }
        
        with patch("services.tools.summarize_asset.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await summarize_asset(
                ctx, 
                asset_path="Assets/Materials/Player.mat"
            )
        
        assert result["success"] is True
        assert result["data"]["type"] == "material"
        assert result["data"]["summary"]["shader"] == "Standard"

    async def test_summarize_texture(self, ctx):
        """test_summarize_texture: Generates texture summary."""
        mock_response = {
            "success": True,
            "data": {
                "guid": "tex001",
                "path": "Assets/Textures/Player_Diffuse.png",
                "type": "texture",
                "summary": {
                    "width": 2048,
                    "height": 2048,
                    "format": "RGBA32",
                    "mips": 11,
                    "memory_size_bytes": 16777216
                },
                "import_settings": {
                    "textureType": "Sprite",
                    "maxTextureSize": 2048,
                    "compression": "DXT5"
                }
            }
        }
        
        with patch("services.tools.summarize_asset.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await summarize_asset(
                ctx, 
                asset_path="Assets/Textures/Player_Diffuse.png"
            )
        
        assert result["success"] is True
        assert result["data"]["type"] == "texture"
        assert result["data"]["summary"]["width"] == 2048

    async def test_summarize_by_guid(self, ctx, mock_asset_summary):
        """test_summarize_prefab: Can summarize by GUID."""
        with patch("services.tools.summarize_asset.send_with_unity_instance",
                   AsyncMock(return_value=mock_asset_summary)):
            result = await summarize_asset(ctx, asset_guid="prefab001")
        
        assert result["success"] is True
        assert result["data"]["guid"] == "prefab001"

    async def test_summarize_requires_path_or_guid(self, ctx):
        """test_summarize_prefab: Requires asset_path or asset_guid."""
        result = await summarize_asset(ctx)
        
        assert result["success"] is False

    async def test_summarize_with_dependencies(self, ctx, mock_asset_summary):
        """test_summarize_prefab: Includes dependencies when requested."""
        with patch("services.tools.summarize_asset.send_with_unity_instance",
                   AsyncMock(return_value=mock_asset_summary)):
            result = await summarize_asset(
                ctx, 
                asset_path="Assets/Prefabs/Character.prefab",
                include_dependencies=True
            )
        
        assert result["success"] is True
        assert "dependencies" in result["data"]

    async def test_summarize_with_size_details(self, ctx):
        """test_summarize_texture: Includes size details when requested."""
        mock_response = {
            "success": True,
            "data": {
                "type": "texture",
                "summary": {"width": 1024, "height": 1024},
                "size_details": {
                    "file_size_bytes": 1048576,
                    "memory_size_bytes": 4194304,
                    "compression_ratio": 0.25
                }
            }
        }
        
        with patch("services.tools.summarize_asset.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await summarize_asset(
                ctx, 
                asset_path="Assets/Textures/Test.png",
                include_size_details=True
            )
        
        assert result["success"] is True
        assert "size_details" in result["data"]
