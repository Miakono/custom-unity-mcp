"""Tests for capability flags system."""

import json
import tempfile
from pathlib import Path

import pytest

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
    set_capability_config,
    reload_capability_config,
    get_capability_config,
)


class TestCapabilityFlags:
    """Test basic capability flag functions."""

    def test_supports_dry_run_with_valid_tool(self):
        assert supports_dry_run("apply_text_edits") is True
        assert supports_dry_run("create_script") is True

    def test_supports_dry_run_with_invalid_tool(self):
        assert supports_dry_run("nonexistent_tool") is False
        assert supports_dry_run(None) is False
        assert supports_dry_run("") is False

    def test_is_local_only_tool(self):
        assert is_local_only_tool("debug_request_context") is True
        assert is_local_only_tool("manage_catalog") is True
        assert is_local_only_tool("manage_scene") is False
        assert is_local_only_tool(None) is False

    def test_is_runtime_only_tool(self):
        assert is_runtime_only_tool("read_console") is True
        assert is_runtime_only_tool("get_runtime_status") is True
        assert is_runtime_only_tool("manage_scene") is False
        assert is_runtime_only_tool(None) is False

    def test_supports_verification(self):
        assert supports_verification("manage_script") is True
        assert supports_verification("apply_text_edits") is True
        assert supports_verification("manage_checkpoints") is True
        assert supports_verification("debug_request_context") is False
        assert supports_verification(None) is False

    def test_get_tool_capability_flags(self):
        flags = get_tool_capability_flags("apply_text_edits")
        assert flags["supports_dry_run"] is True
        assert flags["local_only"] is False
        assert flags["runtime_only"] is False
        assert flags["supports_verification"] is True

        flags = get_tool_capability_flags("debug_request_context")
        assert flags["local_only"] is True

        flags = get_tool_capability_flags("read_console")
        assert flags["runtime_only"] is True

        flags = get_tool_capability_flags(None)
        assert all(not v for v in flags.values())


class TestCapabilityConfig:
    """Test CapabilityConfig dataclass."""

    def test_default_config(self):
        config = CapabilityConfig()
        assert config.enable_dry_run is True
        assert config.enable_high_risk_tools is True
        assert config.require_explicit_opt_in is False
        assert config.enable_runtime_only_tools is True
        assert config.enable_local_only_tools is True
        assert config.enable_verification is True

    def test_is_tool_enabled_default(self):
        config = CapabilityConfig()
        assert config.is_tool_enabled("any_tool") is True
        assert config.is_tool_enabled("any_tool", is_high_risk=True) is True

    def test_is_tool_disabled_when_opt_in_required(self):
        config = CapabilityConfig(
            require_explicit_opt_in=True,
        )
        # Non-high-risk tools are enabled
        assert config.is_tool_enabled("manage_scene", is_high_risk=False) is True
        # High-risk tools are disabled without explicit opt-in
        assert config.is_tool_enabled("delete_script", is_high_risk=True) is False

    def test_is_tool_enabled_with_override(self):
        config = CapabilityConfig(
            require_explicit_opt_in=True,
            tool_opt_in={"delete_script": True},
        )
        # Tool with explicit opt-in is enabled
        assert config.is_tool_enabled("delete_script", is_high_risk=True) is True
        # Other high-risk tools still disabled
        assert config.is_tool_enabled("execute_menu_item", is_high_risk=True) is False

    def test_requires_explicit_opt_in_with_override(self):
        config = CapabilityConfig(
            tool_opt_in={"delete_script": True},
        )
        # Tool already opted in doesn't require opt-in again
        assert config.requires_explicit_opt_in("delete_script") is False


class TestLoadCapabilityConfig:
    """Test configuration file loading."""

    def test_load_default_when_no_file(self):
        config = load_capability_config("/nonexistent/path.json")
        assert config.enable_dry_run is True
        assert config.config_path == Path("/nonexistent/path.json")

    def test_load_valid_config_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "enable_dry_run": False,
                "require_explicit_opt_in": True,
                "tool_opt_in": {"execute_menu_item": True},
            }, f)
            temp_path = f.name

        try:
            config = load_capability_config(temp_path)
            assert config.enable_dry_run is False
            assert config.require_explicit_opt_in is True
            assert config.tool_opt_in == {"execute_menu_item": True}
        finally:
            Path(temp_path).unlink()

    def test_load_invalid_json_returns_defaults(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json")
            temp_path = f.name

        try:
            config = load_capability_config(temp_path)
            # Should return defaults on parse error
            assert config.enable_dry_run is True
        finally:
            Path(temp_path).unlink()

    def test_reload_capability_config(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"enable_dry_run": False}, f)
            temp_path = f.name

        try:
            config = reload_capability_config(temp_path)
            assert config.enable_dry_run is False
            # Verify it was set as global
            assert get_capability_config().enable_dry_run is False
            # Restore defaults
            set_capability_config(CapabilityConfig())
        finally:
            Path(temp_path).unlink()


class TestToolSets:
    """Test that tool sets are properly defined."""

    def test_dry_run_tools_is_set(self):
        assert "apply_text_edits" in TOOLS_SUPPORTING_DRY_RUN
        assert "script_apply_edits" in TOOLS_SUPPORTING_DRY_RUN
        assert "manage_script" in TOOLS_SUPPORTING_DRY_RUN

    def test_local_only_tools_is_set(self):
        assert "debug_request_context" in LOCAL_ONLY_TOOLS
        assert "manage_catalog" in LOCAL_ONLY_TOOLS
        assert "manage_checkpoints" in LOCAL_ONLY_TOOLS
        assert "manage_tools" in LOCAL_ONLY_TOOLS

    def test_runtime_only_tools_is_set(self):
        assert "read_console" in RUNTIME_ONLY_TOOLS
        assert "get_runtime_status" in RUNTIME_ONLY_TOOLS

    def test_high_risk_tools_is_set(self):
        assert "delete_script" in HIGH_RISK_TOOLS
        assert "execute_menu_item" in HIGH_RISK_TOOLS
        assert "batch_execute" in HIGH_RISK_TOOLS

    def test_verification_tools_is_set(self):
        assert "manage_script" in TOOLS_SUPPORTING_VERIFICATION
        assert "script_apply_edits" in TOOLS_SUPPORTING_VERIFICATION
        assert "create_script" in TOOLS_SUPPORTING_VERIFICATION
