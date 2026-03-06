# Unity MCP Tool Catalog

Generated machine-readable catalog derived from the live server tool registry.

Tool count: 40
Default enabled groups: core

## apply_text_edits

Apply small text edits to a C# script identified by URI.
    IMPORTANT: This tool replaces EXACT character positions. Always verify content at target lines/columns BEFORE editing!
    RECOMMENDED WORKFLOW:
        1. First call resources/read with start_line/line_count to verify exact content
        2. Count columns carefully (or use find_in_file to locate patterns)
        3. Apply your edit with precise coordinates
        4. Consider script_apply_edits with anchors for safer pattern-based replacements
    Notes:
        - For method/class operations, use script_apply_edits (safer, structured edits)
        - For pattern-based replacements, consider anchor operations in script_apply_edits
        - Lines, columns are 1-indexed
        - Tabs count as 1 column

- Group: `core`
- Unity target: `manage_script`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Parameters:
  - `uri`: type=`string`, required=`true`
  - `edits`: type=`array`, required=`true`
  - `precondition_sha256`: type=`string`, required=`false`
  - `strict`: type=`boolean`, required=`false`
  - `options`: type=`object`, required=`false`

## audit_prefab_integrity

Audit prefab assets under a folder for missing scripts, variants, and load failures.

- Group: `testing`
- Unity target: `audit_prefab_integrity`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Parameters:
  - `root_folder`: type=`string`, required=`false`
  - `max_prefabs`: type=`integer`, required=`false`
  - `max_issues`: type=`integer`, required=`false`
  - `include_variants`: type=`boolean`, required=`false`

## audit_scene_integrity

Audit loaded scenes for missing scripts, dirty state, inactive object counts, and issue samples.

- Group: `testing`
- Unity target: `audit_scene_integrity`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Parameters:
  - `scope`: type=`enum`, required=`false`, enum=`active`, `loaded`
  - `include_inactive`: type=`boolean`, required=`false`
  - `max_issues`: type=`integer`, required=`false`

## batch_execute

Executes multiple MCP commands in a single batch for dramatically better performance. STRONGLY RECOMMENDED when creating/modifying multiple objects, adding components to multiple targets, or performing any repetitive operations. Reduces latency and token costs by 10-100x compared to sequential tool calls. The max commands per batch is configurable in the Unity MCP Tools window (default 25, hard max 100). Example: creating 5 cubes → use 1 batch_execute with 5 create commands instead of 5 separate calls.

- Group: `core`
- Unity target: `batch_execute`
- Action model: `mixed`
- Mutating: `false`
- High risk: `false`
- Parameters:
  - `commands`: type=`array`, required=`true`
  - `parallel`: type=`boolean`, required=`false`
  - `fail_fast`: type=`boolean`, required=`false`
  - `max_parallelism`: type=`integer`, required=`false`

## create_script

Create a new C# script at the given project path.

- Group: `core`
- Unity target: `manage_script`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Parameters:
  - `path`: type=`string`, required=`true`
  - `contents`: type=`string`, required=`true`
  - `script_type`: type=`string`, required=`false`
  - `namespace`: type=`string`, required=`false`

## debug_request_context

