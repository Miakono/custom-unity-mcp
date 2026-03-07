using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Runtime.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace MCPForUnity.Editor.Tools
{
    /// <summary>
    /// Handles editor selection management - getting and setting selected objects.
    /// </summary>
    [McpForUnityTool("manage_selection", AutoRegister = false)]
    public static class ManageSelection
    {
        /// <summary>
        /// Main handler for selection management actions.
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
                case "get_selection":
                    return GetSelection();

                case "set_selection":
                    var targetToken = @params["target"];
                    bool clear = p.GetBool("clear", true);
                    bool add = p.GetBool("add", false);
                    return SetSelection(targetToken, clear, add);

                case "frame_selection":
                    bool frameSelected = p.GetBool("frameSelected", true);
                    return FrameSelection(frameSelected);

                default:
                    return new ErrorResponse(
                        $"Unknown action: '{action}'. Supported actions: get_selection, set_selection, frame_selection."
                    );
            }
        }

        private static object GetSelection()
        {
            try
            {
                var selectedObjects = UnityEditor.Selection.objects;
                var selectionList = new List<object>();

                foreach (var obj in selectedObjects)
                {
                    if (obj == null) continue;

                    var item = new Dictionary<string, object>
                    {
                        ["name"] = obj.name,
                        ["type"] = obj.GetType().Name,
                        ["instanceID"] = obj.GetInstanceID()
                    };

                    // Add additional info for GameObjects
                    if (obj is GameObject go)
                    {
                        item["isActive"] = go.activeInHierarchy;
                        item["tag"] = go.tag;
                        item["layer"] = go.layer;
                        item["scene"] = go.scene.name;
                    }

                    selectionList.Add(item);
                }

                return new SuccessResponse(
                    $"Retrieved {selectionList.Count} selected objects.",
                    new
                    {
                        count = selectionList.Count,
                        selection = selectionList
                    }
                );
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Error getting selection: {e.Message}");
            }
        }

        private static object SetSelection(JToken targetToken, bool clear, bool add)
        {
            try
            {
                if (targetToken == null || targetToken.Type == JTokenType.Null)
                {
                    if (clear)
                    {
                        UnityEditor.Selection.objects = new UnityEngine.Object[0];
                        return new SuccessResponse("Selection cleared.");
                    }
                    return new ErrorResponse("No target specified for selection.");
                }

                var objectsToSelect = new List<UnityEngine.Object>();

                // Handle array of targets
                if (targetToken.Type == JTokenType.Array)
                {
                    foreach (var item in targetToken)
                    {
                        var obj = ResolveTarget(item);
                        if (obj != null)
                        {
                            objectsToSelect.Add(obj);
                        }
                    }
                }
                else
                {
                    // Single target
                    var obj = ResolveTarget(targetToken);
                    if (obj != null)
                    {
                        objectsToSelect.Add(obj);
                    }
                }

                if (objectsToSelect.Count == 0)
                {
                    return new ErrorResponse("Could not resolve any valid target objects.");
                }

                // Apply selection
                if (add && !clear)
                {
                    // Add to existing selection
                    var current = UnityEditor.Selection.objects;
                    var combined = current.Concat(objectsToSelect).Distinct().ToArray();
                    UnityEditor.Selection.objects = combined;
                }
                else
                {
                    // Replace selection (default behavior)
                    UnityEditor.Selection.objects = objectsToSelect.ToArray();
                }

                return new SuccessResponse(
                    $"Selected {objectsToSelect.Count} object(s).",
                    new
                    {
                        selectedCount = objectsToSelect.Count,
                        selectedNames = objectsToSelect.Select(o => o.name).ToList()
                    }
                );
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Error setting selection: {e.Message}");
            }
        }

        private static object FrameSelection(bool frameSelected)
        {
            try
            {
                var sceneView = SceneView.lastActiveSceneView;
                if (sceneView == null)
                {
                    return new ErrorResponse("No active Scene View found.");
                }

                if (frameSelected)
                {
                    if (UnityEditor.Selection.objects.Length == 0)
                    {
                        return new ErrorResponse("No objects selected to frame.");
                    }

                    sceneView.FrameSelected();
                    return new SuccessResponse("Framed selected object(s) in Scene View.");
                }
                else
                {
                    // Frame entire scene
                    Bounds bounds = new Bounds(Vector3.zero, Vector3.zero);
                    bool hasBounds = false;

                    foreach (var r in UnityObjectCompatibility.FindObjectsByType<Renderer>())
                    {
                        if (r == null || !r.gameObject.activeInHierarchy) continue;
                        if (!hasBounds)
                        {
                            bounds = r.bounds;
                            hasBounds = true;
                        }
                        else
                        {
                            bounds.Encapsulate(r.bounds);
                        }
                    }

                    if (!hasBounds)
                    {
                        bounds = new Bounds(Vector3.zero, Vector3.one * 10f);
                    }

                    sceneView.Frame(bounds, false);
                    return new SuccessResponse("Framed entire scene in Scene View.");
                }
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Error framing selection: {e.Message}");
            }
        }

        private static UnityEngine.Object ResolveTarget(JToken token)
        {
            if (token == null || token.Type == JTokenType.Null)
                return null;

            // Try integer instance ID first
            if (token.Type == JTokenType.Integer || int.TryParse(token.ToString(), out _))
            {
                if (int.TryParse(token.ToString(), out int id))
                {
                    var obj = UnityEditorObjectLookup.FindObjectByInstanceId(id);
                    if (obj != null) return obj;
                }
            }

            string target = token.ToString();
            if (string.IsNullOrWhiteSpace(target))
                return null;

            // Try to find by path (contains '/')
            if (target.Contains("/"))
            {
                var ids = GameObjectLookup.SearchGameObjects(
                    "by_path", target, includeInactive: true, maxResults: 1);
                if (ids.Count > 0)
                {
                    return GameObjectLookup.FindById(ids[0]);
                }
            }

            // Try to find by name in all scenes
            foreach (var scene in GetAllLoadedScenes())
            {
                if (!scene.IsValid() || !scene.isLoaded) continue;

                foreach (var root in scene.GetRootGameObjects())
                {
                    if (root.name == target)
                        return root;

                    var transform = root.transform.Find(target);
                    if (transform != null)
                        return transform.gameObject;

                    // Search in children
                    var child = root.transform.Find(target);
                    if (child != null)
                        return child.gameObject;

                    // Deep search
                    var found = root.GetComponentsInChildren<Transform>(true)
                        .FirstOrDefault(t => t.name == target);
                    if (found != null)
                        return found.gameObject;
                }
            }

            return null;
        }

        private static IEnumerable<Scene> GetAllLoadedScenes()
        {
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                yield return SceneManager.GetSceneAt(i);
            }
        }
    }
}
