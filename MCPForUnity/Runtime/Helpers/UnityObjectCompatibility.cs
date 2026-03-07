using UnityEngine;

namespace MCPForUnity.Runtime.Helpers
{
    /// <summary>
    /// Wraps Unity object enumeration APIs that changed across engine versions.
    /// </summary>
    public static class UnityObjectCompatibility
    {
        public static T[] FindObjectsByType<T>(bool includeInactive = false) where T : Object
        {
#if UNITY_2022_2_OR_NEWER
            return Object.FindObjectsByType<T>(
                includeInactive ? FindObjectsInactive.Include : FindObjectsInactive.Exclude,
                FindObjectsSortMode.None);
#else
            return Object.FindObjectsOfType<T>(includeInactive);
#endif
        }
    }
}
