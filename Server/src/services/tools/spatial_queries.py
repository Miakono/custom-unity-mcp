"""
Spatial query tool for Unity scenes.

Provides operations for finding objects by spatial relationships:
nearest neighbor, radius/box queries, overlap checks, raycasting,
distance/direction calculations, and relative offsets.
Part of the 'spatial' tool group for scene analysis and construction.
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
    coerce_int,
    normalize_vector3,
    normalize_string_list,
)


@mcp_for_unity_tool(
    name="spatial_queries",
    description=(
        "Spatial queries for Unity scenes: find nearest objects, objects within radius/box, "
        "overlap checks, raycasting, distance/direction calculations, and relative offsets. "
        "Enables agents to reason about spatial relationships without blind coordinate edits."
    ),
    annotations=ToolAnnotations(
        title="Spatial Queries",
        destructiveHint=False,
    ),
    group="spatial",
)
async def spatial_queries(
    ctx: Context,
    action: Annotated[
        Literal[
            "nearest_object",
            "objects_in_radius",
            "objects_in_box",
            "overlap_check",
            "raycast",
            "get_distance",
            "get_direction",
            "get_relative_offset",
        ],
        "Spatial query action to perform",
    ],
    # Source/target objects
    source: Annotated[
        str | None,
        "Source GameObject identifier (name, path, instance ID) or 'selected' for current selection"
    ] = None,
    target: Annotated[
        str | None,
        "Target GameObject identifier for distance/direction/offset queries"
    ] = None,
    search_method: Annotated[
        Literal["by_id", "by_name", "by_path", "by_tag", "by_layer", "by_component"],
        "How to resolve GameObject identifiers"
    ] = "by_name",
    # Point/position parameters
    point: Annotated[
        list[float] | dict[str, float] | str | None,
        "World point as [x, y, z] for queries from a specific position"
    ] = None,
    # Query filter parameters
    filter_by_tag: Annotated[
        str | None,
        "Filter results by tag name"
    ] = None,
    filter_by_layer: Annotated[
        str | None,
        "Filter results by layer name"
    ] = None,
    filter_by_component: Annotated[
        str | None,
        "Filter results by component type name"
    ] = None,
    exclude_inactive: Annotated[
        bool | str | None,
        "Exclude inactive GameObjects from results (default: True)"
    ] = None,
    # Radius query parameters
    radius: Annotated[
        float | str | None,
        "Radius for sphere query (default: 10.0)"
    ] = None,
    max_results: Annotated[
        int | str | None,
        "Maximum number of results to return (default: 50)"
    ] = None,
    # Box query parameters
    box_center: Annotated[
        list[float] | dict[str, float] | str | None,
        "Center of query box as [x, y, z]"
    ] = None,
    box_size: Annotated[
        list[float] | dict[str, float] | str | None,
        "Size of query box as [x, y, z]"
    ] = None,
    # Overlap check parameters
    object_to_place: Annotated[
        str | None,
        "Object identifier for overlap check (the object that would be placed)"
    ] = None,
    placement_position: Annotated[
        list[float] | dict[str, float] | str | None,
        "Position where object would be placed for overlap check"
    ] = None,
    rotation_at_placement: Annotated[
        list[float] | dict[str, float] | str | None,
        "Rotation at placement for overlap check"
    ] = None,
    scale_at_placement: Annotated[
        list[float] | dict[str, float] | str | None,
        "Scale at placement for overlap check"
    ] = None,
    min_clearance: Annotated[
        float | str | None,
        "Minimum clearance distance for overlap check (default: 0.0)"
    ] = None,
    # Raycast parameters
    origin: Annotated[
        list[float] | dict[str, float] | str | None,
        "Ray origin as [x, y, z]"
    ] = None,
    direction: Annotated[
        list[float] | dict[str, float] | str | None,
        "Ray direction as [x, y, z] (will be normalized)"
    ] = None,
    max_distance: Annotated[
        float | str | None,
        "Maximum raycast distance (default: 1000.0)"
    ] = None,
    layer_mask: Annotated[
        str | None,
        "Layer mask names comma-separated (e.g., 'Default,Obstacles')"
    ] = None,
    # Offset parameters
    offset_type: Annotated[
        Literal["position", "bounds_center", "bounds_min", "bounds_max", "pivot"],
        "Type of offset to calculate (default: position)"
    ] = "position",
) -> dict[str, Any]:
    """
    Perform spatial queries on Unity scenes and GameObjects.

    Actions:
    - nearest_object: Find the nearest object to a source object or point
    - objects_in_radius: Find all objects within a spherical radius
    - objects_in_box: Find all objects within a bounding box
    - overlap_check: Check if placing an object would cause overlaps
    - raycast: Cast a ray and return hit information
    - get_distance: Get distance between two objects or points
    - get_direction: Get direction vector between two objects
    - get_relative_offset: Get offset from one object to another
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    gate = await maybe_run_tool_preflight(ctx, "spatial_queries")
    if gate is not None:
        return gate.model_dump()

    # Validate required parameters
    if action is None:
        return {
            "success": False,
            "message": "Missing required parameter 'action'. Valid actions: nearest_object, "
                      "objects_in_radius, objects_in_box, overlap_check, raycast, "
                      "get_distance, get_direction, get_relative_offset"
        }

    # Normalize vector parameters
    point, point_error = normalize_vector3(point, "point")
    if point_error:
        return {"success": False, "message": point_error}

    box_center, box_center_error = normalize_vector3(box_center, "box_center")
    if box_center_error:
        return {"success": False, "message": box_center_error}

    box_size, box_size_error = normalize_vector3(box_size, "box_size")
    if box_size_error:
        return {"success": False, "message": box_size_error}

    placement_position, placement_pos_error = normalize_vector3(placement_position, "placement_position")
    if placement_pos_error:
        return {"success": False, "message": placement_pos_error}

    rotation_at_placement, rotation_error = normalize_vector3(rotation_at_placement, "rotation_at_placement")
    if rotation_error:
        return {"success": False, "message": rotation_error}

    scale_at_placement, scale_error = normalize_vector3(scale_at_placement, "scale_at_placement")
    if scale_error:
        return {"success": False, "message": scale_error}

    origin, origin_error = normalize_vector3(origin, "origin")
    if origin_error:
        return {"success": False, "message": origin_error}

    direction_vec, direction_error = normalize_vector3(direction, "direction")
    if direction_error:
        return {"success": False, "message": direction_error}

    # Normalize boolean parameters
    exclude_inactive = coerce_bool(exclude_inactive, default=True)

    # Normalize numeric parameters
    radius = coerce_float(radius, default=10.0)
    max_results = coerce_int(max_results, default=50)
    max_distance = coerce_float(max_distance, default=1000.0)
    min_clearance = coerce_float(min_clearance, default=0.0)

    try:
        params = {
            "action": action,
            "source": source,
            "target": target,
            "searchMethod": search_method,
            "point": point,
            "filterByTag": filter_by_tag,
            "filterByLayer": filter_by_layer,
            "filterByComponent": filter_by_component,
            "excludeInactive": exclude_inactive,
            "radius": radius,
            "maxResults": max_results,
            "boxCenter": box_center,
            "boxSize": box_size,
            "objectToPlace": object_to_place,
            "placementPosition": placement_position,
            "rotationAtPlacement": rotation_at_placement,
            "scaleAtPlacement": scale_at_placement,
            "minClearance": min_clearance,
            "origin": origin,
            "direction": direction_vec,
            "maxDistance": max_distance,
            "layerMask": layer_mask,
            "offsetType": offset_type,
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "spatial_queries",
            params,
        )

        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Spatial query '{action}' completed successfully."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}

    except Exception as e:
        return {"success": False, "message": f"Python error in spatial_queries: {e!s}"}
