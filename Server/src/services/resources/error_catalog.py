"""
error_catalog resource - exposes the generated fork error catalog.

URI: mcpforunity://error-catalog
"""
from typing import Any

from fastmcp import Context

from services.error_catalog import build_error_catalog
from services.registry import mcp_for_unity_resource


@mcp_for_unity_resource(
    uri="mcpforunity://error-catalog",
    name="error_catalog",
    description=(
        "Generated error-code and operational-contract catalog for the custom Unity MCP fork.\n\n"
        "URI: mcpforunity://error-catalog"
    ),
)
async def get_error_catalog(ctx: Context) -> dict[str, Any]:
    _ = ctx
    return build_error_catalog()
