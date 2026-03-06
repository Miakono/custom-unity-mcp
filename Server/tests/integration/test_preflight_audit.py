import pytest

from .test_helpers import DummyContext
import services.tools.preflight_audit as preflight_audit_mod


@pytest.mark.asyncio
async def test_preflight_audit_aggregates_success(monkeypatch):
    async def fake_compile(ctx, **kwargs):
        _ = ctx
        _ = kwargs
        return {
            "success": True,
            "data": {
                "ready_for_mutation": True,
                "diagnostics": {"error_count": 0, "warning_count": 0},
            },
        }

    async def fake_scene(ctx, **kwargs):
        _ = ctx
        _ = kwargs
        return {
            "success": True,
            "data": {
                "summary": {
                    "totalMissingScripts": 0,
                    "dirtySceneCount": 0,
                },
            },
        }

    async def fake_prefab(ctx, **kwargs):
        _ = ctx
        _ = kwargs
        return {
            "success": True,
            "data": {
                "summary": {
                    "totalMissingScripts": 0,
                    "prefabsWithIssues": 0,
                },
            },
        }

    monkeypatch.setattr(preflight_audit_mod, "validate_compile_health", fake_compile)
    monkeypatch.setattr(preflight_audit_mod, "audit_scene_integrity", fake_scene)
    monkeypatch.setattr(preflight_audit_mod, "audit_prefab_integrity", fake_prefab)

    result = await preflight_audit_mod.preflight_audit(DummyContext())

    assert result["success"] is True
    assert result["data"]["ready_for_mutation"] is True
    assert result["data"]["blockers"] == []


@pytest.mark.asyncio
async def test_preflight_audit_reports_blockers(monkeypatch):
    async def fake_compile(ctx, **kwargs):
        _ = ctx
        _ = kwargs
        return {
            "success": True,
            "data": {
                "ready_for_mutation": False,
                "diagnostics": {"error_count": 2, "warning_count": 0},
            },
        }

    async def fake_scene(ctx, **kwargs):
        _ = ctx
        _ = kwargs
        return {
            "success": True,
            "data": {
                "summary": {
                    "totalMissingScripts": 3,
                    "dirtySceneCount": 1,
                },
            },
        }

    async def fake_prefab(ctx, **kwargs):
        _ = ctx
        _ = kwargs
        return {
            "success": True,
            "data": {
                "summary": {
                    "totalMissingScripts": 2,
                    "prefabsWithIssues": 4,
                },
            },
        }

    monkeypatch.setattr(preflight_audit_mod, "validate_compile_health", fake_compile)
    monkeypatch.setattr(preflight_audit_mod, "audit_scene_integrity", fake_scene)
    monkeypatch.setattr(preflight_audit_mod, "audit_prefab_integrity", fake_prefab)

    result = await preflight_audit_mod.preflight_audit(DummyContext())

    assert result["data"]["ready_for_mutation"] is False
    assert "compile_health" in result["data"]["blockers"]
    assert "scene_missing_scripts" in result["data"]["blockers"]
    assert "dirty_scenes" in result["data"]["blockers"]
    assert "prefab_missing_scripts" in result["data"]["blockers"]
    assert "prefab_issues" in result["data"]["blockers"]
