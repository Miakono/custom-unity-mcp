"""Utilities for building and exporting a live tool catalog."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import UnionType
from typing import Any, Annotated, Literal, Union, get_args, get_origin, get_type_hints

from services.registry import (
    DEFAULT_ENABLED_GROUPS,
    TOOL_GROUPS,
    ensure_tool_registry_populated,
    get_registered_tools,
)
from services.tools.action_policy import (
    get_known_read_only_actions,
    get_tool_action_model,
    get_tool_action_policy,
    ToolActionPolicy,
)
from core.capability_flags import (
    supports_dry_run,
    is_local_only_tool,
    is_runtime_only_tool,
    requires_explicit_opt_in,
    supports_verification,
    get_tool_capability_flags,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_catalog_output_dir() -> Path:
    return _repo_root() / "Generated" / "Catalog"


def _get_tool_capabilities(tool_name: str, unity_target: str | None) -> dict[str, Any]:
    """Get comprehensive capability metadata for a tool.

    Uses actual implementation from capability_flags and action_policy
    rather than hardcoded values.
    """
    policy = get_tool_action_policy(tool_name)
    action_model = get_tool_action_model(tool_name)

    # Get capabilities from the central capability registry
    capability_flags = get_tool_capability_flags(tool_name)

    # Override with policy-specific values where appropriate
    return {
        "read_only": not policy.mutating,
        "mutating": policy.mutating,
        "high_risk": policy.high_risk,
        "requires_unity": unity_target is not None and not capability_flags["local_only"],
        "server_only": unity_target is None or capability_flags["local_only"],
        "supports_verification": capability_flags["supports_verification"],
        "supports_dry_run": capability_flags["supports_dry_run"],
        "local_only": capability_flags["local_only"],
        "runtime_only": capability_flags["runtime_only"],
        "requires_explicit_opt_in": capability_flags["requires_explicit_opt_in"],
        "action_model": action_model,
        "known_read_only_actions": get_known_read_only_actions(tool_name),
        "wait_for_no_compile": policy.wait_for_no_compile,
        "refresh_if_dirty": policy.refresh_if_dirty,
        "requires_no_tests": policy.requires_no_tests,
    }


def _unwrap_annotation(annotation: Any) -> Any:
    current = annotation
    while get_origin(current) is Annotated:
        args = get_args(current)
        current = args[0] if args else current
    return current


def _extract_literal_strings(annotation: Any) -> list[str]:
    current = _unwrap_annotation(annotation)
    origin = get_origin(current)

    if origin is Literal:
        return sorted(str(arg) for arg in get_args(current) if isinstance(arg, str))

    if origin is None:
        return []

    values: list[str] = []
    for arg in get_args(current):
        values.extend(_extract_literal_strings(arg))
    return sorted(set(values))


def _annotation_type_name(annotation: Any) -> str:
    current = _unwrap_annotation(annotation)
    origin = get_origin(current)
    union_origins = (Union, UnionType)

    if origin is Literal:
        return "enum"
    if origin in (list, tuple, set):
        return "array"
    if origin is dict:
        return "object"
    if origin in union_origins:
        args = [arg for arg in get_args(current) if arg is not type(None)]
        if not args:
            return "unknown"
        names = sorted({_annotation_type_name(arg) for arg in args})
        return names[0] if len(names) == 1 else " | ".join(names)
    if current in (str,):
        return "string"
    if current in (int,):
        return "integer"
    if current in (float,):
        return "number"
    if current in (bool,):
        return "boolean"
    if current is inspect._empty:
        return "unknown"
    if origin is not None:
        return str(origin).replace("typing.", "")
    return getattr(current, "__name__", str(current))


def _get_tool_signature_details(func: Any, tool_name: str) -> dict[str, Any]:
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return {"parameters": [], "supported_actions": [], "action_capabilities": {}}
    try:
        resolved_hints = get_type_hints(func, include_extras=True)
    except Exception:
        resolved_hints = {}

    parameters = []
    supported_actions: list[str] = []
    action_capabilities: dict[str, Any] = {}

    for param in signature.parameters.values():
        if param.name == "ctx":
            continue

        annotation = resolved_hints.get(param.name, param.annotation)
        enum_values = _extract_literal_strings(annotation)
        parameter_info = {
            "name": param.name,
            "required": param.default is inspect._empty,
            "type": _annotation_type_name(annotation),
        }
        if enum_values:
            parameter_info["enum"] = enum_values
        parameters.append(parameter_info)

        if param.name == "action" and enum_values:
            supported_actions = enum_values

    for action_name in supported_actions:
        policy = get_tool_action_policy(tool_name, action=action_name)
        action_capabilities[action_name] = {
            "read_only": not policy.mutating,
            "mutating": policy.mutating,
            "high_risk": policy.high_risk,
            "supports_dry_run": policy.supports_dry_run,
            "wait_for_no_compile": policy.wait_for_no_compile,
            "refresh_if_dirty": policy.refresh_if_dirty,
            "requires_no_tests": policy.requires_no_tests,
        }

    return {
        "parameters": parameters,
        "supported_actions": supported_actions,
        "action_capabilities": action_capabilities,
    }


def build_tool_catalog() -> dict[str, Any]:
    """Build a machine-readable tool catalog from the live registry."""
    ensure_tool_registry_populated()
    entries = []

    for tool in sorted(get_registered_tools(), key=lambda item: item["name"]):
        group = tool.get("group")
        unity_target = tool.get("unity_target")
        kwargs = tool.get("kwargs") or {}
        tags = sorted(kwargs.get("tags") or [])
        signature_details = _get_tool_signature_details(tool.get("func"), tool["name"])

        entries.append({
            "name": tool["name"],
            "description": tool.get("description"),
            "group": group,
            "group_description": TOOL_GROUPS.get(group) if group else None,
            "default_enabled": group in DEFAULT_ENABLED_GROUPS if group else True,
            "unity_target": unity_target,
            "tags": tags,
            "capabilities": _get_tool_capabilities(tool["name"], unity_target),
            "parameters": signature_details["parameters"],
            "supported_actions": signature_details["supported_actions"],
            "action_capabilities": signature_details["action_capabilities"],
        })

    grouped_counts = {
        group: len([entry for entry in entries if entry["group"] == group])
        for group in sorted(TOOL_GROUPS.keys())
    }

    return {
        "version": 1,
        "generated_from": "live_tool_registry",
        "default_enabled_groups": sorted(DEFAULT_ENABLED_GROUPS),
        "group_count": len(TOOL_GROUPS),
        "tool_count": len(entries),
        "grouped_counts": grouped_counts,
        "tools": entries,
    }


def _render_catalog_markdown(catalog: dict[str, Any]) -> str:
    lines = [
        "# Unity MCP Tool Catalog",
        "",
        "Generated machine-readable catalog derived from the live server tool registry.",
        "",
        f"Tool count: {catalog['tool_count']}",
        f"Default enabled groups: {', '.join(catalog['default_enabled_groups'])}",
        "",
    ]

    for tool in catalog["tools"]:
        caps = tool["capabilities"]
        lines.extend([
            f"## {tool['name']}",
            "",
            tool.get("description") or "No description.",
            "",
            f"- Group: `{tool['group']}`" if tool["group"] else "- Group: `server-meta`",
            f"- Unity target: `{tool['unity_target']}`" if tool["unity_target"] else "- Unity target: `server-only`",
            f"- Action model: `{caps['action_model']}`",
            f"- Mutating: `{str(caps['mutating']).lower()}`",
            f"- High risk: `{str(caps['high_risk']).lower()}`",
            f"- Supports dry-run: `{str(caps['supports_dry_run']).lower()}`",
            f"- Local only: `{str(caps['local_only']).lower()}`",
            f"- Runtime only: `{str(caps['runtime_only']).lower()}`",
            f"- Requires explicit opt-in: `{str(caps['requires_explicit_opt_in']).lower()}`",
        ])
        if tool["supported_actions"]:
            lines.append(
                f"- Supported actions: {', '.join(f'`{action}`' for action in tool['supported_actions'])}"
            )
        if caps["known_read_only_actions"]:
            lines.append(
                f"- Known read-only actions: {', '.join(f'`{action}`' for action in caps['known_read_only_actions'])}"
            )
        if tool["parameters"]:
            lines.extend([
                "- Parameters:",
                *[
                    (
                        f"  - `{param['name']}`: "
                        f"type=`{param['type']}`, "
                        f"required=`{str(param['required']).lower()}`"
                        + (
                            f", enum={', '.join(f'`{value}`' for value in param['enum'])}"
                            if param.get("enum")
                            else ""
                        )
                    )
                    for param in tool["parameters"]
                ],
            ])
        if tool["action_capabilities"]:
            lines.extend([
                "- Action contracts:",
                *[
                    (
                        f"  - `{action}`: "
                        f"read_only=`{str(details['read_only']).lower()}`, "
                        f"mutating=`{str(details['mutating']).lower()}`, "
                        f"high_risk=`{str(details['high_risk']).lower()}`, "
                        f"supports_dry_run=`{str(details.get('supports_dry_run', False)).lower()}`"
                    )
                    for action, details in sorted(tool["action_capabilities"].items())
                ],
            ])
        lines.append("")

    return "\n".join(lines)


def export_tool_catalog_artifacts(
    output_dir: str | Path | None = None,
    *,
    include_json: bool = True,
    include_markdown: bool = True,
) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir is not None else default_catalog_output_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    catalog = build_tool_catalog()
    written_files: list[str] = []

    if include_json:
        json_path = target_dir / "tool_catalog.json"
        json_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written_files.append(str(json_path))

    if include_markdown:
        md_path = target_dir / "README.md"
        md_path.write_text(_render_catalog_markdown(catalog) + "\n", encoding="utf-8")
        written_files.append(str(md_path))

    return {
        "output_dir": str(target_dir),
        "written_files": written_files,
        "tool_count": catalog["tool_count"],
    }


def get_tool_capabilities_query(tool_name: str) -> dict[str, Any]:
    """Query capabilities for a specific tool programmatically.

    This function allows external callers to query tool capabilities
    without needing to build the entire catalog.

    Args:
        tool_name: Name of the tool to query

    Returns:
        Dictionary containing all capability metadata for the tool
    """
    ensure_tool_registry_populated()

    # Find the tool in the registry
    for tool in get_registered_tools():
        if tool["name"] == tool_name:
            unity_target = tool.get("unity_target")
            return {
                "tool_name": tool_name,
                "found": True,
                "capabilities": _get_tool_capabilities(tool_name, unity_target),
            }

    return {
        "tool_name": tool_name,
        "found": False,
        "capabilities": None,
    }


def query_capabilities(
    tool_name: str | None = None,
    capability_filter: str | None = None,
) -> dict[str, Any]:
    """Query tool capabilities with optional filtering.

    Args:
        tool_name: Optional specific tool to query. If None, returns all tools.
        capability_filter: Optional capability to filter by (e.g., "supports_dry_run",
                          "local_only", "runtime_only", "requires_explicit_opt_in")

    Returns:
        Dictionary with matching tools and their capabilities
    """
    ensure_tool_registry_populated()

    if tool_name:
        result = get_tool_capabilities_query(tool_name)
        if not result["found"]:
            return {"error": f"Tool '{tool_name}' not found"}
        return result

    # Return all tools, optionally filtered
    tools = []
    for tool in get_registered_tools():
        unity_target = tool.get("unity_target")
        capabilities = _get_tool_capabilities(tool["name"], unity_target)

        # Apply filter if specified
        if capability_filter:
            if not capabilities.get(capability_filter, False):
                continue

        tools.append({
            "name": tool["name"],
            "capabilities": capabilities,
        })

    return {
        "tool_count": len(tools),
        "capability_filter": capability_filter,
        "tools": tools,
    }
