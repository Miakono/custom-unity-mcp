"""
Code Intelligence Tool - Local code indexing and search for Unity projects.

This tool provides code intelligence capabilities WITHOUT requiring Unity to be running.
It uses file system operations only and caches the index for fast lookups.

Actions:
- search_code: Search across all C# files using regex or text search
- find_symbol: Find class/method/field definitions by name
- find_references: Find all references to a symbol
- get_symbols: List all symbols in a file or codebase
- build_code_index: Build a searchable index of the codebase
- update_code_index: Incrementally update the code index
- get_index_status: Get index statistics and status
- clear_code_index: Clear the index and cache
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.code_indexer import get_index_manager

logger = logging.getLogger("mcp-for-unity-server")


@mcp_for_unity_tool(
    unity_target=None,
    group="core",
    description=(
        """Local code intelligence for Unity C# projects - works WITHOUT Unity running!
        
Actions:
- search_code: Search across all C# files using regex or text search
- find_symbol: Find class/method/field definitions by name  
- find_references: Find all references to a symbol
- get_symbols: List all symbols in a file or across the codebase
- build_code_index: Build/update the searchable code index
- update_code_index: Incrementally update based on file changes
- get_index_status: Get index statistics
- clear_code_index: Clear the index cache

This tool indexes your C# code locally using file system operations only.
The index is cached for fast lookups and supports incremental updates."""
    ),
    annotations=ToolAnnotations(
        title="Code Intelligence",
        readOnlyHint=False,
    ),
)
async def manage_code_intelligence(
    ctx: Context,
    action: Annotated[
        Literal[
            "search_code",
            "find_symbol",
            "find_references",
            "get_symbols",
            "build_code_index",
            "update_code_index",
            "get_index_status",
            "clear_code_index"
        ],
        "The action to perform"
    ],
    project_root: Annotated[
        str | None,
        "Optional project root path. If not provided, uses current working directory"
    ] = None,
    # search_code parameters
    pattern: Annotated[
        str | None,
        "For search_code: The regex pattern or text to search for"
    ] = None,
    use_regex: Annotated[
        bool,
        "For search_code: Whether to treat pattern as regex (default: True)"
    ] = True,
    ignore_case: Annotated[
        bool,
        "For search_code: Case insensitive search (default: True)"
    ] = True,
    file_pattern: Annotated[
        str | None,
        "For search_code: Optional file pattern to filter files (e.g., 'Controller')"
    ] = None,
    # symbol search parameters
    symbol_name: Annotated[
        str | None,
        "For find_symbol/find_references: The symbol name to search for"
    ] = None,
    symbol_type: Annotated[
        str | None,
        "For find_symbol/get_symbols: Filter by symbol type (class, method, property, field, interface, struct, enum, event, delegate)"
    ] = None,
    exact_match: Annotated[
        bool,
        "For find_symbol: Whether to match symbol name exactly (default: True)"
    ] = True,
    # file-specific parameters
    file_path: Annotated[
        str | None,
        "For get_symbols: Specific file to list symbols from. If not provided, searches all files"
    ] = None,
    namespace: Annotated[
        str | None,
        "For get_symbols: Filter by namespace"
    ] = None,
    # build/update parameters
    include_packages: Annotated[
        bool,
        "For build_code_index: Whether to include Packages/ folder (default: False)"
    ] = False,
    force_rebuild: Annotated[
        bool,
        "For build_code_index: Force full rebuild even if cache exists (default: False)"
    ] = False,
    # pagination parameters
    offset: Annotated[
        int,
        "Pagination offset for results (default: 0)"
    ] = 0,
    max_results: Annotated[
        int,
        "Maximum number of results to return (default: 100, max: 500)"
    ] = 100,
) -> dict[str, Any]:
    """
    Code intelligence tool for local C# code indexing and search.
    Works WITHOUT Unity running - uses file system operations only.
    """
    await ctx.info(f"Processing manage_code_intelligence: {action}")
    
    # Clamp max_results
    max_results = min(max(1, max_results), 500)
    
    try:
        # Get or create index manager
        manager = get_index_manager(project_root)
        
        if action == "search_code":
            if not pattern:
                return {
                    "success": False,
                    "error": "pattern is required for search_code action"
                }
            
            # Ensure index is built
            status = manager.get_index_status()
            if not status["loaded"] or status["files_indexed"] == 0:
                await ctx.info("Index not found, building...")
                manager.build_index(include_packages=include_packages)
            
            result = manager.search_code(
                pattern=pattern,
                regex=use_regex,
                ignore_case=ignore_case,
                file_pattern=file_pattern,
                max_results=max_results,
                offset=offset
            )
            return result
        
        elif action == "find_symbol":
            if not symbol_name:
                return {
                    "success": False,
                    "error": "symbol_name is required for find_symbol action"
                }
            
            # Ensure index is built
            status = manager.get_index_status()
            if not status["loaded"] or status["files_indexed"] == 0:
                await ctx.info("Index not found, building...")
                manager.build_index(include_packages=include_packages)
            
            result = manager.find_symbol(
                name=symbol_name,
                symbol_type=symbol_type,
                exact_match=exact_match
            )
            return result
        
        elif action == "find_references":
            if not symbol_name:
                return {
                    "success": False,
                    "error": "symbol_name is required for find_references action"
                }
            
            # Ensure index is built
            status = manager.get_index_status()
            if not status["loaded"] or status["files_indexed"] == 0:
                await ctx.info("Index not found, building...")
                manager.build_index(include_packages=include_packages)
            
            result = manager.find_references(
                symbol_name=symbol_name,
                max_results=max_results,
                offset=offset
            )
            return result
        
        elif action == "get_symbols":
            # Ensure index is built
            status = manager.get_index_status()
            if not status["loaded"] or status["files_indexed"] == 0:
                await ctx.info("Index not found, building...")
                manager.build_index(include_packages=include_packages)
            
            result = manager.get_symbols(
                file_path=file_path,
                symbol_type=symbol_type,
                namespace=namespace,
                max_results=max_results,
                offset=offset
            )
            return result
        
        elif action == "build_code_index":
            result = manager.build_index(
                include_packages=include_packages,
                force_rebuild=force_rebuild
            )
            return result
        
        elif action == "update_code_index":
            result = manager.update_index(include_packages=include_packages)
            return result
        
        elif action == "get_index_status":
            result = manager.get_index_status()
            return result
        
        elif action == "clear_code_index":
            result = manager.clear_index()
            return result
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
    
    except Exception as e:
        logger.exception(f"Error in manage_code_intelligence: {e}")
        return {
            "success": False,
            "error": f"Code intelligence error: {str(e)}"
        }


@mcp_for_unity_tool(
    unity_target=None,
    group="core",
    description=(
        """Quickly search C# code files using regex patterns.
        
