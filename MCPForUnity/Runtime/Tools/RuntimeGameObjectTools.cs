// -----------------------------------------------------------------------
// RuntimeGameObjectTools.cs
// Runtime-only GameObject manipulation tools
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
    /// Runtime GameObject tools for MCP.
    /// 
    /// Provides capabilities to:
    /// - Find and inspect GameObjects at runtime
    /// - Modify GameObject properties (transform, active state, etc.)
    /// - Get component information
    /// - Navigate hierarchy
    /// 
    /// These operations work ONLY in runtime context.
    /// </summary>
    public static class RuntimeGameObjectTools
    {
        /// <summary>
        /// Register all GameObject tools with the runtime registry
        /// </summary>
        public static void Register(RuntimeToolRegistry registry)
        {
            // Find GameObjects
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_gameobject_find",
                    Description = "Find GameObjects in the active scene by name, tag, or component type",
                    Category = "gameobject",
                    IsMutating = false,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "query", Type = "string", Description = "Name, tag, or search term", Required = true },
                        new() { Name = "search_by", Type = "string", Description = "Search method: 'name', 'tag', 'component', or 'path'", Required = false, DefaultValue = "name" },
                        new() { Name = "include_inactive", Type = "boolean", Description = "Include inactive GameObjects", Required = false, DefaultValue = false },
                        new() { Name = "max_results", Type = "number", Description = "Maximum results to return", Required = false, DefaultValue = 50 }
                    }
                },
                FindGameObjectsAsync
            );

            // Get GameObject info
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_gameobject_get_info",
                    Description = "Get detailed information about a GameObject including transform, components, and hierarchy",
                    Category = "gameobject",
                    IsMutating = false,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "target", Type = "string", Description = "GameObject name, path, or instance ID", Required = true },
                        new() { Name = "include_components", Type = "boolean", Description = "Include component details", Required = false, DefaultValue = true },
                        new() { Name = "include_children", Type = "boolean", Description = "Include child GameObjects", Required = false, DefaultValue = false }
                    }
                },
                GetGameObjectInfoAsync
            );

            // Set GameObject active state
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_gameobject_set_active",
                    Description = "Set a GameObject's active state (enable/disable)",
                    Category = "gameobject",
                    IsMutating = true,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "target", Type = "string", Description = "GameObject name, path, or instance ID", Required = true },
                        new() { Name = "active", Type = "boolean", Description = "Active state to set", Required = true }
                    }
                },
                SetGameObjectActiveAsync
            );

            // Set Transform properties
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_gameobject_set_transform",
                    Description = "Set Transform properties (position, rotation, scale) of a GameObject",
                    Category = "gameobject",
                    IsMutating = true,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "target", Type = "string", Description = "GameObject name, path, or instance ID", Required = true },
                        new() { Name = "position", Type = "object", Description = "Position as {x, y, z}", Required = false },
                        new() { Name = "rotation", Type = "object", Description = "Rotation as Euler angles {x, y, z}", Required = false },
                        new() { Name = "scale", Type = "object", Description = "Scale as {x, y, z}", Required = false },
                        new() { Name = "local", Type = "boolean", Description = "Use local space (true) or world space (false)", Required = false, DefaultValue = true },
                        new() { Name = "relative", Type = "boolean", Description = "Apply as relative offset", Required = false, DefaultValue = false }
                    }
                },
                SetTransformAsync
            );

            // Get Component info
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_gameobject_get_components",
                    Description = "Get all components attached to a GameObject",
                    Category = "gameobject",
                    IsMutating = false,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "target", Type = "string", Description = "GameObject name, path, or instance ID", Required = true },
                        new() { Name = "include_properties", Type = "boolean", Description = "Include component property values", Required = false, DefaultValue = false }
                    }
                },
                GetComponentsAsync
            );

            // Destroy GameObject
            registry.RegisterTool(
                new RuntimeToolMetadata
                {
                    Name = "runtime_gameobject_destroy",
                    Description = "Destroy a GameObject at runtime (use with caution)",
                    Category = "gameobject",
                    IsMutating = true,
                    Parameters = new List<RuntimeToolParameter>
                    {
                        new() { Name = "target", Type = "string", Description = "GameObject name, path, or instance ID", Required = true },
                        new() { Name = "immediate", Type = "boolean", Description = "Destroy immediately (true) or at end of frame (false)", Required = false, DefaultValue = false }
                    }
                },
                DestroyGameObjectAsync
            );

            Debug.Log("[RuntimeGameObjectTools] Registered 6 runtime tools");
        }

        #region Tool Implementations

        private static Task<Dictionary<string, object>> FindGameObjectsAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();
            
            try
            {
                string query = parameters.GetValueOrDefault("query", "").ToString()!;
                string searchBy = parameters.GetValueOrDefault("search_by", "name").ToString()!.ToLower();
                bool includeInactive = GetBoolParameter(parameters, "include_inactive", false);
                int maxResults = GetIntParameter(parameters, "max_results", 50);

                if (string.IsNullOrWhiteSpace(query))
                {
                    result["success"] = false;
                    result["error"] = "missing_query";
                    result["message"] = "Query parameter is required";
                    return Task.FromResult(result);
                }

                var scene = SceneManager.GetActiveScene();
                var rootObjects = scene.GetRootGameObjects();
                var matches = new List<Dictionary<string, object>>();

                foreach (var root in rootObjects)
                {
                    SearchGameObjectRecursive(root, query, searchBy, includeInactive, matches, maxResults);
                    if (matches.Count >= maxResults) break;
                }

                result["success"] = true;
                result["message"] = $"Found {matches.Count} GameObjects";
                result["data"] = new Dictionary<string, object>
                {
                    ["gameobjects"] = matches.Take(maxResults).ToList(),
                    ["count"] = matches.Count,
                    ["query"] = query,
                    ["search_by"] = searchBy,
                    ["scene"] = scene.name
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "search_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static void SearchGameObjectRecursive(
            GameObject go,
            string query,
            string searchBy,
            bool includeInactive,
            List<Dictionary<string, object>> matches,
            int maxResults
        )
        {
            if (matches.Count >= maxResults) return;
            if (!includeInactive && !go.activeInHierarchy) return;

            bool isMatch = searchBy switch
            {
                "name" => go.name.Contains(query, StringComparison.OrdinalIgnoreCase),
                "tag" => go.CompareTag(query),
                "component" => go.GetComponent(query) != null,
                "path" => GetGameObjectPath(go).Contains(query, StringComparison.OrdinalIgnoreCase),
                _ => go.name.Contains(query, StringComparison.OrdinalIgnoreCase)
            };

            if (isMatch)
            {
                matches.Add(CreateGameObjectSummary(go));
            }

            foreach (Transform child in go.transform)
            {
                SearchGameObjectRecursive(child.gameObject, query, searchBy, includeInactive, matches, maxResults);
            }
        }

        private static Task<Dictionary<string, object>> GetGameObjectInfoAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                string target = parameters.GetValueOrDefault("target", "").ToString()!;
                bool includeComponents = GetBoolParameter(parameters, "include_components", true);
                bool includeChildren = GetBoolParameter(parameters, "include_children", false);

                var go = FindGameObject(target);
                if (go == null)
                {
                    result["success"] = false;
                    result["error"] = "gameobject_not_found";
                    result["message"] = $"GameObject not found: '{target}'";
                    return Task.FromResult(result);
                }

                var data = CreateDetailedGameObjectInfo(go, includeComponents, includeChildren);

                result["success"] = true;
                result["message"] = "GameObject info retrieved";
                result["data"] = data;
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "get_info_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static Task<Dictionary<string, object>> SetGameObjectActiveAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                string target = parameters.GetValueOrDefault("target", "").ToString()!;
                bool active = GetBoolParameter(parameters, "active", true);

                var go = FindGameObject(target);
                if (go == null)
                {
                    result["success"] = false;
                    result["error"] = "gameobject_not_found";
                    result["message"] = $"GameObject not found: '{target}'";
                    return Task.FromResult(result);
                }

                go.SetActive(active);

                result["success"] = true;
                result["message"] = $"GameObject '{go.name}' set to active={active}";
                result["data"] = new Dictionary<string, object>
                {
                    ["name"] = go.name,
                    ["active"] = go.activeSelf,
                    ["active_in_hierarchy"] = go.activeInHierarchy
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "set_active_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static Task<Dictionary<string, object>> SetTransformAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                string target = parameters.GetValueOrDefault("target", "").ToString()!;
                var go = FindGameObject(target);
                if (go == null)
                {
                    result["success"] = false;
                    result["error"] = "gameobject_not_found";
                    result["message"] = $"GameObject not found: '{target}'";
                    return Task.FromResult(result);
                }

                var transform = go.transform;
                bool local = GetBoolParameter(parameters, "local", true);
                bool relative = GetBoolParameter(parameters, "relative", false);

                // Position
                if (parameters.TryGetValue("position", out var posObj) && posObj is Dictionary<string, object> posDict)
                {
                    Vector3 position = ParseVector3(posDict);
                    if (local)
                    {
                        transform.localPosition = relative ? transform.localPosition + position : position;
                    }
                    else
                    {
                        transform.position = relative ? transform.position + position : position;
                    }
                }

                // Rotation
                if (parameters.TryGetValue("rotation", out var rotObj) && rotObj is Dictionary<string, object> rotDict)
                {
                    Vector3 rotation = ParseVector3(rotDict);
                    if (local)
                    {
                        transform.localEulerAngles = relative ? transform.localEulerAngles + rotation : rotation;
                    }
                    else
                    {
                        transform.eulerAngles = relative ? transform.eulerAngles + rotation : rotation;
                    }
                }

                // Scale
                if (parameters.TryGetValue("scale", out var scaleObj) && scaleObj is Dictionary<string, object> scaleDict)
                {
                    Vector3 scale = ParseVector3(scaleDict);
                    transform.localScale = relative ? Vector3.Scale(transform.localScale, scale) : scale;
                }

                result["success"] = true;
                result["message"] = $"Transform updated for '{go.name}'";
                result["data"] = new Dictionary<string, object>
                {
                    ["position"] = Vector3ToDict(transform.position),
                    ["local_position"] = Vector3ToDict(transform.localPosition),
                    ["rotation"] = Vector3ToDict(transform.eulerAngles),
                    ["local_rotation"] = Vector3ToDict(transform.localEulerAngles),
                    ["scale"] = Vector3ToDict(transform.localScale)
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "set_transform_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static Task<Dictionary<string, object>> GetComponentsAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                string target = parameters.GetValueOrDefault("target", "").ToString()!;
                bool includeProperties = GetBoolParameter(parameters, "include_properties", false);

                var go = FindGameObject(target);
                if (go == null)
                {
                    result["success"] = false;
                    result["error"] = "gameobject_not_found";
                    result["message"] = $"GameObject not found: '{target}'";
                    return Task.FromResult(result);
                }

                var components = go.GetComponents<Component>();
                var componentList = new List<Dictionary<string, object>>();

                foreach (var comp in components)
                {
                    if (comp == null) continue;

                    var compInfo = new Dictionary<string, object>
                    {
                        ["type"] = comp.GetType().Name,
                        ["full_type"] = comp.GetType().FullName,
                        ["enabled"] = true  // Default, will be updated if possible
                    };

                    // Try to get enabled state for Behaviour components
                    if (comp is Behaviour behaviour)
                    {
                        compInfo["enabled"] = behaviour.enabled;
                    }

                    componentList.Add(compInfo);
                }

                result["success"] = true;
                result["message"] = $"Found {componentList.Count} components";
                result["data"] = new Dictionary<string, object>
                {
                    ["gameobject"] = go.name,
                    ["instance_id"] = go.GetInstanceID(),
                    ["components"] = componentList,
                    ["count"] = componentList.Count
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "get_components_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        private static Task<Dictionary<string, object>> DestroyGameObjectAsync(
            Dictionary<string, object> parameters
        )
        {
            var result = new Dictionary<string, object>();

            try
            {
                string target = parameters.GetValueOrDefault("target", "").ToString()!;
                bool immediate = GetBoolParameter(parameters, "immediate", false);

                var go = FindGameObject(target);
                if (go == null)
                {
                    result["success"] = false;
                    result["error"] = "gameobject_not_found";
                    result["message"] = $"GameObject not found: '{target}'";
                    return Task.FromResult(result);
                }

                string name = go.name;
                int instanceId = go.GetInstanceID();

                if (immediate)
                {
                    UnityEngine.Object.DestroyImmediate(go);
                }
                else
                {
                    UnityEngine.Object.Destroy(go);
                }

                result["success"] = true;
                result["message"] = $"GameObject '{name}' destroyed";
                result["data"] = new Dictionary<string, object>
                {
                    ["name"] = name,
                    ["instance_id"] = instanceId,
                    ["immediate"] = immediate
                };
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["error"] = "destroy_failed";
                result["message"] = ex.Message;
            }

            return Task.FromResult(result);
        }

        #endregion

        #region Helper Methods

        private static GameObject? FindGameObject(string identifier)
        {
            // Try by instance ID first
            if (int.TryParse(identifier, out int instanceId))
            {
                // Note: Unity doesn't have a direct Find by instance ID for arbitrary objects
                // We search through all objects
                var allObjects = UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsSortMode.None);
                foreach (var go in allObjects)
                {
                    if (go.GetInstanceID() == instanceId)
                    {
                        return go;
                    }
                }
            }

            // Try by exact name
            var byName = GameObject.Find(identifier);
            if (byName != null) return byName;

            // Try by path
            var byPath = GameObject.Find(identifier.Replace("/", "/"));
            if (byPath != null) return byPath;

            // Search by partial name match
            var all = UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsSortMode.None);
            return all.FirstOrDefault(go => go.name.Equals(identifier, StringComparison.OrdinalIgnoreCase));
        }

        private static string GetGameObjectPath(GameObject go)
        {
            if (go.transform.parent == null)
            {
                return go.name;
            }
            return $"{GetGameObjectPath(go.transform.parent.gameObject)}/{go.name}";
        }

        private static Dictionary<string, object> CreateGameObjectSummary(GameObject go)
        {
            return new Dictionary<string, object>
            {
                ["name"] = go.name,
                ["path"] = GetGameObjectPath(go),
                ["instance_id"] = go.GetInstanceID(),
                ["active"] = go.activeSelf,
                ["active_in_hierarchy"] = go.activeInHierarchy,
                ["tag"] = go.tag,
                ["layer"] = LayerMask.LayerToName(go.layer),
                ["child_count"] = go.transform.childCount,
                ["position"] = Vector3ToDict(go.transform.position)
            };
        }

        private static Dictionary<string, object> CreateDetailedGameObjectInfo(
            GameObject go,
            bool includeComponents,
            bool includeChildren
        )
        {
            var data = CreateGameObjectSummary(go);

            // Transform details
            data["transform"] = new Dictionary<string, object>
            {
                ["position"] = Vector3ToDict(go.transform.position),
                ["local_position"] = Vector3ToDict(go.transform.localPosition),
                ["rotation"] = Vector3ToDict(go.transform.eulerAngles),
                ["local_rotation"] = Vector3ToDict(go.transform.localEulerAngles),
                ["scale"] = Vector3ToDict(go.transform.localScale),
                ["local_scale"] = Vector3ToDict(go.transform.localScale),
                ["forward"] = Vector3ToDict(go.transform.forward),
                ["up"] = Vector3ToDict(go.transform.up),
                ["right"] = Vector3ToDict(go.transform.right)
            };

            // Components
            if (includeComponents)
            {
                var components = go.GetComponents<Component>();
                var compList = new List<Dictionary<string, object>>();
                foreach (var comp in components)
                {
                    if (comp != null)
                    {
                        compList.Add(new Dictionary<string, object>
                        {
                            ["type"] = comp.GetType().Name,
                            ["full_type"] = comp.GetType().FullName
                        });
                    }
                }
                data["components"] = compList;
                data["component_count"] = compList.Count;
            }

            // Children
            if (includeChildren && go.transform.childCount > 0)
            {
                var children = new List<Dictionary<string, object>>();
                foreach (Transform child in go.transform)
                {
                    children.Add(CreateGameObjectSummary(child.gameObject));
                }
                data["children"] = children;
            }

            // Parent
            if (go.transform.parent != null)
            {
                data["parent"] = new Dictionary<string, object>
                {
                    ["name"] = go.transform.parent.name,
                    ["instance_id"] = go.transform.parent.gameObject.GetInstanceID()
                };
            }
            else
            {
                data["parent"] = "none";
            }

            return data;
        }

        private static Vector3 ParseVector3(Dictionary<string, object> dict)
        {
            return new Vector3(
                GetFloatValue(dict, "x"),
                GetFloatValue(dict, "y"),
                GetFloatValue(dict, "z")
            );
        }

        private static Dictionary<string, object> Vector3ToDict(Vector3 v)
        {
            return new Dictionary<string, object>
            {
                ["x"] = v.x,
                ["y"] = v.y,
                ["z"] = v.z
            };
        }

        private static float GetFloatValue(Dictionary<string, object> dict, string key)
        {
            if (dict.TryGetValue(key, out var value))
            {
                return Convert.ToSingle(value);
            }
            return 0f;
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
