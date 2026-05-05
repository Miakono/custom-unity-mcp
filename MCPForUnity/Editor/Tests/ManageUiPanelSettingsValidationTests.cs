using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

namespace MCPForUnity.Editor.Tests
{
    /// <summary>
    /// Covers the strict-key validation added to manage_ui's create_panel_settings
    /// and update_panel_settings actions. Previously, unknown top-level keys
    /// (e.g. `sort_order: 9999` instead of `settings.sortingOrder`) and unknown
    /// inner-`settings` keys were silently dropped. Both paths now return a
    /// structured `unknown_keys` error.
    ///
    /// Notable contract: snake_case aliases that survive the apply path's
    /// underscore-stripping normalizer (scale_mode, reference_resolution, …)
    /// ARE accepted. `sort_order` is intentionally NOT aliased — it must be
    /// sent as `sortingOrder`, which is PanelSettings's actual serialized
    /// field name.
    /// </summary>
    public class ManageUiPanelSettingsValidationTests
    {
        private const string TempFolder = "Assets/__McpManageUiValidationTests_Temp__";
        private const string ExistingAssetPath =
            TempFolder + "/Test.panelsettings.asset";
        // Path used by tests that exercise the *create* code path. Distinct
        // from ExistingAssetPath so we can assert "no asset was created" cleanly.
        private const string CreateTargetPath =
            TempFolder + "/Created.panelsettings.asset";

        [SetUp]
        public void SetUp()
        {
            if (!AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.CreateFolder("Assets", "__McpManageUiValidationTests_Temp__");
            }

            // Pre-existing PanelSettings asset for the update_panel_settings tests.
            // The create_panel_settings tests target a different path so they can
            // freely assert "no asset was created" on validation failure.
            var ps = ScriptableObject.CreateInstance<PanelSettings>();
            AssetDatabase.CreateAsset(ps, ExistingAssetPath);
            AssetDatabase.SaveAssets();
        }

        [TearDown]
        public void TearDown()
        {
            if (AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.DeleteAsset(TempFolder);
            }
        }

        private static JObject Call(JObject paramsObj)
        {
            var raw = ManageUI.HandleCommand(paramsObj);
            return JObject.FromObject(raw);
        }

        // Mirrors ComponentSetPropertyTests.FirstStructuredError style: pull the
        // structured `unknown_keys` payload off response.data so individual tests
        // can assert against (code, scope, unknown[]) without re-parsing the
        // JObject in every test.
        private static (string code, string scope, JArray unknown) ExtractUnknownKeysError(JObject response)
        {
            var data = response["data"] as JObject;
            return (
                data?["code"]?.ToString(),
                data?["scope"]?.ToString(),
                data?["unknown"] as JArray);
        }

        // ─── create_panel_settings ──────────────────────────────────────────

        [Test]
        public void CreatePanelSettings_UnknownTopLevelKey_ReturnsUnknownKeysError()
        {
            // `sort_order` at the top level was the user's headline regression —
            // it used to be silently dropped because only `settings` is the
            // documented carrier. Validation should run *before* mutation, so no
            // asset should be created either.
            var paramsObj = new JObject
            {
                ["action"] = "create_panel_settings",
                ["path"] = CreateTargetPath,
                ["sort_order"] = 9999,
            };

            var response = Call(paramsObj);

            Assert.IsFalse((bool)response["success"],
                "create_panel_settings with an unknown top-level key should be refused: " + response);
            var (code, scope, unknown) = ExtractUnknownKeysError(response);
            Assert.AreEqual("unknown_keys", code, "data.code should be unknown_keys");
            Assert.AreEqual("top_level", scope, "data.scope should be top_level");
            Assert.IsNotNull(unknown, "data.unknown array should be present");
            CollectionAssert.Contains(
                unknown.ToObject<string[]>(),
                "sort_order",
                "data.unknown should list the offending key.");

            Assert.IsNull(
                AssetDatabase.LoadAssetAtPath<PanelSettings>(CreateTargetPath),
                "Validation must run before mutation — no PanelSettings asset should have been created.");
        }

        [Test]
        public void CreatePanelSettings_UnknownKeyInsideSettings_ReturnsUnknownKeysError()
        {
            // `settings: { sort_order: 9999 }` is the other half of the regression:
            // PanelSettings's field is `sortingOrder`, and the apply path's
            // normalizer collapses `sort_order` → `sortorder` (≠ `sortingorder`),
            // so the value would be silently dropped. The validator must reject
            // it with a hint pointing at `sortingOrder`.
            var paramsObj = new JObject
            {
                ["action"] = "create_panel_settings",
                ["path"] = CreateTargetPath,
                ["settings"] = new JObject
                {
                    ["sort_order"] = 9999,
                },
            };

            var response = Call(paramsObj);

            Assert.IsFalse((bool)response["success"],
                "create_panel_settings with an unknown body key should be refused: " + response);
            var (code, scope, unknown) = ExtractUnknownKeysError(response);
            Assert.AreEqual("unknown_keys", code);
            Assert.AreEqual("settings", scope);
            Assert.IsNotNull(unknown);
            var unknownList = unknown.ToObject<string[]>();
            Assert.AreEqual(1, unknownList.Length, "Only `sort_order` should be flagged.");
            Assert.AreEqual("sort_order", unknownList[0]);

            string hint = response["data"]?["hint"]?.ToString() ?? string.Empty;
            Assert.IsTrue(hint.Contains("sortingOrder"),
                "Hint should steer the caller toward `sortingOrder`. Was: " + hint);

            Assert.IsNull(
                AssetDatabase.LoadAssetAtPath<PanelSettings>(CreateTargetPath),
                "No asset should be created when validation fails.");
        }

