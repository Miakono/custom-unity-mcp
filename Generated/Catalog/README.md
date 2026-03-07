# Unity MCP Tool Catalog

Generated machine-readable catalog derived from the live server tool registry.

Tool count: 133
Default enabled groups: animation, asset_intelligence, core, dev_tools, diff_patch, events, input, navigation, pipeline, pipeline_control, profiling, project_config, scripting_ext, spatial, testing, transactions, ui, vfx, visual_qa

## analyze_asset_dependencies

Analyze asset dependencies and relationships. Read-only actions: get_dependencies, get_dependents, analyze_circular. Helps understand asset relationships, find what depends on what, and detect circular dependencies that can cause issues.

- Group: `project_config`
- Unity target: `analyze_asset_dependencies`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `analyze_circular`, `get_dependencies`, `get_dependents`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`analyze_circular`, `get_dependencies`, `get_dependents`
  - `asset_path`: type=`string`, required=`false`
  - `asset_guid`: type=`string`, required=`false`
  - `include_indirect`: type=`boolean`, required=`false`
  - `max_depth`: type=`integer`, required=`false`
  - `search_scope`: type=`string`, required=`false`
- Action contracts:
  - `analyze_circular`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_dependencies`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_dependents`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## analyze_screenshot

Analyze screenshots and images for visual verification. Works with manage_video_capture to provide a complete capture → analyze workflow. Actions: analyze (perform image analysis). 

Analysis Types:
- ui_validation: Verify UI elements are present and correctly positioned
- scene_composition: Analyze overall scene layout and visual balance
- object_presence: Check for expected objects in the scene
- color_check: Validate color schemes and visual consistency
- custom: Use natural language query for specific analysis


Workflow:
1. Use manage_video_capture to capture a screenshot
2. Pass the screenshot path or data to analyze_screenshot
3. Specify analysis_type and optional expected_elements
4. Review structured analysis results

- Group: `visual_qa`
- Unity target: `server-only`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `analyze`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`analyze`
  - `analysis_type`: type=`enum`, required=`true`, enum=`color_check`, `custom`, `object_presence`, `scene_composition`, `ui_validation`
  - `screenshot_path`: type=`string`, required=`false`
  - `screenshot_data`: type=`string`, required=`false`
  - `query`: type=`string`, required=`false`
  - `expected_elements`: type=`array`, required=`false`
  - `regions_of_interest`: type=`array`, required=`false`
- Action contracts:
  - `analyze`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

## apply_prefab_patch

Apply structured patches to Unity prefabs. Supports applying patches derived from diffs (via based_on_diff parameter) or custom patch operations. Can modify prefab assets directly or apply overrides to instances. Provides dry-run mode for previewing changes before application. All changes are applied deterministically and can be reviewed via the returned results.

- Group: `diff_patch`
- Unity target: `apply_prefab_patch`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `prefab_path`: type=`string`, required=`true`
  - `operations`: type=`array | string`, required=`false`
  - `based_on_diff`: type=`string`, required=`false`
  - `target_mode`: type=`enum`, required=`false`, enum=`asset`, `instance`, `variant`
  - `instance_path`: type=`string`, required=`false`
  - `dry_run`: type=`boolean | string`, required=`false`
  - `create_checkpoint`: type=`boolean | string`, required=`false`
  - `apply_as_override`: type=`boolean | string`, required=`false`

## apply_scene_patch

Apply structured patches to Unity scenes. Supports applying patches derived from diffs (via based_on_diff parameter) or custom patch operations. Provides dry-run mode for previewing changes before application. All changes are applied deterministically and can be reviewed via the returned results.

- Group: `diff_patch`
- Unity target: `apply_scene_patch`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `scene_path`: type=`string`, required=`false`
  - `operations`: type=`array | string`, required=`false`
  - `based_on_diff`: type=`string`, required=`false`
  - `dry_run`: type=`boolean | string`, required=`false`
  - `create_checkpoint`: type=`boolean | string`, required=`false`
  - `skip_validation`: type=`boolean | string`, required=`false`

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
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `uri`: type=`string`, required=`true`
  - `edits`: type=`array`, required=`true`
  - `precondition_sha256`: type=`string`, required=`false`
  - `strict`: type=`boolean`, required=`false`
  - `options`: type=`object | string`, required=`false`

## asset_index_status

Check the status of the asset index without modifying it. Reports index freshness, coverage statistics, and whether the index needs to be rebuilt before searching.

- Group: `asset_intelligence`
- Unity target: `asset_index_status`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `detailed`: type=`boolean`, required=`false`

## audit_prefab_integrity

Audit prefab assets under a folder for missing scripts, variants, and load failures.

- Group: `testing`
- Unity target: `audit_prefab_integrity`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
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
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `scope`: type=`enum`, required=`false`, enum=`active`, `loaded`
  - `include_inactive`: type=`boolean`, required=`false`
  - `max_issues`: type=`integer`, required=`false`

## batch_execute

Executes multiple MCP commands in a single batch for dramatically better performance. STRONGLY RECOMMENDED when creating/modifying multiple objects, adding components to multiple targets, or performing any repetitive operations. Reduces latency and token costs by 10-100x compared to sequential tool calls. The max commands per batch is configurable in the Unity MCP Tools window (default 25, hard max 100). Example: creating 5 cubes → use 1 batch_execute with 5 create commands instead of 5 separate calls.

- Group: `core`
- Unity target: `batch_execute`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `true`
- Parameters:
  - `commands`: type=`array`, required=`true`
  - `parallel`: type=`boolean`, required=`false`
  - `fail_fast`: type=`boolean`, required=`false`
  - `max_parallelism`: type=`integer`, required=`false`

## build_asset_index

Build and maintain a searchable index of Unity project assets. Supports full rebuilds, incremental updates, and index persistence. The index enables fast asset discovery without repeated Unity queries.

- Group: `asset_intelligence`
- Unity target: `build_asset_index`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `build`, `clear`, `update`, `validate`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`build`, `clear`, `update`, `validate`
  - `scope`: type=`string`, required=`false`
  - `include_types`: type=`array`, required=`false`
  - `exclude_paths`: type=`array`, required=`false`
  - `include_dependencies`: type=`boolean`, required=`false`
  - `include_references`: type=`boolean`, required=`false`
  - `include_import_settings`: type=`boolean`, required=`false`
  - `max_depth`: type=`integer`, required=`false`
  - `force_rebuild`: type=`boolean`, required=`false`
- Action contracts:
  - `build`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `clear`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `update`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `validate`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## build_code_index

Build or update the code intelligence index.
        
Works WITHOUT Unity running - uses local file system.
Indexes all C# files in Assets/ (and optionally Packages/).
The index is cached for fast subsequent lookups.

- Group: `core`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `project_root`: type=`string`, required=`false`
  - `include_packages`: type=`boolean`, required=`false`
  - `force_rebuild`: type=`boolean`, required=`false`

## clear_traces

Clear trace history. Can clear specific traces or all completed traces. Active traces are not cleared unless explicitly specified.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `trace_id`: type=`string`, required=`false`
  - `clear_active`: type=`boolean`, required=`false`

## code_index_status

Get code intelligence index status and statistics.
        
Returns information about indexed files, symbol counts, etc.

- Group: `core`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `project_root`: type=`string`, required=`false`

## compare_benchmarks

Compare two benchmark runs to detect performance regressions or improvements. Returns statistical comparison with percentage changes.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `baseline_run_id`: type=`string`, required=`true`
  - `comparison_run_id`: type=`string`, required=`true`

## configure_replay_scenario

Configure scenario injection for replay sessions. Modify replay behavior with error injection, latency, or data overrides.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `session_id`: type=`string`, required=`true`
  - `force_success`: type=`boolean`, required=`false`
  - `force_error`: type=`string`, required=`false`
  - `inject_latency_ms`: type=`integer`, required=`false`
  - `data_overrides`: type=`object`, required=`false`

## create_playbook

Create a playbook from a pipeline or step definitions. Playbooks are reusable templates for common Unity workflows. Can create from existing pipelines or define steps directly. Built-in playbooks: basic_player_controller, ui_canvas_setup, scene_lighting_setup

- Group: `pipeline`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `from_pipeline`, `from_steps`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`from_pipeline`, `from_steps`
  - `name`: type=`string`, required=`true`
  - `description`: type=`string`, required=`false`
  - `pipeline_name`: type=`string`, required=`false`
  - `steps`: type=`array`, required=`false`
  - `category`: type=`string`, required=`false`
  - `tags`: type=`array`, required=`false`
  - `parameters`: type=`object`, required=`false`
  - `overwrite`: type=`boolean`, required=`false`
- Action contracts:
  - `from_pipeline`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `from_steps`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## create_script

Create a new C# script at the given project path.

