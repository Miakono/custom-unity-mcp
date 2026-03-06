"""Server-local tool for listing and exporting registry-backed subagent artifacts."""

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.subagents import export_subagent_artifacts, build_subagent_catalog


@mcp_for_unity_tool(
    unity_target=None,
    group=None,
    description=(
        "List or export generated Unity MCP subagent artifacts built from the live tool registry. "
        "Use action='list' to inspect the current catalog. "
        "Use action='export' to write JSON and/or Markdown subagent files to disk."
    ),
    annotations=ToolAnnotations(
        title="Manage Subagents",
        readOnlyHint=False,
    ),
)
async def manage_subagents(
    ctx: Context,
    action: Annotated[
        Literal["list", "export"],
        "Whether to inspect the catalog or export artifacts to disk.",
    ],
    output_dir: Annotated[
        str | None,
        "Directory for exported artifacts. Defaults to Generated/Subagents in the repo root.",
    ] = None,
    format: Annotated[
        Literal["json", "markdown", "both"],
        "Export format when action='export'.",
    ] = "both",
) -> dict[str, Any]:
    if action == "list":
        return build_subagent_catalog()

    include_json = format in {"json", "both"}
    include_markdown = format in {"markdown", "both"}
    await ctx.info("Exporting subagent artifacts from the live tool registry")
    result = export_subagent_artifacts(
        output_dir,
        include_json=include_json,
        include_markdown=include_markdown,
    )
    return {
        "exported": True,
        "output_dir": result["output_dir"],
        "written_files": result["written_files"],
        "subagent_count": result["subagent_count"],
        "message": (
            f"Exported {result['subagent_count']} subagent artifacts to {result['output_dir']}."
        ),
    }
