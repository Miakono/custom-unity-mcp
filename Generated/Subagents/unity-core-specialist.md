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
- `manage_asset`
- `manage_components`
- `manage_editor`
- `manage_gameobject`
- `manage_material`
- `manage_prefabs`
- `manage_scene`
- `refresh_unity`
- `apply_text_edits`
- `create_script`
- `delete_script`
- `validate_script`
- `manage_script`
- `get_sha`
- `read_console`
- `validate_compile_health`
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
