using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Events;

namespace MCPForUnity.Runtime.Video
{
    /// <summary>
    /// Video capture controller for recording gameplay footage.
    /// Works in both Editor and Play mode using frame capture.
    /// Supports MP4 (via external encoder), GIF, and PNG sequence output.
    /// </summary>
    public class VideoCaptureController : MonoBehaviour
    {
        #region Singleton
        private static VideoCaptureController s_instance;
        public static VideoCaptureController Instance
        {
            get
            {
                if (s_instance == null)
                {
                    var go = new GameObject("VideoCaptureController");
                    s_instance = go.AddComponent<VideoCaptureController>();
                    DontDestroyOnLoad(go);
                }
                return s_instance;
            }
        }
        #endregion

        #region Events
        public UnityEvent OnRecordingStarted;
        public UnityEvent OnRecordingStopped;
        public UnityEvent<string> OnRecordingSaved;
        public UnityEvent<string> OnRecordingError;
        #endregion

        #region Recording State
        private bool m_isRecording = false;
        private float m_recordingStartTime;
        private int m_capturedFrameCount;
        private string m_outputPath;
        private string m_outputFormat;
        private List<Texture2D> m_capturedFrames;
        private Coroutine m_recordingCoroutine;
        private Coroutine m_durationLimitCoroutine;
        #endregion

        #region Settings
        [System.Serializable]
        public class CaptureSettings
        {
            public int targetFps = 30;
            public string quality = "high";
            public Vector2Int resolution = new Vector2Int(1920, 1080);
            public string format = "mp4";
            public bool includeAudio = false;
            public int gifLoopCount = 0;
            public int gifFrameSkip = 1;
            public bool useScreenResolution = true;
        }

        private CaptureSettings m_settings = new CaptureSettings();
        #endregion

        #region Properties
        public bool IsRecording => m_isRecording;
        public float RecordingDuration => m_isRecording ? Time.time - m_recordingStartTime : 0f;
        public int FrameCount => m_capturedFrameCount;
        public CaptureSettings Settings => m_settings;
        #endregion

        private void Awake()
        {
            if (s_instance != null && s_instance != this)
            {
                Destroy(gameObject);
                return;
            }
            s_instance = this;
            DontDestroyOnLoad(gameObject);
            m_capturedFrames = new List<Texture2D>();
        }

        private void OnDestroy()
        {
            if (m_isRecording)
            {
                StopRecording();
            }
            ClearCapturedFrames();
        }

        #region Public API
        /// <summary>
        /// Configure capture settings before recording.
        /// </summary>
        public void SetSettings(CaptureSettings settings)
        {
            m_settings = settings ?? new CaptureSettings();
        }

        /// <summary>
        /// Configure capture settings from dictionary parameters.
        /// </summary>
        public void SetSettingsFromDict(Dictionary<string, object> settings)
        {
            if (settings == null) return;

            if (settings.TryGetValue("fps", out var fps))
                m_settings.targetFps = Convert.ToInt32(fps);

            if (settings.TryGetValue("quality", out var quality))
                m_settings.quality = quality.ToString().ToLower();

            if (settings.TryGetValue("resolution", out var resObj) && resObj is Dictionary<string, object> res)
            {
                m_settings.resolution = new Vector2Int(
                    Convert.ToInt32(res["width"]),
                    Convert.ToInt32(res["height"])
                );
                m_settings.useScreenResolution = false;
            }

            if (settings.TryGetValue("format", out var format))
                m_settings.format = format.ToString().ToLower();

            if (settings.TryGetValue("includeAudio", out var audio))
                m_settings.includeAudio = Convert.ToBoolean(audio);

            if (settings.TryGetValue("loopCount", out var loop))
                m_settings.gifLoopCount = Convert.ToInt32(loop);

            if (settings.TryGetValue("frameSkip", out var skip))
                m_settings.gifFrameSkip = Convert.ToInt32(skip);
        }

