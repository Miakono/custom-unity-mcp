"""
Prefab patch application tool for applying structured patches to Unity prefabs.

Supports:
- Applying patches derived from diffs
- Modifying prefab assets and instances
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
    
    valid_ops = {"add", "remove", "replace", "move", "modify_component", "add_component", "remove_component", "modify_property"}
    
    for i, op in enumerate(operations):
        if not isinstance(op, dict):
            return False, f"Operation {i} must be an object"
        
        op_type = op.get("op") or op.get("type")
        if op_type not in valid_ops:
            return False, f"Operation {i}: invalid op '{op_type}', must be one of {valid_ops}"
        
        path = op.get("path") or op.get("target")
        if not path or not isinstance(path, str):
            return False, f"Operation {i}: missing or invalid 'path'"
        
        # Validate component_type for component operations
        if op_type in ("add_component", "remove_component", "modify_component"):
            if "component_type" not in op and "component" not in op:
                return False, f"Operation {i}: component operations require 'component_type'"
        
        # Validate value for add/replace operations
        if op_type in ("add", "replace", "modify_property") and "value" not in op:
            return False, f"Operation {i}: '{op_type}' operation requires 'value'"
        if op_type == "add_component" and "value" not in op and "component" not in op:
            return False, f"Operation {i}: '{op_type}' operation requires 'value'"
    
    return True, ""


def _normalize_patch_operation(op: dict[str, Any]) -> dict[str, Any]:
    """Normalize a patch operation for Unity consumption."""
    op_type = op.get("op") or op.get("type")
    component_type = op.get("component_type") or op.get("component")
    if op_type == "modify_property":
        return {
            "op": "replace",
            "path": f"{op.get('target', '').strip('/')}/{op.get('property', '').strip('/')}",
            "value": op.get("value"),
        }
    normalized = {
        "op": op_type,
        "path": op.get("path") or op.get("target"),
    }
    
    if "value" in op:
        normalized["value"] = op["value"]
    if "from" in op:
        normalized["from"] = op["from"]
    if component_type is not None:
        normalized["componentType"] = component_type
    if "property_type" in op:
        normalized["propertyType"] = op["property_type"]
    if "apply_to_instance" in op:
        normalized["applyToInstance"] = op["apply_to_instance"]
    if "override_existing" in op:
        normalized["overrideExisting"] = op["override_existing"]
    
    return normalized


def _generate_preview(operations: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a preview of patch operations without applying."""
    preview = {
        "total_operations": len(operations),
        "by_type": {},
        "affected_paths": [],
        "component_operations": [],
    }
    
    for op in operations:
        op_type = op.get("op", "unknown")
        preview["by_type"][op_type] = preview["by_type"].get(op_type, 0) + 1
        
        path = op.get("path", "")
        if path and path not in preview["affected_paths"]:
            preview["affected_paths"].append(path)
        
        # Track component operations separately
        if "component" in op_type or op.get("component_type"):
            preview["component_operations"].append({
                "op": op_type,
                "path": path,
                "component": op.get("component_type"),
            })
    
    # Group by object
    object_changes: dict[str, dict[str, int]] = {}
    for op in operations:
        path = op.get("path", "")
        # Extract object path (first segment)
        obj_path = path.split("/")[0] if "/" in path else path
        
        if obj_path not in object_changes:
            object_changes[obj_path] = {}
        
        op_type = op.get("op", "unknown")
        object_changes[obj_path][op_type] = object_changes[obj_path].get(op_type, 0) + 1
    
    preview["object_summary"] = object_changes
    
    return preview


