// -----------------------------------------------------------------------
// RuntimeCommandProcessor.cs
// Processes runtime MCP commands
// 
// Routes commands to appropriate runtime tools and manages execution.
// -----------------------------------------------------------------------

#nullable enable

using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;

namespace MCPForUnity.Runtime.MCP
{
    /// <summary>
    /// Processes runtime MCP commands by routing them to the appropriate tools.
    /// 
    /// This processor handles the bridge between the WebSocket transport and
    /// the runtime tool registry. It ensures proper error handling and response formatting.
    /// </summary>
    public class RuntimeCommandProcessor
    {
        private readonly RuntimeMCPBridge _bridge;

        /// <summary>
        /// Create a new command processor
        /// </summary>
        public RuntimeCommandProcessor(RuntimeMCPBridge bridge)
        {
            _bridge = bridge ?? throw new ArgumentNullException(nameof(bridge));
        }

        /// <summary>
        /// Execute a command with the given parameters
        /// </summary>
        public async Task<Dictionary<string, object>> ExecuteCommandAsync(
            string commandName,
            Dictionary<string, object> parameters
        )
        {
            try
            {
                // Handle built-in bridge commands
                var builtInResult = await TryExecuteBuiltInCommandAsync(commandName, parameters);
                if (builtInResult != null)
                {
                    return builtInResult;
                }

                // Route to tool registry
                var registry = _bridge.ToolRegistry;
                
                if (!registry.HasTool(commandName))
                {
                    return new Dictionary<string, object>
                    {
                        ["success"] = false,
                        ["error"] = "unknown_command",
                        ["message"] = $"Unknown runtime command: '{commandName}'",
                        ["available_commands"] = registry.GetToolNames()
                    };
                }

                // Execute via registry
                var result = await registry.ExecuteToolAsync(commandName, parameters);
                
                // Ensure result has required fields
                if (!result.ContainsKey("success"))
                {
                    result["success"] = true;
                }
                
                // Tag as runtime execution
                result["_runtime_executed"] = true;
                result["_domain"] = "runtime";
                
                return result;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[RuntimeCommandProcessor] Command execution failed: {ex}");
                
                return new Dictionary<string, object>
                {
                    ["success"] = false,
                    ["error"] = "command_execution_failed",
                    ["message"] = ex.Message,
                    ["stack_trace"] = ex.StackTrace,
                    ["command"] = commandName,
                    ["_runtime_executed"] = false,
                    ["_domain"] = "runtime"
                };
            }
        }

        /// <summary>
        /// Try to execute a built-in bridge command
        /// </summary>
        private Task<Dictionary<string, object>?> TryExecuteBuiltInCommandAsync(
            string commandName,
            Dictionary<string, object> parameters
        )
        {
            Dictionary<string, object>? result = commandName switch
            {
                "runtime_bridge" => ExecuteBridgeCommand(parameters),
                "get_runtime_status" => GetRuntimeStatus(),
                "list_runtime_tools" => ListRuntimeTools(parameters),
                _ => null
            };

            return Task.FromResult(result);
        }

        /// <summary>
        /// Execute bridge control commands
        /// </summary>
        private Dictionary<string, object> ExecuteBridgeCommand(Dictionary<string, object> parameters)
        {
            string action = parameters.GetValueOrDefault("action", "").ToString()!;

            return action switch
            {
                "get_status" => GetRuntimeStatus(),
                "list_tools" => ListRuntimeTools(parameters),
                "get_connection_info" => _bridge.GetConnectionInfo(),
                _ => new Dictionary<string, object>
                {
                    ["success"] = false,
                    ["error"] = "unknown_bridge_action",
                    ["message"] = $"Unknown bridge action: '{action}'"
                }
            };
        }

        /// <summary>
        /// Get runtime status
        /// </summary>
        private Dictionary<string, object> GetRuntimeStatus()
        {
            var status = _bridge.GetStatus();
            
            // Add capability metadata
            status["_server_capabilities"] = new Dictionary<string, object>
            {
                ["runtime_only"] = true,
                ["requires_runtime_context"] = true,
                ["domain"] = "runtime",
                ["separate_connection"] = true
            };
            
            return new Dictionary<string, object>
            {
                ["success"] = true,
                ["message"] = "Runtime status retrieved",
                ["data"] = status
            };
        }

        /// <summary>
        /// List available runtime tools
        /// </summary>
        private Dictionary<string, object> ListRuntimeTools(Dictionary<string, object> parameters)
        {
            string category = parameters.GetValueOrDefault("category", "all").ToString()!;
            bool includeMetadata = GetBoolParameter(parameters, "include_metadata", true);
            
            var registry = _bridge.ToolRegistry;
            List<Dictionary<string, object>> tools;
            
            if (category == "all")
            {
                tools = registry.GetToolDefinitions();
            }
            else
            {
                var categoryTools = registry.GetToolsByCategory(category);
                tools = categoryTools.ConvertAll(t => t.ToDictionary());
            }
            
            var result = new Dictionary<string, object>
            {
                ["success"] = true,
                ["message"] = $"Found {tools.Count} runtime tools",
                ["data"] = new Dictionary<string, object>
                {
                    ["tools"] = tools,
                    ["count"] = tools.Count,
                    ["category"] = category,
                    ["_domain"] = "runtime",
                    ["_runtime_only"] = true
                }
            };
            
            if (includeMetadata)
            {
                ((Dictionary<string, object>)result["data"])["_capability_metadata"] = new Dictionary<string, object>
                {
                    ["runtime_only"] = true,
                    ["requires_runtime_context"] = true,
                    ["separate_from_editor"] = true
                };
            }
            
            return result;
        }

        /// <summary>
        /// Helper to safely get boolean parameter
        /// </summary>
        private static bool GetBoolParameter(
            Dictionary<string, object> parameters,
            string key,
            bool defaultValue
        )
        {
            if (!parameters.TryGetValue(key, out var value))
            {
                return defaultValue;
            }

            return value switch
            {
                bool b => b,
                string s => bool.TryParse(s, out var result) ? result : defaultValue,
                _ => defaultValue
            };
        }
    }
}
