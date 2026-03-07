# Live Test Matrix

Status note:

This is a current supporting operational reference for live Unity smoke coverage and validation results.

Use this file for smoke-matrix scope and concrete live validation outcomes.
Use `Docs/V2_V3_VALIDATION_PLAN.md` for the broader validation workflow entry points.
Use `Docs/HANDOFF_2026-03-06.md` for the latest validated implementation snapshot.

Last updated: 2026-03-07

## Scope

This document tracks live verification against a running Unity editor instance via the local MCP server.

Test target during this pass:

- Unity project: `BattleStreet`
- Unity version: `6000.3.8f1`
- Active Unity instance used for validation: `BattleStreet@63b48c2db2e73e3e`
- Smoke asset root: `Assets/MCPToolSmokeTests/Live_20260306_003519`
- Smoke scene used: `Assets/MCPToolSmokeTests/Scenes/ToolSmoke_20260305_233638.unity`

## Automated Validation Entry Points

Reusable validation entry points now available:

- `Server/tests/integration/test_live_unity_smoke_runner.py`
- `Scripts/Run-LiveUnitySmoke.ps1`
- `Scripts/Run-ValidationSuite.ps1`
- `Run Validation Suite` VS Code task
- `Run Live Unity Smoke` VS Code task

## Verified Automation Results

### Targeted Server Validation

Verified during this pass:

- `213 passed in 34.12s`

### Live Unity Smoke Validation

Verified during this pass:

- `1 passed, 1 deselected in 0.72s`

The live smoke test executed a representative 29-command matrix over `/api/command` against the active Unity editor.

## Representative Live Matrix Coverage

The automated live smoke currently exercises:

- ping and basic connectivity
- selection and window management
- hierarchy focus and scene framing
- project, editor, player, build, and define-symbol settings
- transform and spatial query surface
- advanced asset search surface
- compile-idle waiter surface
- event subscribe and unsubscribe flow
- transaction begin, preview, and commit flow
- scene diff callability
- editor navigation, framing, and inspector targeting
- playbook dry-run surface
- benchmark surface

When extended surface smoke is enabled with `UNITY_MCP_INCLUDE_EXTENDED_SURFACE_SMOKE=1`, the matrix also exercises representative commands from:

- `animation`: `manage_animation(action="clip_get_info")`
- `asset_intelligence`: `build_asset_index(action="validate")`, `asset_index_status`, `find_asset_references`, `summarize_asset`
- `diff_patch`: `diff_asset(compare_mode="current_vs_saved")`, `diff_prefab(compare_mode="current_vs_saved")`
- `pipeline`: `list_playbooks`, `list_pipelines`
- `pipeline_control`: `manage_import_pipeline(action="get_import_queue_status")`
- `project_config`: `analyze_asset_dependencies`, `find_builtin_assets`, `get_component_types`, `get_object_references`, `list_shaders`, `manage_asset_import_settings(action="get_import_settings")`, `manage_project_memory(action="summarize_conventions")`
- `scripting_ext`: `manage_scriptable_object(action="modify", dry_run=true)` against a smoke ScriptableObject fixture
- `ui`: `manage_ui(action="list")`
- `input`: `manage_input_system(action="asset_get_all")`
- `profiling`: `manage_profiler(action="get_status")`
- `testing`: `audit_scene_integrity(scope="active")`, `audit_prefab_integrity`, `preflight_audit`
- `vfx`: `manage_vfx(action="ping")`
- `visual_qa`: `analyze_screenshot(action="compare_screenshots")` using a deterministic inline smoke image

When screenshot smoke is enabled, the live matrix also exercises:

- `manage_screenshot(action="capture_scene_view")`
- `manage_screenshot(action="capture_editor_window")`
- `manage_screenshot(action="get_last_screenshot")`

When runtime UI smoke is enabled with `UNITY_MCP_INCLUDE_RUNTIME_UI_SMOKE=1`, the matrix also exercises:

