"""
Runtime Bridge Tool - Foundation for Runtime/In-Game MCP support.

This module provides tools for interacting with Unity's Runtime/Play Mode context.
Runtime tools are CLEARLY tagged as runtime_only and NEVER appear in editor-only environments.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.runtime_guard import get_runtime_opt_in_gate
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry
from services.tools.utils import coerce_bool, parse_json_payload


# Runtime capability metadata flags
RUNTIME_CAPABILITY_FLAGS = {
    "runtime_only": True,
    "requires_runtime_context": True,
    "domain": "runtime",
}


@mcp_for_unity_tool(
    unity_target=None,
    description=(
        "Check if Runtime MCP is available and get runtime status. "
        "Returns connection state, active scene, play mode status, and available runtime tools. "
        "Use this to verify runtime context before executing runtime commands."
    ),
    annotations=ToolAnnotations(
        title="Get Runtime Status",
        readOnlyHint=True,
    ),
    group="core",
)
async def get_runtime_status(
    ctx: Context,
    include_capabilities: Annotated[
        bool | str,
        "Include detailed capability flags in response"
    ] | None = True,
) -> dict[str, Any]:
    """Check if Runtime MCP is available and return status information."""
    gate = get_runtime_opt_in_gate("get_runtime_status")
    if gate is not None:
        return gate

    unity_instance = await get_unity_instance_from_context(ctx)
    include_capabilities = coerce_bool(include_capabilities, default=True)

    try:
        params = {
            "action": "get_status",
            "include_capabilities": include_capabilities,
            "capability_flags": RUNTIME_CAPABILITY_FLAGS,
        }

        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "runtime_bridge",
            params,
        )

        if isinstance(response, dict):
            # Enrich response with server-side capability metadata
            if "data" in response and isinstance(response["data"], dict):
                response["data"]["_server_capabilities"] = RUNTIME_CAPABILITY_FLAGS
            return response
        
        return {
            "success": False,
            "message": f"Unexpected response type: {type(response).__name__}",
            "error": "invalid_response",
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get runtime status: {e!s}",
            "error": "runtime_status_failed",
        }


@mcp_for_unity_tool(
    unity_target=None,
    description=(
        "List tools available in runtime context. "
        "Returns runtime-only tools that can be executed in Play Mode or Built Games. "
        "These tools are separate from Editor-only tools and have different capabilities."
    ),
    annotations=ToolAnnotations(
        title="List Runtime Tools",
        readOnlyHint=True,
    ),
    group="core",
)
async def list_runtime_tools(
    ctx: Context,
    category: Annotated[
        Literal["all", "gameobject", "scene", "input", "physics", "debug"],
        "Filter tools by category"
    ] | None = "all",
    include_metadata: Annotated[
        bool | str,
        "Include full capability metadata for each tool"
    ] | None = True,
) -> dict[str, Any]:
    """List tools available in runtime context."""
    gate = get_runtime_opt_in_gate("list_runtime_tools")
    if gate is not None:
        return gate

    unity_instance = await get_unity_instance_from_context(ctx)
    include_metadata = coerce_bool(include_metadata, default=True)

    try:
        params = {
            "action": "list_tools",
            "category": category or "all",
            "include_metadata": include_metadata,
        }

        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "runtime_bridge",
            params,
        )

        if isinstance(response, dict):
            # Tag response as runtime domain
            if "data" in response and isinstance(response["data"], dict):
                response["data"]["_domain"] = "runtime"
                response["data"]["_runtime_only"] = True
            return response

        return {
            "success": False,
            "message": f"Unexpected response type: {type(response).__name__}",
            "error": "invalid_response",
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to list runtime tools: {e!s}",
            "error": "list_runtime_tools_failed",
        }


@mcp_for_unity_tool(
    unity_target=None,
    description=(
        "Execute a command in runtime context (Play Mode or Built Game). "
        "Commands are routed to the Runtime MCP Bridge in the active Unity instance. "
        "Use list_runtime_tools to discover available commands. "
        "REQUIRES active Play Mode or Built Game connection."
    ),
    annotations=ToolAnnotations(
        title="Execute Runtime Command",
        destructiveHint=True,
    ),
    group="core",
)
async def execute_runtime_command(
    ctx: Context,
    command: Annotated[
        str,
        "Runtime command to execute (e.g., 'runtime_gameobject_get', 'runtime_scene_get_active')"
    ],
    parameters: Annotated[
        dict[str, Any] | str,
        "Command parameters as object or JSON string"
    ] | None = None,
    timeout_seconds: Annotated[
        float,
        "Timeout for command execution in seconds (default: 30)"
    ] | None = 30.0,
    wait_for_completion: Annotated[
        bool | str,
        "If True, waits for command completion; if False, returns immediately with job ID"
    ] | None = True,
) -> dict[str, Any]:
    """
    Execute a command in runtime context.
    
    This routes commands to the Runtime MCP Bridge which operates in Play Mode
    or Built Games, separate from the Editor-only tool set.
    """
    gate = get_runtime_opt_in_gate("execute_runtime_command")
    if gate is not None:
        return gate

    unity_instance = await get_unity_instance_from_context(ctx)

    # Parse parameters if provided as string
    parsed_params: dict[str, Any] | None = None
    if parameters is not None:
        if isinstance(parameters, str):
            parsed = parse_json_payload(parameters)
            if isinstance(parsed, dict):
                parsed_params = parsed
            else:
                return {
                    "success": False,
                    "message": f"Parameters must be a JSON object, got: {type(parsed).__name__}",
                    "error": "invalid_parameters",
                }
        elif isinstance(parameters, dict):
            parsed_params = parameters
        else:
            return {
                "success": False,
                "message": f"Parameters must be a dict or JSON string, got: {type(parameters).__name__}",
                "error": "invalid_parameters",
            }

    wait_for_completion = coerce_bool(wait_for_completion, default=True)

    try:
        params = {
            "action": "execute_command",
            "command": command,
            "parameters": parsed_params or {},
            "timeout_seconds": timeout_seconds,
            "wait_for_completion": wait_for_completion,
            "_runtime_context": True,
            "_capability_flags": RUNTIME_CAPABILITY_FLAGS,
        }

        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "runtime_bridge",
            params,
        )

        if isinstance(response, dict):
            # Tag response with runtime domain info
            if "data" in response and isinstance(response["data"], dict):
                response["data"]["_runtime_executed"] = True
                response["data"]["_domain"] = "runtime"
            return response

        return {
            "success": False,
            "message": f"Unexpected response type: {type(response).__name__}",
            "error": "invalid_response",
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to execute runtime command: {e!s}",
            "error": "runtime_command_failed",
        }


@mcp_for_unity_tool(
    unity_target=None,
    description=(
        "Get runtime connection details including WebSocket endpoint and port. "
        "Runtime uses a separate connection from Editor MCP. "
        "Use this to establish direct runtime communication."
    ),
    annotations=ToolAnnotations(
        title="Get Runtime Connection Info",
        readOnlyHint=True,
    ),
    group="core",
)
async def get_runtime_connection_info(
    ctx: Context,
) -> dict[str, Any]:
    """Get runtime connection details including WebSocket endpoint."""
    gate = get_runtime_opt_in_gate("get_runtime_connection_info")
    if gate is not None:
        return gate

    unity_instance = await get_unity_instance_from_context(ctx)

    try:
        params = {
            "action": "get_connection_info",
        }

        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "runtime_bridge",
            params,
        )

        if isinstance(response, dict):
            # Add server-side capability metadata
            if "data" in response and isinstance(response["data"], dict):
                response["data"]["_runtime_only"] = True
                response["data"]["_separate_connection"] = True
                response["data"]["_editor_port"] = None  # Will be populated by Unity
                response["data"]["_runtime_port"] = None  # Will be populated by Unity
            return response

        return {
            "success": False,
            "message": f"Unexpected response type: {type(response).__name__}",
            "error": "invalid_response",
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get runtime connection info: {e!s}",
            "error": "runtime_connection_info_failed",
        }
