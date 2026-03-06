import pytest

import services.resources.validation_profiles as validation_profiles_module
from services.resources.validation_profiles import get_validation_profiles

from .test_helpers import DummyContext


@pytest.mark.asyncio
async def test_validation_profiles_resource_returns_unity_payload(monkeypatch):
    async def fake_get_instance(ctx):
        _ = ctx
        return "Example@abc123"

    async def fake_send(sender, unity_instance, command, params):
        _ = sender
        assert unity_instance == "Example@abc123"
        assert command == "get_validation_profiles"
        assert params == {}
        return {
            "success": True,
            "data": {
                "profile_count": 2,
                "profiles": [{"tool": "validate_project_state"}],
            },
        }

    monkeypatch.setattr(validation_profiles_module, "get_unity_instance_from_context", fake_get_instance)
    monkeypatch.setattr(validation_profiles_module, "send_with_unity_instance", fake_send)

    result = await get_validation_profiles(DummyContext())

    assert result["profile_count"] == 2
    assert result["profiles"][0]["tool"] == "validate_project_state"
