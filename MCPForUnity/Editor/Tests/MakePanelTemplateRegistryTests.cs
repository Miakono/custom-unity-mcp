using System.Collections.Generic;
using System.IO;
using System.Linq;
using MCPForUnity.Editor.Tools.UI;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

namespace MCPForUnity.Editor.Tests
{
    /// <summary>
    /// Verifies the make_panel template registry: list_templates discovery,
    /// alias resolution, and that each non-component built-in template
    /// (loading_screen, confirm_dialog, picker, slotted) generates UXML that
    /// imports as a VisualTreeAsset and clones with its documented slot names.
    /// Mirrors temp-folder + SetUp/TearDown convention from MakePanelTests.cs.
    /// </summary>
    public class MakePanelTemplateRegistryTests
    {
        private const string TempFolder = "Assets/__McpMakePanelRegistryTests_Temp__";
        private const string TempFolderName = "__McpMakePanelRegistryTests_Temp__";

        [SetUp]
        public void SetUp()
        {
            if (!AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.CreateFolder("Assets", TempFolderName);
            }
        }

        [TearDown]
        public void TearDown()
        {
            if (AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.DeleteAsset(TempFolder);
            }
        }

        private static JObject Invoke(JObject paramsObj)
        {
            var raw = MakePanel.HandleCommand(paramsObj);
            return JObject.FromObject(raw);
        }

        private static JObject GenerateAndAssertSuccess(string template, string fileStem, JObject inner = null)
        {
            string uxmlPath = TempFolder + "/" + fileStem + ".uxml";
            var paramsObj = new JObject
            {
                ["action"] = "generate",
                ["template"] = template,
                ["outputPath"] = uxmlPath,
                ["params"] = inner ?? new JObject(),
            };
            var response = Invoke(paramsObj);
            Assert.IsTrue((bool)response["success"], $"make_panel generate ({template}) should succeed: " + response);
            Assert.AreEqual(uxmlPath, response["data"]?["uxmlPath"]?.ToString());
            return response;
        }

        // ---------------------- list_templates ----------------------

        [Test]
        public void ListTemplates_ReturnsAllSixBuiltins()
        {
            var response = Invoke(new JObject { ["action"] = "list_templates" });

            Assert.IsTrue((bool)response["success"], "list_templates should succeed: " + response);

            var data = response["data"] as JObject;
            Assert.IsNotNull(data, "list_templates response missing 'data' object.");

            int count = (int)data["count"];
            Assert.AreEqual(6, count, "Expected exactly 6 built-in templates registered.");

            var templates = data["templates"] as JArray;
            Assert.IsNotNull(templates, "list_templates 'data.templates' should be an array.");
            Assert.AreEqual(6, templates.Count, "templates array length should match count.");

            var names = templates.Select(t => t["name"]?.ToString()).ToList();
            string[] expected = { "modal", "level_up", "loading_screen", "confirm_dialog", "picker", "slotted" };
            foreach (var name in expected)
            {
                Assert.Contains(name, names,
                    $"Expected built-in template '{name}' missing from list_templates output. Got: " +
                    string.Join(", ", names));
            }
        }

        [Test]
        public void ListTemplates_IncludesAliases()
        {
            var response = Invoke(new JObject { ["action"] = "list_templates" });
            Assert.IsTrue((bool)response["success"]);

            var templates = response["data"]?["templates"] as JArray;
            Assert.IsNotNull(templates);

            // Build a name -> aliases map from the response.
            var aliasMap = new Dictionary<string, HashSet<string>>();
            foreach (var entry in templates)
            {
                string name = entry["name"]?.ToString();
                Assert.IsFalse(string.IsNullOrEmpty(name), "template entry missing name");
                var aliases = (entry["aliases"] as JArray)?.Select(a => a.ToString()) ?? Enumerable.Empty<string>();
                aliasMap[name] = new HashSet<string>(aliases);
            }

            // Spot-check the documented aliases for each built-in. Lower-cased
            // because the registry stores aliases case-insensitively.
            Assert.IsTrue(aliasMap.ContainsKey("level_up"));
            Assert.Contains("levelup", aliasMap["level_up"].ToList(), "level_up should advertise 'levelup' alias.");
            Assert.Contains("level-up", aliasMap["level_up"].ToList(), "level_up should advertise 'level-up' alias.");

            Assert.IsTrue(aliasMap.ContainsKey("loading_screen"));
            Assert.Contains("loading", aliasMap["loading_screen"].ToList(), "loading_screen should advertise 'loading' alias.");
            Assert.Contains("loadingscreen", aliasMap["loading_screen"].ToList(), "loading_screen should advertise 'loadingscreen' alias.");

            Assert.IsTrue(aliasMap.ContainsKey("confirm_dialog"));
            Assert.Contains("confirm", aliasMap["confirm_dialog"].ToList(), "confirm_dialog should advertise 'confirm' alias.");
            Assert.Contains("confirmdialog", aliasMap["confirm_dialog"].ToList(), "confirm_dialog should advertise 'confirmdialog' alias.");

            Assert.IsTrue(aliasMap.ContainsKey("picker"));
            Assert.Contains("list_picker", aliasMap["picker"].ToList(), "picker should advertise 'list_picker' alias.");
            Assert.Contains("listpicker", aliasMap["picker"].ToList(), "picker should advertise 'listpicker' alias.");

            Assert.IsTrue(aliasMap.ContainsKey("slotted"));
            Assert.Contains("blank", aliasMap["slotted"].ToList(), "slotted should advertise 'blank' alias.");
            Assert.Contains("content", aliasMap["slotted"].ToList(), "slotted should advertise 'content' alias.");
        }

