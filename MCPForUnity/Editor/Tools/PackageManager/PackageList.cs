using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.PackageManager;
using UnityEditor.PackageManager.Requests;
using PackageInfo = UnityEditor.PackageManager.PackageInfo;

namespace MCPForUnity.Editor.Tools.PackageManager
{
    /// <summary>
    /// Handles listing and retrieving package information from Unity Package Manager.
    /// </summary>
    public static class PackageList
    {
        /// <summary>
        /// Get all installed packages from the Package Manager.
        /// </summary>
        public static async Task<object> GetInstalledPackagesAsync(string sourceFilter = "all")
        {
            try
            {
                PackageInfo[] packages;
                if (!PackageRequestUtility.TryGetInstalledPackagesFromCache(out packages))
                {
                    packages = await PackageRequestUtility.RunExclusiveAsync(
                        "list_installed",
                        async () =>
                        {
                            // Listing installed packages should be satisfied from local package state.
                            // Avoid network-backed refreshes here because a stalled Package Manager request
                            // can wedge the MCP command lane and make unrelated tools time out.
                            var request = Client.List(true, true);
                            var wait = await PackageRequestUtility.WaitForCompletionAsync(
                                request,
                                "list_installed",
                                PackageRequestUtility.ReadTimeoutMs
                            );

                            if (!wait.Success)
                            {
                                throw new InvalidOperationException(wait.ErrorMessage);
                            }

                            return request.Result.ToArray();
                        }
                    );
                    PackageRequestUtility.StoreInstalledPackages(packages);
                }

                var packageList = new List<object>();
                
                foreach (var pkg in packages)
                {
                    // Apply source filter
                    if (sourceFilter != "all" && !MatchesSourceFilter(pkg, sourceFilter))
                    {
                        continue;
                    }
                    
                    packageList.Add(PackageToDictionary(pkg));
                }
                
                return new SuccessResponse(
                    $"Found {packageList.Count} installed packages.",
                    new
                    {
                        packages = packageList,
                        totalCount = packageList.Count,
                        sourceFilter = sourceFilter
                    }
                );
            }
            catch (InvalidOperationException e)
            {
                return new ErrorResponse(e.Message);
            }
            catch (Exception e)
            {
                McpLog.Error($"[PackageList] Error getting installed packages: {e.Message}");
                return new ErrorResponse($"Error getting installed packages: {e.Message}");
            }
        }
        
        /// <summary>
        /// Get detailed information about a specific package.
        /// </summary>
        public static async Task<object> GetPackageInfoAsync(string packageName)
        {
            if (string.IsNullOrEmpty(packageName))
            {
                return new ErrorResponse("package_name is required.");
            }
            
            try
            {
                PackageInfo[] packages;
                if (!PackageRequestUtility.TryGetInstalledPackagesFromCache(out packages))
                {
                    packages = await PackageRequestUtility.RunExclusiveAsync(
                        "get_package_info",
                        async () =>
                        {
                            var request = Client.List(true, true);
                            var wait = await PackageRequestUtility.WaitForCompletionAsync(
                                request,
                                "get_package_info",
                                PackageRequestUtility.ReadTimeoutMs
                            );

                            if (!wait.Success)
                            {
                                throw new InvalidOperationException(wait.ErrorMessage);
                            }

                            return request.Result.ToArray();
                        }
                    );
                    PackageRequestUtility.StoreInstalledPackages(packages);
                }
                
                var pkg = packages.FirstOrDefault(p => p.name == packageName);
                
                if (pkg == null)
                {
                    return new ErrorResponse($"Package '{packageName}' not found.");
                }
                
                return new SuccessResponse(
                    $"Package info for '{packageName}'.",
                    PackageToDictionary(pkg, includeDetails: true)
                );
            }
            catch (InvalidOperationException e)
            {
                return new ErrorResponse(e.Message);
            }
            catch (Exception e)
            {
                McpLog.Error($"[PackageList] Error getting package info: {e.Message}");
                return new ErrorResponse($"Error getting package info: {e.Message}");
            }
        }
        
