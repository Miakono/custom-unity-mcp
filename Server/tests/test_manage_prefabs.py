"""Tests for manage_prefabs tool - component_properties parameter."""

import inspect
from unittest.mock import AsyncMock

import pytest

from services.tools.manage_prefabs import manage_prefabs
from tests.integration.test_helpers import DummyContext


class TestManagePrefabsComponentProperties:
    """Tests for the component_properties parameter on manage_prefabs."""

    def test_component_properties_parameter_exists(self):
        """The manage_prefabs tool should have a component_properties parameter."""
        sig = inspect.signature(manage_prefabs)
        assert "component_properties" in sig.parameters

    def test_component_properties_parameter_is_optional(self):
        """component_properties should default to None."""
        sig = inspect.signature(manage_prefabs)
        param = sig.parameters["component_properties"]
        assert param.default is None

    def test_tool_description_mentions_component_properties(self):
        """The tool description should mention component_properties."""
        from services.registry import get_registered_tools
        tools = get_registered_tools()
        prefab_tool = next(
            (t for t in tools if t["name"] == "manage_prefabs"), None
        )
        assert prefab_tool is not None
        # Description is stored at top level or in kwargs depending on how the decorator stores it
        desc = prefab_tool.get("description") or prefab_tool.get("kwargs", {}).get("description", "")
        assert "component_properties" in desc

    def test_required_params_include_modify_contents(self):
        """modify_contents should be a valid action requiring prefab_path."""
        from services.tools.manage_prefabs import REQUIRED_PARAMS
        assert "modify_contents" in REQUIRED_PARAMS
        assert "prefab_path" in REQUIRED_PARAMS["modify_contents"]

    @pytest.mark.asyncio
    async def test_create_child_accepts_json_string(self, monkeypatch):
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True}

        monkeypatch.setattr("services.tools.manage_prefabs.send_with_unity_instance", fake_send)
        monkeypatch.setattr("services.tools.manage_prefabs.get_unity_instance_from_context", AsyncMock(return_value="Project@hash"))
        monkeypatch.setattr("services.tools.manage_prefabs.maybe_run_tool_preflight", AsyncMock(return_value=None))

        resp = await manage_prefabs(
            DummyContext(),
            action="modify_contents",
            prefab_path="Assets/Test.prefab",
            create_child='[{"name":"Child","position":[1,2,3]}]',
        )

        assert resp["success"] is True
        assert captured["params"]["createChild"][0]["position"] == [1.0, 2.0, 3.0]
