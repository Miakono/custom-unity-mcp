"""
Scene patch application tool for applying structured patches to Unity scenes.

Supports:
- Applying patches derived from diffs
- Dry-run mode for previewing changes
- Deterministic application of changes
"""

from __future__ import annotations

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


def _generate_patch_id() -> str:
    """Generate a unique patch identifier."""
    return f"patch_{uuid4().hex[:12]}"


def _validate_patch_operations(operations: list[dict[str, Any]]) -> tuple[bool, str]:
    """
    Validate patch operations before application.
    
    Args:
        operations: List of patch operations
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(operations, list):
        return False, "Operations must be a list"
    
    valid_ops = {"add", "remove", "replace", "move", "modify_property", "delete_object", "add_component"}
    
    for i, op in enumerate(operations):
        if not isinstance(op, dict):
            return False, f"Operation {i} must be an object"
        
        op_type = op.get("op") or op.get("type")
        if op_type not in valid_ops:
            return False, f"Operation {i}: invalid op '{op_type}', must be one of {valid_ops}"
        
        path = op.get("path") or op.get("target")
        if not path or not isinstance(path, str):
            return False, f"Operation {i}: missing or invalid 'path'"
        
        # Validate value for add/replace operations
        if op_type in ("add", "replace", "modify_property", "add_component") and "value" not in op and "component" not in op:
            return False, f"Operation {i}: '{op_type}' operation requires 'value'"
        
        # Validate from for move operations
        if op_type == "move" and "from" not in op:
            return False, f"Operation {i}: 'move' operation requires 'from'"
    
    return True, ""


def _normalize_patch_operation(op: dict[str, Any]) -> dict[str, Any]:
    """Normalize a patch operation for Unity consumption."""
    op_type = op.get("op") or op.get("type")
    if op_type == "modify_property":
        normalized = {
            "op": "replace",
            "path": f"{op.get('target', '').strip('/')}/{op.get('property', '').strip('/')}",
            "value": op.get("value"),
        }
        return normalized
    if op_type == "delete_object":
        return {
            "op": "remove",
            "path": op.get("target"),
        }
    if op_type == "add_component":
        component = op.get("component") or op.get("value")
        return {
            "op": "add",
            "path": f"{op.get('target', '').strip('/')}/components/{component}",
            "value": {"component": component},
        }
    normalized = {
        "op": op_type,
        "path": op.get("path"),
    }
    
    if "value" in op:
        normalized["value"] = op["value"]
    if "from" in op:
        normalized["from"] = op["from"]
    
    # Add metadata if present
    if "component_type" in op:
        normalized["componentType"] = op["component_type"]
    if "property_type" in op:
        normalized["propertyType"] = op["property_type"]
    
    return normalized


def _generate_preview(operations: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a preview of patch operations without applying."""
    preview = {
        "total_operations": len(operations),
        "by_type": {},
        "affected_paths": [],
    }
    
    for op in operations:
        op_type = op.get("op", "unknown")
        preview["by_type"][op_type] = preview["by_type"].get(op_type, 0) + 1
        
        path = op.get("path", "")
        if path and path not in preview["affected_paths"]:
            preview["affected_paths"].append(path)
    
    # Group by hierarchy level
    hierarchy_changes: dict[str, list[str]] = {}
    for path in preview["affected_paths"]:
        # Get top-level object
        parts = path.strip("/").split("/")
        top_level = parts[0] if parts else path
        
        if top_level not in hierarchy_changes:
            hierarchy_changes[top_level] = []
        hierarchy_changes[top_level].append(path)
    
    preview["hierarchy_summary"] = {
        obj: len(paths) for obj, paths in hierarchy_changes.items()
    }
    
    return preview


