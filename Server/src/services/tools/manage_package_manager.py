"""
Defines the manage_package_manager tool for interacting with Unity's Package Manager.

This tool provides functionality to:
- List installed packages with their versions and sources
- Search Unity Package Registry for packages
- Add packages (registry, git, local, tarball)
- Remove packages
- Get detailed package information
- List configured scoped registries
- Resolve dependencies (force package resolution)
"""
from __future__ import annotations

import asyncio
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.package_resolver import PackageResolver, PackageSource
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry
from services.tools.action_policy import maybe_run_tool_preflight


# Actions that are read-only (non-mutating)
_READ_ONLY_ACTIONS = {
    "list_installed",
    "search_packages",
    "get_package_info",
    "list_registries",
}


@mcp_for_unity_tool(
    description=(
        "Manages Unity Package Manager packages and dependencies.\n\n"
        "Read-only actions (safe): list_installed, search_packages, get_package_info, list_registries.\n"
        "Mutating actions (modifies project): add_package, remove_package, resolve_dependencies.\n\n"
        "Supports all package sources: registry, git, local path, tarball.\n"
        "Returns structured data with name, version, source, and dependencies."
    ),
    annotations=ToolAnnotations(
        title="Manage Package Manager",
        destructiveHint=True,
    ),
    group="core",
)
async def manage_package_manager(
    ctx: Context,
    action: Annotated[
        Literal[
            "list_installed",
            "search_packages",
            "add_package",
            "remove_package",
            "get_package_info",
            "list_registries",
            "resolve_dependencies",
        ],
        "Package manager action to perform."
    ],
    # For add_package / remove_package / get_package_info
    package_name: Annotated[
        str,
        "Package name (e.g., 'com.unity.entities', 'com.unity.textmeshpro')"
    ] | None = None,
    # For add_package - version specification
    version: Annotated[
        str,
        "Version specification. Can be: version number (e.g., '1.0.0'), git URL, local path, or tarball path."
    ] | None = None,
    # For search_packages
    search_query: Annotated[
        str,
        "Search query for searching packages in Unity Package Registry."
    ] | None = None,
    # For search_packages - pagination
    page_size: Annotated[
        int | float | str,
        "Number of results per page (default: 20, max: 100)."
    ] | None = None,
    page: Annotated[
        int | float | str,
        "Page number for pagination (1-based, default: 1)."
    ] | None = None,
    # For search_packages - filters
    include_prerelease: Annotated[
        bool | str,
        "Include pre-release packages in search results."
    ] = False,
    # For list_installed - filter by source
    source_filter: Annotated[
        Literal["registry", "git", "local", "tarball", "built-in", "all"],
        "Filter packages by source type."
    ] = "all",
    # For add_package with git - branch/tag/revision
    git_ref: Annotated[
        str,
        "Git branch, tag, or revision hash (for git packages)."
    ] | None = None,
) -> dict[str, Any]:
    """
    Manage Unity Package Manager packages.
    
    This tool allows listing, searching, adding, and removing packages
    from the Unity Package Manager. It supports all package sources:
    registry, git, local, and tarball.
    
    Read-only actions don't modify the project:
    - list_installed: List all installed packages
    - search_packages: Search Unity Package Registry
    - get_package_info: Get info about a specific package
    - list_registries: List configured scoped registries
    
    Mutating actions modify the project:
    - add_package: Add a package
    - remove_package: Remove a package
    - resolve_dependencies: Force package resolution
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    # Run preflight checks for mutating actions
    gate = await maybe_run_tool_preflight(ctx, "manage_package_manager", action=action)
    if gate is not None:
        return gate.model_dump()
    
    # Handle read-only actions that can be served from manifest directly
    if action in _READ_ONLY_ACTIONS:
        result = await _handle_read_only_action(
            ctx, action, package_name, search_query, source_filter,
            page_size, page, include_prerelease
        )
        return result
    
    # Handle mutating actions - send to Unity
    try:
        params = _build_params(
            action, package_name, version, search_query,
            page_size, page, include_prerelease, source_filter, git_ref
        )
        
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_package_manager",
            params
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", "Package operation successful."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
        
    except Exception as e:
        return {"success": False, "message": f"Package manager error: {str(e)}"}


def _coerce_int(value: int | float | str | None, default: int | None = None) -> int | None:
    """Coerce a value to integer."""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _coerce_bool(value: bool | str | None, default: bool = False) -> bool:
    """Coerce a value to boolean."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return default


