from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models import MCPResponse
from services.tools.preflight import preflight


@dataclass(frozen=True)
class ToolActionPolicy:
    mutating: bool
    high_risk: bool = False
    wait_for_no_compile: bool = True
    refresh_if_dirty: bool = True
    requires_no_tests: bool = False


_READ_ONLY_ACTIONS: dict[str, set[str]] = {
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


def get_tool_action_policy(
    tool_name: str | None,
    *,
    action: Any = None,
    commands: list[dict[str, Any]] | None = None,
) -> ToolActionPolicy:
    normalized_tool = (tool_name or "").strip()
    if not normalized_tool:
        return ToolActionPolicy(mutating=True, high_risk=True)

    if normalized_tool == "batch_execute":
        return get_batch_policy(commands)

    if normalized_tool in _ALWAYS_READ_ONLY_TOOLS:
        return ToolActionPolicy(mutating=False)

    if normalized_tool in _ALWAYS_MUTATING_TOOLS:
        return ToolActionPolicy(mutating=True, high_risk=True)

    normalized_action = _normalize_action(action)
    read_only_actions = _READ_ONLY_ACTIONS.get(normalized_tool)
    if read_only_actions is not None:
        is_mutating = normalized_action not in read_only_actions
        return ToolActionPolicy(
            mutating=is_mutating,
            high_risk=is_mutating,
        )

    # Unknown tools/actions default to mutating to avoid policy bypasses.
    return ToolActionPolicy(mutating=True, high_risk=True)


def get_batch_policy(commands: list[dict[str, Any]] | None) -> ToolActionPolicy:
    if not commands:
        return ToolActionPolicy(mutating=False)

    is_mutating = False
    high_risk = False
    requires_no_tests = False

    for command in commands:
        if not isinstance(command, dict):
            return ToolActionPolicy(mutating=True, high_risk=True)

        tool_name = command.get("tool")
        params = command.get("params") or {}
        action = params.get("action") if isinstance(params, dict) else None
        child_policy = get_tool_action_policy(tool_name, action=action)

        is_mutating = is_mutating or child_policy.mutating
        high_risk = high_risk or child_policy.high_risk
        requires_no_tests = requires_no_tests or child_policy.requires_no_tests

    return ToolActionPolicy(
        mutating=is_mutating,
        high_risk=high_risk or is_mutating,
        requires_no_tests=requires_no_tests,
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
