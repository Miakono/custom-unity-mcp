using System;
using System.Collections.Generic;
using System.Text;
using Newtonsoft.Json.Linq;
using MCPForUnity.Editor.Helpers;

namespace MCPForUnity.Editor.Tools.UI
{
    /// <summary>
    /// Result of a template generator: the .uxml content to write, the .uss
    /// content to write, plus a hint about the primary component type (purely
    /// informational — surfaced back to callers in the response payload).
    /// </summary>
    public readonly struct MakePanelTemplateResult
    {
        public readonly string UxmlContent;
        public readonly string UssContent;
        public readonly string ComponentTypeFullName;

        public MakePanelTemplateResult(string uxmlContent, string ussContent, string componentTypeFullName)
        {
            UxmlContent = uxmlContent;
            UssContent = ussContent;
            ComponentTypeFullName = componentTypeFullName;
        }
    }

    /// <summary>
    /// Signature for a make_panel template generator.
    /// <paramref name="templateParams"/> is the inner "params" JObject the user
    /// passed in — never null. <paramref name="ussFileName"/> is the stem of the
    /// sibling user-overrides .uss file (already determined by make_panel).
    /// </summary>
    public delegate MakePanelTemplateResult MakePanelTemplateGenerator(JObject templateParams, string ussFileName);

    /// <summary>
    /// Registry of template generators for make_panel. Built-in templates
    /// (modal, level_up, loading_screen, confirm_dialog, picker, slotted) are
    /// pre-registered. Project-side code can extend the catalog via
    /// <see cref="Register"/> from an [InitializeOnLoad] static ctor — no edits
    /// to MakePanel.cs required.
    /// </summary>
    public static class MakePanelTemplateRegistry
    {
        private static readonly Dictionary<string, MakePanelTemplateGenerator> s_generators =
            new Dictionary<string, MakePanelTemplateGenerator>(StringComparer.OrdinalIgnoreCase);

        private static readonly Dictionary<string, string[]> s_aliases =
            new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase);

        static MakePanelTemplateRegistry()
        {
            // Built-ins. Modal and level_up generators live in MakePanel.cs to
            // keep their existing UXML byte-for-byte stable; they self-register
            // from MakePanel's static constructor via RegisterBuiltin().
            // The remaining built-ins are defined here.
            Register("loading_screen", BuiltinTemplates.BuildLoadingScreen,
                aliases: new[] { "loading", "loadingscreen" });
            Register("confirm_dialog", BuiltinTemplates.BuildConfirmDialog,
                aliases: new[] { "confirm", "confirmdialog" });
            Register("picker", BuiltinTemplates.BuildPicker,
                aliases: new[] { "list_picker", "listpicker" });
            Register("slotted", BuiltinTemplates.BuildSlotted,
                aliases: new[] { "blank", "content" });
        }

        /// <summary>
        /// Registers a template generator. The canonical name is stored
        /// case-insensitively; any aliases resolve back to the same generator.
        /// Re-registering an existing name overwrites it (later registrations win).
        /// </summary>
        public static void Register(string name, MakePanelTemplateGenerator generator, string[] aliases = null)
        {
            if (string.IsNullOrEmpty(name))
                throw new ArgumentException("Template name must be non-empty.", nameof(name));
            if (generator == null)
                throw new ArgumentNullException(nameof(generator));

            string canonical = name.ToLowerInvariant();
            s_generators[canonical] = generator;

            // Build a fresh alias list (any prior aliases for this name go away).
            var collected = new List<string>();
            if (aliases != null)
            {
                foreach (var a in aliases)
                {
                    if (string.IsNullOrEmpty(a)) continue;
                    string lower = a.ToLowerInvariant();
                    if (lower == canonical) continue;
                    s_generators[lower] = generator;
                    collected.Add(lower);
                }
            }
            s_aliases[canonical] = collected.ToArray();
        }

        public static bool TryGet(string nameOrAlias, out MakePanelTemplateGenerator generator)
        {
            if (string.IsNullOrEmpty(nameOrAlias))
            {
                generator = null;
                return false;
            }
            return s_generators.TryGetValue(nameOrAlias, out generator);
        }

