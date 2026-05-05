using MCPForUnity.Editor.Helpers;
using Newtonsoft.Json.Linq;

namespace MCPForUnity.Editor.Tools
{
    /// <summary>
    /// Flush the script-edit debounce queue immediately and force a compile request.
    /// Use this when an agent has finished a burst of edits and wants the compile to start
    /// without waiting for the 200ms debounce window.
    /// </summary>
    [McpForUnityTool("compile_now", AutoRegister = false)]
    public static class CompileNow
    {
        public static object HandleCommand(JObject @params)
        {
            try
            {
                RefreshDebounce.FlushNow();
                return new SuccessResponse("Compile flush requested.", new
                {
                    hint = "Poll editor_state until ready_for_tools is true before issuing more script edits."
                });
            }
            catch (System.Exception ex)
            {
                return new ErrorResponse($"compile_now failed: {ex.Message}");
            }
        }
    }
}
