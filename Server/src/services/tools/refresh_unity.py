from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from models import MCPResponse
from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
import transport.unity_transport as unity_transport
import transport.legacy.unity_connection as _legacy_conn
from transport.legacy.unity_connection import _extract_response_reason
from services.state.external_changes_scanner import external_changes_scanner
import services.resources.editor_state as editor_state

logger = logging.getLogger(__name__)

# Blocking reasons that indicate Unity is actually busy (not just stale status).
# Must match activityPhase values from EditorStateCache.cs
_REAL_BLOCKING_REASONS = {"compiling", "domain_reload", "running_tests", "asset_import"}


def _in_pytest() -> bool:
    """Return True when running inside pytest to avoid polling unmocked resources."""
    return "PYTEST_CURRENT_TEST" in os.environ


async def wait_for_editor_ready(
    ctx: Context,
    timeout_s: float = 30.0,
    *,
    return_last_state: bool = False,
) -> tuple[bool, float] | tuple[bool, float, dict | None]:
    """Poll editor_state until Unity is ready for tool calls.

    Returns (ready, elapsed_seconds) by default.  When ``return_last_state``
    is True, returns (ready, elapsed_seconds, last_state_data) where
    last_state_data is the most-recent ``data`` payload observed (used by
    refresh_unity to surface accurate post-wait state on timeout/success).

    Treats exceptions from get_editor_state as "not ready yet" so the loop
    survives transient connection errors during domain reload.
    """
    if _in_pytest():
        return (True, 0.0, None) if return_last_state else (True, 0.0)

    start = time.monotonic()
    last_data: dict | None = None
    # Require two consecutive "ready" observations before declaring ready.
    # Right after refresh_unity returns, editor_state can briefly look idle
    # in the gap between the C# tool returning and Unity actually entering
    # compile/domain-reload — a single sample is not enough to trust.
    consecutive_ready = 0
    required_consecutive_ready = 2
    poll_interval = 0.25  # 250ms — responsive without hammering the editor
    while time.monotonic() - start < timeout_s:
        try:
            state_resp = await editor_state.get_editor_state(ctx)
            state = state_resp.model_dump() if hasattr(state_resp, "model_dump") else state_resp
            data = (state or {}).get("data") if isinstance(state, dict) else None
            if isinstance(data, dict):
                last_data = data
            advice = (data or {}).get("advice") if isinstance(data, dict) else None
            if isinstance(advice, dict):
                ready_now = False
                if advice.get("ready_for_tools") is True:
                    ready_now = True
                else:
                    blocking = set(advice.get("blocking_reasons") or [])
                    # Only "stale_status" (or no reasons) counts as not-really-blocked.
                    # Any real blocker keeps us waiting.
                    if not (blocking & _REAL_BLOCKING_REASONS):
                        ready_now = True
                if ready_now:
                    consecutive_ready += 1
                    if consecutive_ready >= required_consecutive_ready:
                        elapsed = time.monotonic() - start
                        return (True, elapsed, last_data) if return_last_state else (True, elapsed)
                else:
                    consecutive_ready = 0
        except Exception:
            # Connection errors during domain reload are expected — reset the
            # consecutive counter so we don't accept a single post-disconnect
            # success as proof of readiness.
            consecutive_ready = 0
        await asyncio.sleep(poll_interval)

    elapsed = time.monotonic() - start
    return (False, elapsed, last_data) if return_last_state else (False, elapsed)


def is_reloading_rejection(resp: Any) -> bool:
    """True when Unity rejected a command because it thinks it is reloading.

    The command was never executed, so retrying is safe.
    """
    if not isinstance(resp, dict) or resp.get("success"):
        return False
    data = resp.get("data") or {}
    return data.get("reason") == "reloading" and resp.get("hint") == "retry"


def is_connection_lost_after_send(resp: Any) -> bool:
    """True when a mutation's response indicates TCP was lost after command was sent.

    Script mutations trigger domain reload which kills the TCP connection.
    The mutation was likely executed but the response was lost.
    """
    if isinstance(resp, dict):
        if resp.get("success"):
            return False
        err = (resp.get("error") or resp.get("message") or "").lower()
    else:
        if getattr(resp, "success", None):
            return False
        err = (getattr(resp, "error", "") or "").lower()
    return "connection closed" in err or "disconnected" in err or "aborted" in err


