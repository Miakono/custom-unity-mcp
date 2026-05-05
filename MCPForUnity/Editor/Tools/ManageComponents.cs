using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace MCPForUnity.Editor.Tools
{
    /// <summary>
    /// Tool for managing components on GameObjects.
    /// Actions: add, remove, set_property
    ///
    /// This is a focused tool for component lifecycle operations.
    /// For reading component data, use the unity://scene/gameobject/{id}/components resource.
    ///
    /// Object reference shorthand (UnityEngine.Object-typed fields)
    /// -------------------------------------------------------------
    /// Any property/field on a component that takes a UnityEngine.Object reference
    /// (assets like VisualTreeAsset / Material / Texture / AudioClip / GameObject /
    /// MonoScript, scene-object refs, etc.) accepts the same shorthand as
    /// `manage_scriptable_object` and `apply_scene_patch`. The shared resolver lives
    /// at MCPForUnity/Editor/Helpers/ObjectReferenceResolver.cs. Accepted forms:
    ///
    ///   - bare 32-hex-char GUID string:   "f1e2d3c4a5b6789012345678abcdef01"
    ///   - bare asset path string:         "Assets/UI/LoadingScreen.uxml"
    ///   - GUID object:                    { "guid": "f1e2d3c4..." }
    ///   - path object:                    { "path": "Assets/UI/LoadingScreen.uxml" }
    ///   - instanceID object:              { "instanceID": 12345 }
    ///   - bare integer instanceID:        12345
    ///   - scene-name lookup:              { "name": "Player" }   (manage_components only)
    ///   - explicit ref wrapper:           { "ref": { "guid": "..." } } or { "ref": { "path": "..." } }
    ///   - null:                           clears the reference
    ///
    /// Works in `set_property` for `value`, every entry of `properties`, and inside
    /// `patches[].value`. Same dialect as manage_scriptable_object / apply_scene_patch /
    /// apply_prefab_patch / manage_prefabs.modify_contents.
    /// </summary>
    [McpForUnityTool("manage_components")]
    public static class ManageComponents
    {
        /// <summary>
        /// Handles the manage_components command.
        /// </summary>
        /// <param name="params">
        /// Command parameters. For `set_property`, values for UnityEngine.Object-typed
        /// fields accept the same shorthand as manage_scriptable_object / apply_scene_patch:
        /// bare GUID ("f1e2..."), bare asset path ("Assets/UI/LoadingScreen.uxml"),
        /// {guid:"..."}, {path:"..."}, {instanceID:n}, {name:"..."} (scene lookup),
        /// {ref:{guid|path}}, bare integer instanceID, or null to clear. See the
        /// class-level summary for the full list.
        /// </param>
        /// <returns>Result of the component operation</returns>
        public static object HandleCommand(JObject @params)
        {
            if (@params == null)
            {
                return new ErrorResponse("Parameters cannot be null.");
            }

            string action = ParamCoercion.CoerceString(@params["action"], null)?.ToLowerInvariant();
            if (string.IsNullOrEmpty(action))
            {
                return new ErrorResponse("'action' parameter is required (add, remove, set_property).");
            }

            // Target resolution
            JToken targetToken = @params["target"];
            string searchMethod = ParamCoercion.CoerceString(@params["searchMethod"] ?? @params["search_method"], null);

            if (targetToken == null)
            {
                return new ErrorResponse("'target' parameter is required.");
            }

            try
            {
                return action switch
                {
                    "add" => AddComponent(@params, targetToken, searchMethod),
                    "remove" => RemoveComponent(@params, targetToken, searchMethod),
                    "set_property" => SetProperty(@params, targetToken, searchMethod),
                    _ => new ErrorResponse($"Unknown action: '{action}'. Supported actions: add, remove, set_property")
                };
            }
            catch (Exception e)
            {
                McpLog.Error($"[ManageComponents] Action '{action}' failed: {e}");
                return new ErrorResponse($"Internal error processing action '{action}': {e.Message}");
            }
        }

        #region Action Implementations

        private static object AddComponent(JObject @params, JToken targetToken, string searchMethod)
        {
            GameObject targetGo = FindTarget(targetToken, searchMethod);
            if (targetGo == null)
            {
                return new ErrorResponse($"Target GameObject ('{targetToken}') not found using method '{searchMethod ?? "default"}'.");
            }

            string componentTypeName = ParamCoercion.CoerceString(@params["componentType"] ?? @params["component_type"], null);
            if (string.IsNullOrEmpty(componentTypeName))
            {
                return new ErrorResponse("'componentType' parameter is required for 'add' action.");
            }

            // Resolve component type using unified type resolver
            Type type = UnityTypeResolver.ResolveComponent(componentTypeName);
            if (type == null)
            {
                return new ErrorResponse($"Component type '{componentTypeName}' not found. Use a fully-qualified name if needed.");
            }

            // Use ComponentOps for the actual operation
            Component newComponent = ComponentOps.AddComponent(targetGo, type, out string error);
            if (newComponent == null)
            {
                return new ErrorResponse(error ?? $"Failed to add component '{componentTypeName}'.");
            }

            // When adding VFX-related components (ParticleSystem, LineRenderer, TrailRenderer),
            // ensure the renderer has a material compatible with the active render pipeline.
            // Without this, newly added ParticleSystems in URP/HDRP projects get Unity's default
            // Built-in RP particle material, which renders as magenta.
            EnsureVfxRendererMaterial(targetGo, newComponent);

            // Set properties if provided
            JObject properties = @params["properties"] as JObject ?? @params["componentProperties"] as JObject;
            if (properties != null && properties.HasValues)
            {
                // Record for undo before modifying properties
                Undo.RecordObject(newComponent, "Modify Component Properties");
                SetPropertiesOnComponent(newComponent, properties);
            }

            EditorUtility.SetDirty(targetGo);
            MarkOwningSceneDirty(targetGo);

            return new
            {
                success = true,
                message = $"Component '{componentTypeName}' added to '{targetGo.name}'.",
                data = new
                {
                    instanceID = targetGo.GetInstanceID(),
                    componentType = type.FullName,
                    componentInstanceID = newComponent.GetInstanceID()
                }
            };
        }

        private static object RemoveComponent(JObject @params, JToken targetToken, string searchMethod)
        {
            GameObject targetGo = FindTarget(targetToken, searchMethod);
            if (targetGo == null)
            {
                return new ErrorResponse($"Target GameObject ('{targetToken}') not found using method '{searchMethod ?? "default"}'.");
            }

            string componentTypeName = ParamCoercion.CoerceString(@params["componentType"] ?? @params["component_type"], null);
            if (string.IsNullOrEmpty(componentTypeName))
            {
                return new ErrorResponse("'componentType' parameter is required for 'remove' action.");
            }

            // Resolve component type using unified type resolver
            Type type = UnityTypeResolver.ResolveComponent(componentTypeName);
            if (type == null)
            {
                return new ErrorResponse($"Component type '{componentTypeName}' not found.");
            }

            // Use ComponentOps for the actual operation
            bool removed = ComponentOps.RemoveComponent(targetGo, type, out string error);
            if (!removed)
            {
                return new ErrorResponse(error ?? $"Failed to remove component '{componentTypeName}'.");
            }

            EditorUtility.SetDirty(targetGo);
            MarkOwningSceneDirty(targetGo);

            return new
            {
                success = true,
                message = $"Component '{componentTypeName}' removed from '{targetGo.name}'.",
                data = new
                {
                    instanceID = targetGo.GetInstanceID()
                }
            };
        }

        /// <summary>
        /// Sets one or more properties/fields on a component. Accepts three call shapes:
        /// `property` + `value` (single), `properties` (object map), or `patches`
        /// (SerializedPropertyPatcher dialect — same as apply_scene_patch /
        /// apply_prefab_patch / manage_scriptable_object).
        ///
        /// Any value targeting a UnityEngine.Object-typed field (asset references like
        /// VisualTreeAsset / Material / Texture / AudioClip / Sprite / GameObject /
        /// MonoScript, or scene-object refs) accepts the shared shorthand resolved by
        /// ObjectReferenceResolver — same dialect as `manage_scriptable_object` and
        /// `apply_scene_patch`:
        ///   "f1e2d3c4a5b6789012345678abcdef01"        // bare 32-hex-char GUID
        ///   "Assets/UI/LoadingScreen.uxml"            // bare asset path
        ///   { "guid": "f1e2..." }                     // GUID object
        ///   { "path": "Assets/UI/LoadingScreen.uxml" } // path object
        ///   { "instanceID": 12345 }                   // instanceID object
        ///   12345                                     // bare integer instanceID
        ///   { "name": "Player" }                      // scene-name lookup
        ///   { "ref": { "guid": "..." } } / { "ref": { "path": "..." } }
        ///   null                                      // clears the reference
        ///
        /// Set `confirmReplace: true` to bypass the list-shrink data-loss guard when
        /// replacing a list/array with one whose new size is &lt;50% of the old.
        /// </summary>
        private static object SetProperty(JObject @params, JToken targetToken, string searchMethod)
        {
            GameObject targetGo = FindTarget(targetToken, searchMethod);
            if (targetGo == null)
            {
                return new ErrorResponse($"Target GameObject ('{targetToken}') not found using method '{searchMethod ?? "default"}'.");
            }

            string componentType = ParamCoercion.CoerceString(@params["componentType"] ?? @params["component_type"], null);
            if (string.IsNullOrEmpty(componentType))
            {
                return new ErrorResponse("'componentType' parameter is required for 'set_property' action.");
            }

            // Resolve component type using unified type resolver
            Type type = UnityTypeResolver.ResolveComponent(componentType);
            if (type == null)
            {
                return new ErrorResponse($"Component type '{componentType}' not found.");
            }

            Component component = targetGo.GetComponent(type);
            if (component == null)
            {
                return new ErrorResponse($"Component '{componentType}' not found on '{targetGo.name}'.");
            }

            // Get property and value (existing call shapes)
            string propertyName = ParamCoercion.CoerceString(@params["property"], null);
            JToken valueToken = @params["value"];

            // Support both single property or properties object
            JObject properties = @params["properties"] as JObject;

            // SerializedPropertyPatcher-style patches array — converges this surface with
            // apply_scene_patch / apply_prefab_patch / manage_scriptable_object.
            JArray patches = @params["patches"] as JArray;

            bool hasSingle = !string.IsNullOrEmpty(propertyName) && valueToken != null;
            bool hasBulk = properties != null && properties.HasValues;
            bool hasPatches = patches != null && patches.Count > 0;

            if (!hasSingle && !hasBulk && !hasPatches)
            {
                return new ErrorResponse("Either 'property'+'value', 'properties' object, or 'patches' array is required for 'set_property' action.");
            }

            // Opt-in override for the list-shrink guard. Required to replace a list with a
            // shorter one when the new size is <50% of the old (data-loss protection).
            bool confirmReplace = ParamCoercion.CoerceBool(
                @params["confirmReplace"] ?? @params["confirm_replace"], false);
            var options = new SetPropertyOptions { ConfirmReplace = confirmReplace };

            var errors = new List<object>();

            try
            {
                Undo.RecordObject(component, $"Set property on {componentType}");

                if (hasSingle)
                {
                    AppendErrorIfFailed(errors, propertyName, TrySetProperty(component, propertyName, valueToken, options));
                }

                if (hasBulk)
                {
                    foreach (var prop in properties.Properties())
                    {
                        AppendErrorIfFailed(errors, prop.Name, TrySetProperty(component, prop.Name, prop.Value, options));
                    }
                }

                if (hasPatches)
                {
                    var patchResult = ComponentOps.ApplyPatches(component, patches, options);
                    if (!patchResult.Success)
                    {
                        foreach (var err in patchResult.Errors) errors.Add(err);
                    }
                }

                EditorUtility.SetDirty(component);
                MarkOwningSceneDirty(targetGo);

                if (errors.Count > 0)
                {
                    return new
                    {
                        success = false,
                        message = $"Some properties failed to set on '{componentType}'.",
                        data = new
                        {
                            instanceID = targetGo.GetInstanceID(),
                            errors = errors
                        }
                    };
                }

                return new
                {
                    success = true,
                    message = $"Properties set on component '{componentType}' on '{targetGo.name}'.",
                    data = new
                    {
                        instanceID = targetGo.GetInstanceID()
                    }
                };
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Error setting properties on component '{componentType}': {e.Message}");
            }
        }

        /// <summary>
        /// Appends a structured error entry for a failed property set, tagging known error
        /// codes (e.g. list_shrink_blocked) so callers can branch on them.
        /// </summary>
        private static void AppendErrorIfFailed(List<object> errors, string propertyName, string error)
        {
            if (error == null) return;
            const string ListShrink = "list_shrink_blocked: ";
            if (error.StartsWith(ListShrink, StringComparison.Ordinal))
            {
                errors.Add(new
                {
                    property = propertyName,
                    code = "list_shrink_blocked",
                    message = error.Substring(ListShrink.Length)
                });
            }
            else
            {
                errors.Add(new { property = propertyName, message = error });
            }
        }

        #endregion

        #region Helpers

        /// <summary>
        /// When a VFX-capable component is added (ParticleSystem, LineRenderer, TrailRenderer),
        /// ensures its renderer material is valid for the active render pipeline.
        /// This prevents magenta rendering in URP/HDRP projects where the default built-in
        /// particle/line materials use incompatible shaders.
        /// </summary>
        private static void EnsureVfxRendererMaterial(GameObject go, Component addedComponent)
        {
            Renderer renderer = null;

            if (addedComponent is ParticleSystem ps)
            {
                renderer = go.GetComponent<ParticleSystemRenderer>();

                // Apply sensible defaults so newly added ParticleSystems aren't oversized.
                // These are overridden by any subsequent particle_set_* calls.
                RendererHelpers.SetSensibleParticleDefaults(ps);
            }
            else if (addedComponent is Renderer r)
            {
                // Covers LineRenderer, TrailRenderer, and any other Renderer subclass
                renderer = r;
            }

            if (renderer != null)
            {
                var result = RendererHelpers.EnsureMaterial(renderer);
                if (result.MaterialReplaced)
                {
                    McpLog.Info($"[ManageComponents] Auto-assigned pipeline-compatible material to {renderer.GetType().Name} on '{go.name}' (reason: {result.ReplacementReason}).");
                }
            }
        }

        /// <summary>
        /// Marks the appropriate scene as dirty for the given GameObject.
        /// Handles both regular scenes and prefab stages.
        /// </summary>
        private static void MarkOwningSceneDirty(GameObject targetGo)
        {
            var prefabStage = PrefabStageUtility.GetCurrentPrefabStage();
            if (prefabStage != null)
            {
                EditorSceneManager.MarkSceneDirty(prefabStage.scene);
            }
            else
            {
                EditorSceneManager.MarkSceneDirty(targetGo.scene);
            }
        }

        private static GameObject FindTarget(JToken targetToken, string searchMethod)
        {
            if (targetToken == null)
                return null;

            // Try instance ID first
            if (targetToken.Type == JTokenType.Integer)
            {
                int instanceId = targetToken.Value<int>();
                return GameObjectLookup.FindById(instanceId);
            }

            string targetStr = targetToken.ToString();

            // Try parsing as instance ID
            if (int.TryParse(targetStr, out int parsedId))
            {
                var byId = GameObjectLookup.FindById(parsedId);
                if (byId != null)
                    return byId;
            }

            // Use GameObjectLookup for search
            return GameObjectLookup.FindByTarget(targetToken, searchMethod ?? "by_name", true);
        }

        private static void SetPropertiesOnComponent(Component component, JObject properties)
        {
            if (component == null || properties == null)
                return;

            var errors = new List<string>();
            foreach (var prop in properties.Properties())
            {
                var error = TrySetProperty(component, prop.Name, prop.Value, SetPropertyOptions.Default);
                if (error != null)
                    errors.Add(error);
            }

            if (errors.Count > 0)
            {
                McpLog.Warn($"[ManageComponents] Some properties failed to set on {component.GetType().Name}: {string.Join(", ", errors)}");
            }
        }

        /// <summary>
        /// Attempts to set a property or field on a component.
        /// Delegates to ComponentOps.SetProperty for unified implementation.
        /// </summary>
        private static string TrySetProperty(Component component, string propertyName, JToken value, SetPropertyOptions options)
        {
            if (component == null || string.IsNullOrEmpty(propertyName))
                return "Invalid component or property name";

            if (ComponentOps.SetProperty(component, propertyName, value, options, out string error))
            {
                return null; // Success
            }

            McpLog.Warn($"[ManageComponents] {error}");
            return error;
        }

        #endregion
    }
}
