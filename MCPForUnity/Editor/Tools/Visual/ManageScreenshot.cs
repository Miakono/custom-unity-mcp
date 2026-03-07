using System;
using System.IO;
using System.Reflection;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEditor;
using UnityEditorInternal;
using MCPForUnity.Editor.Helpers;

namespace MCPForUnity.Editor.Tools.Visual
{
    /// <summary>
    /// Screenshot capture tools for AI vision/multimodal support.
    /// Closes the major feature gap vs competitors.
    /// </summary>
    [McpForUnityTool("manage_screenshot", AutoRegister = false, Group = "visual_qa")]
    public static class ManageScreenshot
    {
        private static byte[] s_lastCapturePng;
        private static int s_lastCaptureWidth;
        private static int s_lastCaptureHeight;
        private static string s_lastCaptureSource;

        public static object HandleCommand(JObject @params)
        {
            try
            {
                var parameters = @params ?? new JObject();
                string action = parameters["action"]?.Value<string>();
                if (string.IsNullOrWhiteSpace(action))
                {
                    return new ErrorResponse("Action parameter is required.");
                }

                return action switch
                {
                    "capture_game_view" => CaptureGameView(parameters),
                    "capture_scene_view" => CaptureSceneView(parameters),
                    "capture_object_preview" => CaptureObjectPreview(parameters),
                    "capture_editor_window" => CaptureEditorWindow(parameters),
                    "get_last_screenshot" => GetLastScreenshot(parameters),
                    _ => new ErrorResponse($"Unknown action: {action}")
                };
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"Screenshot failed: {ex.Message}");
            }
        }

        /// <summary>
        /// Capture the Game view as base64 PNG
        /// </summary>
        private static JObject CaptureGameView(JObject parameters)
        {
            int width = parameters["width"]?.Value<int>() ?? 1920;
            int height = parameters["height"]?.Value<int>() ?? 1080;
            string format = parameters["format"]?.Value<string>() ?? "base64";

            byte[] imageData = CaptureGameViewInternal(width, height);
            
            if (imageData == null || imageData.Length == 0)
            {
                return ToErrorObject("Failed to capture Game view. Is the Game view open?");
            }

            return FormatAndRememberResponse(imageData, format, width, height, "capture_game_view");
        }

        /// <summary>
        /// Capture the Scene view from a specific camera angle
        /// </summary>
        private static JObject CaptureSceneView(JObject parameters)
        {
            int width = parameters["width"]?.Value<int>() ?? 1920;
            int height = parameters["height"]?.Value<int>() ?? 1080;
            string format = parameters["format"]?.Value<string>() ?? "base64";
            
            JToken posToken = parameters["camera_position"];
            JToken rotToken = parameters["camera_rotation"];

            byte[] imageData;
            
            if (posToken != null && rotToken != null)
            {
                Vector3? position = VectorParsing.ParseVector3(posToken);
                Vector3? rotation = VectorParsing.ParseVector3(rotToken);
                if (!position.HasValue || !rotation.HasValue)
                {
                    return ToErrorObject("camera_position and camera_rotation must be valid Vector3 values.");
                }

                imageData = CaptureSceneViewFromAngle(position.Value, rotation.Value, width, height);
            }
            else
            {
                imageData = CaptureSceneViewInternal(width, height);
            }

            if (imageData == null || imageData.Length == 0)
            {
                return ToErrorObject("Failed to capture Scene view. Is the Scene view open?");
            }

            return FormatAndRememberResponse(imageData, format, width, height, "capture_scene_view");
        }