async def send_mutation(
    ctx: Context,
    unity_instance: str | None,
    command: str,
    params: dict[str, Any],
    *,
    verify_after_disconnect: Callable[[], Awaitable[dict | None]] | None = None,
) -> dict | Any:
    """Send a non-idempotent mutation with reload recovery.

    Handles the full retry/recovery pattern for script mutations:
    1. Send with retry_on_reload=False (don't re-send if Unity is reloading)
    2. If reloading rejection (command never executed) → wait + retry once
    3. If connection lost after send → wait + verify via callback
    4. Wait for editor readiness before returning

    Args:
        verify_after_disconnect: async callable returning a replacement response
            dict if the mutation was verified after connection loss, or None to
            keep the original error response.
    """
    resp = await unity_transport.send_with_unity_instance(
        _legacy_conn.async_send_command_with_retry,
        unity_instance,
        command,
        params,
        retry_on_reload=False,
    )
    if is_reloading_rejection(resp):
        await wait_for_editor_ready(ctx)
        resp = await unity_transport.send_with_unity_instance(
            _legacy_conn.async_send_command_with_retry,
            unity_instance,
            command,
            params,
            retry_on_reload=False,
        )
    if is_connection_lost_after_send(resp) and verify_after_disconnect:
        await wait_for_editor_ready(ctx)
        verified = await verify_after_disconnect()
        if verified is not None:
            resp = verified
    await wait_for_editor_ready(ctx)
    return resp


async def verify_edit_by_sha(
    unity_instance: str | None,
    name: str,
    path: str,
    pre_sha: str | None,
) -> bool:
    """Verify a script edit was applied by comparing SHA before and after.

    Returns True if the file's SHA changed (edit likely applied).
    """
    if not pre_sha:
        return False
    try:
        verify = await unity_transport.send_with_unity_instance(
            _legacy_conn.async_send_command_with_retry,
            unity_instance,
            "manage_script",
            {"action": "get_sha", "name": name, "path": path},
        )
        if isinstance(verify, dict) and verify.get("success"):
            new_sha = (verify.get("data") or {}).get("sha256")
            return bool(new_sha and new_sha != pre_sha)
    except Exception as exc:
        logger.debug(
            "Failed to verify edit after disconnect for %s at %s: %r",
            name, path, exc,
        )
    return False


