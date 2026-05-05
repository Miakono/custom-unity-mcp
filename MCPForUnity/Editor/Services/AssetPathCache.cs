using System.Collections.Concurrent;
using UnityEditor;

namespace MCPForUnity.Editor.Services
{
    /// <summary>
    /// In-memory bidirectional cache for GUID ↔ asset path lookups.
    /// AssetDatabase has its own internal caching, but these calls still cost a managed→native
    /// transition each time and can dominate when asset-heavy tools resolve many references in a
    /// single command. The cache front-runs both directions and is invalidated by an
    /// AssetPostprocessor on every asset import/move/delete.
    ///
    /// Use via static helpers: <see cref="GetPath"/>, <see cref="GetGuid"/>.
    /// Falls back to AssetDatabase on miss and populates both directions for future hits.
    /// </summary>
    public static class AssetPathCache
    {
        private static readonly ConcurrentDictionary<string, string> _guidToPath = new();
        private static readonly ConcurrentDictionary<string, string> _pathToGuid = new();
        private static long _hits;
        private static long _misses;

        /// <summary>
        /// Resolve a GUID to an asset path. Returns empty string if the GUID is unknown
        /// (mirroring AssetDatabase.GUIDToAssetPath behaviour).
        /// </summary>
        public static string GetPath(string guid)
        {
            if (string.IsNullOrEmpty(guid)) return string.Empty;

            if (_guidToPath.TryGetValue(guid, out var cached))
            {
                System.Threading.Interlocked.Increment(ref _hits);
                return cached;
            }

            System.Threading.Interlocked.Increment(ref _misses);
            string path = AssetDatabase.GUIDToAssetPath(guid) ?? string.Empty;
            if (path.Length > 0)
            {
                _guidToPath[guid] = path;
                _pathToGuid[path] = guid;
            }
            return path;
        }

        /// <summary>
        /// Resolve an asset path to a GUID. Returns empty string if the path is unknown
        /// (mirroring AssetDatabase.AssetPathToGUID behaviour).
        /// </summary>
        public static string GetGuid(string path)
        {
            if (string.IsNullOrEmpty(path)) return string.Empty;

            if (_pathToGuid.TryGetValue(path, out var cached))
            {
                System.Threading.Interlocked.Increment(ref _hits);
                return cached;
            }

            System.Threading.Interlocked.Increment(ref _misses);
            string guid = AssetDatabase.AssetPathToGUID(path) ?? string.Empty;
            if (guid.Length > 0)
            {
                _pathToGuid[path] = guid;
                _guidToPath[guid] = path;
            }
            return guid;
        }

        public static (long hits, long misses) GetStats() =>
            (System.Threading.Interlocked.Read(ref _hits), System.Threading.Interlocked.Read(ref _misses));

        /// <summary>
        /// Drop all cached entries. Called by the AssetPostprocessor on any asset change.
        /// Cheap — ConcurrentDictionary.Clear() is O(N) where N is the cached entry count,
        /// not the project asset count.
        /// </summary>
        internal static void Invalidate()
        {
            _guidToPath.Clear();
            _pathToGuid.Clear();
        }

        private sealed class Postprocessor : AssetPostprocessor
        {
            private static void OnPostprocessAllAssets(
                string[] importedAssets,
                string[] deletedAssets,
                string[] movedAssets,
                string[] movedFromAssetPaths)
            {
                if ((importedAssets?.Length ?? 0) == 0
                    && (deletedAssets?.Length ?? 0) == 0
                    && (movedAssets?.Length ?? 0) == 0)
                {
                    return;
                }
                Invalidate();
            }
        }
    }
}
