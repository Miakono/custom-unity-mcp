"""
Prefab comparison tool for generating structured diffs between Unity prefabs.

Supports comparing:
- Prefab asset against instance
- Two prefab variants
- Showing override information
"""

from __future__ import annotations

import hashlib
import json
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


def _compare_prefab_objects(
    source_objects: list[dict[str, Any]],
    target_objects: list[dict[str, Any]],
    path_prefix: str = "",
    track_overrides: bool = False,
) -> list[dict[str, Any]]:
    """
    Compare two prefab object hierarchies and return change records.
    
    Args:
        source_objects: Objects from source prefab
        target_objects: Objects from target prefab
        path_prefix: Current path prefix for nested objects
        track_overrides: Whether to track prefab overrides
        
    Returns:
        List of change records
    """
    changes: list[dict[str, Any]] = []
    
    # Index by path
    source_by_path: dict[str, dict[str, Any]] = {}
    target_by_path: dict[str, dict[str, Any]] = {}
    
    for obj in source_objects:
        path = obj.get("path") or obj.get("name", "")
        full_path = f"{path_prefix}/{path}" if path_prefix else path
        source_by_path[full_path] = {**obj, "full_path": full_path}
        
    for obj in target_objects:
        path = obj.get("path") or obj.get("name", "")
        full_path = f"{path_prefix}/{path}" if path_prefix else path
        target_by_path[full_path] = {**obj, "full_path": full_path}
    
    all_paths = set(source_by_path.keys()) | set(target_by_path.keys())
    
    for path in sorted(all_paths):
        source_obj = source_by_path.get(path)
        target_obj = target_by_path.get(path)
        
        if source_obj is None:
            # Added in target (could be override)
            change = {
                "path": path,
                "change_type": "added",
                "component_changes": [],
                "property_changes": [],
                "details": {
                    "name": target_obj.get("name"),
                    "active": target_obj.get("active", True),
                },
            }
            if track_overrides:
                change["is_override"] = True
                change["override_type"] = "added_object"
            changes.append(change)
            
        elif target_obj is None:
            # Removed from source
            changes.append({
                "path": path,
                "change_type": "removed",
                "component_changes": [],
                "property_changes": [],
                "details": {
                    "name": source_obj.get("name"),
                },
            })
            
        else:
            # Compare existing object
            obj_changes = _compare_single_prefab_object(
                source_obj, target_obj, path, track_overrides
            )
            if obj_changes:
                changes.append(obj_changes)
                
            # Recursively compare children
            source_children = source_obj.get("children", [])
            target_children = target_obj.get("children", [])
            if source_children or target_children:
                child_changes = _compare_prefab_objects(
                    source_children, target_children, path, track_overrides
                )
                changes.extend(child_changes)
    
    return changes


