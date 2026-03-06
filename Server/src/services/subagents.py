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
        if tool.get("group") is None
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
            "Start with core unless the task is clearly UI, VFX, animation, data, or testing focused.",
            "Use manage_tools to activate only the group needed for the current phase of work.",
            "Set the active Unity instance before specialist handoff when multiple editors are connected.",
            "After meaningful mutations, hand off to the testing specialist for verification.",
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
    """Build a subagent catalog from the live tool registry."""
    ensure_tool_registry_populated()
    group_tools = get_group_tool_names()
    server_tools = _server_meta_tools()

    subagents = [_build_orchestrator(server_tools, group_tools)]
    for group in sorted(TOOL_GROUPS.keys()):
        subagents.append(_build_specialist(group, group_tools.get(group, []), server_tools))

    return {
        "version": 1,
        "generated_from": "live_tool_registry",
        "default_enabled_groups": sorted(DEFAULT_ENABLED_GROUPS),
        "group_count": len(TOOL_GROUPS),
        "subagent_count": len(subagents),
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
