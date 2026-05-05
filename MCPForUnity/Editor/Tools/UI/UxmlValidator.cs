using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml;
using System.Xml.Linq;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

namespace MCPForUnity.Editor.Tools.UI
{
    /// <summary>
    /// Validation helpers for UXML and USS — implements `manage_ui` actions
    /// `validate_uxml` and `validate_uss`. The goal is a "preview before write"
    /// path that catches typos (unknown elements, malformed XML, broken USS
    /// selectors) without needing to enter Play mode.
    ///
    /// Validation strategy:
    ///   1. If `content` is provided, write it to a sandbox folder under
    ///      `Assets/__McpUxmlValidate_Temp__/`, otherwise re-import the asset
    ///      already on disk at `path`.
    ///   2. Subscribe to `Application.logMessageReceived` while
    ///      `AssetDatabase.ImportAsset(..., ForceUpdate)` runs — Unity's UXML/USS
    ///      importers route parse errors through the log handler.
    ///   3. Load the asset via AssetDatabase. A null result means the import
    ///      surface failed; a non-null result with no captured errors counts as
    ///      valid. We additionally pre-parse UXML with `XDocument.Parse` so we
    ///      get a real `(line, column, message)` triple for malformed XML before
    ///      Unity ever sees the file.
    /// </summary>
    internal static class UxmlValidator
    {
        private const string TempFolder = "Assets/__McpUxmlValidate_Temp__";

        private static readonly HashSet<string> BuiltinUxmlElementNames = new(StringComparer.Ordinal)
        {
            // Common engine-level visual elements. Used for hint-only diagnostics; the
            // authoritative source is Unity's importer, but flagging obvious typos
            // (e.g. "Buton") with a helpful suggestion is strictly additive.
            "UXML", "Style", "Template", "Instance", "AttributeOverrides", "AttributeOverride",
            "VisualElement", "BindableElement", "Box", "ScrollView", "ListView", "TreeView",
            "GroupBox", "TwoPaneSplitView", "Foldout", "Label", "Button", "Toggle", "Scroller",
            "TextField", "Toolbar", "ToolbarButton", "ToolbarMenu", "ToolbarSpacer",
            "ToolbarToggle", "ToolbarSearchField", "Image", "RepeatButton", "PopupWindow",
            "IMGUIContainer", "Slider", "SliderInt", "MinMaxSlider", "ProgressBar",
            "DropdownField", "EnumField", "MaskField", "LayerMaskField", "LayerField",
            "TagField", "RadioButton", "RadioButtonGroup", "IntegerField", "FloatField",
            "LongField", "DoubleField", "Hash128Field", "Vector2Field", "Vector3Field",
            "Vector4Field", "RectField", "BoundsField", "Vector2IntField", "Vector3IntField",
            "RectIntField", "BoundsIntField", "ColorField", "CurveField", "GradientField",
            "ObjectField", "HelpBox", "Card", "UnsignedIntegerField", "UnsignedLongField"
        };

        public static object ValidateUxml(JObject @params)
        {
            var p = new ToolParams(@params);
            string path = p.Get("path");
            string content = p.Get("content") ?? p.Get("contents");

            bool hasPath = !string.IsNullOrEmpty(path);
            bool hasContent = !string.IsNullOrEmpty(content);

            if (!hasPath && !hasContent)
            {
                return new ErrorResponse("validate_uxml requires either 'path' or 'content'.");
            }

