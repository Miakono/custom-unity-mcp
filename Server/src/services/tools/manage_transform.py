"""
Transform management tool for Unity GameObjects.

Provides operations for getting/setting world and local transforms,
bounds queries, alignment, distribution, and placement validation.
Part of the 'spatial' tool group for advanced scene construction.
"""
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry
from services.tools.utils import (
    coerce_bool,
    coerce_float,
    normalize_vector3,
    normalize_string_list,
)


@mcp_for_unity_tool(
    name="manage_transform",
    description=(
        "Advanced transform operations for GameObjects including world/local space queries, "
        "bounds retrieval, grid snapping, alignment, distribution, and placement validation. "
        "Complements manage_gameobject by focusing purely on spatial manipulation."
    ),
    annotations=ToolAnnotations(
        title="Manage Transform",
        destructiveHint=True,
    ),
    group="spatial",
)
async def manage_transform(
    ctx: Context,
    action: Annotated[
        Literal[
            "get_world_transform",
            "get_local_transform",
            "set_world_transform",
            "set_local_transform",
            "get_bounds",
            "snap_to_grid",
            "align_to_object",
            "distribute_objects",
            "place_relative",
            "validate_placement",
        ],
        "Transform action to perform",
    ],
    target: Annotated[
        str | None,
        "Target GameObject identifier (name, path, instance ID, or null for selected)"
    ] = None,
    search_method: Annotated[
        Literal["by_id", "by_name", "by_path", "by_tag", "by_layer", "by_component"],
        "How to resolve 'target' if provided as string"
    ] = "by_name",
    # Transform data parameters
    position: Annotated[
        list[float] | dict[str, float] | str | None,
        "Position as [x, y, z] array, {x, y, z} object, or JSON string"
    ] = None,
    rotation: Annotated[
        list[float] | dict[str, float] | str | None,
        "Rotation as [x, y, z] euler angles array, {x, y, z} object, or JSON string"
    ] = None,
    scale: Annotated[
        list[float] | dict[str, float] | str | None,
        "Scale as [x, y, z] array, {x, y, z} object, or JSON string"
    ] = None,
    # Grid snapping parameters
    grid_size: Annotated[
        float | str | None,
        "Grid size for snap_to_grid (default: 1.0)"
    ] = None,
    snap_position: Annotated[
        bool | str | None,
        "Whether to snap position (default: True)"
    ] = None,
    snap_rotation: Annotated[
        bool | str | None,
        "Whether to snap rotation to 90-degree increments (default: False)"
    ] = None,
    # Alignment parameters
    reference_object: Annotated[
        str | None,
        "Reference GameObject for alignment operations"
    ] = None,
    align_axis: Annotated[
        Literal["x", "y", "z", "all"],
        "Axis to align (default: all)"
    ] = "all",
    align_mode: Annotated[
        Literal["min", "max", "center", "pivot"],
        "Alignment mode: align to min bounds, max bounds, center, or pivot (default: center)"
    ] = "center",
    # Distribution parameters
    targets: Annotated[
        list[str] | str | None,
        "List of target GameObject identifiers for distribute_objects"
    ] = None,
    distribute_axis: Annotated[
        Literal["x", "y", "z"],
        "Axis for distribution (default: x)"
    ] = "x",
    distribute_spacing: Annotated[
        float | str | None,
        "Spacing between objects for distribution (default: auto-calculate)"
    ] = None,
    # Relative placement parameters
    offset: Annotated[
        list[float] | dict[str, float] | str | None,
        "Offset vector for place_relative as [x, y, z]"
    ] = None,
    direction: Annotated[
        Literal[
            "left", "right", "up", "down", "forward", "back",
            "front", "backward", "behind", "above", "below",
            "north", "south", "east", "west"
        ],
        "Cardinal direction for relative placement"
    ] = None,
    distance: Annotated[
        float | str | None,
        "Distance in the specified direction (default: 1.0)"
    ] = None,
    use_world_space: Annotated[
        bool | str | None,
        "Use world space directions (default: True) or reference object's local space"
    ] = None,
    # Validation parameters
    check_overlap: Annotated[
        bool | str | None,
        "Check for overlapping objects in validate_placement (default: True)"
    ] = None,
    check_off_grid: Annotated[
        bool | str | None,
        "Check if position is off-grid in validate_placement (default: True)"
    ] = None,
    check_invalid_scale: Annotated[
        bool | str | None,
        "Check for invalid (zero/negative) scale in validate_placement (default: True)"
    ] = None,
    min_spacing: Annotated[
        float | str | None,
        "Minimum spacing required between objects for overlap check (default: 0.0)"
    ] = None,
) -> dict[str, Any]:
    """
    Perform advanced transform operations on GameObjects.

    Actions:
    - get_world_transform: Get world-space position, rotation, and scale
    - get_local_transform: Get local-space position, rotation, and scale
    - set_world_transform: Set world-space transform (position, rotation, scale)
    - set_local_transform: Set local-space transform
    - get_bounds: Get renderer/collider bounds (center, extents, min, max)
    - snap_to_grid: Snap object position/rotation to grid
    - align_to_object: Align to another object by bounds or pivot
    - distribute_objects: Evenly distribute multiple objects along an axis
    - place_relative: Place object relative to another with offset/direction
    - validate_placement: Check for off-grid, overlap, and invalid scale
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    gate = await maybe_run_tool_preflight(ctx, "manage_transform")
    if gate is not None:
        return gate.model_dump()

    # Validate required parameters
    if action is None:
        return {
            "success": False,
            "message": "Missing required parameter 'action'. Valid actions: get_world_transform, get_local_transform, "
                      "set_world_transform, set_local_transform, get_bounds, snap_to_grid, align_to_object, "
                      "distribute_objects, place_relative, validate_placement"
        }

    # Normalize vector parameters
    position, pos_error = normalize_vector3(position, "position")
    if pos_error:
        return {"success": False, "message": pos_error}

    rotation, rot_error = normalize_vector3(rotation, "rotation")
    if rot_error:
        return {"success": False, "message": rot_error}

    scale, scale_error = normalize_vector3(scale, "scale")
    if scale_error:
        return {"success": False, "message": scale_error}

    offset, offset_error = normalize_vector3(offset, "offset")
    if offset_error:
        return {"success": False, "message": offset_error}

    # Normalize boolean parameters
    snap_position = coerce_bool(snap_position, default=True)
    snap_rotation = coerce_bool(snap_rotation, default=False)
    use_world_space = coerce_bool(use_world_space, default=True)
    check_overlap = coerce_bool(check_overlap, default=True)
    check_off_grid = coerce_bool(check_off_grid, default=True)
    check_invalid_scale = coerce_bool(check_invalid_scale, default=True)

    # Normalize float parameters
    grid_size = coerce_float(grid_size, default=1.0)
    distribute_spacing = coerce_float(distribute_spacing)
    distance = coerce_float(distance, default=1.0)
    min_spacing = coerce_float(min_spacing, default=0.0)

    # Normalize targets list for distribute_objects
    targets_list, targets_error = normalize_string_list(targets, "targets")
    if targets_error:
        return {"success": False, "message": targets_error}

    try:
        params = {
            "action": action,
            "target": target,
            "searchMethod": search_method,
            "position": position,
            "rotation": rotation,
            "scale": scale,
            "gridSize": grid_size,
            "snapPosition": snap_position,
            "snapRotation": snap_rotation,
            "referenceObject": reference_object,
            "alignAxis": align_axis,
            "alignMode": align_mode,
            "targets": targets_list,
            "distributeAxis": distribute_axis,
            "distributeSpacing": distribute_spacing,
            "offset": offset,
            "direction": direction,
            "distance": distance,
            "useWorldSpace": use_world_space,
            "checkOverlap": check_overlap,
            "checkOffGrid": check_off_grid,
            "checkInvalidScale": check_invalid_scale,
            "minSpacing": min_spacing,
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_transform",
            params,
        )

        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Transform operation '{action}' completed successfully."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}

    except Exception as e:
        return {"success": False, "message": f"Python error in manage_transform: {e!s}"}