        /// <summary>
        /// Search packages in the Unity Package Registry.
        /// </summary>
        public static async Task<object> SearchPackagesAsync(
            string searchQuery, 
            int pageSize = 20, 
            int page = 1, 
            bool includePrerelease = false)
        {
            if (string.IsNullOrEmpty(searchQuery))
            {
                searchQuery = "";
            }
            
            try
            {
                // Clamp page size to reasonable limits
                pageSize = Math.Clamp(pageSize, 1, 100);
                page = Math.Max(1, page);
                
                var allPackages = await PackageRequestUtility.RunExclusiveAsync(
                    "search_packages",
                    async () =>
                    {
                        var request = Client.SearchAll(includePrerelease);
                        var wait = await PackageRequestUtility.WaitForCompletionAsync(
                            request,
                            "search_packages",
                            PackageRequestUtility.MutationTimeoutMs
                        );

                        if (!wait.Success)
                        {
                            throw new InvalidOperationException(wait.ErrorMessage);
                        }

                        return request.Result;
                    }
                );
                
                // Filter by search query if provided
                var filteredPackages = allPackages;
                if (!string.IsNullOrEmpty(searchQuery))
                {
                    var query = searchQuery.ToLowerInvariant();
                    filteredPackages = allPackages.Where(p =>
                        (p.name?.ToLowerInvariant().Contains(query) ?? false) ||
                        (p.displayName?.ToLowerInvariant().Contains(query) ?? false) ||
                        (p.description?.ToLowerInvariant().Contains(query) ?? false)
                    ).ToArray();
                }
                
                // Apply pagination
                var totalCount = filteredPackages.Length;
                var totalPages = (int)Math.Ceiling(totalCount / (double)pageSize);
                var pagedPackages = filteredPackages
                    .Skip((page - 1) * pageSize)
                    .Take(pageSize)
                    .ToList();
                
                var packageList = pagedPackages.Select(pkg => PackageToDictionary(pkg)).ToList();
                
                return new SuccessResponse(
                    $"Found {totalCount} packages matching '{searchQuery}'. Showing page {page} of {totalPages}.",
                    new
                    {
                        packages = packageList,
                        totalCount = totalCount,
                        pageSize = pageSize,
                        page = page,
                        totalPages = totalPages,
                        searchQuery = searchQuery,
                        includePrerelease = includePrerelease
                    }
                );
            }
            catch (InvalidOperationException e)
            {
                return new ErrorResponse(e.Message);
            }
            catch (Exception e)
            {
                McpLog.Error($"[PackageList] Error searching packages: {e.Message}");
                return new ErrorResponse($"Error searching packages: {e.Message}");
            }
        }
        
        /// <summary>
        /// List configured scoped registries.
        /// Note: This reads from the manifest.json file directly.
        /// </summary>
        public static object ListRegistries()
        {
            try
            {
                var manifestPath = System.IO.Path.Combine(
                    System.IO.Directory.GetCurrentDirectory(), 
                    "Packages", 
                    "manifest.json"
                );
                
                if (!System.IO.File.Exists(manifestPath))
                {
                    return new ErrorResponse("Package manifest not found.");
                }
                
                var manifestJson = System.IO.File.ReadAllText(manifestPath);
                var manifest = JObject.Parse(manifestJson);
                
                var registries = new List<object>();
                var scopedRegistries = manifest["scopedRegistries"] as JArray;
                
                if (scopedRegistries != null)
                {
                    foreach (var reg in scopedRegistries)
                    {
                        registries.Add(new
                        {
                            name = reg["name"]?.ToString(),
                            url = reg["url"]?.ToString(),
                            scopes = reg["scopes"]?.ToObject<List<string>>() ?? new List<string>()
                        });
                    }
                }
                
                return new SuccessResponse(
                    $"Found {registries.Count} scoped registries.",
                    new
                    {
                        registries = registries,
                        totalCount = registries.Count
                    }
                );
            }
            catch (Exception e)
            {
                McpLog.Error($"[PackageList] Error listing registries: {e.Message}");
                return new ErrorResponse($"Error listing registries: {e.Message}");
            }
        }
        
