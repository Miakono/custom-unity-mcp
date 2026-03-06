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
    /// Handles safe method invocation and instance creation for reflection operations.
    /// Includes permission checks and safeguards against dangerous operations.
    /// </summary>
    public static class SafeInvoker
    {
        #region Configuration

        /// <summary>
        /// List of namespaces that are considered safe for reflection operations.
        /// Types outside these namespaces require additional confirmation.
        /// </summary>
        private static readonly HashSet<string> SafeNamespaces = new(StringComparer.OrdinalIgnoreCase)
        {
            "UnityEngine",
            "UnityEngine.UI",
            "UnityEngine.EventSystems",
            "UnityEditor",
            "UnityEditor.SceneManagement",
            "UnityEditorInternal",
            "System",
            "System.Collections",
            "System.Collections.Generic",
        };

        /// <summary>
        /// List of type prefixes that are blocked from reflection operations.
        /// These are considered dangerous or internal.
        /// </summary>
        private static readonly HashSet<string> BlockedTypePrefixes = new(StringComparer.OrdinalIgnoreCase)
        {
            "System.Reflection.Emit",
            "System.Runtime.InteropServices",
            "System.Security",
            "System.Diagnostics.Process",
            "System.IO.File",
            "System.Net",
        };

        /// <summary>
        /// List of method names that are blocked from invocation.
        /// These methods are considered dangerous.
        /// </summary>
        private static readonly HashSet<string> BlockedMethodNames = new(StringComparer.OrdinalIgnoreCase)
        {
            "Exit",
            "Abort",
            "Terminate",
            "Kill",
            "Delete",
            "RemoveAll",
            "Format",
            "Execute",
            "InvokeMember",
            "CreateInstanceFrom",
        };

        #endregion

        #region Permission Checks

        /// <summary>
        /// Validates whether a type is safe for reflection operations.
        /// </summary>
        public static (bool isSafe, string reason) ValidateTypeSafety(Type type, bool highRiskConfirmed)
        {
            if (type == null)
                return (false, "Type is null");

            var namespaceName = type.Namespace ?? "";

            // Check for blocked type prefixes
            foreach (var prefix in BlockedTypePrefixes)
            {
                if (namespaceName.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                {
                    if (!highRiskConfirmed)
                    {
                        return (false, $"Type namespace '{namespaceName}' is in a restricted area. High-risk confirmation required.");
                    }
                }
            }

            // Check if namespace is in safe list
            bool isSafeNamespace = SafeNamespaces.Any(ns => 
                namespaceName.Equals(ns, StringComparison.OrdinalIgnoreCase) || 
                namespaceName.StartsWith(ns + ".", StringComparison.OrdinalIgnoreCase));

            if (!isSafeNamespace && !highRiskConfirmed)
            {
                return (false, $"Type '{type.FullName}' is not in a known safe namespace. High-risk confirmation required.");
            }

            return (true, null);
        }

        /// <summary>
        /// Validates whether a method is safe for invocation.
        /// </summary>
        public static (bool isSafe, string reason) ValidateMethodSafety(MethodInfo method, bool highRiskConfirmed)
        {
            if (method == null)
                return (false, "Method is null");

            // Check for blocked method names
            if (BlockedMethodNames.Contains(method.Name))
            {
                if (!highRiskConfirmed)
                {
                    return (false, $"Method '{method.Name}' is in the restricted list. High-risk confirmation required.");
                }
            }

            // Validate declaring type
            var typeValidation = ValidateTypeSafety(method.DeclaringType, highRiskConfirmed);
            if (!typeValidation.isSafe)
            {
                return typeValidation;
            }

            return (true, null);
        }

        /// <summary>
        /// Validates that high-risk operations have been confirmed.
        /// </summary>
        public static (bool isValid, string error) ValidateHighRiskConfirmation(bool highRiskConfirmed, string operation)
        {
            if (!highRiskConfirmed)
            {
                return (false, 
                    $"Operation '{operation}' is HIGH RISK and requires explicit confirmation. " +
                    "Set high_risk_confirmed=true to proceed. " +
                    "WARNING: This operation can modify state or execute arbitrary code.");
            }
            return (true, null);
        }

        #endregion

        #region Method Invocation

        /// <summary>
        /// Invokes a method on an object or type with safety checks.
        /// </summary>
        public static object InvokeMethod(
            Type type, 
            object target, 
            string methodName, 
            JToken parameters,
            bool highRiskConfirmed)
        {
            // Validate high-risk confirmation
            var confirmation = ValidateHighRiskConfirmation(highRiskConfirmed, "invoke_method");
            if (!confirmation.isValid)
                return new ErrorResponse(confirmation.error);

            if (type == null)
                return new ErrorResponse("Type is null");

            if (string.IsNullOrEmpty(methodName))
                return new ErrorResponse("Method name is required");

            try
            {
                // Get methods with the specified name
                var methods = type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance)
                    .Where(m => m.Name == methodName)
                    .ToList();

                if (methods.Count == 0)
                    return new ErrorResponse($"Method '{methodName}' not found on type '{type.FullName}'");

                // Validate safety
                var safety = ValidateMethodSafety(methods[0], highRiskConfirmed);
                if (!safety.isSafe)
                    return new ErrorResponse(safety.reason);

                // Parse parameters
                object[] args;
                Type[] argTypes;

                if (parameters == null || parameters.Type == JTokenType.Null)
                {
                    args = Array.Empty<object>();
                    argTypes = Array.Empty<Type>();
                }
                else if (parameters.Type == JTokenType.Array)
                {
                    var arr = (JArray)parameters;
                    args = new object[arr.Count];
                    argTypes = new Type[arr.Count];
                    for (int i = 0; i < arr.Count; i++)
                    {
                        args[i] = arr[i];
                        argTypes[i] = args[i]?.GetType() ?? typeof(object);
                    }
                }
                else if (parameters.Type == JTokenType.Object)
                {
                    // Named parameters - we need to find a matching method
                    var obj = (JObject)parameters;
                    return InvokeWithNamedParameters(type, target, methodName, obj, methods, highRiskConfirmed);
                }
                else
                {
                    args = new[] { parameters.ToObject<object>() };
                    argTypes = new[] { args[0]?.GetType() ?? typeof(object) };
                }

                // Find best matching method
                var method = FindBestMatchingMethod(methods, argTypes);
                if (method == null)
                {
                    // Try with exact parameter count match
                    method = methods.FirstOrDefault(m => m.GetParameters().Length == args.Length);
                    if (method == null)
                        return new ErrorResponse($"No matching overload found for method '{methodName}' with {args.Length} parameters");
                }

                // Coerce parameters to match method signature
                args = CoerceParameters(args, method.GetParameters());

                // Invoke the method
                McpLog.Info($"[SafeInvoker] Invoking method '{methodName}' on type '{type.FullName}'");
                var result = method.Invoke(target, args);

                return new
                {
                    success = true,
                    message = $"Method '{methodName}' invoked successfully",
                    data = new
                    {
                        methodName = methodName,
                        returnType = method.ReturnType.FullName,
                        returnValue = SerializeReturnValue(result),
                        isStatic = method.IsStatic,
                        declaringType = method.DeclaringType?.FullName,
                        parametersPassed = args.Length
                    }
                };
            }
            catch (TargetInvocationException ex) when (ex.InnerException != null)
            {
                McpLog.Error($"[SafeInvoker] Method invocation failed: {ex.InnerException.Message}");
                return new ErrorResponse($"Method invocation failed: {ex.InnerException.Message}");
            }
            catch (Exception ex)
            {
                McpLog.Error($"[SafeInvoker] Failed to invoke method {methodName}: {ex.Message}");
                return new ErrorResponse($"Failed to invoke method: {ex.Message}");
            }
        }

        /// <summary>
        /// Invokes a method with named parameters.
        /// </summary>
        private static object InvokeWithNamedParameters(
            Type type, 
            object target, 
            string methodName, 
            JObject parameters,
            List<MethodInfo> candidates,
            bool highRiskConfirmed)
        {
            // Find a method that has matching parameter names
            foreach (var method in candidates)
            {
                var methodParams = method.GetParameters();
                if (methodParams.Length == 0 && parameters.Count > 0)
                    continue;

                // Check if all provided parameters match
                bool allMatch = true;
                var args = new object[methodParams.Length];

                for (int i = 0; i < methodParams.Length; i++)
                {
                    var param = methodParams[i];
                    if (parameters.TryGetValue(param.Name, StringComparison.OrdinalIgnoreCase, out JToken value))
                    {
                        try
                        {
                            args[i] = CoerceParameter(value, param.ParameterType);
                        }
                        catch (Exception ex)
                        {
                            allMatch = false;
                            break;
                        }
                    }
                    else if (param.IsOptional)
                    {
                        args[i] = param.DefaultValue;
                    }
                    else if (parameters.Count == methodParams.Length)
                    {
                        // Try positional matching
                        var positionalValue = parameters.Properties().ElementAtOrDefault(i)?.Value;
                        if (positionalValue != null)
                        {
                            try
                            {
                                args[i] = CoerceParameter(positionalValue, param.ParameterType);
                            }
                            catch
                            {
                                allMatch = false;
                                break;
                            }
                        }
                        else
                        {
                            allMatch = false;
                            break;
                        }
                    }
                    else
                    {
                        allMatch = false;
                        break;
                    }
                }

                if (allMatch)
                {
                    // Validate safety
                    var safety = ValidateMethodSafety(method, highRiskConfirmed);
                    if (!safety.isSafe)
                        return new ErrorResponse(safety.reason);

                    // Invoke
                    McpLog.Info($"[SafeInvoker] Invoking method '{methodName}' with named parameters on type '{type.FullName}'");
                    var result = method.Invoke(target, args);

                    return new
                    {
                        success = true,
                        message = $"Method '{methodName}' invoked successfully",
                        data = new
                        {
                            methodName = methodName,
                            returnType = method.ReturnType.FullName,
                            returnValue = SerializeReturnValue(result),
                            isStatic = method.IsStatic,
                            declaringType = method.DeclaringType?.FullName,
                            parametersPassed = args.Length,
                            namedParameters = true
                        }
                    };
                }
            }

            return new ErrorResponse($"No matching method overload found for '{methodName}' with the provided named parameters");
        }

        #endregion

        #region Instance Creation

        /// <summary>
        /// Creates an instance of a type with safety checks.
        /// </summary>
        public static object CreateInstance(Type type, JToken parameters, bool highRiskConfirmed)
        {
            // Validate high-risk confirmation
            var confirmation = ValidateHighRiskConfirmation(highRiskConfirmed, "create_instance");
            if (!confirmation.isValid)
                return new ErrorResponse(confirmation.error);

            if (type == null)
                return new ErrorResponse("Type is null");

            // Validate type safety
            var safety = ValidateTypeSafety(type, highRiskConfirmed);
            if (!safety.isSafe)
                return new ErrorResponse(safety.reason);

            // Check for abstract classes and interfaces
            if (type.IsAbstract)
                return new ErrorResponse($"Cannot create instance of abstract type '{type.FullName}'");

            if (type.IsInterface)
                return new ErrorResponse($"Cannot create instance of interface '{type.FullName}'");

            try
            {
                object instance;

                if (parameters == null || parameters.Type == JTokenType.Null)
                {
                    // Default constructor
                    instance = Activator.CreateInstance(type);
                }
                else if (parameters.Type == JTokenType.Array)
                {
                    // Constructor with positional parameters
                    var arr = (JArray)parameters;
                    var args = arr.Select(t => t.ToObject<object>()).ToArray();
                    instance = Activator.CreateInstance(type, args);
                }
                else if (parameters.Type == JTokenType.Object)
                {
                    // Try to find a matching constructor or use object initializer pattern
                    var obj = (JObject)parameters;
                    instance = CreateInstanceWithParameters(type, obj);
                }
                else
                {
                    // Single parameter
                    instance = Activator.CreateInstance(type, parameters.ToObject<object>());
                }

                McpLog.Info($"[SafeInvoker] Created instance of type '{type.FullName}'");

                return new
                {
                    success = true,
                    message = $"Instance of '{type.FullName}' created successfully",
                    data = new
                    {
                        typeName = type.FullName,
                        instanceID = instance is UnityEngine.Object unityObj ? unityObj.GetInstanceID() : (int?)null,
                        isUnityObject = instance is UnityEngine.Object,
                        serializedValue = SerializeReturnValue(instance)
                    }
                };
            }
            catch (TargetInvocationException ex) when (ex.InnerException != null)
            {
                McpLog.Error($"[SafeInvoker] Instance creation failed: {ex.InnerException.Message}");
                return new ErrorResponse($"Instance creation failed: {ex.InnerException.Message}");
            }
            catch (MissingMethodException ex)
            {
                McpLog.Error($"[SafeInvoker] No matching constructor found: {ex.Message}");
                return new ErrorResponse($"No matching constructor found: {ex.Message}");
            }
            catch (Exception ex)
            {
                McpLog.Error($"[SafeInvoker] Failed to create instance: {ex.Message}");
                return new ErrorResponse($"Failed to create instance: {ex.Message}");
            }
        }

        /// <summary>
        /// Creates an instance with named parameter matching.
        /// </summary>
        private static object CreateInstanceWithParameters(Type type, JObject parameters)
        {
            // Get all constructors
            var constructors = type.GetConstructors(BindingFlags.Public | BindingFlags.Instance);

            // Try to find a matching constructor
            foreach (var ctor in constructors)
            {
                var ctorParams = ctor.GetParameters();
                if (ctorParams.Length == 0 && parameters.Count == 0)
                {
                    return Activator.CreateInstance(type);
                }

                if (ctorParams.Length == parameters.Count)
                {
                    var args = new object[ctorParams.Length];
                    bool match = true;

                    // Try positional matching first
                    if (parameters.Properties().All(p => int.TryParse(p.Name, out _)))
                    {
                        for (int i = 0; i < ctorParams.Length; i++)
                        {
                            var param = parameters[i.ToString()];
                            if (param != null)
                            {
                                args[i] = CoerceParameter(param, ctorParams[i].ParameterType);
                            }
                            else
                            {
                                match = false;
                                break;
                            }
                        }
                    }
                    else
                    {
                        // Named parameter matching
                        for (int i = 0; i < ctorParams.Length; i++)
                        {
                            var param = ctorParams[i];
                            if (parameters.TryGetValue(param.Name, StringComparison.OrdinalIgnoreCase, out JToken value))
                            {
                                args[i] = CoerceParameter(value, param.ParameterType);
                            }
                            else if (param.IsOptional)
                            {
                                args[i] = param.DefaultValue;
                            }
                            else
                            {
                                match = false;
                                break;
                            }
                        }
                    }

                    if (match)
                    {
                        return ctor.Invoke(args);
                    }
                }
            }

            // No matching constructor found, try default and set properties
            var defaultInstance = Activator.CreateInstance(type);
            
            foreach (var prop in parameters.Properties())
            {
                var property = type.GetProperty(prop.Name, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
                if (property != null && property.CanWrite)
                {
                    var value = CoerceParameter(prop.Value, property.PropertyType);
                    property.SetValue(defaultInstance, value);
                }
                else
                {
                    var field = type.GetField(prop.Name, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
                    if (field != null && !field.IsInitOnly)
                    {
                        var value = CoerceParameter(prop.Value, field.FieldType);
                        field.SetValue(defaultInstance, value);
                    }
                }
            }

            return defaultInstance;
        }

        #endregion

        #region Helper Methods

        /// <summary>
        /// Finds the best matching method based on parameter types.
        /// </summary>
        private static MethodInfo FindBestMatchingMethod(List<MethodInfo> methods, Type[] argTypes)
        {
            MethodInfo bestMatch = null;
            int bestScore = -1;

            foreach (var method in methods)
            {
                var parameters = method.GetParameters();
                
                // Skip if parameter count doesn't match
                if (parameters.Length != argTypes.Length)
                    continue;

                int score = 0;
                bool exactMatch = true;

                for (int i = 0; i < parameters.Length; i++)
                {
                    if (parameters[i].ParameterType == argTypes[i])
                    {
                        score += 2; // Exact match
                    }
                    else if (parameters[i].ParameterType.IsAssignableFrom(argTypes[i]))
                    {
                        score += 1; // Compatible match
                    }
                    else
                    {
                        exactMatch = false;
                        break;
                    }
                }

                if (exactMatch && score > bestScore)
                {
                    bestScore = score;
                    bestMatch = method;
                }
            }

            return bestMatch ?? methods.FirstOrDefault(m => m.GetParameters().Length == argTypes.Length);
        }

        /// <summary>
        /// Coerces parameters to match method signature.
        /// </summary>
        private static object[] CoerceParameters(object[] args, ParameterInfo[] parameters)
        {
            var result = new object[parameters.Length];

            for (int i = 0; i < parameters.Length; i++)
            {
                if (i < args.Length)
                {
                    result[i] = CoerceParameter(args[i], parameters[i].ParameterType);
                }
                else if (parameters[i].IsOptional)
                {
                    result[i] = parameters[i].DefaultValue;
                }
                else
                {
                    result[i] = null;
                }
            }

            return result;
        }

        /// <summary>
        /// Coerces a single parameter to the target type.
        /// </summary>
        private static object CoerceParameter(object value, Type targetType)
        {
            if (value == null)
                return null;

            if (value is JToken token)
            {
                return ObjectInspectorCoerce(token, targetType);
            }

            if (targetType.IsInstanceOfType(value))
                return value;

            try
            {
                return Convert.ChangeType(value, targetType);
            }
            catch
            {
                return value;
            }
        }

        /// <summary>
        /// Coerces a JToken to the target type (delegates to ObjectInspector's logic).
        /// </summary>
        private static object ObjectInspectorCoerce(JToken token, Type targetType)
        {
            // This is a simplified version - in production, this would use the full coercion logic
            return token.ToObject(targetType);
        }

        /// <summary>
        /// Serializes a return value for transmission.
        /// </summary>
        private static object SerializeReturnValue(object value)
        {
            if (value == null)
                return null;

            if (value is UnityEngine.Object unityObj)
            {
                return new
                {
                    _type = value.GetType().Name,
                    _reference = true,
                    instanceID = unityObj.GetInstanceID(),
                    name = unityObj.name
                };
            }

            // For primitives, return directly
            var type = value.GetType();
            if (type.IsPrimitive || type == typeof(string) || type == typeof(decimal))
                return value;

            // For value types that are likely Unity types, serialize specially
            if (type == typeof(Vector2) || type == typeof(Vector3) || type == typeof(Vector4) ||
                type == typeof(Quaternion) || type == typeof(Color))
            {
                return value; // These will be serialized by JSON serializer
            }

            // Return type information
            return new
            {
                _type = type.Name,
                _fullType = type.FullName,
                _value = value.ToString()
            };
        }

        #endregion
    }
}
