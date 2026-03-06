from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models import MCPResponse
from services.tools.preflight import preflight


@dataclass(frozen=True)
class ToolActionPolicy:
    """Policy defining the behavior and capabilities of a tool or action.

    Attributes:
        mutating: Whether the tool/action modifies state
        high_risk: Whether the tool/action is high-risk (destructive or impactful)
        wait_for_no_compile: Whether to wait for compilation to finish before executing
        refresh_if_dirty: Whether to refresh assets if external changes are detected
        requires_no_tests: Whether the tool requires no tests to be running
        supports_dry_run: Whether the tool/action supports dry-run (preview) mode
        local_only: Whether the tool is server-only (doesn't require Unity connection)
        runtime_only: Whether the tool only works when Unity is in play mode
        requires_explicit_opt_in: Whether the tool requires explicit user opt-in
    """

    mutating: bool
    high_risk: bool = False
    wait_for_no_compile: bool = True
    refresh_if_dirty: bool = True
    requires_no_tests: bool = False
    supports_dry_run: bool = False
    local_only: bool = False
    runtime_only: bool = False
    requires_explicit_opt_in: bool = False


_READ_ONLY_ACTIONS: dict[str, set[str]] = {
    "manage_addressables": {
        "analyze",
        "get_groups",
        "get_group_assets",
        "get_labels",
        "validate",
        "get_settings",
    },
    "manage_catalog": {"list"},
    "manage_error_catalog": {"list"},
    "manage_animation": {
        "animator_get_info",
        "animator_get_parameter",
        "controller_get_info",
        "clip_get_info",
    },
    "manage_asset": {"search", "get_info", "get_components"},
    "manage_editor": {"telemetry_status", "telemetry_ping"},
    "manage_material": {"ping", "get_material_info"},
    "manage_package_manager": {
        "list_installed",
        "search_packages",
        "get_package_info",
        "list_registries",
    },
    "manage_prefabs": {"get_info", "get_hierarchy"},
    "manage_scene": {
        "get_hierarchy",
        "get_active",
        "get_build_settings",
        "screenshot",
        "scene_view_frame",
    },
    "manage_script": {"read"},
    "manage_subagents": {"list"},
    "manage_shader": {"read"},
    "manage_tools": {"list_groups"},
    "manage_ui": {"ping", "read", "get_visual_tree", "list"},
    "manage_vfx": {
        "ping",
        "particle_get_info",
        "vfx_get_info",
        "vfx_list_templates",
        "vfx_list_assets",
        "line_get_info",
        "trail_get_info",
    },
    "read_console": {"get"},
}

_ALWAYS_READ_ONLY_TOOLS = {
    "audit_prefab_integrity",
    "audit_scene_integrity",
    "debug_request_context",
    "find_gameobjects",
    "find_in_file",
    "get_sha",
    "get_test_job",
    "manage_script_capabilities",
    "preflight_audit",
    "validate_compile_health",
    "validate_script",
}

_ALWAYS_MUTATING_TOOLS = {
    "apply_text_edits",
    "create_script",
    "delete_script",
    "execute_custom_tool",
    "execute_menu_item",
    "manage_components",
    "manage_gameobject",
    "manage_scriptable_object",
    "manage_texture",
    "refresh_unity",
    "run_tests",
    "script_apply_edits",
}

# Tools that support dry-run (preview) mode
_DRY_RUN_SUPPORTED_TOOLS = {
    "apply_text_edits",
    "script_apply_edits",
    "create_script",
    "delete_script",
    "manage_script",
    "manage_scene",
    "manage_gameobject",
    "manage_components",
    "manage_asset",
    "manage_material",
    "manage_prefabs",
    "manage_shader",
    "manage_texture",
    "manage_ui",
    "manage_vfx",
    "manage_animation",
    "manage_scriptable_object",
    "manage_addressables",  # Supports dry_run for build operations
    "batch_execute",
}

# Server-only tools that don't require Unity connection
_LOCAL_ONLY_TOOLS = {
    "debug_request_context",
    "manage_catalog",
    "manage_error_catalog",
    "manage_script_capabilities",
    "manage_subagents",
    "manage_tools",
    "preflight_audit",
    "set_active_instance",
    "validate_compile_health",
}

# Tools that only work in Unity play mode
_RUNTIME_ONLY_TOOLS = {
    "read_console",
}

