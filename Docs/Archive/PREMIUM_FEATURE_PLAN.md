# Premium Feature Plan

Date: 2026-03-05

Status note: historical planning record.
For the current repo-grounded remediation plan, see `../GAP_CLOSURE_PLAN.md`.
For the latest validated implementation snapshot, see `../HANDOFF_2026-03-06.md`.

## Purpose
- Define the next implementation phases after the safety/policy foundation.
- Focus on premium-value features that materially expand capability instead of adding more low-level CRUD tools.
- Keep the fork game-agnostic and MCP-native.
- Maximize useful tool coverage without bypassing the centralized safety model.

## Current Baseline
- Centralized action policy and preflight enforcement are in place for server tool entrypoints.
- Read-only vs mutating behavior is now routed through a shared policy layer.
- The fork already covers core Unity MCP categories:
  - scenes
  - gameobjects
  - components
  - assets
  - prefabs
  - scripts
  - materials/shaders/textures/VFX
  - animation
  - UI authoring
  - editor control
  - tests

## Strategic Gaps
The highest-value remaining gaps are now:
- deeper test depth for premium/runtime tool families (beyond baseline coverage)
- checkpoint/restore workflows for multi-step high-risk operations
- stronger post-mutation verification and job-progress primitives across long-running operations
- runtime/in-game MCP maturity and isolation hardening
- ongoing documentation/metadata drift control as new tools are added

## Planning Principles
- New feature families must route through the same policy/capability layer as existing tools.
- Add breadth, but separate low-risk editor workflows from high-risk runtime/reflection workflows.
- Prefer feature flags and explicit opt-in for anything that can invoke arbitrary methods or mutate live runtime state.
- Ship read/inspect/validate flows before broad mutation where practical.
- Generate documentation and capability metadata from the live registry instead of hand-maintaining parallel catalogs.

## Delivery Order

### Phase 1: Capability Metadata and Error Contracts
Status: Complete

#### Scope
- Finish machine-readable capability metadata per tool/action:
  - `read_only`
  - `mutating`
  - `high_risk`
  - `supports_dry_run`
  - `supports_verification`
  - `requires_unity`
  - `local_only`
  - `runtime_only`
  - `requires_explicit_opt_in`
- Standardize response envelopes and stable error codes.
- Add generated tool catalog output from the live registry.
- Add generated skill/doc artifacts for tools and tool groups.

#### Why First
- This is the control plane for every premium feature that follows.
- It keeps expansion from collapsing back into ad hoc tool growth.

#### Acceptance
- Tool metadata can be queried programmatically.
- Error codes are stable and documented.
- A generated tool catalog and skill/catalog artifacts can be produced from the registry.

#### Implementation Notes
- Completed via centralized action policy coverage, generated catalog/subagent/error artifacts, and synced registry exports.
- Metadata now includes local-only/runtime-only/high-risk/read-only signals for premium tool families.

### Phase 2: Local Code Intelligence
Status: Complete

#### Scope
- Add server-local code tools that do not require a live Unity editor:
  - `search_code`
  - `find_symbol`
  - `find_references`
  - `get_symbols`
  - `build_code_index`
  - `update_code_index`
- Index `Assets/` by default and optionally selected package folders.
- Expose whether a tool is local-only, read-only, indexed, or Unity-dependent.

#### Why First
- Immediate premium value.
- Works even when Unity is closed or compiling.
- Reduces Unity round-trips and improves agent reliability.

#### Acceptance
- Code queries succeed with Unity closed.
- Index build/update is incremental.
- Tool metadata exposes local/read-only capability.

#### Implementation Notes
- Implemented via `manage_code_intelligence` plus helper tools (`search_code`, `find_symbol`, `find_references`, `get_symbols`, `build_code_index`, `code_index_status`).
- Local-only classification now routes through the centralized policy metadata and generated catalog.

### Phase 3: Package and Project Management
Status: Complete

#### Scope
- Add `manage_package_manager` with actions for:
  - list installed packages
  - search packages
  - add package
  - remove package
  - inspect package sources/versions
- Add scoped project settings/package-registry inspection where feasible.
- Start with read/list/search flows, then controlled mutations.

#### Acceptance
- Package list/search/inspect flows work reliably.
- Add/remove operations are gated, classified as mutating, and return normalized results.

#### Implementation Notes
- `manage_package_manager` implemented with read-only and mutating action split.
- Package operations are preflight-gated for mutating actions and covered by targeted tests.

### Phase 4: Addressables
Status: Complete

#### Scope
- Add `manage_addressables` with scoped actions for:
  - analyze
  - build
  - inspect groups
  - assign/remove labels
  - move assets between groups
  - validate configuration
- Prefer read/validate/build flows first, then broader mutation coverage.

#### Acceptance
- Core analyze/build/read flows work end-to-end.
- Wide-scope changes support `dry_run`.
- Failures return stable codes and actionable hints.

#### Implementation Notes
- `manage_addressables` is implemented with explicit read-only/build/mutating action families.
- `dry_run` is surfaced for build-style operations and reflected in capability metadata.

### Phase 5: Input System
Status: Complete

#### Scope
- Add `manage_input_system` for:
  - action maps
  - actions
  - bindings
  - control schemes
  - input asset inspection
- Add optional runtime input simulation where Unity supports it.
- Keep editor-time configuration and runtime simulation clearly separated.

#### Acceptance
- Input assets can be inspected and updated safely.
- Runtime simulation actions are marked as higher-risk/runtime-dependent.

#### Implementation Notes
- `manage_input_system` implemented across action maps/actions/bindings/schemes/assets/simulation/state.
- Runtime-sensitive simulation/state actions are represented in policy and generated metadata.

### Phase 6: Profiler and Diagnostics
Status: Complete

