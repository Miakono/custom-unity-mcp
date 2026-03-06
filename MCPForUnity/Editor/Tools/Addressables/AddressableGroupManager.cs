#if UNITY_ADDRESSABLES
using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.AddressableAssets;
using UnityEditor.AddressableAssets.Settings;
using UnityEditor.AddressableAssets.Settings.GroupSchemas;
using UnityEngine;
using MCPForUnity.Editor.Helpers;

namespace MCPForUnity.Editor.Tools.Addressables
{
    /// <summary>
    /// Manages Addressable Asset Groups in Unity.
    /// </summary>
    public static class AddressableGroupManager
    {
        /// <summary>
        /// Gets the AddressableAssetSettings instance.
        /// </summary>
        public static AddressableAssetSettings GetSettings()
        {
            return AddressableAssetSettingsDefaultObject.Settings;
        }

        /// <summary>
        /// Checks if Addressables system is initialized.
        /// </summary>
        public static bool IsAddressablesInitialized()
        {
            return AddressableAssetSettingsDefaultObject.Settings != null;
        }

        /// <summary>
        /// Ensures Addressables is initialized, attempting to create settings if needed.
        /// </summary>
        public static bool EnsureInitialized()
        {
            if (IsAddressablesInitialized())
                return true;

            // Try to find existing settings
            var settings = AddressableAssetSettingsDefaultObject.GetSettings(true);
            return settings != null;
        }

        /// <summary>
        /// Gets all Addressable groups.
        /// </summary>
        public static object GetGroups(int? pageSize = null, int? pageNumber = null)
        {
            if (!EnsureInitialized())
                return new ErrorResponse("Addressables not initialized. Please set up Addressables first.");

            var settings = GetSettings();
            var groups = settings.groups;

            if (groups == null)
                return new SuccessResponse("No groups found.", new { groups = new List<object>() });

            var groupList = new List<object>();

            foreach (var group in groups)
            {
                if (group == null) continue;

                var bundleSchema = group.GetSchema<BundledAssetGroupSchema>();
                var contentUpdateSchema = group.GetSchema<ContentUpdateGroupSchema>();

                groupList.Add(new
                {
                    name = group.Name,
                    guid = group.Guid,
                    assetCount = group.entries.Count,
                    settings = new
                    {
                        bundleNamingMode = bundleSchema?.BundleNaming.ToString(),
                        bundleMode = bundleSchema?.BundleMode.ToString(),
                        compressionMode = bundleSchema?.CompressionMode.ToString(),
                        buildPath = bundleSchema?.BuildPath?.GetValue(settings),
                        loadPath = bundleSchema?.LoadPath?.GetValue(settings),
                    },
                    contentUpdate = contentUpdateSchema != null ? new
                    {
                        staticContent = contentUpdateSchema.StaticContent,
                    } : null,
                });
            }

            // Apply pagination if requested
            var totalGroups = groupList.Count;
            if (pageSize.HasValue && pageNumber.HasValue && pageSize.Value > 0)
            {
                int startIndex = (pageNumber.Value - 1) * pageSize.Value;
                if (startIndex < 0) startIndex = 0;
                if (startIndex >= groupList.Count)
                {
                    groupList = new List<object>();
                }
                else
                {
                    int count = Math.Min(pageSize.Value, groupList.Count - startIndex);
                    groupList = groupList.Skip(startIndex).Take(count).ToList();
                }
            }

            return new SuccessResponse(
                $"Found {totalGroups} group(s).",
                new
                {
                    totalGroups = totalGroups,
                    pageSize = pageSize,
                    pageNumber = pageNumber,
                    groups = groupList,
                }
            );
        }

        /// <summary>
        /// Creates a new Addressable group.
        /// </summary>
        public static object CreateGroup(string groupName, JObject options = null)
        {
            if (string.IsNullOrEmpty(groupName))
                return new ErrorResponse("Group name is required.");

            if (!EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            var settings = GetSettings();

            // Check if group already exists
            var existingGroup = settings.FindGroup(groupName);
            if (existingGroup != null)
                return new ErrorResponse($"Group '{groupName}' already exists.");

            try
            {
                // Create the group
                var defaultSchemas = settings.DefaultGroup?.Schemas ?? new List<AddressableAssetGroupSchema>();
                var group = settings.CreateGroup(groupName, false, false, false, defaultSchemas);

                // Apply optional settings
                if (options != null)
                {
                    var bundleSchema = group.GetSchema<BundledAssetGroupSchema>();
                    if (bundleSchema != null)
                    {
                        // Bundle naming mode
                        var namingMode = options["bundleNamingMode"]?.ToString();
                        if (!string.IsNullOrEmpty(namingMode))
                        {
                            if (Enum.TryParse<BundledAssetGroupSchema.BundleNamingStyle>(
                                namingMode, out var naming))
                            {
                                bundleSchema.BundleNaming = naming;
                            }
                        }

                        // Bundle mode
                        var bundleMode = options["bundleMode"]?.ToString();
                        if (!string.IsNullOrEmpty(bundleMode))
                        {
                            if (Enum.TryParse<BundledAssetGroupSchema.BundlePackingMode>(
                                bundleMode, out var packing))
                            {
                                bundleSchema.BundleMode = packing;
                            }
                        }

                        // Compression mode
                        var compressionMode = options["compressionMode"]?.ToString();
                        if (!string.IsNullOrEmpty(compressionMode))
                        {
                            if (Enum.TryParse<BundledAssetGroupSchema.AssetBundleCompressionType>(
                                compressionMode, out var compression))
                            {
                                bundleSchema.CompressionMode = compression;
                            }
                        }
                    }
                }

                EditorUtility.SetDirty(settings);
                AssetDatabase.SaveAssets();

                return new SuccessResponse(
                    $"Group '{groupName}' created successfully.",
                    new
                    {
                        name = group.Name,
                        guid = group.Guid,
                    }
                );
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Failed to create group: {e.Message}");
            }
        }

