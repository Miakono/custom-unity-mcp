"""Utilities for building and exporting stable error-code artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_ERROR_DOMAINS: list[dict[str, Any]] = [
    {
        "id": "script_editing",
        "title": "Script Editing",
        "description": "Stable machine-readable codes emitted by script edit and validation flows.",
        "entries": [
            {
                "code": "missing_field",
                "surface": ["apply_text_edits", "script_apply_edits"],
                "meaning": "A required edit field was omitted or could not be normalized.",
                "typical_fix": "Send the required path, range, or replacement fields.",
            },
            {
                "code": "zero_based_explicit_fields",
                "surface": ["apply_text_edits"],
                "meaning": "Explicit line or column coordinates were sent as 0-based values.",
                "typical_fix": "Resend explicit line and column coordinates as 1-based indices.",
            },
            {
                "code": "overlap",
                "surface": ["apply_text_edits"],
                "meaning": "Two requested edit spans overlap.",
                "typical_fix": "Split or reorder edits so no two spans intersect.",
            },
            {
                "code": "preview_failed",
                "surface": ["apply_text_edits"],
                "meaning": "The server could not build the requested local preview payload.",
                "typical_fix": "Retry with a smaller edit batch or remove preview mode.",
            },
            {
                "code": "path_outside_assets",
                "surface": ["create_script", "delete_script", "validate_script", "apply_text_edits"],
                "meaning": "A path or URI resolved outside the Unity Assets folder.",
                "typical_fix": "Use an asset path rooted under Assets/.",
            },
            {
                "code": "bad_path",
                "surface": ["create_script"],
                "meaning": "The provided path was malformed, absolute, or traversal-like.",
                "typical_fix": "Send a normalized Unity asset path without traversal segments.",
            },
            {
                "code": "bad_extension",
                "surface": ["create_script"],
                "meaning": "The provided file extension is not valid for that script operation.",
                "typical_fix": "Use a .cs target path for script creation.",
            },
            {
                "code": "bad_level",
                "surface": ["validate_script"],
                "meaning": "The requested script validation level is not recognized.",
                "typical_fix": "Use one of the documented level values.",
            },
            {
                "code": "anchor_not_found",
                "surface": ["script_apply_edits"],
                "meaning": "An anchor-based edit target could not be resolved.",
                "typical_fix": "Re-read the file and provide a more specific anchor.",
            },
            {
                "code": "unsupported_op",
                "surface": ["script_apply_edits"],
                "meaning": "The requested structured edit operation is not supported.",
                "typical_fix": "Rewrite the request using a supported edit op.",
            },
            {
                "code": "no_spans",
                "surface": ["script_apply_edits"],
                "meaning": "No applicable text spans were computed for the requested edit.",
                "typical_fix": "Verify that the target method, class, or anchor still exists.",
            },
            {
                "code": "conversion_failed",
                "surface": ["script_apply_edits"],
                "meaning": "The server failed converting a higher-level edit into raw spans.",
                "typical_fix": "Simplify the edit request and retry after re-reading the file.",
            },
        ],
    },
    {
        "id": "scriptable_objects",
        "title": "Scriptable Objects",
        "description": "Stable Unity-side error codes emitted by ScriptableObject management.",
        "entries": [
            {
                "code": "compiling_or_reloading",
                "surface": ["manage_scriptable_object"],
                "meaning": "Unity was compiling or reloading and rejected the write operation.",
                "typical_fix": "Wait until the editor is idle, then retry.",
            },
            {
                "code": "invalid_params",
                "surface": ["manage_scriptable_object"],
                "meaning": "A required ScriptableObject parameter was missing or malformed.",
                "typical_fix": "Validate the action payload and resend the required fields.",
            },
            {
                "code": "type_not_found",
                "surface": ["manage_scriptable_object"],
                "meaning": "The requested ScriptableObject CLR type could not be resolved.",
                "typical_fix": "Use a valid namespace-qualified ScriptableObject type name.",
            },
            {
                "code": "invalid_folder_path",
                "surface": ["manage_scriptable_object"],
                "meaning": "The target folder path is invalid or outside the supported project area.",
                "typical_fix": "Use a valid folder rooted under Assets/.",
            },
            {
                "code": "target_not_found",
                "surface": ["manage_scriptable_object"],
                "meaning": "The ScriptableObject target could not be resolved from guid or path.",
                "typical_fix": "Re-resolve the asset guid or path and retry.",
            },
            {
                "code": "asset_create_failed",
                "surface": ["manage_scriptable_object"],
                "meaning": "Unity failed while creating or saving the requested asset.",
                "typical_fix": "Inspect the payload and target path, then retry after Unity is idle.",
            },
        ],
    },
]


_OPERATIONAL_PATTERNS: list[dict[str, str]] = [
    {
        "pattern": "success=false with guidance to call set_active_instance",
        "surface": "multi-instance server flows",
        "meaning": "No active Unity instance is selected for the current session.",
        "typical_fix": "Call set_active_instance with a Name@hash value from mcpforunity://instances.",
    },
    {
        "pattern": "preflight-gated tool returns success=false before mutation",
        "surface": "mutating tools",
        "meaning": "Unity is compiling, importing, running tests, or otherwise not ready for mutation.",
        "typical_fix": "Wait for the editor to become ready, then retry the mutation tool.",
    },
    {
        "pattern": "manage_tools(action='sync') returns unsupported wording",
        "surface": "tool visibility sync",
        "meaning": "The connected Unity plugin is too old to report tool-state visibility.",
        "typical_fix": "Update the Unity package or toggle groups manually with activate/deactivate.",
    },
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_error_catalog_output_dir() -> Path:
    return _repo_root() / "Generated" / "ErrorCatalog"


def build_error_catalog() -> dict[str, Any]:
    """Return the current structured error and contract catalog."""
    domains = [
        {
            **domain,
            "entry_count": len(domain["entries"]),
        }
        for domain in _ERROR_DOMAINS
    ]

    stable_codes = [entry["code"] for domain in domains for entry in domain["entries"]]
    surfaces = sorted(
        {
            surface
            for domain in domains
            for entry in domain["entries"]
            for surface in entry["surface"]
        }
    )

    return {
        "version": 1,
        "generated_from": "fork_error_contract_registry",
        "domain_count": len(domains),
        "stable_code_count": len(stable_codes),
        "surfaces": surfaces,
        "domains": domains,
        "operational_patterns": list(_OPERATIONAL_PATTERNS),
    }


def _render_error_catalog_markdown(catalog: dict[str, Any]) -> str:
    lines = [
        "# Unity MCP Error Catalog",
        "",
        "Structured error and operational contract data for the custom fork.",
        "",
        f"Stable codes: {catalog['stable_code_count']}",
        f"Domains: {catalog['domain_count']}",
        "",
    ]

    for domain in catalog["domains"]:
        lines.extend([
            f"## {domain['title']}",
            "",
            domain["description"],
            "",
        ])
        for entry in domain["entries"]:
            lines.extend([
                f"- `{entry['code']}`",
                f"  - Surfaces: {', '.join(f'`{surface}`' for surface in entry['surface'])}",
                f"  - Meaning: {entry['meaning']}",
                f"  - Typical fix: {entry['typical_fix']}",
            ])
        lines.append("")

    if catalog["operational_patterns"]:
        lines.extend([
            "## Operational Patterns",
            "",
        ])
        for pattern in catalog["operational_patterns"]:
            lines.extend([
                f"- `{pattern['pattern']}`",
                f"  - Surface: {pattern['surface']}",
                f"  - Meaning: {pattern['meaning']}",
                f"  - Typical fix: {pattern['typical_fix']}",
            ])
        lines.append("")

    return "\n".join(lines).rstrip()


def export_error_catalog_artifacts(
    output_dir: str | Path | None = None,
    *,
    include_json: bool = True,
    include_markdown: bool = True,
) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir is not None else default_error_catalog_output_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    catalog = build_error_catalog()
    written_files: list[str] = []

    if include_json:
        json_path = target_dir / "error_catalog.json"
        json_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written_files.append(str(json_path))

    if include_markdown:
        md_path = target_dir / "README.md"
        md_path.write_text(_render_error_catalog_markdown(catalog) + "\n", encoding="utf-8")
        written_files.append(str(md_path))

    return {
        "output_dir": str(target_dir),
        "written_files": written_files,
        "stable_code_count": catalog["stable_code_count"],
        "domain_count": catalog["domain_count"],
    }
