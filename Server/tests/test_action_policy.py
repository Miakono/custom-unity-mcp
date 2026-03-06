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
