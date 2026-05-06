using System;
using System.Collections.Generic;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace MCPForUnity.Editor.Tools
{
    /// <summary>
    /// Generic primitive: append an entry to a serialized list/array field on a Component or
    /// ScriptableObject. Solves the "register a thing in a global registry" pattern that
    /// every Unity project hits — pool managers, addressables groups, audio mixer groups,
    /// scene catalogs, monster registries — without baking project-specific knowledge into
    /// the MCP package.
    ///
    /// Three target kinds:
    ///   - target_kind="asset": entry into a list field on a ScriptableObject asset.
    ///   - target_kind="prefab": entry into a list field on a Component inside a prefab.
    ///   - target_kind="scene_object": entry into a list field on a Component on a scene GameObject.
    ///
    /// Entry kinds (the `entry` param):
    ///   - {"asset_path": "Assets/Foo/Bar.prefab"}    → load + assign as objectReferenceValue
    ///   - {"asset_guid": "abc123..."}                → resolve via GUID + assign
    ///   - {"value": 42 | "text" | true}              → assign as primitive (int/string/float/bool)
    ///
    /// Dedupe: when dedupe=true (default), the tool refuses to add a duplicate entry. For
    /// object references, dedupe compares by Unity object identity. For primitives, by value.
    /// </summary>
    [McpForUnityTool("register_in_serialized_list", AutoRegister = false)]
    public static class RegisterInSerializedList
    {
        public static object HandleCommand(JObject @params)
        {
            if (@params == null) return new ErrorResponse("Parameters are required.");

            string targetKind = (@params["target_kind"]?.ToString() ?? @params["targetKind"]?.ToString() ?? string.Empty)
                .Trim().ToLowerInvariant();
            if (string.IsNullOrEmpty(targetKind))
                return new ErrorResponse("'target_kind' is required ('asset' | 'prefab' | 'scene_object').");

            string fieldPath = @params["field_path"]?.ToString() ?? @params["fieldPath"]?.ToString();
            if (string.IsNullOrWhiteSpace(fieldPath))
                return new ErrorResponse("'field_path' is required (serialized property path of the list/array field).");

            JToken entryTok = @params["entry"];
            if (entryTok == null || entryTok.Type == JTokenType.Null)
                return new ErrorResponse("'entry' is required.");

            bool dedupe = ParamCoercion.CoerceBool(@params["dedupe"], true);

            UnityEngine.Object resolvedTarget;
            string saveDescription;
            Action saveAction;
            try
            {
                (resolvedTarget, saveDescription, saveAction) = ResolveTarget(targetKind, @params);
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to resolve target: {ex.Message}");
            }

            if (resolvedTarget == null)
                return new ErrorResponse($"Target not found for kind '{targetKind}'.");

            var so = new SerializedObject(resolvedTarget);
            so.Update();

            var listProp = so.FindProperty(fieldPath);
            if (listProp == null)
                return new ErrorResponse($"Serialized property '{fieldPath}' not found on '{resolvedTarget.name}'.");
            if (!listProp.isArray)
                return new ErrorResponse($"Serialized property '{fieldPath}' is not an array/list.");

            // Resolve entry into a typed value.
            var entryDescriptor = ParseEntry(entryTok);
            if (entryDescriptor.Error != null)
                return new ErrorResponse(entryDescriptor.Error);

            // Dedupe.
            if (dedupe)
            {
                int existingIndex = FindExistingIndex(listProp, entryDescriptor);
                if (existingIndex >= 0)
                {
                    return new SuccessResponse("Entry already present; no change.", new
                    {
                        target = resolvedTarget.name,
                        field_path = fieldPath,
                        existing_index = existingIndex,
                        list_size = listProp.arraySize,
                        added = false,
                    });
                }
            }

            // Append.
            int newIndex = listProp.arraySize;
            listProp.arraySize = newIndex + 1;
            so.ApplyModifiedProperties();
            so.Update();

            var newElem = listProp.GetArrayElementAtIndex(newIndex);
            string assignError = AssignToProperty(newElem, entryDescriptor);
            if (assignError != null)
            {
                // Roll back the array resize so the caller doesn't end up with a half-written entry.
                listProp.arraySize = newIndex;
                so.ApplyModifiedProperties();
                return new ErrorResponse($"Failed to assign entry: {assignError}");
            }

            so.ApplyModifiedProperties();
            EditorUtility.SetDirty(resolvedTarget);

            try
            {
                saveAction?.Invoke();
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Entry assigned but save failed: {ex.Message}");
            }

            return new SuccessResponse($"Appended entry to '{fieldPath}' on '{resolvedTarget.name}'.", new
            {
                target = resolvedTarget.name,
                target_kind = targetKind,
                field_path = fieldPath,
                new_index = newIndex,
                list_size = listProp.arraySize,
                added = true,
                save = saveDescription,
            });
        }

        // -------------------- target resolution --------------------

        private static (UnityEngine.Object, string, Action) ResolveTarget(string kind, JObject p)
        {
            switch (kind)
            {
                case "asset":
                {
                    string assetPath = p["asset_path"]?.ToString() ?? p["assetPath"]?.ToString();
                    if (string.IsNullOrWhiteSpace(assetPath))
                        throw new InvalidOperationException("'asset_path' is required for target_kind='asset'.");
                    var so = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(assetPath);
                    if (so == null)
                        throw new InvalidOperationException($"No asset at '{assetPath}'.");
                    return (so, "AssetDatabase.SaveAssetIfDirty", () =>
                    {
                        AssetDatabase.SaveAssetIfDirty(so);
                    });
                }
                case "prefab":
                {
                    string prefabPath = p["prefab_path"]?.ToString() ?? p["prefabPath"]?.ToString();
                    string componentName = p["component"]?.ToString();
                    if (string.IsNullOrWhiteSpace(prefabPath) || string.IsNullOrWhiteSpace(componentName))
                        throw new InvalidOperationException("'prefab_path' and 'component' are required for target_kind='prefab'.");

                    var contents = PrefabUtility.LoadPrefabContents(prefabPath);
                    if (contents == null)
                        throw new InvalidOperationException($"Failed to load prefab '{prefabPath}'.");

                    var compType = GameObjectLookup.FindComponentType(componentName);
                    if (compType == null)
                    {
                        PrefabUtility.UnloadPrefabContents(contents);
                        throw new InvalidOperationException($"Component type '{componentName}' not found.");
                    }
                    var comp = contents.GetComponentInChildren(compType, includeInactive: true);
                    if (comp == null)
                    {
                        PrefabUtility.UnloadPrefabContents(contents);
                        throw new InvalidOperationException($"Component '{componentName}' not found on prefab '{prefabPath}'.");
                    }

                    return (comp, "PrefabUtility.SaveAsPrefabAsset", () =>
                    {
                        try
                        {
                            PrefabUtility.SaveAsPrefabAsset(contents, prefabPath);
                        }
                        finally
                        {
                            PrefabUtility.UnloadPrefabContents(contents);
                        }
                    });
                }
                case "scene_object":
                {
                    string find = p["find"]?.ToString();
                    string searchMethod = p["search_method"]?.ToString() ?? p["searchMethod"]?.ToString() ?? "by_id_or_name_or_path";
                    string componentName = p["component"]?.ToString();
                    string scenePath = p["scene_path"]?.ToString() ?? p["scenePath"]?.ToString();
                    if (string.IsNullOrWhiteSpace(find) || string.IsNullOrWhiteSpace(componentName))
                        throw new InvalidOperationException("'find' and 'component' are required for target_kind='scene_object'.");

                    Scene? loadedScene = null;
                    bool wasLoaded = false;
                    if (!string.IsNullOrWhiteSpace(scenePath))
                    {
                        var scene = SceneManager.GetSceneByPath(scenePath);
                        if (!scene.isLoaded)
                        {
                            loadedScene = EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Additive);
                            wasLoaded = true;
                        }
                        else
                        {
                            loadedScene = scene;
                        }
                    }

                    var go = GameObjectLookup.FindByTarget(new JValue(find), searchMethod, includeInactive: true);
                    if (go == null)
                        throw new InvalidOperationException($"GameObject '{find}' not found.");

                    var compType = GameObjectLookup.FindComponentType(componentName);
                    if (compType == null)
                        throw new InvalidOperationException($"Component type '{componentName}' not found.");

                    var comp = go.GetComponent(compType);
                    if (comp == null)
                        throw new InvalidOperationException($"Component '{componentName}' not on '{go.name}'.");

                    return (comp, "EditorSceneManager.SaveScene", () =>
                    {
                        var sceneToSave = loadedScene ?? go.scene;
                        EditorSceneManager.MarkSceneDirty(sceneToSave);
                        EditorSceneManager.SaveScene(sceneToSave);
                        if (wasLoaded && loadedScene.HasValue)
                        {
                            // Don't unload — the caller may want to inspect; SaveScene already persisted.
                        }
                    });
                }
                default:
                    throw new InvalidOperationException($"Unknown target_kind '{kind}'.");
            }
        }

        // -------------------- entry parsing & assignment --------------------

        private enum EntryKind { ObjectReference, Primitive, Struct }

        private struct EntryDescriptor
        {
            public string Error;
            public EntryKind Kind;
            public UnityEngine.Object ObjectReference;
            public JToken PrimitiveValue;
            // Sub-field map for struct entries: keys are sub-property names (relative to the
            // newly-appended array element), values are nested EntryDescriptors describing
            // either an object reference, a primitive, or a nested struct.
            public Dictionary<string, EntryDescriptor> StructFields;
        }

        private static EntryDescriptor ParseEntry(JToken entry)
        {
            if (entry is JObject obj)
            {
                string assetPath = obj["asset_path"]?.ToString() ?? obj["assetPath"]?.ToString();
                string assetGuid = obj["asset_guid"]?.ToString() ?? obj["assetGuid"]?.ToString();
                if (!string.IsNullOrEmpty(assetPath))
                {
                    var loaded = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(assetPath);
                    if (loaded == null) return new EntryDescriptor { Error = $"No asset at '{assetPath}'." };
                    return new EntryDescriptor { Kind = EntryKind.ObjectReference, ObjectReference = loaded };
                }
                if (!string.IsNullOrEmpty(assetGuid))
                {
                    var path = AssetDatabase.GUIDToAssetPath(assetGuid);
                    if (string.IsNullOrEmpty(path)) return new EntryDescriptor { Error = $"GUID '{assetGuid}' did not resolve." };
                    var loaded = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(path);
                    if (loaded == null) return new EntryDescriptor { Error = $"GUID '{assetGuid}' resolves to '{path}' but failed to load." };
                    return new EntryDescriptor { Kind = EntryKind.ObjectReference, ObjectReference = loaded };
                }
                if (obj["value"] != null)
                {
                    return new EntryDescriptor { Kind = EntryKind.Primitive, PrimitiveValue = obj["value"] };
                }
                if (obj["fields"] is JObject fields)
                {
                    var map = new Dictionary<string, EntryDescriptor>();
                    foreach (var prop in fields.Properties())
                    {
                        var nested = ParseEntry(prop.Value);
                        if (nested.Error != null)
                            return new EntryDescriptor { Error = $"fields.{prop.Name}: {nested.Error}" };
                        map[prop.Name] = nested;
                    }
                    return new EntryDescriptor { Kind = EntryKind.Struct, StructFields = map };
                }
                return new EntryDescriptor { Error = "entry must contain one of: asset_path, asset_guid, value, or fields." };
            }

            // Bare primitive
            return new EntryDescriptor { Kind = EntryKind.Primitive, PrimitiveValue = entry };
        }

        private static int FindExistingIndex(SerializedProperty listProp, EntryDescriptor entry)
        {
            for (int i = 0; i < listProp.arraySize; i++)
            {
                var el = listProp.GetArrayElementAtIndex(i);
                if (entry.Kind == EntryKind.ObjectReference)
                {
                    if (el.propertyType == SerializedPropertyType.ObjectReference
                        && el.objectReferenceValue == entry.ObjectReference)
                    {
                        return i;
                    }
                }
                else if (entry.Kind == EntryKind.Primitive)
                {
                    if (PrimitiveEquals(el, entry.PrimitiveValue))
                    {
                        return i;
                    }
                }
                else if (entry.Kind == EntryKind.Struct)
                {
                    // Struct dedupe: match if every named field equals (object refs by identity,
                    // primitives by value). Unspecified fields don't have to match.
                    if (StructEqualsExisting(el, entry.StructFields))
                    {
                        return i;
                    }
                }
            }
            return -1;
        }

        private static bool StructEqualsExisting(SerializedProperty element, Dictionary<string, EntryDescriptor> fields)
        {
            foreach (var kvp in fields)
            {
                var sub = element.FindPropertyRelative(kvp.Key);
                if (sub == null) return false;
                var v = kvp.Value;
                if (v.Kind == EntryKind.ObjectReference)
                {
                    if (sub.propertyType != SerializedPropertyType.ObjectReference) return false;
                    if (sub.objectReferenceValue != v.ObjectReference) return false;
                }
                else if (v.Kind == EntryKind.Primitive)
                {
                    if (!PrimitiveEquals(sub, v.PrimitiveValue)) return false;
                }
                else
                {
                    // Nested struct dedupe is rare; skip and treat as non-match to err on the
                    // side of NOT silently merging two complex entries.
                    return false;
                }
            }
            return true;
        }

        private static string AssignToProperty(SerializedProperty prop, EntryDescriptor entry)
        {
            if (entry.Kind == EntryKind.Struct)
            {
                if (prop.propertyType != SerializedPropertyType.Generic)
                    return $"Field is {prop.propertyType}, expected a struct (Generic property) for entry with 'fields'.";

                foreach (var kvp in entry.StructFields)
                {
                    var sub = prop.FindPropertyRelative(kvp.Key);
                    if (sub == null)
                        return $"Sub-field '{kvp.Key}' not found on element struct.";
                    var nestedError = AssignToProperty(sub, kvp.Value);
                    if (nestedError != null)
                        return $"fields.{kvp.Key}: {nestedError}";
                }
                return null;
            }

            if (entry.Kind == EntryKind.ObjectReference)
            {
                if (prop.propertyType != SerializedPropertyType.ObjectReference)
                    return $"Field is {prop.propertyType}, expected ObjectReference for asset entry.";
                prop.objectReferenceValue = entry.ObjectReference;
                return null;
            }

            try
            {
                switch (prop.propertyType)
                {
                    case SerializedPropertyType.Integer:
                        prop.intValue = entry.PrimitiveValue.Value<int>();
                        return null;
                    case SerializedPropertyType.Float:
                        prop.floatValue = entry.PrimitiveValue.Value<float>();
                        return null;
                    case SerializedPropertyType.Boolean:
                        prop.boolValue = entry.PrimitiveValue.Value<bool>();
                        return null;
                    case SerializedPropertyType.String:
                        prop.stringValue = entry.PrimitiveValue.Value<string>();
                        return null;
                    case SerializedPropertyType.Enum:
                        prop.enumValueIndex = entry.PrimitiveValue.Value<int>();
                        return null;
                    default:
                        return $"Unsupported primitive assignment for SerializedPropertyType '{prop.propertyType}'.";
                }
            }
            catch (Exception ex)
            {
                return ex.Message;
            }
        }

        private static bool PrimitiveEquals(SerializedProperty prop, JToken value)
        {
            if (value == null) return false;
            try
            {
                switch (prop.propertyType)
                {
                    case SerializedPropertyType.Integer:
                        return prop.intValue == value.Value<int>();
                    case SerializedPropertyType.Float:
                        return Mathf.Approximately(prop.floatValue, value.Value<float>());
                    case SerializedPropertyType.Boolean:
                        return prop.boolValue == value.Value<bool>();
                    case SerializedPropertyType.String:
                        return string.Equals(prop.stringValue, value.Value<string>(), StringComparison.Ordinal);
                    case SerializedPropertyType.Enum:
                        return prop.enumValueIndex == value.Value<int>();
                    default:
                        return false;
                }
            }
            catch
            {
                return false;
            }
        }
    }
}
