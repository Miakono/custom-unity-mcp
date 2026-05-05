using System;
using System.Collections.Generic;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Runtime.Helpers;
using Unity.Profiling;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.Profiler
{
    /// <summary>
    /// Data structure for a profiler snapshot capturing CPU, GPU, Memory and Rendering stats.
    /// All Capture() methods read from <see cref="ProfilerRecorderPool"/>, which holds
    /// long-lived ProfilerRecorder instances. The previous implementation created
    /// ephemeral recorders inside using-blocks and read LastValue immediately, which
    /// always returned 0 because Unity needs at least one frame to elapse before any
    /// recorder has data.
    /// </summary>
    [Serializable]
    public class ProfilerSnapshot
    {
        public long timestamp;
        public int frameIndex;
        public double frameTimeMs;
        public double fps;

        // CPU Data
        public CpuData cpu;

        // GPU Data
        public GpuData gpu;

        // Memory Data
        public MemoryData memory;

        // Rendering Data
        public RenderingData rendering;

        // Audio Data
        public AudioData audio;

        public static ProfilerSnapshot Capture()
        {
            var snapshot = new ProfilerSnapshot
            {
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
                frameIndex = UnityEngine.Time.frameCount,
                cpu = CpuData.Capture(),
                gpu = GpuData.Capture(),
                memory = MemoryData.Capture(),
                rendering = RenderingData.Capture(),
                audio = AudioData.Capture()
            };

            // Frame time priority: total > main thread > render thread > 0
            // Total Frame Time is the most representative if available.
            if (snapshot.cpu.totalTimeMs > 0)
            {
                snapshot.frameTimeMs = snapshot.cpu.totalTimeMs;
            }
            else if (snapshot.cpu.mainThreadTimeMs > 0)
            {
                snapshot.frameTimeMs = snapshot.cpu.mainThreadTimeMs;
            }
            else if (snapshot.cpu.renderThreadTimeMs > 0)
            {
                snapshot.frameTimeMs = snapshot.cpu.renderThreadTimeMs;
            }

            snapshot.fps = snapshot.frameTimeMs > 0 ? 1000.0 / snapshot.frameTimeMs : 0;

            return snapshot;
        }
    }

    [Serializable]
    public class CpuData
    {
        public double totalTimeMs;
        public double mainThreadTimeMs;
        public double renderThreadTimeMs;
        public double scriptsTimeMs;
        public double physicsTimeMs;
        public double animationTimeMs;
        public double uiTimeMs;
        public double renderingTimeMs;
        public double editorOverheadMs;
        public double gcTimeMs;

        // Per-category breakdown
        public Dictionary<string, double> categoryBreakdown;

        public static CpuData Capture()
        {
            var data = new CpuData
            {
                categoryBreakdown = new Dictionary<string, double>()
            };

            try
            {
                // Use the average across the recorder's sample buffer for a more stable
                // frame-time reading than a single LastValue. Buffer is ~60 samples
                // (~1s at 60 Hz), so this smooths short spikes.
                data.totalTimeMs = ProfilerRecorderPool.ReadAverageNanosecondsAsMs(
                    ProfilerCategory.Internal, ProfilerRecorderPool.Counters.CpuTotalFrameTime);
                data.mainThreadTimeMs = ProfilerRecorderPool.ReadAverageNanosecondsAsMs(
                    ProfilerCategory.Internal, ProfilerRecorderPool.Counters.CpuMainThreadFrameTime);
                data.renderThreadTimeMs = ProfilerRecorderPool.ReadAverageNanosecondsAsMs(
                    ProfilerCategory.Internal, ProfilerRecorderPool.Counters.CpuRenderThreadFrameTime);

                // Build category breakdown — only include categories with non-zero data.
                // Unity doesn't expose per-category CPU time as a single counter, so this
                // is best-effort and will be sparse outside of deep profiling.
                if (data.totalTimeMs > 0) data.categoryBreakdown["Total"] = data.totalTimeMs;
                if (data.mainThreadTimeMs > 0) data.categoryBreakdown["MainThread"] = data.mainThreadTimeMs;
                if (data.renderThreadTimeMs > 0) data.categoryBreakdown["RenderThread"] = data.renderThreadTimeMs;
            }
            catch (Exception ex)
            {
                McpLog.Warn($"[ProfilerSnapshot] Error capturing CPU data: {ex.Message}");
            }

            return data;
        }
    }

    [Serializable]
    public class GpuData
    {
        public double totalTimeMs;
        public double opaqueTimeMs;
        public double transparentTimeMs;
        public double shadowTimeMs;
        public double postProcessingTimeMs;

        public static GpuData Capture()
        {
            var data = new GpuData();

            try
            {
                data.totalTimeMs = ProfilerRecorderPool.ReadAverageNanosecondsAsMs(
                    ProfilerCategory.Render, ProfilerRecorderPool.Counters.GpuFrameTime);
                // Note: per-pass GPU breakdown (opaque/transparent/shadow/post) is not
                // exposed as discrete counters in standard Unity. Would require Frame
                // Debugger or a custom render-pass profiler. Leaving these as 0 is honest.
            }
            catch (Exception ex)
            {
                McpLog.Warn($"[ProfilerSnapshot] Error capturing GPU data: {ex.Message}");
            }

            return data;
        }
    }

    [Serializable]
    public class MemoryData
    {
        public long totalUsedMemoryBytes;
        public long totalAllocatedMemoryBytes;
        public long gcHeapSizeBytes;
        public long gcUsedMemoryBytes;
        public long gcAllocatedInFrameBytes;
        public long textureMemoryBytes;
        public long meshMemoryBytes;
        public long audioMemoryBytes;
        public long videoMemoryBytes;
        public long renderTextureMemoryBytes;
        public long bufferMemoryBytes;
        public int gcCollectionCount;
        public long managedHeapSizeBytes;
        public long managedUsedSizeBytes;

        public int gameObjectCount;
        public int sceneObjectCount;
        public int assetCount;

        // System memory
        public long systemTotalMemoryBytes;
        public long systemUsedMemoryBytes;

        public static MemoryData Capture()
        {
            var data = new MemoryData();

            try
            {
                // Prefer Profiler counters; fall back to GC.GetTotalMemory if they're 0
                // (which can happen in edit mode when nothing is rendering).
                data.totalUsedMemoryBytes = ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Memory, ProfilerRecorderPool.Counters.TotalUsedMemory);
                if (data.totalUsedMemoryBytes == 0)
                {
                    data.totalUsedMemoryBytes = GC.GetTotalMemory(forceFullCollection: false);
                }

                data.totalAllocatedMemoryBytes = ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Memory, ProfilerRecorderPool.Counters.TotalReservedMemory);

                data.gcUsedMemoryBytes = ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Memory, ProfilerRecorderPool.Counters.GcUsedMemory);
                data.gcHeapSizeBytes = ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Memory, ProfilerRecorderPool.Counters.GcReservedMemory);
                data.gcAllocatedInFrameBytes = ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Memory, ProfilerRecorderPool.Counters.GcAllocatedInFrame);

                data.textureMemoryBytes = ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Memory, ProfilerRecorderPool.Counters.TextureMemory);
                data.meshMemoryBytes = ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Memory, ProfilerRecorderPool.Counters.MeshMemory);
                data.audioMemoryBytes = ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Memory, ProfilerRecorderPool.Counters.AudioReservedMemory);
                data.videoMemoryBytes = ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Memory, ProfilerRecorderPool.Counters.VideoMemory);

                // Object counts give Claude actionable signal about scene complexity.
                data.gameObjectCount = (int)ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Memory, ProfilerRecorderPool.Counters.GameObjectCount);
                data.sceneObjectCount = (int)ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Memory, ProfilerRecorderPool.Counters.SceneObjectCount);
                data.assetCount = (int)ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Memory, ProfilerRecorderPool.Counters.AssetCount);

                // Managed-heap shadow figures — useful when comparing against profiler totals.
                data.managedHeapSizeBytes = GC.GetTotalMemory(false);
                data.managedUsedSizeBytes = data.managedHeapSizeBytes;

                // GC collection count (gen 0)
                data.gcCollectionCount = GC.CollectionCount(0);

                // System memory
                data.systemTotalMemoryBytes = (long)UnityEngine.SystemInfo.systemMemorySize * 1024 * 1024;
            }
            catch (Exception ex)
            {
                McpLog.Warn($"[ProfilerSnapshot] Error capturing memory data: {ex.Message}");
            }

            return data;
        }
    }

    [Serializable]
    public class RenderingData
    {
        public int drawCalls;
        public int setPassCalls;
        public int triangles;
        public int vertices;
        public int shadowCasters;
        public int batches;
        public int staticBatchedDrawCalls;
        public int dynamicBatchedDrawCalls;
        public int instancedDrawCalls;

        public static RenderingData Capture()
        {
            var data = new RenderingData();

            try
            {
                // Primary path: ProfilerRecorder counters from the Render category.
                // These work in both Editor and built players, in edit mode and play mode,
                // wherever the renderer ran a frame recently.
                data.drawCalls = (int)ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Render, ProfilerRecorderPool.Counters.DrawCallsCount);
                data.setPassCalls = (int)ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Render, ProfilerRecorderPool.Counters.SetPassCallsCount);
                data.triangles = (int)ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Render, ProfilerRecorderPool.Counters.TrianglesCount);
                data.vertices = (int)ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Render, ProfilerRecorderPool.Counters.VerticesCount);
                data.batches = (int)ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Render, ProfilerRecorderPool.Counters.BatchesCount);
                data.shadowCasters = (int)ProfilerRecorderPool.ReadLong(
                    ProfilerCategory.Render, ProfilerRecorderPool.Counters.ShadowCastersCount);

                // Secondary path: UnityEditor.UnityStats exposes per-batch breakdowns
                // (static/dynamic/instanced) that aren't covered by the Render counters.
                CaptureFromUnityStats(data);
            }
            catch (Exception ex)
            {
                McpLog.Warn($"[ProfilerSnapshot] Error capturing rendering data: {ex.Message}");
            }

            return data;
        }

        private static void CaptureFromUnityStats(RenderingData data)
        {
            // UnityEditor.UnityStats fields/properties vary by version. Look up via
            // reflection so this code compiles against any 2020+ editor and silently
            // skips fields that have moved or been renamed.
            try
            {
                var unityStatsType = typeof(UnityEditor.Editor).Assembly.GetType("UnityEditor.UnityStats");
                if (unityStatsType == null) return;

                // Prefer fields, fall back to properties for newer Unity revisions.
                int? TryReadInt(string name)
                {
                    try
                    {
                        var f = unityStatsType.GetField(name,
                            System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public);
                        if (f != null) return Convert.ToInt32(f.GetValue(null));
                        var p = unityStatsType.GetProperty(name,
                            System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public);
                        if (p != null) return Convert.ToInt32(p.GetValue(null));
                    }
                    catch { }
                    return null;
                }

                // Only overwrite if UnityStats has a non-zero value AND the recorder didn't
                // already populate it. UnityStats reflects the last frame the SceneView /
                // GameView rendered, which can be more reliable in edit mode.
                int? dc = TryReadInt("drawCalls");
                if (dc.HasValue && data.drawCalls == 0) data.drawCalls = dc.Value;

                int? sp = TryReadInt("setPassCalls");
                if (sp.HasValue && data.setPassCalls == 0) data.setPassCalls = sp.Value;

                int? tris = TryReadInt("triangles");
                if (tris.HasValue && data.triangles == 0) data.triangles = tris.Value;

                int? verts = TryReadInt("vertices");
                if (verts.HasValue && data.vertices == 0) data.vertices = verts.Value;

                int? batches = TryReadInt("batches");
                if (batches.HasValue && data.batches == 0) data.batches = batches.Value;

                // These are UnityStats-only (no recorder equivalent).
                int? statBatches = TryReadInt("staticBatchedDrawCalls");
                if (statBatches.HasValue) data.staticBatchedDrawCalls = statBatches.Value;

                int? dynBatches = TryReadInt("dynamicBatchedDrawCalls");
                if (dynBatches.HasValue) data.dynamicBatchedDrawCalls = dynBatches.Value;

                int? instDc = TryReadInt("instancedDrawCalls");
                if (instDc.HasValue) data.instancedDrawCalls = instDc.Value;
            }
            catch { }
        }
    }

    [Serializable]
    public class AudioData
    {
        public int totalAudioSources;
        public int playingAudioSources;
        public int voiceCount;
        public float audioLevel;
        public float clipCount;

        public static AudioData Capture()
        {
            var data = new AudioData();

            try
            {
                if (UnityEngine.Application.isPlaying)
                {
                    var audioSources = UnityObjectCompatibility.FindObjectsByType<UnityEngine.AudioSource>();
                    data.totalAudioSources = audioSources.Length;
                    data.playingAudioSources = 0;
                    foreach (var source in audioSources)
                    {
                        if (source.isPlaying)
                            data.playingAudioSources++;
                    }
                }

                // dspLoad is not available in all Unity versions.
                data.audioLevel = 0f;
            }
            catch (Exception ex)
            {
                McpLog.Warn($"[ProfilerSnapshot] Error capturing audio data: {ex.Message}");
            }

            return data;
        }
    }
}
