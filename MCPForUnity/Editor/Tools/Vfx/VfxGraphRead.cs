using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using Newtonsoft.Json.Linq;
using UnityEngine;

#if UNITY_VFX_GRAPH
using UnityEngine.VFX;
#endif

namespace MCPForUnity.Editor.Tools.Vfx
{
    /// <summary>
    /// Read operations for VFX Graph (VisualEffect component).
    /// Requires com.unity.visualeffectgraph package and UNITY_VFX_GRAPH symbol.
    /// </summary>
    internal static class VfxGraphRead
    {
#if !UNITY_VFX_GRAPH
        public static object GetInfo(JObject @params)
        {
            return new { success = false, message = "VFX Graph package (com.unity.visualeffectgraph) not installed" };
        }
#else
        private static object GetMemberValue(object instance, params string[] memberNames)
        {
            if (instance == null || memberNames == null)
            {
                return null;
            }

            Type type = instance.GetType();
            foreach (string memberName in memberNames)
            {
                if (string.IsNullOrEmpty(memberName))
                {
                    continue;
                }

                PropertyInfo property = type.GetProperty(memberName, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.IgnoreCase);
                if (property != null)
                {
                    try
                    {
                        return property.GetValue(instance);
                    }
                    catch
                    {
                        // Ignore reflection failures and continue probing.
                    }
                }

                FieldInfo field = type.GetField(memberName, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.IgnoreCase);
                if (field != null)
                {
                    try
                    {
                        return field.GetValue(instance);
                    }
                    catch
                    {
                        // Ignore reflection failures and continue probing.
                    }
                }
            }

            return null;
        }

        private static string ExtractParameterName(object exposed)
        {
            object name = GetMemberValue(exposed, "name", "Name");
            if (name != null)
            {
                return name.ToString();
            }

            object property = GetMemberValue(exposed, "property", "Property");
            if (property != null)
            {
                object nestedName = GetMemberValue(property, "name", "Name");
                if (nestedName != null)
                {
                    return nestedName.ToString();
                }
            }

            return null;
        }

        private static string ExtractParameterType(object exposed)
        {
            object type = GetMemberValue(exposed, "type", "Type", "valueType", "ValueType");
            if (type == null)
            {
                object property = GetMemberValue(exposed, "property", "Property");
                if (property != null)
                {
                    type = GetMemberValue(property, "type", "Type", "valueType", "ValueType");
                }
            }

            if (type == null)
            {
                return "unknown";
            }

            return type.ToString();
        }

        private static List<object> EnumerateExposedParameters(VisualEffectAsset asset)
        {
            var parameters = new List<object>();
            if (asset == null)
            {
                return parameters;
            }

            try
            {
                Type assetType = asset.GetType();
                MethodInfo method = assetType.GetMethod("GetExposedProperties", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic, null, Type.EmptyTypes, null);

                if (method != null)
                {
                    object result = method.Invoke(asset, null);
                    if (result is IEnumerable enumerable)
                    {
                        foreach (object item in enumerable)
                        {
                            string name = ExtractParameterName(item);
                            if (!string.IsNullOrEmpty(name))
                            {
                                parameters.Add(new
                                {
                                    name,
                                    type = ExtractParameterType(item)
                                });
                            }
                        }
                        if (parameters.Count > 0)
                        {
                            return parameters;
                        }
                    }
                }

                MethodInfo[] methods = assetType.GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
                foreach (MethodInfo candidate in methods)
                {
                    if (!string.Equals(candidate.Name, "GetExposedProperties", StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    ParameterInfo[] candidateParams = candidate.GetParameters();
                    if (candidateParams.Length != 1)
                    {
                        continue;
                    }

                    Type paramType = candidateParams[0].ParameterType;
                    if (!paramType.IsGenericType)
                    {
                        continue;
                    }

                    Type genericDef = paramType.GetGenericTypeDefinition();
                    if (genericDef != typeof(List<>))
                    {
                        continue;
                    }

                    Type itemType = paramType.GetGenericArguments()[0];
                    Type listType = typeof(List<>).MakeGenericType(itemType);
                    object outputList = Activator.CreateInstance(listType);
                    candidate.Invoke(asset, new[] { outputList });

                    if (outputList is IEnumerable outEnumerable)
                    {
                        foreach (object item in outEnumerable)
                        {
                            string name = ExtractParameterName(item);
                            if (!string.IsNullOrEmpty(name))
                            {
                                parameters.Add(new
                                {
                                    name,
                                    type = ExtractParameterType(item)
                                });
                            }
                        }
                    }

                    if (parameters.Count > 0)
                    {
                        break;
                    }
                }
            }
            catch
            {
                // Introspection is best-effort and must never fail the command.
            }

            return parameters;
        }

        public static object GetInfo(JObject @params)
        {
            VisualEffect vfx = VfxGraphCommon.FindVisualEffect(@params);
            if (vfx == null)
            {
                return new { success = false, message = "VisualEffect not found" };
            }

            var exposedParameters = EnumerateExposedParameters(vfx.visualEffectAsset);

            return new
            {
                success = true,
                data = new
                {
                    gameObject = vfx.gameObject.name,
                    assetName = vfx.visualEffectAsset?.name ?? "None",
                    aliveParticleCount = vfx.aliveParticleCount,
                    culled = vfx.culled,
                    pause = vfx.pause,
                    playRate = vfx.playRate,
                    startSeed = vfx.startSeed,
                    exposedParameters,
                    exposedParameterCount = exposedParameters.Count
                }
            };
        }
#endif
    }
}
