using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using MCPForUnity.Editor.Helpers;
using UnityEditor.PackageManager;
using UnityEditor.PackageManager.Requests;
using PackageInfo = UnityEditor.PackageManager.PackageInfo;

namespace MCPForUnity.Editor.Tools.PackageManager
{
    internal static class PackageRequestUtility
    {
        internal const int ReadTimeoutMs = 5000;
        internal const int MutationTimeoutMs = 30000;
        private const int ReadCacheTtlMs = 2000;
        private const int PollIntervalMs = 50;
        private static readonly SemaphoreSlim RequestGate = new SemaphoreSlim(1, 1);
        private static readonly object CacheLock = new object();
        private static PackageInfo[] _cachedInstalledPackages;
        private static long _cachedInstalledPackagesAtMs;

        private static long GetMonotonicMilliseconds()
        {
            return (long)(Stopwatch.GetTimestamp() * 1000.0 / Stopwatch.Frequency);
        }

        internal readonly struct RequestWaitResult
        {
            public RequestWaitResult(bool success, string errorMessage)
            {
                Success = success;
                ErrorMessage = errorMessage;
            }

            public bool Success { get; }
            public string ErrorMessage { get; }
        }

        internal static async Task<RequestWaitResult> WaitForCompletionAsync(
            Request request,
            string operationName,
            int timeoutMs)
        {
            if (request == null)
            {
                return new RequestWaitResult(false, $"Package Manager request '{operationName}' was null.");
            }

            long startedAtMs = GetMonotonicMilliseconds();
            while (!request.IsCompleted)
            {
                if (GetMonotonicMilliseconds() - startedAtMs >= timeoutMs)
                {
                    var message =
                        $"Package Manager request '{operationName}' timed out after {timeoutMs} ms. " +
                        "Unity Package Manager may be busy or waiting on network/package resolution.";
                    McpLog.Warn($"[PackageManager] {message}");
                    return new RequestWaitResult(false, message);
                }

                await Task.Delay(PollIntervalMs);
            }

            if (request.Status == StatusCode.Failure)
            {
                return new RequestWaitResult(
                    false,
                    request.Error?.message ?? $"Package Manager request '{operationName}' failed."
                );
            }

            return new RequestWaitResult(true, null);
        }

        internal static async Task<T> RunExclusiveAsync<T>(
            string operationName,
            Func<Task<T>> action)
        {
            await RequestGate.WaitAsync();
            try
            {
                return await action();
            }
            finally
            {
                RequestGate.Release();
            }
        }

        internal static bool TryGetInstalledPackagesFromCache(out PackageInfo[] packages)
        {
            lock (CacheLock)
            {
                if (_cachedInstalledPackages != null &&
                    GetMonotonicMilliseconds() - _cachedInstalledPackagesAtMs <= ReadCacheTtlMs)
                {
                    packages = _cachedInstalledPackages;
                    return true;
                }
            }

            packages = null;
            return false;
        }

        internal static void StoreInstalledPackages(PackageInfo[] packages)
        {
            lock (CacheLock)
            {
                _cachedInstalledPackages = packages;
                _cachedInstalledPackagesAtMs = GetMonotonicMilliseconds();
            }
        }

        internal static void InvalidateInstalledPackagesCache()
        {
            lock (CacheLock)
            {
                _cachedInstalledPackages = null;
                _cachedInstalledPackagesAtMs = 0;
            }
        }
    }
}
