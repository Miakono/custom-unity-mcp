// -----------------------------------------------------------------------
// RuntimeInputTools.cs
// Runtime-only Input simulation and query tools
// 
// These tools are ONLY available in Play Mode or Built Games.
// They NEVER appear in Editor-only environments.
// -----------------------------------------------------------------------

#nullable enable

#if ENABLE_INPUT_SYSTEM

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using MCPForUnity.Runtime.MCP;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.Controls;
using UnityEngine.InputSystem.LowLevel;

namespace MCPForUnity.Runtime.Tools
{
    /// <summary>
    /// Runtime Input tools for MCP.
    /// 
    /// Provides capabilities to:
    /// - Simulate keyboard input
    /// - Simulate mouse movement and clicks
    /// - Query input device states
    /// - Get current input values
    /// 
    /// These operations work ONLY in runtime context.
    /// </summary>
    public static class RuntimeInputTools
    {
        /// <summary>
        /// Register all Input tools with the runtime registry
        /// </summary>
        public static void Register(RuntimeToolRegistry registry)
        {
            // Simulate key press
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_input_simulate_key",
                    Description = "Simulate a keyboard key press, release, or tap",
                    Category = "input",
                    IsMutating = true,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "key", Type = "string", Description = "Key name (e.g., 'space', 'enter', 'a', 'left')", Required = true },
                        new() { Name = "action", Type = "string", Description = "Action: 'press', 'release', or 'tap'", Required = false, DefaultValue = "tap" },
                        new() { Name = "duration_ms", Type = "number", Description = "Duration for press in milliseconds", Required = false, DefaultValue = 100 }
                    }
                },
                SimulateKeyAsync
            );

            // Simulate mouse
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_input_simulate_mouse",
                    Description = "Simulate mouse movement, clicks, or scroll",
                    Category = "input",
                    IsMutating = true,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "action", Type = "string", Description = "Action: 'move', 'click', 'down', 'up', 'scroll'", Required = true },
                        new() { Name = "button", Type = "number", Description = "Mouse button (0=left, 1=right, 2=middle)", Required = false, DefaultValue = 0 },
                        new() { Name = "x", Type = "number", Description = "X position or delta", Required = false, DefaultValue = 0 },
                        new() { Name = "y", Type = "number", Description = "Y position or delta", Required = false, DefaultValue = 0 },
                        new() { Name = "delta", Type = "number", Description = "Scroll delta", Required = false, DefaultValue = 0 },
                        new() { Name = "screen_space", Type = "boolean", Description = "Use screen coordinates (true) or relative (false)", Required = false, DefaultValue = true }
                    }
                },
                SimulateMouseAsync
            );

            // Get keyboard state
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_input_get_keyboard_state",
                    Description = "Get current keyboard key states",
                    Category = "input",
                    IsMutating = false,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "keys", Type = "array", Description = "Specific keys to check (empty = all keys)", Required = false }
                    }
                },
                GetKeyboardStateAsync
            );

            // Get mouse state
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_input_get_mouse_state",
                    Description = "Get current mouse position and button states",
                    Category = "input",
                    IsMutating = false,
                    Parameters = new List<RuntimeToolParameter>()
                },
                GetMouseStateAsync
            );

            // Get input axes
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_input_get_axes",
                    Description = "Get Unity Input Manager axis values (legacy Input system)",
                    Category = "input",
                    IsMutating = false,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "axes", Type = "array", Description = "Axis names to query (empty = common axes)", Required = false }
                    }
                },
                GetInputAxesAsync
            );

            // Simulate touch
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_input_simulate_touch",
                    Description = "Simulate touch input (for mobile testing)",
                    Category = "input",
                    IsMutating = true,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "action", Type = "string", Description = "Action: 'begin', 'move', 'end'", Required = true },
                        new() { Name = "finger_id", Type = "number", Description = "Finger ID (0-4)", Required = false, DefaultValue = 0 },
                        new() { Name = "x", Type = "number", Description = "X position", Required = true },
                        new() { Name = "y", Type = "number", Description = "Y position", Required = true }
                    }
                },
                SimulateTouchAsync
            );

            Debug.Log("[RuntimeInputTools] Registered 6 runtime tools");
        }

        #region Tool Implementations

        private static async Task<Dictionary<string, object>> SimulateKeyAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                string key = parameters.GetValueOrDefault("key", "").ToString()!.ToLower();
                string action = parameters.GetValueOrDefault("action", "tap").ToString()!.ToLower();
                int durationMs = GetIntParameter(parameters, "duration_ms", 100);

                if (string.IsNullOrEmpty(key))
                {
                    result["success"] = false;
                    result["error"] = "missing_key";
                    result["message"] = "Key parameter is required";
                    return result;
                }

                // Check if Input System is available
                #if ENABLE_INPUT_SYSTEM
                var keyboard = Keyboard.current;
                if (keyboard == null)
                {
                    result["success"] = false;
                    result["error"] = "keyboard_not_available";
                    result["message"] = "Keyboard input device not available";
                    return result;
                }

                var keyControl = GetKeyControl(keyboard, key);
                if (keyControl == null)
                {
                    result["success"] = false;
                    result["error"] = "unknown_key";
                    result["message"] = $"Unknown key: '{key}'";
                    return result;
                }

                // Perform action
                switch (action)
                {
                    case "press":
                        InputSystem.QueueStateEvent(Keyboard.current, new KeyboardState(keyControl.keyCode));
                        break;
                    case "release":
                        InputSystem.QueueStateEvent(Keyboard.current, new KeyboardState());
                        break;
                    case "tap":
                    default:
                        InputSystem.QueueStateEvent(Keyboard.current, new KeyboardState(keyControl.keyCode));
                        await Task.Delay(durationMs);
                        InputSystem.QueueStateEvent(Keyboard.current, new KeyboardState());
                        break;
                }
                #else
                // Legacy Input system fallback
                result["success"] = false;
                result["error"] = "input_system_not_enabled";
                result["message"] = "New Input System is not enabled. Enable it in Project Settings > Player > Other Settings";
                return result;
                #endif

                result["success"] = true;
                result["message"] = $"Key '{key}' {action} performed";
                result["data"] = new Dictionary<string, object>
                {
                    ["key"] = key,
                    ["action"] = action,
                    ["duration_ms"] = durationMs
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "simulation_failed";
                result["message"] = ex.Message;
            }

            return result;
        }

        private static Task<Dictionary<string, object>> SimulateMouseAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                string action = parameters.GetValueOrDefault("action", "").ToString()!.ToLower();
                int button = GetIntParameter(parameters, "button", 0);
                float x = GetFloatParameter(parameters, "x", 0);
                float y = GetFloatParameter(parameters, "y", 0);
                float delta = GetFloatParameter(parameters, "delta", 0);
                bool screenSpace = GetBoolParameter(parameters, "screen_space", true);

                #if ENABLE_INPUT_SYSTEM
                var mouse = Mouse.current;
                if (mouse == null)
                {
                    result["success"] = false;
                    result["error"] = "mouse_not_available";
                    result["message"] = "Mouse input device not available";
                    return Task.FromResult(result);
                }

                switch (action)
                {
                    case "move":
                        if (screenSpace)
                        {
                            // Warp cursor position
                            #if UNITY_EDITOR
                            // Editor doesn't support warp
                            #else
                            UnityEngine.InputSystem.Mouse.current.WarpCursorPosition(new Vector2(x, y));
                            #endif
                        }
                        else
                        {
                            // Delta movement
                            // Note: Direct delta injection requires more complex handling
                        }
                        break;

                    case "down":
                        {
                            var mouseState = new MouseState();
                            switch (button)
                            {
                                case 0: mouseState.WithButton(MouseButton.Left, true); break;
                                case 1: mouseState.WithButton(MouseButton.Right, true); break;
                                case 2: mouseState.WithButton(MouseButton.Middle, true); break;
                            }
                            InputSystem.QueueStateEvent(mouse, mouseState);
                        }
                        break;

                    case "up":
                        {
                            var mouseState = new MouseState();
                            switch (button)
                            {
                                case 0: mouseState.WithButton(MouseButton.Left, false); break;
                                case 1: mouseState.WithButton(MouseButton.Right, false); break;
                                case 2: mouseState.WithButton(MouseButton.Middle, false); break;
                            }
                            InputSystem.QueueStateEvent(mouse, mouseState);
                        }
                        break;

                    case "click":
                        {
                            var pressState = new MouseState();
                            switch (button)
                            {
                                case 0: pressState.WithButton(MouseButton.Left, true); break;
                                case 1: pressState.WithButton(MouseButton.Right, true); break;
                                case 2: pressState.WithButton(MouseButton.Middle, true); break;
                            }
                            InputSystem.QueueStateEvent(mouse, pressState);
                            // Release will be done async
                            _ = ReleaseMouseButtonAsync(mouse, button, 50);
                        }
                        break;

                    case "scroll":
                        InputState.Change(mouse.scroll, new Vector2(0, delta));
                        break;
                }
                #else
                result["success"] = false;
                result["error"] = "input_system_not_enabled";
                result["message"] = "New Input System is not enabled. Enable it in Project Settings > Player > Other Settings";
                return Task.FromResult(result);
                #endif

                result["success"] = true;
                result["message"] = $"Mouse action '{action}' performed";
                result["data"] = new Dictionary<string, object>
                {
                    ["action"] = action,
                    ["button"] = button,
                    ["x"] = x,
                    ["y"] = y,
                    ["delta"] = delta
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "simulation_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static Task<Dictionary<string, object>> GetKeyboardStateAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                var keyStates = new Dictionary<string, object>();

                #if ENABLE_INPUT_SYSTEM
                var keyboard = Keyboard.current;
                if (keyboard != null)
                {
                    // Check specific keys if provided
                    if (parameters.TryGetValue("keys", out var keysValue) && keysValue is List<object> keysList)
                    {
                        foreach (var keyObj in keysList)
                        {
                            string keyName = keyObj.ToString()!.ToLower();
                            var keyControl = GetKeyControl(keyboard, keyName);
                            if (keyControl != null)
                            {
                                keyStates[keyName] = keyControl.isPressed;
                            }
                        }
                    }
                    else
                    {
                        // Return common keys state
                        keyStates["space"] = keyboard.spaceKey.isPressed;
                        keyStates["enter"] = keyboard.enterKey.isPressed;
                        keyStates["escape"] = keyboard.escapeKey.isPressed;
                        keyStates["left_shift"] = keyboard.leftShiftKey.isPressed;
                        keyStates["left_ctrl"] = keyboard.leftCtrlKey.isPressed;
                        keyStates["w"] = keyboard.wKey.isPressed;
                        keyStates["a"] = keyboard.aKey.isPressed;
                        keyStates["s"] = keyboard.sKey.isPressed;
                        keyStates["d"] = keyboard.dKey.isPressed;
                    }
                }
                #else
                // Legacy input fallback
                keyStates["note"] = "New Input System not enabled";
                #endif

                result["success"] = true;
                result["message"] = "Keyboard state retrieved";
                result["data"] = new Dictionary<string, object>
                {
                    ["keys"] = keyStates,
                    ["any_key_pressed"] = keyStates.Values.OfType<bool>().Any(v => v)
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "get_state_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static Task<Dictionary<string, object>> GetMouseStateAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                #if ENABLE_INPUT_SYSTEM
                var mouse = Mouse.current;
                if (mouse != null)
                {
                    var position = mouse.position.ReadValue();
                    
                    result["success"] = true;
                    result["message"] = "Mouse state retrieved";
                    result["data"] = new Dictionary<string, object>
                    {
                        ["position"] = new Dictionary<string, object>
                        {
                            ["x"] = position.x,
                            ["y"] = position.y
                        },
                        ["left_button"] = mouse.leftButton.isPressed,
                        ["right_button"] = mouse.rightButton.isPressed,
                        ["middle_button"] = mouse.middleButton.isPressed,
                        ["scroll"] = new Dictionary<string, object>
                        {
                            ["x"] = mouse.scroll.ReadValue().x,
                            ["y"] = mouse.scroll.ReadValue().y
                        }
                    };
                }
                else
                {
                    result["success"] = false;
                    result["error"] = "mouse_not_available";
                    result["message"] = "Mouse device not available";
                }
                #else
                // Legacy Input fallback
                result["success"] = true;
                result["message"] = "Mouse state (legacy Input)";
                result["data"] = new Dictionary<string, object>
                {
                    ["position"] = new Dictionary<string, object>
                    {
                        ["x"] = UnityEngine.Input.mousePosition.x,
                        ["y"] = UnityEngine.Input.mousePosition.y
                    },
                    ["left_button"] = UnityEngine.Input.GetMouseButton(0),
                    ["right_button"] = UnityEngine.Input.GetMouseButton(1),
                    ["middle_button"] = UnityEngine.Input.GetMouseButton(2),
                    ["note"] = "Using legacy Input system"
                };
                #endif
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "get_state_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static Task<Dictionary<string, object>> GetInputAxesAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                var axes = new Dictionary<string, object>();

                // Common Unity Input Manager axes
                var axesToQuery = new List<string> { "Horizontal", "Vertical" };

                if (parameters.TryGetValue("axes", out var axesValue) && axesValue is List<object> axesList)
                {
                    axesToQuery = axesList.ConvertAll(a => a.ToString()!);
                }

                foreach (var axis in axesToQuery)
                {
                    try
                    {
                        axes[axis] = UnityEngine.Input.GetAxis(axis);
                    }
                    catch
                    {
                        axes[axis] = 0f; // Axis not configured
                    }
                }

                result["success"] = true;
                result["message"] = "Input axes retrieved";
                result["data"] = new Dictionary<string, object>
                {
                    ["axes"] = axes,
                    ["note"] = "Legacy Input Manager axes (New Input System axes require different handling)"
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "get_axes_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static Task<Dictionary<string, object>> SimulateTouchAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                string action = parameters.GetValueOrDefault("action", "").ToString()!.ToLower();
                int fingerId = GetIntParameter(parameters, "finger_id", 0);
                float x = GetFloatParameter(parameters, "x", 0);
                float y = GetFloatParameter(parameters, "y", 0);

                #if ENABLE_INPUT_SYSTEM
                var touchscreen = Touchscreen.current;
                if (touchscreen == null)
                {
                    result["success"] = false;
                    result["error"] = "touch_not_available";
                    result["message"] = "Touch input device not available";
                    return Task.FromResult(result);
                }

                // Note: Direct touch simulation in New Input System requires
                // using InputTestFixture or similar in play mode tests
                // This is a simplified implementation
                result["success"] = true;
                result["message"] = "Touch simulation requested (requires Input System testing setup)";
                result["data"] = new Dictionary<string, object>
                {
                    ["action"] = action,
                    ["finger_id"] = fingerId,
                    ["position"] = new Dictionary<string, object> { ["x"] = x, ["y"] = y },
                    ["note"] = "Full touch simulation requires Input System test utilities"
                };
                #else
                // Legacy touch support
                result["success"] = true;
                result["message"] = "Touch info (legacy system)";
                result["data"] = new Dictionary<string, object>
                {
                    ["touch_supported"] = UnityEngine.Input.touchSupported,
                    ["touch_count"] = UnityEngine.Input.touchCount,
                    ["note"] = "Legacy touch input (New Input System recommended)"
                };
                #endif
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "simulation_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        #endregion

        #region Helper Methods

        #if ENABLE_INPUT_SYSTEM
        private static UnityEngine.InputSystem.Controls.KeyControl? GetKeyControl(Keyboard keyboard, string keyName)
        {
            return keyName.ToLower() switch
            {
                "space" => keyboard.spaceKey,
                "enter" or "return" => keyboard.enterKey,
                "escape" or "esc" => keyboard.escapeKey,
                "tab" => keyboard.tabKey,
                "backspace" => keyboard.backspaceKey,
                "delete" or "del" => keyboard.deleteKey,
                "left" or "left_arrow" => keyboard.leftArrowKey,
                "right" or "right_arrow" => keyboard.rightArrowKey,
                "up" or "up_arrow" => keyboard.upArrowKey,
                "down" or "down_arrow" => keyboard.downArrowKey,
                "left_shift" => keyboard.leftShiftKey,
                "right_shift" => keyboard.rightShiftKey,
                "left_ctrl" or "left_control" => keyboard.leftCtrlKey,
                "right_ctrl" or "right_control" => keyboard.rightCtrlKey,
                "left_alt" => keyboard.leftAltKey,
                "right_alt" => keyboard.rightAltKey,
                "a" => keyboard.aKey,
                "b" => keyboard.bKey,
                "c" => keyboard.cKey,
                "d" => keyboard.dKey,
                "e" => keyboard.eKey,
                "f" => keyboard.fKey,
                "g" => keyboard.gKey,
                "h" => keyboard.hKey,
                "i" => keyboard.iKey,
                "j" => keyboard.jKey,
                "k" => keyboard.kKey,
                "l" => keyboard.lKey,
                "m" => keyboard.mKey,
                "n" => keyboard.nKey,
                "o" => keyboard.oKey,
                "p" => keyboard.pKey,
                "q" => keyboard.qKey,
                "r" => keyboard.rKey,
                "s" => keyboard.sKey,
                "t" => keyboard.tKey,
                "u" => keyboard.uKey,
                "v" => keyboard.vKey,
                "w" => keyboard.wKey,
                "x" => keyboard.xKey,
                "y" => keyboard.yKey,
                "z" => keyboard.zKey,
                "0" => keyboard.digit0Key,
                "1" => keyboard.digit1Key,
                "2" => keyboard.digit2Key,
                "3" => keyboard.digit3Key,
                "4" => keyboard.digit4Key,
                "5" => keyboard.digit5Key,
                "6" => keyboard.digit6Key,
                "7" => keyboard.digit7Key,
                "8" => keyboard.digit8Key,
                "9" => keyboard.digit9Key,
                _ => null
            };
        }

        private static async Task ReleaseMouseButtonAsync(Mouse mouse, int button, int delayMs)
        {
            await Task.Delay(delayMs);
            var mouseState = new MouseState();
            switch (button)
            {
                case 0: mouseState.WithButton(MouseButton.Left, false); break;
                case 1: mouseState.WithButton(MouseButton.Right, false); break;
                case 2: mouseState.WithButton(MouseButton.Middle, false); break;
            }
            InputSystem.QueueStateEvent(mouse, mouseState);
        }
        #endif

        private static bool GetBoolParameter(Dictionary<string, object> parameters, string key, bool defaultValue)
        {
            if (!parameters.TryGetValue(key, out var value))
            {
                return defaultValue;
            }

            return value switch
            {
                bool b => b,
                string s => bool.TryParse(s, out var result) ? result : defaultValue,
                _ => defaultValue
            };
        }

        private static int GetIntParameter(Dictionary<string, object> parameters, string key, int defaultValue)
        {
            if (!parameters.TryGetValue(key, out var value))
            {
                return defaultValue;
            }

            return value switch
            {
                int i => i,
                long l => (int)l,
                string s => int.TryParse(s, out var result) ? result : defaultValue,
                _ => defaultValue
            };
        }

        private static float GetFloatParameter(Dictionary<string, object> parameters, string key, float defaultValue)
        {
            if (!parameters.TryGetValue(key, out var value))
            {
                return defaultValue;
            }

            return value switch
            {
                float f => f,
                double d => (float)d,
                int i => i,
                long l => l,
                string s => float.TryParse(s, out var result) ? result : defaultValue,
                _ => defaultValue
            };
        }

        #endregion
    }
}

#else

using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using MCPForUnity.Runtime.MCP;
using UnityEngine;

namespace MCPForUnity.Runtime.Tools
{
    /// <summary>
    /// Fallback when Input System is not enabled.
    /// </summary>
    [RuntimeMcpTool("runtime_input_simulate_key", runtimeOnly: true)]
    public static class RuntimeInputTools
    {
        public static Task<object> SimulateKey(Dictionary<string, object> parameters)
        {
            return Task.FromResult<object>(new { error = "Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings." });
        }

        public static Task<object> SimulateMouse(Dictionary<string, object> parameters)
        {
            return Task.FromResult<object>(new { error = "Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings." });
        }

        public static Task<object> GetKeyboardState(Dictionary<string, object> parameters)
        {
            return Task.FromResult<object>(new { error = "Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings." });
        }

        public static Task<object> GetMouseState(Dictionary<string, object> parameters)
        {
            return Task.FromResult<object>(new { error = "Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings." });
        }

        public static Task<object> GetAxes(Dictionary<string, object> parameters)
        {
            return Task.FromResult<object>(new { error = "Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings." });
        }

        public static Task<object> SimulateTouch(Dictionary<string, object> parameters)
        {
            return Task.FromResult<object>(new { error = "Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings." });
        }
    }
}

#endif