        // ---------------------- generate per template ----------------------

        [Test]
        public void Generate_LoadingScreen_ProducesLoadableUxml()
        {
            string fileStem = "SmokeLoadingScreen";
            var response = GenerateAndAssertSuccess("loading_screen", fileStem,
                new JObject
                {
                    ["title"] = "Loading...",
                    ["subtitle"] = "Connecting to server",
                    ["progress"] = 0.5f,
                });

            string uxmlPath = TempFolder + "/" + fileStem + ".uxml";
            Assert.IsTrue(File.Exists(Path.Combine(Application.dataPath, TempFolderName + "/" + fileStem + ".uxml")));

            var asset = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(uxmlPath);
            Assert.IsNotNull(asset, "UXML failed to import as VisualTreeAsset: " + uxmlPath);

            var instance = asset.CloneTree();
            Assert.IsNotNull(instance, "CloneTree() returned null.");

            Assert.IsNotNull(instance.Q(name: "loading-screen"),
                "Expected #loading-screen root element in loading_screen template.");
            Assert.IsNotNull(instance.Q(name: "loading-screen__bar-fill"),
                "Expected #loading-screen__bar-fill in loading_screen template.");
            Assert.IsNotNull(instance.Q<Label>(name: "loading-screen__title"),
                "Expected #loading-screen__title Label in loading_screen template.");
        }

        [Test]
        public void Generate_ConfirmDialog_ContainsExpectedSlots()
        {
            string fileStem = "SmokeConfirmDialog";
            GenerateAndAssertSuccess("confirm_dialog", fileStem,
                new JObject
                {
                    ["title"] = "Delete file?",
                    ["body"] = "This cannot be undone.",
                    ["confirmText"] = "Delete",
                    ["cancelText"] = "Cancel",
                    ["danger"] = true,
                });

            string uxmlPath = TempFolder + "/" + fileStem + ".uxml";
            var asset = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(uxmlPath);
            Assert.IsNotNull(asset, "UXML failed to import as VisualTreeAsset: " + uxmlPath);

            var instance = asset.CloneTree();
            Assert.IsNotNull(instance);

            var yes = instance.Q<Button>(name: "confirm-yes");
            Assert.IsNotNull(yes, "Expected #confirm-yes Button in confirm_dialog template.");
            var no = instance.Q<Button>(name: "confirm-no");
            Assert.IsNotNull(no, "Expected #confirm-no Button in confirm_dialog template.");

            // Sanity-check authored text propagated.
            Assert.AreEqual("Delete", yes.text, "Confirm button text should reflect 'confirmText' param.");
            Assert.AreEqual("Cancel", no.text, "Cancel button text should reflect 'cancelText' param.");
        }

        [Test]
        public void Generate_Picker_ContainsListView()
        {
            string fileStem = "SmokePicker";
            GenerateAndAssertSuccess("picker", fileStem,
                new JObject
                {
                    ["title"] = "Pick One",
                    ["itemHeight"] = 40,
                    ["showCancel"] = true,
                });

            string uxmlPath = TempFolder + "/" + fileStem + ".uxml";
            var asset = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(uxmlPath);
            Assert.IsNotNull(asset, "UXML failed to import as VisualTreeAsset: " + uxmlPath);

            var instance = asset.CloneTree();
            Assert.IsNotNull(instance);

            var list = instance.Q<ListView>(name: "picker-list");
            Assert.IsNotNull(list, "Expected #picker-list ListView in picker template.");

            Assert.IsNotNull(instance.Q<Button>(name: "picker-cancel"),
                "Expected #picker-cancel Button when showCancel=true.");
        }

        [Test]
        public void Generate_Slotted_ContainsContentSlot()
        {
            string fileStem = "SmokeSlotted";
            GenerateAndAssertSuccess("slotted", fileStem,
                new JObject
                {
                    ["title"] = "Settings",
                });

            string uxmlPath = TempFolder + "/" + fileStem + ".uxml";
            var asset = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(uxmlPath);
            Assert.IsNotNull(asset, "UXML failed to import as VisualTreeAsset: " + uxmlPath);

            var instance = asset.CloneTree();
            Assert.IsNotNull(instance);

            Assert.IsNotNull(instance.Q(name: "content"),
                "Expected #content slot element in slotted template.");
            // Default rootName is 'panel'.
            Assert.IsNotNull(instance.Q(name: "panel"),
                "Expected #panel root element in slotted template (default rootName).");
            // Title was supplied — panel-title should exist.
            Assert.IsNotNull(instance.Q<Label>(name: "panel-title"),
                "Expected #panel-title Label when title param is supplied.");
        }

