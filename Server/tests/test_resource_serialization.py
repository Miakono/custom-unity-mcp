import json

from models.models import MCPResponse
from services.resources.__init__ import _serialize_resource_result


def test_resource_serializer_converts_dict_to_json_text():
    payload = {"success": True, "data": {"count": 1}}

    result = _serialize_resource_result(payload)

    assert isinstance(result, str)
    assert json.loads(result) == payload


def test_resource_serializer_converts_mcp_response_to_json_text():
    payload = MCPResponse(success=True, message="ok", data={"value": 42})

    result = _serialize_resource_result(payload)

    assert isinstance(result, str)
    assert json.loads(result)["data"]["value"] == 42
