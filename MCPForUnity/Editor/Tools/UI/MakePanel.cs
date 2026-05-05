using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.UI
{
    /// <summary>
    /// MCP tool that scaffolds UI Toolkit panels from named templates. Generates
    /// a .uxml referencing a packaged component (Modal, LevelUpChoice) plus a
    /// sibling .uss for user customization. Token + component stylesheets are
    /// referenced via project URIs so the generated panel works anywhere under
    /// Assets/.
    ///
    /// Templates are looked up via <see cref="MakePanelTemplateRegistry"/>.
    /// Built-ins (modal, level_up, loading_screen, confirm_dialog, picker,
    /// slotted) are registered at editor-init time. Project code can register
    /// additional templates from an [InitializeOnLoad] static ctor — no edit
    /// to this file required.
    ///
    /// Actions:
    ///   generate         — write .uxml + .uss for the given template.
    ///   attach_to_scene  — delegate to manage_ui's attach_ui_document action.
    ///   list_templates   — return all registered template names + aliases.
    /// </summary>
    [McpForUnityTool("make_panel", AutoRegister = false, Group = "ui")]
    public static class MakePanel
    {
        private const string PackageName = "com.customgamedev.unity-mcp";
        private const string TokensUri = "project://database/Packages/" + PackageName + "/Runtime/UI/Tokens/tokens.uss";
        private const string ModalUssUri = "project://database/Packages/" + PackageName + "/Runtime/UI/Components/Modal/Modal.uss";
        private const string LevelUpUssUri = "project://database/Packages/" + PackageName + "/Runtime/UI/Components/LevelUpChoice/LevelUpChoice.uss";

        private const string ModalTypeFullName = "MCPForUnity.UIElements.Modal";
        private const string LevelUpTypeFullName = "MCPForUnity.UIElements.LevelUpChoice";

        static MakePanel()
        {
            // Self-register modal + level_up so the registry is the single
            // source of truth for available templates. The generators close
            // over BuildModalUxml / BuildLevelUpUxml + BuildPanelUssShell to
            // keep their generated output byte-for-byte stable for callers
            // (and existing tests).
            MakePanelTemplateRegistry.RegisterBuiltin(
                "modal",
                (inner, ussFileName) => new MakePanelTemplateResult(
                    BuildModalUxml(inner, ussFileName),
                    BuildPanelUssShell("modal", ussFileName),
                    ModalTypeFullName));

            MakePanelTemplateRegistry.RegisterBuiltin(
                "level_up",
                (inner, ussFileName) => new MakePanelTemplateResult(
                    BuildLevelUpUxml(inner, ussFileName),
                    BuildPanelUssShell("level_up", ussFileName),
                    LevelUpTypeFullName),
                aliases: new[] { "levelup", "level-up" });
        }

        public static object HandleCommand(JObject @params)
        {
            if (@params == null) return new ErrorResponse("Parameters object is required.");

            string action = @params["action"]?.ToString()?.ToLowerInvariant();
            if (string.IsNullOrEmpty(action))
            {
                action = "generate"; // default action
            }

            try
            {
                switch (action)
                {
                    case "generate":
                        return Generate(@params);

                    case "attach_to_scene":
                    case "attach":
                        return AttachToScene(@params);

                    case "list_templates":
                    case "list":
                    case "templates":
                        return ListTemplates();

                    default:
                        return new ErrorResponse($"Unknown action: {action}. Valid actions: generate, attach_to_scene, list_templates.");
                }
            }
            catch (Exception ex)
            {
                return new ErrorResponse(ex.Message, new { stackTrace = ex.StackTrace });
            }
        }

        private static object ListTemplates()
        {
            var aliasMap = MakePanelTemplateRegistry.GetAliasMap();
            var sortedNames = new List<string>(aliasMap.Keys);
            sortedNames.Sort(StringComparer.OrdinalIgnoreCase);

            var entries = new List<object>(sortedNames.Count);
            foreach (var name in sortedNames)
            {
                entries.Add(new
                {
                    name,
                    aliases = aliasMap[name],
                });
            }

            return new SuccessResponse(
                $"Found {entries.Count} registered make_panel templates.",
                new
                {
                    templates = entries,
                    count = entries.Count,
                });
        }

        private static object Generate(JObject @params)
        {
            var p = new ToolParams(@params);

            string template = p.Get("template")?.ToLowerInvariant();
            if (string.IsNullOrEmpty(template))
            {
                string supported = string.Join(", ", MakePanelTemplateRegistry.GetCanonicalNames());
                return new ErrorResponse($"'template' is required. Supported: {supported}.");
            }

            var pathResult = p.GetRequired("outputPath", "'outputPath' is required (e.g. 'Assets/UI/MyPanel.uxml').");
            var pathError = pathResult.GetOrError(out string rawOutputPath);
            if (pathError != null) return pathError;

            string uxmlPath = AssetPathUtility.SanitizeAssetPath(rawOutputPath);
            if (uxmlPath == null || !AssetPathUtility.IsValidAssetPath(uxmlPath))
            {
                return new ErrorResponse($"Invalid outputPath: '{rawOutputPath}'.");
            }
            if (!uxmlPath.EndsWith(".uxml", StringComparison.OrdinalIgnoreCase))
            {
                return new ErrorResponse($"outputPath must end in '.uxml'. Got: '{uxmlPath}'.");
            }

            bool overwrite = p.GetBool("overwrite", false);
            string ussPath = Path.ChangeExtension(uxmlPath, ".uss").Replace('\\', '/');
            string ussFileName = Path.GetFileName(ussPath);

            JObject inner = @params["params"] as JObject ?? new JObject();

            if (!MakePanelTemplateRegistry.TryGet(template, out var generator))
            {
                string supported = string.Join(", ", MakePanelTemplateRegistry.GetCanonicalNames());
                return new ErrorResponse($"Unknown template: '{template}'. Supported: {supported}.");
            }

            MakePanelTemplateResult result;
            try
            {
                result = generator(inner, ussFileName);
            }
            catch (Exception ex)
            {
                return new ErrorResponse(
                    $"Template generator '{template}' threw: {ex.Message}",
                    new { stackTrace = ex.StackTrace });
            }

            string uxmlContent = result.UxmlContent;
            string ussContent = result.UssContent;
            string componentTypeFullName = result.ComponentTypeFullName;

            if (string.IsNullOrEmpty(uxmlContent))
            {
                return new ErrorResponse($"Template '{template}' returned empty UXML.");
            }
            if (ussContent == null)
            {
                // Empty stylesheet is fine, but null is a generator bug — guard it.
                ussContent = string.Empty;
            }

            // Write USS first so the AssetDatabase already knows about the
            // sibling stylesheet by the time it semantic-validates the .uxml's
            // <ui:Style src="..."> references during ImportAsset.
            string ussError = WriteAssetText(ussPath, ussContent, overwrite);
            if (ussError != null) return new ErrorResponse(ussError);

            string uxmlError = WriteAssetText(uxmlPath, uxmlContent, overwrite);
            if (uxmlError != null) return new ErrorResponse(uxmlError);

            return new SuccessResponse(
                $"Generated {template} panel at {uxmlPath}",
                new
                {
                    uxmlPath,
                    ussPath,
                    componentTypeFullName,
                    template,
                });
        }

        private static object AttachToScene(JObject @params)
        {
            var p = new ToolParams(@params);

            string outputPath = p.Get("outputPath") ?? p.Get("source_asset") ?? p.Get("uxmlPath");
            if (string.IsNullOrEmpty(outputPath))
            {
                return new ErrorResponse("'outputPath' (or source_asset) is required for attach_to_scene.");
            }

            string target = p.Get("target");
            if (string.IsNullOrEmpty(target))
            {
                return new ErrorResponse("'target' GameObject path is required for attach_to_scene.");
            }

            // Translate to manage_ui's attach_ui_document shape and delegate so
            // we don't duplicate UIDocument / PanelSettings handling.
            var attachParams = new JObject
            {
                ["action"] = "attach_ui_document",
                ["target"] = target,
                ["source_asset"] = outputPath,
            };

            string panelSettings = p.Get("panel_settings") ?? p.Get("panelSettings");
            if (!string.IsNullOrEmpty(panelSettings))
            {
                attachParams["panel_settings"] = panelSettings;
            }

            int? sortOrder = p.GetInt("sort_order") ?? p.GetInt("sortOrder");
            if (sortOrder.HasValue)
            {
                attachParams["sort_order"] = sortOrder.Value;
            }

            return ManageUI.HandleCommand(attachParams);
        }

        // -------------------- UXML builders --------------------

        private static string BuildModalUxml(JObject inner, string ussFileName)
        {
            string title = EscapeAttr(inner["title"]?.ToString() ?? "Modal");
            bool showCloseButton = ParamCoercion.CoerceBool(inner["showCloseButton"] ?? inner["show_close_button"], true);
            bool openOnAttach = ParamCoercion.CoerceBool(inner["openOnAttach"] ?? inner["open_on_attach"], false);
            string bodyText = inner["bodyText"]?.ToString() ?? inner["body_text"]?.ToString();
            string bodyXml = inner["bodyXml"]?.ToString() ?? inner["body_xml"]?.ToString();

            string bodyContent;
            if (!string.IsNullOrEmpty(bodyXml))
            {
                bodyContent = bodyXml;
            }
            else if (!string.IsNullOrEmpty(bodyText))
            {
                bodyContent = $"        <ui:Label text=\"{EscapeAttr(bodyText)}\" class=\"modal__body-text\" />";
            }
            else
            {
                bodyContent = string.Empty;
            }

            var sb = new StringBuilder();
            sb.AppendLine("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
            sb.AppendLine("<!--");
            sb.AppendLine("    Generated by MCPForUnity make_panel (template: modal).");
            sb.AppendLine("    Tokens: tokens.uss; component: Modal.uss; user overrides: " + ussFileName);
            sb.AppendLine("-->");
            sb.AppendLine("<ui:UXML xmlns:ui=\"UnityEngine.UIElements\" xmlns:mcp=\"MCPForUnity.UIElements\">");
            sb.AppendLine($"    <ui:Style src=\"{TokensUri}\" />");
            sb.AppendLine($"    <ui:Style src=\"{ModalUssUri}\" />");
            sb.AppendLine($"    <ui:Style src=\"{ussFileName}\" />");
            sb.Append("    <mcp:Modal");
            sb.Append($" title=\"{title}\"");
            sb.Append($" show-close-button=\"{(showCloseButton ? "true" : "false")}\"");
            sb.Append($" open-on-attach=\"{(openOnAttach ? "true" : "false")}\"");
            if (string.IsNullOrEmpty(bodyContent))
            {
                sb.AppendLine(" />");
            }
            else
            {
                sb.AppendLine(">");
                sb.AppendLine(bodyContent);
                sb.AppendLine("    </mcp:Modal>");
            }
            sb.AppendLine("</ui:UXML>");
            return sb.ToString();
        }

        private static string BuildLevelUpUxml(JObject inner, string ussFileName)
        {
            string title = EscapeAttr(inner["title"]?.ToString() ?? "Level Up!");
            JArray choices = inner["choices"] as JArray ?? new JArray();

            var sb = new StringBuilder();
            sb.AppendLine("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
            sb.AppendLine("<!--");
            sb.AppendLine("    Generated by MCPForUnity make_panel (template: level_up).");
            sb.AppendLine("    Tokens: tokens.uss; component: LevelUpChoice.uss; user overrides: " + ussFileName);
            sb.AppendLine("-->");
            sb.AppendLine("<ui:UXML xmlns:ui=\"UnityEngine.UIElements\" xmlns:mcp=\"MCPForUnity.UIElements\">");
            sb.AppendLine($"    <ui:Style src=\"{TokensUri}\" />");
            sb.AppendLine($"    <ui:Style src=\"{LevelUpUssUri}\" />");
            sb.AppendLine($"    <ui:Style src=\"{ussFileName}\" />");
            sb.AppendLine($"    <mcp:LevelUpChoice title=\"{title}\">");

            for (int i = 0; i < choices.Count; i++)
            {
                var choice = choices[i] as JObject ?? new JObject();
                AppendChoiceCard(sb, choice, i);
            }

            sb.AppendLine("    </mcp:LevelUpChoice>");
            sb.AppendLine("</ui:UXML>");
            return sb.ToString();
        }

        private static void AppendChoiceCard(StringBuilder sb, JObject choice, int index)
        {
            string name = EscapeAttr(choice["name"]?.ToString() ?? $"Choice {index + 1}");
            string description = EscapeAttr(choice["description"]?.ToString() ?? string.Empty);
            string rarity = (choice["rarity"]?.ToString() ?? "common").ToLowerInvariant();
            bool isPrimary = ParamCoercion.CoerceBool(choice["isPrimary"] ?? choice["is_primary"], false);

            string rarityClass = rarity switch
            {
                "uncommon" => "luc-card--rarity-uncommon",
                "rare" => "luc-card--rarity-rare",
                "epic" => "luc-card--rarity-epic",
                "legendary" => "luc-card--rarity-legendary",
                _ => "luc-card--rarity-common",
            };

            string classes = "luc-card " + rarityClass;
            if (isPrimary) classes += " luc-card--primary";

            sb.AppendLine($"        <ui:VisualElement name=\"luc-card-{index}\" class=\"{classes}\">");
            sb.AppendLine($"            <ui:VisualElement name=\"luc-card-{index}__icon\" class=\"luc-card__icon\" />");
            sb.AppendLine($"            <ui:Label name=\"luc-card-{index}__name\" class=\"luc-card__name\" text=\"{name}\" />");
            sb.AppendLine($"            <ui:Label name=\"luc-card-{index}__description\" class=\"luc-card__description\" text=\"{description}\" />");
            sb.AppendLine($"            <ui:Button name=\"luc-card-{index}__pick\" class=\"luc-card__pick\" text=\"Pick\" />");
            sb.AppendLine("        </ui:VisualElement>");
        }

        private static string BuildPanelUssShell(string template, string ussFileName)
        {
            // The user-side override stylesheet starts mostly empty — token and
            // component styles already provide the look. This file is the place
            // for instance-level tweaks.
            var sb = new StringBuilder();
            sb.AppendLine("/*");
            sb.AppendLine($" * {ussFileName} — generated by MCPForUnity make_panel (template: {template}).");
            sb.AppendLine(" * This stylesheet rides alongside the .uxml as a place for instance-specific");
            sb.AppendLine(" * overrides. Token + component styles are loaded from the package via");
            sb.AppendLine(" * <ui:Style> references in the .uxml; you don't need to redeclare them here.");
            sb.AppendLine(" */");
            sb.AppendLine();
            return sb.ToString();
        }

        // -------------------- File writer --------------------

        /// <summary>
        /// Writes a text asset under Assets/. Returns null on success, or an error
        /// message string. Pattern mirrors ManageUI.CreateFile() so behavior stays
        /// consistent across UI generation tools.
        /// </summary>
        private static string WriteAssetText(string assetPath, string contents, bool overwrite)
        {
            string fullPath = Path.Combine(Application.dataPath,
                assetPath.Substring("Assets/".Length));
            fullPath = fullPath.Replace('/', Path.DirectorySeparatorChar);

            if (File.Exists(fullPath) && !overwrite)
            {
                return $"File already exists at {assetPath}. Pass overwrite=true to replace.";
            }

            string dir = Path.GetDirectoryName(fullPath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }

            File.WriteAllText(fullPath, contents, Encoding.UTF8);
            AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);
            return null;
        }

        private static string EscapeAttr(string s)
        {
            if (string.IsNullOrEmpty(s)) return string.Empty;
            return s
                .Replace("&", "&amp;")
                .Replace("\"", "&quot;")
                .Replace("<", "&lt;")
                .Replace(">", "&gt;");
        }
    }
}
