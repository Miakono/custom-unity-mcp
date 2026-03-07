#if MCP_ADDRESSABLES_PACKAGE_PRESENT
using System.Collections.Generic;
using MCPForUnity.Editor.Tools.Addressables;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;

namespace MCPForUnity.Editor.Tools
{
    /// <summary>
    /// Main handler for manage_addressables command.
    /// Routes to specialized managers for groups, builds, and assets.
    /// </summary>
    [McpForUnityTool("manage_addressables")]
    public static class ManageAddressables
    {
        // Define valid actions
        private static readonly List<string> ValidActions = new List<string>
        {
            // Analysis
            "analyze",
            "validate",
            "get_settings",
            
            // Build operations
            "build",
            "build_player",
            "clean_build",
            
            // Group management
            "get_groups",
            "create_group",
            "delete_group",
            "get_group_assets",
            
            // Asset management
            "add_asset",
            "remove_asset",
            "move_asset",
            
            // Label management
            "assign_label",
            "remove_label",
            "get_labels",
        };

        /// <summary>
        /// Main entry point for manage_addressables command.
        /// </summary>
        public static object HandleCommand(JObject @params)
        {
            string action = @params["action"]?.ToString()?.ToLowerInvariant();
            if (string.IsNullOrEmpty(action))
            {
                return new ErrorResponse("Action parameter is required.");
            }

            // Validate action
            if (!ValidActions.Contains(action))
            {
                string validActionsList = string.Join(", ", ValidActions);
                return new ErrorResponse(
                    $"Unknown action: '{action}'. Valid actions are: {validActionsList}"
                );
            }

            try
            {
                // Route to appropriate manager based on action
                switch (action)
                {
                    // Analysis and settings
                    case "analyze":
                        return AddressableBuildManager.Analyze(
                            @params["reportPath"]?.ToString()
                        );

                    case "validate":
                        return AddressableBuildManager.Validate();

                    case "get_settings":
                        return AddressableGroupManager.GetSettings(
                            @params["settingsPath"]?.ToString()
                        );

                    // Build operations
                    case "build":
                        return AddressableBuildManager.Build(
                            platform: @params["platform"]?.ToString(),
                            dryRun: @params["dryRun"]?.ToObject<bool>() ?? false,
                            clean: @params["clean"]?.ToObject<bool>() ?? false,
                            settingsPath: @params["settingsPath"]?.ToString()
                        );

                    case "build_player":
                        return AddressableBuildManager.BuildPlayer(
                            platform: @params["platform"]?.ToString(),
                            dryRun: @params["dryRun"]?.ToObject<bool>() ?? false,
                            clean: @params["clean"]?.ToObject<bool>() ?? false
                        );

                    case "clean_build":
                        return AddressableBuildManager.CleanBuild();

                    // Group operations
                    case "get_groups":
                        return AddressableGroupManager.GetGroups(
                            pageSize: @params["pageSize"]?.ToObject<int?>(),
                            pageNumber: @params["pageNumber"]?.ToObject<int?>()
                        );

                    case "create_group":
                        return AddressableGroupManager.CreateGroup(
                            @params["groupName"]?.ToString(),
                            @params["options"] as JObject
                        );

                    case "delete_group":
                        return AddressableGroupManager.DeleteGroup(
                            @params["groupName"]?.ToString()
                        );

                    case "get_group_assets":
                        return AddressableGroupManager.GetGroupAssets(
                            groupName: @params["groupName"]?.ToString(),
                            pageSize: @params["pageSize"]?.ToObject<int?>(),
                            pageNumber: @params["pageNumber"]?.ToObject<int?>()
                        );

                    case "get_labels":
                        return AddressableGroupManager.GetLabels();

                    // Asset operations
                    case "add_asset":
                        var labels = new List<string>();
                        var labelsToken = @params["labels"];
                        if (labelsToken is JArray labelsArray)
                        {
                            foreach (var label in labelsArray)
                            {
                                labels.Add(label.ToString());
                            }
                        }

                        return AddressableAssetManager.AddAsset(
                            assetPath: @params["assetPath"]?.ToString(),
                            groupName: @params["groupName"]?.ToString(),
                            address: @params["address"]?.ToString(),
                            labels: labels
                        );

                    case "remove_asset":
                        return AddressableAssetManager.RemoveAsset(
                            @params["assetPath"]?.ToString()
                        );

                    case "move_asset":
                        return AddressableAssetManager.MoveAsset(
                            assetPath: @params["assetPath"]?.ToString(),
                            targetGroup: @params["targetGroup"]?.ToString()
                        );

                    // Label operations
                    case "assign_label":
                        return AddressableAssetManager.AssignLabel(
                            assetPath: @params["assetPath"]?.ToString(),
                            label: @params["labels"]?.ToString() ?? @params["label"]?.ToString()
                        );

                    case "remove_label":
                        return AddressableAssetManager.RemoveLabel(
                            assetPath: @params["assetPath"]?.ToString(),
                            label: @params["label"]?.ToString()
                        );

                    default:
                        return new ErrorResponse($"Action '{action}' is not implemented.");
                }
            }
            catch (System.Exception e)
            {
                McpLog.Error($"[ManageAddressables] Action '{action}' failed: {e}");
                return new ErrorResponse(
                    $"Internal error processing action '{action}': {e.Message}"
                );
            }
        }
    }
}
#endif
