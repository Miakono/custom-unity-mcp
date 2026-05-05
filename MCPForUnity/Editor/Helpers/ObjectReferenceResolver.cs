using System;
using System.Text.RegularExpressions;
using Newtonsoft.Json.Linq;
using UnityEditor;

namespace MCPForUnity.Editor.Helpers
{
    /// <summary>
    /// Shared shorthand resolver for UnityEngine.Object references coming from JSON.
    /// Used by both SerializedPropertyPatcher (apply_scene_patch / apply_prefab_patch /
    /// manage_scriptable_object) and ComponentOps (manage_components / manage_prefabs)
    /// so all surfaces accept the same dialect.
    ///
    /// Accepted forms:
    ///   null / JTokenType.Null                    → Cleared
    ///   JTokenType.Integer                        → instanceID lookup
    ///   { instanceID: int }                       → instanceID lookup
    ///   { guid: string } | { ref: { guid: string } }  → GUID → path → asset
    ///   { path: string } | { ref: { path: string } }  → asset path → asset
    ///   { name: string }                          → scene-name search (only when allowSceneNameFallback)
    ///   "32-hex-char string"                      → guid-shorthand
    ///   "Assets/..." or contains "/"              → path-shorthand
    ///   other string                              → NeedsSceneSearch (when allowSceneNameFallback) or Unrecognized
    /// </summary>
    public static class ObjectReferenceResolver
    {
        public enum ResolveOutcome
        {
            Resolved,           // Asset is non-null and ready to assign
            Cleared,            // Caller should null out the reference
            NotFound,           // Form was recognized but asset/object missing — Error explains
            NeedsSceneSearch,   // Caller should do scene-name lookup with SceneNameHint
            Unrecognized        // Form not recognized — Error lists accepted shapes
        }

        public struct Result
        {
            public ResolveOutcome Outcome;
            public UnityEngine.Object Asset;
            public string ResolveMethod;
            public string Error;
            public string SceneNameHint;
        }

        private static readonly Regex GuidShorthand = new Regex(@"^[0-9a-fA-F]{32}$", RegexOptions.Compiled);

        public static Result Resolve(JToken value, JObject patchObj, bool allowSceneNameFallback)
        {
            // 1. Explicit { ref: { guid|path } } takes priority — SerializedPropertyPatcher dialect.
            var refObj = patchObj?["ref"] as JObject;
            string refGuid = refObj?["guid"]?.ToString();
            string refPath = refObj?["path"]?.ToString();
            if (!string.IsNullOrEmpty(refGuid))
            {
                return ResolveByGuid(refGuid, "ref.guid");
            }
            if (!string.IsNullOrEmpty(refPath))
            {
                return ResolveByPath(refPath, "ref.path");
            }

            // 2. Null / missing value → cleared (no ref object given).
            if (value == null || value.Type == JTokenType.Null)
            {
                return new Result { Outcome = ResolveOutcome.Cleared, ResolveMethod = "cleared" };
            }

            // 3. Bare integer → instanceID lookup.
            if (value.Type == JTokenType.Integer)
            {
                int id = value.Value<int>();
                return ResolveByInstanceId(id, "instanceID");
            }

            // 4. JObject with one of the supported keys.
            if (value is JObject jObj)
            {
                var idTok = jObj["instanceID"] ?? jObj["instance_id"];
                if (idTok != null)
                {
                    int id = ParamCoercion.CoerceInt(idTok, 0);
                    return ResolveByInstanceId(id, "instanceID");
                }

                var guidTok = jObj["guid"];
                if (guidTok != null)
                {
                    return ResolveByGuid(guidTok.ToString(), "guid");
                }

                var pathTok = jObj["path"];
                if (pathTok != null)
                {
                    return ResolveByPath(pathTok.ToString(), "path");
                }

                var nameTok = jObj["name"];
                if (nameTok != null)
                {
                    string nm = nameTok.ToString();
                    if (allowSceneNameFallback)
                    {
                        return new Result
                        {
                            Outcome = ResolveOutcome.NeedsSceneSearch,
                            ResolveMethod = "name",
                            SceneNameHint = nm
                        };
                    }
                    return new Result
                    {
                        Outcome = ResolveOutcome.Unrecognized,
                        Error = $"Object reference {{ name: '{nm}' }} requires a scene context — not allowed for this tool. " +
                                "Use { guid }, { path }, or a 32-char GUID / 'Assets/...' string."
                    };
                }

                return new Result
                {
                    Outcome = ResolveOutcome.Unrecognized,
                    Error = "Object reference object must contain 'instanceID', 'guid', 'path', or 'name'."
                };
            }

            // 5. Bare string — try GUID-shorthand, then path-shorthand, then scene-name.
            if (value.Type == JTokenType.String)
            {
                string s = value.ToString();
                if (GuidShorthand.IsMatch(s))
                {
                    return ResolveByGuid(s, "guid-shorthand");
                }
                if (s.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase) || s.Contains("/"))
                {
                    return ResolveByPath(s, "path-shorthand");
                }
                if (allowSceneNameFallback)
                {
                    return new Result
                    {
                        Outcome = ResolveOutcome.NeedsSceneSearch,
                        ResolveMethod = "scene-name",
                        SceneNameHint = s
                    };
                }
                return new Result
                {
                    Outcome = ResolveOutcome.Unrecognized,
                    Error = $"Could not resolve object reference from string '{s}'. " +
                            "Provide a 32-char GUID, an Assets/-prefixed path, or { guid|path: ... }."
                };
            }

