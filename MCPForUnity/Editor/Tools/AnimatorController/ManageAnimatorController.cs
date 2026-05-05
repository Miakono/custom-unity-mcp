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
    /// Read + targeted-mutation tool for AnimatorController state machines: states,
    /// transitions, parameters, layers, default state, copy-from, override controllers.
    /// Existing manage_animation handles AnimationClip authoring; this one owns the
    /// controller graph that wires clips together.
    ///
    /// Split across partial files:
    ///   - ManageAnimatorController.cs              (entry point, dispatch, shared helpers, baseline actions)
    ///   - ManageAnimatorController.Layers.cs       (set_default_state, copy_layer_from)
    ///   - ManageAnimatorController.Transitions.cs  (set_transition_property, add_any_state_transition)
    ///   - ManageAnimatorController.Override.cs     (create_override, list_overrides, set_override_clip, clear_override)
    /// </summary>
    [McpForUnityTool("manage_animator_controller", AutoRegister = false, Group = "animation")]
    public static partial class ManageAnimatorController
    {
        public static object HandleCommand(JObject @params)
        {
            if (@params == null) return new ErrorResponse("Parameters cannot be null.");

            // Action-level batch over multiple controllers: dispatch the action against each
            // and aggregate. This is purely a server-side loop — saves LLM↔server round trips.
            var controllersToken = @params["controllers"] ?? @params["Controllers"];
            if (controllersToken is JArray controllersArray && controllersArray.Count > 0)
            {
                return DispatchControllerBatch(@params, controllersArray);
            }

            var p = new ToolParams(@params);
            var actionResult = p.GetRequired("action");
            if (!actionResult.IsSuccess) return new ErrorResponse(actionResult.ErrorMessage);
            string action = actionResult.Value.ToLowerInvariant();

            try
            {
                switch (action)
                {
                    case "get": return Get(p);
                    case "list_states": return ListStates(p);
                    case "list_transitions": return ListTransitions(p);
                    case "list_parameters": return ListParameters(p);
                    case "list_layers": return ListLayers(p);
                    case "add_parameter": return AddParameter(p, @params);
                    case "remove_parameter": return RemoveParameter(p);
                    case "add_state": return AddState(p, @params);
                    case "remove_state": return RemoveState(p);
                    case "add_transition": return AddTransition(p, @params);
                    case "set_default_state": return SetDefaultState(p);
                    case "set_transition_property": return SetTransitionProperty(p, @params);
                    case "add_any_state_transition": return AddAnyStateTransition(p, @params);
                    case "copy_layer_from": return CopyLayerFrom(p);
                    case "create_override": return CreateOverride(p);
                    case "list_overrides": return ListOverrides(p);
                    case "set_override_clip": return SetOverrideClip(p);
                    case "clear_override": return ClearOverride(p);
                    case "add_layer": return AddLayer(p, @params);
                    case "remove_layer": return RemoveLayer(p);
                    case "rename_layer": return RenameLayer(p);
                    case "set_layer_property": return SetLayerProperty(p, @params);
                    case "set_state_property": return SetStateProperty(p, @params);
                    default:
                        return new ErrorResponse(
                            $"Unknown action '{action}'. Valid: get, list_states, list_transitions, " +
                            "list_parameters, list_layers, add_parameter, remove_parameter, " +
                            "add_state, remove_state, add_transition, set_default_state, " +
                            "set_transition_property, add_any_state_transition, copy_layer_from, " +
                            "create_override, list_overrides, set_override_clip, clear_override, " +
                            "add_layer, remove_layer, rename_layer, set_layer_property, set_state_property.");
                }
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"manage_animator_controller {action} failed: {ex.Message}");
            }
        }

        // ─── controller-batch dispatch ───────────────────────────────────────────────

        private static object DispatchControllerBatch(JObject original, JArray controllers)
        {
            var successes = new List<object>();
            var failures = new List<object>();

            foreach (var token in controllers)
            {
                string path = token?.ToString();
                if (string.IsNullOrEmpty(path)) continue;

                var clone = (JObject)original.DeepClone();
                clone.Remove("controllers");
                clone.Remove("Controllers");
                clone["controllerPath"] = path;

                var result = HandleCommand(clone);
                bool ok = result is SuccessResponse;
                var entry = new { controllerPath = path, response = result };
                if (ok) successes.Add(entry); else failures.Add(entry);
            }

            return new SuccessResponse(
                $"Batch complete: {successes.Count} succeeded, {failures.Count} failed.",
                new
                {
                    success_count = successes.Count,
                    failure_count = failures.Count,
                    successes,
                    failures,
                });
        }

        // ─── helpers ──────────────────────────────────────────────────────────────────

        private static (UnityEditor.Animations.AnimatorController controller, string error) LoadController(ToolParams p)
        {
            string path = p.Get("controllerPath");
            if (string.IsNullOrEmpty(path))
                return (null, "'controllerPath' is required (Assets/.../*.controller).");
            return LoadControllerAtPath(path);
        }

        private static (UnityEditor.Animations.AnimatorController controller, string error) LoadControllerAtPath(string path)
        {
            if (string.IsNullOrEmpty(path)) return (null, "Controller path is null/empty.");
            var ctrl = AssetDatabase.LoadAssetAtPath<UnityEditor.Animations.AnimatorController>(path);
            if (ctrl == null)
                return (null, $"AnimatorController not found at '{path}'.");
            return (ctrl, null);
        }

        private static object DescribeParameter(AnimatorControllerParameter param) => new
        {
            name = param.name,
            type = param.type.ToString(),
            default_bool = param.defaultBool,
            default_float = param.defaultFloat,
            default_int = param.defaultInt,
        };

        private static object DescribeState(AnimatorState state, int layerIndex) => new
        {
            name = state.name,
            layer_index = layerIndex,
            speed = state.speed,
            motion_name = state.motion != null ? state.motion.name : null,
            motion_path = state.motion != null ? AssetDatabase.GetAssetPath(state.motion) : null,
            transition_count = state.transitions?.Length ?? 0,
            cycle_offset = state.cycleOffset,
            mirror = state.mirror,
            write_default_values = state.writeDefaultValues,
            tag = state.tag,
            ik_on_feet = state.iKOnFeet,
        };

        /// <summary>Layer-describe used by both Get and ListLayers — exposes IK Pass + sync fields.</summary>
        private static object DescribeLayer(AnimatorControllerLayer layer, int idx)
        {
            AnimatorState defaultState = layer.stateMachine?.defaultState;
            return new
            {
                index = idx,
                name = layer.name,
                weight = layer.defaultWeight,
                state_count = layer.stateMachine?.states?.Length ?? 0,
                blending_mode = layer.blendingMode.ToString(),
                ik_pass = layer.iKPass,
                avatar_mask_path = layer.avatarMask != null ? AssetDatabase.GetAssetPath(layer.avatarMask) : null,
                synced_layer_index = layer.syncedLayerIndex,
                synced_layer_affects_timing = layer.syncedLayerAffectsTiming,
                default_state_name = defaultState != null ? defaultState.name : null,
                default_state_path = defaultState != null
                    ? BuildStatePath(layer.name, layer.stateMachine, defaultState)
                    : null,
            };
        }

        /// <summary>
        /// Resolve a state by simple name, dotted path ("Base Layer.Sub.Idle" or "Sub.Idle"),
        /// or short name within nested state machines (depth-first search). Returns null if not found.
        /// Also returns the parent state machine for callers that need it (e.g. defaultState assignment).
        /// </summary>
        private static (AnimatorState state, AnimatorStateMachine parent, string fullPath) FindState(
            AnimatorStateMachine root, string nameOrPath, string rootName = null)
        {
            if (root == null || string.IsNullOrEmpty(nameOrPath))
                return (null, null, null);

            // Dotted path: descend by name.
            if (nameOrPath.Contains("."))
            {
                var parts = nameOrPath.Split('.');
                int startIdx = 0;
                // Allow optional leading layer/root name like "Base Layer.X" — skip it if it matches.
                if (rootName != null && parts.Length > 1 && string.Equals(parts[0], rootName, StringComparison.Ordinal))
                    startIdx = 1;

                AnimatorStateMachine cur = root;
                for (int i = startIdx; i < parts.Length - 1; i++)
                {
                    var nextSm = cur.stateMachines.FirstOrDefault(c => c.stateMachine.name == parts[i]).stateMachine;
                    if (nextSm == null) return (null, null, null);
                    cur = nextSm;
                }
                string leaf = parts[parts.Length - 1];
                var match = cur.states.FirstOrDefault(c => c.state.name == leaf).state;
                if (match == null) return (null, null, null);
                return (match, cur, BuildStatePath(rootName, root, match));
            }

            // Bare name: depth-first search.
            return FindStateRecursive(root, nameOrPath, rootName);
        }

        private static (AnimatorState, AnimatorStateMachine, string) FindStateRecursive(
            AnimatorStateMachine sm, string name, string rootName)
        {
            foreach (var cs in sm.states)
            {
                if (cs.state.name == name)
                    return (cs.state, sm, BuildStatePath(rootName, sm, cs.state));
            }
            foreach (var ssm in sm.stateMachines)
            {
                var (s, parent, path) = FindStateRecursive(ssm.stateMachine, name, rootName);
                if (s != null) return (s, parent, path);
            }
            return (null, null, null);
        }

        /// <summary>
        /// Build a dotted state path like "Base Layer.SubMachine.Idle". When the state lives at
        /// the root of the layer, returns "Base Layer.Idle". `rootName` is typically the layer name.
        /// </summary>
        private static string BuildStatePath(string rootName, AnimatorStateMachine root, AnimatorState target)
        {
            // We don't have a parent-pointer on AnimatorStateMachine, so recurse and prepend.
            var path = new List<string>();
            if (BuildStatePathRecursive(root, target, path))
            {
                if (!string.IsNullOrEmpty(rootName)) path.Insert(0, rootName);
                return string.Join(".", path);
            }
            return target?.name;
        }

        private static bool BuildStatePathRecursive(AnimatorStateMachine sm, AnimatorState target, List<string> path)
        {
            foreach (var cs in sm.states)
            {
                if (cs.state == target)
                {
                    path.Add(cs.state.name);
                    return true;
                }
            }
            foreach (var ssm in sm.stateMachines)
            {
                if (BuildStatePathRecursive(ssm.stateMachine, target, path))
                {
                    path.Insert(0, ssm.stateMachine.name);
                    return true;
                }
            }
            return false;
        }

        private static object DescribeTransition(AnimatorStateTransition t, string sourceName, int transitionIndex) => new
        {
            source = sourceName,                              // either "any_state" or the source state name
            from_state = sourceName == "any_state" ? null : sourceName,
            to_state = t.destinationState?.name,
            to_state_machine = t.destinationStateMachine?.name,
            transition_index = transitionIndex,
            duration = t.duration,
            offset = t.offset,
            has_exit_time = t.hasExitTime,
            exit_time = t.exitTime,
            interruption_source = t.interruptionSource.ToString(),
            ordered_interruption = t.orderedInterruption,
            can_transition_to_self = t.canTransitionToSelf,
            condition_count = t.conditions?.Length ?? 0,
            conditions = t.conditions?.Select(c => (object)new
            {
                parameter = c.parameter,
                mode = c.mode.ToString(),
                threshold = c.threshold,
            }).ToArray() ?? Array.Empty<object>(),
        };

        /// <summary>
        /// Apply optional timing/interruption fields from request params onto a transition. Returns
        /// the list of fields that were updated, for logging in responses.
        /// </summary>
        private static List<string> ApplyTransitionProperties(
            AnimatorStateTransition transition, ToolParams p, JObject raw)
        {
            var changed = new List<string>();
            if (p.Has("duration"))
            {
                var v = p.GetFloat("duration");
                if (v.HasValue) { transition.duration = v.Value; changed.Add("duration"); }
            }
            if (p.Has("hasExitTime") || p.Has("has_exit_time"))
            {
                transition.hasExitTime = p.GetBool("hasExitTime", transition.hasExitTime);
                changed.Add("hasExitTime");
            }
            if (p.Has("exitTime") || p.Has("exit_time"))
            {
                var v = p.GetFloat("exitTime");
                if (v.HasValue) { transition.exitTime = v.Value; changed.Add("exitTime"); }
            }
            if (p.Has("offset"))
            {
                var v = p.GetFloat("offset");
                if (v.HasValue) { transition.offset = v.Value; changed.Add("offset"); }
            }
            string interruption = p.Get("interruptionSource");
            if (!string.IsNullOrEmpty(interruption))
            {
                if (Enum.TryParse<TransitionInterruptionSource>(interruption, ignoreCase: true, out var src))
                {
                    transition.interruptionSource = src;
                    changed.Add("interruptionSource");
                }
            }
            if (p.Has("orderedInterruption") || p.Has("ordered_interruption"))
            {
                transition.orderedInterruption = p.GetBool("orderedInterruption", transition.orderedInterruption);
                changed.Add("orderedInterruption");
            }
            if (p.Has("canTransitionToSelf") || p.Has("can_transition_to_self"))
            {
                transition.canTransitionToSelf = p.GetBool("canTransitionToSelf", transition.canTransitionToSelf);
                changed.Add("canTransitionToSelf");
            }
            return changed;
        }

        /// <summary>
        /// Apply a `conditions: [{parameter, mode, threshold?}, ...]` array if present, replacing any
        /// existing conditions. Falls back to single-condition shape (conditionParameter/Mode/Threshold)
        /// if `conditions` is absent. Returns count of conditions written, or -1 if no conditions block was provided.
        /// </summary>
        private static int ApplyConditions(AnimatorStateTransition transition, ToolParams p, JObject raw)
        {
            var arr = raw["conditions"] as JArray;
            if (arr != null)
            {
                // Wholesale replacement: clear then add.
                while (transition.conditions != null && transition.conditions.Length > 0)
                    transition.RemoveCondition(transition.conditions[0]);
                int added = 0;
                foreach (var c in arr.OfType<JObject>())
                {
                    string parm = c.Value<string>("parameter");
                    string modeRaw = c.Value<string>("mode");
                    if (string.IsNullOrEmpty(parm) || string.IsNullOrEmpty(modeRaw)) continue;
                    if (!Enum.TryParse<AnimatorConditionMode>(modeRaw, ignoreCase: true, out var modeEnum)) continue;
                    float thr = 0f;
                    var thrToken = c["threshold"];
                    if (thrToken != null && thrToken.Type != JTokenType.Null)
                    {
                        float.TryParse(thrToken.ToString(), System.Globalization.NumberStyles.Float,
                            System.Globalization.CultureInfo.InvariantCulture, out thr);
                    }
                    transition.AddCondition(modeEnum, thr, parm);
                    added++;
                }
                return added;
            }

            string singleParam = p.Get("conditionParameter");
            string singleMode = p.Get("conditionMode");
            float? singleThreshold = p.GetFloat("conditionThreshold");
            if (!string.IsNullOrEmpty(singleParam) && !string.IsNullOrEmpty(singleMode))
            {
                if (Enum.TryParse<AnimatorConditionMode>(singleMode, ignoreCase: true, out var modeEnum))
                {
                    transition.AddCondition(modeEnum, singleThreshold ?? 0f, singleParam);
                    return 1;
                }
            }
            return -1;
        }

        // ─── get ─────────────────────────────────────────────────────────────────────

        private static object Get(ToolParams p)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            var layers = ctrl.layers.Select((layer, idx) => DescribeLayer(layer, idx)).ToArray();

            return new SuccessResponse($"AnimatorController '{ctrl.name}' loaded.", new
            {
                controller_path = AssetDatabase.GetAssetPath(ctrl),
                name = ctrl.name,
                layer_count = ctrl.layers.Length,
                parameter_count = ctrl.parameters.Length,
                layers,
                parameters = ctrl.parameters.Select(prm => DescribeParameter(prm)).ToArray(),
            });
        }

        // ─── list_states ─────────────────────────────────────────────────────────────

        private static object ListStates(ToolParams p)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            int layerIndex = p.GetInt("layerIndex", 0) ?? 0;
            if (layerIndex < 0 || layerIndex >= ctrl.layers.Length)
                return new ErrorResponse($"layerIndex {layerIndex} out of range (controller has {ctrl.layers.Length} layers).");

            var layer = ctrl.layers[layerIndex];
            var states = layer.stateMachine?.states ?? Array.Empty<ChildAnimatorState>();
            var output = states.Select(cs => DescribeState(cs.state, layerIndex)).ToArray();

            return new SuccessResponse($"Layer '{layer.name}' has {output.Length} states.", new
            {
                controller_path = AssetDatabase.GetAssetPath(ctrl),
                layer_index = layerIndex,
                layer_name = layer.name,
                state_count = output.Length,
                states = output,
            });
        }

        // ─── list_transitions ────────────────────────────────────────────────────────

        private static object ListTransitions(ToolParams p)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            int layerIndex = p.GetInt("layerIndex", 0) ?? 0;
            string fromStateFilter = p.Get("fromState");
            if (layerIndex < 0 || layerIndex >= ctrl.layers.Length)
                return new ErrorResponse($"layerIndex {layerIndex} out of range.");

            var layer = ctrl.layers[layerIndex];
            var transitions = new List<object>();
            var stateMachineTransitions = new List<object>();

            foreach (var cs in layer.stateMachine?.states ?? Array.Empty<ChildAnimatorState>())
            {
                if (!string.IsNullOrEmpty(fromStateFilter) &&
                    !string.Equals(cs.state.name, fromStateFilter, StringComparison.OrdinalIgnoreCase))
                    continue;

                var trans = cs.state.transitions ?? Array.Empty<AnimatorStateTransition>();
                for (int i = 0; i < trans.Length; i++)
                {
                    transitions.Add(DescribeTransition(trans[i], cs.state.name, i));
                }
            }

            // Any-State transitions (no fromState filter — they're orthogonal to per-state filtering).
            var anyTrans = layer.stateMachine?.anyStateTransitions ?? Array.Empty<AnimatorStateTransition>();
            for (int i = 0; i < anyTrans.Length; i++)
            {
                stateMachineTransitions.Add(DescribeTransition(anyTrans[i], "any_state", i));
            }

            return new SuccessResponse($"Found {transitions.Count} state transitions, {stateMachineTransitions.Count} any-state transitions.", new
            {
                controller_path = AssetDatabase.GetAssetPath(ctrl),
                layer_index = layerIndex,
                layer_name = layer.name,
                from_state_filter = fromStateFilter,
                transition_count = transitions.Count,
                transitions,
                state_machine_transition_count = stateMachineTransitions.Count,
                state_machine_transitions = stateMachineTransitions,
            });
        }

        // ─── list_parameters ─────────────────────────────────────────────────────────

        private static object ListParameters(ToolParams p)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            return new SuccessResponse($"Controller has {ctrl.parameters.Length} parameters.", new
            {
                controller_path = AssetDatabase.GetAssetPath(ctrl),
                parameter_count = ctrl.parameters.Length,
                parameters = ctrl.parameters.Select(prm => DescribeParameter(prm)).ToArray(),
            });
        }

        // ─── list_layers ─────────────────────────────────────────────────────────────

        private static object ListLayers(ToolParams p)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            return new SuccessResponse($"Controller has {ctrl.layers.Length} layers.", new
            {
                controller_path = AssetDatabase.GetAssetPath(ctrl),
                layer_count = ctrl.layers.Length,
                layers = ctrl.layers.Select((layer, idx) => DescribeLayer(layer, idx)).ToArray(),
            });
        }

        // ─── add_parameter (single + batch) ───────────────────────────────────────────

        private static object AddParameter(ToolParams p, JObject raw)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            // Batch shape: parameters: [{name, type, default?}, ...]
            var batch = raw["parameters"] as JArray;
            if (batch != null)
            {
                var added = new List<object>();
                var errors = new List<object>();
                foreach (var item in batch.OfType<JObject>())
                {
                    string name = item.Value<string>("name") ?? item.Value<string>("parameterName");
                    string typeRaw = item.Value<string>("type") ?? item.Value<string>("parameterType");
                    string defaultRaw = item.Value<string>("default") ?? item.Value<string>("defaultValue");
                    var addErr = AddSingleParameter(ctrl, name, typeRaw, defaultRaw);
                    if (addErr != null) errors.Add(new { name, error = addErr });
                    else added.Add(new { name, type = typeRaw });
                }
                EditorUtility.SetDirty(ctrl);
                AssetDatabase.SaveAssetIfDirty(ctrl);
                return new SuccessResponse(
                    $"Batch add_parameter: {added.Count} added, {errors.Count} skipped.",
                    new
                    {
                        controller_path = AssetDatabase.GetAssetPath(ctrl),
                        added_count = added.Count,
                        added,
                        error_count = errors.Count,
                        errors,
                        parameter_count = ctrl.parameters.Length,
                    });
            }

            // Single shape (existing).
            string sName = p.Get("parameterName");
            string sType = p.Get("parameterType");
            string sDefault = p.Get("defaultValue");
            if (string.IsNullOrEmpty(sName) || string.IsNullOrEmpty(sType))
                return new ErrorResponse("parameterName and parameterType required (type: Bool|Float|Int|Trigger), or pass `parameters: [...]` for batch.");

            var singleErr = AddSingleParameter(ctrl, sName, sType, sDefault);
            if (singleErr != null) return new ErrorResponse(singleErr);

            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);
            return new SuccessResponse($"Added parameter '{sName}' ({sType}).", new
            {
                controller_path = AssetDatabase.GetAssetPath(ctrl),
                parameter = new { name = sName, type = sType },
                parameter_count = ctrl.parameters.Length,
            });
        }

        private static string AddSingleParameter(
            UnityEditor.Animations.AnimatorController ctrl, string name, string typeRaw, string defaultRaw)
        {
            if (string.IsNullOrEmpty(name)) return "parameter name is required.";
            if (string.IsNullOrEmpty(typeRaw)) return "parameter type is required.";
            if (!Enum.TryParse<AnimatorControllerParameterType>(typeRaw, ignoreCase: true, out var pType))
                return $"Invalid parameterType '{typeRaw}' (use Bool|Float|Int|Trigger).";
            if (ctrl.parameters.Any(prm => prm.name == name))
                return $"Parameter '{name}' already exists on this controller.";

            ctrl.AddParameter(name, pType);

            if (!string.IsNullOrEmpty(defaultRaw))
            {
                var newParam = ctrl.parameters.LastOrDefault(prm => prm.name == name);
                if (newParam != null)
                {
                    try
                    {
                        if (pType == AnimatorControllerParameterType.Bool)
                            newParam.defaultBool = bool.Parse(defaultRaw);
                        else if (pType == AnimatorControllerParameterType.Float)
                            newParam.defaultFloat = float.Parse(defaultRaw, System.Globalization.CultureInfo.InvariantCulture);
                        else if (pType == AnimatorControllerParameterType.Int)
                            newParam.defaultInt = int.Parse(defaultRaw);
                        // Trigger has no default value field beyond the implicit false.
                    }
                    catch
                    {
                        // Default-value parse failures are non-fatal — the parameter still exists.
                    }
                }
            }

            return null;
        }

        // ─── remove_parameter ────────────────────────────────────────────────────────

        private static object RemoveParameter(ToolParams p)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);
            string name = p.Get("parameterName");
            if (string.IsNullOrEmpty(name)) return new ErrorResponse("parameterName required.");

            int idx = -1;
            for (int i = 0; i < ctrl.parameters.Length; i++)
            {
                if (ctrl.parameters[i].name == name) { idx = i; break; }
            }
            if (idx < 0) return new ErrorResponse($"Parameter '{name}' not found.");

            ctrl.RemoveParameter(idx);
            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);
            return new SuccessResponse($"Removed parameter '{name}'.", new
            {
                controller_path = AssetDatabase.GetAssetPath(ctrl),
                parameter_count = ctrl.parameters.Length,
            });
        }

        // ─── add_state (single + batch) ──────────────────────────────────────────────

        private static object AddState(ToolParams p, JObject raw)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            int layerIndex = p.GetInt("layerIndex", 0) ?? 0;
            if (layerIndex < 0 || layerIndex >= ctrl.layers.Length)
                return new ErrorResponse($"layerIndex {layerIndex} out of range.");
            var layer = ctrl.layers[layerIndex];
            var sm = layer.stateMachine;
            if (sm == null) return new ErrorResponse($"Layer {layerIndex} has no state machine.");

            // Batch shape: states: [{name, clipPath?}, ...]
            var batch = raw["states"] as JArray;
            if (batch != null)
            {
                var added = new List<object>();
                var errors = new List<object>();
                foreach (var item in batch.OfType<JObject>())
                {
                    string name = item.Value<string>("name") ?? item.Value<string>("stateName");
                    string clipPath = item.Value<string>("clipPath");
                    var (newState, addErr) = AddSingleState(sm, name, clipPath);
                    if (addErr != null) errors.Add(new { name, error = addErr });
                    else added.Add(DescribeState(newState, layerIndex));
                }
                EditorUtility.SetDirty(ctrl);
                AssetDatabase.SaveAssetIfDirty(ctrl);
                return new SuccessResponse(
                    $"Batch add_state: {added.Count} added, {errors.Count} skipped.",
                    new
                    {
                        controller_path = AssetDatabase.GetAssetPath(ctrl),
                        layer_index = layerIndex,
                        added_count = added.Count,
                        added,
                        error_count = errors.Count,
                        errors,
                    });
            }

            string sName = p.Get("stateName");
            string sClip = p.Get("clipPath");
            if (string.IsNullOrEmpty(sName)) return new ErrorResponse("stateName required, or pass `states: [...]` for batch.");

            var (single, singleErr) = AddSingleState(sm, sName, sClip);
            if (singleErr != null) return new ErrorResponse(singleErr);

            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);
            return new SuccessResponse($"Added state '{sName}' to layer {layerIndex}.",
                DescribeState(single, layerIndex));
        }

        private static (AnimatorState state, string error) AddSingleState(
            AnimatorStateMachine sm, string stateName, string clipPath)
        {
            if (string.IsNullOrEmpty(stateName)) return (null, "state name is required.");
            if (sm.states.Any(s => s.state.name == stateName))
                return (null, $"State '{stateName}' already exists.");

            var newState = sm.AddState(stateName);
            if (!string.IsNullOrEmpty(clipPath))
            {
                var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
                if (clip != null) newState.motion = clip;
            }
            return (newState, null);
        }

        // ─── remove_state ────────────────────────────────────────────────────────────

        private static object RemoveState(ToolParams p)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            string stateName = p.Get("stateName");
            int layerIndex = p.GetInt("layerIndex", 0) ?? 0;
            if (string.IsNullOrEmpty(stateName)) return new ErrorResponse("stateName required.");
            if (layerIndex < 0 || layerIndex >= ctrl.layers.Length)
                return new ErrorResponse($"layerIndex {layerIndex} out of range.");

            var sm = ctrl.layers[layerIndex].stateMachine;
            var match = sm?.states.FirstOrDefault(s => s.state.name == stateName).state;
            if (match == null) return new ErrorResponse($"State '{stateName}' not found.");

            sm.RemoveState(match);
            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);
            return new SuccessResponse($"Removed state '{stateName}'.", new
            {
                controller_path = AssetDatabase.GetAssetPath(ctrl),
                layer_index = layerIndex,
            });
        }

        // ─── add_transition (extended) ────────────────────────────────────────────────

        private static object AddTransition(ToolParams p, JObject raw)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            string fromName = p.Get("fromState");
            string toName = p.Get("toState");
            int layerIndex = p.GetInt("layerIndex", 0) ?? 0;
            if (string.IsNullOrEmpty(fromName) || string.IsNullOrEmpty(toName))
                return new ErrorResponse("fromState and toState required.");
            if (layerIndex < 0 || layerIndex >= ctrl.layers.Length)
                return new ErrorResponse($"layerIndex {layerIndex} out of range.");

            var sm = ctrl.layers[layerIndex].stateMachine;
            if (sm == null) return new ErrorResponse("Layer has no state machine.");

            var (fromState, _, _) = FindState(sm, fromName, ctrl.layers[layerIndex].name);
            var (toState, _, _) = FindState(sm, toName, ctrl.layers[layerIndex].name);
            if (fromState == null) return new ErrorResponse($"fromState '{fromName}' not found.");
            if (toState == null) return new ErrorResponse($"toState '{toName}' not found.");

            var transition = fromState.AddTransition(toState);

            var changed = ApplyTransitionProperties(transition, p, raw);
            int condCount = ApplyConditions(transition, p, raw);

            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);

            int newIndex = Array.IndexOf(fromState.transitions, transition);
            return new SuccessResponse($"Added transition {fromName} → {toName}.", new
            {
                controller_path = AssetDatabase.GetAssetPath(ctrl),
                layer_index = layerIndex,
                from_state = fromName,
                to_state = toName,
                transition_index = newIndex,
                duration = transition.duration,
                has_exit_time = transition.hasExitTime,
                exit_time = transition.exitTime,
                condition_count = transition.conditions?.Length ?? 0,
                applied_properties = changed,
                conditions_written = condCount,
            });
        }
    }
}
