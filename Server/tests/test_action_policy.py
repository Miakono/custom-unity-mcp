import pytest

import services.tools.action_policy as action_policy


def test_tool_action_is_mutating_classifies_key_actions():
    assert action_policy.tool_action_is_mutating("manage_asset", action="modify") is True
    assert action_policy.tool_action_is_mutating("manage_asset", action="search") is False
    assert action_policy.tool_action_is_mutating("manage_catalog", action="list") is False
    assert action_policy.tool_action_is_mutating("manage_catalog", action="export") is True
    assert action_policy.tool_action_is_mutating("manage_error_catalog", action="list") is False
    assert action_policy.tool_action_is_mutating("manage_error_catalog", action="export") is True
    assert action_policy.tool_action_is_mutating("manage_scene", action="save") is True
    assert action_policy.tool_action_is_mutating("manage_scene", action="screenshot") is False
    assert action_policy.tool_action_is_mutating("manage_prefabs", action="modify_contents") is True
    assert action_policy.tool_action_is_mutating("manage_prefabs", action="get_info") is False
    assert action_policy.tool_action_is_mutating("find_gameobjects") is False
    assert action_policy.tool_action_is_mutating("find_in_file") is False
    assert action_policy.tool_action_is_mutating("get_sha") is False
    assert action_policy.tool_action_is_mutating("get_test_job") is False
    assert action_policy.tool_action_is_mutating("manage_script_capabilities") is False
    assert action_policy.tool_action_is_mutating("manage_subagents", action="list") is False
    assert action_policy.tool_action_is_mutating("manage_subagents", action="export") is True
    assert action_policy.tool_action_is_mutating("manage_tools", action="list_groups") is False
    assert action_policy.tool_action_is_mutating("manage_tools", action="activate") is True
    assert action_policy.tool_action_is_mutating("read_console", action="get") is False
    assert action_policy.tool_action_is_mutating("read_console", action="clear") is True
    assert action_policy.tool_action_is_mutating("apply_text_edits") is True
    assert action_policy.tool_action_is_mutating("create_script") is True
    assert action_policy.tool_action_is_mutating("delete_script") is True
    assert action_policy.tool_action_is_mutating("validate_script") is False


def test_batch_policy_is_read_only_when_all_children_are_read_only():
    policy = action_policy.get_batch_policy(
        [
            {"tool": "manage_scene", "params": {"action": "get_active"}},
            {"tool": "manage_asset", "params": {"action": "search"}},
            {"tool": "find_gameobjects", "params": {"search_term": "Player"}},
        ]
    )

    assert policy.mutating is False
    assert policy.high_risk is False


def test_batch_policy_is_mutating_when_any_child_mutates():
    policy = action_policy.get_batch_policy(
        [
            {"tool": "manage_scene", "params": {"action": "get_active"}},
            {"tool": "manage_asset", "params": {"action": "modify"}},
        ]
    )

    assert policy.mutating is True
    assert policy.high_risk is True


@pytest.mark.asyncio
async def test_maybe_run_tool_preflight_skips_underlying_preflight_for_read_only(monkeypatch):
    called = False

    async def fake_preflight(*args, **kwargs):
        nonlocal called
        called = True
        return {"success": False}

    monkeypatch.setattr(action_policy, "preflight", fake_preflight)

    result = await action_policy.maybe_run_tool_preflight(
        object(),
        "manage_asset",
        action="search",
    )

    assert result is None
    assert called is False


@pytest.mark.asyncio
async def test_maybe_run_tool_preflight_calls_underlying_preflight_for_mutation(monkeypatch):
    captured = {}

    async def fake_preflight(ctx, **kwargs):
        captured["ctx"] = ctx
        captured["kwargs"] = kwargs
        return None

    monkeypatch.setattr(action_policy, "preflight", fake_preflight)
    ctx = object()

    result = await action_policy.maybe_run_tool_preflight(
        ctx,
        "manage_scene",
        action="save",
    )

    assert result is None
    assert captured["ctx"] is ctx
    assert captured["kwargs"]["wait_for_no_compile"] is True
    assert captured["kwargs"]["refresh_if_dirty"] is True


