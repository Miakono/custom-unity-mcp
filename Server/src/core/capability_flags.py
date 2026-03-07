"""
Central capability flag registry for MCP tools.

This module provides:
- Capability flag definitions for tools
- Feature flag system for opt-in features
- Config file loading for capabilities
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Tool names that support dry-run mode (preview without applying changes)
TOOLS_SUPPORTING_DRY_RUN: set[str] = {
    # Script editing tools
    "apply_text_edits",
    "script_apply_edits",
    "create_script",
    "delete_script",
    "manage_script",
    # Scene management
    "manage_scene",
    # GameObject management
    "manage_gameobject",
    # Component management
    "manage_components",
    # Asset management
    "manage_asset",
    # Material management
    "manage_material",
    # Prefab management
    "manage_prefabs",
    # Shader management
    "manage_shader",
    # Texture management
    "manage_texture",
    # UI management
    "manage_ui",
    # VFX management
    "manage_vfx",
    # Animation management
    "manage_animation",
    # ScriptableObject management
    "manage_scriptable_object",
    # Batch operations
    "batch_execute",
    # Checkpoint/restore operations
    "manage_checkpoints",
}

# Tools that are local/server-only (don't require Unity connection)
LOCAL_ONLY_TOOLS: set[str] = {
    "debug_request_context",
    "manage_catalog",
    "manage_checkpoints",
    "manage_code_intelligence",
    "manage_error_catalog",
    "manage_script_capabilities",
    "manage_subagents",
    "manage_tools",
    "search_code",
    "find_symbol",
    "find_references",
    "get_symbols",
    "build_code_index",
    "code_index_status",
    "preflight_audit",
    "set_active_instance",
    "validate_compile_health",
}

# Tools that only work when Unity is in play mode
RUNTIME_ONLY_TOOLS: set[str] = {
    "execute_runtime_command",
    "get_runtime_connection_info",
    "get_runtime_status",
    "list_runtime_tools",
    "manage_runtime_ui",
    "read_console",
}

# High-risk tools that require explicit opt-in via configuration
HIGH_RISK_TOOLS: set[str] = {
    # Destructive operations
    "delete_script",
    "execute_menu_item",
    # High-impact batch operations
    "batch_execute",
    # Tools that can modify project structure
    "manage_scriptable_object",
    # Tools that can execute arbitrary code
    "execute_custom_tool",
    # Scene deletion operations
    "manage_scene",  # Only certain actions are high-risk
    # GameObject deletion
    "manage_gameobject",  # Only delete action
}

# Tools that support verification (post-operation confirmation)
TOOLS_SUPPORTING_VERIFICATION: set[str] = {
    # Script editing tools
    "manage_script",
    "script_apply_edits",
    "apply_text_edits",
    "create_script",
    "delete_script",
    # GameObject operations
    "manage_gameobject",
    # Prefab operations
    "manage_prefabs",
    # Scene operations
    "manage_scene",
    # Component operations
    "manage_components",
    # Asset operations
    "manage_asset",
    # Checkpoint workflows
    "manage_checkpoints",
}


@dataclass
class CapabilityConfig:
    """Configuration for tool capabilities and feature flags."""

    # Feature flags
    enable_dry_run: bool = True
    enable_high_risk_tools: bool = True
    require_explicit_opt_in: bool = False
    enable_runtime_only_tools: bool = True
    enable_local_only_tools: bool = True
    enable_verification: bool = True

    # Tool-specific opt-in settings (overrides global settings)
    tool_opt_in: dict[str, bool] = field(default_factory=dict)

    # Paths
    config_path: Path | None = None

    def is_tool_enabled(self, tool_name: str, is_high_risk: bool = False) -> bool:
        """Check if a tool is enabled based on configuration."""
        # Check tool-specific override first
        if tool_name in self.tool_opt_in:
            return self.tool_opt_in[tool_name]

        # If global explicit opt-in is required and tool is high-risk
        if self.require_explicit_opt_in and is_high_risk:
            return False

        return True

    def requires_explicit_opt_in(self, tool_name: str) -> bool:
        """Check if a tool requires explicit opt-in."""
        if tool_name in self.tool_opt_in:
            return False  # Already explicitly configured

        # Runtime-only tools and high-risk tools require explicit opt-in by default.
        return tool_name in HIGH_RISK_TOOLS or tool_name in RUNTIME_ONLY_TOOLS


# Global capability configuration instance
_capability_config: CapabilityConfig | None = None


def get_default_config_paths() -> list[Path]:
    """Return default paths to search for capability configuration."""
    paths: list[Path] = []

    # Current working directory
    paths.append(Path.cwd() / "mcp_capabilities.json")

    # User home directory
    paths.append(Path.home() / ".config" / "mcp-for-unity" / "capabilities.json")

    # Platform-specific locations
    if os.name == "nt":  # Windows
        app_data = os.environ.get("APPDATA")
        if app_data:
            paths.append(Path(app_data) / "MCPForUnity" / "capabilities.json")
    else:  # Unix-like
        paths.append(Path.home() / ".mcp-for-unity" / "capabilities.json")

    # Server installation directory
    server_dir = Path(__file__).resolve().parents[1]
    paths.append(server_dir / "config" / "capabilities.json")

    return paths


def load_capability_config(path: str | Path | None = None) -> CapabilityConfig:
    """Load capability configuration from file.

    Args:
        path: Path to configuration file. If None, searches default locations.

    Returns:
        CapabilityConfig instance
    """
    if path is not None:
        config_path = Path(path)
        if config_path.exists():
            return _parse_config_file(config_path)
        else:
            # Return default config with the specified path
            return CapabilityConfig(config_path=config_path)
    else:
        for default_path in get_default_config_paths():
            if default_path.exists():
                return _parse_config_file(default_path)

    # Return default configuration if no file found
    return CapabilityConfig()


def _parse_config_file(path: Path) -> CapabilityConfig:
    """Parse a capability configuration file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = CapabilityConfig(
            config_path=path,
            enable_dry_run=data.get("enable_dry_run", True),
            enable_high_risk_tools=data.get("enable_high_risk_tools", True),
            require_explicit_opt_in=data.get("require_explicit_opt_in", False),
            enable_runtime_only_tools=data.get("enable_runtime_only_tools", True),
            enable_local_only_tools=data.get("enable_local_only_tools", True),
            enable_verification=data.get("enable_verification", True),
            tool_opt_in=data.get("tool_opt_in", {}),
        )
        return config
    except (json.JSONDecodeError, IOError, KeyError) as e:
        # Log error and return defaults
        import logging
        logging.getLogger(__name__).warning(f"Failed to load capability config from {path}: {e}")
        return CapabilityConfig(config_path=path)