            string assetPath;
            string tempPathToCleanup = null;
            try
            {
                if (hasContent)
                {
                    assetPath = WriteTempAsset(content, ".uxml", out tempPathToCleanup);
                }
                else
                {
                    assetPath = AssetPathUtility.SanitizeAssetPath(path);
                    if (assetPath == null)
                        return new ErrorResponse("Invalid path: contains traversal sequences.");
                    if (!assetPath.EndsWith(".uxml", StringComparison.OrdinalIgnoreCase))
                        return new ErrorResponse("'path' must point to a .uxml file.");

                    string fullPath = AssetsRelativeToFullPath(assetPath);
                    if (!File.Exists(fullPath))
                        return new ErrorResponse($"File not found: {assetPath}");

                    content = File.ReadAllText(fullPath, Encoding.UTF8);
                }

                var errors = new List<ValidationError>();

                // Step 1: lexical/XML well-formedness via XDocument. This gives us
                // real line/column for typos like missing closing tags. Unity's
                // importer would report the same via console, but the line info
                // is unreliable across versions — XDocument is dependable.
                XDocument doc = null;
                try
                {
                    doc = XDocument.Parse(content, LoadOptions.SetLineInfo);
                }
                catch (XmlException xex)
                {
                    errors.Add(new ValidationError
                    {
                        line = xex.LineNumber,
                        column = xex.LinePosition,
                        message = xex.Message,
                        severity = "error",
                        source = "xml"
                    });
                }

                // Step 2: Unity importer pass — captures factory/registration errors
                // (e.g. <Buton/> -> "Element 'Buton' is not known"). We only run this
                // if XML at least parsed; otherwise Unity will just complain about XML.
                int elementCount = 0;
                if (doc != null)
                {
                    var capturedLogs = new List<string>();
                    Application.LogCallback handler = (string msg, string stack, LogType type) =>
                    {
                        if (type == LogType.Error || type == LogType.Exception || type == LogType.Warning)
                        {
                            if (LooksLikeUxmlImporterMessage(msg))
                                capturedLogs.Add(msg);
                        }
                    };

                    Application.logMessageReceived += handler;
                    VisualTreeAsset vta = null;
                    try
                    {
                        AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);
                        vta = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(assetPath);
                    }
                    finally
                    {
                        Application.logMessageReceived -= handler;
                    }

                    foreach (var raw in capturedLogs)
                        errors.Add(ParseUxmlImporterMessage(raw));

                    if (vta != null)
                    {
                        try
                        {
                            var clone = vta.CloneTree();
                            if (clone != null)
                                elementCount = CountVisualElements(clone);
                        }
                        catch (Exception ex)
                        {
                            errors.Add(new ValidationError
                            {
                                line = 0,
                                column = 0,
                                message = $"CloneTree threw: {ex.Message}",
                                severity = "error",
                                source = "clone"
                            });
                        }
                    }
                    else if (errors.Count == 0)
                    {
                        errors.Add(new ValidationError
                        {
                            line = 0,
                            column = 0,
                            message = "Unity could not load the file as a VisualTreeAsset (no specific error surfaced).",
                            severity = "error",
                            source = "import"
                        });
                    }

                    // Hint pass: walk the parsed tree and flag obvious unknown engine-level
                    // names (e.g. <ui:Buton/>). User-defined custom elements with a fully
                    // qualified namespace are intentionally skipped.
                    AddUnknownElementHints(doc, errors);
                }

                bool valid = errors.All(e => e.severity != "error");
                return new SuccessResponse(
                    valid ? "UXML parsed successfully" : "UXML failed validation",
                    new
                    {
                        valid,
                        path = hasPath ? path : null,
                        elementCount,
                        errors = errors.Select(e => (object)new
                        {
                            line = e.line,
                            column = e.column,
                            message = e.message,
                            severity = e.severity,
                            source = e.source
                        }).ToList()
                    });
            }
            catch (Exception ex)
            {
                return new ErrorResponse(ex.Message, new { stackTrace = ex.StackTrace });
            }
            finally
            {
                CleanupTemp(tempPathToCleanup);
            }
        }

        public static object ValidateUss(JObject @params)
        {
            var p = new ToolParams(@params);
            string path = p.Get("path");
            string content = p.Get("content") ?? p.Get("contents");

            bool hasPath = !string.IsNullOrEmpty(path);
            bool hasContent = !string.IsNullOrEmpty(content);

            if (!hasPath && !hasContent)
            {
                return new ErrorResponse("validate_uss requires either 'path' or 'content'.");
            }

