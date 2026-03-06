# Premium Feature Plan

Date: 2026-03-05

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
The highest-value missing categories relative to more premium toolsets are:
- local code intelligence
- addressables
- input system
- profiler/performance diagnostics
- video capture
- runtime UI automation
- package/project settings management
- package manager tooling
- generated skill/catalog artifacts from the live registry
- gated reflection/object introspection
- runtime/in-game MCP as a separate longer-term track

## Planning Principles
- New feature families must route through the same policy/capability layer as existing tools.
- Add breadth, but separate low-risk editor workflows from high-risk runtime/reflection workflows.
- Prefer feature flags and explicit opt-in for anything that can invoke arbitrary methods or mutate live runtime state.
- Ship read/inspect/validate flows before broad mutation where practical.
- Generate documentation and capability metadata from the live registry instead of hand-maintaining parallel catalogs.

## Delivery Order

### Phase 1: Capability Metadata and Error Contracts
Status: Planned

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

### Phase 2: Local Code Intelligence
Status: Planned

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

### Phase 3: Package and Project Management
Status: Planned

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

### Phase 4: Addressables
Status: Planned

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

### Phase 5: Input System
Status: Planned

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

### Phase 6: Profiler and Diagnostics
Status: Planned

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

### Phase 7: Visual QA and Runtime UI Automation
Status: Planned

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

### Phase 8: Reflection and Object Introspection
Status: Planned

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

### Phase 9: Runtime/In-Game MCP
Status: Planned

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

### Long-Running Job UX
- Normalize long operations into job-based patterns.
- Expose progress/status polling.
- Ensure retries do not duplicate already-started work.

### Tool Catalog Discipline
- Generate a current tool catalog from the live registry.
- Keep capability metadata and docs in sync with actual registration.
- Add generated skill/catalog artifacts for tool families and high-level workflows.

## Recommended Execution Sequence
1. Finish capability metadata, generated catalog/skills, and response/error contracts.
2. Implement local code intelligence.
3. Implement package manager and project/package inspection.
4. Implement addressables.
5. Implement input system.
6. Implement profiler/diagnostics.
7. Implement visual QA and runtime UI automation.
8. Design and then implement gated reflection/object introspection.
9. Design and then implement runtime/in-game MCP.

## Non-Goals
- Rewriting the server as a Rust CLI.
- Copying another project's architecture wholesale.
- Adding game-specific workflow assumptions to the server core.

## Notes
- The premium goal should be measured by reliability, workflow compression, and observability, not raw tool count alone.
- New features should prefer additive, capability-driven design over one-off command growth.
- Reflection and runtime access are valuable, but only if they remain policy-driven, auditable, and explicitly enabled.
