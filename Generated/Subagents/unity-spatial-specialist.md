# Unity Spatial Specialist

ID: `unity-spatial-specialist`
Kind: `specialist`

Owns transform operations and spatial awareness for reliable scene construction and object placement.

Tool group: `spatial`
Activate with: `manage_tools(action="activate", group="spatial")`

Shared meta-tools:
- `debug_request_context`
- `execute_custom_tool`
- `manage_catalog`
- `manage_error_catalog`
- `manage_script_capabilities`
- `manage_subagents`
- `manage_tools`
- `set_active_instance`

Primary tools:
- `manage_transform`
- `spatial_queries`

Use when:
- Transform-aware inspection and manipulation
- Spatial reasoning about object placement
- Snap, align, and distribute operations
- Bounds and overlap queries
- Raycast and surface queries
- Distance, direction, and relative offset calculations

Workflow:
- Activate the spatial group for the current session.
- Use spatial_queries to understand scene layout before making changes.
- Apply transforms with manage_transform using spatial context.
- Validate placement with spatial validation checks.
- Hand off to core builder for prefab/scene saves after placement.

Handoff targets:
- `unity-core-builder` (for prefab/scene saves)
- `unity-testing-specialist` (for validation)