- Group: `core`
- Unity target: `manage_script`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
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
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`

## delete_fixture

Delete a specific fixture by ID or delete all fixtures matching filters.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `fixture_id`: type=`string`, required=`false`
  - `scenario`: type=`string`, required=`false`

## delete_script

Delete a C# script by URI or Assets-relative path.

- Group: `core`
- Unity target: `manage_script`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `true`
- Parameters:
  - `uri`: type=`string`, required=`true`

## diff_asset

Compare Unity assets and generate structured diffs. Supports comparing any Unity asset type (materials, textures, scripts, etc.), showing import setting changes, and binary asset comparison via hash. Returns a structured diff that can be used for review and verification workflows.

- Group: `diff_patch`
- Unity target: `diff_asset`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `source_path`: type=`string`, required=`true`
  - `target_path`: type=`string`, required=`false`
  - `compare_mode`: type=`enum`, required=`false`, enum=`check_import_settings`, `current_vs_saved`, `two_assets`
  - `include_binary`: type=`boolean | string`, required=`false`
  - `include_import_settings`: type=`boolean | string`, required=`false`

## diff_prefab

Compare Unity prefabs and generate structured diffs. Supports comparing prefab asset against instance, comparing two prefab variants, and showing prefab override information. Returns a structured diff that can be used for review, dry-run flows, and patch generation.

- Group: `diff_patch`
- Unity target: `diff_prefab`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `compare_mode`: type=`enum`, required=`true`, enum=`asset_vs_instance`, `show_overrides`, `two_prefabs`
  - `source_prefab`: type=`string`, required=`true`
  - `target_prefab`: type=`string`, required=`false`
  - `include_unchanged`: type=`boolean | string`, required=`false`
  - `show_override_details`: type=`boolean | string`, required=`false`

## diff_scene

Compare Unity scenes and generate structured diffs. Supports comparing active scene against saved version, two open scenes, or scene states at different checkpoints. Returns a structured diff with hierarchy, component, and property changes that can be used for review, dry-run flows, and patch generation.

- Group: `diff_patch`
- Unity target: `diff_scene`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `compare_mode`: type=`enum`, required=`true`, enum=`active_vs_saved`, `checkpoint`, `two_scenes`
  - `source_scene`: type=`string`, required=`false`
  - `target_scene`: type=`string`, required=`false`
  - `source_checkpoint_id`: type=`string`, required=`false`
  - `target_checkpoint_id`: type=`string`, required=`false`
  - `include_unchanged`: type=`boolean | string`, required=`false`
  - `max_depth`: type=`integer | string`, required=`false`

## execute_custom_tool

Execute a project-scoped custom tool registered by Unity.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `true`
- Parameters:
  - `tool_name`: type=`string`, required=`true`
  - `parameters`: type=`dict | string`, required=`false`

## execute_menu_item

Execute a Unity menu item by path.

- Group: `core`
- Unity target: `execute_menu_item`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `true`
- Parameters:
  - `menu_path`: type=`string`, required=`false`

## execute_runtime_command

Execute a command in runtime context (Play Mode or Built Game). Commands are routed to the Runtime MCP Bridge in the active Unity instance. Use list_runtime_tools to discover available commands. REQUIRES active Play Mode or Built Game connection.

- Group: `core`
- Unity target: `server-only`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `true`
- Requires explicit opt-in: `true`
- Parameters:
  - `command`: type=`string`, required=`true`
  - `parameters`: type=`object | string`, required=`false`
  - `timeout_seconds`: type=`number`, required=`false`
  - `wait_for_completion`: type=`boolean | string`, required=`false`

## find_asset_references

Find asset references bidirectionally. Discover what assets reference a target asset (dependents) and what assets the target references (dependencies). Includes reference path finding and impact analysis.

- Group: `asset_intelligence`
- Unity target: `find_asset_references`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `analyze_impact`, `find_circular`, `find_dependencies`, `find_dependents`, `find_path`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`analyze_impact`, `find_circular`, `find_dependencies`, `find_dependents`, `find_path`
  - `asset_path`: type=`string`, required=`false`
  - `asset_guid`: type=`string`, required=`false`
  - `target_asset_path`: type=`string`, required=`false`
  - `target_asset_guid`: type=`string`, required=`false`
  - `direction`: type=`enum`, required=`false`, enum=`both`, `downstream`, `upstream`
  - `max_depth`: type=`integer`, required=`false`
  - `include_indirect`: type=`boolean`, required=`false`
  - `filter_types`: type=`array`, required=`false`
  - `search_scope`: type=`string`, required=`false`
  - `include_usage_context`: type=`boolean`, required=`false`
- Action contracts:
  - `analyze_impact`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `find_circular`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `find_dependencies`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `find_dependents`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `find_path`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

## find_builtin_assets

Find and search Unity built-in assets. Read-only actions: search, list_by_type. Find built-in textures, meshes, materials, and other default assets.

- Group: `project_config`
- Unity target: `find_builtin_assets`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `list_by_type`, `search`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`list_by_type`, `search`
  - `search_pattern`: type=`string`, required=`false`
  - `asset_type`: type=`string`, required=`false`
  - `max_results`: type=`integer`, required=`false`
  - `include_preview`: type=`boolean`, required=`false`
- Action contracts:
  - `list_by_type`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `search`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## find_gameobjects

Search for GameObjects in the scene by name, tag, layer, component type, or path. Returns instance IDs only (paginated). Then use mcpforunity://scene/gameobject/{id} resource for full data, or mcpforunity://scene/gameobject/{id}/components for component details. For CRUD operations (create/modify/delete), use manage_gameobject instead.

- Group: `core`
- Unity target: `find_gameobjects`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
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
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `uri`: type=`string`, required=`true`
  - `pattern`: type=`string`, required=`true`
  - `project_root`: type=`string`, required=`false`
  - `max_results`: type=`integer`, required=`false`
  - `ignore_case`: type=`boolean | string`, required=`false`

## find_references

Find all references to a symbol across the codebase.
        
Works WITHOUT Unity running - uses local file system.
Returns all locations where the symbol is used.

- Group: `core`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `symbol_name`: type=`string`, required=`true`
  - `project_root`: type=`string`, required=`false`
  - `max_results`: type=`integer`, required=`false`

## find_symbol

Find definitions of classes, methods, properties, fields, etc.
        
Works WITHOUT Unity running - uses local file system.
Returns symbol details including file path, line number, modifiers, etc.

Example searches:
- symbol_name="PlayerController" - Find PlayerController class
- symbol_name="Update", symbol_type="method" - Find Update methods

- Group: `core`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `name`: type=`string`, required=`true`
  - `project_root`: type=`string`, required=`false`
  - `symbol_type`: type=`string`, required=`false`
  - `exact_match`: type=`boolean`, required=`false`

## focus_hierarchy

Focuses and expands a GameObject in the Unity Hierarchy window. Scrolls to make the GameObject visible, optionally expands its children, and can select the object. Use this to direct user attention to specific GameObjects in the scene hierarchy.

- Group: `navigation`
- Unity target: `focus_hierarchy`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `target`: type=`integer | object | string`, required=`true`
  - `expand`: type=`boolean`, required=`false`
  - `expand_depth`: type=`integer`, required=`false`
  - `select`: type=`boolean`, required=`false`
  - `frame_in_scene`: type=`boolean`, required=`false`
  - `highlight`: type=`boolean`, required=`false`

## frame_scene_target

Frames a target in the Unity Scene view camera. Can frame selected objects, a specific GameObject, or a world position. Also supports querying the current Scene view camera pose. Use this to direct user attention to specific areas of the scene.

- Group: `navigation`
- Unity target: `frame_scene_target`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `target_type`: type=`enum`, required=`false`, enum=`gameobject`, `position`, `query_camera`, `selection`
  - `target`: type=`integer | object | string`, required=`false`
  - `view_angle`: type=`enum`, required=`false`, enum=`back`, `bottom`, `current`, `front`, `left`, `perspective`, `right`, `top`
  - `distance`: type=`number`, required=`false`
  - `orthographic`: type=`boolean`, required=`false`
  - `duration`: type=`number`, required=`false`

## get_benchmark_results

Get detailed results from a benchmark run including all iterations and computed statistics.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `run_id`: type=`string`, required=`true`
  - `include_iterations`: type=`boolean`, required=`false`

## get_benchmark_trends

Get performance trends over time for a specific benchmark. Useful for tracking performance degradation or optimization progress.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `benchmark_name`: type=`string`, required=`true`
  - `points`: type=`integer`, required=`false`

## get_captured_fixtures

Get captured fixtures with optional filtering by scenario, tool, or tags. Returns fixture data including request/response pairs.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `scenario`: type=`string`, required=`false`
  - `tool`: type=`string`, required=`false`
  - `tags`: type=`array`, required=`false`
  - `limit`: type=`integer`, required=`false`

## get_command_stats

Retrieves command usage statistics for the MCP server. Returns metrics like total commands executed, success rates, most used tools, and error counts. Useful for monitoring and debugging.

- Group: `core`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Known read-only actions: `get_stats`
- Parameters:
  - `tool_filter`: type=`string`, required=`false`
  - `since_hours`: type=`integer`, required=`false`

## get_component_types

List and get information about Unity component types. Read-only actions: list_all, search, get_info. Discover built-in components, search for specific types, and get detailed component information.

- Group: `project_config`
- Unity target: `get_component_types`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `get_info`, `list_all`, `search`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`get_info`, `list_all`, `search`
  - `component_name`: type=`string`, required=`false`
  - `namespace`: type=`string`, required=`false`
  - `include_builtin`: type=`boolean`, required=`false`
  - `include_custom`: type=`boolean`, required=`false`
  - `max_results`: type=`integer`, required=`false`
  - `include_properties`: type=`boolean`, required=`false`
  - `include_methods`: type=`boolean`, required=`false`
- Action contracts:
  - `get_info`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `list_all`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `search`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## get_diagnostics

Gets comprehensive diagnostics for the Unity project in a single call. Aggregates: compile state, console errors/warnings, profiler snapshot, test results, scene dirty state, and prefab integrity. Use this for quick health checks before/after operations. Read-only operation - does not modify any project state.

- Group: `core`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `include_profiler`: type=`boolean | string`, required=`false`
  - `include_tests`: type=`boolean | string`, required=`false`
  - `include_scene_health`: type=`boolean | string`, required=`false`
  - `include_console`: type=`boolean | string`, required=`false`
  - `console_error_limit`: type=`integer | string`, required=`false`
  - `severity_threshold`: type=`enum`, required=`false`, enum=`error`, `info`, `warning`

## get_object_references

Find object references in Unity scenes and assets. Read-only actions: get_references, get_referenced_by. Helps understand object relationships in scenes and prefabs.

- Group: `project_config`
- Unity target: `get_object_references`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `get_referenced_by`, `get_references`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`get_referenced_by`, `get_references`
  - `target`: type=`string`, required=`true`
  - `search_scope`: type=`string`, required=`false`
  - `reference_type`: type=`string`, required=`false`
  - `max_results`: type=`integer`, required=`false`
  - `include_inactive`: type=`boolean`, required=`false`
- Action contracts:
  - `get_referenced_by`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_references`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## get_runtime_connection_info

Get runtime connection details including WebSocket endpoint and port. Runtime uses a separate connection from Editor MCP. Use this to establish direct runtime communication.

- Group: `core`
- Unity target: `server-only`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `true`
- Requires explicit opt-in: `true`

## get_runtime_status

Check if Runtime MCP is available and get runtime status. Returns connection state, active scene, play mode status, and available runtime tools. Use this to verify runtime context before executing runtime commands.

- Group: `core`
- Unity target: `server-only`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `true`
- Requires explicit opt-in: `true`
- Parameters:
  - `include_capabilities`: type=`boolean | string`, required=`false`

## get_sha

Get SHA256 and basic metadata for a Unity C# script without returning file contents. Requires uri (script path under Assets/ or mcpforunity://path/Assets/... or file://...).

- Group: `core`
- Unity target: `manage_script`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `uri`: type=`string`, required=`true`

## get_symbols

List all symbols in a file or across the codebase.
        
Works WITHOUT Unity running - uses local file system.
Can filter by symbol type and namespace.

- Group: `core`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `project_root`: type=`string`, required=`false`
  - `file_path`: type=`string`, required=`false`
  - `symbol_type`: type=`string`, required=`false`
  - `namespace`: type=`string`, required=`false`
  - `max_results`: type=`integer`, required=`false`

## get_test_job

Polls an async Unity test job by job_id.

- Group: `testing`
- Unity target: `get_test_job`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `job_id`: type=`string`, required=`true`
  - `include_failed_tests`: type=`boolean`, required=`false`
  - `include_details`: type=`boolean`, required=`false`
  - `wait_timeout`: type=`integer`, required=`false`

