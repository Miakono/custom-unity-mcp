using System;
using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;

namespace MCPForUnity.Editor.Resources.Editor
{
    /// <summary>
    /// Returns Unity plugin workflow specialists derived from the tool registry.
    /// This lets the server or editor UI reason about specialist handoffs using Unity-local metadata.
    /// </summary>
    [McpForUnityResource("get_subagent_profiles")]
    public static class SubagentProfiles
    {
        public static object HandleCommand(JObject @params)
        {
            try
            {
                var catalog = SubagentCatalogBuilder.BuildCatalog();
                return new SuccessResponse("Retrieved Unity subagent profiles.", JObject.FromObject(catalog));
            }
            catch (Exception e)
            {
                return new ErrorResponse($"Failed to retrieve subagent profiles: {e.Message}");
            }
        }
    }
}
