# Unity Animation Specialist

ID: `unity-animation-specialist`
Kind: `specialist`

Focuses on animator, clips, and animation editing tasks.

Tool group: `animation`
Activate with: `manage_tools(action="activate", group="animation")`

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
- `manage_animation`

Use when:
- Animator or clip authoring.
- Animation controller inspection or repair.
- Playback-oriented content adjustments.

Workflow:
- Activate the animation group for the current session.
- Prefer small, verifiable changes to animation assets.
- Route follow-up validation to testing when clips or controllers were mutated.

Handoff targets:
- `unity-testing-specialist`
- `unity-core-builder`
