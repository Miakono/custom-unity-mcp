from __future__ import annotations

"""Tool for revealing/ping assets in the Unity Project window.

Provides focused asset revealing functionality to highlight and ping
assets in the Project browser, making them visible to the user.
"""

from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    group="navigation",
    description=(
        "Reveals/ping an asset in the Unity Project window. "
        "Highlights the asset and scrolls to make it visible. "
        "Supports revealing by asset path, GUID, or asset database ID. "
        "Use this to direct user attention to specific assets in the project."
    ),
    annotations=ToolAnnotations(
        title="Reveal Asset",
        destructiveHint=False,
    ),
)
async def reveal_asset(
    ctx: Context,
    asset_path: Annotated[
        str | None,
        "Asset path relative to project root (e.g., 'Assets/Scripts/MyScript.cs')."
    ] = None,
    guid: Annotated[
        str | None,
        "Asset GUID for revealing by unique identifier."
    ] = None,
    asset_guid: Annotated[
        str | None,
        "Alias for guid."
    ] = None,
    instance_id: Annotated[
        int | None,
        "Asset instance ID for revealing loaded assets."
    ] = None,
    select: Annotated[
        bool,
        "If true, also select the asset in addition to revealing it. Default true."
    ] = True,
    highlight: Annotated[
        bool,
        "If true, highlight/ping the asset in the Project window. Default true."
    ] = True,
) -> dict[str, Any]:
    """Reveal/ping an asset in the Unity Project window.

    Args:
        ctx: FastMCP context
        asset_path: Path to the asset (relative to project root)
        guid: Asset GUID
        instance_id: Asset instance ID
        select: Whether to select the asset
        highlight: Whether to highlight/ping the asset

    Returns:
        Reveal result with asset info and success status
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    # Preflight check
    gate = await maybe_run_tool_preflight(ctx, "reveal_asset", action="reveal")
    if gate is not None:
        return gate.model_dump()

    # Validate that at least one identifier is provided
    effective_guid = asset_guid or guid
    if asset_path is None and effective_guid is None and instance_id is None:
        return {
            "success": False,
            "message": "Must provide at least one of: asset_path, guid, or instance_id"
        }

    try:
        # Build target specification
        target: dict[str, Any] = {}
        if asset_path is not None:
            target["path"] = asset_path
        if effective_guid is not None:
            target["guid"] = effective_guid
        if instance_id is not None:
            target["instance_id"] = instance_id

        # Build parameters
        params: dict[str, Any] = {
            "navigationType": "reveal_in_project",
            "target": target,
            "select": select,
            "highlight": highlight,
        }

        # Send command to Unity
        response = await send_with_unity_instance(
            async_send_command_with_retry, unity_instance, "navigate_editor", params
        )

        # Process response
        if hasattr(response, 'model_dump'):
            result = response.model_dump()
        elif isinstance(response, dict):
            result = response
        else:
            return {
                "success": False,
                "message": f"Unexpected response type: {type(response).__name__}"
            }

        # Standardize response format
        return {
            "success": result.get("success", False),
            "message": result.get("message", "Asset reveal completed"),
            "data": result.get("data", {}),
            "navigation_id": result.get("navigation_id"),
            "action": "reveal_in_project",
            "target": target,
            "result": result.get("result", {}),
            "editor_state": result.get("editor_state", {}),
            "asset_info": result.get("asset_info", {}),
        }

    except TimeoutError:
        return {
            "success": False,
            "message": "Unity connection timeout. Please check if Unity is running and responsive."
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"Error revealing asset: {exc}"
        }
