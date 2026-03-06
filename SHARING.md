# Sharing Custom Unity MCP

This folder is a standalone custom MCP fork that you can share with friends.

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

4. Open `Window > MCP for Unity` and start the server.
5. Configure MCP client (VS Code/Cursor/Claude Code) using the generated config from the Unity window.

## Included Custom Tool

- `validate_project_state`
- Returns editor compile/play/update status, active scene info, and a readiness recommendation.

## Recommended Next Steps

1. Add project tools in `MCPForUnity/Editor/Tools/Custom/`.
2. Keep upstream MIT license and attribution.
3. Tag releases for stable versions your friends can pin.
