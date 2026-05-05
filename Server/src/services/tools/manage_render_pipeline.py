"""
Render Pipeline Asset, URP Renderer Features, and Volume Profiles management.

All Unity-side access goes via reflection so the package does not require URP / HDRP
to be installed — projects on the Built-in pipeline get clean responses describing
what's not available rather than compile errors.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight
from services.tools.utils import coerce_bool, coerce_int
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    group="project_config",
    description=(
        "Manage the active render pipeline configuration: detect URP/HDRP/Built-in, list "
        "+ toggle URP renderer features, list Volume Profile assets, read profile overrides, "
        "and set a single override parameter. Read-only by default — set_renderer_feature_active "
        "and set_volume_override are the only mutating actions."
    ),
    annotations=ToolAnnotations(
        title="Manage Render Pipeline",
        destructiveHint=True,
    ),
)
async def manage_render_pipeline(
    ctx: Context,
    action: Annotated[
        Literal[
            "get_active",
            "list_renderer_features",
            "set_renderer_feature_active",
            "list_volume_profiles",
            "get_volume_profile",
            "set_volume_override",
        ],
        "Action to perform. set_renderer_feature_active and set_volume_override are mutating."
    ],
    renderer_index: Annotated[
        int | str | None,
        "URP renderer index (default 0 — most projects only have one)."
    ] = None,
    feature_name: Annotated[
        str | None,
        "Renderer feature name (for set_renderer_feature_active). Either name or feature_index required."
    ] = None,
    feature_index: Annotated[
        int | str | None,
        "Renderer feature index (alternative to feature_name)."
    ] = None,
    active: Annotated[
        bool | str | None,
        "Target active state for set_renderer_feature_active."
    ] = None,
    folder: Annotated[
        str | None,
        "Optional folder path filter for list_volume_profiles (e.g. 'Assets/Settings')."
    ] = None,
    max_results: Annotated[
        int | str | None,
        "Cap for list_volume_profiles (default 100)."
    ] = None,
    profile_path: Annotated[
        str | None,
        "VolumeProfile asset path (for get_volume_profile / set_volume_override)."
    ] = None,
    component_type: Annotated[
        str | None,
        "VolumeComponent type name (e.g. 'Bloom', 'ColorAdjustments') for set_volume_override."
    ] = None,
    parameter_name: Annotated[
        str | None,
        "Parameter field name on the VolumeComponent for set_volume_override."
    ] = None,
    value: Annotated[
        str | None,
        "Parameter value (string-coerced into target type — supports bool/int/float/string/Color "
        "as 'r,g,b[,a]' / Vector3 as 'x,y,z' / enum names)."
    ] = None,
    override_state: Annotated[
        bool | str | None,
        "Whether the override is active for set_volume_override (true to apply, false to disable)."
    ] = None,
) -> dict[str, Any]:
    """Surface URP / HDRP / Built-in pipeline configuration via the MCP."""
    unity_instance = await get_unity_instance_from_context(ctx)

    gate = await maybe_run_tool_preflight(ctx, "manage_render_pipeline", action=action)
    if gate is not None:
        return gate.model_dump()

    params: dict[str, Any] = {"action": action}
    if renderer_index is not None:
        params["rendererIndex"] = coerce_int(renderer_index, default=0)
    if feature_name is not None:
        params["featureName"] = feature_name
    if feature_index is not None:
        params["featureIndex"] = coerce_int(feature_index, default=0)
    if active is not None:
        params["active"] = coerce_bool(active, default=False)
    if folder is not None:
        params["folder"] = folder
    if max_results is not None:
        params["maxResults"] = coerce_int(max_results, default=100)
    if profile_path is not None:
        params["profilePath"] = profile_path
    if component_type is not None:
        params["componentType"] = component_type
    if parameter_name is not None:
        params["parameterName"] = parameter_name
    if value is not None:
        params["value"] = value
    if override_state is not None:
        params["overrideState"] = coerce_bool(override_state, default=False)

    try:
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_render_pipeline",
            params,
        )
        if isinstance(response, dict):
            return response
        return {"success": False, "message": str(response)}
    except Exception as e:
        return {"success": False, "message": f"manage_render_pipeline {action} error: {e!s}"}
