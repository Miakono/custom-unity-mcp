using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Threading;

namespace MCPForUnity.Editor.Services
{
    /// <summary>
    /// Lightweight in-process performance counters surfaced through get_diagnostics / get_command_stats.
    /// Drop-in for environments where the Python-side trace recorder is sampled or disabled — the
    /// numbers here are always-on, allocation-free on the hot path, and bounded in memory.
    /// </summary>
    internal static class PerfMetrics
    {
        public sealed class ToolStats
        {
            public long CallCount;
            public long FailureCount;
            public long TotalHandlerMs;
            public long TotalQueueWaitMs;
            public long MaxHandlerMs;
            public long MaxQueueWaitMs;
        }

        private static readonly ConcurrentDictionary<string, ToolStats> _byTool = new();
        private static long _compileTriggerCount;
        private static long _forcedSyncImportCount;
        private static long _idleTickCount;
        private static long _activeTickCount;
        private static readonly DateTime _sessionStartUtc = DateTime.UtcNow;

        public static void RecordCommand(string toolName, long queueWaitMs, long handlerMs, bool success)
        {
            if (string.IsNullOrEmpty(toolName)) toolName = "(unknown)";

            var stats = _byTool.GetOrAdd(toolName, _ => new ToolStats());
            Interlocked.Increment(ref stats.CallCount);
            if (!success) Interlocked.Increment(ref stats.FailureCount);
            Interlocked.Add(ref stats.TotalHandlerMs, handlerMs);
            Interlocked.Add(ref stats.TotalQueueWaitMs, queueWaitMs);
            UpdateMax(ref stats.MaxHandlerMs, handlerMs);
            UpdateMax(ref stats.MaxQueueWaitMs, queueWaitMs);
        }

        public static void RecordCompileTrigger() => Interlocked.Increment(ref _compileTriggerCount);
        public static void RecordForcedSyncImport() => Interlocked.Increment(ref _forcedSyncImportCount);
        public static void RecordIdleTick() => Interlocked.Increment(ref _idleTickCount);
        public static void RecordActiveTick() => Interlocked.Increment(ref _activeTickCount);

        public static long CompileTriggerCount => Interlocked.Read(ref _compileTriggerCount);
        public static long ForcedSyncImportCount => Interlocked.Read(ref _forcedSyncImportCount);

        public static IDictionary<string, object> Snapshot(int topN = 20)
        {
            double sessionSec = Math.Max(1.0, (DateTime.UtcNow - _sessionStartUtc).TotalSeconds);
            long totalCalls = 0;
            long totalFailures = 0;
            long totalHandlerMs = 0;

            var tools = new List<object>();
            foreach (var kvp in _byTool)
            {
                var s = kvp.Value;
                long calls = Interlocked.Read(ref s.CallCount);
                long failures = Interlocked.Read(ref s.FailureCount);
                long handlerMs = Interlocked.Read(ref s.TotalHandlerMs);
                long queueMs = Interlocked.Read(ref s.TotalQueueWaitMs);
                long maxHandler = Interlocked.Read(ref s.MaxHandlerMs);
                long maxQueue = Interlocked.Read(ref s.MaxQueueWaitMs);

                totalCalls += calls;
                totalFailures += failures;
                totalHandlerMs += handlerMs;

                tools.Add(new Dictionary<string, object>
                {
                    ["tool"] = kvp.Key,
                    ["calls"] = calls,
                    ["failures"] = failures,
                    ["total_handler_ms"] = handlerMs,
                    ["avg_handler_ms"] = calls > 0 ? Math.Round(handlerMs / (double)calls, 2) : 0.0,
                    ["max_handler_ms"] = maxHandler,
                    ["total_queue_wait_ms"] = queueMs,
                    ["max_queue_wait_ms"] = maxQueue,
                });
            }

            // Cumulative-cost sort: what's actually eating budget, not the single slowest call.
            var ordered = tools
                .OrderByDescending(t => (long)((Dictionary<string, object>)t)["total_handler_ms"])
                .Take(Math.Max(1, topN))
                .ToList();

            long idle = Interlocked.Read(ref _idleTickCount);
            long active = Interlocked.Read(ref _activeTickCount);
            var (cacheHits, cacheMisses) = AssetPathCache.GetStats();
            long cacheTotal = cacheHits + cacheMisses;

            return new Dictionary<string, object>
            {
                ["session_seconds"] = Math.Round(sessionSec, 1),
                ["total_calls"] = totalCalls,
                ["total_failures"] = totalFailures,
                ["total_handler_ms"] = totalHandlerMs,
                ["compile_trigger_count"] = Interlocked.Read(ref _compileTriggerCount),
                ["forced_sync_import_count"] = Interlocked.Read(ref _forcedSyncImportCount),
                ["idle_ticks"] = idle,
                ["active_ticks"] = active,
                ["idle_ticks_per_sec"] = Math.Round(idle / sessionSec, 2),
                ["asset_path_cache_hits"] = cacheHits,
                ["asset_path_cache_misses"] = cacheMisses,
                ["asset_path_cache_hit_rate"] = cacheTotal > 0 ? Math.Round(cacheHits / (double)cacheTotal, 3) : 0.0,
                ["top_n_slow"] = ordered,
            };
        }

        public static void Reset()
        {
            _byTool.Clear();
            Interlocked.Exchange(ref _compileTriggerCount, 0);
            Interlocked.Exchange(ref _forcedSyncImportCount, 0);
            Interlocked.Exchange(ref _idleTickCount, 0);
            Interlocked.Exchange(ref _activeTickCount, 0);
        }

        private static void UpdateMax(ref long target, long value)
        {
            long current;
            do
            {
                current = Interlocked.Read(ref target);
                if (value <= current) return;
            } while (Interlocked.CompareExchange(ref target, value, current) != current);
        }
    }
}
