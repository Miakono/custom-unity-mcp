"""Tests for get_command_stats V2 tool."""

import inspect
from unittest.mock import AsyncMock, patch

import pytest

from services.tools.get_command_stats import get_command_stats
from tests.integration.test_helpers import DummyContext


class TestGetCommandStatsInterface:
    """Tests for tool interface and parameter validation."""

    def test_tool_has_required_parameters(self):
        """The get_command_stats tool should have required parameters."""
        sig = inspect.signature(get_command_stats)
        assert "ctx" in sig.parameters

    def test_optional_parameters_exist(self):
        """Optional parameters should be present."""
        sig = inspect.signature(get_command_stats)
        assert "tool_filter" in sig.parameters
        assert "since_hours" in sig.parameters

    def test_optional_parameters_have_none_defaults(self):
        """Optional parameters should default to None."""
        sig = inspect.signature(get_command_stats)
        assert sig.parameters["tool_filter"].default is None
        assert sig.parameters["since_hours"].default is None


class TestGetStatsBasic:
    """Tests for basic stats retrieval."""

    @pytest.mark.asyncio
    async def test_get_stats_basic(self):
        """Test getting basic command statistics."""
        resp = await get_command_stats(
            DummyContext(),
        )

        assert resp["success"] is True
        assert "data" in resp
        assert "telemetry_enabled" in resp["data"]
        assert "period_hours" in resp["data"]
        assert resp["data"]["period_hours"] == 24  # Default value

    @pytest.mark.asyncio
    async def test_get_stats_with_custom_hours(self):
        """Test getting stats with custom hours parameter."""
        resp = await get_command_stats(
            DummyContext(),
            since_hours=48,
        )

        assert resp["success"] is True
        assert resp["data"]["period_hours"] == 48

    @pytest.mark.asyncio
    async def test_get_stats_with_tool_filter(self):
        """Test getting stats filtered by tool name."""
        resp = await get_command_stats(
            DummyContext(),
            tool_filter="manage_gameobject",
        )

        assert resp["success"] is True
        assert resp["data"]["tool_filter"] == "manage_gameobject"

    @pytest.mark.asyncio
    async def test_get_stats_with_zero_hours(self):
        """Test getting stats with zero hours (edge case)."""
        resp = await get_command_stats(
            DummyContext(),
            since_hours=0,
        )

        assert resp["success"] is True
        assert resp["data"]["period_hours"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_contains_record_types(self):
        """Test that stats include record types information."""
        resp = await get_command_stats(
            DummyContext(),
        )

        assert resp["success"] is True
        assert "record_types_tracked" in resp["data"]
        assert isinstance(resp["data"]["record_types_tracked"], list)


class TestGetStatsWithTelemetry:
    """Tests for stats with telemetry enabled/disabled."""

    @pytest.mark.asyncio
    async def test_get_stats_telemetry_enabled(self, monkeypatch):
        """Test getting stats when telemetry is enabled."""
        monkeypatch.setattr(
            "core.telemetry.is_telemetry_enabled",
            lambda: True,
        )

        resp = await get_command_stats(
            DummyContext(),
        )

        assert resp["success"] is True
        assert resp["data"]["telemetry_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_stats_telemetry_disabled(self, monkeypatch):
        """Test getting stats when telemetry is disabled."""
        monkeypatch.setattr(
            "core.telemetry.is_telemetry_enabled",
            lambda: False,
        )

        resp = await get_command_stats(
            DummyContext(),
        )

        assert resp["success"] is True
        assert resp["data"]["telemetry_enabled"] is False


class TestGetStatsErrorHandling:
    """Tests for error handling in get_command_stats."""

    @pytest.mark.asyncio
    async def test_get_stats_error_response(self, monkeypatch):
        """Test that errors are properly formatted in response."""
        # The get_command_stats tool catches exceptions and returns error responses
        # Test that error responses have the expected structure
        resp = await get_command_stats(
            DummyContext(),
            since_hours=-1,  # Invalid value might trigger error path
        )
        
        # Response should have success field
        assert "success" in resp
        # Error responses should include error_code when there's a failure
        if not resp.get("success"):
            assert "error_code" in resp or "message" in resp

    @pytest.mark.asyncio
    async def test_get_stats_response_structure(self):
        """Test that response has correct structure."""
        resp = await get_command_stats(
            DummyContext(),
        )
        
        # Check required fields in response
        assert "success" in resp
        assert "message" in resp
        assert "data" in resp
        
        # Check data structure
        assert "telemetry_enabled" in resp["data"]
        assert "period_hours" in resp["data"]
        assert "record_types_tracked" in resp["data"]
