from __future__ import annotations

"""
Manage Unity Asset Import Pipeline including reimport, reserialize, and import control.

Actions:
- get_import_queue_status: Check current import queue
- force_reimport: Force reimport of assets
- force_reserialize: Force reserialize assets
- pause_import: Pause asset importing
- resume_import: Resume asset importing

Safety:
- Mass reimport/reserialize are high-risk operations requiring explicit confirmation
- Pausing import may block other operations
- Operations are clearly classified and auditable
"""
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    group="pipeline_control",
    description=(
        "Manage Unity Asset Import Pipeline including reimport, reserialize, and import control. "
        "Read-only actions: get_import_queue_status. "
        "Modifying actions: force_reimport, force_reserialize (high-risk), pause_import, resume_import. "
        "Mass reimport/reserialize require explicit confirmation."
    ),
    annotations=ToolAnnotations(
        title="Manage Import Pipeline",
        destructiveHint=True,
    ),
)
async def manage_import_pipeline(
    ctx: Context,
    action: Annotated[
        Literal[
            "get_import_queue_status",
            "get_queue",
            "force_reimport",
            "force_reimport_by_type",
            "force_reserialize",
            "pause_import",
            "resume_import",
            "refresh",
            "stop_refresh",
            "get_importer_settings",
            "set_importer_settings",
        ],
        "Action to perform: get_import_queue_status (check queue), force_reimport (reimport assets), "
        "force_reserialize (reserialize assets - high-risk), pause_import (pause importing), "
        "resume_import (resume importing)"
    ],
    asset_paths: Annotated[
        list[str] | None,
        "List of asset paths to process (for force_reimport/force_reserialize). "
        "If empty or not provided, applies to all assets (high-risk)."
    ] = None,
    options: Annotated[
        dict[str, Any] | None,
        "Additional options for reimport/reserialize operations (e.g., {'importDependencies': true})"
    ] = None,
    asset_type: Annotated[
        str | None,
        "Optional asset type alias for targeted operations."
    ] = None,
    asset_path: Annotated[
        str | None,
        "Optional single asset path alias."
    ] = None,
    settings: Annotated[
        dict[str, Any] | None,
        "Importer settings payload for set_importer_settings."
    ] = None,
) -> dict[str, Any]:
    """
    Manage Unity Asset Import Pipeline.
    
    This tool provides control over the asset import pipeline:
    - Monitor import queue status
    - Force reimport of specific assets or entire project
    - Force reserialize assets (text/binary conversion)
    - Pause/resume background importing
    
    Use Cases:
    - Fix corrupted import data by reimporting
    - Convert asset serialization format
    - Control import overhead during intensive operations
    - Monitor long-running import processes
    
    Safety Notes:
    - force_reimport without asset_paths triggers full project reimport (very high-risk)
    - force_reserialize modifies asset files on disk
    - pause_import may block operations that depend on up-to-date imports
    - Reserialization changes file formats and may affect version control
    
    Options for force_reimport:
    - importDependencies: Also reimport dependent assets (default: true)
    - forceUpdate: Force update even if asset appears unchanged (default: true)
    
    Options for force_reserialize:
    - serializationMode: Target format - 'forceText' or 'forceBinary'
    
    Examples:
    - Check queue status: action="get_import_queue_status"
    - Reimport specific assets: action="force_reimport", asset_paths=["Assets/Textures/hero.png"]
    - Reimport folder: action="force_reimport", asset_paths=["Assets/Scripts"]
    - Full project reimport: action="force_reimport" (requires explicit confirmation)
    - Reserialize to text: action="force_reserialize", options={"serializationMode": "forceText"}
    - Pause importing: action="pause_import"
    - Resume importing: action="resume_import"
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "manage_import_pipeline", action=action)
    if gate is not None:
        return gate.model_dump()
    
    try:
        action_aliases = {
            "get_queue": "get_import_queue_status",
            "refresh": "force_reimport",
            "stop_refresh": "pause_import",
        }
        resolved_action = action_aliases.get(action, action)
        params: dict[str, Any] = {"action": resolved_action}
        
        effective_asset_paths = list(asset_paths or [])
        if asset_path:
            effective_asset_paths.append(asset_path)
        effective_options = dict(options or {})

        if action == "force_reimport_by_type" and asset_type:
            effective_options.setdefault("assetType", asset_type)
        elif asset_type:
            params["assetType"] = asset_type

        if effective_asset_paths:
            params["assetPaths"] = effective_asset_paths
        if asset_path:
            params["assetPath"] = asset_path
        if effective_options:
            params["options"] = effective_options
        if settings is not None:
            params["settings"] = settings
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_import_pipeline",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Import pipeline operation '{resolved_action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error managing import pipeline: {e!s}"}
