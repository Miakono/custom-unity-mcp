"""Tests for manage_selection V2 tool."""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.tools.manage_selection import manage_selection
from tests.integration.test_helpers import DummyContext


class TestManageSelectionInterface:
    """Tests for tool interface and parameter validation."""

    def test_tool_has_required_parameters(self):
        """The manage_selection tool should have required parameters."""
        sig = inspect.signature(manage_selection)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters

    def test_action_parameter_has_correct_type(self):
        """action parameter should accept the correct Literal values."""
        sig = inspect.signature(manage_selection)
        action_param = sig.parameters["action"]
        # The annotation should be a Literal type
        assert "Literal" in str(action_param.annotation)

    def test_optional_parameters_exist(self):
        """All optional parameters should be present."""
        sig = inspect.signature(manage_selection)
        optional_params = ["target", "clear", "add", "frame_selected"]
        for param in optional_params:
            assert param in sig.parameters

    def test_optional_parameters_have_none_defaults(self):
        """Optional parameters should default to None."""
        sig = inspect.signature(manage_selection)
        assert sig.parameters["target"].default is None
        assert sig.parameters["clear"].default is None
        assert sig.parameters["add"].default is None
        assert sig.parameters["frame_selected"].default is None


class TestSetSelection:
    """Tests for set_selection action."""

    @pytest.mark.asyncio
    async def test_set_selection_by_path(self, monkeypatch):
        """Test setting selection by object path."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "selected": ["Assets/Player"], "count": 1}

        monkeypatch.setattr(
            "services.tools.manage_selection.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_selection(
            DummyContext(),
            action="set_selection",
            target="Assets/Player",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "set_selection"
        assert captured["params"]["target"] == "Assets/Player"

    @pytest.mark.asyncio
    async def test_set_selection_by_name(self, monkeypatch):
        """Test setting selection by object name."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "selected": ["Player"], "count": 1}

        monkeypatch.setattr(
            "services.tools.manage_selection.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_selection(
            DummyContext(),
            action="set_selection",
            target="Player",
            clear=True,
        )

        assert resp["success"] is True
        assert captured["params"]["target"] == "Player"
        assert captured["params"]["clear"] is True

    @pytest.mark.asyncio
    async def test_set_selection_add_to_existing(self, monkeypatch):
        """Test adding to existing selection."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "selected": ["Player", "Enemy"], "count": 2}

        monkeypatch.setattr(
            "services.tools.manage_selection.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_selection(
            DummyContext(),
            action="set_selection",
            target="Enemy",
            add=True,
        )

        assert resp["success"] is True
        assert captured["params"]["add"] is True

    @pytest.mark.asyncio
    async def test_set_selection_multiple_targets(self, monkeypatch):
        """Test selecting multiple objects at once."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "selected": ["A", "B", "C"], "count": 3}

        monkeypatch.setattr(
            "services.tools.manage_selection.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_selection(
            DummyContext(),
            action="set_selection",
            target=["A", "B", "C"],
        )

        assert resp["success"] is True
        assert captured["params"]["target"] == ["A", "B", "C"]


class TestFrameSelection:
    """Tests for frame_selection action."""

    @pytest.mark.asyncio
    async def test_frame_selection(self, monkeypatch):
        """Test framing selected objects."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "message": "Framed 2 objects"}

        monkeypatch.setattr(
            "services.tools.manage_selection.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_selection(
            DummyContext(),
            action="frame_selection",
            frame_selected=True,
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "frame_selection"
        assert captured["params"]["frameSelected"] is True


class TestGetSelection:
    """Tests for get_selection action."""

    @pytest.mark.asyncio
    async def test_get_selection(self, monkeypatch):
        """Test getting current selection."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "selected": [
                    {"name": "Player", "instanceId": 12345, "path": "Assets/Player"}
                ],
                "count": 1,
            }

        monkeypatch.setattr(
            "services.tools.manage_selection.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_selection(
            DummyContext(),
            action="get_selection",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "get_selection"


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_timeout_error(self, monkeypatch):
        """Test handling of TimeoutError."""

        async def fake_send(*args, **kwargs):
            raise TimeoutError("Connection timeout")

        monkeypatch.setattr(
            "services.tools.manage_selection.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_selection(
            DummyContext(),
            action="get_selection",
        )

        assert resp["success"] is False
        assert "timeout" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_general_exception(self, monkeypatch):
        """Test handling of general exceptions."""

        async def fake_send(*args, **kwargs):
            raise RuntimeError("Unexpected error")

        monkeypatch.setattr(
            "services.tools.manage_selection.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_selection(
            DummyContext(),
            action="get_selection",
        )

        assert resp["success"] is False
        assert "Error managing selection" in resp["message"]

    @pytest.mark.asyncio
    async def test_unexpected_response_type(self, monkeypatch):
        """Test handling of unexpected response types."""

        async def fake_send(*args, **kwargs):
            return "unexpected string response"

        monkeypatch.setattr(
            "services.tools.manage_selection.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_selection(
            DummyContext(),
            action="get_selection",
        )

        assert resp["success"] is False
        assert "Unexpected response type" in resp["message"]


class TestPreflight:
    """Tests for preflight check behavior."""

    @pytest.mark.asyncio
    async def test_preflight_blocks_execution(self, monkeypatch):
        """Test that preflight can block execution."""
        from mcp.types import TextContent

        class FakeGateResponse:
            def model_dump(self):
                return {"success": False, "message": "Gate blocked"}

        monkeypatch.setattr(
            "services.tools.manage_selection.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_selection.maybe_run_tool_preflight",
            AsyncMock(return_value=FakeGateResponse()),
        )

        resp = await manage_selection(
            DummyContext(),
            action="get_selection",
        )

        assert resp["success"] is False
        assert resp["message"] == "Gate blocked"
