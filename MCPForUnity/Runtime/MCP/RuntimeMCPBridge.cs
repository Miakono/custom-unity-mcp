// -----------------------------------------------------------------------
// RuntimeMCPBridge.cs
// Main bridge for Runtime/In-Game MCP support
// 
// This component provides the foundation for MCP connectivity in Play Mode
// and Built Games. It operates independently from Editor MCP.
// -----------------------------------------------------------------------

#nullable enable

using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using MCPForUnity.Runtime.Tools;
using MCPForUnity.Runtime.UI;
using UnityEngine;

namespace MCPForUnity.Runtime.MCP
{
    /// <summary>
    /// Runtime context type for the MCP bridge
    /// </summary>
    public enum RuntimeContextType
    {
        PlayMode,
        BuiltGame,
        DevelopmentBuild,
        Unknown
    }

    /// <summary>
    /// Main bridge for Runtime MCP connectivity.
    /// 
    /// Attach this component to a GameObject in your scene to enable
    /// MCP connectivity during Play Mode or in Built Games.
    /// 
    /// Runtime tools are CLEARLY tagged as runtime_only and NEVER
    /// appear in editor-only environments.
    /// </summary>
    [AddComponentMenu("MCP/Runtime MCP Bridge")]
    [DefaultExecutionOrder(-100)] // Initialize early
    public class RuntimeMCPBridge : MonoBehaviour
    {
        #region Singleton Pattern
        
        private static RuntimeMCPBridge? _instance;
        
        /// <summary>
        /// Get the singleton instance of the Runtime MCP Bridge
        /// </summary>
        public static RuntimeMCPBridge? Instance => _instance;
        
        #endregion

        #region Configuration

        [Header("Connection Settings")]
        [Tooltip("Server host address")]
        [SerializeField] private string serverHost = "127.0.0.1";
        
        [Tooltip("Server WebSocket port (default: 8090 for runtime, separate from editor)")]
        [SerializeField] private int serverPort = 8090;
        
        [Tooltip("Auto-connect on Start")]
        [SerializeField] private bool autoConnect = true;
        
        [Tooltip("Reconnect on disconnect")]
        [SerializeField] private bool autoReconnect = true;
        
        [Tooltip("Reconnect delay in seconds")]
        [SerializeField] private float reconnectDelay = 5f;

        [Header("Runtime Context")]
        [Tooltip("Project name identifier")]
        [SerializeField] private string projectName = "";
        
        [Tooltip("Additional capability metadata")]
        [SerializeField] private List<string> capabilities = new();

        [Header("Debug")]
        [Tooltip("Enable verbose logging")]
        [SerializeField] private bool verboseLogging = false;

        #endregion

        #region Properties

        /// <summary>
        /// Current runtime context type
        /// </summary>
        public RuntimeContextType ContextType { get; private set; } = RuntimeContextType.Unknown;
        
        /// <summary>
        /// Whether the bridge is currently connected
        /// </summary>
        public bool IsConnected => _webSocketClient?.IsConnected ?? false;
        
        /// <summary>
        /// Session ID assigned by the server
        /// </summary>
        public string? SessionId { get; private set; }
        
        /// <summary>
        /// Server-assigned capabilities
        /// </summary>
        public IReadOnlyDictionary<string, object> ServerCapabilities => _serverCapabilities;

        /// <summary>
        /// Runtime tool registry
        /// </summary>
        public RuntimeToolRegistry ToolRegistry { get; private set; } = null!;
        
        /// <summary>
        /// Command processor for runtime commands
        /// </summary>
        public RuntimeCommandProcessor CommandProcessor { get; private set; } = null!;

        #endregion

        #region Private Fields

        private RuntimeWebSocketClient? _webSocketClient;
        private readonly Dictionary<string, object> _serverCapabilities = new();
        private bool _isConnecting;
        private float _reconnectTimer;
        private bool _shouldReconnect;

        #endregion

        #region Unity Lifecycle

        private void Awake()
        {
            // Singleton setup
            if (_instance != null && _instance != this)
            {
                Debug.LogWarning("[RuntimeMCPBridge] Multiple instances detected. Destroying duplicate.");
                Destroy(gameObject);
                return;
            }
            
            _instance = this;
            
            // Don't destroy on load to persist across scenes
            if (transform.parent == null)
            {
                DontDestroyOnLoad(gameObject);
            }
            
            // Determine runtime context
            DetectRuntimeContext();
            
            // Initialize components
            InitializeComponents();
            
            LogInfo($"RuntimeMCPBridge initialized. Context: {ContextType}");
        }

        private void Start()
        {
            if (autoConnect)
            {
                _ = ConnectAsync();
            }
        }

