"""
Unified diagnostics tool that aggregates various editor health metrics in a single call.
Provides comprehensive project diagnostics including compile state, console errors,
profiler data, test results, and scene integrity.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from models import MCPResponse
from services.profiler_helper import (
    AggregatedStats,
    ProfilerDataAggregator,
    generate_performance_report,
)
from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry

logger = logging.getLogger(__name__)


class CompileHealth(BaseModel):
    """Compilation health information."""
    status: str
    hasErrors: bool
    hasWarnings: bool
    errorCount: int
    warningCount: int
    lastCompileTime: str | None = None


class ConsoleSummary(BaseModel):
    """Console messages summary."""
    errorCount: int
    warningCount: int
    logCount: int
    recentErrors: list[dict[str, Any]] | None = None


class ProfilerSummary(BaseModel):
    """Profiler performance summary."""
    isRecording: bool
    snapshotCount: int
    avgFrameTimeMs: float | None = None
    avgFps: float | None = None
    avgMemoryMB: float | None = None


class TestSummary(BaseModel):
    """Test run summary."""
    lastRunStatus: str | None = None
    totalTests: int | None = None
    passed: int | None = None
    failed: int | None = None
    skipped: int | None = None


class SceneHealth(BaseModel):
    """Scene integrity health."""
    sceneName: str | None = None
    isDirty: bool
    missingReferences: list[str] | None = None
    brokenPrefabs: list[str] | None = None


class DiagnosticsData(BaseModel):
    """Complete diagnostics data."""
    timestamp: int
    unityVersion: str | None = None
    isEditor: bool | None = None
    isPlaying: bool | None = None
    compileHealth: CompileHealth
    consoleSummary: ConsoleSummary
    profilerSummary: ProfilerSummary | None = None
    testSummary: TestSummary | None = None
    sceneHealth: SceneHealth | None = None
    overallStatus: str
    issues: list[dict[str, Any]]
    recommendations: list[str]


class DiagnosticsResponse(MCPResponse):
    """Response for get_diagnostics."""
    data: DiagnosticsData | None = None


@mcp_for_unity_tool(
    group="core",
    description=(
        "Gets comprehensive diagnostics for the Unity project in a single call. "
        "Aggregates: compile state, console errors/warnings, profiler snapshot, "
        "test results, scene dirty state, and prefab integrity. "
        "Use this for quick health checks before/after operations. "
        "Read-only operation - does not modify any project state."
    ),
    annotations=ToolAnnotations(
        title="Get Diagnostics",
        readOnlyHint=True,
    ),
)
async def get_diagnostics(
    ctx: Context,
    include_profiler: Annotated[
        bool | str,
        "Include profiler data (default: true)"
    ] = True,
    include_tests: Annotated[
        bool | str,
        "Include test results (default: true)"
    ] = True,
    include_scene_health: Annotated[
        bool | str,
        "Include scene integrity check (default: true)"
    ] = True,
    include_console: Annotated[
        bool | str,
        "Include console summary (default: true)"
    ] = True,
    console_error_limit: Annotated[
        int | str,
        "Max recent errors to include (default: 5)"
    ] = 5,
    severity_threshold: Annotated[
        Literal["info", "warning", "error"],
        "Minimum severity to report (default: info)"
    ] = "info",
) -> dict[str, Any]:
    """Get comprehensive Unity project diagnostics.

    This tool aggregates multiple health checks into a single call, providing:
    - Compile health (errors, warnings, status)
    - Console summary (error/warning counts, recent errors)
    - Profiler snapshot (frame time, FPS, memory)
    - Test results (last run status, pass/fail counts)
    - Scene health (dirty state, missing references, broken prefabs)

    Use this for quick project health checks before committing changes,
    after major refactoring, or to diagnose issues.
    """
    unity_instance = await get_unity_instance_from_context(ctx)

    # Coerce boolean parameters
    from services.tools.utils import coerce_bool, coerce_int
    incl_profiler = coerce_bool(include_profiler, default=True)
    incl_tests = coerce_bool(include_tests, default=True)
    incl_scene = coerce_bool(include_scene_health, default=True)
    incl_console = coerce_bool(include_console, default=True)
    error_limit = coerce_int(console_error_limit, default=5)

    diagnostics_tasks = []

    # Compile health check
    diagnostics_tasks.append(
        _get_compile_health(unity_instance)
    )

    # Console summary
    if incl_console:
        diagnostics_tasks.append(
            _get_console_summary(unity_instance, error_limit)
        )
    else:
        diagnostics_tasks.append(
            asyncio.sleep(0)
        )

    # Profiler summary
    if incl_profiler:
        diagnostics_tasks.append(
            _get_profiler_summary(unity_instance)
        )
    else:
        diagnostics_tasks.append(
            asyncio.sleep(0)
        )

    # Test summary
    if incl_tests:
        diagnostics_tasks.append(
            _get_test_summary(unity_instance)
        )
    else:
        diagnostics_tasks.append(
            asyncio.sleep(0)
        )

    # Scene health
    if incl_scene:
        diagnostics_tasks.append(
            _get_scene_health(unity_instance)
        )
    else:
        diagnostics_tasks.append(
            asyncio.sleep(0)
        )

    # Execute all diagnostics in parallel
    try:
        results = await asyncio.gather(
            *diagnostics_tasks,
            return_exceptions=True
        )

        compile_health = results[0] if not isinstance(results[0], Exception) else _default_compile_health()
        console_summary = results[1] if not isinstance(results[1], Exception) and incl_console else _default_console_summary()
        profiler_summary = results[2] if not isinstance(results[2], Exception) and incl_profiler else None
        test_summary = results[3] if not isinstance(results[3], Exception) and incl_tests else None
        scene_health = results[4] if not isinstance(results[4], Exception) and incl_scene else None

        # Get basic editor state
        editor_state = await _get_editor_state(unity_instance)

        # Analyze issues and generate recommendations
        issues = _analyze_issues(
            compile_health,
            console_summary,
            profiler_summary,
            test_summary,
            scene_health,
            severity_threshold
        )
        recommendations = _generate_recommendations(
            compile_health,
            console_summary,
            profiler_summary,
            test_summary,
            scene_health
        )

        # Determine overall status
        overall_status = _determine_overall_status(issues, severity_threshold)

        import time
        data = DiagnosticsData(
            timestamp=int(time.time() * 1000),
            unityVersion=editor_state.get("unityVersion"),
            isEditor=editor_state.get("isEditor"),
            isPlaying=editor_state.get("isPlaying"),
            compileHealth=compile_health if isinstance(compile_health, CompileHealth) else _default_compile_health(),
            consoleSummary=console_summary if isinstance(console_summary, ConsoleSummary) else _default_console_summary(),
            profilerSummary=profiler_summary if isinstance(profiler_summary, ProfilerSummary) else None,
            testSummary=test_summary if isinstance(test_summary, TestSummary) else None,
            sceneHealth=scene_health if isinstance(scene_health, SceneHealth) else None,
            overallStatus=overall_status,
            issues=issues,
            recommendations=recommendations
        )

        return DiagnosticsResponse(
            success=True,
            message=f"Diagnostics complete. Status: {overall_status}",
            data=data
        ).model_dump()

    except Exception as e:
        logger.error(f"Diagnostics failed: {e}")
        return MCPResponse(
            success=False,
            error=f"Failed to get diagnostics: {str(e)}"
        ).model_dump()


async def _get_compile_health(unity_instance: str | None) -> CompileHealth:
    """Get compilation health from Unity."""
    try:
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "validate_compile_health",
            {},
        )

        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            return CompileHealth(
                status=data.get("status", "unknown"),
                hasErrors=data.get("hasErrors", False),
                hasWarnings=data.get("hasWarnings", False),
                errorCount=data.get("errorCount", 0),
                warningCount=data.get("warningCount", 0),
                lastCompileTime=data.get("lastCompileTime")
            )
    except Exception as e:
        logger.warning(f"Failed to get compile health: {e}")

    return _default_compile_health()


def _default_compile_health() -> CompileHealth:
    """Return default compile health when unavailable."""
    return CompileHealth(
        status="unknown",
        hasErrors=False,
        hasWarnings=False,
        errorCount=0,
        warningCount=0
    )


async def _get_console_summary(unity_instance: str | None, error_limit: int) -> ConsoleSummary:
    """Get console summary from Unity."""
    try:
        # Get error count
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "read_console",
            {
                "action": "get",
                "types": ["error"],
                "count": error_limit,
                "format": "json"
            },
        )

        errors = []
        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            if isinstance(data, list):
                errors = data
            elif isinstance(data, dict):
                errors = data.get("items", [])

        # Get warning count
        warning_response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "read_console",
            {
                "action": "get",
                "types": ["warning"],
                "count": 1,
                "format": "plain"
            },
        )

        warning_count = 0
        if isinstance(warning_response, dict) and warning_response.get("success"):
            # Try to extract count from response
            warning_data = warning_response.get("data", {})
            if isinstance(warning_data, dict):
                warning_count = warning_data.get("total", 0)

        # Get log count
        log_response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "read_console",
            {
                "action": "get",
                "types": ["log"],
                "count": 1,
                "format": "plain"
            },
        )

        log_count = 0
        if isinstance(log_response, dict) and log_response.get("success"):
            log_data = log_response.get("data", {})
            if isinstance(log_data, dict):
                log_count = log_data.get("total", 0)

        recent_errors = [
            {"type": e.get("type"), "message": e.get("message")}
            for e in errors[:error_limit]
            if isinstance(e, dict)
        ]

        return ConsoleSummary(
            errorCount=len(errors),
            warningCount=warning_count,
            logCount=log_count,
            recentErrors=recent_errors if recent_errors else None
        )

    except Exception as e:
        logger.warning(f"Failed to get console summary: {e}")

    return _default_console_summary()


def _default_console_summary() -> ConsoleSummary:
    """Return default console summary when unavailable."""
    return ConsoleSummary(
        errorCount=0,
        warningCount=0,
        logCount=0
    )


async def _get_profiler_summary(unity_instance: str | None) -> ProfilerSummary | None:
    """Get profiler summary from Unity."""
    try:
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_profiler",
            {"action": "get_snapshot"},
        )

        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            snapshot = data.get("snapshot", {})
            aggregated = data.get("aggregatedStats", {})

            return ProfilerSummary(
                isRecording=data.get("isRecording", False),
                snapshotCount=data.get("totalSnapshots", 0),
                avgFrameTimeMs=aggregated.get("avgFrameTimeMs") or snapshot.get("frameTimeMs"),
                avgFps=aggregated.get("avgFps") or snapshot.get("fps"),
                avgMemoryMB=aggregated.get("avgMemoryMB")
            )
    except Exception as e:
        logger.warning(f"Failed to get profiler summary: {e}")

    return None


async def _get_test_summary(unity_instance: str | None) -> TestSummary | None:
    """Get test summary from Unity."""
    try:
        # Try to get info about tests resource
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "get_tests",
            {},
        )

        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            return TestSummary(
                lastRunStatus=data.get("lastRunStatus"),
                totalTests=data.get("totalTests"),
                passed=data.get("passed"),
                failed=data.get("failed"),
                skipped=data.get("skipped")
            )
    except Exception as e:
        logger.warning(f"Failed to get test summary: {e}")

    return None


async def _get_scene_health(unity_instance: str | None) -> SceneHealth | None:
    """Get scene health from Unity."""
    try:
        # Check scene integrity
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "audit_scene_integrity",
            {},
        )

        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            return SceneHealth(
                sceneName=data.get("sceneName"),
                isDirty=data.get("isDirty", False),
                missingReferences=data.get("missingReferences") or None,
                brokenPrefabs=data.get("brokenPrefabs") or None
            )
    except Exception as e:
        logger.warning(f"Failed to get scene health: {e}")

    return None


async def _get_editor_state(unity_instance: str | None) -> dict[str, Any]:
    """Get basic editor state from Unity."""
    try:
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_profiler",
            {"action": "get_status"},
        )

        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            return {
                "unityVersion": data.get("unityVersion"),
                "isEditor": data.get("isEditor"),
                "isPlaying": data.get("isPlaying")
            }
    except Exception:
        pass

    return {}


def _analyze_issues(
    compile_health: CompileHealth,
    console_summary: ConsoleSummary,
    profiler_summary: ProfilerSummary | None,
    test_summary: TestSummary | None,
    scene_health: SceneHealth | None,
    severity_threshold: str
) -> list[dict[str, Any]]:
    """Analyze all diagnostics and compile a list of issues."""
    issues = []
    severity_levels = {"info": 0, "warning": 1, "error": 2}
    threshold_level = severity_levels.get(severity_threshold, 0)

    # Compile errors
    if compile_health.hasErrors:
        issues.append({
            "severity": "error",
            "category": "compile",
            "message": f"Compile errors: {compile_health.errorCount}",
            "details": compile_health.lastCompileTime
        })
    elif compile_health.hasWarnings and threshold_level <= 1:
        issues.append({
            "severity": "warning",
            "category": "compile",
            "message": f"Compile warnings: {compile_health.warningCount}"
        })

    # Console errors
    if console_summary.errorCount > 0:
        issues.append({
            "severity": "error",
            "category": "console",
            "message": f"Console errors: {console_summary.errorCount}"
        })
    elif console_summary.warningCount > 0 and threshold_level <= 1:
        issues.append({
            "severity": "warning",
            "category": "console",
            "message": f"Console warnings: {console_summary.warningCount}"
        })

    # Performance issues
    if profiler_summary and profiler_summary.avgFrameTimeMs:
        if profiler_summary.avgFrameTimeMs > 33.3:
            issues.append({
                "severity": "error",
                "category": "performance",
                "message": f"Poor performance: {profiler_summary.avgFrameTimeMs:.1f}ms frame time"
            })
        elif profiler_summary.avgFrameTimeMs > 16.7 and threshold_level <= 1:
            issues.append({
                "severity": "warning",
                "category": "performance",
                "message": f"Suboptimal performance: {profiler_summary.avgFrameTimeMs:.1f}ms frame time"
            })

    # Test failures
    if test_summary and test_summary.failed and test_summary.failed > 0:
        issues.append({
            "severity": "error",
            "category": "tests",
            "message": f"Test failures: {test_summary.failed}/{test_summary.totalTests}"
        })

    # Scene issues
    if scene_health:
        if scene_health.missingReferences:
            issues.append({
                "severity": "error",
                "category": "scene",
                "message": f"Missing references: {len(scene_health.missingReferences)}"
            })
        if scene_health.brokenPrefabs:
            issues.append({
                "severity": "error",
                "category": "prefab",
                "message": f"Broken prefabs: {len(scene_health.brokenPrefabs)}"
            })
        if scene_health.isDirty and threshold_level <= 1:
            issues.append({
                "severity": "warning",
                "category": "scene",
                "message": "Scene has unsaved changes"
            })

    return issues


def _generate_recommendations(
    compile_health: CompileHealth,
    console_summary: ConsoleSummary,
    profiler_summary: ProfilerSummary | None,
    test_summary: TestSummary | None,
    scene_health: SceneHealth | None
) -> list[str]:
    """Generate recommendations based on diagnostics."""
    recommendations = []

    if compile_health.hasErrors:
        recommendations.append("Fix compile errors before continuing.")

    if console_summary.errorCount > 0:
        recommendations.append("Check console for runtime errors.")

    if profiler_summary:
        if profiler_summary.avgFrameTimeMs and profiler_summary.avgFrameTimeMs > 33.3:
            recommendations.append("Frame time is critical. Profile to identify bottlenecks.")
        elif profiler_summary.avgFrameTimeMs and profiler_summary.avgFrameTimeMs > 16.7:
            recommendations.append("Consider optimizing for 60 FPS target.")

    if test_summary and test_summary.failed and test_summary.failed > 0:
        recommendations.append("Run tests to investigate failures.")

    if scene_health:
        if scene_health.missingReferences:
            recommendations.append("Fix missing references in the scene.")
        if scene_health.brokenPrefabs:
            recommendations.append("Repair broken prefab connections.")
        if scene_health.isDirty:
            recommendations.append("Save scene to preserve changes.")

    if not recommendations:
        recommendations.append("Project health looks good!")

    return recommendations


def _determine_overall_status(
    issues: list[dict[str, Any]],
    severity_threshold: str
) -> str:
    """Determine overall status based on issues."""
    if not issues:
        return "healthy"

    has_errors = any(i["severity"] == "error" for i in issues)
    has_warnings = any(i["severity"] == "warning" for i in issues)

    if has_errors:
        return "critical"
    elif has_warnings:
        return "warnings"
    else:
        return "healthy"