        /// <summary>
        /// Capture the full Unity editor window, including docked panels.
        /// </summary>
        private static JObject CaptureEditorWindow(JObject parameters)
        {
            int targetWidth = parameters["width"]?.Value<int>() ?? 0;
            int targetHeight = parameters["height"]?.Value<int>() ?? 0;
            string format = parameters["format"]?.Value<string>() ?? "base64";
            bool allowScreenFallback = parameters["allow_screen_fallback"]?.Value<bool>() ?? false;

            if (!EnsureEditorWindowReadyForCapture(out string prepError))
            {
                return ToErrorObject(prepError);
            }

            if (TryCaptureEditorWindowNative(out byte[] nativeBytes, out int nativeWidth, out int nativeHeight, out string nativeError))
            {
                int finalWidth = targetWidth > 0 ? targetWidth : nativeWidth;
                int finalHeight = targetHeight > 0 ? targetHeight : nativeHeight;

                byte[] outputBytes = nativeBytes;
                if (finalWidth != nativeWidth || finalHeight != nativeHeight)
                {
                    outputBytes = ResizePng(nativeBytes, finalWidth, finalHeight);
                }

                JObject nativeResult = FormatAndRememberResponse(outputBytes, format, finalWidth, finalHeight, "capture_editor_window");
                nativeResult["capture_backend"] = "native_window_enum_clientdc";
                return nativeResult;
            }

            if (!allowScreenFallback)
            {
                return ToErrorObject(
                    $"Native editor-window capture failed: {nativeError}. " +
                    "Set allow_screen_fallback=true to use screen-space capture as a fallback.");
            }

            if (!TryGetMainEditorWindowRect(out Rect editorRect))
            {
                return ToErrorObject("Failed to resolve Unity main editor window bounds.");
            }

            int captureWidth = Mathf.Max(1, Mathf.RoundToInt(editorRect.width));
            int captureHeight = Mathf.Max(1, Mathf.RoundToInt(editorRect.height));
            int x = Mathf.RoundToInt(editorRect.x);
            int y = Mathf.RoundToInt(editorRect.y);

            Color[] pixels;
            try
            {
                // ReadScreenPixel expects native screen-space coordinates for editor windows.
                pixels = InternalEditorUtility.ReadScreenPixel(new Vector2(x, y), captureWidth, captureHeight);
            }
            catch (Exception ex)
            {
                return ToErrorObject($"Failed to read editor pixels: {ex.Message}");
            }

            if (pixels == null || pixels.Length != captureWidth * captureHeight)
            {
                return ToErrorObject("Failed to capture editor window pixels.");
            }

            Texture2D screenshot = new Texture2D(captureWidth, captureHeight, TextureFormat.RGB24, false);
            screenshot.SetPixels(pixels);
            screenshot.Apply();

            int fallbackWidth = targetWidth > 0 ? targetWidth : captureWidth;
            int fallbackHeight = targetHeight > 0 ? targetHeight : captureHeight;

            if (fallbackWidth != captureWidth || fallbackHeight != captureHeight)
            {
                Texture2D resized = ResizeTexture(screenshot, fallbackWidth, fallbackHeight);
                UnityEngine.Object.DestroyImmediate(screenshot);
                screenshot = resized;
            }

            byte[] bytes = screenshot.EncodeToPNG();
            UnityEngine.Object.DestroyImmediate(screenshot);

            JObject fallbackResult = FormatAndRememberResponse(bytes, format, fallbackWidth, fallbackHeight, "capture_editor_window");
            fallbackResult["capture_backend"] = "screen_pixel_fallback";
            return fallbackResult;
        }

        /// <summary>
        /// Return the most recent screenshot captured by this tool.
        /// </summary>
        private static JObject GetLastScreenshot(JObject parameters)
        {
            string format = parameters["format"]?.Value<string>() ?? "base64";

            if (s_lastCapturePng == null || s_lastCapturePng.Length == 0)
            {
                return ToErrorObject("No screenshot has been captured yet in this editor session.");
            }

            JObject result = FormatResponse(s_lastCapturePng, format, s_lastCaptureWidth, s_lastCaptureHeight);
            if (!string.IsNullOrEmpty(s_lastCaptureSource))
            {
                result["source_action"] = s_lastCaptureSource;
            }
            return result;
        }

        /// <summary>
        /// Render a specific GameObject in isolation (useful for asset preview)
        /// </summary>
        private static JObject CaptureObjectPreview(JObject parameters)
        {
            string targetPath = parameters["target_object"]?.Value<string>();
            int width = parameters["width"]?.Value<int>() ?? 512;
            int height = parameters["height"]?.Value<int>() ?? 512;
            string format = parameters["format"]?.Value<string>() ?? "base64";
            Color? background = parameters["background_color"] != null 
                ? ParseColor(parameters["background_color"]) 
                : null;

            if (string.IsNullOrEmpty(targetPath))
            {
                return ToErrorObject("target_object parameter required");
            }

            GameObject target = ResolveGameObject(targetPath);
            if (target == null)
            {
                return ToErrorObject($"GameObject not found: {targetPath}");
            }

            byte[] imageData = CaptureObjectPreviewInternal(target, width, height, background);
            
            if (imageData == null || imageData.Length == 0)
            {
                return ToErrorObject("Failed to render object preview");
            }

            return FormatAndRememberResponse(imageData, format, width, height, "capture_object_preview", target.name);
        }

