"""
scaffold_from_editor_menu — execute any Unity Editor [MenuItem] and return an asset diff.

Generic primitive for agent-driven setup: every Unity project ships with editor scaffolders
(Assets/Editor/*.cs) that create default ScriptableObjects, prefabs, lighting, scenes, etc.
Without this tool, an agent has to either (a) call execute_menu_item and then guess what
got created, or (b) reimplement the scaffolder logic in MCP calls. This tool runs the menu
item AND returns added/removed/modified asset paths in one call.
"""
from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from models import MCPResponse
from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    description=(
        "Execute a Unity Editor menu item by path and return the resulting asset diff "
        "(added / removed / modified asset paths). Use this to invoke project scaffolders "
        "and immediately know what assets they produced. Refuses destructive built-ins "
        "(File/Quit, Edit/Project Settings/Reset, Assets/Reimport All)."
    ),
    annotations=ToolAnnotations(
        title="Scaffold from Editor Menu",
        destructiveHint=True,
    ),
    group="pipeline",
)
async def scaffold_from_editor_menu(
    ctx: Context,
    menu_path: Annotated[
        str,
        "Full menu path, e.g. 'Roguelike/Create Default Statue Blessing Assets' or 'Assets/Create/Material'",
    ],
    dry_run: Annotated[
        bool,
        "When true, snapshots assets and returns counts without executing the menu item.",
    ] = False,
    max_diff_entries: Annotated[
        int,
        "Cap on entries returned in each diff list (default 50).",
    ] = 50,
) -> MCPResponse:
    gate = await maybe_run_tool_preflight(ctx, "scaffold_from_editor_menu")
    if gate is not None:
        return MCPResponse(**gate.model_dump())

    unity_instance = await get_unity_instance_from_context(ctx)
    params: dict[str, Any] = {
        "menu_path": menu_path,
        "dry_run": dry_run,
        "max_diff_entries": max_diff_entries,
    }
    result = await send_with_unity_instance(
        async_send_command_with_retry, unity_instance, "scaffold_from_editor_menu", params
    )
    return MCPResponse(**result) if isinstance(result, dict) else result
