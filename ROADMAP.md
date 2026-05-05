# Unity MCP Fork Roadmap (Bezi-Inspired, Game-Agnostic)

Date: 2026-05-02

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

## v0.2 UX, Action Model, and Performance Foundation
Status: Complete (shipped 2026-05-02)

### Scope
- Add an explicit action capability schema for each tool (read-only vs mutating metadata).
- Extend capability metadata to cover high-risk, local-only, runtime-only, dry-run, verification, and opt-in requirements.
- Improve error payloads for action mismatch and invalid parameter shapes.
- Add a consistent "what to do next" hint in common failure responses.
- Generate tool catalog / skill artifacts from the live registry.
- Performance pass: hot-path optimizations in command dispatch and editor-side caches.
- Make the profiler tool surface actually return real data (was returning zeros for CPU/GPU/render).
- Make the multi-agent system fully usable (orchestrator + specialists with rich routing metadata).
- Optional integration with Singularity Group Hot Reload to skip full domain reload on script edits.

### Delivered (2026-05-02 — v0.2.0 release)
- **Action capability metadata** now covers core and premium tool families:
  - mutating vs read-only action classification for mixed tools, high-risk / local-only / runtime-only flags, dry-run support metadata.
- **Generated artifacts** synced from the live registry and policy layer (`Generated/Catalog/tool_catalog.json`, `Generated/Subagents/subagents.json`, `Generated/ErrorCatalog/error_catalog.json`).
- **Performance — Editor (C#)**:
  - `CommandRegistry` now uses `TypeCache.GetTypesWithAttribute<T>()` instead of scanning every loaded assembly on each domain reload (multi-second cold-load improvement).
  - `CommandRegistry` async dispatch caches a bound `Func<JObject, Task>` delegate at registration time — eliminates per-call `MethodInfo.Invoke` and `GetProperty("Result")` reflection.
  - `EnumerateShaderNames()` caches the sorted shader name list, invalidated on `EditorApplication.projectChanged` and assembly reload (was the dominant cost of every `list_shaders` call).
  - `AssetDatabase.Refresh()` audit: 10 sites converted to `AssetDatabase.ImportAsset(path)` for single-file edits in `InputActionManager`, `ManagePrefabs`, `VfxGraphAssets` — input-system YAML edits no longer trigger full project import.
- **Performance — Server (Python)**:
  - C# code indexer (`code_indexer.py`) parallelized with `ThreadPoolExecutor` (capped at min(8, cpu_count)) for both `build_index` and `update_index` paths.
- **Profiler tool surface — fully fixed**:
  - New `ProfilerRecorderPool.cs` holds long-lived `ProfilerRecorder` instances. The previous code created/disposed recorders inside `using` blocks per call, which always returned 0 because Unity needs at least one frame to elapse before any sample is captured.
  - `ProfilerSnapshot.cs` rewritten to read from the pool with correct Unity 6 counter names (`Total Used Memory`, `GC Allocated In Frame`, `Game Object Count`, `Texture Memory`, etc.).
  - `ProfilerDataCollector.cs` switched from `Time.frameCount` (which doesn't tick in Edit mode) to `EditorApplication.timeSinceStartup` — `record_profiler_session` now actually accumulates snapshots.
  - `manage_profiler.py` field-name mismatch fixed (Python read `avgMemoryMB`, C# emitted `avgMemoryBytes`).
- **Hot Reload integration** (optional, project-agnostic):
  - New `HotReloadIntegration.cs` helper detects Singularity Group Hot Reload via reflection (no hard dependency).
  - `ManageScript` `ApplyTextEdits` / `RefreshDebounce` / `ImportAndRequestCompile` skip `AssetDatabase.ImportAsset` + `RequestScriptCompilation` when Hot Reload's server is running and the edit is patchable. `CreateScript` opts out of the defer because new types can't be patched.
- **Code-quality fixes**:
  - `ValidateScriptSyntaxUnity` false positives removed: dropped 7 substring co-occurrence checks (e.g. `"FindObjectOfType" + "Update()"`) that fired on every file containing both keywords anywhere. Kept the 4 checks that detect real bugs (missing `using UnityEngine`, parameterized `Start()`/`Update()`).
- **Multi-agent system**:
  - MCP server `instructions` block now includes a Performance Profiling section that documents when to use `get_snapshot` vs `record_profiler_session` vs `run_benchmark`, plus thresholds and known limits.
  - All 19 specialists in `_GROUP_SPECIALISTS` now have populated `when_to_use`, `workflow`, and `handoff_targets`. Orchestrator can route reliably.
  - Orchestrator `instructions` updated to mention profiling routing explicitly.
  - User-level Claude Code skill `unity-profiling` documents the workflow for any Unity project.
- **Error message hygiene**:
  - "Miakono Unity MCP" instance-not-found error now also lists the connected instance and suggests `set_active_instance` before failing outright.
  - `manage_reflection get_capability_status` `availableOperations` now reflects the actual gating state instead of listing operations that error when called.

### Skipped from v0.2 (deferred)
- `start_trace` / `get_command_stats` — reported in audit but instrumentation is non-blocking. Tracked in v0.3.

### Acceptance
- Tool metadata can be programmatically queried for mutability and risk.
- Profiler `manage_profiler get_snapshot` returns non-zero CPU/GPU/render data after one frame elapses in Play mode.
- `manage_subagents list` returns no specialist with empty `when_to_use` / `workflow` / `handoff_targets`.
- `dotnet build MCPForUnity.Editor.csproj` and `pytest Server/tests/` pass cleanly.

## v0.3 Agentic Workflows, Checkpoints, and Self-Introspection
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
1. Fix `start_trace` (returns 0 entries) and `get_command_stats` (currently a stub returning telemetry config) — both are observability tools and should self-instrument cleanly.
2. Start checkpoint/restore primitives and deterministic dry-run validation output from v0.3.
3. Split `MCPForUnity/Editor/Tools/LiveV2V3Tools.cs` (~3,600-line god file) into per-tool files matching the existing `Addressables/`, `Prefabs/`, `InputSystem/` layout. Pure mechanical refactor; defer until painful.
4. MCP SDK upgrade from 1.16 to 1.25+ to access structured content + elicitation features. Risky — schedule with a dedicated test pass.
5. Add a release checklist step that regenerates and verifies all `Generated/*` artifacts in CI.
6. Keep roadmap/plan status updates in lockstep with implementation merges.