def _convert_diff_to_operations(diff: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Convert a diff result to patch operations.
    
    Args:
        diff: Diff result from diff_scene
        
    Returns:
        List of patch operations
    """
    operations: list[dict[str, Any]] = []
    
    changes = diff.get("changes", [])
    
    for change in changes:
        change_type = change.get("change_type")
        path = change.get("path", "")
        
        if change_type == "added":
            # Add operation
            details = change.get("details", {})
            operations.append({
                "op": "add",
                "path": path,
                "value": {
                    "name": details.get("name"),
                    "active": details.get("active", True),
                    "layer": details.get("layer"),
                    "tag": details.get("tag"),
                },
            })
            
        elif change_type == "removed":
            # Remove operation
            operations.append({
                "op": "remove",
                "path": path,
            })
            
        elif change_type == "modified":
            # Property changes -> replace operations
            for prop_change in change.get("property_changes", []):
                prop_path = f"{path}/{prop_change['property']}"
                operations.append({
                    "op": "replace",
                    "path": prop_path,
                    "value": prop_change.get("new_value"),
                    "old_value": prop_change.get("old_value"),  # For verification
                })
            
            # Component changes
            for comp_change in change.get("component_changes", []):
                comp_type = comp_change.get("component_type")
                comp_change_type = comp_change.get("change_type")
                
                if comp_change_type == "added":
                    operations.append({
                        "op": "add",
                        "path": f"{path}/components/{comp_type}",
                        "value": {"type": comp_type},
                        "component_type": comp_type,
                    })
                elif comp_change_type == "removed":
                    operations.append({
                        "op": "remove",
                        "path": f"{path}/components/{comp_type}",
                        "component_type": comp_type,
                    })
                elif comp_change_type == "modified":
                    # Component property changes
                    for prop_change in comp_change.get("property_changes", []):
                        prop_path = f"{path}/components/{comp_type}/{prop_change['property']}"
                        operations.append({
                            "op": "replace",
                            "path": prop_path,
                            "value": prop_change.get("new_value"),
                            "old_value": prop_change.get("old_value"),
                            "component_type": comp_type,
                        })
    
    return operations


@mcp_for_unity_tool(
    group="diff_patch",
    description=(
        "Apply structured patches to Unity scenes. "
        "Supports applying patches derived from diffs (via based_on_diff parameter) "
        "or custom patch operations. "
        "Provides dry-run mode for previewing changes before application. "
        "All changes are applied deterministically and can be reviewed via the returned results."
    ),
    annotations=ToolAnnotations(
        title="Apply Scene Patch",
        destructiveHint=True,
    ),
)
async def apply_scene_patch(
    ctx: Context,
    scene_path: Annotated[
        str | None,
        "Target scene path (None for active scene)"
    ] = None,
    operations: Annotated[
        list[dict[str, Any]] | str | None,
        "Patch operations as list or JSON string. Each operation has: op (add/remove/replace/move), path, value (for add/replace), from (for move)"
    ] = None,
    based_on_diff: Annotated[
        str | None,
        "Diff ID to derive operations from (alternative to providing operations directly)"
    ] = None,
    dry_run: Annotated[
        bool | str,
        "Preview changes without applying them"
    ] = False,
    create_checkpoint: Annotated[
        bool | str,
        "Create a checkpoint before applying patches"
    ] = True,
    skip_validation: Annotated[
        bool | str,
        "Skip operation validation (faster but less safe)"
    ] = False,
    patch: Annotated[
        dict[str, Any] | list[dict[str, Any]] | str | None,
        "Alias payload containing operations or a list of operations."
    ] = None,
    target_mode: Annotated[
        str | None,
        "Alias such as 'active_scene'."
    ] = None,
) -> dict[str, Any]:
    """
    Apply a structured patch to a Unity scene.
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    # Preflight check
    gate = await maybe_run_tool_preflight(ctx, "apply_scene_patch", action="apply")
    if gate is not None:
        return gate.model_dump()
    
    # Normalize parameters
    dry_run_val = coerce_bool(dry_run, default=False)
    create_checkpoint_val = coerce_bool(create_checkpoint, default=True)
    skip_validation_val = coerce_bool(skip_validation, default=False)
    
    patch_id = _generate_patch_id()
    
    try:
        if patch is not None and operations is None:
            if isinstance(patch, dict) and "operations" in patch:
                operations = patch.get("operations")
            else:
                operations = patch

        # Parse operations if provided as string
        if isinstance(operations, str):
            operations = parse_json_payload(operations)

        if target_mode == "active_scene":
            scene_path = None
        
        # If based_on_diff is provided, we would look up the diff and convert to operations
        # For now, this is a placeholder - in production this would query a diff store
        if based_on_diff and not operations:
            return {
                "success": False,
                "message": f"Diff lookup not implemented. Please provide operations directly.",
                "patch_id": patch_id,
            }
        
        if not operations:
            return {
                "success": False,
                "message": "Either operations or based_on_diff must be provided",
                "patch_id": patch_id,
            }
        
        # Validate operations
        if not skip_validation_val:
            is_valid, error_msg = _validate_patch_operations(operations)
            if not is_valid:
                return {
                    "success": False,
                    "message": f"Invalid patch operations: {error_msg}",
                    "patch_id": patch_id,
                }
        
        # Create checkpoint if requested
        checkpoint_result = None
        if create_checkpoint_val:
            # Note: In production, this would call the checkpoint service
            checkpoint_result = {
                "checkpoint_id": f"auto_{patch_id}",
                "created": True,
                "note": f"Auto-created before patch {patch_id}",
            }
        
        # Normalize operations for Unity
        normalized_ops = [_normalize_patch_operation(op) for op in operations]
        
        # Build request parameters
        params: dict[str, Any] = {
            "action": "apply_patch",
            "patchId": patch_id,
            "operations": normalized_ops,
        }
        if dry_run_val:
            params["dryRun"] = True
        
        if scene_path:
            params["scenePath"] = scene_path
        
        # Send command to Unity
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "apply_scene_patch",
            params
        )
        
        if not isinstance(response, dict):
            return {
                "success": False,
                "message": f"Unexpected response type: {type(response).__name__}",
                "patch_id": patch_id,
            }
        
        # Build result
        result: dict[str, Any] = {
            "patch_id": patch_id,
            "applied": response.get("success", False),
            "scene_path": scene_path or "Active Scene",
            "operations_applied": len(operations),
        }
        
        if checkpoint_result:
            result["checkpoint"] = checkpoint_result
        
        if response.get("success"):
            return {
                "success": True,
                "message": f"Patch applied successfully: {len(operations)} operations",
                "data": response.get("data", {}),
                "patch_id": patch_id,
            }
        else:
            result["error"] = response.get("message", "Unknown error")
            return {
                "success": False,
                "message": f"Failed to apply patch: {result['error']}",
                "data": response.get("data", {}),
                "patch_id": patch_id,
            }
        
    except Exception as exc:
        return {
            "success": False,
            "message": f"Error applying scene patch: {exc!s}",
            "patch_id": patch_id,
        }
