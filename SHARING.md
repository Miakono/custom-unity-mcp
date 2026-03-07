# Sharing Custom Game Dev Unity MCP

This package is derived from CoplayDev/unity-mcp and published with the package name `com.customgamedev.unity-mcp`.

## What To Share

- Entire folder: `custom-unity-mcp/` (or your chosen repo name)
- Includes:
- `MCPForUnity/` (Unity package)
- `Server/` (MCP server)
- `LICENSE` (MIT, upstream attribution)

## Friend Setup (Unity)

1. Clone this repository.
2. In Unity, open `Window > Package Manager`.
3. Add package from git URL:

```text
https://github.com/your-org/custom-unity-mcp.git?path=/MCPForUnity
```

Or pin this fork directly:

```text
https://github.com/Miakono/custom-unity-mcp.git?path=/MCPForUnity#main
```

1. Open `Window > MCP for Unity` and start the server.
2. Configure MCP client (VS Code/Cursor/Claude Code) using the generated config from the Unity window.

## Included Custom Tool

- `validate_project_state`
- Returns editor compile/play/update status, active scene info, and a readiness recommendation.

## Validation Artifacts To Share

- Live validation matrix: `Docs/LIVE_TEST_MATRIX.md`
- Current handoff summary: `Docs/HANDOFF_2026-03-06.md`
- VFX preset walkthrough: `Docs/MAGE_FIREBALL_VFX.md`

These documents capture what has been verified live, known limitations, and practical recovery steps.

## CLI Reliability Notes For Users

- When targeting by instance ID and the ID is negative, include `--` before the ID:
  `--search-method by_id -- -59950`
- If multiple GameObjects share a name, resolve IDs first via `gameobject find` and target by ID to avoid ambiguity.

## Recommended Next Steps

1. Add project tools in `MCPForUnity/Editor/Tools/Custom/`.
2. Keep upstream MIT license and attribution.
3. Tag releases for stable versions your friends can pin.
