"""Validation tests for V3 Dev Tools (Phase 7).

Tests for:
- dev_trace_tools
- capture_unity_fixture
- replay_unity_fixture
- benchmark_tool_surface
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock
import json

import pytest

from services.tools.dev_trace_tools import (
    start_trace,
    stop_trace,
    get_trace_summary,
    list_traces,
    clear_traces,
    record_trace_entry,
    get_current_trace_id,
    set_current_trace_id,
)
from services.tools.capture_unity_fixture import capture_unity_fixture
from services.tools.replay_unity_fixture import replay_unity_fixture
from services.tools.benchmark_tool_surface import benchmark_tool_surface
from tests.integration.test_helpers import DummyContext


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def ctx():
    """Provide a dummy context for testing."""
    return DummyContext()


@pytest.fixture
def reset_traces():
    """Reset trace state before and after tests."""
    # Clear any existing traces
    set_current_trace_id(None)
    # Note: We can't directly clear _active_traces and _completed_traces
    # as they're module-level private variables, but clear_traces tool can help
    yield
    # Cleanup after test
    set_current_trace_id(None)


# =============================================================================
# Phase 7: Dev Tools - dev_trace_tools
# =============================================================================

@pytest.mark.asyncio
class TestDevTraceTools:
    """Tests for the dev_trace_tools module."""

    async def test_start_trace(self, ctx, reset_traces):
        """test_trace_request: Starts a new trace session."""
        result = await start_trace(ctx)
        
        assert result["success"] is True
        assert "trace_id" in result
        assert result["trace_id"] is not None
        assert "started_at" in result

    async def test_start_trace_with_tags(self, ctx, reset_traces):
        """test_trace_request: Starts trace with tags."""
        tags = ["test", "debug", "performance"]
        result = await start_trace(ctx, tags=tags)
        
        assert result["success"] is True
        
        # Verify tags are stored by checking the trace summary
        trace_id = result["trace_id"]
        summary = await get_trace_summary(ctx, trace_id=trace_id)
        assert summary["success"] is True
        assert summary["tags"] == tags

    async def test_stop_trace(self, ctx, reset_traces):
        """test_get_trace_logs: Stops trace and returns data."""
        # Start a trace
        start_result = await start_trace(ctx)
        trace_id = start_result["trace_id"]
        
        # Record a mock entry
        record_trace_entry(
            tool="test_tool",
            normalized_params={"param1": "value1"},
            unity_instance="Project@hash",
            retries=0,
            latency_ms=100.0,
            response_status="success"
        )
        
        # Stop the trace
        result = await stop_trace(ctx, trace_id=trace_id)
        
        assert result["success"] is True
        assert result["trace_id"] == trace_id
        assert "summary" in result
        assert result["summary"]["total_requests"] == 1

    async def test_stop_trace_without_entries(self, ctx, reset_traces):
        """test_get_trace_logs: Stops empty trace."""
        start_result = await start_trace(ctx)
        trace_id = start_result["trace_id"]
        
        result = await stop_trace(ctx, trace_id=trace_id)
        
        assert result["success"] is True
        assert result["summary"]["total_requests"] == 0

    async def test_stop_trace_not_found(self, ctx):
        """test_get_trace_logs: Returns error for non-existent trace."""
        result = await stop_trace(ctx, trace_id="non_existent")
        
        assert result["success"] is False
        assert result["error"] == "trace_not_found"

    async def test_stop_no_active_trace(self, ctx, reset_traces):
        """test_get_trace_logs: Returns error when no active trace."""
        result = await stop_trace(ctx)
        
        assert result["success"] is False
        assert result["error"] == "no_active_trace"

    async def test_get_trace_summary(self, ctx, reset_traces):
        """test_get_trace_logs: Gets summary of trace."""
        start_result = await start_trace(ctx, tags=["test"])
        trace_id = start_result["trace_id"]
        
        # Record entries with different statuses
        record_trace_entry("tool1", {}, None, 0, 50.0, "success")
        record_trace_entry("tool2", {}, None, 1, 150.0, "error", error="Test error")
        
        result = await get_trace_summary(ctx, trace_id=trace_id)
        
        assert result["success"] is True
        assert result["trace_id"] == trace_id
        assert result["is_active"] is True
        assert result["tags"] == ["test"]
        assert result["summary"]["total_requests"] == 2
        assert result["summary"]["success_count"] == 1
        assert result["summary"]["error_count"] == 1
        assert result["summary"]["total_retries"] == 1

    async def test_get_trace_summary_stats(self, ctx, reset_traces):
        """test_get_trace_logs: Summary includes latency stats."""
        start_result = await start_trace(ctx)
        trace_id = start_result["trace_id"]
        
        record_trace_entry("tool", {}, None, 0, 100.0, "success")
        record_trace_entry("tool", {}, None, 0, 200.0, "success")
        
        result = await get_trace_summary(ctx, trace_id=trace_id)
        
        assert result["success"] is True
        assert result["summary"]["avg_latency_ms"] == 150.0
        assert result["summary"]["min_latency_ms"] == 100.0
        assert result["summary"]["max_latency_ms"] == 200.0

    async def test_list_traces(self, ctx, reset_traces):
        """test_get_trace_logs: Lists all traces."""
        # Create a couple traces
        trace1 = await start_trace(ctx, tags=["tag1"])
        trace2 = await start_trace(ctx, tags=["tag2"])
        
        result = await list_traces(ctx)
        
        assert result["success"] is True
        assert result["active_count"] >= 2
        assert len(result["traces"]) >= 2

    async def test_list_traces_include_completed(self, ctx, reset_traces):
        """test_get_trace_logs: Lists completed traces."""
        # Create and complete a trace
        start_result = await start_trace(ctx)
        await stop_trace(ctx, trace_id=start_result["trace_id"])
        
        result = await list_traces(ctx, include_completed=True)
        
        assert result["success"] is True
        assert result["completed_count"] >= 1

    async def test_list_traces_exclude_completed(self, ctx, reset_traces):
        """test_get_trace_logs: Can exclude completed traces."""
        result = await list_traces(ctx, include_completed=False)
        
        assert result["success"] is True
        # Should only show active traces
        for trace in result["traces"]:
            assert trace["status"] == "active"

    async def test_clear_traces_specific(self, ctx, reset_traces):
        """test_get_trace_logs: Clears specific trace."""
        start_result = await start_trace(ctx)
        trace_id = start_result["trace_id"]
        
        result = await clear_traces(ctx, trace_id=trace_id)
        
        assert result["success"] is True
        assert trace_id in result["message"]

    async def test_clear_traces_all_completed(self, ctx, reset_traces):
        """test_get_trace_logs: Clears all completed traces."""
        # Complete a trace
        start_result = await start_trace(ctx)
        await stop_trace(ctx, trace_id=start_result["trace_id"])
        
        result = await clear_traces(ctx)
        
        assert result["success"] is True
        assert "cleared" in result["message"].lower()

    async def test_clear_active_trace_requires_flag(self, ctx, reset_traces):
        """test_get_trace_logs: Requires flag to clear active trace."""
        start_result = await start_trace(ctx)
        trace_id = start_result["trace_id"]
        
        result = await clear_traces(ctx, trace_id=trace_id)
        
        assert result["success"] is False
        assert result["error"] == "trace_active"

    async def test_clear_active_trace_with_flag(self, ctx, reset_traces):
        """test_get_trace_logs: Can clear active with flag."""
        start_result = await start_trace(ctx)
        trace_id = start_result["trace_id"]
        
        result = await clear_traces(ctx, trace_id=trace_id, clear_active=True)
        
        assert result["success"] is True

    async def test_trace_entry_recording(self, ctx, reset_traces):
        """test_trace_request: Records trace entries."""
        await start_trace(ctx)
        
        recorded = record_trace_entry(
            tool="manage_gameobject",
            normalized_params={"action": "create"},
            unity_instance="TestProject",
            retries=2,
            latency_ms=250.5,
            response_status="success",
            error=None,
            metadata={"cached": False}
        )
        
        assert recorded is True
        
        # Verify by getting summary
        summary = await get_trace_summary(ctx)
        assert summary["summary"]["total_requests"] == 1

    async def test_trace_entry_no_active_trace(self, ctx, reset_traces):
        """test_trace_request: Returns False when no active trace."""
        set_current_trace_id(None)
        
        recorded = record_trace_entry(
            tool="test_tool",
            normalized_params={},
            unity_instance=None,
            retries=0,
            latency_ms=100.0,
            response_status="success"
        )
        
        assert recorded is False


# =============================================================================
# Phase 7: Dev Tools - capture_unity_fixture
# =============================================================================

@pytest.mark.asyncio
class TestCaptureUnityFixture:
    """Tests for the capture_unity_fixture tool."""

    async def test_capture_response(self, ctx):
        """test_capture_response: Captures Unity response as fixture."""
        mock_response = {
            "success": True,
            "data": {"objects": [{"name": "Player", "id": 1}]}
        }
        
        with patch("services.tools.capture_unity_fixture.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await capture_unity_fixture(
                ctx, 
                tool_name="find_gameobjects",
                params={"name": "Player"}
            )
        
        assert result["success"] is True
        assert "fixture_id" in result
        assert result["tool"] == "find_gameobjects"

    async def test_capture_with_metadata(self, ctx):
        """test_capture_response: Captures with metadata."""
        mock_response = {"success": True, "data": {}}
        
        with patch("services.tools.capture_unity_fixture.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await capture_unity_fixture(
                ctx, 
                tool_name="test_tool",
                params={},
                metadata={
                    "description": "Test fixture",
                    "version": "1.0",
                    "tags": ["test", "v1"]
                }
            )
        
        assert result["success"] is True

    async def test_save_fixture(self, ctx):
        """test_save_fixture: Saves fixture to file."""
        mock_response = {"success": True, "data": {}}
        
        with patch("services.tools.capture_unity_fixture.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await capture_unity_fixture(
                ctx, 
                tool_name="test_tool",
                params={},
                save_path="fixtures/test_fixture.json"
            )
        
        assert result["success"] is True

    async def test_capture_error_response(self, ctx):
        """test_capture_response: Can capture error responses."""
        mock_response = {"success": False, "error": "not_found", "message": "Object not found"}
        
        with patch("services.tools.capture_unity_fixture.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await capture_unity_fixture(
                ctx, 
                tool_name="find_gameobject",
                params={"name": "Missing"}
            )
        
        assert result["success"] is True
        assert result["captured_response"]["success"] is False

    async def test_capture_unity_error(self, ctx):
        """test_capture_response: Handles Unity connection errors."""
        with patch("services.tools.capture_unity_fixture.send_with_unity_instance",
                   AsyncMock(return_value={"success": False, "message": "Connection failed"})):
            result = await capture_unity_fixture(
                ctx, 
                tool_name="test_tool",
                params={}
            )
        
        assert result["success"] is True  # Capture succeeded even if response is error


# =============================================================================
# Phase 7: Dev Tools - replay_unity_fixture
# =============================================================================

@pytest.mark.asyncio
class TestReplayUnityFixture:
    """Tests for the replay_unity_fixture tool."""

    async def test_replay_fixture(self, ctx):
        """test_replay_fixture: Replays captured fixture."""
        fixture_data = {
            "tool": "find_gameobjects",
            "params": {"name": "Player"},
            "response": {"success": True, "data": {"objects": [{"name": "Player"}]}}
        }
        
        with patch("services.tools.replay_unity_fixture._load_fixture",
                   return_value=fixture_data):
            result = await replay_unity_fixture(ctx, fixture_id="fixture_123")
        
        assert result["success"] is True
        assert result["replayed"] is True
        assert result["response"] == fixture_data["response"]

    async def test_replay_fixture_not_found(self, ctx):
        """test_replay_fixture: Returns error for missing fixture."""
        result = await replay_unity_fixture(ctx, fixture_id="non_existent")
        
        assert result["success"] is False
        assert result["error"] == "fixture_not_found"

    async def test_replay_fixture_from_file(self, ctx):
        """test_replay_fixture: Can load fixture from file."""
        fixture_data = {
            "tool": "test_tool",
            "params": {},
            "response": {"success": True, "data": {}}
        }
        
        with patch("services.tools.replay_unity_fixture._load_fixture_from_file",
                   return_value=fixture_data):
            result = await replay_unity_fixture(
                ctx, 
                fixture_path="fixtures/test.json"
            )
        
        assert result["success"] is True

    async def test_mock_from_fixture(self, ctx):
        """test_mock_from_fixture: Uses fixture to mock Unity calls."""
        fixture_data = {
            "tool": "find_gameobjects",
            "params": {"name": "Player"},
            "response": {"success": True, "data": {"objects": [{"name": "Player"}]}}
        }
        
        with patch("services.tools.replay_unity_fixture._load_fixture",
                   return_value=fixture_data):
            result = await replay_unity_fixture(
                ctx, 
                fixture_id="fixture_123",
                mock_mode=True
            )
        
        assert result["success"] is True
        assert result["mock_mode"] is True

    async def test_replay_with_transformations(self, ctx):
        """test_replay_fixture: Applies transformations to response."""
        fixture_data = {
            "tool": "test_tool",
            "params": {},
            "response": {"success": True, "data": {"count": 5}}
        }
        
        with patch("services.tools.replay_unity_fixture._load_fixture",
                   return_value=fixture_data):
            result = await replay_unity_fixture(
                ctx, 
                fixture_id="fixture_123",
                transform={"multiply_count": 2}
            )
        
        assert result["success"] is True


# =============================================================================
# Phase 7: Dev Tools - benchmark_tool_surface
# =============================================================================

@pytest.mark.asyncio
class TestBenchmarkToolSurface:
    """Tests for the benchmark_tool_surface tool."""

    async def test_benchmark_tool(self, ctx):
        """test_benchmark_tool: Benchmarks a single tool."""
        mock_response = {"success": True, "data": {}}
        
        with patch("services.tools.benchmark_tool_surface.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await benchmark_tool_surface(
                ctx, 
                tool_name="find_gameobjects",
                iterations=10
            )
        
        assert result["success"] is True
        assert result["tool"] == "find_gameobjects"
        assert result["iterations"] == 10
        assert "avg_latency_ms" in result
        assert "min_latency_ms" in result
        assert "max_latency_ms" in result

    async def test_benchmark_tool_with_params(self, ctx):
        """test_benchmark_tool: Benchmarks with specific parameters."""
        mock_response = {"success": True, "data": {"objects": []}}
        
        with patch("services.tools.benchmark_tool_surface.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await benchmark_tool_surface(
                ctx, 
                tool_name="find_gameobjects",
                params={"name": "Player", "max_results": 10},
                iterations=5
            )
        
        assert result["success"] is True

    async def test_benchmark_tool_warmup(self, ctx):
        """test_benchmark_tool: Supports warmup iterations."""
        mock_response = {"success": True, "data": {}}
        
        with patch("services.tools.benchmark_tool_surface.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await benchmark_tool_surface(
                ctx, 
                tool_name="test_tool",
                warmup_iterations=3,
                iterations=10
            )
        
        assert result["success"] is True
        assert result["warmup_iterations"] == 3

    async def test_benchmark_workflow(self, ctx):
        """test_benchmark_workflow: Benchmarks multi-tool workflow."""
        mock_response = {"success": True, "data": {}}
        
        workflow = [
            {"tool": "find_gameobjects", "params": {"name": "Player"}},
            {"tool": "get_component", "params": {"target": "Player", "component": "Transform"}}
        ]
        
        with patch("services.tools.benchmark_tool_surface.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await benchmark_tool_surface(
                ctx, 
                workflow=workflow,
                iterations=5
            )
        
        assert result["success"] is True
        assert "workflow" in result
        assert len(result["workflow"]) == 2

    async def test_benchmark_with_concurrency(self, ctx):
        """test_benchmark_tool: Supports concurrent benchmarking."""
        mock_response = {"success": True, "data": {}}
        
        with patch("services.tools.benchmark_tool_surface.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await benchmark_tool_surface(
                ctx, 
                tool_name="test_tool",
                iterations=20,
                concurrency=5
            )
        
        assert result["success"] is True

    async def test_benchmark_reports_percentiles(self, ctx):
        """test_benchmark_tool: Reports latency percentiles."""
        mock_response = {"success": True, "data": {}}
        
        with patch("services.tools.benchmark_tool_surface.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await benchmark_tool_surface(
                ctx, 
                tool_name="test_tool",
                iterations=100
            )
        
        assert result["success"] is True
        assert "p50_latency_ms" in result
        assert "p95_latency_ms" in result
        assert "p99_latency_ms" in result

    async def test_benchmark_reports_errors(self, ctx):
        """test_benchmark_tool: Reports error rates."""
        # Mix of success and error responses
        responses = [
            {"success": True, "data": {}},
            {"success": True, "data": {}},
            {"success": False, "error": "test_error"}
        ]
        
        with patch("services.tools.benchmark_tool_surface.send_with_unity_instance",
                   AsyncMock(side_effect=responses)):
            result = await benchmark_tool_surface(
                ctx, 
                tool_name="test_tool",
                iterations=3
            )
        
        assert result["success"] is True
        assert result["error_count"] == 1
        assert result["success_count"] == 2
        assert result["error_rate"] == pytest.approx(0.333, abs=0.01)

    async def test_benchmark_requires_tool_or_workflow(self, ctx):
        """test_benchmark_tool: Requires tool_name or workflow."""
        result = await benchmark_tool_surface(ctx)
        
        assert result["success"] is False
        assert "tool_name" in result["message"].lower() or "workflow" in result["message"].lower()

    async def test_benchmark_saves_results(self, ctx):
        """test_benchmark_tool: Can save results to file."""
        mock_response = {"success": True, "data": {}}
        
        with patch("services.tools.benchmark_tool_surface.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await benchmark_tool_surface(
                ctx, 
                tool_name="test_tool",
                iterations=10,
                save_path="benchmarks/results.json"
            )
        
        assert result["success"] is True
        assert "saved_to" in result
