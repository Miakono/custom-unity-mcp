#nullable disable
using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace MCPForUnity.Editor.Tools.Spatial
{
    /// <summary>
    /// Handles advanced transform operations for GameObjects including world/local space queries,
    /// bounds retrieval, grid snapping, alignment, distribution, and placement validation.
    /// Part of the 'spatial' tool group.
    /// </summary>
    [McpForUnityTool("manage_transform", AutoRegister = false, Group = "spatial")]
    public static class ManageTransform
    {
        public static object HandleCommand(JObject @params)
        {
            if (@params == null)
            {
                return new ErrorResponse("Parameters cannot be null.");
            }

            string action = @params["action"]?.ToString().ToLower();
            if (string.IsNullOrEmpty(action))
            {
                return new ErrorResponse("Action parameter is required.");
            }

            // Get target GameObject (or use selected if not specified)
            JToken targetToken = @params["target"];
            string searchMethod = @params["searchMethod"]?.ToString().ToLower();

            GameObject targetGo = null;
            if (targetToken != null)
            {
                targetGo = FindGameObject(targetToken, searchMethod);
                if (targetGo == null)
                {
                    return new ErrorResponse($"Target GameObject '{targetToken}' not found.");
                }
            }
            else
            {
                // Use current selection if available
                if (Selection.activeGameObject != null)
                {
                    targetGo = Selection.activeGameObject;
                }
                else
                {
                    return new ErrorResponse("No target specified and no GameObject selected.");
                }
            }

            try
            {
                switch (action)
                {
                    case "get_world_transform":
                        return GetWorldTransform(targetGo);
                    case "get_local_transform":
                        return GetLocalTransform(targetGo);
                    case "set_world_transform":
                        return SetWorldTransform(targetGo, @params);
                    case "set_local_transform":
                        return SetLocalTransform(targetGo, @params);
                    case "get_bounds":
                        return GetBounds(targetGo);
                    case "snap_to_grid":
                        return SnapToGrid(targetGo, @params);
                    case "align_to_object":
                        return AlignToObject(targetGo, @params);
                    case "distribute_objects":
                        return DistributeObjects(@params);
                    case "place_relative":
                        return PlaceRelative(targetGo, @params);
                    case "validate_placement":
                        return ValidatePlacement(targetGo, @params);

                    default:
                        return new ErrorResponse($"Unknown action: '{action}'. Valid actions: get_world_transform, get_local_transform, set_world_transform, set_local_transform, get_bounds, snap_to_grid, align_to_object, distribute_objects, place_relative, validate_placement");
                }
            }
            catch (Exception e)
            {
                McpLog.Error($"[ManageTransform] Action '{action}' failed: {e}");
                return new ErrorResponse($"Internal error processing action '{action}': {e.Message}");
            }
        }

        private static GameObject FindGameObject(JToken targetToken, string searchMethod)
        {
            if (targetToken.Type == JTokenType.Integer)
            {
                int instanceId = targetToken.ToObject<int>();
                return GameObjectLookup.FindById(instanceId);
            }

            string targetStr = targetToken.ToString();
            if (targetStr == "selected")
            {
                return Selection.activeGameObject;
            }

            var results = GameObjectLookup.SearchGameObjects(searchMethod, targetStr, true, 1);
            return results.Count > 0 ? GameObjectLookup.FindById(results[0]) : null;
        }

        private static object GetWorldTransform(GameObject go)
        {
            var t = go.transform;
            var data = new
            {
                instanceId = go.GetInstanceID(),
                name = go.name,
                position = new[] { t.position.x, t.position.y, t.position.z },
                rotation = new[] { t.eulerAngles.x, t.eulerAngles.y, t.eulerAngles.z },
                scale = new[] { t.lossyScale.x, t.lossyScale.y, t.lossyScale.z },
                space = "world"
            };

            return new SuccessResponse($"World transform for '{go.name}' retrieved.", data);
        }

        private static object GetLocalTransform(GameObject go)
        {
            var t = go.transform;
            var data = new
            {
                instanceId = go.GetInstanceID(),
                name = go.name,
                position = new[] { t.localPosition.x, t.localPosition.y, t.localPosition.z },
                rotation = new[] { t.localEulerAngles.x, t.localEulerAngles.y, t.localEulerAngles.z },
                scale = new[] { t.localScale.x, t.localScale.y, t.localScale.z },
                parent = t.parent?.name,
                space = "local"
            };

            return new SuccessResponse($"Local transform for '{go.name}' retrieved.", data);
        }

        private static object SetWorldTransform(GameObject go, JObject @params)
        {
            Vector3? position = VectorParsing.ParseVector3(@params["position"]);
            Vector3? rotation = VectorParsing.ParseVector3(@params["rotation"]);
            Vector3? scale = VectorParsing.ParseVector3(@params["scale"]);

            Undo.RecordObject(go.transform, "Set World Transform");

            var t = go.transform;
            if (position.HasValue) t.position = position.Value;
            if (rotation.HasValue) t.rotation = Quaternion.Euler(rotation.Value);
            if (scale.HasValue)
            {
                // World scale is read-only in Unity, so we warn if user tries to set it
                return new ErrorResponse("Cannot set world scale directly. Use set_local_transform with scale parameter, or modify the object's transform hierarchy.");
            }

            EditorUtility.SetDirty(go);

            var data = new
            {
                position = new[] { t.position.x, t.position.y, t.position.z },
                rotation = new[] { t.eulerAngles.x, t.eulerAngles.y, t.eulerAngles.z }
            };

            return new SuccessResponse($"World transform updated for '{go.name}'.", data);
        }

        private static object SetLocalTransform(GameObject go, JObject @params)
        {
            Vector3? position = VectorParsing.ParseVector3(@params["position"]);
            Vector3? rotation = VectorParsing.ParseVector3(@params["rotation"]);
            Vector3? scale = VectorParsing.ParseVector3(@params["scale"]);

            Undo.RecordObject(go.transform, "Set Local Transform");

            var t = go.transform;
            if (position.HasValue) t.localPosition = position.Value;
            if (rotation.HasValue) t.localEulerAngles = rotation.Value;
            if (scale.HasValue) t.localScale = scale.Value;

            EditorUtility.SetDirty(go);

            var data = new
            {
                position = new[] { t.localPosition.x, t.localPosition.y, t.localPosition.z },
                rotation = new[] { t.localEulerAngles.x, t.localEulerAngles.y, t.localEulerAngles.z },
                scale = new[] { t.localScale.x, t.localScale.y, t.localScale.z }
            };

            return new SuccessResponse($"Local transform updated for '{go.name}'.", data);
        }

        private static object GetBounds(GameObject go)
        {
            var renderers = go.GetComponentsInChildren<Renderer>(true);
            var colliders = go.GetComponentsInChildren<Collider>(true);

            if (renderers.Length == 0 && colliders.Length == 0)
            {
                // Return bounds based on transform only
                var data = new
                {
                    hasRenderer = false,
                    hasCollider = false,
                    center = new[] { go.transform.position.x, go.transform.position.y, go.transform.position.z },
                    extents = new[] { 0f, 0f, 0f },
                    size = new[] { 0f, 0f, 0f },
                    min = new[] { go.transform.position.x, go.transform.position.y, go.transform.position.z },
                    max = new[] { go.transform.position.x, go.transform.position.y, go.transform.position.z }
                };
                return new SuccessResponse($"No renderer or collider found for '{go.name}'. Returning pivot position.", data);
            }

            Bounds bounds = new Bounds(go.transform.position, Vector3.zero);
            bool hasBounds = false;

            foreach (var renderer in renderers)
            {
                if (!hasBounds)
                {
                    bounds = renderer.bounds;
                    hasBounds = true;
                }
                else
                {
                    bounds.Encapsulate(renderer.bounds);
                }
            }

            foreach (var collider in colliders)
            {
                if (!hasBounds)
                {
                    bounds = collider.bounds;
                    hasBounds = true;
                }
                else
                {
                    bounds.Encapsulate(collider.bounds);
                }
            }

            var boundsData = new
            {
                hasRenderer = renderers.Length > 0,
                rendererCount = renderers.Length,
                hasCollider = colliders.Length > 0,
                colliderCount = colliders.Length,
                center = new[] { bounds.center.x, bounds.center.y, bounds.center.z },
                extents = new[] { bounds.extents.x, bounds.extents.y, bounds.extents.z },
                size = new[] { bounds.size.x, bounds.size.y, bounds.size.z },
                min = new[] { bounds.min.x, bounds.min.y, bounds.min.z },
                max = new[] { bounds.max.x, bounds.max.y, bounds.max.z }
            };

            return new SuccessResponse($"Bounds retrieved for '{go.name}'.", boundsData);
        }

        private static object SnapToGrid(GameObject go, JObject @params)
        {
            float gridSize = @params["gridSize"]?.ToObject<float>() ?? 1.0f;
            bool snapPosition = @params["snapPosition"]?.ToObject<bool>() ?? true;
            bool snapRotation = @params["snapRotation"]?.ToObject<bool>() ?? false;

            Undo.RecordObject(go.transform, "Snap to Grid");

            var t = go.transform;

            if (snapPosition)
            {
                Vector3 snappedPos = new Vector3(
                    Mathf.Round(t.position.x / gridSize) * gridSize,
                    Mathf.Round(t.position.y / gridSize) * gridSize,
                    Mathf.Round(t.position.z / gridSize) * gridSize
                );
                t.position = snappedPos;
            }

            if (snapRotation)
            {
                Vector3 snappedRot = new Vector3(
                    Mathf.Round(t.eulerAngles.x / 90f) * 90f,
                    Mathf.Round(t.eulerAngles.y / 90f) * 90f,
                    Mathf.Round(t.eulerAngles.z / 90f) * 90f
                );
                t.rotation = Quaternion.Euler(snappedRot);
            }

            EditorUtility.SetDirty(go);

            var data = new
            {
                gridSize,
                snappedPosition = new[] { t.position.x, t.position.y, t.position.z },
                snappedRotation = new[] { t.eulerAngles.x, t.eulerAngles.y, t.eulerAngles.z }
            };

            return new SuccessResponse($"'{go.name}' snapped to grid (size: {gridSize}).", data);
        }

        private static object AlignToObject(GameObject go, JObject @params)
        {
            string referenceId = @params["referenceObject"]?.ToString();
            if (string.IsNullOrEmpty(referenceId))
            {
                return new ErrorResponse("referenceObject parameter is required for align_to_object.");
            }

            string searchMethod = @params["searchMethod"]?.ToString().ToLower();
            GameObject referenceGo = FindGameObject(referenceId, searchMethod);
            if (referenceGo == null)
            {
                return new ErrorResponse($"Reference object '{referenceId}' not found.");
            }

            string alignAxis = @params["alignAxis"]?.ToString().ToLower() ?? "all";
            string alignMode = @params["alignMode"]?.ToString().ToLower() ?? "center";

            Undo.RecordObject(go.transform, "Align to Object");

            Vector3 targetPos = CalculateAlignPosition(go, referenceGo, alignAxis, alignMode);
            go.transform.position = targetPos;

            EditorUtility.SetDirty(go);

            var data = new
            {
                alignedTo = referenceGo.name,
                alignAxis,
                alignMode,
                newPosition = new[] { go.transform.position.x, go.transform.position.y, go.transform.position.z }
            };

            return new SuccessResponse($"'{go.name}' aligned to '{referenceGo.name}' ({alignAxis} axis, {alignMode} mode).", data);
        }

        private static Vector3 CalculateAlignPosition(GameObject source, GameObject target, string axis, string mode)
        {
            Bounds sourceBounds = CalculateBounds(source);
            Bounds targetBounds = CalculateBounds(target);

            Vector3 newPos = source.transform.position;

            if (mode == "pivot")
            {
                // Align pivots
                if (axis == "all" || axis == "x") newPos.x = target.transform.position.x;
                if (axis == "all" || axis == "y") newPos.y = target.transform.position.y;
                if (axis == "all" || axis == "z") newPos.z = target.transform.position.z;
            }
            else if (mode == "center")
            {
                // Align centers
                if (axis == "all" || axis == "x") newPos.x = targetBounds.center.x + (newPos.x - sourceBounds.center.x);
                if (axis == "all" || axis == "y") newPos.y = targetBounds.center.y + (newPos.y - sourceBounds.center.y);
                if (axis == "all" || axis == "z") newPos.z = targetBounds.center.z + (newPos.z - sourceBounds.center.z);
            }
            else if (mode == "min")
            {
                // Align min bounds
                if (axis == "all" || axis == "x") newPos.x = targetBounds.min.x + (newPos.x - sourceBounds.min.x);
                if (axis == "all" || axis == "y") newPos.y = targetBounds.min.y + (newPos.y - sourceBounds.min.y);
                if (axis == "all" || axis == "z") newPos.z = targetBounds.min.z + (newPos.z - sourceBounds.min.z);
            }
            else if (mode == "max")
            {
                // Align max bounds
                if (axis == "all" || axis == "x") newPos.x = targetBounds.max.x - (sourceBounds.max.x - newPos.x);
                if (axis == "all" || axis == "y") newPos.y = targetBounds.max.y - (sourceBounds.max.y - newPos.y);
                if (axis == "all" || axis == "z") newPos.z = targetBounds.max.z - (sourceBounds.max.z - newPos.z);
            }

            return newPos;
        }

        private static Bounds CalculateBounds(GameObject go)
        {
            var renderers = go.GetComponentsInChildren<Renderer>(true);
            var colliders = go.GetComponentsInChildren<Collider>(true);

            Bounds bounds = new Bounds(go.transform.position, Vector3.zero);
            bool hasBounds = false;

            foreach (var renderer in renderers)
            {
                if (!hasBounds)
                {
                    bounds = renderer.bounds;
                    hasBounds = true;
                }
                else
                {
                    bounds.Encapsulate(renderer.bounds);
                }
            }

            foreach (var collider in colliders)
            {
                if (!hasBounds)
                {
                    bounds = collider.bounds;
                    hasBounds = true;
                }
                else
                {
                    bounds.Encapsulate(collider.bounds);
                }
            }

            // If no bounds found, use a point at the transform position
            if (!hasBounds)
            {
                bounds = new Bounds(go.transform.position, Vector3.zero);
            }

            return bounds;
        }

        private static object DistributeObjects(JObject @params)
        {
            JArray targetsArray = @params["targets"] as JArray;
            if (targetsArray == null || targetsArray.Count < 2)
            {
                return new ErrorResponse("At least 2 target objects are required for distribute_objects.");
            }

            string searchMethod = @params["searchMethod"]?.ToString().ToLower();
            string distributeAxis = @params["distributeAxis"]?.ToString().ToLower() ?? "x";
            float? distributeSpacing = @params["distributeSpacing"]?.ToObject<float?>();

            // Resolve all target objects
            List<GameObject> objects = new List<GameObject>();
            foreach (var token in targetsArray)
            {
                GameObject go = FindGameObject(token, searchMethod);
                if (go == null)
                {
                    return new ErrorResponse($"Target object '{token}' not found.");
                }
                objects.Add(go);
            }

            // Sort objects by position along the distribution axis
            int axisIndex = distributeAxis switch
            {
                "x" => 0,
                "y" => 1,
                "z" => 2,
                _ => 0
            };

            objects.Sort((a, b) =>
            {
                float posA = axisIndex == 0 ? a.transform.position.x : axisIndex == 1 ? a.transform.position.y : a.transform.position.z;
                float posB = axisIndex == 0 ? b.transform.position.x : axisIndex == 1 ? b.transform.position.y : b.transform.position.z;
                return posA.CompareTo(posB);
            });

            // Calculate positions
            float startPos, endPos, spacing;
            if (distributeSpacing.HasValue)
            {
                spacing = distributeSpacing.Value;
                startPos = axisIndex == 0 ? objects[0].transform.position.x :
                          axisIndex == 1 ? objects[0].transform.position.y : objects[0].transform.position.z;
            }
            else
            {
                // Auto-calculate spacing based on first and last object
                startPos = axisIndex == 0 ? objects[0].transform.position.x :
                          axisIndex == 1 ? objects[0].transform.position.y : objects[0].transform.position.z;
                endPos = axisIndex == 0 ? objects[objects.Count - 1].transform.position.x :
                        axisIndex == 1 ? objects[objects.Count - 1].transform.position.y : objects[objects.Count - 1].transform.position.z;
                spacing = (endPos - startPos) / (objects.Count - 1);
            }

            // Record undos and apply positions
            Undo.SetCurrentGroupName("Distribute Objects");
            int undoGroup = Undo.GetCurrentGroup();

            for (int i = 0; i < objects.Count; i++)
            {
                Undo.RecordObject(objects[i].transform, $"Distribute {objects[i].name}");
                Vector3 pos = objects[i].transform.position;
                float newPos = startPos + (i * spacing);

                if (axisIndex == 0) pos.x = newPos;
                else if (axisIndex == 1) pos.y = newPos;
                else pos.z = newPos;

                objects[i].transform.position = pos;
                EditorUtility.SetDirty(objects[i]);
            }

            Undo.CollapseUndoOperations(undoGroup);

            var data = new
            {
                objectCount = objects.Count,
                distributeAxis,
                spacing,
                objects = objects.Select(go => new { instanceId = go.GetInstanceID(), name = go.name }).ToArray()
            };

            return new SuccessResponse($"Distributed {objects.Count} objects along {distributeAxis} axis (spacing: {spacing:F3}).", data);
        }

        private static object PlaceRelative(GameObject go, JObject @params)
        {
            string referenceId = @params["referenceObject"]?.ToString();
            if (string.IsNullOrEmpty(referenceId))
            {
                return new ErrorResponse("referenceObject parameter is required for place_relative.");
            }

            string searchMethod = @params["searchMethod"]?.ToString().ToLower();
            GameObject referenceGo = FindGameObject(referenceId, searchMethod);
            if (referenceGo == null)
            {
                return new ErrorResponse($"Reference object '{referenceId}' not found.");
            }

            Vector3? offset = VectorParsing.ParseVector3(@params["offset"]);
            string direction = @params["direction"]?.ToString().ToLower();
            float distance = @params["distance"]?.ToObject<float>() ?? 1.0f;
            bool useWorldSpace = @params["useWorldSpace"]?.ToObject<bool>() ?? true;

            Undo.RecordObject(go.transform, "Place Relative");

            Vector3 newPosition;
            Transform referenceTransform = referenceGo.transform;

            if (offset.HasValue)
            {
                // Use explicit offset
                if (useWorldSpace)
                {
                    newPosition = referenceTransform.position + offset.Value;
                }
                else
                {
                    newPosition = referenceTransform.TransformPoint(offset.Value);
                }
            }
            else if (!string.IsNullOrEmpty(direction))
            {
                // Use direction and distance
                Vector3 dir = ParseDirection(direction, useWorldSpace ? null : referenceTransform);
                newPosition = referenceTransform.position + dir * distance;
            }
            else
            {
                return new ErrorResponse("Either 'offset' or 'direction' parameter is required for place_relative.");
            }

            go.transform.position = newPosition;
            EditorUtility.SetDirty(go);

            var data = new
            {
                referenceObject = referenceGo.name,
                newPosition = new[] { go.transform.position.x, go.transform.position.y, go.transform.position.z },
                relativeTo = referenceTransform.position,
                useWorldSpace
            };

            return new SuccessResponse($"'{go.name}' placed relative to '{referenceGo.name}'.", data);
        }

        private static Vector3 ParseDirection(string direction, Transform localSpace)
        {
            Vector3 worldDir = direction switch
            {
                "left" => Vector3.left,
                "right" => Vector3.right,
                "up" => Vector3.up,
                "down" => Vector3.down,
                "forward" or "front" => Vector3.forward,
                "back" or "backward" or "behind" => Vector3.back,
                "above" => Vector3.up,
                "below" => Vector3.down,
                "north" => Vector3.forward,
                "south" => Vector3.back,
                "east" => Vector3.right,
                "west" => Vector3.left,
                _ => Vector3.forward
            };

            if (localSpace != null)
            {
                return localSpace.TransformDirection(worldDir);
            }

            return worldDir;
        }

        private static object ValidatePlacement(GameObject go, JObject @params)
        {
            bool checkOverlap = @params["checkOverlap"]?.ToObject<bool>() ?? true;
            bool checkOffGrid = @params["checkOffGrid"]?.ToObject<bool>() ?? true;
            bool checkInvalidScale = @params["checkInvalidScale"]?.ToObject<bool>() ?? true;
            float minSpacing = @params["minSpacing"]?.ToObject<float>() ?? 0f;

            var issues = new List<string>();
            var warnings = new List<string>();

            // Check off-grid
            if (checkOffGrid)
            {
                float gridSize = 1.0f; // Default grid size
                Vector3 pos = go.transform.position;
                bool onGridX = Mathf.Abs(pos.x % gridSize) < 0.001f || Mathf.Abs(pos.x % gridSize - gridSize) < 0.001f;
                bool onGridY = Mathf.Abs(pos.y % gridSize) < 0.001f || Mathf.Abs(pos.y % gridSize - gridSize) < 0.001f;
                bool onGridZ = Mathf.Abs(pos.z % gridSize) < 0.001f || Mathf.Abs(pos.z % gridSize - gridSize) < 0.001f;

                if (!onGridX || !onGridY || !onGridZ)
                {
                    warnings.Add($"Object is not aligned to {gridSize} unit grid");
                }
            }

            // Check invalid scale
            if (checkInvalidScale)
            {
                Vector3 scale = go.transform.localScale;
                if (scale.x <= 0 || scale.y <= 0 || scale.z <= 0)
                {
                    issues.Add("Object has zero or negative scale");
                }
            }

            // Check overlap
            if (checkOverlap)
            {
                Bounds myBounds = CalculateBounds(go);
                var allObjects = GameObjectLookup.GetAllSceneObjects(false);

                foreach (var other in allObjects)
                {
                    if (other == go) continue;

                    Bounds otherBounds = CalculateBounds(other);
                    if (myBounds.Intersects(otherBounds))
                    {
                        // Calculate minimum distance between bounds
                        float distance = Vector3.Distance(myBounds.center, otherBounds.center) -
                                        (myBounds.extents.magnitude + otherBounds.extents.magnitude);

                        if (distance < minSpacing)
                        {
                            issues.Add($"Overlaps with '{other.name}' (distance: {distance:F3})");
                        }
                    }
                }
            }

            bool isValid = issues.Count == 0;
            string message = isValid
                ? $"Placement validation passed for '{go.name}'"
                : $"Placement validation found {issues.Count} issue(s) for '{go.name}'";

            if (warnings.Count > 0)
            {
                message += $" and {warnings.Count} warning(s)";
            }

            var data = new
            {
                isValid,
                issues,
                warnings,
                position = new[] { go.transform.position.x, go.transform.position.y, go.transform.position.z },
                scale = new[] { go.transform.localScale.x, go.transform.localScale.y, go.transform.localScale.z }
            };

            if (!isValid)
            {
                return new ErrorResponse(message, data);
            }

            return new SuccessResponse(message, data);
        }
    }
}
