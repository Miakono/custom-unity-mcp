"""
Defines the manage_addressables tool for Unity's Addressable Asset System.

This tool provides comprehensive management of Addressables including:
- Group management (create, delete, list)
- Asset management (add, remove, move, label)
- Build operations (build, clean build, platform-specific builds)
- Analysis and validation (dependencies, build reports, settings)
"""
import asyncio
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.utils import coerce_bool, coerce_int
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry
from services.tools.action_policy import maybe_run_tool_preflight


@mcp_for_unity_tool(
    description=(
        "Manages Unity Addressable Asset System.\n\n"
        "Read-only actions: analyze, get_groups, get_group_assets, get_labels, validate, get_settings.\n"
        "Build actions (high_risk): build, build_player, clean_build.\n"
        "Modifying actions (high_risk): create_group, delete_group, add_asset, remove_asset, "
        "move_asset, assign_label, remove_label.\n\n"
        "Use 'dry_run=true' for build operations to preview changes without executing.\n"
        "Supports multiple platforms: StandaloneWindows64, StandaloneOSX, StandaloneLinux64, "
        "iOS, Android, WebGL, PS5, XboxSeriesX."
    ),
    annotations=ToolAnnotations(
        title="Manage Addressables",
        destructiveHint=True,
    ),
)
async def manage_addressables(
    ctx: Context,
    action: Annotated[
        Literal[
            "analyze",
            "build",
            "build_player",
            "clean_build",
            "get_groups",
            "create_group",
            "delete_group",
            "get_group_assets",
            "add_asset",
            "remove_asset",
            "move_asset",
            "assign_label",
            "remove_label",
            "get_labels",
            "validate",
            "get_settings",
        ],
        "Addressables operation to perform."
    ],
    # Group parameters
    group_name: Annotated[str, "Name of the Addressable group (for group-related actions)."] | None = None,
    # Asset parameters
    asset_path: Annotated[str, "Asset path (e.g., 'Assets/Prefabs/MyPrefab.prefab')."] | None = None,
    address: Annotated[str, "Custom address for the asset (optional, defaults to asset path)."] | None = None,
    labels: Annotated[list[str], "Labels to assign to the asset."] | None = None,
    # Build parameters
    platform: Annotated[
        str,
        "Target platform for build (e.g., 'StandaloneWindows64', 'Android', 'iOS'). "
        "Defaults to current build target."
    ] | None = None,
    dry_run: Annotated[bool, "If true, simulate build without making changes."] = False,
    clean: Annotated[bool, "If true, clean build cache before building."] = False,
    # Move parameters
    target_group: Annotated[str, "Target group name for move operations."] | None = None,
    # Analysis parameters
    report_path: Annotated[str, "Path to build report JSON for analysis."] | None = None,
    # Settings parameters
    settings_path: Annotated[str, "Path to Addressables settings (auto-detected if not provided)."] | None = None,
    # Pagination
    page_size: Annotated[int | str, "Page size for pagination."] | None = None,
    page_number: Annotated[int | str, "Page number for pagination (1-based)."] | None = None,
) -> dict[str, Any]:
    """
    Manage Unity Addressable Asset System.
    
    Provides comprehensive control over Addressables including groups, assets,
    labels, builds, and analysis.
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    # Run preflight check for mutating operations
    gate = await maybe_run_tool_preflight(ctx, "manage_addressables", action=action)
    if gate is not None:
        return gate.model_dump()

    # Normalize pagination parameters
    page_size_int = coerce_int(page_size, default=None)
    page_number_int = coerce_int(page_number, default=None)

    # Prepare parameters for Unity
    params: dict[str, Any] = {"action": action}

    # Add optional parameters
    if group_name is not None:
        params["groupName"] = group_name
    if asset_path is not None:
        params["assetPath"] = asset_path
    if address is not None:
        params["address"] = address
    if labels is not None:
        params["labels"] = labels
    if platform is not None:
        params["platform"] = platform
    if dry_run:
        params["dryRun"] = True
    if clean:
        params["clean"] = True
    if target_group is not None:
        params["targetGroup"] = target_group
    if report_path is not None:
        params["reportPath"] = report_path
    if settings_path is not None:
        params["settingsPath"] = settings_path
    if page_size_int is not None:
        params["pageSize"] = page_size_int
    if page_number_int is not None:
        params["pageNumber"] = page_number_int

    try:
        # Send command to Unity
        result = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_addressables",
            params
        )

        # Return result
        if isinstance(result, dict):
            return result
        return {"success": False, "message": str(result)}

    except Exception as e:
        return {"success": False, "message": f"Error managing Addressables: {str(e)}"}
