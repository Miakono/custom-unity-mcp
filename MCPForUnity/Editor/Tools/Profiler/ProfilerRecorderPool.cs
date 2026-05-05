using System;
using System.Collections.Generic;
using Unity.Profiling;
using UnityEditor;

namespace MCPForUnity.Editor.Tools.Profiler
{
    /// <summary>
    /// Long-lived pool of Unity ProfilerRecorder instances.
    ///
    /// The previous implementation created a recorder via ProfilerRecorder.StartNew(...)
    /// inside a using block and immediately read LastValue. ProfilerRecorder needs at
    /// least one frame to elapse before it has any sample data, so that pattern always
    /// returned 0 — which is why every CPU/GPU/render counter showed up as zero in the
    /// MCP responses.
    ///
    /// This pool starts each recorder once on first read and keeps it alive for the
    /// editor session, so subsequent reads return real values. Recorders are disposed on
    /// assembly reload (Unity disposes them anyway, but explicit cleanup avoids native
    /// handle leaks during repeated reloads).
    /// </summary>
    internal static class ProfilerRecorderPool
    {
        private struct Key : IEquatable<Key>
        {
            public ProfilerCategory Category;
            public string Name;

            public bool Equals(Key other) => Category == other.Category && Name == other.Name;
            public override bool Equals(object obj) => obj is Key k && Equals(k);
            public override int GetHashCode() => unchecked(Category.GetHashCode() * 397 ^ (Name?.GetHashCode() ?? 0));
        }

        private static readonly Dictionary<Key, ProfilerRecorder> _recorders = new();
        private static readonly object _lock = new();
        private static bool _registered;

        // Common counter names — exposed as constants so callers don't risk typos.
        // Verified against Unity 6000.x. Unity's Profiler Counters Reference is the
        // authoritative source; counter availability varies by category and Unity version.
        public static class Counters
        {
            // ProfilerCategory.Internal
            public const string CpuTotalFrameTime = "CPU Total Frame Time";
            public const string CpuMainThreadFrameTime = "CPU Main Thread Frame Time";
            public const string CpuRenderThreadFrameTime = "CPU Render Thread Frame Time";

            // ProfilerCategory.Render
            public const string GpuFrameTime = "GPU Frame Time";
            public const string DrawCallsCount = "Draw Calls Count";
            public const string TrianglesCount = "Triangles Count";
            public const string VerticesCount = "Vertices Count";
            public const string BatchesCount = "Batches Count";
            public const string SetPassCallsCount = "SetPass Calls Count";
            public const string ShadowCastersCount = "Shadow Casters Count";

            // ProfilerCategory.Memory
            public const string TotalUsedMemory = "Total Used Memory";
            public const string TotalReservedMemory = "Total Reserved Memory";
            public const string GcUsedMemory = "GC Used Memory";
            public const string GcReservedMemory = "GC Reserved Memory";
            public const string GcAllocatedInFrame = "GC Allocated In Frame";
            public const string TextureMemory = "Texture Memory";
            public const string MeshMemory = "Mesh Memory";
            public const string AudioReservedMemory = "Audio Reserved Memory";
            public const string AudioUsedMemory = "Audio Used Memory";
            public const string VideoMemory = "Video Memory";
            public const string GameObjectCount = "Game Object Count";
            public const string AssetCount = "Asset Count";
            public const string SceneObjectCount = "Scene Object Count";

            // ProfilerCategory.Physics
            public const string PhysicsActiveDynamicBodies = "Active Dynamic Bodies";
            public const string PhysicsActiveKinematicBodies = "Active Kinematic Bodies";
            public const string PhysicsStaticColliders = "Static Colliders";
            public const string PhysicsDynamicColliders = "Dynamic Colliders";

            // ProfilerCategory.Network
            public const string NetworkSentBytes = "Network Sent Bytes";
            public const string NetworkReceivedBytes = "Network Received Bytes";
        }

        [InitializeOnLoadMethod]
        private static void RegisterReloadCleanup()
        {
            if (_registered) return;
            _registered = true;
            AssemblyReloadEvents.beforeAssemblyReload += DisposeAll;
        }

        /// <summary>
        /// Returns the most recent value of a counter as a long, or 0 if the recorder
        /// hasn't captured a sample yet (e.g. first frame after starting). Lazily starts
        /// the recorder on first call.
        /// </summary>
        public static long ReadLong(ProfilerCategory category, string counter)
        {
            var recorder = GetOrStart(category, counter);
            if (!recorder.Valid || recorder.Count == 0) return 0;
            return recorder.LastValue;
        }

        /// <summary>
        /// Convenience wrapper that converts a nanosecond-valued counter to milliseconds.
        /// Most CPU/GPU time counters report in ns.
        /// </summary>
        public static double ReadNanosecondsAsMs(ProfilerCategory category, string counter)
        {
            long ns = ReadLong(category, counter);
            return ns / 1_000_000.0;
        }

        /// <summary>
        /// Average of all currently buffered samples, in nanoseconds. Larger sample window
        /// gives a stabler frame-time reading than a single LastValue. Returns 0 if no
        /// samples are available.
        /// </summary>
        public static double ReadAverageNanosecondsAsMs(ProfilerCategory category, string counter)
        {
            var recorder = GetOrStart(category, counter);
            if (!recorder.Valid || recorder.Count == 0) return 0;

            // Sum across the recorder's sample buffer for a smoother frame-time reading.
            long sum = 0;
            int count = recorder.Count;
            for (int i = 0; i < count; i++)
            {
                sum += recorder.GetSample(i).Value;
            }
            return (sum / (double)count) / 1_000_000.0;
        }

        private static ProfilerRecorder GetOrStart(ProfilerCategory category, string counter)
        {
            var key = new Key { Category = category, Name = counter };
            lock (_lock)
            {
                if (_recorders.TryGetValue(key, out var existing) && existing.Valid)
                {
                    return existing;
                }

                // Allocate a recorder with capacity for ~one second of samples at 60 Hz so
                // ReadAverageNanosecondsAsMs can smooth across recent frames. Capacity is
                // a buffer size (samples kept), not a duration — Unity overwrites oldest.
                ProfilerRecorder rec;
                try
                {
                    rec = ProfilerRecorder.StartNew(category, counter, capacity: 60);
                }
                catch
                {
                    // Counter doesn't exist in this Unity version / on this platform.
                    // Cache an invalid recorder so we don't retry every call.
                    rec = default;
                }
                _recorders[key] = rec;
                return rec;
            }
        }

        private static void DisposeAll()
        {
            lock (_lock)
            {
                foreach (var rec in _recorders.Values)
                {
                    try
                    {
                        if (rec.Valid) rec.Dispose();
                    }
                    catch { }
                }
                _recorders.Clear();
            }
        }
    }
}