- `manage_runtime_ui(action="find_elements")`

When stateful workflow smoke is enabled with `UNITY_MCP_INCLUDE_STATEFUL_WORKFLOW_SMOKE=1`, the matrix additionally exercises the previously uncovered workflow-oriented surfaces:

- `dev_tools`: `start_trace`, `start_fixture_capture`, `start_fixture_replay`
- `diff_patch`: `apply_scene_patch(dry_run=true)`, `apply_prefab_patch(dry_run=true)`
- `pipeline`: `record_pipeline`, `stop_pipeline_recording`, `save_pipeline`, `replay_pipeline(dry_run=true)`, `create_playbook`
- `profiling`: `record_profiler_session`
- `transactions`: `rollback_changes`
- `vfx`: `manage_shader(create/read/delete)`, `manage_texture(create/delete)`

The stateful workflow gate creates temporary pipeline/playbook artifacts and then removes the repo-local temporary files as best-effort cleanup after the pass.

When async test smoke is enabled with `UNITY_MCP_INCLUDE_ASYNC_TEST_SMOKE=1`, the matrix additionally exercises:

- `testing`: `run_tests`, `get_test_job`

This gate is intentionally separate because it depends on the connected Unity project having a usable Unity Test Runner setup and can be more time-sensitive than the main editor-surface matrix.

## Newly Validated Live V2/V3 Bridge Surface

The previously problematic V2/V3 bridge surface was revalidated against the active `BattleStreet` editor after fixing compilation and registration issues in `MCPForUnity/Editor/Tools/LiveV2V3Tools.cs`.

Live-passed in this representative pass:

- `manage_project_settings`
- `manage_editor_settings`
- `manage_player_settings`
- `manage_build_settings`
- `manage_define_symbols`
- `manage_registry_config`
- `navigate_editor`
- `focus_hierarchy`
- `frame_scene_target`
- `open_inspector_target`
- `search_assets_advanced`
- `wait_for_editor_condition`
- `subscribe_editor_events`
- `manage_transactions`
- `preview_changes`
- `diff_scene`
- `run_playbook`
- `run_benchmark`

## Behavioral Notes

- `preview_changes` and `diff_scene` are now callable through the live Unity bridge.
- `run_playbook` accepts the payload shapes used by the current server-side caller and succeeds in dry-run mode live.
- `run_benchmark` accepts the validated benchmark request shape used by the representative smoke flow.
- The smoke runner no longer hardcodes a single scene object; it probes a list of known smoke objects and binds to one that exists in the active scene.
- During refresh or domain reload, the Unity session can briefly disappear from `/api/instances`; this is expected while the editor recompiles.
- For local Windows HTTP sessions, `capture_editor_window` may be served directly by the Python server using backend marker `server_hwnd_client_bbox` instead of the Unity-side native capture path.
- The screenshot smoke extension increases the representative HTTP matrix from 29 commands to 32 commands.

## Known Limits

- This matrix is representative and release-focused, not a full exhaustive certification of every repo tool.
- `diff_scene` remains partial in live depth even though the validated call path now works.
- Additional live coverage should be added for more asset-intelligence, pipeline-control, and dev-tool surfaces.
- Whole-editor screenshot capture is currently validated as a local Windows capability and still depends on OS-visible/restorable Unity window state.
- Runtime UI smoke remains separately opt-in because it requires play-mode/runtime gating and is expected to be more environment-sensitive than the editor-surface matrix.
- The extended surface gate now covers all previously zero-live-coverage catalog groups except runtime-only `manage_runtime_ui`, which remains separately gated.
- Stateful workflow and async test coverage are now available, but they remain separately gated because they are more artifact-producing or environment-sensitive than the release-focused representative matrix.
- Fireball visual tuning note: square-card artifacts were reduced by assigning `SmokeMat`, switching particle renderer mode to `Stretch`, and tuning start size/lifetime plus size-over-lifetime shaping.
