using System.Collections.Generic;
using System.IO;
using System.Linq;
using MCPForUnity.Editor.Tools.AnimatorControllerTool;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace MCPForUnity.Editor.Tests
{
    /// <summary>
    /// Coverage for the gaps the user hit while wiring Stage 2 monster controllers:
    /// default-state assignment, Any-State transition visibility, transition-property writes,
    /// batch parameter/state creation, layer copying, override controllers.
    /// </summary>
    public class AnimatorControllerTests
    {
        private const string TempFolder = "Assets/__McpAnimTests_Temp__";
        private string _ctrlPath;

        [SetUp]
        public void SetUp()
        {
            if (!AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.CreateFolder("Assets", "__McpAnimTests_Temp__");
            }
            _ctrlPath = Path.Combine(TempFolder, "Test.controller").Replace('\\', '/');
            AnimatorController.CreateAnimatorControllerAtPath(_ctrlPath);
        }

        [TearDown]
        public void TearDown()
        {
            if (AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.DeleteAsset(TempFolder);
            }
        }

        // ─── helpers ─────────────────────────────────────────────────────────────────

        private static JObject Call(JObject paramsObj)
        {
            var raw = ManageAnimatorController.HandleCommand(paramsObj);
            return JObject.FromObject(raw);
        }

        private static JObject Build(params (string key, object value)[] kv)
        {
            var o = new JObject();
            foreach (var (k, v) in kv)
            {
                o[k] = v switch
                {
                    JToken jt => jt,
                    null => JValue.CreateNull(),
                    _ => JToken.FromObject(v),
                };
            }
            return o;
        }

        private static AnimatorController Reload(string path)
        {
            return AssetDatabase.LoadAssetAtPath<AnimatorController>(path);
        }

        private static AnimationClip CreateTempClip(string name, string folder)
        {
            var clip = new AnimationClip { name = name };
            string path = Path.Combine(folder, name + ".anim").Replace('\\', '/');
            AssetDatabase.CreateAsset(clip, path);
            AssetDatabase.SaveAssets();
            return AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
        }

        private static AnimatorState AddState(string ctrlPath, int layerIndex, string name)
        {
            var ctrl = Reload(ctrlPath);
            var sm = ctrl.layers[layerIndex].stateMachine;
            var s = sm.AddState(name);
            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssetIfDirty(ctrl);
            return s;
        }

        // ─── 1. set_default_state ────────────────────────────────────────────────────

        [Test]
        public void SetDefaultState_ChangesLayerDefault()
        {
            AddState(_ctrlPath, 0, "Idle");
            AddState(_ctrlPath, 0, "Run");
            // Default is whichever was added first; flip it.
            var resp = Call(Build(
                ("action", "set_default_state"),
                ("controllerPath", _ctrlPath),
                ("layerIndex", 0),
                ("stateName", "Run")));

            Assert.IsTrue((bool)resp["success"], "set_default_state should succeed: " + resp);

            var ctrl = Reload(_ctrlPath);
            Assert.AreEqual("Run", ctrl.layers[0].stateMachine.defaultState.name);
        }

        // ─── 2. get exposes default_state_name ───────────────────────────────────────

        [Test]
        public void Get_IncludesDefaultStateName()
        {
            AddState(_ctrlPath, 0, "Idle");
            AddState(_ctrlPath, 0, "Run");
            // Force a known default to remove ordering ambiguity.
            Call(Build(
                ("action", "set_default_state"),
                ("controllerPath", _ctrlPath),
                ("layerIndex", 0),
                ("stateName", "Idle")));

            var resp = Call(Build(
                ("action", "get"),
                ("controllerPath", _ctrlPath)));

            Assert.IsTrue((bool)resp["success"], resp.ToString());
            var layer0 = resp["data"]["layers"][0];
            Assert.AreEqual("Idle", (string)layer0["default_state_name"]);
            Assert.IsNotNull((string)layer0["default_state_path"]);
        }

        // ─── 3. list_transitions includes Any-State transitions ──────────────────────

        [Test]
        public void ListTransitions_IncludesAnyStateTransitions()
        {
            AddState(_ctrlPath, 0, "Idle");
            AddState(_ctrlPath, 0, "Hit");

            // Any → Hit on a trigger.
            Call(Build(
                ("action", "add_parameter"),
                ("controllerPath", _ctrlPath),
                ("parameterName", "GetHit"),
                ("parameterType", "Trigger")));
            Call(Build(
                ("action", "add_any_state_transition"),
                ("controllerPath", _ctrlPath),
                ("destinationState", "Hit"),
                ("conditions", new JArray
                {
                    new JObject { ["parameter"] = "GetHit", ["mode"] = "If" }
                })));

            var resp = Call(Build(
                ("action", "list_transitions"),
                ("controllerPath", _ctrlPath)));

            Assert.IsTrue((bool)resp["success"], resp.ToString());
            var anyTrans = resp["data"]["state_machine_transitions"] as JArray;
            Assert.IsNotNull(anyTrans);
            Assert.AreEqual(1, anyTrans.Count, "Expected one any-state transition.");
            Assert.AreEqual("any_state", (string)anyTrans[0]["source"]);
            Assert.AreEqual("Hit", (string)anyTrans[0]["to_state"]);
            Assert.AreEqual(1, (int)anyTrans[0]["condition_count"]);
        }

        // ─── 4. add_transition timing ────────────────────────────────────────────────

        [Test]
        public void AddTransition_RespectsTimingProps()
        {
            AddState(_ctrlPath, 0, "Idle");
            AddState(_ctrlPath, 0, "Hit");

            var resp = Call(Build(
                ("action", "add_transition"),
                ("controllerPath", _ctrlPath),
                ("fromState", "Idle"),
                ("toState", "Hit"),
                ("duration", 0.5f),
                ("hasExitTime", true),
                ("exitTime", 0.9f)));

            Assert.IsTrue((bool)resp["success"], resp.ToString());

            var ctrl = Reload(_ctrlPath);
            var idle = ctrl.layers[0].stateMachine.states.First(s => s.state.name == "Idle").state;
            Assert.AreEqual(1, idle.transitions.Length);
            var t = idle.transitions[0];
            Assert.AreEqual(0.5f, t.duration, 0.001f);
            Assert.IsTrue(t.hasExitTime);
            Assert.AreEqual(0.9f, t.exitTime, 0.001f);
        }

        // ─── 5. set_transition_property ──────────────────────────────────────────────

        [Test]
        public void SetTransitionProperty_ModifiesExisting()
        {
            AddState(_ctrlPath, 0, "Idle");
            AddState(_ctrlPath, 0, "Run");

            Call(Build(
                ("action", "add_transition"),
                ("controllerPath", _ctrlPath),
                ("fromState", "Idle"),
                ("toState", "Run")));

            var resp = Call(Build(
                ("action", "set_transition_property"),
                ("controllerPath", _ctrlPath),
                ("fromState", "Idle"),
                ("toState", "Run"),
                ("transitionIndex", 0),
                ("duration", 0.25f),
                ("hasExitTime", true),
                ("exitTime", 0.75f)));

            Assert.IsTrue((bool)resp["success"], resp.ToString());

            var ctrl = Reload(_ctrlPath);
            var idle = ctrl.layers[0].stateMachine.states.First(s => s.state.name == "Idle").state;
            var t = idle.transitions[0];
            Assert.AreEqual(0.25f, t.duration, 0.001f);
            Assert.IsTrue(t.hasExitTime);
            Assert.AreEqual(0.75f, t.exitTime, 0.001f);
        }

        // ─── 6. add_parameter batch ──────────────────────────────────────────────────

        [Test]
        public void AddParameter_BatchCreatesAll()
        {
            var resp = Call(Build(
                ("action", "add_parameter"),
                ("controllerPath", _ctrlPath),
                ("parameters", new JArray
                {
                    new JObject { ["name"] = "Speed", ["type"] = "Float" },
                    new JObject { ["name"] = "IsRunning", ["type"] = "Bool" },
                    new JObject { ["name"] = "GetHit", ["type"] = "Trigger" },
                })));

            Assert.IsTrue((bool)resp["success"], resp.ToString());

            var ctrl = Reload(_ctrlPath);
            Assert.AreEqual(3, ctrl.parameters.Length);
            Assert.IsTrue(ctrl.parameters.Any(p => p.name == "Speed" && p.type == AnimatorControllerParameterType.Float));
            Assert.IsTrue(ctrl.parameters.Any(p => p.name == "IsRunning" && p.type == AnimatorControllerParameterType.Bool));
            Assert.IsTrue(ctrl.parameters.Any(p => p.name == "GetHit" && p.type == AnimatorControllerParameterType.Trigger));
        }

        // ─── 7. add_state batch ──────────────────────────────────────────────────────

        [Test]
        public void AddState_BatchCreatesAll()
        {
            var resp = Call(Build(
                ("action", "add_state"),
                ("controllerPath", _ctrlPath),
                ("states", new JArray
                {
                    new JObject { ["name"] = "Idle" },
                    new JObject { ["name"] = "Run" },
                    new JObject { ["name"] = "Attack" },
                })));

            Assert.IsTrue((bool)resp["success"], resp.ToString());

            var ctrl = Reload(_ctrlPath);
            var sm = ctrl.layers[0].stateMachine;
            Assert.AreEqual(3, sm.states.Length);
            CollectionAssert.AreEquivalent(
                new[] { "Idle", "Run", "Attack" },
                sm.states.Select(s => s.state.name).ToArray());
        }

        // ─── 8. add_any_state_transition ─────────────────────────────────────────────

        [Test]
        public void AddAnyStateTransition_LandsOnAnyStateTransitions()
        {
            AddState(_ctrlPath, 0, "Death");
            Call(Build(
                ("action", "add_parameter"),
                ("controllerPath", _ctrlPath),
                ("parameterName", "Die"),
                ("parameterType", "Trigger")));

            var resp = Call(Build(
                ("action", "add_any_state_transition"),
                ("controllerPath", _ctrlPath),
                ("destinationState", "Death"),
                ("hasExitTime", false),
                ("duration", 0f),
                ("conditions", new JArray
                {
                    new JObject { ["parameter"] = "Die", ["mode"] = "If" }
                })));

            Assert.IsTrue((bool)resp["success"], resp.ToString());

            var ctrl = Reload(_ctrlPath);
            var sm = ctrl.layers[0].stateMachine;
            Assert.AreEqual(1, sm.anyStateTransitions.Length);
            Assert.AreEqual("Death", sm.anyStateTransitions[0].destinationState.name);
            Assert.AreEqual(1, sm.anyStateTransitions[0].conditions.Length);
            Assert.AreEqual("Die", sm.anyStateTransitions[0].conditions[0].parameter);
        }

        // ─── 9. copy_layer_from ──────────────────────────────────────────────────────

        [Test]
        public void CopyLayerFrom_ClonesStatesAndTransitions()
        {
            // Source: 3 states + Idle→Run + Run→Idle + Any→Attack with condition.
            var srcPath = Path.Combine(TempFolder, "Source.controller").Replace('\\', '/');
            AnimatorController.CreateAnimatorControllerAtPath(srcPath);
            Call(Build(
                ("action", "add_parameter"),
                ("controllerPath", srcPath),
                ("parameterName", "Attack"),
                ("parameterType", "Trigger")));
            Call(Build(
                ("action", "add_state"),
                ("controllerPath", srcPath),
                ("states", new JArray
                {
                    new JObject { ["name"] = "Idle" },
                    new JObject { ["name"] = "Run" },
                    new JObject { ["name"] = "Attack" },
                })));
            Call(Build(
                ("action", "add_transition"),
                ("controllerPath", srcPath),
                ("fromState", "Idle"),
                ("toState", "Run")));
            Call(Build(
                ("action", "add_transition"),
                ("controllerPath", srcPath),
                ("fromState", "Run"),
                ("toState", "Idle")));
            Call(Build(
                ("action", "add_any_state_transition"),
                ("controllerPath", srcPath),
                ("destinationState", "Attack"),
                ("conditions", new JArray
                {
                    new JObject { ["parameter"] = "Attack", ["mode"] = "If" }
                })));

            // Target: bare controller (created in SetUp).
            var resp = Call(Build(
                ("action", "copy_layer_from"),
                ("sourceController", srcPath),
                ("targetController", _ctrlPath),
                ("overwrite", true)));

            Assert.IsTrue((bool)resp["success"], resp.ToString());

            var tgt = Reload(_ctrlPath);
            var tgtSm = tgt.layers[0].stateMachine;
            Assert.AreEqual(3, tgtSm.states.Length, "All 3 states should have been cloned.");
            CollectionAssert.AreEquivalent(
                new[] { "Idle", "Run", "Attack" },
                tgtSm.states.Select(s => s.state.name).ToArray());

            int totalStateTransitions = tgtSm.states.Sum(s => s.state.transitions.Length);
            Assert.AreEqual(2, totalStateTransitions, "Expected 2 state→state transitions.");
            Assert.AreEqual(1, tgtSm.anyStateTransitions.Length, "Expected 1 any-state transition.");

            // Parameter should have been copied across.
            Assert.IsTrue(tgt.parameters.Any(p => p.name == "Attack"));

            // Any-state transition condition survived.
            var anyT = tgtSm.anyStateTransitions[0];
            Assert.AreEqual(1, anyT.conditions.Length);
            Assert.AreEqual("Attack", anyT.conditions[0].parameter);
        }

        // ─── 10. override controller round-trip ──────────────────────────────────────

        [Test]
        public void CreateOverride_SetClip_RoundTrips()
        {
            // Base controller with two clip-bearing states.
            var baseClipIdle = CreateTempClip("BaseIdle", TempFolder);
            var baseClipRun = CreateTempClip("BaseRun", TempFolder);

            Call(Build(
                ("action", "add_state"),
                ("controllerPath", _ctrlPath),
                ("states", new JArray
                {
                    new JObject { ["name"] = "Idle", ["clipPath"] = AssetDatabase.GetAssetPath(baseClipIdle) },
                    new JObject { ["name"] = "Run", ["clipPath"] = AssetDatabase.GetAssetPath(baseClipRun) },
                })));

            // Create override.
            var overridePath = Path.Combine(TempFolder, "Test_Override.overrideController").Replace('\\', '/');
            var resp = Call(Build(
                ("action", "create_override"),
                ("outputPath", overridePath),
                ("baseController", _ctrlPath)));
            Assert.IsTrue((bool)resp["success"], resp.ToString());

            // Set Idle override to a different clip.
            var customIdle = CreateTempClip("CustomIdle", TempFolder);
            resp = Call(Build(
                ("action", "set_override_clip"),
                ("overrideControllerPath", overridePath),
                ("originalClipName", "BaseIdle"),
                ("overrideClip", AssetDatabase.GetAssetPath(customIdle))));
            Assert.IsTrue((bool)resp["success"], resp.ToString());

            // Verify via the AOC API directly.
            var aoc = AssetDatabase.LoadAssetAtPath<AnimatorOverrideController>(overridePath);
            Assert.IsNotNull(aoc);
            var pairs = new List<KeyValuePair<AnimationClip, AnimationClip>>();
            aoc.GetOverrides(pairs);

            var idlePair = pairs.FirstOrDefault(kvp => kvp.Key != null && kvp.Key.name == "BaseIdle");
            Assert.IsNotNull(idlePair.Key, "BaseIdle pair missing.");
            Assert.IsNotNull(idlePair.Value, "Override for BaseIdle was not applied.");
            Assert.AreEqual("CustomIdle", idlePair.Value.name);

            // Run pair should still be unset.
            var runPair = pairs.FirstOrDefault(kvp => kvp.Key != null && kvp.Key.name == "BaseRun");
            Assert.IsNotNull(runPair.Key, "BaseRun pair missing.");
            Assert.IsNull(runPair.Value, "BaseRun should NOT have an override yet.");

            // List_overrides reads back the same shape.
            resp = Call(Build(
                ("action", "list_overrides"),
                ("overrideControllerPath", overridePath)));
            Assert.IsTrue((bool)resp["success"], resp.ToString());
            var entries = resp["data"]["overrides"] as JArray;
            Assert.IsNotNull(entries);
            var idleEntry = entries.FirstOrDefault(e => (string)e["original_name"] == "BaseIdle");
            Assert.IsNotNull(idleEntry);
            Assert.IsTrue((bool)idleEntry["has_override"]);
            Assert.AreEqual("CustomIdle", (string)idleEntry["override_name"]);
        }

        // ─── 11. controllers batch ───────────────────────────────────────────────────

        [Test]
        public void AddParameter_ControllerBatch_AppliesToAll()
        {
            var ctrl2Path = Path.Combine(TempFolder, "Test2.controller").Replace('\\', '/');
            AnimatorController.CreateAnimatorControllerAtPath(ctrl2Path);

            var resp = Call(Build(
                ("action", "add_parameter"),
                ("controllers", new JArray { _ctrlPath, ctrl2Path }),
                ("parameterName", "Speed"),
                ("parameterType", "Float")));

            Assert.IsTrue((bool)resp["success"], resp.ToString());
            Assert.AreEqual(2, (int)resp["data"]["success_count"], "Both controllers should succeed.");

            Assert.IsTrue(Reload(_ctrlPath).parameters.Any(p => p.name == "Speed"));
            Assert.IsTrue(Reload(ctrl2Path).parameters.Any(p => p.name == "Speed"));
        }

        // ─── 12. add_layer ───────────────────────────────────────────────────────────

        [Test]
        public void AddLayer_AppendsLayerWithProperties()
        {
            var resp = Call(Build(
                ("action", "add_layer"),
                ("controllerPath", _ctrlPath),
                ("layerName", "Upper Body"),
                ("iKPass", true),
                ("blendingMode", "Additive"),
                ("defaultWeight", 0.5f)));

            Assert.IsTrue((bool)resp["success"], resp.ToString());

            var ctrl = Reload(_ctrlPath);
            Assert.AreEqual(2, ctrl.layers.Length, "Expected base + new layer.");
            Assert.AreEqual("Upper Body", ctrl.layers[1].name);
            Assert.IsTrue(ctrl.layers[1].iKPass, "iKPass did not persist on new layer.");
            Assert.AreEqual(AnimatorLayerBlendingMode.Additive, ctrl.layers[1].blendingMode);
            Assert.AreEqual(0.5f, ctrl.layers[1].defaultWeight, 0.001f);
        }

        // ─── 13. remove_layer ────────────────────────────────────────────────────────

        [Test]
        public void RemoveLayer_ByIndex_RemovesIt()
        {
            Call(Build(
                ("action", "add_layer"),
                ("controllerPath", _ctrlPath),
                ("layerName", "Extra")));
            Assert.AreEqual(2, Reload(_ctrlPath).layers.Length);

            var resp = Call(Build(
                ("action", "remove_layer"),
                ("controllerPath", _ctrlPath),
                ("layerIndex", 1)));

            Assert.IsTrue((bool)resp["success"], resp.ToString());
            Assert.AreEqual(1, Reload(_ctrlPath).layers.Length);
        }

        // ─── 14. remove_layer refuses index 0 without force ──────────────────────────

        [Test]
        public void RemoveLayer_RefusesIndex0_WithoutForce()
        {
            var refused = Call(Build(
                ("action", "remove_layer"),
                ("controllerPath", _ctrlPath),
                ("layerIndex", 0)));
            Assert.IsFalse((bool)refused["success"], "Removing layer 0 without force should fail.");

            var forced = Call(Build(
                ("action", "remove_layer"),
                ("controllerPath", _ctrlPath),
                ("layerIndex", 0),
                ("force", true)));
            Assert.IsTrue((bool)forced["success"], forced.ToString());
            Assert.AreEqual(0, Reload(_ctrlPath).layers.Length);
        }

        // ─── 15. rename_layer ────────────────────────────────────────────────────────

        [Test]
        public void RenameLayer_PersistsName()
        {
            Call(Build(
                ("action", "add_layer"),
                ("controllerPath", _ctrlPath),
                ("layerName", "OldName")));

            var resp = Call(Build(
                ("action", "rename_layer"),
                ("controllerPath", _ctrlPath),
                ("layerIndex", 1),
                ("newLayerName", "NewName")));

            Assert.IsTrue((bool)resp["success"], resp.ToString());
            Assert.AreEqual("NewName", Reload(_ctrlPath).layers[1].name);
        }

        // ─── 16. set_layer_property — IK Pass (struct round-trip critical test) ──────

        [Test]
        public void SetLayerProperty_TogglesIKPassAndWeight()
        {
            var ctrlBefore = Reload(_ctrlPath);
            Assert.IsFalse(ctrlBefore.layers[0].iKPass, "Layer 0 starts with iKPass off.");

            var resp = Call(Build(
                ("action", "set_layer_property"),
                ("controllerPath", _ctrlPath),
                ("layerIndex", 0),
                ("iKPass", true),
                ("defaultWeight", 0.7f)));

            Assert.IsTrue((bool)resp["success"], resp.ToString());

            // Reload from disk to verify the struct round-trip actually persisted.
            var ctrlAfter = Reload(_ctrlPath);
            Assert.IsTrue(ctrlAfter.layers[0].iKPass, "iKPass struct write did not persist.");
            Assert.AreEqual(0.7f, ctrlAfter.layers[0].defaultWeight, 0.001f);
        }

        // ─── 17. set_state_property ──────────────────────────────────────────────────

        [Test]
        public void SetStateProperty_UpdatesSpeedAndIKOnFeet()
        {
            AddState(_ctrlPath, 0, "Idle");

            var resp = Call(Build(
                ("action", "set_state_property"),
                ("controllerPath", _ctrlPath),
                ("layerIndex", 0),
                ("stateName", "Idle"),
                ("speed", 2.0f),
                ("iKOnFeet", true),
                ("tag", "Locomotion")));

            Assert.IsTrue((bool)resp["success"], resp.ToString());

            var ctrl = Reload(_ctrlPath);
            var idle = ctrl.layers[0].stateMachine.states.First(s => s.state.name == "Idle").state;
            Assert.AreEqual(2.0f, idle.speed, 0.001f);
            Assert.IsTrue(idle.iKOnFeet);
            Assert.AreEqual("Locomotion", idle.tag);
        }

        // ─── 18. get exposes layer ik_pass ───────────────────────────────────────────

        [Test]
        public void Get_ExposesLayerIKPass()
        {
            Call(Build(
                ("action", "set_layer_property"),
                ("controllerPath", _ctrlPath),
                ("layerIndex", 0),
                ("iKPass", true)));

            var resp = Call(Build(
                ("action", "get"),
                ("controllerPath", _ctrlPath)));

            Assert.IsTrue((bool)resp["success"], resp.ToString());
            var layer0 = resp["data"]["layers"][0];
            Assert.IsTrue((bool)layer0["ik_pass"], "get did not expose ik_pass.");
            Assert.AreEqual(-1, (int)layer0["synced_layer_index"]);
        }
    }
}
