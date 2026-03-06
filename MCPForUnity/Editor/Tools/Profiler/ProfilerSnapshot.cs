using System;
using System.Collections.Generic;
using Unity.Profiling;
using Unity.Profiling.Editor;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.Profiler
{
    /// <summary>
    /// Data structure for a profiler snapshot capturing CPU, GPU, Memory and Rendering stats.
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
            
            // Calculate frame time and FPS from render thread time if available
            if (snapshot.cpu.renderThreadTimeMs > 0)
            {
                snapshot.frameTimeMs = snapshot.cpu.renderThreadTimeMs;
            }
            else if (snapshot.cpu.mainThreadTimeMs > 0)
            {
                snapshot.frameTimeMs = snapshot.cpu.mainThreadTimeMs;
            }
            else
            {
                snapshot.frameTimeMs = snapshot.cpu.totalTimeMs;
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
                // Get frame time from ProfilerRecorder if available
                using (var totalTimeRecorder = ProfilerRecorder.StartNew(ProfilerCategory.Internal, "CPU Total Frame Time"))
                using (var mainThreadRecorder = ProfilerRecorder.StartNew(ProfilerCategory.Internal, "CPU Main Thread Frame Time"))
                using (var renderThreadRecorder = ProfilerRecorder.StartNew(ProfilerCategory.Internal, "CPU Render Thread Frame Time"))
                {
                    // Give a frame for recorders to capture data
                    if (totalTimeRecorder.Valid && totalTimeRecorder.Count > 0)
                        data.totalTimeMs = totalTimeRecorder.LastValue / 1000000.0; // Convert ns to ms
                    if (mainThreadRecorder.Valid && mainThreadRecorder.Count > 0)
                        data.mainThreadTimeMs = mainThreadRecorder.LastValue / 1000000.0;
                    if (renderThreadRecorder.Valid && renderThreadRecorder.Count > 0)
                        data.renderThreadTimeMs = renderThreadRecorder.LastValue / 1000000.0;
                }

                // Try to get category-specific timings
                CaptureCategoryTimes(data);
            }
            catch (Exception ex)
            {
                McpLog.Warn($"[ProfilerSnapshot] Error capturing CPU data: {ex.Message}");
            }

            return data;
        }

        private static void CaptureCategoryTimes(CpuData data)
        {
            // Scripting time
            try
            {
                using (var recorder = ProfilerRecorder.StartNew(ProfilerCategory.Scripts, "Scripting"))
                {
                    if (recorder.Valid && recorder.Count > 0)
                        data.scriptsTimeMs = recorder.LastValue / 1000000.0;
                }
            }
            catch { }

            // Physics time
            try
            {
                using (var recorder = ProfilerRecorder.StartNew(ProfilerCategory.Physics, "Physics.Processing"))
                {
                    if (recorder.Valid && recorder.Count > 0)
                        data.physicsTimeMs = recorder.LastValue / 1000000.0;
                }
            }
            catch { }

            // Animation time
            try
            {
                using (var recorder = ProfilerRecorder.StartNew(ProfilerCategory.Animation, "Animation.Update"))
                {
                    if (recorder.Valid && recorder.Count > 0)
                        data.animationTimeMs = recorder.LastValue / 1000000.0;
                }
            }
            catch { }

            // UI time
            try
            {
                using (var recorder = ProfilerRecorder.StartNew(ProfilerCategory.UI, "UI"))
                {
                    if (recorder.Valid && recorder.Count > 0)
                        data.uiTimeMs = recorder.LastValue / 1000000.0;
                }
            }
            catch { }

            // Rendering time
            try
            {
                using (var recorder = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Render"))
                {
                    if (recorder.Valid && recorder.Count > 0)
                        data.renderingTimeMs = recorder.LastValue / 1000000.0;
                }
            }
            catch { }

            // GC time
            try
            {
                using (var recorder = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "GC.Collect"))
                {
                    if (recorder.Valid && recorder.Count > 0)
                        data.gcTimeMs = recorder.LastValue / 1000000.0;
                }
            }
            catch { }

            // Build category breakdown
            if (data.scriptsTimeMs > 0) data.categoryBreakdown["Scripts"] = data.scriptsTimeMs;
            if (data.physicsTimeMs > 0) data.categoryBreakdown["Physics"] = data.physicsTimeMs;
            if (data.animationTimeMs > 0) data.categoryBreakdown["Animation"] = data.animationTimeMs;
            if (data.uiTimeMs > 0) data.categoryBreakdown["UI"] = data.uiTimeMs;
            if (data.renderingTimeMs > 0) data.categoryBreakdown["Rendering"] = data.renderingTimeMs;
            if (data.gcTimeMs > 0) data.categoryBreakdown["GC"] = data.gcTimeMs;
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
                using (var recorder = ProfilerRecorder.StartNew(ProfilerCategory.Render, "GPU Frame Time"))
                {
                    if (recorder.Valid && recorder.Count > 0)
                        data.totalTimeMs = recorder.LastValue / 1000000.0;
                }
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
        public long textureMemoryBytes;
        public long meshMemoryBytes;
        public long audioMemoryBytes;
        public long renderTextureMemoryBytes;
        public long bufferMemoryBytes;
        public int gcCollectionCount;
        public long managedHeapSizeBytes;
        public long managedUsedSizeBytes;
        
        // System memory
        public long systemTotalMemoryBytes;
        public long systemUsedMemoryBytes;

        public static MemoryData Capture()
        {
            var data = new MemoryData();

            try
            {
                // Total memory
                data.totalUsedMemoryBytes = GC.GetTotalMemory(false);
                data.totalAllocatedMemoryBytes = GC.GetTotalMemory(true);

                // Try to get more detailed memory info from ProfilerRecorder
                using (var recorder = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "Total Used Memory"))
                {
                    if (recorder.Valid && recorder.Count > 0)
                        data.totalUsedMemoryBytes = (long)recorder.LastValue;
                }

                // Texture memory
                try
                {
                    using (var recorder = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "Texture Memory"))
                    {
                        if (recorder.Valid && recorder.Count > 0)
                            data.textureMemoryBytes = (long)recorder.LastValue;
                    }
                }
                catch { }

                // Mesh memory
                try
                {
                    using (var recorder = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "Mesh Memory"))
                    {
                        if (recorder.Valid && recorder.Count > 0)
                            data.meshMemoryBytes = (long)recorder.LastValue;
                    }
                }
                catch { }

                // Audio memory
                try
                {
                    using (var recorder = ProfilerRecorder.StartNew(ProfilerCategory.Audio, "Audio AudioManager"))
                    {
                        if (recorder.Valid && recorder.Count > 0)
                            data.audioMemoryBytes = (long)recorder.LastValue;
                    }
                }
                catch { }

                // Render texture memory
                try
                {
                    using (var recorder = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "Render Texture Memory"))
                    {
                        if (recorder.Valid && recorder.Count > 0)
                            data.renderTextureMemoryBytes = (long)recorder.LastValue;
                    }
                }
                catch { }

                // GC collection count
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
                // Try to get rendering stats from Unity's internal APIs
                // These may not be available in all Unity versions
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
            // Use reflection to try to access Unity's internal rendering statistics
            // This is best-effort as the APIs change between versions
            try
            {
                var unityStatsType = typeof(UnityEditor.Editor).Assembly.GetType("UnityEditor.UnityStats");
                if (unityStatsType != null)
                {
                    var drawCallsField = unityStatsType.GetField("drawCalls", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public);
                    if (drawCallsField != null)
                        data.drawCalls = (int)drawCallsField.GetValue(null);

                    var setPassCallsField = unityStatsType.GetField("setPassCalls", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public);
                    if (setPassCallsField != null)
                        data.setPassCalls = (int)setPassCallsField.GetValue(null);

                    var trianglesField = unityStatsType.GetField("triangles", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public);
                    if (trianglesField != null)
                        data.triangles = (int)trianglesField.GetValue(null);

                    var verticesField = unityStatsType.GetField("vertices", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public);
                    if (verticesField != null)
                        data.vertices = (int)verticesField.GetValue(null);

                    var batchesField = unityStatsType.GetField("batches", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public);
                    if (batchesField != null)
                        data.batches = (int)batchesField.GetValue(null);

                    var staticBatchesField = unityStatsType.GetField("staticBatchedDrawCalls", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public);
                    if (staticBatchesField != null)
                        data.staticBatchedDrawCalls = (int)staticBatchesField.GetValue(null);

                    var dynamicBatchesField = unityStatsType.GetField("dynamicBatchedDrawCalls", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public);
                    if (dynamicBatchesField != null)
                        data.dynamicBatchedDrawCalls = (int)dynamicBatchesField.GetValue(null);

                    var instancedDrawCallsField = unityStatsType.GetField("instancedDrawCalls", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public);
                    if (instancedDrawCallsField != null)
                        data.instancedDrawCalls = (int)instancedDrawCallsField.GetValue(null);
                }
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
                // Count audio sources in the scene
                if (UnityEngine.Application.isPlaying)
                {
                    var audioSources = UnityEngine.Object.FindObjectsOfType<UnityEngine.AudioSource>();
                    data.totalAudioSources = audioSources.Length;
                    data.playingAudioSources = 0;
                    foreach (var source in audioSources)
                    {
                        if (source.isPlaying)
                            data.playingAudioSources++;
                    }
                }

                // Try to get DSP load
                data.audioLevel = UnityEngine.AudioSettings.dspLoad;
            }
            catch (Exception ex)
            {
                McpLog.Warn($"[ProfilerSnapshot] Error capturing audio data: {ex.Message}");
            }

            return data;
        }
    }
}
