import pytest
from unittest.mock import AsyncMock

import services.tools.manage_addressables as manage_addressables_mod
import services.tools.manage_code_intelligence as manage_code_intelligence_mod
import services.tools.manage_input_system as manage_input_system_mod
import services.tools.manage_package_manager as manage_package_manager_mod
import services.tools.manage_profiler as manage_profiler_mod
import services.tools.manage_reflection as manage_reflection_mod
import services.tools.manage_runtime_ui as manage_runtime_ui_mod
import services.tools.manage_video_capture as manage_video_capture_mod
from core.config import config as server_config

from .test_helpers import DummyContext


@pytest.mark.asyncio
async def test_manage_addressables_read_only_get_groups_routes_to_unity(monkeypatch):
    captured = {}

    async def fake_send(_send_fn, _unity_instance, command_type, params):
        captured["command_type"] = command_type
        captured["params"] = params
        return {"success": True, "data": {"groups": []}}

    monkeypatch.setattr(
        manage_addressables_mod,
        "get_unity_instance_from_context",
        AsyncMock(return_value="unity-instance-1"),
    )
    monkeypatch.setattr(manage_addressables_mod, "send_with_unity_instance", fake_send)

    result = await manage_addressables_mod.manage_addressables(
        ctx=DummyContext(),
        action="get_groups",
        page_size="25",
        page_number="2",
    )

    assert result["success"] is True
    assert captured["command_type"] == "manage_addressables"
    assert captured["params"]["action"] == "get_groups"
    assert captured["params"]["pageSize"] == 25
    assert captured["params"]["pageNumber"] == 2


@pytest.mark.asyncio
async def test_manage_input_system_read_only_state_routes_without_preflight(monkeypatch):
    captured = {"preflight_called": False}

    async def fake_preflight(*_args, **_kwargs):
        captured["preflight_called"] = True
        return None

    async def fake_send(_send_fn, _unity_instance, command_type, params):
        captured["command_type"] = command_type
        captured["params"] = params
        return {"success": True, "data": {"actions": []}}

    monkeypatch.setattr(manage_input_system_mod, "maybe_run_tool_preflight", fake_preflight)
    monkeypatch.setattr(
        manage_input_system_mod,
        "get_unity_instance_from_context",
        AsyncMock(return_value="unity-instance-1"),
    )
    monkeypatch.setattr(manage_input_system_mod, "send_with_unity_instance", fake_send)

    result = await manage_input_system_mod.manage_input_system(
        ctx=DummyContext(),
        action="state_get_all_actions",
        asset_path="Assets/InputSystem_Actions.inputactions",
    )

    assert result["success"] is True
    assert captured["preflight_called"] is False
    assert captured["command_type"] == "manage_input_system"
    assert captured["params"]["action"] == "state_get_all_actions"


@pytest.mark.asyncio
async def test_manage_profiler_preflight_only_for_mutating_actions(monkeypatch):
    captured = {"preflight_actions": []}

    async def fake_preflight(_ctx, tool_name, action=None, **_kwargs):
        captured["preflight_actions"].append((tool_name, action))
        return None

    async def fake_send(_send_fn, _unity_instance, command_type, params):
        captured["command_type"] = command_type
        captured["params"] = params
        return {"success": True, "data": {"isRecording": False}}

    monkeypatch.setattr(manage_profiler_mod, "maybe_run_tool_preflight", fake_preflight)
    monkeypatch.setattr(
        manage_profiler_mod,
        "get_unity_instance_from_context",
        AsyncMock(return_value="unity-instance-1"),
    )
    monkeypatch.setattr(manage_profiler_mod, "send_with_unity_instance", fake_send)

    read_only_result = await manage_profiler_mod.manage_profiler(
        ctx=DummyContext(),
        action="get_status",
    )
    mutating_result = await manage_profiler_mod.manage_profiler(
        ctx=DummyContext(),
        action="start",
    )

    assert read_only_result["success"] is True
    assert mutating_result["success"] is True
    assert captured["preflight_actions"] == [("manage_profiler", "start")]


@pytest.mark.asyncio
async def test_manage_package_manager_read_only_uses_local_handler(monkeypatch):
    captured = {}

    async def fake_local_handler(*_args, **_kwargs):
        captured["local_handler_called"] = True
        return {"success": True, "data": {"packages": []}}

    async def fail_if_unity_called(*_args, **_kwargs):
        raise AssertionError("Unity transport should not be used for read-only package actions")

    monkeypatch.setattr(manage_package_manager_mod, "_handle_read_only_action", fake_local_handler)
    monkeypatch.setattr(manage_package_manager_mod, "send_with_unity_instance", fail_if_unity_called)
    monkeypatch.setattr(
        manage_package_manager_mod,
        "get_unity_instance_from_context",
        AsyncMock(return_value="unity-instance-1"),
    )

    result = await manage_package_manager_mod.manage_package_manager(
        ctx=DummyContext(),
        action="list_installed",
    )

    assert result["success"] is True
    assert captured["local_handler_called"] is True


