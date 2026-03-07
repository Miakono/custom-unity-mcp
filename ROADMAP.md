# Unity MCP Fork Roadmap (Bezi-Inspired, Game-Agnostic)

Date: 2026-03-05

## Current Document Map
- Current remediation and gap-priority plan: [Docs/GAP_CLOSURE_PLAN.md](Docs/GAP_CLOSURE_PLAN.md)
- Current validated implementation snapshot: [Docs/HANDOFF_2026-03-06.md](Docs/HANDOFF_2026-03-06.md)
- Current validation workflow reference: [Docs/V2_V3_VALIDATION_PLAN.md](Docs/V2_V3_VALIDATION_PLAN.md)
- Current subagent/catalog usage reference: [Docs/SUBAGENTS.md](Docs/SUBAGENTS.md)
- Supporting live smoke and task-specific operational references: [Docs/LIVE_TEST_MATRIX.md](Docs/LIVE_TEST_MATRIX.md), [Docs/MAGE_FIREBALL_VFX.md](Docs/MAGE_FIREBALL_VFX.md)
- Historical archive index (superseded plans and handoffs): [Docs/Archive/README.md](Docs/Archive/README.md)

Use this roadmap as the top-level index. Do not treat all plan documents as equally current.

## Goals
- Keep the fork game-agnostic and safe by default.
- Improve reliability before adding higher-level automation.
- Add observable acceptance checks for each phase.
- See [Docs/GAP_CLOSURE_PLAN.md](Docs/GAP_CLOSURE_PLAN.md) for the current repo-grounded remediation plan.
- See [Docs/Archive/README.md](Docs/Archive/README.md) for superseded premium and implementation planning docs.

Archive guardrail:
- If guidance in an archived planning document conflicts with this roadmap or current docs in `Docs/`, treat archived guidance as historical context only.

## v0.1 Safety and Reliability (Current)
Status: Complete

### Delivered
- Added a centralized server-side action policy registry to classify read-only vs mutating tool actions.
- Added server-side preflight gating to mutating tools:
  - `manage_material`
  - `manage_shader`
  - `manage_ui`
  - `manage_vfx`
  - `manage_scriptable_object`
  - `script_apply_edits`
  - `manage_animation`
  - `execute_menu_item`
  - `execute_custom_tool`
  - `manage_editor` (non-telemetry actions)
  - `manage_script` (create/delete)
  - `batch_execute`
  - `apply_text_edits`
  - `create_script`
  - `delete_script`
- Converted read-only actions that were over-gated to use centralized policy decisions instead of blanket preflight checks.
- Added an audit test that prevents direct tool-module `preflight(...)` usage outside the centralized policy layer.

### Remaining
- Keep CI checks pinned to the latest generated artifacts and policy tests.
- Continue tightening documentation drift between implementation and roadmap state.

### Acceptance
- All mutating tool entrypoints perform preflight before sending Unity mutations.
- Read-only actions remain callable without unnecessary blocking.
- All patched Python modules pass `python -m py_compile`.

## v0.2 UX and Action Model
Status: In Progress

### Scope
- Add an explicit action capability schema for each tool (read-only vs mutating metadata).
- Extend capability metadata to cover high-risk, local-only, runtime-only, dry-run, verification, and opt-in requirements.
- Improve error payloads for action mismatch and invalid parameter shapes.
- Add a consistent "what to do next" hint in common failure responses.
- Generate tool catalog / skill artifacts from the live registry.

### Delivered (Current)
- Action capability metadata now covers core and premium tool families, including:
  - mutating vs read-only action classification for mixed tools
  - high-risk flags
  - local-only and runtime-only flags
  - dry-run support metadata where implemented
- Generated artifacts are now synced from the live registry and policy layer:
  - `Generated/Catalog/tool_catalog.json`
  - `Generated/Subagents/subagents.json`
  - `Generated/ErrorCatalog/error_catalog.json`
- Error catalogs and docs are generated and versioned for stable code references.

### Remaining
- Expand action-level coverage for newly added runtime bridge and future domains as they land.
- Continue broadening direct tests for premium tool surfaces and edge-case payloads.

### Acceptance
- Tool metadata can be programmatically queried for mutability.
- Tool metadata can also express runtime/reflection risk and capability requirements.
- Error responses use stable `code` values and include one actionable rewrite hint.
- Batch command failures identify failing step with normalized command echo.
- Generated docs remain in sync with the registered tools.

## v0.3 Agentic Workflows and Checkpoints
Status: Planned

### Scope
- Introduce optional checkpoint/create-restore flow for high-risk multi-step edits.
- Add plan-preview mode for batch operations (dry-run with validation report).
- Add post-mutation verification hooks where practical (hash/asset existence checks).
- Use the same primitives for future runtime/reflection/package/addressables workflows.

### Acceptance
- Multi-step mutating workflows can optionally create and restore checkpoints.
- Dry-run mode returns deterministic pre-execution validation output.
- Verification metrics are emitted for edited/created/deleted artifacts.

## Design Constraints
- No game-specific assumptions in server or package code.
- Keep tool contracts backward-compatible unless versioned.
- Prefer additive changes and explicit feature flags for behavioral shifts.

## Suggested Next Tasks
1. Complete Phase 2 acceptance by adding deeper end-to-end tests for premium/runtime tool paths.
2. Start checkpoint/restore primitives and deterministic dry-run validation output from v0.3.
3. Add a release checklist step that regenerates and verifies all `Generated/*` artifacts in CI.
4. Keep roadmap/plan status updates in lockstep with implementation merges.
