using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

namespace MCPForUnity.Editor.Windows.Components
{
    /// <summary>
    /// Shows the plugin's workflow specialists built from the Unity-side tool registry.
    /// </summary>
    public class McpWorkflowsSection
    {
        private readonly VisualElement root;
        private Label summaryLabel;
        private Label noteLabel;
        private Button refreshButton;
        private Button copyJsonButton;
        private VisualElement catalogContainer;

        public McpWorkflowsSection(VisualElement root)
        {
            this.root = root;
            BuildUI();
            RegisterCallbacks();
        }

        public void Refresh()
        {
            catalogContainer?.Clear();

            var catalog = SubagentCatalogBuilder.BuildCatalog();
            summaryLabel.text = $"{catalog.SubagentCount} profiles across {catalog.GroupCount} tool groups.";
            noteLabel.text = $"Default enabled groups: {string.Join(", ", catalog.DefaultEnabledGroups)}.";

            foreach (var profile in catalog.Subagents)
            {
                catalogContainer.Add(CreateProfileCard(profile));
            }
        }

        private void BuildUI()
        {
            root.Clear();

            var section = new VisualElement();
            section.AddToClassList("section");

            var title = new Label("Workflows");
            title.AddToClassList("section-title");
            section.Add(title);

            var content = new VisualElement();
            content.AddToClassList("section-content");

            summaryLabel = new Label("Building workflow catalog...");
            summaryLabel.AddToClassList("help-text");
            content.Add(summaryLabel);

            var actions = new VisualElement();
            actions.AddToClassList("tool-actions");

            var row = new VisualElement();
            row.style.flexDirection = FlexDirection.Row;

            refreshButton = new Button { text = "Refresh" };
            refreshButton.AddToClassList("tool-action-button");
            refreshButton.style.marginRight = 4;
            row.Add(refreshButton);

            copyJsonButton = new Button { text = "Copy JSON" };
            copyJsonButton.AddToClassList("tool-action-button");
            row.Add(copyJsonButton);

            actions.Add(row);
            content.Add(actions);

            noteLabel = new Label();
            noteLabel.AddToClassList("help-text");
            content.Add(noteLabel);

            catalogContainer = new VisualElement();
            catalogContainer.AddToClassList("tool-category-container");
            content.Add(catalogContainer);

            section.Add(content);
            root.Add(section);
        }

        private void RegisterCallbacks()
        {
            refreshButton.clicked += Refresh;
            copyJsonButton.clicked += () =>
            {
                var catalog = SubagentCatalogBuilder.BuildCatalog();
                EditorGUIUtility.systemCopyBuffer = JsonConvert.SerializeObject(catalog, Formatting.Indented);
                ShowTransientStatus("Workflow catalog copied to clipboard.");
            };
        }

        private VisualElement CreateProfileCard(SubagentProfile profile)
        {
            var card = new Foldout
            {
                text = BuildFoldoutTitle(profile),
                value = string.Equals(profile.Kind, "orchestrator", StringComparison.OrdinalIgnoreCase)
            };

            card.Add(CreateDescription(profile.Description));
            card.Add(CreateTagRow(profile));
            card.Add(CreateListBlock("Use when", profile.WhenToUse));
            card.Add(CreateListBlock("Workflow", profile.Workflow));
            card.Add(CreateListBlock("Tools", profile.Tools.Select(tool => $"`{tool}`").ToList()));

            if (profile.HandoffTargets != null && profile.HandoffTargets.Count > 0)
            {
                card.Add(CreateListBlock("Handoffs", profile.HandoffTargets.Select(target => $"`{target}`").ToList()));
            }

            return card;
        }

        private static string BuildFoldoutTitle(SubagentProfile profile)
        {
            int toolCount = profile.Tools?.Count ?? 0;
            return $"{profile.Name} ({toolCount} tools)";
        }

        private static Label CreateDescription(string text)
        {
            var label = new Label(text ?? string.Empty);
            label.AddToClassList("tool-item-description");
            label.style.marginTop = 4;
            return label;
        }

        private static VisualElement CreateTagRow(SubagentProfile profile)
        {
            var row = new VisualElement();
            row.AddToClassList("tool-tags");
            row.style.marginTop = 4;
            row.style.marginBottom = 4;

            row.Add(CreateTag(profile.Kind));

            if (!string.IsNullOrWhiteSpace(profile.Group))
            {
                row.Add(CreateTag($"Group: {profile.Group}"));
            }

            if (profile.DefaultEnabled)
            {
                row.Add(CreateTag("Default"));
            }

            return row;
        }

        private static VisualElement CreateListBlock(string title, IReadOnlyCollection<string> items)
        {
            var container = new VisualElement();
            container.style.marginBottom = 4;

            var titleLabel = new Label(title);
            titleLabel.AddToClassList("help-text");
            titleLabel.style.unityFontStyleAndWeight = FontStyle.Bold;
            container.Add(titleLabel);

            if (items == null || items.Count == 0)
            {
                var empty = new Label("None");
                empty.AddToClassList("tool-item-description");
                container.Add(empty);
                return container;
            }

            foreach (var item in items)
            {
                var row = new Label($"- {item}");
                row.AddToClassList("tool-item-description");
                container.Add(row);
            }

            return container;
        }

        private static Label CreateTag(string text)
        {
            var tag = new Label(text);
            tag.AddToClassList("tool-tag");
            return tag;
        }

        private void ShowTransientStatus(string message)
        {
            noteLabel.text = message;
            noteLabel.schedule.Execute(() =>
            {
                var catalog = SubagentCatalogBuilder.BuildCatalog();
                noteLabel.text = $"Default enabled groups: {string.Join(", ", catalog.DefaultEnabledGroups)}.";
            }).StartingIn(1800);
        }
    }
}
