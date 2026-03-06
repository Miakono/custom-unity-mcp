# Unity MCP Fork Roadmap (Bezi-Inspired, Game-Agnostic)

Date: 2026-03-05

## Goals
- Keep the fork game-agnostic and safe by default.
- Improve reliability before adding higher-level automation.
- Add observable acceptance checks for each phase.
- See [Docs/PREMIUM_FEATURE_PLAN.md](Docs/PREMIUM_FEATURE_PLAN.md) for the post-foundation premium capability roadmap.

## v0.1 Safety and Reliability (Current)
Status: In Progress

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
- Fold the current audit coverage into a repeatable CI check.
- Close remaining documentation gaps around policy metadata and error contracts.

### Acceptance
- All mutating tool entrypoints perform preflight before sending Unity mutations.
- Read-only actions remain callable without unnecessary blocking.
- All patched Python modules pass `python -m py_compile`.

## v0.2 UX and Action Model
Status: Planned

### Scope
- Add an explicit action capability schema for each tool (read-only vs mutating metadata).
- Extend capability metadata to cover high-risk, local-only, runtime-only, dry-run, verification, and opt-in requirements.
- Improve error payloads for action mismatch and invalid parameter shapes.
- Add a consistent "what to do next" hint in common failure responses.
- Generate tool catalog / skill artifacts from the live registry.

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
1. Add machine-readable capability metadata for tool/action mutability, risk, runtime scope, and opt-in requirements.
2. Add generated tool catalog / skill output from the registry.
3. Add `docs/ERROR_CODES.md` to lock response contracts.
4. Start Phase 2 from [Docs/PREMIUM_FEATURE_PLAN.md](Docs/PREMIUM_FEATURE_PLAN.md): local code intelligence tools.
