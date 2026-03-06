using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.Reflection
{
    /// <summary>
    /// Handles object inspection and member discovery for reflection operations.
    /// Provides methods to discover methods, properties, and fields on types.
    /// </summary>
    public static class ObjectInspector
    {
        #region Type Discovery

        /// <summary>
        /// Gets detailed type information for a given type.
        /// </summary>
        public static object GetTypeInfo(Type type)
        {
            if (type == null)
                return new ErrorResponse("Type is null");

            return new
            {
                success = true,
                message = $"Type information for '{type.FullName}'",
                data = new
                {
                    name = type.Name,
                    fullName = type.FullName,
                    namespace_name = type.Namespace,
                    baseType = type.BaseType?.FullName,
                    isClass = type.IsClass,
                    isValueType = type.IsValueType,
                    isEnum = type.IsEnum,
                    isAbstract = type.IsAbstract,
                    isSealed = type.IsSealed,
                    isInterface = type.IsInterface,
                    isArray = type.IsArray,
                    isGenericType = type.IsGenericType,
                    genericTypeDefinition = type.IsGenericType ? type.GetGenericTypeDefinition().FullName : null,
                    assembly = type.Assembly?.GetName()?.Name,
                    attributes = type.GetCustomAttributesData()
                        .Select(a => a.AttributeType.Name)
                        .ToList()
                }
            };
        }

        /// <summary>
        /// Discovers methods on a type with detailed signature information.
        /// </summary>
        public static object DiscoverMethods(Type type, BindingFlags bindingFlags, bool includeStatic, bool includeInstance)
        {
            if (type == null)
                return new ErrorResponse("Type is null");

            try
            {
                var flags = BuildBindingFlags(bindingFlags, includeStatic, includeInstance);
                var methods = type.GetMethods(flags)
                    .Where(m => !m.IsSpecialName) // Exclude property accessors
                    .Select(m => new
                    {
                        name = m.Name,
                        returnType = m.ReturnType.FullName,
                        parameters = m.GetParameters().Select(p => new
                        {
                            name = p.Name,
                            type = p.ParameterType.FullName,
                            isOptional = p.IsOptional,
                            defaultValue = p.IsOptional ? p.DefaultValue : null,
                            isOut = p.IsOut,
                            isRef = p.ParameterType.IsByRef && !p.IsOut
                        }).ToList(),
                        isStatic = m.IsStatic,
                        isPublic = m.IsPublic,
                        isVirtual = m.IsVirtual,
                        isAbstract = m.IsAbstract,
                        declaringType = m.DeclaringType?.FullName,
                        attributes = m.GetCustomAttributesData()
                            .Select(a => a.AttributeType.Name)
                            .ToList()
                    })
                    .OrderBy(m => m.name)
                    .ToList();

                return new
                {
                    success = true,
                    message = $"Discovered {methods.Count} methods on '{type.FullName}'",
                    data = new
                    {
                        typeName = type.FullName,
                        bindingFlags = bindingFlags.ToString(),
                        methodCount = methods.Count,
                        methods = methods
                    }
                };
            }
            catch (Exception ex)
            {
                McpLog.Error($"[ObjectInspector] Failed to discover methods for {type.FullName}: {ex.Message}");
                return new ErrorResponse($"Failed to discover methods: {ex.Message}");
            }
        }

        /// <summary>
        /// Discovers properties on a type.
        /// </summary>
        public static object DiscoverProperties(Type type, BindingFlags bindingFlags, bool includeStatic, bool includeInstance)
        {
            if (type == null)
                return new ErrorResponse("Type is null");

            try
            {
                var flags = BuildBindingFlags(bindingFlags, includeStatic, includeInstance);
                var properties = type.GetProperties(flags)
                    .Select(p => new
                    {
                        name = p.Name,
                        propertyType = p.PropertyType.FullName,
                        canRead = p.CanRead,
                        canWrite = p.CanWrite,
                        isStatic = (p.GetGetMethod(true) ?? p.GetSetMethod(true))?.IsStatic ?? false,
                        declaringType = p.DeclaringType?.FullName,
                        indexParameters = p.GetIndexParameters().Select(ip => new
                        {
                            name = ip.Name,
                            type = ip.ParameterType.FullName
                        }).ToList(),
                        attributes = p.GetCustomAttributesData()
                            .Select(a => a.AttributeType.Name)
                            .ToList()
                    })
                    .OrderBy(p => p.name)
                    .ToList();

                return new
                {
                    success = true,
                    message = $"Discovered {properties.Count} properties on '{type.FullName}'",
                    data = new
                    {
                        typeName = type.FullName,
                        bindingFlags = bindingFlags.ToString(),
                        propertyCount = properties.Count,
                        properties = properties
                    }
                };
            }
            catch (Exception ex)
            {
                McpLog.Error($"[ObjectInspector] Failed to discover properties for {type.FullName}: {ex.Message}");
                return new ErrorResponse($"Failed to discover properties: {ex.Message}");
            }
        }

        /// <summary>
        /// Discovers fields on a type.
        /// </summary>
        public static object DiscoverFields(Type type, BindingFlags bindingFlags, bool includeStatic, bool includeInstance)
        {
            if (type == null)
                return new ErrorResponse("Type is null");

            try
            {
                var flags = BuildBindingFlags(bindingFlags, includeStatic, includeInstance);
                var fields = type.GetFields(flags)
                    .Select(f => new
                    {
                        name = f.Name,
                        fieldType = f.FieldType.FullName,
                        isStatic = f.IsStatic,
                        isReadonly = f.IsInitOnly,
                        isPublic = f.IsPublic,
                        isPrivate = f.IsPrivate,
                        isProtected = f.IsFamily,
                        declaringType = f.DeclaringType?.FullName,
                        attributes = f.GetCustomAttributesData()
                            .Select(a => a.AttributeType.Name)
                            .ToList()
                    })
                    .OrderBy(f => f.name)
                    .ToList();

                return new
                {
                    success = true,
                    message = $"Discovered {fields.Count} fields on '{type.FullName}'",
                    data = new
                    {
                        typeName = type.FullName,
                        bindingFlags = bindingFlags.ToString(),
                        fieldCount = fields.Count,
                        fields = fields
                    }
                };
            }
            catch (Exception ex)
            {
                McpLog.Error($"[ObjectInspector] Failed to discover fields for {type.FullName}: {ex.Message}");
                return new ErrorResponse($"Failed to discover fields: {ex.Message}");
            }
        }

        #endregion

        #region Member Access

        /// <summary>
        /// Gets a property value from an object or type.
        /// </summary>
        public static object GetProperty(Type type, object target, string propertyName)
        {
            if (type == null)
                return new ErrorResponse("Type is null");

            if (string.IsNullOrEmpty(propertyName))
                return new ErrorResponse("Property name is required");

            try
            {
                var property = type.GetProperty(propertyName, 
                    BindingFlags.Public | BindingFlags.NonPublic | 
                    BindingFlags.Static | BindingFlags.Instance);

                if (property == null)
                    return new ErrorResponse($"Property '{propertyName}' not found on type '{type.FullName}'");

                if (!property.CanRead)
                    return new ErrorResponse($"Property '{propertyName}' does not have a getter");

                var value = property.GetValue(target);
                var serializedValue = SerializeValue(value);

                return new
                {
                    success = true,
                    message = $"Got property '{propertyName}' value",
                    data = new
                    {
                        propertyName = propertyName,
                        propertyType = property.PropertyType.FullName,
                        value = serializedValue,
                        isStatic = target == null,
                        declaringType = property.DeclaringType?.FullName
                    }
                };
            }
            catch (TargetInvocationException ex) when (ex.InnerException != null)
            {
                McpLog.Error($"[ObjectInspector] Failed to get property {propertyName}: {ex.InnerException.Message}");
                return new ErrorResponse($"Failed to get property: {ex.InnerException.Message}");
            }
            catch (Exception ex)
            {
                McpLog.Error($"[ObjectInspector] Failed to get property {propertyName}: {ex.Message}");
                return new ErrorResponse($"Failed to get property: {ex.Message}");
            }
        }

        /// <summary>
        /// Sets a property value on an object or type.
        /// </summary>
        public static object SetProperty(Type type, object target, string propertyName, JToken valueToken)
        {
            if (type == null)
                return new ErrorResponse("Type is null");

            if (string.IsNullOrEmpty(propertyName))
                return new ErrorResponse("Property name is required");

            try
            {
                var property = type.GetProperty(propertyName, 
                    BindingFlags.Public | BindingFlags.NonPublic | 
                    BindingFlags.Static | BindingFlags.Instance);

                if (property == null)
                    return new ErrorResponse($"Property '{propertyName}' not found on type '{type.FullName}'");

                if (!property.CanWrite)
                    return new ErrorResponse($"Property '{propertyName}' does not have a setter or is read-only");

                object value = CoerceValue(valueToken, property.PropertyType);
                property.SetValue(target, value);

                return new
                {
                    success = true,
                    message = $"Set property '{propertyName}' value",
                    data = new
                    {
                        propertyName = propertyName,
                        propertyType = property.PropertyType.FullName,
                        newValue = SerializeValue(value),
                        isStatic = target == null,
                        declaringType = property.DeclaringType?.FullName
                    }
                };
            }
            catch (TargetInvocationException ex) when (ex.InnerException != null)
            {
                McpLog.Error($"[ObjectInspector] Failed to set property {propertyName}: {ex.InnerException.Message}");
                return new ErrorResponse($"Failed to set property: {ex.InnerException.Message}");
            }
            catch (Exception ex)
            {
                McpLog.Error($"[ObjectInspector] Failed to set property {propertyName}: {ex.Message}");
                return new ErrorResponse($"Failed to set property: {ex.Message}");
            }
        }

        /// <summary>
        /// Gets a field value from an object or type.
        /// </summary>
        public static object GetField(Type type, object target, string fieldName)
        {
            if (type == null)
                return new ErrorResponse("Type is null");

            if (string.IsNullOrEmpty(fieldName))
                return new ErrorResponse("Field name is required");

            try
            {
                var field = type.GetField(fieldName, 
                    BindingFlags.Public | BindingFlags.NonPublic | 
                    BindingFlags.Static | BindingFlags.Instance);

                if (field == null)
                    return new ErrorResponse($"Field '{fieldName}' not found on type '{type.FullName}'");

                var value = field.GetValue(target);
                var serializedValue = SerializeValue(value);

                return new
                {
                    success = true,
                    message = $"Got field '{fieldName}' value",
                    data = new
                    {
                        fieldName = fieldName,
                        fieldType = field.FieldType.FullName,
                        value = serializedValue,
                        isStatic = field.IsStatic,
                        isReadonly = field.IsInitOnly,
                        declaringType = field.DeclaringType?.FullName
                    }
                };
            }
            catch (Exception ex)
            {
                McpLog.Error($"[ObjectInspector] Failed to get field {fieldName}: {ex.Message}");
                return new ErrorResponse($"Failed to get field: {ex.Message}");
            }
        }

        /// <summary>
        /// Sets a field value on an object or type.
        /// </summary>
        public static object SetField(Type type, object target, string fieldName, JToken valueToken)
        {
            if (type == null)
                return new ErrorResponse("Type is null");

            if (string.IsNullOrEmpty(fieldName))
                return new ErrorResponse("Field name is required");

            try
            {
                var field = type.GetField(fieldName, 
                    BindingFlags.Public | BindingFlags.NonPublic | 
                    BindingFlags.Static | BindingFlags.Instance);

                if (field == null)
                    return new ErrorResponse($"Field '{fieldName}' not found on type '{type.FullName}'");

                if (field.IsInitOnly)
                    return new ErrorResponse($"Field '{fieldName}' is read-only (init-only)");

                object value = CoerceValue(valueToken, field.FieldType);
                field.SetValue(target, value);

                return new
                {
                    success = true,
                    message = $"Set field '{fieldName}' value",
                    data = new
                    {
                        fieldName = fieldName,
                        fieldType = field.FieldType.FullName,
                        newValue = SerializeValue(value),
                        isStatic = field.IsStatic,
                        declaringType = field.DeclaringType?.FullName
                    }
                };
            }
            catch (Exception ex)
            {
                McpLog.Error($"[ObjectInspector] Failed to set field {fieldName}: {ex.Message}");
                return new ErrorResponse($"Failed to set field: {ex.Message}");
            }
        }

        #endregion

        #region Helper Methods

        /// <summary>
        /// Builds binding flags based on parameters.
        /// </summary>
        private static BindingFlags BuildBindingFlags(BindingFlags bindingFlags, bool includeStatic, bool includeInstance)
        {
            var flags = BindingFlags.Public;

            if (bindingFlags == BindingFlags.NonPublic || bindingFlags == (BindingFlags.Public | BindingFlags.NonPublic))
                flags |= BindingFlags.NonPublic;

            if (includeStatic)
                flags |= BindingFlags.Static;

            if (includeInstance)
                flags |= BindingFlags.Instance;

            return flags;
        }

        /// <summary>
        /// Coerces a JSON value to the target type.
        /// </summary>
        private static object CoerceValue(JToken token, Type targetType)
        {
            if (token == null || token.Type == JTokenType.Null)
                return null;

            // Handle nullable types
            var underlyingType = Nullable.GetUnderlyingType(targetType);
            if (underlyingType != null)
                targetType = underlyingType;

            // Handle enums
            if (targetType.IsEnum)
            {
                if (token.Type == JTokenType.String)
                    return Enum.Parse(targetType, token.Value<string>(), true);
                return Enum.ToObject(targetType, token.Value<int>());
            }

            // Handle primitives
            if (targetType == typeof(string))
                return token.Value<string>();
            if (targetType == typeof(int) || targetType == typeof(Int32))
                return token.Value<int>();
            if (targetType == typeof(float) || targetType == typeof(Single))
                return token.Value<float>();
            if (targetType == typeof(double) || targetType == typeof(Double))
                return token.Value<double>();
            if (targetType == typeof(bool) || targetType == typeof(Boolean))
                return token.Value<bool>();
            if (targetType == typeof(long) || targetType == typeof(Int64))
                return token.Value<long>();

            // Handle Unity types - convert from arrays/objects
            if (targetType == typeof(Vector2))
            {
                if (token.Type == JTokenType.Array)
                    return new Vector2(token[0].Value<float>(), token[1].Value<float>());
                return new Vector2(token["x"]?.Value<float>() ?? 0, token["y"]?.Value<float>() ?? 0);
            }
            if (targetType == typeof(Vector3))
            {
                if (token.Type == JTokenType.Array)
                    return new Vector3(token[0].Value<float>(), token[1].Value<float>(), token[2].Value<float>());
                return new Vector3(
                    token["x"]?.Value<float>() ?? 0, 
                    token["y"]?.Value<float>() ?? 0, 
                    token["z"]?.Value<float>() ?? 0);
            }
            if (targetType == typeof(Vector4))
            {
                if (token.Type == JTokenType.Array)
                    return new Vector4(token[0].Value<float>(), token[1].Value<float>(), token[2].Value<float>(), token[3].Value<float>());
                return new Vector4(
                    token["x"]?.Value<float>() ?? 0, 
                    token["y"]?.Value<float>() ?? 0, 
                    token["z"]?.Value<float>() ?? 0,
                    token["w"]?.Value<float>() ?? 0);
            }
            if (targetType == typeof(Quaternion))
            {
                if (token.Type == JTokenType.Array)
                    return new Quaternion(token[0].Value<float>(), token[1].Value<float>(), token[2].Value<float>(), token[3].Value<float>());
                return new Quaternion(
                    token["x"]?.Value<float>() ?? 0, 
                    token["y"]?.Value<float>() ?? 0, 
                    token["z"]?.Value<float>() ?? 0,
                    token["w"]?.Value<float>() ?? 1);
            }
            if (targetType == typeof(Color))
            {
                if (token.Type == JTokenType.Array)
                    return new Color(token[0].Value<float>(), token[1].Value<float>(), token[2].Value<float>(), token.ElementAtOrDefault(3)?.Value<float>() ?? 1);
                return new Color(
                    token["r"]?.Value<float>() ?? 0, 
                    token["g"]?.Value<float>() ?? 0, 
                    token["b"]?.Value<float>() ?? 0,
                    token["a"]?.Value<float>() ?? 1);
            }

            // Fallback: use JToken.ToObject
            return token.ToObject(targetType);
        }

        /// <summary>
        /// Serializes a value for safe JSON transmission.
        /// </summary>
        private static object SerializeValue(object value, int maxDepth = 3, int currentDepth = 0)
        {
            if (currentDepth >= maxDepth)
                return new { _truncated = true, type = value?.GetType()?.Name };

            if (value == null)
                return null;

            var type = value.GetType();

            // Handle primitives
            if (type.IsPrimitive || type == typeof(string) || type == typeof(decimal))
                return value;

            // Handle enums
            if (type.IsEnum)
                return new { name = value.ToString(), value = (int)value, type = type.Name };

            // Handle Unity Vector types
            if (value is Vector2 v2)
                return new { x = v2.x, y = v2.y, type = "Vector2" };
            if (value is Vector3 v3)
                return new { x = v3.x, y = v3.y, z = v3.z, type = "Vector3" };
            if (value is Vector4 v4)
                return new { x = v4.x, y = v4.y, z = v4.z, w = v4.w, type = "Vector4" };
            if (value is Quaternion q)
                return new { x = q.x, y = q.y, z = q.z, w = q.w, type = "Quaternion" };
            if (value is Color c)
                return new { r = c.r, g = c.g, b = c.b, a = c.a, type = "Color" };
            if (value is Rect r)
                return new { x = r.x, y = r.y, width = r.width, height = r.height, type = "Rect" };
            if (value is Bounds b)
                return new { center = SerializeValue(b.center, maxDepth, currentDepth + 1), extents = SerializeValue(b.extents, maxDepth, currentDepth + 1), type = "Bounds" };

            // Handle UnityObject references
            if (value is UnityEngine.Object unityObj)
            {
                return new
                {
                    _type = type.Name,
                    _reference = true,
                    instanceID = unityObj.GetInstanceID(),
                    name = unityObj.name,
                    type = type.FullName
                };
            }

            // Handle arrays and lists
            if (value is System.Collections.IEnumerable enumerable && !(value is string))
            {
                try
                {
                    var items = new List<object>();
                    foreach (var item in enumerable)
                    {
                        items.Add(SerializeValue(item, maxDepth, currentDepth + 1));
                        if (items.Count >= 100) // Limit array size
                        {
                            items.Add(new { _truncated = true, message = "Array truncated at 100 items" });
                            break;
                        }
                    }
                    return new { _type = type.Name, _isArray = true, count = items.Count, items };
                }
                catch (Exception ex)
                {
                    return new { _type = type.Name, _error = $"Failed to enumerate: {ex.Message}" };
                }
            }

            // Handle general objects
            try
            {
                var result = new Dictionary<string, object>
                {
                    ["_type"] = type.Name,
                    ["_fullType"] = type.FullName
                };

                // Add common Unity properties if they exist
                if (value is Component comp)
                {
                    result["gameObject"] = SerializeValue(comp.gameObject, maxDepth, currentDepth + 1);
                }

                return result;
            }
            catch (Exception ex)
            {
                return new { _type = type.Name, _error = $"Failed to serialize: {ex.Message}" };
            }
        }

        #endregion
    }
}
