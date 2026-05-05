"""
compose_prefab — build a prefab from scratch in one MCP call.

Takes a JSON tree describing GameObjects, components, and serialized property patches.
Internally creates a temporary GameObject in the active scene with the described shape,
saves it as a prefab at `prefab_path`, then deletes the temp.

Generic — no project-specific assumptions. The tool's value is collapsing the existing
"create scene GO → add components → set fields → save_as_prefab → delete scene GO" sequence
(5+ MCP calls) down to one.
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
        "Build a prefab from a JSON tree describing GameObjects, components, and "
        "serialized property patches. Saves to prefab_path in one round trip. "
        "Each node accepts: name, tag, layer, active, transform "
        "(position/rotation/scale arrays), components (list of {type, patches}), "
        "children (recursive)."
    ),
    annotations=ToolAnnotations(
        title="Compose Prefab",
        destructiveHint=True,
    ),
    group="pipeline",
)
async def compose_prefab(
    ctx: Context,
    prefab_path: Annotated[
        str,
        "Where to save the prefab, e.g. 'Assets/Prefabs/Foo.prefab'. Folder is created if missing.",
    ],
    root: Annotated[
        dict[str, Any],
        "Root GameObject spec: {name, tag?, layer?, active?, transform?, components?, children?}",
    ],
    overwrite: Annotated[
        bool,
        "If true, replace any existing asset at prefab_path (default false).",
    ] = False,
) -> MCPResponse:
    gate = await maybe_run_tool_preflight(ctx, "compose_prefab")
    if gate is not None:
        return MCPResponse(**gate.model_dump())

    unity_instance = await get_unity_instance_from_context(ctx)
    params: dict[str, Any] = {
        "prefab_path": prefab_path,
        "root": root,
        "overwrite": overwrite,
    }
    result = await send_with_unity_instance(
        async_send_command_with_retry, unity_instance, "compose_prefab", params
    )
    return MCPResponse(**result) if isinstance(result, dict) else result
