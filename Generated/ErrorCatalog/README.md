# Unity MCP Error Catalog

Structured error and operational contract data for the custom fork.

Stable codes: 53
Domains: 9

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
- `sha_mismatch`
  - Surfaces: `apply_text_edits`, `create_script`, `delete_script`
  - Meaning: The content SHA256 did not match, indicating concurrent modification.
  - Typical fix: Re-read the file and retry the operation with the updated SHA.
- `file_not_found`
  - Surfaces: `apply_text_edits`, `delete_script`, `validate_script`
  - Meaning: The target script file could not be found.
  - Typical fix: Verify the file path exists and is correctly spelled.
- `file_locked`
  - Surfaces: `apply_text_edits`, `create_script`, `delete_script`
  - Meaning: The target file is locked by another process (e.g., IDE, version control).
  - Typical fix: Close the file in other applications and retry.
- `syntax_error`
  - Surfaces: `validate_script`, `apply_text_edits`
  - Meaning: The resulting script would have syntax errors.
  - Typical fix: Review the edit for unbalanced braces, missing semicolons, etc.

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
- `asset_modify_failed`
  - Surfaces: `manage_scriptable_object`
  - Meaning: Unity failed while modifying the ScriptableObject.
  - Typical fix: Check that all serialized fields exist and types match.
- `type_mismatch`
  - Surfaces: `manage_scriptable_object`
  - Meaning: The provided value type does not match the expected field type.
  - Typical fix: Ensure JSON values match the C# field types (e.g., use numbers for int/float).

## GameObject Management

Error codes for GameObject CRUD operations.

- `gameobject_not_found`
  - Surfaces: `manage_gameobject`
  - Meaning: The target GameObject could not be found by name, path, or ID.
  - Typical fix: Verify the GameObject exists in the current scene. Use find_gameobjects to search.
- `invalid_parent`
  - Surfaces: `manage_gameobject`
  - Meaning: The specified parent GameObject is invalid or not found.
  - Typical fix: Verify the parent exists, or use null for root-level objects.
- `component_not_found`
  - Surfaces: `manage_gameobject`, `manage_components`
  - Meaning: The requested component could not be found on the target GameObject.
  - Typical fix: Verify the component name is correct and exists on the GameObject.
- `component_add_failed`
  - Surfaces: `manage_components`
  - Meaning: Failed to add the component (type may not exist or be allowed).
  - Typical fix: Verify the component type name is fully qualified and the assembly is loaded.
- `invalid_transform`
  - Surfaces: `manage_gameobject`
  - Meaning: The provided position, rotation, or scale values are invalid.
  - Typical fix: Use valid numeric arrays with 3 elements [x, y, z].

## Scene Management

Error codes for scene operations.

- `scene_not_found`
  - Surfaces: `manage_scene`
  - Meaning: The requested scene could not be found.
  - Typical fix: Verify the scene path is correct and the scene exists in the project.
- `scene_load_failed`
  - Surfaces: `manage_scene`
  - Meaning: Unity failed to load the scene.
  - Typical fix: Check that the scene is in the build settings and has no load errors.
- `scene_save_failed`
  - Surfaces: `manage_scene`
  - Meaning: Unity failed to save the scene.
  - Typical fix: Check file permissions and disk space.
- `active_scene_unchanged`
  - Surfaces: `manage_scene`
  - Meaning: The requested scene is already the active scene.
  - Typical fix: No action needed, or specify a different scene to activate.

## Prefab Operations

Error codes for prefab management.

- `prefab_not_found`
  - Surfaces: `manage_prefabs`
  - Meaning: The prefab asset could not be found.
  - Typical fix: Verify the prefab path is correct and exists in the project.
- `prefab_instantiate_failed`
  - Surfaces: `manage_prefabs`
  - Meaning: Failed to instantiate the prefab into the scene.
  - Typical fix: Verify the prefab is valid and can be instantiated.
- `prefab_variant_not_supported`
  - Surfaces: `manage_prefabs`
  - Meaning: The operation is not supported on prefab variants.
  - Typical fix: Apply the operation to the base prefab or use supported actions.