## get_trace_summary

Get a summary of traced operations without full trace data. Returns statistics like total requests, average latency, error counts, and tools used. Can query active or completed traces.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `trace_id`: type=`string`, required=`false`

## import_fixtures

Import fixtures from a JSON file. Useful for sharing fixtures between team members or loading pre-recorded scenarios.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `import_path`: type=`string`, required=`true`
  - `merge_scenario`: type=`string`, required=`false`

## list_benchmarks

List all benchmark runs with optional filtering by name or date range.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `benchmark_name`: type=`string`, required=`false`
  - `limit`: type=`integer`, required=`false`

## list_event_subscriptions

Lists all active event subscriptions with their status and event counts. Useful for debugging and monitoring subscription health.

- Group: `core`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `include_expired`: type=`boolean | string`, required=`false`

## list_pipelines

List saved pipelines or get details of a specific pipeline. Pipelines are searched in ProjectRoot/Pipelines/ and ~/.unity-mcp/pipelines/. Use to discover available automation workflows before replaying them.

- Group: `pipeline`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `get`, `list`
- Parameters:
  - `action`: type=`enum`, required=`false`, enum=`get`, `list`
  - `name`: type=`string`, required=`false`
  - `filter_tags`: type=`array`, required=`false`
  - `filter_author`: type=`string`, required=`false`
- Action contracts:
  - `get`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `list`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## list_playbooks

List available playbooks or get details of a specific playbook. Playbooks are reusable templates for common Unity workflows. Built-in playbooks include: basic_player_controller, ui_canvas_setup, scene_lighting_setup. Use run_playbook to execute them.

- Group: `pipeline`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `get`, `list`
- Parameters:
  - `action`: type=`enum`, required=`false`, enum=`get`, `list`
  - `playbook_id`: type=`string`, required=`false`
  - `filter_category`: type=`string`, required=`false`
  - `filter_tags`: type=`array`, required=`false`
- Action contracts:
  - `get`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `list`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## list_replay_sessions

List all active replay sessions with their status and configuration.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`

## list_runtime_tools

List tools available in runtime context. Returns runtime-only tools that can be executed in Play Mode or Built Games. These tools are separate from Editor-only tools and have different capabilities.

- Group: `core`
- Unity target: `server-only`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `true`
- Requires explicit opt-in: `true`
- Parameters:
  - `category`: type=`enum`, required=`false`, enum=`all`, `debug`, `gameobject`, `input`, `physics`, `scene`
  - `include_metadata`: type=`boolean | string`, required=`false`

## list_shaders

List and get information about Unity shaders. Read-only actions: list_builtin, list_custom, get_shader_info. Helps discover available shaders for materials and understand their properties.

- Group: `project_config`
- Unity target: `list_shaders`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `get_shader_info`, `list_builtin`, `list_custom`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`get_shader_info`, `list_builtin`, `list_custom`
  - `shader_name`: type=`string`, required=`false`
  - `search_pattern`: type=`string`, required=`false`
  - `include_properties`: type=`boolean`, required=`false`
  - `folder_path`: type=`string`, required=`false`
- Action contracts:
  - `get_shader_info`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `list_builtin`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `list_custom`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## list_traces

List all available trace sessions (both active and completed). Returns trace IDs with basic metadata for each.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `include_completed`: type=`boolean`, required=`false`

## manage_addressables

Manages Unity Addressable Asset System.

Read-only actions: analyze, get_groups, get_group_assets, get_labels, validate, get_settings.
Build actions (high_risk): build, build_player, clean_build.
Modifying actions (high_risk): create_group, delete_group, add_asset, remove_asset, move_asset, assign_label, remove_label.

Use 'dry_run=true' for build operations to preview changes without executing.
Supports multiple platforms: StandaloneWindows64, StandaloneOSX, StandaloneLinux64, iOS, Android, WebGL, PS5, XboxSeriesX.

- Group: `core`
- Unity target: `manage_addressables`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `add_asset`, `analyze`, `assign_label`, `build`, `build_player`, `clean_build`, `create_group`, `delete_group`, `get_group_assets`, `get_groups`, `get_labels`, `get_settings`, `move_asset`, `remove_asset`, `remove_label`, `validate`
- Known read-only actions: `analyze`, `get_group_assets`, `get_groups`, `get_labels`, `get_settings`, `validate`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`add_asset`, `analyze`, `assign_label`, `build`, `build_player`, `clean_build`, `create_group`, `delete_group`, `get_group_assets`, `get_groups`, `get_labels`, `get_settings`, `move_asset`, `remove_asset`, `remove_label`, `validate`
  - `group_name`: type=`string`, required=`false`
  - `asset_path`: type=`string`, required=`false`
  - `address`: type=`string`, required=`false`
  - `labels`: type=`array`, required=`false`
  - `platform`: type=`string`, required=`false`
  - `dry_run`: type=`boolean`, required=`false`
  - `clean`: type=`boolean`, required=`false`
  - `target_group`: type=`string`, required=`false`
  - `report_path`: type=`string`, required=`false`
  - `settings_path`: type=`string`, required=`false`
  - `page_size`: type=`integer | string`, required=`false`
  - `page_number`: type=`integer | string`, required=`false`
- Action contracts:
  - `add_asset`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `analyze`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `assign_label`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `build`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `build_player`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `clean_build`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `create_group`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `delete_group`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `get_group_assets`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_groups`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_labels`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_settings`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `move_asset`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `remove_asset`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `remove_label`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `validate`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

## manage_animation

Manage Unity animation: Animator control and AnimationClip creation. Action prefixes: animator_* (play, crossfade, set parameters, get info), controller_* (create AnimatorControllers, add states/transitions/parameters), clip_* (create clips, add keyframe curves, assign to GameObjects). Action-specific parameters go in `properties` (keys match ManageAnimation.cs).

- Group: `animation`
- Unity target: `manage_animation`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
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
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
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
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `create_folder`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `duplicate`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `get_components`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_info`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `import`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `modify`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `move`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `rename`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `search`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

## manage_asset_import_settings

Manage Unity asset import settings for different asset types. Read-only actions: get_import_settings. Modifying actions: update_import_settings. Supports textures, models, audio, video, and other asset types.

- Group: `project_config`
- Unity target: `manage_asset_import_settings`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `get_import_settings`, `update_import_settings`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`get_import_settings`, `update_import_settings`
  - `asset_path`: type=`string`, required=`true`
  - `importer_type`: type=`string`, required=`false`
  - `settings`: type=`object`, required=`false`
  - `platform`: type=`string`, required=`false`
- Action contracts:
  - `get_import_settings`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `update_import_settings`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_build_settings

Manage Unity Build Settings including scenes, target platform, and build configuration. Read-only actions: get_build_settings, get_scenes_in_build. Modifying actions: set_build_settings, add_scene_to_build, remove_scene_from_build, set_build_platform (high-risk). Platform switching requires explicit confirmation.

- Group: `pipeline_control`
- Unity target: `manage_build_settings`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `add_scene_to_build`, `get_build_settings`, `get_scenes_in_build`, `remove_scene_from_build`, `set_build_platform`, `set_build_settings`
- Known read-only actions: `get_build_settings`, `get_scenes_in_build`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`add_scene_to_build`, `get_build_settings`, `get_scenes_in_build`, `remove_scene_from_build`, `set_build_platform`, `set_build_settings`
  - `scene_path`: type=`string`, required=`false`
  - `scene_enabled`: type=`boolean`, required=`false`
  - `settings`: type=`object`, required=`false`
  - `target_platform`: type=`string`, required=`false`
  - `output_path`: type=`string`, required=`false`
- Action contracts:
  - `add_scene_to_build`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_build_settings`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_scenes_in_build`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `remove_scene_from_build`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_build_platform`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_build_settings`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_catalog

List, query, or export the generated Unity MCP tool catalog built from the live tool registry and action policy metadata. Actions: list (full catalog), get_tool (specific tool capabilities), query (filtered search), export (save to disk).

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `export`, `get_tool`, `list`, `query`
- Known read-only actions: `get_tool`, `list`, `query`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`export`, `get_tool`, `list`, `query`
  - `output_dir`: type=`string`, required=`false`
  - `format`: type=`enum`, required=`false`, enum=`both`, `json`, `markdown`
  - `tool_name`: type=`string`, required=`false`
  - `capability_filter`: type=`string`, required=`false`
- Action contracts:
  - `export`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_tool`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `list`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `query`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

## manage_checkpoints

Create, inspect, verify, restore, and delete local file checkpoints for high-risk workflows. This tool is server-local and does not require Unity. Use create before large edits, verify for drift detection, and restore to roll back files.

- Group: `core`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `create`, `delete`, `inspect`, `list`, `restore`, `verify`
- Known read-only actions: `inspect`, `list`, `verify`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`create`, `delete`, `inspect`, `list`, `restore`, `verify`
  - `checkpoint_id`: type=`string`, required=`false`
  - `name`: type=`string`, required=`false`
  - `note`: type=`string`, required=`false`
  - `paths`: type=`array | string`, required=`false`
  - `dry_run`: type=`boolean | string`, required=`false`
- Action contracts:
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `inspect`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `list`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `restore`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `verify`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

## manage_code_intelligence

Local code intelligence for Unity C# projects - works WITHOUT Unity running!
        
Actions:
- search_code: Search across all C# files using regex or text search
- find_symbol: Find class/method/field definitions by name  
- find_references: Find all references to a symbol
- get_symbols: List all symbols in a file or across the codebase
- build_code_index: Build/update the searchable code index
- update_code_index: Incrementally update based on file changes
- get_index_status: Get index statistics
- clear_code_index: Clear the index cache

This tool indexes your C# code locally using file system operations only.
The index is cached for fast lookups and supports incremental updates.

- Group: `core`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `build_code_index`, `clear_code_index`, `find_references`, `find_symbol`, `get_index_status`, `get_symbols`, `search_code`, `update_code_index`
- Known read-only actions: `find_references`, `find_symbol`, `get_index_status`, `get_symbols`, `search_code`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`build_code_index`, `clear_code_index`, `find_references`, `find_symbol`, `get_index_status`, `get_symbols`, `search_code`, `update_code_index`
  - `project_root`: type=`string`, required=`false`
  - `pattern`: type=`string`, required=`false`
  - `use_regex`: type=`boolean`, required=`false`
  - `ignore_case`: type=`boolean`, required=`false`
  - `file_pattern`: type=`string`, required=`false`
  - `symbol_name`: type=`string`, required=`false`
  - `symbol_type`: type=`string`, required=`false`
  - `exact_match`: type=`boolean`, required=`false`
  - `file_path`: type=`string`, required=`false`
  - `namespace`: type=`string`, required=`false`
  - `include_packages`: type=`boolean`, required=`false`
  - `force_rebuild`: type=`boolean`, required=`false`
  - `offset`: type=`integer`, required=`false`
  - `max_results`: type=`integer`, required=`false`
