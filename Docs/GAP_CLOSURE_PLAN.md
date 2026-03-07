# Unity MCP Gap Closure Plan (Repo-Grounded)

**Goal**: Close real feature and reliability gaps without damaging Unity asset integrity or existing release workflows.  
**Repo Snapshot Date**: 2026-03-06.

This is the current remediation plan for repo cleanup and workflow hardening.
It is grounded in the checked-in source, generated artifacts, and recent validation work, but it is not a claim that every acceptance criterion below is already passing.

Document role:

- Use this file for current gap-remediation priorities.
- Use `Docs/HANDOFF_2026-03-06.md` for the latest validated implementation and smoke-status snapshot.
- Treat `Docs/PREMIUM_FEATURE_PLAN*.md` as historical planning records unless explicitly reactivated.

---

## Reality Check (Before Any Work)

This plan replaces stale assumptions from the prior draft.

- Screenshot capability already exists in source (`manage_screenshot`, Unity `ManageScreenshot`), but the repo still shows source-vs-export contract drift that should be cleaned up before calling the surface stable.
- UI Toolkit support already exists (`manage_ui`, `manage_runtime_ui`, `UIToolkitAutomation`).
- Tracked virtualenv files under `Server/.venv/` are already `0`.
- `Generated/` contains publishable artifacts (catalog, error catalog, subagents), not disposable build junk.
- Unity `.meta` files are required for GUID stability and must not be mass-deleted.

Recent validated state that should not be reopened casually:

- The nullable screenshot compile break in `ManageScreenshot.cs` has already been fixed.
- The `focus_hierarchy` resolver drift in `LiveV2V3Tools.cs` has already been fixed and live-smoke validated.
- Current bridge hardening should preserve that green state rather than restart broad refactors blindly.

**Hard Safety Rules**:

- Do not remove `**/*.meta` globally.
- Do not delete `Generated/` wholesale.
- Do not perform broad namespace/package renames until transport + registry tests are green.

---

## Phase 0: Contract Alignment and Baseline (2-3 days)

**Goal**: Eliminate current inconsistencies that cause false failures and drift.

### 0.0 Binding decision: `get_last_screenshot`

Decision for this run:

1. Remove `get_last_screenshot` from the Python-exposed `manage_screenshot` action list in Phase 0.
2. Re-introduce it only after a Unity-side implementation exists and is tested end-to-end.

Rationale:

1. Avoid shipping an advertised action that currently returns unsupported behavior.

### 0.1 Fix `manage_screenshot` contract mismatch

Current repo-grounded mismatch:

- The server source currently advertises `get_last_screenshot` and still uses `group="visual"`.
- The Unity-side implementation path currently supports only `capture_game_view`, `capture_scene_view`, and `capture_object_preview`.
- The generated catalog currently emphasizes `visual_qa` tooling, so the published story is not as explicit or coherent as the source suggests.

Actions:

1. Execute the binding decision from Phase 0.0.
2. Align tool group naming: use `visual_qa` consistently, or formally document and export `visual` as an intentional public group.
3. Normalize parameter aliasing and response keys (`image_base64`, `data_uri`, file path mode).

### 0.2 Baseline snapshot and publish

Capture and commit a baseline report in docs:

1. Tool/group inventory from generated catalog.
2. Live smoke status for key bridge commands.
3. Latency baseline (p50/p95) for representative read and write calls.

**Acceptance Criteria**:

- [ ] `manage_screenshot` source-facing and generated-artifact-facing actions exactly match executable Unity actions.
- [ ] No unknown group registration errors for screenshot tooling.
- [ ] Baseline report recorded and referenced by subsequent phases.

### Phase 0 Gate (must pass before Phase 1)

1. Validation suite passes for server-side tests touching screenshot/tool-registry surfaces.
2. Live smoke run passes for `manage_screenshot` actions that remain exposed.
3. No compile errors reported by `validate_compile_health`.

---

## Phase 1: Reliability and Bridge Hardening (Week 1)

