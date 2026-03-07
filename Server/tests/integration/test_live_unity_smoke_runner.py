from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest

from transport.legacy.stdio_port_registry import stdio_port_registry


DEFAULT_HTTP_URL = os.environ.get("UNITY_MCP_HTTP_URL", "http://127.0.0.1:8080")
DEFAULT_INSTANCE = os.environ.get("UNITY_MCP_LIVE_INSTANCE")
SMOKE_TINY_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aGxkAAAAASUVORK5CYII="
SMOKE_ANIMATION_CLIP_PATH = "Assets/MCPToolSmokeTests/Live_20260306_003519/Animations/Smoke.anim"
SMOKE_PREFAB_PATH = "Assets/MCPToolSmokeTests/Live_20260306_003519/Prefabs/SmokeCube.prefab"
SMOKE_SCRIPTABLE_OBJECT_PATH = "Assets/MCPToolSmokeTests/Live_20260306_003519/ScriptableObjects/ProbeConfigSmoke.asset"
SMOKE_TARGET_CANDIDATES = (
    "MCP_Live_20260306_003519",
    "MCP_MageFireball_Test",
    "MCP_VfxSmoke",
    "MCP_AnimSmoke_20260306_0225",
    "MCP_LineSmoke_20260306_0206",
    "MCP_TrailSmoke_20260306_0206",
    "MCP_ParticleSmoke_20260306_0238",
)


@dataclass(frozen=True)
class CommandSpec:
    label: str
    tool: str
    params: dict[str, Any]
    timeout: int = 20


@dataclass(frozen=True)
class CommandResult:
    label: str
    tool: str
    success: bool
    message: str
    response: dict[str, Any] | None = None


def _is_enabled() -> bool:
    return bool(os.environ.get("UNITY_MCP_RUN_LIVE_SMOKE"))


def _include_screenshot_smoke() -> bool:
    return bool(os.environ.get("UNITY_MCP_INCLUDE_SCREENSHOT_SMOKE"))


def _include_extended_surface_smoke() -> bool:
    return bool(os.environ.get("UNITY_MCP_INCLUDE_EXTENDED_SURFACE_SMOKE"))


def _include_runtime_ui_smoke() -> bool:
    return bool(os.environ.get("UNITY_MCP_INCLUDE_RUNTIME_UI_SMOKE"))


def _include_stateful_workflow_smoke() -> bool:
    return bool(os.environ.get("UNITY_MCP_INCLUDE_STATEFUL_WORKFLOW_SMOKE"))


def _include_async_test_smoke() -> bool:
    return bool(os.environ.get("UNITY_MCP_INCLUDE_ASYNC_TEST_SMOKE"))


def _extract_tool_result(payload: dict[str, Any]) -> tuple[bool, str]:
    result = payload.get("result") or {}
    if "success" in result:
        success = bool(result.get("success"))
    else:
        success = payload.get("status") == "success"

    message = str(
        result.get("message")
        or result.get("error")
        or result.get("code")
        or payload.get("message")
        or payload.get("error")
        or ""
    )
    return success, message


