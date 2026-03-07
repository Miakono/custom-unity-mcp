"""Tests for manage_windows V2 tool."""

import inspect
from unittest.mock import AsyncMock

import pytest

from services.tools.manage_windows import manage_windows
from tests.integration.test_helpers import DummyContext


class TestManageWindowsInterface:
    """Tests for tool interface and parameter validation."""

    def test_tool_has_required_parameters(self):
        """The manage_windows tool should have required parameters."""
        sig = inspect.signature(manage_windows)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters

    def test_action_parameter_values(self):
        """action parameter should accept correct Literal values."""
        sig = inspect.signature(manage_windows)
        action_annotation = str(sig.parameters["action"].annotation)
        expected_actions = [
            "list_windows",
            "open_window",
            "focus_window",
            "close_window",
            "get_active_tool",
            "set_active_tool",
        ]
        for action in expected_actions:
            assert action in action_annotation

    def test_optional_parameters_exist(self):
        """All optional parameters should be present."""
        sig = inspect.signature(manage_windows)
        optional_params = ["window_type", "window_id", "window_title", "tool_name"]
        for param in optional_params:
            assert param in sig.parameters


class TestListWindows:
    """Tests for list_windows action."""

    @pytest.mark.asyncio
    async def test_list_windows(self, monkeypatch):
        """Test listing all editor windows."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "windows": [
                    {"id": 1, "title": "Hierarchy", "type": "Hierarchy"},
                    {"id": 2, "title": "Inspector", "type": "Inspector"},
                    {"id": 3, "title": "Scene", "type": "Scene"},
                ],
            }

        monkeypatch.setattr(
            "services.tools.manage_windows.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_windows(
            DummyContext(),
            action="list_windows",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "list_windows"


class TestOpenWindow:
    """Tests for open_window action."""

    @pytest.mark.asyncio
    async def test_open_window_by_type(self, monkeypatch):
        """Test opening a window by type."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "windowId": 5, "title": "Console"}

        monkeypatch.setattr(
            "services.tools.manage_windows.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_windows(
            DummyContext(),
            action="open_window",
            window_type="Console",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "open_window"
        assert captured["params"]["windowType"] == "Console"

    @pytest.mark.asyncio
    async def test_open_common_window_types(self, monkeypatch):
        """Test opening common window types."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "windowId": 1}

        monkeypatch.setattr(
            "services.tools.manage_windows.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        window_types = ["Scene", "Game", "Inspector", "Hierarchy", "Project"]
        for window_type in window_types:
            resp = await manage_windows(
                DummyContext(),
                action="open_window",
                window_type=window_type,
            )
            assert resp["success"] is True


class TestFocusWindow:
    """Tests for focus_window action."""

    @pytest.mark.asyncio
    async def test_focus_window_by_id(self, monkeypatch):
        """Test focusing a window by ID."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "message": "Window focused"}

        monkeypatch.setattr(
            "services.tools.manage_windows.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_windows(
            DummyContext(),
            action="focus_window",
            window_id=3,
        )

        assert resp["success"] is True
        assert captured["params"]["windowId"] == 3

    @pytest.mark.asyncio
    async def test_focus_window_by_title(self, monkeypatch):
        """Test focusing a window by title."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "message": "Window focused"}

        monkeypatch.setattr(
            "services.tools.manage_windows.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_windows(
            DummyContext(),
            action="focus_window",
            window_title="My Custom Window",
        )

        assert resp["success"] is True
        assert captured["params"]["windowTitle"] == "My Custom Window"


class TestCloseWindow:
    """Tests for close_window action."""

    @pytest.mark.asyncio
    async def test_close_window_by_id(self, monkeypatch):
        """Test closing a window by ID."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "message": "Window closed"}

        monkeypatch.setattr(
            "services.tools.manage_windows.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_windows(
            DummyContext(),
            action="close_window",
            window_id=5,
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "close_window"


class TestActiveTool:
    """Tests for get_active_tool and set_active_tool actions."""

    @pytest.mark.asyncio
    async def test_get_active_tool(self, monkeypatch):
        """Test getting the current active tool."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "activeTool": "Move"}

        monkeypatch.setattr(
            "services.tools.manage_windows.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_windows(
            DummyContext(),
            action="get_active_tool",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "get_active_tool"

    @pytest.mark.asyncio
    async def test_set_active_tool(self, monkeypatch):
        """Test setting the active tool."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "previousTool": "Move", "newTool": "Rotate"}

        monkeypatch.setattr(
            "services.tools.manage_windows.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        tool_names = ["View", "Move", "Rotate", "Scale", "Rect", "Transform", "Custom"]
        for tool_name in tool_names:
            resp = await manage_windows(
                DummyContext(),
                action="set_active_tool",
                tool_name=tool_name,
            )
            assert resp["success"] is True
            assert captured["params"]["toolName"] == tool_name


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_timeout_error(self, monkeypatch):
        """Test handling of TimeoutError."""

        async def fake_send(*args, **kwargs):
            raise TimeoutError("Connection timeout")

        monkeypatch.setattr(
            "services.tools.manage_windows.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_windows(
            DummyContext(),
            action="list_windows",
        )

        assert resp["success"] is False
        assert "timeout" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_general_exception(self, monkeypatch):
        """Test handling of general exceptions."""

        async def fake_send(*args, **kwargs):
            raise RuntimeError("Unexpected error")

        monkeypatch.setattr(
            "services.tools.manage_windows.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_windows(
            DummyContext(),
            action="list_windows",
        )

        assert resp["success"] is False
        assert "Error managing windows" in resp["message"]

    @pytest.mark.asyncio
    async def test_response_without_success_field(self, monkeypatch):
        """Test handling of response without success field."""

        async def fake_send(*args, **kwargs):
            return {"data": "some data"}  # No success field

        monkeypatch.setattr(
            "services.tools.manage_windows.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_windows.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_windows(
            DummyContext(),
            action="list_windows",
        )

        # Should add success=False when missing
        assert resp["success"] is False
