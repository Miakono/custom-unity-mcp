from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from core.telemetry import is_telemetry_enabled, record_tool_usage
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry
from services.tools.utils import coerce_bool


@mcp_for_unity_tool(
    description="Controls and queries the Unity editor's state and settings. Tip: pass booleans as true/false; if your client only sends strings, 'true'/'false' are accepted. Read-only actions: telemetry_status, telemetry_ping. Modifying actions: play, pause, stop, set_active_tool, add_tag, remove_tag, add_layer, remove_layer, quit_editor. WARNING: quit_editor requires explicit opt-in and will close the Unity Editor.",
    annotations=ToolAnnotations(
        title="Manage Editor",
        destructiveHint=True,
    ),
    capabilities={
        "requires_explicit_opt_in": True,
    },
)
async def manage_editor(
    ctx: Context,
    action: Annotated[Literal["telemetry_status", "telemetry_ping", "play", "pause", "stop", "set_active_tool", "add_tag", "remove_tag", "add_layer", "remove_layer", "quit_editor"], "Get and update the Unity Editor state."],
    wait_for_completion: Annotated[bool | str,
                                   "Optional. If True, waits for certain actions (accepts true/false or 'true'/'false')"] | None = None,
    tool_name: Annotated[str,
                         "Tool name when setting active tool"] | None = None,
    tag_name: Annotated[str,
                        "Tag name when adding and removing tags"] | None = None,
    layer_name: Annotated[str,
                          "Layer name when adding and removing layers"] | None = None,
    confirm_quit: Annotated[bool | str,
                           "Required confirmation flag for quit_editor action. Must be set to true to quit Unity."] | None = None,
) -> dict[str, Any]:
    gate = await maybe_run_tool_preflight(ctx, "manage_editor", action=action)
    if gate is not None:
        return gate.model_dump()

    # Get active instance from request state (injected by middleware)
    unity_instance = await get_unity_instance_from_context(ctx)

    wait_for_completion = coerce_bool(wait_for_completion)

    try:
        # Diagnostics: quick telemetry checks
        if action == "telemetry_status":
            return {"success": True, "telemetry_enabled": is_telemetry_enabled()}

        if action == "telemetry_ping":
            record_tool_usage("diagnostic_ping", True, 1.0, None)
            return {"success": True, "message": "telemetry ping queued"}
        # Prepare parameters, removing None values
        # Validate quit_editor confirmation
        if action == "quit_editor":
            confirm_val = coerce_bool(confirm_quit)
            if confirm_val is not True:
                return {
                    "success": False,
                    "message": "quit_editor requires confirm_quit=true. This is a safety measure to prevent accidental editor closure."
                }

        params = {
            "action": action,
            "waitForCompletion": wait_for_completion,
            "toolName": tool_name,
            "tagName": tag_name,
            "layerName": layer_name,
            "confirmQuit": confirm_quit,
        }
        params = {k: v for k, v in params.items() if v is not None}

        # Send command using centralized retry helper with instance routing
        response = await send_with_unity_instance(async_send_command_with_retry, unity_instance, "manage_editor", params)

        # Preserve structured failure data; unwrap success into a friendlier shape
        if isinstance(response, dict) and response.get("success"):
            return {"success": True, "message": response.get("message", "Editor operation successful."), "data": response.get("data")}
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}

    except Exception as e:
        return {"success": False, "message": f"Python error managing editor: {str(e)}"}
