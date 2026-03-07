# V2 & V3 Validation Plan

Date: 2026-03-06

Status note:

This is the current supporting validation workflow reference for the V2/V3 live-repair surface.

Use this file for validation entry points and scope.
Use `Docs/HANDOFF_2026-03-06.md` for the latest validated implementation snapshot.
Use `Docs/GAP_CLOSURE_PLAN.md` for current remediation priorities outside the narrow validation workflow.
Treat old planning docs indexed in `Docs/Archive/README.md` as historical-only unless explicitly reactivated.

## Purpose

This document tracks the validation workflow that is actually in use after the live Unity 6.3 repair pass. It replaces the earlier planning state that assumed large parts of V3 were still unregistered or unvalidated.

## Current Verified State

- Representative V2/V3 live runtime surface was re-tested against the active `BattleStreet` Unity 6.3 editor.
- The Unity bridge now accepts the payload shapes used by the server for the validated matrix.
- The previously missing live handlers for `preview_changes` and `diff_scene` were added to the Unity bridge.
- A reusable live smoke test now exists in `Server/tests/integration/test_live_unity_smoke_runner.py`.
- The live smoke runner now also supports an opt-in screenshot extension for scene capture, editor capture, and `get_last_screenshot`.
- One-command validation wrappers now exist in:
  - `Scripts/Run-LiveUnitySmoke.ps1`
  - `Scripts/Run-ValidationSuite.ps1`
- Workspace tasks now exist for:
  - `Run Validation Suite`
  - `Run Live Unity Smoke`

## Validation Entry Points

### 1. Targeted Server Validation

Run the targeted regression suite from the server root:

```powershell
python -m pytest \
  tests/test_v2_ping.py \
  tests/test_v2_manage_windows.py \
  tests/test_v2_manage_selection.py \
  tests/test_v2_project_config.py \
  tests/test_v2_spatial.py \
  tests/test_v3_navigation.py \
  tests/test_v3_transactions.py \
  tests/test_v3_waiters_events.py \
  tests/integration/test_live_unity_smoke_runner.py
```

Verified result from this pass:

- `213 passed in 34.12s`

### 2. Live Unity Smoke Validation

The live smoke runner executes a representative HTTP matrix against the MCP server and a running Unity editor.

Primary entry points:

- `Scripts/Run-LiveUnitySmoke.ps1`
- `Server/tests/integration/test_live_unity_smoke_runner.py`

Verified result from this pass:

- `1 passed, 1 deselected in 0.72s`
- The live test executed a 29-command representative matrix successfully.
- With screenshot smoke enabled, the same runner executes a 32-command representative matrix.

### 3. Combined Validation

Use the combined wrapper when validating both server and live Unity behavior together:

```powershell
./Scripts/Run-ValidationSuite.ps1 -UnityInstance "BattleStreet@63b48c2db2e73e3e"
```

This wrapper was executed successfully during this pass.

### 4. VS Code Task Entry Points

The workspace now exposes the same flows through `.vscode/tasks.json`.

- `Run Validation Suite`
- `Run Live Unity Smoke`

## What The Live Smoke Covers

The representative live matrix currently covers:

- connectivity and selection/window basics
- project/editor/player/build/define-symbol settings
- transform and spatial query surface
- asset search surface
- wait/event subscription surface
- transaction begin / preview / commit flow
- scene diff callability
- editor navigation and inspector targeting
- playbook dry-run surface
- benchmark surface

This is a release-blocker smoke suite, not an exhaustive all-tools certification pass.

## Known Gaps

These are the main remaining gaps after the current pass:

- `diff_scene` is callable and smoke-tested live, but the current live bridge implementation is still limited in depth and scope.
- The live smoke matrix is representative, not exhaustive across every tool in the catalog.
- Whole-editor screenshot validation lives beside this runner but is operationally narrower: the most reliable editor-window capture path is currently local Windows HTTP only.
- Generated specialist/subagent artifacts still need a tighter audit against the runtime-exposed tool story.

## Definition Of Done For This Validation Layer

For V2/V3 validation work to be considered closed, each change should satisfy all of the following:

- server-side regression coverage exists where practical
- Unity bridge handler exists and accepts the server payload shape
- live Unity smoke covers the feature group or a representative command from it
- docs point to the real validation entry point instead of aspirational plans

## Next Expansion Priorities

1. Expand the live smoke matrix beyond the current representative 29-command set.
2. Add more release-gate coverage for asset-intelligence and pipeline-control surfaces.
3. Deepen `diff_scene` beyond the current limited live implementation.
4. Keep generated docs/artifacts aligned with the verified runtime surface.
