#if ENABLE_INPUT_SYSTEM

using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityInputSystem = UnityEngine.InputSystem.InputSystem;

namespace MCPForUnity.Editor.Tools.InputSystem
{
    /// <summary>
    /// Runtime input simulation for Unity Input System.
    /// This is for PLAY MODE ONLY - allows simulating input during runtime.
    /// </summary>
    public static class InputSimulation
    {
        private static readonly Dictionary<string, InputDevice> _simulatedDevices = new Dictionary<string, InputDevice>();
        private static bool _isInitialized = false;

        #region Initialization

        private static void EnsureInitialized()
        {
            if (_isInitialized) return;

            // Check if we're in play mode
            if (!Application.isPlaying)
            {
                throw new InvalidOperationException("Input simulation is only available in Play mode");
            }

            // Input System is ready for simulation
            _isInitialized = true;
        }

        private static void Cleanup()
        {
            foreach (var device in _simulatedDevices.Values)
            {
                if (device != null && device.added)
                {
                    UnityInputSystem.RemoveDevice(device);
                }
            }
            _simulatedDevices.Clear();
            _isInitialized = false;
        }

        #endregion

        #region Key Simulation

        public static object SimulateKeyPress(JObject @params)
        {
            try
            {
                EnsureInitialized();

                string keyName = @params["properties"]?["key"]?.ToString();
                double duration = @params["properties"]?["duration"]?.ToObject<double>() ?? 0.1;

                if (string.IsNullOrEmpty(keyName))
                {
                    return new ErrorResponse("properties.key is required (e.g., 'Space', 'W', 'Escape')");
                }

                var key = ParseKey(keyName);
                if (key == Key.None)
                {
                    return new ErrorResponse($"Unknown key: {keyName}");
                }

                // Press and release the key
                var keyboard = GetOrCreateKeyboard();
                UnityInputSystem.QueueStateEvent(keyboard, new KeyboardState(key));
                
                // Schedule release
                if (duration > 0)
                {
                    UnityInputSystem.QueueStateEvent(keyboard, new KeyboardState(), Time.time + (float)duration);
                }

                return new SuccessResponse($"Simulated key press: {keyName}", new { key = keyName, duration });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to simulate key press: {ex.Message}");
            }
        }

        public static object SimulateKeyHold(JObject @params)
        {
            try
            {
                EnsureInitialized();

                string keyName = @params["properties"]?["key"]?.ToString();

                if (string.IsNullOrEmpty(keyName))
                {
                    return new ErrorResponse("properties.key is required");
                }

                var key = ParseKey(keyName);
                if (key == Key.None)
                {
                    return new ErrorResponse($"Unknown key: {keyName}");
                }

                var keyboard = GetOrCreateKeyboard();
                UnityInputSystem.QueueStateEvent(keyboard, new KeyboardState(key));

                return new SuccessResponse($"Holding key: {keyName}", new { key = keyName, action = "hold" });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to hold key: {ex.Message}");
            }
        }

        public static object SimulateKeyRelease(JObject @params)
        {
            try
            {
                EnsureInitialized();

                string keyName = @params["properties"]?["key"]?.ToString();

                if (string.IsNullOrEmpty(keyName))
                {
                    return new ErrorResponse("properties.key is required");
                }

                var key = ParseKey(keyName);
                if (key == Key.None)
                {
                    return new ErrorResponse($"Unknown key: {keyName}");
                }

                var keyboard = GetOrCreateKeyboard();
                UnityInputSystem.QueueStateEvent(keyboard, new KeyboardState());

                return new SuccessResponse($"Released key: {keyName}", new { key = keyName, action = "release" });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to release key: {ex.Message}");
            }
        }

        #endregion

        #region Button Simulation

        public static object SimulateButtonPress(JObject @params)
        {
            try
            {
                EnsureInitialized();

                string button = @params["properties"]?["button"]?.ToString() ?? "buttonSouth";
                string deviceType = @params["properties"]?["device"]?.ToString() ?? "gamepad";
                double duration = @params["properties"]?["duration"]?.ToObject<double>() ?? 0.1;

                if (deviceType.ToLower() == "gamepad")
                {
                    var gamepad = GetOrCreateGamepad();
                    var control = ParseGamepadButton(button);
                    
                    // Simulate button press
                    var state = new GamepadState
                    {
                        buttons = (uint)(1 << (int)control)
                    };
                    UnityInputSystem.QueueStateEvent(gamepad, state);

                    return new SuccessResponse($"Simulated {button} press on {deviceType}", 
                        new { button, device = deviceType, duration });
                }
                else if (deviceType.ToLower() == "mouse")
                {
                    var mouse = GetOrCreateMouse();
                    var buttonControl = ParseMouseButton(button);
                    
                    // Press mouse button
                    var mouseState = new MouseState();
                    mouseState.WithButton(buttonControl, true);
                    UnityInputSystem.QueueStateEvent(mouse, mouseState);

                    return new SuccessResponse($"Simulated {button} press on {deviceType}",
                        new { button, device = deviceType, duration });
                }

                return new ErrorResponse($"Unsupported device type: {deviceType}");
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to simulate button press: {ex.Message}");
            }
        }

