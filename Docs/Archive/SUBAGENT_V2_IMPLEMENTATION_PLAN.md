# Subagent-Driven V2 Implementation Plan

Date: 2026-03-06

Status note:

This is a historical implementation-planning record for the V2 rollout, not the current operational definition of the subagent surface.

For the current repo-grounded remediation plan, see `../GAP_CLOSURE_PLAN.md`.
For the latest validated implementation snapshot, see `../HANDOFF_2026-03-06.md`.
For the current subagent/catalog usage reference, see `../SUBAGENTS.md` and `../../Generated/Subagents/`.

## Overview

This plan maps the Premium Feature Plan V2 phases to specialist subagents for parallel implementation.

## New V2 Specialists

### 1. Unity Spatial Specialist
**ID:** `unity-spatial-specialist`
**Group:** `spatial` (new)
**Phase:** Phase 3

**Tools:**
- `manage_transform` (new)
- `spatial_queries` (new)

**When to Use:**
- Transform-aware inspection and manipulation
- Spatial reasoning about object placement
- Snap, align, distribute operations
- Bounds and overlap queries
- Raycast and surface queries

**Workflow:**
1. Activate spatial group
2. Use spatial_queries to understand scene layout
3. Apply transforms with manage_transform
4. Validate placement with spatial validation

**Handoff Targets:**
- `unity-core-builder` (for prefab/scene saves)
- `unity-testing-specialist` (for validation)

---

### 2. Unity Project Config Specialist
**ID:** `unity-project-config-specialist`
**Group:** `project_config` (new)
**Phase:** Phase 2

**Tools:**
- `manage_project_settings` (new)
- `manage_editor_settings` (new)
- `manage_registry_config` (new)
- `analyze_asset_dependencies` (new)
- `manage_asset_import_settings` (new)
- `list_shaders` (new)
- `find_builtin_assets` (new)
- `get_component_types` (new)
- `get_object_references` (new)

**When to Use:**
- Project settings inspection or mutation
- Package registry management
- Asset dependency analysis
- Import settings configuration
- Shader and built-in asset discovery
- Component type enumeration

**Workflow:**
1. Activate project_config group
2. Inspect current configuration
3. Make targeted updates
4. Validate changes compile/work

**Handoff Targets:**
- `unity-core-builder` (for asset operations)
- `unity-testing-specialist` (for validation)

---

### 3. Unity Pipeline Specialist
**ID:** `unity-pipeline-specialist`
**Group:** `pipeline` (new)
**Phase:** Phase 5

**Tools:**
- `record_pipeline` (new)
- `stop_pipeline_recording` (new)
- `replay_pipeline` (new)
- `save_pipeline` (new)
- `list_pipelines` (new)
- `list_playbooks` (new)
- `run_playbook` (new)
- `create_playbook` (new)

**When to Use:**
- Recording editor workflows
- Replaying saved workflows
- Running pre-built playbooks
- Creating reusable automation

**Workflow:**
1. Start recording
2. Execute workflow via other specialists
3. Stop and save pipeline
4. Replay or convert to playbook

**Handoff Targets:**
- All specialists (pipelines orchestrate other tools)

---

### 4. Unity Visual QA Specialist
**ID:** `unity-visual-qa-specialist`
**Group:** `visual_qa` (new)
**Phase:** Phase 4

**Tools:**
- `analyze_screenshot` (new)
- Visual verification loop integration

**When to Use:**
- Post-mutation visual verification
- Screenshot analysis
- Visual regression detection
- Scene/UI validation

**Workflow:**
1. Activate visual_qa group
2. Capture screenshot via manage_video_capture
3. Analyze with analyze_screenshot
4. Report findings

**Handoff Targets:**
- `unity-testing-specialist` (for structural validation)
- `unity-core-builder` (for fixes)

---

## Phase 1: Editor Workflow Completion

### Assigned to: `unity-core-specialist` (extension)

**New/Extended Tools:**
1. Extend `manage_prefabs` with stage actions:
   - `open_stage`
   - `save_open_stage`
   - `close_stage`

