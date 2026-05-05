"""
Hot-reload Python modules inside the running MCP server process.

Why this exists: stdio MCP servers are tied to a Claude Code session via pipes.
Killing the server (the usual way to pick up Python source changes) severs the
pipe and the client doesn't auto-reconnect — the user has to restart their entire
Claude Code session, losing context. This tool re-imports server modules in-place
so source changes are loaded WITHOUT killing the process.

Limitations honestly:
- Tools registered via @mcp_for_unity_tool decorator run their decorator at module
  import time; reloading a tool module re-runs the decorator, which may or may not
  cleanly replace the FastMCP-side reference depending on FastMCP version. For
  *new* tool additions or breaking signature changes, a fresh session is still
  cleanest.
- Most useful for: helper functions, transport tweaks, action_policy entries,
  tool *body* changes (not signature/decorator changes).
- Modules with module-level state (caches, started threads, registered handlers)
  may end up with two copies of the state after reload.
"""
from __future__ import annotations

import importlib
import sys
from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool


# Modules we never want to touch — reloading them would corrupt the running server
# (FastMCP itself, the transport stdio handler, asyncio internals, etc.).
_EXCLUDED_PREFIXES = (
    "fastmcp",
    "mcp",
    "asyncio",
    "anyio",
    "services.registry",       # tool registration runs here; reloading mid-call breaks dispatch
    "services.tools.reload_server",  # don't reload ourselves mid-execution
)


@mcp_for_unity_tool(
    name="reload_server",
    unity_target=None,
    description=(
        "Hot-reload Python modules inside the running MCP server. Picks up source "
        "changes without killing the stdio server (which would disconnect the current "
        "Claude Code session). Pass module='services.tools.manage_profiler' to reload "
        "a single module, or call with no args to reload everything under 'services.*' "
        "and 'transport.*' that's currently loaded. CAVEATS: tool decorators may not "
        "re-register cleanly for added/renamed tools — for those, restart the session. "
        "Best for: helper fixes, body changes inside existing tools, action_policy edits, "
        "transport tweaks."
    ),
    annotations=ToolAnnotations(
        title="Reload Server Modules",
        destructiveHint=True,
    ),
    group=None,  # always-visible meta-tool
)
async def reload_server(
    ctx: Context,
    module: Annotated[
        str | None,
        "Specific module to reload (e.g. 'services.tools.manage_profiler'). If omitted, "
        "reloads every loaded module under 'services.*' or 'transport.*' (excluding the "
        "tool registry and reload_server itself)."
    ] = None,
    dry_run: Annotated[
        bool | str,
        "If true, list what *would* be reloaded without actually doing it. Default false."
    ] = False,
) -> dict[str, Any]:
    """Re-import Python modules in place."""

    # Coerce dry_run: accept bool or string forms
    if isinstance(dry_run, str):
        dry_run = dry_run.strip().lower() in ("true", "1", "yes", "on")

    # Build target list
    if module:
        if module not in sys.modules:
            return {
                "success": False,
                "error": "module_not_loaded",
                "message": f"Module '{module}' is not currently loaded — nothing to reload.",
                "data": {"loaded_module_count": len(sys.modules)},
            }
        if any(module.startswith(p) for p in _EXCLUDED_PREFIXES):
            return {
                "success": False,
                "error": "module_excluded",
                "message": (
                    f"Module '{module}' is on the never-reload list ({_EXCLUDED_PREFIXES}). "
                    "Reloading it would corrupt the running server."
                ),
            }
        targets = [module]
    else:
        prefixes = ("services.", "transport.")
        targets = [
            m for m in list(sys.modules.keys())
            if m.startswith(prefixes)
            and not any(m.startswith(p) for p in _EXCLUDED_PREFIXES)
            and sys.modules[m] is not None
        ]
        # Reload deeper modules before their parents so leaf changes take effect first.
        targets.sort(key=lambda m: -m.count("."))

    if dry_run:
        return {
            "success": True,
            "message": f"Dry run: would reload {len(targets)} module(s).",
            "data": {
                "dry_run": True,
                "would_reload_count": len(targets),
                "targets": targets,
            },
        }

    results: dict[str, str] = {}
    for m in targets:
        mod_obj = sys.modules.get(m)
        if mod_obj is None:
            results[m] = "skipped: not loaded"
            continue
        try:
            importlib.reload(mod_obj)
            results[m] = "reloaded"
        except Exception as ex:  # noqa: BLE001 — surface per-module failures, don't abort batch
            results[m] = f"error: {ex.__class__.__name__}: {ex}"

    success_count = sum(1 for v in results.values() if v == "reloaded")
    error_count = sum(1 for v in results.values() if v.startswith("error"))

    return {
        "success": error_count == 0,
        "message": f"Reloaded {success_count} of {len(targets)} module(s); {error_count} error(s).",
        "data": {
            "reloaded_count": success_count,
            "error_count": error_count,
            "skipped_count": len(targets) - success_count - error_count,
            "results": results,
            "note": (
                "Tool decorators run at import time; if you added/renamed tools or changed "
                "decorator parameters, the FastMCP-side registry may still hold old references. "
                "Start a fresh Claude Code session for those changes. Body-only edits are safe."
            ),
        },
    }
