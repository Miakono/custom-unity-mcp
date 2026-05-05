using System;
using System.Collections.Generic;
using System.IO;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tools
{
    /// <summary>
    /// Build a prefab from scratch in one MCP call: takes a JSON tree describing
    /// GameObjects, components, and serialized property patches, then saves the
    /// result to <c>prefab_path</c>. Generic — no project assumptions.
    ///
    /// What this replaces: the 5-step "create scene GO → add components → set fields →
    /// save_as_prefab → delete scene GO" sequence the existing tools require.
    ///
    /// JSON shape (root node and every child node is recursive):
    /// <code>
    /// {
    ///   "prefab_path": "Assets/Prefabs/Foo.prefab",
    ///   "overwrite": false,
    ///   "root": {
    ///     "name": "Foo",
    ///     "tag": "Untagged", "layer": "Default", "active": true,
    ///     "transform": { "position": [0,0,0], "rotation": [0,0,0], "scale": [1,1,1] },
    ///     "components": [
    ///       { "type": "Rigidbody",   "patches": [{"property_path": "m_Mass", "value": 5}] },
    ///       { "type": "BoxCollider", "patches": [{"property_path": "m_IsTrigger", "value": true}] }
    ///     ],
    ///     "children": [
    ///       { "name": "VisualChild", "components": [ ... ] }
    ///     ]
    ///   }
    /// }
    /// </code>
    /// </summary>
    [McpForUnityTool("compose_prefab", AutoRegister = false)]
    public static class ComposePrefab
    {
        public static object HandleCommand(JObject @params)
        {
            if (@params == null) return new ErrorResponse("Parameters are required.");

            string prefabPath = @params["prefab_path"]?.ToString() ?? @params["prefabPath"]?.ToString();
            if (string.IsNullOrWhiteSpace(prefabPath))
                return new ErrorResponse("'prefab_path' is required.");
            if (!prefabPath.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase))
                return new ErrorResponse("'prefab_path' must start with 'Assets/'.");
            if (!prefabPath.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase))
                return new ErrorResponse("'prefab_path' must end with '.prefab'.");

            bool overwrite = ParamCoercion.CoerceBool(@params["overwrite"], false);
            if (!overwrite && File.Exists(Path.GetFullPath(prefabPath)))
            {
                return new ErrorResponse($"Asset already exists at '{prefabPath}'. Pass overwrite=true to replace.");
            }

            JObject root = @params["root"] as JObject;
            if (root == null)
                return new ErrorResponse("'root' (object) is required.");

            // Ensure the target folder exists; create intermediate folders if needed.
            try
            {
                EnsureFolderExists(Path.GetDirectoryName(prefabPath).Replace('\\', '/'));
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to create folder hierarchy for '{prefabPath}': {ex.Message}");
            }

            // Suppress import storms while we build the temp GO + save the prefab.
            bool startedEditing = false;
            GameObject scratch = null;
            var warnings = new List<string>();
            var componentPatchSummaries = new List<object>();

            try
            {
                AssetDatabase.StartAssetEditing();
                startedEditing = true;

                scratch = BuildNode(root, parent: null, warnings, componentPatchSummaries);
                if (scratch == null)
                    return new ErrorResponse("Failed to build root GameObject.");

                // SaveAsPrefabAsset requires the GO to live in a scene; the new GO is created
                // in the active scene by default, so we're fine.
                bool saved = false;
                GameObject prefabAsset = PrefabUtility.SaveAsPrefabAsset(scratch, prefabPath, out saved);
                if (!saved || prefabAsset == null)
                    return new ErrorResponse($"PrefabUtility.SaveAsPrefabAsset reported failure for '{prefabPath}'.");

                string guid = AssetDatabase.AssetPathToGUID(prefabPath);

                return new SuccessResponse($"Composed prefab '{prefabPath}'.", new
                {
                    prefab_path = prefabPath,
                    guid,
                    overwrote = overwrite && File.Exists(Path.GetFullPath(prefabPath)),
                    component_patches = componentPatchSummaries,
                    warnings,
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"compose_prefab failed: {ex.Message}");
            }
            finally
            {
                if (scratch != null)
                {
                    try { UnityEngine.Object.DestroyImmediate(scratch); }
                    catch (Exception ex) { McpLog.Warn($"compose_prefab: failed to clean up scratch GO: {ex.Message}"); }
                }
                if (startedEditing)
                {
                    try { AssetDatabase.StopAssetEditing(); }
                    catch (Exception ex) { McpLog.Warn($"compose_prefab: StopAssetEditing threw: {ex.Message}"); }
                }
            }
        }

        // -------------------- recursive node builder --------------------

        private static GameObject BuildNode(
            JObject node,
            GameObject parent,
            List<string> warnings,
            List<object> componentPatchSummaries)
        {
            string name = node["name"]?.ToString() ?? "Node";
            var go = new GameObject(name);

            if (parent != null)
            {
                go.transform.SetParent(parent.transform, worldPositionStays: false);
            }

            // Tag + layer
            string tag = node["tag"]?.ToString();
            if (!string.IsNullOrEmpty(tag))
            {
                try { go.tag = tag; }
                catch (UnityException) { warnings.Add($"Tag '{tag}' is not defined; skipped on '{name}'."); }
            }

            string layer = node["layer"]?.ToString();
            if (!string.IsNullOrEmpty(layer))
            {
                int layerIndex = LayerMask.NameToLayer(layer);
                if (layerIndex >= 0) go.layer = layerIndex;
                else warnings.Add($"Layer '{layer}' is not defined; skipped on '{name}'.");
            }

            if (node["active"] != null)
            {
                go.SetActive(ParamCoercion.CoerceBool(node["active"], true));
            }

            // Transform
            ApplyTransform(go, node["transform"] as JObject, warnings);

            // Components + patches
            if (node["components"] is JArray componentsArr)
            {
                foreach (var token in componentsArr)
                {
                    if (token is not JObject compSpec) continue;
                    string typeName = compSpec["type"]?.ToString();
                    if (string.IsNullOrWhiteSpace(typeName))
                    {
                        warnings.Add($"Component on '{name}' missing 'type'; skipped.");
                        continue;
                    }

                    Type compType = GameObjectLookup.FindComponentType(typeName);
                    if (compType == null)
                    {
                        warnings.Add($"Component type '{typeName}' not found; skipped on '{name}'.");
                        continue;
                    }

                    Component comp = go.GetComponent(compType);
                    if (comp == null)
                    {
                        try { comp = go.AddComponent(compType); }
                        catch (Exception ex)
                        {
                            warnings.Add($"AddComponent('{typeName}') on '{name}' threw: {ex.Message}");
                            continue;
                        }
                    }

                    var patches = compSpec["patches"] as JArray;
                    if (patches != null && patches.Count > 0)
                    {
                        var result = SerializedPropertyPatcher.ApplyPatches(comp, patches);
                        componentPatchSummaries.Add(new
                        {
                            node = name,
                            component = typeName,
                            applied = result.AnyChanged,
                            results = result.Results,
                            warnings = result.Warnings,
                        });
                    }
                }
            }

            // Recurse into children
            if (node["children"] is JArray childrenArr)
            {
                foreach (var token in childrenArr)
                {
                    if (token is not JObject childNode) continue;
                    BuildNode(childNode, go, warnings, componentPatchSummaries);
                }
            }

            return go;
        }

        private static void ApplyTransform(GameObject go, JObject transformSpec, List<string> warnings)
        {
            if (transformSpec == null) return;
            try
            {
                if (transformSpec["position"] is JArray pos && pos.Count == 3)
                    go.transform.localPosition = new Vector3(pos[0].Value<float>(), pos[1].Value<float>(), pos[2].Value<float>());
                if (transformSpec["rotation"] is JArray rot && rot.Count == 3)
                    go.transform.localEulerAngles = new Vector3(rot[0].Value<float>(), rot[1].Value<float>(), rot[2].Value<float>());
                if (transformSpec["scale"] is JArray scale && scale.Count == 3)
                    go.transform.localScale = new Vector3(scale[0].Value<float>(), scale[1].Value<float>(), scale[2].Value<float>());
            }
            catch (Exception ex)
            {
                warnings.Add($"Transform on '{go.name}' partially failed: {ex.Message}");
            }
        }

        private static void EnsureFolderExists(string folderPath)
        {
            if (string.IsNullOrEmpty(folderPath)) return;
            folderPath = folderPath.Replace('\\', '/').TrimEnd('/');
            if (AssetDatabase.IsValidFolder(folderPath)) return;

            // Walk up until we hit an existing folder, then create downwards.
            var parts = folderPath.Split('/');
            string accum = parts[0];
            for (int i = 1; i < parts.Length; i++)
            {
                string next = accum + "/" + parts[i];
                if (!AssetDatabase.IsValidFolder(next))
                {
                    AssetDatabase.CreateFolder(accum, parts[i]);
                }
                accum = next;
            }
        }
    }
}