- Action contracts:
  - `build_code_index`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `clear_code_index`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `find_references`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `find_symbol`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_index_status`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_symbols`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `search_code`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `update_code_index`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_components

Add, remove, or set properties on components attached to GameObjects. Actions: add, remove, set_property. Requires target (instance ID or name) and component_type. For READING component data, use the mcpforunity://scene/gameobject/{id}/components resource or mcpforunity://scene/gameobject/{id}/component/{name} for a single component. For creating/deleting GameObjects themselves, use manage_gameobject instead.

- Group: `core`
- Unity target: `manage_components`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
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
  - `add`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `remove`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `set_property`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`

## manage_define_symbols

Manage Unity Scripting Define Symbols for conditional compilation. Read-only actions: get_define_symbols. Modifying actions: add_define_symbol, remove_define_symbol, set_define_symbols. Changes trigger script recompilation.

- Group: `pipeline_control`
- Unity target: `manage_define_symbols`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `add_define_symbol`, `get_define_symbols`, `remove_define_symbol`, `set_define_symbols`
- Known read-only actions: `get_define_symbols`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`add_define_symbol`, `get_define_symbols`, `remove_define_symbol`, `set_define_symbols`
  - `platform`: type=`string`, required=`false`
  - `symbol`: type=`string`, required=`false`
  - `symbols`: type=`array`, required=`false`
- Action contracts:
  - `add_define_symbol`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_define_symbols`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `remove_define_symbol`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_define_symbols`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_editor

Controls and queries the Unity editor's state and settings. Tip: pass booleans as true/false; if your client only sends strings, 'true'/'false' are accepted. Read-only actions: telemetry_status, telemetry_ping. Modifying actions: play, pause, stop, set_active_tool, add_tag, remove_tag, add_layer, remove_layer, quit_editor. WARNING: quit_editor requires explicit opt-in and will close the Unity Editor.

- Group: `core`
- Unity target: `manage_editor`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `add_layer`, `add_tag`, `pause`, `play`, `quit_editor`, `remove_layer`, `remove_tag`, `set_active_tool`, `stop`, `telemetry_ping`, `telemetry_status`
- Known read-only actions: `telemetry_ping`, `telemetry_status`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`add_layer`, `add_tag`, `pause`, `play`, `quit_editor`, `remove_layer`, `remove_tag`, `set_active_tool`, `stop`, `telemetry_ping`, `telemetry_status`
  - `wait_for_completion`: type=`boolean | string`, required=`false`
  - `tool_name`: type=`string`, required=`false`
  - `tag_name`: type=`string`, required=`false`
  - `layer_name`: type=`string`, required=`false`
  - `confirm_quit`: type=`boolean | string`, required=`false`
- Action contracts:
  - `add_layer`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `add_tag`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `pause`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `play`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `quit_editor`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `remove_layer`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `remove_tag`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_active_tool`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `stop`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `telemetry_ping`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `telemetry_status`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

## manage_editor_settings

Manage Unity Editor preferences and settings. Read-only actions: get_preferences. Modifying actions: update_preferences (safe settings only). Provides access to editor preferences that can be safely read and modified.

- Group: `project_config`
- Unity target: `manage_editor_settings`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `get_preferences`, `update_preferences`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`get_preferences`, `update_preferences`
  - `preference_category`: type=`string`, required=`false`
  - `preferences`: type=`object`, required=`false`
- Action contracts:
  - `get_preferences`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `update_preferences`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_error_catalog

List, query, or export the generated error-code and operational-contract catalog for this fork. Actions: list (full catalog), get_code (specific error details), get_for_surface (codes by tool), export (save to disk).

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `export`, `get_code`, `get_for_surface`, `list`
- Known read-only actions: `get_code`, `get_for_surface`, `list`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`export`, `get_code`, `get_for_surface`, `list`
  - `output_dir`: type=`string`, required=`false`
  - `format`: type=`enum`, required=`false`, enum=`both`, `json`, `markdown`
  - `code`: type=`string`, required=`false`
  - `surface`: type=`string`, required=`false`
- Action contracts:
  - `export`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_code`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_for_surface`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `list`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

## manage_gameobject

Performs CRUD operations on GameObjects. Actions: create, modify, delete, duplicate, move_relative, look_at. NOT for searching — use the find_gameobjects tool to search by name/tag/layer/component/path. NOT for component management — use the manage_components tool (add/remove/set_property) or mcpforunity://scene/gameobject/{id}/components resource (read).

- Group: `core`
- Unity target: `manage_gameobject`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `true`
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
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `duplicate`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `look_at`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `modify`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `move_relative`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`

## manage_import_pipeline

Manage Unity Asset Import Pipeline including reimport, reserialize, and import control. Read-only actions: get_import_queue_status. Modifying actions: force_reimport, force_reserialize (high-risk), pause_import, resume_import. Mass reimport/reserialize require explicit confirmation.

- Group: `pipeline_control`
- Unity target: `manage_import_pipeline`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `force_reimport`, `force_reserialize`, `get_import_queue_status`, `pause_import`, `resume_import`
- Known read-only actions: `get_import_queue_status`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`force_reimport`, `force_reserialize`, `get_import_queue_status`, `pause_import`, `resume_import`
  - `asset_paths`: type=`array`, required=`false`
  - `options`: type=`object`, required=`false`
- Action contracts:
  - `force_reimport`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `force_reserialize`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_import_queue_status`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `pause_import`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `resume_import`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_input_system

Manage Unity Input System - Action Maps, Actions, Bindings, Control Schemes, and Runtime Simulation. Action prefixes: actionmap_* (manage maps), action_* (manage actions), binding_* (manage bindings), scheme_* (control schemes), asset_* (Input Action assets), simulate_* (runtime input simulation - high risk), state_* (read input state). Runtime simulation actions require play mode and are marked as high risk.

- Group: `input`
- Unity target: `manage_input_system`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Known read-only actions: `action_get`, `action_get_all`, `actionmap_get`, `actionmap_get_all`, `asset_get_all`, `asset_get_info`, `binding_get_all`, `scheme_get_all`, `state_get_action_value`, `state_get_all_actions`, `state_get_control_value`, `state_is_action_pressed`
- Parameters:
  - `action`: type=`string`, required=`true`
  - `asset_path`: type=`string`, required=`false`
  - `action_map`: type=`string`, required=`false`
  - `action_name`: type=`string`, required=`false`
  - `properties`: type=`object | string`, required=`false`

## manage_material

Manages Unity materials (set properties, colors, shaders, etc). Read-only actions: ping, get_material_info. Modifying actions: create, set_material_shader_property, set_material_color, assign_material_to_renderer, set_renderer_color.

- Group: `core`
- Unity target: `manage_material`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
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
  - `assign_material_to_renderer`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `get_material_info`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `ping`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `set_material_color`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `set_material_shader_property`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `set_renderer_color`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`

## manage_package_manager

Manages Unity Package Manager packages and dependencies.

Read-only actions (safe): list_installed, search_packages, get_package_info, list_registries.
Mutating actions (modifies project): add_package, remove_package, resolve_dependencies.

Supports all package sources: registry, git, local path, tarball.
Returns structured data with name, version, source, and dependencies.

- Group: `core`
- Unity target: `manage_package_manager`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `add_package`, `get_package_info`, `list_installed`, `list_registries`, `remove_package`, `resolve_dependencies`, `search_packages`
- Known read-only actions: `get_package_info`, `list_installed`, `list_registries`, `search_packages`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`add_package`, `get_package_info`, `list_installed`, `list_registries`, `remove_package`, `resolve_dependencies`, `search_packages`
  - `package_name`: type=`string`, required=`false`
  - `version`: type=`string`, required=`false`
  - `search_query`: type=`string`, required=`false`
  - `page_size`: type=`integer | number | string`, required=`false`
  - `page`: type=`integer | number | string`, required=`false`
  - `include_prerelease`: type=`boolean | string`, required=`false`
  - `source_filter`: type=`enum`, required=`false`, enum=`all`, `built-in`, `git`, `local`, `registry`, `tarball`
  - `git_ref`: type=`string`, required=`false`
- Action contracts:
  - `add_package`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_package_info`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `list_installed`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `list_registries`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `remove_package`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `resolve_dependencies`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `search_packages`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

## manage_player_settings

Manage Unity Player Settings including company info, product info, version, resolution, and publishing configuration. Read-only actions: get_player_settings, get_resolution_settings, get_publishing_settings. Modifying actions: set_player_settings, set_resolution_settings.

- Group: `pipeline_control`
- Unity target: `manage_player_settings`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `get_player_settings`, `get_publishing_settings`, `get_resolution_settings`, `set_player_settings`, `set_resolution_settings`
- Known read-only actions: `get_player_settings`, `get_publishing_settings`, `get_resolution_settings`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`get_player_settings`, `get_publishing_settings`, `get_resolution_settings`, `set_player_settings`, `set_resolution_settings`
  - `settings`: type=`object`, required=`false`
  - `platform`: type=`string`, required=`false`
