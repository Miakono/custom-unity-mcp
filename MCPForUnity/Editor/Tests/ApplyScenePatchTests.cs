using System.IO;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tests
{
    /// <summary>
    /// Verifies the `set` op on apply_scene_patch can write Component fields on a scene
    /// GameObject — previously the tool only supported add (create empty GO) and remove.
    ///
    /// Tests run against the active scene (whatever the test runner has open) rather than
    /// creating a new one — Unity's NewScene API rejects additive creation when there's an
    /// unsaved untitled scene, which is the default state in the test runner. We use a
    /// GUID-suffixed GameObject name to avoid collisions with anything already in the scene.
    /// </summary>
    public class ApplyScenePatchTests
    {
        private const string TempFolder = "Assets/__McpScenePatchTests_Temp__";
        private string _refPrefabAPath;
        private string _refPrefabBPath;
        private string _fixtureName;
        private GameObject _fixtureGo;

        [SetUp]
        public void SetUp()
        {
            if (!AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.CreateFolder("Assets", "__McpScenePatchTests_Temp__");
            }

            _refPrefabAPath = CreateBareRefPrefab("RefA");
            _refPrefabBPath = CreateBareRefPrefab("RefB");
            AssetDatabase.SaveAssets();

            _fixtureName = "__McpFixture_" + System.Guid.NewGuid().ToString("N");
            _fixtureGo = new GameObject(_fixtureName);
            _fixtureGo.AddComponent<SerializedPatchFixture>();
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

        private static JObject Patch(JArray operations)
        {
            var paramsObj = new JObject { ["operations"] = operations };
            var raw = ApplyScenePatch.HandleCommand(paramsObj);
            return JObject.FromObject(raw);
        }

        [Test]
        public void Set_FloatField_OnSceneComponent_Persists()
        {
            var ops = new JArray
            {
                new JObject
                {
                    ["op"] = "set",
                    ["path"] = _fixtureName,
                    ["componentType"] = nameof(SerializedPatchFixture),
                    ["patches"] = new JArray
                    {
                        new JObject
                        {
                            ["propertyPath"] = "damage",
                            ["op"] = "set",
                            ["value"] = 9.25f,
                        }
                    }
                }
            };

            var response = Patch(ops);
            Assert.IsTrue((bool)response["success"], "apply_scene_patch set should succeed: " + response);

            var fixture = _fixtureGo.GetComponent<SerializedPatchFixture>();
            Assert.IsNotNull(fixture);
            Assert.AreEqual(9.25f, fixture.damage, 0.0001f);
        }

        [Test]
        public void Set_GameObjectArray_OnSceneComponent_ByPathStrings_PopulatesList()
        {
            var ops = new JArray
            {
                new JObject
                {
                    ["op"] = "set",
                    ["path"] = _fixtureName,
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

            var response = Patch(ops);
            Assert.IsTrue((bool)response["success"], "apply_scene_patch set (array) should succeed: " + response);

            var fixture = _fixtureGo.GetComponent<SerializedPatchFixture>();
            Assert.IsNotNull(fixture);
            Assert.AreEqual(2, fixture.targets.Count);
            Assert.IsNotNull(fixture.targets[0]);
            Assert.IsNotNull(fixture.targets[1]);
            Assert.AreEqual("RefA", fixture.targets[0].name);
            Assert.AreEqual("RefB", fixture.targets[1].name);
        }
    }
}
