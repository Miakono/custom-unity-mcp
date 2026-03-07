"""Validation tests for V3 Waiters & Events tools (Phase 2).

Tests for:
- wait_for_editor_condition
- subscribe_editor_events
- unsubscribe_editor_events
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.tools.wait_for_editor_condition import (
    wait_for_editor_condition,
    _parse_float,
    _validate_condition_params,
)
from services.tools.subscribe_editor_events import (
    subscribe_editor_events,
    _parse_event_types,
    _parse_filter_criteria,
    _parse_expiration,
    VALID_EVENT_TYPES,
)
from services.tools.unsubscribe_editor_events import (
    unsubscribe_editor_events,
)
from tests.integration.test_helpers import DummyContext


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def ctx():
    """Provide a dummy context for testing."""
    return DummyContext()


@pytest.fixture
def mock_unity_idle():
    """Mock Unity response for compile idle state."""
    return {
        "success": True,
        "data": {
            "compilation": {
                "is_compiling": False,
                "is_domain_reload_pending": False,
            }
        }
    }


@pytest.fixture
def mock_unity_compiling():
    """Mock Unity response for compiling state."""
    return {
        "success": True,
        "data": {
            "compilation": {
                "is_compiling": True,
                "is_domain_reload_pending": False,
            }
        }
    }


# =============================================================================
# Phase 2: Waiters & Events - wait_for_editor_condition
# =============================================================================

@pytest.mark.asyncio
class TestWaitForEditorCondition:
    """Tests for the wait_for_editor_condition tool."""

    async def test_wait_for_compile_idle_success(self, ctx, mock_unity_idle):
        """test_wait_for_compile_idle: Successfully waits for compile idle."""
        with patch("services.tools.wait_for_editor_condition.unity_transport.send_with_unity_instance",
                   AsyncMock(return_value=mock_unity_idle)):
            result = await wait_for_editor_condition(ctx, condition="compile_idle")
        
        assert result.success is True
        assert result.data.condition_met is True
        assert result.data.condition_type == "compile_idle"
        assert result.data.timed_out is False

    async def test_wait_for_compile_idle_timeout(self, ctx, mock_unity_compiling):
        """test_wait_timeout: Times out when condition not met."""
        with patch("services.tools.wait_for_editor_condition.unity_transport.send_with_unity_instance",
                   AsyncMock(return_value=mock_unity_compiling)):
            result = await wait_for_editor_condition(
                ctx, 
                condition="compile_idle",
                timeout_seconds=0.1,
                poll_interval_seconds=0.05
            )
        
        assert result.success is False
        assert result.error == "timeout"
        assert result.data.timed_out is True

    async def test_wait_for_scene_load_requires_scene_params(self, ctx):
        """test_wait_for_scene_load: Validates scene-specific parameters."""
        # This test validates the parameter handling
        # Actual Unity calls are mocked
        mock_response = {
            "success": True,
            "data": {
                "editor": {"active_scene": {"path": "Assets/Scenes/Test.unity", "name": "Test"}},
                "activity": {"phase": ""}
            }
        }
        
        with patch("services.tools.wait_for_editor_condition.unity_transport.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await wait_for_editor_condition(
                ctx, 
                condition="scene_load_complete",
                scene_path="Assets/Scenes/Test.unity"
            )
        
        assert result.success is True

    async def test_wait_for_play_mode_requires_target(self, ctx):
        """test_wait_for_play_mode: Requires play_mode_target parameter."""
        result = await wait_for_editor_condition(ctx, condition="play_mode_state")
        
        assert result.success is False
        assert "play_mode_target" in result.message.lower()

    async def test_wait_for_play_mode_success(self, ctx):
        """test_wait_for_play_mode: Successfully waits for play mode state."""
        mock_response = {
            "success": True,
            "data": {
                "editor": {
                    "play_mode": {
                        "is_playing": True,
                        "is_paused": False,
                        "is_changing": False,
                    }
                }
            }
        }
        
        with patch("services.tools.wait_for_editor_condition.unity_transport.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await wait_for_editor_condition(
                ctx, 
                condition="play_mode_state",
                play_mode_target="playing"
            )
        
        assert result.success is True
        assert result.data.condition_met is True
        assert result.data.details["current_state"] == "playing"

    async def test_wait_timeout_custom_timeout(self, ctx, mock_unity_compiling):
        """test_wait_timeout: Respects custom timeout value."""
        with patch("services.tools.wait_for_editor_condition.unity_transport.send_with_unity_instance",
                   AsyncMock(return_value=mock_unity_compiling)):
            start_time = asyncio.get_event_loop().time()
            result = await wait_for_editor_condition(
                ctx, 
                condition="compile_idle",
                timeout_seconds=0.2,
                poll_interval_seconds=0.05
            )
            elapsed = asyncio.get_event_loop().time() - start_time
        
        assert result.success is False
        assert result.error == "timeout"
        # Should complete close to timeout (with some tolerance)
        assert elapsed >= 0.15

    async def test_wait_cancellation(self, ctx, mock_unity_compiling):
        """test_wait_timeout: Handles cancellation properly."""
        with patch("services.tools.wait_for_editor_condition.unity_transport.send_with_unity_instance",
                   AsyncMock(return_value=mock_unity_compiling)):
            task = asyncio.create_task(
                wait_for_editor_condition(
                    ctx, 
                    condition="compile_idle",
                    timeout_seconds=10
                )
            )
            # Cancel after brief delay
            await asyncio.sleep(0.05)
            task.cancel()
            
            with pytest.raises(asyncio.CancelledError):
                await task

    async def test_wait_invalid_condition(self, ctx):
        """test_wait_for_editor_condition: Handles unknown condition."""
        result = await wait_for_editor_condition(ctx, condition="unknown_condition")
        
        # Should return False with unknown condition error
        assert result.success is False

    async def test_wait_for_asset_import_complete(self, ctx):
        """test_wait_for_editor_condition: Waits for asset import completion."""
        mock_response = {
            "success": True,
            "data": {
                "assets": {
                    "refresh": {"is_refresh_in_progress": False},
                    "is_updating": False,
                }
            }
        }
        
        with patch("services.tools.wait_for_editor_condition.unity_transport.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await wait_for_editor_condition(ctx, condition="asset_import_complete")
        
        assert result.success is True
        assert result.data.condition_met is True

    async def test_wait_for_object_exists_by_name(self, ctx):
        """test_wait_for_editor_condition: Waits for object by name."""
        mock_response = {
            "success": True,
            "data": {"exists": True}
        }
        
        with patch("services.tools.wait_for_editor_condition.unity_transport.send_with_unity_instance",
                   AsyncMock(return_value=mock_response)):
            result = await wait_for_editor_condition(
                ctx, 
                condition="object_exists",
                object_name="Player"
            )
        
        assert result.success is True
        assert result.data.condition_met is True

    async def test_wait_for_object_exists_requires_criteria(self, ctx):
        """test_wait_for_editor_condition: Requires object_name or object_guid."""
        result = await wait_for_editor_condition(ctx, condition="object_exists")
        
        assert result.success is False
        assert "object_name" in result.message.lower() or "object_guid" in result.message.lower()


# =============================================================================
# Phase 2: Waiters & Events - Helper Functions
# =============================================================================

class TestWaitConditionHelpers:
    """Tests for wait condition helper functions."""

    def test_parse_float_with_int(self):
        """test_parse_float: Handles integer input."""
        assert _parse_float(30, 10) == 30.0

    def test_parse_float_with_float(self):
        """test_parse_float: Handles float input."""
        assert _parse_float(30.5, 10) == 30.5

    def test_parse_float_with_string(self):
        """test_parse_float: Handles string input."""
        assert _parse_float("30", 10) == 30.0

    def test_parse_float_with_invalid_string(self):
        """test_parse_float: Returns default for invalid string."""
        assert _parse_float("invalid", 10) == 10.0

    def test_parse_float_with_none(self):
        """test_parse_float: Returns default for None."""
        assert _parse_float(None, 10) == 10.0

    def test_validate_condition_params_play_mode(self):
        """test_validate_condition_params: Validates play mode params."""
        error = _validate_condition_params("play_mode_state", None, None, None, None)
        assert error is not None
        assert "play_mode_target" in error

    def test_validate_condition_params_prefab_stage(self):
        """test_validate_condition_params: Validates prefab stage params."""
        error = _validate_condition_params("prefab_stage_state", None, None, None, None)
        assert error is not None
        assert "prefab_stage_target" in error

    def test_validate_condition_params_object_exists(self):
        """test_validate_condition_params: Validates object exists params."""
        error = _validate_condition_params("object_exists", None, None, None, None)
        assert error is not None
        assert "object_name" in error or "object_guid" in error

    def test_validate_condition_params_compile_idle(self):
        """test_validate_condition_params: No extra params needed for compile_idle."""
        error = _validate_condition_params("compile_idle", None, None, None, None)
        assert error is None


# =============================================================================
# Phase 2: Waiters & Events - subscribe_editor_events
# =============================================================================

@pytest.mark.asyncio
class TestSubscribeEditorEvents:
    """Tests for the subscribe_editor_events tool."""

    async def test_subscribe_requires_event_types(self, ctx):
        """test_subscribe_console: Requires event_types parameter."""
        with pytest.raises(Exception):  # Should fail validation
            await subscribe_editor_events(ctx, event_types=None)

    async def test_subscribe_with_single_event_type(self, ctx):
        """test_subscribe_console: Subscribes to single event type."""
        with patch("services.tools.subscribe_editor_events._register_with_unity",
                   AsyncMock(return_value={"success": True, "data": {}})):
            result = await subscribe_editor_events(ctx, event_types=["console_updates"])
        
        assert result.success is True
        assert "console_updates" in result.data.event_types
        assert result.data.subscription_id is not None

    async def test_subscribe_with_multiple_event_types(self, ctx):
        """test_subscribe_compile: Subscribes to multiple event types."""
        with patch("services.tools.subscribe_editor_events._register_with_unity",
                   AsyncMock(return_value={"success": True, "data": {}})):
            result = await subscribe_editor_events(
                ctx, 
                event_types=["console_updates", "compile_state_changes"]
            )
        
        assert result.success is True
        assert len(result.data.event_types) == 2
        assert "console_updates" in result.data.event_types
        assert "compile_state_changes" in result.data.event_types

    async def test_subscribe_hierarchy(self, ctx):
        """test_subscribe_hierarchy: Subscribes to hierarchy changes."""
        with patch("services.tools.subscribe_editor_events._register_with_unity",
                   AsyncMock(return_value={"success": True, "data": {}})):
            result = await subscribe_editor_events(ctx, event_types=["hierarchy_changes"])
        
        assert result.success is True
        assert "hierarchy_changes" in result.data.event_types

    async def test_subscribe_with_invalid_event_type(self, ctx):
        """test_subscribe_console: Returns error for invalid event type."""
        result = await subscribe_editor_events(ctx, event_types=["invalid_type"])
        
        assert result.success is False
        assert result.error == "invalid_event_types"

    async def test_subscribe_with_filter_criteria(self, ctx):
        """test_subscribe_console: Supports filter criteria."""
        with patch("services.tools.subscribe_editor_events._register_with_unity",
                   AsyncMock(return_value={"success": True, "data": {}})):
            result = await subscribe_editor_events(
                ctx, 
                event_types=["console_updates"],
                filter_criteria={"log_level": "error"}
            )
        
        assert result.success is True

    async def test_subscribe_with_expiration(self, ctx):
        """test_subscribe_console: Supports expiration time."""
        with patch("services.tools.subscribe_editor_events._register_with_unity",
                   AsyncMock(return_value={"success": True, "data": {}})):
            result = await subscribe_editor_events(
                ctx, 
                event_types=["console_updates"],
                expiration_minutes=60
            )
        
        assert result.success is True
        assert result.data.expires_at is not None

    async def test_subscribe_with_string_event_types(self, ctx):
        """test_subscribe_compile: Accepts comma-separated string."""
        with patch("services.tools.subscribe_editor_events._register_with_unity",
                   AsyncMock(return_value={"success": True, "data": {}})):
            result = await subscribe_editor_events(
                ctx, 
                event_types="console_updates, compile_state_changes"
            )
        
        assert result.success is True
        assert len(result.data.event_types) == 2


# =============================================================================
# Phase 2: Waiters & Events - Subscribe Helper Functions
# =============================================================================

class TestSubscribeHelpers:
    """Tests for subscribe helper functions."""

    def test_parse_event_types_with_list(self):
        """test_parse_event_types: Handles list input."""
        result = _parse_event_types(["console_updates", "compile_state_changes"])
        assert result == ["console_updates", "compile_state_changes"]

    def test_parse_event_types_with_string(self):
        """test_parse_event_types: Handles comma-separated string."""
        result = _parse_event_types("console_updates, compile_state_changes")
        assert result == ["console_updates", "compile_state_changes"]

    def test_parse_event_types_with_none(self):
        """test_parse_event_types: Returns error for None."""
        result = _parse_event_types(None)
        assert isinstance(result, str)
        assert "required" in result.lower()

    def test_parse_event_types_with_invalid_items(self):
        """test_parse_event_types: Returns error for non-string items."""
        result = _parse_event_types([1, 2, 3])
        assert isinstance(result, str)
        assert "strings" in result.lower()

    def test_parse_filter_criteria_with_dict(self):
        """test_parse_filter_criteria: Handles dict input."""
        criteria = {"log_level": "error"}
        result = _parse_filter_criteria(criteria)
        assert result == criteria

    def test_parse_filter_criteria_with_json_string(self):
        """test_parse_filter_criteria: Handles JSON string."""
        result = _parse_filter_criteria('{"log_level": "error"}')
        assert result == {"log_level": "error"}

    def test_parse_filter_criteria_with_none(self):
        """test_parse_filter_criteria: Returns empty dict for None."""
        result = _parse_filter_criteria(None)
        assert result == {}

    def test_parse_filter_criteria_with_invalid_json(self):
        """test_parse_filter_criteria: Returns error for invalid JSON."""
        result = _parse_filter_criteria("invalid json")
        assert isinstance(result, str)
        assert "Invalid" in result

    def test_parse_expiration_with_valid_int(self):
        """test_parse_expiration: Handles valid integer."""
        result = _parse_expiration(60)
        assert result == 60

    def test_parse_expiration_with_valid_string(self):
        """test_parse_expiration: Handles valid string."""
        result = _parse_expiration("60")
        assert result == 60

    def test_parse_expiration_with_none(self):
        """test_parse_expiration: Returns None for None input."""
        result = _parse_expiration(None)
        assert result is None

    def test_parse_expiration_with_zero(self):
        """test_parse_expiration: Returns error for zero."""
        result = _parse_expiration(0)
        assert isinstance(result, str)
        assert "at least 1" in result

    def test_parse_expiration_with_too_large(self):
        """test_parse_expiration: Returns error for too large value."""
        result = _parse_expiration(2000)
        assert isinstance(result, str)
        assert "exceed" in result.lower()

    def test_valid_event_types_defined(self):
        """test_subscribe_compile: Valid event types are defined."""
        expected_types = {
            "console_updates",
            "compile_state_changes",
            "play_mode_transitions",
            "hierarchy_changes",
            "test_job_progress",
            "runtime_bridge_status",
        }
        assert VALID_EVENT_TYPES == expected_types


# =============================================================================
# Phase 2: Waiters & Events - unsubscribe_editor_events
# =============================================================================

@pytest.mark.asyncio
class TestUnsubscribeEditorEvents:
    """Tests for the unsubscribe_editor_events tool."""

    async def test_unsubscribe_by_id_success(self, ctx):
        """test_unsubscribe_by_id: Successfully unsubscribes by ID."""
        # First subscribe
        with patch("services.tools.subscribe_editor_events._register_with_unity",
                   AsyncMock(return_value={"success": True, "data": {}})):
            sub_result = await subscribe_editor_events(ctx, event_types=["console_updates"])
            sub_id = sub_result.data.subscription_id
        
        # Then unsubscribe
        with patch("services.tools.unsubscribe_editor_events._unregister_with_unity",
                   AsyncMock(return_value={"success": True})):
            result = await unsubscribe_editor_events(ctx, subscription_id=sub_id)
        
        assert result.success is True
        assert result.data.unsubscribed is True

    async def test_unsubscribe_by_id_not_found(self, ctx):
        """test_unsubscribe_by_id: Returns error for non-existent ID."""
        result = await unsubscribe_editor_events(ctx, subscription_id="non_existent_id")
        
        assert result.success is False
        assert result.error == "subscription_not_found"

    async def test_unsubscribe_all(self, ctx):
        """test_unsubscribe_all: Unsubscribes from all events."""
        # Create a few subscriptions
        with patch("services.tools.subscribe_editor_events._register_with_unity",
                   AsyncMock(return_value={"success": True, "data": {}})):
            await subscribe_editor_events(ctx, event_types=["console_updates"])
            await subscribe_editor_events(ctx, event_types=["hierarchy_changes"])
        
        # Unsubscribe all
        with patch("services.tools.unsubscribe_editor_events._unregister_with_unity",
                   AsyncMock(return_value={"success": True})):
            result = await unsubscribe_editor_events(ctx, unsubscribe_all=True)
        
        assert result.success is True
        assert result.data.unsubscribed_all is True
        assert result.data.unsubscribed_count >= 2

    async def test_unsubscribe_requires_id_or_all(self, ctx):
        """test_unsubscribe_by_id: Requires subscription_id or unsubscribe_all."""
        result = await unsubscribe_editor_events(ctx)
        
        assert result.success is False
        assert result.error == "missing_parameter"

    async def test_unsubscribe_handles_unity_error(self, ctx):
        """test_unsubscribe_by_id: Handles Unity unregister errors gracefully."""
        # First subscribe
        with patch("services.tools.subscribe_editor_events._register_with_unity",
                   AsyncMock(return_value={"success": True, "data": {}})):
            sub_result = await subscribe_editor_events(ctx, event_types=["console_updates"])
            sub_id = sub_result.data.subscription_id
        
        # Then unsubscribe with Unity error
        with patch("services.tools.unsubscribe_editor_events._unregister_with_unity",
                   AsyncMock(return_value={"success": False, "error": "Unity error"})):
            result = await unsubscribe_editor_events(ctx, subscription_id=sub_id)
        
        # Should still succeed (server-side cleanup)
        assert result.success is True
