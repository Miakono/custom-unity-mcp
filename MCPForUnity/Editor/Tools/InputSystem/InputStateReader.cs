#if ENABLE_INPUT_SYSTEM

using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Runtime.Helpers;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.Controls;
using UnityInputSystem = UnityEngine.InputSystem.InputSystem;

namespace MCPForUnity.Editor.Tools.InputSystem
{
    /// <summary>
    /// Reads current input state from the Unity Input System.
    /// Works in both Editor and Play mode for querying input values.
    /// </summary>
    public static class InputStateReader
    {
        #region Action State Reading

        public static object GetActionValue(JObject @params)
        {
            try
            {
                if (!Application.isPlaying)
                {
                    return new ErrorResponse("GetActionValue requires Play mode");
                }

                string assetPath = @params["assetPath"]?.ToString();
                string mapName = @params["actionMap"]?.ToString();
                string actionName = @params["actionName"]?.ToString();

                if (string.IsNullOrEmpty(actionName))
                {
                    return new ErrorResponse("actionName is required");
                }

                // Try to find the action
                InputAction action = null;
                
                if (!string.IsNullOrEmpty(assetPath) && !string.IsNullOrEmpty(mapName))
                {
                    // Load from specific asset
                    var asset = UnityEditor.AssetDatabase.LoadAssetAtPath<InputActionAsset>(assetPath);
                    var map = asset?.FindActionMap(mapName);
                    action = map?.FindAction(actionName);
                }
                else
                {
                    // Search in all active assets
                    action = FindActionInActiveAssets(actionName);
                }

                if (action == null)
                {
                    return new ErrorResponse($"Action '{actionName}' not found");
                }

                // Enable action if needed
                if (!action.enabled)
                {
                    action.Enable();
                }

                // Read value based on action type
                object value = ReadActionValue(action);

                return new SuccessResponse($"Retrieved value for action '{actionName}'", new
                {
                    actionName = action.name,
                    actionType = action.type.ToString(),
                    expectedControlType = action.expectedControlType,
                    value = value,
                    phase = action.phase.ToString(),
                    enabled = action.enabled
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get action value: {ex.Message}");
            }
        }

        public static object GetAllActions(JObject @params)
        {
            try
            {
                if (!Application.isPlaying)
                {
                    return new ErrorResponse("GetAllActions requires Play mode");
                }

                string assetPath = @params["assetPath"]?.ToString();
                string mapName = @params["actionMap"]?.ToString();

                List<InputAction> actions = new List<InputAction>();

                if (!string.IsNullOrEmpty(assetPath))
                {
                    var asset = UnityEditor.AssetDatabase.LoadAssetAtPath<InputActionAsset>(assetPath);
                    if (asset == null)
                    {
                        return new ErrorResponse($"Could not load asset: {assetPath}");
                    }

                    if (!string.IsNullOrEmpty(mapName))
                    {
                        var map = asset.FindActionMap(mapName);
                        if (map != null)
                        {
                            actions.AddRange(map.actions);
                        }
                    }
                    else
                    {
                        foreach (var map in asset.actionMaps)
                        {
                            actions.AddRange(map.actions);
                        }
                    }
                }
                else
                {
                    // Get all active actions
                    actions.AddRange(GetAllActiveActions());
                }

                var actionData = actions.Select(a => new
                {
                    name = a.name,
                    mapName = a.actionMap?.name,
                    type = a.type.ToString(),
                    expectedControlType = a.expectedControlType,
                    phase = a.enabled ? a.phase.ToString() : "Disabled",
                    bindings = a.bindings.Select(b => new
                    {
                        path = b.path,
                        groups = b.groups
                    }).ToList()
                }).ToList();

                return new SuccessResponse($"Found {actionData.Count} actions", new { actions = actionData });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get all actions: {ex.Message}");
            }
        }

        public static object IsActionPressed(JObject @params)
        {
            try
            {
                if (!Application.isPlaying)
                {
                    return new ErrorResponse("IsActionPressed requires Play mode");
                }

                string assetPath = @params["assetPath"]?.ToString();
                string mapName = @params["actionMap"]?.ToString();
                string actionName = @params["actionName"]?.ToString();

                if (string.IsNullOrEmpty(actionName))
                {
                    return new ErrorResponse("actionName is required");
                }

                InputAction action = null;
                
                if (!string.IsNullOrEmpty(assetPath) && !string.IsNullOrEmpty(mapName))
                {
                    var asset = UnityEditor.AssetDatabase.LoadAssetAtPath<InputActionAsset>(assetPath);
                    var map = asset?.FindActionMap(mapName);
                    action = map?.FindAction(actionName);
                }
                else
                {
                    action = FindActionInActiveAssets(actionName);
                }

                if (action == null)
                {
                    return new ErrorResponse($"Action '{actionName}' not found");
                }

                if (!action.enabled)
                {
                    action.Enable();
                }

                bool isPressed = action.IsPressed();
                bool wasPressed = action.WasPressedThisFrame();
                bool wasReleased = action.WasReleasedThisFrame();

                return new SuccessResponse($"Action '{actionName}' press state retrieved", new
                {
                    actionName = action.name,
                    isPressed = isPressed,
                    wasPressedThisFrame = wasPressed,
                    wasReleasedThisFrame = wasReleased,
                    trigger = action.triggered
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to check action pressed: {ex.Message}");
            }
        }

        #endregion

        #region Control State Reading

        public static object GetControlValue(JObject @params)
        {
            try
            {
                string controlPath = @params["properties"]?["controlPath"]?.ToString();
                string deviceType = @params["properties"]?["deviceType"]?.ToString() ?? "any";

                if (string.IsNullOrEmpty(controlPath))
                {
                    return new ErrorResponse("properties.controlPath is required (e.g., '<Keyboard>/space', '<Mouse>/position')");
                }

                InputControl control = null;

                // Try to find the control
                if (controlPath.StartsWith("<"))
                {
                    // Full path like <Keyboard>/space
                    control = UnityInputSystem.FindControl(controlPath);
                }
                else
                {
                    // Search by name across all devices
                    control = FindControlByName(controlPath, deviceType);
                }

                if (control == null)
                {
                    // Return available devices for debugging
                    var availableDevices = UnityInputSystem.devices.Select(d => $"{d.name} ({d.layout})").ToList();
                    
                    return new ErrorResponse(
                        $"Control '{controlPath}' not found. " +
                        $"Available devices: {string.Join(", ", availableDevices.Take(10))}...");
                }

                object value = ReadControlValue(control);

                return new SuccessResponse($"Retrieved value for control '{controlPath}'", new
                {
                    controlPath = control.path,
                    controlName = control.name,
                    deviceName = control.device?.name,
                    deviceType = control.device?.layout,
                    value = value,
                    valueType = control.valueType?.Name
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get control value: {ex.Message}");
            }
        }

        #endregion

        #region Helper Methods

        private static InputAction FindActionInActiveAssets(string actionName)
        {
            // Search in all loaded InputActionAssets
            var guids = UnityEditor.AssetDatabase.FindAssets("t:InputActionAsset");
            
            foreach (var guid in guids)
            {
                string path = UnityEditor.AssetDatabase.GUIDToAssetPath(guid);
                var asset = UnityEditor.AssetDatabase.LoadAssetAtPath<InputActionAsset>(path);
                
                if (asset != null)
                {
                    foreach (var map in asset.actionMaps)
                    {
                        var action = map.FindAction(actionName);
                        if (action != null)
                        {
                            return action;
                        }
                    }
                }
            }

            // Also search in PlayerInput components
            var playerInputs = UnityObjectCompatibility.FindObjectsByType<PlayerInput>();
            foreach (var playerInput in playerInputs)
            {
                var action = playerInput.actions?.FindAction(actionName);
                if (action != null)
                {
                    return action;
                }
            }

            return null;
        }

        private static List<InputAction> GetAllActiveActions()
        {
            var actions = new List<InputAction>();
            
            // Get from all loaded assets
            var guids = UnityEditor.AssetDatabase.FindAssets("t:InputActionAsset");
            foreach (var guid in guids)
            {
                string path = UnityEditor.AssetDatabase.GUIDToAssetPath(guid);
                var asset = UnityEditor.AssetDatabase.LoadAssetAtPath<InputActionAsset>(path);
                
                if (asset != null)
                {
                    foreach (var map in asset.actionMaps)
                    {
                        actions.AddRange(map.actions);
                    }
                }
            }

            // Get from PlayerInput components
            var playerInputs = UnityObjectCompatibility.FindObjectsByType<PlayerInput>();
            foreach (var playerInput in playerInputs)
            {
                if (playerInput.actions != null)
                {
                    foreach (var map in playerInput.actions.actionMaps)
                    {
                        actions.AddRange(map.actions);
                    }
                }
            }

            return actions.Distinct().ToList();
        }

        private static InputControl FindControlByName(string name, string deviceType)
        {
            foreach (var device in UnityInputSystem.devices)
            {
                if (deviceType != "any" && !device.layout.Contains(deviceType, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                var control = device.TryGetChildControl(name);
                if (control != null)
                {
                    return control;
                }
            }

            return null;
        }

        private static object ReadActionValue(InputAction action)
        {
            try
            {
                switch (action.expectedControlType)
                {
                    case "Button":
                    case "Digital":
                        return action.ReadValue<float>() > 0;

                    case "Axis":
                    case "Float":
                        return action.ReadValue<float>();

                    case "Vector2":
                        var vec2 = action.ReadValue<Vector2>();
                        return new { x = vec2.x, y = vec2.y };

                    case "Vector3":
                        var vec3 = action.ReadValue<Vector3>();
                        return new { x = vec3.x, y = vec3.y, z = vec3.z };

                    case "Quaternion":
                        var quat = action.ReadValue<Quaternion>();
                        return new { x = quat.x, y = quat.y, z = quat.z, w = quat.w };

                    case "Integer":
                        return action.ReadValue<int>();

                    case "Touch":
                        // Touch is complex, return basic info
                        return new { type = "Touch", available = true };

                    default:
                        // Try to read as float fallback
                        return action.ReadValue<float>();
                }
            }
            catch (Exception ex)
            {
                return $"<error reading value: {ex.Message}>";
            }
        }

        private static object ReadControlValue(InputControl control)
        {
            try
            {
                if (control is ButtonControl button)
                {
                    return new
                    {
                        isPressed = button.isPressed,
                        wasPressedThisFrame = button.wasPressedThisFrame,
                        wasReleasedThisFrame = button.wasReleasedThisFrame
                    };
                }

                if (control is AxisControl axis)
                {
                    return axis.ReadValue();
                }

                if (control is Vector2Control vec2)
                {
                    var value = vec2.ReadValue();
                    return new { x = value.x, y = value.y };
                }

                if (control is Vector3Control vec3)
                {
                    var value = vec3.ReadValue();
                    return new { x = value.x, y = value.y, z = value.z };
                }

                if (control is QuaternionControl quat)
                {
                    var value = quat.ReadValue();
                    return new { x = value.x, y = value.y, z = value.z, w = value.w };
                }

                if (control is IntegerControl integer)
                {
                    return integer.ReadValue();
                }

                if (control is KeyControl key)
                {
                    return new
                    {
                        isPressed = key.isPressed,
                        keyCode = key.keyCode.ToString()
                    };
                }

                // Default: try to read as object
                return control.ReadValueAsObject()?.ToString();
            }
            catch (Exception ex)
            {
                return $"<error reading control: {ex.Message}>";
            }
        }

        #endregion

        #region Composite Binding Helpers

        public static object GetCompositeBindingInfo(JObject @params)
        {
            try
            {
                string assetPath = @params["assetPath"]?.ToString();
                string mapName = @params["actionMap"]?.ToString();
                string actionName = @params["actionName"]?.ToString();

                if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(mapName) || string.IsNullOrEmpty(actionName))
                {
                    return new ErrorResponse("assetPath, actionMap, and actionName are required");
                }

                var asset = UnityEditor.AssetDatabase.LoadAssetAtPath<InputActionAsset>(assetPath);
                var map = asset?.FindActionMap(mapName);
                var action = map?.FindAction(actionName);

                if (action == null)
                {
                    return new ErrorResponse($"Action '{actionName}' not found");
                }

                var composites = new List<object>();
                
                for (int i = 0; i < action.bindings.Count; i++)
                {
                    var binding = action.bindings[i];
                    
                    if (binding.isComposite)
                    {
                        var parts = new List<object>();
                        
                        // Collect parts of this composite
                        for (int j = i + 1; j < action.bindings.Count && action.bindings[j].isPartOfComposite; j++)
                        {
                            parts.Add(new
                            {
                                name = action.bindings[j].name,
                                path = action.bindings[j].path,
                                index = j
                            });
                        }

                        composites.Add(new
                        {
                            name = binding.name,
                            path = binding.path, // e.g., "2DVector"
                            index = i,
                            parts = parts
                        });
                    }
                }

                return new SuccessResponse($"Found {composites.Count} composite bindings", new
                {
                    actionName = action.name,
                    composites = composites
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get composite binding info: {ex.Message}");
            }
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
    public static class InputStateReader
    {
        public static object GetActionValue(JObject @params) => ErrorResponse();
        public static object GetAllActions(JObject @params) => ErrorResponse();
        public static object IsActionPressed(JObject @params) => ErrorResponse();
        public static object GetControlValue(JObject @params) => ErrorResponse();

        private static object ErrorResponse()
        {
            return new ErrorResponse("Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings.");
        }
    }
}

#endif
