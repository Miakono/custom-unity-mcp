using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.Custom
{
    /// <summary>
    /// Project health snapshot for quick AI diagnosis.
    /// Keeps output compact so LLM tools can decide what to run next.
    /// </summary>
    [McpForUnityTool("validate_project_state", Description = "Return core Unity editor/project readiness.", Group = "core")]
    public static class ValidateProjectState
    {
        public static object HandleCommand(JObject @params)
        {
            var activeScene = EditorSceneManager.GetActiveScene();

            var summary = new
            {
                unity = new
                {
                    version = Application.unityVersion,
                    isCompiling = EditorApplication.isCompiling,
                    isUpdating = EditorApplication.isUpdating,
                    isPlaying = EditorApplication.isPlaying,
                    isPlayingOrWillChangePlaymode = EditorApplication.isPlayingOrWillChangePlaymode
                },
                scene = new
                {
                    name = activeScene.name,
                    path = activeScene.path,
                    isDirty = activeScene.isDirty,
                    loadedSceneCount = EditorSceneManager.sceneCount
                },
                selection = new
                {
                    objectCount = Selection.objects?.Length ?? 0,
                    activeObject = Selection.activeObject != null ? Selection.activeObject.name : null
                },
                recommendation = BuildRecommendation()
            };

            return new SuccessResponse("Project state validated.", summary);
        }

        private static string BuildRecommendation()
        {
            if (EditorApplication.isCompiling)
            {
                return "Unity is compiling. Wait for compilation to finish before running mutation tools.";
            }

            if (EditorApplication.isUpdating)
            {
                return "Unity is importing/updating assets. Retry when editor is idle.";
            }

            if (EditorApplication.isPlayingOrWillChangePlaymode)
            {
                return "Unity is entering or running Play Mode. Use read-only tooling unless Play Mode actions are intended.";
            }

            return "Editor is ready for tool execution.";
        }
    }
}
