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
            {
                "code": "sha_mismatch",
                "surface": ["apply_text_edits", "create_script", "delete_script"],
                "meaning": "The content SHA256 did not match, indicating concurrent modification.",
                "typical_fix": "Re-read the file and retry the operation with the updated SHA.",
            },
            {
                "code": "file_not_found",
                "surface": ["apply_text_edits", "delete_script", "validate_script"],
                "meaning": "The target script file could not be found.",
                "typical_fix": "Verify the file path exists and is correctly spelled.",
            },
            {
                "code": "file_locked",
                "surface": ["apply_text_edits", "create_script", "delete_script"],
                "meaning": "The target file is locked by another process (e.g., IDE, version control).",
                "typical_fix": "Close the file in other applications and retry.",
            },
            {
                "code": "syntax_error",
                "surface": ["validate_script", "apply_text_edits"],
                "meaning": "The resulting script would have syntax errors.",
                "typical_fix": "Review the edit for unbalanced braces, missing semicolons, etc.",
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
            {
                "code": "asset_modify_failed",
                "surface": ["manage_scriptable_object"],
                "meaning": "Unity failed while modifying the ScriptableObject.",
                "typical_fix": "Check that all serialized fields exist and types match.",
            },
            {
                "code": "type_mismatch",
                "surface": ["manage_scriptable_object"],
                "meaning": "The provided value type does not match the expected field type.",
                "typical_fix": "Ensure JSON values match the C# field types (e.g., use numbers for int/float).",
            },
        ],
    },
    {
        "id": "gameobject_management",
        "title": "GameObject Management",
        "description": "Error codes for GameObject CRUD operations.",
        "entries": [
            {
                "code": "gameobject_not_found",
                "surface": ["manage_gameobject"],
                "meaning": "The target GameObject could not be found by name, path, or ID.",
                "typical_fix": "Verify the GameObject exists in the current scene. Use find_gameobjects to search.",
            },
            {
                "code": "invalid_parent",
                "surface": ["manage_gameobject"],
                "meaning": "The specified parent GameObject is invalid or not found.",
                "typical_fix": "Verify the parent exists, or use null for root-level objects.",
            },
            {
                "code": "component_not_found",
                "surface": ["manage_gameobject", "manage_components"],
                "meaning": "The requested component could not be found on the target GameObject.",
                "typical_fix": "Verify the component name is correct and exists on the GameObject.",
            },
            {
                "code": "component_add_failed",
                "surface": ["manage_components"],
                "meaning": "Failed to add the component (type may not exist or be allowed).",
                "typical_fix": "Verify the component type name is fully qualified and the assembly is loaded.",
            },
            {
                "code": "invalid_transform",
                "surface": ["manage_gameobject"],
                "meaning": "The provided position, rotation, or scale values are invalid.",
                "typical_fix": "Use valid numeric arrays with 3 elements [x, y, z].",
            },
        ],
    },
    {
        "id": "scene_management",
        "title": "Scene Management",
        "description": "Error codes for scene operations.",
        "entries": [
            {
                "code": "scene_not_found",
                "surface": ["manage_scene"],
                "meaning": "The requested scene could not be found.",
                "typical_fix": "Verify the scene path is correct and the scene exists in the project.",
            },
            {
                "code": "scene_load_failed",
                "surface": ["manage_scene"],
                "meaning": "Unity failed to load the scene.",
                "typical_fix": "Check that the scene is in the build settings and has no load errors.",
            },
            {
                "code": "scene_save_failed",
                "surface": ["manage_scene"],
                "meaning": "Unity failed to save the scene.",
                "typical_fix": "Check file permissions and disk space.",
            },
            {
                "code": "active_scene_unchanged",
                "surface": ["manage_scene"],
                "meaning": "The requested scene is already the active scene.",
                "typical_fix": "No action needed, or specify a different scene to activate.",
            },
        ],
    },
    {
        "id": "prefab_operations",
        "title": "Prefab Operations",
        "description": "Error codes for prefab management.",
        "entries": [
            {
                "code": "prefab_not_found",
                "surface": ["manage_prefabs"],
                "meaning": "The prefab asset could not be found.",
                "typical_fix": "Verify the prefab path is correct and exists in the project.",
            },
            {
                "code": "prefab_instantiate_failed",
                "surface": ["manage_prefabs"],
                "meaning": "Failed to instantiate the prefab into the scene.",
                "typical_fix": "Verify the prefab is valid and can be instantiated.",
            },
            {
                "code": "prefab_variant_not_supported",
                "surface": ["manage_prefabs"],
                "meaning": "The operation is not supported on prefab variants.",
                "typical_fix": "Apply the operation to the base prefab or use supported actions.",
            },
            {
                "code": "nested_prefab_modified",
                "surface": ["manage_prefabs"],
                "meaning": "Attempted to modify a nested prefab which requires special handling.",
                "typical_fix": "Unpack or open the prefab for editing before making changes.",
            },
        ],
    },
    {
        "id": "asset_management",
        "title": "Asset Management",
        "description": "Error codes for asset operations.",
        "entries": [
            {
                "code": "asset_not_found",
                "surface": ["manage_asset", "manage_material", "manage_texture"],
                "meaning": "The asset could not be found at the specified path.",
                "typical_fix": "Verify the asset path is correct and the asset exists.",
            },
            {
                "code": "asset_import_failed",
                "surface": ["manage_asset"],
                "meaning": "Unity failed to import the asset.",
                "typical_fix": "Check the asset file format and integrity.",
            },
            {
                "code": "invalid_guid",
                "surface": ["manage_asset"],
                "meaning": "The provided GUID is invalid or malformed.",
                "typical_fix": "Use a valid Unity GUID (32 hexadecimal characters).",
            },
            {
                "code": "guid_not_found",
                "surface": ["manage_asset"],
                "meaning": "No asset found with the specified GUID.",
                "typical_fix": "Verify the GUID is correct and the asset exists in the project.",
            },
        ],
    },
    {
        "id": "batch_execution",
        "title": "Batch Execution",
        "description": "Error codes for batch_execute operations.",
        "entries": [
            {
                "code": "batch_too_large",
                "surface": ["batch_execute"],
                "meaning": "The batch contains more commands than the configured maximum.",
                "typical_fix": "Split the batch into smaller chunks or increase the limit in Unity settings.",
            },
            {
                "code": "invalid_command",
                "surface": ["batch_execute"],
                "meaning": "One or more commands in the batch are malformed or missing required fields.",
                "typical_fix": "Ensure each command has 'tool' and 'params' fields with valid values.",
            },
            {
                "code": "batch_partial_failure",
                "surface": ["batch_execute"],
                "meaning": "Some commands in the batch succeeded while others failed.",
                "typical_fix": "Review the per-command results and retry failed commands individually.",
            },
            {
                "code": "circular_reference",
                "surface": ["batch_execute"],
                "meaning": "Commands in the batch have circular dependencies.",
                "typical_fix": "Restructure the batch to remove circular dependencies.",
            },
        ],
    },
    {
        "id": "connection_errors",
        "title": "Connection and Transport",
        "description": "Error codes for Unity connection issues.",
        "entries": [
            {
                "code": "unity_not_connected",
                "surface": ["*"],
                "meaning": "No Unity instance is currently connected.",
                "typical_fix": "Ensure Unity is running with the MCP plugin enabled.",
            },
            {
                "code": "connection_timeout",
                "surface": ["*"],
                "meaning": "The connection to Unity timed out.",
                "typical_fix": "Check Unity is responsive and retry the operation.",
            },
            {
                "code": "instance_not_found",
                "surface": ["set_active_instance"],
                "meaning": "The specified Unity instance could not be found.",
                "typical_fix": "List available instances with mcpforunity://instances and use a valid Name@hash.",
            },
            {
                "code": "serialization_error",
                "surface": ["*"],
                "meaning": "Failed to serialize or deserialize the request/response.",
                "typical_fix": "Check that all parameters are JSON-serializable.",
            },
        ],
    },
    {
        "id": "tool_capabilities",
        "title": "Tool Capability Errors",
        "description": "Error codes for capability and permission issues.",
        "entries": [
            {
                "code": "tool_disabled",
                "surface": ["*"],
                "meaning": "The tool is disabled by configuration or group settings.",
                "typical_fix": "Enable the tool group with manage_tools(action='activate') or check capability config.",
            },
            {
                "code": "opt_in_required",
                "surface": ["execute_menu_item", "batch_execute", "delete_script"],
                "meaning": "This tool requires explicit user opt-in before use.",
                "typical_fix": "Add the tool to the tool_opt_in section of capabilities.json.",
            },
            {
                "code": "runtime_only_tool",
                "surface": ["read_console"],
                "meaning": "This tool only works when Unity is in play mode.",
                "typical_fix": "Enter play mode in Unity before using this tool.",
            },
            {
                "code": "dry_run_not_supported",
                "surface": ["*"],
                "meaning": "The requested dry-run (preview) mode is not supported by this tool.",
                "typical_fix": "Remove the dry_run flag or use a different tool.",
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
    {
        "pattern": "busy response with retry_after_ms",
        "surface": "all tools with preflight",
        "meaning": "The server is temporarily unable to process the request (compiling, testing, etc.).",
        "typical_fix": "Wait for the specified retry_after_ms period and retry the request.",
    },
    {
        "pattern": "success=false with code and data fields",
        "surface": "structured error responses",
        "meaning": "A recoverable error occurred with machine-readable details.",
        "typical_fix": "Check the 'code' field against the error catalog and apply the typical fix.",
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


def get_error_code_info(code: str) -> dict[str, Any] | None:
    """Get detailed information about a specific error code.

    Args:
        code: The error code to look up

    Returns:
        Error code details or None if not found
    """
    for domain in _ERROR_DOMAINS:
        for entry in domain["entries"]:
            if entry["code"] == code:
                return {
                    "code": entry["code"],
                    "domain": domain["id"],
                    "domain_title": domain["title"],
                    "meaning": entry["meaning"],
                    "typical_fix": entry["typical_fix"],
                    "surfaces": entry["surface"],
                }
    return None


def list_error_codes_for_surface(surface: str) -> list[dict[str, Any]]:
    """List all error codes that can be emitted by a specific tool/surface.

    Args:
        surface: The tool name or surface to filter by

    Returns:
        List of error codes that apply to the surface
    """
    results = []
    for domain in _ERROR_DOMAINS:
        for entry in domain["entries"]:
            if surface in entry["surface"] or "*" in entry["surface"]:
                results.append({
                    "code": entry["code"],
                    "domain": domain["id"],
                    "meaning": entry["meaning"],
                })
    return results
