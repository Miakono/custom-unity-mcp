using System;
using System.Reflection;
using UnityEditor;

namespace MCPForUnity.Editor.Helpers
{
    /// <summary>
    /// Optional integration with Singularity Group Hot Reload (com.singularitygroup.hotreload).
    /// When Hot Reload is installed AND its server is running, MCP can skip its own
    /// AssetDatabase.ImportAsset + RequestScriptCompilation calls for .cs edits and let
    /// Hot Reload's filesystem watcher patch the running domain instead.
    ///
    /// All access goes through reflection so the MCP package has no hard dependency on
    /// Hot Reload — projects without it pay only the one-time type-resolution cost.
    /// </summary>
    public static class HotReloadIntegration
    {
        private const string EditorCodePatcherTypeName = "SingularityGroup.HotReload.Editor.EditorCodePatcher";

        // The 'Started' property is internal in Hot Reload, so BindingFlags.NonPublic.
        private const BindingFlags StartedPropertyFlags =
            BindingFlags.Static | BindingFlags.NonPublic | BindingFlags.Public;

        // Re-resolving Type.GetType across every assembly is expensive; resolve once and
        // invalidate on assembly reload (Hot Reload's own asmdef may load/unload).
        private static bool _typeResolved;
        private static Type _editorCodePatcherType;
        private static PropertyInfo _startedProperty;

        // Hot Reload's server status can flap; cache the bool briefly so a burst of script
        // edits doesn't pay reflection overhead per call.
        private const double StartedCacheTtlSeconds = 1.5;
        private static DateTime _startedCachedAt;
        private static bool _startedCachedValue;

        [InitializeOnLoadMethod]
        private static void RegisterReloadInvalidation()
        {
            AssemblyReloadEvents.afterAssemblyReload += InvalidateCaches;
        }

        private static void InvalidateCaches()
        {
            _typeResolved = false;
            _editorCodePatcherType = null;
            _startedProperty = null;
            _startedCachedAt = DateTime.MinValue;
        }

        /// <summary>
        /// True when the Hot Reload editor assembly is loaded into the current domain.
        /// Cheap to call after the first lookup (cached until next assembly reload).
        /// </summary>
        public static bool IsAvailable => ResolveType() != null;

        /// <summary>
        /// True when Hot Reload is loaded AND its server reports as healthy/running.
        /// This is the signal MCP should gate "skip our own Refresh" behavior on, since
        /// Hot Reload only patches changes when its server is up.
        /// </summary>
        public static bool IsActive
        {
            get
            {
                var now = DateTime.UtcNow;
                if ((now - _startedCachedAt).TotalSeconds < StartedCacheTtlSeconds)
                {
                    return _startedCachedValue;
                }

                bool active = false;
                try
                {
                    var prop = ResolveStartedProperty();
                    if (prop != null)
                    {
                        active = prop.GetValue(null) is bool b && b;
                    }
                }
                catch
                {
                    // Hot Reload internals can throw during startup/shutdown — treat as inactive.
                    active = false;
                }

                _startedCachedValue = active;
                _startedCachedAt = now;
                return active;
            }
        }

        /// <summary>
        /// Decide whether a script-edit handler should defer compilation to Hot Reload
        /// instead of calling AssetDatabase.ImportAsset + RequestScriptCompilation.
        /// Returns true only when Hot Reload's server is actually running, so a paused or
        /// uninstalled Hot Reload falls back to MCP's normal refresh path.
        /// </summary>
        public static bool ShouldDeferScriptCompilation() => IsActive;

        private static Type ResolveType()
        {
            if (_typeResolved)
            {
                return _editorCodePatcherType;
            }

            // Type.GetType only finds types in mscorlib + the calling assembly without an
            // assembly-qualified name; Hot Reload lives in a separate asmdef, so we have
            // to scan loaded assemblies. Cheap when Hot Reload isn't present (single pass)
            // and cached after the first hit.
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                if (asm.IsDynamic)
                {
                    continue;
                }

                Type t;
                try
                {
                    t = asm.GetType(EditorCodePatcherTypeName, throwOnError: false);
                }
                catch
                {
                    continue;
                }

                if (t != null)
                {
                    _editorCodePatcherType = t;
                    break;
                }
            }

            _typeResolved = true;
            return _editorCodePatcherType;
        }

        private static PropertyInfo ResolveStartedProperty()
        {
            if (_startedProperty != null)
            {
                return _startedProperty;
            }

            var t = ResolveType();
            if (t == null)
            {
                return null;
            }

            _startedProperty = t.GetProperty("Started", StartedPropertyFlags);
            return _startedProperty;
        }
    }
}
