"""Runtime MCP gating helpers."""

from __future__ import annotations

from typing import Any

from core.config import config


def get_runtime_opt_in_gate(tool_name: str) -> dict[str, Any] | None:
    """Return an error payload when runtime MCP is disabled."""
    if config.runtime_mcp_enabled:
        return None

    return {
        "success": False,
        "error": "runtime_mcp_disabled",
        "message": (
            "Runtime MCP is disabled by default. "
            "Enable 'runtime_mcp_enabled: true' in the server configuration to use runtime tools."
        ),
        "data": {
            "tool": tool_name,
            "runtime_mcp_enabled": False,
            "requires_explicit_opt_in": True,
        },
    }
