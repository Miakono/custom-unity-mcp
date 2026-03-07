using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tools
{
    /// <summary>
    /// Handles Unity Editor window management and tool selection.
    /// </summary>
    [McpForUnityTool("manage_windows", AutoRegister = false)]
    public static class ManageWindows
    {
        /// <summary>
        /// Main handler for window management actions.
        /// </summary>
        public static object HandleCommand(JObject @params)
        {
            if (@params == null)
            {
                return new ErrorResponse("Parameters cannot be null.");
            }

            var p = new ToolParams(@params);

            var actionResult = p.GetRequired("action");
            if (!actionResult.IsSuccess)
            {
                return new ErrorResponse(actionResult.ErrorMessage);
            }
            string action = actionResult.Value.ToLowerInvariant();

            switch (action)
            {
                case "list_windows":
                    return ListWindows();

                case "open_window":
                    var windowTypeResult = p.GetRequired("windowType", "'windowType' parameter required for open_window.");
                    if (!windowTypeResult.IsSuccess)
                        return new ErrorResponse(windowTypeResult.ErrorMessage);
                    return OpenWindow(windowTypeResult.Value);

                case "focus_window":
                    int? windowId = p.GetInt("windowId");
                    string windowTitle = p.Get("windowTitle");
                    return FocusWindow(windowId, windowTitle);

                case "close_window":
                    windowId = p.GetInt("windowId");
                    windowTitle = p.Get("windowTitle");
                    return CloseWindow(windowId, windowTitle);

                case "get_active_tool":
                    return GetActiveTool();

                case "set_active_tool":
                    var toolNameResult = p.GetRequired("toolName", "'toolName' parameter required for set_active_tool.");
                    if (!toolNameResult.IsSuccess)
                        return new ErrorResponse(toolNameResult.ErrorMessage);
                    return SetActiveTool(toolNameResult.Value);

                default:
                    return new ErrorResponse(
                        $"Unknown action: '{action}'. Supported actions: list_windows, open_window, focus_window, close_window, get_active_tool, set_active_tool."
                    );
            }
        }

        private static object ListWindows()
        {
            try
            {
                var windows = new List<object>();
                var allWindows = UnityEngine.Resources.FindObjectsOfTypeAll<EditorWindow>();

                foreach (var window in allWindows)
                {
                    if (window == null) continue;

                    var windowInfo = new Dictionary<string, object>
                    {
                        ["id"] = window.GetInstanceID(),
                        ["title"] = window.titleContent.text,
                        ["type"] = window.GetType().FullName,
                        ["typeName"] = window.GetType().Name,
                        ["hasFocus"] = EditorWindow.focusedWindow == window
                    };

                    windows.Add(windowInfo);
                }

                return new SuccessResponse(
                    $"Found {windows.Count} open editor windows.",
                    new
                    {
                        count = windows.Count,
                        windows = windows
                    }
                );
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Error listing windows: {e.Message}");
            }
        }

        private static object OpenWindow(string windowType)
        {
            try
            {
                // Map common window names to their types
                var windowTypeMap = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
                {
                    ["console"] = "UnityEditor.ConsoleWindow",
                    ["inspector"] = "UnityEditor.InspectorWindow",
                    ["scene"] = "UnityEditor.SceneView",
                    ["game"] = "UnityEditor.GameView",
                    ["hierarchy"] = "UnityEditor.SceneHierarchyWindow",
                    ["project"] = "UnityEditor.ProjectBrowser",
                    ["animation"] = "UnityEditor.AnimationWindow",
                    ["animator"] = "UnityEditor.AnimatorControllerTool",
                    ["profiler"] = "UnityEditor.ProfilerWindow",
                    ["preferences"] = "UnityEditor.PreferencesWindow",
                    ["settings"] = "UnityEditor.ProjectSettingsWindow",
                    ["lighting"] = "UnityEditor.LightingWindow",
                    ["navigation"] = "UnityEditor.NavMeshEditorWindow",
                };

                string typeName = windowTypeMap.TryGetValue(windowType, out var mappedType)
                    ? mappedType
                    : windowType;

                // Try to find the type
                var type = FindEditorWindowType(typeName);

                if (type == null)
                {
                    // Try executing as menu item
                    string menuPath = GetMenuPathForWindow(windowType);
                    if (!string.IsNullOrEmpty(menuPath))
                    {
                        bool result = EditorApplication.ExecuteMenuItem(menuPath);
                        if (result)
                        {
                            return new SuccessResponse($"Opened window via menu: {windowType}",
                                new { windowType = windowType, menuPath = menuPath });
                        }
                    }

                    return new ErrorResponse(
                        $"Could not find window type '{windowType}'. Try using the full type name or a known window name (Console, Inspector, Scene, Game, Hierarchy, Project, Animation, Animator, Profiler)."
                    );
                }

                // Open the window
                var window = EditorWindow.GetWindow(type);
                if (window != null)
                {
                    window.Focus();
                    return new SuccessResponse(
                        $"Opened {windowType} window.",
                        new
                        {
                            windowType = windowType,
                            windowId = window.GetInstanceID(),
                            title = window.titleContent.text
                        }
                    );
                }

                return new ErrorResponse($"Failed to open window: {windowType}");
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Error opening window: {e.Message}");
            }
        }

        private static object FocusWindow(int? windowId, string windowTitle)
        {
            try
            {
                EditorWindow targetWindow = null;

                if (windowId.HasValue)
                {
                    var allWindows = UnityEngine.Resources.FindObjectsOfTypeAll<EditorWindow>();
                    targetWindow = allWindows.FirstOrDefault(w => w.GetInstanceID() == windowId.Value);
                }
                else if (!string.IsNullOrEmpty(windowTitle))
                {
                    var allWindows = UnityEngine.Resources.FindObjectsOfTypeAll<EditorWindow>();
                    targetWindow = allWindows.FirstOrDefault(w =>
                        w.titleContent.text.Equals(windowTitle, StringComparison.OrdinalIgnoreCase));
                }

                if (targetWindow == null)
                {
                    return new ErrorResponse(
                        "Window not found. Use list_windows to see available windows, or provide a valid windowId or windowTitle."
                    );
                }

                targetWindow.Focus();
                return new SuccessResponse(
                    $"Focused window: {targetWindow.titleContent.text}",
                    new
                    {
                        windowId = targetWindow.GetInstanceID(),
                        title = targetWindow.titleContent.text
                    }
                );
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Error focusing window: {e.Message}");
            }
        }

        private static object CloseWindow(int? windowId, string windowTitle)
        {
            try
            {
                EditorWindow targetWindow = null;

                if (windowId.HasValue)
                {
                    var allWindows = UnityEngine.Resources.FindObjectsOfTypeAll<EditorWindow>();
                    targetWindow = allWindows.FirstOrDefault(w => w.GetInstanceID() == windowId.Value);
                }
                else if (!string.IsNullOrEmpty(windowTitle))
                {
                    var allWindows = UnityEngine.Resources.FindObjectsOfTypeAll<EditorWindow>();
                    targetWindow = allWindows.FirstOrDefault(w =>
                        w.titleContent.text.Equals(windowTitle, StringComparison.OrdinalIgnoreCase));
                }

                if (targetWindow == null)
                {
                    return new ErrorResponse(
                        "Window not found. Use list_windows to see available windows, or provide a valid windowId or windowTitle."
                    );
                }

                string title = targetWindow.titleContent.text;
                targetWindow.Close();

                return new SuccessResponse(
                    $"Closed window: {title}",
                    new { title = title }
                );
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Error closing window: {e.Message}");
            }
        }

        private static object GetActiveTool()
        {
            try
            {
                var currentTool = UnityEditor.Tools.current;
                var toolNames = new Dictionary<Tool, string>
                {
                    [Tool.View] = "View",
                    [Tool.Move] = "Move",
                    [Tool.Rotate] = "Rotate",
                    [Tool.Scale] = "Scale",
                    [Tool.Rect] = "Rect",
                    [Tool.Transform] = "Transform",
                    [Tool.Custom] = "Custom",
                    [Tool.None] = "None"
                };

                return new SuccessResponse(
                    "Retrieved active tool.",
                    new
                    {
                        tool = currentTool.ToString(),
                        toolName = toolNames.GetValueOrDefault(currentTool, currentTool.ToString()),
                        pivotMode = UnityEditor.Tools.pivotMode.ToString(),
                        pivotRotation = UnityEditor.Tools.pivotRotation.ToString(),
                        viewTool = UnityEditor.Tools.viewTool.ToString()
                    }
                );
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Error getting active tool: {e.Message}");
            }
        }

        private static object SetActiveTool(string toolName)
        {
            try
            {
                if (Enum.TryParse<Tool>(toolName, true, out var targetTool))
                {
                    if (targetTool != Tool.None && targetTool <= Tool.Custom)
                    {
                        UnityEditor.Tools.current = targetTool;
                        return new SuccessResponse(
                            $"Set active tool to '{targetTool}'.",
                            new { tool = targetTool.ToString() }
                        );
                    }
                    else
                    {
                        return new ErrorResponse(
                            $"Cannot set tool to '{toolName}'. It might be None, Custom, or invalid."
                        );
                    }
                }
                else
                {
                    return new ErrorResponse(
                        $"Could not parse '{toolName}' as a standard Unity Tool. " +
                        "Valid values: View, Move, Rotate, Scale, Rect, Transform, Custom."
                    );
                }
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Error setting active tool: {e.Message}");
            }
        }

        private static System.Type FindEditorWindowType(string typeName)
        {
            // Try exact match first
            var type = System.Type.GetType(typeName);
            if (type != null) return type;

            // Try with UnityEditor assembly
            type = System.Type.GetType($"{typeName},UnityEditor");
            if (type != null) return type;

            // Search in all assemblies
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                try
                {
                    type = assembly.GetType(typeName);
                    if (type != null && typeof(EditorWindow).IsAssignableFrom(type))
                        return type;
                }
                catch { }
            }

            return null;
        }

        private static string GetMenuPathForWindow(string windowName)
        {
            var menuMap = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
            {
                ["console"] = "Window/General/Console",
                ["inspector"] = "Window/General/Inspector",
                ["scene"] = "Window/General/Scene",
                ["game"] = "Window/General/Game",
                ["hierarchy"] = "Window/General/Hierarchy",
                ["project"] = "Window/General/Project",
                ["animation"] = "Window/Animation/Animation",
                ["animator"] = "Window/Animation/Animator",
                ["profiler"] = "Window/Analysis/Profiler",
            };

            return menuMap.TryGetValue(windowName, out var path) ? path : null;
        }
    }
}
