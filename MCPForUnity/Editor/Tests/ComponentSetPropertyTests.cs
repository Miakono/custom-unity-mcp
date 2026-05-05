using System.IO;
using MCPForUnity.Editor.Tools;
using MCPForUnity.Editor.Tools.Prefabs;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tests
{
    /// <summary>
    /// Covers two recently-fixed papercuts on manage_components.set_property and
    /// manage_prefabs.modify_contents:
    ///   1. List-shrink data-loss guard (the PoolManager incident).
    ///   2. Object-reference shorthand parity with manage_scriptable_object — bare
    ///      32-char GUIDs and bare 'Assets/...' path strings should resolve, mismatched
    ///      forms should produce a useful error rather than silently set null.
    /// </summary>
    public class ComponentSetPropertyTests
    {
        private const string TempFolder = "Assets/__McpComponentSetPropertyTests_Temp__";
        private const int InitialTargetCount = 10;

        private string[] _refPaths;
        private GameObject[] _refAssets;
        private string _fixtureName;
        private GameObject _fixtureGo;
        private string _prefabPath;

        [SetUp]
        public void SetUp()
        {
            if (!AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.CreateFolder("Assets", "__McpComponentSetPropertyTests_Temp__");
            }

            _refPaths = new string[InitialTargetCount];
            _refAssets = new GameObject[InitialTargetCount];
            for (int i = 0; i < InitialTargetCount; i++)
            {
                _refPaths[i] = CreateBareRefPrefab($"Ref{i}");
            }
            AssetDatabase.SaveAssets();
            for (int i = 0; i < InitialTargetCount; i++)
            {
                _refAssets[i] = AssetDatabase.LoadAssetAtPath<GameObject>(_refPaths[i]);
            }

            // GUID-suffixed name avoids collisions with anything else in the active scene.
            _fixtureName = "__McpFixture_" + System.Guid.NewGuid().ToString("N");
            _fixtureGo = new GameObject(_fixtureName);
            _fixtureGo.AddComponent<SerializedPatchFixture>();

            // Companion prefab for the parity test against manage_prefabs.modify_contents.
            _prefabPath = Path.Combine(TempFolder, "FixturePrefab.prefab").Replace('\\', '/');
            var stagingGo = new GameObject("FixturePrefab");
            try
            {
                stagingGo.AddComponent<SerializedPatchFixture>();
                PrefabUtility.SaveAsPrefabAsset(stagingGo, _prefabPath);
            }
            finally
            {
                Object.DestroyImmediate(stagingGo);
            }
            AssetDatabase.SaveAssets();
        }

        [TearDown]
        public void TearDown()
        {
            if (_fixtureGo != null)
            {
                Object.DestroyImmediate(_fixtureGo);
            }
            if (AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.DeleteAsset(TempFolder);
            }
        }

        private static string CreateBareRefPrefab(string name)
        {
            string path = Path.Combine(TempFolder, name + ".prefab").Replace('\\', '/');
            var go = new GameObject(name);
            try
            {
                PrefabUtility.SaveAsPrefabAsset(go, path);
            }
            finally
            {
                Object.DestroyImmediate(go);
            }
            return path;
        }

        private void PrePopulateTargets(int count)
        {
            var fixture = _fixtureGo.GetComponent<SerializedPatchFixture>();
            fixture.targets.Clear();
            for (int i = 0; i < count; i++)
            {
                fixture.targets.Add(_refAssets[i]);
            }
        }

        private JObject CallSetProperty(string property, JToken value, bool confirmReplace = false)
        {
            var paramsObj = new JObject
            {
                ["action"] = "set_property",
                ["target"] = _fixtureName,
                ["componentType"] = nameof(SerializedPatchFixture),
                ["property"] = property,
                ["value"] = value,
            };
            if (confirmReplace)
            {
                paramsObj["confirmReplace"] = true;
            }
            var raw = ManageComponents.HandleCommand(paramsObj);
            return JObject.FromObject(raw);
        }

        private static (string code, string message) FirstStructuredError(JObject response)
        {
            var errors = response["data"]?["errors"] as JArray;
            if (errors == null || errors.Count == 0) return (null, null);
            var first = errors[0] as JObject;
            return (first?["code"]?.ToString(), first?["message"]?.ToString());
        }

        // ---------- Phase 1: list-shrink guard ----------

        [Test]
        public void Set_ListField_LargeShrink_WithoutConfirm_ReturnsError_PreservesList()
        {
            PrePopulateTargets(InitialTargetCount);

            // Drop 10 entries down to 1 — a 90% shrink, well over the 50% threshold.
            var response = CallSetProperty("targets", new JArray { _refPaths[0] });

            Assert.IsFalse((bool)response["success"], "Large shrink without confirmReplace should be refused: " + response);
            var (code, message) = FirstStructuredError(response);
            Assert.AreEqual("list_shrink_blocked", code, "Error code should identify the data-loss guard.");
            Assert.IsTrue(message != null && message.Contains("targets"), "Error message should name the field. Was: " + message);

            var fixture = _fixtureGo.GetComponent<SerializedPatchFixture>();
            Assert.AreEqual(InitialTargetCount, fixture.targets.Count, "List must be untouched when the write is refused.");
        }

        [Test]
        public void Set_ListField_LargeShrink_WithConfirmReplace_Succeeds()
        {
            PrePopulateTargets(InitialTargetCount);

            var response = CallSetProperty("targets", new JArray { _refPaths[0] }, confirmReplace: true);

            Assert.IsTrue((bool)response["success"], "confirmReplace=true should bypass the shrink guard: " + response);
            var fixture = _fixtureGo.GetComponent<SerializedPatchFixture>();
            Assert.AreEqual(1, fixture.targets.Count, "Targets should now hold a single entry.");
            Assert.IsNotNull(fixture.targets[0]);
            Assert.AreEqual("Ref0", fixture.targets[0].name);
        }

        [Test]
        public void Set_ListField_SmallShrink_NoConfirmNeeded()
        {
            PrePopulateTargets(InitialTargetCount);

            // 10 → 9 is a 10% shrink — under the 50% threshold, should proceed.
            var nine = new JArray();
            for (int i = 0; i < 9; i++) nine.Add(_refPaths[i]);

            var response = CallSetProperty("targets", nine);

            Assert.IsTrue((bool)response["success"], "Small shrink should proceed without confirmReplace: " + response);
            var fixture = _fixtureGo.GetComponent<SerializedPatchFixture>();
            Assert.AreEqual(9, fixture.targets.Count);
        }

        // ---------- Phase 2: object-ref shorthand parity ----------

        [Test]
        public void Set_ObjectRef_PlainGuidString_Resolves()
        {
            // Empty list grows to 1 — no shrink guard — exercises bare-GUID shorthand.
            string guid = AssetDatabase.AssetPathToGUID(_refPaths[0]);
            Assert.IsTrue(guid != null && guid.Length == 32, "Setup precondition: GUID should be 32 hex chars.");

            var response = CallSetProperty("targets", new JArray { guid });

            Assert.IsTrue((bool)response["success"], "Plain 32-char GUID string should resolve: " + response);
            var fixture = _fixtureGo.GetComponent<SerializedPatchFixture>();
            Assert.AreEqual(1, fixture.targets.Count);
            Assert.IsNotNull(fixture.targets[0], "Asset should resolve via guid-shorthand, not be null.");
            Assert.AreEqual("Ref0", fixture.targets[0].name);
        }

        [Test]
        public void Set_ObjectRef_PlainPathString_Resolves()
        {
            var response = CallSetProperty("targets", new JArray { _refPaths[0] });

            Assert.IsTrue((bool)response["success"], "Plain Assets/.../*.prefab path should resolve: " + response);
            var fixture = _fixtureGo.GetComponent<SerializedPatchFixture>();
            Assert.AreEqual(1, fixture.targets.Count);
            Assert.IsNotNull(fixture.targets[0]);
            Assert.AreEqual("Ref0", fixture.targets[0].name);
        }

        [Test]
        public void Set_ObjectRef_GarbageString_ReturnsUsefulError()
        {
            // No '/', not 32 hex chars, no scene GameObject named like this — should fail
            // with a non-empty error, not silently leave the list with a null entry.
            var response = CallSetProperty("targets", new JArray { "definitely-not-a-real-target" });

            Assert.IsFalse((bool)response["success"], "Garbage string should be reported as a failure: " + response);
            var (code, message) = FirstStructuredError(response);
            Assert.IsTrue(!string.IsNullOrEmpty(message), "Error must not be empty for an unresolved object reference.");
        }

        [Test]
        public void Set_ObjectRef_GuidObjectForm_StillWorks()
        {
            // Regression: the explicit { guid: "..." } form must keep working alongside
            // the new shorthand, since callers in the wild already pass it.
            string guid = AssetDatabase.AssetPathToGUID(_refPaths[0]);
            var response = CallSetProperty(
                "targets",
                new JArray { new JObject { ["guid"] = guid } });

            Assert.IsTrue((bool)response["success"], "{guid: ...} object form should still resolve: " + response);
            var fixture = _fixtureGo.GetComponent<SerializedPatchFixture>();
            Assert.AreEqual(1, fixture.targets.Count);
            Assert.IsNotNull(fixture.targets[0]);
            Assert.AreEqual("Ref0", fixture.targets[0].name);
        }

        // ---------- Phase 3: patches dialect convergence ----------

        [Test]
        public void Patches_SetFloatField_OnSceneComponent_Persists()
        {
            // The new patches form on manage_components.set_property — same shape as
            // apply_scene_patch / apply_prefab_patch / manage_scriptable_object.
            var patches = new JArray
            {
                new JObject
                {
                    ["propertyPath"] = "damage",
                    ["op"] = "set",
                    ["value"] = 4.25f,
                }
            };

            var paramsObj = new JObject
            {
                ["action"] = "set_property",
                ["target"] = _fixtureName,
                ["componentType"] = nameof(SerializedPatchFixture),
                ["patches"] = patches,
            };
            var response = JObject.FromObject(ManageComponents.HandleCommand(paramsObj));

            Assert.IsTrue((bool)response["success"], "patches form should succeed: " + response);
            var fixture = _fixtureGo.GetComponent<SerializedPatchFixture>();
            Assert.AreEqual(4.25f, fixture.damage, 0.0001f);
        }

        [Test]
        public void Patches_LargeShrink_RespectsGuard()
        {
            // patches form must respect the same shrink guard as the legacy single-property form.
            PrePopulateTargets(InitialTargetCount);

            var patches = new JArray
            {
                new JObject
                {
                    ["propertyPath"] = "targets",
                    ["op"] = "set",
                    ["value"] = new JArray { _refPaths[0] },
                }
            };

            var paramsObj = new JObject
            {
                ["action"] = "set_property",
                ["target"] = _fixtureName,
                ["componentType"] = nameof(SerializedPatchFixture),
                ["patches"] = patches,
            };
            var response = JObject.FromObject(ManageComponents.HandleCommand(paramsObj));

            Assert.IsFalse((bool)response["success"],
                "patches dialect should refuse large shrinks the same way as the legacy form: " + response);
            var (code, _) = FirstStructuredError(response);
            Assert.AreEqual("list_shrink_blocked", code);

            var fixture = _fixtureGo.GetComponent<SerializedPatchFixture>();
            Assert.AreEqual(InitialTargetCount, fixture.targets.Count, "List must be untouched.");
        }

        [Test]
        public void ComponentPatches_OnPrefab_Persists()
        {
            // Mirror Patches_SetFloatField_OnSceneComponent_Persists for the prefab surface.
            var paramsObj = new JObject
            {
                ["action"] = "modify_contents",
                ["prefabPath"] = _prefabPath,
                ["componentPatches"] = new JObject
                {
                    [nameof(SerializedPatchFixture)] = new JArray
                    {
                        new JObject
                        {
                            ["propertyPath"] = "damage",
                            ["op"] = "set",
                            ["value"] = 11.5f,
                        }
                    }
                }
            };
            var response = JObject.FromObject(ManagePrefabs.HandleCommand(paramsObj));

            Assert.IsTrue((bool)response["success"],
                "manage_prefabs.modify_contents componentPatches should succeed: " + response);

            var reloaded = PrefabUtility.LoadPrefabContents(_prefabPath);
            try
            {
                var fixture = reloaded.GetComponent<SerializedPatchFixture>();
                Assert.IsNotNull(fixture);
                Assert.AreEqual(11.5f, fixture.damage, 0.0001f);
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(reloaded);
            }
        }

        // ---------- Parity with manage_prefabs.modify_contents ----------

        [Test]
        public void Modify_PrefabContents_ListShrink_WithoutConfirm_ReturnsError()
        {
            // Pre-populate the prefab's list with 10 entries by writing through Unity APIs.
            // Done by loading the prefab contents, mutating in place, then saving back.
            var prefabContents = PrefabUtility.LoadPrefabContents(_prefabPath);
            try
            {
                var fx = prefabContents.GetComponent<SerializedPatchFixture>();
                fx.targets.Clear();
                for (int i = 0; i < InitialTargetCount; i++) fx.targets.Add(_refAssets[i]);
                PrefabUtility.SaveAsPrefabAsset(prefabContents, _prefabPath, out _);
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(prefabContents);
            }
            AssetDatabase.ImportAsset(_prefabPath);

            // Now try to shrink it via modify_contents without confirmReplace.
            var paramsObj = new JObject
            {
                ["action"] = "modify_contents",
                ["prefabPath"] = _prefabPath,
                ["component_properties"] = new JObject
                {
                    [nameof(SerializedPatchFixture)] = new JObject
                    {
                        ["targets"] = new JArray { _refPaths[0] }
                    }
                }
            };
            var raw = ManagePrefabs.HandleCommand(paramsObj);
            var response = JObject.FromObject(raw);

            Assert.IsFalse((bool)response["success"],
                "manage_prefabs.modify_contents should refuse a 10→1 shrink without confirmReplace: " + response);

            // ManagePrefabs concatenates errors into the response message — the error code
            // prefix from ComponentOps should be visible for callers to detect.
            string text = response["error"]?.ToString()
                       ?? response["code"]?.ToString()
                       ?? response["message"]?.ToString()
                       ?? response.ToString();
            Assert.IsTrue(text.Contains("list_shrink_blocked"),
                "Error text should surface 'list_shrink_blocked'. Was: " + text);

            // List on disk must be unchanged.
            var reloaded = PrefabUtility.LoadPrefabContents(_prefabPath);
            try
            {
                var fixture = reloaded.GetComponent<SerializedPatchFixture>();
                Assert.AreEqual(InitialTargetCount, fixture.targets.Count,
                    "Prefab list must be untouched when the write is refused.");
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(reloaded);
            }
        }
    }
}