#### Scope
- Add `manage_profiler` for:
  - start
  - stop
  - status
  - snapshot/basic metrics
- Add richer diagnostics aggregation across:
  - console
  - compile state
  - test jobs
  - profiler state
- Normalize long-running operations into explicit job/status patterns where needed.

#### Acceptance
- Profiler status and snapshot calls work reliably.
- Long-running diagnostics expose progress and normalized result payloads.

#### Implementation Notes
- `manage_profiler` and `record_profiler_session` are implemented.
- `get_diagnostics` is available for aggregated operational status.

### Phase 7: Visual QA and Runtime UI Automation
Status: Complete

#### Scope
- Extend capture tooling with video start/status/stop.
- Add runtime UI automation/query tools for:
  - find UI elements
  - inspect state
  - set values
  - click/submit interactions
- Keep UI authoring tools and runtime UI automation as separate tool families.

#### Acceptance
- Agents can capture both screenshots and short video evidence.
- Runtime UI flows can be queried and driven for QA tasks.
- Runtime-only actions are clearly classified and guarded.

#### Implementation Notes
- Implemented via `manage_video_capture` and `manage_runtime_ui`.
- Runtime-only/tool-risk metadata is now generated from centralized policy state.

### Phase 8: Reflection and Object Introspection
Status: Complete

#### Scope
- Add a gated reflection/object-inspection family for:
  - method discovery
  - safe method invocation
  - object data inspection
  - controlled object mutation
- Keep this behind explicit capability flags and per-project opt-in.
- Start with discovery and read-only inspection before invocation/mutation.

#### Safety Requirements
- Reflection features must be disabled by default.
- Invocation and mutation actions must be classified as `high_risk`.
- Runtime execution must require explicit opt-in and clear auditability.

#### Acceptance
- Read-only reflection discovery works without broad mutation exposure.
- Invocation/mutation paths cannot be used unless opt-in is enabled.
- Error responses clearly state why access is blocked when the feature is disabled.

#### Implementation Notes
- Implemented via `manage_reflection` with explicit capability checks and action-level controls.
- High-risk reflection operations are differentiated from read-only discovery paths.

### Phase 9: Runtime/In-Game MCP
Status: Complete

#### Scope
- Design and implement a separate runtime MCP track for play mode / built game support.
- Keep editor MCP and runtime MCP as distinct capability domains.
- Reuse the same policy metadata, error contracts, and opt-in model.

#### Safety Requirements
- Runtime MCP features must be explicitly enabled.
- Runtime-only tools must be clearly tagged and never silently appear in editor-only environments.

#### Acceptance
- Runtime tools are isolated, classifiable, and discoverable.
- The runtime track does not weaken editor-side safety assumptions.

#### Implementation Notes
- Runtime bridge foundations are present (`get_runtime_status`, `list_runtime_tools`, `execute_runtime_command`, `get_runtime_connection_info`).
- Runtime MCP now requires explicit opt-in via server configuration (`runtime_mcp_enabled`).
- Runtime bridge and runtime UI automation tools now fail closed with explicit guidance when runtime MCP is disabled.
- Runtime-only capability metadata is aligned with centralized policy and capability flag registries.
- Runtime gating and routing behavior now has dedicated integration test coverage.

## Cross-Cutting Work

### Capability Metadata
- Add machine-readable capability metadata per tool/action and generate it from one source of truth.
- Use metadata to drive:
  - preflight/policy routing
  - tool listing and filtering
  - generated docs/skills
  - runtime/editor separation
  - high-risk gating

### Error Contracts
- Standardize response envelopes and stable error codes.
- Add one actionable recovery hint for common failures.
- Document contracts in a dedicated `ERROR_CODES.md`.

### Checkpoints and Verification
- Add checkpoint/restore primitives for high-risk multi-step workflows.
- Add post-mutation verification hooks where practical:
  - file hash changed
  - asset exists
  - prefab/scene object exists
  - compile completed successfully

Status: Complete

Implementation Notes:
- Added server-local `manage_checkpoints` with `create`, `list`, `inspect`, `verify`, `restore`, and `delete` actions.
- Checkpoint verification now reports changed/missing/unchanged paths using file-hash comparisons.
- Restore and delete support `dry_run` preview mode for safer rollback workflows.

### Long-Running Job UX
- Normalize long operations into job-based patterns.
- Expose progress/status polling.
- Ensure retries do not duplicate already-started work.

Status: Complete

Implementation Notes:
- Async test jobs (`run_tests` + `get_test_job`) remain the canonical job contract with progress/status payloads.
- Runtime command execution continues to support async behavior (`wait_for_completion=false`) with job-style response handling.

### Tool Catalog Discipline
- Generate a current tool catalog from the live registry.
- Keep capability metadata and docs in sync with actual registration.
- Add generated skill/catalog artifacts for tool families and high-level workflows.

## Recommended Execution Sequence
1. Deepen E2E and resilience tests for premium/runtime families (especially runtime bridge flows). (Complete)
2. Implement checkpoint/restore primitives for high-risk multi-step workflows. (Complete)
3. Expand post-mutation verification hooks and long-running job progress normalization. (Complete)
4. Continue runtime/in-game MCP isolation and safety hardening. (Complete)
5. Enforce generated-artifact sync checks in CI to prevent drift. (Next)

## Non-Goals
- Rewriting the server as a Rust CLI.
- Copying another project's architecture wholesale.
- Adding game-specific workflow assumptions to the server core.

## Notes
- The premium goal should be measured by reliability, workflow compression, and observability, not raw tool count alone.
- New features should prefer additive, capability-driven design over one-off command growth.
- Reflection and runtime access are valuable, but only if they remain policy-driven, auditable, and explicitly enabled.
