"""Tests for ping V2 tool."""

import inspect
from unittest.mock import AsyncMock

import pytest

from services.tools.ping import ping
from tests.integration.test_helpers import DummyContext


class TestPingInterface:
    """Tests for tool interface and parameter validation."""

    def test_tool_has_required_parameters(self):
        """The ping tool should have required parameters."""
        sig = inspect.signature(ping)
        assert "ctx" in sig.parameters

    def test_optional_parameters_exist(self):
        """Optional parameters should be present."""
        sig = inspect.signature(ping)
        assert "ping_unity" in sig.parameters

    def test_ping_unity_defaults_to_none(self):
        """ping_unity parameter should default to None."""
        sig = inspect.signature(ping)
        assert sig.parameters["ping_unity"].default is None


class TestPingBasic:
    """Tests for basic ping functionality."""

    @pytest.mark.asyncio
    async def test_ping_basic(self):
        """Test basic ping without Unity check."""
        resp = await ping(
            DummyContext(),
            ping_unity=False,
        )

        assert resp["success"] is True
        assert resp["server_status"] == "running"
        assert resp["unity_status"] == "not_checked"
        assert "MCP server is running" in resp["message"]

    @pytest.mark.asyncio
    async def test_ping_default_no_unity_check(self):
        """Test that ping defaults to not checking Unity."""
        resp = await ping(
            DummyContext(),
        )

        assert resp["success"] is True
        assert resp["unity_status"] == "not_checked"


class TestPingWithUnity:
    """Tests for ping with Unity connectivity check."""

    @pytest.mark.asyncio
    async def test_ping_with_unity_connected(self, monkeypatch):
        """Test ping when Unity is connected."""

        async def fake_send(*args, **kwargs):
            return {"status": "ok", "message": "Unity is responsive"}

        monkeypatch.setattr(
            "services.tools.ping.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.ping.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )

        resp = await ping(
            DummyContext(),
            ping_unity=True,
        )

        assert resp["success"] is True
        assert resp["unity_status"] == "connected"
        assert "unity_response" in resp

    @pytest.mark.asyncio
    async def test_ping_with_unity_disconnected(self, monkeypatch):
        """Test ping when Unity is disconnected."""

        async def fake_send(*args, **kwargs):
            raise ConnectionError("Cannot connect to Unity")

        monkeypatch.setattr(
            "services.tools.ping.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.ping.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )

        resp = await ping(
            DummyContext(),
            ping_unity=True,
        )

        assert resp["success"] is True  # Server is still running
        assert resp["unity_status"] == "disconnected"
        assert "unity_error" in resp

    @pytest.mark.asyncio
    async def test_ping_with_unity_timeout(self, monkeypatch):
        """Test ping when Unity connection times out."""

        async def fake_send(*args, **kwargs):
            raise TimeoutError("Unity not responding")

        monkeypatch.setattr(
            "services.tools.ping.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.ping.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )

        resp = await ping(
            DummyContext(),
            ping_unity=True,
        )

        assert resp["success"] is True  # Server is still running
        assert resp["unity_status"] == "disconnected"
        assert "unity_error" in resp

    @pytest.mark.asyncio
    async def test_ping_unity_non_dict_response(self, monkeypatch):
        """Test ping with Unity returning non-dict response."""

        async def fake_send(*args, **kwargs):
            return "Unity response as string"

        monkeypatch.setattr(
            "services.tools.ping.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.ping.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )

        resp = await ping(
            DummyContext(),
            ping_unity=True,
        )

        assert resp["success"] is True
        assert resp["unity_status"] == "connected"
        assert resp["unity_response"]["message"] == "Unity response as string"


class TestPingErrorHandling:
    """Tests for error handling in ping."""

    @pytest.mark.asyncio
    async def test_ping_handles_various_exceptions(self, monkeypatch):
        """Test that ping handles various exception types gracefully."""

        exceptions = [
            ConnectionError("Connection refused"),
            TimeoutError("Request timeout"),
            RuntimeError("Some runtime error"),
            Exception("Generic exception"),
        ]

        for exc in exceptions:

            async def fake_send(*args, **kwargs):
                raise exc

            monkeypatch.setattr(
                "services.tools.ping.send_with_unity_instance", fake_send
            )
            monkeypatch.setattr(
                "services.tools.ping.get_unity_instance_from_context",
                AsyncMock(return_value="Project@hash"),
            )

            resp = await ping(
                DummyContext(),
                ping_unity=True,
            )

            assert resp["success"] is True  # Server is still running
            assert resp["unity_status"] == "disconnected"
