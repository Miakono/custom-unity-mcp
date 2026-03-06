"""Server-local tool for listing and exporting the fork error catalog."""

from typing import Annotated, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.error_catalog import (
    build_error_catalog,
    export_error_catalog_artifacts,
    get_error_code_info,
    list_error_codes_for_surface,
)
from services.registry import mcp_for_unity_tool


@mcp_for_unity_tool(
    unity_target=None,
    group=None,
    description=(
        "List, query, or export the generated error-code and operational-contract catalog for this fork. "
        "Actions: list (full catalog), get_code (specific error details), get_for_surface (codes by tool), "
        "export (save to disk)."
    ),
    annotations=ToolAnnotations(
        title="Manage Error Catalog",
        readOnlyHint=True,
    ),
)
async def manage_error_catalog(
    ctx: Context,
    action: Annotated[
        Literal["list", "export", "get_code", "get_for_surface"],
        "Whether to list the catalog, export it, or query specific error information.",
    ],
    output_dir: Annotated[
        str | None,
        "Directory for exported artifacts. Defaults to Generated/ErrorCatalog in the repo root.",
    ] = None,
    format: Annotated[
        Literal["json", "markdown", "both"],
        "Export format when action='export'.",
    ] = "both",
    code: Annotated[
        str | None,
        "Error code to look up when action='get_code'.",
    ] = None,
    surface: Annotated[
        str | None,
        "Tool/surface name to filter by when action='get_for_surface'.",
    ] = None,
) -> dict:
    if action == "list":
        return build_error_catalog()

    if action == "get_code":
        if not code:
            return {
                "success": False,
                "error": "code parameter is required for get_code action",
            }
        info = get_error_code_info(code)
        if info is None:
            return {
                "success": False,
                "error": f"Error code '{code}' not found in catalog",
                "available_codes": [
                    entry["code"]
                    for domain in build_error_catalog()["domains"]
                    for entry in domain["entries"]
                ],
            }
        return {"success": True, "data": info}

    if action == "get_for_surface":
        if not surface:
            return {
                "success": False,
                "error": "surface parameter is required for get_for_surface action",
            }
        codes = list_error_codes_for_surface(surface)
        return {
            "success": True,
            "data": {
                "surface": surface,
                "error_count": len(codes),
                "codes": codes,
            },
        }

    # action == "export"
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
