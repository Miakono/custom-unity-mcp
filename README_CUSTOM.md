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