# High-risk tools that may require explicit opt-in
_HIGH_RISK_TOOLS = {
    "delete_script",
    "execute_menu_item",
    "batch_execute",
    "execute_custom_tool",
    "manage_addressables",  # Build operations are high-risk
}


def get_known_read_only_actions(tool_name: str | None) -> list[str]:
    normalized_tool = (tool_name or "").strip()
    if not normalized_tool:
        return []
    return sorted(_READ_ONLY_ACTIONS.get(normalized_tool, set()))


def get_tool_action_model(tool_name: str | None) -> str:
    normalized_tool = (tool_name or "").strip()
    if not normalized_tool:
        return "unknown"
    if normalized_tool == "batch_execute":
        return "mixed"
    if normalized_tool in _ALWAYS_READ_ONLY_TOOLS:
        return "always_read_only"
    if normalized_tool in _ALWAYS_MUTATING_TOOLS:
        return "always_mutating"
    if normalized_tool in _READ_ONLY_ACTIONS:
        return "mixed"
    return "unknown"


def _normalize_action(action: Any) -> str | None:
    if action is None:
        return None
    if not isinstance(action, str):
        return None
    normalized = action.strip().lower()
    return normalized or None


def _is_high_risk_tool(tool_name: str) -> bool:
    """Determine if a tool is classified as high-risk."""
    if tool_name in _HIGH_RISK_TOOLS:
        return True
    if tool_name in _ALWAYS_MUTATING_TOOLS:
        return True
    return False


def _supports_dry_run(tool_name: str, action: str | None = None) -> bool:
    """Determine if a tool/action supports dry-run mode."""
    if tool_name in _DRY_RUN_SUPPORTED_TOOLS:
        # For mixed tools, only mutating actions support dry-run
        if action and tool_name in _READ_ONLY_ACTIONS:
            return action not in _READ_ONLY_ACTIONS[tool_name]
        return True
    return False


def _is_local_only(tool_name: str) -> bool:
    """Determine if a tool is server-only (doesn't require Unity)."""
    return tool_name in _LOCAL_ONLY_TOOLS


def _is_runtime_only(tool_name: str) -> bool:
    """Determine if a tool only works in Unity play mode."""
    return tool_name in _RUNTIME_ONLY_TOOLS


def _requires_explicit_opt_in(tool_name: str) -> bool:
    """Determine if a tool requires explicit user opt-in."""
    # Check configuration for tool-specific opt-in status
    try:
        from core.capability_flags import requires_explicit_opt_in as config_requires_opt_in
        return config_requires_opt_in(tool_name)
    except ImportError:
        pass
    # Fallback to hardcoded high-risk list
    return tool_name in _HIGH_RISK_TOOLS


def get_tool_action_policy(
    tool_name: str | None,
    *,
    action: Any = None,
    commands: list[dict[str, Any]] | None = None,
) -> ToolActionPolicy:
    """Get the action policy for a tool.

    Args:
        tool_name: Name of the tool
        action: Specific action being performed (for mixed tools)
        commands: List of commands (for batch_execute)

    Returns:
        ToolActionPolicy with all capability flags set appropriately
    """
    normalized_tool = (tool_name or "").strip()
    if not normalized_tool:
        return ToolActionPolicy(
            mutating=True,
            high_risk=True,
            supports_dry_run=False,
            local_only=False,
            runtime_only=False,
            requires_explicit_opt_in=True,
        )

    if normalized_tool == "batch_execute":
        # When no commands specified (bare tool query), treat as high-risk
        if not commands:
            return ToolActionPolicy(
                mutating=True,  # Default to mutating for safety
                high_risk=True,
                supports_dry_run=True,
                local_only=False,
                runtime_only=False,
                requires_explicit_opt_in=True,
            )
        return get_batch_policy(commands)

    if normalized_tool in _ALWAYS_READ_ONLY_TOOLS:
        return ToolActionPolicy(
            mutating=False,
            high_risk=False,
            supports_dry_run=_supports_dry_run(normalized_tool),
            local_only=_is_local_only(normalized_tool),
            runtime_only=_is_runtime_only(normalized_tool),
            requires_explicit_opt_in=_requires_explicit_opt_in(normalized_tool),
        )

    if normalized_tool in _ALWAYS_MUTATING_TOOLS:
        return ToolActionPolicy(
            mutating=True,
            high_risk=True,
            supports_dry_run=_supports_dry_run(normalized_tool),
            local_only=_is_local_only(normalized_tool),
            runtime_only=_is_runtime_only(normalized_tool),
            requires_explicit_opt_in=_requires_explicit_opt_in(normalized_tool),
        )

    normalized_action = _normalize_action(action)
    read_only_actions = _READ_ONLY_ACTIONS.get(normalized_tool)
    if read_only_actions is not None:
        is_mutating = normalized_action not in read_only_actions
        return ToolActionPolicy(
            mutating=is_mutating,
            high_risk=is_mutating,
            supports_dry_run=_supports_dry_run(normalized_tool, normalized_action),
            local_only=_is_local_only(normalized_tool),
            runtime_only=_is_runtime_only(normalized_tool),
            requires_explicit_opt_in=_requires_explicit_opt_in(normalized_tool) if is_mutating else False,
        )

    # Unknown tools/actions default to mutating to avoid policy bypasses.
    return ToolActionPolicy(
        mutating=True,
        high_risk=True,
        supports_dry_run=False,
        local_only=_is_local_only(normalized_tool),
        runtime_only=_is_runtime_only(normalized_tool),
        requires_explicit_opt_in=True,
    )


