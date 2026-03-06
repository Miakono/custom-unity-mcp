using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Unity.Profiling;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.Profiler
{
    /// <summary>
    /// Main controller for Unity Profiler integration via MCP.
    /// Handles profiling session management, data collection, and capture file operations.
    /// </summary>
    [McpForUnityTool("manage_profiler", AutoRegister = false, Group = "profiling")]
    public static class ProfilerController
    {
        private static ProfilerDataCollector _collector;
        private static bool _isRecording;
        private static List<ProfilerCategory> _enabledCategories = new List<ProfilerCategory>();
        
        // Default capture directory
        private static string CaptureDirectory => ProfilerDataCollector.GetDefaultCaptureDirectory();

        /// <summary>
        /// Main handler for profiler management actions.
        /// </summary>
        public static object HandleCommand(JObject @params)
        {
            if (@params == null)
            {
                return new ErrorResponse("Parameters cannot be null.");
            }

            var p = new ToolParams(@params);
            var actionResult = p.GetRequired("action");
            if (!actionResult.IsSuccess)
            {
                return new ErrorResponse(actionResult.ErrorMessage);
            }

            string action = actionResult.Value.ToLowerInvariant();

            switch (action)
            {
                case "start":
                    return StartProfiling(p);
                    
                case "stop":
                    return StopProfiling();
                    
                case "get_status":
                    return GetStatus();
                    
                case "get_snapshot":
                    return GetSnapshot();
                    
                case "get_memory":
                    return GetMemoryDetails();
                    
                case "get_cpu":
                    return GetCpuDetails();
                    
                case "get_rendering":
                    return GetRenderingDetails();
                    
                case "get_audio":
                    return GetAudioDetails();
                    
                case "clear":
                    return ClearData();
                    
                case "save_capture":
                    return SaveCapture(p);
                    
                case "load_capture":
                    return LoadCapture(p);
                    
                case "set_categories":
                    return SetCategories(p);
                    
                default:
                    return new ErrorResponse(
                        $"Unknown action: '{action}'. Supported actions: start, stop, get_status, get_snapshot, " +
                        "get_memory, get_cpu, get_rendering, get_audio, clear, save_capture, load_capture, set_categories"
                    );
            }
        }

        #region Profiling Session Control

        private static object StartProfiling(ToolParams p)
        {
            try
            {
                int intervalFrames = p.GetInt("intervalFrames", 10);
                bool deepProfiling = p.GetBool("deepProfiling", false);

                // Initialize collector if needed
                if (_collector == null)
                {
                    _collector = new ProfilerDataCollector();
                }

                // Enable deep profiling if requested
                if (deepProfiling && !Profiler.enabled)
                {
                    Profiler.enabled = true;
                    Profiler.deepProfiling = true;
                }

                // Start collection
                _collector.Start(intervalFrames);
                _isRecording = true;

                // Register update callback
                EditorApplication.update -= OnEditorUpdate;
                EditorApplication.update += OnEditorUpdate;

                return new SuccessResponse("Profiling session started.", new
                {
                    intervalFrames = intervalFrames,
                    deepProfiling = deepProfiling,
                    isRecording = true
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to start profiling: {ex.Message}");
            }
        }

        private static object StopProfiling()
        {
            try
            {
                if (_collector != null)
                {
                    _collector.Stop();
                }

                _isRecording = false;
                EditorApplication.update -= OnEditorUpdate;

                // Disable deep profiling if it was enabled
                if (Profiler.deepProfiling)
                {
                    Profiler.deepProfiling = false;
                }

                return new SuccessResponse("Profiling session stopped.", new
                {
                    isRecording = false,
                    snapshotCount = _collector?.SnapshotCount ?? 0
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to stop profiling: {ex.Message}");
            }
        }

        private static void OnEditorUpdate()
        {
            _collector?.Update();
        }

        #endregion

        #region Status and Snapshots

        private static object GetStatus()
        {
            var status = new
            {
                isRecording = _isRecording,
                snapshotCount = _collector?.SnapshotCount ?? 0,
                profilerEnabled = Profiler.enabled,
                deepProfiling = Profiler.deepProfiling,
                supportedCategories = GetSupportedCategories(),
                enabledCategories = _enabledCategories.Select(c => c.ToString()).ToList(),
                unityVersion = Application.unityVersion,
                isEditor = Application.isEditor,
                isPlaying = EditorApplication.isPlaying,
                currentFrame = Time.frameCount
            };

            return new SuccessResponse("Profiler status retrieved.", status);
        }

        private static object GetSnapshot()
        {
            try
            {
                var snapshot = ProfilerSnapshot.Capture();
                var stats = _collector?.GetAggregatedStats() ?? new AggregatedStats();

                return new SuccessResponse("Profiler snapshot captured.", new
                {
                    snapshot = snapshot,
                    aggregatedStats = stats,
                    isRecording = _isRecording,
                    totalSnapshots = _collector?.SnapshotCount ?? 0
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to capture snapshot: {ex.Message}");
            }
        }

        #endregion

        #region Detailed Data

        private static object GetMemoryDetails()
        {
            try
            {
                var memory = ProfilerSnapshot.Capture().memory;
                
                // Add additional memory breakdown
                var details = new
                {
                    memory = memory,
                    breakdown = new Dictionary<string, object>
                    {
                        ["totalUsedMB"] = memory.totalUsedMemoryBytes / (1024.0 * 1024.0),
                        ["gcHeapMB"] = memory.gcHeapSizeBytes / (1024.0 * 1024.0),
                        ["textureMB"] = memory.textureMemoryBytes / (1024.0 * 1024.0),
                        ["meshMB"] = memory.meshMemoryBytes / (1024.0 * 1024.0),
                        ["audioMB"] = memory.audioMemoryBytes / (1024.0 * 1024.0),
                        ["renderTextureMB"] = memory.renderTextureMemoryBytes / (1024.0 * 1024.0),
                        ["gcCollectionCountGen0"] = memory.gcCollectionCount,
                    },
                    recommendations = GetMemoryRecommendations(memory)
                };

                return new SuccessResponse("Memory details retrieved.", details);
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get memory details: {ex.Message}");
            }
        }

        private static object GetCpuDetails()
        {
            try
            {
                var cpu = ProfilerSnapshot.Capture().cpu;
                
                var details = new
                {
                    cpu = cpu,
                    breakdown = new Dictionary<string, object>
                    {
                        ["totalTimeMs"] = cpu.totalTimeMs,
                        ["mainThreadMs"] = cpu.mainThreadTimeMs,
                        ["renderThreadMs"] = cpu.renderThreadTimeMs,
                        ["scriptsMs"] = cpu.scriptsTimeMs,
                        ["physicsMs"] = cpu.physicsTimeMs,
                        ["animationMs"] = cpu.animationTimeMs,
                        ["uiMs"] = cpu.uiTimeMs,
                        ["renderingMs"] = cpu.renderingTimeMs,
                        ["gcMs"] = cpu.gcTimeMs,
                        ["categories"] = cpu.categoryBreakdown
                    },
                    recommendations = GetCpuRecommendations(cpu)
                };

                return new SuccessResponse("CPU details retrieved.", details);
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get CPU details: {ex.Message}");
            }
        }

        private static object GetRenderingDetails()
        {
            try
            {
                var rendering = ProfilerSnapshot.Capture().rendering;
                
                var details = new
                {
                    rendering = rendering,
                    breakdown = new Dictionary<string, object>
                    {
                        ["drawCalls"] = rendering.drawCalls,
                        ["setPassCalls"] = rendering.setPassCalls,
                        ["triangles"] = rendering.triangles,
                        ["vertices"] = rendering.vertices,
                        ["batches"] = rendering.batches,
                        ["staticBatchedDrawCalls"] = rendering.staticBatchedDrawCalls,
                        ["dynamicBatchedDrawCalls"] = rendering.dynamicBatchedDrawCalls,
                        ["instancedDrawCalls"] = rendering.instancedDrawCalls
                    },
                    recommendations = GetRenderingRecommendations(rendering)
                };

                return new SuccessResponse("Rendering details retrieved.", details);
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get rendering details: {ex.Message}");
            }
        }

        private static object GetAudioDetails()
        {
            try
            {
                var audio = ProfilerSnapshot.Capture().audio;
                
                var details = new
                {
                    audio = audio,
                    breakdown = new Dictionary<string, object>
                    {
                        ["totalSources"] = audio.totalAudioSources,
                        ["playingSources"] = audio.playingAudioSources,
                        ["dspLoad"] = audio.audioLevel,
                        ["dspLoadPercent"] = audio.audioLevel * 100.0
                    },
                    recommendations = GetAudioRecommendations(audio)
                };

                return new SuccessResponse("Audio details retrieved.", details);
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to get audio details: {ex.Message}");
            }
        }

        #endregion

        #region Data Management

        private static object ClearData()
        {
            try
            {
                _collector?.Clear();
                return new SuccessResponse("Profiler data cleared.", new
                {
                    snapshotCount = 0
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to clear data: {ex.Message}");
            }
        }

        private static object SaveCapture(ToolParams p)
        {
            try
            {
                string filePath = p.Get("filePath");
                
                if (string.IsNullOrEmpty(filePath))
                {
                    filePath = Path.Combine(CaptureDirectory, ProfilerDataCollector.GenerateCaptureFileName());
                }
                else if (!Path.IsPathRooted(filePath))
                {
                    // Relative path - resolve against capture directory
                    filePath = Path.Combine(CaptureDirectory, filePath);
                }

                // Ensure directory exists
                string directory = Path.GetDirectoryName(filePath);
                if (!Directory.Exists(directory))
                {
                    Directory.CreateDirectory(directory);
                }

                // Save the capture
                if (_collector?.SaveToFile(filePath) ?? false)
                {
                    return new SuccessResponse("Profiler capture saved.", new
                    {
                        filePath = filePath,
                        fileSize = new FileInfo(filePath).Length,
                        snapshotCount = _collector?.SnapshotCount ?? 0
                    });
                }
                else
                {
                    return new ErrorResponse("Failed to save profiler capture.");
                }
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to save capture: {ex.Message}");
            }
        }

        private static object LoadCapture(ToolParams p)
        {
            try
            {
                string filePath = p.GetRequired("filePath", "filePath is required for load_capture.").Value;
                
                if (!Path.IsPathRooted(filePath))
                {
                    // Relative path - resolve against capture directory
                    filePath = Path.Combine(CaptureDirectory, filePath);
                }

                if (_collector == null)
                {
                    _collector = new ProfilerDataCollector();
                }

                if (_collector.LoadFromFile(filePath))
                {
                    return new SuccessResponse("Profiler capture loaded.", new
                    {
                        filePath = filePath,
                        snapshotCount = _collector.SnapshotCount,
                        aggregatedStats = _collector.GetAggregatedStats()
                    });
                }
                else
                {
                    return new ErrorResponse($"Failed to load profiler capture from: {filePath}");
                }
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to load capture: {ex.Message}");
            }
        }

        private static object SetCategories(ToolParams p)
        {
            try
            {
                var categories = p.GetStringArray("categories");
                var enable = p.GetBool("enable", true);

                if (categories == null || categories.Length == 0)
                {
                    return new ErrorResponse("categories array is required for set_categories.");
                }

                var result = new List<string>();
                foreach (var catName in categories)
                {
                    if (Enum.TryParse<ProfilerCategory>(catName, true, out var category))
                    {
                        if (enable)
                        {
                            if (!_enabledCategories.Contains(category))
                                _enabledCategories.Add(category);
                        }
                        else
                        {
                            _enabledCategories.Remove(category);
                        }
                        result.Add($"{catName}: {(enable ? "enabled" : "disabled")}");
                    }
                    else
                    {
                        result.Add($"{catName}: unknown category");
                    }
                }

                return new SuccessResponse("Categories updated.", new
                {
                    changes = result,
                    enabledCategories = _enabledCategories.Select(c => c.ToString()).ToList()
                });
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Failed to set categories: {ex.Message}");
            }
        }

        #endregion

        #region Helper Methods

        private static List<string> GetSupportedCategories()
        {
            return Enum.GetNames(typeof(ProfilerCategory)).ToList();
        }

        private static List<string> GetMemoryRecommendations(MemoryData memory)
        {
            var recommendations = new List<string>();
            
            double memoryMB = memory.totalUsedMemoryBytes / (1024.0 * 1024.0);
            
            if (memoryMB > 1000)
            {
                recommendations.Add("High memory usage detected. Consider using the Memory Profiler package for detailed analysis.");
            }
            
            if (memory.textureMemoryBytes > 500 * 1024 * 1024)
            {
                recommendations.Add("Texture memory usage is high. Consider texture compression and mipmapping.");
            }
            
            if (memory.gcCollectionCount > 10)
            {
                recommendations.Add("Frequent garbage collections detected. Consider object pooling to reduce allocations.");
            }
            
            return recommendations;
        }

        private static List<string> GetCpuRecommendations(CpuData cpu)
        {
            var recommendations = new List<string>();
            
            if (cpu.totalTimeMs > 33.3) // Less than 30 FPS
            {
                recommendations.Add("Frame time exceeds 33ms (below 30 FPS). Consider profiling specific systems.");
            }
            else if (cpu.totalTimeMs > 16.7) // Less than 60 FPS
            {
                recommendations.Add("Frame time exceeds 16ms (below 60 FPS). Room for optimization.");
            }
            
            if (cpu.renderingTimeMs > cpu.totalTimeMs * 0.5)
            {
                recommendations.Add("Rendering time is >50% of frame. Consider draw call batching and LOD.");
            }
            
            if (cpu.scriptsTimeMs > cpu.totalTimeMs * 0.3)
            {
                recommendations.Add("Script time is >30% of frame. Check for expensive Update loops.");
            }
            
            return recommendations;
        }

        private static List<string> GetRenderingRecommendations(RenderingData rendering)
        {
            var recommendations = new List<string>();
            
            if (rendering.drawCalls > 200)
            {
                recommendations.Add("High draw call count. Consider static/dynamic batching, GPU instancing, or SRP Batcher.");
            }
            
            if (rendering.triangles > 100000)
            {
                recommendations.Add("High triangle count. Consider implementing LOD (Level of Detail) system.");
            }
            
            if (rendering.setPassCalls > 50)
            {
                recommendations.Add("High SetPass call count. Try to reduce shader/material variants.");
            }
            
            return recommendations;
        }

        private static List<string> GetAudioRecommendations(AudioData audio)
        {
            var recommendations = new List<string>();
            
            if (audio.audioLevel > 0.8)
            {
                recommendations.Add("DSP load is high (>80%). Consider reducing voice count or using simpler audio clips.");
            }
            
            if (audio.playingAudioSources > 32)
            {
                recommendations.Add("Many audio sources playing simultaneously. Consider audio prioritization.");
            }
            
            return recommendations;
        }

        #endregion
    }
}
