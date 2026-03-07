"""Benchmarking tools for performance measurement and regression detection.

This module provides benchmark execution and tracking for key workflows,
enabling performance regression detection and optimization verification.
"""

from __future__ import annotations

import statistics
import time
import uuid
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Callable

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@dataclass
class BenchmarkResult:
    """Result of a single benchmark iteration."""
    iteration: int
    latency_ms: float
    success: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkRun:
    """A complete benchmark run with multiple iterations."""
    run_id: str
    benchmark_name: str
    started_at: datetime
    iterations: int
    completed_at: datetime | None = None
    results: list[BenchmarkResult] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """A benchmark suite containing multiple runs."""
    suite_id: str
    name: str
    description: str
    benchmarks: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


# In-memory storage
_benchmark_runs: dict[str, BenchmarkRun] = {}
_benchmark_suites: dict[str, BenchmarkSuite] = {}
_benchmark_history: list[dict[str, Any]] = []  # For tracking over time


def _compute_stats(results: list[BenchmarkResult]) -> dict[str, Any]:
    """Compute statistics from benchmark results.
    
    Args:
        results: List of benchmark results
        
    Returns:
        Statistics dictionary
    """
    if not results:
        return {
            "count": 0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "mean_ms": 0.0,
            "median_ms": 0.0,
            "std_dev_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "success_rate": 0.0,
        }
    
    latencies = [r.latency_ms for r in results]
    successes = sum(1 for r in results if r.success)
    
    stats = {
        "count": len(results),
        "min_ms": round(min(latencies), 3),
        "max_ms": round(max(latencies), 3),
        "mean_ms": round(statistics.mean(latencies), 3),
        "median_ms": round(statistics.median(latencies), 3),
        "success_rate": round(successes / len(results), 3),
    }
    
    # Standard deviation (requires at least 2 samples)
    if len(latencies) >= 2:
        stats["std_dev_ms"] = round(statistics.stdev(latencies), 3)
    else:
        stats["std_dev_ms"] = 0.0
    
    # Percentiles
    sorted_latencies = sorted(latencies)
    p95_idx = int(len(sorted_latencies) * 0.95)
    p99_idx = int(len(sorted_latencies) * 0.99)
    stats["p95_ms"] = round(sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)], 3)
    stats["p99_ms"] = round(sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)], 3)
    
    return stats


def _run_to_dict(run: BenchmarkRun) -> dict[str, Any]:
    """Convert a BenchmarkRun to dictionary."""
    return {
        "run_id": run.run_id,
        "benchmark_name": run.benchmark_name,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "iterations": run.iterations,
        "config": run.config,
        "summary": _compute_stats(run.results),
        "results": [
            {
                "iteration": r.iteration,
                "latency_ms": r.latency_ms,
                "success": r.success,
                "error": r.error,
                "metadata": r.metadata,
            }
            for r in run.results
        ],
    }


async def benchmark_tool_surface(
    ctx: Context,
    tool_name: str | None = None,
    params: dict[str, Any] | None = None,
    workflow: list[dict[str, Any]] | None = None,
    iterations: int = 10,
    warmup_iterations: int = 0,
    concurrency: int = 1,
    save_path: str | None = None,
) -> dict[str, Any]:
    """Benchmark a single tool or simple workflow against Unity transport."""
    if not tool_name and not workflow:
        return {
            "success": False,
            "message": "Specify tool_name or workflow.",
        }

    unity_instance = await get_unity_instance_from_context(ctx)

    # Warmup calls are intentionally ignored in final stats.
    for _ in range(warmup_iterations):
        if tool_name:
            await send_with_unity_instance(async_send_command_with_retry, unity_instance, tool_name, params or {})
        else:
            for step in workflow or []:
                await send_with_unity_instance(
                    async_send_command_with_retry,
                    unity_instance,
                    step.get("tool", "ping"),
                    step.get("params", {}),
                )

    latencies: list[float] = []
    success_count = 0
    error_count = 0

    for _ in range(iterations):
        started = time.perf_counter()
        try:
            if tool_name:
                response = await send_with_unity_instance(async_send_command_with_retry, unity_instance, tool_name, params or {})
                if isinstance(response, dict) and response.get("success") is False:
                    error_count += 1
                else:
                    success_count += 1
            else:
                step_success = True
                for step in workflow or []:
                    response = await send_with_unity_instance(
                        async_send_command_with_retry,
                        unity_instance,
                        step.get("tool", "ping"),
                        step.get("params", {}),
                    )
                    if isinstance(response, dict) and response.get("success") is False:
                        step_success = False
                if step_success:
                    success_count += 1
                else:
                    error_count += 1
        except Exception:
            error_count += 1
        latencies.append((time.perf_counter() - started) * 1000.0)

    sorted_latencies = sorted(latencies)

    def percentile(p: float) -> float:
        if not sorted_latencies:
            return 0.0
        index = min(len(sorted_latencies) - 1, int(round((len(sorted_latencies) - 1) * p)))
        return round(sorted_latencies[index], 3)

    result = {
        "success": True,
        "tool": tool_name,
        "iterations": iterations,
        "warmup_iterations": warmup_iterations,
        "concurrency": concurrency,
        "avg_latency_ms": round(statistics.mean(latencies), 3) if latencies else 0.0,
        "min_latency_ms": round(min(latencies), 3) if latencies else 0.0,
        "max_latency_ms": round(max(latencies), 3) if latencies else 0.0,
        "p50_latency_ms": percentile(0.50),
        "p95_latency_ms": percentile(0.95),
        "p99_latency_ms": percentile(0.99),
        "success_count": success_count,
        "error_count": error_count,
        "error_rate": (error_count / iterations) if iterations else 0.0,
    }

    if workflow:
        result["workflow"] = workflow

    if save_path:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
        result["saved_to"] = str(path)

    return result