Return the current FastMCP request context details (client_id, session_id, and meta dump).

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`

## delete_script

Delete a C# script by URI or Assets-relative path.

- Group: `core`
- Unity target: `manage_script`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Parameters:
  - `uri`: type=`string`, required=`true`

## execute_custom_tool

Execute a project-scoped custom tool registered by Unity.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Parameters:
  - `tool_name`: type=`string`, required=`true`
  - `parameters`: type=`dict`, required=`false`

## execute_menu_item

Execute a Unity menu item by path.

- Group: `core`
- Unity target: `execute_menu_item`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Parameters:
  - `menu_path`: type=`string`, required=`false`

## find_gameobjects

Search for GameObjects in the scene by name, tag, layer, component type, or path. Returns instance IDs only (paginated). Then use mcpforunity://scene/gameobject/{id} resource for full data, or mcpforunity://scene/gameobject/{id}/components for component details. For CRUD operations (create/modify/delete), use manage_gameobject instead.

- Group: `core`
- Unity target: `find_gameobjects`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Parameters:
  - `search_term`: type=`string`, required=`true`
  - `search_method`: type=`enum`, required=`false`, enum=`by_component`, `by_id`, `by_layer`, `by_name`, `by_path`, `by_tag`
  - `include_inactive`: type=`boolean | string`, required=`false`
  - `page_size`: type=`integer | string`, required=`false`
  - `cursor`: type=`integer | string`, required=`false`

## find_in_file

Searches a file with a regex pattern and returns line numbers and excerpts.

- Group: `core`
- Unity target: `manage_script`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Parameters:
  - `uri`: type=`string`, required=`true`
  - `pattern`: type=`string`, required=`true`
  - `project_root`: type=`string`, required=`false`
  - `max_results`: type=`integer`, required=`false`
  - `ignore_case`: type=`boolean | string`, required=`false`

## get_sha

Get SHA256 and basic metadata for a Unity C# script without returning file contents. Requires uri (script path under Assets/ or mcpforunity://path/Assets/... or file://...).

- Group: `core`
- Unity target: `manage_script`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Parameters:
  - `uri`: type=`string`, required=`true`

## get_test_job

Polls an async Unity test job by job_id.

- Group: `testing`
- Unity target: `get_test_job`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Parameters:
  - `job_id`: type=`string`, required=`true`
  - `include_failed_tests`: type=`boolean`, required=`false`
  - `include_details`: type=`boolean`, required=`false`
  - `wait_timeout`: type=`integer`, required=`false`

## manage_animation

Manage Unity animation: Animator control and AnimationClip creation. Action prefixes: animator_* (play, crossfade, set parameters, get info), controller_* (create AnimatorControllers, add states/transitions/parameters), clip_* (create clips, add keyframe curves, assign to GameObjects). Action-specific parameters go in `properties` (keys match ManageAnimation.cs).

- Group: `animation`
- Unity target: `manage_animation`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Known read-only actions: `animator_get_info`, `animator_get_parameter`, `clip_get_info`, `controller_get_info`
- Parameters:
  - `action`: type=`string`, required=`true`
  - `target`: type=`string`, required=`false`
  - `search_method`: type=`enum`, required=`false`, enum=`by_id`, `by_layer`, `by_name`, `by_path`, `by_tag`
  - `clip_path`: type=`string`, required=`false`
  - `controller_path`: type=`string`, required=`false`
  - `properties`: type=`object | string`, required=`false`

## manage_asset

Performs asset operations (import, create, modify, delete, etc.) in Unity.

Tip (payload safety): for `action="search"`, prefer paging (`page_size`, `page_number`) and keep `generate_preview=false` (previews can add large base64 blobs).

- Group: `core`
- Unity target: `manage_asset`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `create`, `create_folder`, `delete`, `duplicate`, `get_components`, `get_info`, `import`, `modify`, `move`, `rename`, `search`
- Known read-only actions: `get_components`, `get_info`, `search`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`create`, `create_folder`, `delete`, `duplicate`, `get_components`, `get_info`, `import`, `modify`, `move`, `rename`, `search`
  - `path`: type=`string`, required=`true`
  - `asset_type`: type=`string`, required=`false`
  - `properties`: type=`object`, required=`false`
  - `destination`: type=`string`, required=`false`
  - `generate_preview`: type=`boolean`, required=`false`
  - `search_pattern`: type=`string`, required=`false`
  - `filter_type`: type=`string`, required=`false`
  - `filter_date_after`: type=`string`, required=`false`
  - `page_size`: type=`integer | number | string`, required=`false`
  - `page_number`: type=`integer | number | string`, required=`false`
- Action contracts:
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `create_folder`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `duplicate`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `get_components`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `get_info`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `import`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `modify`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `move`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `rename`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `search`: read_only=`true`, mutating=`false`, high_risk=`false`

## manage_catalog

List or export the generated Unity MCP tool catalog built from the live tool registry and action policy metadata.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `export`, `list`
- Known read-only actions: `list`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`export`, `list`
  - `output_dir`: type=`string`, required=`false`
  - `format`: type=`enum`, required=`false`, enum=`both`, `json`, `markdown`
- Action contracts:
  - `export`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `list`: read_only=`true`, mutating=`false`, high_risk=`false`

## manage_components

Add, remove, or set properties on components attached to GameObjects. Actions: add, remove, set_property. Requires target (instance ID or name) and component_type. For READING component data, use the mcpforunity://scene/gameobject/{id}/components resource or mcpforunity://scene/gameobject/{id}/component/{name} for a single component. For creating/deleting GameObjects themselves, use manage_gameobject instead.

- Group: `core`
- Unity target: `manage_components`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supported actions: `add`, `remove`, `set_property`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`add`, `remove`, `set_property`
  - `target`: type=`integer | string`, required=`true`
  - `component_type`: type=`string`, required=`true`
  - `search_method`: type=`enum`, required=`false`, enum=`by_id`, `by_name`, `by_path`
  - `property`: type=`string`, required=`false`
  - `value`: type=`boolean | dict | integer | list | number | string`, required=`false`
  - `properties`: type=`object`, required=`false`
- Action contracts:
  - `add`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `remove`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `set_property`: read_only=`false`, mutating=`true`, high_risk=`true`

## manage_editor

Controls and queries the Unity editor's state and settings. Tip: pass booleans as true/false; if your client only sends strings, 'true'/'false' are accepted. Read-only actions: telemetry_status, telemetry_ping. Modifying actions: play, pause, stop, set_active_tool, add_tag, remove_tag, add_layer, remove_layer.

- Group: `core`
- Unity target: `manage_editor`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `add_layer`, `add_tag`, `pause`, `play`, `remove_layer`, `remove_tag`, `set_active_tool`, `stop`, `telemetry_ping`, `telemetry_status`
- Known read-only actions: `telemetry_ping`, `telemetry_status`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`add_layer`, `add_tag`, `pause`, `play`, `remove_layer`, `remove_tag`, `set_active_tool`, `stop`, `telemetry_ping`, `telemetry_status`
  - `wait_for_completion`: type=`boolean | string`, required=`false`
  - `tool_name`: type=`string`, required=`false`
  - `tag_name`: type=`string`, required=`false`
  - `layer_name`: type=`string`, required=`false`
- Action contracts:
  - `add_layer`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `add_tag`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `pause`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `play`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `remove_layer`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `remove_tag`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `set_active_tool`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `stop`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `telemetry_ping`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `telemetry_status`: read_only=`true`, mutating=`false`, high_risk=`false`

## manage_error_catalog

List or export the generated error-code and operational-contract catalog for this fork.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `export`, `list`
- Known read-only actions: `list`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`export`, `list`
  - `output_dir`: type=`string`, required=`false`
  - `format`: type=`enum`, required=`false`, enum=`both`, `json`, `markdown`
- Action contracts:
  - `export`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `list`: read_only=`true`, mutating=`false`, high_risk=`false`

## manage_gameobject

Performs CRUD operations on GameObjects. Actions: create, modify, delete, duplicate, move_relative, look_at. NOT for searching — use the find_gameobjects tool to search by name/tag/layer/component/path. NOT for component management — use the manage_components tool (add/remove/set_property) or mcpforunity://scene/gameobject/{id}/components resource (read).

- Group: `core`
- Unity target: `manage_gameobject`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supported actions: `create`, `delete`, `duplicate`, `look_at`, `modify`, `move_relative`
- Parameters:
  - `action`: type=`enum`, required=`false`, enum=`create`, `delete`, `duplicate`, `look_at`, `modify`, `move_relative`
  - `target`: type=`string`, required=`false`
  - `search_method`: type=`enum`, required=`false`, enum=`by_component`, `by_id`, `by_layer`, `by_name`, `by_path`, `by_tag`
  - `name`: type=`string`, required=`false`
  - `tag`: type=`string`, required=`false`
  - `parent`: type=`string`, required=`false`
  - `position`: type=`array | object | string`, required=`false`
  - `rotation`: type=`array | object | string`, required=`false`
  - `scale`: type=`array | object | string`, required=`false`
  - `components_to_add`: type=`array | string`, required=`false`
  - `primitive_type`: type=`string`, required=`false`
  - `save_as_prefab`: type=`boolean | string`, required=`false`
  - `prefab_path`: type=`string`, required=`false`
  - `prefab_folder`: type=`string`, required=`false`
  - `set_active`: type=`boolean | string`, required=`false`
  - `layer`: type=`string`, required=`false`
  - `components_to_remove`: type=`array | string`, required=`false`
  - `component_properties`: type=`object`, required=`false`
  - `new_name`: type=`string`, required=`false`
  - `offset`: type=`array | string`, required=`false`
  - `reference_object`: type=`string`, required=`false`
  - `direction`: type=`enum`, required=`false`, enum=`back`, `backward`, `behind`, `down`, `forward`, `front`, `left`, `right`, `up`
  - `distance`: type=`number`, required=`false`
  - `world_space`: type=`boolean | string`, required=`false`
  - `look_at_target`: type=`array | string`, required=`false`
  - `look_at_up`: type=`array | string`, required=`false`
- Action contracts:
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `duplicate`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `look_at`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `modify`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `move_relative`: read_only=`false`, mutating=`true`, high_risk=`true`

## manage_material

Manages Unity materials (set properties, colors, shaders, etc). Read-only actions: ping, get_material_info. Modifying actions: create, set_material_shader_property, set_material_color, assign_material_to_renderer, set_renderer_color.

- Group: `core`
- Unity target: `manage_material`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `assign_material_to_renderer`, `create`, `get_material_info`, `ping`, `set_material_color`, `set_material_shader_property`, `set_renderer_color`
- Known read-only actions: `get_material_info`, `ping`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`assign_material_to_renderer`, `create`, `get_material_info`, `ping`, `set_material_color`, `set_material_shader_property`, `set_renderer_color`
  - `material_path`: type=`string`, required=`false`
  - `property`: type=`string`, required=`false`
  - `shader`: type=`string`, required=`false`
  - `properties`: type=`object`, required=`false`
  - `value`: type=`boolean | integer | list | number | string`, required=`false`
  - `color`: type=`array | object | string`, required=`false`
  - `target`: type=`string`, required=`false`
  - `search_method`: type=`enum`, required=`false`, enum=`by_component`, `by_layer`, `by_name`, `by_path`, `by_tag`
  - `slot`: type=`integer`, required=`false`
  - `mode`: type=`enum`, required=`false`, enum=`instance`, `property_block`, `shared`
- Action contracts:
  - `assign_material_to_renderer`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `get_material_info`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `ping`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `set_material_color`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `set_material_shader_property`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `set_renderer_color`: read_only=`false`, mutating=`true`, high_risk=`true`

## manage_prefabs

Manages Unity Prefab assets via headless operations (no UI, no prefab stages). Actions: get_info, get_hierarchy, create_from_gameobject, modify_contents. Use modify_contents for headless prefab editing - ideal for automated workflows. Use create_child parameter with modify_contents to add child GameObjects to a prefab (single object or array for batch creation in one save). Example: create_child=[{"name": "Child1", "primitive_type": "Sphere", "position": [1,0,0]}, {"name": "Child2", "primitive_type": "Cube", "parent": "Child1"}]. Use component_properties with modify_contents to set serialized fields on existing components (e.g. component_properties={"Rigidbody": {"mass": 5.0}, "MyScript": {"health": 100}}). Supports object references via {"guid": "..."}, {"path": "Assets/..."}, or {"instanceID": 123}. Use manage_asset action=search filterType=Prefab to list prefabs.

- Group: `core`
- Unity target: `manage_prefabs`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `create_from_gameobject`, `get_hierarchy`, `get_info`, `modify_contents`
- Known read-only actions: `get_hierarchy`, `get_info`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`create_from_gameobject`, `get_hierarchy`, `get_info`, `modify_contents`
  - `prefab_path`: type=`string`, required=`false`
  - `target`: type=`string`, required=`false`
  - `allow_overwrite`: type=`boolean`, required=`false`
  - `search_inactive`: type=`boolean`, required=`false`
  - `unlink_if_instance`: type=`boolean`, required=`false`
  - `position`: type=`array | object | string`, required=`false`
  - `rotation`: type=`array | object | string`, required=`false`
  - `scale`: type=`array | object | string`, required=`false`
  - `name`: type=`string`, required=`false`
  - `tag`: type=`string`, required=`false`
  - `layer`: type=`string`, required=`false`
  - `set_active`: type=`boolean`, required=`false`
  - `parent`: type=`string`, required=`false`
  - `components_to_add`: type=`array`, required=`false`
  - `components_to_remove`: type=`array`, required=`false`
  - `create_child`: type=`array | object`, required=`false`
  - `component_properties`: type=`object`, required=`false`
- Action contracts:
  - `create_from_gameobject`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `get_hierarchy`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `get_info`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `modify_contents`: read_only=`false`, mutating=`true`, high_risk=`true`

## manage_scene

Performs CRUD operations on Unity scenes. Read-only actions: get_hierarchy, get_active, get_build_settings, screenshot, scene_view_frame. Modifying actions: create, load, save. screenshot supports include_image=true to return an inline base64 PNG for AI vision. screenshot with batch='surround' captures 6 angles around the scene (no file saved) for comprehensive scene understanding. screenshot with batch='orbit' captures configurable azimuth x elevation grid for visual QA (use orbit_angles, orbit_elevations, orbit_distance, orbit_fov). screenshot with look_at/view_position creates a temp camera at that viewpoint and returns an inline image.

- Group: `core`
- Unity target: `manage_scene`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `create`, `get_active`, `get_build_settings`, `get_hierarchy`, `load`, `save`, `scene_view_frame`, `screenshot`
- Known read-only actions: `get_active`, `get_build_settings`, `get_hierarchy`, `scene_view_frame`, `screenshot`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`create`, `get_active`, `get_build_settings`, `get_hierarchy`, `load`, `save`, `scene_view_frame`, `screenshot`
  - `name`: type=`string`, required=`false`
  - `path`: type=`string`, required=`false`
  - `build_index`: type=`integer | string`, required=`false`
  - `screenshot_file_name`: type=`string`, required=`false`
  - `screenshot_super_size`: type=`integer | string`, required=`false`
  - `camera`: type=`string`, required=`false`
  - `include_image`: type=`boolean | string`, required=`false`
  - `max_resolution`: type=`integer | string`, required=`false`
  - `batch`: type=`string`, required=`false`
  - `look_at`: type=`array | integer | string`, required=`false`
  - `view_position`: type=`array | string`, required=`false`
  - `view_rotation`: type=`array | string`, required=`false`
  - `orbit_angles`: type=`integer | string`, required=`false`
  - `orbit_elevations`: type=`array | string`, required=`false`
  - `orbit_distance`: type=`number | string`, required=`false`
  - `orbit_fov`: type=`number | string`, required=`false`
  - `scene_view_target`: type=`integer | string`, required=`false`
  - `parent`: type=`integer | string`, required=`false`
  - `page_size`: type=`integer | string`, required=`false`
  - `cursor`: type=`integer | string`, required=`false`
  - `max_nodes`: type=`integer | string`, required=`false`
  - `max_depth`: type=`integer | string`, required=`false`
  - `max_children_per_node`: type=`integer | string`, required=`false`
  - `include_transform`: type=`boolean | string`, required=`false`
- Action contracts:
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `get_active`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `get_build_settings`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `get_hierarchy`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `load`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `save`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `scene_view_frame`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `screenshot`: read_only=`true`, mutating=`false`, high_risk=`false`

## manage_script

Compatibility router for legacy script operations. Prefer apply_text_edits (ranges) or script_apply_edits (structured) for edits. Read-only action: read. Modifying actions: create, delete.

- Group: `core`
- Unity target: `manage_script`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `create`, `delete`, `read`
- Known read-only actions: `read`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`create`, `delete`, `read`
  - `name`: type=`string`, required=`true`
  - `path`: type=`string`, required=`true`
  - `contents`: type=`string`, required=`false`
  - `script_type`: type=`string`, required=`false`
  - `namespace`: type=`string`, required=`false`
- Action contracts:
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `read`: read_only=`true`, mutating=`false`, high_risk=`false`

## manage_script_capabilities

Get manage_script capabilities (supported ops, limits, and guards).
    Returns:
        - ops: list of supported structured ops
        - text_ops: list of supported text ops
        - max_edit_payload_bytes: server edit payload cap
        - guards: header/using guard enabled flag

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`