@pytest.mark.asyncio
async def test_maybe_run_tool_preflight_skips_batch_when_all_commands_are_read_only(monkeypatch):
    called = False

    async def fake_preflight(*args, **kwargs):
        nonlocal called
        called = True
        return None

    monkeypatch.setattr(action_policy, "preflight", fake_preflight)

    result = await action_policy.maybe_run_tool_preflight(
        object(),
        "batch_execute",
        commands=[
            {"tool": "manage_scene", "params": {"action": "get_active"}},
            {"tool": "manage_asset", "params": {"action": "search"}},
        ],
    )

    assert result is None
    assert called is False


@pytest.mark.asyncio
async def test_maybe_run_tool_preflight_calls_preflight_for_mutating_batch(monkeypatch):
    called = False

    async def fake_preflight(*args, **kwargs):
        nonlocal called
        called = True
        return None

    monkeypatch.setattr(action_policy, "preflight", fake_preflight)

    result = await action_policy.maybe_run_tool_preflight(
        object(),
        "batch_execute",
        commands=[
            {"tool": "manage_scene", "params": {"action": "get_active"}},
            {"tool": "manage_asset", "params": {"action": "modify"}},
        ],
    )

    assert result is None
    assert called is True


# New tests for capability flags


def test_tool_action_policy_has_capability_fields():
    """Test that ToolActionPolicy includes all new capability fields."""
    policy = action_policy.ToolActionPolicy(
        mutating=True,
        high_risk=True,
        supports_dry_run=True,
        local_only=False,
        runtime_only=False,
        requires_explicit_opt_in=True,
    )

    assert policy.mutating is True
    assert policy.high_risk is True
    assert policy.supports_dry_run is True
    assert policy.local_only is False
    assert policy.runtime_only is False
    assert policy.requires_explicit_opt_in is True


def test_get_tool_action_policy_returns_capability_flags():
    """Test that get_tool_action_policy returns correct capability flags."""
    # Script editing tools support dry-run
    policy = action_policy.get_tool_action_policy("apply_text_edits")
    assert policy.supports_dry_run is True
    assert policy.mutating is True
    assert policy.high_risk is True

    # Local-only tools
    policy = action_policy.get_tool_action_policy("debug_request_context")
    assert policy.local_only is True
    assert policy.mutating is False

    # Runtime-only tools
    policy = action_policy.get_tool_action_policy("read_console")
    assert policy.runtime_only is True

    # Read-only actions don't support dry-run (no need)
    policy = action_policy.get_tool_action_policy("manage_script", action="read")
    assert policy.mutating is False
    assert policy.supports_dry_run is False  # Read-only doesn't need dry-run


def test_get_tool_action_policy_high_risk_classification():
    """Test that high-risk tools are properly classified."""
    high_risk_tools = ["delete_script", "execute_menu_item", "batch_execute"]

    for tool in high_risk_tools:
        policy = action_policy.get_tool_action_policy(tool)
        assert policy.high_risk is True, f"{tool} should be high-risk"


def test_get_tool_action_policy_safe_tools():
    """Test that read-only tools are not marked as high-risk."""
    safe_tools = ["find_gameobjects", "get_sha", "validate_script"]

    for tool in safe_tools:
        policy = action_policy.get_tool_action_policy(tool)
        assert policy.high_risk is False, f"{tool} should not be high-risk"
        assert policy.mutating is False, f"{tool} should be read-only"


def test_get_batch_policy_aggregates_capabilities():
    """Test that batch policy aggregates capabilities from children."""
    # Mixed batch with dry-run supported and not supported
    policy = action_policy.get_batch_policy([
        {"tool": "apply_text_edits", "params": {}},  # supports dry-run
        {"tool": "execute_menu_item", "params": {}},  # doesn't support dry-run
    ])

    # Batch doesn't support dry-run if any child doesn't
    assert policy.supports_dry_run is False
    assert policy.mutating is True  # Because execute_menu_item is mutating
    assert policy.high_risk is True


