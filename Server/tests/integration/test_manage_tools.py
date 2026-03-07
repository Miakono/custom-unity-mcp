import pytest

from services.registry import DEFAULT_ENABLED_GROUPS
from services.registry import mcp_for_unity_tool
import services.registry.tool_registry as tool_registry_module
from services.tools.manage_tools import manage_tools

from .test_helpers import DummyContext


@pytest.fixture(autouse=True)
def restore_tool_registry_state():
    original_registry = list(tool_registry_module._tool_registry)
    try:
        yield
    finally:
        tool_registry_module._tool_registry[:] = original_registry


def _register_minimal_toolset():
    @mcp_for_unity_tool(group="core")
    def _manage_scene():
        return None

    @mcp_for_unity_tool(group="testing")
    def _run_tests():
        return None


@pytest.mark.asyncio
async def test_manage_tools_list_groups_reflects_defaults():
    _register_minimal_toolset()
    ctx = DummyContext()

    result = await manage_tools(ctx, action="list_groups")

    groups = {group["name"]: group for group in result["groups"]}
    assert groups["core"]["enabled"] is True
    assert groups["testing"]["enabled"] is ("testing" in DEFAULT_ENABLED_GROUPS)
    assert "_manage_scene" in groups["core"]["tools"]
    assert "_run_tests" in groups["testing"]["tools"]


@pytest.mark.asyncio
async def test_manage_tools_activate_and_reset_updates_session_visibility():
    _register_minimal_toolset()
    ctx = DummyContext()

    activated = await manage_tools(ctx, action="activate", group="testing")
    assert activated["activated"] == "testing"

    listed = await manage_tools(ctx, action="list_groups")
    groups = {group["name"]: group for group in listed["groups"]}
    assert groups["testing"]["enabled"] is True

    reset = await manage_tools(ctx, action="reset")
    assert reset["reset"] is True

    listed_after_reset = await manage_tools(ctx, action="list_groups")
    groups_after_reset = {group["name"]: group for group in listed_after_reset["groups"]}
    assert groups_after_reset["testing"]["enabled"] is ("testing" in DEFAULT_ENABLED_GROUPS)


@pytest.mark.asyncio
async def test_manage_tools_deactivate_updates_session_visibility():
    _register_minimal_toolset()
    ctx = DummyContext()

    await manage_tools(ctx, action="activate", group="testing")
    deactivated = await manage_tools(ctx, action="deactivate", group="testing")
    assert deactivated["deactivated"] == "testing"

    listed = await manage_tools(ctx, action="list_groups")
    groups = {group["name"]: group for group in listed["groups"]}
    assert groups["testing"]["enabled"] is False


@pytest.mark.asyncio
async def test_manage_tools_sync_reports_enabled_and_disabled_groups(monkeypatch):
    _register_minimal_toolset()
    ctx = DummyContext()

    async def fake_sync(notify=True):
        assert notify is True
        return {
            "synced": True,
            "enabled_groups": ["core"],
            "disabled_groups": ["testing"],
            "enabled_tool_count": 1,
            "total_tool_count": 2,
        }

    monkeypatch.setattr("services.tools.sync_tool_visibility_from_unity", fake_sync)

    result = await manage_tools(ctx, action="sync")

    assert result["synced"] is True
    assert result["enabled_groups"] == ["core"]
    assert result["disabled_groups"] == ["testing"]
    assert result["enabled_tool_count"] == 1
    assert result["total_tool_count"] == 2
