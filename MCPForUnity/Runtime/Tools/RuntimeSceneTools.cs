// -----------------------------------------------------------------------
// RuntimeSceneTools.cs
// Runtime-only Scene manipulation tools
// 
// These tools are ONLY available in Play Mode or Built Games.
// They NEVER appear in Editor-only environments.
// -----------------------------------------------------------------------

#nullable enable

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using MCPForUnity.Runtime.MCP;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace MCPForUnity.Runtime.Tools
{
    /// <summary>
    /// Runtime Scene tools for MCP.
    /// 
    /// Provides capabilities to:
    /// - Get active scene information
    /// - List loaded scenes
    /// - Query scene root objects
    /// - Load scenes (if allowed in runtime)
    /// - Get scene hierarchy
    /// 
    /// These operations work ONLY in runtime context.
    /// </summary>
    public static class RuntimeSceneTools
    {
        /// <summary>
        /// Register all Scene tools with the runtime registry
        /// </summary>
        public static void Register(RuntimeToolRegistry registry)
        {
            // Get active scene
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_scene_get_active",
                    Description = "Get information about the currently active scene",
                    Category = "scene",
                    IsMutating = false,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "include_objects", Type = "boolean", Description = "Include root GameObject summaries", Required = false, DefaultValue = true }
                    }
                },
                GetActiveSceneAsync
            );

            // List loaded scenes
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_scene_list",
                    Description = "List all currently loaded scenes",
                    Category = "scene",
                    IsMutating = false,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "include_details", Type = "boolean", Description = "Include detailed scene information", Required = false, DefaultValue = false }
                    }
                },
                ListScenesAsync
            );

            // Get scene hierarchy
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_scene_get_hierarchy",
                    Description = "Get the full hierarchy of the active scene",
                    Category = "scene",
                    IsMutating = false,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "max_depth", Type = "number", Description = "Maximum depth to traverse (0 = unlimited)", Required = false, DefaultValue = 10 },
                        new() { Name = "include_inactive", Type = "boolean", Description = "Include inactive GameObjects", Required = false, DefaultValue = false }
                    }
                },
                GetSceneHierarchyAsync
            );

            // Load scene
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_scene_load",
                    Description = "Load a scene by name or build index (single mode)",
                    Category = "scene",
                    IsMutating = true,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "scene_name", Type = "string", Description = "Name of scene to load", Required = false },
                        new() { Name = "build_index", Type = "number", Description = "Build index of scene to load", Required = false },
                        new() { Name = "mode", Type = "string", Description = "Load mode: 'single' or 'additive'", Required = false, DefaultValue = "single" }
                    }
                },
                LoadSceneAsync
            );

            // Get root objects
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_scene_get_root_objects",
                    Description = "Get all root GameObjects in the active scene",
                    Category = "scene",
                    IsMutating = false,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "include_inactive", Type = "boolean", Description = "Include inactive GameObjects", Required = false, DefaultValue = false }
                    }
                },
                GetRootObjectsAsync
            );

            // Query scene statistics
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_scene_get_stats",
                    Description = "Get statistics about the current scene (object counts, etc.)",
                    Category = "scene",
                    IsMutating = false,
                    Parameters = new List<RuntimeToolParameter>()
                },
                GetSceneStatsAsync
            );

            Debug.Log("[RuntimeSceneTools] Registered 6 runtime tools");
        }

        #region Tool Implementations

        private static Task<Dictionary<string, object>> GetActiveSceneAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                bool includeObjects = GetBoolParameter(parameters, "include_objects", true);
                var scene = SceneManager.GetActiveScene();

                var data = new Dictionary<string, object>
                {
                    ["name"] = scene.name,
                    ["path"] = scene.path,
                    ["build_index"] = scene.buildIndex,
                    ["is_loaded"] = scene.isLoaded,
                    ["root_count"] = scene.rootCount,
                    ["is_valid"] = scene.IsValid(),
                    ["handle"] = scene.handle
                };

                if (includeObjects)
                {
                    var rootObjects = scene.GetRootGameObjects();
                    var objects = rootObjects.Select(go => new Dictionary<string, object>
                    {
                        ["name"] = go.name,
                        ["instance_id"] = go.GetInstanceID(),
                        ["active"] = go.activeSelf,
                        ["child_count"] = go.transform.childCount
                    }).ToList();

                    data["root_objects"] = objects;
                }

                result["success"] = true;
                result["message"] = "Active scene info retrieved";
                result["data"] = data;
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "get_scene_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static Task<Dictionary<string, object>> ListScenesAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                bool includeDetails = GetBoolParameter(parameters, "include_details", false);
                int sceneCount = SceneManager.sceneCount;
                var scenes = new List<Dictionary<string, object>>();

                for (int i = 0; i < sceneCount; i++)
                {
                    var scene = SceneManager.GetSceneAt(i);
                    var sceneInfo = new Dictionary<string, object>
                    {
                        ["name"] = scene.name,
                        ["path"] = scene.path,
                        ["build_index"] = scene.buildIndex,
                        ["is_loaded"] = scene.isLoaded,
                        ["is_active"] = scene == SceneManager.GetActiveScene()
                    };

                    if (includeDetails)
                    {
                        sceneInfo["root_count"] = scene.rootCount;
                        sceneInfo["is_valid"] = scene.IsValid();
                    }

                    scenes.Add(sceneInfo);
                }

                result["success"] = true;
                result["message"] = $"Found {scenes.Count} loaded scenes";
                result["data"] = new Dictionary<string, object>
                {
                    ["scenes"] = scenes,
                    ["count"] = scenes.Count,
                    ["scene_count_in_build"] = SceneManager.sceneCountInBuildSettings
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "list_scenes_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static Task<Dictionary<string, object>> GetSceneHierarchyAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                int maxDepth = GetIntParameter(parameters, "max_depth", 10);
                bool includeInactive = GetBoolParameter(parameters, "include_inactive", false);

                var scene = SceneManager.GetActiveScene();
                var rootObjects = scene.GetRootGameObjects();

                var hierarchy = new List<Dictionary<string, object>>();
                foreach (var root in rootObjects)
                {
                    hierarchy.Add(CreateHierarchyNode(root, 0, maxDepth, includeInactive));
                }

                result["success"] = true;
                result["message"] = "Scene hierarchy retrieved";
                result["data"] = new Dictionary<string, object>
                {
                    ["scene_name"] = scene.name,
                    ["root_count"] = rootObjects.Length,
                    ["hierarchy"] = hierarchy
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "get_hierarchy_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static async Task<Dictionary<string, object>> LoadSceneAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                string? sceneName = parameters.TryGetValue("scene_name", out var sceneVal) ? sceneVal?.ToString() : null;
                int buildIndex = GetIntParameter(parameters, "build_index", -1);
                string mode = parameters.GetValueOrDefault("mode", "single")?.ToString()!.ToLower() ?? "single";

                LoadSceneMode loadMode = mode == "additive" ? LoadSceneMode.Additive : LoadSceneMode.Single;

                AsyncOperation? loadOp = null;

                if (!string.IsNullOrEmpty(sceneName))
                {
                    loadOp = SceneManager.LoadSceneAsync(sceneName, loadMode);
                }
                else if (buildIndex >= 0)
                {
                    loadOp = SceneManager.LoadSceneAsync(buildIndex, loadMode);
                }
                else
                {
                    result["success"] = false;
                    result["error"] = "invalid_parameters";
                    result["message"] = "Must specify either scene_name or build_index";
                    return result;
                }

                if (loadOp == null)
                {
                    result["success"] = false;
                    result["error"] = "load_failed";
                    result["message"] = "Failed to start scene load operation";
                    return result;
                }

                // Wait for load to complete
                while (!loadOp.isDone)
                {
                    await Task.Yield();
                }

                var activeScene = SceneManager.GetActiveScene();

                result["success"] = true;
                result["message"] = "Scene loaded successfully";
                result["data"] = new Dictionary<string, object>
                {
                    ["scene_name"] = activeScene.name,
                    ["build_index"] = activeScene.buildIndex,
                    ["mode"] = mode
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "load_scene_failed";
                result["message"] = ex.Message;
            }

            return result;
        }

        private static Task<Dictionary<string, object>> GetRootObjectsAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                bool includeInactive = GetBoolParameter(parameters, "include_inactive", false);
                var scene = SceneManager.GetActiveScene();
                var rootObjects = scene.GetRootGameObjects();

                var objects = new List<Dictionary<string, object>>();
                foreach (var go in rootObjects)
                {
                    if (!includeInactive && !go.activeInHierarchy) continue;

                    objects.Add(new Dictionary<string, object>
                    {
                        ["name"] = go.name,
                        ["instance_id"] = go.GetInstanceID(),
                        ["active"] = go.activeSelf,
                        ["active_in_hierarchy"] = go.activeInHierarchy,
                        ["tag"] = go.tag,
                        ["child_count"] = go.transform.childCount,
                        ["component_count"] = go.GetComponents<Component>().Length
                    });
                }

                result["success"] = true;
                result["message"] = $"Found {objects.Count} root objects";
                result["data"] = new Dictionary<string, object>
                {
                    ["scene_name"] = scene.name,
                    ["count"] = objects.Count,
                    ["objects"] = objects
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "get_root_objects_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static Task<Dictionary<string, object>> GetSceneStatsAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                var scene = SceneManager.GetActiveScene();
                var rootObjects = scene.GetRootGameObjects();

                int totalObjects = 0;
                int activeObjects = 0;
                int inactiveObjects = 0;
                int totalComponents = 0;
                var componentTypes = new HashSet<string>();

                foreach (var root in rootObjects)
                {
                    CountObjectsRecursive(root, ref totalObjects, ref activeObjects, ref inactiveObjects, 
                        ref totalComponents, componentTypes);
                }

                result["success"] = true;
                result["message"] = "Scene statistics retrieved";
                result["data"] = new Dictionary<string, object>
                {
                    ["scene_name"] = scene.name,
                    ["root_object_count"] = rootObjects.Length,
                    ["total_object_count"] = totalObjects,
                    ["active_object_count"] = activeObjects,
                    ["inactive_object_count"] = inactiveObjects,
                    ["total_component_count"] = totalComponents,
                    ["unique_component_types"] = componentTypes.Count,
                    ["component_types"] = componentTypes.ToList()
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "get_stats_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        #endregion

        #region Helper Methods

        private static Dictionary<string, object> CreateHierarchyNode(
            GameObject go,
            int currentDepth,
            int maxDepth,
            bool includeInactive
        )
        {
            var node = new Dictionary<string, object>
            {
                ["name"] = go.name,
                ["instance_id"] = go.GetInstanceID(),
                ["active"] = go.activeSelf,
                ["active_in_hierarchy"] = go.activeInHierarchy,
                ["tag"] = go.tag,
                ["child_count"] = go.transform.childCount
            };

            if (currentDepth < maxDepth && go.transform.childCount > 0)
            {
                var children = new List<Dictionary<string, object>>();
                foreach (Transform child in go.transform)
                {
                    if (!includeInactive && !child.gameObject.activeInHierarchy) continue;
                    children.Add(CreateHierarchyNode(child.gameObject, currentDepth + 1, maxDepth, includeInactive));
                }
                node["children"] = children;
            }

            return node;
        }

        private static void CountObjectsRecursive(
            GameObject go,
            ref int totalObjects,
            ref int activeObjects,
            ref int inactiveObjects,
            ref int totalComponents,
            HashSet<string> componentTypes
        )
        {
            totalObjects++;
            
            if (go.activeInHierarchy)
                activeObjects++;
            else
                inactiveObjects++;

            var components = go.GetComponents<Component>();
            totalComponents += components.Length;
            
            foreach (var comp in components)
            {
                if (comp != null)
                {
                    componentTypes.Add(comp.GetType().Name);
                }
            }

            foreach (Transform child in go.transform)
            {
                CountObjectsRecursive(child.gameObject, ref totalObjects, ref activeObjects, 
                    ref inactiveObjects, ref totalComponents, componentTypes);
            }
        }

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

        #endregion
    }
}
