using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Services;

namespace MCPForUnity.Editor.Helpers
{
    internal sealed class SubagentCatalog
    {
        public int Version { get; set; } = 1;
        public string GeneratedFrom { get; set; } = "unity_plugin_tool_registry";
        public List<string> DefaultEnabledGroups { get; set; } = new();
        public int GroupCount { get; set; }
        public int SubagentCount { get; set; }
        public List<SubagentProfile> Subagents { get; set; } = new();
    }

    internal sealed class SubagentProfile
    {
        public string Id { get; set; }
        public string Name { get; set; }
        public string Kind { get; set; }
        public string Group { get; set; }
        public string Description { get; set; }
        public bool DefaultEnabled { get; set; }
        public string ActivationGroup { get; set; }
        public List<string> Tools { get; set; } = new();
        public List<string> WhenToUse { get; set; } = new();
        public List<string> Workflow { get; set; } = new();
        public List<string> HandoffTargets { get; set; } = new();
    }

    internal static class SubagentCatalogBuilder
    {
        private static readonly HashSet<string> DefaultEnabledGroups = new(StringComparer.OrdinalIgnoreCase)
        {
            "core"
        };

        private static readonly Dictionary<string, SpecialistTemplate> Templates = new(StringComparer.OrdinalIgnoreCase)
        {
            ["core"] = new SpecialistTemplate(
                "Unity Core Builder",
                "Owns everyday Unity editing work: scenes, gameobjects, prefabs, assets, scripts, and editor state.",
                new[]
                {
                    "Scene composition, hierarchy edits, and asset inspection.",
                    "Script reads or targeted script mutations.",
                    "Prefab creation, updates, and validation."
                },
                new[]
                {
                    "Inspect current state before mutating.",
                    "Batch related changes when the task spans multiple objects.",
                    "Hand off to testing after compile-sensitive or wide-scope edits."
                },
                new[]
                {
                    "unity-testing-specialist",
                    "unity-ui-specialist"
                }
            ),
            ["vfx"] = new SpecialistTemplate(
                "Unity VFX Specialist",
                "Handles shaders, materials, textures, and VFX authoring flows.",
                new[]
                {
                    "Shader and material iteration.",
                    "Texture inspection or mutation workflows.",
                    "VFX Graph or look-dev tasks."
                },
                new[]
                {
                    "Inspect asset state before broad mutations.",
                    "Keep look-dev changes scoped to clear targets.",
                    "Escalate to testing when visuals need validation."
                },
                new[]
                {
                    "unity-core-specialist",
                    "unity-testing-specialist"
                }
            ),
            ["animation"] = new SpecialistTemplate(
                "Unity Animation Specialist",
                "Focuses on animator, clips, and animation editing tasks.",
                new[]
                {
                    "Animator or clip authoring.",
                    "Animation controller inspection or repair.",
                    "Playback-oriented content adjustments."
                },
                new[]
                {
                    "Prefer small, verifiable changes to animation assets.",
                    "Keep clip/controller edits grouped by target.",
                    "Route final validation through testing when animation behavior changed."
                },
                new[]
                {
                    "unity-testing-specialist",
                    "unity-core-specialist"
                }
            ),
            ["ui"] = new SpecialistTemplate(
                "Unity UI Specialist",
                "Owns UI Toolkit and interface authoring tasks.",
                new[]
                {
                    "UXML, USS, and UIDocument changes.",
                    "UI hierarchy or styling work.",
                    "Interface assembly and review loops."
                },
                new[]
                {
                    "Keep UI changes scoped and inspect the result after edits.",
                    "Separate content edits from styling edits when possible.",
                    "Hand off to testing for visual verification."
                },
                new[]
                {
                    "unity-testing-specialist",
                    "unity-core-specialist"
                }
            ),
            ["scripting_ext"] = new SpecialistTemplate(
                "Unity Data Specialist",
                "Handles ScriptableObject and data-oriented authoring flows.",
                new[]
                {
                    "ScriptableObject reads and mutations.",
                    "Data definition setup and maintenance.",
                    "Project data validation tasks."
                },
                new[]
                {
                    "Inspect target data before write operations.",
                    "Keep data migrations explicit and reversible.",
                    "Escalate to testing if data impacts runtime behavior."
                },
                new[]
                {
                    "unity-testing-specialist",
                    "unity-core-specialist"
                }
            ),
            ["testing"] = new SpecialistTemplate(
                "Unity Testing Specialist",
                "Runs validation loops, test jobs, and post-change verification.",
                new[]
                {
                    "Run tests after code or asset mutations.",
                    "Collect diagnostics after failures.",
                    "Verify compile, editor, or batch outcomes."
                },
                new[]
                {
                    "Use focused checks first, then broader suites if failures persist.",
                    "Capture exact failing commands or artifacts.",
                    "Return findings to the originating specialist with concrete next steps."
                },
                new[]
                {
                    "unity-core-specialist",
                    "unity-ui-specialist",
                    "unity-vfx-specialist"
                }
            ),
        };

