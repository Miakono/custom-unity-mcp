# Unity MCP Gap Closure Plan (Repo-Grounded)

**Goal**: Close real feature and reliability gaps without damaging Unity asset integrity or existing release workflows.  
**Repo Snapshot Date**: 2026-03-07.

This is the current remediation plan for repo cleanup and workflow hardening.
It is grounded in the checked-in source, generated artifacts, and recent validation work, but it is not a claim that every acceptance criterion below is already passing.

Document role:

- Use this file for current gap-remediation priorities.
- Use `Docs/HANDOFF_2026-03-06.md` for the latest validated implementation and smoke-status snapshot.
- Treat premium/legacy planning docs indexed under `Docs/Archive/README.md` as historical records unless explicitly reactivated.

Archive guardrail:

- Active planning and execution sources are the current docs in `Docs/`.
- Archived planning docs under `Docs/Archive/` are non-authoritative for current scope unless a current doc explicitly reactivates them.

---

## Reality Check (Before Any Work)

This plan replaces stale assumptions from the prior draft.

- Screenshot capability is now implemented end-to-end for the current supported path: `manage_screenshot` exposes `capture_editor_window` and `get_last_screenshot`, `analyze_screenshot` supports `compare_screenshots`, and local Windows HTTP editor capture is handled server-side when available.
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

1. Keep `get_last_screenshot` in the Python-exposed `manage_screenshot` action list.
2. Treat it as part of the supported visual QA workflow because Unity-side storage and retrieval now exist and route tests cover the surface.

Rationale:

1. The action is implemented and should no longer be documented as aspirational or removed.

### 0.1 Screenshot contract status

Current repo-grounded state:

- The server source exposes screenshot actions under `group="visual_qa"`.
- The Unity-side implementation now supports `capture_game_view`, `capture_scene_view`, `capture_object_preview`, `capture_editor_window`, and `get_last_screenshot`.
- Local Windows HTTP `capture_editor_window` requests are intercepted server-side and returned with backend marker `server_hwnd_client_bbox` when the Unity editor window can be resolved.
- Screenshot comparison is available through `analyze_screenshot(action="compare_screenshots", ...)`.

Actions:

1. Keep `visual_qa` as the documented screenshot group.
2. Preserve the current response contract (`image_base64`, `data_uri`, optional `file_path`) and backend marker fields.
3. Document the supported operating boundary clearly: whole-editor capture is currently a local Windows HTTP capability and remains OS/window-state constrained.

### 0.2 Baseline snapshot and publish

Capture and commit a baseline report in docs:

1. Tool/group inventory from generated catalog.
2. Live smoke status for key bridge commands.
3. Latency baseline (p50/p95) for representative read and write calls.

**Acceptance Criteria**:

- [x] `manage_screenshot` source-facing and generated-artifact-facing actions exactly match executable Unity actions.
- [x] No unknown group registration errors for screenshot tooling.
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

### 2.1 Screenshot workflow status

Action:

1. `compare_screenshots` is now implemented in `analyze_screenshot`.
2. `get_last_screenshot` is now implemented through the Unity screenshot tool state.
3. Remaining work is operational hardening, not surface creation: document limits, keep smoke coverage on, and add more diagnostics if window selection drifts.

### 2.2 Wire visual tooling coherently

Action:

1. Align `manage_screenshot`, `manage_video_capture`, and `analyze_screenshot` into a documented flow.
2. Ensure output contracts are consistent and renderable by common MCP clients.

**Acceptance Criteria**:

- [x] A full capture -> analyze -> compare flow works in automated tests.
- [x] Returned image payloads are accepted by target MCP clients.
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