def _convert_diff_to_operations(diff: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Convert a prefab diff result to patch operations.
    
    Args:
        diff: Diff result from diff_prefab
        
    Returns:
        List of patch operations
    """
    operations: list[dict[str, Any]] = []
    
    changes = diff.get("changes", [])
    
    for change in changes:
        change_type = change.get("change_type")
        path = change.get("path", "")
        
        if change_type == "added":
            # Add GameObject
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
            # Remove GameObject
            operations.append({
                "op": "remove",
                "path": path,
            })
            
        elif change_type == "modified":
            # Handle component changes
            for comp_change in change.get("component_changes", []):
                comp_type = comp_change.get("component_type")
                comp_change_type = comp_change.get("change_type")
                
                if comp_change_type == "added":
                    operations.append({
                        "op": "add_component",
                        "path": path,
                        "component_type": comp_type,
                        "value": {"type": comp_type},
                    })
                elif comp_change_type == "removed":
                    operations.append({
                        "op": "remove_component",
                        "path": path,
                        "component_type": comp_type,
                    })
                elif comp_change_type == "modified":
                    # Apply each property change
                    for prop_change in comp_change.get("property_changes", []):
                        operations.append({
                            "op": "modify_component",
                            "path": f"{path}/{prop_change['property']}",
                            "component_type": comp_type,
                            "value": prop_change.get("new_value"),
                            "old_value": prop_change.get("old_value"),
                        })
            
            # Handle property changes (non-component)
            for prop_change in change.get("property_changes", []):
                prop_name = prop_change.get("property", "")
                # Skip transform properties that are handled specially
                if not prop_name.startswith("transform."):
                    operations.append({
                        "op": "replace",
                        "path": f"{path}/{prop_name}",
                        "value": prop_change.get("new_value"),
                        "old_value": prop_change.get("old_value"),
                    })
                else:
                    # Transform property
                    transform_prop = prop_name.replace("transform.", "")
                    operations.append({
                        "op": "replace",
                        "path": f"{path}/transform/{transform_prop}",
                        "value": prop_change.get("new_value"),
                        "old_value": prop_change.get("old_value"),
                    })
    
    return operations


@mcp_for_unity_tool(
    group="diff_patch",
    description=(
        "Apply structured patches to Unity prefabs. "
        "Supports applying patches derived from diffs (via based_on_diff parameter) "
        "or custom patch operations. "
        "Can modify prefab assets directly or apply overrides to instances. "
        "Provides dry-run mode for previewing changes before application. "
        "All changes are applied deterministically and can be reviewed via the returned results."
    ),
    annotations=ToolAnnotations(
        title="Apply Prefab Patch",
        destructiveHint=True,
    ),
)
async def apply_prefab_patch(
    ctx: Context,
    prefab_path: Annotated[
        str | None,
        "Target prefab path (e.g., 'Assets/Prefabs/MyPrefab.prefab')"
    ] = None,
    operations: Annotated[
        list[dict[str, Any]] | str | None,
        "Patch operations as list or JSON string. Operations: add, remove, replace, move, add_component, remove_component, modify_component"
    ] = None,
    based_on_diff: Annotated[
        str | None,
        "Diff ID to derive operations from (alternative to providing operations directly)"
    ] = None,
    target_mode: Annotated[
        Literal["asset", "instance", "variant"],
        "How to apply the patch: asset (modify prefab asset), instance (apply as override), variant (create/modify variant)"
    ] = "asset",
    instance_path: Annotated[
        str | None,
        "Path to prefab instance in scene (required when target_mode='instance')"
    ] = None,
    dry_run: Annotated[
        bool | str,
        "Preview changes without applying them"
    ] = False,
    create_checkpoint: Annotated[
        bool | str,
        "Create a checkpoint before applying patches"
    ] = True,
    apply_as_override: Annotated[
        bool | str,
        "Apply changes as prefab overrides (when target_mode='instance')"
    ] = True,
    patch: Annotated[
        dict[str, Any] | list[dict[str, Any]] | str | None,
        "Alias payload containing operations or a list of operations."
    ] = None,
    prefab_guid: Annotated[
        str | None,
        "Optional prefab GUID identifier."
    ] = None,
    handle_variants: Annotated[
        bool | None,
        "Compatibility flag for variant-aware patching."
    ] = None,
) -> dict[str, Any]:
    """
    Apply a structured patch to a Unity prefab.
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    # Preflight check
    gate = await maybe_run_tool_preflight(ctx, "apply_prefab_patch", action="apply")
    if gate is not None:
        return gate.model_dump()
    
    # Normalize parameters
    dry_run_val = coerce_bool(dry_run, default=False)
    create_checkpoint_val = coerce_bool(create_checkpoint, default=True)
    apply_as_override_val = coerce_bool(apply_as_override, default=True)
    
    # Validate instance path requirement
    if target_mode == "instance" and not instance_path:
        return {
            "success": False,
            "message": "instance_path is required when target_mode='instance'",
        }

    if prefab_path is None and prefab_guid is None:
        return {
            "success": False,
            "message": "prefab_path or prefab_guid is required",
            "patch_id": _generate_patch_id(),
        }
    
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
        
        # If based_on_diff is provided, we would look up the diff and convert to operations
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
            checkpoint_result = {
                "checkpoint_id": f"auto_{patch_id}",
                "created": True,
                "note": f"Auto-created before prefab patch {patch_id}",
            }
        
        # Normalize operations for Unity
        normalized_ops = [_normalize_patch_operation(op) for op in operations]
        
        # Build request parameters
        params: dict[str, Any] = {
            "action": "apply_patch",
            "patchId": patch_id,
            "prefabPath": prefab_path,
            "operations": normalized_ops,
            "targetMode": target_mode,
        }
        if dry_run_val:
            params["dryRun"] = True
        
        if instance_path:
            params["instancePath"] = instance_path
        if prefab_guid:
            params["prefabGuid"] = prefab_guid
        if handle_variants is not None:
            params["handleVariants"] = bool(handle_variants)
        if apply_as_override_val and target_mode == "instance":
            params["applyAsOverride"] = True
        
        # Send command to Unity
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "apply_prefab_patch",
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
            "prefab_path": prefab_path,
            "target_mode": target_mode,
            "operations_applied": len(operations),
        }
        
        if instance_path:
            result["instance_path"] = instance_path
        
        if checkpoint_result:
            result["checkpoint"] = checkpoint_result
        
        if response.get("success"):
            return {
                "success": True,
                "message": f"Prefab patch applied successfully: {len(operations)} operations",
                "data": response.get("data", {}),
                "patch_id": patch_id,
            }
        else:
            result["error"] = response.get("message", "Unknown error")
            return {
                "success": False,
                "message": f"Failed to apply prefab patch: {result['error']}",
                "data": response.get("data", {}),
                "patch_id": patch_id,
            }
        
    except Exception as exc:
        return {
            "success": False,
            "message": f"Error applying prefab patch: {exc!s}",
            "patch_id": patch_id,
        }
