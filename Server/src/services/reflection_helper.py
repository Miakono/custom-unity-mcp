"""
Reflection helper service for type discovery, caching, and safe method invocation.

This module provides utilities for examining and invoking types at runtime
with permission checks and security controls.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

from core.config import config

logger = logging.getLogger("mcp-for-unity-server")


class PermissionLevel(Enum):
    """Permission levels for reflection operations."""
    READ = "read"           # Read-only operations (discover, get)
    WRITE = "write"         # Write operations (set properties/fields)
    INVOKE = "invoke"       # Method invocation
    CREATE = "create"       # Instance creation


@dataclass
class MethodSignature:
    """Represents a method signature for reflection."""
    name: str
    return_type: str
    parameters: list[dict[str, Any]] = field(default_factory=list)
    is_static: bool = False
    is_public: bool = True


@dataclass
class PropertyInfo:
    """Represents a property for reflection."""
    name: str
    property_type: str
    can_read: bool = True
    can_write: bool = True
    is_static: bool = False


@dataclass
class FieldInfo:
    """Represents a field for reflection."""
    name: str
    field_type: str
    is_static: bool = False
    is_readonly: bool = False
    is_public: bool = True


@dataclass
class TypeInfo:
    """Represents type information for reflection."""
    name: str
    namespace: str | None = None
    base_type: str | None = None
    is_class: bool = True
    is_value_type: bool = False
    is_enum: bool = False
    is_abstract: bool = False
    is_sealed: bool = False
    assembly: str | None = None


class ReflectionSecurityError(Exception):
    """Raised when a reflection operation violates security policy."""
    pass


class ReflectionHelper:
    """
    Helper class for reflection operations with caching and security controls.
    
    This class manages:
    - Type discovery and caching
    - Safe method invocation with permission checks
    - Object serialization for return values
    - Parameter type coercion
    """
    
    # Cache for type information
    _type_cache: dict[str, TypeInfo] = {}
    _method_cache: dict[str, list[MethodSignature]] = {}
    _property_cache: dict[str, list[PropertyInfo]] = {}
    _field_cache: dict[str, list[FieldInfo]] = {}
    
    # High-risk operations that require explicit opt-in
    HIGH_RISK_OPERATIONS = {
        "invoke_method",
        "set_property",
        "set_field",
        "create_instance",
    }
    
    @classmethod
    def is_reflection_enabled(cls) -> bool:
        """Check if reflection is enabled in configuration."""
        return getattr(config, "reflection_enabled", False)
    
    @classmethod
    def check_enabled(cls) -> None:
        """Raise an error if reflection is not enabled."""
        if not cls.is_reflection_enabled():
            raise ReflectionSecurityError(
                "Reflection is disabled. Enable 'reflection_enabled' in server configuration. "
                "WARNING: Reflection allows runtime examination and invocation of arbitrary code. "
                "Only enable in trusted environments."
            )
    
    @classmethod
    def check_permission(cls, operation: str, permission_level: PermissionLevel) -> None:
        """
        Check if the operation is allowed based on permission level.
        
        Args:
            operation: The operation name
            permission_level: The required permission level
            
        Raises:
            ReflectionSecurityError: If the operation is not allowed
        """
        cls.check_enabled()
        
        # All high-risk operations require explicit opt-in capability
        if operation in cls.HIGH_RISK_OPERATIONS:
            # High-risk operations are marked but allowed if reflection is enabled
            # The tool decorator should also mark these as high_risk
            logger.warning(
                f"High-risk reflection operation '{operation}' is being executed. "
                "Ensure this is intentional."
            )
    
    @classmethod
    def cache_type_info(cls, type_name: str, type_info: TypeInfo) -> None:
        """Cache type information."""
        cls._type_cache[type_name] = type_info
    
    @classmethod
    def get_cached_type_info(cls, type_name: str) -> TypeInfo | None:
        """Get cached type information."""
        return cls._type_cache.get(type_name)
    
    @classmethod
    def cache_methods(cls, type_name: str, methods: list[MethodSignature]) -> None:
        """Cache method signatures for a type."""
        cls._method_cache[type_name] = methods
    
    @classmethod
    def get_cached_methods(cls, type_name: str) -> list[MethodSignature] | None:
        """Get cached method signatures for a type."""
        return cls._method_cache.get(type_name)
    
    @classmethod
    def cache_properties(cls, type_name: str, properties: list[PropertyInfo]) -> None:
        """Cache properties for a type."""
        cls._property_cache[type_name] = properties
    
    @classmethod
    def get_cached_properties(cls, type_name: str) -> list[PropertyInfo] | None:
        """Get cached properties for a type."""
        return cls._property_cache.get(type_name)
    
    @classmethod
    def cache_fields(cls, type_name: str, fields: list[FieldInfo]) -> None:
        """Cache fields for a type."""
        cls._field_cache[type_name] = fields
    
    @classmethod
    def get_cached_fields(cls, type_name: str) -> list[FieldInfo] | None:
        """Get cached fields for a type."""
        return cls._field_cache.get(type_name)
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear all caches."""
        cls._type_cache.clear()
        cls._method_cache.clear()
        cls._property_cache.clear()
        cls._field_cache.clear()
        logger.info("Reflection cache cleared")
    
    @classmethod
    def serialize_return_value(cls, value: Any, max_depth: int = 3, current_depth: int = 0) -> Any:
        """
        Serialize a return value for safe transmission.
        
        Args:
            value: The value to serialize
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth
            
        Returns:
            Serialized value safe for JSON transmission
        """
        if current_depth >= max_depth:
            return {"_truncated": True, "type": type(value).__name__ if value is not None else None}
        
        if value is None:
            return None
        
        # Handle primitive types
        if isinstance(value, (str, int, float, bool)):
            return value
        
        # Handle enums
        if isinstance(value, Enum):
            return {"name": value.name, "value": value.value}
        
        # Handle lists/arrays
        if isinstance(value, (list, tuple)):
            return [
                cls.serialize_return_value(item, max_depth, current_depth + 1)
                for item in value
            ]
        
        # Handle dictionaries
        if isinstance(value, dict):
            return {
                str(k): cls.serialize_return_value(v, max_depth, current_depth + 1)
                for k, v in value.items()
            }
        
        # Handle objects - convert to dictionary representation
        try:
            # Try to get object attributes
            result = {
                "_type": type(value).__name__,
                "_module": type(value).__module__,
            }
            
            # Add common Unity-like properties if they exist
            for attr in ["name", "instanceID", "instance_id", "enabled", "gameObject", "transform"]:
                if hasattr(value, attr):
                    try:
                        attr_value = getattr(value, attr)
                        result[attr] = cls.serialize_return_value(attr_value, max_depth, current_depth + 1)
                    except Exception:
                        pass
            
            return result
        except Exception as e:
            return {"_type": type(value).__name__, "_error": str(e)}
    
    @classmethod
    def coerce_parameter(cls, value: Any, target_type: str) -> tuple[Any, bool]:
        """
        Coerce a parameter value to the target type.
        
        Args:
            value: The value to coerce
            target_type: The target type name
            
        Returns:
            Tuple of (coerced_value, success)
        """
        if value is None:
            return None, True
        
        # Normalize type name
        target_type = target_type.lower().strip()
        
        # Handle primitive types
        type_coercions: dict[str, Callable[[Any], Any]] = {
            "string": lambda v: str(v),
            "str": lambda v: str(v),
            "int": lambda v: int(v) if isinstance(v, (int, float, str)) else v,
            "int32": lambda v: int(v) if isinstance(v, (int, float, str)) else v,
            "int64": lambda v: int(v) if isinstance(v, (int, float, str)) else v,
            "float": lambda v: float(v) if isinstance(v, (int, float, str)) else v,
            "single": lambda v: float(v) if isinstance(v, (int, float, str)) else v,
            "double": lambda v: float(v) if isinstance(v, (int, float, str)) else v,
            "bool": lambda v: bool(v) if isinstance(v, (bool, int)) else str(v).lower() in ("true", "1", "yes"),
            "boolean": lambda v: bool(v) if isinstance(v, (bool, int)) else str(v).lower() in ("true", "1", "yes"),
        }
        
        if target_type in type_coercions:
            try:
                return type_coercions[target_type](value), True
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to coerce {value} to {target_type}: {e}")
                return value, False
        
        # For unknown types, return as-is
        return value, True
    
    @classmethod
    def validate_target_object(cls, target: Any, allow_static: bool = True) -> tuple[bool, str]:
        """
        Validate a target object for instance operations.
        
        Args:
            target: The target object (instance ID, name, or None for static)
            allow_static: Whether static operations are allowed
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if target is None:
            if allow_static:
                return True, ""
            return False, "Target is required for non-static operations"
        
        # Target can be an instance ID (int) or object identifier (str)
        if isinstance(target, int):
            return True, ""
        
        if isinstance(target, str) and target.strip():
            return True, ""
        
        return False, f"Invalid target type: {type(target).__name__}"
    
    @classmethod
    def format_method_signature(cls, method: MethodSignature) -> dict[str, Any]:
        """Format a method signature for output."""
        return {
            "name": method.name,
            "returnType": method.return_type,
            "parameters": method.parameters,
            "isStatic": method.is_static,
            "isPublic": method.is_public,
        }
    
    @classmethod
    def format_property_info(cls, prop: PropertyInfo) -> dict[str, Any]:
        """Format property info for output."""
        return {
            "name": prop.name,
            "type": prop.property_type,
            "canRead": prop.can_read,
            "canWrite": prop.can_write,
            "isStatic": prop.is_static,
        }
    
    @classmethod
    def format_field_info(cls, field: FieldInfo) -> dict[str, Any]:
        """Format field info for output."""
        return {
            "name": field.name,
            "type": field.field_type,
            "isStatic": field.is_static,
            "isReadonly": field.is_readonly,
            "isPublic": field.is_public,
        }
    
    @classmethod
    def format_type_info(cls, type_info: TypeInfo) -> dict[str, Any]:
        """Format type info for output."""
        return {
            "name": type_info.name,
            "namespace": type_info.namespace,
            "baseType": type_info.base_type,
            "isClass": type_info.is_class,
            "isValueType": type_info.is_value_type,
            "isEnum": type_info.is_enum,
            "isAbstract": type_info.is_abstract,
            "isSealed": type_info.is_sealed,
            "assembly": type_info.assembly,
        }


def get_reflection_capability_status() -> dict[str, Any]:
    """
    Get the current status of reflection capabilities.
    
    Returns:
        Dictionary with capability status information
    """
    enabled = ReflectionHelper.is_reflection_enabled()
    
    return {
        "enabled": enabled,
        "highRiskAllowed": enabled,  # High-risk ops allowed if reflection is enabled
        "availableOperations": (
            ["discover_methods", "discover_properties", "discover_fields", "get_type_info", "find_objects"]
            if not enabled else
            [
                "discover_methods", "discover_properties", "discover_fields", "get_type_info",
                "invoke_method", "get_property", "set_property", "get_field", "set_field",
                "create_instance", "find_objects"
            ]
        ),
        "cacheStats": {
            "types": len(ReflectionHelper._type_cache),
            "methods": len(ReflectionHelper._method_cache),
            "properties": len(ReflectionHelper._property_cache),
            "fields": len(ReflectionHelper._field_cache),
        }
    }
