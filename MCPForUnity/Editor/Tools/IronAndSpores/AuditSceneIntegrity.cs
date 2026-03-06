using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace MCPForUnity.Editor.Tools.IronAndSpores
{
    /// <summary>
    /// Read-only scene audit for fast agent verification.
    /// Reports missing scripts, dirty scenes, object counts, and sample issue paths.
    /// </summary>
    [McpForUnityTool(
        "audit_scene_integrity",
        Description = "Audit loaded scene integrity: missing scripts, dirty scenes, inactive object counts, and issue samples.",
        Group = "testing"
    )]
    public static class AuditSceneIntegrity
    {
        public sealed class Parameters
        {
            [ToolParameter("Scope to audit: 'active' or 'loaded'.", Required = false, DefaultValue = "loaded")]
            public string Scope { get; set; }

            [ToolParameter("Whether to include inactive objects in traversal.", Required = false, DefaultValue = "true")]
            public bool IncludeInactive { get; set; }

            [ToolParameter("Maximum number of issue samples to include.", Required = false, DefaultValue = "20")]
            public int MaxIssues { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            try
            {
                var p = new ToolParams(@params ?? new JObject());
                string scope = (p.Get("scope", "loaded") ?? "loaded").Trim().ToLowerInvariant();
                bool includeInactive = p.GetBool("include_inactive", true);
                int maxIssues = Math.Max(1, Math.Min(100, p.GetInt("max_issues", 20) ?? 20));

                List<Scene> scenes = ResolveScenes(scope);
                var sceneReports = new List<object>();
                var issues = new List<object>();

                int totalGameObjects = 0;
                int totalInactive = 0;
                int totalMissingScripts = 0;
                int totalComponents = 0;
                int dirtyScenes = 0;

                foreach (var scene in scenes)
                {
                    if (!scene.IsValid() || !scene.isLoaded)
                    {
                        continue;
                    }

                    var report = AuditScene(scene, includeInactive, maxIssues - issues.Count);
                    totalGameObjects += report.TotalGameObjects;
                    totalInactive += report.InactiveGameObjects;
                    totalMissingScripts += report.MissingScripts;
                    totalComponents += report.ComponentCount;
                    if (report.IsDirty)
                    {
                        dirtyScenes++;
                    }

                    issues.AddRange(report.IssueSamples);
                    sceneReports.Add(new
                    {
                        name = report.Name,
                        path = report.Path,
                        isDirty = report.IsDirty,
                        rootObjectCount = report.RootObjectCount,
                        gameObjectCount = report.TotalGameObjects,
                        inactiveGameObjectCount = report.InactiveGameObjects,
                        componentCount = report.ComponentCount,
                        missingScripts = report.MissingScripts
                    });
                }

                var result = new
                {
                    scope,
                    includeInactive,
                    summary = new
                    {
                        sceneCount = sceneReports.Count,
                        dirtySceneCount = dirtyScenes,
                        totalGameObjects,
                        totalInactiveGameObjects = totalInactive,
                        totalComponents,
                        totalMissingScripts = totalMissingScripts,
                        isCompiling = EditorApplication.isCompiling,
                        isUpdating = EditorApplication.isUpdating,
                        isPlayingOrWillChangePlaymode = EditorApplication.isPlayingOrWillChangePlaymode
                    },
                    scenes = sceneReports,
                    issueSamples = issues.Take(maxIssues).ToList(),
                    recommendation = BuildRecommendation(totalMissingScripts, dirtyScenes)
                };

                return new SuccessResponse("Scene integrity audit completed.", result);
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Scene integrity audit failed: {e.Message}");
            }
        }

        private static List<Scene> ResolveScenes(string scope)
        {
            if (scope == "active")
            {
                return new List<Scene> { EditorSceneManager.GetActiveScene() };
            }

            var scenes = new List<Scene>();
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                scenes.Add(SceneManager.GetSceneAt(i));
            }
            return scenes;
        }

        private static SceneAuditReport AuditScene(Scene scene, bool includeInactive, int remainingIssueSlots)
        {
            var report = new SceneAuditReport
            {
                Name = scene.name,
                Path = scene.path,
                IsDirty = scene.isDirty
            };

            foreach (var root in scene.GetRootGameObjects())
            {
                report.RootObjectCount++;
                Traverse(root.transform, includeInactive, transform =>
                {
                    var go = transform.gameObject;
                    report.TotalGameObjects++;
                    if (!go.activeInHierarchy)
                    {
                        report.InactiveGameObjects++;
                    }

                    var components = go.GetComponents<Component>();
                    int missingScripts = components.Count(component => component == null);
                    report.MissingScripts += missingScripts;
                    report.ComponentCount += components.Length - missingScripts;

                    if (missingScripts > 0 && report.IssueSamples.Count < remainingIssueSlots)
                    {
                        report.IssueSamples.Add(new
                        {
                            scene = scene.name,
                            path = BuildPath(go.transform),
                            missingScripts,
                            activeSelf = go.activeSelf,
                            activeInHierarchy = go.activeInHierarchy
                        });
                    }
                });
            }

            return report;
        }

        private static void Traverse(Transform root, bool includeInactive, Action<Transform> visitor)
        {
            if (root == null)
            {
                return;
            }

            if (includeInactive || root.gameObject.activeInHierarchy)
            {
                visitor(root);
            }

            for (int i = 0; i < root.childCount; i++)
            {
                Traverse(root.GetChild(i), includeInactive, visitor);
            }
        }

        private static string BuildPath(Transform transform)
        {
            if (transform == null)
            {
                return string.Empty;
            }

            var segments = new Stack<string>();
            Transform current = transform;
            while (current != null)
            {
                segments.Push(current.name);
                current = current.parent;
            }

            return string.Join("/", segments);
        }

        private static string BuildRecommendation(int missingScripts, int dirtyScenes)
        {
            if (EditorApplication.isCompiling)
            {
                return "Unity is compiling. Wait for compilation to finish before mutating scenes.";
            }

            if (EditorApplication.isUpdating)
            {
                return "Unity is importing assets. Retry when the editor is idle.";
            }

            if (missingScripts > 0)
            {
                return "Resolve missing scripts before broad scene edits or test runs.";
            }

            if (dirtyScenes > 0)
            {
                return "There are unsaved scene changes. Save or checkpoint before risky mutations.";
            }

            return "Loaded scenes look healthy for additional tooling.";
        }

        private sealed class SceneAuditReport
        {
            public string Name { get; set; }
            public string Path { get; set; }
            public bool IsDirty { get; set; }
            public int RootObjectCount { get; set; }
            public int TotalGameObjects { get; set; }
            public int InactiveGameObjects { get; set; }
            public int ComponentCount { get; set; }
            public int MissingScripts { get; set; }
            public List<object> IssueSamples { get; } = new();
        }
    }
}