## manage_scriptable_object

Creates and modifies ScriptableObject assets using Unity SerializedObject property paths.

- Group: `scripting_ext`
- Unity target: `manage_scriptable_object`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supported actions: `create`, `modify`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`create`, `modify`
  - `type_name`: type=`string`, required=`false`
  - `folder_path`: type=`string`, required=`false`
  - `asset_name`: type=`string`, required=`false`
  - `overwrite`: type=`boolean | string`, required=`false`
  - `target`: type=`object | string`, required=`false`
  - `patches`: type=`array | string`, required=`false`
  - `dry_run`: type=`boolean | string`, required=`false`
- Action contracts:
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `modify`: read_only=`false`, mutating=`true`, high_risk=`true`

## manage_shader

Manages shader scripts in Unity (create, read, update, delete). Read-only action: read. Modifying actions: create, update, delete.

- Group: `vfx`
- Unity target: `manage_shader`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `create`, `delete`, `read`, `update`
- Known read-only actions: `read`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`create`, `delete`, `read`, `update`
  - `name`: type=`string`, required=`true`
  - `path`: type=`string`, required=`true`
  - `contents`: type=`string`, required=`false`
- Action contracts:
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `read`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `update`: read_only=`false`, mutating=`true`, high_risk=`true`

## manage_subagents