2. Extend `manage_scene` with:
   - `list_opened`
   - `set_active`
   - `unload`

3. New `manage_selection`:
   - `set_selection`
   - `frame_selection`

4. New `manage_windows`:
   - `list_windows`
   - `open_window`
   - `focus_window`
   - `close_window`
   - `get_active_tool`
   - `set_active_tool`

5. Extend `manage_editor`:
   - `play`
   - `pause`
   - `stop`
   - `quit_editor` (with explicit opt-in)

6. New `manage_script_execution`:
   - `execute_csharp_snippet`

7. New `ping`
8. New `get_command_stats`

**Subagent Tasks:**
```json
{
  "subagent": "unity-core-specialist",
  "task": "Implement Phase 1: Editor Workflow Completion",
  "work_packages": [
    {
      "name": "Prefab Stage Lifecycle",
      "tools": ["manage_prefabs:open_stage", "manage_prefabs:save_open_stage", "manage_prefabs:close_stage"],
      "acceptance": "Agents can edit prefabs in isolation mode"
    },
    {
      "name": "Multi-Scene Control",
      "tools": ["manage_scene:list_opened", "manage_scene:set_active", "manage_scene:unload"],
      "acceptance": "Agents can manage additive scene workflows"
    },
    {
      "name": "Selection Management",
      "tools": ["manage_selection:set_selection", "manage_selection:frame_selection"],
      "acceptance": "Agents can change selection and frame objects"
    },
    {
      "name": "Window and Tool Control",
      "tools": ["manage_windows:list_windows", "manage_windows:open_window", "manage_windows:focus_window", "manage_windows:close_window", "manage_windows:get_active_tool", "manage_windows:set_active_tool"],
      "acceptance": "Agents can control editor windows and active tools"
    },
    {
      "name": "Play Mode Control",
      "tools": ["manage_editor:play", "manage_editor:pause", "manage_editor:stop", "manage_editor:quit_editor"],
      "acceptance": "Agents can control play mode and safely quit editor"
    }
  ]
}
```

---

## Phase 2: Project and Asset Intelligence

### Assigned to: `unity-project-config-specialist`

**New Tools:**
1. `manage_project_settings` - read/update project settings
2. `manage_editor_settings` - read/update editor preferences
3. `manage_registry_config` - manage scoped registries
4. `analyze_asset_dependencies` - dependency graph analysis
5. `manage_asset_import_settings` - import settings inspection/mutation
6. `list_shaders` - enumerate available shaders
7. `find_builtin_assets` - search built-in assets
8. `get_component_types` - global component discovery
9. `get_object_references` - object reference graph inspection

**Subagent Tasks:**
```json
{
  "subagent": "unity-project-config-specialist",
  "task": "Implement Phase 2: Project and Asset Intelligence",
  "work_packages": [
    {
      "name": "Project Settings",
      "tools": ["manage_project_settings"],
      "acceptance": "Agents can inspect and update project settings safely"
    },
    {
      "name": "Editor Settings",
      "tools": ["manage_editor_settings"],
      "acceptance": "Agents can inspect and update editor preferences"
    },
    {
      "name": "Registry Management",
      "tools": ["manage_registry_config"],
      "acceptance": "Agents can manage scoped package registries"
    },
    {
      "name": "Asset Intelligence",
      "tools": ["analyze_asset_dependencies", "manage_asset_import_settings", "list_shaders", "find_builtin_assets"],
      "acceptance": "Agents can analyze asset relationships and configure import pipelines"
    },
    {
      "name": "Component Discovery",
      "tools": ["get_component_types", "get_object_references"],
      "acceptance": "Agents can discover component types and inspect object references"
    }
  ]
}
```

---

## Phase 3: Transform and Spatial Awareness

### Assigned to: `unity-spatial-specialist`

**New Tools:**
1. `manage_transform` - transform operations
2. `spatial_queries` - spatial reasoning

**Actions in manage_transform:**
- `get_world_transform`
- `get_local_transform`
- `set_world_transform`
- `set_local_transform`
- `get_bounds`
- `snap_to_grid`
- `align_to_object`
- `distribute_objects`
- `place_relative`
- `validate_placement`

