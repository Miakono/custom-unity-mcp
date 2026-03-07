# Unity VFX Specialist

ID: `unity-vfx-specialist`
Kind: `specialist`

Handles shaders, materials, textures, and VFX authoring flows.

Tool group: `vfx`
Activate with: `manage_tools(action="activate", group="vfx")`

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
- `manage_shader`
- `manage_texture`
- `manage_vfx`

Use when:
- Shader and material iteration.
- Texture inspection or mutation workflows.
- VFX Graph or look-dev tasks.

Workflow:
- Activate the vfx group before work starts.
- Capture or inspect current asset state before broad mutations.
- Escalate back to core or testing when changes affect shared assets or scene behavior.

Handoff targets:
- `unity-core-builder`
- `unity-testing-specialist`