        #region Implementation

        private static JObject ToErrorObject(string message)
        {
            return JObject.FromObject(new ErrorResponse(message));
        }

        private static GameObject ResolveGameObject(string targetPath)
        {
            var byPath = GameObjectLookup.SearchGameObjects("by_path", targetPath, true, 1);
            if (byPath.Count > 0)
            {
                return GameObjectLookup.FindById(byPath[0]);
            }

            var byName = GameObjectLookup.SearchGameObjects("by_name", targetPath, true, 1);
            if (byName.Count > 0)
            {
                return GameObjectLookup.FindById(byName[0]);
            }

            return null;
        }

        private static byte[] CaptureGameViewInternal(int width, int height)
        {
            if (Application.isPlaying)
            {
                return CaptureFromScreen(width, height);
            }
            return CaptureFromGameViewRenderTexture(width, height);
        }

        private static byte[] CaptureFromScreen(int width, int height)
        {
            Texture2D screenshot = ScreenCapture.CaptureScreenshotAsTexture();
            
            if (screenshot.width != width || screenshot.height != height)
            {
                Texture2D resized = ResizeTexture(screenshot, width, height);
                UnityEngine.Object.DestroyImmediate(screenshot);
                screenshot = resized;
            }

            byte[] bytes = screenshot.EncodeToPNG();
            UnityEngine.Object.DestroyImmediate(screenshot);
            return bytes;
        }

        private static byte[] CaptureFromGameViewRenderTexture(int width, int height)
        {
            Camera camera = Camera.main ?? UnityEngine.Object.FindFirstObjectByType<Camera>();
            if (camera == null) return null;
            return CaptureFromCamera(camera, width, height);
        }

        private static byte[] CaptureSceneViewInternal(int width, int height)
        {
            var sceneView = SceneView.lastActiveSceneView;
            if (sceneView == null) return null;
            return CaptureFromCamera(sceneView.camera, width, height);
        }

        private static byte[] CaptureSceneViewFromAngle(Vector3 position, Vector3 rotation, int width, int height)
        {
            GameObject tempCameraObj = new GameObject("TempScreenshotCamera");
            Camera tempCamera = tempCameraObj.AddComponent<Camera>();
            
            try
            {
                tempCamera.transform.position = position;
                tempCamera.transform.rotation = Quaternion.Euler(rotation);
                
                var sceneView = SceneView.lastActiveSceneView;
                if (sceneView != null)
                {
                    tempCamera.fieldOfView = sceneView.camera.fieldOfView;
                }

                return CaptureFromCamera(tempCamera, width, height);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(tempCameraObj);
            }
        }

        private static byte[] CaptureObjectPreviewInternal(GameObject target, int width, int height, Color? background)
        {
            GameObject previewObj = UnityEngine.Object.Instantiate(target);
            previewObj.hideFlags = HideFlags.HideAndDontSave;
            previewObj.transform.position = Vector3.zero;
            
            Bounds bounds = CalculateBounds(previewObj);
            float maxExtent = Mathf.Max(bounds.extents.x, bounds.extents.y, bounds.extents.z);
            float distance = maxExtent * 3f + 0.5f;

            GameObject camObj = new GameObject("PreviewCamera");
            Camera camera = camObj.AddComponent<Camera>();
            camera.backgroundColor = background ?? new Color(0.2f, 0.2f, 0.2f, 1f);
            camera.clearFlags = background.HasValue ? CameraClearFlags.SolidColor : CameraClearFlags.Depth;
            camera.transform.position = bounds.center + new Vector3(0, 0, -distance);
            camera.transform.LookAt(bounds.center);
            
            byte[] result;
            try
            {
                result = CaptureFromCamera(camera, width, height);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(camObj);
                UnityEngine.Object.DestroyImmediate(previewObj);
            }

            return result;
        }

