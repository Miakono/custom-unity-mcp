using System;
using System.IO;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEditor;
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

            return FormatResponse(imageData, format, width, height);
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

            return FormatResponse(imageData, format, width, height);
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

            return FormatResponse(imageData, format, width, height, target.name);
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
