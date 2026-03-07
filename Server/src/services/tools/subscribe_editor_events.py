"""
Event subscription tool for subscribing to Unity editor events.

Provides real-time event notifications for editor state changes.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from models import MCPResponse
from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
import transport.unity_transport as unity_transport
from transport.legacy.unity_connection import async_send_command_with_retry

logger = logging.getLogger(__name__)

# Valid event types that can be subscribed to
VALID_EVENT_TYPES = {
    "console_updates",
    "compile_state_changes",
    "play_mode_transitions",
    "hierarchy_changes",
    "test_job_progress",
    "runtime_bridge_status",
}


class SubscriptionResult(BaseModel):
    subscription_id: str
    event_types: list[str]
    unity_instance: str | None
    created_at: str
    expires_at: str | None


class SubscribeResponse(MCPResponse):
    data: SubscriptionResult | None = None


@mcp_for_unity_tool(
    group="events",
    unity_target=None,
    description=(
        "Subscribes to Unity editor events for real-time notifications. "
        "Returns a subscription_id that can be used to unsubscribe. "
        "Events are delivered through the MCP notification channel when available."
    ),
    annotations=ToolAnnotations(
        title="Subscribe to Editor Events",
        readOnlyHint=False,
    ),
)
async def subscribe_editor_events(
    ctx: Context,
    event_types: Annotated[
        list[str] | str,
        "Event types to subscribe to. Options: console_updates, compile_state_changes, "
        "play_mode_transitions, hierarchy_changes, test_job_progress, runtime_bridge_status. "
        "Can be a list or a comma-separated string."
    ],
    filter_criteria: Annotated[
        dict[str, Any] | str | None,
        "Optional filter criteria as dict or JSON string. "
        "E.g., {'log_level': 'error'} for console_updates, "
        "{'scene_path': '/path/to/scene'} for hierarchy_changes."
    ] = None,
    expiration_minutes: Annotated[
        int | str | None,
        "Optional subscription expiration time in minutes (default: no expiration). "
        "Maximum: 1440 (24 hours)."
    ] = None,
    buffer_events: Annotated[
        bool | str,
        "If True (default), events are buffered until first poll. "
        "If False, events before first poll are discarded."
    ] = True,
) -> SubscribeResponse | MCPResponse:
    """
    Subscribe to Unity editor events.
    
    Creates a subscription for the specified event types. Events will be
    captured and made available through the event_subscriptions resource.
    
    Example:
        subscribe_editor_events(
            event_types=["console_updates", "compile_state_changes"],
            filter_criteria={"log_level": "error"},
            expiration_minutes=60
        )
    """
    if event_types is None:
        raise ValueError("event_types is required")

    unity_instance = await get_unity_instance_from_context(ctx)

    gate = await maybe_run_tool_preflight(ctx, "subscribe_editor_events")
    if isinstance(gate, MCPResponse):
        return gate

    # Parse event_types
    parsed_event_types = _parse_event_types(event_types)
    if isinstance(parsed_event_types, str):
        # Error message returned
        return MCPResponse(success=False, error=parsed_event_types)

    # Validate event types
    invalid_types = set(parsed_event_types) - VALID_EVENT_TYPES
    if invalid_types:
        return MCPResponse(
            success=False,
            error="invalid_event_types",
            message=f"Invalid event types: {sorted(invalid_types)}. "
                    f"Valid types: {sorted(VALID_EVENT_TYPES)}"
        )

    # Parse filter_criteria
    parsed_filters = _parse_filter_criteria(filter_criteria)
    if isinstance(parsed_filters, str):
        return MCPResponse(success=False, error=parsed_filters)

    # Parse expiration
    expiration_mins = _parse_expiration(expiration_minutes)
    if isinstance(expiration_mins, str):
        return MCPResponse(success=False, error=expiration_mins)

    # Parse buffer_events
    should_buffer = _parse_bool(buffer_events, default=True)

    # Generate subscription ID
    subscription_id = str(uuid.uuid4())

    # Calculate timestamps
    now = datetime.now(timezone.utc)
    created_at = now.isoformat()
    expires_at = None
    if expiration_mins:
        from datetime import timedelta
        expires_at = (now + timedelta(minutes=expiration_mins)).isoformat()

    # Register subscription with Unity if supported
    unity_subscription_id = None
    try:
        unity_response = await _register_with_unity(
            unity_instance,
            parsed_event_types,
            parsed_filters,
            subscription_id,
        )
        if isinstance(unity_response, dict) and unity_response.get("success"):
            data = unity_response.get("data", {})
            unity_subscription_id = data.get("unity_subscription_id")
    except Exception as e:
        logger.warning(f"Could not register subscription with Unity: {e}")
        # Continue anyway - we'll track events server-side

    # Store subscription in the event_subscriptions resource
    from services.resources.event_subscriptions import add_subscription
    
    subscription_data = {
        "subscription_id": subscription_id,
        "event_types": parsed_event_types,
        "unity_instance": unity_instance,
        "created_at": created_at,
        "expires_at": expires_at,
        "filter_criteria": parsed_filters,
        "buffer_events": should_buffer,
        "unity_subscription_id": unity_subscription_id,
        "event_buffer": [],
        "total_events_received": 0,
        "is_active": True,
    }
    
    add_subscription(subscription_id, subscription_data)

    logger.info(
        f"Created subscription {subscription_id} for events: {parsed_event_types}"
    )

    result = SubscriptionResult(
        subscription_id=subscription_id,
        event_types=parsed_event_types,
        unity_instance=unity_instance,
        created_at=created_at,
        expires_at=expires_at,
    )

    return SubscribeResponse(
        success=True,
        message=f"Subscribed to {len(parsed_event_types)} event type(s)",
        data=result
    )


def _parse_event_types(event_types: list[str] | str) -> list[str] | str:
    """Parse event_types parameter to a list of strings."""
    if event_types is None:
        return "event_types is required"
    
    if isinstance(event_types, list):
        # Validate all items are strings
        result = []
        for item in event_types:
            if not isinstance(item, str):
                return f"All event_types must be strings, got: {type(item).__name__}"
            result.append(item.strip().lower())
        return result
    
    if isinstance(event_types, str):
        # Parse comma-separated string
        items = [item.strip().lower() for item in event_types.split(",")]
        return [item for item in items if item]
    
    return f"event_types must be a list or string, got: {type(event_types).__name__}"


def _parse_filter_criteria(
    filter_criteria: dict[str, Any] | str | None
) -> dict[str, Any] | str:
    """Parse filter_criteria parameter to a dict."""
    if filter_criteria is None:
        return {}
    
    if isinstance(filter_criteria, dict):
        return filter_criteria
    
    if isinstance(filter_criteria, str):
        try:
            import json
            parsed = json.loads(filter_criteria)
            if not isinstance(parsed, dict):
                return "filter_criteria JSON must parse to an object"
            return parsed
        except json.JSONDecodeError as e:
            return f"Invalid filter_criteria JSON: {e}"
    
    return f"filter_criteria must be a dict or JSON string, got: {type(filter_criteria).__name__}"


def _parse_expiration(expiration_minutes: int | str | None) -> int | str:
    """Parse and validate expiration_minutes."""
    if expiration_minutes is None:
        return None
    
    try:
        mins = int(expiration_minutes)
        if mins < 1:
            return "expiration_minutes must be at least 1"
        if mins > 1440:
            return "expiration_minutes cannot exceed 1440 (24 hours)"
        return mins
    except (ValueError, TypeError):
        return f"expiration_minutes must be an integer, got: {expiration_minutes}"


def _parse_bool(value: bool | str, default: bool) -> bool:
    """Parse a boolean value that could be bool or string."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    return default


async def _register_with_unity(
    unity_instance: str | None,
    event_types: list[str],
    filter_criteria: dict[str, Any],
    subscription_id: str,
) -> dict[str, Any]:
    """
    Try to register the subscription with Unity for native event delivery.
    
    If Unity doesn't support this command, we'll fall back to polling-based
    event detection on the server side.
    """
    params = {
        "subscription_id": subscription_id,
        "event_types": event_types,
        "filter_criteria": filter_criteria,
    }
    
    response = await unity_transport.send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "subscribe_editor_events",
        params,
    )
    
    if isinstance(response, dict):
        return response
    
    return {"success": False, "error": str(response)}
