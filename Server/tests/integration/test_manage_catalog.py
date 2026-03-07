import pytest

from services.registry import DEFAULT_ENABLED_GROUPS, TOOL_GROUPS
from services.registry import mcp_for_unity_tool
import services.registry.tool_registry as tool_registry_module
from services.resources.tool_catalog import get_tool_catalog
from services.tools.manage_catalog import manage_catalog

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


@pytest.mark.asyncio
async def test_manage_catalog_list_returns_catalog():
    _register_minimal_toolset()
    ctx = DummyContext()

    result = await manage_catalog(ctx, action="list")

    assert result["tool_count"] >= 2
    assert any(item["name"] == "_manage_scene" for item in result["tools"])


@pytest.mark.asyncio
async def test_tool_catalog_resource_returns_catalog():
    _register_minimal_toolset()
    ctx = DummyContext()

    result = await get_tool_catalog(ctx)

    assert result["group_count"] == len(TOOL_GROUPS)
    assert result["default_enabled_groups"] == sorted(DEFAULT_ENABLED_GROUPS)
    assert result["tool_count"] >= 2
    assert any(item["name"] == "_manage_scene" for item in result["tools"])


@pytest.mark.asyncio
async def test_manage_catalog_export_writes_artifacts(tmp_path):
    _register_minimal_toolset()
    ctx = DummyContext()

    result = await manage_catalog(
        ctx,
        action="export",
        output_dir=str(tmp_path),
        format="json",
    )

    assert result["exported"] is True
    assert result["tool_count"] >= 2
    assert any(path.endswith("tool_catalog.json") for path in result["written_files"])