            string assetPath;
            string tempPathToCleanup = null;
            try
            {
                if (hasContent)
                {
                    assetPath = WriteTempAsset(content, ".uss", out tempPathToCleanup);
                }
                else
                {
                    assetPath = AssetPathUtility.SanitizeAssetPath(path);
                    if (assetPath == null)
                        return new ErrorResponse("Invalid path: contains traversal sequences.");
                    if (!assetPath.EndsWith(".uss", StringComparison.OrdinalIgnoreCase))
                        return new ErrorResponse("'path' must point to a .uss file.");

                    string fullPath = AssetsRelativeToFullPath(assetPath);
                    if (!File.Exists(fullPath))
                        return new ErrorResponse($"File not found: {assetPath}");
                }

                var errors = new List<ValidationError>();
                var capturedLogs = new List<string>();

                Application.LogCallback handler = (string msg, string stack, LogType type) =>
                {
                    if (type == LogType.Error || type == LogType.Exception || type == LogType.Warning)
                    {
                        if (LooksLikeUssImporterMessage(msg))
                            capturedLogs.Add(msg);
                    }
                };

                Application.logMessageReceived += handler;
                StyleSheet sheet = null;
                try
                {
                    AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);
                    sheet = AssetDatabase.LoadAssetAtPath<StyleSheet>(assetPath);
                }
                finally
                {
                    Application.logMessageReceived -= handler;
                }

                foreach (var raw in capturedLogs)
                    errors.Add(ParseUssImporterMessage(raw));

                if (sheet == null && errors.Count == 0)
                {
                    errors.Add(new ValidationError
                    {
                        line = 0,
                        column = 0,
                        message = "Unity could not load the file as a StyleSheet (no specific error surfaced).",
                        severity = "error",
                        source = "import"
                    });
                }

                int ruleCount = 0;
                if (sheet != null)
                {
                    // StyleSheet exposes complexSelectors (rule blocks) reflectively via
                    // serialized fields in some Unity versions; fall back to 0 if absent.
                    var complexSelectorsField = typeof(StyleSheet).GetProperty(
                        "complexSelectors", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
                    if (complexSelectorsField != null)
                    {
                        var arr = complexSelectorsField.GetValue(sheet) as Array;
                        if (arr != null) ruleCount = arr.Length;
                    }
                }

                bool valid = errors.All(e => e.severity != "error");
                return new SuccessResponse(
                    valid ? "USS parsed successfully" : "USS failed validation",
                    new
                    {
                        valid,
                        path = hasPath ? path : null,
                        ruleCount,
                        errors = errors.Select(e => (object)new
                        {
                            line = e.line,
                            column = e.column,
                            message = e.message,
                            severity = e.severity,
                            source = e.source
                        }).ToList()
                    });
            }
            catch (Exception ex)
            {
                return new ErrorResponse(ex.Message, new { stackTrace = ex.StackTrace });
            }
            finally
            {
                CleanupTemp(tempPathToCleanup);
            }
        }

        // ---------- internals ----------

        private class ValidationError
        {
            public int line;
            public int column;
            public string message;
            public string severity; // "error" | "warning"
            public string source;   // "xml" | "import" | "hint" | "clone"
        }

        private static string WriteTempAsset(string content, string extension, out string assetPathToCleanup)
        {
            if (!AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.CreateFolder("Assets", "__McpUxmlValidate_Temp__");
            }
            string fileName = "validate_" + Guid.NewGuid().ToString("N") + extension;
            string assetPath = TempFolder + "/" + fileName;
            string fullPath = AssetsRelativeToFullPath(assetPath);

            string dir = Path.GetDirectoryName(fullPath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                Directory.CreateDirectory(dir);

            File.WriteAllText(fullPath, content, new UTF8Encoding(false));
            AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceSynchronousImport);

            assetPathToCleanup = assetPath;
            return assetPath;
        }

