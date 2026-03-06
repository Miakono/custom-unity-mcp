# Subagents

The server now exposes a generated subagent catalog derived from the live tool registry.

What is included:
- One `unity-orchestrator` definition for routing work between specialists.
- One specialist per tool group: core, vfx, animation, ui, scripting_ext, and testing.
- Shared meta-tools such as `manage_tools` included in each artifact for session routing.
- Capability metadata can now also be pulled from `mcpforunity://tool-catalog`.
- The tool catalog now includes parameter schemas, supported action enums, and per-action read-only vs mutating contracts where they can be inferred from signatures plus action policy.

How to consume it:
- Read the MCP resource `mcpforunity://subagents/catalog` for the live catalog.
- Read the MCP resource `mcpforunity://tool-catalog` for the live tool capability catalog.
- Read the MCP resource `mcpforunity://error-catalog` for stable error-code and operational-contract data.
- Read the MCP resource `mcpforunity://validation/profiles` for Unity-side validation and audit profile metadata.
- Call `manage_subagents(action="list")` to inspect the same catalog as a tool response.
- Call `manage_subagents(action="export")` to write JSON and Markdown artifacts to `Generated/Subagents/`.
- Call `manage_catalog(action="export")` to write the tool catalog to `Generated/Catalog/`.
- Call `manage_error_catalog(action="export")` to write the error catalog to `Generated/ErrorCatalog/`.
- Catalog and subagent exports are safe to run from a cold process now; they bootstrap the live registry before writing artifacts.

Why this shape:
- It matches the existing tool-group visibility model instead of inventing a separate runtime.
- It stays game-agnostic and server-local.
- It creates reusable specialist definitions for Codex, Claude, or other MCP clients that support subagent-style workflows.
