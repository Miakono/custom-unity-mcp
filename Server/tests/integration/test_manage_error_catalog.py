import pytest

from services.resources.error_catalog import get_error_catalog
from services.tools.manage_error_catalog import manage_error_catalog

from .test_helpers import DummyContext


@pytest.mark.asyncio
async def test_manage_error_catalog_list_returns_catalog():
    ctx = DummyContext()

    result = await manage_error_catalog(ctx, action="list")

    assert result["stable_code_count"] >= 18
    assert any(domain["id"] == "script_editing" for domain in result["domains"])


@pytest.mark.asyncio
async def test_error_catalog_resource_returns_catalog():
    ctx = DummyContext()

    result = await get_error_catalog(ctx)

    assert result["domain_count"] >= 2
    assert any(domain["id"] == "scriptable_objects" for domain in result["domains"])


@pytest.mark.asyncio
async def test_manage_error_catalog_export_writes_artifacts(tmp_path):
    ctx = DummyContext()

    result = await manage_error_catalog(
        ctx,
        action="export",
        output_dir=str(tmp_path),
        format="json",
    )

    assert result["exported"] is True
    assert result["stable_code_count"] >= 18
    assert any(path.endswith("error_catalog.json") for path in result["written_files"])