        // ---------------------- alias resolution ----------------------

        [Test]
        public void Generate_AliasName_ResolvesToCanonical()
        {
            // Generate via canonical name and via alias, then compare the
            // raw .uxml bytes — same params should produce identical output.
            string canonicalUxml = TempFolder + "/AliasCanonical.uxml";
            string aliasUxml = TempFolder + "/AliasAlias.uxml";

            var canonicalParams = new JObject
            {
                ["action"] = "generate",
                ["template"] = "confirm_dialog",
                ["outputPath"] = canonicalUxml,
                ["params"] = new JObject
                {
                    ["title"] = "Same Title",
                    ["body"] = "Same body.",
                },
            };
            var aliasParams = new JObject
            {
                ["action"] = "generate",
                ["template"] = "confirm",
                ["outputPath"] = aliasUxml,
                ["params"] = new JObject
                {
                    ["title"] = "Same Title",
                    ["body"] = "Same body.",
                },
            };

            var canonicalResp = Invoke(canonicalParams);
            var aliasResp = Invoke(aliasParams);

            Assert.IsTrue((bool)canonicalResp["success"], "canonical confirm_dialog should succeed: " + canonicalResp);
            Assert.IsTrue((bool)aliasResp["success"], "alias 'confirm' should succeed: " + aliasResp);

            string canonicalAbs = Path.Combine(Application.dataPath, TempFolderName + "/AliasCanonical.uxml");
            string aliasAbs = Path.Combine(Application.dataPath, TempFolderName + "/AliasAlias.uxml");
            Assert.IsTrue(File.Exists(canonicalAbs), "canonical UXML missing on disk: " + canonicalAbs);
            Assert.IsTrue(File.Exists(aliasAbs), "alias UXML missing on disk: " + aliasAbs);

            // The generator embeds each output's basename in its UXML (USS sibling
            // ref), so byte-equality across different output paths isn't a useful
            // signal. Verify structural equivalence instead: both load as
            // VisualTreeAssets and expose the same documented slots.
            var canonicalAsset = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(canonicalUxml);
            var aliasAsset = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(aliasUxml);
            Assert.IsNotNull(canonicalAsset, "canonical confirm_dialog UXML failed to import");
            Assert.IsNotNull(aliasAsset, "alias 'confirm' UXML failed to import");

            var canonicalTree = canonicalAsset.CloneTree();
            var aliasTree = aliasAsset.CloneTree();

            Assert.IsNotNull(canonicalTree.Q<Button>(name: "confirm-yes"),
                "Canonical confirm_dialog should expose #confirm-yes.");
            Assert.IsNotNull(canonicalTree.Q<Button>(name: "confirm-no"),
                "Canonical confirm_dialog should expose #confirm-no.");
            Assert.IsNotNull(aliasTree.Q<Button>(name: "confirm-yes"),
                "Alias 'confirm' should also expose #confirm-yes.");
            Assert.IsNotNull(aliasTree.Q<Button>(name: "confirm-no"),
                "Alias 'confirm' should also expose #confirm-no.");
        }

        // ---------------------- error path ----------------------

        [Test]
        public void Generate_UnknownTemplate_ReturnsError()
        {
            string uxmlPath = TempFolder + "/UnknownTemplate.uxml";
            var paramsObj = new JObject
            {
                ["action"] = "generate",
                ["template"] = "nonexistent_template",
                ["outputPath"] = uxmlPath,
                ["params"] = new JObject(),
            };

            var response = Invoke(paramsObj);
            Assert.IsFalse((bool)response["success"],
                "Unknown template should return success=false. Got: " + response);

            string error = response["error"]?.ToString() ?? response["message"]?.ToString() ?? string.Empty;
            Assert.IsFalse(string.IsNullOrEmpty(error), "Error response should include an error/message field: " + response);

            // Error message should enumerate at least the canonical built-in
            // names so callers can self-correct without reading docs.
            StringAssert.Contains("modal", error, "Error message should list 'modal' as an available template.");
            StringAssert.Contains("level_up", error, "Error message should list 'level_up' as an available template.");
            StringAssert.Contains("confirm_dialog", error, "Error message should list 'confirm_dialog' as an available template.");
            StringAssert.Contains("picker", error, "Error message should list 'picker' as an available template.");
            StringAssert.Contains("slotted", error, "Error message should list 'slotted' as an available template.");
            StringAssert.Contains("loading_screen", error, "Error message should list 'loading_screen' as an available template.");
        }
    }
}