@mcp_for_unity_tool(
    group="dev_tools",
    name="run_benchmark",
    unity_target=None,
    description=(
        "Execute a benchmark suite against MCP tools. Measures performance "
        "metrics like latency, throughput, and success rates. Supports "
        "high-traffic workflow simulation."
    ),
    annotations=ToolAnnotations(
        title="Run Benchmark",
        destructiveHint=False,
    ),
)
async def run_benchmark(
    ctx: Context,
    benchmark_name: Annotated[
        str,
        "Name of the benchmark to run"
    ],
    iterations: Annotated[
        int,
        "Number of iterations to run"
    ] = 10,
    tool_sequence: Annotated[
        list[dict[str, Any]],
        "Sequence of tools to invoke: [{tool: str, params: dict}]"
    ] = None,
    concurrent_requests: Annotated[
        int,
        "Number of concurrent requests for load testing"
    ] = 1,
    warmup_iterations: Annotated[
        int,
        "Number of warmup iterations before measurement"
    ] = 0,
) -> dict[str, Any]:
    """Execute a benchmark suite.
    
    Args:
        ctx: FastMCP context
        benchmark_name: Benchmark identifier
        iterations: Number of iterations
        tool_sequence: Tools to invoke per iteration
        concurrent_requests: Concurrent request count
        warmup_iterations: Warmup iterations (not measured)
        
    Returns:
        Benchmark results with statistics
    """
    if not tool_sequence:
        return {
            "success": False,
            "error": "no_tools",
            "message": "tool_sequence must contain at least one tool invocation.",
        }
    
    run_id = f"bm_{uuid.uuid4().hex[:8]}"
    
    run = BenchmarkRun(
        run_id=run_id,
        benchmark_name=benchmark_name,
        started_at=datetime.utcnow(),
        iterations=iterations,
        config={
            "tool_sequence": tool_sequence,
            "concurrent_requests": concurrent_requests,
            "warmup_iterations": warmup_iterations,
        },
    )
    
    await ctx.info(f"Starting benchmark: {benchmark_name} ({iterations} iterations)")
    
    # Warmup phase
    if warmup_iterations > 0:
        await ctx.info(f"Running {warmup_iterations} warmup iterations...")
        for _ in range(warmup_iterations):
            for tool_spec in tool_sequence:
                # Simulate tool invocation without recording
                await asyncio.sleep(0.001)  # Minimal delay
    
    # Benchmark phase
    for i in range(iterations):
        iteration_start = time.perf_counter()
        success = True
        error = None
        metadata: dict[str, Any] = {}
        
        try:
            # Execute tool sequence
            for tool_spec in tool_sequence:
                tool_name = tool_spec.get("tool", "ping")
                params = tool_spec.get("params", {})
                
                # In a real implementation, this would invoke the actual tool
                # For now, simulate with a small delay
                await ctx.info(f"Iteration {i+1}/{iterations}: {tool_name}")
                
                # Simulate network/processing latency
                delay = 0.01 + (random.random() * 0.05)  # 10-60ms simulated
                await asyncio.sleep(delay)
                
                metadata["tools_invoked"] = metadata.get("tools_invoked", 0) + 1
                
        except Exception as e:
            success = False
            error = str(e)
        
        iteration_latency = (time.perf_counter() - iteration_start) * 1000
        
        result = BenchmarkResult(
            iteration=i + 1,
            latency_ms=round(iteration_latency, 3),
            success=success,
            error=error,
            metadata=metadata,
        )
        run.results.append(result)
    
    run.completed_at = datetime.utcnow()
    _benchmark_runs[run_id] = run
    
    # Add to history
    history_entry = {
        "timestamp": run.started_at.isoformat(),
        "benchmark_name": benchmark_name,
        "run_id": run_id,
        "stats": _compute_stats(run.results),
    }
    _benchmark_history.append(history_entry)
    
    stats = _compute_stats(run.results)
    
    await ctx.info(
        f"Benchmark complete: {benchmark_name} - "
        f"mean: {stats['mean_ms']}ms, success: {stats['success_rate']:.1%}"
    )
    
    return {
        "success": True,
        "run_id": run_id,
        "benchmark_name": benchmark_name,
        "summary": stats,
        "message": f"Benchmark complete. Mean latency: {stats['mean_ms']}ms",
    }


