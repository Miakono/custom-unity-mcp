"""Server-local tool for listing and exporting the fork error catalog."""

from typing import Annotated, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.error_catalog import build_error_catalog, export_error_catalog_artifacts
from services.registry import mcp_for_unity_tool


@mcp_for_unity_tool(
    unity_target=None,
    group=None,
    description=(
        "List or export the generated error-code and operational-contract catalog for this fork."
    ),
    annotations=ToolAnnotations(
        title="Manage Error Catalog",
        readOnlyHint=False,
    ),
)
async def manage_error_catalog(
    ctx: Context,
    action: Annotated[
        Literal["list", "export"],
        "Whether to inspect the catalog or export it to disk.",
    ],
    output_dir: Annotated[
        str | None,
        "Directory for exported artifacts. Defaults to Generated/ErrorCatalog in the repo root.",
    ] = None,
    format: Annotated[
        Literal["json", "markdown", "both"],
        "Export format when action='export'.",
    ] = "both",
) -> dict:
    if action == "list":
        return build_error_catalog()

    include_json = format in {"json", "both"}
    include_markdown = format in {"markdown", "both"}
    await ctx.info("Exporting error catalog artifacts")
    result = export_error_catalog_artifacts(
        output_dir,
        include_json=include_json,
        include_markdown=include_markdown,
    )
    return {
        "exported": True,
        "output_dir": result["output_dir"],
        "written_files": result["written_files"],
        "stable_code_count": result["stable_code_count"],
        "domain_count": result["domain_count"],
        "message": (
            f"Exported error catalog with {result['stable_code_count']} stable codes to {result['output_dir']}."
        ),
    }
