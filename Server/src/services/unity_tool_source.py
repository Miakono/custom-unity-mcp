"""Static Unity tool-source compatibility helpers.

These helpers scan the Unity package source tree for ``[McpForUnityTool]``
declarations so the Python server can avoid advertising Unity-targeted tools
that have no matching C# handler.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from typing import Any


_TOOL_ATTRIBUTE_PATTERN = re.compile(
    r"\[McpForUnityTool\s*\(\s*(?:(?:Name|CommandName)\s*=\s*)?\"(?P<name>[^\"]+)\"",
    re.DOTALL,
)


@dataclass(frozen=True)
class UnityToolCompatibility:
    tool_name: str
    unity_target: str | None
    publishable: bool
    status: str
    handler_files: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "unity_target": self.unity_target,
            "publishable": self.publishable,
            "status": self.status,
            "handler_files": list(self.handler_files),
        }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _unity_editor_root() -> Path:
    """Locate the MCPForUnity/Editor directory.

    Works in two contexts:
    - Dev/editable install: __file__ is inside the workspace (parents[3] = repo root).
    - uvx archive install: __file__ is in the uv cache. We recover the original
      source path from the package's ``direct_url.json`` metadata.
    """
    # Fast path: dev/editable install — parents[3] is the repo root.
    candidate = _repo_root() / "MCPForUnity" / "Editor"
    if candidate.exists():
        return candidate

    # Fallback: uvx installed from a file: URL — direct_url.json records the source.
    try:
        import importlib.metadata
        import json
        from pathlib import PurePosixPath
        from urllib.parse import urlparse

        dist = importlib.metadata.distribution("mcpforunityserver")
        raw = dist.read_text("direct_url.json")
        if raw:
            url = json.loads(raw).get("url", "")
            if url.startswith("file:"):
                parsed = urlparse(url)
                # urllib gives a POSIX path; on Windows it may start with /C:/…
                raw_path = parsed.path
                if raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
                    raw_path = raw_path[1:]  # strip leading / before drive letter
                server_root = Path(raw_path)
                sibling = server_root.parent / "MCPForUnity" / "Editor"
                if sibling.exists():
                    return sibling
    except Exception:
        pass

    # Best-effort: return the original guess even if it won't exist.
    return candidate


@lru_cache(maxsize=1)
def discover_unity_tool_handlers() -> dict[str, tuple[str, ...]]:
    """Return Unity tool names mapped to the C# files that declare them."""
    handlers: dict[str, list[str]] = {}
    root = _unity_editor_root()

    if not root.exists():
        return {}

    for path in root.rglob("*.cs"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        if "HandleCommand" not in text or "McpForUnityTool" not in text:
            continue

        # Use the effective repo root (parent of MCPForUnity/) so the path
        # stays readable in both dev and uvx-archive contexts.
        effective_root = root.parent.parent
        try:
            relative_path = path.relative_to(effective_root).as_posix()
        except ValueError:
            relative_path = path.as_posix()
        for match in _TOOL_ATTRIBUTE_PATTERN.finditer(text):
            tool_name = match.group("name")
            handlers.setdefault(tool_name, []).append(relative_path)

    return {
        name: tuple(sorted(set(paths)))
        for name, paths in handlers.items()
    }


def get_unity_tool_compatibility(tool_name: str, unity_target: str | None) -> UnityToolCompatibility:
    """Describe whether a Python tool can be safely advertised as Unity-backed."""
    handlers = discover_unity_tool_handlers()

    if unity_target is None:
        return UnityToolCompatibility(
            tool_name=tool_name,
            unity_target=None,
            publishable=True,
            status="server_only",
        )

    handler_files = handlers.get(unity_target, ())
    if unity_target != tool_name:
        return UnityToolCompatibility(
            tool_name=tool_name,
            unity_target=unity_target,
            publishable=bool(handler_files),
            status="alias" if handler_files else "missing_alias_target",
            handler_files=handler_files,
        )

    return UnityToolCompatibility(
        tool_name=tool_name,
        unity_target=unity_target,
        publishable=bool(handler_files),
        status="unity_handler" if handler_files else "missing_unity_handler",
        handler_files=handler_files,
    )


def is_publishable_registry_tool(tool_info: dict[str, Any]) -> bool:
    """Return whether a registry tool should be published to clients."""
    compatibility = get_unity_tool_compatibility(
        tool_name=tool_info["name"],
        unity_target=tool_info.get("unity_target"),
    )
    return compatibility.publishable


def summarize_registry_compatibility(tools: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize compatibility across a registry snapshot."""
    supported = 0
    unsupported: list[str] = []
    server_only = 0
    alias_count = 0

    for tool in tools:
        compatibility = get_unity_tool_compatibility(tool["name"], tool.get("unity_target"))
        if compatibility.status == "server_only":
            server_only += 1
        elif compatibility.status == "alias":
            alias_count += 1

        if compatibility.publishable:
            supported += 1
        else:
            unsupported.append(tool["name"])

    return {
        "publishable_tool_count": supported,
        "server_only_tool_count": server_only,
        "alias_tool_count": alias_count,
        "unsupported_tools": sorted(unsupported),
    }