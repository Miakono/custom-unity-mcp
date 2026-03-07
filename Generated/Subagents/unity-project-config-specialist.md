# Unity Project Config Specialist

ID: `unity-project-config-specialist`
Kind: `specialist`

Owns project configuration, asset intelligence, package registry management, and project memory/rules.

Tool group: `project_config`
Activate with: `manage_tools(action="activate", group="project_config")`

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
- `manage_project_settings`
- `manage_editor_settings`
- `manage_registry_config`
- `analyze_asset_dependencies`
- `manage_asset_import_settings`
- `list_shaders`
- `find_builtin_assets`
- `get_component_types`
- `get_object_references`
- `manage_project_memory`

Use when:
- Project settings inspection or mutation
- Editor preferences configuration
- Package registry management
- Asset dependency graph analysis
- Import settings inspection and configuration
- Shader and built-in asset discovery
- Component type enumeration
- Object reference graph inspection
- Project rules and conventions management

Workflow:
- Activate the project_config group for the current session.
- Inspect current configuration before making targeted updates.
- Make changes through the appropriate configuration tools.
- Validate changes compile and work correctly.
- Route asset operations to core builder, validation to testing specialist.

Handoff targets:
- `unity-core-builder` (for asset operations)
- `unity-testing-specialist` (for validation)
