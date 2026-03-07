# Unity Core Builder

ID: `unity-core-specialist`
Kind: `specialist`

Owns everyday Unity editing work: scenes, gameobjects, prefabs, assets, scripts, and editor state.

Tool group: `core`
Activate with: `manage_tools(action="activate", group="core")`

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
- `batch_execute`
- `execute_menu_item`
- `find_gameobjects`
- `find_in_file`
- `get_diagnostics`
- `manage_addressables`
- `manage_asset`
- `manage_checkpoints`
- `manage_code_intelligence`
- `search_code`
- `find_symbol`
- `find_references`
- `get_symbols`
- `build_code_index`
- `code_index_status`
- `manage_components`
- `manage_editor`
- `manage_gameobject`
- `manage_material`
- `manage_package_manager`
- `manage_prefabs`
- `manage_reflection`
- `refresh_unity`
- `manage_scene`
- `apply_text_edits`
- `create_script`
- `delete_script`
- `validate_script`
- `manage_script`
- `get_sha`
- `manage_video_capture`
- `read_console`
- `validate_compile_health`
- `get_runtime_status`
- `list_runtime_tools`
- `execute_runtime_command`
- `get_runtime_connection_info`
- `script_apply_edits`

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
