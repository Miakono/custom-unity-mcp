"""
Runtime Connection Manager - Manages WebSocket connections to Unity Runtime/Play Mode.

This module provides a separate connection path for Runtime MCP, distinct from
Editor MCP connections. Runtime connections operate on a different port and use
a separate protocol optimized for in-game scenarios.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket, WebSocketState

logger = logging.getLogger(__name__)


class RuntimeConnectionState(Enum):
    """States for a runtime connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    READY = "ready"
    ERROR = "error"


@dataclass
class RuntimeSession:
    """Information about an active runtime session."""
    session_id: str
    project_name: str
    project_hash: str
    unity_version: str
    build_target: str
    is_play_mode: bool
    is_build: bool
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    state: RuntimeConnectionState = RuntimeConnectionState.CONNECTED
    capabilities: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "project_name": self.project_name,
            "project_hash": self.project_hash,
            "unity_version": self.unity_version,
            "build_target": self.build_target,
            "is_play_mode": self.is_play_mode,
            "is_build": self.is_build,
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
            "state": self.state.value,
            "capabilities": self.capabilities,
            "tool_count": len(self.tools),
            "metadata": self.metadata,
        }


class RuntimeRegistry:
    """
    Registry for tracking active runtime sessions.
    
    This is separate from the Editor PluginRegistry to maintain clear separation
    between Editor and Runtime domains.
    """
    
    _instance: ClassVar[RuntimeRegistry | None] = None
    _lock: asyncio.Lock | None = None
    
    def __new__(cls) -> RuntimeRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sessions: dict[str, RuntimeSession] = {}
            cls._instance._connections: dict[str, WebSocket] = {}
            cls._instance._project_to_session: dict[str, str] = {}
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> RuntimeRegistry:
        """Get the singleton instance of the runtime registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def register(
        self,
        session_id: str,
        project_name: str,
        project_hash: str,
        unity_version: str,
        build_target: str,
        is_play_mode: bool,
        is_build: bool,
        capabilities: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeSession:
        """Register a new runtime session."""
        if self._lock is None:
            self._lock = asyncio.Lock()
            
        async with self._lock:
            session = RuntimeSession(
                session_id=session_id,
                project_name=project_name,
                project_hash=project_hash,
                unity_version=unity_version,
                build_target=build_target,
                is_play_mode=is_play_mode,
                is_build=is_build,
                capabilities=capabilities or {},
                metadata=metadata or {},
            )
            self._sessions[session_id] = session
            self._project_to_session[project_hash] = session_id
            logger.info(
                f"Runtime session registered: {project_name} ({project_hash}) "
                f"[play_mode={is_play_mode}, build={is_build}]"
            )
            return session
    
    async def unregister(self, session_id: str) -> bool:
        """Unregister a runtime session."""
        if self._lock is None:
            self._lock = asyncio.Lock()
            
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            self._connections.pop(session_id, None)
            if session:
                self._project_to_session.pop(session.project_hash, None)
                logger.info(f"Runtime session unregistered: {session_id}")
                return True
            return False
    
    async def get_session(self, session_id: str) -> RuntimeSession | None:
        """Get a runtime session by ID."""
        return self._sessions.get(session_id)
    
    async def get_session_by_project(self, project_hash: str) -> RuntimeSession | None:
        """Get a runtime session by project hash."""
        session_id = self._project_to_session.get(project_hash)
        if session_id:
            return self._sessions.get(session_id)
        return None
    
    async def list_sessions(self) -> dict[str, RuntimeSession]:
        """List all active runtime sessions."""
        return self._sessions.copy()
    
    async def update_heartbeat(self, session_id: str) -> bool:
        """Update the last heartbeat time for a session."""
        session = self._sessions.get(session_id)
        if session:
            session.last_heartbeat = time.time()
            return True
        return False
    
    async def update_tools(self, session_id: str, tools: dict[str, Any]) -> bool:
        """Update the tools available for a session."""
        session = self._sessions.get(session_id)
        if session:
            session.tools = tools
            return True
        return False
    
    async def update_state(
        self,
        session_id: str,
        state: RuntimeConnectionState
    ) -> bool:
        """Update the connection state for a session."""
        session = self._sessions.get(session_id)
        if session:
            session.state = state
            return True
        return False
    
    async def set_connection(self, session_id: str, websocket: WebSocket) -> bool:
        """Store the WebSocket connection for a session."""
        if self._lock is None:
            self._lock = asyncio.Lock()
            
        async with self._lock:
            if session_id in self._sessions:
                self._connections[session_id] = websocket
                return True
            return False
    
    async def get_connection(self, session_id: str) -> WebSocket | None:
        """Get the WebSocket connection for a session."""
        return self._connections.get(session_id)
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics about runtime connections."""
        play_mode_count = sum(1 for s in self._sessions.values() if s.is_play_mode)
        build_count = sum(1 for s in self._sessions.values() if s.is_build)
        
        return {
            "total_sessions": len(self._sessions),
            "play_mode_sessions": play_mode_count,
            "build_sessions": build_count,
            "active_connections": len(self._connections),
        }


