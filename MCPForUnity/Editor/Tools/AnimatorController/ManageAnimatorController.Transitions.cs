using System;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Animations;

namespace MCPForUnity.Editor.Tools.AnimatorControllerTool
{
    /// <summary>
    /// Transition-scoped operations: editing properties on existing transitions, and adding
    /// transitions onto the layer's state-machine "Any State" node.
    /// </summary>
    public static partial class ManageAnimatorController
    {
        // ─── set_transition_property ─────────────────────────────────────────────────

        private static object SetTransitionProperty(ToolParams p, JObject raw)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            int layerIndex = p.GetInt("layerIndex", 0) ?? 0;
            if (layerIndex < 0 || layerIndex >= ctrl.layers.Length)
                return new ErrorResponse($"layerIndex {layerIndex} out of range.");

            string fromName = p.Get("fromState");
            string toName = p.Get("toState");
            int transitionIndex = p.GetInt("transitionIndex", 0) ?? 0;
            if (string.IsNullOrEmpty(toName)) return new ErrorResponse("toState required.");

            var sm = ctrl.layers[layerIndex].stateMachine;
            if (sm == null) return new ErrorResponse("Layer has no state machine.");

            AnimatorStateTransition transition = null;
            string source;

            bool isAnyState = string.IsNullOrEmpty(fromName)
                           || string.Equals(fromName, "any_state", StringComparison.OrdinalIgnoreCase)
                           || string.Equals(fromName, "AnyState", StringComparison.OrdinalIgnoreCase);

            if (isAnyState)
            {
                // Lookup on anyStateTransitions, filtered by destination + index among matches.
                var matches = (sm.anyStateTransitions ?? Array.Empty<AnimatorStateTransition>())
                    .Where(t => t.destinationState != null && t.destinationState.name == toName)
                    .ToArray();
                if (matches.Length == 0)
                    return new ErrorResponse($"No any-state transition to '{toName}' found on layer {layerIndex}.");
                if (transitionIndex < 0 || transitionIndex >= matches.Length)
                    return new ErrorResponse($"transitionIndex {transitionIndex} out of range (found {matches.Length} matching any-state transitions).");
                transition = matches[transitionIndex];
                source = "any_state";
            }
            else
            {
                var (fromState, _, _) = FindState(sm, fromName, ctrl.layers[layerIndex].name);
                if (fromState == null) return new ErrorResponse($"fromState '{fromName}' not found.");
                var matches = (fromState.transitions ?? Array.Empty<AnimatorStateTransition>())
                    .Where(t => t.destinationState != null && t.destinationState.name == toName)
                    .ToArray();
                if (matches.Length == 0)
                    return new ErrorResponse($"No transition '{fromName}' → '{toName}' found.");
                if (transitionIndex < 0 || transitionIndex >= matches.Length)
                    return new ErrorResponse($"transitionIndex {transitionIndex} out of range (found {matches.Length} matching transitions).");
                transition = matches[transitionIndex];
                source = fromName;
            }

            var changed = ApplyTransitionProperties(transition, p, raw);
            int condCount = ApplyConditions(transition, p, raw);

            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);

            return new SuccessResponse(
                $"Updated transition {source} → {toName} (index {transitionIndex}).",
                new
                {
                    controller_path = AssetDatabase.GetAssetPath(ctrl),
                    layer_index = layerIndex,
                    source,
                    to_state = toName,
                    transition_index = transitionIndex,
                    applied_properties = changed,
                    conditions_written = condCount,
                    duration = transition.duration,
                    has_exit_time = transition.hasExitTime,
                    exit_time = transition.exitTime,
                });
        }

        // ─── add_any_state_transition ────────────────────────────────────────────────

        private static object AddAnyStateTransition(ToolParams p, JObject raw)
        {
            var (ctrl, err) = LoadController(p);
            if (err != null) return new ErrorResponse(err);

            int layerIndex = p.GetInt("layerIndex", 0) ?? 0;
            if (layerIndex < 0 || layerIndex >= ctrl.layers.Length)
                return new ErrorResponse($"layerIndex {layerIndex} out of range.");

            string toName = p.Get("destinationState") ?? p.Get("toState");
            if (string.IsNullOrEmpty(toName))
                return new ErrorResponse("destinationState (or toState) required.");

            var sm = ctrl.layers[layerIndex].stateMachine;
            if (sm == null) return new ErrorResponse("Layer has no state machine.");

            var (toState, _, _) = FindState(sm, toName, ctrl.layers[layerIndex].name);
            if (toState == null) return new ErrorResponse($"destinationState '{toName}' not found.");

            var transition = sm.AddAnyStateTransition(toState);

            var changed = ApplyTransitionProperties(transition, p, raw);
            int condCount = ApplyConditions(transition, p, raw);

            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);

            int newIndex = Array.IndexOf(sm.anyStateTransitions, transition);
            return new SuccessResponse(
                $"Added any-state transition → {toName}.",
                new
                {
                    controller_path = AssetDatabase.GetAssetPath(ctrl),
                    layer_index = layerIndex,
                    source = "any_state",
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
