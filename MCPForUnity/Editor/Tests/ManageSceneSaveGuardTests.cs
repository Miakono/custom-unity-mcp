using System.IO;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace MCPForUnity.Editor.Tests
{
    /// <summary>
    /// Verifies the destructive-save guard added to ManageScene.SaveScene. The guard refuses
    /// `manage_scene action=save` when the in-memory scene's root GameObject count drops by
    /// >=5 OR by >=30% versus the on-disk version, unless the caller passes
    /// confirmDestructiveSave: true (or its snake_case alias confirm_destructive_save).
    ///
    /// Strategy A is used: each test additively creates a real scene, populates it with empty
    /// root GameObjects, saves it as a baseline, mutates the in-memory roots, then invokes
    /// ManageScene.HandleCommand with action=save. After the assert we re-read the on-disk
    /// .unity YAML via CountSceneRootsOnDisk's same heuristic to confirm whether the file was
    /// rewritten or left untouched.
    /// </summary>
    public class ManageSceneSaveGuardTests
    {
        private const string TempFolder = "Assets/__McpSceneSaveGuardTests_Temp__";
        private string _scenePath;
        private string _previouslyActiveScenePath;
        private Scene _testScene;
        private Scene _previouslyActiveScene;
        private bool _activeSceneWasReplaced;

        [SetUp]
        public void SetUp()
        {
            if (!AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.CreateFolder("Assets", "__McpSceneSaveGuardTests_Temp__");
            }

            _previouslyActiveScene = EditorSceneManager.GetActiveScene();
            _previouslyActiveScenePath = _previouslyActiveScene.path;

            string fileName = "GuardTest_" + System.Guid.NewGuid().ToString("N") + ".unity";
            _scenePath = TempFolder + "/" + fileName;

            // Try to create an additive scene first so we don't disturb the runner's active scene.
            // Unity's NewScene(Additive) refuses when there is an unsaved untitled scene. If that
            // happens, fall back to Single mode and remember to restore in TearDown.
            try
            {
                _testScene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
                _activeSceneWasReplaced = false;
            }
            catch
            {
                _testScene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                _activeSceneWasReplaced = true;
            }
        }

        [TearDown]
        public void TearDown()
        {
            if (_activeSceneWasReplaced)
            {
                // We replaced the active scene with our test scene via Single mode. Restore the
                // previously-active scene if it had a path, otherwise leave the editor with a
                // fresh untitled scene so the next test gets a clean slate.
                if (!string.IsNullOrEmpty(_previouslyActiveScenePath))
                {
                    try
                    {
                        EditorSceneManager.OpenScene(_previouslyActiveScenePath, OpenSceneMode.Single);
                    }
                    catch
                    {
                        EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
                    }
                }
                else
                {
                    EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
                }
            }
            else
            {
                // Additive path: just close our scene without saving any in-memory mutations.
                if (_testScene.IsValid() && _testScene.isLoaded)
                {
                    EditorSceneManager.CloseScene(_testScene, true);
                }

                if (_previouslyActiveScene.IsValid() && _previouslyActiveScene.isLoaded)
                {
                    EditorSceneManager.SetActiveScene(_previouslyActiveScene);
                }
            }

            if (AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.DeleteAsset(TempFolder);
            }
        }

        // ---- helpers --------------------------------------------------------

        private void PopulateRoots(int count, string prefix)
        {
            for (int i = 0; i < count; i++)
            {
                var go = new GameObject(prefix + "_" + i);
                SceneManager.MoveGameObjectToScene(go, _testScene);
            }
        }

        private void DeleteFirstNRoots(int n)
        {
            var roots = _testScene.GetRootGameObjects();
            for (int i = 0; i < n && i < roots.Length; i++)
            {
                Object.DestroyImmediate(roots[i]);
            }
        }

        private void SaveBaseline()
        {
            EditorSceneManager.SaveScene(_testScene, _scenePath);
        }

        private JObject InvokeSave(bool? confirmDestructiveSave = null, bool useSnakeCase = false)
        {
            // The guard reads currentScene = EditorSceneManager.GetActiveScene(); make our scene active.
            EditorSceneManager.SetActiveScene(_testScene);

            var paramsObj = new JObject
            {
                ["action"] = "save",
                ["path"] = _scenePath,
            };
            if (confirmDestructiveSave.HasValue)
            {
                if (useSnakeCase)
                    paramsObj["confirm_destructive_save"] = confirmDestructiveSave.Value;
                else
                    paramsObj["confirmDestructiveSave"] = confirmDestructiveSave.Value;
            }

            var raw = ManageScene.HandleCommand(paramsObj);
            return JObject.FromObject(raw);
        }

        /// <summary>
        /// Re-reads the on-disk .unity file and counts roots using the same heuristic the guard
        /// uses (Transform documents with m_Father.fileID == 0; falls back to GameObject headers).
        /// </summary>
        private int CountRootsOnDisk()
        {
            string projectRoot = Application.dataPath.Substring(0, Application.dataPath.Length - "Assets".Length);
            string fullPath = Path.Combine(projectRoot, _scenePath);
            if (!File.Exists(fullPath)) return -1;

            string[] lines = File.ReadAllLines(fullPath);
            int rootCount = 0;
            int totalGameObjectHeaders = 0;
            bool sawAnyTransform = false;

            int i = 0;
            while (i < lines.Length)
            {
                string line = lines[i];
                if (line.StartsWith("--- !u!", System.StringComparison.Ordinal))
                {
                    int idStart = "--- !u!".Length;
                    int idEnd = line.IndexOf(' ', idStart);
                    if (idEnd > idStart)
                    {
                        string classIdStr = line.Substring(idStart, idEnd - idStart);
                        if (int.TryParse(classIdStr, out int classId))
                        {
                            if (classId == 1)
                            {
                                totalGameObjectHeaders++;
                            }
                            else if (classId == 4 || classId == 224)
                            {
                                sawAnyTransform = true;
                                int j = i + 1;
                                while (j < lines.Length && !lines[j].StartsWith("--- ", System.StringComparison.Ordinal))
                                {
                                    string body = lines[j];
                                    int idx = body.IndexOf("m_Father:", System.StringComparison.Ordinal);
                                    if (idx >= 0)
                                    {
                                        int fileIdIdx = body.IndexOf("fileID:", idx, System.StringComparison.Ordinal);
                                        if (fileIdIdx >= 0)
                                        {
                                            int k = fileIdIdx + "fileID:".Length;
                                            while (k < body.Length && body[k] == ' ') k++;
                                            int numStart = k;
                                            if (k < body.Length && (body[k] == '-' || body[k] == '+')) k++;
                                            while (k < body.Length && char.IsDigit(body[k])) k++;
                                            if (k > numStart)
                                            {
                                                if (long.TryParse(body.Substring(numStart, k - numStart), out long parentFileId))
                                                {
                                                    if (parentFileId == 0) rootCount++;
                                                }
                                            }
                                        }
                                        break;
                                    }
                                    j++;
                                }
                                i = j;
                                continue;
                            }
                        }
                    }
                }
                i++;
            }

            return sawAnyTransform ? rootCount : totalGameObjectHeaders;
        }

        // ---- tests ----------------------------------------------------------

        [Test]
        public void Save_NoExistingFile_ProceedsWithoutGuard()
        {
            // First save (no on-disk baseline) must succeed regardless of root count.
            // Even with a low root count there's no prior state to compare to.
            PopulateRoots(2, "Root");

            var response = InvokeSave();
            Assert.IsTrue((bool)response["success"], "First save should bypass the guard: " + response);

            string projectRoot = Application.dataPath.Substring(0, Application.dataPath.Length - "Assets".Length);
            Assert.IsTrue(File.Exists(Path.Combine(projectRoot, _scenePath)), "Scene file should exist on disk after first save.");
            Assert.AreEqual(2, CountRootsOnDisk(), "On-disk root count should match what we saved.");
        }

        [Test]
        public void Save_GrowingRootCount_Succeeds()
        {
            // Establish a 5-root baseline on disk.
            PopulateRoots(5, "Initial");
            SaveBaseline();
            Assert.AreEqual(5, CountRootsOnDisk(), "Sanity: baseline should be 5 roots on disk.");

            // Add 3 more roots in memory (5 -> 8). Growth must never trigger the guard.
            PopulateRoots(3, "Added");

            var response = InvokeSave();
            Assert.IsTrue((bool)response["success"], "Growing the root count should always succeed: " + response);
            Assert.AreEqual(8, CountRootsOnDisk(), "On-disk file should now reflect the grown root count.");
        }

        [Test]
        public void Save_SmallShrink_LogsWarningProceedsAnyway()
        {
            // 10 -> 8: delta of 2, which is under the absolute threshold (5) AND
            // under the percent threshold (20% < 30%). Should warn but allow.
            PopulateRoots(10, "Initial");
            SaveBaseline();
            Assert.AreEqual(10, CountRootsOnDisk());

            DeleteFirstNRoots(2);
            Assert.AreEqual(8, _testScene.rootCount, "Sanity: in-memory root count should be 8.");

            var response = InvokeSave();
            Assert.IsTrue((bool)response["success"], "Small shrink should not be blocked: " + response);
            Assert.AreEqual(8, CountRootsOnDisk(), "On-disk file should reflect the small shrink.");
        }

        [Test]
        public void Save_LargeShrinkAbsolute_RefusedWithoutConfirm()
        {
            // 15 -> 2: delta -13, well over the absolute threshold of 5. Without confirm,
            // the guard must refuse and the on-disk file must remain unchanged.
            PopulateRoots(15, "Initial");
            SaveBaseline();
            Assert.AreEqual(15, CountRootsOnDisk());

            DeleteFirstNRoots(13);
            Assert.AreEqual(2, _testScene.rootCount);

            var response = InvokeSave();
            Assert.IsFalse((bool)response["success"], "Large absolute shrink should be refused: " + response);
            Assert.AreEqual("destructive_save_blocked", (string)response["data"]["code"]);
            Assert.AreEqual(_scenePath, (string)response["data"]["scenePath"]);
            Assert.AreEqual(15, (int)response["data"]["oldRootCount"]);
            Assert.AreEqual(2, (int)response["data"]["newRootCount"]);
            Assert.AreEqual(13, (int)response["data"]["delta"]);

            // On-disk file must be unchanged.
            Assert.AreEqual(15, CountRootsOnDisk(), "Refused save must leave the on-disk file untouched.");
        }

        [Test]
        public void Save_LargeShrinkPercent_RefusedWithoutConfirm()
        {
            // 10 -> 6: delta -4, under the absolute threshold (5) but 40% drop -> over 30%.
            // Verifies the percent branch fires independently of the absolute threshold.
            PopulateRoots(10, "Initial");
            SaveBaseline();
            Assert.AreEqual(10, CountRootsOnDisk());

            DeleteFirstNRoots(4);
            Assert.AreEqual(6, _testScene.rootCount);

            var response = InvokeSave();
            Assert.IsFalse((bool)response["success"], "Large percent shrink should be refused: " + response);
            Assert.AreEqual("destructive_save_blocked", (string)response["data"]["code"]);
            Assert.AreEqual(10, (int)response["data"]["oldRootCount"]);
            Assert.AreEqual(6, (int)response["data"]["newRootCount"]);
            Assert.AreEqual(4, (int)response["data"]["delta"]);

            Assert.AreEqual(10, CountRootsOnDisk(), "Refused save must leave the on-disk file untouched.");
        }

        [Test]
        public void Save_LargeShrink_WithConfirmReplace_Succeeds()
        {
            // Same setup as the absolute-shrink test, but pass confirmDestructiveSave=true.
            // The save should go through and the on-disk file should reflect the smaller state.
            PopulateRoots(15, "Initial");
            SaveBaseline();
            Assert.AreEqual(15, CountRootsOnDisk());

            DeleteFirstNRoots(13);
            Assert.AreEqual(2, _testScene.rootCount);

            var response = InvokeSave(confirmDestructiveSave: true);
            Assert.IsTrue((bool)response["success"], "Confirmed destructive save should succeed: " + response);
            Assert.AreEqual(2, CountRootsOnDisk(), "On-disk file should be rewritten with the new (smaller) state.");
        }

        [Test]
        public void Save_LargeShrink_WithSnakeCaseConfirm_Succeeds()
        {
            // Confirms the snake_case alias `confirm_destructive_save` is honored equivalently.
            PopulateRoots(12, "Initial");
            SaveBaseline();
            Assert.AreEqual(12, CountRootsOnDisk());

            DeleteFirstNRoots(10);
            Assert.AreEqual(2, _testScene.rootCount);

            var response = InvokeSave(confirmDestructiveSave: true, useSnakeCase: true);
            Assert.IsTrue((bool)response["success"], "snake_case confirm alias should succeed: " + response);
            Assert.AreEqual(2, CountRootsOnDisk(), "On-disk file should be rewritten with the new (smaller) state.");
        }
    }
}