- Action contracts:
  - `get_player_settings`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_publishing_settings`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_resolution_settings`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `set_player_settings`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_resolution_settings`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_prefabs

Manages Unity Prefab assets. Actions: get_info, get_hierarchy, create_from_gameobject, modify_contents, open_stage, save_open_stage, close_stage. Use modify_contents for headless prefab editing - ideal for automated workflows. Use open_stage/edit/save_open_stage/close_stage for interactive prefab editing in isolation mode. Use create_child parameter with modify_contents to add child GameObjects to a prefab (single object or array for batch creation in one save). Example: create_child=[{"name": "Child1", "primitive_type": "Sphere", "position": [1,0,0]}, {"name": "Child2", "primitive_type": "Cube", "parent": "Child1"}]. Use component_properties with modify_contents to set serialized fields on existing components (e.g. component_properties={"Rigidbody": {"mass": 5.0}, "MyScript": {"health": 100}}). Supports object references via {"guid": "..."}, {"path": "Assets/..."}, or {"instanceID": 123}. Use manage_asset action=search filterType=Prefab to list prefabs.

- Group: `core`
- Unity target: `manage_prefabs`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `close_stage`, `create_from_gameobject`, `get_hierarchy`, `get_info`, `modify_contents`, `open_stage`, `save_open_stage`
- Known read-only actions: `get_hierarchy`, `get_info`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`close_stage`, `create_from_gameobject`, `get_hierarchy`, `get_info`, `modify_contents`, `open_stage`, `save_open_stage`
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
  - `create_child`: type=`array | object | string`, required=`false`
  - `component_properties`: type=`object | string`, required=`false`
  - `save_changes`: type=`boolean`, required=`false`
- Action contracts:
  - `close_stage`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `create_from_gameobject`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `get_hierarchy`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_info`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `modify_contents`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `open_stage`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `save_open_stage`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`

## manage_profiler

Manages Unity Profiler sessions and data collection. Actions: start/stop (mutating) control profiling sessions; get_status, get_snapshot (read-only) query current state; get_memory, get_cpu, get_rendering, get_audio (read-only) get detailed breakdowns; clear (mutating) removes collected data; save_capture, load_capture (mutating) manage capture files; set_categories (mutating) enable/disable profiler categories.

- Group: `profiling`
- Unity target: `manage_profiler`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `clear`, `get_audio`, `get_cpu`, `get_memory`, `get_rendering`, `get_snapshot`, `get_status`, `load_capture`, `save_capture`, `set_categories`, `start`, `stop`
- Known read-only actions: `get_audio`, `get_cpu`, `get_memory`, `get_rendering`, `get_snapshot`, `get_status`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`clear`, `get_audio`, `get_cpu`, `get_memory`, `get_rendering`, `get_snapshot`, `get_status`, `load_capture`, `save_capture`, `set_categories`, `start`, `stop`
  - `interval_frames`: type=`integer | string`, required=`false`
  - `deep_profiling`: type=`boolean | string`, required=`false`
  - `file_path`: type=`string`, required=`false`
  - `categories`: type=`array | string`, required=`false`
  - `enable`: type=`boolean | string`, required=`false`
  - `wait_for_completion`: type=`boolean | string`, required=`false`
- Action contracts:
  - `clear`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_audio`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_cpu`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_memory`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_rendering`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_snapshot`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_status`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `load_capture`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `save_capture`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_categories`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `start`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `stop`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_project_memory

Manage project memory and rules for Unity MCP. Actions: load_rules (read rules file), save_rules (write rules), summarize_conventions (get conventions summary), get_active_rules (rules by category), validate_against_rules (check content - advisory only). Rules stored in .unity-mcp-rules or UnityMCPRules.md in project root.

- Group: `project_config`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `get_active_rules`, `load_rules`, `save_rules`, `summarize_conventions`, `validate_against_rules`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`get_active_rules`, `load_rules`, `save_rules`, `summarize_conventions`, `validate_against_rules`
  - `path`: type=`string`, required=`false`
  - `rules`: type=`object`, required=`false`
  - `format`: type=`enum`, required=`false`, enum=`json`, `markdown`, `yaml`
  - `category`: type=`enum`, required=`false`, enum=`all`, `code_style`, `naming`, `organization`, `validation`
  - `content_type`: type=`enum`, required=`false`, enum=`asset`, `prefab`, `scene`, `script`
  - `content_path`: type=`string`, required=`false`
- Action contracts:
  - `get_active_rules`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `load_rules`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `save_rules`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `summarize_conventions`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `validate_against_rules`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_project_settings

Manage Unity project settings and build configuration. Read-only actions: get_settings, get_build_settings. Modifying actions: update_settings, update_build_settings. Provides access to Player Settings, project metadata, and build configuration.

- Group: `project_config`
- Unity target: `manage_project_settings`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `get_build_settings`, `get_settings`, `update_build_settings`, `update_settings`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`get_build_settings`, `get_settings`, `update_build_settings`, `update_settings`
  - `settings_category`: type=`string`, required=`false`
  - `settings`: type=`object`, required=`false`
  - `platform`: type=`string`, required=`false`
- Action contracts:
  - `get_build_settings`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_settings`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `update_build_settings`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `update_settings`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_reflection

Runtime reflection and object introspection for Unity. DISCOVER types, methods, properties, and fields. INSPECT and optionally MODIFY objects at runtime. WARNING: DISABLED BY DEFAULT - requires reflection_enabled config. High-risk operations (invoke_method, set_property, set_field, create_instance) allow arbitrary code execution - use with extreme caution.

- Group: `core`
- Unity target: `manage_reflection`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `clear_cache`, `create_instance`, `discover_fields`, `discover_methods`, `discover_properties`, `find_objects`, `get_capability_status`, `get_field`, `get_property`, `get_type_info`, `invoke_method`, `set_field`, `set_property`
- Known read-only actions: `discover_fields`, `discover_methods`, `discover_properties`, `find_objects`, `get_capability_status`, `get_field`, `get_property`, `get_type_info`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`clear_cache`, `create_instance`, `discover_fields`, `discover_methods`, `discover_properties`, `find_objects`, `get_capability_status`, `get_field`, `get_property`, `get_type_info`, `invoke_method`, `set_field`, `set_property`
  - `target_type`: type=`string`, required=`false`
  - `target_object`: type=`integer | string`, required=`false`
  - `member_name`: type=`string`, required=`false`
  - `parameters`: type=`array | object`, required=`false`
  - `value`: type=`Any`, required=`false`
  - `binding_flags`: type=`enum`, required=`false`, enum=`all`, `non_public`, `public`
  - `include_static`: type=`boolean`, required=`false`
  - `include_instance`: type=`boolean`, required=`false`
  - `search_assemblies`: type=`array | string`, required=`false`
  - `scene_path`: type=`string`, required=`false`
  - `high_risk_confirmed`: type=`boolean`, required=`false`
- Action contracts:
  - `clear_cache`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `create_instance`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `discover_fields`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `discover_methods`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `discover_properties`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `find_objects`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_capability_status`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_field`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_property`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_type_info`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `invoke_method`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_field`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_property`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_registry_config

Manage Unity Package Manager scoped registries. Read-only actions: list_scoped_registries. Modifying actions: add_registry, remove_registry, update_registry. Scoped registries allow using custom package registries for private or custom packages.

- Group: `project_config`
- Unity target: `manage_registry_config`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `add_registry`, `list_scoped_registries`, `remove_registry`, `update_registry`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`add_registry`, `list_scoped_registries`, `remove_registry`, `update_registry`
  - `registry_name`: type=`string`, required=`false`
  - `registry_url`: type=`string`, required=`false`
  - `scopes`: type=`array`, required=`false`
  - `new_name`: type=`string`, required=`false`
- Action contracts:
  - `add_registry`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `list_scoped_registries`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `remove_registry`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `update_registry`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_runtime_ui

Runtime UI automation for Play mode - interact with uGUI and UI Toolkit elements. WARNING: Only works during Play mode. High-risk tool that simulates user input. 

Actions:
- find_elements: Search UI elements by type, name, text, or automation ID
- get_element_state: Get element properties (text, enabled, visible, position, hierarchy path)
- click: Simulate click/tap on a button or any interactive element
- set_text: Enter text into InputField or TextField
- set_value: Set Slider value, Toggle state, or Dropdown index
- scroll: Scroll a ScrollView or ScrollRect
- hover: Move cursor over element (triggers hover states)
- wait_for_element: Poll until element appears or timeout
- get_screenshot: Capture screenshot of specific UI element


Supported UI Systems:
- uGUI: Canvas-based UI (GameObject hierarchy)
- UI Toolkit: Runtime VisualElement-based UI


Element Queries:
- Query by name: element name/path
- Query by type: Button, InputField, Slider, etc.
- Query by text content: button label, input placeholder
- Query by automation ID: data-testid or name attribute

- Group: `ui`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `true`
- Requires explicit opt-in: `true`
- Supported actions: `click`, `find_elements`, `get_element_state`, `get_screenshot`, `hover`, `scroll`, `set_text`, `set_value`, `wait_for_element`
- Known read-only actions: `find_elements`, `get_element_state`, `get_screenshot`, `wait_for_element`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`click`, `find_elements`, `get_element_state`, `get_screenshot`, `hover`, `scroll`, `set_text`, `set_value`, `wait_for_element`
  - `ui_system`: type=`enum`, required=`false`, enum=`auto`, `ugui`, `uitoolkit`
  - `element_path`: type=`string`, required=`false`
  - `element_name`: type=`string`, required=`false`
  - `element_type`: type=`string`, required=`false`
  - `element_text`: type=`string`, required=`false`
  - `automation_id`: type=`string`, required=`false`
  - `text`: type=`string`, required=`false`
  - `value`: type=`boolean | integer | number`, required=`false`
  - `scroll_delta`: type=`object`, required=`false`
  - `scroll_to_end`: type=`boolean`, required=`false`
  - `timeout_seconds`: type=`number`, required=`false`
  - `poll_interval`: type=`number`, required=`false`
  - `max_resolution`: type=`integer`, required=`false`
  - `include_image`: type=`boolean`, required=`false`
  - `max_results`: type=`integer`, required=`false`
  - `include_invisible`: type=`boolean`, required=`false`
- Action contracts:
  - `click`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `find_elements`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_element_state`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_screenshot`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `hover`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `scroll`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_text`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_value`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `wait_for_element`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

## manage_scene

Performs CRUD operations on Unity scenes. Read-only actions: get_hierarchy, get_active, get_build_settings, screenshot, scene_view_frame, list_opened. Modifying actions: create, load, save, set_active, unload. screenshot supports include_image=true to return an inline base64 PNG for AI vision. screenshot with batch='surround' captures 6 angles around the scene (no file saved) for comprehensive scene understanding. screenshot with batch='orbit' captures configurable azimuth x elevation grid for visual QA (use orbit_angles, orbit_elevations, orbit_distance, orbit_fov). screenshot with look_at/view_position creates a temp camera at that viewpoint and returns an inline image. Use list_opened to see all loaded scenes in additive mode, set_active to switch active scene, unload to remove additive scenes.

- Group: `core`
- Unity target: `manage_scene`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `true`
- Supported actions: `create`, `get_active`, `get_build_settings`, `get_hierarchy`, `list_opened`, `load`, `save`, `scene_view_frame`, `screenshot`, `set_active`, `unload`
- Known read-only actions: `get_active`, `get_build_settings`, `get_hierarchy`, `list_opened`, `scene_view_frame`, `screenshot`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`create`, `get_active`, `get_build_settings`, `get_hierarchy`, `list_opened`, `load`, `save`, `scene_view_frame`, `screenshot`, `set_active`, `unload`
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
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `get_active`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_build_settings`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `get_hierarchy`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `list_opened`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `load`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `save`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `scene_view_frame`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `screenshot`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `set_active`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `unload`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`

## manage_script

Compatibility router for legacy script operations. Prefer apply_text_edits (ranges) or script_apply_edits (structured) for edits. Read-only action: read. Modifying actions: create, delete.

- Group: `core`
- Unity target: `manage_script`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
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
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `read`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

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
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`