**Actions in spatial_queries:**
- `nearest_object`
- `objects_in_radius`
- `objects_in_box`
- `overlap_check`
- `raycast`
- `get_distance`
- `get_direction`
- `get_relative_offset`

**Subagent Tasks:**
```json
{
  "subagent": "unity-spatial-specialist",
  "task": "Implement Phase 3: Transform and Spatial Awareness",
  "work_packages": [
    {
      "name": "Transform Inspection",
      "actions": ["get_world_transform", "get_local_transform", "get_bounds"],
      "acceptance": "Agents can inspect transforms and bounds accurately"
    },
    {
      "name": "Spatial Queries",
      "actions": ["nearest_object", "objects_in_radius", "objects_in_box", "overlap_check", "raycast"],
      "acceptance": "Agents can query spatial relationships"
    },
    {
      "name": "Placement Helpers",
      "actions": ["snap_to_grid", "align_to_object", "distribute_objects", "place_relative"],
      "acceptance": "Agents can place objects with precision"
    },
    {
      "name": "Transform Validation",
      "actions": ["validate_placement"],
      "acceptance": "Agents can detect invalid placements"
    }
  ]
}
```

---

## Phase 4: Visual Verification

### Assigned to: `unity-visual-qa-specialist`

**New Tools:**
1. `analyze_screenshot` - AI-powered screenshot analysis

**Integration Points:**
- Uses existing `manage_video_capture` for capture
- Returns structured analysis of visual state

**Subagent Tasks:**
```json
{
  "subagent": "unity-visual-qa-specialist",
  "task": "Implement Phase 4: Visual Verification",
  "work_packages": [
    {
      "name": "Screenshot Analysis",
      "tools": ["analyze_screenshot"],
      "acceptance": "Agents can capture and analyze visual evidence"
    },
    {
      "name": "Visual Verification Loop",
      "workflow": "Capture → Analyze → Report → Act",
      "acceptance": "Visual verification is a first-class workflow pattern"
    }
  ]
}
```

---

## Phase 5: Pipelines and Playbooks

### Assigned to: `unity-pipeline-specialist`

**New Tools:**
1. `record_pipeline` - start recording
2. `stop_pipeline_recording` - stop and save
3. `replay_pipeline` - replay saved pipeline
4. `save_pipeline` - persist pipeline
5. `list_pipelines` - enumerate saved pipelines
6. `list_playbooks` - enumerate playbooks
7. `run_playbook` - execute playbook
8. `create_playbook` - create from pipeline or steps

**Subagent Tasks:**
```json
{
  "subagent": "unity-pipeline-specialist",
  "task": "Implement Phase 5: Pipelines and Playbooks",
  "work_packages": [
    {
      "name": "Recording Infrastructure",
      "tools": ["record_pipeline", "stop_pipeline_recording"],
      "acceptance": "Editor actions can be recorded"
    },
    {
      "name": "Pipeline Management",
      "tools": ["save_pipeline", "list_pipelines", "replay_pipeline"],
      "acceptance": "Pipelines can be saved, listed, and replayed"
    },
    {
      "name": "Playbook System",
      "tools": ["list_playbooks", "run_playbook", "create_playbook"],
      "acceptance": "Playbooks provide reusable workflows"
    }
  ]
}
```

---

## Phase 6: Project Memory and Rules

### Assigned to: `unity-project-config-specialist` (extension)

**New Tools:**
1. `manage_project_memory` - rules and conventions storage

**Actions:**
- `load_rules`
- `save_rules`
- `summarize_conventions`
- `get_active_rules`
- `validate_against_rules`

**Subagent Tasks:**
```json
{
  "subagent": "unity-project-config-specialist",
  "task": "Implement Phase 6: Project Memory and Rules",
  "work_packages": [
    {
      "name": "Rules Storage",
      "actions": ["load_rules", "save_rules"],
      "acceptance": "Project conventions can be persisted"
    },
    {
      "name": "Rules Retrieval",
      "actions": ["summarize_conventions", "get_active_rules"],
      "acceptance": "Agents can retrieve current rule set"
    },
    {
      "name": "Rules Validation",
      "actions": ["validate_against_rules"],
      "acceptance": "Agents can check work against project conventions"
    }
  ]
}
```

