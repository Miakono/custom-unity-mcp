using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.PackageManager;
using UnityEditor.PackageManager.Requests;
using PackageInfo = UnityEditor.PackageManager.PackageInfo;

namespace MCPForUnity.Editor.Tools.PackageManager
{
    /// <summary>
    /// Handles package operations: add, remove, and resolve dependencies.
    /// </summary>
    public static class PackageOperations
    {
        /// <summary>
        /// Add a package to the project.
        /// Supports registry packages (name@version), git URLs, and local paths.
        /// </summary>
        public static async Task<object> AddPackageAsync(string packageName, string version, string gitRef = null)
        {
            if (string.IsNullOrEmpty(packageName))
            {
                return new ErrorResponse("package_name is required for add_package.");
            }
            
            try
            {
                PackageRequestUtility.InvalidateInstalledPackagesCache();
                string packageIdentifier;
                
                // Determine the package identifier format
                if (IsGitUrl(packageName))
                {
                    // Git URL format
                    packageIdentifier = packageName;
                    if (!string.IsNullOrEmpty(gitRef))
                    {
                        // Append git ref (branch, tag, or commit hash)
                        packageIdentifier = $"{packageName}#{gitRef}";
                    }
                }
                else if (IsLocalPath(packageName))
                {
                    // Local path format
                    packageIdentifier = packageName;
                }
                else if (IsTarballPath(packageName))
                {
                    // Tarball format
                    packageIdentifier = packageName;
                }
                else
                {
                    // Registry package format: name@version or just name for latest
                    if (!string.IsNullOrEmpty(version))
                    {
                        packageIdentifier = $"{packageName}@{version}";
                    }
                    else
                    {
                        packageIdentifier = packageName;
                    }
                }
                
                McpLog.Info($"[PackageOperations] Adding package: {packageIdentifier}");
                
                // Start the add request
                var addedPackage = await PackageRequestUtility.RunExclusiveAsync(
                    "add_package",
                    async () =>
                    {
                        var request = Client.Add(packageIdentifier);
                        var wait = await PackageRequestUtility.WaitForCompletionAsync(
                            request,
                            "add_package",
                            PackageRequestUtility.MutationTimeoutMs
                        );

                        if (!wait.Success)
                        {
                            throw new InvalidOperationException(wait.ErrorMessage);
                        }

                        return request.Result;
                    }
                );
                PackageRequestUtility.InvalidateInstalledPackagesCache();
                
                return new SuccessResponse(
                    $"Package '{addedPackage.displayName ?? addedPackage.name}' ({addedPackage.name}@{addedPackage.version}) added successfully.",
                    new
                    {
                        name = addedPackage.name,
                        version = addedPackage.version,
                        displayName = addedPackage.displayName,
                        source = GetPackageSourceString(addedPackage),
                        resolvedPath = addedPackage.resolvedPath
                    }
                );
            }
            catch (InvalidOperationException e)
            {
                return new ErrorResponse(e.Message);
            }
            catch (Exception e)
            {
                McpLog.Error($"[PackageOperations] Error adding package: {e.Message}");
                return new ErrorResponse($"Error adding package: {e.Message}");
            }
        }
        
        /// <summary>
        /// Remove a package from the project.
        /// </summary>
        public static async Task<object> RemovePackageAsync(string packageName)
        {
            if (string.IsNullOrEmpty(packageName))
            {
                return new ErrorResponse("package_name is required for remove_package.");
            }
            
            try
            {
                PackageRequestUtility.InvalidateInstalledPackagesCache();
                await PackageRequestUtility.RunExclusiveAsync(
                    "remove_package",
                    async () =>
                    {
                        var listRequest = Client.List(false, true);
                        var listWait = await PackageRequestUtility.WaitForCompletionAsync(
                            listRequest,
                            "remove_package:list_installed",
                            PackageRequestUtility.ReadTimeoutMs
                        );

                        if (!listWait.Success)
                        {
                            throw new InvalidOperationException(listWait.ErrorMessage);
                        }

                        var pkg = listRequest.Result.FirstOrDefault(p => p.name == packageName);
                        if (pkg == null)
                        {
                            throw new InvalidOperationException($"Package '{packageName}' not found.");
                        }

                        if (!pkg.isDirectDependency)
                        {
                            throw new InvalidOperationException(
                                $"Cannot remove '{packageName}' - it is a transitive dependency, not a direct dependency."
                            );
                        }

                        var request = Client.Remove(packageName);
                        var wait = await PackageRequestUtility.WaitForCompletionAsync(
                            request,
                            "remove_package",
                            PackageRequestUtility.MutationTimeoutMs
                        );

                        if (!wait.Success)
                        {
                            throw new InvalidOperationException(wait.ErrorMessage);
                        }

                        return true;
                    }
                );
                PackageRequestUtility.InvalidateInstalledPackagesCache();
                return new SuccessResponse(
                    $"Package '{packageName}' removed successfully."
                );
            }
            catch (InvalidOperationException e)
            {
                return new ErrorResponse(e.Message);
            }
            catch (Exception e)
            {
                McpLog.Error($"[PackageOperations] Error removing package: {e.Message}");
                return new ErrorResponse($"Error removing package: {e.Message}");
            }
        }
        
