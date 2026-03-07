import pytest

import services.tools.manage_screenshot as manage_screenshot_mod


class _FakeUnity:
    def __init__(self, result):
        self._result = result
        self.calls = []

    async def send_command(self, command_type, params):
        self.calls.append((command_type, params))
        return dict(self._result)


@pytest.mark.asyncio
async def test_manage_screenshot_routes_capture_editor_window(monkeypatch):
    fake_unity = _FakeUnity({"success": True, "image_base64": "ZmFrZQ=="})
    async def fake_get_unity_instance_from_context(_ctx):
        return "unity-smoke"

    async def fake_send_with_unity_instance(_transport, unity_instance, command_type, params):
        assert unity_instance == "unity-smoke"
        return await fake_unity.send_command(command_type, params)

    monkeypatch.setattr(manage_screenshot_mod, "get_unity_instance_from_context", fake_get_unity_instance_from_context)
    monkeypatch.setattr(manage_screenshot_mod, "send_with_unity_instance", fake_send_with_unity_instance)

    result = await manage_screenshot_mod.manage_screenshot(
        ctx=None,
        action="capture_editor_window",
        width=1366,
        height=768,
        format="base64",
    )

    assert result["success"] is True
    assert result["data_uri"] == "data:image/png;base64,ZmFrZQ=="

    assert len(fake_unity.calls) == 1
    command_type, params = fake_unity.calls[0]
    assert command_type == "manage_screenshot"
    assert params["action"] == "capture_editor_window"
    assert params["width"] == 1366
    assert params["height"] == 768
    assert params["format"] == "base64"


@pytest.mark.asyncio
async def test_manage_screenshot_routes_get_last_screenshot(monkeypatch):
    fake_unity = _FakeUnity({"success": True, "image_base64": "ZmFrZQ==", "source_action": "capture_scene_view"})
    async def fake_get_unity_instance_from_context(_ctx):
        return None

    async def fake_send_with_unity_instance(_transport, unity_instance, command_type, params):
        assert unity_instance is None
        return await fake_unity.send_command(command_type, params)

    monkeypatch.setattr(manage_screenshot_mod, "get_unity_instance_from_context", fake_get_unity_instance_from_context)
    monkeypatch.setattr(manage_screenshot_mod, "send_with_unity_instance", fake_send_with_unity_instance)

    result = await manage_screenshot_mod.manage_screenshot(
        ctx=None,
        action="get_last_screenshot",
        format="base64",
    )

    assert result["success"] is True
    assert result["data_uri"] == "data:image/png;base64,ZmFrZQ=="
    assert result["source_action"] == "capture_scene_view"

    assert len(fake_unity.calls) == 1
    command_type, params = fake_unity.calls[0]
    assert command_type == "manage_screenshot"
    assert params["action"] == "get_last_screenshot"
    assert params["format"] == "base64"