        #endregion

        #region Axis Simulation

        public static object SimulateAxis(JObject @params)
        {
            try
            {
                EnsureInitialized();

                string axisName = @params["properties"]?["axisName"]?.ToString();
                float value = @params["properties"]?["value"]?.ToObject<float>() ?? 0f;

                if (string.IsNullOrEmpty(axisName))
                {
                    return new ErrorResponse("properties.axisName is required");
                }

                // Try to find the axis on gamepad first
                var gamepad = GetOrCreateGamepad();
                
                switch (axisName.ToLower())
                {
                    case "lefttrigger":
                    case "left_trigger":
                        UnityInputSystem.QueueStateEvent(gamepad, new GamepadState { leftTrigger = value });
                        break;
                    case "righttrigger":
                    case "right_trigger":
                        UnityInputSystem.QueueStateEvent(gamepad, new GamepadState { rightTrigger = value });
                        break;
                    default:
                        return new ErrorResponse($"Unknown axis: {axisName}");
                }

                return new SuccessResponse($"Simulated axis '{axisName}' = {value}", 
                    new { axisName, value });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to simulate axis: {ex.Message}");
            }
        }

        public static object SimulateVector2(JObject @params)
        {
            try
            {
                EnsureInitialized();

                string controlName = @params["properties"]?["control"]?.ToString() ?? "leftStick";
                float x = @params["properties"]?["x"]?.ToObject<float>() ?? 0f;
                float y = @params["properties"]?["y"]?.ToObject<float>() ?? 0f;

                var gamepad = GetOrCreateGamepad();
                var vector = new Vector2(x, y);

                var state = new GamepadState();
                switch (controlName.ToLower())
                {
                    case "leftstick":
                    case "left_stick":
                        state.leftStick = vector;
                        break;
                    case "rightstick":
                    case "right_stick":
                        state.rightStick = vector;
                        break;
                    case "dpad":
                        uint buttons = 0;
                        if (vector.y > 0.5f) buttons |= 1u << (int)GamepadButton.DpadUp;
                        if (vector.x > 0.5f) buttons |= 1u << (int)GamepadButton.DpadRight;
                        if (vector.y < -0.5f) buttons |= 1u << (int)GamepadButton.DpadDown;
                        if (vector.x < -0.5f) buttons |= 1u << (int)GamepadButton.DpadLeft;
                        state.buttons = buttons;
                        break;
                    default:
                        return new ErrorResponse($"Unknown Vector2 control: {controlName}");
                }

                UnityInputSystem.QueueStateEvent(gamepad, state);

                return new SuccessResponse($"Simulated {controlName} = ({x}, {y})", 
                    new { control = controlName, x, y });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to simulate Vector2: {ex.Message}");
            }
        }

        #endregion

        #region Mouse Simulation

        public static object SimulateMouseMove(JObject @params)
        {
            try
            {
                EnsureInitialized();

                float deltaX = @params["properties"]?["deltaX"]?.ToObject<float>() ?? 0f;
                float deltaY = @params["properties"]?["deltaY"]?.ToObject<float>() ?? 0f;
                float? positionX = @params["properties"]?["positionX"]?.ToObject<float?>();
                float? positionY = @params["properties"]?["positionY"]?.ToObject<float?>();

                var mouse = GetOrCreateMouse();

                var state = new MouseState
                {
                    delta = new Vector2(deltaX, deltaY)
                };

                if (positionX.HasValue && positionY.HasValue)
                {
                    state.position = new Vector2(positionX.Value, positionY.Value);
                }

                UnityInputSystem.QueueStateEvent(mouse, state);

                return new SuccessResponse($"Simulated mouse move: delta=({deltaX}, {deltaY})",
                    new { deltaX, deltaY, positionX, positionY });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to simulate mouse move: {ex.Message}");
            }
        }