**Goal**: Reduce "registered but unsupported" failures and compile-related regressions.

### 1.1 Refactor `LiveV2V3Tools.cs` safely

Action:

1. Create a rollback checkpoint before any split (file-scoped checkpoint for touched bridge files).
1. Split by domain (`transactions`, `events`, `diff_patch`, `navigation`, `pipeline_control`, `dev_tools`).
2. Keep behavior unchanged during split.
3. Retain a thin aggregator only if needed for route compatibility.

### 1.2 Add compile-health gate to validation flow

Action:

1. Run `validate_compile_health` and `read_console` checks after bridge edits and Unity refresh.
2. Fail fast on compile errors before concluding handler registration is broken.
3. Add regression checks for commands previously known to drift (`preview_changes`, `diff_scene`, etc.).

### 1.3 Standardize payload shape coverage

Action:

1. Add tests for snake_case + camelCase aliases where transport history requires both.
2. Document canonical payload keys and accepted aliases in tool docs.

**Acceptance Criteria**:

- [ ] No compile errors after bridge refactor.
- [ ] Live smoke matrix has no "Unknown or unsupported command type" for in-scope tools.
- [ ] Alias coverage tests exist for known bridge-sensitive parameters.

### Phase 1 Gate (must pass before Phase 2)

1. `validate_compile_health` reports healthy state.
2. `read_console` has no new compile-error entries attributable to bridge changes.
3. Live smoke subset passes for `preview_changes`, `diff_scene`, and one command from each split domain.

---

## Phase 2: Visual QA Completion (Week 2)

**Goal**: Turn existing screenshot capability into a stable visual QA workflow.

### 2.1 Complete screenshot workflow

Action:

1. Add `compare_screenshots` (or equivalent diff path) by integrating with diff/analysis tools.
2. Add bounded in-memory recent capture buffer only if needed (`get_last_screenshot` implementation path).
3. Enforce predictable size/format limits and timeouts.

### 2.2 Wire visual tooling coherently

Action:

1. Align `manage_screenshot`, `manage_video_capture`, and `analyze_screenshot` into a documented flow.
2. Ensure output contracts are consistent and renderable by common MCP clients.

**Acceptance Criteria**:

- [ ] A full capture -> analyze -> compare flow works in automated tests.
- [ ] Returned image payloads are accepted by target MCP clients.
- [ ] 1080p screenshot capture meets latency/error SLOs: p50 <= 750 ms, p95 <= 1200 ms, failure rate <= 1% over 100 runs.

### Phase 2 Gate (must pass before Phase 3)

1. Capture -> analyze -> compare workflow passes end-to-end smoke tests.
2. Screenshot SLOs pass over the defined sample window.
3. No regression in existing `manage_ui` render/capture-related tests.

---

## Phase 3: UI Toolkit Depth and Boundaries (Week 3)

**Goal**: Close functional gaps in existing UI tooling without introducing duplicate tools.

### 3.1 Expand existing `manage_ui` and `manage_runtime_ui`

Action:

1. Add missing high-value actions to existing tools (do not create `manage_ui_toolkit` duplicate).
2. Ensure editor-time and play-mode boundaries are explicit and tested.
3. Improve element query reliability (path, name, type, text, automation id).

### 3.2 Clarify scope for built-in Unity editor windows

Action:

1. Treat built-in editor window automation as stretch due Unity internal API variability.
2. Keep core acceptance centered on custom UIDocument/runtime and supported editor surfaces.

**Acceptance Criteria**:

- [ ] `manage_ui` + `manage_runtime_ui` cover documented core actions with passing integration tests.
- [ ] Runtime UI Toolkit automation passes play-mode smoke tests.
- [ ] Scope boundaries are documented to avoid unsupported expectations.

### Phase 3 Gate (must pass before Phase 4)

1. Integration tests for core editor UI actions pass.
2. Play-mode runtime UI smoke tests pass.
3. Unsupported built-in editor-window scenarios are explicitly documented as out-of-scope.

---

