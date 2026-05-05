import os

import pytest

from services.code_indexer import get_index_manager, get_project_root_key, normalize_project_root


def test_get_index_manager_rejects_missing_project_root(tmp_path):
    missing_root = tmp_path / "MissingProject"

    with pytest.raises(FileNotFoundError, match="Project root does not exist"):
        get_index_manager(str(missing_root))


def test_get_project_root_key_normalizes_path_casing_and_segments(tmp_path):
    project_root = tmp_path / "ExampleProject"
    project_root.mkdir()

    canonical = str(project_root)
    variant = os.path.join(canonical, ".")

    assert normalize_project_root(variant) == canonical
    assert get_project_root_key(variant) == get_project_root_key(canonical)


# ---------------------------------------------------------------------------
# file_pattern glob-as-regex bug fix tests
# ---------------------------------------------------------------------------

def _make_project(tmp_path, cs_files: dict[str, str]):
    """Create a minimal Unity project layout with given C# files under Assets/."""
    assets = tmp_path / "Assets"
    assets.mkdir()
    for rel, content in cs_files.items():
        target = assets / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return tmp_path


def test_file_pattern_glob_star_matches_extension(tmp_path):
    """*.cs should return all .cs files and exclude non-.cs files."""
    project = _make_project(tmp_path, {
        "Scripts/PlayerController.cs": "public class PlayerController {}",
        "Scripts/EnemyAI.cs": "public class EnemyAI {}",
    })
    manager = get_index_manager(str(project))
    manager.build_index(force_rebuild=True)

    result = manager.search_code(pattern="class", file_pattern="*.cs")
    assert result["success"] is True
    matched_files = {r["file_path"] for r in result["results"]}
    # Both .cs files should appear
    assert any("PlayerController.cs" in f for f in matched_files)
    assert any("EnemyAI.cs" in f for f in matched_files)


def test_file_pattern_glob_prefix_star_filters_correctly(tmp_path):
    """Player*.cs should match PlayerController.cs but not EnemyAI.cs."""
    project = _make_project(tmp_path, {
        "Scripts/PlayerController.cs": "public class PlayerController { void Update() {} }",
        "Scripts/EnemyAI.cs": "public class EnemyAI { void Update() {} }",
    })
    manager = get_index_manager(str(project))
    manager.build_index(force_rebuild=True)

    result = manager.search_code(pattern="Update", file_pattern="Player*.cs")
    assert result["success"] is True
    matched_files = {r["file_path"] for r in result["results"]}
    assert any("PlayerController.cs" in f for f in matched_files), (
        "Player*.cs glob should match PlayerController.cs"
    )
    assert not any("EnemyAI.cs" in f for f in matched_files), (
        "Player*.cs glob must NOT match EnemyAI.cs"
    )


def test_file_pattern_plain_substring_filter(tmp_path):
    """A plain word like 'Player' should match as a substring of the file path."""
    project = _make_project(tmp_path, {
        "Scripts/PlayerController.cs": "public class PlayerController {}",
        "Scripts/EnemyAI.cs": "public class EnemyAI {}",
    })
    manager = get_index_manager(str(project))
    manager.build_index(force_rebuild=True)

    result = manager.search_code(pattern="class", file_pattern="Player")
    assert result["success"] is True
    matched_files = {r["file_path"] for r in result["results"]}
    assert any("PlayerController.cs" in f for f in matched_files)
    assert not any("EnemyAI.cs" in f for f in matched_files)


# ---------------------------------------------------------------------------
# Stale index: deleted-file eviction in update_index
# ---------------------------------------------------------------------------

def test_update_index_evicts_file_deleted_after_discovery(tmp_path, monkeypatch):
    """
    When a file passes find_cs_files() but is deleted before os.path.getmtime()
    is called, update_index must evict the stale entry rather than leaving it.
    """
    project = _make_project(tmp_path, {
        "Scripts/Alive.cs": "public class Alive {}",
        "Scripts/Doomed.cs": "public class Doomed {}",
    })
    manager = get_index_manager(str(project))
    manager.build_index(force_rebuild=True)
    assert len(manager.index.files) == 2

    doomed = os.path.join(str(tmp_path), "Assets", "Scripts", "Doomed.cs")

    original_getmtime = os.path.getmtime

    def _getmtime_deletes_on_first_call(path):
        # Simulate the file being deleted between discovery and stat
        if os.path.normcase(path) == os.path.normcase(doomed):
            os.remove(path)
            raise OSError(f"Simulated: {path} deleted")
        return original_getmtime(path)

    monkeypatch.setattr(os.path, "getmtime", _getmtime_deletes_on_first_call)

    result = manager.update_index()

    assert result["success"] is True
    # The doomed file should be gone from the index
    remaining = list(manager.index.files.keys())
    assert not any("Doomed.cs" in p for p in remaining), (
        "Stale entry for a deleted file must be evicted from the index"
    )
    assert any("Alive.cs" in p for p in remaining), "Alive.cs must still be indexed"