def test_get_batch_policy_all_dry_run_supported():
    """Test batch where all children support dry-run."""
    policy = action_policy.get_batch_policy([
        {"tool": "apply_text_edits", "params": {}},
        {"tool": "create_script", "params": {}},
    ])

    assert policy.supports_dry_run is True


def test_get_tool_capabilities_function():
    """Test the get_tool_capabilities helper function."""
    caps = action_policy.get_tool_capabilities("apply_text_edits")

    assert "supports_dry_run" in caps
    assert "local_only" in caps
    assert "runtime_only" in caps
    assert "requires_explicit_opt_in" in caps

    assert caps["supports_dry_run"] is True
    assert caps["local_only"] is False
    assert caps["runtime_only"] is False


def test_get_tool_capabilities_local_tool():
    """Test get_tool_capabilities for local-only tools."""
    caps = action_policy.get_tool_capabilities("debug_request_context")

    assert caps["local_only"] is True
    assert caps["supports_dry_run"] is False


def test_premium_and_runtime_action_policy_classification():
    # Catalog/error catalog query actions are read-only; export remains mutating.
    assert action_policy.tool_action_is_mutating("manage_catalog", action="query") is False
    assert action_policy.tool_action_is_mutating("manage_error_catalog", action="get_code") is False
    assert action_policy.tool_action_is_mutating("manage_error_catalog", action="export") is True

    # Premium mixed tools classify read-only and mutating actions correctly.
    assert action_policy.tool_action_is_mutating("manage_input_system", action="state_get_all_actions") is False
    assert action_policy.tool_action_is_mutating("manage_input_system", action="simulate_key_press") is True
    assert action_policy.tool_action_is_mutating("manage_profiler", action="get_status") is False
    assert action_policy.tool_action_is_mutating("manage_profiler", action="start") is True
    assert action_policy.tool_action_is_mutating("manage_runtime_ui", action="find_elements") is False
    assert action_policy.tool_action_is_mutating("manage_runtime_ui", action="click") is True
    assert action_policy.tool_action_is_mutating("manage_video_capture", action="get_status") is False
    assert action_policy.tool_action_is_mutating("manage_video_capture", action="start") is True
    assert action_policy.tool_action_is_mutating("manage_reflection", action="discover_methods") is False
    assert action_policy.tool_action_is_mutating("manage_reflection", action="invoke_method") is True
    assert action_policy.tool_action_is_mutating("manage_checkpoints", action="list") is False
    assert action_policy.tool_action_is_mutating("manage_checkpoints", action="restore") is True

    # Local-only and runtime-only capability flags for newer surfaces.
    assert action_policy.get_tool_action_policy("manage_code_intelligence").local_only is True
    assert action_policy.get_tool_action_policy("manage_checkpoints").local_only is True
    assert action_policy.get_tool_action_policy("search_code").local_only is True
    assert action_policy.get_tool_action_policy("manage_runtime_ui").runtime_only is True
    assert action_policy.get_tool_action_policy("get_runtime_status").runtime_only is True
    assert action_policy.get_tool_action_policy("execute_runtime_command").runtime_only is True
    assert action_policy.get_tool_action_policy("get_runtime_status").requires_explicit_opt_in is True


def test_unknown_tool_defaults_to_safe_mutating():
    """Test that unknown tools default to mutating/high-risk for safety."""
    policy = action_policy.get_tool_action_policy("unknown_tool_xyz")

    assert policy.mutating is True
    assert policy.high_risk is True
    assert policy.supports_dry_run is False
    assert policy.requires_explicit_opt_in is True


def test_empty_tool_name_defaults_to_safe():
    """Test that empty/None tool name defaults to safe values."""
    policy = action_policy.get_tool_action_policy(None)

    assert policy.mutating is True
    assert policy.high_risk is True
    assert policy.requires_explicit_opt_in is True
