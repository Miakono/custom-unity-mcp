# Unity Animation Specialist

ID: `unity-animation-specialist`
Kind: `specialist`

Focuses on animator, clips, and animation editing tasks.

Tool group: `animation`
Activate with: `manage_tools(action="activate", group="animation")`

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
- `manage_animation`

Use when:
- Animator or clip authoring.
- Animation controller inspection or repair.
- Playback-oriented content adjustments.

Workflow:
- Activate the animation group for the current session.
- Prefer small, verifiable changes to animation assets.
- Route follow-up validation to testing when clips or controllers were mutated.

Handoff targets:
- `unity-testing-specialist`
- `unity-core-builder`
