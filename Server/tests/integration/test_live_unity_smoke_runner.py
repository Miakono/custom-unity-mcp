from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx
import pytest


DEFAULT_HTTP_URL = os.environ.get("UNITY_MCP_HTTP_URL", "http://127.0.0.1:8080")
DEFAULT_INSTANCE = os.environ.get("UNITY_MCP_LIVE_INSTANCE")
SMOKE_TARGET_CANDIDATES = (
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


def _extract_tool_result(payload: dict[str, Any]) -> tuple[bool, str]:
    result = payload.get("result") or {}
    if "success" in result:
        success = bool(result.get("success"))
    else:
        success = payload.get("status") == "success"

    message = str(result.get("message") or payload.get("message") or "")
    return success, message


async def _resolve_instance(client: httpx.AsyncClient, http_url: str) -> str:
    if DEFAULT_INSTANCE:
        return DEFAULT_INSTANCE

    response = await client.get(f"{http_url}/api/instances", timeout=10)
    response.raise_for_status()
    payload = response.json()
    instances = payload.get("instances") or []
    if len(instances) == 1:
        instance = instances[0]
        if isinstance(instance, dict):
            return str(instance.get("id") or instance.get("name") or "")
        return str(instance)

    if not instances:
        pytest.skip("No Unity instances available from /api/instances.")

    pytest.skip(
        "Multiple Unity instances detected. Set UNITY_MCP_LIVE_INSTANCE to select one explicitly."
    )


async def _invoke_command(
    client: httpx.AsyncClient,
    http_url: str,
    unity_instance: str,
    spec: CommandSpec,
) -> CommandResult:
    payload = {
        "type": spec.tool,
        "params": spec.params,
        "unity_instance": unity_instance,
    }

    try:
        response = await client.post(
            f"{http_url}/api/command",
            json=payload,
            timeout=spec.timeout,
        )
        response.raise_for_status()
        body = response.json()
        success, message = _extract_tool_result(body)
        return CommandResult(
            label=spec.label,
            tool=spec.tool,
            success=success,
            message=message,
            response=body,
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
            {"action": "nearest_object", "source": target_name, "searchMethod": "by_name", "maxResults": 3},
        ),
        CommandSpec(
            "asset search",
            "search_assets_advanced",
            {"namePattern": "SmokeCube*", "searchPath": "Assets/MCPToolSmokeTests", "pageSize": 5, "includeMetadata": False},
        ),
        CommandSpec(
            "wait compile idle",
            "wait_for_editor_condition",
            {"condition": "compile_idle", "timeout_seconds": 10},
            timeout=15,
        ),
    ]


def _require_data_field(result: CommandResult, field_name: str) -> str:
    payload = result.response or {}
    data = ((payload.get("result") or {}).get("data") or {})
    value = data.get(field_name)
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

    pytest.skip(
        "No known smoke target was found in the active Unity scene. "
        "Expected one of the documented MCP smoke objects to exist."
    )


async def run_live_smoke_matrix(http_url: str = DEFAULT_HTTP_URL) -> list[CommandResult]:
    async with httpx.AsyncClient() as client:
        unity_instance = await _resolve_instance(client, http_url)
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

        for spec in transaction_specs:
            results.append(await _invoke_command(client, http_url, unity_instance, spec))

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
    failures = [result for result in results if not result.success]

    assert len(results) == 29
    assert not failures, "\n".join(
        f"{result.label} ({result.tool}): {result.message or 'failed without message'}"
        for result in failures
    )