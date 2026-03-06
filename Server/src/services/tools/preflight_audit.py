"""Aggregate read-only audit for compile, scene, and prefab readiness."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools.audit_prefab_integrity import audit_prefab_integrity
from services.tools.audit_scene_integrity import audit_scene_integrity
from services.tools.validate_compile_health import validate_compile_health


def _is_success(payload: dict[str, Any]) -> bool:
    return isinstance(payload, dict) and bool(payload.get("success"))


@mcp_for_unity_tool(
    description=(
        "Run a combined read-only preflight audit: compile health, scene integrity, and prefab integrity. "
        "Use this before broad mutations or test runs."
    ),
    group="testing",
    annotations=ToolAnnotations(
        title="Preflight Audit",
        readOnlyHint=True,
    ),
)
async def preflight_audit(
    ctx: Context,
    scene_scope: Annotated[str, "Scene audit scope: 'active' or 'loaded'."] = "loaded",
    prefab_root_folder: Annotated[str, "Folder to scan for prefab audit."] = "Assets",
    prefab_scan_limit: Annotated[int, "Maximum prefab assets to inspect."] = 100,
    max_issue_samples: Annotated[int, "Maximum issue samples returned per audit section."] = 10,
) -> dict[str, Any]:
    compile_task = validate_compile_health(
        ctx,
        include_warnings=True,
        compiler_only=True,
        max_diagnostics=max(10, max_issue_samples * 5),
    )
    scene_task = audit_scene_integrity(
        ctx,
        scope=scene_scope,
        include_inactive=True,
        max_issues=max_issue_samples,
    )
    prefab_task = audit_prefab_integrity(
        ctx,
        root_folder=prefab_root_folder,
        max_prefabs=prefab_scan_limit,
        max_issues=max_issue_samples,
        include_variants=True,
    )

    compile_result, scene_result, prefab_result = await asyncio.gather(
        compile_task,
        scene_task,
        prefab_task,
    )

    compile_data = (compile_result.get("data") or {}) if _is_success(compile_result) else {}
    scene_data = (scene_result.get("data") or {}) if _is_success(scene_result) else {}
    prefab_data = (prefab_result.get("data") or {}) if _is_success(prefab_result) else {}

    compile_ready = bool(compile_data.get("ready_for_mutation"))
    scene_missing_scripts = ((scene_data.get("summary") or {}).get("totalMissingScripts") or 0)
    dirty_scenes = ((scene_data.get("summary") or {}).get("dirtySceneCount") or 0)
    prefab_missing_scripts = ((prefab_data.get("summary") or {}).get("totalMissingScripts") or 0)
    prefabs_with_issues = ((prefab_data.get("summary") or {}).get("prefabsWithIssues") or 0)

    ready_for_mutation = (
        _is_success(compile_result)
        and _is_success(scene_result)
        and _is_success(prefab_result)
        and compile_ready
        and scene_missing_scripts == 0
        and dirty_scenes == 0
        and prefab_missing_scripts == 0
        and prefabs_with_issues == 0
    )

    blockers = []
    if not compile_ready:
        blockers.append("compile_health")
    if scene_missing_scripts > 0:
        blockers.append("scene_missing_scripts")
    if dirty_scenes > 0:
        blockers.append("dirty_scenes")
    if prefab_missing_scripts > 0:
        blockers.append("prefab_missing_scripts")
    if prefabs_with_issues > 0:
        blockers.append("prefab_issues")
    if not _is_success(scene_result):
        blockers.append("scene_audit_failed")
    if not _is_success(prefab_result):
        blockers.append("prefab_audit_failed")

    return {
        "success": True,
        "message": "Preflight audit completed.",
        "data": {
            "ready_for_mutation": ready_for_mutation,
            "blockers": blockers,
            "compile_health": compile_result,
            "scene_integrity": scene_result,
            "prefab_integrity": prefab_result,
            "recommendation": (
                "Safe to proceed with mutations."
                if ready_for_mutation
                else "Resolve the reported blockers before broad mutations or test runs."
            ),
        },
    }