        private void Update()
        {
            // Process WebSocket messages on main thread
            _webSocketClient?.ProcessMessageQueue();
            
            // Handle reconnection
            if (_shouldReconnect && autoReconnect)
            {
                _reconnectTimer += Time.deltaTime;
                if (_reconnectTimer >= reconnectDelay)
                {
                    _reconnectTimer = 0f;
                    _shouldReconnect = false;
                    _ = ConnectAsync();
                }
            }
        }

        private void OnDestroy()
        {
            if (_instance == this)
            {
                _instance = null;
            }
            
            _ = DisconnectAsync();
        }

        private void OnApplicationQuit()
        {
            _webSocketClient?.Close();
        }

        #endregion

        #region Initialization

        private void DetectRuntimeContext()
        {
            #if UNITY_EDITOR
                ContextType = RuntimeContextType.PlayMode;
            #else
                if (Debug.isDebugBuild)
                {
                    ContextType = RuntimeContextType.DevelopmentBuild;
                }
                else
                {
                    ContextType = RuntimeContextType.BuiltGame;
                }
            #endif
            
            // Auto-populate project name if empty
            if (string.IsNullOrEmpty(projectName))
            {
                projectName = Application.productName;
            }
        }

        private void InitializeComponents()
        {
            ToolRegistry = new RuntimeToolRegistry();
            CommandProcessor = new RuntimeCommandProcessor(this);
            _webSocketClient = new RuntimeWebSocketClient();
            
            // Register default runtime tools
            RegisterDefaultTools();
        }

        private void RegisterDefaultTools()
        {
            // Register tools from separate tool classes
            RuntimeGameObjectTools.Register(ToolRegistry);
            RuntimeSceneTools.Register(ToolRegistry);
            RuntimeInputTools.Register(ToolRegistry);
            
            LogInfo($"Registered {ToolRegistry.Count} runtime tools");
        }

        #endregion

        #region Connection Management

        /// <summary>
        /// Connect to the MCP server
        /// </summary>
        public async Task<bool> ConnectAsync()
        {
            if (_isConnecting || IsConnected)
            {
                return IsConnected;
            }

            _isConnecting = true;
            
            try
            {
                LogInfo($"Connecting to MCP server at {serverHost}:{serverPort}...");
                
                var url = $"ws://{serverHost}:{serverPort}/runtime";
                bool connected = await _webSocketClient!.ConnectAsync(url);
                
                if (connected)
                {
                    // Set up message handlers
                    _webSocketClient.OnMessageReceived += OnWebSocketMessage;
                    _webSocketClient.OnDisconnected += OnWebSocketDisconnected;
                    
                    // Send registration
                    await SendRegistrationAsync();
                    
                    LogInfo("Connected to MCP server successfully");
                    return true;
                }
                else
                {
                    LogWarning("Failed to connect to MCP server");
                    _shouldReconnect = autoReconnect;
                    return false;
                }
            }
            catch (Exception ex)
            {
                LogError($"Connection error: {ex.Message}");
                _shouldReconnect = autoReconnect;
                return false;
            }
            finally
            {
                _isConnecting = false;
            }
        }

        /// <summary>
        /// Disconnect from the MCP server
        /// </summary>
        public async Task DisconnectAsync()
        {
            if (_webSocketClient == null) return;
            
            _webSocketClient.OnMessageReceived -= OnWebSocketMessage;
            _webSocketClient.OnDisconnected -= OnWebSocketDisconnected;
            
            await _webSocketClient.DisconnectAsync();
            SessionId = null;
            
            LogInfo("Disconnected from MCP server");
        }

        private async Task SendRegistrationAsync()
        {
            var registration = new
            {
                type = "register",
                project_name = projectName,
                project_hash = GenerateProjectHash(),
                unity_version = Application.unityVersion,
                build_target = Application.platform.ToString(),
                is_play_mode = ContextType == RuntimeContextType.PlayMode,
                is_build = ContextType != RuntimeContextType.PlayMode,
                capabilities = new
                {
                    runtime_only = true,
                    requires_runtime_context = true,
                    supports_gameobjects = true,
                    supports_scene_queries = true,
                    supports_input_simulation = true,
                    domain = "runtime",
                    custom_capabilities = capabilities
                },
                metadata = new
                {
                    runtime_version = Application.version,
                    system_language = Application.systemLanguage.ToString(),
                    target_frame_rate = Application.targetFrameRate,
                    screen_resolution = new[] { Screen.width, Screen.height }
                }
            };
            
            await _webSocketClient!.SendAsync(registration);
        }

        private string GenerateProjectHash()
        {
            // Generate a stable hash based on project name and company
            string input = $"{Application.productName}:{Application.companyName}:{Application.unityVersion}";
            int hash = input.GetHashCode();
            return Math.Abs(hash).ToString("X8");
        }

        #endregion

        #region Message Handling

