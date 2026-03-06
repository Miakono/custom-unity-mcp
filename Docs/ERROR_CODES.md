# Error Codes

This document records the currently stable machine-readable error codes used by fork-specific server paths.

Live machine-readable surfaces:
- MCP resource: `mcpforunity://error-catalog`
- Server tool: `manage_error_catalog(action="list" | "export" | "get_code" | "get_for_surface")`
- Generated artifacts: `Generated/ErrorCatalog/`

## Script Editing

These are emitted by `manage_script` and `script_apply_edits` when the server can normalize or reject an edit before sending it to Unity.

| Code | Meaning | Typical fix |
| --- | --- | --- |
| `missing_field` | A required edit field was omitted. | Add the required lines, columns, or path fields. |
| `zero_based_explicit_fields` | Explicit line/column values were provided as 0-based. | Resend line and column values as 1-based indices. |
| `overlap` | Two edit spans overlap. | Split or reorder edits so spans do not intersect. |
| `preview_failed` | The server could not build a preview of the requested edit. | Re-read the file, narrow the edit, and retry. |
| `path_outside_assets` | A path or URI resolved outside `Assets/`. | Use an asset path rooted under `Assets/`. |
| `bad_path` | The supplied path was malformed, absolute, or traversal-like. | Send a normalized Unity asset path. |
| `bad_extension` | The requested file extension is not allowed for that operation. | Use a `.cs` path for script creation. |
| `bad_level` | A validation level or mode was not recognized. | Use one of the documented level values. |
| `anchor_not_found` | An anchor-based edit target could not be resolved. | Re-read the file and provide a more specific anchor. |
| `unsupported_op` | A text edit operation is not supported by the current server path. | Rewrite the request using a supported edit op. |
| `no_spans` | The server computed no applicable edit spans. | Verify the target range or anchor still exists. |
| `conversion_failed` | The server failed converting a higher-level edit into text spans. | Simplify the edit request and retry. |
| `sha_mismatch` | The content SHA256 did not match, indicating concurrent modification. | Re-read the file and retry with the updated SHA. |
| `file_not_found` | The target script file could not be found. | Verify the file path exists and is correctly spelled. |
| `file_locked` | The target file is locked by another process. | Close the file in other applications and retry. |
| `syntax_error` | The resulting script would have syntax errors. | Review the edit for unbalanced braces, missing semicolons, etc. |

## Scriptable Objects

These are emitted by the Unity-side `manage_scriptable_object` implementation and passed through the server unchanged.

| Code | Meaning | Typical fix |
| --- | --- | --- |
| `compiling_or_reloading` | Unity rejected the operation because scripts are compiling or the domain is reloading. | Wait for the editor to become idle, then retry. |
| `invalid_params` | The ScriptableObject payload is missing required fields or uses an invalid shape. | Check the action payload and resend the required parameters. |
| `type_not_found` | The requested ScriptableObject CLR type could not be resolved. | Use a valid namespace-qualified type name. |
| `invalid_folder_path` | The target folder is invalid or not rooted under `Assets/`. | Use a valid project folder under `Assets/`. |
| `target_not_found` | The target asset could not be resolved from the provided guid or path. | Re-resolve the target asset and retry. |
| `asset_create_failed` | Unity failed while creating or saving the requested asset. | Inspect the type, path, and current editor state, then retry. |
| `asset_modify_failed` | Unity failed while modifying the ScriptableObject. | Check that all serialized fields exist and types match. |
| `type_mismatch` | The provided value type does not match the expected field type. | Ensure JSON values match the C# field types. |

## GameObject Management

These are emitted by `manage_gameobject` and `manage_components` operations.

| Code | Meaning | Typical fix |
| --- | --- | --- |
| `gameobject_not_found` | The target GameObject could not be found. | Verify the GameObject exists in the current scene. |
| `invalid_parent` | The specified parent GameObject is invalid. | Verify the parent exists, or use null for root-level objects. |
| `component_not_found` | The requested component could not be found. | Verify the component name is correct and exists. |
| `component_add_failed` | Failed to add the component. | Verify the component type name is fully qualified. |
| `invalid_transform` | The provided transform values are invalid. | Use valid numeric arrays with 3 elements [x, y, z]. |

## Scene Management

These are emitted by `manage_scene` operations.

| Code | Meaning | Typical fix |
| --- | --- | --- |
| `scene_not_found` | The requested scene could not be found. | Verify the scene path is correct. |
| `scene_load_failed` | Unity failed to load the scene. | Check that the scene is in the build settings. |
| `scene_save_failed` | Unity failed to save the scene. | Check file permissions and disk space. |
| `active_scene_unchanged` | The requested scene is already active. | No action needed, or specify a different scene. |

