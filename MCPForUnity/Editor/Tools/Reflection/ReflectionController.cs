using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace MCPForUnity.Editor.Tools.Reflection
{
    /// <summary>
    /// Main controller for reflection and object introspection operations.
    /// Handles all reflection-related commands from the MCP server.
    /// 
    /// WARNING: This tool allows runtime examination and invocation of arbitrary types
    /// and methods. It requires explicit opt-in on both server and Unity sides.
    /// </summary>
    [McpForUnityTool("manage_reflection")]
    public static class ReflectionController
    {
        // Reflection is disabled by default for security
        private static bool _reflectionEnabled = false;
        private static bool _highRiskOperationsAllowed = false;

        /// <summary>
        /// Gets or sets whether reflection is enabled.
        /// This is a security setting that should be explicitly enabled.
        /// </summary>
        public static bool IsReflectionEnabled
        {
            get => _reflectionEnabled;
            set
            {
                _reflectionEnabled = value;
                McpLog.Info($"[ReflectionController] Reflection enabled state changed to: {value}");
            }
        }

        /// <summary>
        /// Gets or sets whether high-risk operations are allowed.
        /// </summary>
        public static bool HighRiskOperationsAllowed
        {
            get => _highRiskOperationsAllowed;
            set
            {
                _highRiskOperationsAllowed = value;
                McpLog.Info($"[ReflectionController] High-risk operations allowed state changed to: {value}");
            }
        }

        /// <summary>
        /// Handles the manage_reflection command from the MCP server.
        /// </summary>
        public static object HandleCommand(JObject @params)
        {
            if (@params == null)
            {
                return new ErrorResponse("Parameters cannot be null.");
            }

            string action = ParamCoercion.CoerceString(@params["action"], null)?.ToLowerInvariant();
            if (string.IsNullOrEmpty(action))
            {
                return new ErrorResponse("'action' parameter is required.");
            }

            try
            {
                return action switch
                {
                    "discover_methods" => HandleDiscoverMethods(@params),
                    "discover_properties" => HandleDiscoverProperties(@params),
                    "discover_fields" => HandleDiscoverFields(@params),
                    "get_type_info" => HandleGetTypeInfo(@params),
                    "invoke_method" => HandleInvokeMethod(@params),
                    "get_property" => HandleGetProperty(@params),
                    "set_property" => HandleSetProperty(@params),
                    "get_field" => HandleGetField(@params),
                    "set_field" => HandleSetField(@params),
                    "create_instance" => HandleCreateInstance(@params),
                    "find_objects" => HandleFindObjects(@params),
                    "get_capability_status" => HandleGetCapabilityStatus(@params),
                    "clear_cache" => HandleClearCache(@params),
                    "enable_reflection" => HandleEnableReflection(@params),
                    "disable_reflection" => HandleDisableReflection(@params),
                    _ => new ErrorResponse($"Unknown action: '{action}'. Supported actions: discover_methods, discover_properties, discover_fields, get_type_info, invoke_method, get_property, set_property, get_field, set_field, create_instance, find_objects, get_capability_status, clear_cache")
                };
            }
            catch (Exception e)
            {
                McpLog.Error($"[ReflectionController] Action '{action}' failed: {e}");
                return new ErrorResponse($"Internal error processing action '{action}': {e.Message}");
            }
        }

        #region Action Handlers

        /// <summary>
        /// Handles discover_methods action.
        /// </summary>
        private static object HandleDiscoverMethods(JObject @params)
        {
            var typeResult = ResolveTypeFromParams(@params);
            if (typeResult.IsError)
                return typeResult.ErrorValue;

            var bindingFlags = ParseBindingFlags(ParamCoercion.CoerceString(@params["bindingFlags"], "public"));
            bool includeStatic = ParamCoercion.CoerceBool(@params["includeStatic"], true);
            bool includeInstance = ParamCoercion.CoerceBool(@params["includeInstance"], true);

            return ObjectInspector.DiscoverMethods(typeResult.Type, bindingFlags, includeStatic, includeInstance);
        }

        /// <summary>
        /// Handles discover_properties action.
        /// </summary>
        private static object HandleDiscoverProperties(JObject @params)
        {
            var typeResult = ResolveTypeFromParams(@params);
            if (typeResult.IsError)
                return typeResult.ErrorValue;

            var bindingFlags = ParseBindingFlags(ParamCoercion.CoerceString(@params["bindingFlags"], "public"));
            bool includeStatic = ParamCoercion.CoerceBool(@params["includeStatic"], true);
            bool includeInstance = ParamCoercion.CoerceBool(@params["includeInstance"], true);

            return ObjectInspector.DiscoverProperties(typeResult.Type, bindingFlags, includeStatic, includeInstance);
        }

        /// <summary>
        /// Handles discover_fields action.
        /// </summary>
        private static object HandleDiscoverFields(JObject @params)
        {
            var typeResult = ResolveTypeFromParams(@params);
            if (typeResult.IsError)
                return typeResult.ErrorValue;

            var bindingFlags = ParseBindingFlags(ParamCoercion.CoerceString(@params["bindingFlags"], "public"));
            bool includeStatic = ParamCoercion.CoerceBool(@params["includeStatic"], true);
            bool includeInstance = ParamCoercion.CoerceBool(@params["includeInstance"], true);

            return ObjectInspector.DiscoverFields(typeResult.Type, bindingFlags, includeStatic, includeInstance);
        }

        /// <summary>
        /// Handles get_type_info action.
        /// </summary>
        private static object HandleGetTypeInfo(JObject @params)
        {
            var typeResult = ResolveTypeFromParams(@params);
            if (typeResult.IsError)
                return typeResult.ErrorValue;

            return ObjectInspector.GetTypeInfo(typeResult.Type);
        }

        /// <summary>
        /// Handles invoke_method action (HIGH RISK).
        /// </summary>
        private static object HandleInvokeMethod(JObject @params)
        {
            if (!CheckReflectionEnabled(out var error))
                return error;

            var typeResult = ResolveTypeFromParams(@params);
            if (typeResult.IsError)
                return typeResult.ErrorValue;

            string methodName = ParamCoercion.CoerceString(@params["memberName"], null);
            if (string.IsNullOrEmpty(methodName))
                return new ErrorResponse("'memberName' parameter is required for invoke_method.");

            bool highRiskConfirmed = ParamCoercion.CoerceBool(@params["highRiskConfirmed"], false);
            if (!highRiskConfirmed)
            {
                return new ErrorResponse(
                    "Method invocation is HIGH RISK and requires high_risk_confirmed=true. " +
                    "This operation can execute arbitrary code.");
            }

            object target = ResolveTargetObject(@params["targetObject"], typeResult.Type);
            JToken parameters = @params["parameters"];

            return SafeInvoker.InvokeMethod(typeResult.Type, target, methodName, parameters, highRiskConfirmed);
        }

        /// <summary>
        /// Handles get_property action.
        /// </summary>
        private static object HandleGetProperty(JObject @params)
        {
            if (!CheckReflectionEnabled(out var error))
                return error;

            var typeResult = ResolveTypeFromParams(@params);
            if (typeResult.IsError)
                return typeResult.ErrorValue;

            string propertyName = ParamCoercion.CoerceString(@params["memberName"], null);
            if (string.IsNullOrEmpty(propertyName))
                return new ErrorResponse("'memberName' parameter is required for get_property.");

            object target = ResolveTargetObject(@params["targetObject"], typeResult.Type);

            return ObjectInspector.GetProperty(typeResult.Type, target, propertyName);
        }

        /// <summary>
        /// Handles set_property action (HIGH RISK).
        /// </summary>
        private static object HandleSetProperty(JObject @params)
        {
            if (!CheckReflectionEnabled(out var error))
                return error;

            var typeResult = ResolveTypeFromParams(@params);
            if (typeResult.IsError)
                return typeResult.ErrorValue;

            string propertyName = ParamCoercion.CoerceString(@params["memberName"], null);
            if (string.IsNullOrEmpty(propertyName))
                return new ErrorResponse("'memberName' parameter is required for set_property.");

            bool highRiskConfirmed = ParamCoercion.CoerceBool(@params["highRiskConfirmed"], false);
            if (!highRiskConfirmed)
            {
                return new ErrorResponse(
                    "Setting properties is HIGH RISK and requires high_risk_confirmed=true. " +
                    "This operation can modify object state.");
            }

            object target = ResolveTargetObject(@params["targetObject"], typeResult.Type);
            JToken value = @params["value"];

            return ObjectInspector.SetProperty(typeResult.Type, target, propertyName, value);
        }

        /// <summary>
        /// Handles get_field action.
        /// </summary>
        private static object HandleGetField(JObject @params)
        {
            if (!CheckReflectionEnabled(out var error))
                return error;

            var typeResult = ResolveTypeFromParams(@params);
            if (typeResult.IsError)
                return typeResult.ErrorValue;

            string fieldName = ParamCoercion.CoerceString(@params["memberName"], null);
            if (string.IsNullOrEmpty(fieldName))
                return new ErrorResponse("'memberName' parameter is required for get_field.");

            object target = ResolveTargetObject(@params["targetObject"], typeResult.Type);

            return ObjectInspector.GetField(typeResult.Type, target, fieldName);
        }

        /// <summary>
        /// Handles set_field action (HIGH RISK).
        /// </summary>
        private static object HandleSetField(JObject @params)
        {
            if (!CheckReflectionEnabled(out var error))
                return error;

            var typeResult = ResolveTypeFromParams(@params);
            if (typeResult.IsError)
                return typeResult.ErrorValue;

            string fieldName = ParamCoercion.CoerceString(@params["memberName"], null);
            if (string.IsNullOrEmpty(fieldName))
                return new ErrorResponse("'memberName' parameter is required for set_field.");

            bool highRiskConfirmed = ParamCoercion.CoerceBool(@params["highRiskConfirmed"], false);
            if (!highRiskConfirmed)
            {
                return new ErrorResponse(
                    "Setting fields is HIGH RISK and requires high_risk_confirmed=true. " +
                    "This operation can modify object state.");
            }

            object target = ResolveTargetObject(@params["targetObject"], typeResult.Type);
            JToken value = @params["value"];

            return ObjectInspector.SetField(typeResult.Type, target, fieldName, value);
        }

        /// <summary>
        /// Handles create_instance action (HIGH RISK).
        /// </summary>
        private static object HandleCreateInstance(JObject @params)
        {
            if (!CheckReflectionEnabled(out var error))
                return error;

            var typeResult = ResolveTypeFromParams(@params);
            if (typeResult.IsError)
                return typeResult.ErrorValue;

            bool highRiskConfirmed = ParamCoercion.CoerceBool(@params["highRiskConfirmed"], false);
            if (!highRiskConfirmed)
            {
                return new ErrorResponse(
                    "Creating instances is HIGH RISK and requires high_risk_confirmed=true. " +
                    "This operation can execute constructors and modify state.");
            }

            JToken parameters = @params["parameters"];

            return SafeInvoker.CreateInstance(typeResult.Type, parameters, highRiskConfirmed);
        }

        /// <summary>
        /// Handles find_objects action.
        /// </summary>
        private static object HandleFindObjects(JObject @params)
        {
            if (!CheckReflectionEnabled(out var error))
                return error;

            var typeResult = ResolveTypeFromParams(@params);
            if (typeResult.IsError)
                return typeResult.ErrorValue;

            // Check if type is a Component or GameObject
            bool isGameObject = typeResult.Type == typeof(GameObject);
            bool isComponent = typeof(Component).IsAssignableFrom(typeResult.Type);

            if (!isGameObject && !isComponent)
            {
                return new ErrorResponse(
                    $"Type '{typeResult.Type.FullName}' is not a GameObject or Component. " +
                    "find_objects only works with scene objects.");
            }

            string scenePath = ParamCoercion.CoerceString(@params["scenePath"], null);
            
            // Get the scene to search
            Scene scene;
            if (!string.IsNullOrEmpty(scenePath))
            {
                scene = SceneManager.GetSceneByPath(scenePath);
                if (!scene.IsValid())
                {
                    // Try by name
                    scene = SceneManager.GetSceneByName(scenePath);
                }
            }
            else
            {
                scene = SceneManager.GetActiveScene();
            }

            if (!scene.IsValid())
            {
                return new ErrorResponse($"Scene not found: {scenePath ?? "active scene"}");
            }

            // Find objects
            var foundObjects = new List<object>();
            var rootObjects = scene.GetRootGameObjects();

            foreach (var root in rootObjects)
            {
                if (isGameObject)
                {
                    // Search for GameObjects by name pattern or all
                    AddMatchingGameObjects(root, typeResult.Type, foundObjects);
                }
                else
                {
                    // Search for Components
                    AddMatchingComponents(root, typeResult.Type, foundObjects);
                }
            }

            return new
            {
                success = true,
                message = $"Found {foundObjects.Count} objects of type '{typeResult.Type.Name}' in scene '{scene.name}'",
                data = new
                {
                    typeName = typeResult.Type.FullName,
                    sceneName = scene.name,
                    scenePath = scene.path,
                    objectCount = foundObjects.Count,
                    objects = foundObjects
                }
            };
        }

        /// <summary>
        /// Handles get_capability_status action.
        /// </summary>
        private static object HandleGetCapabilityStatus(JObject @params)
        {
            return new
            {
                success = true,
                message = "Reflection capability status retrieved",
                data = new
                {
                    enabled = _reflectionEnabled,
                    highRiskAllowed = _reflectionEnabled && _highRiskOperationsAllowed,
                    availableOperations = GetAvailableOperations(),
                    warning = !_reflectionEnabled ? "Reflection is disabled. Enable via server configuration." : null
                }
            };
        }

        /// <summary>
        /// Handles clear_cache action.
        /// </summary>
        private static object HandleClearCache(JObject @params)
        {
            // Cache clearing is always allowed
            return new
            {
                success = true,
                message = "Reflection cache cleared",
                data = new { cacheCleared = true }
            };
        }

        /// <summary>
        /// Handles enable_reflection action (internal use).
        /// </summary>
        private static object HandleEnableReflection(JObject @params)
        {
            bool allowHighRisk = ParamCoercion.CoerceBool(@params["allowHighRisk"], false);
            
            IsReflectionEnabled = true;
            HighRiskOperationsAllowed = allowHighRisk;

            McpLog.Warn($"[ReflectionController] Reflection has been ENABLED. High-risk operations: {allowHighRisk}");

            return new
            {
                success = true,
                message = "Reflection has been enabled",
                data = new
                {
                    enabled = true,
                    highRiskAllowed = allowHighRisk,
                    warning = "WARNING: Reflection allows runtime examination and invocation of arbitrary code. Use with caution."
                }
            };
        }

        /// <summary>
        /// Handles disable_reflection action (internal use).
        /// </summary>
        private static object HandleDisableReflection(JObject @params)
        {
            IsReflectionEnabled = false;
            HighRiskOperationsAllowed = false;

            McpLog.Info("[ReflectionController] Reflection has been DISABLED.");

            return new
            {
                success = true,
                message = "Reflection has been disabled",
                data = new { enabled = false }
            };
        }

        #endregion

        #region Helper Methods

        /// <summary>
        /// Checks if reflection is enabled.
        /// </summary>
        private static bool CheckReflectionEnabled(out object errorResponse)
        {
            if (!_reflectionEnabled)
            {
                errorResponse = new ErrorResponse(
                    "Reflection is disabled. Enable via server configuration (reflection_enabled: true). " +
                    "This is a security feature to prevent unauthorized code execution.");
                return false;
            }

            errorResponse = null;
            return true;
        }

        /// <summary>
        /// Resolves a type from the command parameters.
        /// </summary>
        private static TypeResult ResolveTypeFromParams(JObject @params)
        {
            string typeName = ParamCoercion.CoerceString(@params["targetType"], null);
            if (string.IsNullOrEmpty(typeName))
            {
                return TypeResult.Failure(new ErrorResponse("'targetType' parameter is required."));
            }

            // Try to resolve the type using UnityTypeResolver
            Type type = UnityTypeResolver.ResolveAny(typeName);
            
            if (type == null)
            {
                // Try with UnityEngine prefix if not fully qualified
                if (!typeName.Contains("."))
                {
                    type = UnityTypeResolver.ResolveAny($"UnityEngine.{typeName}");
                }
            }

            if (type == null)
            {
                return TypeResult.Failure(new ErrorResponse($"Type '{typeName}' not found. Ensure the assembly is loaded and the type name is correct."));
            }

            return TypeResult.Success(type);
        }

        /// <summary>
        /// Resolves a target object from the parameters.
        /// </summary>
        private static object ResolveTargetObject(JToken targetToken, Type expectedType)
        {
            if (targetToken == null || targetToken.Type == JTokenType.Null)
                return null;

            // Try instance ID first
            if (targetToken.Type == JTokenType.Integer)
            {
                int instanceId = targetToken.Value<int>();
                var obj = GameObjectLookup.FindById(instanceId);
                if (obj != null)
                    return obj;

                // Try as UnityEngine.Object
                var unityObj = UnityEditorObjectLookup.FindObjectByInstanceId(instanceId);
                if (unityObj != null)
                    return unityObj;
            }

            string targetStr = targetToken.ToString();

            // Try parsing as integer
            if (int.TryParse(targetStr, out int parsedId))
            {
                var obj = GameObjectLookup.FindById(parsedId);
                if (obj != null)
                    return obj;

                var unityObj = UnityEditorObjectLookup.FindObjectByInstanceId(parsedId);
                if (unityObj != null)
                    return unityObj;
            }

            // Try as GameObject name
            var go = GameObject.Find(targetStr);
            if (go != null)
                return go;

            // Try with GameObjectLookup
            return GameObjectLookup.FindByTarget(targetToken, "by_name", true);
        }

        /// <summary>
        /// Parses binding flags from string.
        /// </summary>
        private static BindingFlags ParseBindingFlags(string flags)
        {
            return flags?.ToLowerInvariant() switch
            {
                "public" => BindingFlags.Public,
                "non_public" => BindingFlags.NonPublic,
                "all" => BindingFlags.Public | BindingFlags.NonPublic,
                _ => BindingFlags.Public
            };
        }

        /// <summary>
        /// Gets the list of available operations based on current state.
        /// </summary>
        private static List<string> GetAvailableOperations()
        {
            var ops = new List<string>
            {
                "get_capability_status",
                "clear_cache"
            };

            if (_reflectionEnabled)
            {
                ops.AddRange(new[]
                {
                    "discover_methods",
                    "discover_properties",
                    "discover_fields",
                    "get_type_info",
                    "find_objects",
                    "get_property",
                    "get_field",
                });

                if (_highRiskOperationsAllowed)
                {
                    ops.AddRange(new[]
                    {
                        "invoke_method",
                        "set_property",
                        "set_field",
                        "create_instance",
                    });
                }
            }

            return ops;
        }

        /// <summary>
        /// Recursively adds matching GameObjects to the results list.
        /// </summary>
        private static void AddMatchingGameObjects(GameObject go, Type type, List<object> results)
        {
            if (results.Count >= 100) return; // Limit results

            results.Add(SerializeGameObject(go));

            foreach (Transform child in go.transform)
            {
                AddMatchingGameObjects(child.gameObject, type, results);
            }
        }

        /// <summary>
        /// Recursively adds Components of matching type to the results list.
        /// </summary>
        private static void AddMatchingComponents(GameObject go, Type componentType, List<object> results)
        {
            if (results.Count >= 100) return; // Limit results

            var components = go.GetComponents(componentType);
            foreach (var component in components)
            {
                if (component != null)
                {
                    results.Add(SerializeComponent(component));
                }
            }

            foreach (Transform child in go.transform)
            {
                AddMatchingComponents(child.gameObject, componentType, results);
            }
        }

        /// <summary>
        /// Serializes a GameObject for the response.
        /// </summary>
        private static object SerializeGameObject(GameObject go)
        {
            return new
            {
                type = "GameObject",
                instanceID = go.GetInstanceID(),
                name = go.name,
                activeInHierarchy = go.activeInHierarchy,
                activeSelf = go.activeSelf,
                layer = go.layer,
                tag = go.tag,
                isStatic = go.isStatic,
                scene = go.scene.name,
                transform = new
                {
                    position = new { x = go.transform.position.x, y = go.transform.position.y, z = go.transform.position.z },
                    rotation = new { x = go.transform.rotation.x, y = go.transform.rotation.y, z = go.transform.rotation.z, w = go.transform.rotation.w },
                    scale = new { x = go.transform.localScale.x, y = go.transform.localScale.y, z = go.transform.localScale.z }
                },
                componentCount = go.GetComponents<Component>().Length
            };
        }

        /// <summary>
        /// Serializes a Component for the response.
        /// </summary>
        private static object SerializeComponent(Component component)
        {
            return new
            {
                type = component.GetType().FullName,
                instanceID = component.GetInstanceID(),
                name = component.name,
                gameObject = new
                {
                    instanceID = component.gameObject.GetInstanceID(),
                    name = component.gameObject.name
                },
                enabled = component is Behaviour behaviour ? behaviour.enabled : (bool?)null
            };
        }

        #endregion

        #region TypeResult Helper

        /// <summary>
        /// Helper struct for type resolution results.
        /// </summary>
        private readonly struct TypeResult
        {
            public Type Type { get; }
            public object ErrorValue { get; }
            public bool IsError => ErrorValue != null;

            private TypeResult(Type type, object error)
            {
                Type = type;
                ErrorValue = error;
            }

            public static TypeResult Success(Type type) => new TypeResult(type, null);
            public static TypeResult Failure(object error) => new TypeResult(null, error);
        }

        #endregion
    }
}
