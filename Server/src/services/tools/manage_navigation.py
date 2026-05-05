"""
NavMesh management: bake / clear / status / agent path queries / surface listing.

Supports both legacy NavMeshBuilder and the newer com.unity.ai.navigation
NavMeshSurface component (auto-detected via reflection on the Unity side).
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from services.tools.utils import coerce_bool, coerce_float, coerce_int
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    group="navigation",
    description=(
        "Manage scene NavMesh: bake/clear navmesh data, query bake status, sample positions, "
        "calculate agent paths, and list NavMeshSurface components. Read actions: get_status, "
        "calculate_path, sample_position, list_surfaces. Mutating: bake, clear. Auto-detects "
        "the modern com.unity.ai.navigation package and prefers NavMeshSurface bakes when "
        "surfaces exist; falls back to legacy NavMeshBuilder otherwise."
    ),
    annotations=ToolAnnotations(
        title="Manage Navigation (NavMesh)",
        destructiveHint=True,
    ),
)
async def manage_navigation(
    ctx: Context,
    action: Annotated[
        Literal[
            "get_status",
            "bake",
            "clear",
            "calculate_path",
            "sample_position",
            "list_surfaces",
        ],
        "Action. bake/clear are mutating (long-running for bake)."
    ],
    mode: Annotated[
        Literal["auto", "surfaces", "legacy"] | None,
        "Bake mode for action='bake'. 'auto' (default) prefers NavMeshSurface if any are in the "
        "scene; 'surfaces' forces NavMeshSurface bake; 'legacy' forces the old NavMeshBuilder path."
    ] = None,
    bake_async: Annotated[
        bool | str | None,
        "For mode='legacy', use BuildNavMeshAsync instead of synchronous BuildNavMesh."
    ] = None,
    start: Annotated[
        str | None,
        "Start position 'x,y,z' for calculate_path."
    ] = None,
    end: Annotated[
        str | None,
        "End position 'x,y,z' for calculate_path."
    ] = None,
    position: Annotated[
        str | None,
        "Position 'x,y,z' for sample_position."
    ] = None,
    max_distance: Annotated[
        float | str | None,
        "Max sample distance for sample_position (default 5)."
    ] = None,
    area_mask: Annotated[
        int | str | None,
        "Area mask bitfield for path/sample queries (default NavMesh.AllAreas)."
    ] = None,
) -> dict[str, Any]:
    """Drive NavMesh operations through the Unity Editor."""
    unity_instance = await get_unity_instance_from_context(ctx)

    gate = await maybe_run_tool_preflight(ctx, "manage_navigation", action=action)
    if gate is not None:
        return gate.model_dump()

    params: dict[str, Any] = {"action": action}
    if mode is not None:
        params["mode"] = mode
    if bake_async is not None:
        params["async"] = coerce_bool(bake_async, default=False)
    if start is not None:
        params["start"] = start
    if end is not None:
        params["end"] = end
    if position is not None:
        params["position"] = position
    if max_distance is not None:
        params["maxDistance"] = coerce_float(max_distance, default=5.0)
    if area_mask is not None:
        params["areaMask"] = coerce_int(area_mask, default=-1)

    try:
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_navigation",
            params,
        )
        if isinstance(response, dict):
            return response
        return {"success": False, "message": str(response)}
    except Exception as e:
        return {"success": False, "message": f"manage_navigation {action} error: {e!s}"}
