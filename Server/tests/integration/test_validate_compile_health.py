import pytest

from .test_helpers import DummyContext
import services.tools.validate_compile_health as validate_compile_health_mod
from models import MCPResponse


@pytest.mark.asyncio
async def test_validate_compile_health_reports_compiler_errors(monkeypatch):
    async def fake_get_editor_state(ctx):
        _ = ctx
        return MCPResponse(
            success=True,
            data={
                "unity": {"instance_id": "MyProj@ABC123"},
                "compilation": {
                    "is_compiling": False,
                    "is_domain_reload_pending": False,
                },
                "advice": {
                    "ready_for_tools": True,
                    "blocking_reasons": [],
                },
            },
        )

    async def fake_read_console(ctx, **kwargs):
        _ = ctx
        _ = kwargs
        return {
            "success": True,
            "data": [
                {
                    "type": "Error",
                    "message": "Assets/Scripts/Player.cs(12,5): error CS1002: ; expected",
                    "file": "Assets/Scripts/Player.cs",
                    "line": 12,
                },
                {
                    "type": "Warning",
                    "message": "Assets/Scripts/Player.cs(20,10): warning CS0168: variable is declared but never used",
                    "file": "Assets/Scripts/Player.cs",
                    "line": 20,
                },
            ],
        }

    monkeypatch.setattr(validate_compile_health_mod, "get_editor_state", fake_get_editor_state)
    monkeypatch.setattr(validate_compile_health_mod, "read_console", fake_read_console)

    result = await validate_compile_health_mod.validate_compile_health(DummyContext())

    assert result["success"] is True
    assert result["data"]["ready_for_mutation"] is False
    assert result["data"]["diagnostics"]["error_count"] == 1
    assert result["data"]["diagnostics"]["warning_count"] == 1
    assert "Compiler errors are present" in result["data"]["recommendation"]


@pytest.mark.asyncio
async def test_validate_compile_health_filters_non_compiler_logs(monkeypatch):
    async def fake_get_editor_state(ctx):
        _ = ctx
        return MCPResponse(
            success=True,
            data={
                "unity": {"instance_id": "MyProj@ABC123"},
                "compilation": {
                    "is_compiling": False,
                    "is_domain_reload_pending": False,
                },
                "advice": {
                    "ready_for_tools": True,
                    "blocking_reasons": [],
                },
            },
        )

    async def fake_read_console(ctx, **kwargs):
        _ = ctx
        _ = kwargs
        return {
            "success": True,
            "data": [
                {
                    "type": "Error",
                    "message": "NullReferenceException: Object reference not set",
                    "file": "",
                    "line": 0,
                },
                {
                    "type": "Log",
                    "message": "Compilation completed successfully",
                    "file": "",
                    "line": 0,
                },
            ],
        }

    monkeypatch.setattr(validate_compile_health_mod, "get_editor_state", fake_get_editor_state)
    monkeypatch.setattr(validate_compile_health_mod, "read_console", fake_read_console)

    result = await validate_compile_health_mod.validate_compile_health(
        DummyContext(),
        compiler_only=True,
    )

    assert result["data"]["diagnostics"]["reported_count"] == 0
    assert result["data"]["ready_for_mutation"] is True
    assert "healthy" in result["data"]["recommendation"].lower()


@pytest.mark.asyncio
async def test_validate_compile_health_reports_compiling_state(monkeypatch):
    async def fake_get_editor_state(ctx):
        _ = ctx
        return MCPResponse(
            success=True,
            data={
                "unity": {"instance_id": "MyProj@ABC123"},
                "compilation": {
                    "is_compiling": True,
                    "is_domain_reload_pending": False,
                },
                "advice": {
                    "ready_for_tools": False,
                    "blocking_reasons": ["compiling"],
                },
            },
        )

    async def fake_read_console(ctx, **kwargs):
        _ = ctx
        _ = kwargs
        return {"success": True, "data": []}

    monkeypatch.setattr(validate_compile_health_mod, "get_editor_state", fake_get_editor_state)
    monkeypatch.setattr(validate_compile_health_mod, "read_console", fake_read_console)

    result = await validate_compile_health_mod.validate_compile_health(DummyContext())

    assert result["data"]["ready_for_mutation"] is False
    assert "Wait for compilation to finish" in result["data"]["recommendation"]
