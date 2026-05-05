using System.Collections.Generic;
using UnityEngine;

namespace MCPForUnity.Editor.Tests
{
    /// <summary>
    /// MonoBehaviour fixture used by ApplyScenePatchTests and ApplyPrefabPatchTests.
    /// Top-level (not nested) so AddComponent / PrefabUtility.SaveAsPrefabAsset work cleanly.
    /// </summary>
    public class SerializedPatchFixture : MonoBehaviour
    {
        public float damage;
        public List<GameObject> targets = new List<GameObject>();
    }
}
