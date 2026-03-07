"""
Event unsubscription tool for removing Unity editor event subscriptions.

Provides cleanup of event subscriptions to prevent resource leaks.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

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


class UnsubscribeResult(BaseModel):
    subscription_id: str
    unsubscribed: bool = True
    unsubscribed_all: bool | None = None
    unsubscribed_count: int | None = None
    was_active: bool
    events_received: int
    events_dropped: int | None = None


class UnsubscribeResponse(MCPResponse):
    data: UnsubscribeResult | None = None


@mcp_for_unity_tool(
    group="events",
    unity_target=None,
    description=(
        "Unsubscribes from Unity editor events and cleans up the subscription. "
        "Returns statistics about the subscription (events received, etc.). "
        "Idempotent - safe to call multiple times on the same subscription_id."
    ),
    annotations=ToolAnnotations(
        title="Unsubscribe from Editor Events",
        readOnlyHint=False,
    ),
)
async def unsubscribe_editor_events(
    ctx: Context,
    subscription_id: Annotated[
        str | None,
        "The subscription_id returned by subscribe_editor_events"
    ] = None,
    flush_pending_events: Annotated[
        bool | str,
        "If True (default), return any buffered events in the response. "
        "If False, discard pending events."
    ] = True,
    unsubscribe_all: Annotated[
        bool | str,
        "If True, unsubscribe all subscriptions for the current instance."
    ] = False,
) -> UnsubscribeResponse | MCPResponse:
    """
    Unsubscribe from Unity editor events.
    
    Removes the subscription and optionally returns any pending buffered events.
    This is idempotent - calling multiple times with the same subscription_id
    is safe and will return the same result.
    
    Example:
        unsubscribe_editor_events(subscription_id="uuid-here")
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    gate = await maybe_run_tool_preflight(ctx, "unsubscribe_editor_events")
    if isinstance(gate, MCPResponse):
        return gate

    # Parse flush_pending_events
    should_flush = _parse_bool(flush_pending_events, default=True)
    should_unsubscribe_all = _parse_bool(unsubscribe_all, default=False)

    # Get the subscription from the resource
    from services.resources.event_subscriptions import (
        get_subscription,
        remove_subscription,
        get_pending_events,
        list_subscriptions,
    )

    if not subscription_id and not should_unsubscribe_all:
        return MCPResponse(
            success=False,
            error="missing_parameter",
            message="Provide subscription_id or unsubscribe_all=true"
        )

    if should_unsubscribe_all:
        removed_count = 0
        for sub in list_subscriptions():
            sub_id = sub.get("subscription_id")
            if not sub_id:
                continue
            sub_unity_instance = sub.get("unity_instance")
            if unity_instance and sub_unity_instance and unity_instance != sub_unity_instance:
                continue
            remove_subscription(sub_id)
            removed_count += 1

        return UnsubscribeResponse(
            success=True,
            message=f"Removed {removed_count} subscription(s)",
            data=UnsubscribeResult(
                subscription_id="*",
                unsubscribed=True,
                unsubscribed_all=True,
                unsubscribed_count=removed_count,
                was_active=removed_count > 0,
                events_received=0,
            )
        )

    subscription = get_subscription(subscription_id)
    
    if subscription is None:
        return MCPResponse(
            success=False,
            error="subscription_not_found",
            message=f"Subscription '{subscription_id}' not found. "
                    "It may have already been removed or expired."
        )

    # Verify the subscription belongs to this Unity instance (if specified)
    sub_unity_instance = subscription.get("unity_instance")
    if unity_instance and sub_unity_instance and unity_instance != sub_unity_instance:
        return MCPResponse(
            success=False,
            error="instance_mismatch",
            message=f"Subscription '{subscription_id}' belongs to a different Unity instance"
        )

    was_active = subscription.get("is_active", False)
    total_events_received = subscription.get("total_events_received", 0)
    
    # Get pending events if requested
    pending_events = []
    events_dropped = 0
    if should_flush:
        pending_events = get_pending_events(subscription_id, clear=True)
    else:
        # Count and discard
        events_dropped = len(get_pending_events(subscription_id, clear=True))

    # Try to unregister with Unity if we have a Unity subscription ID
    unity_subscription_id = subscription.get("unity_subscription_id")
    if unity_subscription_id:
        try:
            await _unregister_with_unity(
                unity_instance,
                unity_subscription_id,
            )
        except Exception as e:
            logger.warning(
                f"Could not unregister subscription {subscription_id} from Unity: {e}"
            )

    # Remove the subscription
    remove_subscription(subscription_id)

    logger.info(
        f"Removed subscription {subscription_id} (was_active={was_active}, "
        f"events_received={total_events_received})"
    )

    # Build response
    result = UnsubscribeResult(
        subscription_id=subscription_id,
        unsubscribed=True,
        was_active=was_active,
        events_received=total_events_received,
        events_dropped=events_dropped if not should_flush else None,
    )

    response_data = result.model_dump()
    
    # Include pending events if flushed
    if should_flush and pending_events:
        response_data["pending_events"] = pending_events[:100]  # Cap at 100 events
        if len(pending_events) > 100:
            response_data["pending_events_truncated"] = True
            response_data["total_pending_events"] = len(pending_events)

    return UnsubscribeResponse(
        success=True,
        message=f"Subscription '{subscription_id}' removed",
        data=response_data
    )


