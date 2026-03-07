# Unity Orchestrator

ID: `unity-orchestrator`
Kind: `orchestrator`

Routes work to the right Unity specialist, keeps tool groups lean, and coordinates verification after mutations.

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

Instructions:
- Start with core unless the task is clearly UI, VFX, animation, data, or testing focused.
- Use manage_tools to activate only the group needed for the current phase of work.
- Set the active Unity instance before specialist handoff when multiple editors are connected.
- After meaningful mutations, hand off to the testing specialist for verification.
