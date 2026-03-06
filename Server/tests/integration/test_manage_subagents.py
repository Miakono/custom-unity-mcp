import pytest

from services.registry import mcp_for_unity_tool
import services.registry.tool_registry as tool_registry_module
from services.resources.subagents import get_subagent_catalog
from services.tools.manage_subagents import manage_subagents

from .test_helpers import DummyContext


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


@pytest.mark.asyncio
async def test_manage_subagents_list_returns_catalog():
    _register_minimal_toolset()
    ctx = DummyContext()

    result = await manage_subagents(ctx, action="list")

    assert result["subagent_count"] == 7
    assert any(item["id"] == "unity-orchestrator" for item in result["subagents"])


@pytest.mark.asyncio
async def test_subagent_catalog_resource_returns_catalog():
    _register_minimal_toolset()
    ctx = DummyContext()

    result = await get_subagent_catalog(ctx)

    assert result["group_count"] == 6
    assert result["subagents"][0]["id"] == "unity-orchestrator"
