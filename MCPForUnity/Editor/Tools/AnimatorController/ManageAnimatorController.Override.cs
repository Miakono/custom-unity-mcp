using System.Collections.Generic;
using System.IO;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.AnimatorControllerTool
{
    /// <summary>
    /// AnimatorOverrideController operations: create overrides, list/set/clear individual
    /// clip overrides. Standard pattern for re-skinning a state machine with different clips.
    /// </summary>
    public static partial class ManageAnimatorController
    {
        private static (AnimatorOverrideController aoc, string error) LoadOverride(ToolParams p)
        {
            string path = p.Get("overrideControllerPath") ?? p.Get("controllerPath");
            if (string.IsNullOrEmpty(path))
                return (null, "'overrideControllerPath' is required (Assets/.../*.overrideController).");
            var aoc = AssetDatabase.LoadAssetAtPath<AnimatorOverrideController>(path);
            if (aoc == null)
                return (null, $"AnimatorOverrideController not found at '{path}'.");
            return (aoc, null);
        }

        // ─── create_override ─────────────────────────────────────────────────────────

        private static object CreateOverride(ToolParams p)
        {
            string outputPath = p.Get("outputPath");
            string baseControllerPath = p.Get("baseController") ?? p.Get("baseControllerPath");

            if (string.IsNullOrEmpty(outputPath))
                return new ErrorResponse("outputPath required (Assets/.../*.overrideController).");
            if (string.IsNullOrEmpty(baseControllerPath))
                return new ErrorResponse("baseController required (Assets/.../*.controller).");

            // Normalize extension.
            if (!outputPath.EndsWith(".overrideController", System.StringComparison.OrdinalIgnoreCase))
                outputPath += ".overrideController";

            var (baseCtrl, err) = LoadControllerAtPath(baseControllerPath);
            if (err != null) return new ErrorResponse($"baseController: {err}");

            // Ensure parent folder exists.
            string folder = Path.GetDirectoryName(outputPath)?.Replace('\\', '/');
            if (!string.IsNullOrEmpty(folder) && !AssetDatabase.IsValidFolder(folder))
                return new ErrorResponse($"Output folder '{folder}' does not exist; create it first.");

            if (AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(outputPath) != null)
                return new ErrorResponse($"Asset already exists at '{outputPath}'.");

            var aoc = new AnimatorOverrideController(baseCtrl);
            aoc.name = Path.GetFileNameWithoutExtension(outputPath);
            AssetDatabase.CreateAsset(aoc, outputPath);
            AssetDatabase.SaveAssets();

            return new SuccessResponse(
                $"Created AnimatorOverrideController at '{outputPath}'.",
                new
                {
                    override_controller_path = outputPath,
                    base_controller = baseControllerPath,
                    override_count = aoc.overridesCount,
                });
        }

        // ─── list_overrides ──────────────────────────────────────────────────────────

        private static object ListOverrides(ToolParams p)
        {
            var (aoc, err) = LoadOverride(p);
            if (err != null) return new ErrorResponse(err);

            var pairs = new List<KeyValuePair<AnimationClip, AnimationClip>>();
            aoc.GetOverrides(pairs);

            var entries = pairs.Select(kvp => (object)new
            {
                original_name = kvp.Key != null ? kvp.Key.name : null,
                original_path = kvp.Key != null ? AssetDatabase.GetAssetPath(kvp.Key) : null,
                override_name = kvp.Value != null ? kvp.Value.name : null,
                override_path = kvp.Value != null ? AssetDatabase.GetAssetPath(kvp.Value) : null,
                has_override = kvp.Value != null,
            }).ToArray();

            return new SuccessResponse(
                $"Override controller '{aoc.name}' has {entries.Length} clip slots.",
                new
                {
                    override_controller_path = AssetDatabase.GetAssetPath(aoc),
                    runtime_animator_controller = aoc.runtimeAnimatorController != null
                        ? AssetDatabase.GetAssetPath(aoc.runtimeAnimatorController)
                        : null,
                    override_count = entries.Length,
                    overrides = entries,
                });
        }

        // ─── set_override_clip ───────────────────────────────────────────────────────

        private static object SetOverrideClip(ToolParams p)
        {
            var (aoc, err) = LoadOverride(p);
            if (err != null) return new ErrorResponse(err);

            string originalName = p.Get("originalClipName");
            string overrideClipPath = p.Get("overrideClip") ?? p.Get("overrideClipPath");
            if (string.IsNullOrEmpty(originalName))
                return new ErrorResponse("originalClipName required.");
            if (string.IsNullOrEmpty(overrideClipPath))
                return new ErrorResponse("overrideClip path required (Assets/.../*.anim).");

            var overrideClip = AssetDatabase.LoadAssetAtPath<AnimationClip>(overrideClipPath);
            if (overrideClip == null)
                return new ErrorResponse($"AnimationClip not found at '{overrideClipPath}'.");

            var pairs = new List<KeyValuePair<AnimationClip, AnimationClip>>();
            aoc.GetOverrides(pairs);

            int matchIdx = -1;
            for (int i = 0; i < pairs.Count; i++)
            {
                if (pairs[i].Key != null && pairs[i].Key.name == originalName) { matchIdx = i; break; }
            }
            if (matchIdx < 0)
                return new ErrorResponse($"No clip named '{originalName}' on base controller.");

            pairs[matchIdx] = new KeyValuePair<AnimationClip, AnimationClip>(pairs[matchIdx].Key, overrideClip);
            aoc.ApplyOverrides(pairs);
            EditorUtility.SetDirty(aoc);
            AssetDatabase.SaveAssetIfDirty(aoc);

            return new SuccessResponse(
                $"Override '{originalName}' set to '{overrideClip.name}'.",
                new
                {
                    override_controller_path = AssetDatabase.GetAssetPath(aoc),
                    original_clip_name = originalName,
                    override_clip_name = overrideClip.name,
                    override_clip_path = overrideClipPath,
                });
        }

        // ─── clear_override ──────────────────────────────────────────────────────────

        private static object ClearOverride(ToolParams p)
        {
            var (aoc, err) = LoadOverride(p);
            if (err != null) return new ErrorResponse(err);

            string originalName = p.Get("originalClipName");
            if (string.IsNullOrEmpty(originalName))
                return new ErrorResponse("originalClipName required.");

            var pairs = new List<KeyValuePair<AnimationClip, AnimationClip>>();
            aoc.GetOverrides(pairs);

            int matchIdx = -1;
            for (int i = 0; i < pairs.Count; i++)
            {
                if (pairs[i].Key != null && pairs[i].Key.name == originalName) { matchIdx = i; break; }
            }
            if (matchIdx < 0)
                return new ErrorResponse($"No clip named '{originalName}' on base controller.");

            pairs[matchIdx] = new KeyValuePair<AnimationClip, AnimationClip>(pairs[matchIdx].Key, null);
            aoc.ApplyOverrides(pairs);
            EditorUtility.SetDirty(aoc);
            AssetDatabase.SaveAssetIfDirty(aoc);

            return new SuccessResponse(
                $"Cleared override for '{originalName}'.",
                new
                {
                    override_controller_path = AssetDatabase.GetAssetPath(aoc),
                    original_clip_name = originalName,
                });
        }
    }
}
