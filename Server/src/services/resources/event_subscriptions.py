"""
Event subscription state management resource.

Manages the lifecycle and state of editor event subscriptions.
Provides thread-safe access to subscription data and event buffering.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Any

from fastmcp import Context
from pydantic import BaseModel

from models import MCPResponse
from services.registry import mcp_for_unity_resource
from services.tools import get_unity_instance_from_context

logger = logging.getLogger(__name__)

# In-memory subscription storage
# Maps subscription_id -> subscription_data
_subscriptions: dict[str, dict[str, Any]] = {}

# Event waiters for poll_subscription_events with wait_for_events=True
# Maps subscription_id -> asyncio.Event
_event_waiters: dict[str, asyncio.Event] = {}

# Lock for thread-safe access
_lock = threading.RLock()

# Maximum events to buffer per subscription
MAX_BUFFER_SIZE = 1000


class EventPayload(BaseModel):
    """Standard event payload format."""
    event_id: str
    event_type: str
    timestamp: str  # ISO format
    data: dict[str, Any]
    unity_instance: str | None = None


class SubscriptionStatus(BaseModel):
    """Status of a single subscription."""
    subscription_id: str
    event_types: list[str]
    is_active: bool
    is_expired: bool
    created_at: str
    expires_at: str | None
    total_events_received: int
    buffered_events_count: int


class SubscriptionsListData(BaseModel):
    """Data for listing subscriptions."""
    subscriptions: list[SubscriptionStatus]
    total_count: int


class SubscriptionDetailData(BaseModel):
    """Detailed subscription information."""
    subscription_id: str
    event_types: list[str]
    unity_instance: str | None
    created_at: str
    expires_at: str | None
    last_poll_at: str | None
    is_active: bool
    is_expired: bool
    filter_criteria: dict[str, Any]
    buffer_events: bool
    total_events_received: int
    buffered_events_count: int
    unity_subscription_id: str | None


def add_subscription(subscription_id: str, data: dict[str, Any]) -> None:
    """Add a new subscription to the registry."""
    with _lock:
        _subscriptions[subscription_id] = data
        _event_waiters[subscription_id] = asyncio.Event()
        logger.debug(f"Added subscription {subscription_id}")


def remove_subscription(subscription_id: str) -> dict[str, Any] | None:
    """Remove a subscription from the registry."""
    with _lock:
        data = _subscriptions.pop(subscription_id, None)
        _event_waiters.pop(subscription_id, None)
        if data:
            logger.debug(f"Removed subscription {subscription_id}")
        return data


def get_subscription(subscription_id: str) -> dict[str, Any] | None:
    """Get a subscription by ID."""
    with _lock:
        sub = _subscriptions.get(subscription_id)
        if sub is None:
            return None
        
        # Check if expired
        expires_at = sub.get("expires_at")
        if expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at)
                if expiry < datetime.now(timezone.utc):
                    sub["is_expired"] = True
                    sub["is_active"] = False
            except (ValueError, TypeError):
                pass
        
        return sub.copy() if sub else None


def list_subscriptions(
    unity_instance: str | None = None,
    include_expired: bool = False,
) -> list[dict[str, Any]]:
    """List all subscriptions, optionally filtered."""
    with _lock:
        results = []
        for sub_id, sub in _subscriptions.items():
            # Filter by Unity instance
            if unity_instance and sub.get("unity_instance") != unity_instance:
                continue
            
            # Check expiration
            is_expired = _is_subscription_expired(sub)
            sub["is_expired"] = is_expired
            
            if is_expired and not include_expired:
                continue
            
            results.append(sub.copy())
        
        return results


def _is_subscription_expired(sub: dict[str, Any]) -> bool:
    """Check if a subscription has expired."""
    expires_at = sub.get("expires_at")
    if not expires_at:
        return False
    
    try:
        expiry = datetime.fromisoformat(expires_at)
        return expiry < datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return False


def cleanup_expired_subscriptions() -> int:
    """Remove expired subscriptions. Returns count removed."""
    with _lock:
        to_remove = []
        for sub_id, sub in _subscriptions.items():
            if _is_subscription_expired(sub):
                to_remove.append(sub_id)
        
        for sub_id in to_remove:
            _subscriptions.pop(sub_id, None)
            _event_waiters.pop(sub_id, None)
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} expired subscription(s)")
        
        return len(to_remove)


def add_event_to_subscription(
    subscription_id: str,
    event_type: str,
    event_data: dict[str, Any],
    unity_instance: str | None = None,
) -> bool:
    """
    Add an event to a subscription's buffer.
    
    Returns True if event was added, False if subscription not found or buffering disabled.
    """
    with _lock:
        sub = _subscriptions.get(subscription_id)
        if sub is None:
            return False
        
        if not sub.get("is_active", False):
            return False
        
        if not sub.get("buffer_events", True):
            sub["total_events_received"] = sub.get("total_events_received", 0) + 1
            return True  # Counted but not buffered
        
        # Create event payload
        from uuid import uuid4
        event = EventPayload(
            event_id=str(uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=event_data,
            unity_instance=unity_instance,
        )
        
        # Add to buffer
        buffer = sub.setdefault("event_buffer", [])
        buffer.append(event.model_dump())
        
        # Trim buffer if too large
        if len(buffer) > MAX_BUFFER_SIZE:
            dropped = len(buffer) - MAX_BUFFER_SIZE
            sub["event_buffer"] = buffer[-MAX_BUFFER_SIZE:]
            sub["events_dropped"] = sub.get("events_dropped", 0) + dropped
        
        sub["total_events_received"] = sub.get("total_events_received", 0) + 1
        
        # Signal any waiters
        waiter = _event_waiters.get(subscription_id)
        if waiter:
            waiter.set()
        
        return True


def get_pending_events(
    subscription_id: str,
    max_count: int | None = None,
    clear: bool = True,
) -> list[dict[str, Any]]:
    """
    Get pending events from a subscription's buffer.
    
    Args:
        subscription_id: The subscription ID
        max_count: Maximum number of events to return (None for all)
        clear: If True, clear the returned events from the buffer
    
    Returns:
        List of event payloads
    """
    with _lock:
        sub = _subscriptions.get(subscription_id)
        if sub is None:
            return []
        
        buffer = sub.get("event_buffer", [])
        if not buffer:
            return []
        
        # Get events
        if max_count is None or max_count >= len(buffer):
            events = buffer[:]
            if clear:
                sub["event_buffer"] = []
        else:
            events = buffer[:max_count]
            if clear:
                sub["event_buffer"] = buffer[max_count:]
        
        # Reset the waiter if buffer is now empty
        if not sub.get("event_buffer"):
            waiter = _event_waiters.get(subscription_id)
            if waiter:
                waiter.clear()
        
        return events


async def wait_for_events(
    subscription_id: str,
    max_count: int = 1,
    timeout: float | None = None,
) -> list[dict[str, Any]]:
    """
    Wait for events to arrive on a subscription.
    
    This is used by poll_subscription_events when wait_for_events=True.
    
    Args:
        subscription_id: The subscription ID
        max_count: Maximum number of events to return
        timeout: Maximum time to wait (None for default)
    
    Returns:
        List of event payloads (may be empty on timeout)
    """
    with _lock:
        sub = _subscriptions.get(subscription_id)
        if sub is None:
            return []
        
        # Check if events already available
        buffer = sub.get("event_buffer", [])
        if buffer:
            return get_pending_events(subscription_id, max_count, clear=True)
        
        # Get or create waiter
        waiter = _event_waiters.get(subscription_id)
        if waiter is None:
            waiter = asyncio.Event()
            _event_waiters[subscription_id] = waiter
    
    # Wait outside the lock
    try:
        await asyncio.wait_for(waiter.wait(), timeout=timeout or 30.0)
    except asyncio.TimeoutError:
        return []
    
    # Get events after wait
    return get_pending_events(subscription_id, max_count, clear=True)


def broadcast_event(
    event_type: str,
    event_data: dict[str, Any],
    unity_instance: str | None = None,
) -> int:
    """
    Broadcast an event to all matching subscriptions.
    
    Returns the number of subscriptions that received the event.
    
    Args:
        event_type: The type of event
        event_data: Event-specific data
        unity_instance: The Unity instance the event originated from
    """
    with _lock:
        matching_subs = []
        for sub_id, sub in _subscriptions.items():
            # Check if subscription is active
            if not sub.get("is_active", False):
                continue
            
            # Check if expired
            if _is_subscription_expired(sub):
                continue
            
            # Check if Unity instance matches
            sub_unity = sub.get("unity_instance")
            if unity_instance and sub_unity and sub_unity != unity_instance:
                continue
            
            # Check if event type is subscribed
            if event_type not in sub.get("event_types", []):
                continue
            
            # Check filter criteria
            filters = sub.get("filter_criteria", {})
            if filters and not _matches_filters(event_type, event_data, filters):
                continue
            
            matching_subs.append(sub_id)
    
    # Add events outside the lock
    count = 0
    for sub_id in matching_subs:
        if add_event_to_subscription(sub_id, event_type, event_data, unity_instance):
            count += 1
    
    return count


def _matches_filters(
    event_type: str,
    event_data: dict[str, Any],
    filters: dict[str, Any],
) -> bool:
    """Check if an event matches the filter criteria."""
    # Console updates filters
    if "log_level" in filters and event_type == "console_updates":
        event_level = event_data.get("level", "").lower()
        filter_level = filters["log_level"].lower()
        if filter_level == "error" and event_level not in ("error", "exception", "assert"):
            return False
        if filter_level == "warning" and event_level not in ("warning", "error", "exception", "assert"):
            return False
    
    # Play mode transition filters
    if "target_state" in filters and event_type == "play_mode_transitions":
        if event_data.get("new_state") != filters["target_state"]:
            return False
    
    # Compile state filters
    if "target_state" in filters and event_type == "compile_state_changes":
        if event_data.get("state") != filters["target_state"]:
            return False
    
    # Hierarchy changes filters
    if "scene_path" in filters and event_type == "hierarchy_changes":
        if event_data.get("scene_path") != filters["scene_path"]:
            return False
    
    # Test job progress filters
    if "job_id" in filters and event_type == "test_job_progress":
        if event_data.get("job_id") != filters["job_id"]:
            return False
    
    return True


def get_subscription_stats() -> dict[str, Any]:
    """Get aggregate statistics about all subscriptions."""
    with _lock:
        total = len(_subscriptions)
        active = sum(1 for s in _subscriptions.values() if s.get("is_active", False))
        expired = sum(1 for s in _subscriptions.values() if _is_subscription_expired(s))
        total_events = sum(s.get("total_events_received", 0) for s in _subscriptions.values())
        total_buffered = sum(len(s.get("event_buffer", [])) for s in _subscriptions.values())
        
        event_type_counts: dict[str, int] = {}
        for s in _subscriptions.values():
            for et in s.get("event_types", []):
                event_type_counts[et] = event_type_counts.get(et, 0) + 1
        
        return {
            "total_subscriptions": total,
            "active_subscriptions": active,
            "expired_subscriptions": expired,
            "total_events_received": total_events,
            "total_events_buffered": total_buffered,
            "subscriptions_by_event_type": event_type_counts,
        }


@mcp_for_unity_resource(
    uri="mcpforunity://events/subscriptions",
    name="event_subscriptions",
    description=(
        "Lists all event subscriptions with their status and event counts. "
        "Use subscribe_editor_events tool to create subscriptions. "
        "Use poll_subscription_events tool to retrieve events."
    ),
)
async def get_event_subscriptions(
    ctx: Context,
) -> MCPResponse:
    """
    Get all event subscriptions for the current Unity instance.
    
    This resource provides a read-only view of active subscriptions.
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    # Clean up expired subscriptions
    cleanup_expired_subscriptions()
    
    # Get subscriptions
    subs = list_subscriptions(
        unity_instance=unity_instance,
        include_expired=False,
    )
    
    # Build response
    subscription_statuses = []
    for sub in subs:
        status = SubscriptionStatus(
            subscription_id=sub["subscription_id"],
            event_types=sub["event_types"],
            is_active=sub.get("is_active", False),
            is_expired=sub.get("is_expired", False),
            created_at=sub["created_at"],
            expires_at=sub.get("expires_at"),
            total_events_received=sub.get("total_events_received", 0),
            buffered_events_count=len(sub.get("event_buffer", [])),
        )
        subscription_statuses.append(status)
    
    data = SubscriptionsListData(
        subscriptions=subscription_statuses,
        total_count=len(subscription_statuses),
    )
    
    return MCPResponse(
        success=True,
        message=f"Found {len(subscription_statuses)} subscription(s)",
        data=data.model_dump()
    )