        /// <summary>
        /// Start recording video.
        /// </summary>
        /// <param name="outputPath">Output file path relative to Assets folder</param>
        /// <returns>True if recording started successfully</returns>
        public bool StartRecording(string outputPath = null)
        {
            if (m_isRecording)
            {
                Debug.LogWarning("[VideoCapture] Already recording. Stop current recording first.");
                return false;
            }

            try
            {
                // Resolve output path
                m_outputPath = ResolveOutputPath(outputPath);
                m_outputFormat = m_settings.format;

                // Clear previous frames
                ClearCapturedFrames();
                m_capturedFrames = new List<Texture2D>();

                // Start recording
                m_isRecording = true;
                m_recordingStartTime = Time.time;
                m_capturedFrameCount = 0;

                m_recordingCoroutine = StartCoroutine(CaptureFramesCoroutine());

                OnRecordingStarted?.Invoke();
                Debug.Log($"[VideoCapture] Started recording to: {m_outputPath}");
                return true;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[VideoCapture] Failed to start recording: {ex.Message}");
                OnRecordingError?.Invoke(ex.Message);
                return false;
            }
        }

        /// <summary>
        /// Start recording with automatic stop after duration.
        /// </summary>
        public bool StartRecording(string outputPath, float durationSeconds)
        {
            if (!StartRecording(outputPath))
                return false;

            if (durationSeconds > 0)
            {
                m_durationLimitCoroutine = StartCoroutine(AutoStopCoroutine(durationSeconds));
            }

            return true;
        }

        /// <summary>
        /// Stop recording and save the file.
        /// </summary>
        /// <returns>Path to the saved file, or null on failure</returns>
        public string StopRecording()
        {
            if (!m_isRecording)
            {
                Debug.LogWarning("[VideoCapture] Not currently recording.");
                return null;
            }

            // Stop coroutines
            if (m_recordingCoroutine != null)
                StopCoroutine(m_recordingCoroutine);
            if (m_durationLimitCoroutine != null)
                StopCoroutine(m_durationLimitCoroutine);

            m_isRecording = false;
            m_recordingCoroutine = null;
            m_durationLimitCoroutine = null;

            // Save captured frames
            string savedPath = null;
            try
            {
                savedPath = SaveCapturedFrames();
                OnRecordingSaved?.Invoke(savedPath);
            }
            catch (Exception ex)
            {
                Debug.LogError($"[VideoCapture] Failed to save recording: {ex.Message}");
                OnRecordingError?.Invoke(ex.Message);
            }

            OnRecordingStopped?.Invoke();
            return savedPath;
        }

        /// <summary>
        /// Get current recording status.
        /// </summary>
        public Dictionary<string, object> GetStatus()
        {
            return new Dictionary<string, object>
            {
                ["isRecording"] = m_isRecording,
                ["duration"] = RecordingDuration,
                ["frameCount"] = m_capturedFrameCount,
                ["outputPath"] = m_outputPath,
                ["format"] = m_settings.format,
                ["fps"] = m_settings.targetFps,
                ["estimatedFileSize"] = EstimateFileSize()
            };
        }

        /// <summary>
        /// Capture a short GIF animation.
        /// This automatically starts, records, and stops.
        /// </summary>
        /// <param name="outputPath">Output GIF path</param>
        /// <param name="duration">Duration in seconds</param>
        /// <returns>True if capture started</returns>
        public bool CaptureGif(string outputPath, float duration = 5.0f)
        {
            // Temporarily switch to GIF format
            string previousFormat = m_settings.format;
            m_settings.format = "gif";

            bool started = StartRecording(outputPath, duration);

            // Restore format if start failed
            if (!started)
            {
                m_settings.format = previousFormat;
            }

            return started;
        }
        #endregion

