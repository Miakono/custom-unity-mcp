# Premium Feature Plan V2

Date: 2026-03-06

Status note: historical planning record.
For the current repo-grounded remediation plan, see `../GAP_CLOSURE_PLAN.md`.
For the latest validated implementation snapshot, see `../HANDOFF_2026-03-06.md`.

## Purpose
- Define the next premium roadmap after the largely completed V1 capability build-out.
- Focus on high-value workflow gaps that improve agent effectiveness inside Unity.
- Prioritize verified gaps against this fork's current MCP surface over speculative parity claims.
- Keep the fork game-agnostic, policy-driven, and MCP-native.
- Make "the agent can do essentially everything a user normally does in the Unity Editor" an explicit product goal.

## Current Baseline
- Live server catalog currently exposes 61 tools.
- The fork already includes advanced premium-style capability families:
  - local code intelligence
  - testing and validation
  - runtime MCP bridge
  - reflection
  - profiler tooling
  - checkpoints
  - subagents
  - video capture
  - package manager
  - addressables
  - input system
  - VFX
- Many read-oriented editor capabilities are intentionally exposed as MCP resources rather than tools.

## Strategic Direction
V2 should not chase raw tool count. It should add features that remove current workflow blind spots:
- missing editor workflows that force an agent to stop or fall back to manual Unity usage
- missing scene/prefab lifecycle control for multi-step tasks
- missing visual verification loops after mutations
- missing reusable workflow primitives above single tool calls
- missing project memory/rules mechanisms that improve repeated task quality

## Editor-Complete Goal
The fork should move toward full practical editor operability. That means an agent should be able to:
- inspect editor state, selection, windows, scenes, prefab stage, tools, and project configuration
- inspect spatial state, transforms, bounds, and object relationships
- change selection, active tools, play mode state, open windows, and common editor context
- manage scenes, prefabs, assets, components, packages, tags, layers, and project settings without handoff
- execute menu items, editor scripts, and reusable editor workflows where safety policy allows
- verify results through structural reads, diagnostics, and visual evidence

This does not require exposing every internal Unity API directly. It does require covering the workflows a human editor user relies on day to day.

## Confirmed High-Value Gaps

### Tier 1: Core Workflow Gaps
- Prefab stage lifecycle:
  - open prefab stage
  - save open prefab stage
  - close prefab stage
- Multi-scene control:
  - list opened scenes
  - set active scene
  - unload additive scene
- Editor selection mutation:
  - set selection
  - optionally frame selection
- Editor window and tool control:
  - list windows as tools where useful
  - open/focus common editor windows
  - close windows where safe
  - query and set active editor tool
- Editor application control:
  - play
  - pause
  - stop
  - optionally quit editor with explicit opt-in
- Script execution:
  - execute C# snippet in editor context
- Project and package configuration:
  - get project settings
  - update project settings
  - inspect and update relevant editor settings/preferences
  - manage scoped registries
- Operational diagnostics:
  - public ping tool
  - command statistics

### Tier 2: Deep Inspection Gaps
- Asset dependency graph analysis
- Asset import settings inspection and mutation
- Built-in asset search
- Shader enumeration
- Global component type discovery
- Object reference graph inspection
- Transform and spatial awareness:
  - world/local transform inspection beyond single-object reads
  - bounds and extents inspection
  - distance/direction/relative offset queries
  - overlap and proximity queries
  - placement/snap/alignment helpers

### Tier 3: Premium Workflow Gaps
- Screenshot analysis and visual verification
- Scene/Game/Prefab visual feedback loops after mutation
- Recorded workflows / pipelines
- Reusable playbooks built on top of existing tools
- Project memory and rule ingestion for persistent agent behavior

## Planning Principles
- New features must route through the centralized policy, capability, and metadata layers.
- Prefer verified editor workflow gaps before speculative AI-generation features.
- Prefer inspect/validate/read before mutate where possible.
- Reuse resources where read-only context is the better interface; do not force everything into tools.
- Long-running and multi-step flows should expose job progress, replayability, and auditability.
- Premium features must be measurable by workflow compression and reliability, not marketing category count.

## Delivery Plan

### Phase 1: Editor Workflow Completion
Status: Planned

#### Scope
- Add `manage_prefab_stage` or extend `manage_prefabs` with stage actions:
  - `open_stage`
  - `save_open_stage`
  - `close_stage`
- Extend scene management with:
  - `list_opened`
  - `set_active`
  - `unload`
- Add editor selection mutation:
  - `set_selection`
  - optional `frame_selection`
- Add window/tool/editor control:
  - open/focus windows
  - close windows
  - get/set active tool
  - surface editor-state actions in a more editor-complete shape
- Add public `ping`
- Add command usage/stats surface

#### Why First
- These are hard blockers in real agent workflows.
- They close parity gaps with other Unity automation surfaces without changing product direction.

#### Acceptance
- Agents can complete prefab-stage editing without manual Unity interaction.
- Agents can manage additive scene workflows end to end.
- Selection can be changed programmatically and reflected in editor resources.
- Common editor windows and active tools can be manipulated without manual intervention.
- Connectivity and command-health checks are available through stable tool contracts.

### Phase 2: Project and Asset Intelligence
Status: Planned

#### Scope
- Add project settings read/update tools.
- Add editor settings/preferences read/update tools where Unity safely exposes them.
- Add scoped registry management.
- Add asset dependency analysis.
- Add asset import settings read/update.
- Add built-in asset search.
- Add shader listing.
- Add global component type discovery and object-reference inspection.

#### Why Second
- These deepen project understanding and unblock higher-quality mutations.
- They support agents that need to reason about import pipelines, package sources, and asset graphs.

