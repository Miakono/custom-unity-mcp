from __future__ import annotations

"""
Manage Unity Scripting Define Symbols for conditional compilation.

Actions:
- get_define_symbols: Get scripting define symbols for platform
- add_define_symbol: Add a define symbol
- remove_define_symbol: Remove a define symbol
- set_define_symbols: Replace all symbols

Safety:
- Symbol changes trigger script recompilation
- Removing symbols may break conditional code
- Wide-scope operations are classified and auditable
"""
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    group="pipeline_control",
    description=(
        "Manage Unity Scripting Define Symbols for conditional compilation. "
        "Read-only actions: get_define_symbols. "
        "Modifying actions: add_define_symbol, remove_define_symbol, set_define_symbols. "
        "Changes trigger script recompilation."
    ),
    annotations=ToolAnnotations(
        title="Manage Define Symbols",
        destructiveHint=True,
    ),
)
async def manage_define_symbols(
    ctx: Context,
    action: Annotated[
        Literal[
            "get_define_symbols",
            "get_symbols",
            "add_define_symbol",
            "add_symbol",
            "remove_define_symbol",
            "remove_symbol",
            "set_define_symbols",
            "set_symbols",
            "clear_symbols",
        ],
        "Action to perform: get_define_symbols (read symbols), add_define_symbol (add one), "
        "remove_define_symbol (remove one), set_define_symbols (replace all)"
    ],
    platform: Annotated[
        str | None,
        "Target build platform for the symbols (e.g., 'Standalone', 'Android', 'iOS', 'WebGL', 'All'). "
        "If not specified, uses the current active build target."
    ] = None,
    symbol: Annotated[
        str | None,
        "Define symbol to add or remove (for add_define_symbol/remove_define_symbol actions)"
    ] = None,
    symbols: Annotated[
        list[str] | None,
        "List of define symbols to set (for set_define_symbols action)"
    ] = None,
    build_target: Annotated[
        str | None,
        "Alias for platform."
    ] = None,
) -> dict[str, Any]:
    """
    Manage Unity Scripting Define Symbols for conditional compilation.
    
    This tool provides control over scripting define symbols that enable conditional
    compilation using #if/#elif/#endif preprocessor directives.
    
    Supported Platforms:
    - Standalone (StandaloneWindows, StandaloneOSX, StandaloneLinux)
    - Android
    - iOS
    - WebGL
    - tvOS
    - All (affects all platforms)
    
    Safety Notes:
    - Adding/removing symbols triggers script recompilation which may take time
    - Removing symbols may break code that relies on them
    - Unity's built-in symbols (DEBUG, UNITY_EDITOR, etc.) cannot be modified
    - Symbol names must be valid C# identifiers (letters, digits, underscores, starting with letter or _)
    
    Examples:
    - Get symbols for current platform: action="get_define_symbols"
    - Get symbols for Android: action="get_define_symbols", platform="Android"
    - Add symbol: action="add_define_symbol", symbol="ENABLE_CHEATS"
    - Add platform-specific: action="add_define_symbol", platform="Android", symbol="GOOGLE_PLAY"
    - Remove symbol: action="remove_define_symbol", symbol="ENABLE_CHEATS"
    - Replace all: action="set_define_symbols", symbols=["FEATURE_A", "FEATURE_B", "DEBUG_MODE"]
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "manage_define_symbols", action=action)
    if gate is not None:
        return gate.model_dump()
    
    try:
        action_aliases = {
            "get_symbols": "get_define_symbols",
            "add_symbol": "add_define_symbol",
            "remove_symbol": "remove_define_symbol",
            "set_symbols": "set_define_symbols",
            "clear_symbols": "set_define_symbols",
        }
        resolved_action = action_aliases.get(action, action)
        params: dict[str, Any] = {"action": resolved_action}
        
        effective_platform = build_target or platform
        if effective_platform:
            params["platform"] = effective_platform
        if symbol:
            params["symbol"] = symbol
        if action == "clear_symbols":
            params["symbols"] = []
        elif symbols is not None:
            params["symbols"] = symbols
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_define_symbols",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Define symbols operation '{resolved_action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error managing define symbols: {e!s}"}
