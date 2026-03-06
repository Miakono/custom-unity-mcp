# Unity VFX Specialist

ID: `unity-vfx-specialist`
Kind: `specialist`

Handles shaders, materials, textures, and VFX authoring flows.

Tool group: `vfx`
Activate with: `manage_tools(action="activate", group="vfx")`

Shared meta-tools:
- `debug_request_context`
- `execute_custom_tool`
- `manage_catalog`
- `manage_error_catalog`
- `manage_script_capabilities`
- `manage_subagents`
- `manage_tools`
- `set_active_instance`

Primary tools:
- `manage_shader`
- `manage_texture`
- `manage_vfx`

Use when:
- Shader and material iteration.
- Texture inspection or mutation workflows.
- VFX Graph or look-dev tasks.

Workflow:
- Activate the vfx group before work starts.
- Capture or inspect current asset state before broad mutations.
- Escalate back to core or testing when changes affect shared assets or scene behavior.

Handoff targets:
- `unity-core-builder`
- `unity-testing-specialist`
