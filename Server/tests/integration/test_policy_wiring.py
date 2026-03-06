import pytest

from .test_helpers import DummyContext
import services.tools.batch_execute as batch_execute_mod
import services.tools.manage_script as manage_script_mod


@pytest.mark.asyncio
async def test_batch_execute_routes_through_policy_layer(monkeypatch):
    captured = {}

    async def fake_policy(ctx, tool_name, **kwargs):
        captured["policy"] = {
            "ctx": ctx,
            "tool_name": tool_name,
            "kwargs": kwargs,
        }
        return None

    async def fake_send(cmd, params, **kwargs):
        captured["send"] = {
            "cmd": cmd,
            "params": params,
            "kwargs": kwargs,
        }
        return {"success": True, "data": {}}

    monkeypatch.setattr(batch_execute_mod, "maybe_run_tool_preflight", fake_policy)
    monkeypatch.setattr(batch_execute_mod, "async_send_command_with_retry", fake_send)

    ctx = DummyContext()
    commands = [{"tool": "manage_scene", "params": {"action": "get_active"}}]
    resp = await batch_execute_mod.batch_execute(ctx, commands=commands)

    assert resp["success"] is True
    assert captured["policy"]["ctx"] is ctx
    assert captured["policy"]["tool_name"] == "batch_execute"
    assert captured["policy"]["kwargs"]["commands"] == commands
    assert captured["send"]["cmd"] == "batch_execute"
    assert captured["send"]["params"]["commands"] == commands


@pytest.mark.asyncio
async def test_apply_text_edits_routes_through_policy_layer(monkeypatch):
    captured = {}

    async def fake_policy(ctx, tool_name, **kwargs):
        captured["policy"] = {"ctx": ctx, "tool_name": tool_name, "kwargs": kwargs}
        return None

    async def fake_send_mutation(ctx, unity_instance, command, params, **kwargs):
        captured["mutation"] = {
            "ctx": ctx,
            "unity_instance": unity_instance,
            "command": command,
            "params": params,
            "kwargs": kwargs,
        }
        return {"success": True, "data": {}}

    monkeypatch.setattr(manage_script_mod, "maybe_run_tool_preflight", fake_policy)
    monkeypatch.setattr(manage_script_mod, "send_mutation", fake_send_mutation)

    ctx = DummyContext()
    resp = await manage_script_mod.apply_text_edits(
        ctx,
        "mcpforunity://path/Assets/Scripts/File.cs",
        [{"startLine": 1, "startCol": 1, "endLine": 1, "endCol": 1, "newText": "x"}],
    )

    assert resp["success"] is True
    assert captured["policy"]["ctx"] is ctx
    assert captured["policy"]["tool_name"] == "apply_text_edits"
    assert captured["mutation"]["command"] == "manage_script"
    assert captured["mutation"]["params"]["action"] == "apply_text_edits"


@pytest.mark.asyncio
async def test_create_script_routes_through_policy_layer(monkeypatch):
    captured = {}

    async def fake_policy(ctx, tool_name, **kwargs):
        captured["policy"] = {"ctx": ctx, "tool_name": tool_name, "kwargs": kwargs}
        return None

    async def fake_send_mutation(ctx, unity_instance, command, params, **kwargs):
        captured["mutation"] = {
            "ctx": ctx,
            "unity_instance": unity_instance,
            "command": command,
            "params": params,
            "kwargs": kwargs,
        }
        return {"success": True, "data": {}}

    monkeypatch.setattr(manage_script_mod, "maybe_run_tool_preflight", fake_policy)
    monkeypatch.setattr(manage_script_mod, "send_mutation", fake_send_mutation)

    ctx = DummyContext()
    resp = await manage_script_mod.create_script(
        ctx,
        "Assets/Scripts/NewFile.cs",
        "public class NewFile {}",
    )

    assert resp["success"] is True
    assert captured["policy"]["ctx"] is ctx
    assert captured["policy"]["tool_name"] == "create_script"
    assert captured["mutation"]["params"]["action"] == "create"


@pytest.mark.asyncio
async def test_delete_script_routes_through_policy_layer(monkeypatch):
    captured = {}

    async def fake_policy(ctx, tool_name, **kwargs):
        captured["policy"] = {"ctx": ctx, "tool_name": tool_name, "kwargs": kwargs}
        return None

    async def fake_send_mutation(ctx, unity_instance, command, params, **kwargs):
        captured["mutation"] = {
            "ctx": ctx,
            "unity_instance": unity_instance,
            "command": command,
            "params": params,
            "kwargs": kwargs,
        }
        return {"success": True, "data": {}}

    monkeypatch.setattr(manage_script_mod, "maybe_run_tool_preflight", fake_policy)
    monkeypatch.setattr(manage_script_mod, "send_mutation", fake_send_mutation)

    ctx = DummyContext()
    resp = await manage_script_mod.delete_script(
        ctx,
        "mcpforunity://path/Assets/Scripts/DeleteMe.cs",
    )

    assert resp["success"] is True
    assert captured["policy"]["ctx"] is ctx
    assert captured["policy"]["tool_name"] == "delete_script"
    assert captured["mutation"]["params"]["action"] == "delete"
