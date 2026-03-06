"""
Runtime UI automation tool for interacting with uGUI and UI Toolkit elements during Play mode.

WARNING: This tool only works in Play mode (runtime_only). It is marked as high_risk
because it simulates user input that can affect game state.

Supports:
- uGUI (Canvas-based): Buttons, InputFields, Sliders, Toggles, Dropdowns, ScrollViews
- UI Toolkit (Runtime): VisualElements, Buttons, TextFields, etc.
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
        "Runtime UI automation for Play mode - interact with uGUI and UI Toolkit elements. "
        "WARNING: Only works during Play mode. High-risk tool that simulates user input. "
        "\n\nActions:\n"
        "- find_elements: Search UI elements by type, name, text, or automation ID\n"
        "- get_element_state: Get element properties (text, enabled, visible, position, hierarchy path)\n"
        "- click: Simulate click/tap on a button or any interactive element\n"
        "- set_text: Enter text into InputField or TextField\n"
        "- set_value: Set Slider value, Toggle state, or Dropdown index\n"
        "- scroll: Scroll a ScrollView or ScrollRect\n"
        "- hover: Move cursor over element (triggers hover states)\n"
        "- wait_for_element: Poll until element appears or timeout\n"
        "- get_screenshot: Capture screenshot of specific UI element\n"
        "\n\nSupported UI Systems:\n"
        "- uGUI: Canvas-based UI (GameObject hierarchy)\n"
        "- UI Toolkit: Runtime VisualElement-based UI\n"
        "\n\nElement Queries:\n"
        "- Query by name: element name/path\n"
        "- Query by type: Button, InputField, Slider, etc.\n"
        "- Query by text content: button label, input placeholder\n"
        "- Query by automation ID: data-testid or name attribute"
    ),
    annotations=ToolAnnotations(
        title="Manage Runtime UI",
        destructiveHint=True,
        openWorldHint=False,
    ),
)
async def manage_runtime_ui(
    ctx: Context,
    action: Annotated[Literal[
        "find_elements",
        "get_element_state",
        "click",
        "set_text",
        "set_value",
        "scroll",
        "hover",
        "wait_for_element",
        "get_screenshot",
    ], "Action to perform on the runtime UI."],
    # Common params
    ui_system: Annotated[Literal["auto", "ugui", "uitoolkit"] | None,
                         "Which UI system to target: ugui (Canvas), uitoolkit, or auto-detect (default)."] = None,
    # Element identification
    element_path: Annotated[str | None,
                            "Full hierarchy path to element (e.g., 'Canvas/Panel/Button'). "
                            "Supports uGUI and UI Toolkit."] = None,
    element_name: Annotated[str | None,
                            "Element name to search for."] = None,
    element_type: Annotated[str | None,
                            "Type of element: Button, InputField, Slider, Toggle, Dropdown, ScrollView, etc."] = None,
    element_text: Annotated[str | None,
                            "Text content to search for (button label, etc.)."] = None,
    automation_id: Annotated[str | None,
                             "Automation ID for UI Toolkit elements (name attribute or data-testid)."] = None,
    # Action params
    text: Annotated[str | None,
                    "Text to enter (for set_text action)."] = None,
    value: Annotated[float | bool | int | None,
                     "Value to set: float for Slider, bool for Toggle, int for Dropdown index (for set_value)."] = None,
    scroll_delta: Annotated[dict[str, float] | None,
                            "Scroll amount as {x, y} for scroll action (default: {x:0, y:-100})."] = None,
    scroll_to_end: Annotated[bool | None,
                             "Scroll to end of content (for scroll action)."] = None,
    # Wait params
    timeout_seconds: Annotated[float | None,
                               "Timeout for wait_for_element (default: 10.0)."] = None,
    poll_interval: Annotated[float | None,
                             "Polling interval for wait_for_element (default: 0.5)."] = None,
    # Screenshot params
    max_resolution: Annotated[int | None,
                              "Max resolution for element screenshot (default: 640)."] = None,
    include_image: Annotated[bool | None,
                             "Return base64 image in response (default: true for get_screenshot)."] = None,
    # Find options
    max_results: Annotated[int | None,
                           "Maximum number of elements to return (default: 50)."] = None,
    include_invisible: Annotated[bool | None,
                                  "Include invisible elements in search (default: false)."] = None,
) -> dict[str, Any]:
    """
    Automate runtime UI interactions in Play mode.
    """
    action_lower = action.lower()
    uses_mutation_transport = tool_action_is_mutating("manage_runtime_ui", action=action_lower)

    gate = await maybe_run_tool_preflight(ctx, "manage_runtime_ui", action=action_lower)
    if gate is not None:
        return gate.model_dump()

    unity_instance = await get_unity_instance_from_context(ctx)

    # Build params dict
    params_dict: dict[str, Any] = {"action": action_lower}

    if ui_system is not None:
        params_dict["uiSystem"] = ui_system
    if element_path is not None:
        params_dict["elementPath"] = element_path
    if element_name is not None:
        params_dict["elementName"] = element_name
    if element_type is not None:
        params_dict["elementType"] = element_type
    if element_text is not None:
        params_dict["elementText"] = element_text
    if automation_id is not None:
        params_dict["automationId"] = automation_id
    if text is not None:
        params_dict["text"] = text
    if value is not None:
        params_dict["value"] = value
    if scroll_delta is not None:
        params_dict["scrollDelta"] = scroll_delta
    if scroll_to_end is not None:
        params_dict["scrollToEnd"] = scroll_to_end
    if timeout_seconds is not None:
        params_dict["timeoutSeconds"] = timeout_seconds
    if poll_interval is not None:
        params_dict["pollInterval"] = poll_interval
    if max_resolution is not None:
        params_dict["maxResolution"] = max_resolution
    if include_image is not None:
        params_dict["includeImage"] = include_image
    if max_results is not None:
        params_dict["maxResults"] = max_results
    if include_invisible is not None:
        params_dict["includeInvisible"] = include_invisible

    # Route to Unity
    if uses_mutation_transport:
        result = await send_mutation(
            ctx, unity_instance, "manage_runtime_ui", params_dict,
        )
    else:
        result = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_runtime_ui",
            params_dict,
        )

    return result if isinstance(result, dict) else {"success": False, "message": str(result)}
