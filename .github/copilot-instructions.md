# ironandspores-mcp — Agent Instructions

## Project Purpose

This is a **custom Unity MCP (Model Context Protocol) server extension** for Unity 6.3, forked from upstream MCP for Unity. It is designed to help a **solo developer move fast** building an MMORPG on **SpacetimeDB v2.0.5** (with future upgrade path). The server bridges AI agents ↔ Unity Editor via WebSocket + HTTP, exposing 133 tools across 19 groups.

Target: eliminate boilerplate, catch errors early, and automate repetitive Unity tasks through AI-driven tool calls.

## Architecture

```
Server/          Python MCP server (fastmcp ≥3.0.2, pydantic v2, Python 3.10+)
  src/services/tools/     133 publishable MCP tools
  src/services/state/     Multi-instance Unity session state
  src/services/registry/  Tool registration + action policy
  src/services/catalog.py Tool catalog generation
MCPForUnity/     Unity editor C# package (2021.3 LTS+, targets Unity 6.3)
  Editor/Tools/  19 tool groups; Custom/ is the extension point for new tools
  Editor/Tools/IronAndSpores/  Project-specific audit tools
Generated/       Auto-generated artifacts — DO NOT DELETE
  Catalog/tool_catalog.json    Full tool registry (source of truth)
  Subagents/                   Specialist agent profiles
  ErrorCatalog/error_catalog.json
```

**Flow**: AI agent → Python MCP server → WebSocket bridge → Unity Editor C# handler → response

## Build & Test

```powershell
# Install Python deps (one-time)
cd Server
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

# Start MCP server
python -m main --transport http --http-url http://localhost:8080

# Run unit tests
python -m pytest tests/ -q

# Run live Unity smoke tests (requires editor open)
.\Scripts\Run-ValidationSuite.ps1 -UnityInstance "ProjectName@hashId"
```

**Unity plugin**: Window → MCP for Unity → Auto-Setup → Start Bridge

## Critical Agent Constraints

These apply to every workflow — read before mutating anything:

1. **Compile blocking**: Always call `validate_compile_health` before any script edit. Tools return `compiling_or_reloading` error if Unity is compiling — wait and retry.
2. **SHA versioning**: `apply_text_edits` requires a valid SHA256 of current file content. Re-read the file if a concurrent edit is suspected (`sha_mismatch` error).
3. **Preflight gates**: Mutating tools (scene, prefab, script) are gated by `action_policy.py`. Respect error codes — do not force or skip preflight.
4. **Multi-instance**: If multiple Unity editors are open, call `set_active_instance` with `Name@hash` before any tool use.
5. **No play-mode edits**: Broad scene/asset mutations must be done in edit mode. Use `manage_runtime_ui` only during play mode.
6. **Never delete `.meta` files or `Generated/`** — GUIDs live in `.meta`; `Generated/` holds publishable artifacts.

## Conventions

### Python (Server)
- Type hints required; Pyright basic mode enforced (`pyrightconfig.json`)
- `snake_case` for functions/modules, `PascalCase` for classes
- Async/await throughout (httpx, websockets, fastapi)
- New tools: add to `Server/src/services/tools/` + register in tool registry with a group

### Unity C# (MCPForUnity)
- See [UnityMCPRules.md](../UnityMCPRules.md) for full conventions
- PascalCase: classes, public methods, prefabs, scene names
- `camelCase`: private fields, locals; use `[SerializeField]` not public fields
- XML doc comments on all public APIs
- Cache component refs in `Awake`/`Start` — never `FindObjectOfType` in `Update`
- New editor tools: add to `MCPForUnity/Editor/Tools/Custom/`

### Asset Paths
- All paths Unity-relative under `Assets/` with forward slashes
- Resolve name collisions by GameObject ID via `find_gameobjects` first (names are not unique)

### Batch First
- Prefer `batch_execute` for 3+ sequential operations (10–100× faster than individual calls)
- Always `preflight_audit` before broad multi-step scene changes

## SpacetimeDB Integration

SpacetimeDB v2.0.5 integration is a **future layer** — not yet in source. Extension points when ready:

- Custom Unity tools → `MCPForUnity/Editor/Tools/Custom/`
- Python counterparts → `Server/src/services/tools/`
- Register with new group key `"spacetimedb"` in tool registry
- See the `spacetimedbv2-expert` skill (`c:\Users\Josh\.copilot\skills\spacetimedbv2-expert\SKILL.md`) for WASM reducer, energy, and schema patterns

## Key Docs

| Doc | What it covers |
|-----|---------------|
| [README_CUSTOM.md](../README_CUSTOM.md) | Fork context + customization targets |
| [UnityMCPRules.md](../UnityMCPRules.md) | Full Unity coding + naming conventions |
| [Docs/ERROR_CODES.md](../Docs/ERROR_CODES.md) | All stable error codes by category |
| [Docs/SUBAGENTS.md](../Docs/SUBAGENTS.md) | How to load and use specialist profiles |
| [Docs/HANDOFF_2026-03-06.md](../Docs/HANDOFF_2026-03-06.md) | Latest validated state + known working flows |
| [Docs/GAP_CLOSURE_PLAN.md](../Docs/GAP_CLOSURE_PLAN.md) | Active remediation priorities |
| [Docs/LIVE_TEST_MATRIX.md](../Docs/LIVE_TEST_MATRIX.md) | Tool group coverage + smoke test status |
| [Server/README.md](../Server/README.md) | Server setup (PyPI / Docker / Git) |
| [MCPForUnity/README.md](../MCPForUnity/README.md) | Plugin install + quick-start |
| [SPATIAL_TOOLS_README.md](../SPATIAL_TOOLS_README.md) | Transform + spatial query tools |

## Live MCP Resources (no tool call needed)
- `mcpforunity://tool-catalog` — Full capability registry with schemas
- `mcpforunity://subagents/catalog` — Specialist routing
- `mcpforunity://error-catalog` — Error code → operational response mappings
- `mcpforunity://instances` — Active Unity editor sessions

## Common Pitfalls

| Symptom | Fix |
|---------|-----|
| `compiling_or_reloading` | Wait for compile, then retry |
| `sha_mismatch` on script edit | Re-read file, get fresh SHA, retry |
| `search_code` returns stale results | `manage_code_intelligence(action="rebuild_index")` |
| Screenshot is black/blank | Restore Unity editor window first |
| Wrong instance targeted | `set_active_instance "ProjectName@hash"` |
| `nested_prefab_modified` | Open/unpack nested prefab before editing |
| CLI negative GameObject ID fails | Use `--` before ID: `gameobject find -- -59950` |