        private static void CleanupTemp(string assetPath)
        {
            if (string.IsNullOrEmpty(assetPath)) return;
            try
            {
                AssetDatabase.DeleteAsset(assetPath);
                // Best-effort fold cleanup: if the temp folder is now empty, remove it.
                if (AssetDatabase.IsValidFolder(TempFolder))
                {
                    string fullFolder = AssetsRelativeToFullPath(TempFolder);
                    if (Directory.Exists(fullFolder) &&
                        Directory.GetFiles(fullFolder).Length == 0 &&
                        Directory.GetDirectories(fullFolder).Length == 0)
                    {
                        AssetDatabase.DeleteAsset(TempFolder);
                    }
                }
            }
            catch { /* swallow — temp cleanup is best-effort */ }
        }

        private static string AssetsRelativeToFullPath(string assetsRelative)
        {
            // Convert "Assets/foo/bar" -> absolute path under Application.dataPath.
            if (string.IsNullOrEmpty(assetsRelative)) return null;
            if (!assetsRelative.StartsWith("Assets", StringComparison.Ordinal)) return null;
            string suffix = assetsRelative.Length > "Assets".Length
                ? assetsRelative.Substring("Assets".Length).TrimStart('/', '\\')
                : "";
            string combined = string.IsNullOrEmpty(suffix)
                ? Application.dataPath
                : Path.Combine(Application.dataPath, suffix);
            return combined.Replace('/', Path.DirectorySeparatorChar);
        }

        private static bool LooksLikeUxmlImporterMessage(string msg)
        {
            if (string.IsNullOrEmpty(msg)) return false;
            // Heuristic: avoid swallowing unrelated console noise. Match common UXML
            // importer phrases.
            return msg.IndexOf(".uxml", StringComparison.OrdinalIgnoreCase) >= 0
                || msg.IndexOf("UXML", StringComparison.Ordinal) >= 0
                || msg.IndexOf("VisualTreeAsset", StringComparison.Ordinal) >= 0
                || msg.IndexOf("UxmlFactory", StringComparison.Ordinal) >= 0
                || msg.IndexOf("UxmlTraits", StringComparison.Ordinal) >= 0
                || msg.IndexOf("VisualElement", StringComparison.Ordinal) >= 0
                || msg.IndexOf("registered factory", StringComparison.OrdinalIgnoreCase) >= 0
                || msg.IndexOf("XmlException", StringComparison.Ordinal) >= 0;
        }

        private static bool LooksLikeUssImporterMessage(string msg)
        {
            if (string.IsNullOrEmpty(msg)) return false;
            return msg.IndexOf(".uss", StringComparison.OrdinalIgnoreCase) >= 0
                || msg.IndexOf("USS", StringComparison.Ordinal) >= 0
                || msg.IndexOf("StyleSheet", StringComparison.Ordinal) >= 0
                || msg.IndexOf("Selector", StringComparison.OrdinalIgnoreCase) >= 0
                || msg.IndexOf("syntax", StringComparison.OrdinalIgnoreCase) >= 0;
        }

        private static readonly Regex LineColRegex = new Regex(
            @"\((?<line>\d+)\s*[,:]\s*(?<col>\d+)\)|line\s+(?<line2>\d+)",
            RegexOptions.IgnoreCase | RegexOptions.Compiled);

        private static ValidationError ParseUxmlImporterMessage(string raw)
        {
            var (line, col) = ExtractLineCol(raw);
            return new ValidationError
            {
                line = line,
                column = col,
                message = raw.Trim(),
                severity = raw.IndexOf("warning", StringComparison.OrdinalIgnoreCase) >= 0 ? "warning" : "error",
                source = "import"
            };
        }

        private static ValidationError ParseUssImporterMessage(string raw)
        {
            var (line, col) = ExtractLineCol(raw);
            return new ValidationError
            {
                line = line,
                column = col,
                message = raw.Trim(),
                severity = raw.IndexOf("warning", StringComparison.OrdinalIgnoreCase) >= 0 ? "warning" : "error",
                source = "import"
            };
        }

