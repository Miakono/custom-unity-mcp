using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tools
{
    /// <summary>
    /// Single tool for ScriptableObject workflows:
    /// - action=create: create a ScriptableObject asset (and optionally apply patches)
    /// - action=modify: apply serialized property patches to an existing asset
    ///
    /// Patching is performed via SerializedObject/SerializedProperty paths (Unity-native), not reflection.
    /// </summary>
    [McpForUnityTool("manage_scriptable_object", AutoRegister = false, Group = "scripting_ext")]
    public static class ManageScriptableObject
    {
        private const string CodeCompilingOrReloading = "compiling_or_reloading";
        private const string CodeInvalidParams = "invalid_params";
        private const string CodeTypeNotFound = "type_not_found";
        private const string CodeInvalidFolderPath = "invalid_folder_path";
        private const string CodeTargetNotFound = "target_not_found";
        private const string CodeAssetCreateFailed = "asset_create_failed";

        private static readonly HashSet<string> ValidActions = new(StringComparer.OrdinalIgnoreCase)
        {
            // NOTE: Action strings are normalized by NormalizeAction() (lowercased, '_'/'-' removed),
            // so we only need the canonical normalized forms here.
            "create",
            "createso",
            "modify",
            "modifyso",
        };

        public static object HandleCommand(JObject @params)
        {
            if (@params == null)
            {
                return new ErrorResponse(CodeInvalidParams);
            }

            if (EditorApplication.isCompiling || EditorApplication.isUpdating)
            {
                // Unity is transient; treat as retryable on the client side.
                return new ErrorResponse(CodeCompilingOrReloading, new { hint = "retry" });
            }

            // Allow JSON-string parameters for objects/arrays.
            JsonUtil.CoerceJsonStringParameter(@params, "target");
            CoerceJsonStringArrayParameter(@params, "patches");

            string actionRaw = @params["action"]?.ToString();
            if (string.IsNullOrWhiteSpace(actionRaw))
            {
                return new ErrorResponse(CodeInvalidParams, new { message = "'action' is required.", validActions = ValidActions.ToArray() });
            }

            string action = NormalizeAction(actionRaw);
            if (!ValidActions.Contains(action))
            {
                return new ErrorResponse(CodeInvalidParams, new { message = $"Unknown action: '{actionRaw}'.", validActions = ValidActions.ToArray() });
            }

            if (IsCreateAction(action))
            {
                return HandleCreate(@params);
            }

            return HandleModify(@params);
        }

        private static object HandleCreate(JObject @params)
        {
            string typeName = @params["typeName"]?.ToString() ?? @params["type_name"]?.ToString();
            string folderPath = @params["folderPath"]?.ToString() ?? @params["folder_path"]?.ToString();
            string assetName = @params["assetName"]?.ToString() ?? @params["asset_name"]?.ToString();
            bool overwrite = @params["overwrite"]?.ToObject<bool?>() ?? false;

            if (string.IsNullOrWhiteSpace(typeName))
            {
                return new ErrorResponse(CodeInvalidParams, new { message = "'typeName' is required." });
            }

            if (string.IsNullOrWhiteSpace(folderPath))
            {
                return new ErrorResponse(CodeInvalidParams, new { message = "'folderPath' is required." });
            }

            if (string.IsNullOrWhiteSpace(assetName))
            {
                return new ErrorResponse(CodeInvalidParams, new { message = "'assetName' is required." });
            }

            if (assetName.Contains("/") || assetName.Contains("\\"))
            {
                return new ErrorResponse(CodeInvalidParams, new { message = "'assetName' must not contain path separators." });
            }

            if (!TryNormalizeFolderPath(folderPath, out var normalizedFolder, out var folderNormalizeError))
            {
                return new ErrorResponse(CodeInvalidFolderPath, new { message = folderNormalizeError, folderPath });
            }

            if (!EnsureFolderExists(normalizedFolder, out var folderError))
            {
                return new ErrorResponse(CodeInvalidFolderPath, new { message = folderError, folderPath = normalizedFolder });
            }

            var resolvedType = ResolveType(typeName);
            if (resolvedType == null || !typeof(ScriptableObject).IsAssignableFrom(resolvedType))
            {
                return new ErrorResponse(CodeTypeNotFound, new { message = $"ScriptableObject type not found: '{typeName}'", typeName });
            }

            string fileName = assetName.EndsWith(".asset", StringComparison.OrdinalIgnoreCase)
                ? assetName
                : assetName + ".asset";
            string desiredPath = $"{normalizedFolder.TrimEnd('/')}/{fileName}";
            string finalPath = overwrite ? desiredPath : AssetDatabase.GenerateUniqueAssetPath(desiredPath);

            ScriptableObject instance;
            try
            {
                instance = ScriptableObject.CreateInstance(resolvedType);
                if (instance == null)
                {
                    return new ErrorResponse(CodeAssetCreateFailed, new { message = "CreateInstance returned null.", typeName = resolvedType.FullName });
                }
            }
            catch (Exception ex)
            {
                return new ErrorResponse(CodeAssetCreateFailed, new { message = ex.Message, typeName = resolvedType.FullName });
            }

            // GUID-preserving overwrite logic
            bool isNewAsset = true;
            try
            {
                if (overwrite)
                {
                    var existingAsset = AssetDatabase.LoadAssetAtPath<ScriptableObject>(finalPath);
                    if (existingAsset != null && existingAsset.GetType() == resolvedType)
                    {
                        // Preserve GUID by overwriting existing asset data in-place
                        EditorUtility.CopySerialized(instance, existingAsset);
                        
                        // Fix for "Main Object Name does not match filename" warning:
                        // CopySerialized overwrites the name with the (empty) name of the new instance.
                        // We must restore the correct name to match the filename.
                        existingAsset.name = Path.GetFileNameWithoutExtension(finalPath);

                        UnityEngine.Object.DestroyImmediate(instance); // Destroy temporary instance
                        instance = existingAsset; // Proceed with patching the existing asset
                        isNewAsset = false;
                        
                        // Mark dirty to ensure changes are picked up
                        EditorUtility.SetDirty(instance);
                    }
                    else if (existingAsset != null)
                    {
                        // Type mismatch or not a ScriptableObject - must delete and recreate to change type, losing GUID
                        // (Or we could warn, but overwrite usually implies replacing)
                        AssetDatabase.DeleteAsset(finalPath);
                    }
                }

                if (isNewAsset)
                {
                    // Ensure the new instance has the correct name before creating asset to avoid warnings
                    instance.name = Path.GetFileNameWithoutExtension(finalPath);
                    AssetDatabase.CreateAsset(instance, finalPath);
                }
            }
            catch (Exception ex)
            {
                return new ErrorResponse(CodeAssetCreateFailed, new { message = ex.Message, path = finalPath });
            }

            string guid = AssetDatabase.AssetPathToGUID(finalPath);
            var patchesToken = @params["patches"];
            object patchResults = null;
            var warnings = new List<string>();

            if (patchesToken is JArray patches && patches.Count > 0)
            {
                var patchApply = SerializedPropertyPatcher.ApplyPatches(instance, patches);
                patchResults = patchApply.Results;
                warnings.AddRange(patchApply.Warnings);
            }

            EditorUtility.SetDirty(instance);
            AssetDatabase.SaveAssets();

            return new SuccessResponse(
                "ScriptableObject created.",
                new
                {
                    guid,
                    path = finalPath,
                    typeNameResolved = resolvedType.FullName,
                    patchResults,
                    warnings = warnings.Count > 0 ? warnings : null
                }
            );
        }

        private static object HandleModify(JObject @params)
        {
            if (!TryResolveTarget(@params["target"], out var target, out var targetPath, out var targetGuid, out var err))
            {
                return err;
            }

            var patchesToken = @params["patches"];
            if (patchesToken == null || patchesToken.Type == JTokenType.Null)
            {
                return new ErrorResponse(CodeInvalidParams, new { message = "'patches' is required.", targetPath, targetGuid });
            }

            if (patchesToken is not JArray patches)
            {
                return new ErrorResponse(CodeInvalidParams, new { message = "'patches' must be an array.", targetPath, targetGuid });
            }

            // Phase 5: Dry-run mode - validate patches without applying
            bool dryRun = @params["dryRun"]?.ToObject<bool?>() ?? @params["dry_run"]?.ToObject<bool?>() ?? false;
            
            if (dryRun)
            {
                var validationResults = ValidatePatches(target, patches);
                return new SuccessResponse(
                    "Dry-run validation complete.",
                    new
                    {
                        targetGuid,
                        targetPath,
                        targetTypeName = target.GetType().FullName,
                        dryRun = true,
                        valid = validationResults.All(r => (bool)r.GetType().GetProperty("ok")?.GetValue(r)),
                        validationResults
                    }
                );
            }

            var patchOutcome = SerializedPropertyPatcher.ApplyPatches(target, patches);
            if (patchOutcome.AnyChanged)
            {
                EditorUtility.SetDirty(target);
                AssetDatabase.SaveAssets();
            }

            return new SuccessResponse(
                "Serialized properties patched.",
                new
                {
                    targetGuid,
                    targetPath,
                    targetTypeName = target.GetType().FullName,
                    results = patchOutcome.Results,
                    warnings = patchOutcome.Warnings.Count > 0 ? patchOutcome.Warnings : null
                }
            );
        }

        /// <summary>
        /// Validates patches without applying them (for dry-run mode).
        /// Checks that property paths exist and that value types are compatible.
        /// </summary>
        private static List<object> ValidatePatches(UnityEngine.Object target, JArray patches)
        {
            var results = new List<object>(patches.Count);
            var so = new SerializedObject(target);
            so.Update();

            for (int i = 0; i < patches.Count; i++)
            {
                if (patches[i] is not JObject patchObj)
                {
                    results.Add(new { index = i, propertyPath = "", op = "", ok = false, message = $"Patch at index {i} must be an object." });
                    continue;
                }

                string propertyPath = patchObj["propertyPath"]?.ToString()
                    ?? patchObj["property_path"]?.ToString()
                    ?? patchObj["path"]?.ToString();
                string op = (patchObj["op"]?.ToString() ?? "set").Trim();

                if (string.IsNullOrWhiteSpace(propertyPath))
                {
                    results.Add(new { index = i, propertyPath = propertyPath ?? "", op, ok = false, message = "Missing required field: propertyPath" });
                    continue;
                }

                // Normalize the path
                string normalizedPath = SerializedPropertyPatcher.NormalizePropertyPath(propertyPath);
                string normalizedOp = op.ToLowerInvariant();

                // For array_resize, check if the array exists
                if (normalizedOp == "array_resize")
                {
                    var valueToken = patchObj["value"];
                    if (valueToken == null || valueToken.Type == JTokenType.Null)
                    {
                        results.Add(new { index = i, propertyPath = normalizedPath, op, ok = false, message = "array_resize requires integer 'value'." });
                        continue;
                    }

                    int size = ParamCoercion.CoerceInt(valueToken, -1);
                    if (size < 0)
                    {
                        results.Add(new { index = i, propertyPath = normalizedPath, op, ok = false, message = "array_resize requires non-negative integer 'value'." });
                        continue;
                    }

                    // Check if the array path exists
                    string arrayPath = normalizedPath;
                    if (arrayPath.EndsWith(".Array.size", StringComparison.Ordinal))
                    {
                        arrayPath = arrayPath.Substring(0, arrayPath.Length - ".Array.size".Length);
                    }

                    var arrayProp = so.FindProperty(arrayPath);
                    if (arrayProp == null)
                    {
                        results.Add(new { index = i, propertyPath = normalizedPath, op, ok = false, message = $"Array not found: {arrayPath}" });
                        continue;
                    }

                    if (!arrayProp.isArray)
                    {
                        results.Add(new { index = i, propertyPath = normalizedPath, op, ok = false, message = $"Property is not an array: {arrayPath}" });
                        continue;
                    }

                    results.Add(new { index = i, propertyPath = normalizedPath, op, ok = true, message = $"Will resize to {size}.", currentSize = arrayProp.arraySize });
                    continue;
                }

                // For set operations, check if the property exists (or can be auto-grown)
                var prop = so.FindProperty(normalizedPath);
                
                // Check if it's an auto-growable array element path
                bool isAutoGrowable = false;
                if (prop == null)
                {
                    var match = Regex.Match(normalizedPath, @"^(.+?)\.Array\.data\[(\d+)\]");
                    if (match.Success)
                    {
                        string arrayPath = match.Groups[1].Value;
                        var arrayProp = so.FindProperty(arrayPath);
                        if (arrayProp != null && arrayProp.isArray)
                        {
                            isAutoGrowable = true;
                            // Get the element type info from existing elements or report as growable
                            int targetIndex = int.Parse(match.Groups[2].Value);
                            if (arrayProp.arraySize > 0)
                            {
                                var sampleElement = arrayProp.GetArrayElementAtIndex(0);
                                results.Add(new { 
                                    index = i, 
                                    propertyPath = normalizedPath, 
                                    op, 
                                    ok = true, 
                                    message = $"Will auto-grow array from {arrayProp.arraySize} to {targetIndex + 1}.",
                                    elementType = sampleElement?.propertyType.ToString() ?? "unknown"
                                });
                            }
                            else
                            {
                                results.Add(new { 
                                    index = i, 
                                    propertyPath = normalizedPath, 
                                    op, 
                                    ok = true, 
                                    message = $"Will auto-grow empty array to size {targetIndex + 1}."
                                });
                            }
                            continue;
                        }
                    }
                }

                if (prop == null && !isAutoGrowable)
                {
                    results.Add(new { index = i, propertyPath = normalizedPath, op, ok = false, message = $"Property not found: {normalizedPath}" });
                    continue;
                }

                if (prop != null)
                {
                    // Property exists - validate value format for supported complex types
                    var valueToken = patchObj["value"];
                    string valueValidationMsg = null;
                    bool valueFormatOk = true;
                    
                    // Enhanced dry-run: validate value format for AnimationCurve and Quaternion
                    // Uses shared validators from VectorParsing
                    if (valueToken != null && valueToken.Type != JTokenType.Null)
                    {
                        switch (prop.propertyType)
                        {
                            case SerializedPropertyType.AnimationCurve:
                                valueFormatOk = VectorParsing.ValidateAnimationCurveFormat(valueToken, out valueValidationMsg);
                                break;
                            case SerializedPropertyType.Quaternion:
                                valueFormatOk = VectorParsing.ValidateQuaternionFormat(valueToken, out valueValidationMsg);
                                break;
                        }
                    }
                    
                    if (valueFormatOk)
                    {
                        results.Add(new { 
                            index = i, 
                            propertyPath = normalizedPath, 
                            op, 
                            ok = true, 
                            message = valueValidationMsg ?? "Property found.",
                            propertyType = prop.propertyType.ToString(),
                            isArray = prop.isArray
                        });
                    }
                    else
                    {
                        results.Add(new { 
                            index = i, 
                            propertyPath = normalizedPath, 
                            op, 
                            ok = false, 
                            message = valueValidationMsg,
                            propertyType = prop.propertyType.ToString(),
                            isArray = prop.isArray
                        });
                    }
                }
            }

            return results;
        }

        private static bool TryResolveTarget(JToken targetToken, out UnityEngine.Object target, out string targetPath, out string targetGuid, out object error)
        {
            target = null;
            targetPath = null;
            targetGuid = null;
            error = null;

            if (targetToken is not JObject targetObj)
            {
                error = new ErrorResponse(CodeInvalidParams, new { message = "'target' must be an object with {guid|path}." });
                return false;
            }

            string guid = targetObj["guid"]?.ToString();
            string path = targetObj["path"]?.ToString();

            if (string.IsNullOrWhiteSpace(guid) && string.IsNullOrWhiteSpace(path))
            {
                error = new ErrorResponse(CodeInvalidParams, new { message = "'target' must include 'guid' or 'path'." });
                return false;
            }

            string resolvedPath = !string.IsNullOrWhiteSpace(guid)
                ? AssetDatabase.GUIDToAssetPath(guid)
                : AssetPathUtility.SanitizeAssetPath(path);

            if (string.IsNullOrWhiteSpace(resolvedPath))
            {
                error = new ErrorResponse(CodeTargetNotFound, new { message = "Could not resolve target path.", guid, path });
                return false;
            }

            var obj = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(resolvedPath);
            if (obj == null)
            {
                error = new ErrorResponse(CodeTargetNotFound, new { message = "Target asset not found.", targetPath = resolvedPath, targetGuid = guid });
                return false;
            }

            target = obj;
            targetPath = resolvedPath;
            targetGuid = string.IsNullOrWhiteSpace(guid) ? AssetDatabase.AssetPathToGUID(resolvedPath) : guid;
            return true;
        }

        private static void CoerceJsonStringArrayParameter(JObject @params, string paramName)
        {
            var token = @params?[paramName];
            if (token != null && token.Type == JTokenType.String)
            {
                try
                {
                    var parsed = JToken.Parse(token.ToString());
                    if (parsed is JArray arr)
                    {
                        @params[paramName] = arr;
                    }
                }
                catch (Exception e)
                {
                    McpLog.Warn($"[MCP] Could not parse '{paramName}' JSON string: {e.Message}");
                }
            }
        }

        private static bool EnsureFolderExists(string folderPath, out string error)
        {
            error = null;
            if (string.IsNullOrWhiteSpace(folderPath))
            {
                error = "Folder path is empty.";
                return false;
            }

            // Expect normalized input here (Assets/... or Assets).
            string sanitized = SanitizeSlashes(folderPath);

            if (!sanitized.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase)
                && !string.Equals(sanitized, "Assets", StringComparison.OrdinalIgnoreCase))
            {
                error = "Folder path must be under Assets/.";
                return false;
            }

            if (string.Equals(sanitized, "Assets", StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }

            sanitized = sanitized.TrimEnd('/');
            if (AssetDatabase.IsValidFolder(sanitized))
            {
                return true;
            }

            // Create recursively from Assets/
            var parts = sanitized.Split(new[] { '/' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 0 || !string.Equals(parts[0], "Assets", StringComparison.OrdinalIgnoreCase))
            {
                error = "Folder path must start with Assets/";
                return false;
            }

            string current = "Assets";
            for (int i = 1; i < parts.Length; i++)
            {
                string next = current + "/" + parts[i];
                if (!AssetDatabase.IsValidFolder(next))
                {
                    string guid = AssetDatabase.CreateFolder(current, parts[i]);
                    if (string.IsNullOrEmpty(guid))
                    {
                        error = $"Failed to create folder: {next}";
                        return false;
                    }
                }
                current = next;
            }

            return AssetDatabase.IsValidFolder(sanitized);
        }

        private static string SanitizeSlashes(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                return path;
            }

            var s = AssetPathUtility.NormalizeSeparators(path);
            while (s.IndexOf("//", StringComparison.Ordinal) >= 0)
            {
                s = s.Replace("//", "/", StringComparison.Ordinal);
            }
            return s;
        }

        private static bool TryNormalizeFolderPath(string folderPath, out string normalized, out string error)
        {
            normalized = null;
            error = null;

            if (string.IsNullOrWhiteSpace(folderPath))
            {
                error = "Folder path is empty.";
                return false;
            }

            var s = SanitizeSlashes(folderPath.Trim());

            // Reject obvious non-project/invalid roots. We only support Assets/ (and relative paths that will be rooted under Assets/).
            if (s.StartsWith("/", StringComparison.Ordinal) 
                || s.StartsWith("file:", StringComparison.OrdinalIgnoreCase)
                || Regex.IsMatch(s, @"^[a-zA-Z]:"))
            {
                error = "Folder path must be a project-relative path under Assets/.";
                return false;
            }

            if (s.StartsWith("Packages/", StringComparison.OrdinalIgnoreCase)
                || s.StartsWith("ProjectSettings/", StringComparison.OrdinalIgnoreCase)
                || s.StartsWith("Library/", StringComparison.OrdinalIgnoreCase))
            {
                error = "Folder path must be under Assets/.";
                return false;
            }

            if (string.Equals(s, "Assets", StringComparison.OrdinalIgnoreCase))
            {
                normalized = "Assets";
                return true;
            }

            if (s.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase))
            {
                normalized = s.TrimEnd('/');
                return true;
            }

            // Allow relative paths like "Temp/MyFolder" and root them under Assets/.
            normalized = ("Assets/" + s.TrimStart('/')).TrimEnd('/');
            return true;
        }

        // NOTE: Local TryGet* helpers have been removed. 
        // Using shared helpers instead: ParamCoercion (for int/float/bool) and VectorParsing (for Vector2/3/4, Color)

        private static string NormalizeAction(string raw)
        {
            var s = raw.Trim();
            s = s.Replace("-", "").Replace("_", "");
            return s.ToLowerInvariant();
        }

        private static bool IsCreateAction(string normalized)
        {
            return normalized == "create" || normalized == "createso";
        }

        /// <summary>
        /// Resolves a type by name. Delegates to UnityTypeResolver.ResolveAny().
        /// </summary>
        private static Type ResolveType(string typeName)
        {
            return Helpers.UnityTypeResolver.ResolveAny(typeName);
        }
    }
}
