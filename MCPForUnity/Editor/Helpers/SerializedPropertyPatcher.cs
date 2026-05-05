using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Helpers
{
    /// <summary>
    /// Applies JSON-described SerializedProperty patches to any UnityEngine.Object that
    /// can be wrapped in a SerializedObject (ScriptableObject, Component on a prefab,
    /// Component on a scene GameObject). Caller is responsible for SetDirty / SaveAssets /
    /// SaveAsPrefabAsset / MarkSceneDirty after a successful patch — the helper only
    /// applies modified properties on the SerializedObject.
    /// </summary>
    public static class SerializedPropertyPatcher
    {
        public readonly struct PatchResult
        {
            public readonly List<object> Results;
            public readonly List<string> Warnings;
            public readonly bool AnyChanged;

            public PatchResult(List<object> results, List<string> warnings, bool anyChanged)
            {
                Results = results;
                Warnings = warnings;
                AnyChanged = anyChanged;
            }
        }

        public static PatchResult ApplyPatches(UnityEngine.Object target, JArray patches)
        {
            var warnings = new List<string>();
            var results = new List<object>(patches?.Count ?? 0);
            bool anyChanged = false;

            if (target == null)
            {
                results.Add(new { ok = false, message = "Target object is null." });
                return new PatchResult(results, warnings, false);
            }

            if (patches == null)
            {
                return new PatchResult(results, warnings, false);
            }

            var so = new SerializedObject(target);
            so.Update();

            for (int i = 0; i < patches.Count; i++)
            {
                if (patches[i] is not JObject patchObj)
                {
                    results.Add(new { propertyPath = "", op = "", ok = false, message = $"Patch at index {i} must be an object." });
                    continue;
                }

                string propertyPath = patchObj["propertyPath"]?.ToString()
                    ?? patchObj["property_path"]?.ToString()
                    ?? patchObj["path"]?.ToString();
                string op = (patchObj["op"]?.ToString() ?? "set").Trim();
                if (string.IsNullOrWhiteSpace(propertyPath))
                {
                    results.Add(new { propertyPath = propertyPath ?? "", op, ok = false, message = "Missing required field: propertyPath" });
                    continue;
                }

                if (string.IsNullOrWhiteSpace(op))
                {
                    op = "set";
                }

                var patchResult = ApplyPatch(so, propertyPath, op, patchObj, out bool changed);
                anyChanged |= changed;
                results.Add(patchResult);

                // Array resize should be applied immediately so later paths resolve.
                if (string.Equals(op, "array_resize", StringComparison.OrdinalIgnoreCase) && changed)
                {
                    so.ApplyModifiedProperties();
                    so.Update();
                }
            }

            if (anyChanged)
            {
                so.ApplyModifiedProperties();
            }

            return new PatchResult(results, warnings, anyChanged);
        }

        private static object ApplyPatch(SerializedObject so, string propertyPath, string op, JObject patchObj, out bool changed)
        {
            changed = false;
            try
            {
                string normalizedPath = NormalizePropertyPath(propertyPath);
                string normalizedOp = op.Trim().ToLowerInvariant();

                switch (normalizedOp)
                {
                    case "array_resize":
                        return ApplyArrayResize(so, normalizedPath, patchObj, out changed);
                    case "set":
                    default:
                        return ApplySet(so, normalizedPath, patchObj, out changed);
                }
            }
            catch (Exception ex)
            {
                return new { propertyPath, op, ok = false, message = ex.Message };
            }
        }

        /// <summary>
        /// Normalizes friendly property path syntax to Unity's internal format.
        /// Converts bracket notation (e.g., myList[5]) to Unity's Array.data format (myList.Array.data[5]).
        /// </summary>
        internal static string NormalizePropertyPath(string path)
        {
            if (string.IsNullOrEmpty(path))
                return path;

            return Regex.Replace(path, @"(\w+)\[(\d+)\]", m =>
            {
                string fieldName = m.Groups[1].Value;
                string index = m.Groups[2].Value;

                int matchStart = m.Index;
                if (fieldName == "data" && matchStart >= 7)
                {
                    string preceding = path.Substring(matchStart - 7, 7);
                    if (preceding == ".Array.")
                    {
                        return m.Value;
                    }
                }

                return $"{fieldName}.Array.data[{index}]";
            });
        }

        private static bool EnsureArrayCapacity(SerializedObject so, string path, out bool resized)
        {
            resized = false;

            var match = Regex.Match(path, @"^(.+?)\.Array\.data\[(\d+)\]");
            if (!match.Success)
            {
                return true;
            }

            string arrayPath = match.Groups[1].Value;
            if (!int.TryParse(match.Groups[2].Value, out int targetIndex))
            {
                return false;
            }

            var arrayProp = so.FindProperty(arrayPath);
            if (arrayProp == null || !arrayProp.isArray)
            {
                return false;
            }

            if (arrayProp.arraySize <= targetIndex)
            {
                arrayProp.arraySize = targetIndex + 1;
                so.ApplyModifiedProperties();
                so.Update();
                resized = true;
            }

            return true;
        }

        private static object ApplyArrayResize(SerializedObject so, string propertyPath, JObject patchObj, out bool changed)
        {
            changed = false;

            var valueToken = patchObj["value"];
            if (valueToken == null || valueToken.Type == JTokenType.Null)
            {
                return new { propertyPath, op = "array_resize", ok = false, message = "array_resize requires integer 'value'." };
            }

            int newSize = ParamCoercion.CoerceInt(valueToken, -1);
            if (newSize < 0)
            {
                return new { propertyPath, op = "array_resize", ok = false, message = "array_resize requires integer 'value'." };
            }

            newSize = Math.Max(0, newSize);

            SerializedProperty prop = so.FindProperty(propertyPath);
            SerializedProperty arrayProp = null;
            if (propertyPath.EndsWith(".Array.size", StringComparison.Ordinal))
            {
                var arrayPath = propertyPath.Substring(0, propertyPath.Length - ".Array.size".Length);
                arrayProp = so.FindProperty(arrayPath);
            }
            else
            {
                arrayProp = prop != null && prop.isArray ? prop : so.FindProperty(propertyPath + ".Array.size");
            }

            if (prop == null)
            {
                if (arrayProp != null && arrayProp.isArray)
                {
                    if (arrayProp.arraySize != newSize)
                    {
                        arrayProp.arraySize = newSize;
                        changed = true;
                    }
                    return new
                    {
                        propertyPath,
                        op = "array_resize",
                        ok = true,
                        resolvedPropertyType = "Array",
                        message = $"Set array size to {newSize}."
                    };
                }

                return new { propertyPath, op = "array_resize", ok = false, message = $"Property not found: {propertyPath}" };
            }

            if ((prop.propertyType == SerializedPropertyType.Integer || prop.propertyType == SerializedPropertyType.ArraySize)
                && propertyPath.EndsWith(".Array.size", StringComparison.Ordinal))
            {
                if (prop.intValue != newSize)
                {
                    prop.intValue = newSize;
                    changed = true;
                }
                return new { propertyPath, op = "array_resize", ok = true, resolvedPropertyType = prop.propertyType.ToString(), message = $"Set array size to {newSize}." };
            }

            if (prop.isArray)
            {
                if (prop.arraySize != newSize)
                {
                    prop.arraySize = newSize;
                    changed = true;
                }
                return new { propertyPath, op = "array_resize", ok = true, resolvedPropertyType = "Array", message = $"Set array size to {newSize}." };
            }

            return new { propertyPath, op = "array_resize", ok = false, resolvedPropertyType = prop.propertyType.ToString(), message = $"Property is not an array or array-size field: {propertyPath}" };
        }

        private static object ApplySet(SerializedObject so, string propertyPath, JObject patchObj, out bool changed)
        {
            changed = false;

            if (!EnsureArrayCapacity(so, propertyPath, out bool arrayResized))
            {
                var checkProp = so.FindProperty(propertyPath);
                if (checkProp == null)
                {
                    var arrayMatch = Regex.Match(propertyPath, @"^(.+?)\.Array\.data\[(\d+)\]");
                    if (arrayMatch.Success)
                    {
                        string arrayPath = arrayMatch.Groups[1].Value;
                        var arrayProp = so.FindProperty(arrayPath);
                        if (arrayProp == null)
                        {
                            return new { propertyPath, op = "set", ok = false, message = $"Array property not found: {arrayPath}" };
                        }
                        if (!arrayProp.isArray)
                        {
                            return new { propertyPath, op = "set", ok = false, message = $"Property is not an array: {arrayPath}" };
                        }
                    }
                    return new { propertyPath, op = "set", ok = false, message = $"Property not found: {propertyPath}" };
                }
            }

            var prop = so.FindProperty(propertyPath);
            if (prop == null)
            {
                return new { propertyPath, op = "set", ok = false, message = $"Property not found: {propertyPath}" };
            }

            if (arrayResized)
            {
                changed = true;
            }

            if (prop.propertyType == SerializedPropertyType.ObjectReference)
            {
                if (!TryResolveObjectReference(patchObj["value"], patchObj, out var newRef, out var resolveMethod, out var resolveError))
                {
                    return new { propertyPath, op = "set", ok = false, resolvedPropertyType = prop.propertyType.ToString(), message = resolveError };
                }

                if (prop.objectReferenceValue != newRef)
                {
                    prop.objectReferenceValue = newRef;
                    changed = true;
                }

                string refMessage = newRef == null ? "Cleared reference." : $"Set reference ({resolveMethod}).";
                return new { propertyPath, op = "set", ok = true, resolvedPropertyType = prop.propertyType.ToString(), message = refMessage };
            }

            var valueToken = patchObj["value"];
            if (valueToken == null)
            {
                return new { propertyPath, op = "set", ok = false, resolvedPropertyType = prop.propertyType.ToString(), message = "Missing required field: value" };
            }

            bool ok = TrySetValue(prop, valueToken, out string message);
            if (ok)
            {
                changed = true;
            }
            return new { propertyPath, op = "set", ok, resolvedPropertyType = prop.propertyType.ToString(), message };
        }

        private static bool TrySetValue(SerializedProperty prop, JToken valueToken, out string message)
        {
            return TrySetValueRecursive(prop, valueToken, out message, 0);
        }

        /// <summary>
        /// Resolves a JSON token into a UnityEngine.Object reference. Delegates to the
        /// shared <see cref="ObjectReferenceResolver"/>. Scene-name fallback is disabled —
        /// callers of SerializedPropertyPatcher (apply_scene_patch, apply_prefab_patch,
        /// manage_scriptable_object) require explicit asset references.
        /// 'NotFound' is treated as a successful resolve to null, matching the prior
        /// behavior where a missing GUID/path silently produced a null reference.
        /// </summary>
        private static bool TryResolveObjectReference(JToken valueToken, JObject patchObj,
            out UnityEngine.Object resolved, out string resolveMethod, out string error)
        {
            var result = ObjectReferenceResolver.Resolve(valueToken, patchObj, allowSceneNameFallback: false);

            resolved = null;
            resolveMethod = result.ResolveMethod ?? "explicit";
            error = null;

            switch (result.Outcome)
            {
                case ObjectReferenceResolver.ResolveOutcome.Resolved:
                    resolved = result.Asset;
                    return true;
                case ObjectReferenceResolver.ResolveOutcome.Cleared:
                    resolveMethod = "cleared";
                    return true;
                case ObjectReferenceResolver.ResolveOutcome.NotFound:
                    // Preserve prior SP behavior: missing asset becomes a null assignment.
                    return true;
                case ObjectReferenceResolver.ResolveOutcome.NeedsSceneSearch:
                case ObjectReferenceResolver.ResolveOutcome.Unrecognized:
                default:
                    error = result.Error ?? "Unrecognized object reference value.";
                    return false;
            }
        }

        private static bool TrySetValueRecursive(SerializedProperty prop, JToken valueToken, out string message, int depth)
        {
            message = null;
            const int MaxRecursionDepth = 20;

            if (depth > MaxRecursionDepth)
            {
                message = $"Maximum recursion depth ({MaxRecursionDepth}) exceeded. Check for circular references.";
                return false;
            }

            try
            {
                if (prop.isArray && prop.propertyType != SerializedPropertyType.String && valueToken is JArray jArray)
                {
                    prop.arraySize = jArray.Count;

                    var so = prop.serializedObject;
                    so.ApplyModifiedProperties();
                    so.Update();

                    int successCount = 0;
                    var errors = new List<string>();

                    for (int i = 0; i < jArray.Count; i++)
                    {
                        var elementProp = prop.GetArrayElementAtIndex(i);
                        if (elementProp == null)
                        {
                            errors.Add($"Could not get element at index {i}");
                            continue;
                        }

                        if (TrySetValueRecursive(elementProp, jArray[i], out string elemMessage, depth + 1))
                        {
                            successCount++;
                        }
                        else
                        {
                            errors.Add($"[{i}]: {elemMessage}");
                        }
                    }

                    so.ApplyModifiedProperties();

                    if (errors.Count > 0)
                    {
                        message = $"Set {successCount}/{jArray.Count} elements. Errors: {string.Join("; ", errors)}";
                        return successCount > 0;
                    }

                    message = $"Set array with {jArray.Count} elements.";
                    return true;
                }

                if (prop.propertyType == SerializedPropertyType.Generic && !prop.isArray && valueToken is JObject jObj)
                {
                    int successCount = 0;
                    var errors = new List<string>();
                    var so = prop.serializedObject;

                    foreach (var kvp in jObj)
                    {
                        string childPath = prop.propertyPath + "." + kvp.Key;
                        var childProp = so.FindProperty(childPath);

                        if (childProp == null)
                        {
                            errors.Add($"Property not found: {kvp.Key}");
                            continue;
                        }

                        if (TrySetValueRecursive(childProp, kvp.Value, out string childMessage, depth + 1))
                        {
                            successCount++;
                        }
                        else
                        {
                            errors.Add($"{kvp.Key}: {childMessage}");
                        }
                    }

                    so.ApplyModifiedProperties();

                    if (errors.Count > 0)
                    {
                        message = $"Set {successCount}/{jObj.Count} fields. Errors: {string.Join("; ", errors)}";
                        return successCount > 0;
                    }

                    message = $"Set struct/class with {jObj.Count} fields.";
                    return true;
                }

                switch (prop.propertyType)
                {
                    case SerializedPropertyType.Integer:
                        int intVal = ParamCoercion.CoerceInt(valueToken, int.MinValue);
                        if (intVal == int.MinValue && valueToken?.Type != JTokenType.Integer)
                        {
                            if (valueToken == null || valueToken.Type == JTokenType.Null ||
                                (valueToken.Type == JTokenType.String && !int.TryParse(valueToken.ToString(), out _)))
                            {
                                message = "Expected integer value.";
                                return false;
                            }
                        }
                        prop.intValue = intVal;
                        message = "Set int.";
                        return true;

                    case SerializedPropertyType.Boolean:
                        if (valueToken == null || valueToken.Type == JTokenType.Null)
                        {
                            message = "Expected boolean value.";
                            return false;
                        }
                        bool boolVal = ParamCoercion.CoerceBool(valueToken, false);
                        if (valueToken.Type != JTokenType.Boolean)
                        {
                            string strVal = valueToken.ToString().Trim().ToLowerInvariant();
                            if (strVal != "true" && strVal != "false" && strVal != "1" && strVal != "0" &&
                                strVal != "yes" && strVal != "no" && strVal != "on" && strVal != "off")
                            {
                                message = "Expected boolean value.";
                                return false;
                            }
                        }
                        prop.boolValue = boolVal;
                        message = "Set bool.";
                        return true;

                    case SerializedPropertyType.Float:
                        float floatVal = ParamCoercion.CoerceFloat(valueToken, float.NaN);
                        if (float.IsNaN(floatVal))
                        {
                            message = "Expected float value.";
                            return false;
                        }
                        prop.floatValue = floatVal;
                        message = "Set float.";
                        return true;

                    case SerializedPropertyType.String:
                        prop.stringValue = valueToken.Type == JTokenType.Null ? null : valueToken.ToString();
                        message = "Set string.";
                        return true;

                    case SerializedPropertyType.Enum:
                        return TrySetEnum(prop, valueToken, out message);

                    case SerializedPropertyType.Vector2:
                    {
                        var v2 = VectorParsing.ParseVector2(valueToken);
                        if (v2 == null)
                        {
                            message = "Expected Vector2 (array or object).";
                            return false;
                        }
                        prop.vector2Value = v2.Value;
                        message = "Set Vector2.";
                        return true;
                    }

                    case SerializedPropertyType.Vector3:
                    {
                        var v3 = VectorParsing.ParseVector3(valueToken);
                        if (v3 == null)
                        {
                            message = "Expected Vector3 (array or object).";
                            return false;
                        }
                        prop.vector3Value = v3.Value;
                        message = "Set Vector3.";
                        return true;
                    }

                    case SerializedPropertyType.Vector4:
                    {
                        var v4 = VectorParsing.ParseVector4(valueToken);
                        if (v4 == null)
                        {
                            message = "Expected Vector4 (array or object).";
                            return false;
                        }
                        prop.vector4Value = v4.Value;
                        message = "Set Vector4.";
                        return true;
                    }

                    case SerializedPropertyType.Color:
                    {
                        var col = VectorParsing.ParseColor(valueToken);
                        if (col == null)
                        {
                            message = "Expected Color (array or object).";
                            return false;
                        }
                        prop.colorValue = col.Value;
                        message = "Set Color.";
                        return true;
                    }

                    case SerializedPropertyType.AnimationCurve:
                        return TrySetAnimationCurve(prop, valueToken, out message);

                    case SerializedPropertyType.Quaternion:
                        return TrySetQuaternion(prop, valueToken, out message);

                    case SerializedPropertyType.ObjectReference:
                    {
                        JObject refSubObject = valueToken as JObject;
                        if (!TryResolveObjectReference(valueToken, refSubObject, out var newRef, out var resolveMethod, out var resolveError))
                        {
                            message = resolveError;
                            return false;
                        }
                        prop.objectReferenceValue = newRef;
                        message = newRef == null ? "Cleared reference." : $"Set reference ({resolveMethod}).";
                        return true;
                    }

                    case SerializedPropertyType.LayerMask:
                        return TrySetLayerMask(prop, valueToken, out message);

                    case SerializedPropertyType.Vector2Int:
                    {
                        var v2i = VectorParsing.ParseVector2Int(valueToken);
                        if (v2i == null)
                        {
                            message = "Expected Vector2Int (array [x,y] or object {x,y}).";
                            return false;
                        }
                        prop.vector2IntValue = v2i.Value;
                        message = "Set Vector2Int.";
                        return true;
                    }

                    case SerializedPropertyType.Vector3Int:
                    {
                        var v3i = VectorParsing.ParseVector3Int(valueToken);
                        if (v3i == null)
                        {
                            message = "Expected Vector3Int (array [x,y,z] or object {x,y,z}).";
                            return false;
                        }
                        prop.vector3IntValue = v3i.Value;
                        message = "Set Vector3Int.";
                        return true;
                    }

                    case SerializedPropertyType.Rect:
                    {
                        var rect = VectorParsing.ParseRect(valueToken);
                        if (rect == null)
                        {
                            message = "Expected Rect ({x,y,width,height} or [x,y,width,height]).";
                            return false;
                        }
                        prop.rectValue = rect.Value;
                        message = "Set Rect.";
                        return true;
                    }

                    case SerializedPropertyType.RectInt:
                    {
                        var rectInt = VectorParsing.ParseRectInt(valueToken);
                        if (rectInt == null)
                        {
                            message = "Expected RectInt ({x,y,width,height} or [x,y,width,height]).";
                            return false;
                        }
                        prop.rectIntValue = rectInt.Value;
                        message = "Set RectInt.";
                        return true;
                    }

                    case SerializedPropertyType.Bounds:
                    {
                        var bounds = VectorParsing.ParseBounds(valueToken);
                        if (bounds == null)
                        {
                            message = "Expected Bounds ({center:{x,y,z}, size:{x,y,z}}).";
                            return false;
                        }
                        prop.boundsValue = bounds.Value;
                        message = "Set Bounds.";
                        return true;
                    }

                    case SerializedPropertyType.BoundsInt:
                    {
                        var boundsInt = VectorParsing.ParseBoundsInt(valueToken);
                        if (boundsInt == null)
                        {
                            message = "Expected BoundsInt ({position:{x,y,z}, size:{x,y,z}}).";
                            return false;
                        }
                        prop.boundsIntValue = boundsInt.Value;
                        message = "Set BoundsInt.";
                        return true;
                    }

                    case SerializedPropertyType.Gradient:
                        return TrySetGradient(prop, valueToken, out message);

                    case SerializedPropertyType.Hash128:
                    {
                        if (valueToken == null || valueToken.Type == JTokenType.Null)
                        {
                            message = "Expected Hash128 hex string.";
                            return false;
                        }
                        try
                        {
                            prop.hash128Value = Hash128.Parse(valueToken.ToString());
                            message = "Set Hash128.";
                            return true;
                        }
                        catch (Exception ex)
                        {
                            message = $"Invalid Hash128 string '{valueToken}': {ex.Message}";
                            return false;
                        }
                    }

                    case SerializedPropertyType.Generic:
                        if (prop.isArray)
                        {
                            message = $"Expected array (JArray) for array property, got {valueToken?.Type.ToString() ?? "null"}.";
                        }
                        else
                        {
                            message = $"Expected object (JObject) for struct/class property, got {valueToken?.Type.ToString() ?? "null"}.";
                        }
                        return false;

                    default:
                        message = $"Unsupported SerializedPropertyType: {prop.propertyType}. " +
                                  "This type cannot be set via MCP patches. Consider editing the .asset file directly " +
                                  "or using Unity's Inspector. For complex types, check if there's a supported alternative format.";
                        return false;
                }
            }
            catch (Exception ex)
            {
                message = ex.Message;
                return false;
            }
        }

        private static bool TrySetLayerMask(SerializedProperty prop, JToken valueToken, out string message)
        {
            message = null;
            if (valueToken == null || valueToken.Type == JTokenType.Null)
            {
                prop.intValue = 0;
                message = "Cleared LayerMask.";
                return true;
            }

            try
            {
                if (valueToken.Type == JTokenType.Integer)
                {
                    prop.intValue = valueToken.Value<int>();
                    message = "Set LayerMask (raw mask).";
                    return true;
                }

                if (valueToken.Type == JTokenType.String)
                {
                    string layerName = valueToken.ToString();
                    int layer = LayerMask.NameToLayer(layerName);
                    if (layer < 0)
                    {
                        message = $"Unknown layer name '{layerName}'.";
                        return false;
                    }
                    prop.intValue = 1 << layer;
                    message = $"Set LayerMask to layer '{layerName}'.";
                    return true;
                }

                if (valueToken is JArray arr)
                {
                    int mask = 0;
                    foreach (var item in arr)
                    {
                        if (item.Type == JTokenType.Integer)
                        {
                            int idx = item.Value<int>();
                            if (idx < 0 || idx > 31)
                            {
                                message = $"LayerMask layer index out of range (0-31): {idx}";
                                return false;
                            }
                            mask |= 1 << idx;
                        }
                        else if (item.Type == JTokenType.String)
                        {
                            string name = item.ToString();
                            int layer = LayerMask.NameToLayer(name);
                            if (layer < 0)
                            {
                                message = $"Unknown layer name '{name}'.";
                                return false;
                            }
                            mask |= 1 << layer;
                        }
                        else
                        {
                            message = $"LayerMask array elements must be int or string, got {item.Type}.";
                            return false;
                        }
                    }
                    prop.intValue = mask;
                    message = $"Set LayerMask from {arr.Count} entries.";
                    return true;
                }
            }
            catch (Exception ex)
            {
                message = $"Failed to parse LayerMask: {ex.Message}";
                return false;
            }

            message = "LayerMask requires int (raw mask), string (layer name), or array of int/string.";
            return false;
        }

        // Cached for SerializedProperty.gradientValue, which is internal in Unity 2021.3
        // and only became public in 2022.1. Resolved once and reused.
        private static System.Reflection.PropertyInfo s_gradientValueProperty;

        private static bool TrySetGradient(SerializedProperty prop, JToken valueToken, out string message)
        {
            message = null;
            var gradient = VectorParsing.ParseGradient(valueToken);
            if (gradient == null)
            {
                message = "Expected Gradient ({startColor,endColor} or {colorKeys:[...], alphaKeys:[...]}).";
                return false;
            }

            try
            {
                if (s_gradientValueProperty == null)
                {
                    s_gradientValueProperty = typeof(SerializedProperty).GetProperty(
                        "gradientValue",
                        System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic);
                }

                if (s_gradientValueProperty == null)
                {
                    message = "SerializedProperty.gradientValue not available in this Unity version.";
                    return false;
                }

                s_gradientValueProperty.SetValue(prop, gradient);
                message = "Set Gradient.";
                return true;
            }
            catch (Exception ex)
            {
                message = $"Failed to set Gradient: {ex.Message}";
                return false;
            }
        }

        private static bool TrySetEnum(SerializedProperty prop, JToken valueToken, out string message)
        {
            message = null;
            var names = prop.enumNames;
            if (names == null || names.Length == 0) { message = "Enum has no names."; return false; }

            if (valueToken.Type == JTokenType.Integer)
            {
                int idx = valueToken.Value<int>();
                if (idx < 0 || idx >= names.Length) { message = $"Enum index out of range: {idx}"; return false; }
                prop.enumValueIndex = idx; message = "Set enum."; return true;
            }

            string s = valueToken.ToString();
            for (int i = 0; i < names.Length; i++)
            {
                if (string.Equals(names[i], s, StringComparison.OrdinalIgnoreCase))
                {
                    prop.enumValueIndex = i; message = "Set enum."; return true;
                }
            }
            message = $"Unknown enum name '{s}'.";
            return false;
        }

        private static bool TrySetAnimationCurve(SerializedProperty prop, JToken valueToken, out string message)
        {
            message = null;

            if (valueToken == null || valueToken.Type == JTokenType.Null)
            {
                prop.animationCurveValue = new AnimationCurve();
                message = "Set AnimationCurve to empty.";
                return true;
            }

            JArray keysArray = null;

            if (valueToken is JObject curveObj)
            {
                keysArray = curveObj["keys"] as JArray;
                if (keysArray == null)
                {
                    message = "AnimationCurve object requires 'keys' array. Expected: { \"keys\": [ { \"time\": 0, \"value\": 0 }, ... ] }";
                    return false;
                }
            }
            else if (valueToken is JArray directArray)
            {
                keysArray = directArray;
            }
            else
            {
                message = "AnimationCurve requires object with 'keys' or array of keyframes. " +
                          "Expected: { \"keys\": [ { \"time\": 0, \"value\": 0, \"inSlope\": 0, \"outSlope\": 0 }, ... ] }";
                return false;
            }

            try
            {
                var curve = new AnimationCurve();
                foreach (var keyToken in keysArray)
                {
                    if (keyToken is not JObject keyObj)
                    {
                        message = "Each keyframe must be an object with 'time' and 'value'.";
                        return false;
                    }

                    float time = keyObj["time"]?.Value<float>() ?? 0f;
                    float value = keyObj["value"]?.Value<float>() ?? 0f;
                    float inSlope = keyObj["inSlope"]?.Value<float>() ?? keyObj["inTangent"]?.Value<float>() ?? 0f;
                    float outSlope = keyObj["outSlope"]?.Value<float>() ?? keyObj["outTangent"]?.Value<float>() ?? 0f;

                    var keyframe = new Keyframe(time, value, inSlope, outSlope);

                    if (keyObj["weightedMode"] != null)
                    {
                        int weightedMode = keyObj["weightedMode"].Value<int>();
                        keyframe.weightedMode = (WeightedMode)weightedMode;
                    }
                    if (keyObj["inWeight"] != null)
                    {
                        keyframe.inWeight = keyObj["inWeight"].Value<float>();
                    }
                    if (keyObj["outWeight"] != null)
                    {
                        keyframe.outWeight = keyObj["outWeight"].Value<float>();
                    }

                    curve.AddKey(keyframe);
                }

                prop.animationCurveValue = curve;
                message = $"Set AnimationCurve with {keysArray.Count} keyframes.";
                return true;
            }
            catch (Exception ex)
            {
                message = $"Failed to parse AnimationCurve: {ex.Message}";
                return false;
            }
        }

        private static bool TrySetQuaternion(SerializedProperty prop, JToken valueToken, out string message)
        {
            message = null;

            if (valueToken == null || valueToken.Type == JTokenType.Null)
            {
                prop.quaternionValue = Quaternion.identity;
                message = "Set Quaternion to identity.";
                return true;
            }

            try
            {
                if (valueToken is JArray arr)
                {
                    if (arr.Count == 3)
                    {
                        var euler = new Vector3(
                            arr[0].Value<float>(),
                            arr[1].Value<float>(),
                            arr[2].Value<float>()
                        );
                        prop.quaternionValue = Quaternion.Euler(euler);
                        message = $"Set Quaternion from Euler({euler.x}, {euler.y}, {euler.z}).";
                        return true;
                    }
                    else if (arr.Count == 4)
                    {
                        prop.quaternionValue = new Quaternion(
                            arr[0].Value<float>(),
                            arr[1].Value<float>(),
                            arr[2].Value<float>(),
                            arr[3].Value<float>()
                        );
                        message = "Set Quaternion from [x, y, z, w].";
                        return true;
                    }
                    else
                    {
                        message = "Quaternion array must have 3 elements (Euler) or 4 elements (x, y, z, w).";
                        return false;
                    }
                }
                else if (valueToken is JObject obj)
                {
                    if (obj["euler"] is JArray eulerArr && eulerArr.Count == 3)
                    {
                        var euler = new Vector3(
                            eulerArr[0].Value<float>(),
                            eulerArr[1].Value<float>(),
                            eulerArr[2].Value<float>()
                        );
                        prop.quaternionValue = Quaternion.Euler(euler);
                        message = $"Set Quaternion from euler: ({euler.x}, {euler.y}, {euler.z}).";
                        return true;
                    }

                    if (obj["x"] != null && obj["y"] != null && obj["z"] != null && obj["w"] != null)
                    {
                        prop.quaternionValue = new Quaternion(
                            obj["x"].Value<float>(),
                            obj["y"].Value<float>(),
                            obj["z"].Value<float>(),
                            obj["w"].Value<float>()
                        );
                        message = "Set Quaternion from { x, y, z, w }.";
                        return true;
                    }

                    message = "Quaternion object must have { x, y, z, w } or { euler: [x, y, z] }.";
                    return false;
                }
                else
                {
                    message = "Quaternion requires array [x,y,z] (Euler), [x,y,z,w] (raw), or object { x, y, z, w }.";
                    return false;
                }
            }
            catch (Exception ex)
            {
                message = $"Failed to parse Quaternion: {ex.Message}";
                return false;
            }
        }
    }
}