Works WITHOUT Unity running - uses local file system.
Returns file paths, line numbers, and matching content.

Example patterns:
- "class.*Controller" - Find controller classes
- "public void.*\\(" - Find public void methods
- "SerializeField" - Find all SerializeField attributes"""
    ),
    annotations=ToolAnnotations(
        title="Search Code",
        readOnlyHint=True,
    ),
)
async def search_code(
    ctx: Context,
    pattern: Annotated[str, "The regex pattern to search for"],
    project_root: Annotated[str | None, "Optional project root path"] = None,
    file_pattern: Annotated[str | None, "Optional file name pattern to filter (e.g., 'Player')"] = None,
    use_regex: Annotated[bool, "Treat pattern as regex (default: True)"] = True,
    ignore_case: Annotated[bool, "Case insensitive search (default: True)"] = True,
    max_results: Annotated[int, "Maximum results (default: 100)"] = 100,
) -> dict[str, Any]:
    """Quick code search using regex patterns."""
    await ctx.info(f"Searching code: {pattern}")
    
    try:
        manager = get_index_manager(project_root)
        
        # Auto-build index if needed
        status = manager.get_index_status()
        if not status["loaded"] or status["files_indexed"] == 0:
            await ctx.info("Building code index...")
            manager.build_index()
        
        result = manager.search_code(
            pattern=pattern,
            regex=use_regex,
            ignore_case=ignore_case,
            file_pattern=file_pattern,
            max_results=min(max_results, 500)
        )
        return result
    
    except Exception as e:
        logger.exception(f"Error in search_code: {e}")
        return {"success": False, "error": str(e)}


@mcp_for_unity_tool(
    unity_target=None,
    group="core",
    description=(
        """Find definitions of classes, methods, properties, fields, etc.
        
Works WITHOUT Unity running - uses local file system.
Returns symbol details including file path, line number, modifiers, etc.

Example searches:
- symbol_name="PlayerController" - Find PlayerController class
- symbol_name="Update", symbol_type="method" - Find Update methods"""
    ),
    annotations=ToolAnnotations(
        title="Find Symbol",
        readOnlyHint=True,
    ),
)
async def find_symbol(
    ctx: Context,
    name: Annotated[str, "The symbol name to find"],
    project_root: Annotated[str | None, "Optional project root path"] = None,
    symbol_type: Annotated[
        str | None,
        "Optional type filter: class, interface, struct, enum, method, property, field, event, delegate"
    ] = None,
    exact_match: Annotated[bool, "Match name exactly (default: True)"] = True,
) -> dict[str, Any]:
    """Find symbol definitions by name."""
    await ctx.info(f"Finding symbol: {name}")
    
    try:
        manager = get_index_manager(project_root)
        
        # Auto-build index if needed
        status = manager.get_index_status()
        if not status["loaded"] or status["files_indexed"] == 0:
            await ctx.info("Building code index...")
            manager.build_index()
        
        result = manager.find_symbol(
            name=name,
            symbol_type=symbol_type,
            exact_match=exact_match
        )
        return result
    
    except Exception as e:
        logger.exception(f"Error in find_symbol: {e}")
        return {"success": False, "error": str(e)}


@mcp_for_unity_tool(
    unity_target=None,
    group="core",
    description=(
        """Find all references to a symbol across the codebase.
        
