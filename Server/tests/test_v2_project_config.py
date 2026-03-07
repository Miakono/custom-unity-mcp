"""Tests for V2 project configuration tools.

Covers 9 tools:
- manage_project_settings
- manage_editor_settings
- manage_registry_config
- analyze_asset_dependencies
- manage_asset_import_settings
- list_shaders
- find_builtin_assets
- get_component_types
- get_object_references
"""

import inspect
from unittest.mock import AsyncMock

import pytest

from services.tools.manage_project_settings import manage_project_settings
from services.tools.manage_editor_settings import manage_editor_settings
from services.tools.manage_registry_config import manage_registry_config
from services.tools.analyze_asset_dependencies import analyze_asset_dependencies
from services.tools.manage_asset_import_settings import manage_asset_import_settings
from services.tools.list_shaders import list_shaders
from services.tools.find_builtin_assets import find_builtin_assets
from services.tools.get_component_types import get_component_types
from services.tools.get_object_references import get_object_references
from tests.integration.test_helpers import DummyContext


# =============================================================================
# manage_project_settings Tests
# =============================================================================
class TestManageProjectSettings:
    """Tests for manage_project_settings tool."""

    def test_tool_interface(self):
        """Test tool has correct interface."""
        sig = inspect.signature(manage_project_settings)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "settings_category" in sig.parameters
        assert "settings" in sig.parameters
        assert "platform" in sig.parameters

    @pytest.mark.asyncio
    async def test_get_settings(self, monkeypatch):
        """Test getting project settings."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "companyName": "Test Company",
                    "productName": "Test Game",
                    "version": "1.0.0",
                },
            }

        monkeypatch.setattr(
            "services.tools.manage_project_settings.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_project_settings.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_project_settings.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_project_settings(
            DummyContext(),
            action="get_settings",
            settings_category="player",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "get_settings"
        assert captured["params"]["settingsCategory"] == "player"

    @pytest.mark.asyncio
    async def test_update_settings(self, monkeypatch):
        """Test updating project settings."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "message": "Settings updated"}

        monkeypatch.setattr(
            "services.tools.manage_project_settings.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_project_settings.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_project_settings.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_project_settings(
            DummyContext(),
            action="update_settings",
            settings_category="player",
            settings={"companyName": "New Company"},
        )

        assert resp["success"] is True
        assert captured["params"]["settings"]["companyName"] == "New Company"

    @pytest.mark.asyncio
    async def test_get_build_settings(self, monkeypatch):
        """Test getting build settings."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "scenes": ["Assets/Scenes/Main.unity"],
                    "platform": "StandaloneWindows64",
                },
            }

        monkeypatch.setattr(
            "services.tools.manage_project_settings.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_project_settings.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_project_settings.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_project_settings(
            DummyContext(),
            action="get_build_settings",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "get_build_settings"

    @pytest.mark.asyncio
    async def test_error_handling(self, monkeypatch):
        """Test error handling."""

        async def fake_send(*args, **kwargs):
            raise RuntimeError("Unity error")

        monkeypatch.setattr(
            "services.tools.manage_project_settings.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_project_settings.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_project_settings.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_project_settings(
            DummyContext(),
            action="get_settings",
        )

        assert resp["success"] is False
        assert "Error managing project settings" in resp["message"]


# =============================================================================
# manage_editor_settings Tests
# =============================================================================
class TestManageEditorSettings:
    """Tests for manage_editor_settings tool."""

    def test_tool_interface(self):
        """Test tool has correct interface."""
        sig = inspect.signature(manage_editor_settings)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "preference_category" in sig.parameters
        assert "preferences" in sig.parameters

    @pytest.mark.asyncio
    async def test_get_preferences(self, monkeypatch):
        """Test getting editor preferences."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "autoRefresh": True,
                    "autoSave": False,
                },
            }

        monkeypatch.setattr(
            "services.tools.manage_editor_settings.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_editor_settings.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_editor_settings.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_editor_settings(
            DummyContext(),
            action="get_preferences",
            preference_category="general",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "get_preferences"

    @pytest.mark.asyncio
    async def test_update_preferences(self, monkeypatch):
        """Test updating editor preferences."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "message": "Preferences updated"}

        monkeypatch.setattr(
            "services.tools.manage_editor_settings.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_editor_settings.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_editor_settings.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_editor_settings(
            DummyContext(),
            action="update_preferences",
            preference_category="general",
            preferences={"autoRefresh": False},
        )

        assert resp["success"] is True
        assert captured["params"]["preferences"]["autoRefresh"] is False


# =============================================================================
# manage_registry_config Tests
# =============================================================================
class TestManageRegistryConfig:
    """Tests for manage_registry_config tool."""

    def test_tool_interface(self):
        """Test tool has correct interface."""
        sig = inspect.signature(manage_registry_config)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "registry_name" in sig.parameters
        assert "registry_url" in sig.parameters
        assert "scopes" in sig.parameters

    @pytest.mark.asyncio
    async def test_list_scoped_registries(self, monkeypatch):
        """Test listing scoped registries."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "registries": [
                        {
                            "name": "MyRegistry",
                            "url": "https://npm.example.com",
                            "scopes": ["com.mycompany"],
                        }
                    ]
                },
            }

        monkeypatch.setattr(
            "services.tools.manage_registry_config.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_registry_config.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_registry_config.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_registry_config(
            DummyContext(),
            action="list_scoped_registries",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "list_scoped_registries"

    @pytest.mark.asyncio
    async def test_add_registry(self, monkeypatch):
        """Test adding a scoped registry."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "message": "Registry added"}

        monkeypatch.setattr(
            "services.tools.manage_registry_config.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_registry_config.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_registry_config.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_registry_config(
            DummyContext(),
            action="add_registry",
            registry_name="NewRegistry",
            registry_url="https://npm.new.com",
            scopes=["com.newcompany"],
        )

        assert resp["success"] is True
        assert captured["params"]["registryName"] == "NewRegistry"
        assert captured["params"]["registryUrl"] == "https://npm.new.com"
        assert captured["params"]["scopes"] == ["com.newcompany"]


# =============================================================================
# analyze_asset_dependencies Tests
# =============================================================================
class TestAnalyzeAssetDependencies:
    """Tests for analyze_asset_dependencies tool."""

    def test_tool_interface(self):
        """Test tool has correct interface."""
        sig = inspect.signature(analyze_asset_dependencies)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "asset_path" in sig.parameters
        assert "asset_guid" in sig.parameters

    @pytest.mark.asyncio
    async def test_get_dependencies(self, monkeypatch):
        """Test getting asset dependencies."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "dependencies": [
                        "Assets/Scripts/PlayerController.cs",
                        "Assets/Materials/Red.mat",
                    ]
                },
            }

        monkeypatch.setattr(
            "services.tools.analyze_asset_dependencies.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.analyze_asset_dependencies.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.analyze_asset_dependencies.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await analyze_asset_dependencies(
            DummyContext(),
            action="get_dependencies",
            asset_path="Assets/Prefabs/Player.prefab",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "get_dependencies"
        assert captured["params"]["assetPath"] == "Assets/Prefabs/Player.prefab"

    @pytest.mark.asyncio
    async def test_get_dependencies_requires_path_or_guid(self):
        """Test that get_dependencies requires asset_path or asset_guid."""
        resp = await analyze_asset_dependencies(
            DummyContext(),
            action="get_dependencies",
        )

        assert resp["success"] is False
        assert "requires either asset_path or asset_guid" in resp["message"]

    @pytest.mark.asyncio
    async def test_analyze_circular(self, monkeypatch):
        """Test analyzing circular dependencies."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "data": {"circular": []}}

        monkeypatch.setattr(
            "services.tools.analyze_asset_dependencies.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.analyze_asset_dependencies.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.analyze_asset_dependencies.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await analyze_asset_dependencies(
            DummyContext(),
            action="analyze_circular",
            search_scope="Assets/Scripts",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "analyze_circular"


# =============================================================================
# manage_asset_import_settings Tests
# =============================================================================
class TestManageAssetImportSettings:
    """Tests for manage_asset_import_settings tool."""

    def test_tool_interface(self):
        """Test tool has correct interface."""
        sig = inspect.signature(manage_asset_import_settings)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "asset_path" in sig.parameters
        assert "settings" in sig.parameters

    @pytest.mark.asyncio
    async def test_get_import_settings(self, monkeypatch):
        """Test getting import settings."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "textureType": "Sprite (2D and UI)",
                    "maxSize": 2048,
                },
            }

        monkeypatch.setattr(
            "services.tools.manage_asset_import_settings.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_asset_import_settings.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_asset_import_settings.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_asset_import_settings(
            DummyContext(),
            action="get_import_settings",
            asset_path="Assets/Textures/Sprite.png",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "get_import_settings"

    @pytest.mark.asyncio
    async def test_update_import_settings(self, monkeypatch):
        """Test updating import settings."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "message": "Import settings updated"}

        monkeypatch.setattr(
            "services.tools.manage_asset_import_settings.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_asset_import_settings.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_asset_import_settings.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_asset_import_settings(
            DummyContext(),
            action="update_import_settings",
            asset_path="Assets/Models/Character.fbx",
            settings={"scaleFactor": 0.01, "importAnimation": False},
        )

        assert resp["success"] is True
        assert captured["params"]["settings"]["scaleFactor"] == 0.01

    @pytest.mark.asyncio
    async def test_requires_asset_path(self, monkeypatch):
        """Test that asset_path is required - empty path should be rejected."""
        monkeypatch.setattr(
            "services.tools.manage_asset_import_settings.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_asset_import_settings.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_asset_import_settings(
            DummyContext(),
            action="get_import_settings",
            asset_path="",  # Empty path
        )

        assert resp["success"] is False
        assert "asset_path" in resp["message"].lower()


# =============================================================================
# list_shaders Tests
# =============================================================================
class TestListShaders:
    """Tests for list_shaders tool."""

    def test_tool_interface(self):
        """Test tool has correct interface."""
        sig = inspect.signature(list_shaders)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "shader_name" in sig.parameters
        assert "search_pattern" in sig.parameters

    @pytest.mark.asyncio
    async def test_list_builtin_shaders(self, monkeypatch):
        """Test listing built-in shaders."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "shaders": [
                        {"name": "Standard"},
                        {"name": "Unlit/Color"},
                        {"name": "Sprites/Default"},
                    ]
                },
            }

        monkeypatch.setattr(
            "services.tools.list_shaders.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.list_shaders.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.list_shaders.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await list_shaders(
            DummyContext(),
            action="list_builtin",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "list_builtin"

    @pytest.mark.asyncio
    async def test_get_shader_info_requires_name(self):
        """Test that get_shader_info requires shader_name."""
        resp = await list_shaders(
            DummyContext(),
            action="get_shader_info",
        )

        assert resp["success"] is False
        assert "requires shader_name parameter" in resp["message"]

    @pytest.mark.asyncio
    async def test_list_custom_shaders(self, monkeypatch):
        """Test listing custom shaders."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {"shaders": [{"name": "Custom/MyShader"}]},
            }

        monkeypatch.setattr(
            "services.tools.list_shaders.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.list_shaders.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.list_shaders.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await list_shaders(
            DummyContext(),
            action="list_custom",
            folder_path="Assets/Shaders",
        )

        assert resp["success"] is True
        assert captured["params"]["folderPath"] == "Assets/Shaders"


# =============================================================================
# find_builtin_assets Tests
# =============================================================================
class TestFindBuiltinAssets:
    """Tests for find_builtin_assets tool."""

    def test_tool_interface(self):
        """Test tool has correct interface."""
        sig = inspect.signature(find_builtin_assets)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "search_pattern" in sig.parameters
        assert "asset_type" in sig.parameters

    @pytest.mark.asyncio
    async def test_search_builtin_assets(self, monkeypatch):
        """Test searching built-in assets."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "assets": [
                        {"name": "Default-Diffuse", "type": "material"},
                        {"name": "Default-Specular", "type": "material"},
                    ]
                },
            }

        monkeypatch.setattr(
            "services.tools.find_builtin_assets.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.find_builtin_assets.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.find_builtin_assets.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await find_builtin_assets(
            DummyContext(),
            action="search",
            search_pattern="Default",
        )

        assert resp["success"] is True
        assert captured["params"]["searchPattern"] == "Default"

    @pytest.mark.asyncio
    async def test_list_by_type(self, monkeypatch):
        """Test listing built-in assets by type."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "assets": [
                        {"name": "Cube", "type": "mesh"},
                        {"name": "Sphere", "type": "mesh"},
                    ]
                },
            }

        monkeypatch.setattr(
            "services.tools.find_builtin_assets.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.find_builtin_assets.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.find_builtin_assets.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await find_builtin_assets(
            DummyContext(),
            action="list_by_type",
            asset_type="mesh",
        )

        assert resp["success"] is True
        assert captured["params"]["assetType"] == "mesh"


# =============================================================================
# get_component_types Tests
# =============================================================================
class TestGetComponentTypes:
    """Tests for get_component_types tool."""

    def test_tool_interface(self):
        """Test tool has correct interface."""
        sig = inspect.signature(get_component_types)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "component_name" in sig.parameters
        assert "namespace" in sig.parameters

    @pytest.mark.asyncio
    async def test_list_all_components(self, monkeypatch):
        """Test listing all component types."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "components": [
                        {"name": "Transform", "namespace": "UnityEngine"},
                        {"name": "Rigidbody", "namespace": "UnityEngine"},
                    ]
                },
            }

        monkeypatch.setattr(
            "services.tools.get_component_types.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.get_component_types.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.get_component_types.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await get_component_types(
            DummyContext(),
            action="list_all",
            max_results=100,
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "list_all"

    @pytest.mark.asyncio
    async def test_search_components(self, monkeypatch):
        """Test searching for component types."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "components": [
                        {"name": "BoxCollider", "namespace": "UnityEngine"},
                        {"name": "SphereCollider", "namespace": "UnityEngine"},
                    ]
                },
            }

        monkeypatch.setattr(
            "services.tools.get_component_types.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.get_component_types.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.get_component_types.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await get_component_types(
            DummyContext(),
            action="search",
            component_name="Collider",
        )

        assert resp["success"] is True
        assert captured["params"]["componentName"] == "Collider"

    @pytest.mark.asyncio
    async def test_search_requires_component_name(self):
        """Test that search action requires component_name."""
        resp = await get_component_types(
            DummyContext(),
            action="search",
        )

        assert resp["success"] is False
        assert "requires component_name parameter" in resp["message"]


# =============================================================================
# get_object_references Tests
# =============================================================================
class TestGetObjectReferences:
    """Tests for get_object_references tool."""

    def test_tool_interface(self):
        """Test tool has correct interface."""
        sig = inspect.signature(get_object_references)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "target" in sig.parameters
        assert "search_scope" in sig.parameters

    @pytest.mark.asyncio
    async def test_get_references(self, monkeypatch):
        """Test getting object references."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "references": [
                        {"name": "Player", "path": "Assets/Player.prefab"},
                    ]
                },
            }

        monkeypatch.setattr(
            "services.tools.get_object_references.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.get_object_references.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.get_object_references.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await get_object_references(
            DummyContext(),
            action="get_references",
            target="Assets/Materials/Red.mat",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "get_references"
        assert captured["params"]["target"] == "Assets/Materials/Red.mat"

    @pytest.mark.asyncio
    async def test_get_referenced_by(self, monkeypatch):
        """Test getting objects referenced by target."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "referencedBy": [
                        {"component": "MeshRenderer", "material": "Red.mat"},
                    ]
                },
            }

        monkeypatch.setattr(
            "services.tools.get_object_references.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.get_object_references.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.get_object_references.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await get_object_references(
            DummyContext(),
            action="get_referenced_by",
            target="Player",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "get_referenced_by"

    @pytest.mark.asyncio
    async def test_requires_target(self, monkeypatch):
        """Test that target parameter is required - empty target should be rejected."""
        monkeypatch.setattr(
            "services.tools.get_object_references.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.get_object_references.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await get_object_references(
            DummyContext(),
            action="get_references",
            target="",  # Empty target
        )

        assert resp["success"] is False
        assert "target" in resp["message"].lower()


# =============================================================================
# Error Handling Tests (Common across all tools)
# =============================================================================
class TestProjectConfigErrorHandling:
    """Common error handling tests for all project config tools."""

    @pytest.mark.asyncio
    async def test_preflight_can_block_execution(self, monkeypatch):
        """Test that preflight can block tool execution."""
        class FakeGateResponse:
            def model_dump(self):
                return {"success": False, "message": "Gate blocked", "error_code": "PREFLIGHT_BLOCKED"}

        monkeypatch.setattr(
            "services.tools.manage_project_settings.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_project_settings.maybe_run_tool_preflight",
            AsyncMock(return_value=FakeGateResponse()),
        )

        resp = await manage_project_settings(
            DummyContext(),
            action="get_settings",
        )

        assert resp["success"] is False
        assert resp["message"] == "Gate blocked"