def _compare_single_prefab_object(
    source: dict[str, Any],
    target: dict[str, Any],
    path: str,
    track_overrides: bool = False,
) -> dict[str, Any] | None:
    """
    Compare two versions of the same prefab object.
    
    Args:
        source: Source object data
        target: Target object data
        path: Full path to the object
        track_overrides: Whether to track prefab overrides
        
    Returns:
        Change record or None if no changes
    """
    component_changes: list[dict[str, Any]] = []
    property_changes: list[dict[str, Any]] = []
    
    # Check for prefab connection changes
    source_connected = source.get("isPrefabConnected", True)
    target_connected = target.get("isPrefabConnected", True)
    
    if source_connected != target_connected:
        property_changes.append({
            "property": "isPrefabConnected",
            "old_value": source_connected,
            "new_value": target_connected,
            "value_type": "bool",
        })
    
    # Compare basic properties
    basic_props = ["active", "layer", "tag", "static", "isStatic", "name"]
    for prop in basic_props:
        old_val = source.get(prop)
        new_val = target.get(prop)
        if old_val != new_val and (old_val is not None or new_val is not None):
            prop_change = {
                "property": prop,
                "old_value": old_val,
                "new_value": new_val,
                "value_type": type(new_val).__name__ if new_val is not None else "None",
            }
            if track_overrides:
                prop_change["is_override"] = True
            property_changes.append(prop_change)
    
    # Compare transform properties
    source_transform = source.get("transform", {})
    target_transform = target.get("transform", {})
    
    transform_props = ["position", "rotation", "scale", "localPosition", "localRotation", "localScale"]
    for prop in transform_props:
        old_val = source_transform.get(prop)
        new_val = target_transform.get(prop)
        if old_val != new_val and (old_val is not None or new_val is not None):
            prop_change = {
                "property": f"transform.{prop}",
                "old_value": old_val,
                "new_value": new_val,
                "value_type": "vector3" if isinstance(new_val, (list, tuple)) else type(new_val).__name__,
            }
            if track_overrides:
                prop_change["is_override"] = True
                prop_change["override_type"] = "transform"
            property_changes.append(prop_change)
    
    # Compare components
    source_components = {
        c.get("type", c.get("name", "Unknown")): c 
        for c in source.get("components", [])
    }
    target_components = {
        c.get("type", c.get("name", "Unknown")): c 
        for c in target.get("components", [])
    }
    
    all_component_types = set(source_components.keys()) | set(target_components.keys())
    
    for comp_type in sorted(all_component_types):
        source_comp = source_components.get(comp_type)
        target_comp = target_components.get(comp_type)
        
        if source_comp is None:
            comp_change = {
                "component_type": comp_type,
                "change_type": "added",
                "property_changes": [],
            }
            if track_overrides:
                comp_change["is_override"] = True
                comp_change["override_type"] = "added_component"
            component_changes.append(comp_change)
            
        elif target_comp is None:
            component_changes.append({
                "component_type": comp_type,
                "change_type": "removed",
                "property_changes": [],
            })
            
        else:
            # Compare component properties
            comp_prop_changes = _compare_component_properties(
                source_comp, target_comp, track_overrides
            )
            if comp_prop_changes:
                comp_change = {
                    "component_type": comp_type,
                    "change_type": "modified",
                    "property_changes": comp_prop_changes,
                }
                if track_overrides:
                    comp_change["is_override"] = any(
                        p.get("is_override") for p in comp_prop_changes
                    )
                component_changes.append(comp_change)
    
    if not component_changes and not property_changes:
        return None
        
    result: dict[str, Any] = {
        "path": path,
        "change_type": "modified",
        "component_changes": component_changes,
        "property_changes": property_changes,
    }
    
    if track_overrides:
        result["has_overrides"] = any(
            p.get("is_override") for p in property_changes
        ) or any(c.get("is_override") for c in component_changes)
    
    return result


def _compare_component_properties(
    source: dict[str, Any],
    target: dict[str, Any],
    track_overrides: bool = False,
) -> list[dict[str, Any]]:
    """Compare properties of two component instances."""
    changes: list[dict[str, Any]] = []
    
    # Get properties
    source_props = source.get("properties", source)
    target_props = target.get("properties", target)
    
    # Skip internal properties
    skip_keys = {"type", "name", "instanceID", "hideFlags", "tag"}
    
    all_keys = set(source_props.keys()) | set(target_props.keys())
    all_keys -= skip_keys
    
    for key in sorted(all_keys):
        old_val = source_props.get(key)
        new_val = target_props.get(key)
        
        if _values_differ(old_val, new_val):
            prop_change: dict[str, Any] = {
                "property": key,
                "old_value": old_val,
                "new_value": new_val,
                "value_type": _get_value_type(new_val),
            }
            if track_overrides:
                prop_change["is_override"] = True
            changes.append(prop_change)
    
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
        return "object"
    return type(value).__name__


def _generate_human_readable_summary(diff_result: dict[str, Any]) -> str:
    """Generate a human-readable summary of the diff."""
    summary = diff_result.get("summary", {})
    changes = diff_result.get("changes", [])
    
    lines = [
        "Prefab Diff Summary",
        "===================",
        f"Source: {diff_result.get('source', {}).get('path', 'Unknown')}",
        f"Target: {diff_result.get('target', {}).get('path', 'Unknown')}",
        "",
        f"Added:     {summary.get('added', 0)}",
        f"Removed:   {summary.get('removed', 0)}",
        f"Modified:  {summary.get('modified', 0)}",
    ]
    
    # Show override info if available
    if "overrides" in summary:
        lines.extend([
            "",
            "Override Summary",
            f"  Total Overrides: {summary['overrides'].get('total', 0)}",
            f"  Property Overrides: {summary['overrides'].get('properties', 0)}",
            f"  Component Overrides: {summary['overrides'].get('components', 0)}",
            f"  Added Objects: {summary['overrides'].get('added_objects', 0)}",
        ])
    
    lines.append("")
    
    # List changes by type
    added = [c for c in changes if c["change_type"] == "added"]
    removed = [c for c in changes if c["change_type"] == "removed"]
    modified = [c for c in changes if c["change_type"] == "modified"]
    
    if added:
        lines.append("Added Objects:")
        for change in added[:10]:
            override_mark = " [OVERRIDE]" if change.get("is_override") else ""
            lines.append(f"  + {change['path']}{override_mark}")
        if len(added) > 10:
            lines.append(f"  ... and {len(added) - 10} more")
        lines.append("")
        
    if removed:
        lines.append("Removed Objects:")
        for change in removed[:10]:
            lines.append(f"  - {change['path']}")
        if len(removed) > 10:
            lines.append(f"  ... and {len(removed) - 10} more")
        lines.append("")
        
    if modified:
        lines.append("Modified Objects:")
        for change in modified[:10]:
            comp_count = len(change.get("component_changes", []))
            prop_count = len(change.get("property_changes", []))
            override_mark = " [OVERRIDE]" if change.get("has_overrides") else ""
            lines.append(f"  ~ {change['path']} ({comp_count} component, {prop_count} property){override_mark}")
        if len(modified) > 10:
            lines.append(f"  ... and {len(modified) - 10} more")
        lines.append("")
    
    return "\n".join(lines)


