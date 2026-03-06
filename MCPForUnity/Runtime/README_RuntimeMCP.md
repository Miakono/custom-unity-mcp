# Runtime MCP (Play Mode / Built Games)

This directory contains the Runtime MCP foundation - a separate MCP track that works in **Play Mode** and **Built Games**, distinct from the Editor-only MCP.

## Overview

Runtime MCP provides:
- **Separate capability domain** from Editor MCP
- **Runtime-only tools** that never appear in Editor-only environments
- **Support for Play Mode** (Editor) and **Built Games** (Standalone)
- **WebSocket-based communication** on a separate port (default: 8090)
- **Same policy metadata and error contracts** as Editor MCP

## Key Principles

1. **Runtime tools are CLEARLY tagged as `runtime_only`**
2. **Runtime tools NEVER appear in editor-only environments**
3. **Separate capability domain** from Editor MCP (`domain: "runtime"`)
4. **Reuses same policy metadata and error contracts**
5. **Supports both Play Mode and Built Games**
6. **Uses different port/connection** than Editor MCP

## File Structure

```
MCPForUnity/Runtime/
├── MCP/
│   ├── RuntimeMCPBridge.cs           # Main bridge component
│   ├── RuntimeToolRegistry.cs        # Runtime tool registration
│   ├── RuntimeCommandProcessor.cs    # Command routing
│   └── Transports/
│       └── RuntimeWebSocketClient.cs # WebSocket transport
├── Tools/
│   ├── RuntimeGameObjectTools.cs     # GameObject manipulation
│   ├── RuntimeSceneTools.cs          # Scene queries
│   └── RuntimeInputTools.cs          # Input simulation
└── Helpers/
    └── MiniJSON.cs                   # JSON serialization
```

## Quick Start

### 1. Add Runtime Bridge to Scene

1. Create a new GameObject in your scene (or use an existing manager)
2. Add the **Runtime MCP Bridge** component (`MCP > Runtime MCP Bridge`)
3. Configure connection settings:
   - **Server Host**: `127.0.0.1` (or your MCP server IP)
   - **Server Port**: `8090` (separate from Editor MCP)
   - **Auto Connect**: Enable for automatic connection

### 2. Configure the Server

Ensure the MCP server is configured to accept Runtime connections on port 8090.

### 3. Available Runtime Tools

#### GameObject Tools
- `runtime_gameobject_find` - Find GameObjects by name/tag/component
- `runtime_gameobject_get_info` - Get detailed GameObject information
- `runtime_gameobject_set_active` - Enable/disable GameObjects
- `runtime_gameobject_set_transform` - Modify transform (position/rotation/scale)
- `runtime_gameobject_get_components` - List attached components
- `runtime_gameobject_destroy` - Destroy GameObjects at runtime

#### Scene Tools
- `runtime_scene_get_active` - Get active scene info
- `runtime_scene_list` - List all loaded scenes
- `runtime_scene_get_hierarchy` - Get scene hierarchy
- `runtime_scene_load` - Load scenes
- `runtime_scene_get_root_objects` - Get root GameObjects
- `runtime_scene_get_stats` - Scene statistics

#### Input Tools
- `runtime_input_simulate_key` - Simulate keyboard input
- `runtime_input_simulate_mouse` - Simulate mouse input
- `runtime_input_get_keyboard_state` - Query keyboard state
- `runtime_input_get_mouse_state` - Query mouse state
- `runtime_input_get_axes` - Get Input Manager axes
- `runtime_input_simulate_touch` - Simulate touch input

## Server-Side Bridge Tools

The server provides bridge tools for runtime communication:

- `get_runtime_status` - Check if runtime MCP is available
- `list_runtime_tools` - List tools available in runtime context
- `execute_runtime_command` - Execute command in runtime context
- `get_runtime_connection_info` - Get connection details

## Capability Metadata

Runtime tools include capability flags:

```json
{
  "runtime_only": true,
  "requires_runtime_context": true,
  "domain": "runtime",
  "separate_connection": true
}
```

## Differences from Editor MCP

| Feature | Editor MCP | Runtime MCP |
|---------|------------|-------------|
| Context | Unity Editor | Play Mode / Built Games |
| Port | 8080 (configurable) | 8090 (default) |
| Domain | `editor` | `runtime` |
| Tools | Editor-only | Runtime-only |
| Compilation | Triggers recompile | N/A |
| Asset Database | Full access | Runtime objects only |

## Scripting Example

```csharp
using MCPForUnity.Runtime.MCP;

// Access the runtime bridge
var bridge = RuntimeMCPBridge.Instance;

// Check connection status
if (bridge.IsConnected)
{
    Debug.Log("Runtime MCP connected!");
    Debug.Log($"Session ID: {bridge.SessionId}");
}

// Get runtime status
var status = bridge.GetStatus();
```

## Troubleshooting

### Connection Issues
- Ensure the MCP server is running and accepting connections on port 8090
- Check firewall settings
- Verify the server host IP is correct

### Input System
- Input simulation requires the **New Input System** package
- Enable it in `Project Settings > Player > Other Settings > Active Input Handling`

### Built Games
- The Runtime MCP Bridge must be included in the build
- Ensure the `MCPForUnity.Runtime` assembly is included

## Security Considerations

- Runtime MCP connections should be secured in production builds
- Consider disabling MCP in release builds
- Use authentication for remote connections

## Future Enhancements

- Physics query tools
- Audio control tools
- Animation playback control
- Network multiplayer support
- Profiling and performance tools
