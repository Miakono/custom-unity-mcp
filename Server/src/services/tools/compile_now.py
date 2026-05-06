"""
compile_now — flush the script-edit debounce queue and request a compile.

Use after a burst of manage_script edits when you want compilation to start
immediately rather than wait for the 200ms debounce window. Returns once the
flush is requested; poll editor_state (or call refresh_unity wait_for_ready=true)
to know when the editor is idle again.
"""
from typing import Annotated

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
        "Flush the script-edit debounce queue and request a Unity compile immediately. "
        "Use after a burst of edits when you want the compile to start now rather than "
        "wait for the 200ms debounce. Poll editor_state until ready_for_tools=true "
        "(or call refresh_unity with wait_for_ready=true) before issuing more edits."
    ),
    annotations=ToolAnnotations(
        title="Flush + Compile Now",
        destructiveHint=False,
    ),
    group="dev_tools",
)
async def compile_now(
    ctx: Context,
) -> MCPResponse:
    gate = await maybe_run_tool_preflight(ctx, "compile_now")
    if gate is not None:
        return MCPResponse(**gate.model_dump())

    unity_instance = await get_unity_instance_from_context(ctx)
    result = await send_with_unity_instance(
        async_send_command_with_retry, unity_instance, "compile_now", {}
    )
    return MCPResponse(**result) if isinstance(result, dict) else result
