using UnityEngine;

namespace MCPForUnity.Editor.Helpers
{
    /// <summary>
    /// Resolves Unity objects without relying on obsolete instance-ID editor APIs.
    /// </summary>
    public static class UnityEditorObjectLookup
    {
        public static Object FindObjectByInstanceId(int instanceId)
        {
            if (instanceId == 0)
            {
                return null;
            }

            var loadedObjects = UnityEngine.Resources.FindObjectsOfTypeAll<Object>();
            foreach (var loadedObject in loadedObjects)
            {
                if (loadedObject != null && loadedObject.GetInstanceID() == instanceId)
                {
                    return loadedObject;
                }
            }

            return null;
        }

        public static T FindObjectByInstanceId<T>(int instanceId) where T : Object
        {
            return FindObjectByInstanceId(instanceId) as T;
        }
    }
}
