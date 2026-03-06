"""Core module for MCP server configuration and capabilities."""

from core.capability_flags import (
    CapabilityConfig,
    TOOLS_SUPPORTING_DRY_RUN,
    LOCAL_ONLY_TOOLS,
    RUNTIME_ONLY_TOOLS,
    HIGH_RISK_TOOLS,
    TOOLS_SUPPORTING_VERIFICATION,
    supports_dry_run,
    is_local_only_tool,
    is_runtime_only_tool,
    requires_explicit_opt_in,
    supports_verification,
    get_tool_capability_flags,
    load_capability_config,
    get_capability_config,
    set_capability_config,
    reload_capability_config,
)
from core.config import ServerConfig, config

__all__ = [
    # Capability flags
    "CapabilityConfig",
    "TOOLS_SUPPORTING_DRY_RUN",
    "LOCAL_ONLY_TOOLS",
    "RUNTIME_ONLY_TOOLS",
    "HIGH_RISK_TOOLS",
    "TOOLS_SUPPORTING_VERIFICATION",
    "supports_dry_run",
    "is_local_only_tool",
    "is_runtime_only_tool",
    "requires_explicit_opt_in",
    "supports_verification",
    "get_tool_capability_flags",
    "load_capability_config",
    "get_capability_config",
    "set_capability_config",
    "reload_capability_config",
    # Configuration
    "ServerConfig",
    "config",
]
