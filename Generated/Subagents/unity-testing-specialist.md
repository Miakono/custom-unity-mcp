# Unity Testing Specialist

ID: `unity-testing-specialist`
Kind: `specialist`

Runs validation loops, test jobs, and post-change verification.

Tool group: `testing`
Activate with: `manage_tools(action="activate", group="testing")`

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
- `audit_prefab_integrity`
- `audit_scene_integrity`
- `preflight_audit`
- `run_tests`
- `get_test_job`

Use when:
- Run tests after code or asset mutations.
- Collect diagnostics after failures.
- Verify compile, editor, or batch outcomes.

Workflow:
- Activate the testing group only when validation is needed.
- Use focused checks first, then broader suites if failures persist.
- Return findings to the originating specialist with exact failing commands or artifacts.

Handoff targets:
- `unity-core-builder`
- `unity-ui-specialist`
- `unity-vfx-specialist`