            return new Result
            {
                Outcome = ResolveOutcome.Unrecognized,
                Error = $"Unsupported object reference value type: {value.Type}. " +
                        "Provide null, an instanceID integer, a GUID/path string, or { guid|path|name: ... }."
            };
        }

        private static Result ResolveByGuid(string guid, string method)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            if (string.IsNullOrEmpty(path))
            {
                return new Result
                {
                    Outcome = ResolveOutcome.NotFound,
                    ResolveMethod = method,
                    Error = $"No asset found for GUID '{guid}'."
                };
            }
            var asset = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(path);
            if (asset == null)
            {
                return new Result
                {
                    Outcome = ResolveOutcome.NotFound,
                    ResolveMethod = method,
                    Error = $"GUID '{guid}' resolved to '{path}' but the asset could not be loaded."
                };
            }
            return new Result { Outcome = ResolveOutcome.Resolved, Asset = asset, ResolveMethod = method };
        }

        private static Result ResolveByPath(string rawPath, string method)
        {
            string sanitized = AssetPathUtility.SanitizeAssetPath(rawPath);
            if (string.IsNullOrEmpty(sanitized))
            {
                return new Result
                {
                    Outcome = ResolveOutcome.NotFound,
                    ResolveMethod = method,
                    Error = $"Invalid asset path '{rawPath}' (path traversal sequences are not allowed)."
                };
            }
            var asset = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(sanitized);
            if (asset == null)
            {
                return new Result
                {
                    Outcome = ResolveOutcome.NotFound,
                    ResolveMethod = method,
                    Error = $"No asset found at path '{sanitized}'."
                };
            }
            return new Result { Outcome = ResolveOutcome.Resolved, Asset = asset, ResolveMethod = method };
        }

        private static Result ResolveByInstanceId(int id, string method)
        {
            var resolved = UnityEditorObjectLookup.FindObjectByInstanceId(id);
            if (resolved == null)
            {
                return new Result
                {
                    Outcome = ResolveOutcome.NotFound,
                    ResolveMethod = method,
                    Error = $"No object found with instanceID {id}."
                };
            }
            return new Result { Outcome = ResolveOutcome.Resolved, Asset = resolved, ResolveMethod = method };
        }
    }
}
