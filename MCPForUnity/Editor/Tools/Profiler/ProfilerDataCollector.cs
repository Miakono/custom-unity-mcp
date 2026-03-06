using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json;
using Unity.Profiling;
using Unity.Profiling.Editor;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.Profiler
{
    /// <summary>
    /// Collects and aggregates profiler data over time for trend analysis.
    /// </summary>
    public class ProfilerDataCollector
    {
        private readonly List<ProfilerSnapshot> _snapshots = new List<ProfilerSnapshot>();
        private readonly int _maxSnapshots;
        private bool _isCollecting;
        private int _collectionIntervalFrames;
        private int _lastCollectionFrame;

        public bool IsCollecting => _isCollecting;
        public int SnapshotCount => _snapshots.Count;
        public IReadOnlyList<ProfilerSnapshot> Snapshots => _snapshots;

        public ProfilerDataCollector(int maxSnapshots = 300)
        {
            _maxSnapshots = maxSnapshots;
        }

        /// <summary>
        /// Starts collecting profiler snapshots.
        /// </summary>
        public void Start(int intervalFrames = 10)
        {
            _isCollecting = true;
            _collectionIntervalFrames = Math.Max(1, intervalFrames);
            _lastCollectionFrame = UnityEngine.Time.frameCount;
            McpLog.Info("[ProfilerDataCollector] Started collecting profiler data.");
        }

        /// <summary>
        /// Stops collecting profiler snapshots.
        /// </summary>
        public void Stop()
        {
            _isCollecting = false;
            McpLog.Info("[ProfilerDataCollector] Stopped collecting profiler data.");
        }

        /// <summary>
        /// Updates the collector - should be called regularly (e.g., from Update loop).
        /// </summary>
        public void Update()
        {
            if (!_isCollecting) return;

            int currentFrame = UnityEngine.Time.frameCount;
            if (currentFrame - _lastCollectionFrame >= _collectionIntervalFrames)
            {
                CollectSnapshot();
                _lastCollectionFrame = currentFrame;
            }
        }

        /// <summary>
        /// Collects a single snapshot immediately.
        /// </summary>
        public ProfilerSnapshot CollectSnapshot()
        {
            var snapshot = ProfilerSnapshot.Capture();
            _snapshots.Add(snapshot);

            // Maintain max size
            while (_snapshots.Count > _maxSnapshots)
            {
                _snapshots.RemoveAt(0);
            }

            return snapshot;
        }

        /// <summary>
        /// Clears all collected snapshots.
        /// </summary>
        public void Clear()
        {
            _snapshots.Clear();
        }

        /// <summary>
        /// Gets aggregated statistics from collected snapshots.
        /// </summary>
        public AggregatedStats GetAggregatedStats(int lastN = -1)
        {
            var snapshots = lastN > 0 ? _snapshots.TakeLast(lastN).ToList() : _snapshots;
            
            if (snapshots.Count == 0)
            {
                return new AggregatedStats();
            }

            return new AggregatedStats
            {
                sampleCount = snapshots.Count,
                avgFrameTimeMs = snapshots.Average(s => s.frameTimeMs),
                minFrameTimeMs = snapshots.Min(s => s.frameTimeMs),
                maxFrameTimeMs = snapshots.Max(s => s.frameTimeMs),
                avgFps = snapshots.Average(s => s.fps),
                minFps = snapshots.Min(s => s.fps),
                maxFps = snapshots.Max(s => s.fps),
                avgMemoryBytes = (long)snapshots.Average(s => s.memory.totalUsedMemoryBytes),
                maxMemoryBytes = snapshots.Max(s => s.memory.totalUsedMemoryBytes),
                avgDrawCalls = snapshots.Average(s => s.rendering.drawCalls),
                maxDrawCalls = snapshots.Max(s => s.rendering.drawCalls)
            };
        }

        /// <summary>
        /// Saves snapshots to a JSON file.
        /// </summary>
        public bool SaveToFile(string filePath)
        {
            try
            {
                var data = new ProfilerCaptureData
                {
                    capturedAt = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
                    unityVersion = UnityEngine.Application.unityVersion,
                    platform = UnityEngine.Application.platform.ToString(),
                    snapshots = _snapshots.ToList()
                };

                string json = JsonConvert.SerializeObject(data, Formatting.Indented);
                File.WriteAllText(filePath, json);
                return true;
            }
            catch (Exception ex)
            {
                McpLog.Error($"[ProfilerDataCollector] Failed to save capture: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Loads snapshots from a JSON file.
        /// </summary>
        public bool LoadFromFile(string filePath)
        {
            try
            {
                if (!File.Exists(filePath))
                {
                    McpLog.Error($"[ProfilerDataCollector] Capture file not found: {filePath}");
                    return false;
                }

                string json = File.ReadAllText(filePath);
                var data = JsonConvert.DeserializeObject<ProfilerCaptureData>(json);
                
                _snapshots.Clear();
                _snapshots.AddRange(data.snapshots);
                return true;
            }
            catch (Exception ex)
            {
                McpLog.Error($"[ProfilerDataCollector] Failed to load capture: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Gets the default capture directory.
        /// </summary>
        public static string GetDefaultCaptureDirectory()
        {
            string path = Path.Combine(Application.dataPath, "..", "ProfilerCaptures");
            path = Path.GetFullPath(path);
            
            if (!Directory.Exists(path))
            {
                Directory.CreateDirectory(path);
            }
            
            return path;
        }

        /// <summary>
        /// Generates a unique capture file name.
        /// </summary>
        public static string GenerateCaptureFileName()
        {
            string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            return $"profiler_capture_{timestamp}.json";
        }
    }

    /// <summary>
    /// Aggregated statistics from multiple profiler snapshots.
    /// </summary>
    [Serializable]
    public class AggregatedStats
    {
        public int sampleCount;
        public double avgFrameTimeMs;
        public double minFrameTimeMs;
        public double maxFrameTimeMs;
        public double avgFps;
        public double minFps;
        public double maxFps;
        public long avgMemoryBytes;
        public long maxMemoryBytes;
        public double avgDrawCalls;
        public int maxDrawCalls;
    }

    /// <summary>
    /// Complete profiler capture data for serialization.
    /// </summary>
    [Serializable]
    public class ProfilerCaptureData
    {
        public long capturedAt;
        public string unityVersion;
        public string platform;
        public List<ProfilerSnapshot> snapshots;
    }
}
