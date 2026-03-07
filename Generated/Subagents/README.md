# Unity MCP Subagents

Generated specialist and orchestrator definitions derived from the live MCP tool registry.

Default enabled groups: animation, asset_intelligence, core, dev_tools, diff_patch, events, input, navigation, pipeline, pipeline_control, profiling, project_config, scripting_ext, spatial, testing, transactions, ui, vfx, visual_qa
Total subagents: 20

Available subagents:
- `unity-orchestrator`: Routes work to the right Unity specialist, keeps tool groups lean, and coordinates verification after mutations.
- `unity-animation-specialist`: Focuses on animator, clips, and animation editing tasks.
- `unity-asset-intelligence-specialist`: Advanced asset search, indexing, and analysis
- `unity-core-specialist`: Owns everyday Unity editing work: scenes, gameobjects, prefabs, assets, scripts, and editor state.
- `unity-dev-tools-specialist`: Internal development and debugging tools
- `unity-diff-patch-specialist`: Scene and prefab diff/patch operations
- `unity-events-specialist`: Editor event subscription and condition waiting
- `unity-input-specialist`: Unity Input System - Action Maps, Actions, Bindings, and Runtime Simulation
- `unity-navigation-specialist`: Editor navigation and focus tools
- `unity-pipeline-specialist`: Pipeline recording, replay, and playbook automation tools
- `unity-pipeline-control-specialist`: Build settings, player settings, and import pipeline control
- `unity-profiling-specialist`: Unity Profiler capture, analysis, and performance diagnostics
- `unity-project-config-specialist`: Project and Asset Intelligence – settings, registries, dependencies, built-in assets
- `unity-scripting-ext-specialist`: Handles ScriptableObject and data-oriented authoring flows.
- `unity-spatial-specialist`: Transform operations and spatial queries – advanced scene construction
- `unity-testing-specialist`: Runs validation loops, test jobs, and post-change verification.
- `unity-transactions-specialist`: Transaction management with rollback and preview capabilities
- `unity-ui-specialist`: Owns UI Toolkit and interface authoring tasks.
- `unity-vfx-specialist`: Handles shaders, materials, textures, and VFX authoring flows.
- `unity-visual-qa-specialist`: Visual verification and screenshot analysis – AI-powered image validation

Primary catalog file: `subagents.json`
