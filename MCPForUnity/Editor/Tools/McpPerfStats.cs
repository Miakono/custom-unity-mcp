using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Services;
using Newtonsoft.Json.Linq;

namespace MCPForUnity.Editor.Tools
{
    /// <summary>
    /// Surfaces in-process performance counters: per-tool latency, compile-trigger count,
    /// idle/active editor ticks, top-N slowest tools by cumulative cost.
    /// Always-on, allocation-free on the hot path; complements the sampled Python-side traces.
    /// </summary>
    [McpForUnityTool("mcp_perf_stats", AutoRegister = false)]
    public static class McpPerfStats
    {
        public static object HandleCommand(JObject @params)
        {
            string action = @params?["action"]?.ToString()?.ToLowerInvariant() ?? "snapshot";
            int topN = ParamCoercion.CoerceInt(@params?["top_n"], 20);

            switch (action)
            {
                case "reset":
                    PerfMetrics.Reset();
                    return new SuccessResponse("Perf metrics reset.");
                case "snapshot":
                default:
                    return new SuccessResponse("Perf metrics snapshot.", PerfMetrics.Snapshot(topN));
            }
        }
    }
}