## manage_scriptable_object

Creates and modifies ScriptableObject assets using Unity SerializedObject property paths.

- Group: `scripting_ext`
- Unity target: `manage_scriptable_object`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `true`
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
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `modify`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`

## manage_selection

Manages Unity Editor selection. Actions: set_selection (set selected objects by path/ID), frame_selection (frame selected objects in scene view), get_selection (get currently selected objects). Use set_selection with clear=true to clear selection, or add=true to add to existing selection.

- Group: `core`
- Unity target: `manage_selection`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `frame_selection`, `get_selection`, `set_selection`
- Known read-only actions: `get_selection`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`frame_selection`, `get_selection`, `set_selection`
  - `target`: type=`array | integer | string`, required=`false`
  - `clear`: type=`boolean`, required=`false`
  - `add`: type=`boolean`, required=`false`
  - `frame_selected`: type=`boolean`, required=`false`
- Action contracts:
  - `frame_selection`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_selection`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `set_selection`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_shader

Manages shader scripts in Unity (create, read, update, delete). Read-only action: read. Modifying actions: create, update, delete.

- Group: `vfx`
- Unity target: `manage_shader`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `create`, `delete`, `read`, `update`
- Known read-only actions: `read`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`create`, `delete`, `read`, `update`
  - `name`: type=`string`, required=`true`
  - `path`: type=`string`, required=`true`
  - `contents`: type=`string`, required=`false`
- Action contracts:
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `read`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `update`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`

## manage_subagents

List or export generated Unity MCP subagent artifacts built from the live tool registry. Use action='list' to inspect the current catalog. Use action='export' to write JSON and/or Markdown subagent files to disk.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `export`, `list`
- Known read-only actions: `list`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`export`, `list`
  - `output_dir`: type=`string`, required=`false`
  - `format`: type=`enum`, required=`false`, enum=`both`, `json`, `markdown`
- Action contracts:
  - `export`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `list`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

## manage_texture

Procedural texture generation for Unity. Creates textures with solid fills, patterns (checkerboard, stripes, dots, grid, brick), gradients, and noise. Actions: create, modify, delete, create_sprite, apply_pattern, apply_gradient, apply_noise

- Group: `vfx`
- Unity target: `manage_texture`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
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
  - `apply_gradient`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `apply_noise`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `apply_pattern`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `create_sprite`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `modify`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`

## manage_tools