def _extract_result_data(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result") or {}
    data = result.get("data")
    return data if isinstance(data, dict) else {}


def _extract_result_field(payload: dict[str, Any], field_name: str) -> Any:
    result = payload.get("result") or {}
    if field_name in result:
        return result.get(field_name)
    data = _extract_result_data(payload)
    return data.get(field_name)


def _is_runtime_ui_disabled(result: CommandResult) -> bool:
    return (
        result.tool == "manage_runtime_ui"
        and "Runtime MCP is disabled by default." in result.message
    )


async def _resolve_instance(http_url: str = DEFAULT_HTTP_URL) -> str:
    if DEFAULT_INSTANCE:
        return DEFAULT_INSTANCE

    instances = [
        instance
        for instance in stdio_port_registry.get_instances(force_refresh=True)
        if instance.status in {"running", "reloading"}
    ]
    if len(instances) == 1:
        return str(instances[0].id)

    if not instances:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{http_url}/api/instances", timeout=5)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            payload = {}

        http_instances = payload.get("instances") or []
        if len(http_instances) == 1:
            instance = http_instances[0]
            if isinstance(instance, dict):
                project = str(instance.get("project") or "").strip()
                hash_value = str(instance.get("hash") or "").strip()
                if project and hash_value:
                    return f"{project}@{hash_value}"
                if hash_value:
                    return hash_value
                if project:
                    return project

    if not instances:
        pytest.skip("No Unity instances available from local port discovery or /api/instances.")

    pytest.skip(
        "Multiple Unity instances detected. Set UNITY_MCP_LIVE_INSTANCE to select one explicitly."
    )


async def _invoke_command(
    client: httpx.AsyncClient,
    http_url: str,
    unity_instance: str,
    spec: CommandSpec,
) -> CommandResult:
    try:
        response = await client.post(
            f"{http_url}/api/command",
            json={
                "type": "execute_mcp_tool",
                "params": {"tool_name": spec.tool, "parameters": spec.params},
                "unity_instance": unity_instance,
            },
            timeout=spec.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        success, message = _extract_tool_result(payload)
        return CommandResult(
            label=spec.label,
            tool=spec.tool,
            success=success,
            message=message,
            response=payload,
        )
    except Exception as exc:
        return CommandResult(
            label=spec.label,
            tool=spec.tool,
            success=False,
            message=str(exc),
            response=None,
        )


def _base_specs(target_name: str) -> list[CommandSpec]:
    return [
        CommandSpec("ping", "ping", {}),
        CommandSpec(
            "find smoke target",
            "find_gameobjects",
            {"search_term": target_name, "search_method": "by_name", "page_size": 5},
        ),
        CommandSpec("list windows", "manage_windows", {"action": "list_windows"}),
        CommandSpec("get selection", "manage_selection", {"action": "get_selection"}),
        CommandSpec(
            "focus hierarchy",
            "focus_hierarchy",
            {"target_name": target_name, "expand": True, "select": True},
        ),
        CommandSpec(
            "set selection",
            "manage_selection",
            {"action": "set_selection", "target": target_name, "clear": True},
        ),
        CommandSpec(
            "frame selection",
            "manage_selection",
            {"action": "frame_selection", "frame_selected": True},
        ),
        CommandSpec(
            "project settings",
            "manage_project_settings",
            {"action": "get_settings", "settings_category": "player"},
        ),
        CommandSpec(
            "editor preferences",
            "manage_editor_settings",
            {"action": "get_preferences", "preference_category": "general"},
        ),
        CommandSpec(
            "list registries",
            "manage_registry_config",
            {"action": "list_scoped_registries"},
        ),
        CommandSpec(
            "player settings",
            "manage_player_settings",
            {"action": "get_player_settings", "platform": "Standalone"},
        ),
        CommandSpec(
            "build scenes",
            "manage_build_settings",
            {"action": "get_scenes_in_build"},
        ),
        CommandSpec(
            "define symbols",
            "manage_define_symbols",
            {"action": "get_define_symbols", "platform": "Standalone"},
        ),
        CommandSpec(
            "world transform",
            "manage_transform",
            {"action": "get_world_transform", "target": target_name, "search_method": "by_name"},
        ),
        CommandSpec(
            "spatial nearest",
            "spatial_queries",
            {"action": "get_distance", "source": target_name, "target": target_name, "search_method": "by_name"},
        ),
        CommandSpec(
            "asset search",
            "search_assets_advanced",
            {"name_pattern": "SmokeCube*", "search_path": "Assets/MCPToolSmokeTests", "page_size": 5, "include_metadata": False},
        ),
        CommandSpec(
            "wait compile idle",
            "wait_for_editor_condition",
            {"condition": "compile_idle", "timeout_seconds": 10},
            timeout=15,
        ),
    ]


def _extended_surface_specs() -> list[CommandSpec]:
    return [
        CommandSpec(
            "analyze screenshot compare",
            "analyze_screenshot",
            {
                "action": "compare_screenshots",
                "analysis_type": "custom",
                "screenshot_data": SMOKE_TINY_PNG_BASE64,
                "screenshot_data_b": SMOKE_TINY_PNG_BASE64,
                "query": "Compare these identical smoke images.",
            },
        ),
        CommandSpec(
            "animation clip info",
            "manage_animation",
            {"action": "clip_get_info", "clip_path": SMOKE_ANIMATION_CLIP_PATH},
            timeout=25,
        ),
        CommandSpec(
            "asset index validate",
            "build_asset_index",
            {"action": "validate", "scope": "Assets/MCPToolSmokeTests"},
            timeout=25,
        ),
        CommandSpec(
            "asset index status",
            "asset_index_status",
            {"detailed": True},
        ),
        CommandSpec(
            "diff asset current vs saved",
            "diff_asset",
            {"compare_mode": "current_vs_saved", "asset_path": SMOKE_PREFAB_PATH},
            timeout=25,
        ),
        CommandSpec(
            "diff prefab current vs saved",
            "diff_prefab",
            {"compare_mode": "current_vs_saved", "prefab_path": SMOKE_PREFAB_PATH},
            timeout=25,
        ),
        CommandSpec(
            "find asset dependents",
            "find_asset_references",
            {
                "action": "find_dependents",
                "asset_path": SMOKE_PREFAB_PATH,
                "max_depth": 3,
                "include_indirect": True,
            },
            timeout=25,
        ),
        CommandSpec(
            "analyze asset dependencies",
            "analyze_asset_dependencies",
            {
                "action": "get_dependencies",
                "asset_path": SMOKE_PREFAB_PATH,
                "include_indirect": False,
                "max_depth": 3,
            },
            timeout=25,
        ),
        CommandSpec(
            "find builtin meshes",
            "find_builtin_assets",
            {"action": "list_by_type", "asset_type": "mesh", "max_results": 10, "include_preview": False},
            timeout=25,
        ),
        CommandSpec(
            "search component types",
            "get_component_types",
            {
                "action": "search",
                "component_name": "Renderer",
                "include_builtin": True,
                "include_custom": True,
                "max_results": 10,
                "include_properties": False,
            },
            timeout=25,
        ),
        CommandSpec(
            "get prefab references",
            "get_object_references",
            {
                "action": "get_referenced_by",
                "target": SMOKE_PREFAB_PATH,
                "search_scope": "project",
                "max_results": 10,
                "include_inactive": True,
            },
            timeout=25,
        ),
        CommandSpec(
            "summarize asset",
            "summarize_asset",
            {"asset_path": SMOKE_PREFAB_PATH, "detail_level": "brief", "max_related_assets": 5},
            timeout=25,
        ),
        CommandSpec(
            "list playbooks",
            "list_playbooks",
            {"action": "list"},
        ),
        CommandSpec(
            "list pipelines",
            "list_pipelines",
            {"action": "list"},
        ),
        CommandSpec(
            "list builtin shaders",
            "list_shaders",
            {"action": "list_builtin", "search_pattern": "Standard", "include_properties": False},
            timeout=25,
        ),
        CommandSpec(
            "import queue status",
            "manage_import_pipeline",
            {"action": "get_import_queue_status"},
        ),
        CommandSpec(
            "asset import settings",
            "manage_asset_import_settings",
            {"action": "get_import_settings", "asset_path": SMOKE_ANIMATION_CLIP_PATH},
            timeout=25,
        ),
        CommandSpec(
            "project memory summary",
            "manage_project_memory",
            {"action": "summarize_conventions", "format": "json"},
        ),
        CommandSpec(
            "manage ui list",
            "manage_ui",
            {"action": "list", "filter_type": "uxml", "page_size": 5, "page_number": 1},
        ),
        CommandSpec(
            "input asset list",
            "manage_input_system",
            {"action": "asset_get_all"},
        ),
        CommandSpec(
            "profiler status",
            "manage_profiler",
            {"action": "get_status", "wait_for_completion": True},
        ),
        CommandSpec(
            "scene integrity audit",
            "audit_scene_integrity",
            {"scope": "active", "include_inactive": True, "max_issues": 5},
            timeout=25,
        ),
        CommandSpec(
            "prefab integrity audit",
            "audit_prefab_integrity",
            {
                "root_folder": "Assets/MCPToolSmokeTests",
                "max_prefabs": 20,
                "max_issues": 5,
                "include_variants": True,
            },
            timeout=25,
        ),
        CommandSpec(
            "preflight audit",
            "preflight_audit",
            {
                "scene_scope": "active",
                "prefab_root_folder": "Assets/MCPToolSmokeTests",
                "prefab_scan_limit": 20,
                "max_issue_samples": 5,
            },
            timeout=25,
        ),
        CommandSpec(
            "scriptable object dry run",
            "manage_scriptable_object",
            {
                "action": "modify",
                "target": {"path": SMOKE_SCRIPTABLE_OBJECT_PATH},
                "patches": [],
                "dry_run": True,
            },
            timeout=25,
        ),
        CommandSpec(
            "vfx ping",
            "manage_vfx",
            {"action": "ping"},
        ),
    ]


def _runtime_ui_specs() -> list[CommandSpec]:
    return [
        CommandSpec(
            "runtime ui find elements",
            "manage_runtime_ui",
            {
                "action": "find_elements",
                "ui_system": "auto",
                "max_results": 5,
                "include_invisible": False,
            },
            timeout=25,
        ),
    ]


def _stateful_workflow_specs(suffix: str) -> list[CommandSpec]:
    shader_name = f"LiveSmokeShader_{suffix}"
    shader_folder = "Assets/MCPToolSmokeTests/StatefulSmoke"
    texture_path = f"Assets/MCPToolSmokeTests/StatefulSmoke/LiveSmokeTexture_{suffix}.png"
    pipeline_name = f"live_smoke_pipeline_{suffix}"
    playbook_name = f"live_smoke_playbook_{suffix}"
    rollback_name = f"LiveSmokeRollbackTx_{suffix}"

    return [
        CommandSpec(
            "start trace",
            "start_trace",
            {"tags": ["live-smoke", suffix]},
        ),
        CommandSpec(
            "start fixture capture",
            "start_fixture_capture",
            {"scenario": f"live_smoke_{suffix}", "exclude_tools": ["start_fixture_capture", "stop_fixture_capture"]},
        ),
        CommandSpec(
            "stop fixture capture",
            "stop_fixture_capture",
            {},
        ),
        CommandSpec(
            "start fixture replay",
            "start_fixture_replay",
            {"fixtures": [], "speed_multiplier": 10.0, "deterministic": True},
        ),
        CommandSpec(
            "stop fixture replay",
            "stop_fixture_replay",
            {"session_id": f"missing_{suffix}"},
        ),
        CommandSpec(
            "record pipeline start",
            "record_pipeline",
            {"action": "start", "name": pipeline_name, "description": "Live smoke temporary pipeline capture"},
        ),
        CommandSpec(
            "record pipeline status",
            "record_pipeline",
            {"action": "status"},
        ),
        CommandSpec(
            "record pipeline stop discard",
            "stop_pipeline_recording",
            {"action": "discard", "save": False},
        ),
        CommandSpec(
            "save pipeline",
            "save_pipeline",
            {
                "name": pipeline_name,
                "description": "Live smoke temporary saved pipeline",
                "steps": [{"tool": "ping", "params": {}}],
                "author": "live-smoke",
                "tags": ["live-smoke", suffix],
                "overwrite": True,
            },
        ),
        CommandSpec(
            "replay pipeline dry run",
            "replay_pipeline",
            {"name": pipeline_name, "dry_run": True, "stop_on_error": True},
        ),
        CommandSpec(
            "create playbook from pipeline",
            "create_playbook",
            {
                "action": "from_pipeline",
                "name": playbook_name,
                "pipeline_name": pipeline_name,
                "description": "Live smoke temporary playbook",
                "category": "testing",
                "tags": ["live-smoke", suffix],
                "overwrite": True,
            },
        ),
        CommandSpec(
            "manage shader create",
            "manage_shader",
            {
                "action": "create",
                "name": shader_name,
                "path": shader_folder,
                "contents": "Shader \"Custom/LiveSmokeShader\" { SubShader { Pass { } } }",
            },
            timeout=25,
        ),
        CommandSpec(
            "manage shader read",
            "manage_shader",
            {"action": "read", "name": shader_name, "path": shader_folder},
            timeout=25,
        ),
        CommandSpec(
            "manage texture create",
            "manage_texture",
            {
                "action": "create",
                "path": texture_path,
                "width": 8,
                "height": 8,
                "fill_color": [255, 64, 64, 255],
            },
            timeout=25,
        ),
        CommandSpec(
            "asset import settings temp texture",
            "manage_asset_import_settings",
            {"action": "get_import_settings", "asset_path": texture_path},
            timeout=25,
        ),
        CommandSpec(
            "record profiler session",
            "record_profiler_session",
            {"duration_seconds": 1, "interval_frames": 1, "auto_save": False},
            timeout=35,
        ),
        CommandSpec(
            "apply scene patch dry run",
            "apply_scene_patch",
            {
                "operations": [{"op": "add", "path": f"LiveSmokeSceneProbe_{suffix}", "value": {"name": f"LiveSmokeSceneProbe_{suffix}"}}],
                "dry_run": True,
                "create_checkpoint": False,
            },
            timeout=25,
        ),
        CommandSpec(
            "apply prefab patch dry run",
            "apply_prefab_patch",
            {
                "prefab_path": SMOKE_PREFAB_PATH,
                "operations": [{"op": "add_component", "path": "SmokeCube", "component_type": "BoxCollider", "value": {"type": "BoxCollider"}}],
                "dry_run": True,
                "create_checkpoint": False,
            },
            timeout=25,
        ),
        CommandSpec(
            "rollback begin transaction",
            "manage_transactions",
            {"action": "begin_transaction", "name": rollback_name},
        ),
        CommandSpec(
            "rollback append transaction change",
            "manage_transactions",
            {
                "action": "append_action",
                "transaction_id": f"missing_{suffix}",
                "change_type": "modified",
                "asset_path": SMOKE_PREFAB_PATH,
                "description": "Live smoke rollback transaction",
            },
        ),
        CommandSpec(
            "rollback commit transaction",
            "manage_transactions",
            {"action": "commit_transaction", "transaction_id": f"missing_{suffix}"},
        ),
        CommandSpec(
            "rollback summary",
            "rollback_changes",
            {"action": "get_rollback_summary", "transaction_id": f"missing_{suffix}"},
        ),
        CommandSpec(
            "rollback transaction",
            "rollback_changes",
            {"action": "rollback_transaction", "transaction_id": f"missing_{suffix}"},
        ),
        CommandSpec(
            "manage texture delete",
            "manage_texture",
            {"action": "delete", "path": texture_path},
            timeout=25,
        ),
        CommandSpec(
            "manage shader delete",
            "manage_shader",
            {"action": "delete", "name": shader_name, "path": shader_folder},
            timeout=25,
        ),
        CommandSpec(
            "stop trace",
            "stop_trace",
            {"trace_id": f"missing_{suffix}", "include_entries": True},
        ),
    ]


def _async_test_specs() -> list[CommandSpec]:
    return [
        CommandSpec(
            "run tests",
            "run_tests",
            {"mode": "EditMode", "include_failed_tests": False, "include_details": False},
            timeout=35,
        ),
        CommandSpec(
            "get test job",
            "get_test_job",
            {"job_id": "missing-live-smoke-job", "wait_timeout": 1, "include_failed_tests": False, "include_details": False},
            timeout=15,
        ),
    ]


def _stateful_artifact_paths(suffix: str) -> list[Path]:
    pipeline_name = f"live_smoke_pipeline_{suffix}"
    playbook_name = f"live_smoke_playbook_{suffix}"
    return [
        Path.cwd() / "Pipelines" / f"{pipeline_name}.json",
        Path(__file__).resolve().parents[2] / "src" / "services" / "tools" / "playbooks" / f"{playbook_name}.json",
    ]


def _require_optional_data_field(result: CommandResult, field_name: str, default_value: str) -> str:
    payload = result.response or {}
    value = _extract_result_field(payload, field_name)
    return str(value) if value else default_value


async def _run_stateful_workflow_smoke(
    client: httpx.AsyncClient,
    http_url: str,
    unity_instance: str,
) -> list[CommandResult]:
    suffix = uuid4().hex[:8]
    specs = _stateful_workflow_specs(suffix)
    results: list[CommandResult] = []
    rollback_transaction_id = f"missing_{suffix}"
    trace_id = f"missing_{suffix}"
    replay_session_id = f"missing_{suffix}"

    try:
        for spec in specs:
            params = dict(spec.params)

            if spec.label == "stop fixture replay":
                params["session_id"] = replay_session_id
            elif spec.label == "rollback append transaction change":
                params["transaction_id"] = rollback_transaction_id
            elif spec.label == "rollback commit transaction":
                params["transaction_id"] = rollback_transaction_id
            elif spec.label == "rollback summary":
                params["transaction_id"] = rollback_transaction_id
            elif spec.label == "rollback transaction":
                params["transaction_id"] = rollback_transaction_id
            elif spec.label == "stop trace":
                params["trace_id"] = trace_id

            result = await _invoke_command(
                client,
                http_url,
                unity_instance,
                CommandSpec(spec.label, spec.tool, params, timeout=spec.timeout),
            )
            results.append(result)

            if spec.label == "start trace":
                trace_id = _require_optional_data_field(result, "trace_id", trace_id)
            elif spec.label == "start fixture replay":
                replay_session_id = _require_optional_data_field(result, "session_id", replay_session_id)
            elif spec.label == "rollback begin transaction":
                rollback_transaction_id = _require_optional_data_field(result, "transaction_id", rollback_transaction_id)
    finally:
        for artifact_path in _stateful_artifact_paths(suffix):
            try:
                artifact_path.unlink(missing_ok=True)
            except OSError:
                pass

    return results


async def _run_async_test_smoke(
    client: httpx.AsyncClient,
    http_url: str,
    unity_instance: str,
) -> list[CommandResult]:
    results: list[CommandResult] = []
    job_id = "missing-live-smoke-job"

    for spec in _async_test_specs():
        params = dict(spec.params)
        if spec.label == "get test job":
            params["job_id"] = job_id

        result = await _invoke_command(
            client,
            http_url,
            unity_instance,
            CommandSpec(spec.label, spec.tool, params, timeout=spec.timeout),
        )
        results.append(result)

        if spec.label == "run tests":
            job_id = _require_optional_data_field(result, "job_id", job_id)

    return results


def _require_data_field(result: CommandResult, field_name: str) -> str:
    payload = result.response or {}
    value = _extract_result_field(payload, field_name)
    assert value, f"{result.label} did not return data.{field_name}: {payload}"
    return str(value)


def _has_find_results(result: CommandResult) -> bool:
    payload = result.response or {}
    data = ((payload.get("result") or {}).get("data") or {})
    instance_ids = data.get("instanceIDs") or []
    total_count = data.get("totalCount")
    if isinstance(total_count, int) and total_count > 0:
        return True
    return bool(instance_ids)


def _extract_hierarchy_item_names(result: CommandResult) -> list[str]:
    payload = result.response or {}
    data = ((payload.get("result") or {}).get("data") or {})
    items = data.get("items") or []
    names: list[str] = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
    return names


async def _resolve_smoke_target_name(
    client: httpx.AsyncClient,
    http_url: str,
    unity_instance: str,
) -> str:
    for candidate in SMOKE_TARGET_CANDIDATES:
        result = await _invoke_command(
            client,
            http_url,
            unity_instance,
            CommandSpec(
                label=f"probe {candidate}",
                tool="find_gameobjects",
                params={"search_term": candidate, "search_method": "by_name", "page_size": 1},
            ),
        )
        if result.success and _has_find_results(result):
            return candidate

    hierarchy = await _invoke_command(
        client,
        http_url,
        unity_instance,
        CommandSpec(
            label="probe active hierarchy roots",
            tool="manage_scene",
            params={"action": "get_hierarchy", "page_size": 10, "include_transform": False},
            timeout=25,
        ),
    )
    if hierarchy.success:
        root_names = _extract_hierarchy_item_names(hierarchy)
        for root_name in root_names:
            if root_name.startswith("MCP_"):
                return root_name
        if root_names:
            return root_names[0]

    pytest.skip(
        "No known smoke target was found in the active Unity scene. "
        "Expected one of the documented MCP smoke objects to exist."
    )


async def run_live_smoke_matrix(http_url: str = DEFAULT_HTTP_URL) -> list[CommandResult]:
    async with httpx.AsyncClient() as client:
        unity_instance = await _resolve_instance(http_url)
        target_name = await _resolve_smoke_target_name(client, http_url, unity_instance)
        results: list[CommandResult] = []

        for spec in _base_specs(target_name):
            results.append(await _invoke_command(client, http_url, unity_instance, spec))

        subscribe = await _invoke_command(
            client,
            http_url,
            unity_instance,
            CommandSpec(
                "subscribe events",
                "subscribe_editor_events",
                {"event_types": ["console_updates"], "expiration_minutes": 5, "buffer_events": True},
            ),
        )
        results.append(subscribe)
        subscription_id = _require_data_field(subscribe, "subscription_id")

        results.append(
            await _invoke_command(
                client,
                http_url,
                unity_instance,
                CommandSpec(
                    "unsubscribe events",
                    "unsubscribe_editor_events",
                    {"subscription_id": subscription_id, "flush_pending_events": True},
                ),
            )
        )

        begin_transaction = await _invoke_command(
            client,
            http_url,
            unity_instance,
            CommandSpec(
                "begin transaction",
                "manage_transactions",
                {"action": "begin_transaction", "name": "LiveSmokeValidationTx"},
            ),
        )
        results.append(begin_transaction)
        transaction_id = _require_data_field(begin_transaction, "transaction_id")

        transaction_specs = [
        CommandSpec(
            "append transaction change",
            "manage_transactions",
            {
                "action": "append_action",
                "transaction_id": transaction_id,
                "change_type": "modified",
                "asset_path": "Assets/MCPToolSmokeTests/Scenes/ToolSmoke_20260305_233638.unity",
                "description": "Live smoke transaction",
            },
        ),
        CommandSpec(
            "preview changes",
            "preview_changes",
            {"transaction_id": transaction_id, "include_analysis": True, "detect_conflicts": True},
        ),
        CommandSpec(
            "commit transaction",
            "manage_transactions",
            {"action": "commit_transaction", "transaction_id": transaction_id},
        ),
        CommandSpec(
            "diff active scene",
            "diff_scene",
            {"compare_mode": "active_vs_saved"},
            timeout=25,
        ),
        CommandSpec(
            "navigate get context",
            "navigate_editor",
            {"navigation_type": "get_context"},
        ),
        CommandSpec(
            "frame scene target",
            "frame_scene_target",
            {"target_name": target_name, "duration": 0.1},
        ),
        CommandSpec(
            "open inspector asset",
            "open_inspector_target",
            {"asset_path": "Assets/MCPToolSmokeTests/Live_20260306_003519/Prefabs/SmokeCube.prefab"},
        ),
        CommandSpec(
            "playbook dry run",
            "run_playbook",
            {"playbook_id": "scene_lighting_setup", "dry_run": True},
        ),
        CommandSpec(
            "benchmark smoke",
            "run_benchmark",
            {
                "benchmark_name": "validation_smoke_project_settings",
                "iterations": 2,
                "tool_sequence": [
                    {
                        "tool": "manage_project_settings",
                        "params": {"action": "get_settings", "settingsCategory": "player"},
                    }
                ],
            },
        ),
    ]

        if _include_screenshot_smoke():
            transaction_specs.extend(
                [
                    CommandSpec(
                        "capture scene screenshot",
                        "manage_screenshot",
                        {"action": "capture_scene_view", "width": 960, "height": 540, "format": "base64"},
                    ),
                    CommandSpec(
                        "capture editor screenshot",
                        "manage_screenshot",
                        {"action": "capture_editor_window", "format": "base64"},
                    ),
                    CommandSpec(
                        "read last screenshot",
                        "manage_screenshot",
                        {"action": "get_last_screenshot", "format": "base64"},
                    ),
                ]
            )

        if _include_extended_surface_smoke():
            transaction_specs.extend(_extended_surface_specs())

        if _include_runtime_ui_smoke():
            transaction_specs.extend(_runtime_ui_specs())

        for spec in transaction_specs:
            results.append(await _invoke_command(client, http_url, unity_instance, spec))

        if _include_stateful_workflow_smoke():
            results.extend(await _run_stateful_workflow_smoke(client, http_url, unity_instance))

        if _include_async_test_smoke():
            results.extend(await _run_async_test_smoke(client, http_url, unity_instance))

        return results


def test_live_smoke_matrix_spec_count():
    assert len(_base_specs("MCP_MageFireball_Test")) == 17


@pytest.mark.integration
@pytest.mark.skipif(
    not _is_enabled(),
    reason="Set UNITY_MCP_RUN_LIVE_SMOKE=1 to run against a live Unity instance.",
)
@pytest.mark.asyncio
async def test_live_unity_http_smoke_matrix_opt_in():
    results = await run_live_smoke_matrix()
    failures = [
        result
        for result in results
        if not result.success and not _is_runtime_ui_disabled(result)
    ]

    expected = 29
    if _include_screenshot_smoke():
        expected += 3
    if _include_extended_surface_smoke():
        expected += len(_extended_surface_specs())
    if _include_runtime_ui_smoke():
        expected += len(_runtime_ui_specs())
    if _include_stateful_workflow_smoke():
        expected += len(_stateful_workflow_specs("count"))
    if _include_async_test_smoke():
        expected += len(_async_test_specs())

    assert len(results) == expected
    assert not failures, "\n".join(
        f"{result.label} ({result.tool}): {result.message or 'failed without message'}"
        for result in failures
    )