class RuntimeHub(WebSocketEndpoint):
    """
    WebSocket endpoint for Runtime MCP connections.
    
    This hub manages persistent WebSocket connections to Unity Runtime/Play Mode.
    It operates independently from the Editor PluginHub with a separate registry
    and connection logic optimized for runtime scenarios.
    
    Key differences from Editor MCP:
    - Uses separate port (configured via RUNTIME_PORT env var, default 8090)
    - Different message protocol optimized for lower latency
    - Supports both Play Mode and Built Game connections
    - Runtime-only tool visibility (tools never leak to Editor context)
    """
    
    encoding = "json"
    
    # Timing configuration - optimized for runtime scenarios
    KEEP_ALIVE_INTERVAL = 10  # More frequent than Editor due to gameplay importance
    PING_INTERVAL = 5
    PING_TIMEOUT = 15
    COMMAND_TIMEOUT = 30
    
    _registry: RuntimeRegistry | None = None
    _connections: dict[str, WebSocket] = {}
    _pending: dict[str, dict[str, Any]] = {}
    _lock: asyncio.Lock | None = None
    _last_pong: ClassVar[dict[str, float]] = {}
    _ping_tasks: ClassVar[dict[str, asyncio.Task]] = {}
    
    @classmethod
    def configure(cls, registry: RuntimeRegistry | None = None) -> None:
        """Configure the RuntimeHub with a registry."""
        cls._registry = registry or RuntimeRegistry.get_instance()
        cls._lock = asyncio.Lock()
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if the RuntimeHub is configured."""
        return cls._registry is not None and cls._lock is not None
    
    async def on_connect(self, websocket: WebSocket) -> None:
        """Handle new WebSocket connection."""
        await websocket.accept()
        logger.debug("Runtime WebSocket connection accepted")
        
        # Send welcome message with runtime-specific info
        welcome = {
            "type": "welcome",
            "server_timeout": self.SERVER_TIMEOUT,
            "keep_alive_interval": self.KEEP_ALIVE_INTERVAL,
            "domain": "runtime",
            "runtime_only": True,
        }
        await websocket.send_json(welcome)
    
    async def on_receive(self, websocket: WebSocket, data: Any) -> None:
        """Handle incoming message from runtime."""
        if not isinstance(data, dict):
            logger.warning(f"Runtime received non-object payload: {data}")
            return
        
        message_type = data.get("type")
        
        try:
            if message_type == "register":
                await self._handle_register(websocket, data)
            elif message_type == "register_tools":
                await self._handle_register_tools(websocket, data)
            elif message_type == "pong":
                await self._handle_pong(data)
            elif message_type == "command_result":
                await self._handle_command_result(data)
            elif message_type == "heartbeat":
                await self._handle_heartbeat(data)
            else:
                logger.debug(f"Ignoring runtime message: {data}")
        except Exception as e:
            logger.error(f"Error handling runtime message type {message_type}: {e}")
    
    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        """Handle WebSocket disconnection."""
        cls = type(self)
        lock = cls._lock
        if lock is None:
            return
        
        async with lock:
            session_id = next(
                (sid for sid, ws in cls._connections.items() if ws is websocket),
                None
            )
            if session_id:
                cls._connections.pop(session_id, None)
                ping_task = cls._ping_tasks.pop(session_id, None)
                if ping_task and not ping_task.done():
                    ping_task.cancel()
                cls._last_pong.pop(session_id, None)
                
                # Fail pending commands
                pending_ids = [
                    cmd_id for cmd_id, entry in cls._pending.items()
                    if entry.get("session_id") == session_id
                ]
                for cmd_id in pending_ids:
                    entry = cls._pending.pop(cmd_id, None)
                    future = entry.get("future") if isinstance(entry, dict) else None
                    if future and not future.done():
                        future.set_exception(
                            RuntimeError(f"Runtime session {session_id} disconnected")
                        )
                
                if cls._registry:
                    await cls._registry.unregister(session_id)
                
                logger.info(f"Runtime session {session_id} disconnected ({close_code})")
    
    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------
    
    async def _handle_register(self, websocket: WebSocket, data: dict) -> None:
        """Handle runtime registration message."""
        cls = type(self)
        registry = cls._registry
        lock = cls._lock
        
        if registry is None or lock is None:
            await websocket.close(code=1011)
            return
        
        project_name = data.get("project_name", "Unknown")
        project_hash = data.get("project_hash", "")
        unity_version = data.get("unity_version", "")
        build_target = data.get("build_target", "")
        is_play_mode = data.get("is_play_mode", True)
        is_build = data.get("is_build", False)
        capabilities = data.get("capabilities", {})
        
        if not project_hash:
            await websocket.close(code=4400)
            return
        
        session_id = str(uuid.uuid4())
        
        # Send registered response
        response = {
            "type": "registered",
            "session_id": session_id,
            "domain": "runtime",
        }
        await websocket.send_json(response)
        
        # Register session
        await registry.register(
            session_id=session_id,
            project_name=project_name,
            project_hash=project_hash,
            unity_version=unity_version,
            build_target=build_target,
            is_play_mode=is_play_mode,
            is_build=is_build,
            capabilities=capabilities,
        )
        
        async with lock:
            cls._connections[session_id] = websocket
            cls._last_pong[session_id] = time.time()
            
            # Start ping loop
            old_task = cls._ping_tasks.pop(session_id, None)
            if old_task and not old_task.done():
                old_task.cancel()
            ping_task = asyncio.create_task(cls._ping_loop(session_id, websocket))
            cls._ping_tasks[session_id] = ping_task
        
        logger.info(
            f"Runtime registered: {project_name} ({project_hash}) "
            f"session={session_id}"
        )
    
    async def _handle_register_tools(self, websocket: WebSocket, data: dict) -> None:
        """Handle runtime tool registration."""
        cls = type(self)
        registry = cls._registry
        lock = cls._lock
        
        if registry is None or lock is None:
            return
        
        async with lock:
            session_id = next(
                (sid for sid, ws in cls._connections.items() if ws is websocket),
                None
            )
        
        if not session_id:
            logger.warning("Received register_tools from unknown runtime connection")
            return
        
        tools = data.get("tools", [])
        await registry.update_tools(session_id, {t.get("name", "unknown"): t for t in tools})
        logger.info(f"Registered {len(tools)} runtime tools for session {session_id}")
    
    async def _handle_pong(self, data: dict) -> None:
        """Handle pong response."""
        cls = type(self)
        session_id = data.get("session_id")
        if session_id:
            if cls._registry:
                await cls._registry.update_heartbeat(session_id)
            async with cls._lock:
                cls._last_pong[session_id] = time.time()
    
    async def _handle_command_result(self, data: dict) -> None:
        """Handle command result from runtime."""
        cls = type(self)
        command_id = data.get("id")
        result = data.get("result")
        
        if not command_id:
            logger.warning(f"Runtime command result missing id: {data}")
            return
        
        async with cls._lock:
            entry = cls._pending.get(command_id)
        
        future = entry.get("future") if isinstance(entry, dict) else None
        if future and not future.done():
            future.set_result(result)
    
    async def _handle_heartbeat(self, data: dict) -> None:
        """Handle heartbeat from runtime."""
        session_id = data.get("session_id")
        if session_id and self._registry:
            await self._registry.update_heartbeat(session_id)
    
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    
    @classmethod
    async def send_command(
        cls,
        session_id: str,
        command_type: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a command to a runtime session."""
        websocket = await cls._get_connection(session_id)
        command_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        
        lock = cls._lock
        if lock is None:
            raise RuntimeError("RuntimeHub not configured")
        
        async with lock:
            cls._pending[command_id] = {
                "future": future,
                "session_id": session_id,
            }
        
        try:
            msg = {
                "type": "execute_command",
                "id": command_id,
                "name": command_type,
                "params": params,
                "timeout": cls.COMMAND_TIMEOUT,
            }
            await websocket.send_json(msg)
            result = await asyncio.wait_for(future, timeout=cls.COMMAND_TIMEOUT)
            return result
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "timeout",
                "message": f"Runtime command '{command_type}' timed out",
            }
        finally:
            async with lock:
                cls._pending.pop(command_id, None)
    
    @classmethod
    async def _get_connection(cls, session_id: str) -> WebSocket:
        """Get WebSocket connection for a session."""
        lock = cls._lock
        if lock is None:
            raise RuntimeError("RuntimeHub not configured")
        
        async with lock:
            websocket = cls._connections.get(session_id)
        
        if websocket is None:
            raise RuntimeError(f"Runtime session {session_id} not connected")
        return websocket
    
    @classmethod
    async def _ping_loop(cls, session_id: str, websocket: WebSocket) -> None:
        """Server-initiated ping loop for runtime connections."""
        logger.debug(f"[Runtime Ping] Starting for session {session_id}")
        
        try:
            while True:
                await asyncio.sleep(cls.PING_INTERVAL)
                
                lock = cls._lock
                if lock is None:
                    break
                
                async with lock:
                    if session_id not in cls._connections:
                        break
                    last_pong = cls._last_pong.get(session_id, 0)
                
                # Check staleness
                elapsed = time.time() - last_pong
                if elapsed > cls.PING_TIMEOUT:
                    logger.warning(
                        f"[Runtime Ping] Session {session_id} stale: "
                        f"no pong for {elapsed:.1f}s"
                    )
                    try:
                        await websocket.close(code=1001)
                    except Exception:
                        pass
                    break
                
                # Send ping
                try:
                    ping_msg = {"type": "ping"}
                    await websocket.send_json(ping_msg)
                except Exception as e:
                    logger.debug(f"[Runtime Ping] Failed to send ping: {e}")
                    break
                    
        except asyncio.CancelledError:
            logger.debug(f"[Runtime Ping] Cancelled for session {session_id}")
        except Exception as e:
            logger.warning(f"[Runtime Ping] Error for session {session_id}: {e}")
    
    @classmethod
    async def get_sessions(cls) -> list[dict[str, Any]]:
        """Get all active runtime sessions."""
        if cls._registry is None:
            return []
        
        sessions = await cls._registry.list_sessions()
        return [s.to_dict() for s in sessions.values()]
    
    @classmethod
    async def resolve_session_for_project(cls, project_hash: str) -> str | None:
        """Resolve project hash to runtime session ID."""
        if cls._registry is None:
            return None
        
        session = await cls._registry.get_session_by_project(project_hash)
        return session.session_id if session else None


# Convenience function for external access
def get_runtime_registry() -> RuntimeRegistry:
    """Get the global RuntimeRegistry instance."""
    return RuntimeRegistry.get_instance()
