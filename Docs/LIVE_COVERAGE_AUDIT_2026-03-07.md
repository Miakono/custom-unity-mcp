# Live Coverage Audit 2026-03-07

This audit compares the current live smoke matrix in `Server/tests/integration/test_live_unity_smoke_runner.py` against the generated runtime tool catalog in `Generated/Catalog/tool_catalog.json`.

## Current Coverage Snapshot

- Current representative live matrix: 29 commands in the default release-focused pass.
- Screenshot smoke adds 3 more commands when enabled.
- Extended surface smoke now adds representative coverage across `animation`, `asset_intelligence`, `diff_patch`, `pipeline`, `pipeline_control`, `project_config`, `profiling`, `scripting_ext`, `testing`, `ui`, `vfx`, and `visual_qa`.
- Separate opt-in gates now exist for the remaining workflow-oriented surfaces: `UNITY_MCP_INCLUDE_STATEFUL_WORKFLOW_SMOKE=1` and `UNITY_MCP_INCLUDE_ASYNC_TEST_SMOKE=1`.
- Runtime UI remains separately gated because it is still play-mode and environment sensitive.

## Group Coverage Depth

| Group | Covered Tools | Total Tools | Status |
| --- | ---: | ---: | --- |
| animation | 0 | 1 | zero |
| asset_intelligence | 1 | 5 | thin |
| core | 4 | 44 | thin |
| dev_tools | 1 | 4 | thin |
| diff_patch | 1 | 5 | thin |
| events | 3 | 3 | full |
| input | 0 | 1 | zero |
| navigation | 4 | 5 | strong |
| pipeline | 1 | 8 | thin |
| pipeline_control | 3 | 4 | partial |
| profiling | 0 | 2 | zero |
| project_config | 3 | 10 | thin |
| scripting_ext | 0 | 1 | zero |
| spatial | 2 | 2 | full |
| testing | 0 | 5 | zero |
| transactions | 2 | 3 | partial |
| ui | 0 | 2 | zero |
| vfx | 0 | 3 | zero |
| visual_qa | 0 catalog-counted in current committed matrix, but screenshot smoke uses `manage_screenshot` | 1 | drift |

## Zero-Coverage Tool Groups At Initial Audit Time

- `animation`: `manage_animation`
- `input`: `manage_input_system`
- `profiling`: `manage_profiler`, `record_profiler_session`
- `scripting_ext`: `manage_scriptable_object`
- `testing`: `audit_prefab_integrity`, `audit_scene_integrity`, `get_test_job`, `preflight_audit`, `run_tests`
- `ui`: `manage_runtime_ui`, `manage_ui`
- `vfx`: `manage_shader`, `manage_texture`, `manage_vfx`

Update after extended-surface smoke implementation:

- Representative live smoke coverage is now wired for `animation`, `input`, `profiling`, `scripting_ext`, `testing`, `manage_ui`, `manage_vfx`, `analyze_screenshot`, `build_asset_index`, `diff_asset`, `diff_prefab`, and multiple read-only `project_config` surfaces through the opt-in extended surface gate.
- `manage_runtime_ui` remains separately opt-in under `UNITY_MCP_INCLUDE_RUNTIME_UI_SMOKE=1` because it is runtime-only and play-mode sensitive.

## Thin-Coverage Tool Groups

- `core`: still intentionally representative-only; the goal is release-gate breadth, not exhaustive coverage of all 44 core tools in one pass
- `navigation`: still representative-only, with focus/framing/open-inspector coverage rather than every navigation variant
- `transactions`: the default pass still covers begin/append/preview/commit, while rollback is now isolated behind the stateful workflow gate

## Stateful Coverage Status

The safe representative additions are wired into the extended surface gate. The previously remaining workflow-oriented tools are now also represented, but behind separate opt-in gates so they do not destabilize the default release-focused pass.

### Stateful Workflow Gate