#### Acceptance
- Project/package configuration is inspectable and safely mutable.
- Relevant editor configuration is inspectable and safely mutable.
- Asset relationship analysis returns structured, navigable output.
- Agents can discover relevant built-in assets, shaders, and component types without guesswork.

### Phase 3: Transform and Spatial Awareness
Status: Planned

#### Scope
- Add a dedicated transform/spatial tool family rather than burying all logic in `manage_gameobject`.
- Support transform-aware inspection:
  - get world/local transform
  - get renderer/collider/object bounds
  - get parent/child relative offsets
  - compute distance and direction between objects
- Support spatial queries:
  - nearest object
  - objects in radius/box
  - overlap/intersection checks
  - optional raycast/surface queries where practical
- Support placement helpers:
  - snap to grid
  - align objects
  - distribute objects
  - place relative to another object
  - place at scene-view focus or camera-facing position
- Support transform validation:
  - off-grid detection
  - overlap detection
  - zero/invalid scale detection
  - floating/buried placement heuristics

#### Why Third
- True editor autonomy requires spatial reasoning, not only raw transform field mutation.
- This is the missing layer between basic GameObject CRUD and reliable scene construction.

#### Acceptance
- Agents can reason about where objects are, how large they are, and how they relate spatially.
- Agents can place, snap, align, and validate scene objects without blind trial and error.
- Spatial operations return structured values that can be reused in later tool calls.

### Phase 4: Visual Verification
Status: Planned

#### Scope
- Add screenshot analysis tooling on top of existing capture capabilities.
- Add a post-action visual verification loop for scene/UI/prefab workflows.
- Support scene view and game view visual evidence capture for self-correction.
- Normalize "capture then analyze" as a first-class workflow pattern.

#### Why Third
- Premium value comes from agents verifying what they changed, not only issuing mutations.
- The fork already has screenshot/video primitives; this phase turns them into feedback loops.

#### Acceptance
- Agents can request visual evidence after scene/UI changes and receive structured analysis.
- Visual verification can be used in regression, QA, and self-correction flows.

### Phase 5: Pipelines and Playbooks
Status: Planned

#### Scope
- Add action recording primitives:
  - start recording
  - stop recording
  - inspect recording
- Add reusable workflow storage:
  - save pipeline
  - list pipelines
  - replay pipeline
- Add higher-level playbooks:
  - list playbooks
  - run playbook
  - create playbook from pipeline or declarative steps

#### Why Fourth
- This compounds the value of the existing tool surface instead of only adding more endpoints.
- Reuse and replay are strong premium differentiators once core workflows are complete.

#### Acceptance
- A multi-step editor workflow can be recorded, named, saved, and replayed.
- Playbooks can orchestrate existing tools safely with clear audit trails.

### Phase 6: Project Memory and Rules
Status: Planned

#### Scope
- Add project-scoped memory/rules ingestion:
  - load project rules
  - summarize working conventions
  - expose active rule set to clients/tools
- Support durable workflow hints without hardcoding game-specific logic into the server.
- Optionally add rule-backed validation checks for common policy violations.

#### Why Fifth
- This improves repeated task quality across sessions without polluting core tool contracts.

#### Acceptance
- Project conventions can be stored and surfaced in a structured, inspectable way.
- Agents can retrieve the current rule/memory set before taking action.

## Candidate Tool Surface

### Confirmed Near-Term Additions
- `manage_prefab_stage`
- `manage_selection`
- `manage_windows`
- `ping`
- `get_command_stats`
- `manage_project_settings`
- `manage_editor_settings`
- `manage_registry_config`
- `analyze_asset_dependencies`
- `manage_asset_import_settings`
- `list_shaders`
- `find_builtin_assets`
- `get_component_types`
- `get_object_references`
- `manage_transform`
- `spatial_queries`
- `analyze_screenshot`

### Likely Workflow Additions
- `record_pipeline`
- `stop_pipeline_recording`
- `replay_pipeline`
- `save_pipeline`
- `list_pipelines`
- `list_playbooks`
- `run_playbook`
- `create_playbook`
- `manage_project_memory`

## Implementation Notes
- Prefer extending existing grouped tools when the action family is coherent.
- Prefer new dedicated tools when the concept is a new capability domain:
  - project settings
  - registry config
  - screenshot analysis
  - pipelines
  - project memory
- Continue generating capability metadata and catalog artifacts from the live registry.
- Add integration tests before broadening surface area for visual verification and replay systems.

## Non-Goals for V2
- Do not prioritize 3D model generation first.
- Do not prioritize sprite generation first.
- Do not prioritize audio generation first.
- Do not add provider-specific generative features until editor workflow gaps are closed.
- Do not optimize for matching another product's claimed tool count.

## Recommended Execution Sequence
1. Complete editor workflow gaps: prefab stage, scene lifecycle, selection, windows/tools, ping, stats.
2. Add project/package/asset intelligence: project settings, editor settings, registries, dependencies, import settings.
3. Add transform and spatial awareness primitives for reliable scene reasoning and placement.
4. Add visual verification on top of existing screenshot/video primitives.
5. Add pipeline recording and replay.
6. Add playbooks and project memory.

## Success Metrics
- Fewer tasks require manual Unity editor intervention.
- Agents can complete normal editor workflows without a human taking over for window, selection, or settings operations.
- Agents can place and adjust objects using spatial reasoning instead of blind coordinate edits.
- Agents can verify mutations visually and structurally before continuing.
- Multi-step workflows become reusable and replayable.
- Project-specific context improves repeated-task quality without custom server forks.
- Premium value is reflected in task completion rate, latency reduction, and lower retry count.