        private sealed class SpecialistTemplate
        {
            public SpecialistTemplate(
                string name,
                string description,
                IEnumerable<string> whenToUse,
                IEnumerable<string> workflow,
                IEnumerable<string> handoffTargets)
            {
                Name = name;
                Description = description;
                WhenToUse = whenToUse.ToList();
                Workflow = workflow.ToList();
                HandoffTargets = handoffTargets.ToList();
            }

            public string Name { get; }
            public string Description { get; }
            public List<string> WhenToUse { get; }
            public List<string> Workflow { get; }
            public List<string> HandoffTargets { get; }
        }

        public static SubagentCatalog BuildCatalog()
        {
            var tools = MCPServiceLocator.ToolDiscovery
                .DiscoverAllTools()
                .OrderBy(tool => tool.Name, StringComparer.OrdinalIgnoreCase)
                .ToList();

            var grouped = tools
                .Where(tool => !string.IsNullOrWhiteSpace(tool.Group))
                .GroupBy(tool => tool.Group, StringComparer.OrdinalIgnoreCase)
                .OrderBy(group => GetGroupSortKey(group.Key), StringComparer.OrdinalIgnoreCase)
                .ToList();

            var catalog = new SubagentCatalog
            {
                DefaultEnabledGroups = DefaultEnabledGroups.OrderBy(group => group, StringComparer.OrdinalIgnoreCase).ToList(),
                GroupCount = grouped.Count,
            };

            catalog.Subagents.Add(BuildOrchestrator(grouped));
            foreach (var group in grouped)
            {
                catalog.Subagents.Add(BuildSpecialist(group.Key, group.ToList()));
            }

            catalog.SubagentCount = catalog.Subagents.Count;
            return catalog;
        }

        private static SubagentProfile BuildOrchestrator(IEnumerable<IGrouping<string, ToolMetadata>> grouped)
        {
            return new SubagentProfile
            {
                Id = "unity-orchestrator",
                Name = "Unity Orchestrator",
                Kind = "orchestrator",
                Description = "Routes work to the right Unity specialist and keeps workflows scoped by tool family.",
                Tools = grouped.SelectMany(group => group.Select(tool => tool.Name)).Distinct(StringComparer.OrdinalIgnoreCase).ToList(),
                WhenToUse = new List<string>
                {
                    "Start here when the task spans multiple Unity domains.",
                    "Use when you need to choose between scene, UI, VFX, animation, data, or testing work.",
                    "Use after broad changes to coordinate verification."
                },
                Workflow = new List<string>
                {
                    "Begin with the smallest specialist that fits the current task.",
                    "Keep tool usage scoped to a single family until the task crosses domains.",
                    "Hand off to testing after meaningful mutations."
                },
                HandoffTargets = grouped.Select(group => GetSpecialistId(group.Key)).ToList()
            };
        }

        private static SubagentProfile BuildSpecialist(string group, List<ToolMetadata> tools)
        {
            var template = GetTemplate(group);

            return new SubagentProfile
            {
                Id = GetSpecialistId(group),
                Name = template.Name,
                Kind = "specialist",
                Group = group,
                Description = template.Description,
                DefaultEnabled = DefaultEnabledGroups.Contains(group),
                ActivationGroup = group,
                Tools = tools.Select(tool => tool.Name).ToList(),
                WhenToUse = template.WhenToUse,
                Workflow = template.Workflow,
                HandoffTargets = template.HandoffTargets
            };
        }

        private static SpecialistTemplate GetTemplate(string group)
        {
            if (Templates.TryGetValue(group, out var template))
            {
                return template;
            }

            string title = string.IsNullOrWhiteSpace(group) ? "Unity Specialist" : $"Unity {ToTitle(group)} Specialist";
            return new SpecialistTemplate(
                title,
                $"Handles the '{group}' tool family exposed by this Unity plugin.",
                new[]
                {
                    $"Tasks centered on the {group} tool family.",
                    "Focused work that should stay scoped to one tool group."
                },
                new[]
                {
                    "Inspect the current state before mutating.",
                    "Keep changes narrow and verifiable.",
                    "Escalate to testing after wide-scope edits."
                },
                new[]
                {
                    "unity-testing-specialist",
                    "unity-core-specialist"
                }
            );
        }

        private static string GetSpecialistId(string group)
        {
            string normalized = (group ?? "custom").Replace("_", "-").ToLowerInvariant();
            return $"unity-{normalized}-specialist";
        }

        private static string GetGroupSortKey(string group)
        {
            if (string.Equals(group, "core", StringComparison.OrdinalIgnoreCase))
            {
                return "0-core";
            }

            return $"1-{group}";
        }

        private static string ToTitle(string group)
        {
            var parts = (group ?? string.Empty)
                .Split(new[] { '_', '-', ' ' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(part => char.ToUpperInvariant(part[0]) + part.Substring(1).ToLowerInvariant());
            return string.Join(" ", parts);
        }
    }
}
