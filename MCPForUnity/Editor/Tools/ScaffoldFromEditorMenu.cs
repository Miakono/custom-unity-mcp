using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;

namespace MCPForUnity.Editor.Tools
{
    /// <summary>
    /// Executes a Unity Editor menu item (any [MenuItem]-decorated method) and returns an
    /// asset-database diff so the caller can see exactly what assets the scaffolder created
    /// or modified. Generic — works for every Unity project, not just this one.
    ///
    /// Most projects have a handful of editor scaffolders under `Assets/Editor/` that create
    /// default ScriptableObjects, prefabs, or scenes. Without this tool, agents either need
    /// per-project MCP wrappers or manually rebuild the scaffolder logic in code. This tool
    /// gives them direct access to the existing menu item, with the response telling them
    /// what changed.
    ///
    /// Safety: paths in the destructive blacklist are refused. Callers are also encouraged
    /// to pass `dry_run=true` first to verify the menu path resolves.
    /// </summary>
    [McpForUnityTool("scaffold_from_editor_menu", AutoRegister = false)]
    public static class ScaffoldFromEditorMenu
    {
        // Hard-block menu paths that would corrupt the project or close the editor.
        private static readonly HashSet<string> _blacklist = new HashSet<string>(
            StringComparer.OrdinalIgnoreCase)
        {
            "File/Quit",
            "File/New Project...",
            "Edit/Project Settings/Reset",
            "Assets/Reimport All",
        };

        public static object HandleCommand(JObject @params)
        {
            string menuPath = @params?["menu_path"]?.ToString() ?? @params?["menuPath"]?.ToString();
            if (string.IsNullOrWhiteSpace(menuPath))
            {
                return new ErrorResponse("Required parameter 'menu_path' is missing.");
            }

            if (_blacklist.Contains(menuPath))
            {
                return new ErrorResponse($"Menu path '{menuPath}' is on the destructive blacklist.");
            }

            bool dryRun = ParamCoercion.CoerceBool(@params?["dry_run"], false)
                          || ParamCoercion.CoerceBool(@params?["dryRun"], false);
            int maxDiffEntries = ParamCoercion.CoerceInt(@params?["max_diff_entries"], 50);
            if (maxDiffEntries <= 0) maxDiffEntries = 50;

            // Snapshot asset GUIDs before. AssetDatabase.FindAssets("") returns every asset's
            // GUID; this is O(N) but fine — Unity's internal index makes this microsecond-cheap
            // even on big projects.
            HashSet<string> beforeGuids;
            Dictionary<string, long> beforeMtimes;
            try
            {
                beforeGuids = SnapshotGuids();
                beforeMtimes = SnapshotMtimes(beforeGuids);
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to snapshot AssetDatabase: {ex.Message}");
            }

            if (dryRun)
            {
                return new SuccessResponse($"Dry run — would execute '{menuPath}'.", new
                {
                    menuPath,
                    snapshot_asset_count = beforeGuids.Count,
                });
            }

            // Wrap in StartAssetEditing so any imports the scaffolder triggers don't refresh
            // the editor mid-scan. We still get a refresh at the end (StopAssetEditing)
            // before we compute the diff.
            bool startedEditing = false;
            bool executed = false;
            try
            {
                AssetDatabase.StartAssetEditing();
                startedEditing = true;
                executed = EditorApplication.ExecuteMenuItem(menuPath);
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"ExecuteMenuItem threw: {ex.Message}");
            }
            finally
            {
                if (startedEditing)
                {
                    try { AssetDatabase.StopAssetEditing(); }
                    catch (Exception ex) { McpLog.Warn($"scaffold_from_editor_menu: StopAssetEditing threw: {ex.Message}"); }
                }
            }

            if (!executed)
            {
                return new ErrorResponse(
                    $"Failed to execute '{menuPath}'. It may be invalid, disabled, or context-dependent (some menu items are only enabled when a specific selection / window is active).");
            }

            // Diff
            HashSet<string> afterGuids;
            try
            {
                afterGuids = SnapshotGuids();
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Executed '{menuPath}' but failed to compute diff: {ex.Message}");
            }

            var added = afterGuids.Except(beforeGuids)
                .Select(g => AssetDatabase.GUIDToAssetPath(g))
                .Where(p => !string.IsNullOrEmpty(p))
                .OrderBy(p => p, StringComparer.OrdinalIgnoreCase)
                .Take(maxDiffEntries)
                .ToList();

            var removed = beforeGuids.Except(afterGuids)
                .Take(maxDiffEntries)
                .ToList(); // GUIDs only — paths are gone

            var modified = new List<string>();
            foreach (var guid in beforeGuids)
            {
                if (!afterGuids.Contains(guid)) continue;
                var path = AssetDatabase.GUIDToAssetPath(guid);
                if (string.IsNullOrEmpty(path)) continue;
                long beforeMt = beforeMtimes.TryGetValue(guid, out var bm) ? bm : 0;
                long afterMt = GetMtime(path);
                if (afterMt != beforeMt && afterMt > 0)
                {
                    modified.Add(path);
                    if (modified.Count >= maxDiffEntries) break;
                }
            }

            return new SuccessResponse($"Executed '{menuPath}'.", new
            {
                menuPath,
                added_assets = added,
                removed_asset_guids = removed,
                modified_assets = modified,
                added_count = added.Count,
                removed_count = removed.Count,
                modified_count = modified.Count,
            });
        }

        private static HashSet<string> SnapshotGuids()
        {
            var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            // Empty filter returns every GUID under Assets/. Project Settings live elsewhere
            // and are excluded — that's the right scope for "scaffolders create assets".
            string[] guids = AssetDatabase.FindAssets(string.Empty);
            for (int i = 0; i < guids.Length; i++) set.Add(guids[i]);
            return set;
        }

        private static Dictionary<string, long> SnapshotMtimes(HashSet<string> guids)
        {
            var map = new Dictionary<string, long>(guids.Count);
            foreach (var guid in guids)
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                if (string.IsNullOrEmpty(path)) continue;
                long mt = GetMtime(path);
                if (mt > 0) map[guid] = mt;
            }
            return map;
        }

        private static long GetMtime(string assetRelativePath)
        {
            try
            {
                var full = System.IO.Path.GetFullPath(assetRelativePath);
                if (!System.IO.File.Exists(full)) return 0;
                return System.IO.File.GetLastWriteTimeUtc(full).Ticks;
            }
            catch
            {
                return 0;
            }
        }
    }
}