        #region Private Methods
        private IEnumerator CaptureFramesCoroutine()
        {
            float captureInterval = 1f / m_settings.targetFps;
            float lastCaptureTime = 0f;
            int frameSkipCounter = 0;

            while (m_isRecording)
            {
                // Check if it's time to capture a frame
                if (Time.time - lastCaptureTime >= captureInterval)
                {
                    // Handle frame skipping for GIF
                    frameSkipCounter++;
                    if (m_settings.format == "gif" && frameSkipCounter % m_settings.gifFrameSkip != 0)
                    {
                        lastCaptureTime = Time.time;
                        yield return null;
                        continue;
                    }

                    CaptureFrame();
                    lastCaptureTime = Time.time;
                }

                yield return null;
            }
        }

        private IEnumerator AutoStopCoroutine(float duration)
        {
            yield return new WaitForSeconds(duration);
            if (m_isRecording)
            {
                Debug.Log($"[VideoCapture] Auto-stopping after {duration} seconds");
                StopRecording();
            }
        }

        private void CaptureFrame()
        {
            try
            {
                // Determine capture resolution
                int width = m_settings.useScreenResolution ? Screen.width : m_settings.resolution.x;
                int height = m_settings.useScreenResolution ? Screen.height : m_settings.resolution.y;

                // Apply quality settings
                (width, height) = ApplyQualitySettings(width, height);

                // Capture the screen
                Texture2D frame = CaptureScreen(width, height);
                if (frame != null)
                {
                    m_capturedFrames.Add(frame);
                    m_capturedFrameCount++;
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"[VideoCapture] Frame capture failed: {ex.Message}");
            }
        }

        private Texture2D CaptureScreen(int width, int height)
        {
            // Use RenderTexture for capture
            RenderTexture rt = RenderTexture.GetTemporary(width, height, 24, RenderTextureFormat.ARGB32);
            Texture2D screenshot = null;

            try
            {
                // Render from main camera
                Camera camera = Camera.main;
                if (camera == null)
                {
                    camera = Camera.current;
                }

                if (camera == null)
                {
                    // Fallback: capture entire screen
                    screenshot = new Texture2D(width, height, TextureFormat.RGB24, false);
                    screenshot.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                    screenshot.Apply();
                    return screenshot;
                }

                // Render camera to texture
                RenderTexture prevRT = camera.targetTexture;
                camera.targetTexture = rt;
                camera.Render();
                camera.targetTexture = prevRT;

                // Read pixels from RenderTexture
                RenderTexture.active = rt;
                screenshot = new Texture2D(width, height, TextureFormat.RGB24, false);
                screenshot.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                screenshot.Apply();
                RenderTexture.active = null;

                return screenshot;
            }
            catch
            {
                if (screenshot != null)
                    Destroy(screenshot);
                return null;
            }
            finally
            {
                RenderTexture.ReleaseTemporary(rt);
            }
        }

        private string SaveCapturedFrames()
        {
            if (m_capturedFrames.Count == 0)
            {
                Debug.LogWarning("[VideoCapture] No frames captured.");
                return null;
            }

            switch (m_outputFormat)
            {
                case "gif":
                    return SaveAsGif();
                case "frames":
                    return SaveAsFrameSequence();
                case "mp4":
                default:
                    return SaveAsMp4();
            }
        }

        private string SaveAsGif()
        {
            // For now, save frames and provide info about GIF creation
            // Full GIF encoding would require a GIF encoder library
            string folderPath = Path.GetDirectoryName(m_outputPath);
            string fileName = Path.GetFileNameWithoutExtension(m_outputPath);
            string framesFolder = Path.Combine(folderPath, $"{fileName}_frames");

            Directory.CreateDirectory(framesFolder);

            // Save frames as PNG
            for (int i = 0; i < m_capturedFrames.Count; i++)
            {
                byte[] pngData = m_capturedFrames[i].EncodeToPNG();
                string framePath = Path.Combine(framesFolder, $"frame_{i:D4}.png");
                File.WriteAllBytes(framePath, pngData);
            }

            Debug.Log($"[VideoCapture] Saved {m_capturedFrames.Count} frames for GIF creation to: {framesFolder}");
            Debug.Log($"[VideoCapture] Use external tool to create GIF with loop count: {m_settings.gifLoopCount}");

            return framesFolder;
        }

