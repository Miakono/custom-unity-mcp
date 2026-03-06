using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Services;

namespace MCPForUnity.Editor.Helpers
{
    internal sealed class ValidationProfileCatalog
    {
        public int Version { get; set; } = 1;
        public string GeneratedFrom { get; set; } = "unity_plugin_validation_registry";
        public int ProfileCount { get; set; }
        public List<ValidationProfile> Profiles { get; set; } = new();
    }

    internal sealed class ValidationProfile
    {
        public string Id { get; set; }
        public string Tool { get; set; }
        public string Group { get; set; }
        public bool ReadOnly { get; set; } = true;
        public string Description { get; set; }
        public List<string> WhenToUse { get; set; } = new();
        public List<string> Outputs { get; set; } = new();
    }

    internal static class ValidationProfileCatalogBuilder
    {
        private static readonly Dictionary<string, ValidationTemplate> Templates = new(StringComparer.OrdinalIgnoreCase)
        {
            ["validate_project_state"] = new ValidationTemplate(
                "core",
                "Quick editor and project readiness snapshot.",
                new[]
                {
                    "Use before broad mutations when you need a small readiness check.",
                    "Use when you need play mode, compile, or dirty-scene status in one response."
                },
                new[]
                {
                    "Editor compile and update state",
                    "Active scene summary",
                    "Compact recommendation string"
                }
            ),
            ["audit_scene_integrity"] = new ValidationTemplate(
                "testing",
                "Read-only audit of loaded scenes for integrity issues.",
                new[]
                {
                    "Use before scene-wide edits.",
                    "Use after large hierarchy or prefab changes."
                },
                new[]
                {
                    "Dirty-scene summary",
                    "Inactive-object counts",
                    "Missing-script issue samples"
                }
            ),
            ["audit_prefab_integrity"] = new ValidationTemplate(
                "testing",
                "Read-only audit of prefab assets under a folder.",
                new[]
                {
                    "Use before prefab refactors or migration work.",
                    "Use after broad asset-generation or script changes."
                },
                new[]
                {
                    "Prefab load failures",
                    "Missing-script issue samples",
                    "Variant counts and scan totals"
                }
            ),
        };

        private sealed class ValidationTemplate
        {
            public ValidationTemplate(
                string group,
                string description,
                IEnumerable<string> whenToUse,
                IEnumerable<string> outputs)
            {
                Group = group;
                Description = description;
                WhenToUse = whenToUse.ToList();
                Outputs = outputs.ToList();
            }

            public string Group { get; }
            public string Description { get; }
            public List<string> WhenToUse { get; }
            public List<string> Outputs { get; }
        }

        public static ValidationProfileCatalog BuildCatalog()
        {
            var profiles = MCPServiceLocator.ToolDiscovery
                .DiscoverAllTools()
                .Where(IsValidationTool)
                .OrderBy(tool => tool.Name, StringComparer.OrdinalIgnoreCase)
                .Select(BuildProfile)
                .ToList();

            return new ValidationProfileCatalog
            {
                ProfileCount = profiles.Count,
                Profiles = profiles
            };
        }

        private static ValidationProfile BuildProfile(ToolMetadata tool)
        {
            if (Templates.TryGetValue(tool.Name, out var template))
            {
                return new ValidationProfile
                {
                    Id = $"validation-{tool.Name.Replace('_', '-')}",
                    Tool = tool.Name,
                    Group = template.Group,
                    Description = template.Description,
                    WhenToUse = template.WhenToUse,
                    Outputs = template.Outputs
                };
            }

            return new ValidationProfile
            {
                Id = $"validation-{tool.Name.Replace('_', '-')}",
                Tool = tool.Name,
                Group = string.IsNullOrWhiteSpace(tool.Group) ? "core" : tool.Group,
                Description = tool.Description,
                WhenToUse = new List<string>
                {
                    $"Use when the task needs the '{tool.Name}' validation surface.",
                    "Use before or after broad edits that need lightweight verification."
                },
                Outputs = new List<string>
                {
                    "Tool-specific validation payload"
                }
            };
        }

        private static bool IsValidationTool(ToolMetadata tool)
        {
            if (tool == null || string.IsNullOrWhiteSpace(tool.Name))
            {
                return false;
            }

            return tool.Name.StartsWith("validate_", StringComparison.OrdinalIgnoreCase)
                || tool.Name.StartsWith("audit_", StringComparison.OrdinalIgnoreCase);
        }
    }
}
