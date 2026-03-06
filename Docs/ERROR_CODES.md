# Error Codes

This document records the currently stable machine-readable error codes used by fork-specific server paths.

Live machine-readable surfaces:
- MCP resource: `mcpforunity://error-catalog`
- Server tool: `manage_error_catalog(action="list" | "export")`
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

## Operational Responses

These are not yet standardized everywhere, but they are already relied on by fork features and tests.

| Pattern | Meaning | Typical fix |
| --- | --- | --- |
| `success=false` with `message` asking to call `set_active_instance` | No active Unity instance is selected. | Call `set_active_instance` with `Name@hash` from `mcpforunity://instances`. |
| `success=false` from preflight-gated tools | Unity is compiling, importing, or otherwise not ready for mutation. | Wait for the editor to become ready, then retry. |
| `error` text from `manage_tools(action="sync")` with unsupported wording | The Unity plugin is too old to report tool states. | Update the Unity package or toggle groups manually. |

## Notes

- This file documents codes that are already present in the current fork. It is not yet a complete contract for every tool.
- The generated error catalog is the structured companion to this document and is intended to stay easier for clients to consume than the prose tables here.
