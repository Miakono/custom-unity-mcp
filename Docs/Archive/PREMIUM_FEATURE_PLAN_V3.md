# Premium Feature Plan V3

Date: 2026-03-06

Status note: historical planning record.
For the current repo-grounded remediation plan, see `../GAP_CLOSURE_PLAN.md`.
For the latest validated implementation snapshot, see `../HANDOFF_2026-03-06.md`.

## Purpose
- Define the premium roadmap after V2 without interfering with the active V2 implementation stream.
- Focus on the infrastructure that makes a Unity editor agent feel native, reliable, and reversible.
- Build on V1 and V2 rather than reopening already planned capability gaps.

## Relationship to Prior Plans
- V1 established policy, capability metadata, runtime separation, and premium foundations.
- V2 focuses on editor-complete workflows, spatial reasoning, visual verification, and reusable workflows.
- V3 focuses on the systems that make those workflows dependable at scale:
  - reversibility
  - synchronization
  - structured diffs
  - richer asset intelligence
  - editor navigation
  - pipeline control

## Strategic Goal
By the end of V3, the agent should not only be able to perform editor workflows, but do so with:
- transaction safety
- precise waiting and event awareness
- structured before/after visibility
- richer project-wide discovery outside code
- fast editor-native navigation and context switching

V3 should also improve the speed and safety of developing the MCP itself:
- faster iteration without always requiring a live Unity editor
- stronger contract validation across server/plugin/generated artifacts
- better visibility into failures, retries, and latency
- easier reproduction of Unity-side edge cases

## Core Themes

### 1. Reversible Editing
The agent should be able to stage, group, review, apply, and roll back editor operations with minimal ambiguity.

### 2. Event-Aware Execution
The agent should react to editor state transitions instead of relying on guesswork or fixed delays.

### 3. Structural Diffs and Patches
The agent should be able to reason in terms of scene/prefab/asset deltas, not only imperative mutations.

### 4. Whole-Project Asset Intelligence
The agent should understand project assets with the same depth it already has for code.

### 5. Editor-Native Context Control
The agent should navigate the editor the way a human does: focus, reveal, ping, frame, inspect, open, and trace.

### 6. Development Acceleration
The codebase should become easier to extend, test, benchmark, and debug as the tool surface grows.

## Delivery Plan

### Phase 1: Undo, Transactions, and Change Sets
Status: Planned

#### Scope
- Add transaction primitives for multi-step editor workflows:
  - begin transaction
  - append actions
  - preview transaction
  - commit transaction
  - rollback transaction
- Add editor-native undo integration where Unity APIs allow it.
- Normalize change-set summaries:
  - created
  - modified
  - deleted
  - moved
  - failed
- Connect transaction output to existing checkpoint support without replacing checkpoints.

#### Why First
- V2 makes the agent more powerful.
- V3 needs a safer model for broad editor autonomy.

#### Acceptance
- Multi-step workflows can be grouped into a named transaction.
- Transactions can be previewed before commit.
- Rollback paths are available for supported mutation types.
- Result payloads include a structured change summary.

### Phase 2: Waiters and Event Subscriptions
Status: Planned

#### Scope
- Add wait primitives:
  - wait for compile idle
  - wait for asset import complete
  - wait for scene load complete
  - wait for play mode state
  - wait for prefab stage state
  - wait for object/asset existence
- Add event/subscription surfaces where practical:
  - console updates
  - compile state changes
  - play mode transitions
  - hierarchy changes
  - test job progress
  - runtime bridge status

#### Why Second
- Agents become much more reliable when they can synchronize explicitly.
- This reduces retry loops, sleep-based behavior, and flaky sequencing.

#### Acceptance
- Long workflows can wait on explicit editor conditions instead of fixed delays.
- Event-driven flows can surface meaningful state changes for clients that support them.

### Phase 3: Scene, Prefab, and Asset Diff/Patch
Status: Planned

#### Scope
- Add structured diff tools for:
  - active scene
  - open scenes
  - prefab asset
  - selected GameObjects
  - selected assets
- Add structured patch application for supported surfaces:
  - hierarchy changes
  - transform changes
  - component property changes
  - prefab content changes
- Add approval-friendly summaries:
  - human-readable overview
  - machine-readable patch payload

#### Why Third
- This enables reviewable, replayable, and safer automation.
- It complements V2 pipelines and playbooks.

#### Acceptance
- The agent can produce a structured diff before mutating a scene or prefab.
- Approved patches can be applied deterministically.
- Diff outputs can be reused in review and dry-run flows.

### Phase 4: Asset Intelligence Beyond Code
Status: Planned

#### Scope
- Add structured search/indexing for non-code assets:
  - scenes
  - prefabs
  - materials
  - shaders
  - textures
  - audio clips
  - scriptable objects
  - animation clips/controllers
- Add asset metadata extraction:
  - dependencies
  - labels
  - import settings
  - references
  - usage sites
  - key serialized fields
- Add project inventory summaries and filtered queries.

#### Why Fourth
- Code intelligence is already strong.
- Premium autonomy needs equivalent project-asset intelligence.

