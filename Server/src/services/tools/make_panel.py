"""
Defines the make_panel tool for generating Unity UI Toolkit panels from
named component templates (Modal, LevelUpChoice). Pairs with the runtime
component library under Packages/com.customgamedev.unity-mcp/Runtime/UI/.
"""
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.action_policy import maybe_run_tool_preflight, tool_action_is_mutating
from services.tools.refresh_unity import send_mutation
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    group="ui",
    description=(
        "Generates ready-to-use UI Toolkit panels from a registry of named templates. "
        "Writes a .uxml referencing token-styled markup plus a sibling .uss for project-specific overrides. "
        "Built-in templates use tokens.uss so they stay visually consistent with the MCPForUnity component library.\n\n"
        "Actions:\n"
        "  generate         — write a panel's .uxml + .uss to outputPath.\n"
        "  attach_to_scene  — wire the generated panel to a UIDocument on a target GameObject.\n"
        "  list_templates   — return all registered template names + aliases (no params required).\n\n"
        "Built-in templates:\n"
        "  modal           params: { title, bodyText (or bodyXml), showCloseButton (bool), openOnAttach (bool) }\n"
        "  level_up        params: { title, choices: [{ name, description, iconPath, rarity, isPrimary }, ...] }\n"
        "                  rarity: Common | Uncommon | Rare | Epic | Legendary\n"
        "  loading_screen  params: { title, subtitle, progress (0..1) }\n"
        "                  full-screen panel with centered title and a #loading-screen__bar-fill progress bar slot.\n"
        "  confirm_dialog  params: { title, body, confirmText, cancelText, danger (bool) }\n"
        "                  modal with title, body, and #confirm-yes / #confirm-no buttons.\n"
        "  picker          params: { title, itemHeight (int), showCancel (bool) }\n"
        "                  modal wrapping a #picker-list ListView. Bind itemsSource/makeItem/bindItem from C#.\n"
        "  slotted         params: { title (optional), rootName }\n"
        "                  generic panel with a #content slot — token-styled but no extra chrome.\n\n"
        "Project-side templates: register from an [InitializeOnLoad] static ctor via "
        "MakePanelTemplateRegistry.Register(name, generator, aliases). They become discoverable through list_templates."
    ),
    annotations=ToolAnnotations(
        title="Make Panel",
        destructiveHint=True,
    ),
)
async def make_panel(
    ctx: Context,
    action: Annotated[Literal[
        "generate",
        "attach_to_scene",
        "attach",
        "list_templates",
    ], "Action to perform."] = "generate",

    # NOTE: kept as `str | None` (not Literal) so projects can register custom
    # template names without editing this file. The C# side validates against
    # MakePanelTemplateRegistry; call action='list_templates' to discover.
    template: Annotated[str,
                        "Template name (built-ins: modal, level_up, loading_screen, confirm_dialog, picker, slotted; "
                        "or any project-registered name). Required for generate."] | None = None,

    output_path: Annotated[str,
                            "Assets-relative .uxml path to write (e.g. 'Assets/UI/LevelUp.uxml'). "
                            "A sibling .uss with the same stem is also written. Required for generate."] | None = None,

    params: Annotated[dict[str, Any],
                       "Template-specific parameters. See tool description for shape per template."] | None = None,

    overwrite: Annotated[bool,
                          "Allow overwriting an existing .uxml/.uss at outputPath (default false)."] | None = None,

    # attach_to_scene parameters (delegated to manage_ui's attach_ui_document)
    target: Annotated[str,
                       "Target GameObject name or hierarchy path. Required for attach_to_scene."] | None = None,
    panel_settings: Annotated[str,
                               "Path to PanelSettings asset. Auto-creates default if omitted. For attach_to_scene."] | None = None,
    sort_order: Annotated[int,
                           "UIDocument sort order (default 0). For attach_to_scene."] | None = None,

) -> dict[str, Any]:
    action_lower = action.lower()
    uses_mutation_transport = tool_action_is_mutating("make_panel", action=action_lower)

    gate = await maybe_run_tool_preflight(ctx, "make_panel", action=action_lower)
    if gate is not None:
        return gate.model_dump()

    unity_instance = await get_unity_instance_from_context(ctx)

    params_dict: dict[str, Any] = {"action": action_lower}

    if action_lower == "generate":
        if not template:
            return {"success": False, "message": "'template' is required for the generate action."}
        if not output_path:
            return {"success": False, "message": "'output_path' is required for the generate action."}
        params_dict["template"] = template
        params_dict["outputPath"] = output_path
        if params is not None:
            params_dict["params"] = params
        if overwrite is not None:
            params_dict["overwrite"] = bool(overwrite)
    elif action_lower == "list_templates":
        # No required params — the registry is the source of truth and lookup
        # is read-only. Forward the action verbatim.
        pass
    elif action_lower in ("attach_to_scene", "attach"):
        if not output_path:
            return {"success": False, "message": "'output_path' is required (the .uxml just generated)."}
        if not target:
            return {"success": False, "message": "'target' is required for attach_to_scene."}
        params_dict["outputPath"] = output_path
        params_dict["target"] = target
        if panel_settings is not None:
            params_dict["panelSettings"] = panel_settings
        if sort_order is not None:
            params_dict["sortOrder"] = sort_order

    if uses_mutation_transport:
        result = await send_mutation(
            ctx, unity_instance, "make_panel", params_dict,
        )
    else:
        result = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "make_panel",
            params_dict,
        )

    if isinstance(result, dict):
        return result
    return {"success": False, "message": str(result)}
