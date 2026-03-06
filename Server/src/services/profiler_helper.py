"""
Profiler helper service for parsing profiler data, aggregating statistics,
and handling capture file operations.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ProfilerSnapshot:
    """Represents a single profiler snapshot."""
    timestamp: int
    frame_index: int
    frame_time_ms: float
    fps: float
    cpu: dict[str, Any] = field(default_factory=dict)
    gpu: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    rendering: dict[str, Any] = field(default_factory=dict)
    audio: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfilerSnapshot:
        """Create a snapshot from a dictionary."""
        return cls(
            timestamp=data.get("timestamp", 0),
            frame_index=data.get("frameIndex", 0),
            frame_time_ms=data.get("frameTimeMs", 0.0),
            fps=data.get("fps", 0.0),
            cpu=data.get("cpu", {}),
            gpu=data.get("gpu", {}),
            memory=data.get("memory", {}),
            rendering=data.get("rendering", {}),
            audio=data.get("audio", {}),
        )


@dataclass
class AggregatedStats:
    """Aggregated statistics from multiple snapshots."""
    sample_count: int = 0
    avg_frame_time_ms: float = 0.0
    min_frame_time_ms: float = 0.0
    max_frame_time_ms: float = 0.0
    avg_fps: float = 0.0
    min_fps: float = 0.0
    max_fps: float = 0.0
    avg_memory_bytes: int = 0
    max_memory_bytes: int = 0
    avg_draw_calls: float = 0.0
    max_draw_calls: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sampleCount": self.sample_count,
            "avgFrameTimeMs": round(self.avg_frame_time_ms, 2),
            "minFrameTimeMs": round(self.min_frame_time_ms, 2),
            "maxFrameTimeMs": round(self.max_frame_time_ms, 2),
            "avgFps": round(self.avg_fps, 1),
            "minFps": round(self.min_fps, 1),
            "maxFps": round(self.max_fps, 1),
            "avgMemoryBytes": self.avg_memory_bytes,
            "maxMemoryBytes": self.max_memory_bytes,
            "avgMemoryMB": round(self.avg_memory_bytes / (1024 * 1024), 2),
            "maxMemoryMB": round(self.max_memory_bytes / (1024 * 1024), 2),
            "avgDrawCalls": round(self.avg_draw_calls, 1),
            "maxDrawCalls": self.max_draw_calls,
        }


@dataclass
class ProfilerCaptureData:
    """Complete profiler capture data."""
    captured_at: int
    unity_version: str
    platform: str
    snapshots: list[ProfilerSnapshot]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfilerCaptureData:
        """Create capture data from a dictionary."""
        snapshots = [
            ProfilerSnapshot.from_dict(s) for s in data.get("snapshots", [])
        ]
        return cls(
            captured_at=data.get("capturedAt", 0),
            unity_version=data.get("unityVersion", "unknown"),
            platform=data.get("platform", "unknown"),
            snapshots=snapshots,
        )


class ProfilerDataAggregator:
    """Aggregates profiler data from multiple snapshots."""

    @staticmethod
    def aggregate(snapshots: list[ProfilerSnapshot]) -> AggregatedStats:
        """Calculate aggregated statistics from a list of snapshots."""
        if not snapshots:
            return AggregatedStats()

        frame_times = [s.frame_time_ms for s in snapshots]
        fps_values = [s.fps for s in snapshots]
        memory_values = [
            s.memory.get("totalUsedMemoryBytes", 0) for s in snapshots
        ]
        draw_calls = [
            s.rendering.get("drawCalls", 0) for s in snapshots
        ]

        return AggregatedStats(
            sample_count=len(snapshots),
            avg_frame_time_ms=sum(frame_times) / len(frame_times),
            min_frame_time_ms=min(frame_times),
            max_frame_time_ms=max(frame_times),
            avg_fps=sum(fps_values) / len(fps_values),
            min_fps=min(fps_values),
            max_fps=max(fps_values),
            avg_memory_bytes=int(sum(memory_values) / len(memory_values)),
            max_memory_bytes=max(memory_values),
            avg_draw_calls=sum(draw_calls) / len(draw_calls) if draw_calls else 0,
            max_draw_calls=max(draw_calls) if draw_calls else 0,
        )

    @staticmethod
    def analyze_trends(
        snapshots: list[ProfilerSnapshot],
        window_size: int = 10
    ) -> dict[str, Any]:
        """Analyze performance trends in the snapshot data."""
        if len(snapshots) < window_size * 2:
            return {"error": "Not enough data for trend analysis"}

        # Split data into two windows
        first_window = snapshots[:window_size]
        second_window = snapshots[-window_size:]

        first_stats = ProfilerDataAggregator.aggregate(first_window)
        second_stats = ProfilerDataAggregator.aggregate(second_window)

        # Calculate changes
        fps_change = second_stats.avg_fps - first_stats.avg_fps
        memory_change = second_stats.avg_memory_bytes - first_stats.avg_memory_bytes
        frame_time_change = (
            second_stats.avg_frame_time_ms - first_stats.avg_frame_time_ms
        )

        return {
            "fpsChange": round(fps_change, 1),
            "fpsChangePercent": round(
                (fps_change / first_stats.avg_fps * 100) if first_stats.avg_fps else 0, 1
            ),
            "memoryChangeBytes": memory_change,
            "memoryChangeMB": round(memory_change / (1024 * 1024), 2),
            "frameTimeChangeMs": round(frame_time_change, 2),
            "trend": "improving" if fps_change > 0 else "degrading" if fps_change < 0 else "stable",
        }


class ProfilerCaptureManager:
    """Manages profiler capture file operations."""

    def __init__(self, capture_dir: str | None = None):
        """Initialize the capture manager.

        Args:
            capture_dir: Directory for storing captures. If None, uses default location.
        """
        if capture_dir:
            self.capture_dir = Path(capture_dir)
        else:
            # Default to project's ProfilerCaptures directory
            self.capture_dir = Path.home() / "UnityProfilerCaptures"

        # Ensure directory exists
        self.capture_dir.mkdir(parents=True, exist_ok=True)

    def save_capture(
        self,
        data: dict[str, Any],
        filename: str | None = None
    ) -> str:
        """Save a profiler capture to file.

        Args:
            data: The capture data to save.
            filename: Optional filename. If None, generates a timestamped name.

        Returns:
            Path to the saved file.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"profiler_capture_{timestamp}.json"

        filepath = self.capture_dir / filename

        # Add metadata
        capture_data = {
            "savedAt": int(datetime.now().timestamp() * 1000),
            "savedBy": "profiler_helper",
            **data
        }

        with open(filepath, "w") as f:
            json.dump(capture_data, f, indent=2)

        return str(filepath)

    def load_capture(self, filename: str) -> dict[str, Any]:
        """Load a profiler capture from file.

        Args:
            filename: Name of the capture file.

        Returns:
            The loaded capture data.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file contains invalid JSON.
        """
        filepath = self.capture_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Capture file not found: {filename}")

        with open(filepath, "r") as f:
            return json.load(f)

    def list_captures(self) -> list[dict[str, Any]]:
        """List all available capture files.

        Returns:
            List of capture file metadata.
        """
        captures = []

        for filepath in self.capture_dir.glob("*.json"):
            try:
                stat = filepath.stat()
                captures.append({
                    "filename": filepath.name,
                    "size": stat.st_size,
                    "modified": int(stat.st_mtime * 1000),
                    "path": str(filepath),
                })
            except OSError:
                continue

        # Sort by modification time, newest first
        captures.sort(key=lambda x: x["modified"], reverse=True)
        return captures

    def delete_capture(self, filename: str) -> bool:
        """Delete a capture file.

        Args:
            filename: Name of the capture file to delete.

        Returns:
            True if deleted successfully, False otherwise.
        """
        filepath = self.capture_dir / filename

        try:
            if filepath.exists():
                filepath.unlink()
                return True
        except OSError:
            pass

        return False


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(bytes_value) < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"


