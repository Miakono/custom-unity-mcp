"""
List and get information about Unity component types.

Actions:
- list_all: List all available component types
- search: Search for component types by name
- get_info: Get detailed information about a specific component type

Unity has hundreds of built-in component types, and projects can have
custom components (MonoBehaviour classes) as well.
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
        "List and get information about Unity component types. "
        "Read-only actions: list_all, search, get_info. "
        "Discover built-in components, search for specific types, and get detailed component information."
    ),
    annotations=ToolAnnotations(
        title="Get Component Types",
        readOnlyHint=True,
    ),
)
async def get_component_types(
    ctx: Context,
    action: Annotated[
        Literal["list_all", "search", "get_info"],
        "Action to perform: list_all, search, get_info"
    ],
    component_name: Annotated[
        str | None,
        "Full or partial component name (required for search and get_info)"
    ] = None,
    namespace: Annotated[
        str | None,
        "Filter by namespace (e.g., 'UnityEngine', 'UnityEngine.UI', 'MyNamespace')"
    ] = None,
    include_builtin: Annotated[
        bool,
        "Include Unity built-in components (default: true)"
    ] = True,
    include_custom: Annotated[
        bool,
        "Include custom project components (default: true)"
    ] = True,
    max_results: Annotated[
        int,
        "Maximum number of results (default: 100)"
    ] = 100,
    include_properties: Annotated[
        bool,
        "Include component properties/fields in output (default: true for get_info)"
    ] = True,
    include_methods: Annotated[
        bool,
        "Include public methods in output (default: false)"
    ] = False,
) -> dict[str, Any]:
    """
    List and get information about Unity component types.
    
    Unity components are the building blocks of GameObjects. This tool helps:
    - Discover what components are available
    - Find specific component types
    - Understand component properties and capabilities
    
    Common component categories:
    - Transform: Position, rotation, scale (on every GameObject)
    - Rendering: MeshRenderer, SpriteRenderer, CanvasRenderer
    - Physics: Rigidbody, Collider (BoxCollider, SphereCollider, etc.)
    - Audio: AudioSource, AudioListener
    - UI: Canvas, Image, Text, Button
    - Effects: ParticleSystem, TrailRenderer
    - Scripts: Custom MonoBehaviour components
    
    Examples:
    - List all components: action="list_all", max_results=50
    - Search for colliders: action="search", component_name="Collider"
    - Get component info: action="get_info", component_name="Rigidbody"
    - Find UI components: action="search", component_name="Button", namespace="UnityEngine.UI"
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    gate = await maybe_run_tool_preflight(ctx, "get_component_types", action=action)
    if gate is not None:
        return gate.model_dump()
    
    # Validate required parameters
    if action in ("search", "get_info") and not component_name:
        return {
            "success": False,
            "message": f"Action '{action}' requires component_name parameter."
        }
    
    try:
        params: dict[str, Any] = {
            "action": action,
            "includeBuiltin": include_builtin,
            "includeCustom": include_custom,
            "maxResults": max(max_results, 1),
            "includeProperties": include_properties,
            "includeMethods": include_methods,
        }
        
        if component_name:
            params["componentName"] = component_name
        if namespace:
            params["namespace"] = namespace
            
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "get_component_types",
            params,
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", f"Component types operation '{action}' successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Error getting component types: {e!s}"}
