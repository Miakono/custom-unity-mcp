from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services.tools.manage_vfx import manage_vfx


def test_manage_vfx_accepts_particle_create(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_send_with_unity_instance(send_fn, unity_instance, tool_name, params):
        captured["unity_instance"] = unity_instance
        captured["tool_name"] = tool_name
        captured["params"] = params
        return {"success": True, "message": "ok"}

    monkeypatch.setattr(
        "services.tools.manage_vfx.get_unity_instance_from_context",
        AsyncMock(return_value="unity-instance-1"),
    )
    monkeypatch.setattr(
        "services.tools.manage_vfx.send_with_unity_instance",
        fake_send_with_unity_instance,
    )

    result = asyncio.run(
        manage_vfx(
            SimpleNamespace(),
            action="particle_create",
            target="BudGrowth",
            properties={"position": [0, 1, 0]},
        )
    )

    assert result["success"] is True
    assert captured["unity_instance"] == "unity-instance-1"
    assert captured["tool_name"] == "manage_vfx"
    assert captured["params"] == {
        "action": "particle_create",
        "target": "BudGrowth",
        "properties": {"position": [0, 1, 0]},
    }


@pytest.mark.parametrize(
    ("action", "properties"),
    [
        ("vfx_set_float", {"parameter": "SpawnRate", "value": 1.5}),
        ("vfx_set_int", {"parameter": "Count", "value": 3}),
        ("vfx_set_vector4", {"parameter": "Tint", "value": [1.0, 0.2, 0.3, 1.0]}),
        (
            "vfx_set_gradient",
            {
                "parameter": "ColorOverLife",
                "gradient": {
                    "colorKeys": [
                        {"color": [1.0, 0.0, 0.0, 1.0], "time": 0.0},
                        {"color": [1.0, 1.0, 0.0, 1.0], "time": 1.0},
                    ],
                    "alphaKeys": [
                        {"alpha": 1.0, "time": 0.0},
                        {"alpha": 0.0, "time": 1.0},
                    ],
                },
            },
        ),
        ("vfx_set_mesh", {"parameter": "MeshParam", "meshPath": "Assets/Models/SmokeMesh.fbx"}),
    ],
)
def test_manage_vfx_accepts_schema_dependent_vfx_actions(monkeypatch, action: str, properties: dict) -> None:
    captured: dict[str, object] = {}

    async def fake_send_with_unity_instance(send_fn, unity_instance, tool_name, params):
        captured["unity_instance"] = unity_instance
        captured["tool_name"] = tool_name
        captured["params"] = params
        return {"success": True, "message": "ok"}

    monkeypatch.setattr(
        "services.tools.manage_vfx.get_unity_instance_from_context",
        AsyncMock(return_value="unity-instance-1"),
    )
    monkeypatch.setattr(
        "services.tools.manage_vfx.send_with_unity_instance",
        fake_send_with_unity_instance,
    )

    result = asyncio.run(
        manage_vfx(
            SimpleNamespace(),
            action=action,
            target="MCP_VfxGraphSmoke",
            properties=properties,
        )
    )

    assert result["success"] is True
    assert captured["unity_instance"] == "unity-instance-1"
    assert captured["tool_name"] == "manage_vfx"
    assert captured["params"] == {
        "action": action,
        "target": "MCP_VfxGraphSmoke",
        "properties": properties,
    }


def test_manage_vfx_normalizes_case_for_vfx_action(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_send_with_unity_instance(send_fn, unity_instance, tool_name, params):
        captured["params"] = params
        return {"success": True, "message": "ok"}

    monkeypatch.setattr(
        "services.tools.manage_vfx.get_unity_instance_from_context",
        AsyncMock(return_value="unity-instance-1"),
    )
    monkeypatch.setattr(
        "services.tools.manage_vfx.send_with_unity_instance",
        fake_send_with_unity_instance,
    )

    result = asyncio.run(
        manage_vfx(
            SimpleNamespace(),
            action="VFX_SET_FLOAT",
            properties={"parameter": "SpawnRate", "value": 1.5},
        )
    )

    assert result["success"] is True
    assert captured["params"] == {
        "action": "vfx_set_float",
        "properties": {"parameter": "SpawnRate", "value": 1.5},
    }