@mcp_for_unity_tool(
    description="Request a Unity asset database refresh and optionally a script compilation. Can optionally wait for readiness.",
    annotations=ToolAnnotations(
        title="Refresh Unity",
        destructiveHint=True,
    ),
)
async def refresh_unity(
    ctx: Context,
    mode: Annotated[Literal["if_dirty", "force"], "Refresh mode"] = "if_dirty",
    scope: Annotated[Literal["assets", "scripts", "all"],
                     "Refresh scope"] = "all",
    compile: Annotated[Literal["none", "request"],
                       "Whether to request compilation"] = "none",
    wait_for_ready: Annotated[bool,
                              "If true, wait until editor_state.advice.ready_for_tools is true"] = True,
) -> MCPResponse | dict[str, Any]:
    unity_instance = await get_unity_instance_from_context(ctx)

    params: dict[str, Any] = {
        "mode": mode,
        "scope": scope,
        "compile": compile,
        "wait_for_ready": bool(wait_for_ready),
    }

    recovered_from_disconnect = False
    # Don't retry on reload - refresh_unity triggers compilation/reload,
    # so retrying would cause multiple reloads (issue #577)
    response = await unity_transport.send_with_unity_instance(
        _legacy_conn.async_send_command_with_retry,
        unity_instance,
        "refresh_unity",
        params,
        retry_on_reload=False,
    )

    # Handle connection errors during refresh/compile gracefully.
    # Unity disconnects during domain reload, which is expected behavior - not a failure.
    # If we sent the command and connection closed, the refresh was likely triggered successfully.
    # Convert MCPResponse to dict if needed
    response_dict = response if isinstance(response, dict) else (response.model_dump() if hasattr(response, "model_dump") else response.__dict__)
    if not response_dict.get("success", True):
        hint = response_dict.get("hint")
        err = (response_dict.get("error") or response_dict.get("message") or "").lower()
        reason = _extract_response_reason(response_dict)

        # Connection closed/timeout during compile = refresh was triggered, Unity is reloading
        # This is SUCCESS, not failure - don't return error to prevent Claude Code from retrying
        is_connection_lost = (
            "connection closed" in err
            or "disconnected" in err
            or "aborted" in err  # WinError 10053: connection aborted
            or "timeout" in err
            or reason == "reloading"
        )

        if is_connection_lost and compile == "request":
            # EXPECTED BEHAVIOR: When compile="request", Unity triggers domain reload which
            # causes connection to close mid-command. This is NOT a failure - the refresh
            # was successfully triggered. Treating this as success prevents Claude Code from
            # retrying unnecessarily (which would cause multiple domain reloads - issue #577).
            # The subsequent wait_for_ready loop (below) will verify Unity becomes ready.
            logger.info("refresh_unity: Connection lost during compile (expected - domain reload triggered)")
            recovered_from_disconnect = True
        elif hint == "retry" or "could not connect" in err:
            # Retryable error - proceed to wait loop if wait_for_ready
            if not wait_for_ready:
                return MCPResponse(**response_dict)
            recovered_from_disconnect = True
        else:
            # Non-recoverable error - connection issue unrelated to domain reload
            logger.warning(f"refresh_unity: Non-recoverable error (compile={compile}): {err[:100]}")
            return MCPResponse(**response_dict)

    # Server-side wait loop: when the caller asked us to wait for readiness,
    # ACTUALLY wait. The C# tool may return immediately while Unity is still
    # compiling (Unity 6+ skips its own wait when compile was requested), so
    # this loop is the canonical waiter.
    #
    # Behavior:
    #   wait_for_ready=False  → return immediately (unchanged from prior behavior).
    #   wait_for_ready=True   → poll editor_state until ready_for_tools is true,
    #                           require two consecutive ready samples to avoid
    #                           the "briefly idle, about to compile" race, and
    #                           return success only when readiness is confirmed.
    #                           On timeout, return success=False with timed_out=true
    #                           and the current state — never silently report
    #                           success while the editor is mid-compile.
    wait_timeout_s = 60.0
    ready_confirmed = False
    last_state_data: dict | None = None
    if wait_for_ready:
        ready_confirmed, wait_elapsed, last_state_data = await wait_for_editor_ready(
            ctx, timeout_s=wait_timeout_s, return_last_state=True
        )

        if not ready_confirmed:
            logger.warning(
                "refresh_unity: Timed out after %.1fs waiting for editor to become ready",
                wait_timeout_s,
            )
            advice = (last_state_data or {}).get("advice") if isinstance(last_state_data, dict) else None
            blocking_reasons = list(advice.get("blocking_reasons") or []) if isinstance(advice, dict) else []
            compilation = (last_state_data or {}).get("compilation") if isinstance(last_state_data, dict) else None
            is_compiling = bool(compilation.get("is_compiling")) if isinstance(compilation, dict) else None
            return MCPResponse(
                success=False,
                error="refresh_timeout_waiting_for_ready",
                message=(
                    f"refresh_unity: wait_for_ready=true timed out after {wait_timeout_s:.0f}s; "
                    "editor still not ready for tool calls."
                ),
                data={
                    "timed_out": True,
                    "wait_seconds": wait_elapsed,
                    "wait_timeout_seconds": wait_timeout_s,
                    "refresh_triggered": response_dict.get("data", {}).get("refresh_triggered")
                        if isinstance(response_dict.get("data"), dict) else None,
                    "compile_requested": compile == "request",
                    "blocking_reasons": blocking_reasons,
                    "is_compiling": is_compiling,
                    "hint": "Call wait_for_editor_condition compile_idle or poll editor_state.",
                },
            )

    # After readiness is restored, clear any external-dirty flag for this instance so future tools can proceed cleanly.
    try:
        inst = unity_instance or await editor_state.infer_single_instance_id(ctx)
        if inst:
            external_changes_scanner.clear_dirty(inst)
    except Exception:
        pass

    if recovered_from_disconnect:
        return MCPResponse(
            success=True,
            message="Refresh recovered after Unity disconnect/retry; editor is ready.",
            data={"recovered_from_disconnect": True, "ready_for_tools": True},
        )

    # When wait_for_ready=True and the wait succeeded, the original C# response
    # likely still says resulting_state="compiling" because Unity 6+ short-circuits
    # its internal waiter when compile was requested. Patch the response data so
    # callers see the post-wait state instead of the stale snapshot.
    if wait_for_ready and ready_confirmed and isinstance(response_dict, dict):
        patched = dict(response_dict)
        data_field = patched.get("data")
        if isinstance(data_field, dict):
            data_field = dict(data_field)
            data_field["resulting_state"] = "idle"
            data_field["ready_for_tools"] = True
            data_field["server_waited_for_ready"] = True
            data_field["hint"] = "Unity refresh completed; editor is ready."
            patched["data"] = data_field
        return MCPResponse(**patched)

    return MCPResponse(**response_dict) if isinstance(response, dict) else response
