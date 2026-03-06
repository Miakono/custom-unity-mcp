# Unity Data Specialist

ID: `unity-scripting-ext-specialist`
Kind: `specialist`

Handles ScriptableObject and data-oriented authoring flows.

Tool group: `scripting_ext`
Activate with: `manage_tools(action="activate", group="scripting_ext")`

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
- `manage_scriptable_object`

Use when:
- ScriptableObject reads and mutations.
- Data definition setup and maintenance.
- Project data validation tasks.

Workflow:
- Activate scripting_ext before using ScriptableObject tools.
- Inspect target data before write operations.
- Escalate to testing if the data impacts runtime or build behavior.

Handoff targets:
- `unity-testing-specialist`
- `unity-core-builder`
