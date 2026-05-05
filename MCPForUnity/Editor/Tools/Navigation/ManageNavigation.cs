using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.AI;
// UnityEditor.AI.NavMeshBuilder is referenced via fully-qualified name below — both
// UnityEngine.AI and UnityEditor.AI ship a 'NavMeshBuilder' type so we avoid the using.
using EditorNavMeshBuilder = UnityEditor.AI.NavMeshBuilder;

namespace MCPForUnity.Editor.Tools.Navigation
{
    /// <summary>
    /// NavMesh tooling: trigger bakes, query agent paths, sample positions, list surfaces.
    ///
    /// Supports both the legacy NavMesh system (UnityEditor.AI.NavMeshBuilder, baked at the
    /// scene level) and the newer com.unity.ai.navigation NavMeshSurface component (looked
    /// up via reflection so the MCP package compiles whether or not that package is installed).
    /// </summary>
    [McpForUnityTool("manage_navigation", AutoRegister = false, Group = "navigation")]
    public static class ManageNavigation
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
                    case "get_status": return GetStatus();
                    case "bake": return Bake(p);
                    case "clear": return Clear();
                    case "calculate_path": return CalculatePath(p);
                    case "sample_position": return SamplePosition(p);
                    case "list_surfaces": return ListSurfaces();
                    default:
                        return new ErrorResponse(
                            $"Unknown action '{action}'. Valid: get_status, bake, clear, " +
                            "calculate_path, sample_position, list_surfaces.");
                }
            }
            catch (Exception ex)
            {
                return new ErrorResponse($"manage_navigation {action} failed: {ex.Message}");
            }
        }

        // ─── get_status ──────────────────────────────────────────────────────────────

        private static object GetStatus()
        {
            // Trigger calculation of NavMesh data state in the active scene.
            var triangulation = NavMesh.CalculateTriangulation();
            int vertexCount = triangulation.vertices?.Length ?? 0;
            int triangleCount = (triangulation.indices?.Length ?? 0) / 3;
            int areaCount = triangulation.areas?.Length ?? 0;

            var surfaces = FindNavMeshSurfaces();
            var legacyBaking = EditorNavMeshBuilder.isRunning;

            return new SuccessResponse(
                vertexCount > 0
                    ? $"NavMesh present: {vertexCount} vertices, {triangleCount} triangles."
                    : "No NavMesh built in the active scene.",
                new
                {
                    has_navmesh = vertexCount > 0,
                    vertex_count = vertexCount,
                    triangle_count = triangleCount,
                    area_count = areaCount,
                    legacy_baking_in_progress = legacyBaking,
                    navmesh_surface_count = surfaces.Count,
                    navmesh_surfaces = surfaces.Select(SurfaceDescriptor).ToArray(),
                    has_ai_navigation_package = NavMeshSurfaceTypeReflection != null,
                });
        }

        // ─── bake ────────────────────────────────────────────────────────────────────

        private static object Bake(ToolParams p)
        {
            // Default: bake all NavMeshSurface components if the new package is present;
            // otherwise fall back to the legacy NavMeshBuilder which uses scene-level
            // navigation static flags.
            string mode = (p.Get("mode") ?? "auto").ToLowerInvariant();
            bool async = p.GetBool("async", false);

            var surfaces = FindNavMeshSurfaces();
            bool useSurfaces = mode == "surfaces" || (mode == "auto" && surfaces.Count > 0);

            if (useSurfaces)
            {
                if (surfaces.Count == 0)
                    return new ErrorResponse("Mode requires NavMeshSurface components but none were found in the active scene.");

                int baked = 0;
                foreach (var surface in surfaces)
                {
                    var bakeMethod = surface.GetType().GetMethod("BuildNavMesh",
                        BindingFlags.Public | BindingFlags.Instance);
                    if (bakeMethod != null)
                    {
                        bakeMethod.Invoke(surface, null);
                        baked++;
                    }
                }
                return new SuccessResponse($"Baked {baked} NavMeshSurface(s).", new
                {
                    method = "navmesh_surfaces",
                    surface_count = surfaces.Count,
                    baked_count = baked,
                });
            }

            // Legacy bake path
            if (async)
            {
                EditorNavMeshBuilder.BuildNavMeshAsync();
                return new SuccessResponse("Started async legacy NavMesh build.", new
                {
                    method = "legacy_async",
                    is_running = EditorNavMeshBuilder.isRunning,
                });
            }
            else
            {
                EditorNavMeshBuilder.BuildNavMesh();
                return new SuccessResponse("Completed synchronous legacy NavMesh build.", new
                {
                    method = "legacy_sync",
                    is_running = EditorNavMeshBuilder.isRunning,
                });
            }
        }

        // ─── clear ───────────────────────────────────────────────────────────────────

        private static object Clear()
        {
            EditorNavMeshBuilder.ClearAllNavMeshes();
            return new SuccessResponse("Cleared NavMesh data.");
        }

        // ─── calculate_path ──────────────────────────────────────────────────────────

        private static object CalculatePath(ToolParams p)
        {
            var startVec = ParseVector3(p.Get("start"));
            var endVec = ParseVector3(p.Get("end"));
            if (!startVec.HasValue || !endVec.HasValue)
                return new ErrorResponse("'start' and 'end' required as 'x,y,z' world positions.");

            int areaMask = p.GetInt("areaMask", NavMesh.AllAreas) ?? NavMesh.AllAreas;
            var path = new NavMeshPath();
            bool found = NavMesh.CalculatePath(startVec.Value, endVec.Value, areaMask, path);

            return new SuccessResponse(
                found
                    ? $"Path computed with status '{path.status}' and {path.corners?.Length ?? 0} corners."
                    : "CalculatePath returned false (no path possible from these positions).",
                new
                {
                    found,
                    status = path.status.ToString(),
                    corner_count = path.corners?.Length ?? 0,
                    corners = path.corners?.Select(c => new[] { c.x, c.y, c.z }).ToArray(),
                    total_distance = ComputePathLength(path),
                });
        }

        // ─── sample_position ─────────────────────────────────────────────────────────

        private static object SamplePosition(ToolParams p)
        {
            var posVec = ParseVector3(p.Get("position"));
            if (!posVec.HasValue) return new ErrorResponse("'position' required as 'x,y,z'.");

            float maxDistance = p.GetFloat("maxDistance", 5f) ?? 5f;
            int areaMask = p.GetInt("areaMask", NavMesh.AllAreas) ?? NavMesh.AllAreas;

            bool found = NavMesh.SamplePosition(posVec.Value, out NavMeshHit hit, maxDistance, areaMask);
            return new SuccessResponse(
                found ? $"Sampled NavMesh point at distance {hit.distance:F3}." : "No NavMesh point within maxDistance.",
                new
                {
                    found,
                    distance = hit.distance,
                    position = found ? new[] { hit.position.x, hit.position.y, hit.position.z } : null,
                    normal = found ? new[] { hit.normal.x, hit.normal.y, hit.normal.z } : null,
                    mask = hit.mask,
                });
        }

        // ─── list_surfaces ───────────────────────────────────────────────────────────

        private static object ListSurfaces()
        {
            var surfaces = FindNavMeshSurfaces();
            return new SuccessResponse($"Found {surfaces.Count} NavMeshSurface component(s).", new
            {
                surface_count = surfaces.Count,
                surfaces = surfaces.Select(SurfaceDescriptor).ToArray(),
            });
        }

        // ─── reflection helpers (NavMeshSurface lives in com.unity.ai.navigation) ────

        private static Type _navMeshSurfaceType;
        private static bool _navMeshSurfaceTypeResolved;
        private static Type NavMeshSurfaceTypeReflection
        {
            get
            {
                if (_navMeshSurfaceTypeResolved) return _navMeshSurfaceType;
                _navMeshSurfaceTypeResolved = true;
                foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
                {
                    if (asm.IsDynamic) continue;
                    try
                    {
                        var t = asm.GetType("Unity.AI.Navigation.NavMeshSurface", false);
                        if (t != null) { _navMeshSurfaceType = t; break; }
                    }
                    catch { }
                }
                return _navMeshSurfaceType;
            }
        }

        private static List<UnityEngine.Component> FindNavMeshSurfaces()
        {
            var results = new List<UnityEngine.Component>();
            var t = NavMeshSurfaceTypeReflection;
            if (t == null) return results;

            // Use FindObjectsByType (Unity 2022+) via the non-generic overload.
            var found = UnityEngine.Object.FindObjectsByType(t,
                FindObjectsInactive.Include, FindObjectsSortMode.None) as UnityEngine.Object[];
            if (found == null) return results;

            foreach (var obj in found)
            {
                if (obj is UnityEngine.Component comp) results.Add(comp);
            }
            return results;
        }

        private static object SurfaceDescriptor(UnityEngine.Component surface)
        {
            var t = surface.GetType();
            string ReadField(string n)
            {
                try
                {
                    var f = t.GetField(n, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                    if (f != null) return f.GetValue(surface)?.ToString();
                    var p = t.GetProperty(n, BindingFlags.Public | BindingFlags.Instance);
                    return p?.GetValue(surface)?.ToString();
                }
                catch { return null; }
            }

            return new
            {
                game_object = surface.gameObject.name,
                scene_path = GetGameObjectPath(surface.gameObject),
                agent_type_id = ReadField("m_AgentTypeID") ?? ReadField("agentTypeID"),
                collect_objects = ReadField("m_CollectObjects") ?? ReadField("collectObjects"),
                default_area = ReadField("m_DefaultArea") ?? ReadField("defaultArea"),
                use_geometry = ReadField("m_UseGeometry") ?? ReadField("useGeometry"),
                has_baked_data = ReadField("navMeshData") != null,
            };
        }

        // ─── misc helpers ────────────────────────────────────────────────────────────

        private static Vector3? ParseVector3(string raw)
        {
            if (string.IsNullOrWhiteSpace(raw)) return null;
            var parts = raw.Split(',');
            if (parts.Length != 3) return null;
            try
            {
                return new Vector3(
                    float.Parse(parts[0], System.Globalization.CultureInfo.InvariantCulture),
                    float.Parse(parts[1], System.Globalization.CultureInfo.InvariantCulture),
                    float.Parse(parts[2], System.Globalization.CultureInfo.InvariantCulture));
            }
            catch { return null; }
        }

        private static float ComputePathLength(NavMeshPath path)
        {
            if (path?.corners == null || path.corners.Length < 2) return 0f;
            float dist = 0f;
            for (int i = 1; i < path.corners.Length; i++)
                dist += Vector3.Distance(path.corners[i - 1], path.corners[i]);
            return dist;
        }

        private static string GetGameObjectPath(GameObject go)
        {
            if (go == null) return null;
            var path = go.name;
            var t = go.transform.parent;
            while (t != null)
            {
                path = t.name + "/" + path;
                t = t.parent;
            }
            return path;
        }
    }
}