        /// <summary>
        /// Deletes an Addressable group.
        /// </summary>
        public static object DeleteGroup(string groupName)
        {
            if (string.IsNullOrEmpty(groupName))
                return new ErrorResponse("Group name is required.");

            if (!EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            var settings = GetSettings();
            var group = settings.FindGroup(groupName);

            if (group == null)
                return new ErrorResponse($"Group '{groupName}' not found.");

            try
            {
                // Get asset count for confirmation message
                int assetCount = group.entries.Count;

                settings.RemoveGroup(group);
                
                EditorUtility.SetDirty(settings);
                AssetDatabase.SaveAssets();

                return new SuccessResponse(
                    $"Group '{groupName}' deleted. {assetCount} asset(s) were removed from Addressables.",
                    new { removedAssets = assetCount }
                );
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Failed to delete group: {e.Message}");
            }
        }

        /// <summary>
        /// Gets assets in a specific group.
        /// </summary>
        public static object GetGroupAssets(string groupName, int? pageSize = null, int? pageNumber = null)
        {
            if (string.IsNullOrEmpty(groupName))
                return new ErrorResponse("Group name is required.");

            if (!EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            var settings = GetSettings();
            var group = settings.FindGroup(groupName);

            if (group == null)
                return new ErrorResponse($"Group '{groupName}' not found.");

            var entries = group.entries;
            var assetList = new List<object>();

            foreach (var entry in entries)
            {
                if (entry == null) continue;

                assetList.Add(new
                {
                    guid = entry.guid,
                    assetPath = entry.AssetPath,
                    address = entry.address,
                    labels = entry.labels.ToList(),
                    isSubAsset = entry.IsSubAsset,
                    targetAsset = entry.TargetAsset != null ? entry.TargetAsset.name : null,
                });
            }

            // Apply pagination
            var totalAssets = assetList.Count;
            if (pageSize.HasValue && pageNumber.HasValue && pageSize.Value > 0)
            {
                int startIndex = (pageNumber.Value - 1) * pageSize.Value;
                if (startIndex < 0) startIndex = 0;
                if (startIndex >= assetList.Count)
                {
                    assetList = new List<object>();
                }
                else
                {
                    int count = Math.Min(pageSize.Value, assetList.Count - startIndex);
                    assetList = assetList.Skip(startIndex).Take(count).ToList();
                }
            }

            return new SuccessResponse(
                $"Group '{groupName}' has {totalAssets} asset(s).",
                new
                {
                    groupName = groupName,
                    groupGuid = group.Guid,
                    totalAssets = totalAssets,
                    pageSize = pageSize,
                    pageNumber = pageNumber,
                    assets = assetList,
                }
            );
        }

        /// <summary>
        /// Gets all Addressable labels.
        /// </summary>
        public static object GetLabels()
        {
            if (!EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            var settings = GetSettings();
            var labelTable = settings.labelTable;

            if (labelTable == null)
                return new SuccessResponse("No labels found.", new { labels = new List<string>() });

            var labels = labelTable.labelNames.ToList();

            return new SuccessResponse(
                $"Found {labels.Count} label(s).",
                new
                {
                    totalLabels = labels.Count,
                    labels = labels,
                }
            );
        }

        /// <summary>
        /// Gets Addressables settings information.
        /// </summary>
        public static object GetSettings(string settingsPath = null)
        {
            if (!EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            var settings = GetSettings();

            var profileSettings = settings.profileSettings;
            var activeProfileId = settings.activeProfileId;
            var activeProfileName = profileSettings.GetProfileNameById(activeProfileId);

            var profileData = new Dictionary<string, object>();
            foreach (var profileId in profileSettings.GetAllProfileIds())
            {
                var profileName = profileSettings.GetProfileNameById(profileId);
                var values = profileSettings.GetAllVariablesById(profileId);
                profileData[profileName] = new
                {
                    id = profileId,
                    isActive = profileId == activeProfileId,
                    values = values,
                };
            }

            return new SuccessResponse(
                "Addressables settings retrieved.",
                new
                {
                    settingsAssetPath = AssetDatabase.GetAssetPath(settings),
                    buildTarget = EditorUserBuildSettings.activeBuildTarget.ToString(),
                    activeProfile = activeProfileName,
                    activeProfileId = activeProfileId,
                    overridePlayerVersion = settings.OverridePlayerVersion,
                    checkForContentUpdateRestrictions = settings.CheckForContentUpdateRestrictionsOption.ToString(),
                    profiles = profileData,
                    groupCount = settings.groups.Count,
                    labelCount = settings.labelTable?.labelNames?.Count ?? 0,
                }
            );
        }
    }
}
#endif