@mcp_for_unity_resource(
    uri="mcpforunity://events/subscriptions/{subscription_id}",
    name="event_subscription_detail",
    description="Gets detailed information about a specific event subscription.",
)
async def get_event_subscription_detail(
    ctx: Context,
    subscription_id: str,
) -> MCPResponse:
    """
    Get detailed information about a specific subscription.
    
    URI: mcpforunity://events/subscriptions/{subscription_id}
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    sub = get_subscription(subscription_id)
    if sub is None:
        return MCPResponse(
            success=False,
            error="subscription_not_found",
            message=f"Subscription '{subscription_id}' not found"
        )
    
    # Verify Unity instance match
    sub_unity = sub.get("unity_instance")
    if unity_instance and sub_unity and sub_unity != unity_instance:
        return MCPResponse(
            success=False,
            error="instance_mismatch",
            message=f"Subscription '{subscription_id}' belongs to a different Unity instance"
        )
    
    detail = SubscriptionDetailData(
        subscription_id=sub["subscription_id"],
        event_types=sub["event_types"],
        unity_instance=sub.get("unity_instance"),
        created_at=sub["created_at"],
        expires_at=sub.get("expires_at"),
        last_poll_at=sub.get("last_poll_at"),
        is_active=sub.get("is_active", False),
        is_expired=sub.get("is_expired", False),
        filter_criteria=sub.get("filter_criteria", {}),
        buffer_events=sub.get("buffer_events", True),
        total_events_received=sub.get("total_events_received", 0),
        buffered_events_count=len(sub.get("event_buffer", [])),
        unity_subscription_id=sub.get("unity_subscription_id"),
    )
    
    return MCPResponse(
        success=True,
        message=f"Subscription details for '{subscription_id}'",
        data=detail.model_dump()
    )


@mcp_for_unity_resource(
    uri="mcpforunity://events/stats",
    name="event_subscription_stats",
    description="Get aggregate statistics about all event subscriptions.",
)
async def get_event_subscription_stats(
    ctx: Context,
) -> MCPResponse:
    """
    Get aggregate statistics about event subscriptions.
    """
    stats = get_subscription_stats()
    
    return MCPResponse(
        success=True,
        message="Event subscription statistics",
        data=stats
    )