@pytest.mark.asyncio
async def test_manage_code_intelligence_search_code_uses_index_manager(monkeypatch):
    class FakeManager:
        def get_index_status(self):
            return {"loaded": True, "files_indexed": 1}

        def search_code(self, **kwargs):
            return {"success": True, "query": kwargs["pattern"], "results": []}

    monkeypatch.setattr(manage_code_intelligence_mod, "get_index_manager", lambda _root: FakeManager())

    result = await manage_code_intelligence_mod.manage_code_intelligence(
        ctx=DummyContext(),
        action="search_code",
        pattern="PlayerController",
    )

    assert result["success"] is True
    assert result["query"] == "PlayerController"


@pytest.mark.asyncio
async def test_manage_runtime_ui_routes_read_only_and_mutating_actions(monkeypatch):
    captured = {"read_only_called": False, "mutation_called": False}

    monkeypatch.setattr(server_config, "runtime_mcp_enabled", True)

    async def fake_read_only_send(_send_fn, _unity_instance, command_type, params):
        captured["read_only_called"] = True
        captured["read_only_command_type"] = command_type
        captured["read_only_params"] = params
        return {"success": True, "data": {"elements": []}}

    async def fake_mutation_send(_ctx, _unity_instance, command_type, params):
        captured["mutation_called"] = True
        captured["mutation_command_type"] = command_type
        captured["mutation_params"] = params
        return {"success": True, "message": "clicked"}

    monkeypatch.setattr(
        manage_runtime_ui_mod,
        "get_unity_instance_from_context",
        AsyncMock(return_value="unity-instance-1"),
    )
    monkeypatch.setattr(manage_runtime_ui_mod, "send_with_unity_instance", fake_read_only_send)
    monkeypatch.setattr(manage_runtime_ui_mod, "send_mutation", fake_mutation_send)

    result_read_only = await manage_runtime_ui_mod.manage_runtime_ui(
        ctx=DummyContext(),
        action="find_elements",
        element_type="Button",
    )
    result_mutating = await manage_runtime_ui_mod.manage_runtime_ui(
        ctx=DummyContext(),
        action="click",
        element_name="PlayButton",
    )

    assert result_read_only["success"] is True
    assert result_mutating["success"] is True
    assert captured["read_only_called"] is True
    assert captured["mutation_called"] is True
    assert captured["read_only_command_type"] == "manage_runtime_ui"
    assert captured["mutation_command_type"] == "manage_runtime_ui"


@pytest.mark.asyncio
async def test_manage_video_capture_routes_read_only_and_mutating_actions(monkeypatch):
    captured = {"read_only_called": False, "mutation_called": False}

    async def fake_read_only_send(_send_fn, _unity_instance, command_type, params):
        captured["read_only_called"] = True
        captured["read_only_command_type"] = command_type
        captured["read_only_params"] = params
        return {"success": True, "data": {"isRecording": False}}

    async def fake_mutation_send(_ctx, _unity_instance, command_type, params):
        captured["mutation_called"] = True
        captured["mutation_command_type"] = command_type
        captured["mutation_params"] = params
        return {"success": True, "message": "recording"}

    monkeypatch.setattr(
        manage_video_capture_mod,
        "get_unity_instance_from_context",
        AsyncMock(return_value="unity-instance-1"),
    )
    monkeypatch.setattr(manage_video_capture_mod, "send_with_unity_instance", fake_read_only_send)
    monkeypatch.setattr(manage_video_capture_mod, "send_mutation", fake_mutation_send)

    result_read_only = await manage_video_capture_mod.manage_video_capture(
        ctx=DummyContext(),
        action="get_status",
    )
    result_mutating = await manage_video_capture_mod.manage_video_capture(
        ctx=DummyContext(),
        action="start",
        output_path="Recordings/smoke.mp4",
    )

    assert result_read_only["success"] is True
    assert result_mutating["success"] is True
    assert captured["read_only_called"] is True
    assert captured["mutation_called"] is True
    assert captured["read_only_command_type"] == "manage_video_capture"
    assert captured["mutation_command_type"] == "manage_video_capture"


@pytest.mark.asyncio
async def test_manage_reflection_passes_action_to_preflight(monkeypatch):
    captured = {}

    async def fake_preflight(_ctx, tool_name, action=None, **_kwargs):
        captured["tool_name"] = tool_name
        captured["action"] = action
        return None

    async def fake_send(_send_fn, _unity_instance, command_type, params):
        captured["command_type"] = command_type
        captured["params"] = params
        return {"success": True, "message": "ok", "data": {"members": []}}

    monkeypatch.setattr(manage_reflection_mod, "maybe_run_tool_preflight", fake_preflight)
    monkeypatch.setattr(
        manage_reflection_mod,
        "get_unity_instance_from_context",
        AsyncMock(return_value="unity-instance-1"),
    )
    monkeypatch.setattr(
        manage_reflection_mod.ReflectionHelper,
        "is_reflection_enabled",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr(manage_reflection_mod, "send_with_unity_instance", fake_send)

    result = await manage_reflection_mod.manage_reflection(
        ctx=DummyContext(),
        action="discover_methods",
        target_type="UnityEngine.GameObject",
    )

    assert result["success"] is True
    assert captured["tool_name"] == "manage_reflection"
    assert captured["action"] == "discover_methods"
    assert captured["command_type"] == "manage_reflection"
