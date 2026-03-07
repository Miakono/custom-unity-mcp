# Unity Pipeline Specialist

ID: `unity-pipeline-specialist`
Kind: `specialist`

Owns workflow recording, pipeline management, and reusable playbook execution.

Tool group: `pipeline`
Activate with: `manage_tools(action="activate", group="pipeline")`

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
- `record_pipeline`
- `stop_pipeline_recording`
- `replay_pipeline`
- `save_pipeline`
- `list_pipelines`
- `list_playbooks`
- `run_playbook`
- `create_playbook`

Use when:
- Recording editor workflows for later replay
- Replaying saved multi-step workflows
- Running pre-built playbooks
- Creating reusable automation from recorded actions
- Managing pipeline storage and organization

Workflow:
- Activate the pipeline group for the current session.
- Start recording to capture a workflow.
- Execute workflow via other specialists while recording.
- Stop and save the pipeline with a descriptive name.
- Replay pipelines directly or convert to playbooks for reusable workflows.
- Audit trail is maintained for all pipeline operations.

Handoff targets:
- All specialists (pipelines orchestrate other tools)
