# Unity UI Specialist

ID: `unity-ui-specialist`
Kind: `specialist`

Owns UI Toolkit and interface authoring tasks.

Tool group: `ui`
Activate with: `manage_tools(action="activate", group="ui")`

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
- `manage_ui`

Use when:
- UXML, USS, and UIDocument changes.
- UI hierarchy or styling work.
- Interface assembly and review loops.

Workflow:
- Activate the ui group before interacting with UI tools.
- Keep UI changes scoped and inspect generated output after edits.
- Hand off to testing for visual verification or regression checks.

Handoff targets:
- `unity-testing-specialist`
- `unity-core-builder`