def get_batch_policy(commands: list[dict[str, Any]] | None) -> ToolActionPolicy:
    """Get the aggregated policy for a batch of commands."""
    if not commands:
        return ToolActionPolicy(
            mutating=False,
            supports_dry_run=True,
            local_only=False,
            runtime_only=False,
            requires_explicit_opt_in=False,
        )

    is_mutating = False
    high_risk = False
    requires_no_tests = False
    supports_dry_run = True
    local_only = True  # Batch is local-only if all commands are
    runtime_only = False
    requires_explicit_opt_in = False

    for command in commands:
        if not isinstance(command, dict):
            return ToolActionPolicy(
                mutating=True,
                high_risk=True,
                supports_dry_run=False,
                local_only=False,
                runtime_only=False,
                requires_explicit_opt_in=True,
            )

        tool_name = command.get("tool")
        params = command.get("params") or {}
        action = params.get("action") if isinstance(params, dict) else None
        child_policy = get_tool_action_policy(tool_name, action=action)

        is_mutating = is_mutating or child_policy.mutating
        high_risk = high_risk or child_policy.high_risk
        requires_no_tests = requires_no_tests or child_policy.requires_no_tests
        supports_dry_run = supports_dry_run and child_policy.supports_dry_run
        local_only = local_only and child_policy.local_only
        runtime_only = runtime_only or child_policy.runtime_only
        requires_explicit_opt_in = requires_explicit_opt_in or child_policy.requires_explicit_opt_in

    return ToolActionPolicy(
        mutating=is_mutating,
        high_risk=high_risk or is_mutating,
        requires_no_tests=requires_no_tests,
        supports_dry_run=supports_dry_run,
        local_only=local_only,
        runtime_only=runtime_only,
        requires_explicit_opt_in=requires_explicit_opt_in,
    )


def tool_action_is_mutating(
    tool_name: str | None,
    *,
    action: Any = None,
    commands: list[dict[str, Any]] | None = None,
) -> bool:
    return get_tool_action_policy(
        tool_name,
        action=action,
        commands=commands,
    ).mutating


def get_tool_capabilities(tool_name: str | None) -> dict[str, Any]:
    """Get all capability flags for a tool as a dictionary.

    This is a convenience function for external callers that need
    to query tool capabilities programmatically.
    """
    policy = get_tool_action_policy(tool_name)
    return {
        "supports_dry_run": policy.supports_dry_run,
        "local_only": policy.local_only,
        "runtime_only": policy.runtime_only,
        "requires_explicit_opt_in": policy.requires_explicit_opt_in,
    }


async def maybe_run_tool_preflight(
    ctx,
    tool_name: str | None,
    *,
    action: Any = None,
    commands: list[dict[str, Any]] | None = None,
    requires_no_tests: bool | None = None,
) -> MCPResponse | None:
    policy = get_tool_action_policy(
        tool_name,
        action=action,
        commands=commands,
    )
    effective_requires_no_tests = (
        policy.requires_no_tests
        if requires_no_tests is None
        else bool(requires_no_tests)
    )

    if not policy.mutating and not effective_requires_no_tests:
        return None

    return await preflight(
        ctx,
        requires_no_tests=effective_requires_no_tests,
        wait_for_no_compile=policy.wait_for_no_compile,
        refresh_if_dirty=policy.refresh_if_dirty,
    )
