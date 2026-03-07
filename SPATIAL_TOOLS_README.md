# Phase 3: Transform and Spatial Awareness - Implementation Summary

## Overview
This phase implements the missing layer between GameObject CRUD and scene construction, enabling agents to reason about where objects are and place them reliably without blind coordinate edits.

## New Tools

### 1. `manage_transform`
**Purpose:** Advanced transform operations for GameObjects

**Actions:**
| Action | Description |
|--------|-------------|
| `get_world_transform` | Get world-space position, rotation, and scale |
| `get_local_transform` | Get local-space transform data including parent reference |
| `set_world_transform` | Set world-space position and rotation |
| `set_local_transform` | Set local-space position, rotation, and scale |
| `get_bounds` | Get renderer/collider bounds (center, extents, min, max) |
| `snap_to_grid` | Snap object position/rotation to grid with configurable size |
| `align_to_object` | Align to another object by bounds or pivot (min, max, center, pivot modes) |
| `distribute_objects` | Evenly distribute multiple objects along an axis |
| `place_relative` | Place object relative to another with offset or cardinal direction |
| `validate_placement` | Check for off-grid, overlap, and invalid scale issues |

**Key Features:**
- Both world and local space operations
- Structured return values for reusability
- Grid snapping with configurable size
- Multi-axis alignment (bounds-based or pivot-based)
- Distribution with auto-spacing or explicit spacing
- Cardinal direction support (left, right, up, down, forward, back, north, south, east, west)

### 2. `spatial_queries`
**Purpose:** Spatial queries for scene analysis

**Actions:**
| Action | Description |
|--------|-------------|
| `nearest_object` | Find the nearest object to a point or source object |
| `objects_in_radius` | Find all objects within a spherical radius |
| `objects_in_box` | Find all objects within a bounding box |
| `overlap_check` | Check if placing an object would cause overlaps |
| `raycast` | Cast a ray and return hit information (point, normal, distance, hit object) |
| `get_distance` | Get distance and offset between two objects/points |
| `get_direction` | Get direction vector and cardinal direction between objects |
| `get_relative_offset` | Get offset from one object to another (world and local) |

**Key Features:**
- Filter by tag, layer, or component type
- Configurable max results and search radius
- Returns structured hit information (point, normal, collider, etc.)
- Cardinal direction calculation
- World and local space offset calculations
- Penetration depth calculation for overlaps

## Files Created

### Server-Side Python
- `ironandspores-mcp/Server/src/services/tools/manage_transform.py` - Server tool handler
- `ironandspores-mcp/Server/src/services/tools/spatial_queries.py` - Server tool handler

### Unity C# (Editor)
- `ironandspores-mcp/MCPForUnity/Editor/Tools/Spatial/ManageTransform.cs` - Unity command handler
- `ironandspores-mcp/MCPForUnity/Editor/Tools/Spatial/SpatialQueries.cs` - Unity command handler

### Updated Files
- `ironandspores-mcp/Server/src/services/registry/tool_registry.py` - Added "spatial" to TOOL_GROUPS
- `ironandspores-mcp/MCPForUnity/Editor/Tools/McpForUnityToolAttribute.cs` - Added "spatial" to valid groups

## Tool Group
Both tools are grouped under the **"spatial"** tool group. This group is not enabled by default (like "core") and must be activated via `manage_tools`:

```python
# Activate spatial tools
manage_tools(action="activate", group="spatial")

# Deactivate when done
manage_tools(action="deactivate", group="spatial")
```

## Usage Examples

### Get World Transform
```python
manage_transform(action="get_world_transform", target="Player")
# Returns: {position: [x, y, z], rotation: [x, y, z], scale: [x, y, z], space: "world"}
```

### Snap to Grid
```python
manage_transform(action="snap_to_grid", target="Cube", grid_size=0.5, snap_position=True)
```

### Align Objects
```python
manage_transform(
    action="align_to_object",
    target="Cube1",
    reference_object="Cube2",
    align_axis="y",
    align_mode="center"
)
```

### Find Objects in Radius
```python
spatial_queries(
    action="objects_in_radius",
    source="Player",
    radius=20.0,
    filter_by_tag="Enemy",
    max_results=10
)
```

### Raycast
```python
spatial_queries(
    action="raycast",
    origin=[0, 10, 0],
    direction=[0, -1, 0],
    max_distance=100,
    layer_mask="Default,Obstacles"
)
```

### Check Overlap
```python
spatial_queries(
    action="overlap_check",
    object_to_place="Tree",
    placement_position=[10, 0, 10],
    min_clearance=0.5
)
```

### Place Relative with Cardinal Direction
```python
manage_transform(
    action="place_relative",
    target="Enemy",
    reference_object="Player",
    direction="behind",
    distance=5.0
)
```

## Data Structures

### TransformData (returned by get operations)
```json
{
  "instanceId": 12345,
  "name": "ObjectName",
  "position": [x, y, z],
  "rotation": [x, y, z],
  "scale": [x, y, z],
  "space": "world|local",
  "parent": "ParentName"  // local only
}
```

### BoundsData (returned by get_bounds)
```json
{
  "hasRenderer": true,
  "rendererCount": 2,
  "hasCollider": true,
  "colliderCount": 1,
  "center": [x, y, z],
  "extents": [x, y, z],
  "size": [x, y, z],
  "min": [x, y, z],
  "max": [x, y, z]
}
```

### RaycastHitData (returned by raycast)
```json
{
  "hit": true,
  "hitPoint": [x, y, z],
  "hitNormal": [x, y, z],
  "distance": 15.5,
  "hitObject": {
    "instanceId": 12345,
    "name": "Ground",
    "path": "Environment/Ground"
  }
}
```

## Architecture Notes

1. **Server-Side (Python):**
   - Tools use the `@mcp_for_unity_tool` decorator with `group="spatial"`
   - Parameter normalization via `normalize_vector3`, `coerce_bool`, etc.
   - Commands sent to Unity via `send_with_unity_instance`

2. **Unity-Side (C#):**
   - Tools marked with `[McpForUnityTool(..., Group = "spatial")]`
   - Static `HandleCommand(JObject)` method pattern
   - Auto-discovery via `CommandRegistry`
   - Uses existing helpers: `GameObjectLookup`, `VectorParsing`, `Response` classes

3. **Group Management:**
   - "spatial" group added to `TOOL_GROUPS` in Python
   - Not in `DEFAULT_ENABLED_GROUPS` (must be activated explicitly)
   - Unity attribute comment updated to document valid groups

## Benefits

1. **Reliable Placement:** Agents can validate placements before committing changes
2. **Spatial Awareness:** Query-based discovery eliminates guesswork for coordinates
3. **Grid Alignment:** Built-in snapping ensures consistent alignment
4. **Overlap Prevention:** Pre-validate object placement to avoid collisions
5. **Directional Reasoning:** Cardinal directions make relative placement intuitive
6. **Structured Returns:** All operations return reusable data structures
