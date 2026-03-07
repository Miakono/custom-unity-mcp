using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Services;
using MCPForUnity.Editor.Tools.PackageManager;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace MCPForUnity.Editor.Tools
{
    internal static class LiveV2V3ToolState
    {
        internal sealed class TraceSession
        {
            public string TraceId;
            public DateTime StartedAtUtc;
            public List<string> Tags = new List<string>();
            public List<object> Entries = new List<object>();
            public bool IsActive;
        }

        internal sealed class TransactionSession
        {
            public string TransactionId;
            public string Name;
            public string Status;
            public string CheckpointId;
            public DateTime CreatedAtUtc;
            public DateTime? CompletedAtUtc;
            public List<Dictionary<string, object>> Changes = new List<Dictionary<string, object>>();
        }

        internal sealed class EditorSubscription
        {
            public string SubscriptionId;
            public List<string> EventTypes = new List<string>();
            public string CreatedAt;
            public string ExpiresAt;
            public Dictionary<string, object> FilterCriteria = new Dictionary<string, object>();
            public bool BufferEvents;
            public bool IsActive;
        }

        internal sealed class BenchmarkRun
        {
            public string RunId;
            public string BenchmarkName;
            public DateTime StartedAtUtc;
            public DateTime CompletedAtUtc;
            public List<Dictionary<string, object>> Results = new List<Dictionary<string, object>>();
        }

        internal sealed class AssetIndexEntry
        {
            public string Guid;
            public string Path;
            public string Type;
            public string ImporterType;
            public long SizeBytes;
            public DateTime ModifiedAtUtc;
            public List<string> Dependencies = new List<string>();
            public List<string> ReferencedBy = new List<string>();
            public List<string> Labels = new List<string>();
        }

        internal sealed class AssetIndexSnapshot
        {
            public string SnapshotId;
            public string Scope;
            public DateTime BuiltAtUtc;
            public bool IncludeDependencies;
            public bool IncludeReferences;
            public bool IncludeImportSettings;
            public Dictionary<string, AssetIndexEntry> Entries = new Dictionary<string, AssetIndexEntry>(StringComparer.OrdinalIgnoreCase);
        }

        internal static readonly Dictionary<string, TraceSession> ActiveTraces = new Dictionary<string, TraceSession>();
        internal static readonly Dictionary<string, TraceSession> CompletedTraces = new Dictionary<string, TraceSession>();
        internal static readonly Dictionary<string, TransactionSession> Transactions = new Dictionary<string, TransactionSession>();
        internal static readonly Dictionary<string, EditorSubscription> Subscriptions = new Dictionary<string, EditorSubscription>();
        internal static readonly Dictionary<string, BenchmarkRun> Benchmarks = new Dictionary<string, BenchmarkRun>();
        internal static string CurrentTraceId;
        internal static bool ImportPaused;
        internal static AssetIndexSnapshot CurrentAssetIndex;
    }

    internal static class LiveV2V3ToolCommon
    {
        internal static JToken GetParam(JObject @params, params string[] names)
        {
            if (@params == null || names == null)
            {
                return null;
            }

            foreach (string name in names)
            {
                if (string.IsNullOrWhiteSpace(name))
                {
                    continue;
                }

                JToken token = @params[name];
                if (token != null && token.Type != JTokenType.Null)
                {
                    return token;
                }
            }

            return null;
        }

        internal static string GetStringParam(JObject @params, params string[] names)
        {
            return GetParam(@params, names)?.ToString();
        }

        internal static bool? GetBoolParam(JObject @params, params string[] names)
        {
            JToken token = GetParam(@params, names);
            return token?.Value<bool?>();
        }

        internal static int? GetIntParam(JObject @params, params string[] names)
        {
            JToken token = GetParam(@params, names);
            return token?.Value<int?>();
        }

        internal static ToolParams Wrap(JObject @params)
        {
            return new ToolParams(@params ?? new JObject());
        }

        internal static JObject GetEditorStateSnapshot()
        {
            return EditorStateCache.GetSnapshot();
        }

        internal static string SanitizeAssetPath(string path)
        {
            return AssetPathUtility.SanitizeAssetPath(path);
        }

        internal static UnityEngine.Object ResolveUnityObject(JToken targetToken)
        {
            if (targetToken == null || targetToken.Type == JTokenType.Null)
            {
                return UnityEditor.Selection.activeObject;
            }

            if (targetToken.Type == JTokenType.Integer)
            {
                return UnityEditorObjectLookup.FindObjectByInstanceId(targetToken.Value<int>());
            }

            if (targetToken.Type == JTokenType.String)
            {
                return ResolveByString(targetToken.Value<string>());
            }

            if (targetToken is not JObject target)
            {
                return null;
            }

            JToken instanceIdToken = target["instance_id"] ?? target["instanceId"];
            if (instanceIdToken != null && instanceIdToken.Type == JTokenType.Integer)
            {
                UnityEngine.Object byId = UnityEditorObjectLookup.FindObjectByInstanceId(instanceIdToken.Value<int>());
                if (byId != null)
                {
                    return byId;
                }
            }

            string guid = target.Value<string>("guid");
            if (!string.IsNullOrWhiteSpace(guid))
            {
                string guidPath = AssetDatabase.GUIDToAssetPath(guid);
                if (!string.IsNullOrWhiteSpace(guidPath))
                {
                    UnityEngine.Object byGuid = AssetDatabase.LoadMainAssetAtPath(guidPath);
                    if (byGuid != null)
                    {
                        return byGuid;
                    }
                }
            }

            string path = target.Value<string>("path");
            if (!string.IsNullOrWhiteSpace(path))
            {
                UnityEngine.Object byPath = ResolveByString(path);
                if (byPath != null)
                {
                    return byPath;
                }
            }

            string name = target.Value<string>("name");
            if (!string.IsNullOrWhiteSpace(name))
            {
                UnityEngine.Object byName = ResolveByString(name);
                if (byName != null)
                {
                    return byName;
                }
            }

            return null;
        }

        internal static GameObject ResolveGameObject(JToken targetToken)
        {
            UnityEngine.Object resolved = ResolveUnityObject(targetToken);
            if (resolved is GameObject gameObject)
            {
                return gameObject;
            }

            if (resolved is Component component)
            {
                return component.gameObject;
            }

            return null;
        }

        internal static string[] ExpandAssetPaths(JArray pathsToken)
        {
            if (pathsToken == null || pathsToken.Count == 0)
            {
                return Array.Empty<string>();
            }

            List<string> results = new List<string>();
            foreach (JToken token in pathsToken)
            {
                string raw = token?.ToString();
                if (string.IsNullOrWhiteSpace(raw))
                {
                    continue;
                }

                string sanitized = SanitizeAssetPath(raw);
                if (AssetDatabase.IsValidFolder(sanitized))
                {
                    string[] folderGuids = AssetDatabase.FindAssets(string.Empty, new[] { sanitized });
                    foreach (string guid in folderGuids)
                    {
                        string assetPath = AssetDatabase.GUIDToAssetPath(guid);
                        if (!string.IsNullOrWhiteSpace(assetPath))
                        {
                            results.Add(assetPath);
                        }
                    }
                }
                else
                {
                    results.Add(sanitized);
                }
            }

            return results.Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        }

        internal static Dictionary<string, object> BuildEditorContext()
        {
            Scene activeScene = EditorSceneManager.GetActiveScene();
            return new Dictionary<string, object>
            {
                ["selectionInstanceIds"] = UnityEditor.Selection.objects
                    .Where(obj => obj != null)
                    .Select(obj => obj.GetInstanceID())
                    .ToArray(),
                ["activeObjectName"] = UnityEditor.Selection.activeObject != null ? UnityEditor.Selection.activeObject.name : null,
                ["activeScenePath"] = activeScene.path,
                ["activeSceneName"] = activeScene.name,
                ["editorState"] = GetEditorStateSnapshot(),
            };
        }

        internal static Dictionary<string, object> DescribeObject(UnityEngine.Object target)
        {
            if (target == null)
            {
                return null;
            }

            string assetPath = AssetDatabase.GetAssetPath(target);
            return new Dictionary<string, object>
            {
                ["name"] = target.name,
                ["type"] = target.GetType().Name,
                ["instanceId"] = target.GetInstanceID(),
                ["assetPath"] = string.IsNullOrWhiteSpace(assetPath) ? null : assetPath,
            };
        }

        internal static object ApplyStaticSettings(Type targetType, JObject settings, HashSet<string> allowedProperties = null)
        {
            if (settings == null)
            {
                return new ErrorResponse("'settings' payload is required.");
            }

            List<string> updated = new List<string>();
            List<string> skipped = new List<string>();

            foreach (JProperty property in settings.Properties())
            {
                if (allowedProperties != null && !allowedProperties.Contains(property.Name))
                {
                    skipped.Add(property.Name);
                    continue;
                }

                if (!TrySetProperty(targetType, null, property.Name, property.Value))
                {
                    skipped.Add(property.Name);
                    continue;
                }

                updated.Add(property.Name);
            }

            AssetDatabase.SaveAssets();
            return new SuccessResponse(
                $"Updated {updated.Count} setting(s).",
                new
                {
                    updated,
                    skipped,
                }
            );
        }

        internal static bool TrySetProperty(Type targetType, object target, string propertyName, JToken value)
        {
            BindingFlags flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance | BindingFlags.IgnoreCase;
            PropertyInfo property = targetType.GetProperty(propertyName, flags);
            if (property != null && property.CanWrite)
            {
                object converted = ConvertToken(value, property.PropertyType);
                if (converted != null || Nullable.GetUnderlyingType(property.PropertyType) != null || !property.PropertyType.IsValueType)
                {
                    property.SetValue(target, converted);
                    return true;
                }
            }

            FieldInfo field = targetType.GetField(propertyName, flags);
            if (field != null)
            {
                object converted = ConvertToken(value, field.FieldType);
                if (converted != null || Nullable.GetUnderlyingType(field.FieldType) != null || !field.FieldType.IsValueType)
                {
                    field.SetValue(target, converted);
                    return true;
                }
            }

            return false;
        }

        internal static object ConvertToken(JToken token, Type targetType)
        {
            if (token == null || token.Type == JTokenType.Null)
            {
                return null;
            }

            Type underlying = Nullable.GetUnderlyingType(targetType) ?? targetType;
            if (underlying == typeof(string))
            {
                return token.ToString();
            }

            if (underlying.IsEnum)
            {
                return Enum.Parse(underlying, token.ToString(), true);
            }

            if (underlying == typeof(bool))
            {
                return token.Type == JTokenType.Boolean ? token.Value<bool>() : bool.Parse(token.ToString());
            }

            if (underlying == typeof(int))
            {
                return token.Value<int>();
            }

            if (underlying == typeof(float))
            {
                return token.Value<float>();
            }

            if (underlying == typeof(double))
            {
                return token.Value<double>();
            }

            if (underlying == typeof(long))
            {
                return token.Value<long>();
            }

            if (underlying == typeof(string[]))
            {
                return token.ToObject<string[]>();
            }

            if (underlying == typeof(int[]))
            {
                return token.ToObject<int[]>();
            }

            return token.ToObject(underlying);
        }

        internal static UnityEngine.Object ResolveByString(string raw)
        {
            if (string.IsNullOrWhiteSpace(raw))
            {
                return null;
            }

            string sanitized = SanitizeAssetPath(raw);
            if (!string.IsNullOrWhiteSpace(sanitized))
            {
                UnityEngine.Object asset = AssetDatabase.LoadMainAssetAtPath(sanitized);
                if (asset != null)
                {
                    return asset;
                }
            }

            GameObject sceneObject = GameObject.Find(raw);
            if (sceneObject != null)
            {
                return sceneObject;
            }

            string searchMethod = raw.Contains("/") ? "by_path" : "by_name";
            List<int> sceneMatches = GameObjectLookup.SearchGameObjects(searchMethod, raw, includeInactive: true, maxResults: 1);
            if (sceneMatches.Count > 0)
            {
                GameObject byLookup = GameObjectLookup.FindById(sceneMatches[0]);
                if (byLookup != null)
                {
                    return byLookup;
                }
            }

            string[] guids = AssetDatabase.FindAssets(raw);
            if (guids.Length > 0)
            {
                string firstPath = AssetDatabase.GUIDToAssetPath(guids[0]);
                if (!string.IsNullOrWhiteSpace(firstPath))
                {
                    return AssetDatabase.LoadMainAssetAtPath(firstPath);
                }
            }

            return null;
        }

        internal static Dictionary<string, object> CaptureImporterSettings(AssetImporter importer)
        {
            Dictionary<string, object> data = new Dictionary<string, object>
            {
                ["assetPath"] = importer.assetPath,
                ["importerType"] = importer.GetType().Name,
            };

            BindingFlags flags = BindingFlags.Public | BindingFlags.Instance;
            foreach (PropertyInfo property in importer.GetType().GetProperties(flags))
            {
                if (!property.CanRead || property.GetIndexParameters().Length > 0)
                {
                    continue;
                }

                Type propertyType = property.PropertyType;
                if (propertyType.IsPrimitive || propertyType.IsEnum || propertyType == typeof(string))
                {
                    try
                    {
                        object value = property.GetValue(importer);
                        data[property.Name] = value;
                    }
                    catch
                    {
                    }
                }
            }

            return data;
        }

        internal static bool MatchesPathPattern(string candidate, string pattern)
        {
            if (string.IsNullOrWhiteSpace(pattern))
            {
                return true;
            }

            string regex = "^" + System.Text.RegularExpressions.Regex.Escape(pattern)
                .Replace("\\*", ".*")
                .Replace("\\?", ".") + "$";
            return System.Text.RegularExpressions.Regex.IsMatch(candidate ?? string.Empty, regex, System.Text.RegularExpressions.RegexOptions.IgnoreCase);
        }

        internal static BuildTargetGroup ResolveBuildTargetGroup(string platform)
        {
            if (string.IsNullOrWhiteSpace(platform) || platform.Equals("Current", StringComparison.OrdinalIgnoreCase))
            {
                return BuildPipeline.GetBuildTargetGroup(EditorUserBuildSettings.activeBuildTarget);
            }

            if (platform.Equals("Standalone", StringComparison.OrdinalIgnoreCase))
            {
                return BuildTargetGroup.Standalone;
            }

            if (Enum.TryParse(platform, true, out BuildTargetGroup buildTargetGroup))
            {
                return buildTargetGroup;
            }

            if (Enum.TryParse(platform, true, out BuildTarget buildTarget))
            {
                return BuildPipeline.GetBuildTargetGroup(buildTarget);
            }

            return BuildPipeline.GetBuildTargetGroup(EditorUserBuildSettings.activeBuildTarget);
        }

        internal static NamedBuildTarget ResolveNamedBuildTarget(string platform)
        {
            return NamedBuildTarget.FromBuildTargetGroup(ResolveBuildTargetGroup(platform));
        }

        internal static string GetApplicationIdentifier(string platform)
        {
            return PlayerSettings.GetApplicationIdentifier(ResolveNamedBuildTarget(platform));
        }

        internal static string GetApplicationIdentifier(BuildTargetGroup buildTargetGroup)
        {
            return PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.FromBuildTargetGroup(buildTargetGroup));
        }

        internal static void SetApplicationIdentifier(string platform, string identifier)
        {
            PlayerSettings.SetApplicationIdentifier(ResolveNamedBuildTarget(platform), identifier);
        }

        internal static void SetApplicationIdentifier(BuildTargetGroup buildTargetGroup, string identifier)
        {
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.FromBuildTargetGroup(buildTargetGroup), identifier);
        }

        internal static ScriptingImplementation GetScriptingBackend(string platform)
        {
            return PlayerSettings.GetScriptingBackend(ResolveNamedBuildTarget(platform));
        }

        internal static ScriptingImplementation GetScriptingBackend(BuildTargetGroup buildTargetGroup)
        {
            return PlayerSettings.GetScriptingBackend(NamedBuildTarget.FromBuildTargetGroup(buildTargetGroup));
        }

        internal static string GetScriptingDefineSymbols(string platform)
        {
            return PlayerSettings.GetScriptingDefineSymbols(ResolveNamedBuildTarget(platform));
        }

        internal static string GetScriptingDefineSymbols(BuildTargetGroup buildTargetGroup)
        {
            return PlayerSettings.GetScriptingDefineSymbols(NamedBuildTarget.FromBuildTargetGroup(buildTargetGroup));
        }

        internal static void SetScriptingDefineSymbols(BuildTargetGroup buildTargetGroup, string defines)
        {
            PlayerSettings.SetScriptingDefineSymbols(NamedBuildTarget.FromBuildTargetGroup(buildTargetGroup), defines);
        }

        internal static bool GetDefaultIsFullScreen()
        {
            return PlayerSettings.fullScreenMode != FullScreenMode.Windowed;
        }

        internal static bool TryResolveBuildTarget(string platform, out BuildTarget buildTarget)
        {
            if (Enum.TryParse(platform, true, out buildTarget))
            {
                return true;
            }

            if (platform.Equals("Standalone", StringComparison.OrdinalIgnoreCase))
            {
                buildTarget = EditorUserBuildSettings.activeBuildTarget;
                return true;
            }

            buildTarget = EditorUserBuildSettings.activeBuildTarget;
            return false;
        }
    }

    internal static class LiveV2V3AssetUtility
    {
        private static readonly string[] DefaultBuiltinMeshNames =
        {
            "Cube",
            "Sphere",
            "Capsule",
            "Cylinder",
            "Plane",
            "Quad",
        };

        private static readonly string[] DefaultBuiltinShaderNames =
        {
            "Standard",
            "Sprites/Default",
            "UI/Default",
            "Unlit/Color",
            "Universal Render Pipeline/Lit",
            "Universal Render Pipeline/Unlit",
        };

        internal static string ResolveAssetPath(JObject @params, params string[] names)
        {
            foreach (string name in names)
            {
                string raw = LiveV2V3ToolCommon.GetStringParam(@params, name);
                if (string.IsNullOrWhiteSpace(raw))
                {
                    continue;
                }

                string sanitized = LiveV2V3ToolCommon.SanitizeAssetPath(raw);
                if (!string.IsNullOrWhiteSpace(sanitized))
                {
                    return sanitized;
                }

                return raw;
            }

            string guid = LiveV2V3ToolCommon.GetStringParam(@params, "assetGuid", "asset_guid", "targetAssetGuid", "target_asset_guid");
            if (!string.IsNullOrWhiteSpace(guid))
            {
                return AssetDatabase.GUIDToAssetPath(guid);
            }

            return null;
        }

        internal static List<string> EnumerateAssetPaths(string scope, IEnumerable<string> excludePaths = null)
        {
            string[] searchFolders = ResolveSearchFolders(scope);
            HashSet<string> excluded = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            if (excludePaths != null)
            {
                foreach (string excludePath in excludePaths)
                {
                    if (!string.IsNullOrWhiteSpace(excludePath))
                    {
                        excluded.Add(LiveV2V3ToolCommon.SanitizeAssetPath(excludePath) ?? excludePath);
                    }
                }
            }

            List<string> paths = new List<string>();
            foreach (string guid in AssetDatabase.FindAssets(string.Empty, searchFolders))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (string.IsNullOrWhiteSpace(path) || AssetDatabase.IsValidFolder(path) || path.EndsWith(".meta", StringComparison.OrdinalIgnoreCase) || excluded.Contains(path))
                {
                    continue;
                }

                paths.Add(path);
            }

            return paths.Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(path => path, StringComparer.OrdinalIgnoreCase).ToList();
        }

        internal static string[] ResolveSearchFolders(string scope)
        {
            if (string.IsNullOrWhiteSpace(scope) || scope.Equals("project", StringComparison.OrdinalIgnoreCase) || scope.Equals("all", StringComparison.OrdinalIgnoreCase))
            {
                return null;
            }

            string[] folders = scope.Split(new[] { ';', ',' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(folder => LiveV2V3ToolCommon.SanitizeAssetPath(folder.Trim()) ?? folder.Trim())
                .Where(folder => !string.IsNullOrWhiteSpace(folder) && AssetDatabase.IsValidFolder(folder))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToArray();
            return folders.Length == 0 ? null : folders;
        }

        internal static LiveV2V3ToolState.AssetIndexSnapshot BuildSnapshot(string scope, bool includeDependencies, bool includeReferences, bool includeImportSettings, IEnumerable<string> excludePaths = null)
        {
            List<string> assetPaths = EnumerateAssetPaths(scope, excludePaths);
            LiveV2V3ToolState.AssetIndexSnapshot snapshot = new LiveV2V3ToolState.AssetIndexSnapshot
            {
                SnapshotId = $"asset_index_{Guid.NewGuid():N}",
                Scope = string.IsNullOrWhiteSpace(scope) ? "project" : scope,
                BuiltAtUtc = DateTime.UtcNow,
                IncludeDependencies = includeDependencies,
                IncludeReferences = includeReferences,
                IncludeImportSettings = includeImportSettings,
            };

            foreach (string assetPath in assetPaths)
            {
                LiveV2V3ToolState.AssetIndexEntry entry = BuildEntry(assetPath, includeDependencies);
                if (includeImportSettings)
                {
                    AssetImporter importer = AssetImporter.GetAtPath(assetPath);
                    entry.ImporterType = importer != null ? importer.GetType().Name : null;
                }

                snapshot.Entries[assetPath] = entry;
            }

            if (includeReferences)
            {
                PopulateReferencedBy(snapshot);
            }

            return snapshot;
        }

        internal static LiveV2V3ToolState.AssetIndexEntry BuildEntry(string assetPath, bool includeDependencies)
        {
            string fullPath = Path.GetFullPath(assetPath);
            LiveV2V3ToolState.AssetIndexEntry entry = new LiveV2V3ToolState.AssetIndexEntry
            {
                Guid = AssetDatabase.AssetPathToGUID(assetPath),
                Path = assetPath,
                Type = AssetDatabase.GetMainAssetTypeAtPath(assetPath)?.Name ?? "Unknown",
                SizeBytes = File.Exists(fullPath) ? new FileInfo(fullPath).Length : 0L,
                ModifiedAtUtc = File.Exists(fullPath) ? File.GetLastWriteTimeUtc(fullPath) : DateTime.MinValue,
                Labels = AssetDatabase.GetLabels(AssetDatabase.LoadMainAssetAtPath(assetPath)).ToList(),
            };

            if (includeDependencies)
            {
                entry.Dependencies = AssetDatabase.GetDependencies(assetPath, false)
                    .Where(path => !string.Equals(path, assetPath, StringComparison.OrdinalIgnoreCase))
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                    .ToList();
            }

            return entry;
        }

        internal static void PopulateReferencedBy(LiveV2V3ToolState.AssetIndexSnapshot snapshot)
        {
            foreach (LiveV2V3ToolState.AssetIndexEntry entry in snapshot.Entries.Values)
            {
                entry.ReferencedBy.Clear();
            }

            foreach (KeyValuePair<string, LiveV2V3ToolState.AssetIndexEntry> pair in snapshot.Entries)
            {
                string assetPath = pair.Key;
                IEnumerable<string> dependencies = pair.Value.Dependencies.Count > 0
                    ? pair.Value.Dependencies
                    : AssetDatabase.GetDependencies(assetPath, false).Where(path => !string.Equals(path, assetPath, StringComparison.OrdinalIgnoreCase));

                foreach (string dependency in dependencies)
                {
                    if (snapshot.Entries.TryGetValue(dependency, out LiveV2V3ToolState.AssetIndexEntry referencedEntry))
                    {
                        referencedEntry.ReferencedBy.Add(assetPath);
                    }
                }
            }

            foreach (LiveV2V3ToolState.AssetIndexEntry entry in snapshot.Entries.Values)
            {
                entry.ReferencedBy = entry.ReferencedBy
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                    .ToList();
            }
        }

        internal static Dictionary<string, int> BuildTypeBreakdown(IEnumerable<LiveV2V3ToolState.AssetIndexEntry> entries)
        {
            return entries
                .GroupBy(entry => entry.Type ?? "Unknown", StringComparer.OrdinalIgnoreCase)
                .OrderBy(group => group.Key, StringComparer.OrdinalIgnoreCase)
                .ToDictionary(group => group.Key, group => group.Count(), StringComparer.OrdinalIgnoreCase);
        }

        internal static bool MatchesAssetType(string actualType, string requestedType)
        {
            if (string.IsNullOrWhiteSpace(requestedType))
            {
                return true;
            }

            string normalizedRequested = requestedType.Trim().ToLowerInvariant();
            string normalizedActual = (actualType ?? string.Empty).Trim().ToLowerInvariant();

            if (normalizedActual.Contains(normalizedRequested))
            {
                return true;
            }

            return normalizedRequested switch
            {
                "mesh" => normalizedActual == "mesh" || normalizedActual == "gameobject",
                "material" => normalizedActual == "material",
                "texture" => normalizedActual.Contains("texture") || normalizedActual == "sprite",
                "shader" => normalizedActual == "shader",
                "prefab" => normalizedActual == "gameobject",
                "scene" => normalizedActual == "sceneasset",
                _ => false,
            };
        }

        internal static string ComputeDependencyHash(string assetPath)
        {
            return AssetDatabase.GetAssetDependencyHash(assetPath).ToString();
        }

        internal static List<string> FindDependents(string assetPath, string scope, bool includeIndirect, int maxResults)
        {
            List<string> matches = new List<string>();
            LiveV2V3ToolState.AssetIndexSnapshot snapshot = LiveV2V3ToolState.CurrentAssetIndex;
            if (snapshot != null && snapshot.Entries.TryGetValue(assetPath, out LiveV2V3ToolState.AssetIndexEntry indexedEntry) && snapshot.IncludeReferences)
            {
                IEnumerable<string> indexedMatches = indexedEntry.ReferencedBy;
                if (!string.IsNullOrWhiteSpace(scope) && !scope.Equals("project", StringComparison.OrdinalIgnoreCase) && !scope.Equals("all", StringComparison.OrdinalIgnoreCase))
                {
                    indexedMatches = indexedMatches.Where(path => path.StartsWith(scope, StringComparison.OrdinalIgnoreCase));
                }

                return indexedMatches
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .Take(maxResults > 0 ? maxResults : int.MaxValue)
                    .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                    .ToList();
            }

            string assetFolder = Path.GetDirectoryName(assetPath)?.Replace('\\', '/');
            if (!string.IsNullOrWhiteSpace(assetFolder) && AssetDatabase.IsValidFolder(assetFolder))
            {
                LiveV2V3ToolState.AssetIndexSnapshot folderSnapshot = BuildSnapshot(assetFolder, includeDependencies: true, includeReferences: true, includeImportSettings: false);
                if (folderSnapshot.Entries.TryGetValue(assetPath, out indexedEntry))
                {
                    return indexedEntry.ReferencedBy
                        .Distinct(StringComparer.OrdinalIgnoreCase)
                        .Take(maxResults > 0 ? maxResults : int.MaxValue)
                        .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                        .ToList();
                }
            }

            foreach (string candidate in EnumerateReferenceCandidatePaths(scope))
            {
                if (string.Equals(candidate, assetPath, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                string[] dependencies = AssetDatabase.GetDependencies(candidate, includeIndirect);
                if (!dependencies.Contains(assetPath, StringComparer.OrdinalIgnoreCase))
                {
                    continue;
                }

                matches.Add(candidate);
                if (maxResults > 0 && matches.Count >= maxResults)
                {
                    break;
                }
            }

            return matches;
        }

        internal static IEnumerable<string> EnumerateReferenceCandidatePaths(string scope)
        {
            HashSet<string> likelyExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                ".prefab",
                ".unity",
                ".asset",
                ".mat",
                ".controller",
                ".overridecontroller",
                ".anim",
                ".playable",
                ".shadergraph",
                ".vfx",
            };

            return EnumerateAssetPaths(scope)
                .Where(path => likelyExtensions.Contains(Path.GetExtension(path)));
        }

        internal static List<string> GetDependencies(string assetPath, bool includeIndirect, int maxDepth)
        {
            if (!includeIndirect || maxDepth <= 1)
            {
                return AssetDatabase.GetDependencies(assetPath, false)
                    .Where(path => !string.Equals(path, assetPath, StringComparison.OrdinalIgnoreCase))
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                    .ToList();
            }

            HashSet<string> visited = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            Queue<(string Path, int Depth)> queue = new Queue<(string Path, int Depth)>();
            queue.Enqueue((assetPath, 0));

            while (queue.Count > 0)
            {
                (string currentPath, int depth) = queue.Dequeue();
                if (depth >= maxDepth)
                {
                    continue;
                }

                foreach (string dependency in AssetDatabase.GetDependencies(currentPath, false))
                {
                    if (string.Equals(dependency, currentPath, StringComparison.OrdinalIgnoreCase) || string.Equals(dependency, assetPath, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    if (visited.Add(dependency))
                    {
                        queue.Enqueue((dependency, depth + 1));
                    }
                }
            }

            return visited.OrderBy(path => path, StringComparer.OrdinalIgnoreCase).ToList();
        }

        internal static Dictionary<string, object> BuildAssetDescriptor(string assetPath, bool includeImportSettings)
        {
            UnityEngine.Object asset = AssetDatabase.LoadMainAssetAtPath(assetPath);
            AssetImporter importer = AssetImporter.GetAtPath(assetPath);
            string fullPath = Path.GetFullPath(assetPath);
            string guid = AssetDatabase.AssetPathToGUID(assetPath);
            string typeName = asset != null ? asset.GetType().Name : AssetDatabase.GetMainAssetTypeAtPath(assetPath)?.Name ?? "Unknown";
            string assetName = asset != null ? asset.name : Path.GetFileNameWithoutExtension(assetPath);
            string hash = ComputeDependencyHash(assetPath);

            return new Dictionary<string, object>
            {
                ["path"] = assetPath,
                ["guid"] = guid,
                ["name"] = assetName,
                ["type"] = typeName,
                ["fileHash"] = hash,
                ["importSettings"] = includeImportSettings && importer != null ? LiveV2V3ToolCommon.CaptureImporterSettings(importer) : new Dictionary<string, object>(),
                ["properties"] = new Dictionary<string, object>
                {
                    ["name"] = assetName,
                    ["type"] = typeName,
                    ["labels"] = AssetDatabase.GetLabels(asset).ToList(),
                },
                ["asset_path"] = assetPath,
                ["asset_guid"] = guid,
                ["hash"] = hash,
                ["file_size_bytes"] = File.Exists(fullPath) ? new FileInfo(fullPath).Length : 0L,
                ["last_modified_utc"] = File.Exists(fullPath) ? File.GetLastWriteTimeUtc(fullPath).ToString("o") : null,
                ["import_settings"] = includeImportSettings && importer != null ? LiveV2V3ToolCommon.CaptureImporterSettings(importer) : null,
            };
        }

        internal static List<Dictionary<string, object>> GetBuiltinAssets(string assetType, int maxResults)
        {
            List<Dictionary<string, object>> results = new List<Dictionary<string, object>>();
            if (string.Equals(assetType, "mesh", StringComparison.OrdinalIgnoreCase))
            {
                foreach (string name in DefaultBuiltinMeshNames)
                {
                    results.Add(new Dictionary<string, object>
                    {
                        ["name"] = name,
                        ["asset_type"] = "mesh",
                        ["source"] = "builtin",
                    });
                }
            }
            else if (string.Equals(assetType, "shader", StringComparison.OrdinalIgnoreCase) || string.IsNullOrWhiteSpace(assetType))
            {
                foreach (string shaderName in EnumerateShaderNames())
                {
                    results.Add(new Dictionary<string, object>
                    {
                        ["name"] = shaderName,
                        ["asset_type"] = "shader",
                        ["source"] = "builtin_or_loaded",
                    });
                }
            }

            if (maxResults > 0)
            {
                results = results.Take(maxResults).ToList();
            }

            return results;
        }

        internal static List<string> EnumerateShaderNames()
        {
            HashSet<string> names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (Shader shader in UnityEngine.Resources.FindObjectsOfTypeAll<Shader>())
            {
                if (shader != null && !string.IsNullOrWhiteSpace(shader.name))
                {
                    names.Add(shader.name);
                }
            }

            foreach (string shaderName in DefaultBuiltinShaderNames)
            {
                Shader shader = Shader.Find(shaderName);
                if (shader != null)
                {
                    names.Add(shader.name);
                }
            }

            return names.OrderBy(name => name, StringComparer.OrdinalIgnoreCase).ToList();
        }

        internal static Transform FindTransformByPath(Transform root, string relativePath)
        {
            if (root == null)
            {
                return null;
            }

            if (string.IsNullOrWhiteSpace(relativePath) || relativePath == "/" || string.Equals(relativePath, root.name, StringComparison.OrdinalIgnoreCase))
            {
                return root;
            }

            string[] parts = relativePath.Split(new[] { '/' }, StringSplitOptions.RemoveEmptyEntries);
            int index = parts.Length > 0 && string.Equals(parts[0], root.name, StringComparison.OrdinalIgnoreCase) ? 1 : 0;
            Transform current = root;
            for (; index < parts.Length; index++)
            {
                current = current.Find(parts[index]);
                if (current == null)
                {
                    return null;
                }
            }

            return current;
        }
    }

    [McpForUnityTool("build_asset_index", AutoRegister = false)]
    public static class BuildAssetIndex
    {
        public static object HandleCommand(JObject @params)
        {
            string action = (LiveV2V3ToolCommon.GetStringParam(@params, "action") ?? "build").ToLowerInvariant();
            string scope = LiveV2V3ToolCommon.GetStringParam(@params, "scope") ?? "project";
            bool includeDependencies = LiveV2V3ToolCommon.GetBoolParam(@params, "includeDependencies", "include_dependencies") ?? true;
            bool includeReferences = LiveV2V3ToolCommon.GetBoolParam(@params, "includeReferences", "include_references") ?? true;
            bool includeImportSettings = LiveV2V3ToolCommon.GetBoolParam(@params, "includeImportSettings", "include_import_settings") ?? false;
            bool forceRebuild = LiveV2V3ToolCommon.GetBoolParam(@params, "forceRebuild", "force_rebuild") ?? false;
            List<string> excludedPaths = (LiveV2V3ToolCommon.GetParam(@params, "excludePaths", "exclude_paths") as JArray)?.Values<string>().ToList() ?? new List<string>();

            if (action == "clear")
            {
                LiveV2V3ToolState.CurrentAssetIndex = null;
                return new SuccessResponse("Cleared asset index.", new { index_cleared = true });
            }

            Stopwatch stopwatch = Stopwatch.StartNew();
            LiveV2V3ToolState.AssetIndexSnapshot snapshot = forceRebuild || LiveV2V3ToolState.CurrentAssetIndex == null || action == "build" || action == "update"
                ? LiveV2V3AssetUtility.BuildSnapshot(scope, includeDependencies, includeReferences, includeImportSettings, excludedPaths)
                : LiveV2V3ToolState.CurrentAssetIndex;
            stopwatch.Stop();

            if (action == "build" || action == "update" || action == "rebuild")
            {
                LiveV2V3ToolState.CurrentAssetIndex = snapshot;
                return new SuccessResponse(
                    action == "update" ? "Updated asset index." : "Built asset index.",
                    new
                    {
                        snapshot_id = snapshot.SnapshotId,
                        scope = snapshot.Scope,
                        assets_indexed = snapshot.Entries.Count,
                        dependencies_tracked = snapshot.Entries.Values.Sum(entry => entry.Dependencies.Count),
                        references_tracked = snapshot.Entries.Values.Sum(entry => entry.ReferencedBy.Count),
                        duration_seconds = Math.Round(stopwatch.Elapsed.TotalSeconds, 3),
                        built_at = snapshot.BuiltAtUtc.ToString("o"),
                        index_path = "memory://live-v2v3-asset-index",
                        type_breakdown = LiveV2V3AssetUtility.BuildTypeBreakdown(snapshot.Entries.Values),
                    }
                );
            }

            if (action == "validate")
            {
                LiveV2V3ToolState.AssetIndexSnapshot current = LiveV2V3ToolState.CurrentAssetIndex;
                if (current == null)
                {
                    current = snapshot;
                    LiveV2V3ToolState.CurrentAssetIndex = current;
                }

                LiveV2V3ToolState.AssetIndexSnapshot fresh = LiveV2V3AssetUtility.BuildSnapshot(current.Scope, current.IncludeDependencies, current.IncludeReferences, current.IncludeImportSettings, excludedPaths);
                HashSet<string> previousPaths = new HashSet<string>(current.Entries.Keys, StringComparer.OrdinalIgnoreCase);
                HashSet<string> freshPaths = new HashSet<string>(fresh.Entries.Keys, StringComparer.OrdinalIgnoreCase);
                List<string> missingAssets = previousPaths.Except(freshPaths, StringComparer.OrdinalIgnoreCase).OrderBy(path => path, StringComparer.OrdinalIgnoreCase).ToList();
                List<string> newAssets = freshPaths.Except(previousPaths, StringComparer.OrdinalIgnoreCase).OrderBy(path => path, StringComparer.OrdinalIgnoreCase).ToList();
                List<string> updatedAssets = fresh.Entries.Values
                    .Where(entry => current.Entries.TryGetValue(entry.Path, out LiveV2V3ToolState.AssetIndexEntry existing) && (existing.ModifiedAtUtc != entry.ModifiedAtUtc || existing.SizeBytes != entry.SizeBytes || !string.Equals(existing.Guid, entry.Guid, StringComparison.OrdinalIgnoreCase)))
                    .Select(entry => entry.Path)
                    .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                    .ToList();

                return new SuccessResponse(
                    missingAssets.Count == 0 && newAssets.Count == 0 && updatedAssets.Count == 0 ? "Asset index is current." : "Asset index validation detected drift.",
                    new
                    {
                        index_exists = LiveV2V3ToolState.CurrentAssetIndex != null,
                        is_fresh = missingAssets.Count == 0 && newAssets.Count == 0 && updatedAssets.Count == 0,
                        total_indexed = current.Entries.Count,
                        assets_needing_update = updatedAssets.Count,
                        missing_assets = missingAssets,
                        new_assets = newAssets,
                        updated_assets = updatedAssets,
                        last_build_time = current.BuiltAtUtc.ToString("o"),
                        coverage_percentage = fresh.Entries.Count == 0 ? 100.0 : Math.Round((double)(fresh.Entries.Count - missingAssets.Count) / fresh.Entries.Count * 100.0, 2),
                    }
                );
            }

            return new ErrorResponse("Unsupported action for build_asset_index.");
        }
    }

    [McpForUnityTool("asset_index_status", AutoRegister = false)]
    public static class AssetIndexStatus
    {
        public static object HandleCommand(JObject @params)
        {
            bool detailed = LiveV2V3ToolCommon.GetBoolParam(@params, "detailed") ?? false;
            LiveV2V3ToolState.AssetIndexSnapshot snapshot = LiveV2V3ToolState.CurrentAssetIndex;
            if (snapshot == null)
            {
                snapshot = LiveV2V3AssetUtility.BuildSnapshot("project", includeDependencies: true, includeReferences: true, includeImportSettings: false);
                LiveV2V3ToolState.CurrentAssetIndex = snapshot;
            }

            object entryPreview = detailed
                ? snapshot.Entries.Values.Take(25).Select(entry => new
                {
                    path = entry.Path,
                    guid = entry.Guid,
                    type = entry.Type,
                    dependency_count = entry.Dependencies.Count,
                    referenced_by_count = entry.ReferencedBy.Count,
                    size_bytes = entry.SizeBytes,
                    modified_at = entry.ModifiedAtUtc.ToString("o"),
                }).ToList()
                : null;

            return new SuccessResponse(
                "Retrieved asset index status.",
                new
                {
                    index_exists = snapshot != null,
                    snapshot_id = snapshot.SnapshotId,
                    built_at = snapshot.BuiltAtUtc.ToString("o"),
                    scope = snapshot.Scope,
                    total_assets = snapshot.Entries.Count,
                    type_breakdown = LiveV2V3AssetUtility.BuildTypeBreakdown(snapshot.Entries.Values),
                    dependency_edges = snapshot.Entries.Values.Sum(entry => entry.Dependencies.Count),
                    reference_edges = snapshot.Entries.Values.Sum(entry => entry.ReferencedBy.Count),
                    entries = entryPreview,
                }
            );
        }
    }

    [McpForUnityTool("find_asset_references", AutoRegister = false)]
    public static class FindAssetReferences
    {
        public static object HandleCommand(JObject @params)
        {
            string action = (LiveV2V3ToolCommon.GetStringParam(@params, "action") ?? "find_dependents").ToLowerInvariant();
            string assetPath = LiveV2V3AssetUtility.ResolveAssetPath(@params, "assetPath", "asset_path", "targetAssetPath", "target_asset_path");
            if (string.IsNullOrWhiteSpace(assetPath) || !File.Exists(Path.GetFullPath(assetPath)))
            {
                return new ErrorResponse("Valid asset_path is required.");
            }

            string scope = LiveV2V3ToolCommon.GetStringParam(@params, "searchScope", "search_scope") ?? "project";
            bool includeIndirect = LiveV2V3ToolCommon.GetBoolParam(@params, "includeIndirect", "include_indirect") ?? false;
            int maxDepth = LiveV2V3ToolCommon.GetIntParam(@params, "maxDepth", "max_depth") ?? 3;
            int maxResults = LiveV2V3ToolCommon.GetIntParam(@params, "maxResults", "max_results") ?? 100;

            if (action == "find_dependents" || action == "dependents")
            {
                List<string> dependents = LiveV2V3AssetUtility.FindDependents(assetPath, scope, includeIndirect, maxResults);
                return new SuccessResponse(
                    "Found asset dependents.",
                    new
                    {
                        asset_path = assetPath,
                        asset_guid = AssetDatabase.AssetPathToGUID(assetPath),
                        action,
                        total_results = dependents.Count,
                        references = dependents.Select(path => new { path, type = AssetDatabase.GetMainAssetTypeAtPath(path)?.Name ?? "Unknown" }).ToList(),
                    }
                );
            }

            if (action == "find_dependencies" || action == "dependencies")
            {
                List<string> dependencies = LiveV2V3AssetUtility.GetDependencies(assetPath, includeIndirect, maxDepth);
                return new SuccessResponse(
                    "Found asset dependencies.",
                    new
                    {
                        asset_path = assetPath,
                        asset_guid = AssetDatabase.AssetPathToGUID(assetPath),
                        total_results = dependencies.Count,
                        references = dependencies.Select(path => new { path, type = AssetDatabase.GetMainAssetTypeAtPath(path)?.Name ?? "Unknown" }).ToList(),
                    }
                );
            }

            return new ErrorResponse("Unsupported action for find_asset_references.");
        }
    }

    [McpForUnityTool("analyze_asset_dependencies", AutoRegister = false)]
    public static class AnalyzeAssetDependencies
    {
        public static object HandleCommand(JObject @params)
        {
            string action = (LiveV2V3ToolCommon.GetStringParam(@params, "action") ?? "get_dependencies").ToLowerInvariant();
            string assetPath = LiveV2V3AssetUtility.ResolveAssetPath(@params, "assetPath", "asset_path", "targetAssetPath", "target_asset_path");
            if (string.IsNullOrWhiteSpace(assetPath) || !File.Exists(Path.GetFullPath(assetPath)))
            {
                return new ErrorResponse("Valid asset_path is required.");
            }

            bool includeIndirect = LiveV2V3ToolCommon.GetBoolParam(@params, "includeIndirect", "include_indirect") ?? false;
            int maxDepth = LiveV2V3ToolCommon.GetIntParam(@params, "maxDepth", "max_depth") ?? 3;
            string scope = LiveV2V3ToolCommon.GetStringParam(@params, "searchScope", "search_scope") ?? "project";
            List<string> dependencies = LiveV2V3AssetUtility.GetDependencies(assetPath, includeIndirect, maxDepth);

            if (action == "get_dependencies")
            {
                return new SuccessResponse(
                    "Analyzed asset dependencies.",
                    new
                    {
                        asset_path = assetPath,
                        direct_dependencies = AssetDatabase.GetDependencies(assetPath, false).Where(path => !string.Equals(path, assetPath, StringComparison.OrdinalIgnoreCase)).ToList(),
                        all_dependencies = dependencies,
                        dependency_count = dependencies.Count,
                        dependency_hash = LiveV2V3AssetUtility.ComputeDependencyHash(assetPath),
                    }
                );
            }

            if (action == "analyze_impact")
            {
                List<string> dependents = LiveV2V3AssetUtility.FindDependents(assetPath, scope, includeIndirect, maxResults: 250);
                return new SuccessResponse(
                    "Analyzed asset impact.",
                    new
                    {
                        asset_path = assetPath,
                        dependent_assets = dependents,
                        dependent_count = dependents.Count,
                        dependency_count = dependencies.Count,
                        impact_level = dependents.Count > 20 ? "high" : dependents.Count > 5 ? "medium" : "low",
                    }
                );
            }

            return new ErrorResponse("Unsupported action for analyze_asset_dependencies.");
        }
    }

    [McpForUnityTool("find_builtin_assets", AutoRegister = false)]
    public static class FindBuiltinAssets
    {
        public static object HandleCommand(JObject @params)
        {
            string action = (LiveV2V3ToolCommon.GetStringParam(@params, "action") ?? "list_by_type").ToLowerInvariant();
            string assetType = LiveV2V3ToolCommon.GetStringParam(@params, "assetType", "asset_type") ?? "mesh";
            int maxResults = LiveV2V3ToolCommon.GetIntParam(@params, "maxResults", "max_results") ?? 25;
            string searchPattern = LiveV2V3ToolCommon.GetStringParam(@params, "searchPattern", "search_pattern");
            List<Dictionary<string, object>> results = LiveV2V3AssetUtility.GetBuiltinAssets(assetType, maxResults)
                .Where(item => string.IsNullOrWhiteSpace(searchPattern) || item["name"].ToString().IndexOf(searchPattern, StringComparison.OrdinalIgnoreCase) >= 0)
                .Take(maxResults)
                .ToList();

            if (action == "list_by_type" || action == "search")
            {
                return new SuccessResponse(
                    "Retrieved builtin assets.",
                    new
                    {
                        asset_type = assetType,
                        total_results = results.Count,
                        assets = results,
                    }
                );
            }

            return new ErrorResponse("Unsupported action for find_builtin_assets.");
        }
    }

    [McpForUnityTool("get_component_types", AutoRegister = false)]
    public static class GetComponentTypes
    {
        public static object HandleCommand(JObject @params)
        {
            string action = (LiveV2V3ToolCommon.GetStringParam(@params, "action") ?? "search").ToLowerInvariant();
            string componentName = LiveV2V3ToolCommon.GetStringParam(@params, "componentName", "component_name") ?? string.Empty;
            bool includeBuiltin = LiveV2V3ToolCommon.GetBoolParam(@params, "includeBuiltin", "include_builtin") ?? true;
            bool includeCustom = LiveV2V3ToolCommon.GetBoolParam(@params, "includeCustom", "include_custom") ?? true;
            bool includeProperties = LiveV2V3ToolCommon.GetBoolParam(@params, "includeProperties", "include_properties") ?? false;
            bool includeMethods = LiveV2V3ToolCommon.GetBoolParam(@params, "includeMethods", "include_methods") ?? false;
            int maxResults = LiveV2V3ToolCommon.GetIntParam(@params, "maxResults", "max_results") ?? 50;

            IEnumerable<Type> matches = TypeCache.GetTypesDerivedFrom<Component>()
                .Where(type => !type.IsAbstract)
                .Where(type => string.IsNullOrWhiteSpace(componentName) || type.Name.IndexOf(componentName, StringComparison.OrdinalIgnoreCase) >= 0)
                .Where(type =>
                {
                    bool isBuiltin = type.Namespace != null && type.Namespace.StartsWith("Unity", StringComparison.Ordinal);
                    return (isBuiltin && includeBuiltin) || (!isBuiltin && includeCustom);
                })
                .OrderBy(type => type.Name, StringComparer.OrdinalIgnoreCase)
                .Take(maxResults);

            if (action == "search" || action == "list")
            {
                return new SuccessResponse(
                    "Retrieved component types.",
                    new
                    {
                        total_results = matches.Count(),
                        component_types = matches.Select(type => new
                        {
                            name = type.Name,
                            full_name = type.FullName,
                            assembly = type.Assembly.GetName().Name,
                            is_builtin = type.Namespace != null && type.Namespace.StartsWith("Unity", StringComparison.Ordinal),
                            properties = includeProperties ? type.GetProperties(BindingFlags.Public | BindingFlags.Instance).Select(property => property.Name).Take(25).ToList() : null,
                            methods = includeMethods ? type.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly).Where(method => !method.IsSpecialName).Select(method => method.Name).Distinct().Take(25).ToList() : null,
                        }).ToList(),
                    }
                );
            }

            return new ErrorResponse("Unsupported action for get_component_types.");
        }
    }

    [McpForUnityTool("get_object_references", AutoRegister = false)]
    public static class GetObjectReferences
    {
        public static object HandleCommand(JObject @params)
        {
            string action = (LiveV2V3ToolCommon.GetStringParam(@params, "action") ?? "get_referenced_by").ToLowerInvariant();
            string target = LiveV2V3ToolCommon.GetStringParam(@params, "target");
            if (string.IsNullOrWhiteSpace(target))
            {
                return new ErrorResponse("'target' is required.");
            }

            string assetPath = LiveV2V3ToolCommon.SanitizeAssetPath(target) ?? target;
            bool includeIndirect = LiveV2V3ToolCommon.GetBoolParam(@params, "includeIndirect", "include_indirect") ?? true;
            string scope = LiveV2V3ToolCommon.GetStringParam(@params, "searchScope", "search_scope") ?? "project";
            int maxResults = LiveV2V3ToolCommon.GetIntParam(@params, "maxResults", "max_results") ?? 50;

            if (action == "get_referenced_by")
            {
                List<string> references = LiveV2V3AssetUtility.FindDependents(assetPath, scope, includeIndirect, maxResults);
                return new SuccessResponse(
                    "Retrieved object references.",
                    new
                    {
                        target = assetPath,
                        reference_type = "referenced_by",
                        total_results = references.Count,
                        references = references.Select(path => new { path, type = AssetDatabase.GetMainAssetTypeAtPath(path)?.Name ?? "Unknown" }).ToList(),
                    }
                );
            }

            if (action == "get_references")
            {
                List<string> references = LiveV2V3AssetUtility.GetDependencies(assetPath, includeIndirect, maxDepth: 3).Take(maxResults).ToList();
                return new SuccessResponse(
                    "Retrieved object dependency references.",
                    new
                    {
                        target = assetPath,
                        reference_type = "references",
                        total_results = references.Count,
                        references = references.Select(path => new { path, type = AssetDatabase.GetMainAssetTypeAtPath(path)?.Name ?? "Unknown" }).ToList(),
                    }
                );
            }

            return new ErrorResponse("Unsupported action for get_object_references.");
        }
    }

    [McpForUnityTool("summarize_asset", AutoRegister = false)]
    public static class SummarizeAsset
    {
        public static object HandleCommand(JObject @params)
        {
            string assetPath = LiveV2V3AssetUtility.ResolveAssetPath(@params, "assetPath", "asset_path");
            if (string.IsNullOrWhiteSpace(assetPath) || !File.Exists(Path.GetFullPath(assetPath)))
            {
                return new ErrorResponse("Valid asset_path is required.");
            }

            string detailLevel = (LiveV2V3ToolCommon.GetStringParam(@params, "detailLevel", "detail_level") ?? "brief").ToLowerInvariant();
            int maxRelatedAssets = LiveV2V3ToolCommon.GetIntParam(@params, "maxRelatedAssets", "max_related_assets") ?? 5;
            List<string> dependencies = LiveV2V3AssetUtility.GetDependencies(assetPath, includeIndirect: false, maxDepth: 1);
            List<string> dependents = LiveV2V3AssetUtility.FindDependents(assetPath, "project", includeIndirect: true, maxResults: maxRelatedAssets);
            Dictionary<string, object> descriptor = LiveV2V3AssetUtility.BuildAssetDescriptor(assetPath, includeImportSettings: detailLevel != "brief");
            descriptor["dependencies"] = dependencies.Take(maxRelatedAssets).ToList();
            descriptor["dependents"] = dependents.Take(maxRelatedAssets).ToList();
            descriptor["dependency_count"] = dependencies.Count;
            descriptor["dependent_count"] = dependents.Count;

            return new SuccessResponse(
                "Summarized asset.",
                new
                {
                    asset = descriptor,
                    summary = new
                    {
                        detail_level = detailLevel,
                        dependency_count = dependencies.Count,
                        dependent_count = dependents.Count,
                        max_related_assets = maxRelatedAssets,
                    }
                }
            );
        }
    }

    [McpForUnityTool("list_shaders", AutoRegister = false)]
    public static class ListShaders
    {
        public static object HandleCommand(JObject @params)
        {
            string action = (LiveV2V3ToolCommon.GetStringParam(@params, "action") ?? "list_builtin").ToLowerInvariant();
            string searchPattern = LiveV2V3ToolCommon.GetStringParam(@params, "searchPattern", "search_pattern");
            bool includeProperties = LiveV2V3ToolCommon.GetBoolParam(@params, "includeProperties", "include_properties") ?? false;
            string folderPath = LiveV2V3ToolCommon.GetStringParam(@params, "folderPath", "folder_path");

            if (action == "list_builtin")
            {
                List<string> names = LiveV2V3AssetUtility.EnumerateShaderNames()
                    .Where(name => string.IsNullOrWhiteSpace(searchPattern) || name.IndexOf(searchPattern, StringComparison.OrdinalIgnoreCase) >= 0)
                    .ToList();

                return new SuccessResponse(
                    "Retrieved shader list.",
                    new
                    {
                        total_results = names.Count,
                        shaders = names.Select(name =>
                        {
                            Shader shader = Shader.Find(name);
                            return new
                            {
                                name,
                                is_supported = shader != null && shader.isSupported,
                                properties = includeProperties && shader != null ? Enumerable.Range(0, shader.GetPropertyCount()).Select(index => shader.GetPropertyName(index)).ToList() : null,
                            };
                        }).ToList(),
                    }
                );
            }

            if (action == "list_project")
            {
                IEnumerable<string> shaderPaths = LiveV2V3AssetUtility.EnumerateAssetPaths(folderPath)
                    .Where(path => path.EndsWith(".shader", StringComparison.OrdinalIgnoreCase) || path.EndsWith(".shadergraph", StringComparison.OrdinalIgnoreCase));

                return new SuccessResponse(
                    "Retrieved project shaders.",
                    new
                    {
                        total_results = shaderPaths.Count(),
                        shaders = shaderPaths.Select(path => new { path, name = Path.GetFileNameWithoutExtension(path) }).ToList(),
                    }
                );
            }

            return new ErrorResponse("Unsupported action for list_shaders.");
        }
    }

    [McpForUnityTool("diff_asset", AutoRegister = false)]
    public static class DiffAsset
    {
        public static object HandleCommand(JObject @params)
        {
            string action = (LiveV2V3ToolCommon.GetStringParam(@params, "action") ?? "get_asset_data").ToLowerInvariant();
            string compareMode = (LiveV2V3ToolCommon.GetStringParam(@params, "compareMode", "compare_mode") ?? "current_vs_saved").ToLowerInvariant();
            string assetPath = LiveV2V3AssetUtility.ResolveAssetPath(@params, "assetPath", "asset_path", "sourceAssetPath", "source_asset_path", "sourcePath", "source_path");
            string targetPath = LiveV2V3AssetUtility.ResolveAssetPath(@params, "targetAssetPath", "target_asset_path", "targetPath", "target_path") ?? assetPath;
            bool includeImportSettings = LiveV2V3ToolCommon.GetBoolParam(@params, "includeImportSettings", "include_import_settings") ?? compareMode == "check_import_settings";

            if (string.IsNullOrWhiteSpace(assetPath) || !File.Exists(Path.GetFullPath(assetPath)))
            {
                return new ErrorResponse("Valid asset_path is required.");
            }

            if (action != "get_asset_data")
            {
                return new ErrorResponse("Unsupported action for diff_asset.");
            }

            Dictionary<string, object> source = LiveV2V3AssetUtility.BuildAssetDescriptor(assetPath, includeImportSettings);
            Dictionary<string, object> target = LiveV2V3AssetUtility.BuildAssetDescriptor(targetPath, includeImportSettings);
            List<object> changes = new List<object>();

            if (!string.Equals(source["fileHash"]?.ToString(), target["fileHash"]?.ToString(), StringComparison.OrdinalIgnoreCase))
            {
                changes.Add(new { path = "asset.fileHash", change_type = "modified", property = "fileHash", old_value = source["fileHash"], new_value = target["fileHash"], value_type = "hash" });
            }

            if (!Equals(source["file_size_bytes"], target["file_size_bytes"]))
            {
                changes.Add(new { path = "asset.file_size_bytes", change_type = "modified", property = "file_size_bytes", old_value = source["file_size_bytes"], new_value = target["file_size_bytes"], value_type = "long" });
            }

            return new SuccessResponse(
                changes.Count == 0 ? "Asset states match." : "Computed asset diff.",
                new
                {
                    compare_mode = compareMode,
                    source,
                    target,
                    summary = new { total = changes.Count, import_settings = 0, properties = changes.Count, binary = 0, comparison_limited = compareMode == "current_vs_saved" },
                    changes,
                }
            );
        }
    }

    [McpForUnityTool("diff_prefab", AutoRegister = false)]
    public static class DiffPrefab
    {
        public static object HandleCommand(JObject @params)
        {
            string action = (LiveV2V3ToolCommon.GetStringParam(@params, "action") ?? "get_prefab_data").ToLowerInvariant();
            string compareMode = (LiveV2V3ToolCommon.GetStringParam(@params, "compareMode", "compare_mode") ?? "current_vs_saved").ToLowerInvariant();
            string prefabPath = LiveV2V3AssetUtility.ResolveAssetPath(@params, "prefabPath", "prefab_path", "sourcePrefabPath", "source_prefab_path", "sourcePrefab", "source_prefab");
            string targetPrefabPath = LiveV2V3AssetUtility.ResolveAssetPath(@params, "targetPrefabPath", "target_prefab_path", "targetPrefab", "target_prefab") ?? prefabPath;
            if (string.IsNullOrWhiteSpace(prefabPath) || !File.Exists(Path.GetFullPath(prefabPath)))
            {
                return new ErrorResponse("Valid prefab_path is required.");
            }

            if (action != "get_prefab_data")
            {
                return new ErrorResponse("Unsupported action for diff_prefab.");
            }

            GameObject sourcePrefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            GameObject targetPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(targetPrefabPath);
            if (sourcePrefab == null || targetPrefab == null)
            {
                return new ErrorResponse("Both source and target prefabs must resolve to prefab assets.");
            }

            List<object> changes = new List<object>();
            int sourceChildCount = sourcePrefab.transform.childCount;
            int targetChildCount = targetPrefab.transform.childCount;
            if (sourceChildCount != targetChildCount)
            {
                changes.Add(new { field = "child_count", source = sourceChildCount, target = targetChildCount });
            }

            return new SuccessResponse(
                changes.Count == 0 ? "Prefab states match." : "Computed prefab diff.",
                new
                {
                    compare_mode = compareMode,
                    source = new
                    {
                        path = prefabPath,
                        name = sourcePrefab.name,
                        child_count = sourceChildCount,
                        component_count = sourcePrefab.GetComponents<Component>().Length,
                        objects = new[]
                        {
                            new
                            {
                                path = sourcePrefab.name,
                                name = sourcePrefab.name,
                                active = sourcePrefab.activeSelf,
                                components = sourcePrefab.GetComponents<Component>().Where(component => component != null).Select(component => new { type = component.GetType().Name }).ToList(),
                                children = new object[0],
                            }
                        },
                    },
                    target = new
                    {
                        path = targetPrefabPath,
                        name = targetPrefab.name,
                        child_count = targetChildCount,
                        component_count = targetPrefab.GetComponents<Component>().Length,
                        objects = new[]
                        {
                            new
                            {
                                path = targetPrefab.name,
                                name = targetPrefab.name,
                                active = targetPrefab.activeSelf,
                                components = targetPrefab.GetComponents<Component>().Where(component => component != null).Select(component => new { type = component.GetType().Name }).ToList(),
                                children = new object[0],
                            }
                        },
                    },
                    summary = new { total_changes = changes.Count, added = 0, removed = 0, modified = changes.Count, comparison_limited = compareMode == "current_vs_saved" },
                    changes,
                }
            );
        }
    }

    [McpForUnityTool("apply_scene_patch", AutoRegister = false)]
    public static class ApplyScenePatch
    {
        public static object HandleCommand(JObject @params)
        {
            JArray operations = LiveV2V3ToolCommon.GetParam(@params, "operations") as JArray;
            bool dryRun = LiveV2V3ToolCommon.GetBoolParam(@params, "dryRun", "dry_run") ?? false;
            if (operations == null || operations.Count == 0)
            {
                return new ErrorResponse("'operations' is required.");
            }

            if (dryRun)
            {
                return new SuccessResponse(
                    "Scene patch dry run complete.",
                    new
                    {
                        dry_run = true,
                        operations = operations.Select(operation => new
                        {
                            op = operation["op"]?.ToString(),
                            path = operation["path"]?.ToString(),
                            will_apply = true,
                        }).ToList(),
                        summary = new { total_operations = operations.Count },
                    }
                );
            }

            List<object> applied = new List<object>();
            foreach (JObject operation in operations.OfType<JObject>())
            {
                string op = operation["op"]?.ToString()?.ToLowerInvariant();
                string path = operation["path"]?.ToString();
                switch (op)
                {
                    case "add":
                        JObject value = operation["value"] as JObject;
                        string name = value? ["name"]?.ToString() ?? path ?? $"PatchedObject_{Guid.NewGuid():N}";
                        GameObject created = new GameObject(name);
                        applied.Add(new { op, path = name, instance_id = created.GetInstanceID() });
                        break;
                    case "remove":
                        GameObject target = GameObject.Find(path);
                        if (target != null)
                        {
                            UnityEngine.Object.DestroyImmediate(target);
                            applied.Add(new { op, path, removed = true });
                        }
                        break;
                    default:
                        return new ErrorResponse($"Unsupported scene patch operation '{op}'.");
                }
            }

            EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            return new SuccessResponse("Applied scene patch.", new { dry_run = false, applied, summary = new { total_operations = applied.Count } });
        }
    }

    [McpForUnityTool("apply_prefab_patch", AutoRegister = false)]
    public static class ApplyPrefabPatch
    {
        public static object HandleCommand(JObject @params)
        {
            string prefabPath = LiveV2V3AssetUtility.ResolveAssetPath(@params, "prefabPath", "prefab_path");
            JArray operations = LiveV2V3ToolCommon.GetParam(@params, "operations") as JArray;
            bool dryRun = LiveV2V3ToolCommon.GetBoolParam(@params, "dryRun", "dry_run") ?? false;
            if (string.IsNullOrWhiteSpace(prefabPath) || !File.Exists(Path.GetFullPath(prefabPath)))
            {
                return new ErrorResponse("Valid prefab_path is required.");
            }

            if (operations == null || operations.Count == 0)
            {
                return new ErrorResponse("'operations' is required.");
            }

            if (dryRun)
            {
                return new SuccessResponse(
                    "Prefab patch dry run complete.",
                    new
                    {
                        dry_run = true,
                        prefab_path = prefabPath,
                        operations = operations.Select(operation => new
                        {
                            op = operation["op"]?.ToString(),
                            path = operation["path"]?.ToString(),
                            will_apply = true,
                        }).ToList(),
                        summary = new { total_operations = operations.Count },
                    }
                );
            }

            GameObject prefabRoot = PrefabUtility.LoadPrefabContents(prefabPath);
            try
            {
                List<object> applied = new List<object>();
                foreach (JObject operation in operations.OfType<JObject>())
                {
                    string op = operation["op"]?.ToString()?.ToLowerInvariant();
                    string path = operation["path"]?.ToString();
                    Transform target = LiveV2V3AssetUtility.FindTransformByPath(prefabRoot.transform, path);
                    switch (op)
                    {
                        case "add_component":
                            if (target == null)
                            {
                                return new ErrorResponse($"Target path '{path}' was not found in prefab.");
                            }

                            string componentTypeName = LiveV2V3ToolCommon.GetStringParam(operation, "componentType", "component_type");
                            Type componentType = TypeCache.GetTypesDerivedFrom<Component>().FirstOrDefault(type => string.Equals(type.Name, componentTypeName, StringComparison.OrdinalIgnoreCase) || string.Equals(type.FullName, componentTypeName, StringComparison.OrdinalIgnoreCase));
                            if (componentType == null)
                            {
                                return new ErrorResponse($"Component type '{componentTypeName}' was not found.");
                            }

                            if (target.GetComponent(componentType) == null)
                            {
                                target.gameObject.AddComponent(componentType);
                            }

                            applied.Add(new { op, path, component_type = componentType.Name });
                            break;
                        case "remove_component":
                            if (target == null)
                            {
                                return new ErrorResponse($"Target path '{path}' was not found in prefab.");
                            }

                            string removeTypeName = LiveV2V3ToolCommon.GetStringParam(operation, "componentType", "component_type");
                            Component component = target.GetComponents<Component>().FirstOrDefault(candidate => candidate != null && string.Equals(candidate.GetType().Name, removeTypeName, StringComparison.OrdinalIgnoreCase));
                            if (component != null)
                            {
                                UnityEngine.Object.DestroyImmediate(component, true);
                            }

                            applied.Add(new { op, path, component_type = removeTypeName });
                            break;
                        default:
                            return new ErrorResponse($"Unsupported prefab patch operation '{op}'.");
                    }
                }

                PrefabUtility.SaveAsPrefabAsset(prefabRoot, prefabPath);
                AssetDatabase.SaveAssets();
                return new SuccessResponse("Applied prefab patch.", new { dry_run = false, prefab_path = prefabPath, applied, summary = new { total_operations = applied.Count } });
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(prefabRoot);
            }
        }
    }

    [McpForUnityTool("manage_project_settings", AutoRegister = false)]
    public static class ManageProjectSettings
    {
        public static object HandleCommand(JObject @params)
        {
            ToolParams p = LiveV2V3ToolCommon.Wrap(@params);
            string action = p.Get("action", "get_settings").ToLowerInvariant();
            string category = p.Get("settingsCategory", "player").ToLowerInvariant();

            switch (action)
            {
                case "get_settings":
                    return GetSettings(category);
                case "update_settings":
                    return UpdateSettings(category, @params?["settings"] as JObject);
                case "get_build_settings":
                    return ManageScene.HandleCommand(new JObject { ["action"] = "get_build_settings" });
                case "update_build_settings":
                    return ManageBuildSettings.HandleCommand(new JObject
                    {
                        ["action"] = "set_build_settings",
                        ["settings"] = @params?["settings"] ?? new JObject(),
                        ["platform"] = @params?["platform"],
                    });
                default:
                    return new ErrorResponse("Unknown action for manage_project_settings.");
            }
        }

        private static object GetSettings(string category)
        {
            Dictionary<string, object> data = new Dictionary<string, object>
            {
                ["category"] = category,
                ["projectName"] = Application.productName,
                ["companyName"] = PlayerSettings.companyName,
                ["productName"] = PlayerSettings.productName,
                ["bundleVersion"] = PlayerSettings.bundleVersion,
                ["activeBuildTarget"] = EditorUserBuildSettings.activeBuildTarget.ToString(),
            };

            switch (category)
            {
                case "player":
                    data["settings"] = new Dictionary<string, object>
                    {
                        ["companyName"] = PlayerSettings.companyName,
                        ["productName"] = PlayerSettings.productName,
                        ["bundleVersion"] = PlayerSettings.bundleVersion,
                        ["applicationIdentifier"] = LiveV2V3ToolCommon.GetApplicationIdentifier("Current"),
                    };
                    break;
                case "audio":
                    data["settings"] = new Dictionary<string, object>
                    {
                        ["speakerMode"] = AudioSettings.speakerMode.ToString(),
                        ["sampleRate"] = AudioSettings.outputSampleRate,
                    };
                    break;
                case "graphics":
                    data["settings"] = new Dictionary<string, object>
                    {
                        ["colorSpace"] = PlayerSettings.colorSpace.ToString(),
                            ["renderPipeline"] = UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline != null
                                ? UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline.name
                                : "BuiltIn",
                    };
                    break;
                case "time":
                    data["settings"] = new Dictionary<string, object>
                    {
                        ["timeScale"] = Time.timeScale,
                        ["fixedDeltaTime"] = Time.fixedDeltaTime,
                    };
                    break;
                default:
                    data["settings"] = new Dictionary<string, object>
                    {
                        ["editorState"] = LiveV2V3ToolCommon.GetEditorStateSnapshot(),
                    };
                    break;
            }

            return new SuccessResponse($"Retrieved project settings for '{category}'.", data);
        }

        private static object UpdateSettings(string category, JObject settings)
        {
            if (settings == null)
            {
                return new ErrorResponse("'settings' payload is required.");
            }

            switch (category)
            {
                case "player":
                    List<string> updated = new List<string>();
                    foreach (JProperty property in settings.Properties())
                    {
                        if (property.Name.Equals("applicationIdentifier", StringComparison.OrdinalIgnoreCase))
                        {
                            LiveV2V3ToolCommon.SetApplicationIdentifier("Current", property.Value.ToString());
                            updated.Add(property.Name);
                            continue;
                        }

                        if (LiveV2V3ToolCommon.TrySetProperty(typeof(PlayerSettings), null, property.Name, property.Value))
                        {
                            updated.Add(property.Name);
                        }
                    }

                    return new SuccessResponse(
                        $"Updated {updated.Count} project setting(s) for '{category}'.",
                        new { updated }
                    );
                default:
                    return new SuccessResponse(
                        $"Category '{category}' is live but currently read-mostly.",
                        new
                        {
                            category,
                            settings = settings,
                        }
                    );
            }
        }
    }

    [McpForUnityTool("manage_editor_settings", AutoRegister = false)]
    public static class ManageEditorSettings
    {
        public static object HandleCommand(JObject @params)
        {
            ToolParams p = LiveV2V3ToolCommon.Wrap(@params);
            string action = p.Get("action", "get_preferences").ToLowerInvariant();
            string category = p.Get("preferenceCategory", "general").ToLowerInvariant();
            JObject preferences = @params?["preferences"] as JObject;

            if (action == "get_preferences")
            {
                return new SuccessResponse(
                    $"Retrieved editor preferences for '{category}'.",
                    new
                    {
                        category,
                        preferences = new Dictionary<string, object>
                        {
                            ["autoRefresh"] = EditorPrefs.GetBool("kAutoRefresh"),
                            ["showAssetStoreSearchHits"] = EditorPrefs.GetBool("ShowAssetStoreSearchHits"),
                            ["inspectorMode"] = EditorPrefs.GetInt("InspectorMode", 0),
                            ["lineEndingsForNewScripts"] = EditorSettings.lineEndingsForNewScripts.ToString(),
                            ["enterPlayModeOptionsEnabled"] = EditorSettings.enterPlayModeOptionsEnabled,
                            ["enterPlayModeOptions"] = EditorSettings.enterPlayModeOptions.ToString(),
                        }
                    }
                );
            }

            if (preferences == null)
            {
                return new ErrorResponse("'preferences' payload is required.");
            }

            List<string> updated = new List<string>();
            foreach (JProperty property in preferences.Properties())
            {
                switch (property.Name)
                {
                    case "autoRefresh":
                        EditorPrefs.SetBool("kAutoRefresh", property.Value.Value<bool>());
                        updated.Add(property.Name);
                        break;
                    case "showAssetStoreSearchHits":
                        EditorPrefs.SetBool("ShowAssetStoreSearchHits", property.Value.Value<bool>());
                        updated.Add(property.Name);
                        break;
                    case "enterPlayModeOptionsEnabled":
                    case "enterPlayModeOptions":
                    case "lineEndingsForNewScripts":
                        if (LiveV2V3ToolCommon.TrySetProperty(typeof(EditorSettings), null, property.Name, property.Value))
                        {
                            updated.Add(property.Name);
                        }
                        break;
                }
            }

            return new SuccessResponse("Updated editor preferences.", new { updated, category });
        }
    }

    [McpForUnityTool("manage_player_settings", AutoRegister = false)]
    public static class ManagePlayerSettings
    {
        public static object HandleCommand(JObject @params)
        {
            ToolParams p = LiveV2V3ToolCommon.Wrap(@params);
            string action = p.Get("action", "get_player_settings").ToLowerInvariant();
            JObject settings = @params?["settings"] as JObject;
            string platform = p.Get("platform");
            BuildTargetGroup buildTargetGroup = LiveV2V3ToolCommon.ResolveBuildTargetGroup(platform);

            switch (action)
            {
                case "get_settings":
                case "get_player_settings":
                    return new SuccessResponse(
                        "Retrieved player settings.",
                        new
                        {
                            companyName = PlayerSettings.companyName,
                            productName = PlayerSettings.productName,
                            bundleVersion = PlayerSettings.bundleVersion,
                            applicationIdentifier = LiveV2V3ToolCommon.GetApplicationIdentifier(buildTargetGroup),
                            colorSpace = PlayerSettings.colorSpace.ToString(),
                            scriptingBackend = LiveV2V3ToolCommon.GetScriptingBackend(buildTargetGroup).ToString(),
                        }
                    );
                case "set_settings":
                case "set_player_settings":
                    return SetPlayerSettings(settings, buildTargetGroup);
                case "get_resolution_settings":
                    return new SuccessResponse(
                        "Retrieved resolution settings.",
                        new
                        {
                            defaultScreenWidth = PlayerSettings.defaultScreenWidth,
                            defaultScreenHeight = PlayerSettings.defaultScreenHeight,
                            defaultIsFullScreen = LiveV2V3ToolCommon.GetDefaultIsFullScreen(),
                            resizableWindow = PlayerSettings.resizableWindow,
                            fullscreenMode = PlayerSettings.fullScreenMode.ToString(),
                        }
                    );
                case "set_resolution_settings":
                    return SetPlayerSettings(settings, buildTargetGroup, resolutionOnly: true);
                case "get_publishing_settings":
                    return new SuccessResponse(
                        "Retrieved publishing settings.",
                        new
                        {
                            applicationIdentifier = LiveV2V3ToolCommon.GetApplicationIdentifier(buildTargetGroup),
                            bundleVersion = PlayerSettings.bundleVersion,
                            scriptingBackend = LiveV2V3ToolCommon.GetScriptingBackend(buildTargetGroup).ToString(),
                        }
                    );
                case "get_splash_settings":
                    return new SuccessResponse(
                        "Retrieved splash settings.",
                        new
                        {
                            showUnitySplashScreen = PlayerSettings.SplashScreen.show,
                            overlayOpacity = PlayerSettings.SplashScreen.overlayOpacity,
                        }
                    );
                case "get_icon_settings":
                    return new SuccessResponse("Retrieved icon settings.", new { platform = buildTargetGroup.ToString() });
                default:
                    return new ErrorResponse("Unknown action for manage_player_settings.");
            }
        }

        private static object SetPlayerSettings(JObject settings, BuildTargetGroup buildTargetGroup, bool resolutionOnly = false)
        {
            if (settings == null)
            {
                return new ErrorResponse("'settings' payload is required.");
            }

            List<string> updated = new List<string>();
            foreach (JProperty property in settings.Properties())
            {
                if (property.Name.Equals("applicationIdentifier", StringComparison.OrdinalIgnoreCase))
                {
                    LiveV2V3ToolCommon.SetApplicationIdentifier(buildTargetGroup, property.Value.ToString());
                    updated.Add(property.Name);
                    continue;
                }

                if (resolutionOnly)
                {
                    switch (property.Name)
                    {
                        case "defaultResolution":
                            string[] parts = property.Value.ToString().Split('x');
                            if (parts.Length == 2 && int.TryParse(parts[0], out int width) && int.TryParse(parts[1], out int height))
                            {
                                PlayerSettings.defaultScreenWidth = width;
                                PlayerSettings.defaultScreenHeight = height;
                                updated.Add(property.Name);
                            }
                            continue;
                    }
                }

                if (LiveV2V3ToolCommon.TrySetProperty(typeof(PlayerSettings), null, property.Name, property.Value))
                {
                    updated.Add(property.Name);
                }
            }

            return new SuccessResponse("Updated player settings.", new { updated });
        }
    }

    [McpForUnityTool("manage_build_settings", AutoRegister = false)]
    public static class ManageBuildSettings
    {
        public static object HandleCommand(JObject @params)
        {
            ToolParams p = LiveV2V3ToolCommon.Wrap(@params);
            string action = p.Get("action", "get_build_settings").ToLowerInvariant();
            string scenePath = p.Get("scenePath");
            bool sceneEnabled = p.GetBool("sceneEnabled", true);
            JObject settings = @params?["settings"] as JObject;
            string platform = p.Get("targetPlatform") ?? p.Get("platform");

            switch (action)
            {
                case "get_build_settings":
                case "get_scenes_in_build":
                    return ManageScene.HandleCommand(new JObject { ["action"] = "get_build_settings" });
                case "add_scene_to_build":
                    return AddOrUpdateScene(scenePath, sceneEnabled);
                case "remove_scene_from_build":
                    return RemoveScene(scenePath);
                case "set_build_platform":
                    return SetBuildPlatform(platform);
                case "set_build_settings":
                    return SetBuildSettings(settings);
                default:
                    return new ErrorResponse("Unknown action for manage_build_settings.");
            }
        }

        private static object AddOrUpdateScene(string scenePath, bool enabled)
        {
            string sanitized = LiveV2V3ToolCommon.SanitizeAssetPath(scenePath);
            if (string.IsNullOrWhiteSpace(sanitized))
            {
                return new ErrorResponse("'scenePath' is required.");
            }

            List<EditorBuildSettingsScene> scenes = EditorBuildSettings.scenes.ToList();
            int existingIndex = scenes.FindIndex(scene => scene.path.Equals(sanitized, StringComparison.OrdinalIgnoreCase));
            if (existingIndex >= 0)
            {
                scenes[existingIndex] = new EditorBuildSettingsScene(sanitized, enabled);
            }
            else
            {
                scenes.Add(new EditorBuildSettingsScene(sanitized, enabled));
            }

            EditorBuildSettings.scenes = scenes.ToArray();
            return new SuccessResponse("Updated scenes in build.", new { scenePath = sanitized, enabled });
        }

        private static object RemoveScene(string scenePath)
        {
            string sanitized = LiveV2V3ToolCommon.SanitizeAssetPath(scenePath);
            List<EditorBuildSettingsScene> scenes = EditorBuildSettings.scenes.ToList();
            int removed = scenes.RemoveAll(scene => scene.path.Equals(sanitized, StringComparison.OrdinalIgnoreCase));
            EditorBuildSettings.scenes = scenes.ToArray();
            return new SuccessResponse("Removed scene from build settings.", new { scenePath = sanitized, removed });
        }

        private static object SetBuildPlatform(string platform)
        {
            if (string.IsNullOrWhiteSpace(platform))
            {
                return new ErrorResponse("'targetPlatform' is required.");
            }

            if (!LiveV2V3ToolCommon.TryResolveBuildTarget(platform, out BuildTarget buildTarget))
            {
                return new ErrorResponse($"Unsupported build target '{platform}'.");
            }

            BuildTargetGroup buildTargetGroup = BuildPipeline.GetBuildTargetGroup(buildTarget);
            bool switched = EditorUserBuildSettings.SwitchActiveBuildTarget(buildTargetGroup, buildTarget);
            return new SuccessResponse(
                switched ? "Switched active build target." : "Build target already active or switch was deferred.",
                new
                {
                    targetPlatform = buildTarget.ToString(),
                    buildTargetGroup = buildTargetGroup.ToString(),
                    switched,
                }
            );
        }

        private static object SetBuildSettings(JObject settings)
        {
            if (settings == null)
            {
                return new ErrorResponse("'settings' payload is required.");
            }

            List<string> updated = new List<string>();
            foreach (JProperty property in settings.Properties())
            {
                if (LiveV2V3ToolCommon.TrySetProperty(typeof(EditorUserBuildSettings), null, property.Name, property.Value))
                {
                    updated.Add(property.Name);
                }
            }

            return new SuccessResponse("Updated build settings.", new { updated });
        }
    }

    [McpForUnityTool("manage_define_symbols", AutoRegister = false)]
    public static class ManageDefineSymbols
    {
        public static object HandleCommand(JObject @params)
        {
            ToolParams p = LiveV2V3ToolCommon.Wrap(@params);
            string action = p.Get("action", "get_define_symbols").ToLowerInvariant();
            string platform = p.Get("platform");
            string symbol = p.Get("symbol");
            string[] symbols = @params?["symbols"]?.ToObject<string[]>() ?? Array.Empty<string>();
            BuildTargetGroup buildTargetGroup = LiveV2V3ToolCommon.ResolveBuildTargetGroup(platform);

            string current = LiveV2V3ToolCommon.GetScriptingDefineSymbols(buildTargetGroup);
            List<string> currentSymbols = current.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries).Distinct(StringComparer.OrdinalIgnoreCase).ToList();

            switch (action)
            {
                case "get_symbols":
                case "get_define_symbols":
                    return new SuccessResponse("Retrieved define symbols.", new { platform = buildTargetGroup.ToString(), symbols = currentSymbols });
                case "add_symbol":
                case "add_define_symbol":
                    if (!string.IsNullOrWhiteSpace(symbol) && !currentSymbols.Contains(symbol, StringComparer.OrdinalIgnoreCase))
                    {
                        currentSymbols.Add(symbol);
                    }
                    break;
                case "remove_symbol":
                case "remove_define_symbol":
                    currentSymbols.RemoveAll(item => item.Equals(symbol, StringComparison.OrdinalIgnoreCase));
                    break;
                case "set_symbols":
                case "set_define_symbols":
                    currentSymbols = symbols.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
                    break;
                default:
                    return new ErrorResponse("Unknown action for manage_define_symbols.");
            }

            LiveV2V3ToolCommon.SetScriptingDefineSymbols(buildTargetGroup, string.Join(";", currentSymbols));
            return new SuccessResponse("Updated define symbols.", new { platform = buildTargetGroup.ToString(), symbols = currentSymbols });
        }
    }

    [McpForUnityTool("manage_asset_import_settings", AutoRegister = false)]
    public static class ManageAssetImportSettings
    {
        public static object HandleCommand(JObject @params)
        {
            ToolParams p = LiveV2V3ToolCommon.Wrap(@params);
            string action = p.Get("action", "get_import_settings").ToLowerInvariant();
            string assetPath = LiveV2V3ToolCommon.SanitizeAssetPath(p.Get("assetPath"));
            JObject settings = @params?["settings"] as JObject;

            if (string.IsNullOrWhiteSpace(assetPath))
            {
                return new ErrorResponse("'assetPath' is required.");
            }

            AssetImporter importer = AssetImporter.GetAtPath(assetPath);
            if (importer == null)
            {
                return new ErrorResponse($"No importer found for asset '{assetPath}'.");
            }

            if (action == "get_import_settings")
            {
                return new SuccessResponse("Retrieved import settings.", LiveV2V3ToolCommon.CaptureImporterSettings(importer));
            }

            if (settings == null)
            {
                return new ErrorResponse("'settings' payload is required.");
            }

            List<string> updated = new List<string>();
            foreach (JProperty property in settings.Properties())
            {
                if (LiveV2V3ToolCommon.TrySetProperty(importer.GetType(), importer, property.Name, property.Value))
                {
                    updated.Add(property.Name);
                }
            }

            AssetDatabase.WriteImportSettingsIfDirty(assetPath);
            importer.SaveAndReimport();
            return new SuccessResponse("Updated import settings.", new { assetPath, updated });
        }
    }

    [McpForUnityTool("manage_import_pipeline", AutoRegister = false)]
    public static class ManageImportPipeline
    {
        public static object HandleCommand(JObject @params)
        {
            ToolParams p = LiveV2V3ToolCommon.Wrap(@params);
            string action = p.Get("action", "get_import_queue_status").ToLowerInvariant();
            JObject settings = @params?["settings"] as JObject;
            JArray assetPaths = @params?["assetPaths"] as JArray;
            string assetPath = p.Get("assetPath");
            JObject options = @params?["options"] as JObject;
            string[] resolvedPaths = LiveV2V3ToolCommon.ExpandAssetPaths(assetPaths);
            if (!string.IsNullOrWhiteSpace(assetPath))
            {
                resolvedPaths = resolvedPaths.Concat(new[] { LiveV2V3ToolCommon.SanitizeAssetPath(assetPath) }).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
            }

            switch (action)
            {
                case "get_queue":
                case "get_import_queue_status":
                    return new SuccessResponse(
                        "Retrieved import pipeline status.",
                        new
                        {
                            isUpdating = EditorApplication.isUpdating,
                            isCompiling = EditorApplication.isCompiling,
                            importPaused = LiveV2V3ToolState.ImportPaused,
                            editorState = LiveV2V3ToolCommon.GetEditorStateSnapshot(),
                        }
                    );
                case "force_reimport_by_type":
                case "force_reimport":
                case "refresh":
                    if (resolvedPaths.Length == 0)
                    {
                        AssetDatabase.Refresh();
                        return new SuccessResponse("Refreshed asset database.", new { scope = "project" });
                    }

                    foreach (string path in resolvedPaths.Where(path => !string.IsNullOrWhiteSpace(path)))
                    {
                        AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ImportRecursive);
                    }
                    return new SuccessResponse("Reimported assets.", new { assetPaths = resolvedPaths, options = options });
                case "force_reserialize":
                    AssetDatabase.ForceReserializeAssets(resolvedPaths.Length == 0 ? null : resolvedPaths.ToList());
                    return new SuccessResponse("Force reserialize completed.", new { assetPaths = resolvedPaths });
                case "pause_import":
                case "stop_refresh":
                    if (!LiveV2V3ToolState.ImportPaused)
                    {
                        AssetDatabase.StartAssetEditing();
                        LiveV2V3ToolState.ImportPaused = true;
                    }
                    return new SuccessResponse("Asset import paused.", new { importPaused = true });
                case "resume_import":
                    if (LiveV2V3ToolState.ImportPaused)
                    {
                        AssetDatabase.StopAssetEditing();
                        LiveV2V3ToolState.ImportPaused = false;
                    }
                    return new SuccessResponse("Asset import resumed.", new { importPaused = false });
                case "get_importer_settings":
                    return ManageAssetImportSettings.HandleCommand(new JObject { ["action"] = "get_import_settings", ["assetPath"] = assetPath });
                case "set_importer_settings":
                    return ManageAssetImportSettings.HandleCommand(new JObject { ["action"] = "update_import_settings", ["assetPath"] = assetPath, ["settings"] = settings ?? new JObject() });
                default:
                    return new ErrorResponse("Unknown action for manage_import_pipeline.");
            }
        }
    }

    [McpForUnityTool("manage_registry_config", AutoRegister = false)]
    public static class ManageRegistryConfig
    {
        public static object HandleCommand(JObject @params)
        {
            ToolParams p = LiveV2V3ToolCommon.Wrap(@params);
            string action = p.Get("action", "list_scoped_registries").ToLowerInvariant();
            string registryName = p.Get("registryName");
            string registryUrl = p.Get("registryUrl");
            string newName = p.Get("newName");
            List<string> scopes = @params?["scopes"]?.ToObject<List<string>>() ?? new List<string>();

            if (action == "list_scoped_registries")
            {
                return PackageList.ListRegistries();
            }

            string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), "Packages", "manifest.json");
            if (!File.Exists(manifestPath))
            {
                return new ErrorResponse("Package manifest not found.");
            }

            JObject manifest = JObject.Parse(File.ReadAllText(manifestPath));
            JArray scopedRegistries = manifest["scopedRegistries"] as JArray ?? new JArray();
            manifest["scopedRegistries"] = scopedRegistries;

            JObject existing = scopedRegistries.OfType<JObject>().FirstOrDefault(reg => string.Equals(reg.Value<string>("name"), registryName, StringComparison.OrdinalIgnoreCase));
            switch (action)
            {
                case "add_registry":
                    if (existing != null)
                    {
                        return new ErrorResponse($"Registry '{registryName}' already exists.");
                    }
                    scopedRegistries.Add(new JObject
                    {
                        ["name"] = registryName,
                        ["url"] = registryUrl,
                        ["scopes"] = new JArray(scopes),
                    });
                    break;
                case "remove_registry":
                    if (existing == null)
                    {
                        return new ErrorResponse($"Registry '{registryName}' not found.");
                    }
                    existing.Remove();
                    break;
                case "update_registry":
                    if (existing == null)
                    {
                        return new ErrorResponse($"Registry '{registryName}' not found.");
                    }
                    if (!string.IsNullOrWhiteSpace(newName))
                    {
                        existing["name"] = newName;
                    }
                    if (!string.IsNullOrWhiteSpace(registryUrl))
                    {
                        existing["url"] = registryUrl;
                    }
                    if (scopes.Count > 0)
                    {
                        existing["scopes"] = new JArray(scopes);
                    }
                    break;
                default:
                    return new ErrorResponse("Unknown action for manage_registry_config.");
            }

            File.WriteAllText(manifestPath, manifest.ToString());
            AssetDatabase.Refresh();
            return new SuccessResponse("Registry configuration updated.", new { action, registryName, registryUrl, scopes });
        }
    }

    [McpForUnityTool("navigate_editor", AutoRegister = false)]
    public static class NavigateEditor
    {
        public static object HandleCommand(JObject @params)
        {
            ToolParams p = LiveV2V3ToolCommon.Wrap(@params);
            string navigationType = p.Get("navigationType", "get_context").ToLowerInvariant();
            bool select = p.GetBool("select", true);
            bool highlight = p.GetBool("highlight", true);
            bool frameInScene = p.GetBool("frameInScene", false);
            bool frameSelected = p.GetBool("frameSelected", true);
            bool lockInspector = p.GetBool("lockInspector", false);
            string inspectorAction = p.Get("inspectorAction", "open").ToLowerInvariant();
            JToken targetToken = @params?["target"];
            string navigationId = $"nav_{navigationType}_{Guid.NewGuid():N}";

            switch (navigationType)
            {
                case "get_context":
                    return new SuccessResponse("Retrieved editor navigation context.", new { navigation_id = navigationId, editor_state = LiveV2V3ToolCommon.BuildEditorContext() });
                case "restore_context":
                    return RestoreContext(@params?["previousContext"] as JObject, navigationId);
                case "reveal_in_project":
                    return RevealInProject(targetToken, select, highlight, navigationId);
                case "focus_hierarchy":
                    return FocusHierarchyInternal(targetToken, select, frameInScene, navigationId);
                case "frame_in_scene":
                    return FrameInScene(targetToken, frameSelected, navigationId);
                case "open_inspector":
                    return OpenInspector(targetToken, inspectorAction, lockInspector, navigationId);
                case "open_script":
                case "open_asset":
                    return OpenAsset(targetToken, p.GetInt("lineNumber") ?? 0, navigationId);
                default:
                    return new ErrorResponse($"Unknown navigation type '{navigationType}'.");
            }
        }

        private static object RestoreContext(JObject previousContext, string navigationId)
        {
            if (previousContext == null)
            {
                return new ErrorResponse("'previousContext' is required for restore_context.");
            }

            JArray selectionIds = previousContext["selectionInstanceIds"] as JArray;
            if (selectionIds != null)
            {
                int[] ids = selectionIds.ToObject<int[]>();
                UnityEditor.Selection.objects = ids
                    .Select(UnityEditorObjectLookup.FindObjectByInstanceId)
                    .Where(obj => obj != null)
                    .ToArray();
            }

            return new SuccessResponse("Restored editor context.", new { navigation_id = navigationId, editor_state = LiveV2V3ToolCommon.BuildEditorContext() });
        }

        private static object RevealInProject(JToken targetToken, bool select, bool highlight, string navigationId)
        {
            UnityEngine.Object target = LiveV2V3ToolCommon.ResolveUnityObject(targetToken);
            if (target == null)
            {
                return new ErrorResponse("Target not found for reveal_in_project.");
            }

            EditorUtility.FocusProjectWindow();
            if (select)
            {
                UnityEditor.Selection.activeObject = target;
            }
            if (highlight)
            {
                EditorGUIUtility.PingObject(target);
            }

            return new SuccessResponse(
                "Revealed asset in Project window.",
                new
                {
                    navigation_id = navigationId,
                    asset_info = LiveV2V3ToolCommon.DescribeObject(target),
                    editor_state = LiveV2V3ToolCommon.BuildEditorContext(),
                }
            );
        }

        private static object FocusHierarchyInternal(JToken targetToken, bool select, bool frameInScene, string navigationId)
        {
            GameObject target = LiveV2V3ToolCommon.ResolveGameObject(targetToken);
            if (target == null)
            {
                return new ErrorResponse("Target GameObject not found for focus_hierarchy.");
            }

            EditorApplication.ExecuteMenuItem("Window/General/Hierarchy");
            if (select)
            {
                UnityEditor.Selection.activeGameObject = target;
            }
            EditorGUIUtility.PingObject(target);

            if (frameInScene)
            {
                SceneView.lastActiveSceneView?.FrameSelected();
            }

            return new SuccessResponse(
                "Focused target in Hierarchy.",
                new
                {
                    navigation_id = navigationId,
                    gameobject_info = LiveV2V3ToolCommon.DescribeObject(target),
                    editor_state = LiveV2V3ToolCommon.BuildEditorContext(),
                }
            );
        }

        private static object FrameInScene(JToken targetToken, bool frameSelected, string navigationId)
        {
            GameObject target = LiveV2V3ToolCommon.ResolveGameObject(targetToken);
            if (target != null)
            {
                UnityEditor.Selection.activeGameObject = target;
            }

            SceneView sceneView = SceneView.lastActiveSceneView;
            if (sceneView == null)
            {
                EditorApplication.ExecuteMenuItem("Window/General/Scene");
                sceneView = SceneView.lastActiveSceneView;
            }

            if (sceneView == null)
            {
                return new ErrorResponse("No Scene view available.");
            }

            if (target != null)
            {
                Renderer renderer = target.GetComponentInChildren<Renderer>();
                if (renderer != null)
                {
                    sceneView.Frame(renderer.bounds, false);
                }
                else
                {
                    Bounds bounds = new Bounds(target.transform.position, Vector3.one * 2f);
                    sceneView.Frame(bounds, false);
                }
            }
            else if (frameSelected)
            {
                sceneView.FrameSelected();
            }

            return new SuccessResponse("Framed target in Scene view.", new { navigation_id = navigationId, editor_state = LiveV2V3ToolCommon.BuildEditorContext() });
        }

        private static object OpenInspector(JToken targetToken, string inspectorAction, bool lockInspector, string navigationId)
        {
            EditorApplication.ExecuteMenuItem("Window/General/Inspector");
            Type inspectorType = Type.GetType("UnityEditor.InspectorWindow,UnityEditor");
            EditorWindow inspector = inspectorType != null ? EditorWindow.GetWindow(inspectorType) : null;

            switch (inspectorAction)
            {
                case "clear":
                    UnityEditor.Selection.objects = Array.Empty<UnityEngine.Object>();
                    break;
                case "get_target":
                    return new SuccessResponse("Retrieved inspector target.", new { navigation_id = navigationId, target_info = LiveV2V3ToolCommon.DescribeObject(UnityEditor.Selection.activeObject), editor_state = LiveV2V3ToolCommon.BuildEditorContext() });
                case "lock":
                case "unlock":
                    if (inspector != null)
                    {
                        PropertyInfo isLocked = inspectorType.GetProperty("isLocked", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
                        isLocked?.SetValue(inspector, inspectorAction == "lock");
                    }
                    return new SuccessResponse("Updated inspector lock state.", new { navigation_id = navigationId, locked = inspectorAction == "lock" });
            }

            UnityEngine.Object target = LiveV2V3ToolCommon.ResolveUnityObject(targetToken);
            if (target == null && inspectorAction != "clear")
            {
                return new ErrorResponse("Target not found for inspector navigation.");
            }

            if (target != null)
            {
                UnityEditor.Selection.activeObject = target;
                EditorGUIUtility.PingObject(target);
            }

            if (inspector != null)
            {
                PropertyInfo isLocked = inspectorType.GetProperty("isLocked", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
                isLocked?.SetValue(inspector, lockInspector);
                inspector.Focus();
                inspector.Repaint();
            }

            return new SuccessResponse("Opened target in Inspector.", new { navigation_id = navigationId, target_info = LiveV2V3ToolCommon.DescribeObject(target), editor_state = LiveV2V3ToolCommon.BuildEditorContext() });
        }

        private static object OpenAsset(JToken targetToken, int lineNumber, string navigationId)
        {
            UnityEngine.Object target = LiveV2V3ToolCommon.ResolveUnityObject(targetToken);
            if (target == null)
            {
                return new ErrorResponse("Target not found for open_asset/open_script.");
            }

            AssetDatabase.OpenAsset(target, lineNumber > 0 ? lineNumber : 0);
            return new SuccessResponse("Opened asset.", new { navigation_id = navigationId, asset_info = LiveV2V3ToolCommon.DescribeObject(target), editor_state = LiveV2V3ToolCommon.BuildEditorContext() });
        }
    }

    [McpForUnityTool("reveal_asset", AutoRegister = false)]
    public static class RevealAsset
    {
        public static object HandleCommand(JObject @params)
        {
            JObject target = new JObject();
            if (@params?["assetPath"] != null) target["path"] = @params["assetPath"];
            if (@params?["guid"] != null) target["guid"] = @params["guid"];
            if (@params?["assetGuid"] != null) target["guid"] = @params["assetGuid"];
            if (@params?["instanceId"] != null) target["instance_id"] = @params["instanceId"];
            return NavigateEditor.HandleCommand(new JObject
            {
                ["navigationType"] = "reveal_in_project",
                ["target"] = target,
                ["select"] = @params?["select"] ?? true,
                ["highlight"] = @params?["highlight"] ?? true,
            });
        }
    }

    [McpForUnityTool("focus_hierarchy", AutoRegister = false)]
    public static class FocusHierarchy
    {
        public static object HandleCommand(JObject @params)
        {
            JToken target = @params?["target"];
            if (target == null && @params?["targetName"] != null) target = new JObject { ["name"] = @params["targetName"] };
            if (target == null && @params?["instanceId"] != null) target = new JObject { ["instance_id"] = @params["instanceId"] };
            if (target == null && @params?["hierarchyPath"] != null) target = new JObject { ["path"] = @params["hierarchyPath"] };
            return NavigateEditor.HandleCommand(new JObject
            {
                ["navigationType"] = "focus_hierarchy",
                ["target"] = target,
                ["select"] = @params?["select"] ?? true,
                ["frameInScene"] = @params?["frameInScene"] ?? false,
            });
        }
    }

    [McpForUnityTool("frame_scene_target", AutoRegister = false)]
    public static class FrameSceneTarget
    {
        public static object HandleCommand(JObject @params)
        {
            return NavigateEditor.HandleCommand(new JObject
            {
                ["navigationType"] = "frame_in_scene",
                ["target"] = @params?["target"],
                ["frameSelected"] = @params?["frameSelected"] ?? true,
            });
        }
    }

    [McpForUnityTool("open_inspector_target", AutoRegister = false)]
    public static class OpenInspectorTarget
    {
        public static object HandleCommand(JObject @params)
        {
            JObject mapped = new JObject
            {
                ["navigationType"] = "open_inspector",
                ["inspectorAction"] = @params?["action"] ?? "open",
                ["target"] = @params?["target"],
                ["lockInspector"] = @params?["lock"] ?? false,
            };
            if (@params?["assetGuid"] != null && mapped["target"] == null) mapped["target"] = new JObject { ["guid"] = @params["assetGuid"] };
            if (@params?["assetPath"] != null && mapped["target"] == null) mapped["target"] = new JObject { ["path"] = @params["assetPath"] };
            if (@params?["instanceId"] != null && mapped["target"] == null) mapped["target"] = new JObject { ["instance_id"] = @params["instanceId"] };
            return NavigateEditor.HandleCommand(mapped);
        }
    }

    [McpForUnityTool("search_assets_advanced", AutoRegister = false)]
    public static class SearchAssetsAdvanced
    {
        public static object HandleCommand(JObject @params)
        {
            ToolParams p = LiveV2V3ToolCommon.Wrap(@params);
            string[] assetTypes = @params?["assetTypes"]?.ToObject<string[]>() ?? Array.Empty<string>();
            string[] labels = @params?["labels"]?.ToObject<string[]>() ?? Array.Empty<string>();
            string searchPath = p.Get("searchPath");
            string namePattern = p.Get("namePattern");
            string importerType = p.Get("importerType");
            long? minSizeBytes = @params?["minSizeBytes"]?.Value<long?>();
            long? maxSizeBytes = @params?["maxSizeBytes"]?.Value<long?>();
            string modifiedAfter = p.Get("modifiedAfter");
            string modifiedBefore = p.Get("modifiedBefore");
            bool unusedOnly = p.GetBool("unusedOnly", false);
            int page = Math.Max(1, p.GetInt("page", 1) ?? 1);
            int pageSize = Math.Max(1, Math.Min(100, p.GetInt("pageSize", 25) ?? 25));
            bool includeMetadata = p.GetBool("includeMetadata", true);

            List<string> tokens = new List<string>();
            foreach (string assetType in assetTypes)
            {
                string typeToken = assetType.ToLowerInvariant() switch
                {
                    "scenes" => "t:Scene",
                    "prefabs" => "t:Prefab",
                    "materials" => "t:Material",
                    "shaders" => "t:Shader",
                    "textures" => "t:Texture",
                    "audio" => "t:AudioClip",
                    "scriptable_objects" => "t:ScriptableObject",
                    "animations" => "t:AnimationClip",
                    "models" => "t:Model",
                    "fonts" => "t:Font",
                    "sprites" => "t:Sprite",
                    "folders" => "t:DefaultAsset",
                    _ => string.Empty,
                };
                if (!string.IsNullOrWhiteSpace(typeToken))
                {
                    tokens.Add(typeToken);
                }
            }

            foreach (string label in labels.Where(label => !string.IsNullOrWhiteSpace(label)))
            {
                tokens.Add($"l:{label}");
            }

            if (!string.IsNullOrWhiteSpace(namePattern) && !namePattern.Contains("*") && !namePattern.Contains("?"))
            {
                tokens.Add(namePattern);
            }

            string[] searchFolders = !string.IsNullOrWhiteSpace(searchPath) ? new[] { LiveV2V3ToolCommon.SanitizeAssetPath(searchPath) } : null;
            string[] guids = AssetDatabase.FindAssets(string.Join(" ", tokens), searchFolders);

            DateTime? afterDate = TryParseDate(modifiedAfter);
            DateTime? beforeDate = TryParseDate(modifiedBefore);
            List<Dictionary<string, object>> assets = new List<Dictionary<string, object>>();

            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (!LiveV2V3ToolCommon.MatchesPathPattern(Path.GetFileName(path), namePattern))
                {
                    continue;
                }

                string absolutePath = Path.Combine(Directory.GetCurrentDirectory(), path);
                long fileSize = File.Exists(absolutePath) ? new FileInfo(absolutePath).Length : 0;
                DateTime modifiedTime = File.Exists(absolutePath) ? File.GetLastWriteTimeUtc(absolutePath) : DateTime.MinValue;

                if (minSizeBytes.HasValue && fileSize < minSizeBytes.Value) continue;
                if (maxSizeBytes.HasValue && fileSize > maxSizeBytes.Value) continue;
                if (afterDate.HasValue && modifiedTime < afterDate.Value) continue;
                if (beforeDate.HasValue && modifiedTime > beforeDate.Value) continue;

                AssetImporter importer = (!string.IsNullOrWhiteSpace(importerType) || includeMetadata)
                    ? AssetImporter.GetAtPath(path)
                    : null;
                if (!string.IsNullOrWhiteSpace(importerType) && (importer == null || !importer.GetType().Name.Equals(importerType, StringComparison.OrdinalIgnoreCase)))
                {
                    continue;
                }

                string[] dependencies = (unusedOnly || includeMetadata)
                    ? AssetDatabase.GetDependencies(path, false)
                    : Array.Empty<string>();
                bool isUnused = dependencies.Length > 0 ? dependencies.Length <= 1 : false;
                if (unusedOnly && !isUnused)
                {
                    continue;
                }

                Dictionary<string, object> assetInfo = new Dictionary<string, object>
                {
                    ["guid"] = guid,
                    ["path"] = path,
                    ["name"] = Path.GetFileNameWithoutExtension(path),
                    ["type"] = AssetDatabase.GetMainAssetTypeAtPath(path)?.Name,
                    ["sizeBytes"] = fileSize,
                    ["modifiedTime"] = modifiedTime == DateTime.MinValue ? null : modifiedTime.ToString("o"),
                    ["labels"] = includeMetadata ? AssetDatabase.GetLabels(AssetDatabase.LoadMainAssetAtPath(path)) : Array.Empty<string>(),
                    ["isUnused"] = isUnused,
                };

                if (includeMetadata)
                {
                    assetInfo["dependencies"] = dependencies;
                    assetInfo["importerType"] = importer != null ? importer.GetType().Name : null;
                }

                assets.Add(assetInfo);
            }

            string sortBy = p.Get("sortBy", "relevance").ToLowerInvariant();
            bool desc = p.Get("sortOrder", sortBy == "relevance" ? "desc" : "asc").Equals("desc", StringComparison.OrdinalIgnoreCase);
            IEnumerable<Dictionary<string, object>> ordered = sortBy switch
            {
                "name" => desc ? assets.OrderByDescending(asset => asset["name"]) : assets.OrderBy(asset => asset["name"]),
                "path" => desc ? assets.OrderByDescending(asset => asset["path"]) : assets.OrderBy(asset => asset["path"]),
                "type" => desc ? assets.OrderByDescending(asset => asset["type"]) : assets.OrderBy(asset => asset["type"]),
                "size" => desc ? assets.OrderByDescending(asset => asset["sizeBytes"]) : assets.OrderBy(asset => asset["sizeBytes"]),
                "modified_time" => desc ? assets.OrderByDescending(asset => asset["modifiedTime"]) : assets.OrderBy(asset => asset["modifiedTime"]),
                _ => assets.OrderBy(asset => asset["name"]),
            };

            List<Dictionary<string, object>> paged = ordered.Skip((page - 1) * pageSize).Take(pageSize).ToList();
            return new SuccessResponse(
                $"Found {assets.Count} asset(s) matching criteria.",
                new
                {
                    totalCount = assets.Count,
                    page,
                    pageSize,
                    assets = paged,
                }
            );
        }

        private static DateTime? TryParseDate(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return null;
            }

            return DateTime.TryParse(value, out DateTime parsed) ? parsed.ToUniversalTime() : null;
        }
    }

    [McpForUnityTool("wait_for_editor_condition", AutoRegister = false)]
    public static class WaitForEditorCondition
    {
        public static async Task<object> HandleCommand(JObject @params)
        {
            ToolParams p = LiveV2V3ToolCommon.Wrap(@params);
            string condition = p.Get("condition", string.Empty).ToLowerInvariant();
            double timeoutSeconds = @params?["timeoutSeconds"]?.Value<double?>() ?? 30d;
            double pollIntervalSeconds = @params?["pollIntervalSeconds"]?.Value<double?>() ?? 0.5d;
            Stopwatch stopwatch = Stopwatch.StartNew();

            while (stopwatch.Elapsed.TotalSeconds < timeoutSeconds)
            {
                Dictionary<string, object> details = EvaluateCondition(condition, @params, out bool met);
                if (met)
                {
                    return new SuccessResponse(
                        $"Condition '{condition}' met.",
                        new
                        {
                            condition_met = true,
                            condition_type = condition,
                            wait_duration_ms = (int)stopwatch.Elapsed.TotalMilliseconds,
                            timed_out = false,
                            details,
                        }
                    );
                }

                await Task.Delay(TimeSpan.FromSeconds(Math.Max(0.1d, pollIntervalSeconds)));
            }

            return new ErrorResponse($"Condition '{condition}' not met within {timeoutSeconds} seconds.");
        }

        private static Dictionary<string, object> EvaluateCondition(string condition, JObject @params, out bool met)
        {
            JObject snapshot = LiveV2V3ToolCommon.GetEditorStateSnapshot();
            switch (condition)
            {
                case "compile_idle":
                    met = !EditorApplication.isCompiling;
                    return new Dictionary<string, object> { ["isCompiling"] = EditorApplication.isCompiling, ["editorState"] = snapshot };
                case "asset_import_complete":
                    met = !EditorApplication.isUpdating;
                    return new Dictionary<string, object> { ["isUpdating"] = EditorApplication.isUpdating, ["editorState"] = snapshot };
                case "scene_load_complete":
                    string scenePath = @params?["scenePath"]?.ToString();
                    string sceneName = @params?["sceneName"]?.ToString();
                    Scene activeScene = EditorSceneManager.GetActiveScene();
                    met = activeScene.IsValid() && activeScene.isLoaded && (string.IsNullOrWhiteSpace(scenePath) || activeScene.path.Equals(scenePath, StringComparison.OrdinalIgnoreCase)) && (string.IsNullOrWhiteSpace(sceneName) || activeScene.name.Equals(sceneName, StringComparison.OrdinalIgnoreCase));
                    return new Dictionary<string, object> { ["activeScenePath"] = activeScene.path, ["activeSceneName"] = activeScene.name };
                case "play_mode_state":
                    string playModeTarget = @params?["playModeTarget"]?.ToString() ?? "stopped";
                    met = playModeTarget switch
                    {
                        "playing" => EditorApplication.isPlaying && !EditorApplication.isPaused,
                        "paused" => EditorApplication.isPlaying && EditorApplication.isPaused,
                        _ => !EditorApplication.isPlaying,
                    };
                    return new Dictionary<string, object> { ["isPlaying"] = EditorApplication.isPlaying, ["isPaused"] = EditorApplication.isPaused };
                case "prefab_stage_state":
                    UnityEditor.SceneManagement.PrefabStage prefabStage = UnityEditor.SceneManagement.PrefabStageUtility.GetCurrentPrefabStage();
                    string prefabStageTarget = @params?["prefabStageTarget"]?.ToString() ?? "closed";
                    met = prefabStageTarget == "open" ? prefabStage != null : prefabStage == null;
                    return new Dictionary<string, object> { ["prefabOpen"] = prefabStage != null, ["prefabPath"] = prefabStage != null ? prefabStage.assetPath : null };
                case "object_exists":
                    string objectName = @params?["objectName"]?.ToString();
                    string objectGuid = @params?["objectGuid"]?.ToString();
                    UnityEngine.Object found = !string.IsNullOrWhiteSpace(objectGuid)
                        ? AssetDatabase.LoadMainAssetAtPath(AssetDatabase.GUIDToAssetPath(objectGuid))
                        : LiveV2V3ToolCommon.ResolveByString(objectName);
                    met = found != null;
                    return new Dictionary<string, object> { ["objectFound"] = found != null, ["object"] = LiveV2V3ToolCommon.DescribeObject(found) };
                default:
                    met = false;
                    return new Dictionary<string, object> { ["error"] = $"Unsupported condition '{condition}'" };
            }
        }
    }

    [McpForUnityTool("start_trace", AutoRegister = false)]
    public static class StartTrace
    {
        public static object HandleCommand(JObject @params)
        {
            string traceId = Guid.NewGuid().ToString();
            List<string> tags = @params?["tags"]?.ToObject<List<string>>() ?? new List<string>();
            LiveV2V3ToolState.TraceSession session = new LiveV2V3ToolState.TraceSession
            {
                TraceId = traceId,
                StartedAtUtc = DateTime.UtcNow,
                Tags = tags,
                IsActive = true,
            };
            LiveV2V3ToolState.ActiveTraces[traceId] = session;
            LiveV2V3ToolState.CurrentTraceId = traceId;
            return new SuccessResponse("Trace session started.", new { trace_id = traceId, started_at = session.StartedAtUtc.ToString("o"), tags });
        }
    }

    [McpForUnityTool("stop_trace", AutoRegister = false)]
    public static class StopTrace
    {
        public static object HandleCommand(JObject @params)
        {
            string traceId = @params?["traceId"]?.ToString() ?? LiveV2V3ToolState.CurrentTraceId;
            if (string.IsNullOrWhiteSpace(traceId) || !LiveV2V3ToolState.ActiveTraces.TryGetValue(traceId, out LiveV2V3ToolState.TraceSession session))
            {
                return new ErrorResponse("No active trace session. Call start_trace first.");
            }

            session.IsActive = false;
            LiveV2V3ToolState.ActiveTraces.Remove(traceId);
            LiveV2V3ToolState.CompletedTraces[traceId] = session;
            if (LiveV2V3ToolState.CurrentTraceId == traceId)
            {
                LiveV2V3ToolState.CurrentTraceId = null;
            }

            return new SuccessResponse(
                "Trace session stopped.",
                new
                {
                    trace_id = traceId,
                    summary = new
                    {
                        total_requests = session.Entries.Count,
                        error_count = 0,
                        success_count = session.Entries.Count,
                        tools_used = new List<string>(),
                    },
                    trace = new
                    {
                        trace_id = session.TraceId,
                        started_at = session.StartedAtUtc.ToString("o"),
                        is_active = false,
                        tags = session.Tags,
                        entries = session.Entries,
                    }
                }
            );
        }
    }

    [McpForUnityTool("subscribe_editor_events", AutoRegister = false)]
    public static class SubscribeEditorEvents
    {
        public static object HandleCommand(JObject @params)
        {
            JToken eventTypesToken = LiveV2V3ToolCommon.GetParam(@params, "eventTypes", "event_types");
            List<string> eventTypes = eventTypesToken?.Type == JTokenType.Array
                ? eventTypesToken.ToObject<List<string>>()
                : (eventTypesToken?.ToString() ?? string.Empty).Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries).Select(item => item.Trim()).Where(item => item.Length > 0).ToList();
            string subscriptionId = Guid.NewGuid().ToString();
            int? expirationMinutes = LiveV2V3ToolCommon.GetIntParam(@params, "expirationMinutes", "expiration_minutes");
            DateTimeOffset now = DateTimeOffset.UtcNow;
            LiveV2V3ToolState.Subscriptions[subscriptionId] = new LiveV2V3ToolState.EditorSubscription
            {
                SubscriptionId = subscriptionId,
                EventTypes = eventTypes,
                CreatedAt = now.ToString("o"),
                ExpiresAt = expirationMinutes.HasValue ? now.AddMinutes(expirationMinutes.Value).ToString("o") : null,
                FilterCriteria = LiveV2V3ToolCommon.GetParam(@params, "filterCriteria", "filter_criteria")?.ToObject<Dictionary<string, object>>() ?? new Dictionary<string, object>(),
                BufferEvents = LiveV2V3ToolCommon.GetBoolParam(@params, "bufferEvents", "buffer_events") ?? true,
                IsActive = true,
            };
            return new SuccessResponse("Subscribed to editor events.", new { subscription_id = subscriptionId, event_types = eventTypes, created_at = now.ToString("o"), expires_at = LiveV2V3ToolState.Subscriptions[subscriptionId].ExpiresAt });
        }
    }

    [McpForUnityTool("unsubscribe_editor_events", AutoRegister = false)]
    public static class UnsubscribeEditorEvents
    {
        public static object HandleCommand(JObject @params)
        {
            bool unsubscribeAll = LiveV2V3ToolCommon.GetBoolParam(@params, "unsubscribeAll", "unsubscribe_all") ?? false;
            if (unsubscribeAll)
            {
                int removedCount = LiveV2V3ToolState.Subscriptions.Count;
                LiveV2V3ToolState.Subscriptions.Clear();
                return new SuccessResponse("Unsubscribed from all editor events.", new { unsubscribed_all = true, unsubscribed_count = removedCount });
            }

            string subscriptionId = LiveV2V3ToolCommon.GetStringParam(@params, "subscriptionId", "subscription_id");
            if (string.IsNullOrWhiteSpace(subscriptionId) || !LiveV2V3ToolState.Subscriptions.Remove(subscriptionId))
            {
                return new ErrorResponse("Subscription not found.");
            }

            return new SuccessResponse("Unsubscribed from editor events.", new { subscription_id = subscriptionId });
        }
    }

    [McpForUnityTool("manage_transactions", AutoRegister = false)]
    public static class ManageTransactions
    {
        public static object HandleCommand(JObject @params)
        {
            string action = @params?["action"]?.ToString()?.ToLowerInvariant() ?? "get_transaction_state";
            string transactionId = LiveV2V3ToolCommon.GetStringParam(@params, "transactionId", "transaction_id");

            switch (action)
            {
                case "begin_transaction":
                    string id = Guid.NewGuid().ToString();
                    LiveV2V3ToolState.Transactions[id] = new LiveV2V3ToolState.TransactionSession
                    {
                        TransactionId = id,
                        Name = @params?["name"]?.ToString() ?? "transaction",
                        Status = "pending",
                        CheckpointId = LiveV2V3ToolCommon.GetStringParam(@params, "checkpointId", "checkpoint_id"),
                        CreatedAtUtc = DateTime.UtcNow,
                    };
                    return new SuccessResponse("Started transaction.", new { transaction_id = id, name = LiveV2V3ToolState.Transactions[id].Name, status = "pending", checkpoint_id = LiveV2V3ToolState.Transactions[id].CheckpointId });
                case "append_action":
                    if (!LiveV2V3ToolState.Transactions.TryGetValue(transactionId, out LiveV2V3ToolState.TransactionSession session))
                    {
                        return new ErrorResponse("Transaction not found.");
                    }
                    Dictionary<string, object> change = new Dictionary<string, object>
                    {
                        ["change_type"] = LiveV2V3ToolCommon.GetStringParam(@params, "changeType", "change_type"),
                        ["asset_path"] = LiveV2V3ToolCommon.GetStringParam(@params, "assetPath", "asset_path"),
                        ["description"] = @params?["description"]?.ToString(),
                        ["before_hash"] = LiveV2V3ToolCommon.GetStringParam(@params, "beforeHash", "before_hash"),
                        ["after_hash"] = LiveV2V3ToolCommon.GetStringParam(@params, "afterHash", "after_hash"),
                        ["can_undo"] = LiveV2V3ToolCommon.GetBoolParam(@params, "canUndo", "can_undo") ?? true,
                        ["action_params"] = LiveV2V3ToolCommon.GetParam(@params, "actionParams", "action_params")?.ToObject<Dictionary<string, object>>() ?? new Dictionary<string, object>(),
                    };
                    session.Changes.Add(change);
                    return new SuccessResponse("Appended transaction action.", new { transaction_id = transactionId, change });
                case "preview_transaction":
                case "get_transaction_state":
                    if (!LiveV2V3ToolState.Transactions.TryGetValue(transactionId, out session))
                    {
                        return new ErrorResponse("Transaction not found.");
                    }
                    return new SuccessResponse("Retrieved transaction state.", new { transaction_id = transactionId, name = session.Name, status = session.Status, changes = session.Changes, created_at = session.CreatedAtUtc.ToString("o"), completed_at = session.CompletedAtUtc?.ToString("o") });
                case "list_transactions":
                    return new SuccessResponse("Listed transactions.", new { transactions = LiveV2V3ToolState.Transactions.Values.Select(txn => new { transaction_id = txn.TransactionId, name = txn.Name, status = txn.Status, change_count = txn.Changes.Count, created_at = txn.CreatedAtUtc.ToString("o") }).ToList() });
                case "commit_transaction":
                    if (!LiveV2V3ToolState.Transactions.TryGetValue(transactionId, out session))
                    {
                        return new ErrorResponse("Transaction not found.");
                    }
                    session.Status = "committed";
                    session.CompletedAtUtc = DateTime.UtcNow;
                    return new SuccessResponse("Committed transaction.", new { transaction_id = transactionId, status = session.Status, summary = new { total_changes = session.Changes.Count } });
                case "rollback_transaction":
                    if (!LiveV2V3ToolState.Transactions.TryGetValue(transactionId, out session))
                    {
                        return new ErrorResponse("Transaction not found.");
                    }
                    session.Status = "rolled_back";
                    session.CompletedAtUtc = DateTime.UtcNow;
                    return new SuccessResponse("Rolled back transaction.", new { transaction_id = transactionId, status = session.Status, summary = new { total_changes = session.Changes.Count } });
                default:
                    return new ErrorResponse("Unknown action for manage_transactions.");
            }
        }
    }

    [McpForUnityTool("preview_changes", AutoRegister = false)]
    public static class PreviewChanges
    {
        public static object HandleCommand(JObject @params)
        {
            string transactionId = LiveV2V3ToolCommon.GetStringParam(@params, "transactionId", "transaction_id");
            if (string.IsNullOrWhiteSpace(transactionId) || !LiveV2V3ToolState.Transactions.TryGetValue(transactionId, out LiveV2V3ToolState.TransactionSession session))
            {
                return new ErrorResponse("Transaction not found.");
            }

            bool includeAnalysis = LiveV2V3ToolCommon.GetBoolParam(@params, "includeAnalysis", "include_analysis") ?? true;
            bool detectConflicts = LiveV2V3ToolCommon.GetBoolParam(@params, "detectConflicts", "detect_conflicts") ?? true;

            List<Dictionary<string, object>> created = new List<Dictionary<string, object>>();
            List<Dictionary<string, object>> modified = new List<Dictionary<string, object>>();
            List<Dictionary<string, object>> deleted = new List<Dictionary<string, object>>();
            List<Dictionary<string, object>> moved = new List<Dictionary<string, object>>();
            List<Dictionary<string, object>> failed = new List<Dictionary<string, object>>();

            foreach (Dictionary<string, object> change in session.Changes)
            {
                string changeType = change.TryGetValue("change_type", out object changeTypeValue) ? changeTypeValue?.ToString() : string.Empty;
                switch (changeType)
                {
                    case "created":
                        created.Add(change);
                        break;
                    case "deleted":
                        deleted.Add(change);
                        break;
                    case "moved":
                        moved.Add(change);
                        break;
                    case "failed":
                        failed.Add(change);
                        break;
                    default:
                        modified.Add(change);
                        break;
                }
            }

            List<Dictionary<string, object>> analysis = new List<Dictionary<string, object>>();
            if (includeAnalysis)
            {
                foreach (Dictionary<string, object> change in session.Changes)
                {
                    string changeType = change.TryGetValue("change_type", out object changeTypeValue) ? changeTypeValue?.ToString() : "modified";
                    bool canUndo = !change.TryGetValue("can_undo", out object canUndoValue) || Convert.ToBoolean(canUndoValue);
                    string severity = changeType == "deleted" ? "high" : changeType == "failed" ? "critical" : changeType == "modified" ? "medium" : "low";
                    List<string> warnings = new List<string>();
                    if (!canUndo)
                    {
                        warnings.Add("This change cannot be rolled back");
                    }
                    if (changeType == "deleted")
                    {
                        warnings.Add("Deletion cannot be undone without checkpoint");
                    }

                    analysis.Add(new Dictionary<string, object>
                    {
                        ["asset_path"] = change.TryGetValue("asset_path", out object assetPathValue) ? assetPathValue : null,
                        ["change_type"] = changeType,
                        ["description"] = change.TryGetValue("description", out object descriptionValue) ? descriptionValue : null,
                        ["can_undo"] = canUndo,
                        ["impact"] = new Dictionary<string, object>
                        {
                            ["severity"] = severity,
                            ["warnings"] = warnings,
                            ["affected_dependencies"] = new List<object>(),
                        }
                    });
                }
            }

            List<Dictionary<string, object>> conflicts = new List<Dictionary<string, object>>();
            if (detectConflicts)
            {
                HashSet<string> paths = new HashSet<string>(session.Changes.Select(change => change.TryGetValue("asset_path", out object assetPathValue) ? assetPathValue?.ToString() : null).Where(path => !string.IsNullOrWhiteSpace(path)), StringComparer.OrdinalIgnoreCase);
                foreach (LiveV2V3ToolState.TransactionSession other in LiveV2V3ToolState.Transactions.Values)
                {
                    if (other.TransactionId == session.TransactionId || !string.Equals(other.Status, "pending", StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    foreach (Dictionary<string, object> otherChange in other.Changes)
                    {
                        string otherPath = otherChange.TryGetValue("asset_path", out object assetPathValue) ? assetPathValue?.ToString() : null;
                        if (string.IsNullOrWhiteSpace(otherPath) || !paths.Contains(otherPath))
                        {
                            continue;
                        }

                        conflicts.Add(new Dictionary<string, object>
                        {
                            ["type"] = "concurrent_modification",
                            ["asset_path"] = otherPath,
                            ["other_transaction_id"] = other.TransactionId,
                            ["other_transaction_name"] = other.Name,
                            ["other_change_type"] = otherChange.TryGetValue("change_type", out object otherChangeType) ? otherChangeType : null,
                            ["resolution"] = "commit one transaction before the other",
                        });
                    }
                }
            }

            return new SuccessResponse(
                "Previewed pending transaction changes.",
                new
                {
                    transaction_id = session.TransactionId,
                    name = session.Name,
                    status = session.Status,
                    started_at = session.CreatedAtUtc.ToString("o"),
                    checkpoint_id = session.CheckpointId,
                    summary = new
                    {
                        total_changes = session.Changes.Count,
                        created_count = created.Count,
                        modified_count = modified.Count,
                        deleted_count = deleted.Count,
                        moved_count = moved.Count,
                        failed_count = failed.Count,
                    },
                    changes_by_category = new
                    {
                        created,
                        modified,
                        deleted,
                        moved,
                        failed,
                    },
                    detailed_analysis = includeAnalysis ? analysis : null,
                    conflicts,
                    has_conflicts = conflicts.Count > 0,
                }
            );
        }
    }

    [McpForUnityTool("diff_scene", AutoRegister = false)]
    public static class DiffScene
    {
        private static Dictionary<string, object> SnapshotScene(Scene scene)
        {
            GameObject[] roots = scene.IsValid() && scene.isLoaded ? scene.GetRootGameObjects() : Array.Empty<GameObject>();
            List<Dictionary<string, object>> rootObjects = roots
                .Select(root => new Dictionary<string, object>
                {
                    ["name"] = root.name,
                    ["active"] = root.activeSelf,
                    ["path"] = root.name,
                    ["child_count"] = root.transform.childCount,
                })
                .ToList();

            return new Dictionary<string, object>
            {
                ["path"] = scene.path,
                ["name"] = scene.name,
                ["is_dirty"] = scene.isDirty,
                ["root_count"] = roots.Length,
                ["root_objects"] = rootObjects,
            };
        }

        private static Scene ResolveScene(string identifier)
        {
            if (string.IsNullOrWhiteSpace(identifier))
            {
                return default;
            }

            Scene byPath = SceneManager.GetSceneByPath(identifier);
            if (byPath.IsValid())
            {
                return byPath;
            }

            Scene byName = SceneManager.GetSceneByName(identifier);
            if (byName.IsValid())
            {
                return byName;
            }

            return default;
        }

        public static object HandleCommand(JObject @params)
        {
            string compareMode = LiveV2V3ToolCommon.GetStringParam(@params, "compareMode", "compare_mode") ?? "active_vs_saved";
            compareMode = compareMode.ToLowerInvariant();

            if (compareMode == "active_vs_saved")
            {
                Scene activeScene = EditorSceneManager.GetActiveScene();
                if (!activeScene.IsValid())
                {
                    return new ErrorResponse("No active scene available.");
                }

                Dictionary<string, object> source = SnapshotScene(activeScene);
                List<object> changes = new List<object>();
                if (activeScene.isDirty)
                {
                    changes.Add(new
                    {
                        path = activeScene.path,
                        change_type = "modified",
                        component_changes = new object[0],
                        property_changes = new[]
                        {
                            new { property = "scene.is_dirty", old_value = false, new_value = true, value_type = "bool" }
                        },
                        details = new
                        {
                            note = "Active scene has unsaved changes. Live bridge currently reports scene-dirty state instead of a full current-vs-disk structural diff.",
                            root_count = source["root_count"],
                        }
                    });
                }

                return new SuccessResponse(
                    activeScene.isDirty ? "Computed active scene diff against saved state." : "Active scene matches saved state.",
                    new
                    {
                        diff_id = $"diff_{Guid.NewGuid():N}".Substring(0, 17),
                        compare_mode = compareMode,
                        source,
                        target = new { path = activeScene.path, name = activeScene.name, is_saved_state = true },
                        summary = new
                        {
                            total_changes = changes.Count,
                            added = 0,
                            removed = 0,
                            modified = changes.Count,
                            comparison_limited = true,
                        },
                        changes,
                    }
                );
            }

            if (compareMode == "two_scenes")
            {
                string sourceSceneId = LiveV2V3ToolCommon.GetStringParam(@params, "sourceScene", "source_scene");
                string targetSceneId = LiveV2V3ToolCommon.GetStringParam(@params, "targetScene", "target_scene");
                Scene sourceScene = ResolveScene(sourceSceneId);
                Scene targetScene = ResolveScene(targetSceneId);

                if (!sourceScene.IsValid() || !targetScene.IsValid())
                {
                    return new ErrorResponse("Both source and target scenes must be loaded for two_scenes comparison.");
                }

                Dictionary<string, object> source = SnapshotScene(sourceScene);
                Dictionary<string, object> target = SnapshotScene(targetScene);
                HashSet<string> sourceRoots = new HashSet<string>(((List<Dictionary<string, object>>)source["root_objects"]).Select(item => item["name"].ToString()), StringComparer.OrdinalIgnoreCase);
                HashSet<string> targetRoots = new HashSet<string>(((List<Dictionary<string, object>>)target["root_objects"]).Select(item => item["name"].ToString()), StringComparer.OrdinalIgnoreCase);

                List<object> changes = new List<object>();
                foreach (string added in targetRoots.Except(sourceRoots, StringComparer.OrdinalIgnoreCase))
                {
                    changes.Add(new { path = added, change_type = "added", component_changes = new object[0], property_changes = new object[0] });
                }
                foreach (string removed in sourceRoots.Except(targetRoots, StringComparer.OrdinalIgnoreCase))
                {
                    changes.Add(new { path = removed, change_type = "removed", component_changes = new object[0], property_changes = new object[0] });
                }

                return new SuccessResponse(
                    "Computed scene diff.",
                    new
                    {
                        diff_id = $"diff_{Guid.NewGuid():N}".Substring(0, 17),
                        compare_mode = compareMode,
                        source,
                        target,
                        summary = new
                        {
                            total_changes = changes.Count,
                            added = changes.Count(change => change.GetType().GetProperty("change_type")?.GetValue(change)?.ToString() == "added"),
                            removed = changes.Count(change => change.GetType().GetProperty("change_type")?.GetValue(change)?.ToString() == "removed"),
                            modified = 0,
                            comparison_limited = true,
                        },
                        changes,
                    }
                );
            }

            return new ErrorResponse("diff_scene currently supports compare_mode 'active_vs_saved' and 'two_scenes' in the live Unity bridge.");
        }
    }

    [McpForUnityTool("run_playbook", AutoRegister = false)]
    public static class RunPlaybook
    {
        public static object HandleCommand(JObject @params)
        {
            string playbookId = @params?["playbookId"]?.ToString() ?? @params?["playbook_id"]?.ToString();
            bool dryRun = @params?["dryRun"]?.Value<bool?>() ?? @params?["dry_run"]?.Value<bool?>() ?? false;
            bool stopOnError = @params?["stopOnError"]?.Value<bool?>() ?? @params?["stop_on_error"]?.Value<bool?>() ?? true;
            JObject context = @params?["context"] as JObject;
            JObject[] steps = context?["steps"]?.ToObject<JObject[]>();

            if (string.IsNullOrWhiteSpace(playbookId))
            {
                return new ErrorResponse("'playbookId' is required.");
            }

            if (dryRun)
            {
                List<object> previewSteps = steps != null
                    ? steps.Select((step, index) => (object)new { step = index + 1, tool = step["tool"]?.ToString(), action = step["action"]?.ToString() }).ToList()
                    : new List<object>();
                return new SuccessResponse("Playbook dry run complete.", new { playbook_name = playbookId, steps_preview = previewSteps });
            }

            List<object> results = new List<object>();
            if (steps != null)
            {
                foreach (JObject step in steps)
                {
                    string tool = step["tool"]?.ToString();
                    JObject stepParams = step["params"] as JObject ?? new JObject();
                    if (step["action"] != null && stepParams["action"] == null)
                    {
                        stepParams["action"] = step["action"];
                    }

                    object response;
                    try
                    {
                        response = CommandRegistry.InvokeCommandAsync(tool, stepParams).GetAwaiter().GetResult();
                    }
                    catch (Exception ex)
                    {
                        response = new ErrorResponse(ex.Message);
                    }

                    results.Add(new { tool, success = !(response is ErrorResponse), response });
                    if (stopOnError && response is ErrorResponse)
                    {
                        break;
                    }
                }
            }

            int failed = results.Count(result => ((dynamic)result).success == false);
            return new SuccessResponse("Playbook execution complete.", new { playbook_name = playbookId, executed_steps = results.Count, failed_steps = failed, results });
        }
    }

    [McpForUnityTool("run_benchmark", AutoRegister = false)]
    public static class RunBenchmark
    {
        public static async Task<object> HandleCommand(JObject @params)
        {
            string benchmarkName = @params?["benchmarkName"]?.ToString() ?? @params?["benchmark_name"]?.ToString() ?? "benchmark";
            int iterations = Math.Max(1, @params?["iterations"]?.Value<int?>() ?? 10);
            int warmupIterations = Math.Max(0, @params?["warmupIterations"]?.Value<int?>() ?? @params?["warmup_iterations"]?.Value<int?>() ?? 0);
            JArray toolSequence = @params?["toolSequence"] as JArray ?? @params?["tool_sequence"] as JArray;
            if ((toolSequence == null || toolSequence.Count == 0) && @params?["toolName"] != null)
            {
                toolSequence = new JArray
                {
                    new JObject
                    {
                        ["tool"] = @params?["toolName"],
                        ["params"] = @params?["params"] as JObject ?? new JObject(),
                    }
                };
            }
            if ((toolSequence == null || toolSequence.Count == 0) && @params?["tool_name"] != null)
            {
                toolSequence = new JArray
                {
                    new JObject
                    {
                        ["tool"] = @params?["tool_name"],
                        ["params"] = @params?["params"] as JObject ?? new JObject(),
                    }
                };
            }
            if (toolSequence == null || toolSequence.Count == 0)
            {
                return new ErrorResponse("tool_sequence must contain at least one tool invocation.");
            }

            for (int i = 0; i < warmupIterations; i++)
            {
                await Task.Delay(1);
            }

            string runId = $"bm_{Guid.NewGuid():N}".Substring(0, 11);
            LiveV2V3ToolState.BenchmarkRun run = new LiveV2V3ToolState.BenchmarkRun
            {
                RunId = runId,
                BenchmarkName = benchmarkName,
                StartedAtUtc = DateTime.UtcNow,
            };

            for (int iteration = 0; iteration < iterations; iteration++)
            {
                Stopwatch stopwatch = Stopwatch.StartNew();
                bool success = true;
                string error = null;

                foreach (JObject toolSpec in toolSequence.OfType<JObject>())
                {
                    string tool = toolSpec["tool"]?.ToString();
                    JObject toolParams = toolSpec["params"] as JObject ?? new JObject();
                    try
                    {
                        await CommandRegistry.InvokeCommandAsync(tool, toolParams);
                    }
                    catch (Exception ex)
                    {
                        success = false;
                        error = ex.Message;
                        break;
                    }
                }

                stopwatch.Stop();
                run.Results.Add(new Dictionary<string, object>
                {
                    ["iteration"] = iteration + 1,
                    ["latency_ms"] = Math.Round(stopwatch.Elapsed.TotalMilliseconds, 3),
                    ["success"] = success,
                    ["error"] = error,
                });
            }

            run.CompletedAtUtc = DateTime.UtcNow;
            LiveV2V3ToolState.Benchmarks[runId] = run;
            return new SuccessResponse(
                "Benchmark execution complete.",
                new
                {
                    run_id = runId,
                    benchmark_name = benchmarkName,
                    iterations,
                    summary = new
                    {
                        total_requests = run.Results.Count,
                        success_count = run.Results.Count(result => (bool)result["success"]),
                        error_count = run.Results.Count(result => !(bool)result["success"]),
                        avg_latency_ms = Math.Round(run.Results.Average(result => Convert.ToDouble(result["latency_ms"])), 3),
                    },
                    results = run.Results,
                }
            );
        }
    }
}