## Prefab Operations

These are emitted by `manage_prefabs` operations.

| Code | Meaning | Typical fix |
| --- | --- | --- |
| `prefab_not_found` | The prefab asset could not be found. | Verify the prefab path is correct. |
| `prefab_instantiate_failed` | Failed to instantiate the prefab. | Verify the prefab is valid. |
| `prefab_variant_not_supported` | Operation not supported on prefab variants. | Apply to the base prefab or use supported actions. |
| `nested_prefab_modified` | Attempted to modify a nested prefab. | Unpack or open the prefab for editing. |

## Asset Management

These are emitted by asset operations.

| Code | Meaning | Typical fix |
| --- | --- | --- |
| `asset_not_found` | The asset could not be found. | Verify the asset path is correct. |
| `asset_import_failed` | Unity failed to import the asset. | Check the asset file format and integrity. |
| `invalid_guid` | The provided GUID is invalid. | Use a valid Unity GUID (32 hex characters). |
| `guid_not_found` | No asset found with the specified GUID. | Verify the GUID is correct. |

## Batch Execution

These are emitted by `batch_execute` when batch operations fail.

| Code | Meaning | Typical fix |
| --- | --- | --- |
| `batch_too_large` | The batch contains more commands than allowed. | Split the batch into smaller chunks. |
| `invalid_command` | One or more commands are malformed. | Ensure each command has 'tool' and 'params' fields. |
| `batch_partial_failure` | Some commands succeeded, others failed. | Review per-command results and retry failed ones. |
| `circular_reference` | Commands have circular dependencies. | Restructure the batch to remove circular dependencies. |

## Connection and Transport

These are emitted when Unity connection issues occur.

| Code | Meaning | Typical fix |
| --- | --- | --- |
| `unity_not_connected` | No Unity instance is connected. | Ensure Unity is running with the MCP plugin. |
| `connection_timeout` | Connection to Unity timed out. | Check Unity is responsive and retry. |
| `instance_not_found` | The specified Unity instance could not be found. | Use a valid Name@hash from mcpforunity://instances. |
| `serialization_error` | Failed to serialize/deserialize request/response. | Check that all parameters are JSON-serializable. |

## Tool Capability Errors

These are emitted when tool capabilities or permissions prevent execution.

| Code | Meaning | Typical fix |
| --- | --- | --- |
| `tool_disabled` | The tool is disabled by configuration. | Enable the tool group with manage_tools. |
| `opt_in_required` | This tool requires explicit user opt-in. | Add the tool to tool_opt_in in capabilities.json. |
| `runtime_only_tool` | This tool only works in play mode. | Enter play mode in Unity before using. |
| `dry_run_not_supported` | Dry-run mode is not supported. | Remove the dry_run flag or use a different tool. |

## Operational Responses

These are not yet standardized everywhere, but they are already relied on by fork features and tests.

| Pattern | Meaning | Typical fix |
| --- | --- | --- |
| `success=false` with `message` asking to call `set_active_instance` | No active Unity instance is selected. | Call `set_active_instance` with `Name@hash` from `mcpforunity://instances`. |
| `success=false` from preflight-gated tools | Unity is compiling, importing, or otherwise not ready. | Wait for the editor to become ready, then retry. |
| `error` text from `manage_tools(action="sync")` with unsupported wording | The Unity plugin is too old to report tool states. | Update the Unity package or toggle groups manually. |
| `busy` response with `retry_after_ms` | Server temporarily unable to process (compiling, testing). | Wait for the specified period and retry. |
| `success=false` with `code` and `data` fields | Recoverable error with machine-readable details. | Check the `code` against the error catalog. |

## Capability Metadata

Tools now expose comprehensive capability metadata. Use `manage_catalog` or query the tool catalog to discover:

| Capability | Description |
| --- | --- |
| `supports_dry_run` | Tool supports preview mode without applying changes |
| `local_only` | Tool is server-only (doesn't require Unity connection) |
| `runtime_only` | Tool only works when Unity is in play mode |
| `requires_explicit_opt_in` | Tool requires explicit user opt-in for high-risk operations |
| `supports_verification` | Tool supports post-operation verification |
| `read_only` | Tool/action doesn't modify state |
| `mutating` | Tool/action modifies state |
| `high_risk` | Tool/action has significant impact or is destructive |

## Notes

- This file documents codes that are already present in the current fork. It is not yet a complete contract for every tool.
- The generated error catalog is the structured companion to this document and is intended to stay easier for clients to consume than the prose tables here.
- Tools now properly declare their capabilities via the `ToolActionPolicy` and `capability_flags` modules.
- Capability metadata is queryable programmatically via the catalog or `get_tool_capabilities()` functions.