        private string SaveAsFrameSequence()
        {
            string folderPath = Path.GetDirectoryName(m_outputPath);
            string fileName = Path.GetFileNameWithoutExtension(m_outputPath);
            string framesFolder = Path.Combine(folderPath, $"{fileName}_sequence");

            Directory.CreateDirectory(framesFolder);

            for (int i = 0; i < m_capturedFrames.Count; i++)
            {
                byte[] pngData = m_capturedFrames[i].EncodeToPNG();
                string framePath = Path.Combine(framesFolder, $"frame_{i:D5}.png");
                File.WriteAllBytes(framePath, pngData);
            }

            Debug.Log($"[VideoCapture] Saved {m_capturedFrames.Count} frames to: {framesFolder}");
            return framesFolder;
        }

        private string SaveAsMp4()
        {
            // MP4 encoding requires external tools or Unity Recorder package
            // For now, save as frame sequence with metadata
            string folderPath = SaveAsFrameSequence();

            // Save metadata JSON
            string fileName = Path.GetFileNameWithoutExtension(m_outputPath);
            string metadataPath = Path.Combine(folderPath, "metadata.json");
            string metadata = $"{{\"fps\":{m_settings.targetFps},\"frameCount\":{m_capturedFrameCount},\"targetFormat\":\"mp4\"}}";
            File.WriteAllText(metadataPath, metadata);

            Debug.Log($"[VideoCapture] MP4 creation requires Unity Recorder package or FFmpeg. Frames saved to: {folderPath}");

            return folderPath;
        }

        private void ClearCapturedFrames()
        {
            if (m_capturedFrames != null)
            {
                foreach (var frame in m_capturedFrames)
                {
                    if (frame != null)
                        Destroy(frame);
                }
                m_capturedFrames.Clear();
            }
        }

        private string ResolveOutputPath(string outputPath)
        {
            if (string.IsNullOrEmpty(outputPath))
            {
                string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                outputPath = $"Recordings/recording_{timestamp}.{m_settings.format}";
            }

            // Ensure path is within Assets folder
            if (!outputPath.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase))
            {
                outputPath = $"Assets/{outputPath}";
            }

            // Convert to absolute path
            string fullPath = Path.Combine(Application.dataPath, "..", outputPath);
            fullPath = Path.GetFullPath(fullPath);

            // Ensure directory exists
            string directory = Path.GetDirectoryName(fullPath);
            if (!Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }

            return fullPath;
        }

        private (int width, int height) ApplyQualitySettings(int width, int height)
        {
            float scale = m_settings.quality switch
            {
                "low" => 0.5f,
                "medium" => 0.75f,
                "high" => 1.0f,
                "ultra" => 1.5f,
                _ => 1.0f
            };

            return (
                Mathf.RoundToInt(width * scale),
                Mathf.RoundToInt(height * scale)
            );
        }

        private long EstimateFileSize()
        {
            if (!m_isRecording || m_capturedFrameCount == 0)
                return 0;

            // Rough estimate: 2MB per frame at 1080p, scaled by format
            long bytesPerFrame = m_settings.quality switch
            {
                "low" => 500 * 1024,
                "medium" => 1 * 1024 * 1024,
                "high" => 2 * 1024 * 1024,
                "ultra" => 4 * 1024 * 1024,
                _ => 2 * 1024 * 1024
            };

            float formatMultiplier = m_settings.format switch
            {
                "gif" => 0.3f,
                "mp4" => 0.1f,
                "frames" => 1.0f,
                _ => 1.0f
            };

            return (long)(m_capturedFrameCount * bytesPerFrame * formatMultiplier);
        }
        #endregion
    }
}
