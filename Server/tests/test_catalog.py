import json
from typing import Literal

import pytest

import services.catalog as catalog_module
from services.catalog import build_tool_catalog, export_tool_catalog_artifacts
from services.registry import mcp_for_unity_tool
import services.registry.tool_registry as tool_registry_module


@pytest.fixture(autouse=True)
def restore_tool_registry_state():
    original_registry = list(tool_registry_module._tool_registry)
    try:
        yield
    finally:
        tool_registry_module._tool_registry[:] = original_registry


def _register_minimal_toolset():
    @mcp_for_unity_tool(unity_target=None, group=None)
    def _manage_tools():
        return None

    @mcp_for_unity_tool(group="core")
    def _manage_scene():
        return None

    @mcp_for_unity_tool(group="testing")
    def _run_tests():
        return None

    @mcp_for_unity_tool(name="manage_ui", group="ui")
    def _manage_ui(action: Literal["read", "create"], panel: str | None = None):
        return None


def test_build_tool_catalog_infers_capabilities():
    _register_minimal_toolset()

    catalog = build_tool_catalog()

    assert catalog["generated_from"] == "live_tool_registry"
    assert catalog["tool_count"] >= 4

    core_tool = next(item for item in catalog["tools"] if item["name"] == "_manage_scene")
    assert core_tool["group"] == "core"
    assert core_tool["capabilities"]["action_model"] == "unknown"
    assert core_tool["capabilities"]["mutating"] is True
    assert core_tool["capabilities"]["requires_unity"] is True

    meta_tool = next(item for item in catalog["tools"] if item["name"] == "_manage_tools")
    assert meta_tool["capabilities"]["server_only"] is True
    assert meta_tool["default_enabled"] is True

    ui_tool = next(item for item in catalog["tools"] if item["name"] == "manage_ui")
    assert ui_tool["supported_actions"] == ["create", "read"]
    assert ui_tool["action_capabilities"]["read"]["read_only"] is True
    assert ui_tool["action_capabilities"]["create"]["mutating"] is True
    assert any(
        param["name"] == "action" and param["type"] == "enum"
        for param in ui_tool["parameters"]
    )
    assert any(
        param["name"] == "panel" and param["type"] == "string"
        for param in ui_tool["parameters"]
    )


def test_export_tool_catalog_artifacts_writes_expected_files(tmp_path):
    _register_minimal_toolset()

    result = export_tool_catalog_artifacts(tmp_path)

    assert result["tool_count"] >= 4
    assert len(result["written_files"]) == 2

    catalog_path = tmp_path / "tool_catalog.json"
    readme_path = tmp_path / "README.md"
    assert catalog_path.exists()
    assert readme_path.exists()

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert catalog["tool_count"] >= 4
    assert any(item["name"] == "_manage_scene" for item in catalog["tools"])
    assert any(item["name"] == "manage_ui" for item in catalog["tools"])
    readme = readme_path.read_text(encoding="utf-8")
    assert "Unity MCP Tool Catalog" in readme
    assert "Supported actions: `create`, `read`" in readme
    assert "`action`: type=`enum`, required=`true`, enum=`create`, `read`" in readme
    assert "`create`: read_only=`false`, mutating=`true`, high_risk=`true`" in readme


def test_build_tool_catalog_bootstraps_registry_when_empty(monkeypatch):
    tool_registry_module._tool_registry.clear()
    called = False

    def fake_ensure() -> int:
        nonlocal called
        called = True

        @mcp_for_unity_tool(group="core")
        def _bootstrapped_tool():
            return None

        return 1

    monkeypatch.setattr(catalog_module, "ensure_tool_registry_populated", fake_ensure)

    catalog = build_tool_catalog()

    assert called is True
    assert any(item["name"] == "_bootstrapped_tool" for item in catalog["tools"])
