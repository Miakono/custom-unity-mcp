import services.registry.tool_registry as tool_registry_module
from services.registry import ensure_tool_registry_populated, get_registered_tools
from services.unity_tool_source import discover_unity_tool_handlers, get_unity_tool_compatibility


def test_discover_unity_tool_handlers_supports_multiline_attributes():
    handlers = discover_unity_tool_handlers()

    assert "audit_prefab_integrity" in handlers
    assert "audit_scene_integrity" in handlers
    assert any(path.endswith("AuditPrefabIntegrity.cs") for path in handlers["audit_prefab_integrity"])
    assert any(path.endswith("AuditSceneIntegrity.cs") for path in handlers["audit_scene_integrity"])


def test_manage_video_capture_is_flagged_as_missing_unity_handler():
    compatibility = get_unity_tool_compatibility("manage_video_capture", "manage_video_capture")

    assert compatibility.publishable is False
    assert compatibility.status == "missing_unity_handler"


def test_all_other_unity_targeted_tools_resolve_to_real_handlers():
    tool_registry_module._tool_registry.clear()
    ensure_tool_registry_populated()

    unsupported_direct = []
    missing_alias_targets = []

    for tool in get_registered_tools():
        compatibility = get_unity_tool_compatibility(tool["name"], tool.get("unity_target"))

        if compatibility.status == "missing_unity_handler":
            unsupported_direct.append(tool["name"])
        elif compatibility.status == "missing_alias_target":
            missing_alias_targets.append(tool["name"])

    assert sorted(unsupported_direct) == ["manage_video_capture"]
    assert missing_alias_targets == []