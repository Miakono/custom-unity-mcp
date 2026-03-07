"""
Asset comparison tool for generating structured diffs between Unity assets.

Supports comparing:
- Any Unity asset (materials, textures, scripts, etc.)
- Import settings
- Binary asset comparison (hash-based)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.utils import coerce_bool, parse_json_payload
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry
from services.tools.action_policy import maybe_run_tool_preflight


def _generate_diff_id() -> str:
    """Generate a unique diff identifier."""
    return f"diff_{uuid4().hex[:12]}"


def _compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of a file."""
    try:
        path = Path(file_path)
        if not path.exists():
            return ""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


def _compare_assets(
    source: dict[str, Any],
    target: dict[str, Any],
    include_binary: bool = False,
) -> list[dict[str, Any]]:
    """
    Compare two assets and return change records.
    
    Args:
        source: Source asset data
        target: Target asset data
        include_binary: Whether to include binary/hash comparison
        
    Returns:
        List of change records
    """
    changes: list[dict[str, Any]] = []
    
    # Compare basic properties
    basic_props = ["guid", "type", "name", "path"]
    for prop in basic_props:
        old_val = source.get(prop)
        new_val = target.get(prop)
        if old_val != new_val and (old_val is not None or new_val is not None):
            changes.append({
                "path": f"asset.{prop}",
                "change_type": "modified",
                "property": prop,
                "old_value": old_val,
                "new_value": new_val,
                "value_type": type(new_val).__name__ if new_val is not None else "None",
            })
    
    # Compare import settings
    source_import = source.get("importSettings", {})
    target_import = target.get("importSettings", {})
    
    import_changes = _compare_import_settings(source_import, target_import)
    changes.extend(import_changes)
    
    # Compare asset-specific properties
    source_props = source.get("properties", {})
    target_props = target.get("properties", {})
    
    property_changes = _compare_asset_properties(source_props, target_props)
    changes.extend(property_changes)
    
    # Binary comparison if requested
    if include_binary:
        source_hash = source.get("fileHash", "")
        target_hash = target.get("fileHash", "")
        
        if source_hash and target_hash and source_hash != target_hash:
            changes.append({
                "path": "asset.fileContent",
                "change_type": "modified",
                "property": "fileHash",
                "old_value": source_hash[:16] + "...",
                "new_value": target_hash[:16] + "...",
                "value_type": "hash",
                "binary_changed": True,
            })
    
    return changes


