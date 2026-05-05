using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.AnimatorControllerTool
{
    /// <summary>
    /// Layer-scoped operations: layer CRUD (add/remove/rename), per-layer property writes
    /// (iKPass, defaultWeight, blendingMode, avatarMask, syncedLayerIndex), default-state
    /// assignment, and cloning an entire layer's state graph into a different controller.
    ///
    /// Implementation note: AnimatorControllerLayer is a STRUCT — assigning ctrl.layers[i].x
    /// does not persist. All layer-field writes use read-modify-write:
    ///     var layers = ctrl.layers; layers[i].x = ...; ctrl.layers = layers;
    /// </summary>
    public static partial class ManageAnimatorController
    {
        /// <summary>
        /// Resolve a layer by index (preferred) or by name. Returns -1 on miss.
        /// </summary>
        private static int ResolveLayerIndex(
            UnityEditor.Animations.AnimatorController ctrl, ToolParams p)
        {
            if (p.Has("layerIndex") || p.Has("layer_index"))
            {
                int idx = p.GetInt("layerIndex", 0) ?? 0;
                if (idx >= 0 && idx < ctrl.layers.Length) return idx;
                return -1;
            }
            string name = p.Get("layerName");
            if (!string.IsNullOrEmpty(name))
            {
                for (int i = 0; i < ctrl.layers.Length; i++)
                {
                    if (ctrl.layers[i].name == name) return i;
                }
            }
            return -1;
        }

        // ─── set_default_state ───────────────────────────────────────────────────────

        private static object SetDefaultState(ToolParams p)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            int layerIndex = p.GetInt("layerIndex", 0) ?? 0;
            if (layerIndex < 0 || layerIndex >= ctrl.layers.Length)
                return new ErrorResponse($"layerIndex {layerIndex} out of range.");

            // Accept either stateName (bare name or dotted path) or statePath (alias).
            string nameOrPath = p.Get("stateName") ?? p.Get("statePath");
            if (string.IsNullOrEmpty(nameOrPath))
                return new ErrorResponse("stateName (or statePath) required.");

            var layer = ctrl.layers[layerIndex];
            var sm = layer.stateMachine;
            if (sm == null) return new ErrorResponse($"Layer {layerIndex} has no state machine.");

            var (state, parentSm, fullPath) = FindState(sm, nameOrPath, layer.name);
            if (state == null)
                return new ErrorResponse($"State '{nameOrPath}' not found in layer {layerIndex}.");

            // The default state is set on the parent state machine of the target.
            // For a bare state under the layer root, parentSm == layer.stateMachine.
            parentSm.defaultState = state;

            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);

            return new SuccessResponse(
                $"Default state of layer {layerIndex} set to '{state.name}'.",
                new
                {
                    controller_path = AssetDatabase.GetAssetPath(ctrl),
                    layer_index = layerIndex,
                    layer_name = layer.name,
                    default_state_name = state.name,
                    default_state_path = fullPath,
                });
        }

        // ─── copy_layer_from ─────────────────────────────────────────────────────────

        private static object CopyLayerFrom(ToolParams p)
        {
            string sourcePath = p.Get("sourceController");
            string targetPath = p.Get("targetController");
            int sourceLayerIndex = p.GetInt("sourceLayerIndex", 0) ?? 0;
            int targetLayerIndex = p.GetInt("targetLayerIndex", 0) ?? 0;
            bool remapClips = p.GetBool("remapClips", true);
            bool overwrite = p.GetBool("overwrite", false);

            if (string.IsNullOrEmpty(sourcePath) || string.IsNullOrEmpty(targetPath))
                return new ErrorResponse("sourceController and targetController are required (Assets/.../*.controller).");

            var (src, srcErr) = LoadControllerAtPath(sourcePath);
            if (srcErr != null) return new ErrorResponse($"sourceController: {srcErr}");
            var (tgt, tgtErr) = LoadControllerAtPath(targetPath);
            if (tgtErr != null) return new ErrorResponse($"targetController: {tgtErr}");

            if (sourceLayerIndex < 0 || sourceLayerIndex >= src.layers.Length)
                return new ErrorResponse($"sourceLayerIndex {sourceLayerIndex} out of range (source has {src.layers.Length} layers).");

            // Ensure target layer exists.
            if (targetLayerIndex < 0)
                return new ErrorResponse("targetLayerIndex must be >= 0.");
            while (tgt.layers.Length <= targetLayerIndex)
            {
                tgt.AddLayer($"Layer{tgt.layers.Length}");
            }

            var srcLayer = src.layers[sourceLayerIndex];
            var tgtLayer = tgt.layers[targetLayerIndex];
            var srcSm = srcLayer.stateMachine;
            var tgtSm = tgtLayer.stateMachine;

            if (srcSm == null) return new ErrorResponse("Source layer has no state machine.");
            if (tgtSm == null) return new ErrorResponse("Target layer has no state machine.");

            bool hasExisting = (tgtSm.states != null && tgtSm.states.Length > 0)
                            || (tgtSm.stateMachines != null && tgtSm.stateMachines.Length > 0)
                            || (tgtSm.anyStateTransitions != null && tgtSm.anyStateTransitions.Length > 0);
            if (hasExisting && !overwrite)
                return new ErrorResponse($"Target layer {targetLayerIndex} is non-empty; pass overwrite:true to replace.");

            if (hasExisting)
            {
                // Wipe target sm: any-state transitions, then states (also clears their transitions),
                // then sub-state-machines.
                foreach (var t in tgtSm.anyStateTransitions.ToArray()) tgtSm.RemoveAnyStateTransition(t);
                foreach (var t in tgtSm.entryTransitions.ToArray()) tgtSm.RemoveEntryTransition(t);
                foreach (var s in tgtSm.states.ToArray()) tgtSm.RemoveState(s.state);
                foreach (var ssm in tgtSm.stateMachines.ToArray()) tgtSm.RemoveStateMachine(ssm.stateMachine);
            }

            // Copy parameters that are missing on the target (don't touch existing ones).
            int paramsCopied = 0;
            foreach (var pSrc in src.parameters)
            {
                if (tgt.parameters.Any(pp => pp.name == pSrc.name)) continue;
                tgt.AddParameter(pSrc.name, pSrc.type);
                var newP = tgt.parameters.LastOrDefault(pp => pp.name == pSrc.name);
                if (newP != null)
                {
                    newP.defaultBool = pSrc.defaultBool;
                    newP.defaultFloat = pSrc.defaultFloat;
                    newP.defaultInt = pSrc.defaultInt;
                }
                paramsCopied++;
            }

            // Build a target-clip name lookup once (for clip remapping) — uses base controller's
            // animation clip pool (states, blend trees, override controllers if any).
            Dictionary<string, AnimationClip> targetClipByName = null;
            if (remapClips)
            {
                targetClipByName = new Dictionary<string, AnimationClip>();
                foreach (var clip in tgt.animationClips ?? System.Array.Empty<AnimationClip>())
                {
                    if (clip != null && !targetClipByName.ContainsKey(clip.name))
                        targetClipByName[clip.name] = clip;
                }
            }

            var clipsRemapped = new List<string>();
            var clipsUnmapped = new List<string>();

            // Build state map (source state → newly-created target state) so transitions can resolve.
            var stateMap = new Dictionary<AnimatorState, AnimatorState>();
            int statesCopied = CloneStateMachineRecursive(
                srcSm, tgtSm, stateMap, remapClips, targetClipByName, clipsRemapped, clipsUnmapped);

            // Wire transitions in a second pass now that all states exist.
            int transitionsCopied = 0;
            transitionsCopied += CloneTransitions(srcSm, tgtSm, stateMap);

            // Set default state if source had one and we have a mapping.
            if (srcSm.defaultState != null && stateMap.TryGetValue(srcSm.defaultState, out var newDefault))
            {
                tgtSm.defaultState = newDefault;
            }

            EditorUtility.SetDirty(tgt);
            AssetDatabase.SaveAssetIfDirty(tgt);

            return new SuccessResponse(
                $"Copied layer {sourceLayerIndex} of '{src.name}' → layer {targetLayerIndex} of '{tgt.name}'.",
                new
                {
                    source_controller = sourcePath,
                    target_controller = targetPath,
                    source_layer_index = sourceLayerIndex,
                    target_layer_index = targetLayerIndex,
                    states_copied = statesCopied,
                    transitions_copied = transitionsCopied,
                    parameters_copied = paramsCopied,
                    clips_remapped = clipsRemapped.Count,
                    clips_remapped_names = clipsRemapped,
                    clips_unmapped = clipsUnmapped,
                });
        }

        private static int CloneStateMachineRecursive(
            AnimatorStateMachine srcSm, AnimatorStateMachine tgtSm,
            Dictionary<AnimatorState, AnimatorState> stateMap,
            bool remapClips, Dictionary<string, AnimationClip> targetClipByName,
            List<string> clipsRemapped, List<string> clipsUnmapped)
        {
            int copied = 0;
            foreach (var cs in srcSm.states ?? System.Array.Empty<ChildAnimatorState>())
            {
                var src = cs.state;
                var dst = tgtSm.AddState(src.name, cs.position);
                dst.speed = src.speed;
                dst.cycleOffset = src.cycleOffset;
                dst.mirror = src.mirror;
                dst.writeDefaultValues = src.writeDefaultValues;
                dst.tag = src.tag;
                dst.iKOnFeet = src.iKOnFeet;

                // Motion remap.
                if (src.motion is AnimationClip clip)
                {
                    if (remapClips && targetClipByName != null
                        && targetClipByName.TryGetValue(clip.name, out var matchedClip))
                    {
                        dst.motion = matchedClip;
                        if (!clipsRemapped.Contains(clip.name)) clipsRemapped.Add(clip.name);
                    }
                    else
                    {
                        // Reference the source clip directly when no remap matches.
                        // It's a shared asset, not duplicated, so this is safe.
                        dst.motion = clip;
                        if (remapClips && !clipsUnmapped.Contains(clip.name)) clipsUnmapped.Add(clip.name);
                    }
                }
                else if (src.motion != null)
                {
                    // BlendTree or other Motion subclass — reference as-is (shared asset).
                    dst.motion = src.motion;
                }

                stateMap[src] = dst;
                copied++;
            }

            // Recurse sub-state-machines.
            foreach (var ssm in srcSm.stateMachines ?? System.Array.Empty<ChildAnimatorStateMachine>())
            {
                var dstSsm = tgtSm.AddStateMachine(ssm.stateMachine.name, ssm.position);
                copied += CloneStateMachineRecursive(
                    ssm.stateMachine, dstSsm, stateMap,
                    remapClips, targetClipByName, clipsRemapped, clipsUnmapped);
            }
            return copied;
        }

        private static int CloneTransitions(
            AnimatorStateMachine srcSm, AnimatorStateMachine tgtSm,
            Dictionary<AnimatorState, AnimatorState> stateMap)
        {
            int count = 0;

            // Per-state transitions.
            foreach (var cs in srcSm.states ?? System.Array.Empty<ChildAnimatorState>())
            {
                if (!stateMap.TryGetValue(cs.state, out var dstFrom)) continue;
                foreach (var t in cs.state.transitions ?? System.Array.Empty<AnimatorStateTransition>())
                {
                    if (t.destinationState == null) continue;            // SSM-targeting transitions skipped (best effort).
                    if (!stateMap.TryGetValue(t.destinationState, out var dstTo)) continue;
                    var newT = dstFrom.AddTransition(dstTo);
                    CopyTransitionShape(t, newT);
                    count++;
                }
            }

            // Any-state transitions.
            foreach (var t in srcSm.anyStateTransitions ?? System.Array.Empty<AnimatorStateTransition>())
            {
                if (t.destinationState == null) continue;
                if (!stateMap.TryGetValue(t.destinationState, out var dstTo)) continue;
                var newT = tgtSm.AddAnyStateTransition(dstTo);
                CopyTransitionShape(t, newT);
                count++;
            }

            // Recurse.
            foreach (var ssm in srcSm.stateMachines ?? System.Array.Empty<ChildAnimatorStateMachine>())
            {
                var matchingDst = tgtSm.stateMachines.FirstOrDefault(c => c.stateMachine.name == ssm.stateMachine.name).stateMachine;
                if (matchingDst != null)
                {
                    count += CloneTransitions(ssm.stateMachine, matchingDst, stateMap);
                }
            }
            return count;
        }

        private static void CopyTransitionShape(AnimatorStateTransition src, AnimatorStateTransition dst)
        {
            dst.duration = src.duration;
            dst.exitTime = src.exitTime;
            dst.hasExitTime = src.hasExitTime;
            dst.offset = src.offset;
            dst.interruptionSource = src.interruptionSource;
            dst.orderedInterruption = src.orderedInterruption;
            dst.canTransitionToSelf = src.canTransitionToSelf;
            dst.hasFixedDuration = src.hasFixedDuration;
            dst.solo = src.solo;
            dst.mute = src.mute;

            foreach (var c in src.conditions ?? System.Array.Empty<AnimatorCondition>())
            {
                dst.AddCondition(c.mode, c.threshold, c.parameter);
            }
        }

        // ─── add_layer ───────────────────────────────────────────────────────────────

        private static object AddLayer(ToolParams p, JObject raw)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            string layerName = p.Get("layerName") ?? p.Get("name");
            if (string.IsNullOrEmpty(layerName))
                return new ErrorResponse("layerName required.");
            if (ctrl.layers.Any(l => l.name == layerName))
                return new ErrorResponse($"A layer named '{layerName}' already exists.");

            // ctrl.AddLayer creates a layer with a fresh, empty state machine internally.
            ctrl.AddLayer(layerName);
            int newIndex = ctrl.layers.Length - 1;

            // Apply optional properties to the freshly-added layer (read-modify-write).
            ApplyLayerProperties(ctrl, newIndex, p, raw, out var changed);

            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);

            return new SuccessResponse($"Added layer '{layerName}' at index {newIndex}.", new
            {
                controller_path = AssetDatabase.GetAssetPath(ctrl),
                layer_index = newIndex,
                layer_name = layerName,
                applied_properties = changed,
                layer_count = ctrl.layers.Length,
            });
        }

        // ─── remove_layer ────────────────────────────────────────────────────────────

        private static object RemoveLayer(ToolParams p)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            int idx = ResolveLayerIndex(ctrl, p);
            if (idx < 0) return new ErrorResponse("layerIndex/layerName did not resolve to an existing layer.");

            bool force = p.GetBool("force", false);
            if (idx == 0 && !force)
                return new ErrorResponse("Refusing to remove layer 0 (base layer) without force:true.");

            string removedName = ctrl.layers[idx].name;
            ctrl.RemoveLayer(idx);

            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);

            return new SuccessResponse($"Removed layer '{removedName}' (index {idx}).", new
            {
                controller_path = AssetDatabase.GetAssetPath(ctrl),
                removed_index = idx,
                removed_name = removedName,
                layer_count = ctrl.layers.Length,
            });
        }

        // ─── rename_layer ────────────────────────────────────────────────────────────

        private static object RenameLayer(ToolParams p)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            int idx = ResolveLayerIndex(ctrl, p);
            if (idx < 0) return new ErrorResponse("layerIndex/layerName did not resolve to an existing layer.");

            string newName = p.Get("newLayerName");
            if (string.IsNullOrEmpty(newName)) return new ErrorResponse("newLayerName required.");
            if (ctrl.layers.Any(l => l.name == newName))
                return new ErrorResponse($"A layer named '{newName}' already exists.");

            // Read-modify-write: AnimatorControllerLayer is a struct.
            var layers = ctrl.layers;
            string oldName = layers[idx].name;
            layers[idx].name = newName;
            // The state machine name conventionally tracks the layer name in Unity.
            if (layers[idx].stateMachine != null) layers[idx].stateMachine.name = newName;
            ctrl.layers = layers;

            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);

            return new SuccessResponse($"Renamed layer {idx} '{oldName}' → '{newName}'.", new
            {
                controller_path = AssetDatabase.GetAssetPath(ctrl),
                layer_index = idx,
                old_name = oldName,
                new_name = newName,
            });
        }

        // ─── set_layer_property ──────────────────────────────────────────────────────

        private static object SetLayerProperty(ToolParams p, JObject raw)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            int idx = ResolveLayerIndex(ctrl, p);
            if (idx < 0) return new ErrorResponse("layerIndex/layerName did not resolve to an existing layer.");

            ApplyLayerProperties(ctrl, idx, p, raw, out var changed);
            if (changed.Count == 0)
                return new ErrorResponse("No layer properties supplied. Pass any of: iKPass, defaultWeight, blendingMode, avatarMaskPath, syncedLayerIndex, syncedLayerAffectsTiming.");

            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);

            var layer = ctrl.layers[idx];
            return new SuccessResponse(
                $"Updated layer {idx} ({string.Join(", ", changed)}).",
                new
                {
                    controller_path = AssetDatabase.GetAssetPath(ctrl),
                    layer_index = idx,
                    layer_name = layer.name,
                    applied_properties = changed,
                    ik_pass = layer.iKPass,
                    default_weight = layer.defaultWeight,
                    blending_mode = layer.blendingMode.ToString(),
                    avatar_mask_path = layer.avatarMask != null ? AssetDatabase.GetAssetPath(layer.avatarMask) : null,
                    synced_layer_index = layer.syncedLayerIndex,
                    synced_layer_affects_timing = layer.syncedLayerAffectsTiming,
                });
        }

        /// <summary>
        /// Apply optional layer-property writes via read-modify-write. Returns the list of
        /// fields that changed for the response.
        /// </summary>
        private static void ApplyLayerProperties(
            UnityEditor.Animations.AnimatorController ctrl, int idx, ToolParams p, JObject raw,
            out List<string> changed)
        {
            changed = new List<string>();
            var layers = ctrl.layers;
            var l = layers[idx];

            if (p.Has("iKPass") || p.Has("ik_pass"))
            {
                l.iKPass = p.GetBool("iKPass", l.iKPass);
                changed.Add("iKPass");
            }
            if (p.Has("defaultWeight") || p.Has("default_weight"))
            {
                var v = p.GetFloat("defaultWeight");
                if (v.HasValue) { l.defaultWeight = v.Value; changed.Add("defaultWeight"); }
            }
            string blendRaw = p.Get("blendingMode");
            if (!string.IsNullOrEmpty(blendRaw))
            {
                if (Enum.TryParse<AnimatorLayerBlendingMode>(blendRaw, ignoreCase: true, out var bm))
                {
                    l.blendingMode = bm;
                    changed.Add("blendingMode");
                }
            }
            if (p.Has("avatarMaskPath") || p.Has("avatar_mask_path"))
            {
                string maskPath = p.Get("avatarMaskPath");
                if (string.IsNullOrEmpty(maskPath))
                {
                    l.avatarMask = null;
                    changed.Add("avatarMask(cleared)");
                }
                else
                {
                    var mask = AssetDatabase.LoadAssetAtPath<AvatarMask>(maskPath);
                    if (mask != null) { l.avatarMask = mask; changed.Add("avatarMask"); }
                }
            }
            if (p.Has("syncedLayerIndex") || p.Has("synced_layer_index"))
            {
                var v = p.GetInt("syncedLayerIndex");
                if (v.HasValue) { l.syncedLayerIndex = v.Value; changed.Add("syncedLayerIndex"); }
            }
            if (p.Has("syncedLayerAffectsTiming") || p.Has("synced_layer_affects_timing"))
            {
                l.syncedLayerAffectsTiming = p.GetBool("syncedLayerAffectsTiming", l.syncedLayerAffectsTiming);
                changed.Add("syncedLayerAffectsTiming");
            }

            layers[idx] = l;
            ctrl.layers = layers;
        }
    }
}
