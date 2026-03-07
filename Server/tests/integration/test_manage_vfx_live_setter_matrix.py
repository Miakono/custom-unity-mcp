from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from unittest.mock import AsyncMock
from typing import Callable

import pytest

from services.tools.manage_vfx import manage_vfx

from .test_helpers import DummyContext


@dataclass(frozen=True)
class SetterSpec:
    action: str
    type_hints: tuple[str, ...]
    payload_builder: Callable[[str], dict]


def _payload_float(parameter_name: str) -> dict:
    return {"parameter": parameter_name, "value": 1.25}


def _payload_int(parameter_name: str) -> dict:
    return {"parameter": parameter_name, "value": 7}


def _payload_vector4(parameter_name: str) -> dict:
    return {"parameter": parameter_name, "value": [1.0, 0.2, 0.4, 1.0]}


def _payload_gradient(parameter_name: str) -> dict:
    return {
        "parameter": parameter_name,
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
    }


def _payload_mesh(parameter_name: str) -> dict:
    return {"parameter": parameter_name, "meshPath": "Assets/Models/SmokeMesh.fbx"}


SETTER_SPECS = (
    SetterSpec("vfx_set_float", ("float",), _payload_float),
    SetterSpec("vfx_set_int", ("int",), _payload_int),
    SetterSpec("vfx_set_vector4", ("vector4", "float4", "color"), _payload_vector4),
    SetterSpec("vfx_set_gradient", ("gradient",), _payload_gradient),
    SetterSpec("vfx_set_mesh", ("mesh",), _payload_mesh),
)


def _normalize_type(raw_type: object) -> str:
    return str(raw_type or "").strip().lower()


def _pick_parameter(exposed_parameters: list[dict], type_hints: tuple[str, ...]) -> str | None:
    if not exposed_parameters:
        return None

    for item in exposed_parameters:
        param_name = item.get("name")
        param_type = _normalize_type(item.get("type"))
        if not param_name:
            continue

        if any(hint in param_type for hint in type_hints):
            return str(param_name)

    return None


async def run_vfx_setter_matrix(ctx: DummyContext, target: str) -> dict[str, dict[str, object]]:
    info = await manage_vfx(ctx, action="vfx_get_info", target=target)
    if not info.get("success"):
        return {
            spec.action: {
                "status": "failed",
                "reason": f"vfx_get_info failed: {info.get('message', 'unknown error')}",
            }
            for spec in SETTER_SPECS
        }

    data = info.get("data") or {}
    exposed = data.get("exposedParameters") or []

    results: dict[str, dict[str, object]] = {}
    for spec in SETTER_SPECS:
        parameter_name = _pick_parameter(exposed, spec.type_hints)
        if parameter_name is None:
            results[spec.action] = {
                "status": "skipped",
                "reason": f"No exposed parameter matching type hints {spec.type_hints}",
            }
            continue

        response = await manage_vfx(
            ctx,
            action=spec.action,
            target=target,
            properties=spec.payload_builder(parameter_name),
        )
        if response.get("success"):
            results[spec.action] = {
                "status": "passed",
                "parameter": parameter_name,
            }
        else:
            results[spec.action] = {
                "status": "failed",
                "parameter": parameter_name,
                "reason": response.get("message", "unknown error"),
            }

    return results


@pytest.mark.asyncio
async def test_vfx_setter_matrix_runs_or_skips_by_schema(monkeypatch):
    ctx = DummyContext()

    async def fake_send_with_unity_instance(_send_fn, _unity_instance, _tool_name, params):
        action = params.get("action")
        if action == "vfx_get_info":
            return {
                "success": True,
                "data": {
                    "exposedParameters": [
                        {"name": "SpawnRate", "type": "float"},
                        {"name": "Count", "type": "int32"},
                        {"name": "Tint", "type": "Vector4"},
                        {"name": "ColorOverLife", "type": "gradient"},
                    ]
                },
            }

        return {"success": True, "message": f"ok:{action}"}

    monkeypatch.setattr(
        "services.tools.manage_vfx.get_unity_instance_from_context",
        AsyncMock(return_value="unity-instance-1"),
    )
    monkeypatch.setattr(
        "services.tools.manage_vfx.send_with_unity_instance",
        fake_send_with_unity_instance,
    )

    matrix = await run_vfx_setter_matrix(ctx, target="MCP_VfxGraphSmoke")

    assert matrix["vfx_set_float"]["status"] == "passed"
    assert matrix["vfx_set_int"]["status"] == "passed"
    assert matrix["vfx_set_vector4"]["status"] == "passed"
    assert matrix["vfx_set_gradient"]["status"] == "passed"
    assert matrix["vfx_set_mesh"]["status"] == "skipped"


@pytest.mark.integration
@pytest.mark.skipif(
    not bool(os.environ.get("UNITY_MCP_RUN_LIVE_VFX_MATRIX")),
    reason="Set UNITY_MCP_RUN_LIVE_VFX_MATRIX=1 to run against a live Unity instance.",
)
def test_vfx_setter_matrix_live_opt_in():
    ctx = DummyContext()
    matrix = asyncio.run(run_vfx_setter_matrix(ctx, target="MCP_VfxGraphSmoke_20260306_0223"))

    assert len(matrix) == len(SETTER_SPECS)
    assert all(result["status"] in {"passed", "skipped", "failed"} for result in matrix.values())
