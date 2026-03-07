# Unity Data Specialist

ID: `unity-scripting-ext-specialist`
Kind: `specialist`

Handles ScriptableObject and data-oriented authoring flows.

Tool group: `scripting_ext`
Activate with: `manage_tools(action="activate", group="scripting_ext")`

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
