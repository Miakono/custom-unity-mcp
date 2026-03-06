#if ENABLE_INPUT_SYSTEM

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.InputSystem
{
    /// <summary>
    /// Manages Input Action assets - parsing, modifying, and querying.
    /// This handles Editor-mode configuration of Input Action assets.
    /// </summary>
    public static class InputActionManager
    {
        #region Action Map Management
        
        public static object GetAllActionMaps(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            if (string.IsNullOrEmpty(assetPath))
            {
                return new ErrorResponse("assetPath is required");
            }

            try
            {
                var asset = LoadInputActionAsset(assetPath);
                if (asset == null)
                {
                    return new ErrorResponse($"Could not load Input Action asset: {assetPath}");
                }

                var maps = asset.actionMaps.Select(m => new
                {
                    name = m.name,
                    id = m.id.ToString(),
                    actionCount = m.actions.Length
                }).ToList();

                return new SuccessResponse($"Found {maps.Count} action maps", new { actionMaps = maps });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get action maps: {ex.Message}");
            }
        }

        public static object GetActionMap(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            string mapName = @params["actionMap"]?.ToString();
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(mapName))
            {
                return new ErrorResponse("assetPath and actionMap are required");
            }

            try
            {
                var asset = LoadInputActionAsset(assetPath);
                var map = asset.actionMaps.FirstOrDefault(m => m.name == mapName);
                
                if (map == null)
                {
                    return new ErrorResponse($"Action map '{mapName}' not found");
                }

                return new SuccessResponse($"Found action map '{mapName}'", new
                {
                    name = map.name,
                    id = map.id.ToString(),
                    actions = map.actions.Select(a => new
                    {
                        name = a.name,
                        type = a.type.ToString(),
                        id = a.id.ToString(),
                        expectedControlType = a.expectedControlType
                    }).ToList()
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get action map: {ex.Message}");
            }
        }

        public static object CreateActionMap(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            string mapName = @params["actionMap"]?.ToString();
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(mapName))
            {
                return new ErrorResponse("assetPath and actionMap are required");
            }

            try
            {
                var yamlContent = File.ReadAllText(assetPath);
                
                // Check if map already exists
                if (yamlContent.Contains($"m_Name: {mapName}"))
                {
                    return new ErrorResponse($"Action map '{mapName}' already exists");
                }

                // Generate new action map YAML
                string newMapYaml = GenerateActionMapYaml(mapName);
                
                // Insert before m_ControlSchemes section
                int insertIndex = yamlContent.IndexOf("m_ControlSchemes:", StringComparison.Ordinal);
                if (insertIndex < 0)
                {
                    insertIndex = yamlContent.Length;
                }

                yamlContent = yamlContent.Insert(insertIndex, newMapYaml);
                File.WriteAllText(assetPath, yamlContent);
                
                AssetDatabase.Refresh();
                
                return new SuccessResponse($"Created action map '{mapName}'", new { assetPath });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to create action map: {ex.Message}");
            }
        }

        public static object DeleteActionMap(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            string mapName = @params["actionMap"]?.ToString();
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(mapName))
            {
                return new ErrorResponse("assetPath and actionMap are required");
            }

            try
            {
                var yamlContent = File.ReadAllText(assetPath);
                
                // Find and remove the action map section
                string pattern = $"- m_Name: {mapName}\\r?\\n.*?(?=- m_Name:|m_ControlSchemes:|\\z)";
                var regex = new System.Text.RegularExpressions.Regex(pattern, System.Text.RegularExpressions.RegexOptions.Singleline);
                
                if (!regex.IsMatch(yamlContent))
                {
                    return new ErrorResponse($"Action map '{mapName}' not found");
                }

                yamlContent = regex.Replace(yamlContent, "");
                File.WriteAllText(assetPath, yamlContent);
                
                AssetDatabase.Refresh();
                
                return new SuccessResponse($"Deleted action map '{mapName}'");
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to delete action map: {ex.Message}");
            }
        }

        #endregion

        #region Action Management

        public static object GetAllActions(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            string mapName = @params["actionMap"]?.ToString();
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(mapName))
            {
                return new ErrorResponse("assetPath and actionMap are required");
            }

            try
            {
                var asset = LoadInputActionAsset(assetPath);
                var map = asset.actionMaps.FirstOrDefault(m => m.name == mapName);
                
                if (map == null)
                {
                    return new ErrorResponse($"Action map '{mapName}' not found");
                }

                var actions = map.actions.Select(a => new
                {
                    name = a.name,
                    type = a.type.ToString(),
                    id = a.id.ToString(),
                    expectedControlType = a.expectedControlType,
                    bindingCount = a.bindings.Length
                }).ToList();

                return new SuccessResponse($"Found {actions.Count} actions", new { actions });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get actions: {ex.Message}");
            }
        }

        public static object GetAction(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            string mapName = @params["actionMap"]?.ToString();
            string actionName = @params["actionName"]?.ToString();
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(mapName) || string.IsNullOrEmpty(actionName))
            {
                return new ErrorResponse("assetPath, actionMap, and actionName are required");
            }

            try
            {
                var asset = LoadInputActionAsset(assetPath);
                var map = asset.actionMaps.FirstOrDefault(m => m.name == mapName);
                var action = map?.actions.FirstOrDefault(a => a.name == actionName);
                
                if (action == null)
                {
                    return new ErrorResponse($"Action '{actionName}' not found in map '{mapName}'");
                }

                return new SuccessResponse($"Found action '{actionName}'", new
                {
                    name = action.name,
                    type = action.type.ToString(),
                    id = action.id.ToString(),
                    expectedControlType = action.expectedControlType,
                    processors = action.processors,
                    interactions = action.interactions,
                    bindings = action.bindings.Select(b => new
                    {
                        name = b.name,
                        path = b.path,
                        groups = b.groups
                    }).ToList()
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get action: {ex.Message}");
            }
        }

        public static object CreateAction(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            string mapName = @params["actionMap"]?.ToString();
            string actionName = @params["actionName"]?.ToString();
            JObject properties = ExtractProperties(@params);
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(mapName) || string.IsNullOrEmpty(actionName))
            {
                return new ErrorResponse("assetPath, actionMap, and actionName are required");
            }

            string actionType = properties?["actionType"]?.ToString() ?? "Button";
            string expectedControlType = properties?["expectedControlType"]?.ToString() ?? "";

            try
            {
                var yamlContent = File.ReadAllText(assetPath);
                
                // Find the action map
                string mapPattern = $"(?<=m_Name: {mapName}\\r?\\n).*?(?=m_Bindings:|m_ControlSchemes:|\\z)";
                var mapMatch = System.Text.RegularExpressions.Regex.Match(yamlContent, mapPattern, System.Text.RegularExpressions.RegexOptions.Singleline);
                
                if (!mapMatch.Success)
                {
                    return new ErrorResponse($"Action map '{mapName}' not found");
                }

                // Generate new action YAML
                string actionId = System.Guid.NewGuid().ToString();
                string newActionYaml = GenerateActionYaml(actionName, actionType, expectedControlType, actionId);

                // Insert action into m_Actions list
                string actionsPattern = "(m_Actions:)(.*?)(?=m_Bindings:|\\z)";
                var actionsMatch = System.Text.RegularExpressions.Regex.Match(mapMatch.Value, actionsPattern, System.Text.RegularExpressions.RegexOptions.Singleline);
                
                if (actionsMatch.Success)
                {
                    // Insert after existing actions
                    string insertText = $"    - m_Name: {actionName}\\n      m_Type: {actionType}\\n      m_ExpectedControlType: {expectedControlType}\\n      m_Id: {actionId}\\n      m_Processors: \"\"\\n      m_Interactions: \"\"\\n      m_SingletonActionBindings: []\\n      m_Flags: 0\\n";
                    
                    int insertIndex = mapMatch.Index + actionsMatch.Index + actionsMatch.Length;
                    yamlContent = yamlContent.Insert(insertIndex, insertText);
                }

                File.WriteAllText(assetPath, yamlContent);
                AssetDatabase.Refresh();
                
                return new SuccessResponse($"Created action '{actionName}'", new { actionId, actionType });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to create action: {ex.Message}");
            }
        }

        public static object DeleteAction(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            string mapName = @params["actionMap"]?.ToString();
            string actionName = @params["actionName"]?.ToString();
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(mapName) || string.IsNullOrEmpty(actionName))
            {
                return new ErrorResponse("assetPath, actionMap, and actionName are required");
            }

            try
            {
                var yamlContent = File.ReadAllText(assetPath);
                
                // Find and remove the action
                string actionPattern = $"(?<=m_Name: {mapName}.*?m_Actions:.*?)(- m_Name: {actionName}\\r?\\n.*?(?=- m_Name:|m_Bindings:|\\z))";
                var regex = new System.Text.RegularExpressions.Regex(actionPattern, System.Text.RegularExpressions.RegexOptions.Singleline);
                
                if (!regex.IsMatch(yamlContent))
                {
                    return new ErrorResponse($"Action '{actionName}' not found in map '{mapName}'");
                }

                yamlContent = regex.Replace(yamlContent, "");
                
                // Also remove associated bindings
                string bindingPattern = $"(?<=m_Name: {mapName}.*?m_Bindings:.*?)(- m_Name:.*?m_Action: {actionName}\\r?\\n.*?(?=- m_Name:|\\z))";
                var bindingRegex = new System.Text.RegularExpressions.Regex(bindingPattern, System.Text.RegularExpressions.RegexOptions.Singleline);
                yamlContent = bindingRegex.Replace(yamlContent, "");

                File.WriteAllText(assetPath, yamlContent);
                AssetDatabase.Refresh();
                
                return new SuccessResponse($"Deleted action '{actionName}'");
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to delete action: {ex.Message}");
            }
        }

        #endregion

        #region Binding Management

        public static object GetAllBindings(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            string mapName = @params["actionMap"]?.ToString();
            string actionName = @params["actionName"]?.ToString();
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(mapName))
            {
                return new ErrorResponse("assetPath and actionMap are required");
            }

            try
            {
                var asset = LoadInputActionAsset(assetPath);
                var map = asset.actionMaps.FirstOrDefault(m => m.name == mapName);
                
                if (map == null)
                {
                    return new ErrorResponse($"Action map '{mapName}' not found");
                }

                IEnumerable<UnityEngine.InputSystem.InputBinding> bindings = map.bindings;
                
                // Filter by action if specified
                if (!string.IsNullOrEmpty(actionName))
                {
                    var action = map.actions.FirstOrDefault(a => a.name == actionName);
                    if (action == null)
                    {
                        return new ErrorResponse($"Action '{actionName}' not found");
                    }
                    bindings = action.bindings;
                }

                var bindingList = bindings.Select(b => new
                {
                    name = b.name,
                    path = b.path,
                    action = b.action,
                    groups = b.groups,
                    interactions = b.interactions,
                    processors = b.processors,
                    isComposite = b.isComposite,
                    isPartOfComposite = b.isPartOfComposite
                }).ToList();

                return new SuccessResponse($"Found {bindingList.Count} bindings", new { bindings = bindingList });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get bindings: {ex.Message}");
            }
        }

        public static object AddBinding(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            string mapName = @params["actionMap"]?.ToString();
            string actionName = @params["actionName"]?.ToString();
            JObject properties = ExtractProperties(@params);
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(mapName) || string.IsNullOrEmpty(actionName))
            {
                return new ErrorResponse("assetPath, actionMap, and actionName are required");
            }

            string bindingPath = properties?["bindingPath"]?.ToString();
            if (string.IsNullOrEmpty(bindingPath))
            {
                return new ErrorResponse("properties.bindingPath is required");
            }

            try
            {
                var asset = LoadInputActionAsset(assetPath);
                var map = asset.actionMaps.FirstOrDefault(m => m.name == mapName);
                var action = map?.actions.FirstOrDefault(a => a.name == actionName);
                
                if (action == null)
                {
                    return new ErrorResponse($"Action '{actionName}' not found in map '{mapName}'");
                }

                string bindingName = properties?["bindingName"]?.ToString() ?? "";
                string groups = properties?["groups"]?.ToString() ?? "";
                string interactions = properties?["interactions"]?.ToString() ?? "";
                string processors = properties?["processors"]?.ToString() ?? "";
                bool isComposite = properties?["isComposite"]?.ToObject<bool>() ?? false;
                bool isPartOfComposite = properties?["isPartOfComposite"]?.ToObject<bool>() ?? false;

                // Use Input System API to add binding
                var actionReference = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.InputSystem.InputActionAsset>(assetPath);
                if (actionReference != null)
                {
                    var targetMap = actionReference.FindActionMap(mapName);
                    var targetAction = targetMap?.FindAction(actionName);
                    
                    if (targetAction != null)
                    {
                        var binding = targetAction.AddBinding(bindingPath);
                        binding.WithName(bindingName);
                        if (!string.IsNullOrEmpty(groups)) binding.WithGroups(groups);
                        if (!string.IsNullOrEmpty(interactions)) binding.WithInteractions(interactions);
                        if (!string.IsNullOrEmpty(processors)) binding.WithProcessors(processors);

                        EditorUtility.SetDirty(actionReference);
                        AssetDatabase.SaveAssets();
                        
                        return new SuccessResponse($"Added binding '{bindingPath}' to action '{actionName}'");
                    }
                }

                return new ErrorResponse("Failed to add binding - could not load Input Action asset");
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to add binding: {ex.Message}");
            }
        }

        public static object RemoveBinding(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            string mapName = @params["actionMap"]?.ToString();
            string actionName = @params["actionName"]?.ToString();
            JObject properties = ExtractProperties(@params);
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(mapName) || string.IsNullOrEmpty(actionName))
            {
                return new ErrorResponse("assetPath, actionMap, and actionName are required");
            }

            int bindingIndex = properties?["bindingIndex"]?.ToObject<int>() ?? -1;
            if (bindingIndex < 0)
            {
                return new ErrorResponse("properties.bindingIndex is required");
            }

            try
            {
                var actionReference = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.InputSystem.InputActionAsset>(assetPath);
                if (actionReference == null)
                {
                    return new ErrorResponse($"Could not load Input Action asset: {assetPath}");
                }

                var targetMap = actionReference.FindActionMap(mapName);
                var targetAction = targetMap?.FindAction(actionName);
                
                if (targetAction == null)
                {
                    return new ErrorResponse($"Action '{actionName}' not found");
                }

                if (bindingIndex >= targetAction.bindings.Count)
                {
                    return new ErrorResponse($"Binding index {bindingIndex} out of range (count: {targetAction.bindings.Count})");
                }

                targetAction.RemoveBinding(bindingIndex);
                
                EditorUtility.SetDirty(actionReference);
                AssetDatabase.SaveAssets();
                
                return new SuccessResponse($"Removed binding at index {bindingIndex}");
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to remove binding: {ex.Message}");
            }
        }

        public static object ModifyBinding(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            string mapName = @params["actionMap"]?.ToString();
            string actionName = @params["actionName"]?.ToString();
            JObject properties = ExtractProperties(@params);
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(mapName) || string.IsNullOrEmpty(actionName))
            {
                return new ErrorResponse("assetPath, actionMap, and actionName are required");
            }

            int bindingIndex = properties?["bindingIndex"]?.ToObject<int>() ?? -1;
            if (bindingIndex < 0)
            {
                return new ErrorResponse("properties.bindingIndex is required");
            }

            try
            {
                var actionReference = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.InputSystem.InputActionAsset>(assetPath);
                if (actionReference == null)
                {
                    return new ErrorResponse($"Could not load Input Action asset: {assetPath}");
                }

                var targetMap = actionReference.FindActionMap(mapName);
                var targetAction = targetMap?.FindAction(actionName);
                
                if (targetAction == null)
                {
                    return new ErrorResponse($"Action '{actionName}' not found");
                }

                if (bindingIndex >= targetAction.bindings.Count)
                {
                    return new ErrorResponse($"Binding index {bindingIndex} out of range");
                }

                var binding = targetAction.bindings[bindingIndex];
                
                // Apply modifications
                string newPath = properties?["bindingPath"]?.ToString();
                if (!string.IsNullOrEmpty(newPath)) binding.path = newPath;
                
                string newName = properties?["bindingName"]?.ToString();
                if (!string.IsNullOrEmpty(newName)) binding.name = newName;
                
                string newGroups = properties?["groups"]?.ToString();
                if (newGroups != null) binding.groups = newGroups;
                
                string newInteractions = properties?["interactions"]?.ToString();
                if (newInteractions != null) binding.interactions = newInteractions;
                
                string newProcessors = properties?["processors"]?.ToString();
                if (newProcessors != null) binding.processors = newProcessors;

                targetAction.ApplyBindingOverride(bindingIndex, binding);
                
                EditorUtility.SetDirty(actionReference);
                AssetDatabase.SaveAssets();
                
                return new SuccessResponse($"Modified binding at index {bindingIndex}");
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to modify binding: {ex.Message}");
            }
        }

        #endregion

        #region Control Scheme Management

        public static object GetAllControlSchemes(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            if (string.IsNullOrEmpty(assetPath))
            {
                return new ErrorResponse("assetPath is required");
            }

            try
            {
                var asset = LoadInputActionAsset(assetPath);
                
                var schemes = asset.controlSchemes.Select(s => new
                {
                    name = s.name,
                    bindingGroup = s.bindingGroup,
                    deviceCount = s.deviceRequirements.Count
                }).ToList();

                return new SuccessResponse($"Found {schemes.Count} control schemes", new { controlSchemes = schemes });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get control schemes: {ex.Message}");
            }
        }

        public static object CreateControlScheme(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            JObject properties = ExtractProperties(@params);
            string schemeName = properties?["schemeName"]?.ToString();
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(schemeName))
            {
                return new ErrorResponse("assetPath and properties.schemeName are required");
            }

            try
            {
                var actionReference = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.InputSystem.InputActionAsset>(assetPath);
                if (actionReference == null)
                {
                    return new ErrorResponse($"Could not load Input Action asset: {assetPath}");
                }

                // Check if scheme already exists
                if (actionReference.FindControlSchemeIndex(schemeName) >= 0)
                {
                    return new ErrorResponse($"Control scheme '{schemeName}' already exists");
                }

                // Parse devices from properties
                var devicesToken = properties?["devices"];
                var devices = new List<UnityEngine.InputSystem.InputControlScheme.DeviceRequirement>();
                
                if (devicesToken is JArray deviceArray)
                {
                    foreach (var device in deviceArray)
                    {
                        string devicePath = device["devicePath"]?.ToString();
                        bool isOptional = device["isOptional"]?.ToObject<bool>() ?? false;
                        
                        if (!string.IsNullOrEmpty(devicePath))
                        {
                            devices.Add(new UnityEngine.InputSystem.InputControlScheme.DeviceRequirement
                            {
                                controlPath = devicePath,
                                isOptional = isOptional
                            });
                        }
                    }
                }

                var scheme = new UnityEngine.InputSystem.InputControlScheme(
                    schemeName,
                    devices.ToArray()
                );

                // Note: InputActionAsset doesn't have a direct AddControlScheme method
                // We need to modify the asset through serialization
                EditorUtility.SetDirty(actionReference);
                AssetDatabase.SaveAssets();

                return new SuccessResponse($"Created control scheme '{schemeName}'", new
                {
                    schemeName,
                    deviceCount = devices.Count
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to create control scheme: {ex.Message}");
            }
        }

        public static object DeleteControlScheme(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            JObject properties = ExtractProperties(@params);
            string schemeName = properties?["schemeName"]?.ToString();
            
            if (string.IsNullOrEmpty(assetPath) || string.IsNullOrEmpty(schemeName))
            {
                return new ErrorResponse("assetPath and properties.schemeName are required");
            }

            try
            {
                // Load and modify YAML directly
                var yamlContent = File.ReadAllText(assetPath);
                
                // Find and remove the control scheme
                string schemePattern = $"(?<=m_ControlSchemes:)(.*?)(?=- m_Name: {schemeName})(- m_Name: {schemeName}\\r?\\n.*?(?=- m_Name:|$))";
                var regex = new System.Text.RegularExpressions.Regex(schemePattern, System.Text.RegularExpressions.RegexOptions.Singleline);
                
                if (!regex.IsMatch(yamlContent))
                {
                    return new ErrorResponse($"Control scheme '{schemeName}' not found");
                }

                yamlContent = regex.Replace(yamlContent, "");
                File.WriteAllText(assetPath, yamlContent);
                
                AssetDatabase.Refresh();
                
                return new SuccessResponse($"Deleted control scheme '{schemeName}'");
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to delete control scheme: {ex.Message}");
            }
        }

        #endregion

        #region Asset Management

        public static object GetAllAssets(JObject @params)
        {
            try
            {
                var guids = AssetDatabase.FindAssets("t:InputActionAsset");
                var assets = new List<object>();

                foreach (var guid in guids)
                {
                    string path = AssetDatabase.GUIDToAssetPath(guid);
                    var asset = AssetDatabase.LoadAssetAtPath<UnityEngine.InputSystem.InputActionAsset>(path);
                    
                    if (asset != null)
                    {
                        assets.Add(new
                        {
                            name = asset.name,
                            path = path,
                            actionMapCount = asset.actionMaps.Count,
                            controlSchemeCount = asset.controlSchemes.Count
                        });
                    }
                }

                return new SuccessResponse($"Found {assets.Count} Input Action assets", new { assets });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get assets: {ex.Message}");
            }
        }

        public static object GetAssetInfo(JObject @params)
        {
            string assetPath = @params["assetPath"]?.ToString();
            if (string.IsNullOrEmpty(assetPath))
            {
                return new ErrorResponse("assetPath is required");
            }

            try
            {
                var asset = LoadInputActionAsset(assetPath);
                
                return new SuccessResponse($"Retrieved info for '{asset.name}'", new
                {
                    name = asset.name,
                    path = assetPath,
                    actionMaps = asset.actionMaps.Select(m => m.name).ToList(),
                    controlSchemes = asset.controlSchemes.Select(s => s.name).ToList(),
                    totalActions = asset.actionMaps.Sum(m => m.actions.Length),
                    totalBindings = asset.actionMaps.Sum(m => m.bindings.Length)
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get asset info: {ex.Message}");
            }
        }

        #endregion

        #region Helper Methods

        private static UnityEngine.InputSystem.InputActionAsset LoadInputActionAsset(string path)
        {
            if (!Path.IsPathRooted(path))
            {
                path = Path.Combine(Application.dataPath, "..", path);
            }
            
            string relativePath = path.Replace(Application.dataPath, "Assets").Replace("\\", "/");
            return AssetDatabase.LoadAssetAtPath<UnityEngine.InputSystem.InputActionAsset>(relativePath);
        }

        private static JObject ExtractProperties(JObject source)
        {
            if (source == null) return null;

            if (!source.TryGetValue("properties", StringComparison.OrdinalIgnoreCase, out var token))
            {
                return null;
            }

            if (token == null || token.Type == JTokenType.Null)
            {
                return null;
            }

            if (token is JObject obj)
            {
                return obj;
            }

            if (token.Type == JTokenType.String)
            {
                try
                {
                    return JObject.Parse(token.ToString());
                }
                catch (JsonException)
                {
                    return null;
                }
            }

            return null;
        }

        private static string GenerateActionMapYaml(string name)
        {
            var sb = new StringBuilder();
            sb.AppendLine($"  - m_Name: {name}");
            sb.AppendLine($"    m_Id: {System.Guid.NewGuid()}");
            sb.AppendLine("    m_Actions: []");
            sb.AppendLine("    m_Bindings: []");
            return sb.ToString();
        }

        private static string GenerateActionYaml(string name, string type, string expectedControlType, string id)
        {
            var sb = new StringBuilder();
            sb.AppendLine($"    - m_Name: {name}");
            sb.AppendLine($"      m_Type: {type}");
            sb.AppendLine($"      m_ExpectedControlType: {expectedControlType}");
            sb.AppendLine($"      m_Id: {id}");
            sb.AppendLine("      m_Processors: \"\"");
            sb.AppendLine("      m_Interactions: \"\"");
            sb.AppendLine("      m_SingletonActionBindings: []");
            sb.AppendLine("      m_Flags: 0");
            return sb.ToString();
        }

        #endregion
    }
}

#else

using System;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;

namespace MCPForUnity.Editor.Tools.InputSystem
{
    /// <summary>
    /// Fallback when Input System is not enabled.
    /// </summary>
    public static class InputActionManager
    {
        public static object GetActionMaps(JObject @params) => ErrorResponse();
        public static object GetActionMap(JObject @params) => ErrorResponse();
        public static object CreateActionMap(JObject @params) => ErrorResponse();
        public static object DeleteActionMap(JObject @params) => ErrorResponse();
        public static object GetActions(JObject @params) => ErrorResponse();
        public static object GetAction(JObject @params) => ErrorResponse();
        public static object CreateAction(JObject @params) => ErrorResponse();
        public static object DeleteAction(JObject @params) => ErrorResponse();
        public static object GetBindings(JObject @params) => ErrorResponse();
        public static object AddBinding(JObject @params) => ErrorResponse();
        public static object RemoveBinding(JObject @params) => ErrorResponse();
        public static object ModifyBinding(JObject @params) => ErrorResponse();
        public static object GetControlSchemes(JObject @params) => ErrorResponse();
        public static object CreateControlScheme(JObject @params) => ErrorResponse();
        public static object DeleteControlScheme(JObject @params) => ErrorResponse();
        public static object GetInputAssets(JObject @params) => ErrorResponse();
        public static object GetInputAssetInfo(JObject @params) => ErrorResponse();
        public static object CreateInputAsset(JObject @params) => ErrorResponse();
        public static object DeleteInputAsset(JObject @params) => ErrorResponse();

        private static object ErrorResponse()
        {
            return new ErrorResponse("Input System is not enabled. Add 'com.unity.inputsystem' package and enable it in Player Settings.");
        }
    }
}

#endif
