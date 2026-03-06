import json

import pytest

import services.subagents as subagents_module
from services.registry import mcp_for_unity_tool
import services.registry.tool_registry as tool_registry_module
from services.subagents import build_subagent_catalog, export_subagent_artifacts


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

    @mcp_for_unity_tool(unity_target=None, group=None)
    def _set_active_instance():
        return None

    @mcp_for_unity_tool(group="core")
    def _manage_scene():
        return None

    @mcp_for_unity_tool(group="vfx")
    def _manage_vfx():
        return None

    @mcp_for_unity_tool(group="animation")
    def _manage_animation():
        return None

    @mcp_for_unity_tool(group="ui")
    def _manage_ui():
        return None

    @mcp_for_unity_tool(group="scripting_ext")
    def _manage_scriptable_object():
        return None

    @mcp_for_unity_tool(group="testing")
    def _run_tests():
        return None


def test_build_subagent_catalog_includes_orchestrator_and_specialists():
    _register_minimal_toolset()

    catalog = build_subagent_catalog()

    assert catalog["generated_from"] == "live_tool_registry"
    assert catalog["subagent_count"] == 7

    orchestrator = next(item for item in catalog["subagents"] if item["id"] == "unity-orchestrator")
    assert "_manage_tools" in orchestrator["shared_meta_tools"]
    assert "_set_active_instance" in orchestrator["shared_meta_tools"]
    assert orchestrator["handoff_map"]["core"]["specialist_id"] == "unity-core-specialist"

    core = next(item for item in catalog["subagents"] if item["id"] == "unity-core-specialist")
    assert core["default_enabled"] is True
    assert "_manage_scene" in core["tools"]
    assert core["activation"]["params"] == {"action": "activate", "group": "core"}

    testing = next(item for item in catalog["subagents"] if item["id"] == "unity-testing-specialist")
    assert "_run_tests" in testing["tools"]


def test_export_subagent_artifacts_writes_catalog_and_markdown(tmp_path):
    _register_minimal_toolset()

    result = export_subagent_artifacts(tmp_path)

    assert result["subagent_count"] == 7
    assert len(result["written_files"]) == 9

    catalog_path = tmp_path / "subagents.json"
    readme_path = tmp_path / "README.md"
    orchestrator_path = tmp_path / "unity-orchestrator.md"

    assert catalog_path.exists()
    assert readme_path.exists()
    assert orchestrator_path.exists()

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert catalog["subagent_count"] == 7
    assert "Unity Orchestrator" in orchestrator_path.read_text(encoding="utf-8")
    assert "Unity MCP Subagents" in readme_path.read_text(encoding="utf-8")


def test_build_subagent_catalog_bootstraps_registry_when_empty(monkeypatch):
    tool_registry_module._tool_registry.clear()
    called = False

    def fake_ensure() -> int:
        nonlocal called
        called = True

        @mcp_for_unity_tool(unity_target=None, group=None)
        def _manage_tools():
            return None

        @mcp_for_unity_tool(group="core")
        def _manage_scene():
            return None

        return 2

    monkeypatch.setattr(subagents_module, "ensure_tool_registry_populated", fake_ensure)

    catalog = build_subagent_catalog()

    assert called is True
    core = next(item for item in catalog["subagents"] if item["id"] == "unity-core-specialist")
    assert "_manage_scene" in core["tools"]
