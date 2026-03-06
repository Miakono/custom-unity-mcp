from unittest.mock import AsyncMock

import pytest

import services.tools.script_apply_edits as script_apply_edits_mod
from .test_helpers import DummyContext


@pytest.mark.asyncio
async def test_script_apply_edits_accepts_stringified_options(monkeypatch):
    async def fake_send(*args, **kwargs):
        command = args[2]
        if command == "manage_script":
            return {
                "success": True,
                "data": {
                    "contents": (
                        "using UnityEngine;\n\n"
                        "public class TempProbe : MonoBehaviour\n{\n"
                        "    public int GetValue()\n"
                        "    {\n"
                        "        return 1;\n"
                        "    }\n"
                        "}\n"
                    )
                },
            }
        return {"success": True}

    monkeypatch.setattr(script_apply_edits_mod, "send_with_unity_instance", fake_send)
    monkeypatch.setattr(script_apply_edits_mod, "send_mutation", AsyncMock(return_value={"success": True, "message": "ok"}))
    monkeypatch.setattr(script_apply_edits_mod, "maybe_run_tool_preflight", AsyncMock(return_value=None))
    monkeypatch.setattr(script_apply_edits_mod, "get_unity_instance_from_context", AsyncMock(return_value="Project@hash"))

    resp = await script_apply_edits_mod.script_apply_edits(
        DummyContext(),
        name="TempProbe",
        path="Assets/Scripts",
        edits='[{"op":"replace_method","className":"TempProbe","methodName":"GetValue","replacement":"public int GetValue()\\n    {\\n        return 2;\\n    }"}]',
        options='{"preview":true}',
    )

    assert resp["success"] is True
