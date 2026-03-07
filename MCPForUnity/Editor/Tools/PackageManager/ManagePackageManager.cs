using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;

namespace MCPForUnity.Editor.Tools.PackageManager
{
    /// <summary>
    /// Main handler for Unity Package Manager operations.
    /// 
    /// Provides functionality for:
    /// - Listing installed packages
    /// - Searching Unity Package Registry
    /// - Adding packages (registry, git, local, tarball)
    /// - Removing packages
    /// - Getting package information
    /// - Listing scoped registries
    /// - Resolving dependencies
    /// </summary>
    [McpForUnityTool("manage_package_manager", AutoRegister = false)]
    public static class ManagePackageManager
    {
        // Define the list of valid actions
        private static readonly List<string> ValidActions = new List<string>
        {
            "list_installed",
            "search_packages",
            "add_package",
            "remove_package",
            "get_package_info",
            "list_registries",
            "resolve_dependencies"
        };
        
        /// <summary>
        /// Main entry point for the manage_package_manager tool.
        /// </summary>
        public static async Task<object> HandleCommand(JObject @params)
        {
            if (@params == null)
            {
                return new ErrorResponse("Parameters cannot be null.");
            }
            
            var p = new ToolParams(@params);
            
            // Get and validate the action parameter
            var actionResult = p.GetRequired("action");
            if (!actionResult.IsSuccess)
            {
                return new ErrorResponse(actionResult.ErrorMessage);
            }
            
            string action = actionResult.Value.ToLowerInvariant();
            
            // Validate action
            if (!ValidActions.Contains(action))
            {
                string validActionsList = string.Join(", ", ValidActions);
                return new ErrorResponse(
                    $"Unknown action: '{action}'. Valid actions are: {validActionsList}"
                );
            }
            
            // Extract common parameters
            string packageName = p.Get("packageName");
            string version = p.Get("version");
            string searchQuery = p.Get("searchQuery");
            string sourceFilter = p.Get("sourceFilter", "all");
            string gitRef = p.Get("gitRef");
            int pageSize = p.GetInt("pageSize", 20) ?? 20;
            int page = p.GetInt("page", 1) ?? 1;
            bool includePrerelease = p.GetBool("includePrerelease", false);
            
            // Route to the appropriate handler
            try
            {
                switch (action)
                {
                    case "list_installed":
                        return await PackageList.GetInstalledPackagesAsync(sourceFilter);
                        
                    case "search_packages":
                        return await PackageList.SearchPackagesAsync(searchQuery, pageSize, page, includePrerelease);
                        
                    case "get_package_info":
                        return await PackageList.GetPackageInfoAsync(packageName);
                        
                    case "list_registries":
                        return PackageList.ListRegistries();
                        
                    case "add_package":
                        return await PackageOperations.AddPackageAsync(packageName, version, gitRef);
                        
                    case "remove_package":
                        return await PackageOperations.RemovePackageAsync(packageName);
                        
                    case "resolve_dependencies":
                        return await PackageOperations.ResolveDependenciesAsync();
                        
                    default:
                        // This should not happen due to earlier validation
                        return new ErrorResponse($"Action '{action}' is not implemented.");
                }
            }
            catch (Exception e)
            {
                McpLog.Error($"[ManagePackageManager] Error executing action '{action}': {e.Message}");
                return new ErrorResponse($"Error executing action '{action}': {e.Message}");
            }
        }
    }
}
