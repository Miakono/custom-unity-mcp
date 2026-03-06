// -----------------------------------------------------------------------
// RuntimeWebSocketClient.cs
// WebSocket client for Runtime MCP communication
// 
// Provides low-latency bidirectional communication with the MCP server.
// Uses a separate port from Editor MCP (default: 8090).
// -----------------------------------------------------------------------

#nullable enable

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace MCPForUnity.Runtime.MCP
{
    /// <summary>
    /// WebSocket client optimized for Runtime MCP communication.
    /// 
    /// Key features:
    /// - Async connect/disconnect
    /// - Message queue for thread-safe communication with Unity main thread
    /// - Automatic reconnection support
    /// - Separate from Editor WebSocket transport
    /// </summary>
    public class RuntimeWebSocketClient : IDisposable
    {
        #region Events

        /// <summary>
        /// Called when a message is received
        /// </summary>
        public event Action<string>? OnMessageReceived;

        /// <summary>
        /// Called when connection is established
        /// </summary>
        public event Action? OnConnected;

        /// <summary>
        /// Called when connection is lost
        /// </summary>
        public event Action? OnDisconnected;

        /// <summary>
        /// Called when an error occurs
        /// </summary>
        public event Action<string>? OnError;

        #endregion

        #region Properties

        /// <summary>
        /// Whether the client is currently connected
        /// </summary>
        public bool IsConnected => _webSocket != null && 
            _webSocket.State == System.Net.WebSockets.WebSocketState.Open;

        /// <summary>
        /// Current connection URL
        /// </summary>
        public string? CurrentUrl { get; private set; }

        #endregion

        #region Private Fields

        private System.Net.WebSockets.ClientWebSocket? _webSocket;
        private CancellationTokenSource? _cancellationTokenSource;
        private readonly ConcurrentQueue<string> _messageQueue = new();
        private readonly object _lock = new();

        #endregion

        #region Connection

        /// <summary>
        /// Connect to a WebSocket server
        /// </summary>
        public async Task<bool> ConnectAsync(string url)
        {
            lock (_lock)
            {
                if (IsConnected)
                {
                    Debug.LogWarning("[RuntimeWebSocketClient] Already connected");
                    return true;
                }
            }

            try
            {
                CurrentUrl = url;
                _cancellationTokenSource = new CancellationTokenSource();
                _webSocket = new System.Net.WebSockets.ClientWebSocket();

                var uri = new Uri(url);
                await _webSocket.ConnectAsync(uri, _cancellationTokenSource.Token);

                // Start receiving messages
                _ = ReceiveLoopAsync();

                Debug.Log($"[RuntimeWebSocketClient] Connected to {url}");
                OnConnected?.Invoke();
                
                return true;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[RuntimeWebSocketClient] Connection failed: {ex.Message}");
                OnError?.Invoke(ex.Message);
                Cleanup();
                return false;
            }
        }

        /// <summary>
        /// Disconnect from the server
        /// </summary>
        public async Task DisconnectAsync()
        {
            lock (_lock)
            {
                if (!IsConnected)
                {
                    return;
                }
            }

            try
            {
                _cancellationTokenSource?.Cancel();
                
                if (_webSocket?.State == System.Net.WebSockets.WebSocketState.Open)
                {
                    await _webSocket.CloseAsync(
                        System.Net.WebSockets.WebSocketCloseStatus.NormalClosure,
                        "Client disconnecting",
                        CancellationToken.None
                    );
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[RuntimeWebSocketClient] Disconnect error: {ex.Message}");
            }
            finally
            {
                Cleanup();
                OnDisconnected?.Invoke();
            }
        }

        /// <summary>
        /// Close the connection (synchronous version)
        /// </summary>
        public void Close()
        {
            _ = DisconnectAsync();
        }

        #endregion

        #region Messaging

        /// <summary>
        /// Send a message to the server
        /// </summary>
        public async Task<bool> SendAsync(string message)
        {
            if (!IsConnected)
            {
                Debug.LogWarning("[RuntimeWebSocketClient] Cannot send: not connected");
                return false;
            }

            try
            {
                var bytes = Encoding.UTF8.GetBytes(message);
                var buffer = new ArraySegment<byte>(bytes);
                
                await _webSocket!.SendAsync(
                    buffer,
                    System.Net.WebSockets.WebSocketMessageType.Text,
                    endOfMessage: true,
                    _cancellationTokenSource?.Token ?? CancellationToken.None
                );
                
                return true;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[RuntimeWebSocketClient] Send failed: {ex.Message}");
                OnError?.Invoke(ex.Message);
                return false;
            }
        }

        /// <summary>
        /// Send an object serialized as JSON
        /// </summary>
        public async Task<bool> SendAsync(object data)
        {
            string json = MiniJSON.Serialize(data);
            return await SendAsync(json);
        }

        /// <summary>
        /// Process queued messages on the main thread.
        /// Call this from Update() in your MonoBehaviour.
        /// </summary>
        public void ProcessMessageQueue()
        {
            while (_messageQueue.TryDequeue(out var message))
            {
                try
                {
                    OnMessageReceived?.Invoke(message);
                }
                catch (Exception ex)
                {
                    Debug.LogError($"[RuntimeWebSocketClient] Error processing message: {ex}");
                }
            }
        }

        #endregion

        #region Private Methods

        private async Task ReceiveLoopAsync()
        {
            if (_webSocket == null) return;

            var buffer = new byte[8192];

            try
            {
                while (IsConnected && !_cancellationTokenSource!.IsCancellationRequested)
                {
                    var segment = new ArraySegment<byte>(buffer);
                    var result = await _webSocket.ReceiveAsync(
                        segment, 
                        _cancellationTokenSource.Token
                    );

                    if (result.MessageType == System.Net.WebSockets.WebSocketMessageType.Close)
                    {
                        break;
                    }

                    if (result.MessageType == System.Net.WebSockets.WebSocketMessageType.Text)
                    {
                        var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                        _messageQueue.Enqueue(message);
                    }
                }
            }
            catch (OperationCanceledException)
            {
                // Normal cancellation
            }
            catch (Exception ex)
            {
                Debug.LogError($"[RuntimeWebSocketClient] Receive error: {ex.Message}");
                OnError?.Invoke(ex.Message);
            }
            finally
            {
                OnDisconnected?.Invoke();
                Cleanup();
            }
        }

        private void Cleanup()
        {
            lock (_lock)
            {
                _cancellationTokenSource?.Cancel();
                _cancellationTokenSource?.Dispose();
                _cancellationTokenSource = null;

                _webSocket?.Dispose();
                _webSocket = null;
            }
        }

        #endregion

        #region IDisposable

        public void Dispose()
        {
            _ = DisconnectAsync();
        }

        #endregion
    }
}