Manage which tool groups are visible in this session. Actions: list_groups (show all groups and their status), activate (enable a group), deactivate (disable a group), sync (refresh visibility from Unity Editor's toggle states), reset (restore defaults). Activating a group makes its tools appear; deactivating hides them. Use sync after toggling tools in the Unity Editor GUI.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `activate`, `deactivate`, `list_groups`, `reset`, `sync`
- Known read-only actions: `list_groups`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`activate`, `deactivate`, `list_groups`, `reset`, `sync`
  - `group`: type=`string`, required=`false`
- Action contracts:
  - `activate`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `deactivate`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `list_groups`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `reset`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `sync`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_transactions

Manage multi-step editor transactions with rollback capability. Use this tool to group related actions into atomic units that can be previewed before commit and rolled back if needed. Actions: begin_transaction (start a named transaction), append_action (add a change to current transaction), preview_transaction (see all pending changes without applying), commit_transaction (apply all actions atomically), get_transaction_state (check current transaction status), list_transactions (view historical transactions), rollback_transaction (undo a committed transaction where possible). Integrates with manage_checkpoints for file-level rollback support.

- Group: `transactions`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `append_action`, `begin_transaction`, `commit_transaction`, `get_transaction_state`, `list_transactions`, `preview_transaction`, `rollback_transaction`
- Known read-only actions: `get_transaction_state`, `list_transactions`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`append_action`, `begin_transaction`, `commit_transaction`, `get_transaction_state`, `list_transactions`, `preview_transaction`, `rollback_transaction`
  - `name`: type=`string`, required=`false`
  - `transaction_id`: type=`string`, required=`false`
  - `change_type`: type=`enum`, required=`false`, enum=`created`, `deleted`, `failed`, `modified`, `moved`
  - `asset_path`: type=`string`, required=`false`
  - `description`: type=`string`, required=`false`
  - `before_hash`: type=`string`, required=`false`
  - `after_hash`: type=`string`, required=`false`
  - `can_undo`: type=`boolean | string`, required=`false`
  - `action_params`: type=`object | string`, required=`false`
  - `checkpoint_id`: type=`string`, required=`false`
  - `status_filter`: type=`enum`, required=`false`, enum=`committed`, `failed`, `pending`, `rolled_back`
  - `limit`: type=`integer | string`, required=`false`
- Action contracts:
  - `append_action`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `begin_transaction`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `commit_transaction`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `get_transaction_state`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `list_transactions`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `preview_transaction`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `rollback_transaction`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`

## manage_transform

Advanced transform operations for GameObjects including world/local space queries, bounds retrieval, grid snapping, alignment, distribution, and placement validation. Complements manage_gameobject by focusing purely on spatial manipulation.

- Group: `spatial`
- Unity target: `manage_transform`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `align_to_object`, `distribute_objects`, `get_bounds`, `get_local_transform`, `get_world_transform`, `place_relative`, `set_local_transform`, `set_world_transform`, `snap_to_grid`, `validate_placement`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`align_to_object`, `distribute_objects`, `get_bounds`, `get_local_transform`, `get_world_transform`, `place_relative`, `set_local_transform`, `set_world_transform`, `snap_to_grid`, `validate_placement`
  - `target`: type=`string`, required=`false`
  - `search_method`: type=`enum`, required=`false`, enum=`by_component`, `by_id`, `by_layer`, `by_name`, `by_path`, `by_tag`
  - `position`: type=`array | object | string`, required=`false`
  - `rotation`: type=`array | object | string`, required=`false`
  - `scale`: type=`array | object | string`, required=`false`
  - `grid_size`: type=`number | string`, required=`false`
  - `snap_position`: type=`boolean | string`, required=`false`
  - `snap_rotation`: type=`boolean | string`, required=`false`
  - `reference_object`: type=`string`, required=`false`
  - `align_axis`: type=`enum`, required=`false`, enum=`all`, `x`, `y`, `z`
  - `align_mode`: type=`enum`, required=`false`, enum=`center`, `max`, `min`, `pivot`
  - `targets`: type=`array | string`, required=`false`
  - `distribute_axis`: type=`enum`, required=`false`, enum=`x`, `y`, `z`
  - `distribute_spacing`: type=`number | string`, required=`false`
  - `offset`: type=`array | object | string`, required=`false`
  - `direction`: type=`enum`, required=`false`, enum=`above`, `back`, `backward`, `behind`, `below`, `down`, `east`, `forward`, `front`, `left`, `north`, `right`, `south`, `up`, `west`
  - `distance`: type=`number | string`, required=`false`
  - `use_world_space`: type=`boolean | string`, required=`false`
  - `check_overlap`: type=`boolean | string`, required=`false`
  - `check_off_grid`: type=`boolean | string`, required=`false`
  - `check_invalid_scale`: type=`boolean | string`, required=`false`
  - `min_spacing`: type=`number | string`, required=`false`
- Action contracts:
  - `align_to_object`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `distribute_objects`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_bounds`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_local_transform`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_world_transform`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `place_relative`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_local_transform`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_world_transform`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `snap_to_grid`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `validate_placement`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

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
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
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
  - `attach_ui_document`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `create`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `create_panel_settings`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `delete`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `detach_ui_document`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `get_visual_tree`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `link_stylesheet`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `list`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `modify_visual_element`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `ping`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `read`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `render_ui`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `update`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`
  - `update_panel_settings`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`true`

## manage_vfx

Manage Unity VFX components (ParticleSystem, VisualEffect, LineRenderer, TrailRenderer). Action prefixes: particle_*, vfx_*, line_*, trail_*. Action-specific parameters go in `properties` (keys match ManageVFX.cs).

- Group: `vfx`
- Unity target: `manage_vfx`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Known read-only actions: `line_get_info`, `particle_get_info`, `ping`, `trail_get_info`, `vfx_get_info`, `vfx_list_assets`, `vfx_list_templates`
- Parameters:
  - `action`: type=`string`, required=`true`
  - `target`: type=`string`, required=`false`
  - `search_method`: type=`enum`, required=`false`, enum=`by_id`, `by_layer`, `by_name`, `by_path`, `by_tag`
  - `properties`: type=`object | string`, required=`false`

## manage_video_capture

Record video and capture GIF animations from Unity gameplay. Works in both Editor and Play mode. Actions: start (begin recording), stop (end and save), get_status (recording info), capture_gif (short animated GIF), set_settings (configure fps/quality/resolution). 

Workflow:
1. Use set_settings to configure capture quality and format
2. Use start to begin recording (MP4 or frame sequence)
3. Use get_status to monitor recording progress
4. Use stop to end recording and save the file
5. Use capture_gif for short animated clips (auto-stops when duration reached)

- Group: `core`
- Unity target: `manage_video_capture`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `capture_gif`, `get_status`, `set_settings`, `start`, `stop`
- Known read-only actions: `get_status`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`capture_gif`, `get_status`, `set_settings`, `start`, `stop`
  - `output_path`: type=`string`, required=`false`
  - `duration_seconds`: type=`number`, required=`false`
  - `fps`: type=`integer`, required=`false`
  - `quality`: type=`enum`, required=`false`, enum=`high`, `low`, `medium`, `ultra`
  - `resolution`: type=`object`, required=`false`
  - `format`: type=`enum`, required=`false`, enum=`frames`, `gif`, `mp4`
  - `include_audio`: type=`boolean`, required=`false`
  - `loop_count`: type=`integer`, required=`false`
  - `frame_skip`: type=`integer`, required=`false`
- Action contracts:
  - `capture_gif`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_status`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `set_settings`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `start`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `stop`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## manage_windows

Manages Unity Editor windows and tools. Actions: list_windows, open_window, focus_window, close_window, get_active_tool, set_active_tool. Use list_windows to see all open editor windows with their IDs. Use open_window with window_type (e.g., 'Console', 'Inspector', 'Scene', 'Game', 'Hierarchy'). Use focus_window to bring a window to front. Use set_active_tool to change transform tools: View, Move, Rotate, Scale, Rect, Transform, Custom.

- Group: `core`
- Unity target: `manage_windows`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `close_window`, `focus_window`, `get_active_tool`, `list_windows`, `open_window`, `set_active_tool`
- Known read-only actions: `get_active_tool`, `list_windows`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`close_window`, `focus_window`, `get_active_tool`, `list_windows`, `open_window`, `set_active_tool`
  - `window_type`: type=`string`, required=`false`
  - `window_id`: type=`integer`, required=`false`
  - `window_title`: type=`string`, required=`false`
  - `tool_name`: type=`string`, required=`false`
- Action contracts:
  - `close_window`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `focus_window`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_active_tool`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `list_windows`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`
  - `open_window`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `set_active_tool`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## navigate_editor

Navigates the Unity Editor to direct user attention. Navigation types: reveal_in_project (ping/highlight asset in Project window), focus_hierarchy (focus and expand GameObject in Hierarchy), frame_in_scene (frame object in Scene view camera), open_inspector (open object in Inspector), open_script (open script at specific line/symbol), open_asset (open asset at path in appropriate editor), get_context (return current editor state without navigation). Use restore_context with previous_context to restore editor state.

- Group: `navigation`
- Unity target: `navigate_editor`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Known read-only actions: `get_context`
- Parameters:
  - `navigation_type`: type=`enum`, required=`true`, enum=`focus_hierarchy`, `frame_in_scene`, `get_context`, `open_asset`, `open_inspector`, `open_script`, `restore_context`, `reveal_in_project`
  - `target`: type=`integer | object | string`, required=`false`
  - `line_number`: type=`integer`, required=`false`
  - `column_number`: type=`integer`, required=`false`
  - `symbol_name`: type=`string`, required=`false`
  - `expand_hierarchy`: type=`boolean`, required=`false`
  - `frame_selected`: type=`boolean`, required=`false`
  - `lock_inspector`: type=`boolean`, required=`false`
  - `previous_context`: type=`object`, required=`false`
  - `wait_for_completion`: type=`boolean`, required=`false`

## open_inspector_target

Opens a target in the Unity Inspector window. Supports opening GameObjects, assets, components, or specific component types. Can lock the inspector, expand specific components, and manage multi-object editing. Also supports querying the current Inspector target. Use this to direct user attention to specific properties and settings.

- Group: `navigation`
- Unity target: `open_inspector_target`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `clear`, `get_target`, `lock`, `open`, `open_component`, `unlock`
- Parameters:
  - `action`: type=`enum`, required=`false`, enum=`clear`, `get_target`, `lock`, `open`, `open_component`, `unlock`
  - `target`: type=`array | integer | object | string`, required=`false`
  - `component_type`: type=`string`, required=`false`
  - `component_index`: type=`integer`, required=`false`
  - `expand_component`: type=`boolean`, required=`false`
  - `lock`: type=`boolean`, required=`false`
  - `mode`: type=`enum`, required=`false`, enum=`debug`, `debug_internal`, `normal`
- Action contracts:
  - `clear`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_target`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `lock`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `open`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `open_component`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `unlock`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## ping

Simple connectivity check. Returns server status and optionally pings Unity. Use this to verify the MCP server is running and responsive. Set ping_unity=true to also check Unity connection.

- Group: `core`
- Unity target: `server-only`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Known read-only actions: `ping`
- Parameters:
  - `ping_unity`: type=`boolean`, required=`false`

## poll_subscription_events

Polls for events from a specific subscription. Returns buffered events and clears the buffer. Non-blocking - returns immediately with available events.

- Group: `core`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `subscription_id`: type=`string`, required=`true`
  - `max_events`: type=`integer | string`, required=`false`
  - `wait_for_events`: type=`boolean | string`, required=`false`
  - `wait_timeout_seconds`: type=`integer | string`, required=`false`

## preflight_audit

Run a combined read-only preflight audit: compile health, scene integrity, and prefab integrity. Use this before broad mutations or test runs.

- Group: `testing`
- Unity target: `server-only`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `scene_scope`: type=`string`, required=`false`
  - `prefab_root_folder`: type=`string`, required=`false`
  - `prefab_scan_limit`: type=`integer`, required=`false`
  - `max_issue_samples`: type=`integer`, required=`false`

## preview_changes

Preview pending changes before committing a transaction. Provides detailed analysis including: change summary by category (created/modified/deleted/moved/failed), impact assessment for each change, conflict detection with other pending transactions, rollback feasibility, and verification status (hash comparisons). Use this tool to review multi-step workflows before final commit.

- Group: `transactions`
- Unity target: `server-only`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `transaction_id`: type=`string`, required=`false`
  - `include_analysis`: type=`boolean | string`, required=`false`
  - `detect_conflicts`: type=`boolean | string`, required=`false`
  - `verify_hashes`: type=`boolean | string`, required=`false`

## read_console

Gets messages from or clears the Unity Editor console. Defaults to 10 most recent entries. Use page_size/cursor for paging. Note: For maximum client compatibility, pass count as a quoted string (e.g., '5'). The 'get' action is read-only; 'clear' modifies ephemeral UI state (not project data).

- Group: `core`
- Unity target: `read_console`
- Action model: `mixed`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `true`
- Requires explicit opt-in: `true`
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
  - `clear`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get`: read_only=`true`, mutating=`false`, high_risk=`false`, supports_dry_run=`false`

## record_pipeline

Start recording editor actions into a pipeline or get recording status. Records MCP tool calls made during the session for later replay. Use stop_pipeline_recording to finish and save. Note: Recording captures tool calls at the MCP server level, not Unity editor UI interactions.

- Group: `pipeline`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `start`, `status`
- Parameters:
  - `action`: type=`enum`, required=`false`, enum=`start`, `status`
  - `name`: type=`string`, required=`false`
  - `description`: type=`string`, required=`false`
  - `filter`: type=`array`, required=`false`
- Action contracts:
  - `start`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `status`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## record_profiler_session

Continuously records profiler data for a specified duration. This is a long-running job that collects snapshots at regular intervals and returns aggregated statistics. Use for performance testing and regression detection.

- Group: `profiling`
- Unity target: `manage_profiler`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `duration_seconds`: type=`integer | string`, required=`false`
  - `interval_frames`: type=`integer | string`, required=`false`
  - `include_memory`: type=`boolean | string`, required=`false`
  - `include_rendering`: type=`boolean | string`, required=`false`
  - `auto_save`: type=`boolean | string`, required=`false`
  - `save_path`: type=`string`, required=`false`

## refresh_unity

Request a Unity asset database refresh and optionally a script compilation. Can optionally wait for readiness.

- Group: `core`
- Unity target: `refresh_unity`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `mode`: type=`enum`, required=`false`, enum=`force`, `if_dirty`
  - `scope`: type=`enum`, required=`false`, enum=`all`, `assets`, `scripts`
  - `compile`: type=`enum`, required=`false`, enum=`none`, `request`
  - `wait_for_ready`: type=`boolean`, required=`false`

## replay_pipeline

Execute a saved pipeline (sequence of tool operations). Replays each step in the pipeline sequentially. Supports dry-run mode to preview without executing. Can override parameters at replay time. Use for automating repetitive workflows and standardizing procedures.

- Group: `pipeline`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `name`: type=`string`, required=`true`
  - `parameters`: type=`object`, required=`false`
  - `dry_run`: type=`boolean`, required=`false`
  - `stop_on_error`: type=`boolean`, required=`false`

## replay_request

Replay a captured response for a given tool and parameters. Must have an active replay session. Returns the captured response with optional modifications based on replay configuration.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `session_id`: type=`string`, required=`true`
  - `tool`: type=`string`, required=`true`
  - `params`: type=`object`, required=`true`
  - `fuzzy_match`: type=`boolean`, required=`false`

## reveal_asset

Reveals/ping an asset in the Unity Project window. Highlights the asset and scrolls to make it visible. Supports revealing by asset path, GUID, or asset database ID. Use this to direct user attention to specific assets in the project.

- Group: `navigation`
- Unity target: `reveal_asset`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `asset_path`: type=`string`, required=`false`
  - `guid`: type=`string`, required=`false`
  - `instance_id`: type=`integer`, required=`false`
  - `select`: type=`boolean`, required=`false`
  - `highlight`: type=`boolean`, required=`false`

## rollback_changes

Rollback committed transactions and revert changes. Supports rolling back entire transactions (where all changes are undoable), using checkpoint restoration for file-level rollback, and partial rollback of specific change types. Integrates with manage_checkpoints for checkpoint-based restoration. Use get_rollback_summary first to assess rollback feasibility.

- Group: `transactions`
- Unity target: `server-only`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `get_rollback_summary`, `list_rollback_history`, `rollback_to_checkpoint`, `rollback_transaction`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`get_rollback_summary`, `list_rollback_history`, `rollback_to_checkpoint`, `rollback_transaction`
  - `transaction_id`: type=`string`, required=`false`
  - `checkpoint_id`: type=`string`, required=`false`
  - `change_types`: type=`array | string`, required=`false`
  - `dry_run`: type=`boolean | string`, required=`false`
- Action contracts:
  - `get_rollback_summary`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `list_rollback_history`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `rollback_to_checkpoint`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `rollback_transaction`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## run_benchmark

Execute a benchmark suite against MCP tools. Measures performance metrics like latency, throughput, and success rates. Supports high-traffic workflow simulation.

- Group: `dev_tools`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `benchmark_name`: type=`string`, required=`true`
  - `iterations`: type=`integer`, required=`false`
  - `tool_sequence`: type=`array`, required=`false`
  - `concurrent_requests`: type=`integer`, required=`false`
  - `warmup_iterations`: type=`integer`, required=`false`

## run_playbook

Execute a playbook (reusable template for Unity workflows). Playbooks contain predefined steps that automate common tasks. Built-in playbooks: basic_player_controller, ui_canvas_setup, scene_lighting_setup. Supports parameter overrides for customization.

- Group: `pipeline`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `playbook_id`: type=`string`, required=`true`
  - `context`: type=`object`, required=`false`
  - `dry_run`: type=`boolean`, required=`false`
  - `stop_on_error`: type=`boolean`, required=`false`

## run_tests

Starts a Unity test run asynchronously and returns a job_id immediately. Poll with get_test_job for progress.

- Group: `testing`
- Unity target: `run_tests`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `mode`: type=`enum`, required=`false`, enum=`EditMode`, `PlayMode`
  - `test_names`: type=`array | string`, required=`false`
  - `group_names`: type=`array | string`, required=`false`
  - `category_names`: type=`array | string`, required=`false`
  - `assembly_names`: type=`array | string`, required=`false`
  - `include_failed_tests`: type=`boolean`, required=`false`
  - `include_details`: type=`boolean`, required=`false`

## save_pipeline

Save a pipeline (sequence of tool operations) to disk for later replay. Pipelines can be stored in the project (ProjectRoot/Pipelines/) or user config. Saved pipelines can be replayed with replay_pipeline. Useful for automating repetitive workflows and sharing procedures.

- Group: `pipeline`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `name`: type=`string`, required=`true`
  - `steps`: type=`array`, required=`true`
  - `description`: type=`string`, required=`false`
  - `author`: type=`string`, required=`false`
  - `tags`: type=`array`, required=`false`
  - `version`: type=`string`, required=`false`
  - `overwrite`: type=`boolean`, required=`false`

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
- Supports dry-run: `true`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `name`: type=`string`, required=`true`
  - `path`: type=`string`, required=`true`
  - `edits`: type=`array | string`, required=`true`
  - `options`: type=`object | string`, required=`false`
  - `script_type`: type=`string`, required=`false`
  - `namespace`: type=`string`, required=`false`

## search_assets_advanced

Advanced asset search with structured filtering and rich metadata. Supports filtering by type, labels, import settings, dependencies, and custom criteria like size and date. Returns structured metadata suitable for further tool calls.

- Group: `asset_intelligence`
- Unity target: `search_assets_advanced`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `asset_types`: type=`array`, required=`false`
  - `labels`: type=`array`, required=`false`
  - `search_path`: type=`string`, required=`false`
  - `has_dependencies`: type=`array`, required=`false`
  - `referenced_by`: type=`array`, required=`false`
  - `import_settings`: type=`object`, required=`false`
  - `importer_type`: type=`string`, required=`false`
  - `min_size_bytes`: type=`integer`, required=`false`
  - `max_size_bytes`: type=`integer`, required=`false`
  - `modified_after`: type=`string`, required=`false`
  - `modified_before`: type=`string`, required=`false`
  - `unused_only`: type=`boolean`, required=`false`
  - `name_pattern`: type=`string`, required=`false`
  - `sort_by`: type=`enum`, required=`false`, enum=`modified_time`, `name`, `path`, `relevance`, `size`, `type`
  - `sort_order`: type=`enum`, required=`false`, enum=`asc`, `desc`
  - `page`: type=`integer`, required=`false`
  - `page_size`: type=`integer`, required=`false`
  - `include_metadata`: type=`boolean`, required=`false`

## search_code

Quickly search C# code files using regex patterns.
        
Works WITHOUT Unity running - uses local file system.
Returns file paths, line numbers, and matching content.

Example patterns:
- "class.*Controller" - Find controller classes
- "public void.*\(" - Find public void methods
- "SerializeField" - Find all SerializeField attributes

- Group: `core`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `pattern`: type=`string`, required=`true`
  - `project_root`: type=`string`, required=`false`
  - `file_pattern`: type=`string`, required=`false`
  - `use_regex`: type=`boolean`, required=`false`
  - `ignore_case`: type=`boolean`, required=`false`
  - `max_results`: type=`integer`, required=`false`

## set_active_instance

Set the active Unity instance for this client/session. Accepts Name@hash, hash prefix, or port number (stdio only).

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `instance`: type=`string`, required=`true`

## spatial_queries

Spatial queries for Unity scenes: find nearest objects, objects within radius/box, overlap checks, raycasting, distance/direction calculations, and relative offsets. Enables agents to reason about spatial relationships without blind coordinate edits.

- Group: `spatial`
- Unity target: `spatial_queries`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `get_direction`, `get_distance`, `get_relative_offset`, `nearest_object`, `objects_in_box`, `objects_in_radius`, `overlap_check`, `raycast`
- Parameters:
  - `action`: type=`enum`, required=`true`, enum=`get_direction`, `get_distance`, `get_relative_offset`, `nearest_object`, `objects_in_box`, `objects_in_radius`, `overlap_check`, `raycast`
  - `source`: type=`string`, required=`false`
  - `target`: type=`string`, required=`false`
  - `search_method`: type=`enum`, required=`false`, enum=`by_component`, `by_id`, `by_layer`, `by_name`, `by_path`, `by_tag`
  - `point`: type=`array | object | string`, required=`false`
  - `filter_by_tag`: type=`string`, required=`false`
  - `filter_by_layer`: type=`string`, required=`false`
  - `filter_by_component`: type=`string`, required=`false`
  - `exclude_inactive`: type=`boolean | string`, required=`false`
  - `radius`: type=`number | string`, required=`false`
  - `max_results`: type=`integer | string`, required=`false`
  - `box_center`: type=`array | object | string`, required=`false`
  - `box_size`: type=`array | object | string`, required=`false`
  - `object_to_place`: type=`string`, required=`false`
  - `placement_position`: type=`array | object | string`, required=`false`
  - `rotation_at_placement`: type=`array | object | string`, required=`false`
  - `scale_at_placement`: type=`array | object | string`, required=`false`
  - `min_clearance`: type=`number | string`, required=`false`
  - `origin`: type=`array | object | string`, required=`false`
  - `direction`: type=`array | object | string`, required=`false`
  - `max_distance`: type=`number | string`, required=`false`
  - `layer_mask`: type=`string`, required=`false`
  - `offset_type`: type=`enum`, required=`false`, enum=`bounds_center`, `bounds_max`, `bounds_min`, `pivot`, `position`
- Action contracts:
  - `get_direction`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_distance`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `get_relative_offset`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `nearest_object`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `objects_in_box`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `objects_in_radius`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `overlap_check`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `raycast`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## start_fixture_capture

Start capturing Unity responses as fixtures for replay testing. Captures request/response pairs with scenario tags and metadata.

- Group: `dev_tools`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `scenario`: type=`string`, required=`false`
  - `include_tools`: type=`array`, required=`false`
  - `exclude_tools`: type=`array`, required=`false`
  - `tags`: type=`array`, required=`false`

## start_fixture_replay

Start a fixture replay session for deterministic testing without live Unity. Loads fixtures and replays responses based on tool/parameter matching.

- Group: `dev_tools`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `fixtures`: type=`array`, required=`true`
  - `speed_multiplier`: type=`number`, required=`false`
  - `deterministic`: type=`boolean`, required=`false`
  - `inject_errors`: type=`array`, required=`false`

## start_trace

Begin tracing MCP tool invocations. Captures request details including normalized parameters, Unity instance selection, retries, latency, and response status. Use stop_trace to end tracing and retrieve data.

- Group: `dev_tools`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `tags`: type=`array`, required=`false`

## stop_fixture_capture

Stop capturing fixtures and return capture summary. Optionally export captured fixtures to a file.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `export_path`: type=`string`, required=`false`

## stop_fixture_replay

Stop an active fixture replay session and return replay statistics.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `session_id`: type=`string`, required=`true`

## stop_pipeline_recording

Stop recording a pipeline and optionally save the results. Returns the recorded actions for review. Use 'save' action to persist, 'discard' to cancel without saving. Saved pipelines can be replayed with replay_pipeline.

- Group: `pipeline`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Supported actions: `discard`, `stop`
- Parameters:
  - `action`: type=`enum`, required=`false`, enum=`discard`, `stop`
  - `save`: type=`boolean`, required=`false`
  - `path`: type=`string`, required=`false`
  - `author`: type=`string`, required=`false`
  - `tags`: type=`array`, required=`false`
- Action contracts:
  - `discard`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`
  - `stop`: read_only=`false`, mutating=`true`, high_risk=`true`, supports_dry_run=`false`

## stop_trace

End the active tracing session and return the complete trace data. Includes all captured tool invocations with timing, retries, and responses.

- Group: `server-meta`
- Unity target: `server-only`
- Action model: `unknown`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `trace_id`: type=`string`, required=`false`
  - `include_entries`: type=`boolean`, required=`false`

## subscribe_editor_events

Subscribes to Unity editor events for real-time notifications. Returns a subscription_id that can be used to unsubscribe. Events are delivered through the MCP notification channel when available.

- Group: `events`
- Unity target: `server-only`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `event_types`: type=`array | string`, required=`true`
  - `filter_criteria`: type=`object | string`, required=`false`
  - `expiration_minutes`: type=`integer | string`, required=`false`
  - `buffer_events`: type=`boolean | string`, required=`false`

## summarize_asset

Generate intelligent summaries of Unity assets. Provides high-level understanding of asset purpose, key properties, usage statistics, and relationships. Helps answer 'what is this asset and how is it used?'

- Group: `asset_intelligence`
- Unity target: `summarize_asset`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `asset_path`: type=`string`, required=`false`
  - `asset_guid`: type=`string`, required=`false`
  - `detail_level`: type=`enum`, required=`false`, enum=`brief`, `detailed`, `standard`
  - `include_dependencies`: type=`boolean`, required=`false`
  - `include_dependents`: type=`boolean`, required=`false`
  - `include_usage_stats`: type=`boolean`, required=`false`
  - `include_properties`: type=`boolean`, required=`false`
  - `max_related_assets`: type=`integer`, required=`false`

## unsubscribe_editor_events

Unsubscribes from Unity editor events and cleans up the subscription. Returns statistics about the subscription (events received, etc.). Idempotent - safe to call multiple times on the same subscription_id.

- Group: `events`
- Unity target: `server-only`
- Action model: `always_mutating`
- Mutating: `true`
- High risk: `true`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `subscription_id`: type=`string`, required=`true`
  - `flush_pending_events`: type=`boolean | string`, required=`false`

## validate_compile_health

Check Unity compile readiness and summarize recent compiler diagnostics from editor state and console output.

- Group: `core`
- Unity target: `server-only`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `true`
- Runtime only: `false`
- Requires explicit opt-in: `false`
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
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `uri`: type=`string`, required=`true`
  - `level`: type=`enum`, required=`false`, enum=`basic`, `standard`
  - `include_diagnostics`: type=`boolean`, required=`false`

## wait_for_editor_condition

Waits for a specific Unity editor condition to be met. Useful for long workflows that need to wait for compilation, scene loading, or play mode changes. Supports configurable timeout with default 30s. Can be cancelled.

- Group: `events`
- Unity target: `server-only`
- Action model: `always_read_only`
- Mutating: `false`
- High risk: `false`
- Supports dry-run: `false`
- Local only: `false`
- Runtime only: `false`
- Requires explicit opt-in: `false`
- Parameters:
  - `condition`: type=`enum`, required=`true`, enum=`asset_import_complete`, `compile_idle`, `object_exists`, `play_mode_state`, `prefab_stage_state`, `scene_load_complete`
  - `timeout_seconds`: type=`integer | number | string`, required=`false`
  - `poll_interval_seconds`: type=`number | string`, required=`false`
  - `play_mode_target`: type=`enum`, required=`false`, enum=`paused`, `playing`, `stopped`
  - `prefab_stage_target`: type=`enum`, required=`false`, enum=`closed`, `open`
  - `prefab_path`: type=`string`, required=`false`
  - `object_name`: type=`string`, required=`false`
  - `object_guid`: type=`string`, required=`false`
  - `scene_path`: type=`string`, required=`false`
  - `scene_name`: type=`string`, required=`false`

