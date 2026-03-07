"""
Scene comparison tool for generating structured diffs between Unity scenes.

Supports comparing:
- Active scene against saved version
- Two open scenes
- Scene at different checkpoints
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


def _compute_hash(data: Any) -> str:
    """Compute a hash for data comparison."""
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _compare_gameobjects(
    source_objects: list[dict[str, Any]],
    target_objects: list[dict[str, Any]],
    path_prefix: str = "",
) -> list[dict[str, Any]]:
    """
    Compare two lists of GameObjects and return change records.
    
    Args:
        source_objects: GameObjects from source scene
        target_objects: GameObjects from target scene
        path_prefix: Current path prefix for nested objects
        
    Returns:
        List of change records
    """
    changes: list[dict[str, Any]] = []
    
    # Index by path for O(1) lookup
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
            # Added in target
            changes.append({
                "path": path,
                "change_type": "added",
                "component_changes": [],
                "property_changes": [],
                "details": {
                    "name": target_obj.get("name"),
                    "active": target_obj.get("active", True),
                    "layer": target_obj.get("layer"),
                    "tag": target_obj.get("tag"),
                },
            })
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
            obj_changes = _compare_single_gameobject(source_obj, target_obj, path)
            if obj_changes:
                changes.append(obj_changes)
                
            # Recursively compare children
            source_children = source_obj.get("children", [])
            target_children = target_obj.get("children", [])
            if source_children or target_children:
                child_changes = _compare_gameobjects(source_children, target_children, path)
                changes.extend(child_changes)
    
    return changes


def _compare_single_gameobject(
    source: dict[str, Any],
    target: dict[str, Any],
    path: str,
) -> dict[str, Any] | None:
    """
    Compare two versions of the same GameObject.
    
    Args:
        source: Source GameObject data
        target: Target GameObject data
        path: Full path to the GameObject
        
    Returns:
        Change record or None if no changes
    """
    component_changes: list[dict[str, Any]] = []
    property_changes: list[dict[str, Any]] = []
    
    # Compare basic properties
    basic_props = ["active", "layer", "tag", "static", "isStatic"]
    for prop in basic_props:
        old_val = source.get(prop)
        new_val = target.get(prop)
        if old_val != new_val and (old_val is not None or new_val is not None):
            property_changes.append({
                "property": prop,
                "old_value": old_val,
                "new_value": new_val,
                "value_type": type(new_val).__name__ if new_val is not None else "None",
            })
    
    # Compare transform properties
    source_transform = source.get("transform", {})
    target_transform = target.get("transform", {})
    
    transform_props = ["position", "rotation", "scale", "localPosition", "localRotation", "localScale"]
    for prop in transform_props:
        old_val = source_transform.get(prop)
        new_val = target_transform.get(prop)
        if old_val != new_val and (old_val is not None or new_val is not None):
            property_changes.append({
                "property": f"transform.{prop}",
                "old_value": old_val,
                "new_value": new_val,
                "value_type": "vector3" if isinstance(new_val, (list, tuple)) else type(new_val).__name__,
            })
    
    # Compare components
    source_components = {c.get("type", c.get("name", "Unknown")): c for c in source.get("components", [])}
    target_components = {c.get("type", c.get("name", "Unknown")): c for c in target.get("components", [])}
    
    all_component_types = set(source_components.keys()) | set(target_components.keys())
    
    for comp_type in sorted(all_component_types):
        source_comp = source_components.get(comp_type)
        target_comp = target_components.get(comp_type)
        
        if source_comp is None:
            component_changes.append({
                "component_type": comp_type,
                "change_type": "added",
                "property_changes": [],
            })
        elif target_comp is None:
            component_changes.append({
                "component_type": comp_type,
                "change_type": "removed",
                "property_changes": [],
            })
        else:
            # Compare component properties
            comp_prop_changes = _compare_component_properties(source_comp, target_comp)
            if comp_prop_changes:
                component_changes.append({
                    "component_type": comp_type,
                    "change_type": "modified",
                    "property_changes": comp_prop_changes,
                })
    
    if not component_changes and not property_changes:
        return None
        
    return {
        "path": path,
        "change_type": "modified",
        "component_changes": component_changes,
        "property_changes": property_changes,
    }


def _compare_component_properties(
    source: dict[str, Any],
    target: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare properties of two component instances."""
    changes: list[dict[str, Any]] = []
    
    # Get properties (may be nested under "properties" or directly in the dict)
    source_props = source.get("properties", source)
    target_props = target.get("properties", target)
    
    # Skip internal/system properties
    skip_keys = {"type", "name", "instanceID", "hideFlags", "tag", "enabled"}
    
    all_keys = set(source_props.keys()) | set(target_props.keys())
    all_keys -= skip_keys
    
    for key in sorted(all_keys):
        old_val = source_props.get(key)
        new_val = target_props.get(key)
        
        if _values_differ(old_val, new_val):
            changes.append({
                "property": key,
                "old_value": old_val,
                "new_value": new_val,
                "value_type": _get_value_type(new_val),
            })
    
    return changes