#### Acceptance
- Agents can answer project questions without guessing or brute-force traversal.
- Asset search returns structured metadata suitable for later tool calls.

### Phase 5: Editor Navigation and Context Actions
Status: Planned

#### Scope
- Add navigation actions:
  - reveal asset in project
  - ping object/asset
  - focus hierarchy selection
  - frame scene view target
  - open inspector target
  - open script at symbol
  - open asset at path
- Add context helpers:
  - current inspector target
  - current scene view camera pose
  - current project browser focus
  - current active editor context

#### Why Fifth
- These are small but high-leverage features that make the agent feel editor-native.

#### Acceptance
- The agent can direct user attention and its own workflow through editor navigation primitives.
- Navigation outputs are structured and composable with V2/V3 workflows.

### Phase 6: Import, Build, and Platform Pipeline Control
Status: Planned

#### Scope
- Add project pipeline tools for:
  - build settings inspection/update
  - player settings inspection/update
  - scripting define symbols
  - target platform switching
  - import queue/status inspection
  - forced reimport/reserialize flows
  - content/build pipeline state checks
- Keep destructive or wide-scope operations behind explicit high-risk policy gates.

#### Why Sixth
- Premium editor autonomy eventually reaches beyond content edits into build and pipeline control.

#### Acceptance
- Common project pipeline tasks can be inspected and automated safely.
- Wide-scope operations are clearly classified, gated, and auditable.

### Phase 7: Development Acceleration and Tooling
Status: Planned

#### Scope
- Add a Unity mock/simulator harness for server development without a live editor.
- Add fixture capture and replay for real Unity responses.
- Add contract/golden tests for tools, resources, and generated artifacts.
- Add trace/debug tooling for MCP request flow:
  - normalized params
  - selected Unity instance
  - retries
  - latency
  - response envelope
- Add failure injection scenarios:
  - compile in progress
  - domain reload
  - dropped transport
  - stale editor state
  - locked/missing asset
- Add a one-command developer validation flow:
  - regenerate artifacts
  - run contract tests
  - run key integration suites
  - check docs/catalog sync
- Add benchmark coverage for high-traffic workflows.

#### Why Seventh
- The premium surface is already large.
- Without better internal tooling, feature velocity and reliability will degrade as V2/V3 land.

#### Acceptance
- Core server behavior can be tested locally without always launching Unity.
- Real Unity edge cases can be replayed from captured fixtures.
- Contract drift between tool registry, docs, generated artifacts, and plugin behavior is caught automatically.
- Developers can inspect an end-to-end tool trace when debugging failures.
- Performance regressions on key workflows are measurable over time.

## Candidate Tool Surface

### Transaction and Reversal
- `manage_transactions`
- `preview_changes`
- `rollback_changes`

### Waiting and Events
- `wait_for_editor_condition`
- `subscribe_editor_events`
- `unsubscribe_editor_events`

### Diff/Patch
- `diff_scene`
- `diff_prefab`
- `diff_asset`
- `apply_scene_patch`
- `apply_prefab_patch`

### Asset Intelligence
- `search_assets_advanced`
- `build_asset_index`
- `asset_index_status`
- `find_asset_references`
- `summarize_asset`

### Navigation
- `navigate_editor`
- `reveal_asset`
- `focus_hierarchy`
- `frame_scene_target`
- `open_inspector_target`

### Pipeline Control
- `manage_build_settings`
- `manage_player_settings`
- `manage_define_symbols`
- `manage_import_pipeline`

### Development Tooling
- `dev_trace_tools`
- `replay_unity_fixture`
- `capture_unity_fixture`
- `benchmark_tool_surface`

## Design Principles
- Prefer structured state and diffs over opaque textual summaries.
- Prefer explicit waiting and eventing over hidden sleeps/retries.
- Treat transactionality as a first-class safety layer, not an afterthought.
- Keep patch formats deterministic and suitable for review.
- Keep broad pipeline and platform operations clearly separated from ordinary safe editor actions.
- Treat development tooling as part of product reliability, not optional internal cleanup.

## Non-Goals for V3
- Do not chase generative media features first.
- Do not depend on cloud-only services for core editor autonomy.
- Do not introduce a second policy system outside the existing action/capability layer.
- Do not replace checkpoints; complement them with transactions and diffs.

## Recommended Execution Sequence
1. Add transactions and structured change summaries.
2. Add waiters and event subscriptions.
3. Add scene/prefab/asset diff-patch workflows.
4. Add asset intelligence beyond code.
5. Add editor navigation/context actions.
6. Add import/build/platform pipeline control.
7. Add development acceleration tooling: mocks, replay, traces, contracts, benchmarks.

## Success Metrics
- Fewer destructive workflows require manual babysitting.
- Long-running workflows fail less often because they wait on real conditions.
- Users can review and approve structured changes before broad mutations.
- Asset/project discovery becomes as strong as code discovery.
- The agent behaves more like a native editor operator than a remote command caller.
- Development iteration time drops because more behavior can be tested and debugged without a full live-editor loop.
