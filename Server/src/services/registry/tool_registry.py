"""
Tool registry for auto-discovery of MCP tools.

Tools can be assigned to *groups* via the ``group`` parameter.  Groups map to
FastMCP tags (``"group:<name>"``) which drive the per-session visibility
system exposed through the ``manage_tools`` meta-tool.

The special group value ``None`` means the tool is *always visible* and
cannot be disabled by the group system (used for server meta-tools like
``set_active_instance`` and ``manage_tools``).
"""
import importlib
import sys
from pathlib import Path
from typing import Callable, Any

from utils.module_discovery import discover_modules

# Global registry to collect decorated tools
_tool_registry: list[dict[str, Any]] = []

# Valid group names. ``None`` is also accepted (always-visible meta-tools).
TOOL_GROUPS: dict[str, str] = {
    "core": "Essential scene, script, asset & editor tools (always on by default)",
    "profiling": "Unity Profiler capture, analysis, and performance diagnostics",
    "spatial": "Transform operations and spatial queries – advanced scene construction",
    "vfx": "Visual effects – VFX Graph, shaders, procedural textures",
    "animation": "Animator control & AnimationClip creation",
    "ui": "UI Toolkit (UXML, USS, UIDocument)",
    "scripting_ext": "ScriptableObject management",
    "testing": "Test runner & async test jobs",
    "input": "Unity Input System - Action Maps, Actions, Bindings, and Runtime Simulation",
    "project_config": "Project and Asset Intelligence – settings, registries, dependencies, built-in assets",
    "visual_qa": "Visual verification and screenshot analysis – AI-powered image validation",
    "pipeline": "Pipeline recording, replay, and playbook automation tools",
    # V3 Tool Groups
    "transactions": "Transaction management with rollback and preview capabilities",
    "events": "Editor event subscription and condition waiting",
    "diff_patch": "Scene and prefab diff/patch operations",
    "asset_intelligence": "Advanced asset search, indexing, and analysis",
    "navigation": "Editor navigation and focus tools",
    "pipeline_control": "Build settings, player settings, and import pipeline control",
    "dev_tools": "Internal development and debugging tools",
}

DEFAULT_ENABLED_GROUPS: set[str] = set(TOOL_GROUPS.keys())


def mcp_for_unity_tool(
    name: str | None = None,
    description: str | None = None,
    unity_target: str | None = "self",
    group: str | None = "core",
    capabilities: dict[str, bool] | None = None,
    **kwargs
) -> Callable:
    """Decorator for registering MCP tools in the server's tools directory.

    Tools are registered in the global tool registry.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description
        unity_target: Visibility target used by middleware filtering.
            - "self" (default): tool follows its own enabled state.
            - None: server-only tool, always visible in tool listing.
            - "<tool_name>": alias tool that follows another Unity tool state.
        group: Tool group for dynamic visibility.
            - A group name string (e.g. "core", "vfx") assigns the tool to
              that group and adds a ``tags={"group:<name>"}`` entry.
            - None: the tool is *always visible* (server meta-tools).
        capabilities: Optional capability overrides for this tool.
            - supports_dry_run: Whether tool supports preview mode
            - local_only: Whether tool is server-only
            - runtime_only: Whether tool requires play mode
            - requires_explicit_opt_in: Whether tool requires user opt-in
        **kwargs: Additional arguments passed to @mcp.tool()

    Example:
        @mcp_for_unity_tool(description="Does something cool")
        async def my_custom_tool(ctx: Context, ...):
            pass
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name if name is not None else func.__name__
        # Safety guard: unity_target is internal metadata and must never leak into mcp.tool kwargs.
        tool_kwargs = dict(kwargs)  # Create a copy to avoid side effects
        if "unity_target" in tool_kwargs:
            del tool_kwargs["unity_target"]
        if "group" in tool_kwargs:
            del tool_kwargs["group"]
        if "capabilities" in tool_kwargs:
            del tool_kwargs["capabilities"]

        # Validate and normalize group
        resolved_group: str | None = None
        if group is not None:
            if group not in TOOL_GROUPS:
                raise ValueError(
                    f"Unknown group '{group}' for tool '{tool_name}'. "
                    f"Valid groups: {', '.join(sorted(TOOL_GROUPS))}."
                )
            resolved_group = group
            # Merge the group tag into any existing tags the caller provided
            existing_tags: set[str] = set(tool_kwargs.get("tags") or set())
            existing_tags.add(f"group:{group}")
            tool_kwargs["tags"] = existing_tags

        if unity_target is None:
            normalized_unity_target: str | None = None
        elif isinstance(unity_target, str) and unity_target.strip():
            normalized_unity_target = (
                tool_name if unity_target == "self" else unity_target.strip()
            )
        else:
            raise ValueError(
                f"Invalid unity_target for tool '{tool_name}': {unity_target!r}. "
                "Expected None or a non-empty string."
            )

        _tool_registry.append({
            'func': func,
            'name': tool_name,
            'description': description,
            'unity_target': normalized_unity_target,
            'group': resolved_group,
            'kwargs': tool_kwargs,
            'capabilities': capabilities or {},
        })

        return func

    return decorator


def get_registered_tools() -> list[dict[str, Any]]:
    """Get all registered tools"""
    return _tool_registry.copy()


def get_group_tool_names() -> dict[str, list[str]]:
    """Return a mapping of group name -> list of tool names in that group."""
    result: dict[str, list[str]] = {g: [] for g in TOOL_GROUPS}
    for tool in _tool_registry:
        g = tool.get("group")
        if g and g in result:
            result[g].append(tool["name"])
    return result


def get_tool_by_name(tool_name: str) -> dict[str, Any] | None:
    """Get a specific tool by name.

    Args:
        tool_name: Name of the tool to find

    Returns:
        Tool dictionary or None if not found
    """
    for tool in _tool_registry:
        if tool["name"] == tool_name:
            return tool.copy()
    return None


def get_tool_capabilities(tool_name: str) -> dict[str, Any]:
    """Get declared capabilities for a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Dictionary of capability flags
    """
    tool = get_tool_by_name(tool_name)
    if tool:
        return tool.get("capabilities", {})
    return {}


def clear_tool_registry():
    """Clear the tool registry (useful for testing)"""
    _tool_registry.clear()


def ensure_tool_registry_populated() -> int:
    """Populate the registry from tool modules when running outside server startup."""
    if _tool_registry:
        return len(_tool_registry)

    tools_dir = Path(__file__).resolve().parents[1] / "tools"
    package_name = "services.tools"
    list(discover_modules(tools_dir, package_name))

    if _tool_registry:
        return len(_tool_registry)

    # If tool modules were already imported but the registry was cleared, replay
    # decorators by reloading the existing services.tools submodules.
    prefix = f"{package_name}."
    for module_name, module in list(sys.modules.items()):
        if module_name.startswith(prefix) and module is not None:
            importlib.reload(module)

    return len(_tool_registry)