```python
```python
CommandSpec("start trace", "start_trace", {"tags": ["live-smoke"]}),
CommandSpec("start fixture capture", "start_fixture_capture", {"scenario": "live_smoke_stateful"}),
CommandSpec("start fixture replay", "start_fixture_replay", {"fixtures": []}),
CommandSpec("record pipeline", "record_pipeline", {"action": "start", "name": "<temp-name>"}),
CommandSpec("save pipeline", "save_pipeline", {"name": "<temp-name>", "steps": [{"tool": "ping", "params": {}}], "overwrite": True}),
CommandSpec("replay pipeline", "replay_pipeline", {"name": "<temp-name>", "dry_run": True}),
CommandSpec("create playbook", "create_playbook", {"action": "from_pipeline", "pipeline_name": "<temp-name>", "name": "<temp-playbook>", "overwrite": True}),
CommandSpec("record pipeline", "record_pipeline", {"action": "start"}),
CommandSpec("stop pipeline recording", "stop_pipeline_recording", {"action": "discard"}),
CommandSpec("manage shader", "manage_shader", {"action": "create|read|delete", "...": "temp shader payload"}),
CommandSpec("manage texture", "manage_texture", {"action": "create|delete", "...": "temp texture payload"}),
CommandSpec("apply scene patch", "apply_scene_patch", {"dry_run": True, "operations": [...] }),
CommandSpec("apply prefab patch", "apply_prefab_patch", {"dry_run": True, "operations": [...] }),
CommandSpec("record profiler session", "record_profiler_session", {"duration_seconds": 1}),
CommandSpec("rollback changes", "rollback_changes", {"action": "get_rollback_summary|rollback_transaction", "transaction_id": "<temp-id>"}),
```

The runner now cleans up the temporary repo-local pipeline and playbook artifacts it creates for this gate as best effort after execution.

### Async Test Gate

```python
CommandSpec("run tests", "run_tests", {"mode": "EditMode"}),
CommandSpec("get test job", "get_test_job", {"job_id": "<live-job-id>", "wait_timeout": 1}),
```

This gate remains separate because it depends on a valid Unity Test Runner setup in the connected project.

## Artifact Audit Findings

### Finding 1: `manage_screenshot` was missing from runtime-generated artifacts

- Root cause: `Server/src/services/tools/manage_screenshot.py` imported `mcpforunityserver.*` modules that are not importable during offline registry bootstrap.
- Effect: catalog and subagent generation silently skipped `manage_screenshot`.
- Fix: migrate the tool to the same import and transport pattern used by the rest of `services.tools`.

### Finding 2: committed generated subagent artifacts were stale

- `Generated/Subagents/subagents.json` currently reports 11 groups and 12 subagents.
- Runtime registry defines 19 groups.
- After the registration fix, subagent artifacts should be regenerated from the live registry.

## Release-Gate Recommendation

Prioritize validation in this order:

1. `ui` and `visual_qa`
2. `asset_intelligence`
3. `pipeline` and `pipeline_control`
4. deeper `diff_patch` behavior checks
5. one representative command each for zero-coverage groups
6. 200-invocation transport and screenshot SLO benchmarks

## Implementation Note

The live smoke runner now supports additive opt-in expansions instead of folding every new surface into the default representative pass:

- `UNITY_MCP_INCLUDE_SCREENSHOT_SMOKE=1` adds screenshot surface checks.
- `UNITY_MCP_INCLUDE_EXTENDED_SURFACE_SMOKE=1` adds broader read-only or dry-run representative coverage across visual QA, animation, asset-intelligence, diff/patch, pipeline, pipeline-control, project-config, UI, input, profiling status, testing, scripting-ext, and VFX.
- `UNITY_MCP_INCLUDE_STATEFUL_WORKFLOW_SMOKE=1` adds the remaining workflow-oriented surfaces that create temporary artifacts, run short profiler captures, or exercise rollback and patch-apply flows.
- `UNITY_MCP_INCLUDE_ASYNC_TEST_SMOKE=1` adds the Unity Test Runner async job lifecycle smoke.
- `UNITY_MCP_INCLUDE_RUNTIME_UI_SMOKE=1` adds play-mode runtime UI element discovery smoke.

This keeps the default release-gate matrix stable while still allowing broader end-to-end validation in one runner.