        public static object SimulateMouseClick(JObject @params)
        {
            try
            {
                EnsureInitialized();

                string button = @params["properties"]?["button"]?.ToString() ?? "left";
                int buttonIndex = button.ToLower() switch
                {
                    "left" => 0,
                    "right" => 1,
                    "middle" => 2,
                    _ => 0
                };

                var mouse = GetOrCreateMouse();

                // Press
                var pressState = new MouseState();
                pressState.WithButton((MouseButton)buttonIndex, true);
                UnityInputSystem.QueueStateEvent(mouse, pressState);
                
                // Release after short delay
                UnityInputSystem.QueueStateEvent(mouse, new MouseState(), Time.time + 0.1f);

                return new SuccessResponse($"Simulated {button} mouse click", new { button });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to simulate mouse click: {ex.Message}");
            }
        }

        #endregion

        #region Touch Simulation

        public static object SimulateTouch(JObject @params)
        {
            try
            {
                EnsureInitialized();

                int touchId = @params["properties"]?["touchId"]?.ToObject<int>() ?? 0;
                float x = @params["properties"]?["x"]?.ToObject<float>() ?? 0f;
                float y = @params["properties"]?["y"]?.ToObject<float>() ?? 0f;
                string phase = @params["properties"]?["phase"]?.ToString() ?? "began";
                float pressure = @params["properties"]?["pressure"]?.ToObject<float>() ?? 1f;

                var touchscreen = GetOrCreateTouchscreen();

                UnityEngine.InputSystem.TouchPhase touchPhase = phase.ToLower() switch
                {
                    "began" => UnityEngine.InputSystem.TouchPhase.Began,
                    "moved" => UnityEngine.InputSystem.TouchPhase.Moved,
                    "stationary" => UnityEngine.InputSystem.TouchPhase.Stationary,
                    "ended" => UnityEngine.InputSystem.TouchPhase.Ended,
                    "canceled" => UnityEngine.InputSystem.TouchPhase.Canceled,
                    _ => UnityEngine.InputSystem.TouchPhase.Began
                };

                // Begin touch
                BeginTouch(touchscreen, touchId, new Vector2(x, y), touchPhase, pressure);

                // Auto-release for began/ended
                if (touchPhase == UnityEngine.InputSystem.TouchPhase.Began)
                {
                    // Schedule release
                    var endState = new TouchState
                    {
                        touchId = touchId,
                        position = new Vector2(x, y),
                        phase = UnityEngine.InputSystem.TouchPhase.Ended,
                        pressure = pressure,
                        tapCount = 1
                    };
                    UnityInputSystem.QueueStateEvent(touchscreen, endState, Time.time + 0.1f);
                }

                return new SuccessResponse($"Simulated touch {touchId} at ({x}, {y}) phase={phase}",
                    new { touchId, x, y, phase, pressure });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to simulate touch: {ex.Message}");
            }
        }

        private static void BeginTouch(Touchscreen touchscreen, int touchId, Vector2 position, 
            UnityEngine.InputSystem.TouchPhase phase, float pressure)
        {
            var state = new TouchState
            {
                touchId = touchId,
                position = position,
                phase = phase,
                pressure = pressure,
                tapCount = 1
            };

            UnityInputSystem.QueueStateEvent(touchscreen, state);
        }

        #endregion

        #region Device Management

        private static Keyboard GetOrCreateKeyboard()
        {
            const string deviceKey = "keyboard";
            
            if (_simulatedDevices.TryGetValue(deviceKey, out var device) && device != null && device.added)
            {
                return (Keyboard)device;
            }

            var keyboard = UnityInputSystem.AddDevice<Keyboard>();
            _simulatedDevices[deviceKey] = keyboard;
            return keyboard;
        }

        private static Mouse GetOrCreateMouse()
        {
            const string deviceKey = "mouse";
            
            if (_simulatedDevices.TryGetValue(deviceKey, out var device) && device != null && device.added)
            {
                return (Mouse)device;
            }

            var mouse = UnityInputSystem.AddDevice<Mouse>();
            _simulatedDevices[deviceKey] = mouse;
            return mouse;
        }

        private static Gamepad GetOrCreateGamepad()
        {
            const string deviceKey = "gamepad";
            
            if (_simulatedDevices.TryGetValue(deviceKey, out var device) && device != null && device.added)
            {
                return (Gamepad)device;
            }

            var gamepad = UnityInputSystem.AddDevice<Gamepad>();
            _simulatedDevices[deviceKey] = gamepad;
            return gamepad;
        }

