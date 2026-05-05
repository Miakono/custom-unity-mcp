# Custom Game Dev Unity MCP

This project is derived from CoplayDev/unity-mcp (MIT License).

Package coordinates:

- Unity package name: `com.customgamedev.unity-mcp`
- Git source: `https://github.com/Miakono/custom-unity-mcp.git?path=/MCPForUnity#main`

Upstream source:

- [Miakono/custom-unity-mcp](https://github.com/Miakono/custom-unity-mcp) (forked from [CoplayDev/unity-mcp](https://github.com/CoplayDev/unity-mcp))

Included upstream files:

- `MCPForUnity/`
- `Server/`
- `LICENSE`
- `UPSTREAM_README.md`

Initial customization targets:

1. Add project-specific workflow tools for your game.
2. Add stronger validation/reporting tools (compile, scene checks, prefab integrity).
3. Add progress/log notifications for long-running tasks.
4. Add registry-backed subagent artifacts so MCP clients can route work through Unity specialists.

Recent fork additions:

- Server-generated subagent catalog and export tool.
- Server-generated live tool catalog with action-level capability contracts and parameter metadata.
- Server-generated error catalog with stable codes and operational response patterns.
- Git-based Unity package installer script for `?path=/MCPForUnity` installs.
- Unity plugin workflow catalog with a dedicated `Workflows` tab.
- Unity plugin validation profile catalog exposed as a resource for audit/readiness discovery.
- Read-only Unity audits for scene integrity and prefab integrity.
- Initial `Docs/ERROR_CODES.md` for current machine-readable server edit errors.
- Cold-start-safe artifact export for tool catalogs and subagent bundles outside normal server startup.
- Historical premium roadmap follow-up documents moved under `Docs/Archive/`:
  - `Docs/Archive/PREMIUM_FEATURE_PLAN_V2.md`
  - `Docs/Archive/PREMIUM_FEATURE_PLAN_V3.md`

Latest stability and VFX updates (2026-03-06):

- VFX Graph path now compiles automatically when package is installed.
  `MCPForUnity.Editor.asmdef` includes VFX Graph references and `UNITY_VFX_GRAPH` version define.
- VFX asset creation gate now supports newer package versions (minimum-based check instead of `12.1.x` lock).
- VFX Graph parameter setters now use `Has*` guards to return clean MCP errors for missing parameter names.
- `vfx_get_info` now includes best-effort exposed parameter metadata for schema-guided setter calls.
- Server test coverage expanded for schema-dependent VFX actions.
  `vfx_set_float`, `vfx_set_int`, `vfx_set_vector4`, `vfx_set_gradient`, `vfx_set_mesh`.
- Added opt-in integration matrix test.
  `Server/tests/integration/test_manage_vfx_live_setter_matrix.py`.
- Added live VFX preset script and guide.
  `Scripts/Create-MageFireballVfx.ps1` and `Docs/MAGE_FIREBALL_VFX.md`.

Latest live bridge updates (2026-03-06):

- Added and validated a Unity-side V2/V3 bridge in `MCPForUnity/Editor/Tools/LiveV2V3Tools.cs` so catalog-visible commands are actually executable in a connected editor.
- Restored live execution for editor/project/config workflows including:
  `manage_project_settings`,
  `manage_editor_settings`,
  `manage_player_settings`,
  `manage_build_settings`,
  `manage_define_symbols`,
  `manage_asset_import_settings`,
  `manage_import_pipeline`,
  `manage_registry_config`,
  `navigate_editor`,
  `reveal_asset`,
  `focus_hierarchy`,
  `frame_scene_target`,
  `open_inspector_target`,
  `search_assets_advanced`,
  `wait_for_editor_condition`,
  `start_trace`,
  `subscribe_editor_events`,
  `manage_transactions`,
  `run_playbook`,
  and `run_benchmark`.
- Fixed the main registration blocker: Unity was reporting unsupported commands because the bridge file was not compiling, not because the Python catalog was missing entries.
- Normalized snake_case/camelCase payload handling for `run_playbook` and `run_benchmark` so the higher-level server contract matches Unity live behavior.
- Optimized `search_assets_advanced` to make broad whole-project searches viable without forcing metadata-heavy per-asset work.
- Added reusable live smoke validation entry points:
  `Server/tests/integration/test_live_unity_smoke_runner.py`,
  `Scripts/Run-LiveUnitySmoke.ps1`,
  and `Scripts/Run-ValidationSuite.ps1`.
- See `Docs/LIVE_TEST_MATRIX.md` for the current live verification list and `Docs/HANDOFF_2026-03-06.md` for the implementation summary.

Latest visual QA updates (2026-03-07):

- `manage_screenshot` now exposes and routes `capture_editor_window` and `get_last_screenshot` alongside the existing game/scene/object capture actions.
- `analyze_screenshot` now supports deterministic `compare_screenshots` pixel-diff checks for capture regression testing.
- Local HTTP `/api/command` on Windows now intercepts `capture_editor_window` and captures the Unity editor client area server-side via `Server/src/utils/windows_unity_editor_capture.py`.
- The server-side editor capture path returns the backend marker `server_hwnd_client_bbox` so live validation can prove which implementation handled a capture.
- Screenshot smoke coverage was added to `Server/tests/integration/test_live_unity_smoke_runner.py` as an opt-in extension of the live Unity matrix.
- Operational limitation: whole-editor capture is currently intended for local Windows HTTP sessions and depends on a visible/restorable Unity window; minimized-window capture remains OS-constrained.

Latest package stability updates (2026-03-07):

- Addressables package dependency was added to the Unity package manifest and package version was bumped to `0.1.1`.
- Addressables tooling was moved behind explicit opt-in compile gating to avoid consumer-project compile breaks from Addressables API drift.
  - Required scripting define to compile Addressables tools: `MCP_ENABLE_ADDRESSABLES_TOOLS`
  - Without that define, the Addressables tool assembly is intentionally skipped.
- Addressables build-script invocation in `AddressableBuildManager` now uses a version-safe reflective path instead of a hard dependency on `AddressableDataBuilderInput`.
- Known operational noise: `com.singularitygroup.hotreload` may emit invalid-path delete warnings for temporary package files such as `Packages/manifest.json.<number>` and `Packages/packages-lock.json.<number>` during package churn.
  - This noise is separate from MCP package compile health.

Latest MCP server responsiveness updates (2026-03-10):

- Local code-intelligence MCP tools now offload index building and code search work to background threads instead of running large filesystem scans directly on the async MCP event loop.
- This fixes a server responsiveness failure mode where `search_code` against a large Unity project could stall concurrent MCP HTTP and plugin-hub traffic long enough to look like a broken transport session.
- Code-index managers now normalize project-root paths before caching so repeated requests using equivalent path variants reuse the same cache entry.
- Code-index cache writes are now atomic, reducing the chance of leaving a half-written JSON index behind if the server is interrupted during rebuild.
- Invalid `project_root` values now fail immediately with a clear server-side error instead of falling through into a slow or misleading index attempt.
- Validation added:
  - `Server/tests/integration/test_premium_tool_surfaces.py -k code_intelligence`
  - `Server/tests/test_code_indexer.py`

Performance, profiler, and multi-agent updates (2026-05-02 — v0.2.0):

- **Editor command dispatch perf**: `CommandRegistry` switched from per-domain-reload `AppDomain.GetAssemblies()` scans to Unity's indexed `TypeCache.GetTypesWithAttribute<T>()` (multi-second cold-load improvement). Async dispatch caches a bound `Func<JObject, Task>` delegate at registration time, eliminating per-call `MethodInfo.Invoke` and `GetProperty("Result")` reflection.
- **Shader name cache**: `EnumerateShaderNames` (the dominant cost of every `list_shaders` call) now caches the sorted list, invalidated on `EditorApplication.projectChanged` and assembly reload.
- **`AssetDatabase.Refresh()` audit**: 10 unconditional `Refresh()` sites across `InputActionManager` (5), `ManagePrefabs` (4), `VfxGraphAssets` (1) converted to `AssetDatabase.ImportAsset(path)`. Input-system YAML edits no longer trigger full project import.
- **Code indexer parallelization**: `code_indexer.py` `build_index` and `update_index` now use a `ThreadPoolExecutor` (capped at min(8, cpu_count)) for the per-file parse/diff worker. I/O dominates and releases the GIL, so threads give a real speedup.
- **Profiler tool surface — fully fixed**:
  - New `ProfilerRecorderPool.cs` holds long-lived `ProfilerRecorder` instances. The previous code created/disposed recorders in `using` blocks and read `LastValue` immediately, which always returned 0 because Unity needs at least one frame to elapse before any sample is captured.
  - `ProfilerSnapshot.cs` rewritten to read from the pool with correct Unity 6 counter names (`Total Used Memory`, `GC Allocated In Frame`, `Game Object Count`, `Texture Memory`, etc.).
  - `ProfilerDataCollector.cs` now uses `EditorApplication.timeSinceStartup` instead of `Time.frameCount` (which doesn't tick in Edit mode) — `record_profiler_session` actually accumulates snapshots now.
  - `manage_profiler.py` field-name mismatch fixed (Python read `avgMemoryMB`, C# emitted `avgMemoryBytes`).
- **Hot Reload (Singularity Group) integration** — optional, project-agnostic:
  - New `HotReloadIntegration.cs` helper detects Hot Reload via reflection (no hard dependency on the package).
  - `ManageScript` `ApplyTextEdits`, `RefreshDebounce`, and `ImportAndRequestCompile` skip `AssetDatabase.ImportAsset` + `RequestScriptCompilation` when Hot Reload's server is running and the edit is patchable.
  - `CreateScript` opts out of the defer (new types aren't patchable).
- **Multi-agent system fully documented**:
  - All 19 specialists in `_GROUP_SPECIALISTS` now have populated `when_to_use`, `workflow`, and `handoff_targets`. Orchestrator routing works reliably for every group, not just the original 6.
  - Orchestrator `instructions` updated to mention profiling routing explicitly.
  - MCP server `instructions` block now includes a Performance Profiling section with thresholds and known limits.
  - User-level Claude Code skill `unity-profiling` documents the workflow for any Unity project.
- **Code quality**:
  - `ValidateScriptSyntaxUnity` false positives removed: dropped 7 substring co-occurrence checks (e.g. `"FindObjectOfType" + "Update()"`) that fired on any file containing both keywords anywhere. Kept the 4 checks that detect real bugs (missing `using UnityEngine`, parameterized `Start()`/`Update()`).
- **Error message hygiene**:
  - "No Unity Editor instances found" error now lists the connected instance and recommends `set_active_instance` before failing outright.
  - `manage_reflection get_capability_status` `availableOperations` now reflects actual gating instead of advertising operations that error when called.
- Validation: `dotnet build MCPForUnity.Editor.csproj` clean, `pytest Server/tests/test_code_indexer.py Server/tests/test_subagents.py` pass.
