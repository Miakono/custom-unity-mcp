using System.Collections.Generic;
using System.IO;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tests
{
    /// <summary>
    /// Regression tests for ManageScriptableObject patch types that previously fell through
    /// to the "Unsupported SerializedPropertyType" branch in TrySetValueRecursive.
    /// </summary>
    public class ManageScriptableObjectTests
    {
        public class FixtureSO : ScriptableObject
        {
            public List<GameObject> prefabs = new List<GameObject>();
            public Bounds region;
            public LayerMask mask;
        }

        private const string TempFolder = "Assets/__McpTests_Temp__";
        private string _soPath;
        private string _prefabAPath;
        private string _prefabBPath;

        [SetUp]
        public void SetUp()
        {
            if (!AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.CreateFolder("Assets", "__McpTests_Temp__");
            }

            // Two temp prefab targets for the object-ref array test.
            _prefabAPath = Path.Combine(TempFolder, "PrefabA.prefab").Replace('\\', '/');
            _prefabBPath = Path.Combine(TempFolder, "PrefabB.prefab").Replace('\\', '/');
            CreateTempPrefab(_prefabAPath, "PrefabA");
            CreateTempPrefab(_prefabBPath, "PrefabB");

            // The fixture ScriptableObject under test.
            var so = ScriptableObject.CreateInstance<FixtureSO>();
            _soPath = Path.Combine(TempFolder, "FixtureSO.asset").Replace('\\', '/');
            AssetDatabase.CreateAsset(so, _soPath);
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

        private static void CreateTempPrefab(string path, string name)
        {
            var go = new GameObject(name);
            try
            {
                PrefabUtility.SaveAsPrefabAsset(go, path);
            }
            finally
            {
                Object.DestroyImmediate(go);
            }
        }

        private static JObject Modify(string path, JArray patches)
        {
            var paramsObj = new JObject
            {
                ["action"] = "modify",
                ["target"] = new JObject { ["path"] = path },
                ["patches"] = patches,
            };
            var raw = ManageScriptableObject.HandleCommand(paramsObj);
            // The handler returns SuccessResponse / ErrorResponse — round-trip through JSON
            // so tests can inspect via JObject without depending on the internal types.
            return JObject.FromObject(raw);
        }

        [Test]
        public void Set_ArrayOfObjectReferences_ByPathStrings_PopulatesList()
        {
            // This is the exact scenario that previously hit the "object references not supported"
            // failure path in TrySetValueRecursive.
            var patches = new JArray
            {
                new JObject
                {
                    ["propertyPath"] = "prefabs",
                    ["op"] = "set",
                    ["value"] = new JArray { _prefabAPath, _prefabBPath },
                }
            };

            var response = Modify(_soPath, patches);
            Assert.IsTrue((bool)response["success"], "Patch should succeed: " + response);

            var so = AssetDatabase.LoadAssetAtPath<FixtureSO>(_soPath);
            Assert.AreEqual(2, so.prefabs.Count, "Expected 2 prefab references after patch.");
            Assert.IsNotNull(so.prefabs[0]);
            Assert.IsNotNull(so.prefabs[1]);
            Assert.AreEqual("PrefabA", so.prefabs[0].name);
            Assert.AreEqual("PrefabB", so.prefabs[1].name);
        }

        [Test]
        public void Set_ArrayOfObjectReferences_ByGuidShorthand_PopulatesList()
        {
            string guidA = AssetDatabase.AssetPathToGUID(_prefabAPath);
            string guidB = AssetDatabase.AssetPathToGUID(_prefabBPath);
            Assert.IsNotEmpty(guidA);
            Assert.IsNotEmpty(guidB);

            var patches = new JArray
            {
                new JObject
                {
                    ["propertyPath"] = "prefabs",
                    ["op"] = "set",
                    ["value"] = new JArray { guidA, guidB },
                }
            };

            var response = Modify(_soPath, patches);
            Assert.IsTrue((bool)response["success"], "Patch should succeed: " + response);

            var so = AssetDatabase.LoadAssetAtPath<FixtureSO>(_soPath);
            Assert.AreEqual(2, so.prefabs.Count);
            Assert.AreEqual(guidA, AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(so.prefabs[0])));
            Assert.AreEqual(guidB, AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(so.prefabs[1])));
        }

        [Test]
        public void Set_SingleObjectReference_StillWorks_AfterRefactor()
        {
            // Regression check: the single-property object-ref path was refactored to share
            // a helper with the array path. Make sure { ref: { path: "..." } } still resolves.
            var patches = new JArray
            {
                new JObject
                {
                    ["propertyPath"] = "prefabs.Array.size",
                    ["op"] = "array_resize",
                    ["value"] = 1,
                },
                new JObject
                {
                    ["propertyPath"] = "prefabs.Array.data[0]",
                    ["op"] = "set",
                    ["ref"] = new JObject { ["path"] = _prefabAPath },
                },
            };

            var response = Modify(_soPath, patches);
            Assert.IsTrue((bool)response["success"], "Patch should succeed: " + response);

            var so = AssetDatabase.LoadAssetAtPath<FixtureSO>(_soPath);
            Assert.AreEqual(1, so.prefabs.Count);
            Assert.AreEqual("PrefabA", so.prefabs[0].name);
        }

        [Test]
        public void Set_BoundsField_ParsesCenterAndSize()
        {
            var patches = new JArray
            {
                new JObject
                {
                    ["propertyPath"] = "region",
                    ["op"] = "set",
                    ["value"] = new JObject
                    {
                        ["center"] = new JArray { 1.0f, 2.0f, 3.0f },
                        ["size"] = new JArray { 4.0f, 5.0f, 6.0f },
                    }
                }
            };

            var response = Modify(_soPath, patches);
            Assert.IsTrue((bool)response["success"], "Patch should succeed: " + response);

            var so = AssetDatabase.LoadAssetAtPath<FixtureSO>(_soPath);
            Assert.AreEqual(new Vector3(1, 2, 3), so.region.center);
            Assert.AreEqual(new Vector3(4, 5, 6), so.region.size);
        }

        [Test]
        public void Set_LayerMask_FromLayerNameArray_OrsBitsTogether()
        {
            // "Default" is layer 0, "Water" is layer 4 in Unity's stock layout.
            // Use whichever named layers exist; if neither resolves, skip the assertion.
            int defaultLayer = LayerMask.NameToLayer("Default");
            int waterLayer = LayerMask.NameToLayer("Water");
            if (defaultLayer < 0 || waterLayer < 0)
            {
                Assert.Ignore("Project does not have stock 'Default'/'Water' layers; skipping LayerMask assertion.");
            }

            var patches = new JArray
            {
                new JObject
                {
                    ["propertyPath"] = "mask",
                    ["op"] = "set",
                    ["value"] = new JArray { "Default", "Water" },
                }
            };

            var response = Modify(_soPath, patches);
            Assert.IsTrue((bool)response["success"], "Patch should succeed: " + response);

            var so = AssetDatabase.LoadAssetAtPath<FixtureSO>(_soPath);
            int expected = (1 << defaultLayer) | (1 << waterLayer);
            Assert.AreEqual(expected, so.mask.value);
        }
    }
}