- `nested_prefab_modified`
  - Surfaces: `manage_prefabs`
  - Meaning: Attempted to modify a nested prefab which requires special handling.
  - Typical fix: Unpack or open the prefab for editing before making changes.

## Asset Management

Error codes for asset operations.

- `asset_not_found`
  - Surfaces: `manage_asset`, `manage_material`, `manage_texture`
  - Meaning: The asset could not be found at the specified path.
  - Typical fix: Verify the asset path is correct and the asset exists.
- `asset_import_failed`
  - Surfaces: `manage_asset`
  - Meaning: Unity failed to import the asset.
  - Typical fix: Check the asset file format and integrity.
- `invalid_guid`
  - Surfaces: `manage_asset`
  - Meaning: The provided GUID is invalid or malformed.
  - Typical fix: Use a valid Unity GUID (32 hexadecimal characters).
- `guid_not_found`
  - Surfaces: `manage_asset`
  - Meaning: No asset found with the specified GUID.
  - Typical fix: Verify the GUID is correct and the asset exists in the project.

## Batch Execution

Error codes for batch_execute operations.

- `batch_too_large`
  - Surfaces: `batch_execute`
  - Meaning: The batch contains more commands than the configured maximum.
  - Typical fix: Split the batch into smaller chunks or increase the limit in Unity settings.
- `invalid_command`
  - Surfaces: `batch_execute`
  - Meaning: One or more commands in the batch are malformed or missing required fields.
  - Typical fix: Ensure each command has 'tool' and 'params' fields with valid values.
- `batch_partial_failure`
  - Surfaces: `batch_execute`
  - Meaning: Some commands in the batch succeeded while others failed.
  - Typical fix: Review the per-command results and retry failed commands individually.
- `circular_reference`
  - Surfaces: `batch_execute`
  - Meaning: Commands in the batch have circular dependencies.
  - Typical fix: Restructure the batch to remove circular dependencies.

## Connection and Transport

Error codes for Unity connection issues.

- `unity_not_connected`
  - Surfaces: `*`
  - Meaning: No Unity instance is currently connected.
  - Typical fix: Ensure Unity is running with the MCP plugin enabled.
- `connection_timeout`
  - Surfaces: `*`
  - Meaning: The connection to Unity timed out.
  - Typical fix: Check Unity is responsive and retry the operation.
- `instance_not_found`
  - Surfaces: `set_active_instance`
  - Meaning: The specified Unity instance could not be found.
  - Typical fix: List available instances with mcpforunity://instances and use a valid Name@hash.
- `serialization_error`
  - Surfaces: `*`
  - Meaning: Failed to serialize or deserialize the request/response.
  - Typical fix: Check that all parameters are JSON-serializable.

## Tool Capability Errors

Error codes for capability and permission issues.

- `tool_disabled`
  - Surfaces: `*`
  - Meaning: The tool is disabled by configuration or group settings.
  - Typical fix: Enable the tool group with manage_tools(action='activate') or check capability config.
- `opt_in_required`
  - Surfaces: `execute_menu_item`, `batch_execute`, `delete_script`
  - Meaning: This tool requires explicit user opt-in before use.
  - Typical fix: Add the tool to the tool_opt_in section of capabilities.json.
- `runtime_only_tool`
  - Surfaces: `read_console`
  - Meaning: This tool only works when Unity is in play mode.
  - Typical fix: Enter play mode in Unity before using this tool.
- `dry_run_not_supported`
  - Surfaces: `*`
  - Meaning: The requested dry-run (preview) mode is not supported by this tool.
  - Typical fix: Remove the dry_run flag or use a different tool.

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
- `busy response with retry_after_ms`
  - Surface: all tools with preflight
  - Meaning: The server is temporarily unable to process the request (compiling, testing, etc.).
  - Typical fix: Wait for the specified retry_after_ms period and retry the request.
- `success=false with code and data fields`
  - Surface: structured error responses
  - Meaning: A recoverable error occurred with machine-readable details.
  - Typical fix: Check the 'code' field against the error catalog and apply the typical fix.
