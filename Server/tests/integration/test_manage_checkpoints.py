from pathlib import Path

import pytest

import services.tools.manage_checkpoints as manage_checkpoints_mod

from .test_helpers import DummyContext


@pytest.mark.asyncio
async def test_manage_checkpoints_create_verify_restore_delete(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(manage_checkpoints_mod, "_repo_root", lambda: tmp_path)

    tracked_file = tmp_path / "Assets" / "Player.cs"
    tracked_file.parent.mkdir(parents=True, exist_ok=True)
    tracked_file.write_text("v1", encoding="utf-8")

    created = await manage_checkpoints_mod.manage_checkpoints(
        ctx=DummyContext(),
        action="create",
        name="pre-edit",
        paths=["Assets/Player.cs"],
    )
    assert created["success"] is True
    checkpoint_id = created["data"]["checkpoint"]["id"]

    tracked_file.write_text("v2", encoding="utf-8")

    verify = await manage_checkpoints_mod.manage_checkpoints(
        ctx=DummyContext(),
        action="verify",
        checkpoint_id=checkpoint_id,
    )
    assert verify["success"] is True
    assert verify["data"]["summary"]["changed"] == 1

    preview_restore = await manage_checkpoints_mod.manage_checkpoints(
        ctx=DummyContext(),
        action="restore",
        checkpoint_id=checkpoint_id,
        dry_run=True,
    )
    assert preview_restore["success"] is True
    assert preview_restore["data"]["dry_run"] is True
    assert preview_restore["data"]["restored_count"] == 1

    restored = await manage_checkpoints_mod.manage_checkpoints(
        ctx=DummyContext(),
        action="restore",
        checkpoint_id=checkpoint_id,
    )
    assert restored["success"] is True
    assert tracked_file.read_text(encoding="utf-8") == "v1"

    listed = await manage_checkpoints_mod.manage_checkpoints(
        ctx=DummyContext(),
        action="list",
    )
    assert listed["success"] is True
    assert listed["data"]["count"] == 1

    deleted = await manage_checkpoints_mod.manage_checkpoints(
        ctx=DummyContext(),
        action="delete",
        checkpoint_id=checkpoint_id,
    )
    assert deleted["success"] is True

    listed_after_delete = await manage_checkpoints_mod.manage_checkpoints(
        ctx=DummyContext(),
        action="list",
    )
    assert listed_after_delete["success"] is True
    assert listed_after_delete["data"]["count"] == 0


@pytest.mark.asyncio
async def test_manage_checkpoints_create_requires_paths(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(manage_checkpoints_mod, "_repo_root", lambda: tmp_path)

    result = await manage_checkpoints_mod.manage_checkpoints(
        ctx=DummyContext(),
        action="create",
        paths=None,
    )

    assert result["success"] is False
    assert result["error"] == "paths_required"
