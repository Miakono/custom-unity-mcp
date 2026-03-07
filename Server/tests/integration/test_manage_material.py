import pytest

import services.tools.manage_material as manage_material_mod
from .test_helpers import DummyContext


@pytest.mark.asyncio
async def test_manage_material_ping_action(monkeypatch):
    captured = {}

    async def fake_send(_send_fn, _unity_instance, command_type, params, **_kwargs):
        captured["command_type"] = command_type
        captured["params"] = params
        return {"success": True, "message": "pong"}

    monkeypatch.setattr(manage_material_mod, "send_with_unity_instance", fake_send)

    resp = await manage_material_mod.manage_material(
        ctx=DummyContext(),
        action="ping",
    )

    assert resp["success"] is True
    assert captured["command_type"] == "manage_material"
    assert captured["params"]["action"] == "ping"