def _build_params(
    action: str,
    package_name: str | None,
    version: str | None,
    search_query: str | None,
    page_size: int | float | str | None,
    page: int | float | str | None,
    include_prerelease: bool | str,
    source_filter: str,
    git_ref: str | None
) -> dict[str, Any]:
    """Build the parameters dictionary for Unity."""
    params: dict[str, Any] = {"action": action}
    
    if package_name:
        params["packageName"] = package_name
    if version:
        params["version"] = version
    if search_query:
        params["searchQuery"] = search_query
    if git_ref:
        params["gitRef"] = git_ref
    
    # Coerce pagination params
    coerced_page_size = _coerce_int(page_size)
    if coerced_page_size is not None:
        params["pageSize"] = coerced_page_size
    
    coerced_page = _coerce_int(page, default=1)
    if coerced_page is not None:
        params["page"] = coerced_page
    
    params["includePrerelease"] = _coerce_bool(include_prerelease, default=False)
    params["sourceFilter"] = source_filter
    
    return params


async def _handle_read_only_action(
    ctx: Context,
    action: str,
    package_name: str | None,
    search_query: str | None,
    source_filter: str,
    page_size: int | float | str | None,
    page: int | float | str | None,
    include_prerelease: bool | str
) -> dict[str, Any]:
    """Handle read-only actions using the PackageResolver for quick manifest access."""
    
    resolver = PackageResolver()
    
    if action == "list_installed":
        manifest = resolver.get_manifest()
        if manifest is None:
            return {"success": False, "message": "Could not read package manifest."}
        
        packages = manifest.dependencies.values()
        
        # Apply source filter
        if source_filter != "all":
            source_map = {
                "registry": PackageSource.REGISTRY,
                "git": PackageSource.GIT,
                "local": PackageSource.LOCAL,
                "tarball": PackageSource.TARBALL,
                "built-in": PackageSource.BUILT_IN,
            }
            target_source = source_map.get(source_filter)
            if target_source:
                packages = [p for p in packages if p.source == target_source]
        
        package_list = [
            {
                "name": pkg.name,
                "version": pkg.version,
                "source": pkg.source.value,
                **({"gitUrl": pkg.git_url} if pkg.git_url else {}),
                **({"localPath": pkg.local_path} if pkg.local_path else {}),
                **({"tarballPath": pkg.tarball_path} if pkg.tarball_path else {}),
                **({"resolvedPath": pkg.resolved_path} if pkg.resolved_path else {}),
                **({"isTestPackage": True} if pkg.is_test_package else {}),
                **({"dependencies": pkg.dependencies} if pkg.dependencies else {}),
            }
            for pkg in packages
        ]
        
        # Sort by name for consistency
        package_list.sort(key=lambda x: x["name"])
        
        return {
            "success": True,
            "message": f"Found {len(package_list)} installed packages.",
            "data": {
                "packages": package_list,
                "totalCount": len(package_list),
                "sourceFilter": source_filter
            }
        }
    
    elif action == "get_package_info":
        if not package_name:
            return {"success": False, "message": "package_name is required for get_package_info."}
        
        pkg = resolver.get_package_info(package_name)
        if pkg is None:
            return {"success": False, "message": f"Package '{package_name}' not found in manifest."}
        
        return {
            "success": True,
            "message": f"Package info for '{package_name}'.",
            "data": {
                "name": pkg.name,
                "version": pkg.version,
                "source": pkg.source.value,
                **({"gitUrl": pkg.git_url} if pkg.git_url else {}),
                **({"localPath": pkg.local_path} if pkg.local_path else {}),
                **({"tarballPath": pkg.tarball_path} if pkg.tarball_path else {}),
                **({"resolvedPath": pkg.resolved_path} if pkg.resolved_path else {}),
                **({"isTestPackage": True} if pkg.is_test_package else {}),
                **({"dependencies": pkg.dependencies} if pkg.dependencies else {}),
            }
        }
    
    elif action == "list_registries":
        manifest = resolver.get_manifest()
        if manifest is None:
            return {"success": False, "message": "Could not read package manifest."}
        
        registries = [
            {
                "name": reg.name,
                "url": reg.url,
                "scopes": reg.scopes
            }
            for reg in manifest.scoped_registries
        ]
        
        return {
            "success": True,
            "message": f"Found {len(registries)} scoped registries.",
            "data": {
                "registries": registries,
                "totalCount": len(registries)
            }
        }
    
    elif action == "search_packages":
        # For search_packages, we delegate to Unity which has access to the Package Manager API
        # But we can do a quick local search in the manifest first for installed packages
        unity_instance = await get_unity_instance_from_context(ctx)
        
        params = _build_params(
            action, package_name, None, search_query,
            page_size, page, include_prerelease, source_filter, None
        )
        
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_package_manager",
            params
        )
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "success": True,
                "message": response.get("message", "Search completed."),
                "data": response.get("data")
            }
        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
    
    return {"success": False, "message": f"Unknown action: {action}"}
