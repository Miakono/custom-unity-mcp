using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.IronAndSpores
{
    /// <summary>
    /// Read-only prefab audit for quick asset integrity checks.
    /// Reports missing scripts, traversal failures, and summary counts for a folder scope.
    /// </summary>
    [McpForUnityTool(
        "audit_prefab_integrity",
        Description = "Audit prefab assets under a folder for missing scripts, variants, and load failures.",
        Group = "testing"
    )]
    public static class AuditPrefabIntegrity
    {
        public sealed class Parameters
        {
            [ToolParameter("Folder to scan, usually under Assets/.", Required = false, DefaultValue = "Assets")]
            public string RootFolder { get; set; }

            [ToolParameter("Maximum number of prefabs to scan in one call.", Required = false, DefaultValue = "200")]
            public int MaxPrefabs { get; set; }

            [ToolParameter("Maximum number of issue samples to include.", Required = false, DefaultValue = "20")]
            public int MaxIssues { get; set; }

            [ToolParameter("Whether to include prefab variants.", Required = false, DefaultValue = "true")]
            public bool IncludeVariants { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            try
            {
                var p = new ToolParams(@params ?? new JObject());
                string rootFolder = p.Get("root_folder", "Assets") ?? "Assets";
                int maxPrefabs = Math.Max(1, Math.Min(1000, p.GetInt("max_prefabs", 200) ?? 200));
                int maxIssues = Math.Max(1, Math.Min(100, p.GetInt("max_issues", 20) ?? 20));
                bool includeVariants = p.GetBool("include_variants", true);

                if (!AssetDatabase.IsValidFolder(rootFolder))
                {
                    return new ErrorResponse($"Invalid root folder '{rootFolder}'. Expected a folder under Assets/.");
                }

                string[] guids = AssetDatabase.FindAssets("t:Prefab", new[] { rootFolder });
                var prefabPaths = guids
                    .Select(AssetDatabase.GUIDToAssetPath)
                    .Where(path => !string.IsNullOrWhiteSpace(path))
                    .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                    .Take(maxPrefabs)
                    .ToList();

                int totalMissingScripts = 0;
                int prefabsWithIssues = 0;
                int variantCount = 0;
                var issueSamples = new List<object>();

                foreach (string prefabPath in prefabPaths)
                {
                    try
                    {
                        var prefabAsset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                        PrefabAssetType assetType = PrefabUtility.GetPrefabAssetType(prefabAsset);
                        bool isVariant = assetType == PrefabAssetType.Variant;
                        if (isVariant)
                        {
                            variantCount++;
                        }

                        if (!includeVariants && isVariant)
                        {
                            continue;
                        }

                        GameObject prefabContents = null;
                        try
                        {
                            prefabContents = PrefabUtility.LoadPrefabContents(prefabPath);
                            var audit = AuditPrefab(prefabContents);

                            if (audit.MissingScripts > 0)
                            {
                                prefabsWithIssues++;
                                totalMissingScripts += audit.MissingScripts;
                            }

                            if (audit.MissingScripts > 0 && issueSamples.Count < maxIssues)
                            {
                                issueSamples.Add(new
                                {
                                    path = prefabPath,
                                    rootName = prefabContents.name,
                                    missingScripts = audit.MissingScripts,
                                    gameObjectCount = audit.GameObjectCount,
                                    componentCount = audit.ComponentCount,
                                    isVariant
                                });
                            }
                        }
                        finally
                        {
                            if (prefabContents != null)
                            {
                                PrefabUtility.UnloadPrefabContents(prefabContents);
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        prefabsWithIssues++;
                        if (issueSamples.Count < maxIssues)
                        {
                            issueSamples.Add(new
                            {
                                path = prefabPath,
                                error = ex.Message,
                                kind = "load_failure"
                            });
                        }
                    }
                }

                var scannedCount = includeVariants
                    ? prefabPaths.Count
                    : prefabPaths.Count(path =>
                    {
                        var prefabAsset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                        return PrefabUtility.GetPrefabAssetType(prefabAsset) != PrefabAssetType.Variant;
                    });

                var result = new
                {
                    rootFolder,
                    includeVariants,
                    summary = new
                    {
                        discoveredPrefabs = guids.Length,
                        scannedPrefabs = scannedCount,
                        scanLimit = maxPrefabs,
                        variantCount,
                        prefabsWithIssues,
                        totalMissingScripts
                    },
                    issueSamples,
                    recommendation = BuildRecommendation(totalMissingScripts, prefabsWithIssues)
                };

                return new SuccessResponse("Prefab integrity audit completed.", result);
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Prefab integrity audit failed: {e.Message}");
            }
        }

        private static PrefabAuditReport AuditPrefab(GameObject prefabRoot)
        {
            var report = new PrefabAuditReport();
            Traverse(prefabRoot.transform, transform =>
            {
                var go = transform.gameObject;
                report.GameObjectCount++;
                var components = go.GetComponents<Component>();
                int missingScripts = components.Count(component => component == null);
                report.MissingScripts += missingScripts;
                report.ComponentCount += components.Length - missingScripts;
            });
            return report;
        }

        private static void Traverse(Transform root, Action<Transform> visitor)
        {
            if (root == null)
            {
                return;
            }

            visitor(root);
            for (int i = 0; i < root.childCount; i++)
            {
                Traverse(root.GetChild(i), visitor);
            }
        }

        private static string BuildRecommendation(int totalMissingScripts, int prefabsWithIssues)
        {
            if (totalMissingScripts > 0)
            {
                return "Repair prefabs with missing scripts before bulk prefab or scene mutations.";
            }

            if (prefabsWithIssues > 0)
            {
                return "Some prefabs failed to load cleanly. Inspect the issue samples before continuing.";
            }

            return "Scanned prefabs look healthy for follow-up tooling.";
        }

        private sealed class PrefabAuditReport
        {
            public int GameObjectCount { get; set; }
            public int ComponentCount { get; set; }
            public int MissingScripts { get; set; }
        }
    }
}