---

## Updated Orchestrator Handoff Map

The `unity-orchestrator` needs to route to new specialists:

```json
{
  "handoff_map_updates": {
    "spatial": {
      "specialist_id": "unity-spatial-specialist",
      "tool_count": 2,
      "activate": {
        "tool": "manage_tools",
        "params": {"action": "activate", "group": "spatial"}
      }
    },
    "project_config": {
      "specialist_id": "unity-project-config-specialist",
      "tool_count": 9,
      "activate": {
        "tool": "manage_tools",
        "params": {"action": "activate", "group": "project_config"}
      }
    },
    "pipeline": {
      "specialist_id": "unity-pipeline-specialist",
      "tool_count": 8,
      "activate": {
        "tool": "manage_tools",
        "params": {"action": "activate", "group": "pipeline"}
      }
    },
    "visual_qa": {
      "specialist_id": "unity-visual-qa-specialist",
      "tool_count": 1,
      "activate": {
        "tool": "manage_tools",
        "params": {"action": "activate", "group": "visual_qa"}
      }
    }
  }
}
```

---

## Implementation Sequence

### Parallel Workstreams

**Stream A: Core Editor (unity-core-specialist)**
- Week 1-2: Prefab stage lifecycle, Multi-scene control
- Week 3: Selection management, Window/tool control
- Week 4: Play mode control, Script execution

**Stream B: Project Config (unity-project-config-specialist)**
- Week 1-2: Project settings, Editor settings, Registry config
- Week 3: Asset intelligence (dependencies, import settings, shaders, built-in assets)
- Week 4: Component discovery, Object references

**Stream C: Spatial (unity-spatial-specialist)**
- Week 1-2: Transform inspection, Spatial queries
- Week 3: Placement helpers
- Week 4: Transform validation

**Stream D: Visual QA (unity-visual-qa-specialist)**
- Week 3-4: Screenshot analysis, Visual verification loop

**Stream E: Pipelines (unity-pipeline-specialist)**
- Week 5-6: Recording infrastructure, Pipeline management
- Week 7-8: Playbook system

**Stream F: Memory (unity-project-config-specialist extension)**
- Week 7-8: Rules storage, retrieval, validation

---

## Tool Count Projection

| Phase | New Tools | New Actions | Group |
|-------|-----------|-------------|-------|
| Phase 1 | 4 | 15+ | core extensions |
| Phase 2 | 9 | 25+ | project_config |
| Phase 3 | 2 | 16+ | spatial |
| Phase 4 | 1 | 2+ | visual_qa |
| Phase 5 | 8 | 8+ | pipeline |
| Phase 6 | 1 | 5+ | project_config |
| **Total** | **25** | **71+** | **4 new groups** |

Starting from 61 tools, V2 will bring the total to approximately **86 tools**.

---

## Success Metrics per Subagent

### unity-core-specialist
- Prefab stage workflows complete without manual Unity interaction
- Agents can manage additive scenes end to end
- Selection changes reflect in editor resources

### unity-project-config-specialist
- Project/package configuration inspectable and mutable
- Asset relationships return structured output
- Component discovery works without guesswork

### unity-spatial-specialist
- Agents reason about object placement spatially
- Placement operations return structured values
- Invalid placements are detected automatically

### unity-visual-qa-specialist
- Visual evidence captured and analyzed
- Self-correction flows use visual feedback

### unity-pipeline-specialist
- Multi-step workflows recorded and replayed
- Playbooks compound existing tool value

---

## Next Actions

1. **Create new specialist subagent definitions** in `Generated/Subagents/`
2. **Extend existing specialists** with V2 tool assignments
3. **Update orchestrator** handoff map
4. **Regenerate subagent catalog**
5. **Begin Phase 1 implementation** with unity-core-specialist