        private static byte[] CaptureFromCamera(Camera camera, int width, int height)
        {
            RenderTexture rt = new RenderTexture(width, height, 24);
            camera.targetTexture = rt;
            camera.Render();

            RenderTexture.active = rt;
            Texture2D screenshot = new Texture2D(width, height, TextureFormat.RGB24, false);
            screenshot.ReadPixels(new Rect(0, 0, width, height), 0, 0);
            screenshot.Apply();

            camera.targetTexture = null;
            RenderTexture.active = null;
            UnityEngine.Object.DestroyImmediate(rt);

            byte[] bytes = screenshot.EncodeToPNG();
            UnityEngine.Object.DestroyImmediate(screenshot);

            return bytes;
        }

        private static Texture2D ResizeTexture(Texture2D source, int width, int height)
        {
            RenderTexture rt = RenderTexture.GetTemporary(width, height);
            RenderTexture.active = rt;
            Graphics.Blit(source, rt);
            
            Texture2D result = new Texture2D(width, height, TextureFormat.RGB24, false);
            result.ReadPixels(new Rect(0, 0, width, height), 0, 0);
            result.Apply();
            
            RenderTexture.ReleaseTemporary(rt);
            RenderTexture.active = null;
            
            return result;
        }

        private static Texture2D FlipTextureVertical(Texture2D source)
        {
            int width = source.width;
            int height = source.height;
            Texture2D result = new Texture2D(width, height, TextureFormat.RGB24, false);

            Color[] sourcePixels = source.GetPixels();
            Color[] flipped = new Color[sourcePixels.Length];

            for (int y = 0; y < height; y++)
            {
                int srcRow = y * width;
                int dstRow = (height - 1 - y) * width;
                Array.Copy(sourcePixels, srcRow, flipped, dstRow, width);
            }

            result.SetPixels(flipped);
            result.Apply();
            return result;
        }

        private static bool TryGetMainEditorWindowRect(out Rect rect)
        {
            rect = Rect.zero;

            Type containerWinType = typeof(EditorWindow).Assembly.GetType("UnityEditor.ContainerWindow");
            if (containerWinType == null)
            {
                return false;
            }

            FieldInfo showModeField = containerWinType.GetField("m_ShowMode", BindingFlags.NonPublic | BindingFlags.Instance);
            PropertyInfo positionProperty = containerWinType.GetProperty("position", BindingFlags.Public | BindingFlags.Instance);
            if (showModeField == null || positionProperty == null)
            {
                return false;
            }

            UnityEngine.Object[] windows = UnityEngine.Resources.FindObjectsOfTypeAll(containerWinType);
            foreach (UnityEngine.Object window in windows)
            {
                if (window == null)
                {
                    continue;
                }

                object showModeObj = showModeField.GetValue(window);
                if (showModeObj is int showMode && showMode == 4)
                {
                    object positionObj = positionProperty.GetValue(window, null);
                    if (positionObj is Rect winRect)
                    {
                        rect = winRect;
                        return rect.width > 0f && rect.height > 0f;
                    }
                }
            }

            if (EditorWindow.focusedWindow != null)
            {
                rect = EditorWindow.focusedWindow.position;
                return rect.width > 0f && rect.height > 0f;
            }

            return false;
        }

        private static bool EnsureEditorWindowReadyForCapture(out string error)
        {
            error = null;

#if UNITY_EDITOR_WIN
            try
            {
                IntPtr mainWindow = Process.GetCurrentProcess().MainWindowHandle;
                if (mainWindow != IntPtr.Zero)
                {
                    bool wasMinimized = IsIconic(mainWindow);
                    if (wasMinimized)
                    {
                        ShowWindow(mainWindow, SW_RESTORE);
                    }

                    if (wasMinimized)
                    {
                        // Give Windows one short beat to repaint after restore.
                        Thread.Sleep(150);
                    }
                }
            }
            catch (Exception ex)
            {
                error = $"Failed to restore Unity editor window for capture: {ex.Message}";
                return false;
            }
#endif

            InternalEditorUtility.RepaintAllViews();
            return true;
        }

