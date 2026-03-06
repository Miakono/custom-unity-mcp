"""Server-local tool for listing and exporting the live tool catalog."""

from typing import Annotated, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.catalog import (
    build_tool_catalog,
    export_tool_catalog_artifacts,
    get_tool_capabilities_query,
    query_capabilities,
)
from services.registry import mcp_for_unity_tool


@mcp_for_unity_tool(
    unity_target=None,
    group=None,
    description=(
        "List, query, or export the generated Unity MCP tool catalog built from the live tool registry "
        "and action policy metadata. "
        "Actions: list (full catalog), get_tool (specific tool capabilities), query (filtered search), "
        "export (save to disk)."
    ),
    annotations=ToolAnnotations(
        title="Manage Catalog",
        readOnlyHint=True,
    ),
)
async def manage_catalog(
    ctx: Context,
    action: Annotated[
        Literal["list", "export", "get_tool", "query"],
        "Whether to list the catalog, query capabilities, or export to disk.",
    ],
    output_dir: Annotated[
        str | None,
        "Directory for exported artifacts. Defaults to Generated/Catalog in the repo root.",
    ] = None,
    format: Annotated[
        Literal["json", "markdown", "both"],
        "Export format when action='export'.",
    ] = "both",
    tool_name: Annotated[
        str | None,
        "Tool name to query when action='get_tool'.",
    ] = None,
    capability_filter: Annotated[
        str | None,
        "Filter by capability when action='query' (e.g., 'supports_dry_run', 'local_only').",
    ] = None,
) -> dict:
    if action == "list":
        return build_tool_catalog()

    if action == "get_tool":
        if not tool_name:
            return {
                "success": False,
                "error": "tool_name parameter is required for get_tool action",
            }
        return get_tool_capabilities_query(tool_name)

    if action == "query":
        return query_capabilities(
            tool_name=None,
            capability_filter=capability_filter,
        )

    # action == "export"
    include_json = format in {"json", "both"}
    include_markdown = format in {"markdown", "both"}
    await ctx.info("Exporting live tool catalog artifacts")
    result = export_tool_catalog_artifacts(
        output_dir,
        include_json=include_json,
        include_markdown=include_markdown,
    )
    return {
        "exported": True,
        "output_dir": result["output_dir"],
        "written_files": result["written_files"],
        "tool_count": result["tool_count"],
        "message": f"Exported tool catalog for {result['tool_count']} tools to {result['output_dir']}.",
    }
