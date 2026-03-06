"""
Tool for runtime reflection and object introspection in Unity.

WARNING: This tool allows runtime examination and invocation of arbitrary types
and methods. It is DISABLED BY DEFAULT and must be explicitly enabled via the
reflection_enabled configuration setting.

High-risk operations (invoke_method, set_property, set_field, create_instance)
require explicit opt-in and are marked as dangerous.
"""

from typing import Annotated, Any, Literal

from fastmcp import Context

from core.config import config
from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from services.reflection_helper import (
    ReflectionHelper,
    ReflectionSecurityError,
    get_reflection_capability_status,
    PermissionLevel,
)
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


def _check_reflection_enabled() -> dict[str, Any] | None:
    """Check if reflection is enabled, returning an error response if not."""
    if not ReflectionHelper.is_reflection_enabled():
        return {
            "success": False,
            "message": (
                "Reflection is DISABLED. This is a security feature. "
                "To enable reflection, set 'reflection_enabled: true' in the server configuration. "
                "WARNING: Reflection allows runtime examination and invocation of arbitrary code. "
                "Only enable in trusted environments with caution."
            ),
            "data": {
                "capability": get_reflection_capability_status()
            }
        }
    return None


@mcp_for_unity_tool(
    description=(
        "Runtime reflection and object introspection for Unity. "
        "DISCOVER types, methods, properties, and fields. "
        "INSPECT and optionally MODIFY objects at runtime. "
        "WARNING: DISABLED BY DEFAULT - requires reflection_enabled config. "
        "High-risk operations (invoke_method, set_property, set_field, create_instance) "
        "allow arbitrary code execution - use with extreme caution."
    ),
    group="core",  # Core group but disabled by config
)
async def manage_reflection(
    ctx: Context,
    action: Annotated[
        Literal[
            "discover_methods",
            "discover_properties",
            "discover_fields",
            "get_type_info",
            "invoke_method",
            "get_property",
            "set_property",
            "get_field",
            "set_field",
            "create_instance",
            "find_objects",
            "get_capability_status",
            "clear_cache",
        ],
        "Reflection action to perform: "
        "discover_methods (list methods on type), "
        "discover_properties (list properties), "
        "discover_fields (list fields), "
        "get_type_info (detailed type info), "
        "invoke_method (execute method - HIGH RISK), "
        "get_property (read property value), "
        "set_property (write property - HIGH RISK), "
        "get_field (read field value), "
        "set_field (write field - HIGH RISK), "
        "create_instance (create object - HIGH RISK), "
        "find_objects (find scene objects by type), "
        "get_capability_status (check if reflection enabled), "
        "clear_cache (clear reflection cache)"
    ],
    target_type: Annotated[
        str | None,
        "Type name to reflect on (e.g., 'UnityEngine.Transform', 'MyScript')"
    ] = None,
    target_object: Annotated[
        str | int | None,
        "Target object instance ID or name (for instance operations). Use null for static members."
    ] = None,
    member_name: Annotated[
        str | None,
        "Method, property, or field name (for get/set/invoke operations)"
    ] = None,
    parameters: Annotated[
        dict[str, Any] | list[Any] | None,
        "Parameters for method invocation or constructor. Use dict for named params, list for positional."
    ] = None,
    value: Annotated[
        Any,
        "Value to set (for set_property/set_field actions)"
    ] = None,
    binding_flags: Annotated[
        Literal["public", "non_public", "all"],
        "Which members to include: public (default), non_public, or all"
    ] = "public",
    include_static: Annotated[
        bool,
        "Whether to include static members"
    ] = True,
    include_instance: Annotated[
        bool,
        "Whether to include instance members"
    ] = True,
    search_assemblies: Annotated[
        str | list[str] | None,
        "Specific assemblies to search (null = all loaded assemblies)"
    ] = None,
    scene_path: Annotated[
        str | None,
        "Scene path for find_objects (null = current scene)"
    ] = None,
    high_risk_confirmed: Annotated[
        bool,
        "MUST be true for high-risk operations (invoke_method, set_property, set_field, create_instance)"
    ] = False,
) -> dict[str, Any]:
    """
    Runtime reflection and object introspection for Unity.
    
    This tool allows examining and manipulating types and objects at runtime.
    It is DISABLED BY DEFAULT for security reasons.
    
    Actions:
    - discover_methods: List all methods on a type with signatures
    - discover_properties: List all properties on a type
    - discover_fields: List all fields on a type
    - get_type_info: Get detailed information about a type
    - invoke_method: Invoke a method on an object or type (HIGH RISK)
    - get_property: Get a property value
    - set_property: Set a property value (HIGH RISK)
    - get_field: Get a field value
    - set_field: Set a field value (HIGH RISK)
    - create_instance: Create an instance of a type (HIGH RISK)
    - find_objects: Find objects in the scene by type
    - get_capability_status: Check reflection capability status
    - clear_cache: Clear the reflection cache
    
    Security:
    - DISABLED BY DEFAULT - must enable reflection_enabled config
    - High-risk operations require high_risk_confirmed=true
    - All mutation operations are marked as dangerous
    
    Examples:
    - Discover methods: action="discover_methods", target_type="UnityEngine.Transform"
    - Get property: action="get_property", target_type="UnityEngine.Transform", target_object=12345, member_name="position"
    - Invoke method: action="invoke_method", target_type="UnityEngine.GameObject", target_object=12345, member_name="GetComponents", parameters={"type": "Collider"}, high_risk_confirmed=true
    - Create instance: action="create_instance", target_type="UnityEngine.Vector3", parameters={"x": 1, "y": 2, "z": 3}, high_risk_confirmed=true
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    # Check preflight gate
    gate = await maybe_run_tool_preflight(ctx, "manage_reflection")
    if gate is not None:
        return gate.model_dump()
    
    # Special case: capability status doesn't require enabled reflection
    if action == "get_capability_status":
        return {
            "success": True,
            "message": "Reflection capability status retrieved",
            "data": get_reflection_capability_status()
        }
    
    # Check if reflection is enabled
    if action != "clear_cache":
        error_response = _check_reflection_enabled()
        if error_response:
            return error_response
    
    # Validate high-risk operations
    high_risk_actions = {"invoke_method", "set_property", "set_field", "create_instance"}
    if action in high_risk_actions:
        if not high_risk_confirmed:
            return {
                "success": False,
                "message": (
                    f"Action '{action}' is HIGH RISK and can modify state or execute arbitrary code. "
                    "You must set high_risk_confirmed=true to proceed. "
                    "WARNING: This operation can have unintended side effects."
                ),
                "data": {
                    "action": action,
                    "requiresConfirmation": True,
                    "riskLevel": "high"
                }
            }
        
        # Log warning for high-risk operations
        ReflectionHelper.check_permission(action, PermissionLevel.INVOKE if action == "invoke_method" else PermissionLevel.WRITE)
    
    # Validate required parameters for specific actions
    if action in ("discover_methods", "discover_properties", "discover_fields", "get_type_info", "create_instance"):
        if not target_type:
            return {
                "success": False,
                "message": f"Action '{action}' requires target_type parameter"
            }
    
    if action in ("invoke_method", "get_property", "set_property", "get_field", "set_field"):
        if not target_type:
            return {
                "success": False,
                "message": f"Action '{action}' requires target_type parameter"
            }
        if not member_name:
            return {
                "success": False,
                "message": f"Action '{action}' requires member_name parameter"
            }
    
    if action in ("set_property", "set_field") and value is None:
        # Allow setting to null, but warn
        pass  # Value can be None (null)
    
    try:
        # Build parameters for Unity command
        params: dict[str, Any] = {
            "action": action,
        }
        
        if target_type:
            params["targetType"] = target_type
        if target_object is not None:
            params["targetObject"] = target_object
        if member_name:
            params["memberName"] = member_name
        if parameters is not None:
            params["parameters"] = parameters
        if value is not None:
            params["value"] = value
        
        params["bindingFlags"] = binding_flags
        params["includeStatic"] = include_static
        params["includeInstance"] = include_instance
        
        if search_assemblies:
            params["searchAssemblies"] = search_assemblies
        if scene_path:
            params["scenePath"] = scene_path
        
        # Add high-risk confirmation to params for Unity-side logging
        if action in high_risk_actions:
            params["highRiskConfirmed"] = high_risk_confirmed
        
        # Handle clear_cache locally (no need to go to Unity)
        if action == "clear_cache":
            ReflectionHelper.clear_cache()
            return {
                "success": True,
                "message": "Reflection cache cleared successfully",
                "data": {"cacheCleared": True}
            }
        
        # Send command to Unity
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_reflection",
            params,
        )
        
        # Process response
        if isinstance(response, dict):
            if response.get("success"):
                return {
                    "success": True,
                    "message": response.get("message", f"Reflection action '{action}' completed successfully"),
                    "data": response.get("data")
                }
            else:
                return {
                    "success": False,
                    "message": response.get("message", response.get("error", f"Reflection action '{action}' failed")),
                    "data": response.get("data")
                }
        
        return {
            "success": False,
            "message": f"Unexpected response type from Unity: {type(response).__name__}"
        }
        
    except ReflectionSecurityError as e:
        return {
            "success": False,
            "message": str(e),
            "data": {"securityError": True}
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error executing reflection action '{action}': {e!s}"
        }