        private static byte[] ResizePng(byte[] pngBytes, int width, int height)
        {
            Texture2D source = new Texture2D(2, 2, TextureFormat.RGB24, false);
            if (!source.LoadImage(pngBytes))
            {
                UnityEngine.Object.DestroyImmediate(source);
                throw new InvalidOperationException("Failed to decode PNG for resize.");
            }

            Texture2D resized = ResizeTexture(source, width, height);
            byte[] result = resized.EncodeToPNG();
            UnityEngine.Object.DestroyImmediate(source);
            UnityEngine.Object.DestroyImmediate(resized);
            return result;
        }

        private static bool TryCaptureEditorWindowNative(out byte[] pngBytes, out int width, out int height, out string error)
        {
            pngBytes = null;
            width = 0;
            height = 0;
            error = null;

#if UNITY_EDITOR_WIN
            try
            {
                if (!TryGetBestEditorWindowHandle(out IntPtr hwnd))
                {
                    error = "Unity editor window handle is unavailable.";
                    return false;
                }

                if (!GetClientRect(hwnd, out RECT clientRect))
                {
                    error = "GetClientRect failed.";
                    return false;
                }

                width = Math.Max(1, clientRect.Right - clientRect.Left);
                height = Math.Max(1, clientRect.Bottom - clientRect.Top);

                IntPtr clientDc = GetDC(hwnd);
                if (clientDc == IntPtr.Zero)
                {
                    error = "GetDC failed.";
                    return false;
                }

                IntPtr memoryDc = IntPtr.Zero;
                IntPtr hBitmap = IntPtr.Zero;
                IntPtr oldObject = IntPtr.Zero;

                try
                {
                    memoryDc = CreateCompatibleDC(clientDc);
                    if (memoryDc == IntPtr.Zero)
                    {
                        error = "CreateCompatibleDC failed.";
                        return false;
                    }

                    hBitmap = CreateCompatibleBitmap(clientDc, width, height);
                    if (hBitmap == IntPtr.Zero)
                    {
                        error = "CreateCompatibleBitmap failed.";
                        return false;
                    }

                    oldObject = SelectObject(memoryDc, hBitmap);
                    if (oldObject == IntPtr.Zero)
                    {
                        error = "SelectObject failed.";
                        return false;
                    }

                    bool printed = PrintWindow(hwnd, memoryDc, PW_RENDERFULLCONTENT);
                    bool usedPrintWindow = printed;
                    if (!printed)
                    {
                        bool copied = BitBlt(
                            memoryDc,
                            0,
                            0,
                            width,
                            height,
                            clientDc,
                            0,
                            0,
                            SRCCOPY | CAPTUREBLT);
                        if (!copied)
                        {
                            error = "PrintWindow and BitBlt both failed.";
                            return false;
                        }
                    }

                    if (!TryReadBitmapPixels(memoryDc, hBitmap, width, height, out byte[] bgra))
                    {
                        error = "GetDIBits failed.";
                        return false;
                    }

                    if (usedPrintWindow && IsMostlyWhite(bgra))
                    {
                        bool copied = BitBlt(
                            memoryDc,
                            0,
                            0,
                            width,
                            height,
                            clientDc,
                            0,
                            0,
                            SRCCOPY | CAPTUREBLT);
                        if (copied && TryReadBitmapPixels(memoryDc, hBitmap, width, height, out byte[] fallbackBgra))
                        {
                            bgra = fallbackBgra;
                        }
                    }

                    Color32[] pixels = new Color32[width * height];
                    int stride = width * 4;
                    for (int y = 0; y < height; y++)
                    {
                        // DIB is bottom-up and Unity's SetPixels32 linear layout is also bottom-up.
                        int srcRow = y * stride;
                        int dstRow = y * width;
                        for (int x = 0; x < width; x++)
                        {
                            int src = srcRow + (x * 4);
                            // BGRA -> RGBA
                            pixels[dstRow + x] = new Color32(
                                bgra[src + 2],
                                bgra[src + 1],
                                bgra[src + 0],
                                255);
                        }
                    }

                    Texture2D texture = new Texture2D(width, height, TextureFormat.RGBA32, false);
                    texture.SetPixels32(pixels);
                    texture.Apply();
                    pngBytes = texture.EncodeToPNG();
                    UnityEngine.Object.DestroyImmediate(texture);

                    return pngBytes != null && pngBytes.Length > 0;
                }
                finally
                {
                    if (oldObject != IntPtr.Zero && memoryDc != IntPtr.Zero)
                    {
                        SelectObject(memoryDc, oldObject);
                    }

                    if (hBitmap != IntPtr.Zero)
                    {
                        DeleteObject(hBitmap);
                    }

                    if (memoryDc != IntPtr.Zero)
                    {
                        DeleteDC(memoryDc);
                    }

                    ReleaseDC(hwnd, clientDc);
                }
            }
            catch (Exception ex)
            {
                error = ex.ToString();
                return false;
            }
#else
            error = "Native editor-window capture is currently implemented only for Windows.";
            return false;
#endif
        }

