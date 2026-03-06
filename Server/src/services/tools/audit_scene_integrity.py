"""Read-only wrapper for the Unity-side scene integrity audit tool."""

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from transport.legacy.unity_connection import async_send_command_with_retry
from transport.unity_transport import send_with_unity_instance


@mcp_for_unity_tool(
    description="Audit loaded scenes for missing scripts, dirty state, inactive object counts, and issue samples.",
    group="testing",
    annotations=ToolAnnotations(
        title="Audit Scene Integrity",
        readOnlyHint=True,
    ),
)
async def audit_scene_integrity(
    ctx: Context,
    scope: Annotated[Literal["active", "loaded"], "Whether to inspect only the active scene or all loaded scenes."] = "loaded",
    include_inactive: Annotated[bool, "Whether to include inactive objects while traversing scene hierarchies."] = True,
    max_issues: Annotated[int, "Maximum issue samples to include in the response."] = 20,
) -> dict[str, Any]:
    unity_instance = await get_unity_instance_from_context(ctx)
    params = {
        "scope": scope,
        "includeInactive": bool(include_inactive),
        "maxIssues": max(1, min(100, int(max_issues))),
    }
    response = await send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "audit_scene_integrity",
        params,
    )
    return response if isinstance(response, dict) else {"success": False, "message": str(response)}
