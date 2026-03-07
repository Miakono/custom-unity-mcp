# Unity MCP Subagents

Generated specialist and orchestrator definitions derived from the live MCP tool registry.

Default enabled groups: core
Total subagents: 8

Available subagents:
- `unity-orchestrator`: Routes work to the right Unity specialist, keeps tool groups lean, and coordinates verification after mutations.
- `unity-animation-specialist`: Focuses on animator, clips, and animation editing tasks.
- `unity-core-specialist`: Owns everyday Unity editing work: scenes, gameobjects, prefabs, assets, scripts, and editor state.
- `unity-input-specialist`: Unity Input System - Action Maps, Actions, Bindings, and Runtime Simulation
- `unity-scripting-ext-specialist`: Handles ScriptableObject and data-oriented authoring flows.
- `unity-testing-specialist`: Runs validation loops, test jobs, and post-change verification.
- `unity-ui-specialist`: Owns UI Toolkit and interface authoring tasks.
- `unity-vfx-specialist`: Handles shaders, materials, textures, and VFX authoring flows.

Primary catalog file: `subagents.json`