        private static bool TryReadBitmapPixels(IntPtr memoryDc, IntPtr hBitmap, int width, int height, out byte[] bgra)
        {
            bgra = new byte[width * height * 4];
            BITMAPINFO bmi = new BITMAPINFO
            {
                bmiHeader = new BITMAPINFOHEADER
                {
                    biSize = (uint)Marshal.SizeOf<BITMAPINFOHEADER>(),
                    biWidth = width,
                    biHeight = height,
                    biPlanes = 1,
                    biBitCount = 32,
                    biCompression = BI_RGB,
                }
            };

            int scanLines = GetDIBits(memoryDc, hBitmap, 0, (uint)height, bgra, ref bmi, DIB_RGB_COLORS);
            return scanLines != 0;
        }

        private static bool IsMostlyWhite(byte[] bgra)
        {
            if (bgra == null || bgra.Length < 4)
            {
                return true;
            }

            int whiteish = 0;
            int pixels = bgra.Length / 4;
            for (int index = 0; index < bgra.Length; index += 4)
            {
                if (bgra[index] >= 248 && bgra[index + 1] >= 248 && bgra[index + 2] >= 248)
                {
                    whiteish++;
                }
            }

            return pixels > 0 && ((float)whiteish / pixels) >= 0.98f;
        }

        private static bool TryGetBestEditorWindowHandle(out IntPtr hwnd)
        {
            hwnd = IntPtr.Zero;

#if UNITY_EDITOR_WIN
            int currentProcessId = Process.GetCurrentProcess().Id;
            int bestArea = 0;
            IntPtr bestHandle = IntPtr.Zero;

            bool Callback(IntPtr candidate, IntPtr _)
            {
                if (!IsWindowVisible(candidate))
                {
                    return true;
                }

                GetWindowThreadProcessId(candidate, out uint ownerProcessId);
                if (ownerProcessId != (uint)currentProcessId)
                {
                    return true;
                }

                if (!GetClientRect(candidate, out RECT rect))
                {
                    return true;
                }

                int rectWidth = Math.Max(0, rect.Right - rect.Left);
                int rectHeight = Math.Max(0, rect.Bottom - rect.Top);
                int area = rectWidth * rectHeight;
                if (area <= bestArea)
                {
                    return true;
                }

                bestHandle = candidate;
                bestArea = area;
                return true;
            }

            EnumWindows(Callback, IntPtr.Zero);
            if (bestHandle != IntPtr.Zero)
            {
                hwnd = bestHandle;
                return true;
            }

            hwnd = Process.GetCurrentProcess().MainWindowHandle;
            return hwnd != IntPtr.Zero;
#else
            return false;
#endif
        }

#if UNITY_EDITOR_WIN
        private const int BI_RGB = 0;
        private const uint DIB_RGB_COLORS = 0;
        private const int SRCCOPY = 0x00CC0020;
        private const int CAPTUREBLT = unchecked((int)0x40000000);
        private const int SW_SHOW = 5;
        private const int SW_RESTORE = 9;
        private const uint PW_RENDERFULLCONTENT = 0x00000002;

        [StructLayout(LayoutKind.Sequential)]
        private struct RECT
        {
            public int Left;
            public int Top;
            public int Right;
            public int Bottom;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct BITMAPINFOHEADER
        {
            public uint biSize;
            public int biWidth;
            public int biHeight;
            public ushort biPlanes;
            public ushort biBitCount;
            public uint biCompression;
            public uint biSizeImage;
            public int biXPelsPerMeter;
            public int biYPelsPerMeter;
            public uint biClrUsed;
            public uint biClrImportant;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct BITMAPINFO
        {
            public BITMAPINFOHEADER bmiHeader;
            public uint bmiColors;
        }

        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);

