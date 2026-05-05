using System.IO;
using MCPForUnity.Editor.Tools.UI;
using MCPForUnity.UIElements;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

namespace MCPForUnity.Editor.Tests
{
    /// <summary>
    /// Verifies make_panel generates loadable UXML for the modal and level_up
    /// templates, and that the packaged tokens.uss is reachable via its project
    /// URI. Mirrors the temp-folder + SetUp/TearDown convention from
    /// ApplyScenePatchTests.cs.
    /// </summary>
    public class MakePanelTests
    {
        private const string TempFolder = "Assets/__McpMakePanelTests_Temp__";
        private const string TokensAssetPath = "Packages/com.customgamedev.unity-mcp/Runtime/UI/Tokens/tokens.uss";

        [SetUp]
        public void SetUp()
        {
            if (!AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.CreateFolder("Assets", "__McpMakePanelTests_Temp__");
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

        [Test]
        public void Generate_Modal_Writes_Valid_Uxml_That_Loads()
        {
            string uxmlPath = TempFolder + "/SmokeModal.uxml";
            string ussPath = TempFolder + "/SmokeModal.uss";

            var paramsObj = new JObject
            {
                ["action"] = "generate",
                ["template"] = "modal",
                ["outputPath"] = uxmlPath,
                ["params"] = new JObject
                {
                    ["title"] = "Test Modal",
                    ["bodyText"] = "Hello, world.",
                    ["showCloseButton"] = true,
                    ["openOnAttach"] = true,
                },
            };

            var response = Invoke(paramsObj);
            Assert.IsTrue((bool)response["success"], "make_panel generate (modal) should succeed: " + response);
            Assert.AreEqual(uxmlPath, response["data"]?["uxmlPath"]?.ToString());
            Assert.AreEqual(ussPath, response["data"]?["ussPath"]?.ToString());
            Assert.AreEqual("MCPForUnity.UIElements.Modal", response["data"]?["componentTypeFullName"]?.ToString());

            Assert.IsTrue(File.Exists(Path.Combine(Application.dataPath, "__McpMakePanelTests_Temp__/SmokeModal.uxml")));
            Assert.IsTrue(File.Exists(Path.Combine(Application.dataPath, "__McpMakePanelTests_Temp__/SmokeModal.uss")));

            var vta = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(uxmlPath);
            Assert.IsNotNull(vta, $"Generated UXML failed to load as VisualTreeAsset: {uxmlPath}");

            var root = vta.Instantiate();
            Assert.IsNotNull(root, "VisualTreeAsset.Instantiate() returned null.");

            var modal = root.Q<Modal>();
            Assert.IsNotNull(modal, "Could not find Modal element in instantiated UXML.");
            Assert.AreEqual("Test Modal", modal.GetTitle(), "Modal title was not applied from UXML attribute.");

            var bodyLabel = root.Q<Label>(className: "modal__body-text");
            Assert.IsNotNull(bodyLabel, "Body Label generated from bodyText param was not found.");
            Assert.AreEqual("Hello, world.", bodyLabel.text);
        }

        [Test]
        public void Generate_LevelUpChoice_With_Three_Choices_Creates_Three_Cards()
        {
            string uxmlPath = TempFolder + "/SmokeLevelUp.uxml";

            var paramsObj = new JObject
            {
                ["action"] = "generate",
                ["template"] = "level_up",
                ["outputPath"] = uxmlPath,
                ["params"] = new JObject
                {
                    ["title"] = "Pick One",
                    ["choices"] = new JArray
                    {
                        new JObject
                        {
                            ["name"] = "Fireball",
                            ["description"] = "Burns enemies.",
                            ["rarity"] = "rare",
                        },
                        new JObject
                        {
                            ["name"] = "Frost Aura",
                            ["description"] = "Slows nearby foes.",
                            ["rarity"] = "uncommon",
                        },
                        new JObject
                        {
                            ["name"] = "Lightning Bolt",
                            ["description"] = "Zaps for big damage.",
                            ["rarity"] = "epic",
                            ["isPrimary"] = true,
                        },
                    },
                },
            };

            var response = Invoke(paramsObj);
            Assert.IsTrue((bool)response["success"], "make_panel generate (level_up) should succeed: " + response);
            Assert.AreEqual("MCPForUnity.UIElements.LevelUpChoice", response["data"]?["componentTypeFullName"]?.ToString());

            var vta = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(uxmlPath);
            Assert.IsNotNull(vta, $"Generated UXML failed to load as VisualTreeAsset: {uxmlPath}");

            var root = vta.Instantiate();
            Assert.IsNotNull(root);

            var luc = root.Q<LevelUpChoice>();
            Assert.IsNotNull(luc, "Could not find LevelUpChoice element.");

            var cards = root.Query<VisualElement>(className: LevelUpChoice.CardClass).ToList();
            Assert.AreEqual(3, cards.Count, "Expected exactly 3 author-time cards from inline UXML.");

            var nameLabels = root.Query<Label>(className: LevelUpChoice.CardNameClass).ToList();
            Assert.AreEqual(3, nameLabels.Count);
            Assert.AreEqual("Fireball", nameLabels[0].text);
            Assert.AreEqual("Frost Aura", nameLabels[1].text);
            Assert.AreEqual("Lightning Bolt", nameLabels[2].text);

            var descLabels = root.Query<Label>(className: LevelUpChoice.CardDescClass).ToList();
            Assert.AreEqual("Burns enemies.", descLabels[0].text);
            Assert.AreEqual("Slows nearby foes.", descLabels[1].text);
            Assert.AreEqual("Zaps for big damage.", descLabels[2].text);

            // Rarity classes applied
            Assert.IsTrue(cards[0].ClassListContains("luc-card--rarity-rare"));
            Assert.IsTrue(cards[1].ClassListContains("luc-card--rarity-uncommon"));
            Assert.IsTrue(cards[2].ClassListContains("luc-card--rarity-epic"));
            Assert.IsTrue(cards[2].ClassListContains("luc-card--primary"));
        }

        [Test]
        public void Tokens_Uss_Loads_And_Declares_Expected_Variables()
        {
            var sheet = AssetDatabase.LoadAssetAtPath<StyleSheet>(TokensAssetPath);
            Assert.IsNotNull(sheet, $"tokens.uss did not load via package URI: {TokensAssetPath}. " +
                "Confirm the package is registered as 'com.customgamedev.unity-mcp' and the file exists.");

            // Sanity-check the file content lists the spec'd variables.
            // We read the file directly because StyleSheet's parsed output
            // doesn't expose variable names through a stable public API.
            string fullPath = AssetDatabase.GetAssetPath(sheet);
            Assert.IsFalse(string.IsNullOrEmpty(fullPath));

            // Read raw file contents through the AssetDatabase-resolved path.
            // For package assets, AssetDatabase.GetAssetPath returns the
            // virtual "Packages/..." path which File.ReadAllText cannot open
            // directly — fall back to PackageInfo.resolvedPath if needed.
            string raw = ReadPackagedTextAsset(fullPath);
            Assert.IsNotNull(raw, $"Could not read raw contents of tokens.uss at {fullPath}.");
            StringAssert.Contains("--color-bg", raw, "tokens.uss missing --color-bg variable.");
            StringAssert.Contains("--space-md", raw, "tokens.uss missing --space-md variable.");
            StringAssert.Contains("--radius-md", raw, "tokens.uss missing --radius-md variable.");
            StringAssert.Contains("--anim-default", raw, "tokens.uss missing --anim-default variable.");
        }

        private static string ReadPackagedTextAsset(string assetPath)
        {
            if (string.IsNullOrEmpty(assetPath)) return null;

            // Direct read works for Assets/* paths and resolves Package paths
            // when the Library is up to date.
            try
            {
                if (File.Exists(assetPath))
                {
                    return File.ReadAllText(assetPath);
                }
            }
            catch { /* fall through */ }

            // Resolve Packages/... to its absolute disk path.
            if (assetPath.StartsWith("Packages/"))
            {
                var pkg = UnityEditor.PackageManager.PackageInfo.FindForAssetPath(assetPath);
                if (pkg != null && !string.IsNullOrEmpty(pkg.resolvedPath))
                {
                    string relative = assetPath.Substring(("Packages/" + pkg.name + "/").Length);
                    string abs = Path.Combine(pkg.resolvedPath, relative);
                    if (File.Exists(abs))
                    {
                        return File.ReadAllText(abs);
                    }
                }
            }

            return null;
        }
    }
}