@mcp_for_unity_tool(
    unity_target=None,
    description=(
        "Lists all active event subscriptions with their status and event counts. "
        "Useful for debugging and monitoring subscription health."
    ),
    annotations=ToolAnnotations(
        title="List Event Subscriptions",
        readOnlyHint=True,
    ),
)
async def list_event_subscriptions(
    ctx: Context,
    include_expired: Annotated[
        bool | str,
        "If True, include expired subscriptions in the list. Default: False"
    ] = False,
) -> MCPResponse:
    """
    List all event subscriptions for the current Unity instance.
    
    Returns a list of subscriptions with their status, event counts, and
    other metadata. Useful for debugging and monitoring.
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    # Parse include_expired
    show_expired = _parse_bool(include_expired, default=False)

    from services.resources.event_subscriptions import (
        list_subscriptions,
        cleanup_expired_subscriptions,
    )

    # Clean up expired subscriptions first
    cleanup_expired_subscriptions()

    # Get all subscriptions
    all_subs = list_subscriptions()

    # Filter by Unity instance if specified
    filtered_subs = []
    for sub in all_subs:
        sub_unity = sub.get("unity_instance")
        if unity_instance and sub_unity and sub_unity != unity_instance:
            continue
        
        is_expired = sub.get("is_expired", False)
        if is_expired and not show_expired:
            continue
        
        # Sanitize the subscription data for output
        # Remove internal fields like event_buffer
        sanitized = {
            "subscription_id": sub.get("subscription_id"),
            "event_types": sub.get("event_types"),
            "unity_instance": sub.get("unity_instance"),
            "created_at": sub.get("created_at"),
            "expires_at": sub.get("expires_at"),
            "is_active": sub.get("is_active"),
            "is_expired": is_expired,
            "total_events_received": sub.get("total_events_received", 0),
            "buffered_events_count": len(sub.get("event_buffer", [])),
            "filter_criteria": sub.get("filter_criteria"),
            "buffer_events": sub.get("buffer_events", True),
        }
        filtered_subs.append(sanitized)

    return MCPResponse(
        success=True,
        message=f"Found {len(filtered_subs)} subscription(s)",
        data={
            "subscriptions": filtered_subs,
            "total_count": len(filtered_subs),
            "unity_instance_filter": unity_instance,
        }
    )


@mcp_for_unity_tool(
    unity_target=None,
    description=(
        "Polls for events from a specific subscription. "
        "Returns buffered events and clears the buffer. "
        "Non-blocking - returns immediately with available events."
    ),
    annotations=ToolAnnotations(
        title="Poll Subscription Events",
        readOnlyHint=True,
    ),
)
async def poll_subscription_events(
    ctx: Context,
    subscription_id: Annotated[
        str,
        "The subscription_id to poll"
    ],
    max_events: Annotated[
        int | str | None,
        "Maximum number of events to return (default: 100, max: 1000)"
    ] = None,
    wait_for_events: Annotated[
        bool | str,
        "If True, blocks until at least one event is available or timeout. "
        "If False (default), returns immediately."
    ] = False,
    wait_timeout_seconds: Annotated[
        int | str | None,
        "Maximum time to wait for events in seconds (default: 30, max: 60). "
        "Only used when wait_for_events=True."
    ] = None,
) -> MCPResponse:
    """
    Poll for events from a subscription.
    
    Returns buffered events and clears them from the subscription's buffer.
    Can optionally wait for events to arrive.
    
    Example:
        poll_subscription_events(subscription_id="uuid-here", max_events=50)
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    # Parse parameters
    max_ev = _parse_int(max_events, default=100, min_val=1, max_val=1000)
    if isinstance(max_ev, str):
        return MCPResponse(success=False, error=max_ev)

    should_wait = _parse_bool(wait_for_events, default=False)
    
    wait_timeout = _parse_int(wait_timeout_seconds, default=30, min_val=1, max_val=60)
    if isinstance(wait_timeout, str):
        return MCPResponse(success=False, error=wait_timeout)

    from services.resources.event_subscriptions import (
        get_subscription,
        get_pending_events,
        wait_for_events as wait_for_subscription_events,
    )

    # Verify subscription exists
    subscription = get_subscription(subscription_id)
    if subscription is None:
        return MCPResponse(
            success=False,
            error="subscription_not_found",
            message=f"Subscription '{subscription_id}' not found"
        )

    # Verify Unity instance match
    sub_unity_instance = subscription.get("unity_instance")
    if unity_instance and sub_unity_instance and unity_instance != sub_unity_instance:
        return MCPResponse(
            success=False,
            error="instance_mismatch",
            message=f"Subscription '{subscription_id}' belongs to a different Unity instance"
        )

    events = []
    
    if should_wait:
        # Wait for events
        import asyncio
        try:
            events = await asyncio.wait_for(
                wait_for_subscription_events(subscription_id, max_ev),
                timeout=wait_timeout
            )
        except asyncio.TimeoutError:
            # Return empty list on timeout
            pass
    else:
        # Get immediately available events
        events = get_pending_events(subscription_id, max_count=max_ev, clear=True)

    # Update last_poll timestamp
    from datetime import datetime, timezone
    subscription["last_poll_at"] = datetime.now(timezone.utc).isoformat()

    return MCPResponse(
        success=True,
        message=f"Retrieved {len(events)} event(s)",
        data={
            "subscription_id": subscription_id,
            "events": events,
            "more_available": len(subscription.get("event_buffer", [])) > 0,
        }
    )


def _parse_bool(value: bool | str, default: bool) -> bool:
    """Parse a boolean value that could be bool or string."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    return default


def _parse_int(
    value: int | str | None,
    default: int,
    min_val: int | None = None,
    max_val: int | None = None
) -> int | str:
    """Parse an integer value with optional bounds."""
    if value is None:
        return default
    
    try:
        result = int(value)
        if min_val is not None and result < min_val:
            return f"Value must be at least {min_val}"
        if max_val is not None and result > max_val:
            return f"Value must be at most {max_val}"
        return result
    except (ValueError, TypeError):
        return f"Value must be an integer, got: {value}"


async def _unregister_with_unity(
    unity_instance: str | None,
    unity_subscription_id: str,
) -> dict[str, Any]:
    """
    Try to unregister the subscription with Unity.
    """
    params = {
        "unity_subscription_id": unity_subscription_id,
    }
    
    response = await unity_transport.send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "unsubscribe_editor_events",
        params,
    )
    
    if isinstance(response, dict):
        return response
    
    return {"success": False, "error": str(response)}