        /// <summary>
        /// Returns canonical names only (no aliases) for discovery responses.
        /// </summary>
        public static IReadOnlyCollection<string> GetCanonicalNames()
        {
            return s_aliases.Keys;
        }

        public static IReadOnlyDictionary<string, string[]> GetAliasMap()
        {
            return s_aliases;
        }

        /// <summary>
        /// Internal hook so MakePanel.cs can register modal/level_up without
        /// having to expose its private builders. Equivalent to <see cref="Register"/>.
        /// </summary>
        internal static void RegisterBuiltin(string name, MakePanelTemplateGenerator generator, string[] aliases = null)
        {
            Register(name, generator, aliases);
        }
    }

    /// <summary>
    /// Generators for the built-in panel templates that use generic
    /// ui:VisualElement scaffolding (no packaged component runtime). These
    /// emit token-styled markup and a small, readable user-overrides .uss.
    /// </summary>
    internal static class BuiltinTemplates
    {
        private const string PackageName = "com.customgamedev.unity-mcp";
        private const string TokensUri = "project://database/Packages/" + PackageName + "/Runtime/UI/Tokens/tokens.uss";

        // ---------- loading_screen ----------

        public static MakePanelTemplateResult BuildLoadingScreen(JObject inner, string ussFileName)
        {
            string title = EscapeAttr(inner["title"]?.ToString() ?? "Loading...");
            string subtitle = EscapeAttr(inner["subtitle"]?.ToString() ?? string.Empty);
            float progress = ParamCoercion.CoerceFloat(inner["progress"], 0f);
            if (progress < 0f) progress = 0f;
            if (progress > 1f) progress = 1f;

            var sb = new StringBuilder();
            sb.AppendLine("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
            sb.AppendLine("<!--");
            sb.AppendLine("    Generated by MCPForUnity make_panel (template: loading_screen).");
            sb.AppendLine("    Tokens: tokens.uss; user overrides: " + ussFileName);
            sb.AppendLine("-->");
            sb.AppendLine("<ui:UXML xmlns:ui=\"UnityEngine.UIElements\">");
            sb.AppendLine($"    <ui:Style src=\"{TokensUri}\" />");
            sb.AppendLine($"    <ui:Style src=\"{ussFileName}\" />");
            sb.AppendLine("    <ui:VisualElement name=\"loading-screen\" class=\"loading-screen\" picking-mode=\"Position\">");
            sb.AppendLine("        <ui:VisualElement name=\"loading-screen__inner\" class=\"loading-screen__inner\">");
            sb.AppendLine($"            <ui:Label name=\"loading-screen__title\" class=\"loading-screen__title\" text=\"{title}\" />");
            if (!string.IsNullOrEmpty(subtitle))
            {
                sb.AppendLine($"            <ui:Label name=\"loading-screen__subtitle\" class=\"loading-screen__subtitle\" text=\"{subtitle}\" />");
            }
            sb.AppendLine("            <ui:VisualElement name=\"loading-screen__bar\" class=\"loading-screen__bar\">");
            sb.AppendLine($"                <ui:VisualElement name=\"loading-screen__bar-fill\" class=\"loading-screen__bar-fill\" style=\"width: {(progress * 100f).ToString("0.##", System.Globalization.CultureInfo.InvariantCulture)}%;\" />");
            sb.AppendLine("            </ui:VisualElement>");
            sb.AppendLine("        </ui:VisualElement>");
            sb.AppendLine("    </ui:VisualElement>");
            sb.AppendLine("</ui:UXML>");

            string uss = LoadingScreenUss(ussFileName);
            return new MakePanelTemplateResult(sb.ToString(), uss, "UnityEngine.UIElements.VisualElement");
        }

        private static string LoadingScreenUss(string ussFileName)
        {
            var sb = new StringBuilder();
            sb.AppendLine("/*");
            sb.AppendLine($" * {ussFileName} — generated by MCPForUnity make_panel (template: loading_screen).");
            sb.AppendLine(" * Full-screen panel with a centered title and a progress bar slot.");
            sb.AppendLine(" * Update #loading-screen__bar-fill width via UQuery to reflect progress (0-100%).");
            sb.AppendLine(" */");
            sb.AppendLine();
            sb.AppendLine(".loading-screen {");
            sb.AppendLine("    flex-grow: 1;");
            sb.AppendLine("    background-color: var(--color-bg);");
            sb.AppendLine("    align-items: center;");
            sb.AppendLine("    justify-content: center;");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".loading-screen__inner {");
            sb.AppendLine("    align-items: center;");
            sb.AppendLine("    justify-content: center;");
            sb.AppendLine("    padding: var(--space-xl);");
            sb.AppendLine("    min-width: 320px;");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".loading-screen__title {");
            sb.AppendLine("    color: var(--color-text-primary);");
            sb.AppendLine("    font-size: var(--text-h2);");
            sb.AppendLine("    -unity-font-style: bold;");
            sb.AppendLine("    margin-bottom: var(--space-md);");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".loading-screen__subtitle {");
            sb.AppendLine("    color: var(--color-text-secondary);");
            sb.AppendLine("    font-size: var(--text-body);");
            sb.AppendLine("    margin-bottom: var(--space-lg);");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".loading-screen__bar {");
            sb.AppendLine("    width: 320px;");
            sb.AppendLine("    height: 8px;");
            sb.AppendLine("    background-color: var(--color-bg-elevated);");
            sb.AppendLine("    border-radius: var(--radius-pill);");
            sb.AppendLine("    overflow: hidden;");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".loading-screen__bar-fill {");
            sb.AppendLine("    height: 100%;");
            sb.AppendLine("    background-color: var(--color-primary);");
            sb.AppendLine("    border-radius: var(--radius-pill);");
            sb.AppendLine("    transition-property: width;");
            sb.AppendLine("    transition-duration: var(--anim-default);");
            sb.AppendLine("}");
            return sb.ToString();
        }

        // ---------- confirm_dialog ----------

        public static MakePanelTemplateResult BuildConfirmDialog(JObject inner, string ussFileName)
        {
            string title = EscapeAttr(inner["title"]?.ToString() ?? "Confirm");
            string body = EscapeAttr(inner["body"]?.ToString() ?? inner["bodyText"]?.ToString() ?? inner["body_text"]?.ToString() ?? "Are you sure?");
            string confirmText = EscapeAttr(inner["confirmText"]?.ToString() ?? inner["confirm_text"]?.ToString() ?? "Confirm");
            string cancelText = EscapeAttr(inner["cancelText"]?.ToString() ?? inner["cancel_text"]?.ToString() ?? "Cancel");
            bool danger = ParamCoercion.CoerceBool(inner["danger"], false);

            var sb = new StringBuilder();
            sb.AppendLine("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
            sb.AppendLine("<!--");
            sb.AppendLine("    Generated by MCPForUnity make_panel (template: confirm_dialog).");
            sb.AppendLine("    Tokens: tokens.uss; user overrides: " + ussFileName);
            sb.AppendLine("    Wire #confirm-yes / #confirm-no via UQuery and RegisterCallback<ClickEvent>.");
            sb.AppendLine("-->");
            sb.AppendLine("<ui:UXML xmlns:ui=\"UnityEngine.UIElements\">");
            sb.AppendLine($"    <ui:Style src=\"{TokensUri}\" />");
            sb.AppendLine($"    <ui:Style src=\"{ussFileName}\" />");
            sb.AppendLine("    <ui:VisualElement name=\"confirm-scrim\" class=\"confirm-scrim\" picking-mode=\"Position\">");
            sb.AppendLine("        <ui:VisualElement name=\"confirm-dialog\" class=\"confirm-dialog\">");
            sb.AppendLine($"            <ui:Label name=\"confirm-title\" class=\"confirm-dialog__title\" text=\"{title}\" />");
            sb.AppendLine($"            <ui:Label name=\"confirm-body\" class=\"confirm-dialog__body\" text=\"{body}\" />");
            sb.AppendLine("            <ui:VisualElement name=\"confirm-actions\" class=\"confirm-dialog__actions\">");
            sb.AppendLine($"                <ui:Button name=\"confirm-no\" class=\"confirm-dialog__button confirm-dialog__button--cancel\" text=\"{cancelText}\" />");
            string confirmClass = danger
                ? "confirm-dialog__button confirm-dialog__button--danger"
                : "confirm-dialog__button confirm-dialog__button--primary";
            sb.AppendLine($"                <ui:Button name=\"confirm-yes\" class=\"{confirmClass}\" text=\"{confirmText}\" />");
            sb.AppendLine("            </ui:VisualElement>");
            sb.AppendLine("        </ui:VisualElement>");
            sb.AppendLine("    </ui:VisualElement>");
            sb.AppendLine("</ui:UXML>");

            return new MakePanelTemplateResult(sb.ToString(), ConfirmDialogUss(ussFileName), "UnityEngine.UIElements.VisualElement");
        }

        private static string ConfirmDialogUss(string ussFileName)
        {
            var sb = new StringBuilder();
            sb.AppendLine("/*");
            sb.AppendLine($" * {ussFileName} — generated by MCPForUnity make_panel (template: confirm_dialog).");
            sb.AppendLine(" * Modal-style dialog with title, body, and yes/no buttons (#confirm-yes, #confirm-no).");
            sb.AppendLine(" */");
            sb.AppendLine();
            sb.AppendLine(".confirm-scrim {");
            sb.AppendLine("    flex-grow: 1;");
            sb.AppendLine("    background-color: var(--color-scrim);");
            sb.AppendLine("    align-items: center;");
            sb.AppendLine("    justify-content: center;");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".confirm-dialog {");
            sb.AppendLine("    background-color: var(--color-bg-elevated);");
            sb.AppendLine("    border-radius: var(--radius-md);");
            sb.AppendLine("    border-width: 1px;");
            sb.AppendLine("    border-color: var(--color-border);");
            sb.AppendLine("    padding: var(--space-lg);");
            sb.AppendLine("    min-width: 320px;");
            sb.AppendLine("    max-width: 480px;");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".confirm-dialog__title {");
            sb.AppendLine("    color: var(--color-text-primary);");
            sb.AppendLine("    font-size: var(--text-h3);");
            sb.AppendLine("    -unity-font-style: bold;");
            sb.AppendLine("    margin-bottom: var(--space-sm);");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".confirm-dialog__body {");
            sb.AppendLine("    color: var(--color-text-secondary);");
            sb.AppendLine("    font-size: var(--text-body);");
            sb.AppendLine("    margin-bottom: var(--space-lg);");
            sb.AppendLine("    white-space: normal;");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".confirm-dialog__actions {");
            sb.AppendLine("    flex-direction: row;");
            sb.AppendLine("    justify-content: flex-end;");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".confirm-dialog__button {");
            sb.AppendLine("    padding: var(--space-sm) var(--space-md);");
            sb.AppendLine("    border-radius: var(--radius-sm);");
            sb.AppendLine("    margin-left: var(--space-sm);");
            sb.AppendLine("    color: var(--color-text-primary);");
            sb.AppendLine("    background-color: var(--color-bg);");
            sb.AppendLine("    border-width: 1px;");
            sb.AppendLine("    border-color: var(--color-border);");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".confirm-dialog__button--cancel:hover {");
            sb.AppendLine("    background-color: var(--color-bg-elevated);");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".confirm-dialog__button--primary {");
            sb.AppendLine("    background-color: var(--color-primary);");
            sb.AppendLine("    border-color: var(--color-primary);");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".confirm-dialog__button--primary:hover {");
            sb.AppendLine("    background-color: var(--color-primary-hover);");
            sb.AppendLine("    border-color: var(--color-primary-hover);");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".confirm-dialog__button--danger {");
            sb.AppendLine("    background-color: var(--color-danger);");
            sb.AppendLine("    border-color: var(--color-danger);");
            sb.AppendLine("}");
            return sb.ToString();
        }

        // ---------- picker ----------

        public static MakePanelTemplateResult BuildPicker(JObject inner, string ussFileName)
        {
            string title = EscapeAttr(inner["title"]?.ToString() ?? "Pick One");
            int itemHeight = (int)ParamCoercion.CoerceFloat(inner["itemHeight"] ?? inner["item_height"], 32f);
            if (itemHeight < 1) itemHeight = 32;
            bool showCancel = ParamCoercion.CoerceBool(inner["showCancel"] ?? inner["show_cancel"], true);

            var sb = new StringBuilder();
            sb.AppendLine("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
            sb.AppendLine("<!--");
            sb.AppendLine("    Generated by MCPForUnity make_panel (template: picker).");
            sb.AppendLine("    Tokens: tokens.uss; user overrides: " + ussFileName);
            sb.AppendLine("    Bind itemsSource and makeItem/bindItem on #picker-list from C#.");
            sb.AppendLine("-->");
            sb.AppendLine("<ui:UXML xmlns:ui=\"UnityEngine.UIElements\">");
            sb.AppendLine($"    <ui:Style src=\"{TokensUri}\" />");
            sb.AppendLine($"    <ui:Style src=\"{ussFileName}\" />");
            sb.AppendLine("    <ui:VisualElement name=\"picker-scrim\" class=\"picker-scrim\" picking-mode=\"Position\">");
            sb.AppendLine("        <ui:VisualElement name=\"picker-dialog\" class=\"picker-dialog\">");
            sb.AppendLine($"            <ui:Label name=\"picker-title\" class=\"picker-dialog__title\" text=\"{title}\" />");
            sb.AppendLine($"            <ui:ListView name=\"picker-list\" class=\"picker-dialog__list\" fixed-item-height=\"{itemHeight}\" virtualization-method=\"FixedHeight\" show-border=\"true\" />");
            if (showCancel)
            {
                sb.AppendLine("            <ui:VisualElement name=\"picker-actions\" class=\"picker-dialog__actions\">");
                sb.AppendLine("                <ui:Button name=\"picker-cancel\" class=\"picker-dialog__cancel\" text=\"Cancel\" />");
                sb.AppendLine("            </ui:VisualElement>");
            }
            sb.AppendLine("        </ui:VisualElement>");
            sb.AppendLine("    </ui:VisualElement>");
            sb.AppendLine("</ui:UXML>");

            return new MakePanelTemplateResult(sb.ToString(), PickerUss(ussFileName), "UnityEngine.UIElements.ListView");
        }

        private static string PickerUss(string ussFileName)
        {
            var sb = new StringBuilder();
            sb.AppendLine("/*");
            sb.AppendLine($" * {ussFileName} — generated by MCPForUnity make_panel (template: picker).");
            sb.AppendLine(" * Modal-style dialog wrapping a ListView (#picker-list) for item selection.");
            sb.AppendLine(" * Bind itemsSource / makeItem / bindItem from C#:");
            sb.AppendLine(" *   var list = root.Q<ListView>(\"picker-list\");");
            sb.AppendLine(" *   list.itemsSource = mySource;");
            sb.AppendLine(" *   list.makeItem = () => new Label();");
            sb.AppendLine(" *   list.bindItem = (e, i) => ((Label)e).text = mySource[i].ToString();");
            sb.AppendLine(" */");
            sb.AppendLine();
            sb.AppendLine(".picker-scrim {");
            sb.AppendLine("    flex-grow: 1;");
            sb.AppendLine("    background-color: var(--color-scrim);");
            sb.AppendLine("    align-items: center;");
            sb.AppendLine("    justify-content: center;");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".picker-dialog {");
            sb.AppendLine("    background-color: var(--color-bg-elevated);");
            sb.AppendLine("    border-radius: var(--radius-md);");
            sb.AppendLine("    border-width: 1px;");
            sb.AppendLine("    border-color: var(--color-border);");
            sb.AppendLine("    padding: var(--space-lg);");
            sb.AppendLine("    min-width: 360px;");
            sb.AppendLine("    max-width: 560px;");
            sb.AppendLine("    max-height: 70%;");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".picker-dialog__title {");
            sb.AppendLine("    color: var(--color-text-primary);");
            sb.AppendLine("    font-size: var(--text-h3);");
            sb.AppendLine("    -unity-font-style: bold;");
            sb.AppendLine("    margin-bottom: var(--space-md);");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".picker-dialog__list {");
            sb.AppendLine("    flex-grow: 1;");
            sb.AppendLine("    min-height: 200px;");
            sb.AppendLine("    background-color: var(--color-bg);");
            sb.AppendLine("    border-radius: var(--radius-sm);");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".picker-dialog__actions {");
            sb.AppendLine("    flex-direction: row;");
            sb.AppendLine("    justify-content: flex-end;");
            sb.AppendLine("    margin-top: var(--space-md);");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".picker-dialog__cancel {");
            sb.AppendLine("    padding: var(--space-sm) var(--space-md);");
            sb.AppendLine("    border-radius: var(--radius-sm);");
            sb.AppendLine("    color: var(--color-text-primary);");
            sb.AppendLine("    background-color: var(--color-bg);");
            sb.AppendLine("    border-width: 1px;");
            sb.AppendLine("    border-color: var(--color-border);");
            sb.AppendLine("}");
            return sb.ToString();
        }

        // ---------- slotted ----------

        public static MakePanelTemplateResult BuildSlotted(JObject inner, string ussFileName)
        {
            string title = inner["title"]?.ToString();
            string rootName = EscapeAttr(inner["rootName"]?.ToString() ?? inner["root_name"]?.ToString() ?? "panel");

            var sb = new StringBuilder();
            sb.AppendLine("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
            sb.AppendLine("<!--");
            sb.AppendLine("    Generated by MCPForUnity make_panel (template: slotted).");
            sb.AppendLine("    Tokens: tokens.uss; user overrides: " + ussFileName);
            sb.AppendLine("    Add your content under #content. The .uxml is intentionally minimal.");
            sb.AppendLine("-->");
            sb.AppendLine("<ui:UXML xmlns:ui=\"UnityEngine.UIElements\">");
            sb.AppendLine($"    <ui:Style src=\"{TokensUri}\" />");
            sb.AppendLine($"    <ui:Style src=\"{ussFileName}\" />");
            sb.AppendLine($"    <ui:VisualElement name=\"{rootName}\" class=\"panel\">");
            if (!string.IsNullOrEmpty(title))
            {
                sb.AppendLine($"        <ui:Label name=\"panel-title\" class=\"panel__title\" text=\"{EscapeAttr(title)}\" />");
            }
            sb.AppendLine("        <ui:VisualElement name=\"content\" class=\"panel__content\" />");
            sb.AppendLine("    </ui:VisualElement>");
            sb.AppendLine("</ui:UXML>");

            return new MakePanelTemplateResult(sb.ToString(), SlottedUss(ussFileName), "UnityEngine.UIElements.VisualElement");
        }

        private static string SlottedUss(string ussFileName)
        {
            var sb = new StringBuilder();
            sb.AppendLine("/*");
            sb.AppendLine($" * {ussFileName} — generated by MCPForUnity make_panel (template: slotted).");
            sb.AppendLine(" * Generic panel with a #content slot. No chrome — drop your hierarchy in.");
            sb.AppendLine(" */");
            sb.AppendLine();
            sb.AppendLine(".panel {");
            sb.AppendLine("    background-color: var(--color-bg);");
            sb.AppendLine("    color: var(--color-text-primary);");
            sb.AppendLine("    padding: var(--space-md);");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".panel__title {");
            sb.AppendLine("    font-size: var(--text-h3);");
            sb.AppendLine("    -unity-font-style: bold;");
            sb.AppendLine("    margin-bottom: var(--space-md);");
            sb.AppendLine("    color: var(--color-text-primary);");
            sb.AppendLine("}");
            sb.AppendLine();
            sb.AppendLine(".panel__content {");
            sb.AppendLine("    flex-grow: 1;");
            sb.AppendLine("}");
            return sb.ToString();
        }

        // ---------- shared ----------

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
