using System.Collections.Generic;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.AnimatorControllerTool
{
    /// <summary>
    /// State-property writes (post-creation): speed, cycleOffset, mirror, writeDefaultValues,
    /// tag, iKOnFeet, motion. AnimatorState is a ScriptableObject-derived class so direct
    /// field writes + EditorUtility.SetDirty(ctrl) are sufficient (no struct round-trip needed).
    /// </summary>
    public static partial class ManageAnimatorController
    {
        private static object SetStateProperty(ToolParams p, JObject raw)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            int layerIndex = p.GetInt("layerIndex", 0) ?? 0;
            if (layerIndex < 0 || layerIndex >= ctrl.layers.Length)
                return new ErrorResponse($"layerIndex {layerIndex} out of range.");

            string nameOrPath = p.Get("stateName") ?? p.Get("statePath");
            if (string.IsNullOrEmpty(nameOrPath))
                return new ErrorResponse("stateName (or statePath) required.");

            var layer = ctrl.layers[layerIndex];
            var sm = layer.stateMachine;
            if (sm == null) return new ErrorResponse($"Layer {layerIndex} has no state machine.");

            var (state, _, fullPath) = FindState(sm, nameOrPath, layer.name);
            if (state == null)
                return new ErrorResponse($"State '{nameOrPath}' not found in layer {layerIndex}.");

            var changed = new List<string>();

            if (p.Has("speed"))
            {
                var v = p.GetFloat("speed");
                if (v.HasValue) { state.speed = v.Value; changed.Add("speed"); }
            }
            if (p.Has("cycleOffset") || p.Has("cycle_offset"))
            {
                var v = p.GetFloat("cycleOffset");
                if (v.HasValue) { state.cycleOffset = v.Value; changed.Add("cycleOffset"); }
            }
            if (p.Has("mirror"))
            {
                state.mirror = p.GetBool("mirror", state.mirror);
                changed.Add("mirror");
            }
            if (p.Has("writeDefaultValues") || p.Has("write_default_values"))
            {
                state.writeDefaultValues = p.GetBool("writeDefaultValues", state.writeDefaultValues);
                changed.Add("writeDefaultValues");
            }
            if (p.Has("tag"))
            {
                state.tag = p.Get("tag") ?? string.Empty;
                changed.Add("tag");
            }
            if (p.Has("iKOnFeet") || p.Has("ik_on_feet"))
            {
                state.iKOnFeet = p.GetBool("iKOnFeet", state.iKOnFeet);
                changed.Add("iKOnFeet");
            }

            // Motion: pass empty string OR clearMotion:true to clear; otherwise treat as a clip path.
            bool clearMotion = p.GetBool("clearMotion", false);
            if (clearMotion)
            {
                state.motion = null;
                changed.Add("motion(cleared)");
            }
            else if (p.Has("motion") || p.Has("clipPath") || p.Has("clip_path"))
            {
                string motionPath = p.Get("motion") ?? p.Get("clipPath");
                if (string.IsNullOrEmpty(motionPath))
                {
                    state.motion = null;
                    changed.Add("motion(cleared)");
                }
                else
                {
                    var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(motionPath);
                    if (clip == null)
                        return new ErrorResponse($"AnimationClip not found at '{motionPath}'.");
                    state.motion = clip;
                    changed.Add("motion");
                }
            }

            if (changed.Count == 0)
                return new ErrorResponse("No state properties supplied. Pass any of: speed, cycleOffset, mirror, writeDefaultValues, tag, iKOnFeet, motion, clearMotion.");

            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);

            return new SuccessResponse(
                $"Updated state '{state.name}' ({string.Join(", ", changed)}).",
                new
                {
                    controller_path = AssetDatabase.GetAssetPath(ctrl),
                    layer_index = layerIndex,
                    state_name = state.name,
                    state_path = fullPath,
                    applied_properties = changed,
                    speed = state.speed,
                    cycle_offset = state.cycleOffset,
                    mirror = state.mirror,
                    write_default_values = state.writeDefaultValues,
                    tag = state.tag,
                    ik_on_feet = state.iKOnFeet,
                    motion_name = state.motion != null ? state.motion.name : null,
                    motion_path = state.motion != null ? AssetDatabase.GetAssetPath(state.motion) : null,
                });
        }
    }
}
