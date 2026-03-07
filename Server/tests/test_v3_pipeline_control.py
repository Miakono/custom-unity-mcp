"""Validation tests for V3 Pipeline Control tools (Phase 6).

Tests for:
- manage_build_settings
- manage_player_settings
- manage_define_symbols
- manage_import_pipeline
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.tools.manage_build_settings import manage_build_settings
from services.tools.manage_player_settings import manage_player_settings
from services.tools.manage_define_symbols import manage_define_symbols
from services.tools.manage_import_pipeline import manage_import_pipeline
from tests.integration.test_helpers import DummyContext


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def ctx():
    """Provide a dummy context for testing."""
    return DummyContext()


@pytest.fixture
def mock_build_settings():
    """Provide mock build settings data."""
    return {
        "success": True,
        "data": {
            "targetPlatform": "StandaloneWindows64",
            "scenes": [
                {"path": "Assets/Scenes/MainMenu.unity", "enabled": True},
                {"path": "Assets/Scenes/Level1.unity", "enabled": True},
                {"path": "Assets/Scenes/Level2.unity", "enabled": False}
            ],
            "outputPath": "Builds/Windows",
            "options": {
                "developmentBuild": False,
                "scriptDebugging": False
            }
        }
    }


# =============================================================================
# Phase 6: Pipeline Control - manage_build_settings
# =============================================================================

@pytest.mark.asyncio
class TestManageBuildSettings:
    """Tests for the manage_build_settings tool."""

    async def test_get_build_settings(self, ctx, mock_build_settings):
        """test_get_build_settings: Retrieves current build settings."""
        with patch("services.tools.manage_build_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_build_settings)):
            result = await manage_build_settings(ctx, action="get_build_settings")
        
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["targetPlatform"] == "StandaloneWindows64"

    async def test_get_scenes_in_build(self, ctx):
        """test_get_build_settings: Lists scenes in build."""
        mock_response = {
            "success": True,
            "data": {
                "scenes": [
                    {"path": "Assets/Scenes/Main.unity", "enabled": True, "buildIndex": 0},
                    {"path": "Assets/Scenes/Level1.unity", "enabled": True, "buildIndex": 1}
                ]
            }
        }
        
        with patch("services.tools.manage_build_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_build_settings(ctx, action="get_scenes_in_build")
        
        assert result["success"] is True
        assert len(result["data"]["scenes"]) == 2

    async def test_update_build_settings(self, ctx):
        """test_update_build_settings: Updates build settings."""
        mock_response = {
            "success": True,
            "data": {"updated": True}
        }
        
        settings = {"developmentBuild": True, "scriptDebugging": True}
        
        with patch("services.tools.manage_build_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_build_settings(
                ctx, 
                action="set_build_settings",
                settings=settings
            )
        
        assert result["success"] is True

    async def test_add_scene_to_build(self, ctx):
        """test_update_build_settings: Adds scene to build list."""
        mock_response = {
            "success": True,
            "data": {"added": True, "path": "Assets/Scenes/NewLevel.unity"}
        }
        
        with patch("services.tools.manage_build_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_build_settings(
                ctx, 
                action="add_scene_to_build",
                scene_path="Assets/Scenes/NewLevel.unity",
                scene_enabled=True
            )
        
        assert result["success"] is True

    async def test_remove_scene_from_build(self, ctx):
        """test_update_build_settings: Removes scene from build."""
        mock_response = {
            "success": True,
            "data": {"removed": True, "path": "Assets/Scenes/OldLevel.unity"}
        }
        
        with patch("services.tools.manage_build_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_build_settings(
                ctx, 
                action="remove_scene_from_build",
                scene_path="Assets/Scenes/OldLevel.unity"
            )
        
        assert result["success"] is True

    async def test_set_build_platform(self, ctx):
        """test_update_build_settings: Changes target platform."""
        mock_response = {
            "success": True,
            "data": {"platform_changed": True, "new_platform": "Android"}
        }
        
        with patch("services.tools.manage_build_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_build_settings(
                ctx, 
                action="set_build_platform",
                target_platform="Android"
            )
        
        assert result["success"] is True
        assert result["data"]["new_platform"] == "Android"

    async def test_set_build_platform_high_risk(self, ctx):
        """test_update_build_settings: Platform switch is high-risk operation."""
        # This test documents that platform switching may trigger lengthy reimport
        mock_response = {
            "success": True,
            "data": {
                "platform_changed": True, 
                "new_platform": "iOS",
                "warning": "Platform switch will trigger asset reimport"
            }
        }
        
        with patch("services.tools.manage_build_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_build_settings(
                ctx, 
                action="set_build_platform",
                target_platform="iOS"
            )
        
        assert result["success"] is True

    async def test_update_output_path(self, ctx):
        """test_update_build_settings: Updates build output path."""
        mock_response = {
            "success": True,
            "data": {"output_path_updated": True}
        }
        
        with patch("services.tools.manage_build_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_build_settings(
                ctx, 
                action="set_build_settings",
                output_path="Builds/Release"
            )
        
        assert result["success"] is True


# =============================================================================
# Phase 6: Pipeline Control - manage_player_settings
# =============================================================================

@pytest.mark.asyncio
class TestManagePlayerSettings:
    """Tests for the manage_player_settings tool."""

    async def test_get_player_settings(self, ctx):
        """test_get_player_settings: Retrieves player settings."""
        mock_response = {
            "success": True,
            "data": {
                "companyName": "MyCompany",
                "productName": "MyGame",
                "bundleVersion": "1.0.0",
                "bundleIdentifier": "com.mycompany.mygame",
                "scriptingBackend": "IL2CPP",
                "apiCompatibilityLevel": ".NET Standard 2.1"
            }
        }
        
        with patch("services.tools.manage_player_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_player_settings(ctx, action="get_settings")
        
        assert result["success"] is True
        assert result["data"]["productName"] == "MyGame"

    async def test_update_player_settings(self, ctx):
        """test_update_player_settings: Updates player settings."""
        mock_response = {
            "success": True,
            "data": {"updated": True}
        }
        
        settings = {"productName": "NewGameName", "bundleVersion": "1.1.0"}
        
        with patch("services.tools.manage_player_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_player_settings(
                ctx, 
                action="set_settings",
                settings=settings
            )
        
        assert result["success"] is True

    async def test_get_resolution_settings(self, ctx):
        """test_get_player_settings: Gets resolution settings."""
        mock_response = {
            "success": True,
            "data": {
                "defaultResolution": {"width": 1920, "height": 1080},
                "fullscreenMode": "FullScreenWindow",
                "resizableWindow": True
            }
        }
        
        with patch("services.tools.manage_player_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_player_settings(ctx, action="get_resolution_settings")
        
        assert result["success"] is True
        assert result["data"]["defaultResolution"]["width"] == 1920

    async def test_update_resolution_settings(self, ctx):
        """test_update_player_settings: Updates resolution settings."""
        mock_response = {
            "success": True,
            "data": {"updated": True}
        }
        
        with patch("services.tools.manage_player_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_player_settings(
                ctx, 
                action="set_resolution_settings",
                resolution={"width": 2560, "height": 1440}
            )
        
        assert result["success"] is True

    async def test_get_splash_screen_settings(self, ctx):
        """test_get_player_settings: Gets splash screen settings."""
        mock_response = {
            "success": True,
            "data": {
                "showSplashScreen": True,
                "showUnityLogo": False,
                "splashStyle": "DarkOnLight"
            }
        }
        
        with patch("services.tools.manage_player_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_player_settings(ctx, action="get_splash_settings")
        
        assert result["success"] is True

    async def test_get_icon_settings(self, ctx):
        """test_get_player_settings: Gets application icon settings."""
        mock_response = {
            "success": True,
            "data": {
                "icons": [
                    {"size": 128, "path": "Assets/Icons/icon_128.png"},
                    {"size": 256, "path": "Assets/Icons/icon_256.png"}
                ]
            }
        }
        
        with patch("services.tools.manage_player_settings.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_player_settings(ctx, action="get_icon_settings")
        
        assert result["success"] is True
        assert len(result["data"]["icons"]) == 2


# =============================================================================
# Phase 6: Pipeline Control - manage_define_symbols
# =============================================================================

@pytest.mark.asyncio
class TestManageDefineSymbols:
    """Tests for the manage_define_symbols tool."""

    async def test_get_symbols(self, ctx):
        """test_get_symbols: Retrieves current define symbols."""
        mock_response = {
            "success": True,
            "data": {
                "symbols": ["DEBUG", "ENABLE_CHEATS", "USE_ADS"],
                "target": "Standalone"
            }
        }
        
        with patch("services.tools.manage_define_symbols.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_define_symbols(ctx, action="get_symbols")
        
        assert result["success"] is True
        assert "DEBUG" in result["data"]["symbols"]

    async def test_get_symbols_by_target(self, ctx):
        """test_get_symbols: Gets symbols for specific build target."""
        mock_response = {
            "success": True,
            "data": {
                "symbols": ["MOBILE", "TOUCH_INPUT"],
                "target": "Android"
            }
        }
        
        with patch("services.tools.manage_define_symbols.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_define_symbols(
                ctx, 
                action="get_symbols",
                build_target="Android"
            )
        
        assert result["success"] is True
        assert result["data"]["target"] == "Android"

    async def test_add_symbol(self, ctx):
        """test_add_symbol: Adds a define symbol."""
        mock_response = {
            "success": True,
            "data": {
                "added": True,
                "symbol": "NEW_FEATURE",
                "symbols": ["DEBUG", "NEW_FEATURE"]
            }
        }
        
        with patch("services.tools.manage_define_symbols.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_define_symbols(
                ctx, 
                action="add_symbol",
                symbol="NEW_FEATURE"
            )
        
        assert result["success"] is True
        assert "NEW_FEATURE" in result["data"]["symbols"]

    async def test_add_duplicate_symbol(self, ctx):
        """test_add_symbol: Handles duplicate symbol gracefully."""
        mock_response = {
            "success": True,
            "data": {
                "added": False,
                "message": "Symbol already exists",
                "symbol": "DEBUG"
            }
        }
        
        with patch("services.tools.manage_define_symbols.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_define_symbols(
                ctx, 
                action="add_symbol",
                symbol="DEBUG"
            )
        
        assert result["success"] is True

    async def test_remove_symbol(self, ctx):
        """test_remove_symbol: Removes a define symbol."""
        mock_response = {
            "success": True,
            "data": {
                "removed": True,
                "symbol": "ENABLE_CHEATS",
                "symbols": ["DEBUG"]
            }
        }
        
        with patch("services.tools.manage_define_symbols.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_define_symbols(
                ctx, 
                action="remove_symbol",
                symbol="ENABLE_CHEATS"
            )
        
        assert result["success"] is True
        assert "ENABLE_CHEATS" not in result["data"]["symbols"]

    async def test_remove_nonexistent_symbol(self, ctx):
        """test_remove_symbol: Handles non-existent symbol gracefully."""
        mock_response = {
            "success": True,
            "data": {
                "removed": False,
                "message": "Symbol not found",
                "symbol": "MISSING"
            }
        }
        
        with patch("services.tools.manage_define_symbols.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_define_symbols(
                ctx, 
                action="remove_symbol",
                symbol="MISSING"
            )
        
        assert result["success"] is True

    async def test_set_all_symbols(self, ctx):
        """test_get_symbols: Can set all symbols at once."""
        mock_response = {
            "success": True,
            "data": {
                "symbols": ["RELEASE", "OPTIMIZED"]
            }
        }
        
        with patch("services.tools.manage_define_symbols.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_define_symbols(
                ctx, 
                action="set_symbols",
                symbols=["RELEASE", "OPTIMIZED"]
            )
        
        assert result["success"] is True
        assert result["data"]["symbols"] == ["RELEASE", "OPTIMIZED"]

    async def test_clear_all_symbols(self, ctx):
        """test_remove_symbol: Can clear all symbols."""
        mock_response = {
            "success": True,
            "data": {"cleared": True, "symbols": []}
        }
        
        with patch("services.tools.manage_define_symbols.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_define_symbols(ctx, action="clear_symbols")
        
        assert result["success"] is True
        assert len(result["data"]["symbols"]) == 0


# =============================================================================
# Phase 6: Pipeline Control - manage_import_pipeline
# =============================================================================

@pytest.mark.asyncio
class TestManageImportPipeline:
    """Tests for the manage_import_pipeline tool."""

    async def test_get_import_queue(self, ctx):
        """test_get_import_queue: Retrieves current import queue status."""
        mock_response = {
            "success": True,
            "data": {
                "is_refreshing": True,
                "queue_length": 15,
                "current_item": "Assets/Textures/LargeTexture.png",
                "estimated_seconds_remaining": 30
            }
        }
        
        with patch("services.tools.manage_import_pipeline.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_import_pipeline(ctx, action="get_queue")
        
        assert result["success"] is True
        assert result["data"]["queue_length"] == 15

    async def test_get_import_queue_empty(self, ctx):
        """test_get_import_queue: Handles empty queue."""
        mock_response = {
            "success": True,
            "data": {
                "is_refreshing": False,
                "queue_length": 0,
                "current_item": None
            }
        }
        
        with patch("services.tools.manage_import_pipeline.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_import_pipeline(ctx, action="get_queue")
        
        assert result["success"] is True
        assert result["data"]["queue_length"] == 0

    async def test_force_reimport(self, ctx):
        """test_force_reimport: Forces reimport of specific assets."""
        mock_response = {
            "success": True,
            "data": {
                "reimported": True,
                "assets": ["Assets/Textures/Wall.png", "Assets/Materials/Wall.mat"]
            }
        }
        
        with patch("services.tools.manage_import_pipeline.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_import_pipeline(
                ctx, 
                action="force_reimport",
                asset_paths=["Assets/Textures/Wall.png", "Assets/Materials/Wall.mat"]
            )
        
        assert result["success"] is True
        assert len(result["data"]["assets"]) == 2

    async def test_force_reimport_by_type(self, ctx):
        """test_force_reimport: Reimports assets by type."""
        mock_response = {
            "success": True,
            "data": {
                "reimported": True,
                "asset_type": "texture",
                "count": 25
            }
        }
        
        with patch("services.tools.manage_import_pipeline.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_import_pipeline(
                ctx, 
                action="force_reimport_by_type",
                asset_type="texture"
            )
        
        assert result["success"] is True
        assert result["data"]["count"] == 25

    async def test_stop_refresh(self, ctx):
        """test_get_import_queue: Can stop ongoing refresh."""
        mock_response = {
            "success": True,
            "data": {"stopped": True}
        }
        
        with patch("services.tools.manage_import_pipeline.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_import_pipeline(ctx, action="stop_refresh")
        
        assert result["success"] is True
        assert result["data"]["stopped"] is True

    async def test_refresh_asset_database(self, ctx):
        """test_force_reimport: Refreshes entire asset database."""
        mock_response = {
            "success": True,
            "data": {"refreshed": True}
        }
        
        with patch("services.tools.manage_import_pipeline.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_import_pipeline(ctx, action="refresh")
        
        assert result["success"] is True

    async def test_get_importer_settings(self, ctx):
        """test_get_import_queue: Gets importer settings for asset."""
        mock_response = {
            "success": True,
            "data": {
                "asset_path": "Assets/Textures/Player.png",
                "importer_type": "TextureImporter",
                "settings": {
                    "textureType": "Sprite",
                    "spriteMode": "Single",
                    "maxTextureSize": 2048
                }
            }
        }
        
        with patch("services.tools.manage_import_pipeline.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_import_pipeline(
                ctx, 
                action="get_importer_settings",
                asset_path="Assets/Textures/Player.png"
            )
        
        assert result["success"] is True
        assert result["data"]["importer_type"] == "TextureImporter"

    async def test_set_importer_settings(self, ctx):
        """test_force_reimport: Updates importer settings."""
        mock_response = {
            "success": True,
            "data": {
                "updated": True,
                "asset_path": "Assets/Textures/Player.png"
            }
        }
        
        settings = {"maxTextureSize": 1024, "compression": "DXT5"}
        
        with patch("services.tools.manage_import_pipeline.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_import_pipeline(
                ctx, 
                action="set_importer_settings",
                asset_path="Assets/Textures/Player.png",
                settings=settings
            )
        
        assert result["success"] is True

    async def test_cancel_import(self, ctx):
        """test_get_import_queue: Cancels specific import operation."""
        mock_response = {
            "success": True,
            "data": {"cancelled": True}
        }
        
        with patch("services.tools.manage_import_pipeline.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await manage_import_pipeline(ctx, action="cancel_import")
        
        assert result["success"] is True
