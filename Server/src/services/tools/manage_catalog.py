"""Server-local tool for listing and exporting the live tool catalog."""

from typing import Annotated, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.catalog import build_tool_catalog, export_tool_catalog_artifacts
from services.registry import mcp_for_unity_tool


@mcp_for_unity_tool(
    unity_target=None,
    group=None,
    description=(
        "List or export the generated Unity MCP tool catalog built from the live tool registry "
        "and action policy metadata."
    ),
    annotations=ToolAnnotations(
        title="Manage Catalog",
        readOnlyHint=False,
    ),
)
async def manage_catalog(
    ctx: Context,
    action: Annotated[
        Literal["list", "export"],
        "Whether to inspect the catalog or export it to disk.",
    ],
    output_dir: Annotated[
        str | None,
        "Directory for exported artifacts. Defaults to Generated/Catalog in the repo root.",
    ] = None,
    format: Annotated[
        Literal["json", "markdown", "both"],
        "Export format when action='export'.",
    ] = "both",
) -> dict:
    if action == "list":
        return build_tool_catalog()

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
