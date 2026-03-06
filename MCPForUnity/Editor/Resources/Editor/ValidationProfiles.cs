using System;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;

namespace MCPForUnity.Editor.Resources.Editor
{
    /// <summary>
    /// Returns Unity plugin validation and audit profiles derived from the local tool registry.
    /// This gives clients a structured way to discover read-only health surfaces exposed by the plugin.
    /// </summary>
    [McpForUnityResource("get_validation_profiles")]
    public static class ValidationProfiles
    {
        public static object HandleCommand(JObject @params)
        {
            try
            {
                var catalog = ValidationProfileCatalogBuilder.BuildCatalog();
                return new SuccessResponse("Retrieved Unity validation profiles.", JObject.FromObject(catalog));
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Failed to retrieve validation profiles: {e.Message}");
            }
        }
    }
}