List or export generated Unity MCP subagent artifacts built from the live tool registry. Use action='list' to inspect the current catalog. Use action='export' to write JSON and/or Markdown subagent files to disk.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `export`, `list`
- Known read-only actions: `list`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`export`, `list`
  - `output_dir`: type=`string`, required=`false`
  - `format`: type=`enum`, required=`false`, enum=`both`, `json`, `markdown`
- Action contracts:
  - `export`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `list`: read_only=`true`, mutating=`false`, high_risk=`false`

## manage_texture

Procedural texture generation for Unity. Creates textures with solid fills, patterns (checkerboard, stripes, dots, grid, brick), gradients, and noise. Actions: create, modify, delete, create_sprite, apply_pattern, apply_gradient, apply_noise

- Group: `vfx`
- Unity target: `manage_texture`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supported actions: `apply_gradient`, `apply_noise`, `apply_pattern`, `create`, `create_sprite`, `delete`, `modify`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`apply_gradient`, `apply_noise`, `apply_pattern`, `create`, `create_sprite`, `delete`, `modify`
  - `path`: type=`string`, required=`false`
  - `width`: type=`integer`, required=`false`
  - `height`: type=`integer`, required=`false`
  - `fill_color`: type=`array | object | string`, required=`false`
  - `pattern`: type=`enum`, required=`false`, enum=`brick`, `checkerboard`, `dots`, `grid`, `stripes`, `stripes_diag`, `stripes_h`, `stripes_v`
  - `palette`: type=`array | string`, required=`false`
  - `pattern_size`: type=`integer`, required=`false`
  - `pixels`: type=`array | string`, required=`false`
  - `image_path`: type=`string`, required=`false`
  - `gradient_type`: type=`enum`, required=`false`, enum=`linear`, `radial`
  - `gradient_angle`: type=`number`, required=`false`
  - `noise_scale`: type=`number`, required=`false`
  - `octaves`: type=`integer`, required=`false`
  - `set_pixels`: type=`dict`, required=`false`
  - `as_sprite`: type=`boolean | dict`, required=`false`
  - `import_settings`: type=`dict`, required=`false`
