"""Read-only tool for checking Unity compilation readiness and compiler diagnostics."""

from __future__ import annotations

import re
from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations

from models import MCPResponse
from services.registry import mcp_for_unity_tool
from services.resources.editor_state import get_editor_state
from services.tools.read_console import read_console


_COMPILER_PATTERNS = (
    re.compile(r"\berror\s+CS\d+\b", re.IGNORECASE),
    re.compile(r"\bwarning\s+CS\d+\b", re.IGNORECASE),
    re.compile(r"\.cs\(\d+,\d+\)"),
    re.compile(r"\bcompilation failed\b", re.IGNORECASE),
    re.compile(r"\bscripts have compiler errors\b", re.IGNORECASE),
    re.compile(r"\btype or namespace name\b", re.IGNORECASE),
    re.compile(r"\bare you missing an assembly reference\b", re.IGNORECASE),
)


def _extract_state_data(state_response: MCPResponse | dict[str, Any]) -> dict[str, Any]:
    if isinstance(state_response, MCPResponse):
        return state_response.data if isinstance(state_response.data, dict) else {}
    if isinstance(state_response, dict):
        data = state_response.get("data")
        return data if isinstance(data, dict) else {}
    return {}


def _extract_console_items(console_response: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(console_response, dict):
        return []

    data = console_response.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def _looks_like_compiler_diagnostic(entry: dict[str, Any]) -> bool:
    file_value = str(entry.get("file") or "")
    message = str(entry.get("message") or "")

    if file_value.lower().endswith(".cs"):
        return True

    haystack = f"{message}\n{file_value}"
    return any(pattern.search(haystack) for pattern in _COMPILER_PATTERNS)


def _summarize_diagnostics(items: list[dict[str, Any]], *, compiler_only: bool) -> dict[str, Any]:
    diagnostics = []
    error_count = 0
    warning_count = 0

    for item in items:
        item_type = str(item.get("type") or "").lower()
        is_compiler = _looks_like_compiler_diagnostic(item)
        if compiler_only and not is_compiler:
            continue

        if item_type == "error":
            error_count += 1
        elif item_type == "warning":
            warning_count += 1

        diagnostics.append({
            "type": item_type or "unknown",
            "message": item.get("message"),
            "file": item.get("file"),
            "line": item.get("line"),
            "is_compiler_diagnostic": is_compiler,
        })

    return {
        "errors": error_count,
        "warnings": warning_count,
        "items": diagnostics,
    }


def _build_recommendation(compilation: dict[str, Any], advice: dict[str, Any], diagnostic_summary: dict[str, Any]) -> str:
    if compilation.get("is_compiling"):
        return "Unity is compiling. Wait for compilation to finish, then run this check again."
    if compilation.get("is_domain_reload_pending"):
        return "Unity is reloading the domain. Retry after the editor becomes ready."
    if diagnostic_summary["errors"] > 0:
        return "Compiler errors are present. Fix the reported scripts before mutation tools or tests."
    if advice.get("ready_for_tools") is False:
        blocking = ", ".join(advice.get("blocking_reasons") or [])
        return f"Editor is not ready for tools yet ({blocking}). Retry after it becomes idle."
    if diagnostic_summary["warnings"] > 0:
        return "Compilation is clear of errors. Review warnings before broad edits or test runs."
    return "Compilation looks healthy for additional tooling."


@mcp_for_unity_tool(
    name="validate_compile_health",
    description=(
        "Check Unity compile readiness and summarize recent compiler diagnostics "
        "from editor state and console output."
    ),
    group="core",
    annotations=ToolAnnotations(
        title="Validate Compile Health",
        readOnlyHint=True,
    ),
)
async def validate_compile_health(
    ctx: Context,
    include_warnings: Annotated[
        bool,
        "Whether to include warning diagnostics in the console query.",
    ] = True,
    compiler_only: Annotated[
        bool,
        "Whether to report only diagnostics that look like compiler issues.",
    ] = True,
    max_diagnostics: Annotated[
        int,
        "Maximum recent diagnostics to inspect from the Unity console.",
    ] = 50,
) -> dict[str, Any]:
    max_diagnostics = max(1, min(200, int(max_diagnostics)))

    state_response = await get_editor_state(ctx)
    if isinstance(state_response, MCPResponse) and not state_response.success:
        return state_response.model_dump()

    state_data = _extract_state_data(state_response)
    compilation = state_data.get("compilation") or {}
    advice = state_data.get("advice") or {}
    unity = state_data.get("unity") or {}

    types = ["error", "warning"] if include_warnings else ["error"]
    console_response = await read_console(
        ctx,
        action="get",
        types=types,
        count=max_diagnostics,
        format="detailed",
        include_stacktrace=False,
    )

    console_items = _extract_console_items(console_response)
    diagnostics = _summarize_diagnostics(console_items, compiler_only=compiler_only)

    has_blocking_errors = bool(compilation.get("is_compiling") or compilation.get("is_domain_reload_pending") or diagnostics["errors"] > 0)
    recommendation = _build_recommendation(compilation, advice, diagnostics)

    return {
        "success": True,
        "message": "Compile health validated.",
        "data": {
            "unity_instance": unity.get("instance_id"),
            "ready_for_mutation": not has_blocking_errors and advice.get("ready_for_tools", True),
            "compilation": {
                "is_compiling": compilation.get("is_compiling"),
                "is_domain_reload_pending": compilation.get("is_domain_reload_pending"),
                "last_compile_started_unix_ms": compilation.get("last_compile_started_unix_ms"),
                "last_compile_finished_unix_ms": compilation.get("last_compile_finished_unix_ms"),
            },
            "editor_advice": advice,
            "diagnostics": {
                "inspected_count": len(console_items),
                "reported_count": len(diagnostics["items"]),
                "error_count": diagnostics["errors"],
                "warning_count": diagnostics["warnings"],
                "items": diagnostics["items"],
                "compiler_only": compiler_only,
            },
            "recommendation": recommendation,
        },
    }