        [DllImport("user32.dll")]
        private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern bool IsWindowVisible(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

        [DllImport("user32.dll")]
        private static extern IntPtr GetDC(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern int ReleaseDC(IntPtr hWnd, IntPtr hdc);

        [DllImport("user32.dll")]
        private static extern bool PrintWindow(IntPtr hwnd, IntPtr hdcBlt, uint nFlags);

        [DllImport("gdi32.dll")]
        private static extern IntPtr CreateCompatibleDC(IntPtr hdc);

        [DllImport("gdi32.dll")]
        private static extern bool DeleteDC(IntPtr hdc);

        [DllImport("gdi32.dll")]
        private static extern IntPtr CreateCompatibleBitmap(IntPtr hdc, int nWidth, int nHeight);

        [DllImport("gdi32.dll")]
        private static extern IntPtr SelectObject(IntPtr hdc, IntPtr hgdiobj);

        [DllImport("gdi32.dll")]
        private static extern bool DeleteObject(IntPtr hObject);

        [DllImport("gdi32.dll")]
        private static extern int GetDIBits(
            IntPtr hdc,
            IntPtr hbmp,
            uint uStartScan,
            uint cScanLines,
            [Out] byte[] lpvBits,
            ref BITMAPINFO lpbi,
            uint uUsage);

        [DllImport("gdi32.dll")]
        private static extern bool BitBlt(
            IntPtr hdcDest,
            int nXDest,
            int nYDest,
            int nWidth,
            int nHeight,
            IntPtr hdcSrc,
            int nXSrc,
            int nYSrc,
            int dwRop);

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool IsIconic(IntPtr hWnd);
#endif

        private static Bounds CalculateBounds(GameObject obj)
        {
            Renderer[] renderers = obj.GetComponentsInChildren<Renderer>();
            if (renderers.Length == 0)
            {
                return new Bounds(obj.transform.position, Vector3.one);
            }

            Bounds bounds = renderers[0].bounds;
            for (int i = 1; i < renderers.Length; i++)
            {
                bounds.Encapsulate(renderers[i].bounds);
            }
            return bounds;
        }

        private static JObject FormatResponse(byte[] imageData, string format, int width, int height, string targetName = null)
        {
            var result = new JObject
            {
                ["success"] = true,
                ["width"] = width,
                ["height"] = height,
                ["format"] = "png",
                ["size_bytes"] = imageData.Length
            };

            if (targetName != null)
            {
                result["target"] = targetName;
            }

            if (format == "base64")
            {
                result["image_base64"] = Convert.ToBase64String(imageData);
                result["data_uri"] = $"data:image/png;base64,{result["image_base64"]}";
            }
            else if (format == "path")
            {
                string tempPath = Path.Combine(Path.GetTempPath(), $"mcp_screenshot_{Guid.NewGuid()}.png");
                File.WriteAllBytes(tempPath, imageData);
                result["file_path"] = tempPath;
            }

            return result;
        }

        private static JObject FormatAndRememberResponse(
            byte[] imageData,
            string format,
            int width,
            int height,
            string sourceAction,
            string targetName = null)
        {
            RememberLastCapture(imageData, width, height, sourceAction);
            return FormatResponse(imageData, format, width, height, targetName);
        }

        private static void RememberLastCapture(byte[] imageData, int width, int height, string sourceAction)
        {
            if (imageData == null || imageData.Length == 0)
            {
                return;
            }

            // Copy to avoid accidental mutation of shared arrays.
            s_lastCapturePng = new byte[imageData.Length];
            Array.Copy(imageData, s_lastCapturePng, imageData.Length);
            s_lastCaptureWidth = width;
            s_lastCaptureHeight = height;
            s_lastCaptureSource = sourceAction;
        }

        private static Color ParseColor(JToken token)
        {
            if (token.Type == JTokenType.String)
            {
                if (ColorUtility.TryParseHtmlString(token.Value<string>(), out Color c))
                {
                    return c;
                }
            }
            else if (token.Type == JTokenType.Array)
            {
                var arr = token as JArray;
                return new Color(
                    arr[0].Value<float>(),
                    arr[1].Value<float>(),
                    arr[2].Value<float>(),
                    arr.Count > 3 ? arr[3].Value<float>() : 1f
                );
            }
            return Color.gray;
        }

        #endregion
    }
}