- Action contracts:
  - `apply_gradient`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `apply_noise`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `apply_pattern`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `create_sprite`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `modify`: read_only=`false`, mutating=`true`, high_risk=`true`

## manage_tools

Manage which tool groups are visible in this session. Actions: list_groups (show all groups and their status), activate (enable a group), deactivate (disable a group), sync (refresh visibility from Unity Editor's toggle states), reset (restore defaults). Activating a group makes its tools appear; deactivating hides them. Use sync after toggling tools in the Unity Editor GUI.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `activate`, `deactivate`, `list_groups`, `reset`, `sync`
- Known read-only actions: `list_groups`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`activate`, `deactivate`, `list_groups`, `reset`, `sync`
  - `group`: type=`string`, required=`false`
- Action contracts:
  - `activate`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `deactivate`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `list_groups`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `reset`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `sync`: read_only=`false`, mutating=`true`, high_risk=`true`

## manage_ui

Manages Unity UI Toolkit elements (UXML documents, USS stylesheets, UIDocument components). Read-only actions: ping, read, get_visual_tree, list. Modifying actions: create, update, delete, attach_ui_document, detach_ui_document, create_panel_settings, update_panel_settings, modify_visual_element.
Visual actions: render_ui (captures UI panel to a PNG screenshot for self-evaluation).
Structural actions: link_stylesheet (adds a Style src reference to a UXML file).

UI Toolkit workflow:
1. Use list to discover existing UI assets
2. Create a UXML file (structure, like HTML)
3. Create a USS file (styling, like CSS)
4. Link stylesheet to UXML via link_stylesheet
5. Attach UIDocument to a GameObject with the UXML source
6. Use get_visual_tree to inspect the result
7. Use modify_visual_element to change text, classes, or inline styles on live elements
8. Use render_ui to capture a visual preview for self-evaluation
   - In play mode: first call queues a WaitForEndOfFrame screen capture and returns pending=true;
     call render_ui a second time to retrieve the saved PNG (hasContent will be true).
   - In editor mode: assigns a RenderTexture to PanelSettings (best-effort; may stay blank).
9. Use detach_ui_document to remove UIDocument from a GameObject
10. Use delete to remove .uxml/.uss files

- Group: `ui`
- Unity target: `manage_ui`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `attach_ui_document`, `create`, `create_panel_settings`, `delete`, `detach_ui_document`, `get_visual_tree`, `link_stylesheet`, `list`, `modify_visual_element`, `ping`, `read`, `render_ui`, `update`, `update_panel_settings`
- Known read-only actions: `get_visual_tree`, `list`, `ping`, `read`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`attach_ui_document`, `create`, `create_panel_settings`, `delete`, `detach_ui_document`, `get_visual_tree`, `link_stylesheet`, `list`, `modify_visual_element`, `ping`, `read`, `render_ui`, `update`, `update_panel_settings`
  - `path`: type=`string`, required=`false`
  - `contents`: type=`string`, required=`false`
  - `target`: type=`string`, required=`false`
  - `source_asset`: type=`string`, required=`false`
  - `panel_settings`: type=`string`, required=`false`
  - `sort_order`: type=`integer`, required=`false`
  - `scale_mode`: type=`enum`, required=`false`, enum=`ConstantPhysicalSize`, `ConstantPixelSize`, `ScaleWithScreenSize`
  - `reference_resolution`: type=`object`, required=`false`
  - `settings`: type=`object`, required=`false`
  - `max_depth`: type=`integer`, required=`false`
  - `width`: type=`integer`, required=`false`
  - `height`: type=`integer`, required=`false`
  - `include_image`: type=`boolean`, required=`false`
  - `max_resolution`: type=`integer`, required=`false`
  - `screenshot_file_name`: type=`string`, required=`false`
  - `stylesheet`: type=`string`, required=`false`
  - `filter_type`: type=`string`, required=`false`
  - `page_size`: type=`integer`, required=`false`
  - `page_number`: type=`integer`, required=`false`
  - `element_name`: type=`string`, required=`false`
  - `text`: type=`string`, required=`false`
  - `add_classes`: type=`array`, required=`false`
  - `remove_classes`: type=`array`, required=`false`
  - `toggle_classes`: type=`array`, required=`false`
  - `style`: type=`object`, required=`false`
  - `enabled`: type=`boolean`, required=`false`
  - `visible`: type=`boolean`, required=`false`
  - `tooltip`: type=`string`, required=`false`
- Action contracts:
  - `attach_ui_document`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `create_panel_settings`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `detach_ui_document`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `get_visual_tree`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `link_stylesheet`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `list`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `modify_visual_element`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `ping`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `read`: read_only=`true`, mutating=`false`, high_risk=`false`
  - `render_ui`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `update`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `update_panel_settings`: read_only=`false`, mutating=`true`, high_risk=`true`

## manage_vfx

Manage Unity VFX components (ParticleSystem, VisualEffect, LineRenderer, TrailRenderer). Action prefixes: particle_*, vfx_*, line_*, trail_*. Action-specific parameters go in `properties` (keys match ManageVFX.cs).

- Group: `vfx`
- Unity target: `manage_vfx`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Known read-only actions: `line_get_info`, `particle_get_info`, `ping`, `trail_get_info`, `vfx_get_info`, `vfx_list_assets`, `vfx_list_templates`
- Parameters:
  - `action`: type=`string`, required=`true`
  - `target`: type=`string`, required=`false`
  - `search_method`: type=`enum`, required=`false`, enum=`by_id`, `by_layer`, `by_name`, `by_path`, `by_tag`
  - `properties`: type=`object | string`, required=`false`

## preflight_audit

Run a combined read-only preflight audit: compile health, scene integrity, and prefab integrity. Use this before broad mutations or test runs.

- Group: `testing`
- Unity target: `preflight_audit`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Parameters:
  - `scene_scope`: type=`string`, required=`false`
  - `prefab_root_folder`: type=`string`, required=`false`
  - `prefab_scan_limit`: type=`integer`, required=`false`
  - `max_issue_samples`: type=`integer`, required=`false`

## read_console

Gets messages from or clears the Unity Editor console. Defaults to 10 most recent entries. Use page_size/cursor for paging. Note: For maximum client compatibility, pass count as a quoted string (e.g., '5'). The 'get' action is read-only; 'clear' modifies ephemeral UI state (not project data).

- Group: `core`
- Unity target: `read_console`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supported actions: `clear`, `get`
- Known read-only actions: `get`
- Parameters:
  - `action`: type=`enum`, required=`false`, enum=`clear`, `get`
  - `types`: type=`array | string`, required=`false`, enum=`all`, `error`, `log`, `warning`
  - `count`: type=`integer | string`, required=`false`
  - `filter_text`: type=`string`, required=`false`
  - `page_size`: type=`integer | string`, required=`false`
  - `cursor`: type=`integer | string`, required=`false`
  - `format`: type=`enum`, required=`false`, enum=`detailed`, `json`, `plain`
  - `include_stacktrace`: type=`boolean | string`, required=`false`
- Action contracts:
  - `clear`: read_only=`false`, mutating=`true`, high_risk=`true`
  - `get`: read_only=`true`, mutating=`false`, high_risk=`false`

## refresh_unity

Request a Unity asset database refresh and optionally a script compilation. Can optionally wait for readiness.

- Group: `core`
- Unity target: `refresh_unity`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Parameters:
  - `mode`: type=`enum`, required=`false`, enum=`force`, `if_dirty`
  - `scope`: type=`enum`, required=`false`, enum=`all`, `assets`, `scripts`
  - `compile`: type=`enum`, required=`false`, enum=`none`, `request`
  - `wait_for_ready`: type=`boolean`, required=`false`

## run_tests

Starts a Unity test run asynchronously and returns a job_id immediately. Poll with get_test_job for progress.

- Group: `testing`
- Unity target: `run_tests`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Parameters:
  - `mode`: type=`enum`, required=`false`, enum=`EditMode`, `PlayMode`
  - `test_names`: type=`array | string`, required=`false`
  - `group_names`: type=`array | string`, required=`false`
  - `category_names`: type=`array | string`, required=`false`
  - `assembly_names`: type=`array | string`, required=`false`
  - `include_failed_tests`: type=`boolean`, required=`false`
  - `include_details`: type=`boolean`, required=`false`

## script_apply_edits

Structured C# edits (methods/classes) with safer boundaries - prefer this over raw text.
    Best practices:
    - Prefer anchor_* ops for pattern-based insert/replace near stable markers
    - Use replace_method/delete_method for whole-method changes (keeps signatures balanced)
    - Avoid whole-file regex deletes; validators will guard unbalanced braces
    - For tail insertions, prefer anchor/regex_replace on final brace (class closing)
    - Pass options.validate='standard' for structural checks; 'relaxed' for interior-only edits
    Canonical fields (use these exact keys):
    - op: replace_method | insert_method | delete_method | anchor_insert | anchor_delete | anchor_replace
    - className: string (defaults to 'name' if omitted on method/class ops)
    - methodName: string (required for replace_method, delete_method)
    - replacement: string (required for replace_method, insert_method)
    - position: start | end | after | before (insert_method only)
    - afterMethodName / beforeMethodName: string (required when position='after'/'before')
    - anchor: regex string (for anchor_* ops)
    - text: string (for anchor_insert/anchor_replace)
    Examples:
    1) Replace a method:
    {
        "name": "SmartReach",
        "path": "Assets/Scripts/Interaction",
        "edits": [
        {
        "op": "replace_method",
        "className": "SmartReach",
        "methodName": "HasTarget",
        "replacement": "public bool HasTarget(){ return currentTarget!=null; }"
        }
    ],
    "options": {"validate": "standard", "refresh": "immediate"}
    }
    "2) Insert a method after another:
    {
        "name": "SmartReach",
        "path": "Assets/Scripts/Interaction",
        "edits": [
        {
        "op": "insert_method",
        "className": "SmartReach",
        "replacement": "public void PrintSeries(){ Debug.Log(seriesName); }",
        "position": "after",
        "afterMethodName": "GetCurrentTarget"
        }
    ],
    }
    ]

- Group: `core`
- Unity target: `manage_script`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Parameters:
  - `name`: type=`string`, required=`true`
  - `path`: type=`string`, required=`true`
  - `edits`: type=`array | string`, required=`true`
  - `options`: type=`object`, required=`false`
  - `script_type`: type=`string`, required=`false`
  - `namespace`: type=`string`, required=`false`

## set_active_instance

Set the active Unity instance for this client/session. Accepts Name@hash, hash prefix, or port number (stdio only).

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Parameters:
  - `instance`: type=`string`, required=`true`

## validate_compile_health

Check Unity compile readiness and summarize recent compiler diagnostics from editor state and console output.

- Group: `core`
- Unity target: `validate_compile_health`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Parameters:
  - `include_warnings`: type=`boolean`, required=`false`
  - `compiler_only`: type=`boolean`, required=`false`
  - `max_diagnostics`: type=`integer`, required=`false`

## validate_script

Validate a C# script and return diagnostics.

- Group: `core`
- Unity target: `manage_script`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Parameters:
  - `uri`: type=`string`, required=`true`
  - `level`: type=`enum`, required=`false`, enum=`basic`, `standard`
  - `include_diagnostics`: type=`boolean`, required=`false`