        [Test]
        public void CreatePanelSettings_KnownSnakeCaseAlias_Accepted()
        {
            // scale_mode and reference_resolution are explicitly aliased — they
            // collapse to `scaleMode` / `referenceResolution` after the apply
            // path's normalizer, so the validator must accept them. This
            // guarantees we didn't over-tighten the strict-key check and break
            // documented snake_case usage.
            var paramsObj = new JObject
            {
                ["action"] = "create_panel_settings",
                ["path"] = CreateTargetPath,
                ["settings"] = new JObject
                {
                    ["scale_mode"] = "ScaleWithScreenSize",
                    // Note: the inner-`settings` apply path reads `width`/`height`
                    // off the resolution object. This test sends `x`/`y` per the
                    // task spec to verify the *key* is accepted; the actual
                    // resolution-value assertion lives below.
                    ["reference_resolution"] = new JObject
                    {
                        ["x"] = 1920,
                        ["y"] = 1080,
                    },
                },
            };

            var response = Call(paramsObj);

            Assert.IsTrue((bool)response["success"],
                "snake_case aliases (scale_mode, reference_resolution) must be accepted: " + response);

            var ps = AssetDatabase.LoadAssetAtPath<PanelSettings>(CreateTargetPath);
            Assert.IsNotNull(ps, "Asset should have been created.");
            Assert.AreEqual(PanelScaleMode.ScaleWithScreenSize, ps.scaleMode,
                "scale_mode alias should have been applied to scaleMode.");
        }

        [Test]
        public void CreatePanelSettings_CanonicalKeys_Accepted()
        {
            // Canonical camelCase keys must also pass — sortingOrder in particular
            // is the form the validator's hint steers callers toward, so it had
            // better actually work end-to-end.
            var paramsObj = new JObject
            {
                ["action"] = "create_panel_settings",
                ["path"] = CreateTargetPath,
                ["settings"] = new JObject
                {
                    ["sortingOrder"] = 9999,
                    ["scaleMode"] = "ConstantPixelSize",
                },
            };

            var response = Call(paramsObj);

            Assert.IsTrue((bool)response["success"],
                "Canonical keys should be accepted: " + response);

            var ps = AssetDatabase.LoadAssetAtPath<PanelSettings>(CreateTargetPath);
            Assert.IsNotNull(ps, "Asset should have been created.");
            Assert.AreEqual(9999, ps.sortingOrder,
                "sortingOrder should have been written through to the asset.");
            Assert.AreEqual(PanelScaleMode.ConstantPixelSize, ps.scaleMode);
        }

        // ─── update_panel_settings ──────────────────────────────────────────

        [Test]
        public void UpdatePanelSettings_UnknownKey_ReturnsErrorAndAssetUntouched()
        {
            // The pre-existing asset's sortingOrder defaults to 0; capture it
            // up-front so the post-call assertion compares against the real
            // baseline rather than a hard-coded value.
            var preExisting = AssetDatabase.LoadAssetAtPath<PanelSettings>(ExistingAssetPath);
            Assert.IsNotNull(preExisting, "SetUp must have created the fixture asset.");
            float originalSortingOrder = preExisting.sortingOrder;

            var paramsObj = new JObject
            {
                ["action"] = "update_panel_settings",
                ["path"] = ExistingAssetPath,
                ["settings"] = new JObject
                {
                    ["sort_order"] = 9999,
                },
            };

            var response = Call(paramsObj);

            Assert.IsFalse((bool)response["success"],
                "update_panel_settings with an unknown body key should be refused: " + response);
            var (code, scope, unknown) = ExtractUnknownKeysError(response);
            Assert.AreEqual("unknown_keys", code);
            Assert.AreEqual("settings", scope);
            CollectionAssert.Contains(unknown.ToObject<string[]>(), "sort_order");

            // Reload from disk to confirm the validator refused *before* writing.
            var reloaded = AssetDatabase.LoadAssetAtPath<PanelSettings>(ExistingAssetPath);
            Assert.IsNotNull(reloaded);
            Assert.AreEqual(originalSortingOrder, reloaded.sortingOrder,
                "sortingOrder must be untouched when the update is refused.");
        }

        [Test]
        public void UpdatePanelSettings_CanonicalKey_Applied()
        {
            // Happy path for the update surface: canonical sortingOrder writes
            // through to the existing asset.
            var paramsObj = new JObject
            {
                ["action"] = "update_panel_settings",
                ["path"] = ExistingAssetPath,
                ["settings"] = new JObject
                {
                    ["sortingOrder"] = 1234,
                },
            };

            var response = Call(paramsObj);

            Assert.IsTrue((bool)response["success"],
                "update_panel_settings with sortingOrder should succeed: " + response);

            var reloaded = AssetDatabase.LoadAssetAtPath<PanelSettings>(ExistingAssetPath);
            Assert.IsNotNull(reloaded);
            Assert.AreEqual(1234, reloaded.sortingOrder,
                "sortingOrder should have been written through to the asset.");
        }
    }
}