def get_capability_config() -> CapabilityConfig:
    """Get the global capability configuration (lazy-loaded)."""
    global _capability_config
    if _capability_config is None:
        _capability_config = load_capability_config()
    return _capability_config


def set_capability_config(config: CapabilityConfig) -> None:
    """Set the global capability configuration."""
    global _capability_config
    _capability_config = config


def reload_capability_config(path: str | Path | None = None) -> CapabilityConfig:
    """Reload capability configuration from file."""
    config = load_capability_config(path)
    set_capability_config(config)
    return config


def supports_dry_run(tool_name: str | None) -> bool:
    """Check if a tool supports dry-run mode."""
    if not tool_name:
        return False
    config = get_capability_config()
    if not config.enable_dry_run:
        return False
    return tool_name in TOOLS_SUPPORTING_DRY_RUN


def is_local_only_tool(tool_name: str | None) -> bool:
    """Check if a tool is local/server-only (doesn't require Unity)."""
    if not tool_name:
        return False
    config = get_capability_config()
    if not config.enable_local_only_tools:
        return False
    return tool_name in LOCAL_ONLY_TOOLS


def is_runtime_only_tool(tool_name: str | None) -> bool:
    """Check if a tool only works in Unity play mode."""
    if not tool_name:
        return False
    config = get_capability_config()
    if not config.enable_runtime_only_tools:
        return False
    return tool_name in RUNTIME_ONLY_TOOLS


def requires_explicit_opt_in(tool_name: str | None) -> bool:
    """Check if a tool requires explicit opt-in.

    Returns True if the tool is high-risk and hasn't been explicitly opted into.
    """
    if not tool_name:
        return False
    config = get_capability_config()
    return config.requires_explicit_opt_in(tool_name)


def supports_verification(tool_name: str | None) -> bool:
    """Check if a tool supports verification."""
    if not tool_name:
        return False
    config = get_capability_config()
    if not config.enable_verification:
        return False
    return tool_name in TOOLS_SUPPORTING_VERIFICATION


def get_tool_capability_flags(tool_name: str | None) -> dict[str, bool]:
    """Get all capability flags for a tool as a dictionary."""
    return {
        "supports_dry_run": supports_dry_run(tool_name),
        "local_only": is_local_only_tool(tool_name),
        "runtime_only": is_runtime_only_tool(tool_name),
        "requires_explicit_opt_in": requires_explicit_opt_in(tool_name),
        "supports_verification": supports_verification(tool_name),
    }


# Example/sample configuration file content
SAMPLE_CONFIG = """{
  "enable_dry_run": true,
  "enable_high_risk_tools": true,
  "require_explicit_opt_in": false,
  "enable_runtime_only_tools": true,
  "enable_local_only_tools": true,
  "enable_verification": true,
  "tool_opt_in": {
    "execute_menu_item": true,
    "batch_execute": true,
    "delete_script": true
  }
}
"""