def format_duration(ms: float) -> str:
    """Format milliseconds to human-readable duration."""
    if ms < 1:
        return f"{ms * 1000:.2f} μs"
    elif ms < 1000:
        return f"{ms:.2f} ms"
    else:
        return f"{ms / 1000:.2f} s"


def generate_performance_report(
    capture_data: dict[str, Any],
    include_recommendations: bool = True
) -> dict[str, Any]:
    """Generate a comprehensive performance report from capture data.

    Args:
        capture_data: The profiler capture data.
        include_recommendations: Whether to include optimization recommendations.

    Returns:
        A structured performance report.
    """
    snapshots = [
        ProfilerSnapshot.from_dict(s)
        for s in capture_data.get("snapshots", [])
    ]

    if not snapshots:
        return {"error": "No snapshots in capture data"}

    # Aggregate stats
    stats = ProfilerDataAggregator.aggregate(snapshots)

    # Get latest snapshot for current state
    latest = snapshots[-1]

    report = {
        "summary": {
            "totalSnapshots": len(snapshots),
            "durationSeconds": (
                (snapshots[-1].timestamp - snapshots[0].timestamp) / 1000
                if len(snapshots) > 1 else 0
            ),
            "unityVersion": capture_data.get("unityVersion", "unknown"),
            "platform": capture_data.get("platform", "unknown"),
        },
        "performance": {
            "frameTime": {
                "average": round(stats.avg_frame_time_ms, 2),
                "min": round(stats.min_frame_time_ms, 2),
                "max": round(stats.max_frame_time_ms, 2),
                "target16ms": stats.avg_frame_time_ms <= 16.7,
                "target33ms": stats.avg_frame_time_ms <= 33.3,
            },
            "fps": {
                "average": round(stats.avg_fps, 1),
                "min": round(stats.min_fps, 1),
                "max": round(stats.max_fps, 1),
            },
            "memory": {
                "average": format_bytes(stats.avg_memory_bytes),
                "peak": format_bytes(stats.max_memory_bytes),
                "averageBytes": stats.avg_memory_bytes,
                "peakBytes": stats.max_memory_bytes,
            },
        },
        "current": {
            "frameTimeMs": round(latest.frame_time_ms, 2),
            "fps": round(latest.fps, 1),
            "memoryMB": round(
                latest.memory.get("totalUsedMemoryBytes", 0) / (1024 * 1024), 2
            ),
            "drawCalls": latest.rendering.get("drawCalls", 0),
        },
    }

    # Add trends if enough data
    if len(snapshots) >= 20:
        report["trends"] = ProfilerDataAggregator.analyze_trends(snapshots)

    # Add recommendations
    if include_recommendations:
        report["recommendations"] = _generate_recommendations(stats, latest)

    return report


