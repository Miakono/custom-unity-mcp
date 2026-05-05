# MCP for Unity — Performance Guide

This document is for **agents and humans** integrating with this MCP package. Picking the wrong call pattern can be the difference between a 200 ms response and a 4-second editor stall.

## Built-in fast paths

### 1. `batch_execute` — always batch multi-step work
- Default limit is **50 commands per batch** (configurable up to 100 via `MCPForUnity.BatchExecute.MaxCommands` EditorPref).
- The whole batch runs inside one `AssetDatabase.StartAssetEditing()` / `StopAssetEditing()` scope, so per-command imports are coalesced into a single refresh at the end.
- One batch = one main-thread round trip. Ten sequential calls cost ~5× more than one batch of ten.

### 2. Script edits are debounced — don't double-compile
| Tool | Default refresh | Notes |
|---|---|---|
| `apply_text_edits` | `debounced` (200 ms window) | Override with `refresh: "immediate"` only if subsequent same-response code needs the compile to have finished. |
| `manage_script update` | `debounced` | Same. |
| `create_script` | `debounced` with `forceCompile` | New types can't be Hot-Reload-patched, so the eventual flush always compiles — but multiple consecutive `create_script` calls still coalesce into **one** compile. |
| `compile_now` | — | Flush the debounce queue immediately. Use only when you need a deterministic compile before reading runtime state. |

A 5-edit refactor across 5 files now triggers **1** compile, down from 5.

### 3. Hot Reload integration
If [Singularity Group Hot Reload](https://hotreload.net) is active, in-domain method-body edits skip `AssetDatabase.ImportAsset` + `RequestScriptCompilation` entirely — the file watcher patches in-domain. The MCP package detects this via `HotReloadIntegration.ShouldDeferScriptCompilation()` and steps out of the way. Force-compile callers (e.g. `create_script`, which adds new types Hot Reload can't patch) override the deferral so type additions still recompile.

### 4. Generic compose / scaffold tools — eliminate round-trips
| Tool | Purpose | Replaces |
|---|---|---|
| `compose_prefab` | Build a prefab from a JSON tree (GameObjects + components + serialized property patches + children) in one call. Folder is auto-created. | The "create scene GO → add components → set fields → save_as_prefab → delete scene GO" 5-step sequence. |
| `scaffold_from_editor_menu` | Run any `[MenuItem]`-decorated method by path AND get an asset diff (added / removed / modified paths). | Editor scaffolders that previously needed a project-specific MCP wrapper. |
| `register_in_serialized_list` | Idempotently append a primitive or object reference to a serialized list/array on a ScriptableObject, prefab Component, or scene Component. | Multi-step "find object → SerializedObject → array_resize → set element → save" sequences. |
| `compile_now` | Flush the script-edit debounce queue immediately when a deterministic compile boundary is needed. | Manual `refresh_unity` between edits. |

### 4a. Playbook v2 — composable, conditional, looped workflows

`run_playbook` now supports per-step features beyond literal `{{param}}` substitution:

| Feature | Example |
|---|---|
| Capture step output for later use | `"output_as": "compose"` |
| Reference earlier output | `"prefab_path": "{{step_output.compose.data.prefab_path}}"` |
| Reference previous step | `"when": "{{prev.success}} == true"` |
| Skip on condition | `"when": "{{register_in_pool}} == true"` |
| Iterate over a list | `"for_each": "items"` (loop locals: `{{item}}`, `{{index}}`) |
| Helper functions | `"guid": "{{guid_of('Assets/X.prefab')}}"` |

Type preservation: when a string value is *exactly* one `{{...}}` expression, the resolved value is inserted as its native type (int / dict / list / bool) — so `"value": "{{count}}"` with `count=5` becomes `"value": 5`, not `"value": "5"`. Mixed strings still stringify.

Backwards-compatible: every v1 playbook continues to work unchanged.

### 5. Adaptive polling
`wait_for_editor_condition` now starts at the caller-supplied interval (default 0.1 s) and exponentially backs off (×1.5 per miss, capped at 5× initial or 2 s, whichever is lower). Long compiles no longer get hammered with 0.1 s polls; quick conditions still resolve fast.

### 6. Asset GUID ↔ path cache
`MCPForUnity.Editor.Services.AssetPathCache` provides a process-wide bidirectional cache invalidated automatically on every asset import / move / delete via `AssetPostprocessor`. Use `AssetPathCache.GetPath(guid)` and `AssetPathCache.GetGuid(path)` instead of calling `AssetDatabase` directly inside hot loops.

## Observability — `mcp_perf_stats`

Always-on, allocation-free in-process counters surfaced through the `mcp_perf_stats` tool:

```json
{ "action": "snapshot", "top_n": 20 }
```

Returns per-tool `calls`, `failures`, `total_handler_ms`, `avg_handler_ms`, `max_handler_ms`, `total_queue_wait_ms`, `max_queue_wait_ms`, plus session totals: `compile_trigger_count`, `forced_sync_import_count`, `idle_ticks_per_sec`, `asset_path_cache_hit_rate`. Cumulative-cost sorted (top-N is what's actually eating budget, not the slowest single call).

Reset between workflows with `{ "action": "reset" }` so before/after deltas are clean.

## Anti-patterns

- **Don't insert manual `refresh_unity` calls between script edits** — it re-introduces the per-edit compile cost the debouncer was added to remove.
- **Don't issue 10 sequential `manage_*` calls** when a single `batch_execute` works. The batch wrapper suppresses per-import refresh storms automatically.
- **Don't poll `editor_state` in tight loops** while a long compile/test runs — use `wait_for_editor_condition` or back off exponentially.
- **Don't `Instantiate`/`Destroy` transient gameplay objects from MCP-driven code** — projects with pool managers expect pool spawn/release. (Project-specific; check the host project's CLAUDE.md.)

## Adding new tools

If you write a new MCP handler:
- Avoid calling `AssetDatabase.Refresh()` or `RequestScriptCompilation()` from inside a handler unless the user explicitly asked for a refresh. Trust the batch-level `StartAssetEditing` scope and the debounce.
- If you must compile, increment `MCPForUnity.Editor.Services.PerfMetrics.RecordCompileTrigger()` so it shows up in `mcp_perf_stats` and reviewers can spot regressions.
- Async handlers: when `CommandRegistry.ExecuteCommand` returns null (true async), per-tool latency is measured at task completion automatically — don't double-record.
