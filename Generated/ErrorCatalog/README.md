# Unity MCP Error Catalog

Structured error and operational contract data for the custom fork.

Stable codes: 18
Domains: 2

## Script Editing

Stable machine-readable codes emitted by script edit and validation flows.

- `missing_field`
  - Surfaces: `apply_text_edits`, `script_apply_edits`
  - Meaning: A required edit field was omitted or could not be normalized.
  - Typical fix: Send the required path, range, or replacement fields.
- `zero_based_explicit_fields`
  - Surfaces: `apply_text_edits`
  - Meaning: Explicit line or column coordinates were sent as 0-based values.
  - Typical fix: Resend explicit line and column coordinates as 1-based indices.
- `overlap`
  - Surfaces: `apply_text_edits`
  - Meaning: Two requested edit spans overlap.
  - Typical fix: Split or reorder edits so no two spans intersect.
- `preview_failed`
  - Surfaces: `apply_text_edits`
  - Meaning: The server could not build the requested local preview payload.
  - Typical fix: Retry with a smaller edit batch or remove preview mode.
- `path_outside_assets`
  - Surfaces: `create_script`, `delete_script`, `validate_script`, `apply_text_edits`
  - Meaning: A path or URI resolved outside the Unity Assets folder.
  - Typical fix: Use an asset path rooted under Assets/.
- `bad_path`
  - Surfaces: `create_script`
  - Meaning: The provided path was malformed, absolute, or traversal-like.
  - Typical fix: Send a normalized Unity asset path without traversal segments.
- `bad_extension`
  - Surfaces: `create_script`
  - Meaning: The provided file extension is not valid for that script operation.
  - Typical fix: Use a .cs target path for script creation.
- `bad_level`
  - Surfaces: `validate_script`
  - Meaning: The requested script validation level is not recognized.
  - Typical fix: Use one of the documented level values.
- `anchor_not_found`
  - Surfaces: `script_apply_edits`
  - Meaning: An anchor-based edit target could not be resolved.
  - Typical fix: Re-read the file and provide a more specific anchor.
- `unsupported_op`
  - Surfaces: `script_apply_edits`
  - Meaning: The requested structured edit operation is not supported.
  - Typical fix: Rewrite the request using a supported edit op.
- `no_spans`
  - Surfaces: `script_apply_edits`
  - Meaning: No applicable text spans were computed for the requested edit.
  - Typical fix: Verify that the target method, class, or anchor still exists.
- `conversion_failed`
  - Surfaces: `script_apply_edits`
  - Meaning: The server failed converting a higher-level edit into raw spans.
  - Typical fix: Simplify the edit request and retry after re-reading the file.

## Scriptable Objects

Stable Unity-side error codes emitted by ScriptableObject management.

- `compiling_or_reloading`
  - Surfaces: `manage_scriptable_object`
  - Meaning: Unity was compiling or reloading and rejected the write operation.
  - Typical fix: Wait until the editor is idle, then retry.
- `invalid_params`
  - Surfaces: `manage_scriptable_object`
  - Meaning: A required ScriptableObject parameter was missing or malformed.
  - Typical fix: Validate the action payload and resend the required fields.
- `type_not_found`
  - Surfaces: `manage_scriptable_object`
  - Meaning: The requested ScriptableObject CLR type could not be resolved.
  - Typical fix: Use a valid namespace-qualified ScriptableObject type name.
- `invalid_folder_path`
  - Surfaces: `manage_scriptable_object`
  - Meaning: The target folder path is invalid or outside the supported project area.
  - Typical fix: Use a valid folder rooted under Assets/.
- `target_not_found`
  - Surfaces: `manage_scriptable_object`
  - Meaning: The ScriptableObject target could not be resolved from guid or path.
  - Typical fix: Re-resolve the asset guid or path and retry.
- `asset_create_failed`
  - Surfaces: `manage_scriptable_object`
  - Meaning: Unity failed while creating or saving the requested asset.
  - Typical fix: Inspect the payload and target path, then retry after Unity is idle.

## Operational Patterns

- `success=false with guidance to call set_active_instance`
  - Surface: multi-instance server flows
  - Meaning: No active Unity instance is selected for the current session.
  - Typical fix: Call set_active_instance with a Name@hash value from mcpforunity://instances.
- `preflight-gated tool returns success=false before mutation`
  - Surface: mutating tools
  - Meaning: Unity is compiling, importing, running tests, or otherwise not ready for mutation.
  - Typical fix: Wait for the editor to become ready, then retry the mutation tool.
- `manage_tools(action='sync') returns unsupported wording`
  - Surface: tool visibility sync
  - Meaning: The connected Unity plugin is too old to report tool-state visibility.
  - Typical fix: Update the Unity package or toggle groups manually with activate/deactivate.