        private void OnWebSocketMessage(string message)
        {
            try
            {
                var data = MiniJSON.Deserialize(message) as Dictionary<string, object>;
                if (data == null) return;
                
                string messageType = data.GetValueOrDefault("type", "").ToString()!;
                
                switch (messageType)
                {
                    case "welcome":
                        HandleWelcomeMessage(data);
                        break;
                        
                    case "registered":
                        HandleRegisteredMessage(data);
                        break;
                        
                    case "execute_command":
                        _ = HandleExecuteCommandAsync(data);
                        break;
                        
                    case "ping":
                        HandlePingMessage(data);
                        break;
                        
                    default:
                        LogVerbose($"Unhandled message type: {messageType}");
                        break;
                }
            }
            catch (Exception ex)
            {
                LogError($"Error handling message: {ex.Message}");
            }
        }

        private void OnWebSocketDisconnected()
        {
            LogWarning("WebSocket disconnected");
            SessionId = null;
            _shouldReconnect = autoReconnect;
        }

        private void HandleWelcomeMessage(Dictionary<string, object> data)
        {
            LogInfo("Received welcome from server");
        }

        private void HandleRegisteredMessage(Dictionary<string, object> data)
        {
            SessionId = data.GetValueOrDefault("session_id", "").ToString();
            LogInfo($"Registered with session ID: {SessionId}");
            
            // Send tool registration
            _ = SendToolRegistrationAsync();
        }

        private async Task SendToolRegistrationAsync()
        {
            var tools = ToolRegistry.GetToolDefinitions();
            
            var registration = new
            {
                type = "register_tools",
                tools = tools,
                domain = "runtime"
            };
            
            await _webSocketClient!.SendAsync(registration);
            LogInfo($"Registered {tools.Count} tools with server");
        }

        private async Task HandleExecuteCommandAsync(Dictionary<string, object> data)
        {
            string commandId = data.TryGetValue("id", out var idVal) ? idVal?.ToString() ?? "" : "";
            string commandName = data.TryGetValue("name", out var nameVal) ? nameVal?.ToString() ?? "" : "";
            var parameters = data.TryGetValue("params", out var paramsVal) ? paramsVal as Dictionary<string, object> : null;
            
            LogVerbose($"Executing command: {commandName} (ID: {commandId})");
            
            var result = await CommandProcessor.ExecuteCommandAsync(commandName, parameters ?? new Dictionary<string, object>());
            
            var response = new
            {
                type = "command_result",
                id = commandId,
                result = result
            };
            
            await _webSocketClient!.SendAsync(response);
        }

        private void HandlePingMessage(Dictionary<string, object> data)
        {
            // Respond with pong
            var pong = new
            {
                type = "pong",
                session_id = SessionId
            };
            
            _ = _webSocketClient!.SendAsync(pong);
        }

        #endregion

        #region Public API

        /// <summary>
        /// Get runtime status information
        /// </summary>
        public Dictionary<string, object> GetStatus()
        {
            return new Dictionary<string, object>
            {
                ["connected"] = IsConnected,
                ["session_id"] = SessionId ?? string.Empty,
                ["context_type"] = ContextType.ToString(),
                ["project_name"] = projectName,
                ["unity_version"] = Application.unityVersion,
                ["platform"] = Application.platform.ToString(),
                ["tool_count"] = ToolRegistry.Count,
                ["active_scene"] = UnityEngine.SceneManagement.SceneManager.GetActiveScene().name,
                ["time_scale"] = Time.timeScale,
                ["frame_count"] = Time.frameCount,
                ["runtime_only"] = true,
                ["requires_runtime_context"] = true,
                ["domain"] = "runtime"
            };
        }

        /// <summary>
        /// Get connection information
        /// </summary>
        public Dictionary<string, object> GetConnectionInfo()
        {
            return new Dictionary<string, object>
            {
                ["server_host"] = serverHost,
                ["server_port"] = serverPort,
                ["websocket_url"] = $"ws://{serverHost}:{serverPort}/runtime",
                ["connected"] = IsConnected,
                ["session_id"] = SessionId ?? string.Empty,
                ["runtime_only"] = true,
                ["separate_connection"] = true,
                ["runtime_port"] = serverPort
            };
        }

        #endregion

        #region Logging

        private void LogInfo(string message)
        {
            Debug.Log($"[RuntimeMCP] {message}");
        }

        private void LogWarning(string message)
        {
            Debug.LogWarning($"[RuntimeMCP] {message}");
        }

        private void LogError(string message)
        {
            Debug.LogError($"[RuntimeMCP] {message}");
        }

        private void LogVerbose(string message)
        {
            if (verboseLogging)
            {
                Debug.Log($"[RuntimeMCP] {message}");
            }
        }

        #endregion
    }
}
