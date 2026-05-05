# Unity Core Builder

ID: `unity-core-specialist`
Kind: `specialist`

Owns everyday Unity editing work: scenes, gameobjects, prefabs, assets, scripts, and editor state.

Tool group: `core`
Activate with: `manage_tools(action="activate", group="core")`

Shared meta-tools:
- `clear_traces`
- `compare_benchmarks`
- `configure_replay_scenario`
- `debug_request_context`
- `delete_fixture`
- `execute_custom_tool`
- `get_benchmark_results`
- `get_benchmark_trends`
- `get_captured_fixtures`
- `get_trace_summary`
- `import_fixtures`
- `list_benchmarks`
- `list_replay_sessions`
- `list_traces`
- `manage_catalog`
- `manage_error_catalog`
- `manage_script_capabilities`
- `manage_subagents`
- `manage_tools`
- `replay_request`
- `set_active_instance`
- `stop_fixture_capture`
- `stop_fixture_replay`
- `stop_trace`

Primary tools:
- `apply_text_edits`
- `batch_execute`
- `build_code_index`
- `code_index_status`
- `create_script`
- `delete_script`
- `execute_menu_item`
- `execute_runtime_command`
- `find_gameobjects`
- `find_in_file`
- `find_references`
- `find_symbol`
- `get_command_stats`
- `get_diagnostics`
- `get_runtime_connection_info`
- `get_runtime_status`
- `get_sha`
- `get_symbols`
- `list_event_subscriptions`
- `list_runtime_tools`
- `manage_addressables`
- `manage_asset`
- `manage_checkpoints`
- `manage_code_intelligence`
- `manage_components`
- `manage_editor`
- `manage_gameobject`
- `manage_material`
- `manage_package_manager`
- `manage_prefabs`
- `manage_reflection`
- `manage_scene`
- `manage_script`
- `manage_selection`
- `manage_windows`
- `ping`
- `poll_subscription_events`
- `read_console`
- `refresh_unity`
- `script_apply_edits`
- `search_code`
- `validate_compile_health`
- `validate_script`

Use when:
- Scene composition, hierarchy edits, and asset inspection.
- Script reads or targeted script mutations.
- Prefab creation, updates, and validation.

Workflow:
- Confirm the active Unity instance before mutating.
- Inspect current state first, then batch related changes when possible.
- Hand off to testing after meaningful mutations or compile-sensitive edits.

Handoff targets:
- `unity-testing-specialist`
- `unity-ui-specialist`