        /// <summary>
        /// Check if a package matches the source filter.
        /// </summary>
        private static bool MatchesSourceFilter(PackageInfo pkg, string sourceFilter)
        {
            var source = GetPackageSourceString(pkg);
            return source.Equals(sourceFilter, StringComparison.OrdinalIgnoreCase);
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
        
        /// <summary>
        /// Convert a PackageInfo to a dictionary for JSON serialization.
        /// </summary>
        private static Dictionary<string, object> PackageToDictionary(PackageInfo pkg, bool includeDetails = false)
        {
            var dict = new Dictionary<string, object>
            {
                ["name"] = pkg.name,
                ["version"] = pkg.version,
                ["displayName"] = pkg.displayName,
                ["source"] = GetPackageSourceString(pkg),
                ["resolvedPath"] = pkg.resolvedPath,
                ["isDirectDependency"] = pkg.isDirectDependency
            };
            
            // Add optional fields if they exist
            if (!string.IsNullOrEmpty(pkg.description))
                dict["description"] = pkg.description;
            
            if (pkg.author != null)
            {
                dict["author"] = new
                {
                    name = pkg.author.name,
                    email = pkg.author.email,
                    url = pkg.author.url
                };
            }
            
            if (pkg.dependencies != null && pkg.dependencies.Any())
            {
                dict["dependencies"] = pkg.dependencies.ToDictionary(
                    d => d.name, 
                    d => d.version
                );
            }
            
            if (pkg.keywords != null && pkg.keywords.Any())
                dict["keywords"] = pkg.keywords;
            
            var unityVersion = TryGetStringProperty(pkg, "unity", "unityVersion");
            if (!string.IsNullOrEmpty(unityVersion))
                dict["unityVersion"] = unityVersion;

            var unityRelease = TryGetStringProperty(pkg, "unityRelease");
            if (!string.IsNullOrEmpty(unityRelease))
                dict["unityRelease"] = unityRelease;
            
            // Git-specific info
            if (pkg.source == PackageSource.Git)
            {
                if (!string.IsNullOrEmpty(pkg.packageId))
                {
                    // packageId for git packages often contains the URL
                    dict["gitUrl"] = pkg.packageId;
                }
            }
            
            // Detailed info
            if (includeDetails)
            {
                if (!string.IsNullOrEmpty(pkg.category))
                    dict["category"] = pkg.category;
                
                if (pkg.changelogUrl != null)
                    dict["changelogUrl"] = pkg.changelogUrl.ToString();
                
                if (pkg.documentationUrl != null)
                    dict["documentationUrl"] = pkg.documentationUrl.ToString();
                
                var licenses = TryGetObjectProperty(pkg, "licenses") as System.Collections.IEnumerable;
                if (licenses != null)
                {
                    var licenseNames = new List<string>();
                    foreach (var license in licenses)
                    {
                        var name = TryGetStringProperty(license, "name");
                        if (!string.IsNullOrEmpty(name))
                            licenseNames.Add(name);
                    }

                    if (licenseNames.Count > 0)
                        dict["licenses"] = licenseNames;
                }
                
                if (pkg.repository != null)
                {
                    dict["repository"] = new
                    {
                        type = pkg.repository.type,
                        url = pkg.repository.url,
                        revision = pkg.repository.revision
                    };
                }
                
                var samples = TryGetObjectProperty(pkg, "samples") as System.Collections.IEnumerable;
                if (samples != null)
                {
                    var sampleList = new List<object>();
                    foreach (var sample in samples)
                    {
                        sampleList.Add(new
                        {
                            displayName = TryGetStringProperty(sample, "displayName"),
                            description = TryGetStringProperty(sample, "description"),
                            path = TryGetStringProperty(sample, "path")
                        });
                    }

                    if (sampleList.Count > 0)
                        dict["samples"] = sampleList;
                }
            }
            
            return dict;
        }

        private static string TryGetStringProperty(object target, params string[] propertyNames)
        {
            foreach (var propertyName in propertyNames)
            {
                var value = TryGetObjectProperty(target, propertyName);
                if (value is string s)
                {
                    return s;
                }
            }

            return null;
        }

        private static object TryGetObjectProperty(object target, string propertyName)
        {
            if (target == null || string.IsNullOrEmpty(propertyName))
            {
                return null;
            }

            var property = target.GetType().GetProperty(
                propertyName,
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.IgnoreCase
            );

            return property?.GetValue(target);
        }
    }
}