        private static (int line, int column) ExtractLineCol(string raw)
        {
            if (string.IsNullOrEmpty(raw)) return (0, 0);
            var m = LineColRegex.Match(raw);
            if (!m.Success) return (0, 0);
            int line = 0, col = 0;
            if (m.Groups["line"].Success) int.TryParse(m.Groups["line"].Value, out line);
            else if (m.Groups["line2"].Success) int.TryParse(m.Groups["line2"].Value, out line);
            if (m.Groups["col"].Success) int.TryParse(m.Groups["col"].Value, out col);
            return (line, col);
        }

        private static int CountVisualElements(VisualElement root)
        {
            if (root == null) return 0;
            int count = 1;
            for (int i = 0; i < root.childCount; i++)
                count += CountVisualElements(root[i]);
            return count;
        }

        private static void AddUnknownElementHints(XDocument doc, List<ValidationError> errors)
        {
            if (doc?.Root == null) return;
            foreach (var el in doc.Descendants())
            {
                string ns = el.Name.NamespaceName ?? "";
                bool isEngineNs = ns.Length == 0
                    || ns.IndexOf("UnityEngine.UIElements", StringComparison.Ordinal) >= 0
                    || ns.IndexOf("UnityEditor.UIElements", StringComparison.Ordinal) >= 0;
                if (!isEngineNs) continue; // user-namespaced custom controls — skip

                string local = el.Name.LocalName;
                if (BuiltinUxmlElementNames.Contains(local)) continue;

                // Don't double-report if Unity already complained.
                bool alreadyReported = errors.Any(e =>
                    e.source == "import" &&
                    e.message.IndexOf(local, StringComparison.Ordinal) >= 0);
                if (alreadyReported) continue;

                var lineInfo = (IXmlLineInfo)el;
                string suggestion = SuggestClosestBuiltin(local);
                string msg = string.IsNullOrEmpty(suggestion)
                    ? $"Unknown element '{local}'."
                    : $"Unknown element '{local}'. Did you mean '{suggestion}'?";

                errors.Add(new ValidationError
                {
                    line = lineInfo.HasLineInfo() ? lineInfo.LineNumber : 0,
                    column = lineInfo.HasLineInfo() ? lineInfo.LinePosition : 0,
                    message = msg,
                    severity = "warning", // "hint", really — Unity may still resolve via custom factory
                    source = "hint"
                });
            }
        }

        private static string SuggestClosestBuiltin(string typo)
        {
            if (string.IsNullOrEmpty(typo)) return null;
            string best = null;
            int bestDist = int.MaxValue;
            foreach (var name in BuiltinUxmlElementNames)
            {
                int d = LevenshteinDistance(typo, name);
                if (d < bestDist)
                {
                    bestDist = d;
                    best = name;
                }
            }
            // Only suggest if the edit distance is small relative to the name length —
            // otherwise the suggestion is noise.
            return bestDist <= Math.Max(1, typo.Length / 3) ? best : null;
        }

        private static int LevenshteinDistance(string a, string b)
        {
            if (a == b) return 0;
            if (string.IsNullOrEmpty(a)) return b?.Length ?? 0;
            if (string.IsNullOrEmpty(b)) return a.Length;
            var d = new int[a.Length + 1, b.Length + 1];
            for (int i = 0; i <= a.Length; i++) d[i, 0] = i;
            for (int j = 0; j <= b.Length; j++) d[0, j] = j;
            for (int i = 1; i <= a.Length; i++)
            {
                for (int j = 1; j <= b.Length; j++)
                {
                    int cost = a[i - 1] == b[j - 1] ? 0 : 1;
                    d[i, j] = Math.Min(
                        Math.Min(d[i - 1, j] + 1, d[i, j - 1] + 1),
                        d[i - 1, j - 1] + cost);
                }
            }
            return d[a.Length, b.Length];
        }
    }
}
