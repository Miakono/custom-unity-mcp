using System.IO;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tests
{
    /// <summary>
    /// Verifies the `set` op on apply_prefab_patch can write Component fields back to disk —
    /// previously the tool only supported add_component / remove_component.
    /// </summary>
    public class ApplyPrefabPatchTests
    {
        private const string TempFolder = "Assets/__McpPrefabPatchTests_Temp__";
        private string _prefabPath;
        private string _refPrefabAPath;
        private string _refPrefabBPath;

        [SetUp]
        public void SetUp()
        {
            if (!AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.CreateFolder("Assets", "__McpPrefabPatchTests_Temp__");
            }

            // Match prefab file basename so the saved prefab's root has a predictable name.
            _prefabPath = Path.Combine(TempFolder, "FixturePrefab.prefab").Replace('\\', '/');
            var go = new GameObject("FixturePrefab");
            try
            {
                go.AddComponent<SerializedPatchFixture>();
                PrefabUtility.SaveAsPrefabAsset(go, _prefabPath);
            }
            finally
            {
                Object.DestroyImmediate(go);
            }

            _refPrefabAPath = CreateBareRefPrefab("RefA");
            _refPrefabBPath = CreateBareRefPrefab("RefB");
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

        private static JObject Patch(string prefabPath, JArray operations)
        {
            var paramsObj = new JObject
            {
                ["prefabPath"] = prefabPath,
                ["operations"] = operations,
            };
            var raw = ApplyPrefabPatch.HandleCommand(paramsObj);
            return JObject.FromObject(raw);
        }

        [Test]
        public void Set_FloatField_OnPrefabComponent_PersistsToDisk()
        {
            var ops = new JArray
            {
                new JObject
                {
                    ["op"] = "set",
                    ["path"] = "FixturePrefab",
                    ["componentType"] = nameof(SerializedPatchFixture),
                    ["patches"] = new JArray
                    {
                        new JObject
                        {
                            ["propertyPath"] = "damage",
                            ["op"] = "set",
                            ["value"] = 17.5f,
                        }
                    }
                }
            };

            var response = Patch(_prefabPath, ops);
            Assert.IsTrue((bool)response["success"], "apply_prefab_patch set should succeed: " + response);

            // Reload from disk to confirm the change actually persisted (not just in-memory).
            var loadedRoot = PrefabUtility.LoadPrefabContents(_prefabPath);
            try
            {
                var fixture = loadedRoot.GetComponent<SerializedPatchFixture>();
                Assert.IsNotNull(fixture, "Fixture component should still be on the prefab.");
                Assert.AreEqual(17.5f, fixture.damage, 0.0001f);
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(loadedRoot);
            }
        }

        [Test]
        public void Set_GameObjectArray_OnPrefabComponent_ByPathStrings_PopulatesList()
        {
            // The user's specific blocker: setting an object-reference array on a Component
            // (previously only supported on ScriptableObjects).
            var ops = new JArray
            {
                new JObject
                {
                    ["op"] = "set",
                    ["path"] = "FixturePrefab",
                    ["componentType"] = nameof(SerializedPatchFixture),
                    ["patches"] = new JArray
                    {
                        new JObject
                        {
                            ["propertyPath"] = "targets",
                            ["op"] = "set",
                            ["value"] = new JArray { _refPrefabAPath, _refPrefabBPath },
                        }
                    }
                }
            };

            var response = Patch(_prefabPath, ops);
            Assert.IsTrue((bool)response["success"], "apply_prefab_patch set (array) should succeed: " + response);

            var loadedRoot = PrefabUtility.LoadPrefabContents(_prefabPath);
            try
            {
                var fixture = loadedRoot.GetComponent<SerializedPatchFixture>();
                Assert.IsNotNull(fixture);
                Assert.AreEqual(2, fixture.targets.Count, "Expected 2 GameObject references on targets list.");
                Assert.IsNotNull(fixture.targets[0]);
                Assert.IsNotNull(fixture.targets[1]);
                Assert.AreEqual("RefA", fixture.targets[0].name);
                Assert.AreEqual("RefB", fixture.targets[1].name);
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(loadedRoot);
            }
        }
    }
}
