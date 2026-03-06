#if UNITY_ADDRESSABLES
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.AddressableAssets;
using UnityEditor.AddressableAssets.Settings;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.Addressables
{
    /// <summary>
    /// Manages Addressable assets (entries, labels, addresses) in Unity.
    /// </summary>
    public static class AddressableAssetManager
    {
        /// <summary>
        /// Adds an asset to Addressables.
        /// </summary>
        public static object AddAsset(
            string assetPath,
            string groupName = null,
            string address = null,
            List<string> labels = null)
        {
            if (string.IsNullOrEmpty(assetPath))
                return new ErrorResponse("Asset path is required.");

            if (!AddressableGroupManager.EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            // Validate asset path
            string fullPath = SanitizeAssetPath(assetPath);
            if (!AssetExists(fullPath))
                return new ErrorResponse($"Asset not found at path: {fullPath}");

            var settings = AddressableGroupManager.GetSettings();

            // Determine target group
            AddressableAssetGroup targetGroup;
            if (!string.IsNullOrEmpty(groupName))
            {
                targetGroup = settings.FindGroup(groupName);
                if (targetGroup == null)
                    return new ErrorResponse($"Group '{groupName}' not found.");
            }
            else
            {
                targetGroup = settings.DefaultGroup;
                groupName = targetGroup.Name;
            }

            // Check if already in Addressables
            var existingEntry = settings.FindAssetEntry(AssetDatabase.AssetPathToGUID(fullPath));
            if (existingEntry != null)
            {
                return new ErrorResponse(
                    $"Asset is already in Addressables (group: '{existingEntry.parentGroup.Name}', " +
                    $"address: '{existingEntry.address}'). Use modify instead.");
            }

            try
            {
                // Get or create entry
                string guid = AssetDatabase.AssetPathToGUID(fullPath);
                var entry = settings.CreateOrMoveEntry(guid, targetGroup);

                if (entry == null)
                    return new ErrorResponse("Failed to create Addressable entry.");

                // Set custom address if provided
                if (!string.IsNullOrEmpty(address))
                {
                    entry.address = address;
                }
                else
                {
                    // Use the asset name without extension as default address
                    entry.address = Path.GetFileNameWithoutExtension(fullPath);
                }

                // Add labels
                if (labels != null && labels.Count > 0)
                {
                    foreach (var label in labels)
                    {
                        if (!string.IsNullOrEmpty(label))
                        {
                            // Ensure label exists in settings
                            if (!settings.labelTable.labelNames.Contains(label))
                            {
                                settings.labelTable.AddLabel(label);
                            }
                            entry.labels.Add(label);
                        }
                    }
                }

                EditorUtility.SetDirty(settings);
                AssetDatabase.SaveAssets();

                return new SuccessResponse(
                    $"Asset added to Addressables in group '{groupName}'.",
                    new
                    {
                        assetPath = fullPath,
                        guid = entry.guid,
                        address = entry.address,
                        group = groupName,
                        labels = entry.labels.ToList(),
                    }
                );
            }
            catch (Exception e)
            {
                Debug.LogError($"[AddressableAssetManager] Failed to add asset: {e}");
                return new ErrorResponse($"Failed to add asset: {e.Message}");
            }
        }

        /// <summary>
        /// Removes an asset from Addressables.
        /// </summary>
        public static object RemoveAsset(string assetPath)
        {
            if (string.IsNullOrEmpty(assetPath))
                return new ErrorResponse("Asset path is required.");

            if (!AddressableGroupManager.EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            string fullPath = SanitizeAssetPath(assetPath);
            string guid = AssetDatabase.AssetPathToGUID(fullPath);

            if (string.IsNullOrEmpty(guid))
                return new ErrorResponse($"Could not find GUID for asset: {fullPath}");

            var settings = AddressableGroupManager.GetSettings();
            var entry = settings.FindAssetEntry(guid);

            if (entry == null)
                return new ErrorResponse($"Asset is not in Addressables: {fullPath}");

            var groupName = entry.parentGroup.Name;
            var entryAddress = entry.address;

            try
            {
                settings.RemoveAssetEntry(guid);
                
                EditorUtility.SetDirty(settings);
                AssetDatabase.SaveAssets();

                return new SuccessResponse(
                    $"Asset removed from Addressables (was in group '{groupName}').",
                    new
                    {
                        assetPath = fullPath,
                        guid = guid,
                        previousAddress = entryAddress,
                        previousGroup = groupName,
                    }
                );
            }
            catch (Exception e)
            {
                Debug.LogError($"[AddressableAssetManager] Failed to remove asset: {e}");
                return new ErrorResponse($"Failed to remove asset: {e.Message}");
            }
        }

        /// <summary>
        /// Moves an asset to a different Addressable group.
        /// </summary>
        public static object MoveAsset(string assetPath, string targetGroup)
        {
            if (string.IsNullOrEmpty(assetPath))
                return new ErrorResponse("Asset path is required.");
            if (string.IsNullOrEmpty(targetGroup))
                return new ErrorResponse("Target group is required.");

            if (!AddressableGroupManager.EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            string fullPath = SanitizeAssetPath(assetPath);
            string guid = AssetDatabase.AssetPathToGUID(fullPath);

            if (string.IsNullOrEmpty(guid))
                return new ErrorResponse($"Could not find GUID for asset: {fullPath}");

            var settings = AddressableGroupManager.GetSettings();
            var entry = settings.FindAssetEntry(guid);

            if (entry == null)
                return new ErrorResponse($"Asset is not in Addressables: {fullPath}");

            var sourceGroup = entry.parentGroup.Name;
            if (sourceGroup == targetGroup)
                return new ErrorResponse($"Asset is already in group '{targetGroup}'.");

            var destinationGroup = settings.FindGroup(targetGroup);
            if (destinationGroup == null)
                return new ErrorResponse($"Target group '{targetGroup}' not found.");

            try
            {
                settings.MoveEntry(entry, destinationGroup);
                
                EditorUtility.SetDirty(settings);
                AssetDatabase.SaveAssets();

                return new SuccessResponse(
                    $"Asset moved from '{sourceGroup}' to '{targetGroup}'.",
                    new
                    {
                        assetPath = fullPath,
                        guid = guid,
                        address = entry.address,
                        sourceGroup = sourceGroup,
                        targetGroup = targetGroup,
                    }
                );
            }
            catch (Exception e)
            {
                Debug.LogError($"[AddressableAssetManager] Failed to move asset: {e}");
                return new ErrorResponse($"Failed to move asset: {e.Message}");
            }
        }

        /// <summary>
        /// Assigns a label to an asset.
        /// </summary>
        public static object AssignLabel(string assetPath, string label)
        {
            if (string.IsNullOrEmpty(assetPath))
                return new ErrorResponse("Asset path is required.");
            if (string.IsNullOrEmpty(label))
                return new ErrorResponse("Label is required.");

            if (!AddressableGroupManager.EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            string fullPath = SanitizeAssetPath(assetPath);
            string guid = AssetDatabase.AssetPathToGUID(fullPath);

            if (string.IsNullOrEmpty(guid))
                return new ErrorResponse($"Could not find GUID for asset: {fullPath}");

            var settings = AddressableGroupManager.GetSettings();
            var entry = settings.FindAssetEntry(guid);

            if (entry == null)
                return new ErrorResponse($"Asset is not in Addressables: {fullPath}");

            try
            {
                // Ensure label exists
                if (!settings.labelTable.labelNames.Contains(label))
                {
                    settings.labelTable.AddLabel(label);
                }

                // Add label if not already present
                if (!entry.labels.Contains(label))
                {
                    entry.labels.Add(label);
                    
                    EditorUtility.SetDirty(settings);
                    AssetDatabase.SaveAssets();
                }

                return new SuccessResponse(
                    $"Label '{label}' assigned to asset.",
                    new
                    {
                        assetPath = fullPath,
                        guid = guid,
                        address = entry.address,
                        labels = entry.labels.ToList(),
                    }
                );
            }
            catch (Exception e)
            {
                Debug.LogError($"[AddressableAssetManager] Failed to assign label: {e}");
                return new ErrorResponse($"Failed to assign label: {e.Message}");
            }
        }

        /// <summary>
        /// Removes a label from an asset.
        /// </summary>
        public static object RemoveLabel(string assetPath, string label)
        {
            if (string.IsNullOrEmpty(assetPath))
                return new ErrorResponse("Asset path is required.");
            if (string.IsNullOrEmpty(label))
                return new ErrorResponse("Label is required.");

            if (!AddressableGroupManager.EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            string fullPath = SanitizeAssetPath(assetPath);
            string guid = AssetDatabase.AssetPathToGUID(fullPath);

            if (string.IsNullOrEmpty(guid))
                return new ErrorResponse($"Could not find GUID for asset: {fullPath}");

            var settings = AddressableGroupManager.GetSettings();
            var entry = settings.FindAssetEntry(guid);

            if (entry == null)
                return new ErrorResponse($"Asset is not in Addressables: {fullPath}");

            if (!entry.labels.Contains(label))
                return new ErrorResponse($"Asset does not have label '{label}'.");

            try
            {
                entry.labels.Remove(label);
                
                EditorUtility.SetDirty(settings);
                AssetDatabase.SaveAssets();

                return new SuccessResponse(
                    $"Label '{label}' removed from asset.",
                    new
                    {
                        assetPath = fullPath,
                        guid = guid,
                        address = entry.address,
                        labels = entry.labels.ToList(),
                    }
                );
            }
            catch (Exception e)
            {
                Debug.LogError($"[AddressableAssetManager] Failed to remove label: {e}");
                return new ErrorResponse($"Failed to remove label: {e.Message}");
            }
        }

        /// <summary>
        /// Updates an asset's address.
        /// </summary>
        public static object UpdateAddress(string assetPath, string newAddress)
        {
            if (string.IsNullOrEmpty(assetPath))
                return new ErrorResponse("Asset path is required.");
            if (string.IsNullOrEmpty(newAddress))
                return new ErrorResponse("New address is required.");

            if (!AddressableGroupManager.EnsureInitialized())
                return new ErrorResponse("Addressables not initialized.");

            string fullPath = SanitizeAssetPath(assetPath);
            string guid = AssetDatabase.AssetPathToGUID(fullPath);

            if (string.IsNullOrEmpty(guid))
                return new ErrorResponse($"Could not find GUID for asset: {fullPath}");

            var settings = AddressableGroupManager.GetSettings();
            var entry = settings.FindAssetEntry(guid);

            if (entry == null)
                return new ErrorResponse($"Asset is not in Addressables: {fullPath}");

            var oldAddress = entry.address;

            try
            {
                entry.address = newAddress;
                
                EditorUtility.SetDirty(settings);
                AssetDatabase.SaveAssets();

                return new SuccessResponse(
                    $"Asset address updated from '{oldAddress}' to '{newAddress}'.",
                    new
                    {
                        assetPath = fullPath,
                        guid = guid,
                        oldAddress = oldAddress,
                        newAddress = newAddress,
                        group = entry.parentGroup.Name,
                    }
                );
            }
            catch (Exception e)
            {
                Debug.LogError($"[AddressableAssetManager] Failed to update address: {e}");
                return new ErrorResponse($"Failed to update address: {e.Message}");
            }
        }

        #region Helper Methods

        private static string SanitizeAssetPath(string path)
        {
            if (string.IsNullOrEmpty(path))
                return path;

            path = path.Replace("\\", "/").Trim();
            
            // Ensure path starts with "Assets/"
            if (!path.StartsWith("Assets/") && !path.StartsWith("Packages/"))
            {
                if (!path.StartsWith("/"))
                    path = "Assets/" + path;
                else
                    path = "Assets" + path;
            }

            return path;
        }

        private static bool AssetExists(string path)
        {
            // Check if it's a valid asset
            if (!string.IsNullOrEmpty(AssetDatabase.AssetPathToGUID(path)))
                return true;

            // Check for folder
            if (AssetDatabase.IsValidFolder(path))
                return true;

            // Check file existence
            string fullPath = Path.Combine(Application.dataPath, "..", path);
            if (File.Exists(fullPath) || Directory.Exists(fullPath))
                return true;

            return false;
        }

        #endregion
    }
}
#endif
