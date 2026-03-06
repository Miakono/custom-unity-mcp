"""Read-only wrapper for the Unity-side prefab integrity audit tool."""

from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from transport.legacy.unity_connection import async_send_command_with_retry
from transport.unity_transport import send_with_unity_instance


@mcp_for_unity_tool(
    description="Audit prefab assets under a folder for missing scripts, variants, and load failures.",
    group="testing",
    annotations=ToolAnnotations(
        title="Audit Prefab Integrity",
        readOnlyHint=True,
    ),
)
async def audit_prefab_integrity(
    ctx: Context,
    root_folder: Annotated[str, "Folder to scan, usually under Assets/."] = "Assets",
    max_prefabs: Annotated[int, "Maximum number of prefab assets to scan."] = 200,
    max_issues: Annotated[int, "Maximum issue samples to include in the response."] = 20,
    include_variants: Annotated[bool, "Whether prefab variants should be included in the scan."] = True,
) -> dict[str, Any]:
    unity_instance = await get_unity_instance_from_context(ctx)
    params = {
        "rootFolder": root_folder,
        "maxPrefabs": max(1, min(1000, int(max_prefabs))),
        "maxIssues": max(1, min(100, int(max_issues))),
        "includeVariants": bool(include_variants),
    }
    response = await send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "audit_prefab_integrity",
        params,
    )
    return response if isinstance(response, dict) else {"success": False, "message": str(response)}