Works WITHOUT Unity running - uses local file system.
Returns all locations where the symbol is used."""
    ),
    annotations=ToolAnnotations(
        title="Find References",
        readOnlyHint=True,
    ),
)
async def find_references(
    ctx: Context,
    symbol_name: Annotated[str, "The symbol name to find references for"],
    project_root: Annotated[str | None, "Optional project root path"] = None,
    max_results: Annotated[int, "Maximum results (default: 100)"] = 100,
) -> dict[str, Any]:
    """Find all references to a symbol."""
    await ctx.info(f"Finding references: {symbol_name}")
    
    try:
        manager = get_index_manager(project_root)
        
        # Auto-build index if needed
        status = manager.get_index_status()
        if not status["loaded"] or status["files_indexed"] == 0:
            await ctx.info("Building code index...")
            manager.build_index()
        
        result = manager.find_references(
            symbol_name=symbol_name,
            max_results=min(max_results, 500)
        )
        return result
    
    except Exception as e:
        logger.exception(f"Error in find_references: {e}")
        return {"success": False, "error": str(e)}


@mcp_for_unity_tool(
    unity_target=None,
    group="core",
    description=(
        """List all symbols in a file or across the codebase.
        
Works WITHOUT Unity running - uses local file system.
Can filter by symbol type and namespace."""
    ),
    annotations=ToolAnnotations(
        title="Get Symbols",
        readOnlyHint=True,
    ),
)
async def get_symbols(
    ctx: Context,
    project_root: Annotated[str | None, "Optional project root path"] = None,
    file_path: Annotated[str | None, "Specific file to list symbols from"] = None,
    symbol_type: Annotated[
        str | None,
        "Optional type filter: class, interface, struct, enum, method, property, field, event, delegate"
    ] = None,
    namespace: Annotated[str | None, "Optional namespace filter"] = None,
    max_results: Annotated[int, "Maximum results (default: 100)"] = 100,
) -> dict[str, Any]:
    """List symbols in a file or codebase."""
    await ctx.info("Getting symbols")
    
    try:
        manager = get_index_manager(project_root)
        
        # Auto-build index if needed
        status = manager.get_index_status()
        if not status["loaded"] or status["files_indexed"] == 0:
            await ctx.info("Building code index...")
            manager.build_index()
        
        result = manager.get_symbols(
            file_path=file_path,
            symbol_type=symbol_type,
            namespace=namespace,
            max_results=min(max_results, 500)
        )
        return result
    
    except Exception as e:
        logger.exception(f"Error in get_symbols: {e}")
        return {"success": False, "error": str(e)}


@mcp_for_unity_tool(
    unity_target=None,
    group="core",
    description=(
        """Build or update the code intelligence index.
        
Works WITHOUT Unity running - uses local file system.
Indexes all C# files in Assets/ (and optionally Packages/).
The index is cached for fast subsequent lookups."""
    ),
    annotations=ToolAnnotations(
        title="Build Code Index",
        readOnlyHint=False,
    ),
)
async def build_code_index(
    ctx: Context,
    project_root: Annotated[str | None, "Optional project root path"] = None,
    include_packages: Annotated[bool, "Include Packages/ folder (default: False)"] = False,
    force_rebuild: Annotated[bool, "Force full rebuild (default: False)"] = False,
) -> dict[str, Any]:
    """Build the code intelligence index."""
    await ctx.info("Building code index")
    
    try:
        manager = get_index_manager(project_root)
        result = manager.build_index(
            include_packages=include_packages,
            force_rebuild=force_rebuild
        )
        return result
    
    except Exception as e:
        logger.exception(f"Error in build_code_index: {e}")
        return {"success": False, "error": str(e)}


@mcp_for_unity_tool(
    unity_target=None,
    group="core",
    description=(
        """Get code intelligence index status and statistics.
        
Returns information about indexed files, symbol counts, etc."""
    ),
    annotations=ToolAnnotations(
        title="Code Index Status",
        readOnlyHint=True,
    ),
)
async def code_index_status(
    ctx: Context,
    project_root: Annotated[str | None, "Optional project root path"] = None,
) -> dict[str, Any]:
    """Get the code index status."""
    await ctx.info("Getting code index status")
    
    try:
        manager = get_index_manager(project_root)
        result = manager.get_index_status()
        return result
    
    except Exception as e:
        logger.exception(f"Error in code_index_status: {e}")
        return {"success": False, "error": str(e)}