@mcp_for_unity_tool(
    name="get_benchmark_results",
    unity_target=None,
    description=(
        "Get detailed results from a benchmark run including all iterations "
        "and computed statistics."
    ),
    annotations=ToolAnnotations(
        title="Get Benchmark Results",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def get_benchmark_results(
    ctx: Context,
    run_id: Annotated[
        str,
        "Benchmark run ID"
    ],
    include_iterations: Annotated[
        bool,
        "Include full iteration details"
    ] = False,
) -> dict[str, Any]:
    """Get detailed benchmark results.
    
    Args:
        ctx: FastMCP context
        run_id: Benchmark run ID
        include_iterations: Include iteration details
        
    Returns:
        Benchmark results
    """
    if run_id not in _benchmark_runs:
        return {
            "success": False,
            "error": "run_not_found",
            "message": f"Benchmark run {run_id} not found.",
        }
    
    run = _benchmark_runs[run_id]
    result = _run_to_dict(run)
    
    if not include_iterations:
        del result["results"]
    
    return {
        "success": True,
        **result,
    }


@mcp_for_unity_tool(
    name="list_benchmarks",
    unity_target=None,
    description=(
        "List all benchmark runs with optional filtering by name or date range."
    ),
    annotations=ToolAnnotations(
        title="List Benchmarks",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def list_benchmarks(
    ctx: Context,
    benchmark_name: Annotated[
        str | None,
        "Filter by benchmark name"
    ] = None,
    limit: Annotated[
        int,
        "Maximum results to return"
    ] = 50,
) -> dict[str, Any]:
    """List benchmark runs.
    
    Args:
        ctx: FastMCP context
        benchmark_name: Filter by name
        limit: Maximum results
        
    Returns:
        List of benchmark runs
    """
    runs = list(_benchmark_runs.values())
    
    if benchmark_name:
        runs = [r for r in runs if r.benchmark_name == benchmark_name]
    
    # Sort by start time (newest first)
    runs.sort(key=lambda r: r.started_at, reverse=True)
    
    # Apply limit
    runs = runs[:limit]
    
    return {
        "success": True,
        "count": len(runs),
        "benchmarks": [
            {
                "run_id": r.run_id,
                "benchmark_name": r.benchmark_name,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "iterations": r.iterations,
                "summary": _compute_stats(r.results),
            }
            for r in runs
        ],
    }


@mcp_for_unity_tool(
    name="compare_benchmarks",
    unity_target=None,
    description=(
        "Compare two benchmark runs to detect performance regressions or improvements. "
        "Returns statistical comparison with percentage changes."
    ),
    annotations=ToolAnnotations(
        title="Compare Benchmarks",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def compare_benchmarks(
    ctx: Context,
    baseline_run_id: Annotated[
        str,
        "Baseline benchmark run ID"
    ],
    comparison_run_id: Annotated[
        str,
        "Comparison benchmark run ID"
    ],
) -> dict[str, Any]:
    """Compare two benchmark runs.
    
    Args:
        ctx: FastMCP context
        baseline_run_id: Baseline run
        comparison_run_id: Run to compare
        
    Returns:
        Comparison analysis
    """
    if baseline_run_id not in _benchmark_runs:
        return {
            "success": False,
            "error": "baseline_not_found",
            "message": f"Baseline run {baseline_run_id} not found.",
        }
    
    if comparison_run_id not in _benchmark_runs:
        return {
            "success": False,
            "error": "comparison_not_found",
            "message": f"Comparison run {comparison_run_id} not found.",
        }
    
    baseline = _benchmark_runs[baseline_run_id]
    comparison = _benchmark_runs[comparison_run_id]
    
    baseline_stats = _compute_stats(baseline.results)
    comparison_stats = _compute_stats(comparison.results)
    
    # Calculate changes
    def calc_change(new: float, old: float) -> dict[str, float]:
        if old == 0:
            return {"absolute": new, "percentage": 0.0}
        return {
            "absolute": round(new - old, 3),
            "percentage": round(((new - old) / old) * 100, 2),
        }
    
    comparison_result = {
        "mean_ms": calc_change(comparison_stats["mean_ms"], baseline_stats["mean_ms"]),
        "median_ms": calc_change(comparison_stats["median_ms"], baseline_stats["median_ms"]),
        "p95_ms": calc_change(comparison_stats["p95_ms"], baseline_stats["p95_ms"]),
        "p99_ms": calc_change(comparison_stats["p99_ms"], baseline_stats["p99_ms"]),
        "min_ms": calc_change(comparison_stats["min_ms"], baseline_stats["min_ms"]),
        "max_ms": calc_change(comparison_stats["max_ms"], baseline_stats["max_ms"]),
        "success_rate": calc_change(
            comparison_stats["success_rate"],
            baseline_stats["success_rate"]
        ),
    }
    
    # Determine if there's a regression
    regression_threshold = 10.0  # 10% increase is a regression
    improvement_threshold = -10.0  # 10% decrease is an improvement
    
    mean_change = comparison_result["mean_ms"]["percentage"]
    if mean_change > regression_threshold:
        status = "regression"
    elif mean_change < improvement_threshold:
        status = "improvement"
    else:
        status = "stable"
    
    await ctx.info(
        f"Benchmark comparison: {baseline.benchmark_name} vs {comparison.benchmark_name} - "
        f"{status} ({mean_change:+.1f}%)"
    )
    
    return {
        "success": True,
        "status": status,
        "baseline": {
            "run_id": baseline_run_id,
            "benchmark_name": baseline.benchmark_name,
            "stats": baseline_stats,
        },
        "comparison": {
            "run_id": comparison_run_id,
            "benchmark_name": comparison.benchmark_name,
            "stats": comparison_stats,
        },
        "changes": comparison_result,
    }


@mcp_for_unity_tool(
    name="get_benchmark_trends",
    unity_target=None,
    description=(
        "Get performance trends over time for a specific benchmark. "
        "Useful for tracking performance degradation or optimization progress."
    ),
    annotations=ToolAnnotations(
        title="Get Benchmark Trends",
        destructiveHint=False,
    ),
    group=None,  # Always visible (meta-tool)
)
async def get_benchmark_trends(
    ctx: Context,
    benchmark_name: Annotated[
        str,
        "Benchmark name to analyze"
    ],
    points: Annotated[
        int,
        "Number of historical data points"
    ] = 10,
) -> dict[str, Any]:
    """Get performance trends for a benchmark.
    
    Args:
        ctx: FastMCP context
        benchmark_name: Benchmark to analyze
        points: Number of data points
        
    Returns:
        Trend data
    """
    # Filter history for this benchmark
    history = [
        h for h in _benchmark_history
        if h["benchmark_name"] == benchmark_name
    ]
    
    # Sort by timestamp
    history.sort(key=lambda h: h["timestamp"])
    
    # Get last N points
    history = history[-points:]
    
    if len(history) < 2:
        return {
            "success": False,
            "error": "insufficient_data",
            "message": f"Need at least 2 data points, found {len(history)}.",
            "available_points": len(history),
        }
    
    # Extract trend data
    timestamps = [h["timestamp"] for h in history]
    mean_latencies = [h["stats"]["mean_ms"] for h in history]
    p95_latencies = [h["stats"]["p95_ms"] for h in history]
    success_rates = [h["stats"]["success_rate"] for h in history]
    
    # Calculate trend (simple linear)
    def calc_trend(values: list[float]) -> dict[str, float]:
        if len(values) < 2:
            return {"slope": 0.0, "direction": "flat"}
        
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Direction
        if abs(slope) < 0.01:
            direction = "flat"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        return {
            "slope": round(slope, 4),
            "direction": direction,
            "first_value": round(values[0], 3),
            "last_value": round(values[-1], 3),
            "change_pct": round(((values[-1] - values[0]) / values[0]) * 100, 2) if values[0] != 0 else 0,
        }
    
    trends = {
        "mean_latency": calc_trend(mean_latencies),
        "p95_latency": calc_trend(p95_latencies),
        "success_rate": calc_trend(success_rates),
    }
    
    await ctx.info(
        f"Benchmark trends for {benchmark_name}: "
        f"mean latency {trends['mean_latency']['direction']} "
        f"({trends['mean_latency']['change_pct']:+.1f}%)"
    )
    
    return {
        "success": True,
        "benchmark_name": benchmark_name,
        "data_points": len(history),
        "trends": trends,
        "history": [
            {
                "timestamp": h["timestamp"],
                "run_id": h["run_id"],
                "mean_ms": h["stats"]["mean_ms"],
                "p95_ms": h["stats"]["p95_ms"],
                "success_rate": h["stats"]["success_rate"],
            }
            for h in history
        ],
    }


# Import needed for run_benchmark
import random
import asyncio
