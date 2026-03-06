"""
tool_catalog resource - exposes the generated live tool catalog.

URI: mcpforunity://tool-catalog
"""
from typing import Any

from fastmcp import Context

from services.catalog import build_tool_catalog
from services.registry import mcp_for_unity_resource


@mcp_for_unity_resource(
    uri="mcpforunity://tool-catalog",
    name="tool_catalog",
    description=(
        "Generated tool catalog derived from the live server tool registry, "
        "including capability metadata inferred from action policy.\n\n"
        "URI: mcpforunity://tool-catalog"
    ),
)
async def get_tool_catalog(ctx: Context) -> dict[str, Any]:
    _ = ctx
    return build_tool_catalog()