@mcp_for_unity_tool(
    group="diff_patch",
    description=(
        "Compare Unity prefabs and generate structured diffs. "
        "Supports comparing prefab asset against instance, comparing two prefab variants, "
        "and showing prefab override information. "
        "Returns a structured diff that can be used for review, dry-run flows, and patch generation."
    ),
    annotations=ToolAnnotations(
        title="Diff Prefab",
        destructiveHint=False,
    ),
)
async def diff_prefab(
    ctx: Context,
    compare_mode: Annotated[
        Literal["asset_vs_instance", "two_prefabs", "show_overrides", "current_vs_saved", "checkpoint"],
        "Comparison mode: asset_vs_instance (prefab vs its instance), two_prefabs (compare two prefabs), show_overrides (list all overrides on an instance)"
    ],
    source_prefab: Annotated[
        str | None,
        "Source prefab path (e.g., 'Assets/Prefabs/MyPrefab.prefab') or instance GameObject path"
    ] = None,
    target_prefab: Annotated[
        str | None,
        "Target prefab path (for two_prefabs mode) or target instance (for asset_vs_instance)"
    ] = None,
    include_unchanged: Annotated[
        bool | str,
        "Include unchanged objects in the diff output"
    ] = False,
    show_override_details: Annotated[
        bool | str,
        "Include detailed override information (for show_overrides mode)"
    ] = True,
    prefab_path: Annotated[
        str | None,
        "Alias for source_prefab."
    ] = None,
    source_checkpoint_id: Annotated[
        str | None,
        "Optional checkpoint identifier for checkpoint comparisons."
    ] = None,
) -> dict[str, Any]:
    """
    Generate a structured diff between Unity prefabs.
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    # Preflight check
    gate = await maybe_run_tool_preflight(ctx, "diff_prefab", action="compare")
    if gate is not None:
        return gate.model_dump()
    
    # Normalize parameters
    include_unchanged_val = coerce_bool(include_unchanged, default=False)
    show_override_details_val = coerce_bool(show_override_details, default=True)
    effective_source_prefab = prefab_path or source_prefab
    compare_mode_aliases = {
        "current_vs_saved": "asset_vs_instance",
        "checkpoint": "two_prefabs",
    }
    effective_compare_mode = compare_mode_aliases.get(compare_mode, compare_mode)
    
    diff_id = _generate_diff_id()

    if not effective_source_prefab:
        return {
            "success": False,
            "message": "prefab_path or source_prefab is required",
            "diff_id": diff_id,
        }
    
    try:
        # Build request parameters
        params: dict[str, Any] = {
            "action": "get_prefab_data",
            "compareMode": effective_compare_mode,
            "sourcePrefab": effective_source_prefab,
            "includeMetadata": True,
        }
        
        if target_prefab:
            params["targetPrefab"] = target_prefab
        if source_checkpoint_id:
            params["sourceCheckpointId"] = source_checkpoint_id
        if show_override_details_val:
            params["showOverrideDetails"] = True

        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "diff_prefab",
            params
        )

        if not isinstance(response, dict) or not response.get("success"):
            error_msg = response.get("message", "Unknown error") if isinstance(response, dict) else str(response)
            return {
                "success": False,
                "message": f"Failed to get prefab data: {error_msg}",
                "diff_id": diff_id,
            }

        data = response.get("data", {})
        if not include_unchanged_val and isinstance(data.get("changes"), list):
            data = {
                **data,
                "changes": [c for c in data.get("changes", []) if c.get("change_type") != "unchanged"],
            }
        elif "changes" not in data:
            data = {
                **data,
                "changes": [],
            }

        return {
            "success": True,
            "message": response.get("message", "Prefab diff generated."),
            "data": {
                "diff_id": diff_id,
                **data,
            },
        }
        
    except Exception as exc:
        return {
            "success": False,
            "message": f"Error generating prefab diff: {exc!s}",
            "diff_id": diff_id,
        }
