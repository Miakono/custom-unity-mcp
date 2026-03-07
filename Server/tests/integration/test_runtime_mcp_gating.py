from unittest.mock import AsyncMock

import pytest

import services.tools.runtime_bridge as runtime_bridge_mod
import services.tools.manage_runtime_ui as manage_runtime_ui_mod
from core.config import config as server_config

from .test_helpers import DummyContext


@pytest.mark.asyncio
async def test_runtime_bridge_requires_explicit_runtime_opt_in(monkeypatch):
    monkeypatch.setattr(server_config, "runtime_mcp_enabled", False)

    async def should_not_be_called(*_args, **_kwargs):
        raise AssertionError("Unity should not be queried when runtime MCP is disabled")

    monkeypatch.setattr(runtime_bridge_mod, "get_unity_instance_from_context", should_not_be_called)

    result = await runtime_bridge_mod.get_runtime_status(ctx=DummyContext())

    assert result["success"] is False
    assert result["error"] == "runtime_mcp_disabled"


@pytest.mark.asyncio
async def test_runtime_bridge_status_routes_when_enabled(monkeypatch):
    captured = {}
    monkeypatch.setattr(server_config, "runtime_mcp_enabled", True)

    async def fake_send(_send_fn, _unity_instance, command_type, params):
        captured["command_type"] = command_type
        captured["params"] = params
        return {"success": True, "data": {"play_mode": True}}

    monkeypatch.setattr(
        runtime_bridge_mod,
        "get_unity_instance_from_context",
        AsyncMock(return_value="unity-instance-1"),
    )
    monkeypatch.setattr(runtime_bridge_mod, "send_with_unity_instance", fake_send)

    result = await runtime_bridge_mod.get_runtime_status(ctx=DummyContext(), include_capabilities=True)

    assert result["success"] is True
    assert captured["command_type"] == "runtime_bridge"
    assert captured["params"]["action"] == "get_status"


@pytest.mark.asyncio
async def test_manage_runtime_ui_requires_explicit_runtime_opt_in(monkeypatch):
    monkeypatch.setattr(server_config, "runtime_mcp_enabled", False)

    async def should_not_be_called(*_args, **_kwargs):
        raise AssertionError("Unity should not be queried when runtime MCP is disabled")

    monkeypatch.setattr(manage_runtime_ui_mod, "get_unity_instance_from_context", should_not_be_called)

    result = await manage_runtime_ui_mod.manage_runtime_ui(
        ctx=DummyContext(),
        action="find_elements",
        element_type="Button",
    )

    assert result["success"] is False
    assert result["error"] == "runtime_mcp_disabled"