        /// <summary>
        /// Resolve dependencies by refreshing the package list.
        /// This forces Unity to re-resolve all package dependencies.
        /// </summary>
        public static async Task<object> ResolveDependenciesAsync()
        {
            try
            {
                McpLog.Info("[PackageOperations] Resolving dependencies...");

                PackageRequestUtility.InvalidateInstalledPackagesCache();
                var packageCount = await PackageRequestUtility.RunExclusiveAsync(
                    "resolve_dependencies",
                    async () =>
                    {
                        Client.Resolve();
                        await Task.Delay(300);

                        var listRequest = Client.List(false, true);
                        var listWait = await PackageRequestUtility.WaitForCompletionAsync(
                            listRequest,
                            "resolve_dependencies:list_installed",
                            PackageRequestUtility.ReadTimeoutMs
                        );

                        if (!listWait.Success)
                        {
                            throw new InvalidOperationException(listWait.ErrorMessage);
                        }

                        return listRequest.Result.Count();
                    }
                );
                PackageRequestUtility.InvalidateInstalledPackagesCache();
                
                return new SuccessResponse(
                    $"Dependencies resolved successfully. {packageCount} packages in project.",
                    new
                    {
                        packageCount = packageCount,
                        resolved = true
                    }
                );
            }
            catch (InvalidOperationException e)
            {
                return new ErrorResponse(e.Message);
            }
            catch (Exception e)
            {
                McpLog.Error($"[PackageOperations] Error resolving dependencies: {e.Message}");
                return new ErrorResponse($"Error resolving dependencies: {e.Message}");
            }
        }
        
        /// <summary>
        /// Check if a string is a git URL.
        /// </summary>
        private static bool IsGitUrl(string input)
        {
            return input.StartsWith("https://") || 
                   input.StartsWith("http://") || 
                   input.StartsWith("git@") ||
                   input.StartsWith("git:") ||
                   input.StartsWith("git+") ||
                   input.EndsWith(".git");
        }
        
        /// <summary>
        /// Check if a string is a local file path.
        /// </summary>
        private static bool IsLocalPath(string input)
        {
            // Check for common local path indicators
            return input.StartsWith("file:") ||
                   input.StartsWith("./") ||
                   input.StartsWith("../") ||
                   input.StartsWith("/") ||
                   (input.Length > 1 && input[1] == ':'); // Windows drive letter (e.g., "C:\")
        }
        
        /// <summary>
        /// Check if a string is a tarball path.
        /// </summary>
        private static bool IsTarballPath(string input)
        {
            return input.EndsWith(".tgz") || 
                   input.EndsWith(".tar.gz") ||
                   (input.StartsWith("file:") && (input.EndsWith(".tgz") || input.EndsWith(".tar.gz")));
        }
        
        /// <summary>
        /// Get the source type string for a package.
        /// </summary>
        private static string GetPackageSourceString(PackageInfo pkg)
        {
            if (pkg.source == PackageSource.Registry)
            {
                return pkg.name.StartsWith("com.unity.") ? "built-in" : "registry";
            }
            
            if (pkg.source == PackageSource.Git)
                return "git";
            
            if (pkg.source == PackageSource.Local)
                return "local";
            
            if (pkg.source == PackageSource.LocalTarball)
                return "tarball";
            
            if (pkg.source == PackageSource.Embedded)
                return "embedded";
            
            return "unknown";
        }
    }
}