        private static Touchscreen GetOrCreateTouchscreen()
        {
            const string deviceKey = "touchscreen";
            
            if (_simulatedDevices.TryGetValue(deviceKey, out var device) && device != null && device.added)
            {
                return (Touchscreen)device;
            }

            var touchscreen = UnityInputSystem.AddDevice<Touchscreen>();
            _simulatedDevices[deviceKey] = touchscreen;
            return touchscreen;
        }

        #endregion

        #region Parsing Helpers

        private static Key ParseKey(string keyName)
        {
            if (Enum.TryParse<Key>(keyName, true, out var key))
            {
                return key;
            }

            // Handle common aliases
            return keyName.ToLower() switch
            {
                "space" => Key.Space,
                "enter" => Key.Enter,
                "return" => Key.Enter,
                "escape" => Key.Escape,
                "esc" => Key.Escape,
                "left" => Key.LeftArrow,
                "right" => Key.RightArrow,
                "up" => Key.UpArrow,
                "down" => Key.DownArrow,
                "shift" => Key.LeftShift,
                "leftshift" => Key.LeftShift,
                "rightshift" => Key.RightShift,
                "ctrl" => Key.LeftCtrl,
                "leftctrl" => Key.LeftCtrl,
                "rightctrl" => Key.RightCtrl,
                "alt" => Key.LeftAlt,
                "leftalt" => Key.LeftAlt,
                "rightalt" => Key.RightAlt,
                "tab" => Key.Tab,
                "backspace" => Key.Backspace,
                "delete" => Key.Delete,
                "del" => Key.Delete,
                "insert" => Key.Insert,
                "home" => Key.Home,
                "end" => Key.End,
                "pageup" => Key.PageUp,
                "pagedown" => Key.PageDown,
                "capslock" => Key.CapsLock,
                "numlock" => Key.NumLock,
                "scrolllock" => Key.ScrollLock,
                "printscreen" => Key.PrintScreen,
                "pause" => Key.Pause,
                _ => Key.None
            };
        }

        private static GamepadButton ParseGamepadButton(string buttonName)
        {
            if (Enum.TryParse<GamepadButton>(buttonName, true, out var button))
            {
                return button;
            }

            return buttonName.ToLower() switch
            {
                "a" or "south" or "buttonsouth" => GamepadButton.South,
                "b" or "east" or "buttoneast" => GamepadButton.East,
                "x" or "west" or "buttonwest" => GamepadButton.West,
                "y" or "north" or "buttonnorth" => GamepadButton.North,
                "leftshoulder" or "lb" or "l1" => GamepadButton.LeftShoulder,
                "rightshoulder" or "rb" or "r1" => GamepadButton.RightShoulder,
                "leftstickpress" or "l3" => GamepadButton.LeftStick,
                "rightstickpress" or "r3" => GamepadButton.RightStick,
                "start" or "menu" => GamepadButton.Start,
                "select" or "back" => GamepadButton.Select,
                "dpadup" => GamepadButton.DpadUp,
                "dpaddown" => GamepadButton.DpadDown,
                "dpadleft" => GamepadButton.DpadLeft,
                "dpadright" => GamepadButton.DpadRight,
                _ => GamepadButton.South
            };
        }

        private static MouseButton ParseMouseButton(string buttonName)
        {
            return buttonName.ToLower() switch
            {
                "left" => MouseButton.Left,
                "right" => MouseButton.Right,
                "middle" => MouseButton.Middle,
                "forward" => MouseButton.Forward,
                "back" => MouseButton.Back,
                _ => MouseButton.Left
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
    public static class InputSimulation
    {
        public static object SimulateKeyPress(JObject @params)
        {
            return new ErrorResponse("Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings.");
        }

        public static object SimulateKeyHold(JObject @params)
        {
            return new ErrorResponse("Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings.");
        }

        public static object SimulateKeyRelease(JObject @params)
        {
            return new ErrorResponse("Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings.");
        }

        public static object SimulateButtonPress(JObject @params)
        {
            return new ErrorResponse("Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings.");
        }

        public static object SimulateAxis(JObject @params)
        {
            return new ErrorResponse("Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings.");
        }

        public static object SimulateVector2(JObject @params)
        {
            return new ErrorResponse("Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings.");
        }

        public static object SimulateMouseMove(JObject @params)
        {
            return new ErrorResponse("Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings.");
        }

        public static object SimulateMouseClick(JObject @params)
        {
            return new ErrorResponse("Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings.");
        }

        public static object SimulateTouch(JObject @params)
        {
            return new ErrorResponse("Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings.");
        }

        public static object Cleanup()
        {
            return null;
        }
    }
}

#endif
