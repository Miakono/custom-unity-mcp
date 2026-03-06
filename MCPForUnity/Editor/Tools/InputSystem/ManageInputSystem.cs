#if ENABLE_INPUT_SYSTEM

using System;
using System.Collections.Generic;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.InputSystem
{
    /// <summary>
    /// Main entry point for Input System management commands.
    /// Handles routing to specialized managers for:
    /// - Action Map management (Editor mode)
    /// - Action management (Editor mode)
    /// - Binding management (Editor mode)
    /// - Control Scheme management (Editor mode)
    /// - Input Simulation (Runtime/Play mode)
    /// - Input State Reading (Runtime/Play mode)
    /// </summary>
    [McpForUnityTool("manage_input_system", AutoRegister = false, Group = "input")]
    public static class ManageInputSystem
    {
        private static readonly Dictionary<string, string> ParamAliases = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            { "asset_path", "assetPath" },
            { "action_map", "actionMap" },
            { "action_name", "actionName" },
            { "binding_path", "bindingPath" },
            { "binding_name", "bindingName" },
            { "expected_control_type", "expectedControlType" },
            { "action_type", "actionType" },
            { "is_composite", "isComposite" },
            { "is_part_of_composite", "isPartOfComposite" },
            { "control_scheme", "controlScheme" },
            { "scheme_name", "schemeName" },
            { "binding_index", "bindingIndex" },
        };

        #region Command Handling

        public static object HandleCommand(JObject @params)
        {
            JObject normalizedParams = NormalizeParams(@params);
            string action = normalizedParams["action"]?.ToString();
            
            if (string.IsNullOrEmpty(action))
            {
                return new ErrorResponse("Action is required");
            }

            try
            {
                string actionLower = action.ToLowerInvariant();

                // Route to appropriate handler based on action prefix
                if (actionLower.StartsWith("actionmap_"))
                {
                    return HandleActionMapAction(normalizedParams, actionLower.Substring(10));
                }

                if (actionLower.StartsWith("action_"))
                {
                    return HandleActionAction(normalizedParams, actionLower.Substring(7));
                }

                if (actionLower.StartsWith("binding_"))
                {
                    return HandleBindingAction(normalizedParams, actionLower.Substring(8));
                }

                if (actionLower.StartsWith("scheme_"))
                {
                    return HandleSchemeAction(normalizedParams, actionLower.Substring(7));
                }

                if (actionLower.StartsWith("asset_"))
                {
                    return HandleAssetAction(normalizedParams, actionLower.Substring(6));
                }

                if (actionLower.StartsWith("simulate_"))
                {
                    return HandleSimulationAction(normalizedParams, actionLower.Substring(9));
                }

                if (actionLower.StartsWith("state_"))
                {
                    return HandleStateAction(normalizedParams, actionLower.Substring(6));
                }

                return new ErrorResponse(
                    $"Unknown action: {action}. Actions must be prefixed with: " +
                    "actionmap_, action_, binding_, scheme_, asset_, simulate_, or state_");
            }
            catch (Exception e)
            {
                McpLog.Error($"[ManageInputSystem] Action '{action}' failed: {e}");
                return new ErrorResponse($"Internal error processing action '{action}': {e.Message}");
            }
        }

        #endregion

        #region Action Handlers

        private static object HandleActionMapAction(JObject @params, string subAction)
        {
            switch (subAction)
            {
                case "get_all":
                    return InputActionManager.GetAllActionMaps(@params);
                case "get":
                    return InputActionManager.GetActionMap(@params);
                case "create":
                    return InputActionManager.CreateActionMap(@params);
                case "delete":
                    return InputActionManager.DeleteActionMap(@params);
                default:
                    return new ErrorResponse(
                        $"Unknown actionmap action: {subAction}. Valid: get_all, get, create, delete");
            }
        }

        private static object HandleActionAction(JObject @params, string subAction)
        {
            switch (subAction)
            {
                case "get_all":
                    return InputActionManager.GetAllActions(@params);
                case "get":
                    return InputActionManager.GetAction(@params);
                case "create":
                    return InputActionManager.CreateAction(@params);
                case "delete":
                    return InputActionManager.DeleteAction(@params);
                default:
                    return new ErrorResponse(
                        $"Unknown action action: {subAction}. Valid: get_all, get, create, delete");
            }
        }

        private static object HandleBindingAction(JObject @params, string subAction)
        {
            switch (subAction)
            {
                case "get_all":
                    return InputActionManager.GetAllBindings(@params);
                case "add":
                    return InputActionManager.AddBinding(@params);
                case "remove":
                    return InputActionManager.RemoveBinding(@params);
                case "modify":
                    return InputActionManager.ModifyBinding(@params);
                default:
                    return new ErrorResponse(
                        $"Unknown binding action: {subAction}. Valid: get_all, add, remove, modify");
            }
        }

        private static object HandleSchemeAction(JObject @params, string subAction)
        {
            switch (subAction)
            {
                case "get_all":
                    return InputActionManager.GetAllControlSchemes(@params);
                case "create":
                    return InputActionManager.CreateControlScheme(@params);
                case "delete":
                    return InputActionManager.DeleteControlScheme(@params);
                default:
                    return new ErrorResponse(
                        $"Unknown scheme action: {subAction}. Valid: get_all, create, delete");
            }
        }

        private static object HandleAssetAction(JObject @params, string subAction)
        {
            switch (subAction)
            {
                case "get_all":
                    return InputActionManager.GetAllAssets(@params);
                case "get_info":
                    return InputActionManager.GetAssetInfo(@params);
                default:
                    return new ErrorResponse(
                        $"Unknown asset action: {subAction}. Valid: get_all, get_info");
            }
        }

        private static object HandleSimulationAction(JObject @params, string subAction)
        {
            // Simulation requires play mode - add warning if not in play mode
            if (!Application.isPlaying)
            {
                return new ErrorResponse(
                    "Input simulation requires Play mode. " +
                    "Enter Play mode first to use simulation features.");
            }

            switch (subAction)
            {
                case "key_press":
                    return InputSimulation.SimulateKeyPress(@params);
                case "key_hold":
                    return InputSimulation.SimulateKeyHold(@params);
                case "key_release":
                    return InputSimulation.SimulateKeyRelease(@params);
                case "button_press":
                    return InputSimulation.SimulateButtonPress(@params);
                case "axis":
                    return InputSimulation.SimulateAxis(@params);
                case "vector2":
                    return InputSimulation.SimulateVector2(@params);
                case "mouse_move":
                    return InputSimulation.SimulateMouseMove(@params);
                case "mouse_click":
                    return InputSimulation.SimulateMouseClick(@params);
                case "touch":
                    return InputSimulation.SimulateTouch(@params);
                default:
                    return new ErrorResponse(
                        $"Unknown simulation action: {subAction}. Valid: " +
                        "key_press, key_hold, key_release, button_press, axis, vector2, " +
                        "mouse_move, mouse_click, touch");
            }
        }

        private static object HandleStateAction(JObject @params, string subAction)
        {
            switch (subAction)
            {
                case "get_action_value":
                    return InputStateReader.GetActionValue(@params);
                case "get_all_actions":
                    return InputStateReader.GetAllActions(@params);
                case "is_action_pressed":
                    return InputStateReader.IsActionPressed(@params);
                case "get_control_value":
                    return InputStateReader.GetControlValue(@params);
                default:
                    return new ErrorResponse(
                        $"Unknown state action: {subAction}. Valid: " +
                        "get_action_value, get_all_actions, is_action_pressed, get_control_value");
            }
        }

        #endregion

        #region Parameter Normalization

        private static JObject NormalizeParams(JObject source)
        {
            if (source == null)
            {
                return new JObject();
            }

            var normalized = new JObject();
            var properties = ExtractProperties(source);
            
            if (properties != null)
            {
                foreach (var prop in properties.Properties())
                {
                    normalized[NormalizeKey(prop.Name, true)] = NormalizeToken(prop.Value);
                }
            }

            foreach (var prop in source.Properties())
            {
                if (string.Equals(prop.Name, "properties", StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }
                normalized[NormalizeKey(prop.Name, true)] = NormalizeToken(prop.Value);
            }

            return normalized;
        }

        private static JObject ExtractProperties(JObject source)
        {
            if (source == null)
            {
                return null;
            }

            if (!source.TryGetValue("properties", StringComparison.OrdinalIgnoreCase, out var token))
            {
                return null;
            }

            if (token == null || token.Type == JTokenType.Null)
            {
                return null;
            }

            if (token is JObject obj)
            {
                return obj;
            }

            if (token.Type == JTokenType.String)
            {
                try
                {
                    return JToken.Parse(token.ToString()) as JObject;
                }
                catch (JsonException ex)
                {
                    throw new JsonException(
                        $"Failed to parse 'properties' JSON string. Raw value: {token}",
                        ex);
                }
            }

            return null;
        }

        private static string NormalizeKey(string key, bool allowAliases)
        {
            if (string.IsNullOrEmpty(key))
            {
                return key;
            }
            
            if (string.Equals(key, "action", StringComparison.OrdinalIgnoreCase))
            {
                return "action";
            }
            
            if (allowAliases && ParamAliases.TryGetValue(key, out var alias))
            {
                return alias;
            }
            
            if (key.IndexOf('_') >= 0)
            {
                return StringCaseUtility.ToCamelCase(key);
            }
            
            return key;
        }

        private static JToken NormalizeToken(JToken token)
        {
            if (token == null)
            {
                return null;
            }

            if (token is JObject obj)
            {
                var normalized = new JObject();
                foreach (var prop in obj.Properties())
                {
                    normalized[NormalizeKey(prop.Name, false)] = NormalizeToken(prop.Value);
                }
                return normalized;
            }

            if (token is JArray array)
            {
                var normalized = new JArray();
                foreach (var item in array)
                {
                    normalized.Add(NormalizeToken(item));
                }
                return normalized;
            }

            return token;
        }

        #endregion

        #region Validation Helpers

        /// <summary>
        /// Validates that required parameters are present for an action.
        /// </summary>
        public static bool ValidateRequiredParams(JObject @params, string[] requiredParams, out string missingParam)
        {
            foreach (var param in requiredParams)
            {
                if (@params[param] == null || string.IsNullOrEmpty(@params[param].ToString()))
                {
                    missingParam = param;
                    return false;
                }
            }
            missingParam = null;
            return true;
        }

        /// <summary>
        /// Gets common binding path examples for documentation purposes.
        /// </summary>
        public static Dictionary<string, string[]> GetBindingPathExamples()
        {
            return new Dictionary<string, string[]>
            {
                ["Keyboard"] = new[]
                {
                    "<Keyboard>/space",
                    "<Keyboard>/w",
                    "<Keyboard>/escape",
                    "<Keyboard>/leftShift",
                    "<Keyboard>/anyKey"
                },
                ["Mouse"] = new[]
                {
                    "<Mouse>/leftButton",
                    "<Mouse>/rightButton",
                    "<Mouse>/middleButton",
                    "<Mouse>/position",
                    "<Mouse>/delta",
                    "<Mouse>/scroll"
                },
                ["Gamepad"] = new[]
                {
                    "<Gamepad>/buttonSouth",
                    "<Gamepad>/buttonNorth",
                    "<Gamepad>/buttonEast",
                    "<Gamepad>/buttonWest",
                    "<Gamepad>/leftStick",
                    "<Gamepad>/rightStick",
                    "<Gamepad>/dpad",
                    "<Gamepad>/leftTrigger",
                    "<Gamepad>/rightTrigger"
                },
                ["Touch"] = new[]
                {
                    "<Touchscreen>/primaryTouch/position",
                    "<Touchscreen>/primaryTouch/delta",
                    "<Touchscreen>/primaryTouch/press"
                },
                ["XR"] = new[]
                {
                    "<XRController>/trigger",
                    "<XRController>/grip",
                    "<XRController>/devicePosition",
                    "<XRController>/deviceRotation"
                },
                ["Composite"] = new[]
                {
                    "2DVector",
                    "1DAxis",
                    "ButtonWithOneModifier",
                    "ButtonWithTwoModifiers"
                }
            };
        }

        /// <summary>
        /// Gets action type options.
        /// </summary>
        public static Dictionary<string, string> GetActionTypes()
        {
            return new Dictionary<string, string>
            {
                ["Button"] = "Simple on/off button input",
                ["Value"] = "Continuous value input (requires expectedControlType)",
                ["PassThrough"] = "Like Value but doesn't reset to default when controls are released"
            };
        }

        /// <summary>
        /// Gets expected control type options.
        /// </summary>
        public static string[] GetExpectedControlTypes()
        {
            return new[]
            {
                "",
                "Button",
                "Axis",
                "Vector2",
                "Vector3",
                "Quaternion",
                "Integer",
                "Float",
                "Touch"
            };
        }

        #endregion
    }
}

#else

using System;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;

namespace MCPForUnity.Editor.Tools.InputSystem
{
    /// <summary>
    /// Fallback when Input System is not enabled.
    /// </summary>
    [McpForUnityTool("manage_input_system", AutoRegister = false, Group = "input")]
    public static class ManageInputSystem
    {
        public static object HandleCommand(JObject @params)
        {
            return new ErrorResponse("Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings.");
        }
    }
}

#endif
