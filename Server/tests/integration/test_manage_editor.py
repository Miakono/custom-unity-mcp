import pytest

import services.tools.manage_editor as manage_editor_mod
from .test_helpers import DummyContext


@pytest.mark.asyncio
async def test_manage_editor_telemetry_status(monkeypatch):
    monkeypatch.setattr(manage_editor_mod, "is_telemetry_enabled", lambda: True)

    resp = await manage_editor_mod.manage_editor(
        ctx=DummyContext(),
        action="telemetry_status",
    )

    assert resp == {"success": True, "telemetry_enabled": True}


@pytest.mark.asyncio
async def test_manage_editor_telemetry_ping(monkeypatch):
    captured = {}

    def fake_record(tool_name, success, duration_ms, error):
        captured["tool_name"] = tool_name
        captured["success"] = success
        captured["duration_ms"] = duration_ms
        captured["error"] = error

    monkeypatch.setattr(manage_editor_mod, "record_tool_usage", fake_record)

    resp = await manage_editor_mod.manage_editor(
        ctx=DummyContext(),
        action="telemetry_ping",
    )

    assert resp["success"] is True
    assert "queued" in resp["message"]
    assert captured["tool_name"] == "diagnostic_ping"
    assert captured["success"] is True
    assert captured["error"] is None


@pytest.mark.asyncio
async def test_manage_editor_mutating_action_routes_to_unity(monkeypatch):
    captured = {}

    async def fake_send(_send_fn, _unity_instance, command_type, params, **_kwargs):
        captured["command_type"] = command_type
        captured["params"] = params
        return {"success": True, "message": "ok", "data": {"state": "playing"}}

    monkeypatch.setattr(manage_editor_mod, "send_with_unity_instance", fake_send)

    resp = await manage_editor_mod.manage_editor(
        ctx=DummyContext(),
        action="play",
        wait_for_completion="true",
    )

    assert resp["success"] is True
    assert captured["command_type"] == "manage_editor"
    assert captured["params"]["action"] == "play"
    assert captured["params"]["waitForCompletion"] is True
