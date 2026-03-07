import asyncio

from .test_helpers import DummyContext
import services.tools.manage_asset as manage_asset_mod


def test_manage_asset_pagination_coercion(monkeypatch):
    captured = {}

    async def fake_async_send(cmd, params, **kwargs):
        captured["params"] = params
        return {"success": True, "data": {}}

    monkeypatch.setattr(
        manage_asset_mod, "async_send_command_with_retry", fake_async_send)

    result = asyncio.run(
        manage_asset_mod.manage_asset(
            ctx=DummyContext(),
            action="search",
            path="Assets",
            page_size="50",
            page_number="2",
        )
    )

    assert result == {"success": True, "data": {}}
    assert captured["params"]["pageSize"] == 50
    assert captured["params"]["pageNumber"] == 2


def test_manage_asset_action_passthrough_matrix(monkeypatch):
    captured = []

    async def fake_async_send(cmd, params, **kwargs):
        captured.append((cmd, params))
        return {"success": True, "data": {}}

    monkeypatch.setattr(
        manage_asset_mod, "async_send_command_with_retry", fake_async_send)

    test_calls = [
        {"action": "create", "path": "Assets/T.mat", "asset_type": "Material"},
        {"action": "delete", "path": "Assets/Old.mat"},
        {"action": "duplicate", "path": "Assets/A.mat", "destination": "Assets/B.mat"},
        {"action": "import", "path": "Assets/Source.png", "destination": "Assets/Imported.png"},
        {"action": "modify", "path": "Assets/T.mat", "properties": {"foo": "bar"}},
        {"action": "move", "path": "Assets/A.mat", "destination": "Assets/New/A.mat"},
        {"action": "rename", "path": "Assets/A.mat", "destination": "Assets/B.mat"},
    ]

    for call in test_calls:
        result = asyncio.run(manage_asset_mod.manage_asset(ctx=DummyContext(), **call))
        assert result["success"] is True

    assert len(captured) == len(test_calls)
    sent_actions = [params["action"] for _cmd, params in captured]
    assert sent_actions == [call["action"] for call in test_calls]
