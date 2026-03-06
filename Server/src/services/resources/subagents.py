"""
subagents resource - exposes the generated Unity MCP subagent catalog.

URI: mcpforunity://subagents/catalog
"""
from typing import Any

from fastmcp import Context

from services.registry import mcp_for_unity_resource
from services.subagents import build_subagent_catalog


@mcp_for_unity_resource(
    uri="mcpforunity://subagents/catalog",
    name="subagent_catalog",
    description=(
        "Generated Unity MCP subagent catalog built from the live tool registry. "
        "Includes one orchestrator and one specialist per tool group.\n\n"
        "URI: mcpforunity://subagents/catalog"
    ),
)
async def get_subagent_catalog(ctx: Context) -> dict[str, Any]:
    _ = ctx
    return build_subagent_catalog()
