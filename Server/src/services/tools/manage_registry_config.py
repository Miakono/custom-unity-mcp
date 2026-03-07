"""
Manage Unity Package Manager scoped registries.

Actions:
- list_scoped_registries: List all configured scoped registries
- add_registry: Add a new scoped registry
- remove_registry: Remove a scoped registry
- update_registry: Update registry configuration

Scoped registries allow using custom package registries alongside Unity's
official registry for distributing private or custom packages.
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
    group="project_config",
    description=(
        "Manage Unity Package Manager scoped registries. "
        "Read-only actions: list_scoped_registries. "
        "Modifying actions: add_registry, remove_registry, update_registry. "
        "Scoped registries allow using custom package registries for private or custom packages."
    ),
    annotations=ToolAnnotations(
        title="Manage Registry Configuration",
        destructiveHint=True,
    ),
)
async def manage_registry_config(
    ctx: Context,
    action: Annotated[
        Literal["list_scoped_registries", "add_registry", "remove_registry", "update_registry"],
        "Action to perform: list_scoped_registries, add_registry, remove_registry, update_registry"
    ],
    registry_name: Annotated[
        str | None,
        "Unique name/identifier for the registry (required for add/remove/update)"
    ] = None,
    registry_url: Annotated[
        str | None,
        "URL of the registry (required for add, optional for update)"
    ] = None,
    scopes: Annotated[
        list[str] | None,
        "List of package name scopes for this registry (e.g., ['com.mycompany', 'com.example'])"
    ] = None,
    new_name: Annotated[
        str | None,
        "New name for the registry (for update_registry action)"
    ] = None,
) -> dict[str, Any]:
    """
    Manage Unity Package Manager scoped registries.
    
    Scoped registries allow projects to use packages from custom npm registries
    alongside Unity's official package registry. This is useful for:
    - Private company packages
    - Custom tooling packages
    - Forks of official packages
    
    Examples:
    - List all registries: action="list_scoped_registries"
    - Add registry: action="add_registry", registry_name="MyRegistry",
      registry_url="https://npm.example.com", scopes=["com.mycompany"]
    - Remove registry: action="remove_registry", registry_name="MyRegistry"
    - Update registry: action="update_registry", registry_name="MyRegistry",
      new_name="NewName", scopes=["com.mycompany", "com.newscope"]
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "manage_registry_config", action=action)
    if gate is not None:
        return gate.model_dump()
    
    try:
        params: dict[str, Any] = {"action": action}
        
        if registry_name:
            params["registryName"] = registry_name
        if registry_url:
            params["registryUrl"] = registry_url
        if scopes:
            params["scopes"] = scopes
        if new_name:
            params["newName"] = new_name
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_registry_config",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Registry operation '{action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error managing registry configuration: {e!s}"}
