// -----------------------------------------------------------------------
// RuntimeToolRegistry.cs
// Registry for runtime-only MCP tools
// 
// Runtime tools are CLEARLY tagged as runtime_only and NEVER
// appear in editor-only environments.
// -----------------------------------------------------------------------

#nullable enable

using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;

namespace MCPForUnity.Runtime.MCP
{
    /// <summary>
    /// Metadata for a runtime tool
    /// </summary>
    public class RuntimeToolMetadata
    {
        /// <summary>
        /// Tool name (unique identifier)
        /// </summary>
        public string Name { get; set; } = "";
        
        /// <summary>
        /// Human-readable description
        /// </summary>
        public string Description { get; set; } = "";
        
        /// <summary>
        /// Tool category for organization
        /// </summary>
        public string Category { get; set; } = "general";
        
        /// <summary>
        /// Whether this tool can modify game state
        /// </summary>
        public bool IsMutating { get; set; }
        
        /// <summary>
        /// Whether this tool is only available in runtime context
        /// </summary>
        public bool RuntimeOnly { get; set; } = true;
        
        /// <summary>
        /// Required capability flags
        /// </summary>
        public List<string> RequiredCapabilities { get; set; } = new();
        
        /// <summary>
        /// Parameter definitions
        /// </summary>
        public List<RuntimeToolParameter> Parameters { get; set; } = new();
        
        /// <summary>
        /// Convert to dictionary for serialization
        /// </summary>
        public Dictionary<string, object> ToDictionary()
        {
            return new Dictionary<string, object>
            {
                ["name"] = Name,
                ["description"] = Description,
                ["category"] = Category,
                ["is_mutating"] = IsMutating,
                ["runtime_only"] = RuntimeOnly,
                ["requires_runtime_context"] = true,
                ["required_capabilities"] = RequiredCapabilities,
                ["parameters"] = Parameters.ConvertAll(p => p.ToDictionary()),
                ["domain"] = "runtime"
            };
        }
    }

    /// <summary>
    /// Parameter definition for a runtime tool
    /// </summary>
    public class RuntimeToolParameter
    {
        /// <summary>
        /// Parameter name
        /// </summary>
        public string Name { get; set; } = "";
        
        /// <summary>
        /// Parameter type (string, number, boolean, object, array)
        /// </summary>
        public string Type { get; set; } = "string";
        
        /// <summary>
        /// Parameter description
        /// </summary>
        public string Description { get; set; } = "";
        
        /// <summary>
        /// Whether parameter is required
        /// </summary>
        public bool Required { get; set; } = true;
        
        /// <summary>
        /// Default value (if optional)
        /// </summary>
        public object? DefaultValue { get; set; }
        
        /// <summary>
        /// Convert to dictionary for serialization
        /// </summary>
        public Dictionary<string, object> ToDictionary()
        {
            var dict = new Dictionary<string, object>
            {
                ["name"] = Name,
                ["type"] = Type,
                ["description"] = Description,
                ["required"] = Required
            };
            
            if (DefaultValue != null)
            {
                dict["default"] = DefaultValue;
            }
            
            return dict;
        }
    }

    /// <summary>
    /// Delegate for runtime tool execution
    /// </summary>
    public delegate Task<Dictionary<string, object>> RuntimeToolExecutor(
        Dictionary<string, object> parameters
    );

    /// <summary>
    /// Registry for runtime MCP tools.
    /// 
    /// This registry maintains tools that are ONLY available in runtime context.
    /// These tools never appear in Editor-only environments.
    /// </summary>
    public class RuntimeToolRegistry
    {
        private readonly Dictionary<string, (RuntimeToolMetadata metadata, RuntimeToolExecutor executor)> _tools = new();
        private readonly object _lock = new();

        /// <summary>
        /// Number of registered tools
        /// </summary>
        public int Count => _tools.Count;

        /// <summary>
        /// Register a new runtime tool
        /// </summary>
        public void RegisterTool(RuntimeToolMetadata metadata, RuntimeToolExecutor executor)
        {
            lock (_lock)
            {
                // Ensure runtime-only flag is set
                metadata.RuntimeOnly = true;
                
                _tools[metadata.Name] = (metadata, executor);
                Debug.Log($"[RuntimeToolRegistry] Registered tool: {metadata.Name}");
            }
        }

        /// <summary>
        /// Unregister a tool
        /// </summary>
        public bool UnregisterTool(string name)
        {
            lock (_lock)
            {
                return _tools.Remove(name);
            }
        }

        /// <summary>
        /// Check if a tool is registered
        /// </summary>
        public bool HasTool(string name)
        {
            lock (_lock)
            {
                return _tools.ContainsKey(name);
            }
        }

        /// <summary>
        /// Get tool metadata
        /// </summary>
        public RuntimeToolMetadata? GetMetadata(string name)
        {
            lock (_lock)
            {
                return _tools.TryGetValue(name, out var tool) ? tool.metadata : null;
            }
        }

        /// <summary>
        /// Execute a tool by name
        /// </summary>
        public async Task<Dictionary<string, object>> ExecuteToolAsync(
            string name,
            Dictionary<string, object> parameters
        )
        {
            RuntimeToolExecutor? executor;
            
            lock (_lock)
            {
                if (!_tools.TryGetValue(name, out var tool))
                {
                    return new Dictionary<string, object>
                    {
                        ["success"] = false,
                        ["error"] = "tool_not_found",
                        ["message"] = $"Runtime tool '{name}' not found"
                    };
                }
                
                executor = tool.executor;
            }

            try
            {
                return await executor(parameters);
            }
            catch (Exception ex)
            {
                Debug.LogError($"[RuntimeToolRegistry] Error executing tool '{name}': {ex}");
                return new Dictionary<string, object>
                {
                    ["success"] = false,
                    ["error"] = "execution_error",
                    ["message"] = ex.Message,
                    ["stack_trace"] = ex.StackTrace
                };
            }
        }

        /// <summary>
        /// Get all tool definitions for registration
        /// </summary>
        public List<Dictionary<string, object>> GetToolDefinitions()
        {
            lock (_lock)
            {
                var definitions = new List<Dictionary<string, object>>();
                
                foreach (var (name, (metadata, _)) in _tools)
                {
                    definitions.Add(metadata.ToDictionary());
                }
                
                return definitions;
            }
        }

        /// <summary>
        /// Get tools filtered by category
        /// </summary>
        public List<RuntimeToolMetadata> GetToolsByCategory(string category)
        {
            lock (_lock)
            {
                var tools = new List<RuntimeToolMetadata>();
                
                foreach (var (_, (metadata, _)) in _tools)
                {
                    if (metadata.Category.Equals(category, StringComparison.OrdinalIgnoreCase))
                    {
                        tools.Add(metadata);
                    }
                }
                
                return tools;
            }
        }

        /// <summary>
        /// Get all tool names
        /// </summary>
        public List<string> GetToolNames()
        {
            lock (_lock)
            {
                return new List<string>(_tools.Keys);
            }
        }

        /// <summary>
        /// Clear all registered tools
        /// </summary>
        public void Clear()
        {
            lock (_lock)
            {
                _tools.Clear();
            }
        }
    }
}