def _values_differ(old: Any, new: Any) -> bool:
    """Check if two values are different, handling special cases."""
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
        "Scene Diff Summary",
        "==================",
        f"Source: {diff_result.get('source', {}).get('path', 'Unknown')}",
        f"Target: {diff_result.get('target', {}).get('path', 'Unknown')}",
        "",
        f"Added:     {summary.get('added', 0)}",
        f"Removed:   {summary.get('removed', 0)}",
        f"Modified:  {summary.get('modified', 0)}",
        f"Unchanged: {summary.get('unchanged', 0)}",
        "",
    ]
    
    # List changes by type
    added = [c for c in changes if c["change_type"] == "added"]
    removed = [c for c in changes if c["change_type"] == "removed"]
    modified = [c for c in changes if c["change_type"] == "modified"]
    
    if added:
        lines.append("Added Objects:")
        for change in added[:10]:  # Limit to first 10
            lines.append(f"  + {change['path']}")
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
            lines.append(f"  ~ {change['path']} ({comp_count} component, {prop_count} property changes)")
        if len(modified) > 10:
            lines.append(f"  ... and {len(modified) - 10} more")
        lines.append("")
    
    return "\n".join(lines)


@mcp_for_unity_tool(
    group="diff_patch",
    description=(
        "Compare Unity scenes and generate structured diffs. "
        "Supports comparing active scene against saved version, two open scenes, "
        "or scene states at different checkpoints. "
        "Returns a structured diff with hierarchy, component, and property changes "
        "that can be used for review, dry-run flows, and patch generation."
    ),
    annotations=ToolAnnotations(
        title="Diff Scene",
        destructiveHint=False,
    ),
)
async def diff_scene(
    ctx: Context,
    compare_mode: Annotated[
        Literal["active_vs_saved", "two_scenes", "checkpoint"],
        "Comparison mode: active_vs_saved (current vs disk), two_scenes (compare two open scenes), checkpoint (compare at checkpoints)"
    ],
    source_scene: Annotated[
        str | None,
        "Source scene path or name (for two_scenes mode, or checkpoint mode as base)"
    ] = None,
    target_scene: Annotated[
        str | None,
        "Target scene path or name (for two_scenes mode, or checkpoint mode as comparison)"
    ] = None,
    source_checkpoint_id: Annotated[
        str | None,
        "Checkpoint ID for source state (checkpoint mode)"
    ] = None,
    target_checkpoint_id: Annotated[
        str | None,
        "Checkpoint ID for target state (checkpoint mode)"
    ] = None,
    include_unchanged: Annotated[
        bool | str,
        "Include unchanged objects in the diff output"
    ] = False,
    max_depth: Annotated[
        int | str | None,
        "Maximum hierarchy depth to compare (default: unlimited)"
    ] = None,
) -> dict[str, Any]:
    """
    Generate a structured diff between Unity scenes.
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    # Preflight check
    gate = await maybe_run_tool_preflight(ctx, "diff_scene", action="compare")
    if gate is not None:
        return gate.model_dump()
    
    # Normalize parameters
    include_unchanged_val = coerce_bool(include_unchanged, default=False)
    max_depth_val = None
    if max_depth is not None:
        try:
            max_depth_val = int(max_depth)
        except (ValueError, TypeError):
            pass
    
    diff_id = _generate_diff_id()
    
    try:
        # Build request parameters
        params: dict[str, Any] = {
            "action": "get_scene_data",
            "compareMode": compare_mode,
            "includeMetadata": True,
        }
        
        if source_scene:
            params["sourceScene"] = source_scene
        if target_scene:
            params["targetScene"] = target_scene
        if source_checkpoint_id:
            params["sourceCheckpointId"] = source_checkpoint_id
        if target_checkpoint_id:
            params["targetCheckpointId"] = target_checkpoint_id
        if max_depth_val is not None:
            params["maxDepth"] = max_depth_val
            
        # Request scene data from Unity
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "diff_scene",
            params
        )
        
        if not isinstance(response, dict) or not response.get("success"):
            error_msg = response.get("message", "Unknown error") if isinstance(response, dict) else str(response)
            return {
                "success": False,
                "message": f"Failed to get scene data: {error_msg}",
                "diff_id": diff_id,
            }
        
        data = response.get("data", {})
        source_data = data.get("source", {})
        target_data = data.get("target", {})
        
        source_hierarchy = source_data.get("hierarchy", [])
        target_hierarchy = target_data.get("hierarchy", [])
        
        # Perform comparison
        changes = _compare_gameobjects(source_hierarchy, target_hierarchy)
        
        # Calculate summary
        added_count = sum(1 for c in changes if c["change_type"] == "added")
        removed_count = sum(1 for c in changes if c["change_type"] == "removed")
        modified_count = sum(1 for c in changes if c["change_type"] == "modified")
        
        # Count total objects in source for unchanged calculation
        def count_objects(objs: list[dict]) -> int:
            count = len(objs)
            for obj in objs:
                count += count_objects(obj.get("children", []))
            return count
            
        total_source = count_objects(source_hierarchy)
        unchanged_count = total_source - removed_count - modified_count if not include_unchanged_val else 0
        
        # Filter out unchanged if not requested
        if not include_unchanged_val:
            changes = [c for c in changes if c["change_type"] != "unchanged"]
        
        # Build result
        result = {
            "diff_id": diff_id,
            "source": {
                "type": "scene",
                "path": source_data.get("path") or source_scene or "Active Scene",
                "name": source_data.get("name"),
            },
            "target": {
                "type": "scene",
                "path": target_data.get("path") or target_scene or "Saved/Checkpoint",
                "name": target_data.get("name"),
            },
            "summary": {
                "added": added_count,
                "removed": removed_count,
                "modified": modified_count,
                "unchanged": unchanged_count,
            },
            "changes": changes,
        }
        
        # Add human-readable summary
        result["human_readable"] = _generate_human_readable_summary(result)
        
        return {
            "success": True,
            "message": f"Scene diff generated: {added_count} added, {removed_count} removed, {modified_count} modified",
            "data": result,
        }
        
    except Exception as exc:
        return {
            "success": False,
            "message": f"Error generating scene diff: {exc!s}",
            "diff_id": diff_id,
        }
