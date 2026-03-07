"""Server-local checkpoint and restore primitives for high-risk workflows."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools.utils import coerce_bool, parse_json_payload


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_checkpoint_dir() -> Path:
    return _repo_root() / "Generated" / "Checkpoints"


def _index_file(base_dir: Path) -> Path:
    return base_dir / "checkpoints.json"


def _to_posix_relative(path: Path, *, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _resolve_user_path(raw_path: str, *, root: Path) -> Path:
    normalized = (raw_path or "").strip().replace("\\", "/")
    if not normalized:
        raise ValueError("paths entries must be non-empty")

    candidate = (root / normalized).resolve()
    if root == candidate or root in candidate.parents:
        return candidate

    raise ValueError(f"Path escapes repository root: {raw_path}")


def _sha256_for_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_index(base_dir: Path) -> list[dict[str, Any]]:
    file_path = _index_file(base_dir)
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        checkpoints = payload.get("checkpoints")
        if isinstance(checkpoints, list):
            return checkpoints
    return []


def _save_index(base_dir: Path, checkpoints: list[dict[str, Any]]) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    file_path = _index_file(base_dir)
    payload = {"version": 1, "checkpoints": checkpoints}
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _parse_paths(paths: list[str] | str | None) -> list[str]:
    if paths is None:
        return []
    if isinstance(paths, list):
        return [str(item) for item in paths if str(item).strip()]

    parsed = parse_json_payload(paths)
    if isinstance(parsed, list):
        result: list[str] = []
        for item in parsed:
            if isinstance(item, str) and item.strip():
                result.append(item)
        return result

    raise ValueError("paths must be a list or JSON list string")


def _collect_files(paths: list[str], *, root: Path) -> list[Path]:
    collected: list[Path] = []
    for raw in paths:
        resolved = _resolve_user_path(raw, root=root)
        if not resolved.exists():
            raise FileNotFoundError(f"Path not found: {raw}")

        if resolved.is_file():
            collected.append(resolved)
            continue

        for entry in sorted(resolved.rglob("*")):
            if entry.is_file():
                collected.append(entry)

    seen: set[Path] = set()
    unique: list[Path] = []
    for item in collected:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _get_checkpoint_entry(checkpoints: list[dict[str, Any]], checkpoint_id: str) -> dict[str, Any] | None:
    for entry in checkpoints:
        if entry.get("id") == checkpoint_id:
            return entry
    return None


def _checkpoint_dir(base_dir: Path, checkpoint_id: str) -> Path:
    return base_dir / checkpoint_id


@mcp_for_unity_tool(
    unity_target=None,
    group="core",
    description=(
        "Create, inspect, verify, restore, and delete local file checkpoints for high-risk workflows. "
        "This tool is server-local and does not require Unity. "
        "Use create before large edits, verify for drift detection, and restore to roll back files."
    ),
    annotations=ToolAnnotations(
        title="Manage Checkpoints",
        destructiveHint=True,
    ),
)
async def manage_checkpoints(
    ctx: Context,
    action: Annotated[
        Literal["create", "list", "inspect", "verify", "restore", "delete"],
        "Checkpoint action: create/list/inspect/verify/restore/delete",
    ],
    checkpoint_id: Annotated[
        str | None,
        "Checkpoint identifier for inspect/verify/restore/delete",
    ] = None,
    name: Annotated[
        str | None,
        "Optional label for create action",
    ] = None,
    note: Annotated[
        str | None,
        "Optional note for create action",
    ] = None,
    paths: Annotated[
        list[str] | str | None,
        "Paths for create/restore/verify (list or JSON list string), relative to repo root",
    ] = None,
    dry_run: Annotated[
        bool | str | None,
        "When true, preview restore/delete actions without changing files",
    ] = False,
) -> dict[str, Any]:
    await ctx.info(f"manage_checkpoints action={action}")

    root = _repo_root()
    base_dir = _default_checkpoint_dir()
    dry_run = coerce_bool(dry_run, default=False)

    try:
        if action == "list":
            checkpoints = _load_index(base_dir)
            return {
                "success": True,
                "data": {
                    "count": len(checkpoints),
                    "checkpoints": checkpoints,
                },
            }

        checkpoints = _load_index(base_dir)

        if action == "create":
            selected_paths = _parse_paths(paths)
            if not selected_paths:
                return {
                    "success": False,
                    "error": "paths_required",
                    "message": "create requires at least one path",
                }

            files = _collect_files(selected_paths, root=root)
            if not files:
                return {
                    "success": False,
                    "error": "no_files_found",
                    "message": "No files were found under the provided paths",
                }

            checkpoint_id_value = f"cp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
            cp_dir = _checkpoint_dir(base_dir, checkpoint_id_value)
            files_dir = cp_dir / "files"
            files_dir.mkdir(parents=True, exist_ok=True)

            file_entries: list[dict[str, Any]] = []
            for file_path in files:
                rel = _to_posix_relative(file_path, root=root)
                target = files_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, target)
                file_entries.append(
                    {
                        "path": rel,
                        "size": file_path.stat().st_size,
                        "sha256": _sha256_for_file(file_path),
                    }
                )

            metadata = {
                "id": checkpoint_id_value,
                "name": name or checkpoint_id_value,
                "note": note,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "file_count": len(file_entries),
                "paths": selected_paths,
                "files": file_entries,
            }

            with (cp_dir / "metadata.json").open("w", encoding="utf-8") as handle:
                json.dump(metadata, handle, indent=2)
                handle.write("\n")

            checkpoints.append(
                {
                    "id": metadata["id"],
                    "name": metadata["name"],
                    "created_at_utc": metadata["created_at_utc"],
                    "file_count": metadata["file_count"],
                    "paths": metadata["paths"],
                }
            )
            _save_index(base_dir, checkpoints)

            return {
                "success": True,
                "message": f"Created checkpoint {checkpoint_id_value}",
                "data": {
                    "checkpoint": metadata,
                    "storage_dir": str(cp_dir),
                },
            }

        if not checkpoint_id:
            return {
                "success": False,
                "error": "checkpoint_id_required",
                "message": f"{action} requires checkpoint_id",
            }

        entry = _get_checkpoint_entry(checkpoints, checkpoint_id)
        if entry is None:
            return {
                "success": False,
                "error": "checkpoint_not_found",
                "message": f"Checkpoint not found: {checkpoint_id}",
            }

        cp_dir = _checkpoint_dir(base_dir, checkpoint_id)
        metadata_path = cp_dir / "metadata.json"
        if not metadata_path.exists():
            return {
                "success": False,
                "error": "checkpoint_corrupt",
                "message": f"Checkpoint metadata missing for {checkpoint_id}",
            }

        with metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        file_entries = metadata.get("files") if isinstance(metadata, dict) else None
        if not isinstance(file_entries, list):
            return {
                "success": False,
                "error": "checkpoint_corrupt",
                "message": f"Invalid checkpoint metadata for {checkpoint_id}",
            }

        if action == "inspect":
            return {"success": True, "data": {"checkpoint": metadata}}

        selected = set(_parse_paths(paths))

        if action == "verify":
            changed: list[str] = []
            missing: list[str] = []
            unchanged: list[str] = []

            for file_entry in file_entries:
                rel_path = str(file_entry.get("path") or "")
                if not rel_path:
                    continue
                if selected and rel_path not in selected:
                    continue

                live_path = _resolve_user_path(rel_path, root=root)
                if not live_path.exists():
                    missing.append(rel_path)
                    continue
                if _sha256_for_file(live_path) == str(file_entry.get("sha256") or ""):
                    unchanged.append(rel_path)
                else:
                    changed.append(rel_path)

            return {
                "success": True,
                "data": {
                    "checkpoint_id": checkpoint_id,
                    "changed": changed,
                    "missing": missing,
                    "unchanged": unchanged,
                    "summary": {
                        "changed": len(changed),
                        "missing": len(missing),
                        "unchanged": len(unchanged),
                    },
                },
            }

        if action == "restore":
            restored: list[str] = []
            for file_entry in file_entries:
                rel_path = str(file_entry.get("path") or "")
                if not rel_path:
                    continue
                if selected and rel_path not in selected:
                    continue

                source = cp_dir / "files" / rel_path
                target = _resolve_user_path(rel_path, root=root)

                if not source.exists():
                    continue
                if dry_run:
                    restored.append(rel_path)
                    continue

                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                restored.append(rel_path)

            return {
                "success": True,
                "message": "Restore preview generated" if dry_run else "Checkpoint restored",
                "data": {
                    "checkpoint_id": checkpoint_id,
                    "dry_run": dry_run,
                    "restored_paths": restored,
                    "restored_count": len(restored),
                },
            }

        if action == "delete":
            if dry_run:
                return {
                    "success": True,
                    "message": "Delete preview generated",
                    "data": {
                        "checkpoint_id": checkpoint_id,
                        "dry_run": True,
                    },
                }

            if cp_dir.exists():
                shutil.rmtree(cp_dir)
            checkpoints = [item for item in checkpoints if item.get("id") != checkpoint_id]
            _save_index(base_dir, checkpoints)
            return {
                "success": True,
                "message": f"Deleted checkpoint {checkpoint_id}",
                "data": {
                    "checkpoint_id": checkpoint_id,
                },
            }

        return {
            "success": False,
            "error": "unsupported_action",
            "message": f"Unsupported action: {action}",
        }

    except Exception as exc:
        return {
            "success": False,
            "error": "checkpoint_operation_failed",
            "message": f"Checkpoint operation failed: {exc!s}",
        }
