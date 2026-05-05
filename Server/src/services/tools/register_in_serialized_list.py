"""
register_in_serialized_list — append an entry to a serialized list/array on a Unity object.

Generic primitive for the "register a thing in a global registry" pattern: pool managers,
Addressables groups, audio mixer groups, scene catalogs, monster registries, etc. Avoids
per-project MCP wrappers — every project that has a "list of X" can use this.

Three target kinds:
- target_kind="asset"        → ScriptableObject asset by path
- target_kind="prefab"       → Component on a Component inside a prefab
- target_kind="scene_object" → Component on a scene GameObject (with optional scene_path)

Entry forms (in `entry`):
- {"asset_path": "Assets/Foo/Bar.prefab"}  (object reference)
- {"asset_guid": "abc123..."}              (object reference, by GUID)
- {"value": 42 | "text" | true}            (primitive int/string/bool/float/enum)

Defaults to dedupe=True so re-running the call is idempotent.
"""
from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from models import MCPResponse
from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    description=(
        "Append an entry to a serialized list/array field on a Unity object. Targets a "
        "ScriptableObject asset, a Component on a prefab, or a Component on a scene "
        "GameObject. Supports object references (by asset_path or asset_guid) and "
        "primitives (int / float / bool / string / enum). Idempotent by default."
    ),
    annotations=ToolAnnotations(
        title="Register in Serialized List",
        destructiveHint=False,  # idempotent + non-destructive
    ),
    group="pipeline",
)
async def register_in_serialized_list(
    ctx: Context,
    target_kind: Annotated[
        str,
        "'asset' | 'prefab' | 'scene_object'",
    ],
    field_path: Annotated[
        str,
        "Serialized property path of the list/array field (e.g. 'pools' or 'data.entries').",
    ],
    entry: Annotated[
        dict[str, Any],
        "Entry to append. {asset_path|asset_guid: ...} for object refs; {value: ...} for primitives.",
    ],
    asset_path: Annotated[
        str | None,
        "Required when target_kind='asset': path to the SO asset.",
    ] = None,
    prefab_path: Annotated[
        str | None,
        "Required when target_kind='prefab': path to the prefab.",
    ] = None,
    component: Annotated[
        str | None,
        "Required when target_kind='prefab' or 'scene_object': component type name (e.g. 'PoolManager').",
    ] = None,
    find: Annotated[
        str | None,
        "Required when target_kind='scene_object': GameObject id / name / path.",
    ] = None,
    search_method: Annotated[
        str | None,
        "Optional GameObject lookup mode for scene_object (default 'by_id_or_name_or_path').",
    ] = None,
    scene_path: Annotated[
        str | None,
        "Optional scene path for scene_object — opens additively if not already loaded.",
    ] = None,
    dedupe: Annotated[
        bool,
        "When true, skip insertion if the entry is already in the list.",
    ] = True,
) -> MCPResponse:
    gate = await maybe_run_tool_preflight(ctx, "register_in_serialized_list")
    if gate is not None:
        return MCPResponse(**gate.model_dump())

    unity_instance = await get_unity_instance_from_context(ctx)
    params: dict[str, Any] = {
        "target_kind": target_kind,
        "field_path": field_path,
        "entry": entry,
        "asset_path": asset_path,
        "prefab_path": prefab_path,
        "component": component,
        "find": find,
        "search_method": search_method,
        "scene_path": scene_path,
        "dedupe": dedupe,
    }
    params = {k: v for k, v in params.items() if v is not None}
    result = await send_with_unity_instance(
        async_send_command_with_retry, unity_instance, "register_in_serialized_list", params
    )
    return MCPResponse(**result) if isinstance(result, dict) else result
