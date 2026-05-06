using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;

namespace MCPForUnity.Editor.Services
{
    /// <summary>
    /// Suppresses Unity's "External changes detected, reload scene?" dialog when the MCP
    /// (or any other tool that writes a .unity file followed by AssetDatabase.Refresh) modifies
    /// a scene that's currently loaded.
    ///
    /// Cause: SaveScene → ForceSynchronousImport re-imports the scene, but Unity's loaded scene
    /// object isn't auto-synced. On user focus, Unity detects disk≠memory and prompts.
    ///
    /// Fix: hook AssetPostprocessor.OnPostprocessAllAssets, see if any imported asset is a
    /// currently-loaded scene, and silently re-open it via EditorSceneManager.OpenScene with the
    /// SAME OpenSceneMode it was already in. The user never sees the dialog.
    ///
    /// Safety: only triggered for paths that BOTH (a) appear in importedAssets and (b) match a
    /// scene currently loaded in editor. Won't reload scenes the MCP didn't touch. Won't fight
    /// the user — if they have unsaved in-memory changes (scene.isDirty), we skip the auto-reload
    /// so their work isn't silently overwritten by the disk version.
    /// </summary>
    internal sealed class SceneSyncService : AssetPostprocessor
    {
        // When true, the next OnPostprocessAllAssets pass skips its scene-reload work — used by
        // tools that intentionally save+reimport (so we don't re-trigger their own work).
        // Most tools won't need this; it exists for the rare case where a tool wants strict
        // disk-write-then-explicit-OpenScene control.
        internal static bool SuppressNextPass;

        private static void OnPostprocessAllAssets(
            string[] importedAssets,
            string[] deletedAssets,
            string[] movedAssets,
            string[] movedFromAssetPaths)
        {
            if (SuppressNextPass)
            {
                SuppressNextPass = false;
                return;
            }

            if (importedAssets == null || importedAssets.Length == 0) return;

            // Build a set of imported scene paths so the inner loop is O(loadedScenes).
            HashSet<string> importedScenePaths = null;
            for (int i = 0; i < importedAssets.Length; i++)
            {
                var p = importedAssets[i];
                if (string.IsNullOrEmpty(p)) continue;
                if (!p.EndsWith(".unity", System.StringComparison.OrdinalIgnoreCase)) continue;
                importedScenePaths ??= new HashSet<string>(System.StringComparer.OrdinalIgnoreCase);
                importedScenePaths.Add(p);
            }
            if (importedScenePaths == null) return;

            int loadedCount = SceneManager.sceneCount;
            for (int i = 0; i < loadedCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i);
                if (!scene.IsValid() || !scene.isLoaded) continue;
                if (string.IsNullOrEmpty(scene.path)) continue;
                if (!importedScenePaths.Contains(scene.path)) continue;

                // Don't clobber unsaved user work. If the loaded scene is dirty, the user has
                // in-memory changes that haven't been written; silently reloading would lose them.
                // Better to leave Unity's prompt visible in that rare case than to corrupt work.
                if (scene.isDirty) continue;

                try
                {
                    var mode = scene == EditorSceneManager.GetActiveScene()
                        ? OpenSceneMode.Single
                        : OpenSceneMode.Additive;

                    // OpenScene with Single replaces all scenes; with Additive replaces just this one
                    // (Unity treats re-opening an already-open additive scene as a refresh).
                    EditorSceneManager.OpenScene(scene.path, mode);
                }
                catch (System.Exception ex)
                {
                    // Don't bubble — the user will see the prompt as a fallback, which is at least
                    // not worse than the current behaviour.
                    Helpers.McpLog.Warn($"[SceneSyncService] Auto-reload of '{scene.path}' failed: {ex.Message}");
                }
            }
        }
    }
}
