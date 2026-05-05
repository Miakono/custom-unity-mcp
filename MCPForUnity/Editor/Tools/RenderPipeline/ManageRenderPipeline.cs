using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace MCPForUnity.Editor.Tools.RenderPipeline
{
    /// <summary>
    /// Render pipeline configuration tool: active pipeline detection, URP renderer features,
    /// Volume profiles, and Volume component overrides.
    ///
    /// Implementation note: all URP-specific access is reflection-based so the MCP package
    /// has no hard asmdef dependency on Unity.RenderPipelines.Universal. Projects without
    /// URP installed get clean "not_available" responses instead of compile errors.
    /// </summary>
    [McpForUnityTool("manage_render_pipeline", AutoRegister = false, Group = "project_config")]
    public static class ManageRenderPipeline
    {
        public static object HandleCommand(JObject @params)
        {
            if (@params == null) return new ErrorResponse("Parameters cannot be null.");

            var p = new ToolParams(@params);
            var actionResult = p.GetRequired("action");
            if (!actionResult.IsSuccess) return new ErrorResponse(actionResult.ErrorMessage);
            string action = actionResult.Value.ToLowerInvariant();

            try
            {
                switch (action)
                {
                    case "get_active":
                        return GetActive();
                    case "list_renderer_features":
                        return ListRendererFeatures(p);
                    case "set_renderer_feature_active":
                        return SetRendererFeatureActive(p);
                    case "list_volume_profiles":
                        return ListVolumeProfiles(p);
                    case "get_volume_profile":
                        return GetVolumeProfile(p);
                    case "set_volume_override":
                        return SetVolumeOverride(p);
                    default:
                        return new ErrorResponse(
                            $"Unknown action '{action}'. Valid: get_active, list_renderer_features, " +
                            "set_renderer_feature_active, list_volume_profiles, get_volume_profile, set_volume_override.");
                }
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"manage_render_pipeline {action} failed: {ex.Message}");
            }
        }

        // ─── get_active ────────────────────────────────────────────────────────────────

        private static object GetActive()
        {
            var asset = GraphicsSettings.currentRenderPipeline;
            if (asset == null)
            {
                return new SuccessResponse("Built-in Render Pipeline is active.", new
                {
                    pipeline = "BuiltIn",
                    asset_path = (string)null,
                    asset_type = (string)null,
                });
            }

            var assetPath = AssetDatabase.GetAssetPath(asset);
            var typeName = asset.GetType().FullName ?? "Unknown";
            string pipeline = "Custom";
            if (typeName.IndexOf("Universal", StringComparison.OrdinalIgnoreCase) >= 0 ||
                typeName.IndexOf("URP", StringComparison.OrdinalIgnoreCase) >= 0)
                pipeline = "Universal";
            else if (typeName.IndexOf("HighDefinition", StringComparison.OrdinalIgnoreCase) >= 0 ||
                     typeName.IndexOf("HDRP", StringComparison.OrdinalIgnoreCase) >= 0)
                pipeline = "HighDefinition";

            // Best-effort: pull a few common URP settings via reflection so callers don't
            // need a separate lookup. Properties that don't exist (e.g. on HDRP) are skipped.
            var settings = new Dictionary<string, object>();
            ReadReflectedProperty(asset, "msaaSampleCount", settings, "msaa_sample_count");
            ReadReflectedProperty(asset, "supportsHDR", settings, "supports_hdr");
            ReadReflectedProperty(asset, "renderScale", settings, "render_scale");
            ReadReflectedProperty(asset, "shadowDistance", settings, "shadow_distance");
            ReadReflectedProperty(asset, "shadowCascadeCount", settings, "shadow_cascade_count");
            ReadReflectedProperty(asset, "supportsMainLightShadows", settings, "supports_main_light_shadows");
            ReadReflectedProperty(asset, "supportsAdditionalLightShadows", settings, "supports_additional_light_shadows");

            return new SuccessResponse($"{pipeline} render pipeline is active.", new
            {
                pipeline,
                asset_path = assetPath,
                asset_type = typeName,
                settings,
            });
        }

        // ─── list_renderer_features ────────────────────────────────────────────────────

        private static object ListRendererFeatures(ToolParams p)
        {
            int rendererIndex = p.GetInt("rendererIndex", 0) ?? 0;
            var (renderer, error) = ResolveDefaultRendererData(rendererIndex);
            if (error != null) return new ErrorResponse(error);

            var featuresList = GetRendererFeaturesList(renderer);
            if (featuresList == null)
            {
                return new ErrorResponse(
                    "Could not access rendererFeatures on the renderer data. URP version may be incompatible.");
            }

            var features = new List<object>();
            int idx = 0;
            foreach (var feat in featuresList)
            {
                features.Add(BuildFeatureDescriptor(feat, idx));
                idx++;
            }

            return new SuccessResponse($"Found {features.Count} renderer features.", new
            {
                renderer_index = rendererIndex,
                renderer_data_path = AssetDatabase.GetAssetPath(renderer as UnityEngine.Object),
                feature_count = features.Count,
                features,
            });
        }

        // ─── set_renderer_feature_active ──────────────────────────────────────────────

        private static object SetRendererFeatureActive(ToolParams p)
        {
            int rendererIndex = p.GetInt("rendererIndex", 0) ?? 0;
            string featureName = p.Get("featureName");
            int? featureIndex = p.GetInt("featureIndex");
            bool? activeOpt = TryGetBool(p, "active");
            if (!activeOpt.HasValue)
                return new ErrorResponse("'active' parameter (bool) is required.");

            var (renderer, error) = ResolveDefaultRendererData(rendererIndex);
            if (error != null) return new ErrorResponse(error);

            var featuresList = GetRendererFeaturesList(renderer);
            if (featuresList == null)
                return new ErrorResponse("Could not access rendererFeatures on the renderer data.");

            object target = null;
            int matchedIndex = -1;
            int idx = 0;
            foreach (var feat in featuresList)
            {
                bool nameMatch = !string.IsNullOrEmpty(featureName) &&
                                 string.Equals((feat as UnityEngine.Object)?.name, featureName, StringComparison.OrdinalIgnoreCase);
                bool indexMatch = featureIndex.HasValue && idx == featureIndex.Value;
                if (nameMatch || indexMatch)
                {
                    target = feat;
                    matchedIndex = idx;
                    break;
                }
                idx++;
            }

            if (target == null)
                return new ErrorResponse(
                    $"Renderer feature not found (name='{featureName}', index={featureIndex}). " +
                    "Use list_renderer_features to discover names/indices.");

            // ScriptableRendererFeature.SetActive(bool) — present in URP 7.x+.
            var setActiveMethod = target.GetType().GetMethod("SetActive",
                BindingFlags.Public | BindingFlags.Instance, null, new[] { typeof(bool) }, null);
            if (setActiveMethod != null)
            {
                setActiveMethod.Invoke(target, new object[] { activeOpt.Value });
            }
            else
            {
                // Fallback: write the 'isActive' field directly.
                var isActiveField = target.GetType().GetField("isActive",
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                isActiveField?.SetValue(target, activeOpt.Value);
            }

            EditorUtility.SetDirty(target as UnityEngine.Object);
            EditorUtility.SetDirty(renderer as UnityEngine.Object);
            AssetDatabase.SaveAssetIfDirty(renderer as UnityEngine.Object);

            return new SuccessResponse(
                $"Renderer feature '{(target as UnityEngine.Object)?.name}' set active={activeOpt.Value}.",
                BuildFeatureDescriptor(target, matchedIndex));
        }

        // ─── list_volume_profiles ─────────────────────────────────────────────────────

        private static object ListVolumeProfiles(ToolParams p)
        {
            string folderFilter = p.Get("folder");
            int maxResults = p.GetInt("maxResults", 100) ?? 100;

            string[] guids = string.IsNullOrEmpty(folderFilter)
                ? AssetDatabase.FindAssets("t:VolumeProfile")
                : AssetDatabase.FindAssets("t:VolumeProfile", new[] { folderFilter });

            var profiles = new List<object>();
            int total = guids.Length;
            int taken = Math.Min(maxResults, total);
            for (int i = 0; i < taken; i++)
            {
                string path = AssetDatabase.GUIDToAssetPath(guids[i]);
                profiles.Add(new
                {
                    path,
                    name = System.IO.Path.GetFileNameWithoutExtension(path),
                });
            }

            return new SuccessResponse($"Found {total} VolumeProfile assets.", new
            {
                total_results = total,
                returned = taken,
                truncated = taken < total,
                profiles,
            });
        }

        // ─── get_volume_profile ───────────────────────────────────────────────────────

        private static object GetVolumeProfile(ToolParams p)
        {
            string path = p.Get("profilePath");
            if (string.IsNullOrEmpty(path))
                return new ErrorResponse("'profilePath' is required (Assets/.../*.asset).");

            var profile = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(path);
            if (profile == null)
                return new ErrorResponse($"VolumeProfile not found at '{path}'.");
            if (!profile.GetType().Name.Equals("VolumeProfile", StringComparison.Ordinal))
                return new ErrorResponse($"Asset at '{path}' is not a VolumeProfile (type={profile.GetType().Name}).");

            // VolumeProfile has a 'components' field listing VolumeComponent instances.
            var componentsField = profile.GetType().GetField("components",
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (componentsField == null)
                return new ErrorResponse("Could not access VolumeProfile.components.");

            var components = componentsField.GetValue(profile) as System.Collections.IList;
            var overrides = new List<object>();
            if (components != null)
            {
                foreach (var comp in components)
                {
                    if (comp == null) continue;
                    overrides.Add(BuildVolumeComponentDescriptor(comp));
                }
            }

            return new SuccessResponse($"VolumeProfile '{path}' has {overrides.Count} components.", new
            {
                profile_path = path,
                component_count = overrides.Count,
                components = overrides,
            });
        }

        // ─── set_volume_override ──────────────────────────────────────────────────────

        private static object SetVolumeOverride(ToolParams p)
        {
            string path = p.Get("profilePath");
            string componentTypeName = p.Get("componentType");
            string parameterName = p.Get("parameterName");
            string valueRaw = p.Get("value");
            bool? overrideStateOpt = TryGetBool(p, "overrideState");

            if (string.IsNullOrEmpty(path) || string.IsNullOrEmpty(componentTypeName) || string.IsNullOrEmpty(parameterName))
                return new ErrorResponse("profilePath, componentType, and parameterName are required.");

            var profile = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(path);
            if (profile == null)
                return new ErrorResponse($"VolumeProfile not found at '{path}'.");

            var componentsField = profile.GetType().GetField("components",
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            var components = componentsField?.GetValue(profile) as System.Collections.IList;
            if (components == null) return new ErrorResponse("VolumeProfile has no components list.");

            object targetComponent = null;
            foreach (var comp in components)
            {
                if (comp == null) continue;
                var t = comp.GetType();
                if (t.Name.Equals(componentTypeName, StringComparison.OrdinalIgnoreCase) ||
                    (t.FullName ?? "").EndsWith(componentTypeName, StringComparison.OrdinalIgnoreCase))
                {
                    targetComponent = comp;
                    break;
                }
            }
            if (targetComponent == null)
                return new ErrorResponse($"VolumeComponent '{componentTypeName}' not found in profile.");

            var paramField = targetComponent.GetType().GetField(parameterName,
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (paramField == null)
                return new ErrorResponse($"Parameter '{parameterName}' not found on '{componentTypeName}'.");

            var paramObj = paramField.GetValue(targetComponent);
            if (paramObj == null) return new ErrorResponse($"Parameter '{parameterName}' is null.");

            // VolumeParameter<T> has a 'value' field and an 'overrideState' bool.
            var valueField = paramObj.GetType().GetField("m_Value",
                BindingFlags.NonPublic | BindingFlags.Instance)
                ?? paramObj.GetType().GetField("value",
                    BindingFlags.Public | BindingFlags.Instance);

            if (valueRaw != null && valueField != null)
            {
                try
                {
                    object coerced = CoerceValueForField(valueRaw, valueField.FieldType);
                    valueField.SetValue(paramObj, coerced);
                }
                catch (Exception ex)
                {
                    return new ErrorResponse($"Could not coerce value '{valueRaw}' to {valueField.FieldType.Name}: {ex.Message}");
                }
            }

            if (overrideStateOpt.HasValue)
            {
                var stateProp = paramObj.GetType().GetProperty("overrideState",
                    BindingFlags.Public | BindingFlags.Instance);
                stateProp?.SetValue(paramObj, overrideStateOpt.Value);
            }

            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssetIfDirty(profile);

            return new SuccessResponse($"Set {componentTypeName}.{parameterName} on '{path}'.", new
            {
                profile_path = path,
                component_type = componentTypeName,
                parameter = parameterName,
                value = valueRaw,
                override_state = overrideStateOpt,
            });
        }

        // ─── helpers ──────────────────────────────────────────────────────────────────

        private static bool? TryGetBool(ToolParams p, string key)
        {
            // ToolParams.GetBool returns a non-nullable with a default; we need to know
            // whether the caller provided the key at all. Inspect the raw token directly.
            var raw = p.GetRaw(key);
            if (raw == null || raw.Type == JTokenType.Null) return null;
            try { return raw.ToObject<bool>(); }
            catch { return null; }
        }

        private static (object renderer, string error) ResolveDefaultRendererData(int rendererIndex)
        {
            var asset = GraphicsSettings.currentRenderPipeline;
            if (asset == null) return (null, "No active render pipeline asset (Built-in is active — no renderer features).");

            // URP exposes m_RendererDataList (private array of ScriptableRendererData)
            var listField = asset.GetType().GetField("m_RendererDataList",
                BindingFlags.NonPublic | BindingFlags.Instance);
            if (listField == null)
                return (null, "Active pipeline isn't URP-compatible (no m_RendererDataList field).");

            var arr = listField.GetValue(asset) as Array;
            if (arr == null || arr.Length == 0)
                return (null, "Render pipeline asset has no renderer data entries.");

            if (rendererIndex < 0 || rendererIndex >= arr.Length)
                return (null, $"rendererIndex {rendererIndex} out of range (asset has {arr.Length} renderers).");

            return (arr.GetValue(rendererIndex), null);
        }

        private static System.Collections.IList GetRendererFeaturesList(object rendererData)
        {
            // ScriptableRendererData.rendererFeatures is a List<ScriptableRendererFeature>
            var prop = rendererData.GetType().GetProperty("rendererFeatures",
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            return prop?.GetValue(rendererData) as System.Collections.IList;
        }

        private static object BuildFeatureDescriptor(object feature, int index)
        {
            var t = feature.GetType();
            var unityObj = feature as UnityEngine.Object;
            bool isActive = true;
            try
            {
                var isActiveProp = t.GetProperty("isActive", BindingFlags.Public | BindingFlags.Instance);
                if (isActiveProp != null) isActive = (bool)isActiveProp.GetValue(feature);
            }
            catch { }

            return new
            {
                index,
                name = unityObj?.name,
                type = t.FullName,
                is_active = isActive,
            };
        }

        private static object BuildVolumeComponentDescriptor(object component)
        {
            var t = component.GetType();
            var activeProp = t.GetProperty("active", BindingFlags.Public | BindingFlags.Instance);
            bool active = true;
            try { if (activeProp != null) active = (bool)activeProp.GetValue(component); } catch { }

            // Enumerate fields that are VolumeParameter<T>; record name + override state for discovery.
            var parameters = new List<object>();
            foreach (var f in t.GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
            {
                var paramObj = f.GetValue(component);
                if (paramObj == null) continue;
                var paramType = paramObj.GetType();
                // VolumeParameter is the base class chain — look for an 'overrideState' property.
                var overrideProp = paramType.GetProperty("overrideState",
                    BindingFlags.Public | BindingFlags.Instance);
                if (overrideProp == null) continue;

                bool overrideState = false;
                try { overrideState = (bool)overrideProp.GetValue(paramObj); } catch { }

                parameters.Add(new
                {
                    name = f.Name,
                    parameter_type = paramType.Name,
                    override_state = overrideState,
                });
            }

            return new
            {
                type = t.FullName,
                short_type = t.Name,
                active,
                parameter_count = parameters.Count,
                parameters,
            };
        }

        private static void ReadReflectedProperty(object obj, string memberName, Dictionary<string, object> dest, string outKey)
        {
            try
            {
                var t = obj.GetType();
                var prop = t.GetProperty(memberName, BindingFlags.Public | BindingFlags.Instance);
                if (prop != null)
                {
                    dest[outKey] = prop.GetValue(obj);
                    return;
                }
                var field = t.GetField(memberName, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if (field != null)
                {
                    dest[outKey] = field.GetValue(obj);
                }
            }
            catch
            {
                // Best-effort introspection — settings missing on this pipeline version are skipped.
            }
        }

        private static object CoerceValueForField(string raw, Type fieldType)
        {
            if (fieldType == typeof(bool)) return bool.Parse(raw);
            if (fieldType == typeof(int)) return int.Parse(raw);
            if (fieldType == typeof(float)) return float.Parse(raw, System.Globalization.CultureInfo.InvariantCulture);
            if (fieldType == typeof(double)) return double.Parse(raw, System.Globalization.CultureInfo.InvariantCulture);
            if (fieldType == typeof(string)) return raw;

            // Color: accept "r,g,b[,a]" comma-separated 0-1 floats
            if (fieldType == typeof(Color))
            {
                var parts = raw.Split(',');
                float r = float.Parse(parts[0], System.Globalization.CultureInfo.InvariantCulture);
                float g = float.Parse(parts[1], System.Globalization.CultureInfo.InvariantCulture);
                float b = float.Parse(parts[2], System.Globalization.CultureInfo.InvariantCulture);
                float a = parts.Length > 3 ? float.Parse(parts[3], System.Globalization.CultureInfo.InvariantCulture) : 1f;
                return new Color(r, g, b, a);
            }
            // Vector3: "x,y,z"
            if (fieldType == typeof(Vector3))
            {
                var parts = raw.Split(',');
                return new Vector3(
                    float.Parse(parts[0], System.Globalization.CultureInfo.InvariantCulture),
                    float.Parse(parts[1], System.Globalization.CultureInfo.InvariantCulture),
                    float.Parse(parts[2], System.Globalization.CultureInfo.InvariantCulture));
            }

            // Enum
            if (fieldType.IsEnum) return Enum.Parse(fieldType, raw, ignoreCase: true);

            // Fallback
            return Convert.ChangeType(raw, fieldType, System.Globalization.CultureInfo.InvariantCulture);
        }
    }
}
