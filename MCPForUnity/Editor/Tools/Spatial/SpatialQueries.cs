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
    /// Handles spatial queries for Unity scenes including nearest neighbor searches,
    /// radius/box queries, overlap checks, raycasting, and distance calculations.
    /// Part of the 'spatial' tool group.
    /// </summary>
    [McpForUnityTool("spatial_queries", AutoRegister = false, Group = "spatial")]
    public static class SpatialQueries
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

            try
            {
                switch (action)
                {
                    case "nearest_object":
                        return FindNearestObject(@params);
                    case "objects_in_radius":
                        return FindObjectsInRadius(@params);
                    case "objects_in_box":
                        return FindObjectsInBox(@params);
                    case "overlap_check":
                        return CheckOverlap(@params);
                    case "raycast":
                        return PerformRaycast(@params);
                    case "get_distance":
                        return GetDistance(@params);
                    case "get_direction":
                        return GetDirection(@params);
                    case "get_relative_offset":
                        return GetRelativeOffset(@params);

                    default:
                        return new ErrorResponse($"Unknown action: '{action}'. Valid actions: nearest_object, objects_in_radius, objects_in_box, overlap_check, raycast, get_distance, get_direction, get_relative_offset");
                }
            }
            catch (Exception e)
            {
                McpLog.Error($"[SpatialQueries] Action '{action}' failed: {e}");
                return new ErrorResponse($"Internal error processing action '{action}': {e.Message}");
            }
        }

        private static object FindNearestObject(JObject @params)
        {
            Vector3? point = VectorParsing.ParseVector3(@params["point"]);
            string searchMethod = @params["searchMethod"]?.ToString().ToLower();

            GameObject sourceGo = null;
            if (point == null)
            {
                // Use source object if point not specified
                JToken sourceToken = @params["source"];
                if (sourceToken != null)
                {
                    sourceGo = FindGameObject(sourceToken, searchMethod);
                    if (sourceGo == null)
                    {
                        return new ErrorResponse($"Source object '{sourceToken}' not found.");
                    }
                    point = sourceGo.transform.position;
                }
                else
                {
                    return new ErrorResponse("Either 'point' or 'source' parameter is required for nearest_object.");
                }
            }

            // Get filter parameters
            string filterByTag = @params["filterByTag"]?.ToString();
            string filterByLayer = @params["filterByLayer"]?.ToString();
            string filterByComponent = @params["filterByComponent"]?.ToString();
            bool excludeInactive = @params["excludeInactive"]?.ToObject<bool>() ?? true;

            // Get all objects and find nearest
            var allObjects = GameObjectLookup.GetAllSceneObjects(!excludeInactive);
            GameObject nearest = null;
            float nearestDistance = float.MaxValue;

            foreach (var go in allObjects)
            {
                if (go == sourceGo) continue;

                // Apply filters
                if (!PassesFilters(go, filterByTag, filterByLayer, filterByComponent))
                    continue;

                float distance = Vector3.Distance(point.Value, go.transform.position);
                if (distance < nearestDistance)
                {
                    nearestDistance = distance;
                    nearest = go;
                }
            }

            if (nearest == null)
            {
                return new ErrorResponse("No objects found matching the criteria.");
            }

            var data = new
            {
                fromPoint = new[] { point.Value.x, point.Value.y, point.Value.z },
                fromObject = sourceGo?.name,
                nearestObject = new
                {
                    instanceId = nearest.GetInstanceID(),
                    name = nearest.name,
                    path = GameObjectLookup.GetGameObjectPath(nearest)
                },
                distance = nearestDistance,
                direction = new[]
                {
                    (nearest.transform.position.x - point.Value.x) / nearestDistance,
                    (nearest.transform.position.y - point.Value.y) / nearestDistance,
                    (nearest.transform.position.z - point.Value.z) / nearestDistance
                }
            };

            return new SuccessResponse($"Nearest object to '{sourceGo?.name ?? point.ToString()}' is '{nearest.name}' ({nearestDistance:F3} units away).", data);
        }

        private static object FindObjectsInRadius(JObject @params)
        {
            Vector3? point = VectorParsing.ParseVector3(@params["point"]);
            string searchMethod = @params["searchMethod"]?.ToString().ToLower();

            Vector3 searchPoint;
            if (point == null)
            {
                // Use source object if point not specified
                JToken sourceToken = @params["source"];
                if (sourceToken != null)
                {
                    GameObject sourceGo = FindGameObject(sourceToken, searchMethod);
                    if (sourceGo == null)
                    {
                        return new ErrorResponse($"Source object '{sourceToken}' not found.");
                    }
                    searchPoint = sourceGo.transform.position;
                }
                else
                {
                    return new ErrorResponse("Either 'point' or 'source' parameter is required for objects_in_radius.");
                }
            }
            else
            {
                searchPoint = point.Value;
            }

            float radius = @params["radius"]?.ToObject<float>() ?? 10.0f;
            int maxResults = @params["maxResults"]?.ToObject<int>() ?? 50;

            // Get filter parameters
            string filterByTag = @params["filterByTag"]?.ToString();
            string filterByLayer = @params["filterByLayer"]?.ToString();
            string filterByComponent = @params["filterByComponent"]?.ToString();
            bool excludeInactive = @params["excludeInactive"]?.ToObject<bool>() ?? true;

            // Find objects within radius
            var allObjects = GameObjectLookup.GetAllSceneObjects(!excludeInactive);
            var results = new List<(GameObject go, float distance)>();

            foreach (var go in allObjects)
            {
                // Apply filters
                if (!PassesFilters(go, filterByTag, filterByLayer, filterByComponent))
                    continue;

                float distance = Vector3.Distance(searchPoint, go.transform.position);
                if (distance <= radius)
                {
                    results.Add((go, distance));
                }
            }

            // Sort by distance and take max results
            results.Sort((a, b) => a.distance.CompareTo(b.distance));
            if (maxResults > 0 && results.Count > maxResults)
            {
                results = results.Take(maxResults).ToList();
            }

            var objects = results.Select(r => new
            {
                instanceId = r.go.GetInstanceID(),
                name = r.go.name,
                path = GameObjectLookup.GetGameObjectPath(r.go),
                distance = r.distance,
                position = new[] { r.go.transform.position.x, r.go.transform.position.y, r.go.transform.position.z }
            }).ToArray();

            var data = new
            {
                center = new[] { searchPoint.x, searchPoint.y, searchPoint.z },
                radius,
                foundCount = results.Count,
                objects
            };

            return new SuccessResponse($"Found {results.Count} object(s) within {radius} units radius.", data);
        }

        private static object FindObjectsInBox(JObject @params)
        {
            Vector3? boxCenter = VectorParsing.ParseVector3(@params["boxCenter"]);
            Vector3? boxSize = VectorParsing.ParseVector3(@params["boxSize"]);

            if (boxCenter == null)
            {
                // Try to use source object position
                JToken sourceToken = @params["source"];
                if (sourceToken != null)
                {
                    string searchMethod = @params["searchMethod"]?.ToString().ToLower();
                    GameObject sourceGo = FindGameObject(sourceToken, searchMethod);
                    if (sourceGo != null)
                    {
                        boxCenter = sourceGo.transform.position;
                    }
                }
            }

            if (boxCenter == null)
            {
                return new ErrorResponse("Either 'boxCenter' or 'source' parameter is required for objects_in_box.");
            }

            if (boxSize == null)
            {
                boxSize = new Vector3(10, 10, 10); // Default size
            }

            // Get filter parameters
            string filterByTag = @params["filterByTag"]?.ToString();
            string filterByLayer = @params["filterByLayer"]?.ToString();
            string filterByComponent = @params["filterByComponent"]?.ToString();
            bool excludeInactive = @params["excludeInactive"]?.ToObject<bool>() ?? true;
            int maxResults = @params["maxResults"]?.ToObject<int>() ?? 50;

            Bounds queryBounds = new Bounds(boxCenter.Value, boxSize.Value);

            // Find objects within box
            var allObjects = GameObjectLookup.GetAllSceneObjects(!excludeInactive);
            var results = new List<(GameObject go, float distance)>();

            foreach (var go in allObjects)
            {
                // Apply filters
                if (!PassesFilters(go, filterByTag, filterByLayer, filterByComponent))
                    continue;

                // Check if object is within bounds
                Bounds objBounds = CalculateBounds(go);
                if (queryBounds.Intersects(objBounds) || queryBounds.Contains(go.transform.position))
                {
                    float distance = Vector3.Distance(boxCenter.Value, go.transform.position);
                    results.Add((go, distance));
                }
            }

            // Sort by distance and take max results
            results.Sort((a, b) => a.distance.CompareTo(b.distance));
            if (maxResults > 0 && results.Count > maxResults)
            {
                results = results.Take(maxResults).ToList();
            }

            var objects = results.Select(r => new
            {
                instanceId = r.go.GetInstanceID(),
                name = r.go.name,
                path = GameObjectLookup.GetGameObjectPath(r.go),
                distance = r.distance,
                position = new[] { r.go.transform.position.x, r.go.transform.position.y, r.go.transform.position.z }
            }).ToArray();

            var data = new
            {
                boxCenter = new[] { boxCenter.Value.x, boxCenter.Value.y, boxCenter.Value.z },
                boxSize = new[] { boxSize.Value.x, boxSize.Value.y, boxSize.Value.z },
                foundCount = results.Count,
                objects
            };

            return new SuccessResponse($"Found {results.Count} object(s) within box bounds.", data);
        }

        private static object CheckOverlap(JObject @params)
        {
            string objectToPlace = @params["objectToPlace"]?.ToString();
            if (string.IsNullOrEmpty(objectToPlace))
            {
                return new ErrorResponse("objectToPlace parameter is required for overlap_check.");
            }

            string searchMethod = @params["searchMethod"]?.ToString().ToLower();
            GameObject go = FindGameObject(objectToPlace, searchMethod);
            if (go == null)
            {
                return new ErrorResponse($"Object to place '{objectToPlace}' not found.");
            }

            Vector3? placementPosition = VectorParsing.ParseVector3(@params["placementPosition"]);
            Vector3? rotationAtPlacement = VectorParsing.ParseVector3(@params["rotationAtPlacement"]);
            Vector3? scaleAtPlacement = VectorParsing.ParseVector3(@params["scaleAtPlacement"]);
            float minClearance = @params["minClearance"]?.ToObject<float>() ?? 0f;

            // Calculate bounds at placement position
            Bounds myBounds = CalculateBounds(go);

            // Adjust bounds for placement position
            Vector3 offset = (placementPosition ?? go.transform.position) - go.transform.position;
            myBounds.center += offset;

            // Adjust for rotation if specified
            if (rotationAtPlacement.HasValue)
            {
                // This is a simplified approach - for accurate rotated bounds,
                // we'd need to recalculate from scratch with the new rotation
                Quaternion rotation = Quaternion.Euler(rotationAtPlacement.Value);
                myBounds.extents = rotation * myBounds.extents;
            }

            // Adjust for scale if specified
            if (scaleAtPlacement.HasValue)
            {
                Vector3 scaleRatio = new Vector3(
                    scaleAtPlacement.Value.x / go.transform.localScale.x,
                    scaleAtPlacement.Value.y / go.transform.localScale.y,
                    scaleAtPlacement.Value.z / go.transform.localScale.z
                );
                myBounds.extents = new Vector3(
                    myBounds.extents.x * scaleRatio.x,
                    myBounds.extents.y * scaleRatio.y,
                    myBounds.extents.z * scaleRatio.z
                );
            }

            // Check for overlaps
            var allObjects = GameObjectLookup.GetAllSceneObjects(false);
            var overlaps = new List<object>();

            foreach (var other in allObjects)
            {
                if (other == go) continue;

                Bounds otherBounds = CalculateBounds(other);
                if (myBounds.Intersects(otherBounds))
                {
                    // Calculate penetration depth
                    Vector3 penetration = CalculatePenetration(myBounds, otherBounds);
                    float minDistance = Vector3.Distance(myBounds.center, otherBounds.center) -
                                       (myBounds.extents.magnitude + otherBounds.extents.magnitude);

                    if (minDistance < minClearance)
                    {
                        overlaps.Add(new
                        {
                            instanceId = other.GetInstanceID(),
                            name = other.name,
                            path = GameObjectLookup.GetGameObjectPath(other),
                            penetration = new[] { penetration.x, penetration.y, penetration.z },
                            clearance = minDistance
                        });
                    }
                }
            }

            bool hasOverlap = overlaps.Count > 0;

            var data = new
            {
                wouldOverlap = hasOverlap,
                overlapCount = overlaps.Count,
                placementPosition = new[] { myBounds.center.x, myBounds.center.y, myBounds.center.z },
                placementBounds = new
                {
                    center = new[] { myBounds.center.x, myBounds.center.y, myBounds.center.z },
                    extents = new[] { myBounds.extents.x, myBounds.extents.y, myBounds.extents.z }
                },
                overlaps
            };

            if (hasOverlap)
            {
                return new SuccessResponse($"Overlap check: {overlaps.Count} overlap(s) detected at placement position.", data);
            }

            return new SuccessResponse("Overlap check: No overlaps detected at placement position.", data);
        }

        private static object PerformRaycast(JObject @params)
        {
            Vector3? origin = VectorParsing.ParseVector3(@params["origin"]);
            Vector3? direction = VectorParsing.ParseVector3(@params["direction"]);

            if (origin == null)
            {
                // Try to use source object position
                JToken sourceToken = @params["source"];
                if (sourceToken != null)
                {
                    string searchMethod = @params["searchMethod"]?.ToString().ToLower();
                    GameObject sourceGo = FindGameObject(sourceToken, searchMethod);
                    if (sourceGo != null)
                    {
                        origin = sourceGo.transform.position;
                    }
                }
            }

            if (origin == null)
            {
                return new ErrorResponse("Either 'origin' or 'source' parameter is required for raycast.");
            }

            if (direction == null)
            {
                return new ErrorResponse("direction parameter is required for raycast.");
            }

            float maxDistance = @params["maxDistance"]?.ToObject<float>() ?? 1000f;

            // Parse layer mask if provided
            string layerMaskStr = @params["layerMask"]?.ToString();
            int layerMask = Physics.DefaultRaycastLayers;
            if (!string.IsNullOrEmpty(layerMaskStr))
            {
                layerMask = LayerMask.GetMask(layerMaskStr.Split(',').Select(s => s.Trim()).ToArray());
                if (layerMask == 0)
                {
                    layerMask = ~0; // All layers if parsing fails
                }
            }

            // Perform raycast
            Ray ray = new Ray(origin.Value, direction.Value.normalized);
            RaycastHit hit;

            bool hasHit = Physics.Raycast(ray, out hit, maxDistance, layerMask);

            if (!hasHit)
            {
                var noHitData = new
                {
                    origin = new[] { origin.Value.x, origin.Value.y, origin.Value.z },
                    direction = new[] { direction.Value.x, direction.Value.y, direction.Value.z },
                    normalizedDirection = new[] { ray.direction.x, ray.direction.y, ray.direction.z },
                    maxDistance,
                    hit = false
                };
                return new SuccessResponse("Raycast completed: No hit detected.", noHitData);
            }

            GameObject hitObject = hit.collider?.gameObject;

            var hitData = new
            {
                origin = new[] { origin.Value.x, origin.Value.y, origin.Value.z },
                direction = new[] { direction.Value.x, direction.Value.y, direction.Value.z },
                normalizedDirection = new[] { ray.direction.x, ray.direction.y, ray.direction.z },
                maxDistance,
                hit = true,
                hitPoint = new[] { hit.point.x, hit.point.y, hit.point.z },
                hitNormal = new[] { hit.normal.x, hit.normal.y, hit.normal.z },
                distance = hit.distance,
                hitObject = hitObject != null ? new
                {
                    instanceId = hitObject.GetInstanceID(),
                    name = hitObject.name,
                    path = GameObjectLookup.GetGameObjectPath(hitObject)
                } : null,
                colliderName = hit.collider?.name,
                triangleIndex = hit.triangleIndex
            };

            return new SuccessResponse($"Raycast hit: '{hitObject?.name}' at distance {hit.distance:F3}.", hitData);
        }

        private static object GetDistance(JObject @params)
        {
            JToken sourceToken = @params["source"];
            JToken targetToken = @params["target"];
            string searchMethod = @params["searchMethod"]?.ToString().ToLower();

            Vector3? sourcePoint = VectorParsing.ParseVector3(@params["point"]);
            Vector3? targetPoint = null;

            GameObject sourceGo = null;
            GameObject targetGo = null;

            // Resolve source
            if (sourcePoint == null && sourceToken != null)
            {
                sourceGo = FindGameObject(sourceToken, searchMethod);
                if (sourceGo == null)
                {
                    return new ErrorResponse($"Source object '{sourceToken}' not found.");
                }
                sourcePoint = sourceGo.transform.position;
            }

            // Resolve target
            if (targetToken != null)
            {
                targetGo = FindGameObject(targetToken, searchMethod);
                if (targetGo == null)
                {
                    return new ErrorResponse($"Target object '{targetToken}' not found.");
                }
                targetPoint = targetGo.transform.position;
            }

            if (sourcePoint == null)
            {
                return new ErrorResponse("Either 'point' or 'source' parameter is required.");
            }

            if (targetPoint == null)
            {
                return new ErrorResponse("'target' parameter is required for get_distance.");
            }

            float distance = Vector3.Distance(sourcePoint.Value, targetPoint.Value);
            Vector3 offset = targetPoint.Value - sourcePoint.Value;

            var data = new
            {
                sourcePoint = new[] { sourcePoint.Value.x, sourcePoint.Value.y, sourcePoint.Value.z },
                targetPoint = new[] { targetPoint.Value.x, targetPoint.Value.y, targetPoint.Value.z },
                distance,
                offset = new[] { offset.x, offset.y, offset.z },
                sourceObject = sourceGo?.name,
                targetObject = targetGo?.name
            };

            return new SuccessResponse($"Distance: {distance:F3} units from '{sourceGo?.name ?? sourcePoint.ToString()}' to '{targetGo?.name}'.", data);
        }

        private static object GetDirection(JObject @params)
        {
            JToken sourceToken = @params["source"];
            JToken targetToken = @params["target"];
            string searchMethod = @params["searchMethod"]?.ToString().ToLower();

            if (sourceToken == null || targetToken == null)
            {
                return new ErrorResponse("Both 'source' and 'target' parameters are required for get_direction.");
            }

            GameObject sourceGo = FindGameObject(sourceToken, searchMethod);
            if (sourceGo == null)
            {
                return new ErrorResponse($"Source object '{sourceToken}' not found.");
            }

            GameObject targetGo = FindGameObject(targetToken, searchMethod);
            if (targetGo == null)
            {
                return new ErrorResponse($"Target object '{targetToken}' not found.");
            }

            Vector3 direction = (targetGo.transform.position - sourceGo.transform.position).normalized;
            float distance = Vector3.Distance(sourceGo.transform.position, targetGo.transform.position);

            var data = new
            {
                source = new
                {
                    instanceId = sourceGo.GetInstanceID(),
                    name = sourceGo.name,
                    position = new[] { sourceGo.transform.position.x, sourceGo.transform.position.y, sourceGo.transform.position.z }
                },
                target = new
                {
                    instanceId = targetGo.GetInstanceID(),
                    name = targetGo.name,
                    position = new[] { targetGo.transform.position.x, targetGo.transform.position.y, targetGo.transform.position.z }
                },
                direction = new[] { direction.x, direction.y, direction.z },
                distance,
                cardinalDirection = GetCardinalDirection(direction)
            };

            return new SuccessResponse($"Direction from '{sourceGo.name}' to '{targetGo.name}': [{direction.x:F3}, {direction.y:F3}, {direction.z:F3}].", data);
        }

        private static object GetRelativeOffset(JObject @params)
        {
            JToken sourceToken = @params["source"];
            JToken targetToken = @params["target"];
            string searchMethod = @params["searchMethod"]?.ToString().ToLower();
            string offsetType = @params["offsetType"]?.ToString().ToLower() ?? "position";

            if (sourceToken == null || targetToken == null)
            {
                return new ErrorResponse("Both 'source' and 'target' parameters are required for get_relative_offset.");
            }

            GameObject sourceGo = FindGameObject(sourceToken, searchMethod);
            if (sourceGo == null)
            {
                return new ErrorResponse($"Source object '{sourceToken}' not found.");
            }

            GameObject targetGo = FindGameObject(targetToken, searchMethod);
            if (targetGo == null)
            {
                return new ErrorResponse($"Target object '{targetToken}' not found.");
            }

            Vector3 sourcePoint = GetOffsetPoint(sourceGo, offsetType);
            Vector3 targetPoint = GetOffsetPoint(targetGo, offsetType);

            Vector3 worldOffset = targetPoint - sourcePoint;
            Vector3 localOffset = sourceGo.transform.InverseTransformDirection(worldOffset);

            var data = new
            {
                source = new
                {
                    instanceId = sourceGo.GetInstanceID(),
                    name = sourceGo.name,
                    offsetPoint = new[] { sourcePoint.x, sourcePoint.y, sourcePoint.z }
                },
                target = new
                {
                    instanceId = targetGo.GetInstanceID(),
                    name = targetGo.name,
                    offsetPoint = new[] { targetPoint.x, targetPoint.y, targetPoint.z }
                },
                offsetType,
                worldOffset = new[] { worldOffset.x, worldOffset.y, worldOffset.z },
                localOffset = new[] { localOffset.x, localOffset.y, localOffset.z },
                distance = worldOffset.magnitude
            };

            return new SuccessResponse($"Offset from '{sourceGo.name}' to '{targetGo.name}' ({offsetType}): [{worldOffset.x:F3}, {worldOffset.y:F3}, {worldOffset.z:F3}].", data);
        }

        // Helper methods

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

        private static bool PassesFilters(GameObject go, string filterByTag, string filterByLayer, string filterByComponent)
        {
            if (!string.IsNullOrEmpty(filterByTag) && !go.CompareTag(filterByTag))
                return false;

            if (!string.IsNullOrEmpty(filterByLayer))
            {
                int layer = LayerMask.NameToLayer(filterByLayer);
                if (layer != -1 && go.layer != layer)
                    return false;
            }

            if (!string.IsNullOrEmpty(filterByComponent))
            {
                Type componentType = GameObjectLookup.FindComponentType(filterByComponent);
                if (componentType == null || go.GetComponent(componentType) == null)
                    return false;
            }

            return true;
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

            if (!hasBounds)
            {
                bounds = new Bounds(go.transform.position, Vector3.zero);
            }

            return bounds;
        }

        private static Vector3 CalculatePenetration(Bounds a, Bounds b)
        {
            Vector3 penetration = Vector3.zero;

            // Calculate overlap on each axis
            float overlapX = Mathf.Min(a.max.x - b.min.x, b.max.x - a.min.x);
            float overlapY = Mathf.Min(a.max.y - b.min.y, b.max.y - a.min.y);
            float overlapZ = Mathf.Min(a.max.z - b.min.z, b.max.z - a.min.z);

            // Find the smallest penetration axis
            if (overlapX < overlapY && overlapX < overlapZ)
            {
                penetration.x = overlapX * Mathf.Sign(a.center.x - b.center.x);
            }
            else if (overlapY < overlapZ)
            {
                penetration.y = overlapY * Mathf.Sign(a.center.y - b.center.y);
            }
            else
            {
                penetration.z = overlapZ * Mathf.Sign(a.center.z - b.center.z);
            }

            return penetration;
        }

        private static string GetCardinalDirection(Vector3 direction)
        {
            // Convert direction to cardinal direction
            float absX = Mathf.Abs(direction.x);
            float absY = Mathf.Abs(direction.y);
            float absZ = Mathf.Abs(direction.z);

            if (absY > absX && absY > absZ)
            {
                return direction.y > 0 ? "up" : "down";
            }
            else if (absX > absZ)
            {
                return direction.x > 0 ? "east/right" : "west/left";
            }
            else
            {
                return direction.z > 0 ? "north/forward" : "south/back";
            }
        }

        private static Vector3 GetOffsetPoint(GameObject go, string offsetType)
        {
            switch (offsetType)
            {
                case "bounds_center":
                    return CalculateBounds(go).center;
                case "bounds_min":
                    return CalculateBounds(go).min;
                case "bounds_max":
                    return CalculateBounds(go).max;
                case "pivot":
                case "position":
                default:
                    return go.transform.position;
            }
        }
    }
}