def _compare_import_settings(
    source: dict[str, Any],
    target: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare import settings between two assets."""
    changes: list[dict[str, Any]] = []
    
    all_keys = set(source.keys()) | set(target.keys())
    
    for key in sorted(all_keys):
        old_val = source.get(key)
        new_val = target.get(key)
        
        if _values_differ(old_val, new_val):
            changes.append({
                "path": f"importSettings.{key}",
                "change_type": "modified",
                "property": key,
                "old_value": old_val,
                "new_value": new_val,
                "value_type": _get_value_type(new_val),
                "is_import_setting": True,
            })
    
    return changes


def _compare_asset_properties(
    source: dict[str, Any],
    target: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare asset-specific properties."""
    changes: list[dict[str, Any]] = []
    
    # Skip common/internal properties
    skip_keys = {"guid", "type", "name", "path", "instanceID", "hideFlags"}
    
    all_keys = set(source.keys()) | set(target.keys())
    all_keys -= skip_keys
    
    for key in sorted(all_keys):
        old_val = source.get(key)
        new_val = target.get(key)
        
        if _values_differ(old_val, new_val):
            changes.append({
                "path": f"properties.{key}",
                "change_type": "modified",
                "property": key,
                "old_value": old_val,
                "new_value": new_val,
                "value_type": _get_value_type(new_val),
            })
    
    return changes


def _values_differ(old: Any, new: Any) -> bool:
    """Check if two values are different."""
    if type(old) != type(new):
        return True
        
    if isinstance(old, (list, tuple)):
        if len(old) != len(new):
            return True
        return any(_values_differ(o, n) for o, n in zip(old, new))
        
    if isinstance(old, dict):
        if set(old.keys()) != set(new.keys()):
            return True
        return any(_values_differ(old[k], new[k]) for k in old.keys())
        
    return old != new


def _get_value_type(value: Any) -> str:
    """Get a human-readable type name for a value."""
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        return f"array[{len(value)}]"
    if isinstance(value, dict):
        if "guid" in value:
            return "asset_ref"
        if "instanceID" in value:
            return "object_ref"
        if "r" in value and "g" in value and "b" in value:
            return "color"
        if "x" in value and "y" in value and "z" in value:
            return "vector"
        return "object"
    return type(value).__name__


def _generate_human_readable_summary(diff_result: dict[str, Any]) -> str:
    """Generate a human-readable summary of the diff."""
    summary = diff_result.get("summary", {})
    changes = diff_result.get("changes", [])
    
    source_path = diff_result.get('source', {}).get('path', 'Unknown')
    target_path = diff_result.get('target', {}).get('path', 'Unknown')
    
    lines = [
        "Asset Diff Summary",
        "==================",
        f"Source: {source_path}",
    ]
    
    if target_path != source_path:
        lines.append(f"Target: {target_path}")
    
    lines.extend([
        "",
        f"Total Changes: {summary.get('total', 0)}",
        f"  Import Settings: {summary.get('import_settings', 0)}",
        f"  Properties: {summary.get('properties', 0)}",
        f"  Binary: {summary.get('binary', 0)}",
        "",
    ])
    
    # Group changes by category
    import_changes = [c for c in changes if c.get("is_import_setting")]
    prop_changes = [c for c in changes if not c.get("is_import_setting") and not c.get("binary_changed")]
    binary_changes = [c for c in changes if c.get("binary_changed")]
    
    if import_changes:
        lines.append("Import Setting Changes:")
        for change in import_changes[:15]:
            lines.append(f"  ~ {change['property']}: {change['old_value']} -> {change['new_value']}")
        if len(import_changes) > 15:
            lines.append(f"  ... and {len(import_changes) - 15} more")
        lines.append("")
        
    if prop_changes:
        lines.append("Property Changes:")
        for change in prop_changes[:15]:
            prop_name = change['property']
            old_val = change['old_value']
            new_val = change['new_value']
            # Truncate long values
            old_str = str(old_val)[:30] + "..." if len(str(old_val)) > 30 else str(old_val)
            new_str = str(new_val)[:30] + "..." if len(str(new_val)) > 30 else str(new_val)
            lines.append(f"  ~ {prop_name}: {old_str} -> {new_str}")
        if len(prop_changes) > 15:
            lines.append(f"  ... and {len(prop_changes) - 15} more")
        lines.append("")
        
    if binary_changes:
        lines.append("Binary Changes:")
        for change in binary_changes:
            lines.append(f"  ~ {change['property']}: {change['old_value']} -> {change['new_value']}")
        lines.append("")
    
    return "\n".join(lines)


@mcp_for_unity_tool(
    group="diff_patch",
    description=(
        "Compare Unity assets and generate structured diffs. "
        "Supports comparing any Unity asset type (materials, textures, scripts, etc.), "
        "showing import setting changes, and binary asset comparison via hash. "
        "Returns a structured diff that can be used for review and verification workflows."
    ),
    annotations=ToolAnnotations(
        title="Diff Asset",
        destructiveHint=False,
    ),
)
async def diff_asset(
    ctx: Context,
    source_path: Annotated[
        str | None,
        "Source asset path (e.g., 'Assets/Materials/MyMaterial.mat')"
    ] = None,
    target_path: Annotated[
        str | None,
        "Target asset path (defaults to source_path for version comparison)"
    ] = None,
    compare_mode: Annotated[
        Literal["current_vs_saved", "two_assets", "check_import_settings"],
        "Comparison mode: current_vs_saved (in-memory vs disk), two_assets (compare two different assets), check_import_settings (focus on import settings)"
    ] = "current_vs_saved",
    include_binary: Annotated[
        bool | str,
        "Include binary file hash comparison (for detecting actual file content changes)"
    ] = False,
    include_import_settings: Annotated[
        bool | str,
        "Include import settings in the comparison"
    ] = True,
    asset_path: Annotated[
        str | None,
        "Alias for source_path."
    ] = None,
    asset_guid: Annotated[
        str | None,
        "Optional asset GUID when path is not available."
    ] = None,
) -> dict[str, Any]:
    """
    Generate a structured diff between Unity assets.
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    # Preflight check
    gate = await maybe_run_tool_preflight(ctx, "diff_asset", action="compare")
    if gate is not None:
        return gate.model_dump()
    
    # Normalize parameters
    include_binary_val = coerce_bool(include_binary, default=False)
    include_import_settings_val = coerce_bool(include_import_settings, default=True)
    effective_source_path = asset_path or source_path

    if not effective_source_path and not asset_guid:
        return {
            "success": False,
            "message": "asset_path, source_path, or asset_guid is required",
            "diff_id": _generate_diff_id(),
        }
    
    # Default target to source for current_vs_saved mode
    if compare_mode == "current_vs_saved" and not target_path:
        target_path = effective_source_path
    
    diff_id = _generate_diff_id()
    
    try:
        # Build request parameters
        params: dict[str, Any] = {
            "action": "get_asset_data",
            "compareMode": compare_mode,
            "sourcePath": effective_source_path,
            "includeMetadata": True,
            "includeImportSettings": include_import_settings_val,
        }
        
        if target_path:
            params["targetPath"] = target_path
        if asset_guid:
            params["assetGuid"] = asset_guid
        if include_binary_val:
            params["includeFileHash"] = True
            
        # Request asset data from Unity
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "diff_asset",
            params
        )
        
        if not isinstance(response, dict) or not response.get("success"):
            error_msg = response.get("message", "Unknown error") if isinstance(response, dict) else str(response)
            return {
                "success": False,
                "message": f"Failed to get asset data: {error_msg}",
                "diff_id": diff_id,
            }
        
        data = response.get("data", {})
        return {
            "success": True,
            "message": response.get("message", "Asset diff generated."),
            "data": {
                "diff_id": diff_id,
                **data,
            },
        }
        
    except Exception as exc:
        return {
            "success": False,
            "message": f"Error generating asset diff: {exc!s}",
            "diff_id": diff_id,
        }
