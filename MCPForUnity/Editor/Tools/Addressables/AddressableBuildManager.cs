#if MCP_ADDRESSABLES_PACKAGE_PRESENT
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.AddressableAssets;
using UnityEditor.AddressableAssets.Build;
using UnityEditor.AddressableAssets.Settings;
using UnityEditor.Build.Pipeline.Utilities;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.Addressables
{
    /// <summary>
    /// Manages Addressable Asset builds in Unity.
    /// </summary>
    public static class AddressableBuildManager
    {
        /// <summary>
        /// Default build script path.
        /// </summary>
        private const string BuildScriptPath = 
            "Assets/AddressableAssetsData/DataBuilders/BuildScriptPackedMode.asset";

        /// <summary>
        /// Platform mappings for Addressables builds.
        /// </summary>
        private static readonly Dictionary<string, BuildTarget> PlatformMapping = 
            new Dictionary<string, BuildTarget>(StringComparer.OrdinalIgnoreCase)
        {
            { "StandaloneWindows", BuildTarget.StandaloneWindows },
            { "StandaloneWindows64", BuildTarget.StandaloneWindows64 },
            { "StandaloneOSX", BuildTarget.StandaloneOSX },
            { "StandaloneLinux64", BuildTarget.StandaloneLinux64 },
            { "iOS", BuildTarget.iOS },
            { "Android", BuildTarget.Android },
            { "WebGL", BuildTarget.WebGL },
            { "PS5", BuildTarget.PS5 },
            { "XboxSeriesX", BuildTarget.GameCoreXboxSeries },
            { "NintendoSwitch", BuildTarget.Switch },
        };

        /// <summary>
        /// Builds Addressables for the specified platform.
        /// </summary>
        public static object Build(
            string platform = null,
            bool dryRun = false,
            bool clean = false,
            string settingsPath = null)
        {
            if (!AddressableGroupManager.EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            var settings = AddressableGroupManager.GetSettings();
            if (settings == null)
                return new ErrorResponse("Could not load Addressables settings.");

            // Determine build target
            BuildTarget buildTarget;
            string platformName;

            if (string.IsNullOrEmpty(platform))
            {
                buildTarget = EditorUserBuildSettings.activeBuildTarget;
                platformName = buildTarget.ToString();
            }
            else if (PlatformMapping.TryGetValue(platform, out var mappedTarget))
            {
                buildTarget = mappedTarget;
                platformName = platform;
            }
            else
            {
                return new ErrorResponse(
                    $"Unknown platform '{platform}'. " +
                    $"Supported platforms: {string.Join(", ", PlatformMapping.Keys)}");
            }

            // Dry run - return what would be built
            if (dryRun)
            {
                return GetDryRunInfo(settings, buildTarget, platformName);
            }

            // Clean build if requested
            if (clean)
            {
                var cleanResult = CleanBuild(settings);
                if (cleanResult is ErrorResponse)
                    return cleanResult;
            }

            try
            {
                // Build Addressables
                AddressableAssetBuildResult result = null;

                // Switch to the target platform if different
                BuildTarget originalTarget = EditorUserBuildSettings.activeBuildTarget;
                bool needsSwitch = originalTarget != buildTarget;

                if (needsSwitch)
                {
                    Debug.Log($"[AddressableBuildManager] Switching build target from {originalTarget} to {buildTarget}");
                    BuildTargetGroup targetGroup = BuildPipeline.GetBuildTargetGroup(buildTarget);
                    EditorUserBuildSettings.SwitchActiveBuildTarget(targetGroup, buildTarget);
                }

                // Perform the build
                var buildScript = GetBuildScript(settings);
                if (buildScript == null)
                    return new ErrorResponse("Could not find Addressables build script.");

                result = InvokeBuildData(buildScript, settings);

                // Build result
                var buildReport = new
                {
                    success = result != null && string.IsNullOrEmpty(result.Error),
                    error = result?.Error,
                    duration = result?.Duration,
                    outputPath = result?.OutputPath,
                    assetBundleBuildResults = result?.m_AssetBundleBuildResults?.Select(r => new
                    {
                        filePath = r.FilePath,
                        assetBundleName = r.AssetBundleName,
                    }).ToList(),
                };

                if (result == null || !string.IsNullOrEmpty(result.Error))
                {
                    return new ErrorResponse(
                        $"Build failed: {result?.Error ?? "Unknown error"}",
                        buildReport);
                }

                // Generate detailed report
                var detailedReport = GenerateBuildReport(result, platformName);

                return new SuccessResponse(
                    $"Addressables build completed for {platformName}.",
                    new
                    {
                        platform = platformName,
                        buildTarget = buildTarget.ToString(),
                        duration = result.Duration,
                        outputPath = result.OutputPath,
                        bundleCount = result.m_AssetBundleBuildResults?.Count ?? 0,
                        buildReport = detailedReport,
                    }
                );
            }
            catch (Exception e)
            {
                Debug.LogError($"[AddressableBuildManager] Build failed: {e}");
                return new ErrorResponse($"Build failed: {e.Message}");
            }
        }

        /// <summary>
        /// Builds Addressables for a specific player platform.
        /// </summary>
        public static object BuildPlayer(
            string platform = null,
            bool dryRun = false,
            bool clean = false)
        {
            // This is essentially the same as Build for Addressables,
            // but explicitly for player builds
            return Build(platform, dryRun, clean);
        }

        /// <summary>
        /// Performs a clean build by clearing the build cache.
        /// </summary>
        public static object CleanBuild(AddressableAssetSettings settings = null)
        {
            if (settings == null)
            {
                if (!AddressableGroupManager.EnsureInitialized())
                    return new ErrorResponse("Addressables not initialized.");
                settings = AddressableGroupManager.GetSettings();
            }

            try
            {
                // Clear the build cache
                string libraryPath = Path.Combine(Application.dataPath, "..", "Library", "com.unity.addressables");
                if (Directory.Exists(libraryPath))
                {
                    Directory.Delete(libraryPath, true);
                }

                // Clear asset bundle cache
                string bundleCachePath = Path.Combine(Application.dataPath, "..", "Library", "AssetBundles");
                if (Directory.Exists(bundleCachePath))
                {
                    Directory.Delete(bundleCachePath, true);
                }

                // Clear build data
                string buildDataPath = Path.Combine(Application.dataPath, "..", "Library", "BuildPlayerData");
                if (Directory.Exists(buildDataPath))
                {
                    Directory.Delete(buildDataPath, true);
                }

                Debug.Log("[AddressableBuildManager] Build cache cleared.");
                return new SuccessResponse("Build cache cleared.");
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[AddressableBuildManager] Failed to clean build cache: {e.Message}");
                // Don't fail the operation, just warn
                return new SuccessResponse("Build cache partially cleared.", new { warning = e.Message });
            }
        }

        /// <summary>
        /// Analyzes build report and dependencies.
        /// </summary>
        public static object Analyze(string reportPath = null)
        {
            if (!AddressableGroupManager.EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            var settings = AddressableGroupManager.GetSettings();

            try
            {
                // Find the latest build report if no path provided
                if (string.IsNullOrEmpty(reportPath))
                {
                    reportPath = FindLatestBuildReport();
                }

                JObject reportData = null;
                if (!string.IsNullOrEmpty(reportPath) && File.Exists(reportPath))
                {
                    var json = File.ReadAllText(reportPath);
                    reportData = JObject.Parse(json);
                }

                // Analyze groups
                var groupsAnalysis = AnalyzeGroups(settings);

                // Analyze build report if available
                var buildAnalysis = reportData != null ? AnalyzeBuildReport(reportData) : null;

                return new SuccessResponse(
                    "Addressables analysis complete.",
                    new
                    {
                        summary = new
                        {
                            totalGroups = settings.groups.Count,
                            totalAssets = settings.groups.Sum(g => g?.entries?.Count ?? 0),
                            totalLabels = settings.labelTable?.labelNames?.Count ?? 0,
                        },
                        groups = groupsAnalysis,
                        buildReport = buildAnalysis,
                        issues = FindPotentialIssues(settings),
                    }
                );
            }
            catch (Exception e)
            {
                Debug.LogError($"[AddressableBuildManager] Analysis failed: {e}");
                return new ErrorResponse($"Analysis failed: {e.Message}");
            }
        }

        /// <summary>
        /// Validates the Addressables configuration.
        /// </summary>
        public static object Validate()
        {
            if (!AddressableGroupManager.EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            var settings = AddressableGroupManager.GetSettings();
            var issues = FindPotentialIssues(settings);
            var hasErrors = issues.Any(i => i.StartsWith("[ERROR]"));

            return new SuccessResponse(
                hasErrors ? "Validation found errors." : "Validation passed.",
                new
                {
                    valid = !hasErrors,
                    issueCount = issues.Count,
                    issues = issues,
                }
            );
        }

        #region Private Helper Methods

        private static UnityEngine.Object GetBuildScript(AddressableAssetSettings settings)
        {
            // Find the default build script
            var buildScript = settings.DataBuilders.Find(
                db => db != null && db.GetType().Name == nameof(BuildScriptPackedMode));
            
            if (buildScript == null)
            {
                // Try to find any build script
                buildScript = settings.DataBuilders.FirstOrDefault(db => db != null);
            }

            return buildScript as UnityEngine.Object;
        }

        private static AddressableAssetBuildResult InvokeBuildData(UnityEngine.Object buildScript, AddressableAssetSettings settings)
        {
            if (buildScript == null)
                return null;

            var type = buildScript.GetType();
            var methods = type
                .GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)
                .Where(m => m.Name == "BuildData" && m.IsGenericMethodDefinition)
                .ToList();

            foreach (var method in methods)
            {
                var parameters = method.GetParameters();
                if (parameters.Length == 0)
                    continue;

                if (!parameters[0].ParameterType.IsAssignableFrom(typeof(AddressableAssetSettings))
                    && !typeof(AddressableAssetSettings).IsAssignableFrom(parameters[0].ParameterType))
                    continue;

                var generic = method.MakeGenericMethod(typeof(AddressableAssetBuildResult));
                object[] args;

                if (parameters.Length == 1)
                {
                    args = new object[] { settings };
                }
                else
                {
                    args = new object[] { settings, AssetDatabase.GetAssetPath(buildScript) };
                }

                var invokeResult = generic.Invoke(buildScript, args);
                if (invokeResult is AddressableAssetBuildResult typedResult)
                    return typedResult;
            }

            throw new MissingMethodException(
                $"Could not find a compatible BuildData<T>(...) method on {type.FullName}.");
        }

        private static object GetDryRunInfo(AddressableAssetSettings settings, BuildTarget target, string platformName)
        {
            var groups = settings.groups;
            var analysis = new List<object>();
            long totalSize = 0;

            foreach (var group in groups)
            {
                if (group == null) continue;

                var entryCount = group.entries.Count;
                if (entryCount == 0) continue;

                // Estimate sizes (simplified)
                long estimatedSize = 0;
                foreach (var entry in group.entries)
                {
                    if (entry.TargetAsset != null)
                    {
                        var path = AssetDatabase.GetAssetPath(entry.TargetAsset);
                        if (!string.IsNullOrEmpty(path))
                        {
                            var fullPath = Path.Combine(Application.dataPath, "..", path);
                            if (File.Exists(fullPath))
                            {
                                var fileInfo = new FileInfo(fullPath);
                                estimatedSize += fileInfo.Length;
                            }
                        }
                    }
                }

                totalSize += estimatedSize;

                analysis.Add(new
                {
                    groupName = group.Name,
                    assetCount = entryCount,
                    estimatedSizeBytes = estimatedSize,
                    estimatedSizeMB = Math.Round(estimatedSize / (1024.0 * 1024.0), 2),
                });
            }

            return new SuccessResponse(
                "Dry run - no changes made.",
                new
                {
                    platform = platformName,
                    buildTarget = target.ToString(),
                    wouldBuildGroups = analysis.Count,
                    totalEstimatedSizeBytes = totalSize,
                    totalEstimatedSizeMB = Math.Round(totalSize / (1024.0 * 1024.0), 2),
                    groups = analysis,
                }
            );
        }

        private static string FindLatestBuildReport()
        {
            var reportsDir = Path.Combine(Application.dataPath, "..", "Library", "com.unity.addressables", 
                "BuildReports");
            
            if (!Directory.Exists(reportsDir))
                return null;

            var reportFiles = Directory.GetFiles(reportsDir, "*.json", SearchOption.TopDirectoryOnly);
            if (reportFiles.Length == 0)
                return null;

            // Return the most recent file
            return reportFiles
                .Select(f => new FileInfo(f))
                .OrderByDescending(f => f.LastWriteTime)
                .First()
                .FullName;
        }

        private static List<object> AnalyzeGroups(AddressableAssetSettings settings)
        {
            var result = new List<object>();

            foreach (var group in settings.groups)
            {
                if (group == null) continue;

                var entryCount = group.entries.Count;
                var labels = new HashSet<string>();
                var addressConflicts = new List<string>();
                var addressSet = new HashSet<string>();

                foreach (var entry in group.entries)
                {
                    // Collect labels
                    foreach (var label in entry.labels)
                        labels.Add(label);

                    // Check for address conflicts
                    if (!addressSet.Add(entry.address))
                    {
                        addressConflicts.Add(entry.address);
                    }
                }

                result.Add(new
                {
                    name = group.Name,
                    assetCount = entryCount,
                    uniqueLabels = labels.ToList(),
                    hasAddressConflicts = addressConflicts.Count > 0,
                    addressConflicts = addressConflicts,
                });
            }

            return result;
        }

        private static object AnalyzeBuildReport(JObject reportData)
        {
            var summary = reportData["summary"];
            var bundles = reportData["bundles"] as JArray;
            var errors = reportData["errors"] as JArray;
            var warnings = reportData["warnings"] as JArray;

            long totalSize = 0;
            var bundleInfos = new List<object>();

            if (bundles != null)
            {
                foreach (var bundle in bundles)
                {
                    var size = bundle["sizeBytes"]?.Value<long>() ?? 0;
                    totalSize += size;

                    bundleInfos.Add(new
                    {
                        name = bundle["name"]?.Value<string>(),
                        sizeBytes = size,
                        sizeFormatted = FormatBytes(size),
                        compression = bundle["compression"]?.Value<string>(),
                    });
                }
            }

            return new
            {
                buildPath = summary?["buildPath"]?.Value<string>(),
                buildTarget = summary?["buildTarget"]?.Value<string>(),
                buildDate = summary?["buildDate"]?.Value<string>(),
                totalBundles = bundles?.Count ?? 0,
                totalSizeBytes = totalSize,
                totalSizeFormatted = FormatBytes(totalSize),
                errorCount = errors?.Count ?? 0,
                warningCount = warnings?.Count ?? 0,
                bundles = bundleInfos,
            };
        }

        private static List<string> FindPotentialIssues(AddressableAssetSettings settings)
        {
            var issues = new List<string>();
            var allAddresses = new Dictionary<string, string>(); // address -> group
            var allGuids = new HashSet<string>();

            foreach (var group in settings.groups)
            {
                if (group == null) continue;

                // Empty group warning
                if (group.entries.Count == 0)
                {
                    issues.Add($"[WARNING] Group '{group.Name}' is empty (no assets)");
                }

                foreach (var entry in group.entries)
                {
                    // Duplicate GUID check
                    if (!allGuids.Add(entry.guid))
                    {
                        issues.Add($"[ERROR] Duplicate GUID '{entry.guid}' in group '{group.Name}'");
                    }

                    // Duplicate address check
                    if (allAddresses.TryGetValue(entry.address, out var existingGroup))
                    {
                        issues.Add($"[ERROR] Duplicate address '{entry.address}' in groups '{existingGroup}' and '{group.Name}'");
                    }
                    else
                    {
                        allAddresses[entry.address] = group.Name;
                    }

                    // Check for missing asset
                    if (entry.TargetAsset == null)
                    {
                        issues.Add($"[WARNING] Asset with GUID '{entry.guid}' (address: '{entry.address}') could not be loaded");
                    }

                    // Check for path-style addresses
                    if (entry.address.StartsWith("Assets/"))
                    {
                        issues.Add($"[INFO] Asset '{entry.address}' uses path as address - consider using a simplified address");
                    }

                    // Check for assets without labels
                    if (entry.labels.Count == 0)
                    {
                        issues.Add($"[INFO] Asset '{entry.address}' has no labels assigned");
                    }
                }
            }

            return issues;
        }

        private static object GenerateBuildReport(AddressableAssetBuildResult result, string platform)
        {
            var buildDate = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            var bundles = new List<object>();

            if (result.m_AssetBundleBuildResults != null)
            {
                foreach (var bundle in result.m_AssetBundleBuildResults)
                {
                    long size = 0;
                    if (File.Exists(bundle.FilePath))
                    {
                        size = new FileInfo(bundle.FilePath).Length;
                    }

                    bundles.Add(new
                    {
                        name = bundle.AssetBundleName,
                        filePath = bundle.FilePath,
                        sizeBytes = size,
                        compression = "LZ4", // Default, actual compression would need deeper inspection
                    });
                }
            }

            return new
            {
                summary = new
                {
                    buildPath = result.OutputPath,
                    buildTarget = platform,
                    buildDate = buildDate,
                    totalBundles = bundles.Count,
                    totalSizeBytes = bundles.Sum(b => (long)((dynamic)b).sizeBytes),
                },
                bundles = bundles,
                errors = string.IsNullOrEmpty(result.Error) ? new List<string>() : new List<string> { result.Error },
                warnings = new List<string>(),
            };
        }

        private static string FormatBytes(long bytes)
        {
            string[] suffixes = { "B", "KB", "MB", "GB", "TB" };
            int counter = 0;
            decimal number = bytes;
            while (Math.Round(number / 1024) >= 1)
            {
                number = number / 1024;
                counter++;
            }
            return string.Format("{0:n1} {1}", number, suffixes[counter]);
        }

        #endregion
    }
}
#endif