def _generate_recommendations(
    stats: AggregatedStats,
    latest: ProfilerSnapshot
) -> list[dict[str, str]]:
    """Generate optimization recommendations based on performance data."""
    recommendations = []

    # Frame time recommendations
    if stats.avg_frame_time_ms > 33.3:
        recommendations.append({
            "severity": "critical",
            "category": "performance",
            "message": (
                f"Average frame time ({stats.avg_frame_time_ms:.1f}ms) exceeds "
                "33ms (30 FPS). Major optimization required."
            ),
        })
    elif stats.avg_frame_time_ms > 16.7:
        recommendations.append({
            "severity": "warning",
            "category": "performance",
            "message": (
                f"Average frame time ({stats.avg_frame_time_ms:.1f}ms) exceeds "
                "16ms (60 FPS). Room for optimization."
            ),
        })

    # Memory recommendations
    memory_mb = stats.avg_memory_bytes / (1024 * 1024)
    if memory_mb > 1000:
        recommendations.append({
            "severity": "warning",
            "category": "memory",
            "message": (
                f"High memory usage ({memory_mb:.0f}MB). "
                "Consider using Memory Profiler for detailed analysis."
            ),
        })

    # Draw call recommendations
    avg_draw_calls = stats.avg_draw_calls
    if avg_draw_calls > 200:
        recommendations.append({
            "severity": "warning",
            "category": "rendering",
            "message": (
                f"High draw call count ({avg_draw_calls:.0f}). "
                "Consider batching, GPU instancing, or SRP Batcher."
            ),
        })

    # FPS variance recommendations
    fps_variance = stats.max_fps - stats.min_fps
    if fps_variance > 30:
        recommendations.append({
            "severity": "info",
            "category": "stability",
            "message": (
                f"High FPS variance ({fps_variance:.0f} FPS). "
                "Consider investigating frame time spikes."
            ),
        })

    return recommendations
