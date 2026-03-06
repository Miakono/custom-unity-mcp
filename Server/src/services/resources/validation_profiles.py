from typing import Any

from fastmcp import Context

from models import MCPResponse
from services.registry import mcp_for_unity_resource
from services.tools import get_unity_instance_from_context
from transport.legacy.unity_connection import async_send_command_with_retry
from transport.unity_transport import send_with_unity_instance


@mcp_for_unity_resource(
    uri="mcpforunity://validation/profiles",
    name="validation_profiles",
    description=(
        "Unity plugin validation and audit profiles derived from the local tool registry.\n\n"
        "URI: mcpforunity://validation/profiles"
    ),
)
async def get_validation_profiles(ctx: Context) -> dict[str, Any] | MCPResponse:
    unity_instance = await get_unity_instance_from_context(ctx)
    response = await send_with_unity_instance(
        async_send_command_with_retry,
        unity_instance,
        "get_validation_profiles",
        {},
    )
    if isinstance(response, dict):
        if not response.get("success", True):
            return MCPResponse(**response)
        return response.get("data") or {}
    return MCPResponse(success=False, error="invalid_validation_profiles", message=str(response))
