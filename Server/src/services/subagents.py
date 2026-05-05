"""Utilities for building registry-backed subagent artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.registry import (
    DEFAULT_ENABLED_GROUPS,
    TOOL_GROUPS,
    ensure_tool_registry_populated,
    get_group_tool_names,
    get_registered_tools,
)
from services.unity_tool_source import is_publishable_registry_tool, summarize_registry_compatibility


_GROUP_SPECIALISTS: dict[str, dict[str, Any]] = {
    "core": {
        "name": "Unity Core Builder",
        "description": "Owns everyday Unity editing work: scenes, gameobjects, prefabs, assets, scripts, and editor state.",
        "when_to_use": [
            "Scene composition, hierarchy edits, and asset inspection.",
            "Script reads or targeted script mutations.",
            "Prefab creation, updates, and validation.",
        ],
        "workflow": [
            "Confirm the active Unity instance before mutating.",
            "Inspect current state first, then batch related changes when possible.",
            "Hand off to testing after meaningful mutations or compile-sensitive edits.",
        ],
        "handoff_targets": ["unity-testing-specialist", "unity-ui-specialist"],
    },
    "vfx": {
        "name": "Unity VFX Specialist",
        "description": "Handles shaders, materials, textures, and VFX authoring flows.",
        "when_to_use": [
            "Shader and material iteration.",
            "Texture inspection or mutation workflows.",
            "VFX Graph or look-dev tasks.",
        ],
        "workflow": [
            "Activate the vfx group before work starts.",
            "Capture or inspect current asset state before broad mutations.",
            "Escalate back to core or testing when changes affect shared assets or scene behavior.",
        ],
        "handoff_targets": ["unity-core-builder", "unity-testing-specialist"],
    },
    "animation": {
        "name": "Unity Animation Specialist",
        "description": "Focuses on animator, clips, and animation editing tasks.",
        "when_to_use": [
            "Animator or clip authoring.",
            "Animation controller inspection or repair.",
            "Playback-oriented content adjustments.",
        ],
        "workflow": [
            "Activate the animation group for the current session.",
            "Prefer small, verifiable changes to animation assets.",
            "Route follow-up validation to testing when clips or controllers were mutated.",
        ],
        "handoff_targets": ["unity-testing-specialist", "unity-core-builder"],
    },
    "ui": {
        "name": "Unity UI Specialist",
        "description": "Owns UI Toolkit and interface authoring tasks.",
        "when_to_use": [
            "UXML, USS, and UIDocument changes.",
            "UI hierarchy or styling work.",
            "Interface assembly and review loops.",
        ],
        "workflow": [
            "Activate the ui group before interacting with UI tools.",
            "Keep UI changes scoped and inspect generated output after edits.",
            "Hand off to testing for visual verification or regression checks.",
        ],
        "handoff_targets": ["unity-testing-specialist", "unity-core-builder"],
    },
    "scripting_ext": {
        "name": "Unity Data Specialist",
        "description": "Handles ScriptableObject and data-oriented authoring flows.",
        "when_to_use": [
            "ScriptableObject reads and mutations.",
            "Data definition setup and maintenance.",
            "Project data validation tasks.",
        ],
        "workflow": [
            "Activate scripting_ext before using ScriptableObject tools.",
            "Inspect target data before write operations.",
            "Escalate to testing if the data impacts runtime or build behavior.",
        ],
        "handoff_targets": ["unity-testing-specialist", "unity-core-builder"],
    },
    "testing": {
        "name": "Unity Testing Specialist",
        "description": "Runs validation loops, test jobs, and post-change verification.",
        "when_to_use": [
            "Run tests after code or asset mutations.",
            "Collect diagnostics after failures.",
            "Verify compile, editor, or batch outcomes.",
        ],
        "workflow": [
            "Activate the testing group only when validation is needed.",
            "Use focused checks first, then broader suites if failures persist.",
            "Return findings to the originating specialist with exact failing commands or artifacts.",
        ],
        "handoff_targets": ["unity-core-builder", "unity-ui-specialist", "unity-vfx-specialist"],
    },
    "profiling": {
        "name": "Unity Profiling Specialist",
        "description": "Measures runtime performance: frame time, GC pressure, draw calls, memory, and tool-call latency. Diagnoses bottlenecks and tracks regressions across changes.",
        "when_to_use": [
            "User asks 'why is X slow', 'what's eating frame budget', or 'profile this scene'.",
            "Validating a perf-related change: did the optimization actually improve frame time / draw calls / memory?",
            "Investigating GC spikes, frame stutters, texture/mesh memory growth, or draw call explosions.",
            "Establishing a baseline before refactoring a hot system (enemy spawner, AI, particle systems).",
        ],
        "workflow": [
            "Confirm context with manage_profiler get_status (isPlaying, supported categories). Most numbers are only meaningful in Play mode.",
            "For a quick read, call manage_profiler get_snapshot. The first call after a domain reload returns zeros for time-based counters because Unity needs one frame to elapse — re-call after ~1s.",
            "For sustained measurement (recommended), use record_profiler_session(duration_seconds=10-30). Returns aggregated min/max/avg frame time, FPS, draw calls, and memory.",
            "For comparing changes, use run_benchmark with a tool_sequence to capture a baseline, make the change, run again, then compare_benchmarks(baseline_run_id, comparison_run_id).",
            "Interpret: frame time >33ms = sub-30 FPS, GC allocations per frame >0 = pooling opportunity, texture memory >1GB on desktop = compression review, draw calls >2000 = batching review.",
            "Hand off the diagnosis to the right specialist: core for script changes, vfx for shader/material/texture issues, scripting_ext for ScriptableObject data, animation for animator overhead.",
        ],
        "handoff_targets": ["unity-core-builder", "unity-vfx-specialist", "unity-testing-specialist"],
    },
    "asset_intelligence": {
        "name": "Unity Asset Intelligence Specialist",
        "description": "Searches, indexes, and analyzes assets across the project. Resolves dependency graphs and produces summaries before destructive operations.",
        "when_to_use": [
            "Locating assets by name, type, label, or content across a large project.",
            "Mapping dependencies before deleting, moving, or refactoring an asset.",
            "Producing a quick semantic summary of an unfamiliar prefab, material, or ScriptableObject.",
            "Building or refreshing the asset index after a large import.",
        ],
        "workflow": [
            "Check asset_index_status before searching; rebuild via build_asset_index if stale or after a large import.",
            "Use search_assets_advanced with type/folder/label filters first; broaden only when needed to keep responses small.",
            "For impact analysis, run find_asset_references and analyze_asset_dependencies before any deletion or path change.",
            "Hand off to core for the actual mutation, with the dependency report attached so the change is informed.",
        ],
        "handoff_targets": ["unity-core-builder", "unity-vfx-specialist", "unity-testing-specialist"],
    },
    "dev_tools": {
        "name": "Unity Dev Tools Specialist",
        "description": "Internal development and debugging tooling: benchmarks, fixtures, and request tracing. Used to instrument the MCP itself, not for game-side work.",
        "when_to_use": [
            "Measuring MCP tool latency or comparing two implementations (run_benchmark + compare_benchmarks).",
            "Recording or replaying a fixture for repeatable test setups.",
            "Tracing a session of MCP requests for debugging tool routing or error patterns.",
            "Validating that a perf change to the MCP itself actually improved something.",
        ],
        "workflow": [
            "For latency: run_benchmark with a tool_sequence and iterations >=5 (warmup_iterations >=1 to discount cold-start).",
            "For a single regression check: capture two runs around the change, then compare_benchmarks(baseline_run_id, comparison_run_id).",
            "For tracing: start_trace -> exercise tools -> stop_trace, then get_trace_summary for a digest.",
            "Hand findings back to the originating specialist; dev_tools rarely owns mutations.",
        ],
        "handoff_targets": ["unity-profiling-specialist", "unity-core-builder", "unity-testing-specialist"],
    },
    "diff_patch": {
        "name": "Unity Diff/Patch Specialist",
        "description": "Diff and patch operations on scenes, prefabs, and assets. Used for targeted, reviewable mutations and for inspecting what a previous change actually did.",
        "when_to_use": [
            "Applying a precise, structured edit to a scene or prefab without rewriting the whole file.",
            "Inspecting differences between two scenes/prefabs/assets (e.g. before/after a refactor).",
            "Auditing what an automated change touched.",
            "Composing a multi-step asset change as discrete patches to review individually.",
        ],
        "workflow": [
            "Use diff_scene / diff_prefab / diff_asset first to see the exact delta you intend to apply.",
            "Construct the patch payload from the diff output; keep changes minimal.",
            "Apply with apply_scene_patch / apply_prefab_patch and immediately re-diff to confirm the intended state.",
            "Hand off to testing for verification when the patch touches gameplay-affecting components.",
        ],
        "handoff_targets": ["unity-core-builder", "unity-testing-specialist"],
    },
    "events": {
        "name": "Unity Events Specialist",
        "description": "Editor event subscription and condition-waiting. Used to coordinate multi-step workflows that depend on editor state changes (compile finished, asset imported, play mode toggled).",
        "when_to_use": [
            "Waiting for an asynchronous editor state to settle (compile, import, domain reload) before continuing.",
            "Reacting to editor lifecycle events from a longer-running automation.",
            "Building deterministic wait points into a multi-tool workflow rather than blind sleeps.",
        ],
        "workflow": [
            "Prefer wait_for_editor_condition with an explicit condition over polling editor_state in a loop.",
            "Use subscribe_editor_events for fan-out scenarios; remember to unsubscribe_editor_events to avoid leaks across reloads.",
            "Combine with poll_subscription_events from core when the workflow needs to drain queued events.",
        ],
        "handoff_targets": ["unity-core-builder", "unity-testing-specialist"],
    },
    "input": {
        "name": "Unity Input Specialist",
        "description": "Unity Input System authoring and runtime simulation: action maps, actions, bindings, control schemes.",
        "when_to_use": [
            "Adding, modifying, or deleting actions/maps/bindings in a .inputactions asset.",
            "Auditing a project's input bindings for missing, duplicate, or broken entries.",
            "Simulating input at runtime for tests and demo scripting.",
        ],
        "workflow": [
            "Read the current state with manage_input_system get_* actions before mutating; .inputactions YAML is fragile.",
            "Make one binding/action change at a time; verify with a follow-up read.",
            "Hand off to testing for an editor recompile pass after non-trivial changes — the InputSystem regenerates wrappers.",
        ],
        "handoff_targets": ["unity-core-builder", "unity-testing-specialist"],
    },
    "navigation": {
        "name": "Unity Navigation Specialist",
        "description": "Editor navigation and focus: hierarchy reveal, scene framing, asset reveal, inspector targeting. Used to set up the visual context for a subsequent action.",
        "when_to_use": [
            "Selecting and framing a target before a screenshot, edit, or visual review.",
            "Revealing an asset in the Project window so the user (or visual_qa) can see it.",
            "Pinpointing an inspector target for a follow-up component edit.",
        ],
        "workflow": [
            "Use focus_hierarchy / reveal_asset to surface the target, then frame_scene_target if a SceneView angle matters.",
            "Pair with manage_screenshot from visual_qa for a 'show me what you mean' review loop.",
            "Don't mutate from this group — hand off to core or vfx for the actual edit.",
        ],
        "handoff_targets": ["unity-core-builder", "unity-visual-qa-specialist", "unity-vfx-specialist"],
    },
    "pipeline": {
        "name": "Unity Pipeline Specialist",
        "description": "Pipeline recording, replay, and playbook automation. Used to capture a sequence of MCP tool calls once and re-run it later (regression suites, scripted setups, demo flows).",
        "when_to_use": [
            "Recording a multi-step setup that you'll need to repeat (test scene staging, demo prep).",
            "Replaying a captured pipeline against a fresh project to reproduce a state.",
            "Authoring a playbook for a recurring workflow (build prep, screenshot suite).",
            "Investigating a previous pipeline run's behavior via list_pipelines / list_playbooks.",
        ],
        "workflow": [
            "Start with record_pipeline before the workflow; stop_pipeline_recording when complete.",
            "Save with save_pipeline; later replay with replay_pipeline against the target project.",
            "For named, parameterized flows, prefer create_playbook + run_playbook over raw replay.",
            "Hand off to dev_tools for benchmarking a playbook's runtime cost.",
        ],
        "handoff_targets": ["unity-dev-tools-specialist", "unity-testing-specialist"],
    },
    "pipeline_control": {
        "name": "Unity Pipeline Control Specialist",
        "description": "Build settings, player settings, define symbols, and import pipeline control. High-risk: changes here affect what the project compiles, builds, and ships.",
        "when_to_use": [
            "Modifying build settings, scene list, or platform target.",
            "Adding/removing scripting define symbols (e.g. UNITY_VFX_GRAPH, MCP_ENABLE_ADDRESSABLES_TOOLS).",
            "Adjusting player settings (icons, splash, scripting backend, API compatibility).",
            "Tuning the asset import pipeline (importers, default platform settings).",
        ],
        "workflow": [
            "Read current values before changing — these settings affect the entire project's compile and build output.",
            "Change one axis at a time; many settings trigger a domain reload.",
            "After a define symbol change, hand off to testing for a compile pass — new branches activate immediately.",
            "Document the why in the commit; settings changes are easy to revert but hard to explain after the fact.",
        ],
        "handoff_targets": ["unity-testing-specialist", "unity-core-builder"],
    },
    "project_config": {
        "name": "Unity Project Config Specialist",
        "description": "Project-wide configuration and discovery: settings, registries, dependencies, built-in assets, shaders, project memory. Mostly read-only inspection plus a few targeted writes.",
        "when_to_use": [
            "Inspecting project settings, editor settings, or registry config.",
            "Discovering built-in assets, shaders, or component types available to the project.",
            "Resolving 'what does this asset depend on' or 'who references this object' questions.",
            "Reading or updating the persistent project memory store.",
        ],
        "workflow": [
            "Read first: list_shaders, find_builtin_assets, get_component_types, get_object_references all answer discovery questions cheaply.",
            "For deeper asset relationships, hand off to asset_intelligence for indexed search.",
            "When mutating settings (manage_project_settings / manage_editor_settings), match the format on read; many settings are nested arrays.",
            "Use manage_project_memory for persistent context that should outlive a single session.",
        ],
        "handoff_targets": ["unity-asset-intelligence-specialist", "unity-core-builder"],
    },
    "spatial": {
        "name": "Unity Spatial Specialist",
        "description": "Transform operations and spatial queries: positions, rotations, scales, parent-child relationships, raycast/overlap queries against the scene.",
        "when_to_use": [
            "Bulk transform mutations (positioning, rotating, scaling many objects).",
            "Spatial queries (what's within radius, what's on this raycast, what overlaps this volume).",
            "Setting up complex hierarchies or spatial layouts programmatically.",
            "Aligning, snapping, or distributing objects.",
        ],
        "workflow": [
            "Read the current transform tree (manage_scene get_hierarchy from core, paged) before bulk edits.",
            "Use spatial_queries for scene-aware logic instead of guessing positions.",
            "Apply transform changes via manage_transform; batch related changes when possible to limit undo entries.",
            "Hand off to testing if the change affects physics, navigation, or rendering bounds.",
        ],
        "handoff_targets": ["unity-core-builder", "unity-testing-specialist"],
    },
    "transactions": {
        "name": "Unity Transactions Specialist",
        "description": "Transaction management with rollback and preview: stage a multi-step change, preview it, commit or rollback. Used for high-risk multi-asset workflows where atomicity matters.",
        "when_to_use": [
            "Multi-step workflows touching several assets where partial application would leave the project broken.",
            "Risky refactors where preview-before-apply is required.",
            "Operations that need a clean rollback path if any step fails.",
        ],
        "workflow": [
            "Open a transaction with manage_transactions begin; stage all mutations inside it.",
            "Always call preview_changes before commit to confirm the diff matches intent.",
            "On any failure, rollback_changes; don't leave half-applied state.",
            "Hand off to testing after commit to verify the final state.",
        ],
        "handoff_targets": ["unity-testing-specialist", "unity-diff-patch-specialist"],
    },
    "visual_qa": {
        "name": "Unity Visual QA Specialist",
        "description": "Visual verification: screenshot capture and AI-powered image analysis. Used to confirm UI changes, scene edits, and rendering changes look right.",
        "when_to_use": [
            "Verifying a UI/scene edit visually before declaring it done.",
            "Comparing 'before' and 'after' screenshots to detect regressions.",
            "Asking 'does this screen look right' or 'is this asset displaying correctly' questions.",
            "Capturing reference imagery for documentation or bug reports.",
        ],
        "workflow": [
            "Use navigation specialist to frame/select the target first; visual_qa captures, it doesn't position.",
            "manage_screenshot for capture (game view, scene view, editor window, or specific object).",
            "analyze_screenshot for AI assessment, or compare_screenshots for deterministic pixel diff against a baseline.",
            "Hand off findings to vfx (rendering issues), ui (layout issues), or core (script-driven visuals).",
        ],
        "handoff_targets": ["unity-ui-specialist", "unity-vfx-specialist", "unity-core-builder"],
    },
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_subagent_output_dir() -> Path:
    """Default path for exported subagent artifacts."""
    return _repo_root() / "Generated" / "Subagents"


def _server_meta_tools() -> list[str]:
    return sorted(
        tool["name"]
        for tool in get_registered_tools()
        if tool.get("group") is None and is_publishable_registry_tool(tool)
    )


def _specialist_id(group: str) -> str:
    return f"unity-{group.replace('_', '-')}-specialist"


def _build_orchestrator(server_tools: list[str], group_tools: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "id": "unity-orchestrator",
        "name": "Unity Orchestrator",
        "kind": "orchestrator",
        "description": (
            "Routes work to the right Unity specialist, keeps tool groups lean, "
            "and coordinates verification after mutations."
        ),
        "manages_groups": sorted(TOOL_GROUPS.keys()),
        "shared_meta_tools": server_tools,
        "instructions": [
            "Start with core unless the task is clearly UI, VFX, animation, data, profiling, or testing focused.",
            "Use manage_tools to activate only the group needed for the current phase of work.",
            "Set the active Unity instance before specialist handoff when multiple editors are connected.",
            "After meaningful mutations, hand off to the testing specialist for verification.",
            "For performance questions ('why is X slow', 'profile this', 'check frame time / GC / draw calls') hand off to the profiling specialist before guessing.",
        ],
        "handoff_map": {
            group: {
                "specialist_id": _specialist_id(group),
                "activate": {
                    "tool": "manage_tools",
                    "params": {"action": "activate", "group": group},
                },
                "tool_count": len(group_tools.get(group, [])),
            }
            for group in sorted(TOOL_GROUPS.keys())
        },
    }


def _build_specialist(group: str, tools: list[str], server_tools: list[str]) -> dict[str, Any]:
    template = _GROUP_SPECIALISTS.get(group, {})
    return {
        "id": _specialist_id(group),
        "name": template.get("name", f"Unity {group.title()} Specialist"),
        "kind": "specialist",
        "group": group,
        "description": template.get("description", TOOL_GROUPS[group]),
        "default_enabled": group in DEFAULT_ENABLED_GROUPS,
        "activation": {
            "tool": "manage_tools",
            "params": {"action": "activate", "group": group},
        },
        "tool_group_description": TOOL_GROUPS[group],
        "tools": list(tools),
        "shared_meta_tools": server_tools,
        "when_to_use": list(template.get("when_to_use", [])),
        "workflow": list(template.get("workflow", [])),
        "handoff_targets": list(template.get("handoff_targets", [])),
    }


def build_subagent_catalog() -> dict[str, Any]:
    """Build a subagent catalog from the publishable registry surface."""
    ensure_tool_registry_populated()
    registry_tools = get_registered_tools()
    group_tools = {group: [] for group in TOOL_GROUPS}
    for tool in registry_tools:
        group = tool.get("group")
        if not group or group not in group_tools:
            continue
        if not is_publishable_registry_tool(tool):
            continue
        group_tools[group].append(tool["name"])
    for group in group_tools:
        group_tools[group] = sorted(set(group_tools[group]))

    server_tools = _server_meta_tools()
    compatibility_summary = summarize_registry_compatibility(registry_tools)

    subagents = [_build_orchestrator(server_tools, group_tools)]
    for group in sorted(TOOL_GROUPS.keys()):
        subagents.append(_build_specialist(group, group_tools.get(group, []), server_tools))

    return {
        "version": 1,
        "generated_from": "server_tool_registry",
        "compatibility_source": "unity_csharp_source_scan",
        "default_enabled_groups": sorted(DEFAULT_ENABLED_GROUPS),
        "group_count": len(TOOL_GROUPS),
        "subagent_count": len(subagents),
        "compatibility_summary": compatibility_summary,
        "subagents": subagents,
    }


def _render_subagent_markdown(subagent: dict[str, Any]) -> str:
    lines = [
        f"# {subagent['name']}",
        "",
        f"ID: `{subagent['id']}`",
        f"Kind: `{subagent['kind']}`",
        "",
        subagent["description"],
        "",
    ]

    if "group" in subagent:
        lines.extend(
            [
                f"Tool group: `{subagent['group']}`",
                (
                    "Activate with: "
                    f"`manage_tools(action=\"activate\", group=\"{subagent['group']}\")`"
                ),
                "",
            ]
        )

    shared_meta_tools = subagent.get("shared_meta_tools") or []
    if shared_meta_tools:
        lines.extend(
            [
                "Shared meta-tools:",
                *[f"- `{tool}`" for tool in shared_meta_tools],
                "",
            ]
        )

    tools = subagent.get("tools") or []
    if tools:
        lines.extend(
            [
                "Primary tools:",
                *[f"- `{tool}`" for tool in tools],
                "",
            ]
        )

    when_to_use = subagent.get("when_to_use") or []
    if when_to_use:
        lines.extend(
            [
                "Use when:",
                *[f"- {item}" for item in when_to_use],
                "",
            ]
        )

    instructions = subagent.get("instructions") or []
    if instructions:
        lines.extend(
            [
                "Instructions:",
                *[f"- {item}" for item in instructions],
                "",
            ]
        )

    workflow = subagent.get("workflow") or []
    if workflow:
        lines.extend(
            [
                "Workflow:",
                *[f"- {item}" for item in workflow],
                "",
            ]
        )

    handoff_targets = subagent.get("handoff_targets") or []
    if handoff_targets:
        lines.extend(
            [
                "Handoff targets:",
                *[f"- `{item}`" for item in handoff_targets],
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def _render_catalog_readme(catalog: dict[str, Any]) -> str:
    lines = [
        "# Unity MCP Subagents",
        "",
        "Generated specialist and orchestrator definitions derived from the live MCP tool registry.",
        "",
        f"Default enabled groups: {', '.join(catalog['default_enabled_groups'])}",
        f"Total subagents: {catalog['subagent_count']}",
        "",
        "Available subagents:",
    ]
    for subagent in catalog["subagents"]:
        lines.append(f"- `{subagent['id']}`: {subagent['description']}")
    lines.extend(
        [
            "",
            "Primary catalog file: `subagents.json`",
        ]
    )
    return "\n".join(lines) + "\n"


def export_subagent_artifacts(
    output_dir: str | Path | None = None,
    *,
    include_json: bool = True,
    include_markdown: bool = True,
) -> dict[str, Any]:
    """Write subagent artifacts to disk and return a summary."""
    target_dir = Path(output_dir) if output_dir is not None else default_subagent_output_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    catalog = build_subagent_catalog()
    written_files: list[str] = []

    if include_json:
        json_path = target_dir / "subagents.json"
        json_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written_files.append(str(json_path))

    if include_markdown:
        readme_path = target_dir / "README.md"
        readme_path.write_text(_render_catalog_readme(catalog), encoding="utf-8")
        written_files.append(str(readme_path))

        for subagent in catalog["subagents"]:
            subagent_path = target_dir / f"{subagent['id']}.md"
            subagent_path.write_text(_render_subagent_markdown(subagent), encoding="utf-8")
            written_files.append(str(subagent_path))

    return {
        "output_dir": str(target_dir),
        "written_files": written_files,
        "subagent_count": catalog["subagent_count"],
    }