## Phase 4: Performance Decision Gate (Week 4)

**Goal**: Prove need before introducing native transport complexity.

### 4.1 Measure first

Action:

1. Benchmark existing transport with representative command sets.
2. Track p50/p95 latency and error rates under realistic sequences.

Benchmark protocol:

1. Sample size: minimum 200 invocations across mixed read/write operations.
2. Record: p50, p95, timeout rate, and command failure rate.

### 4.2 Conditional native bridge spike

Proceed only if measured latency blocks user workflows.

Go/No-Go thresholds:

1. **No-Go for native spike** if existing transport meets: p50 <= 120 ms, p95 <= 250 ms, failure rate <= 2%.
2. **Go for native spike** if either condition holds across two benchmark runs:
	a. p95 > 300 ms for core interactive commands, or
	b. failure rate > 2% due to transport bottlenecks.

Action:

1. Build a narrow spike (read-only core queries + one mutation path).
2. Keep fallback to current Python-mediated flow.
3. Define parity matrix from real usage, not assumed full-surface parity.

**Acceptance Criteria**:

- [ ] Documented go/no-go decision with benchmark evidence.
- [ ] If go: native spike validated with fallback behavior.

### Phase 4 Gate (must pass before any broad transport change)

1. Decision record includes benchmark artifacts and threshold outcomes.
2. If "go": spike demonstrates fallback to current Python-mediated flow for unsupported paths.

---

## Phase 5: Optional DOTS/ECS Track (Backlog, Demand-Driven)

**Goal**: Add ECS support only when project demand is confirmed.

### 5.1 Gate conditions

Start only if:

1. Target projects actively use Entities.
2. Core reliability phases are complete.

### 5.2 Implementation approach

Action:

1. Add conditional ECS tooling behind package/version checks.
2. Avoid hard asmdef breakage; use version defines and graceful capability reporting.

**Acceptance Criteria**:

- [ ] Works when Entities package is present.
- [ ] Graceful "not available" behavior when package is absent.

---

## Non-Goals / Removed From Prior Draft

These items were intentionally removed because they are risky or inaccurate:

1. Deleting all `.meta` files.
2. Deleting `Generated/` as "artifact cleanup."
3. Claiming screenshot/UI Toolkit capability is missing.
4. Manual registration edits in `tool_registry.py` for normal tool additions.
5. Mandatory package/folder renames as early cleanup work.

---

## Quick Wins (Do First)

1. Resolve `manage_screenshot` action/group mismatch.
2. Add compile-health + live-smoke gate to every bridge change.
3. Keep generated catalogs in sync by running export flows before handoff/release.

---

## Implementation Priority

```
Week 0: Contract alignment + baseline
Week 1: Bridge reliability hardening
Week 2: Visual QA completion
Week 3: UI Toolkit depth on existing tools
Week 4: Performance measurement + native go/no-go
Backlog: ECS (only if demanded)
```

---

## Success Metrics (Updated)

| Metric | Current Baseline | Target |
|--------|------------------|--------|
| Screenshot contract alignment | Partial mismatch | 0 unsupported advertised actions across 100 screenshot invocations |
| Live bridge unsupported-command rate | Non-zero in historical runs | 0 `Unknown or unsupported command type` errors in in-scope smoke matrix run |
| UI automation coverage | Existing but uneven | 100% pass rate for defined core `manage_ui` and `manage_runtime_ui` integration suites |
| Release artifact drift | Possible if exports skipped | 0 stale generated artifacts at handoff/release (catalog/subagents/error-catalog regenerated in same change window) |
| Latency decision quality | Anecdotal | Go/No-Go record includes 200+ invocation benchmark data and threshold-based decision |

---

## Notes

- This plan favors contract correctness and reliability over headline feature count.
- Existing capabilities should be hardened and integrated before adding new tool families.
- Architectural pivots (native transport, ECS) stay conditional on measured need.
- This file supersedes the premium plan set as the current remediation doc, but it does not replace those documents as historical records of earlier scope and sequencing.
