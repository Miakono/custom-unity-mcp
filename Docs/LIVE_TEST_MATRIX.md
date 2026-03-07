# Live Test Matrix

Status note:

This is a current supporting operational reference for live Unity smoke coverage and validation results.

Use this file for smoke-matrix scope and concrete live validation outcomes.
Use `Docs/V2_V3_VALIDATION_PLAN.md` for the broader validation workflow entry points.
Use `Docs/HANDOFF_2026-03-06.md` for the latest validated implementation snapshot.

Last updated: 2026-03-06

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

## Known Limits

- This matrix is representative and release-focused, not a full exhaustive certification of every repo tool.
- `diff_scene` remains partial in live depth even though the validated call path now works.
- Additional live coverage should be added for more asset-intelligence, pipeline-control, and dev-tool surfaces.
- Fireball visual tuning note: square-card artifacts were reduced by assigning `SmokeMat`, switching particle renderer mode to `Stretch`, and tuning start size/lifetime plus size-over-lifetime shaping.
