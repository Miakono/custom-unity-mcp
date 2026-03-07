"""Tests for V2 pipeline tools.

Covers 8 tools:
- record_pipeline
- stop_pipeline_recording
- save_pipeline
- list_pipelines
- replay_pipeline
- list_playbooks
- run_playbook
- create_playbook
"""

import inspect
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from services.tools.record_pipeline import record_pipeline, record_action, get_recording_state
from services.tools.stop_pipeline_recording import stop_pipeline_recording
from services.tools.save_pipeline import save_pipeline
from services.tools.list_pipelines import list_pipelines
from services.tools.replay_pipeline import replay_pipeline
from services.tools.list_playbooks import list_playbooks
from services.tools.run_playbook import run_playbook
from services.tools.create_playbook import create_playbook
from tests.integration.test_helpers import DummyContext


# =============================================================================
# record_pipeline Tests
# =============================================================================
class TestRecordPipelineInterface:
    """Tests for tool interface."""

    def test_tool_has_required_parameters(self):
        """The record_pipeline tool should have required parameters."""
        sig = inspect.signature(record_pipeline)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "name" in sig.parameters
        assert "description" in sig.parameters
        assert "filter" in sig.parameters


class TestRecordPipelineStatus:
    """Tests for status action."""

    @pytest.mark.asyncio
    async def test_status_not_recording(self):
        """Test status when not recording."""
        # Reset state first
        from services.tools import record_pipeline as rp_module
        rp_module._recording_state["is_recording"] = False

        resp = await record_pipeline(
            DummyContext(),
            action="status",
        )

        assert resp["success"] is True
        assert resp["status"] == "idle"

    @pytest.mark.asyncio
    async def test_status_while_recording(self):
        """Test status while recording."""
        # Start recording first
        from services.tools import record_pipeline as rp_module
        import time
        rp_module._recording_state = {
            "is_recording": True,
            "recording_start_time": time.time(),
            "recorded_actions": [],
            "pipeline_name": "TestPipeline",
            "pipeline_description": "Test description",
            "filter": [],
        }

        resp = await record_pipeline(
            DummyContext(),
            action="status",
        )

        assert resp["success"] is True
        assert resp["status"] == "recording"
        assert resp["pipeline_name"] == "TestPipeline"


class TestRecordPipelineStart:
    """Tests for start action."""

    @pytest.mark.asyncio
    async def test_start_recording(self, tmp_path, monkeypatch):
        """Test starting recording."""
        # Reset state
        from services.tools import record_pipeline as rp_module
        rp_module._recording_state["is_recording"] = False

        # Mock the session file location
        monkeypatch.setattr(
            rp_module,
            "_get_recording_session_file",
            lambda: tmp_path / "current_session.json",
        )

        resp = await record_pipeline(
            DummyContext(),
            action="start",
            name="MyPipeline",
            description="Test pipeline",
            filter=["manage_gameobject"],
        )

        assert resp["success"] is True
        assert resp["pipeline_name"] == "MyPipeline"
        assert "Test pipeline" in resp["description"]

    @pytest.mark.asyncio
    async def test_start_recording_requires_name(self):
        """Test that starting recording requires a name."""
        resp = await record_pipeline(
            DummyContext(),
            action="start",
        )

        assert resp["success"] is False
        assert "name is required" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_start_recording_already_recording(self):
        """Test starting recording when already recording."""
        from services.tools import record_pipeline as rp_module
        import time
        rp_module._recording_state = {
            "is_recording": True,
            "recording_start_time": time.time(),
            "recorded_actions": [],
            "pipeline_name": "ExistingPipeline",
            "pipeline_description": None,
            "filter": [],
        }

        resp = await record_pipeline(
            DummyContext(),
            action="start",
            name="NewPipeline",
        )

        assert resp["success"] is False
        assert "already recording" in resp["message"].lower()


class TestRecordAction:
    """Tests for record_action function."""

    def test_record_action_while_recording(self):
        """Test recording an action while recording is active."""
        from services.tools import record_pipeline as rp_module
        import time
        rp_module._recording_state = {
            "is_recording": True,
            "recording_start_time": time.time(),
            "recorded_actions": [],
            "pipeline_name": "Test",
            "pipeline_description": None,
            "filter": [],
        }

        record_action("manage_gameobject", {"action": "create", "name": "Player"})

        assert len(rp_module._recording_state["recorded_actions"]) == 1
        assert rp_module._recording_state["recorded_actions"][0]["tool"] == "manage_gameobject"

    def test_record_action_not_recording(self):
        """Test that recording is skipped when not recording."""
        from services.tools import record_pipeline as rp_module
        rp_module._recording_state["is_recording"] = False
        original_count = len(rp_module._recording_state["recorded_actions"])

        record_action("manage_gameobject", {"action": "create"})

        assert len(rp_module._recording_state["recorded_actions"]) == original_count

    def test_record_action_with_filter(self):
        """Test that filter is applied correctly."""
        from services.tools import record_pipeline as rp_module
        import time
        rp_module._recording_state = {
            "is_recording": True,
            "recording_start_time": time.time(),
            "recorded_actions": [],
            "pipeline_name": "Test",
            "pipeline_description": None,
            "filter": ["manage_gameobject"],
        }

        record_action("manage_scene", {"action": "save"})  # Not in filter

        assert len(rp_module._recording_state["recorded_actions"]) == 0

        record_action("manage_gameobject", {"action": "create"})  # In filter

        assert len(rp_module._recording_state["recorded_actions"]) == 1


# =============================================================================
# stop_pipeline_recording Tests
# =============================================================================
class TestStopPipelineRecording:
    """Tests for stop_pipeline_recording tool."""

    def test_tool_interface(self):
        """Test tool has correct interface."""
        sig = inspect.signature(stop_pipeline_recording)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "save" in sig.parameters

    @pytest.mark.asyncio
    async def test_stop_not_recording(self):
        """Test stopping when not recording."""
        from services.tools import record_pipeline as rp_module
        rp_module._recording_state["is_recording"] = False

        resp = await stop_pipeline_recording(
            DummyContext(),
            action="stop",
        )

        assert resp["success"] is False
        assert "not currently recording" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_discard_recording(self):
        """Test discarding recording."""
        from services.tools import record_pipeline as rp_module
        import time
        rp_module._recording_state = {
            "is_recording": True,
            "recording_start_time": time.time(),
            "recorded_actions": [{"tool": "test"}],
            "pipeline_name": "TestPipeline",
            "pipeline_description": None,
            "filter": [],
        }

        resp = await stop_pipeline_recording(
            DummyContext(),
            action="discard",
        )

        assert resp["success"] is True
        assert resp["actions_discarded"] == 1

    @pytest.mark.asyncio
    async def test_stop_and_save(self, tmp_path, monkeypatch):
        """Test stopping and saving recording."""
        from services.tools import record_pipeline as rp_module
        import time
        rp_module._recording_state = {
            "is_recording": True,
            "recording_start_time": time.time(),
            "recorded_actions": [
                {"tool": "manage_gameobject", "action": "create", "params": {}, "timestamp": time.time()},
            ],
            "pipeline_name": "TestPipeline",
            "pipeline_description": "Test description",
            "filter": [],
        }

        # Mock the pipelines directory
        def mock_pipelines_dir():
            return tmp_path

        monkeypatch.setattr(
            "services.tools.stop_pipeline_recording._get_pipelines_directory",
            mock_pipelines_dir,
        )

        resp = await stop_pipeline_recording(
            DummyContext(),
            action="stop",
            save=True,
        )

        assert resp["success"] is True
        assert resp["saved"] is True
        assert "saved_path" in resp


# =============================================================================
# save_pipeline Tests
# =============================================================================
class TestSavePipelineInterface:
    """Tests for tool interface."""

    def test_tool_has_required_parameters(self):
        """The save_pipeline tool should have required parameters."""
        sig = inspect.signature(save_pipeline)
        assert "ctx" in sig.parameters
        assert "name" in sig.parameters
        assert "steps" in sig.parameters


class TestSavePipeline:
    """Tests for save_pipeline functionality."""

    @pytest.mark.asyncio
    async def test_save_pipeline(self, tmp_path, monkeypatch):
        """Test saving a pipeline."""
        monkeypatch.setattr(
            "services.tools.save_pipeline._get_pipelines_directory",
            lambda: tmp_path,
        )

        steps = [
            {"tool": "manage_gameobject", "action": "create", "params": {"name": "Player"}},
        ]

        resp = await save_pipeline(
            DummyContext(),
            name="MyPipeline",
            steps=steps,
            description="Test pipeline",
            author="TestAuthor",
            tags=["test", "example"],
        )

        assert resp["success"] is True
        assert resp["step_count"] == 1
        assert (tmp_path / "MyPipeline.json").exists()

    @pytest.mark.asyncio
    async def test_save_pipeline_requires_name(self):
        """Test that saving requires a name."""
        resp = await save_pipeline(
            DummyContext(),
            name="",
            steps=[{"tool": "test"}],
        )

        assert resp["success"] is False
        assert "name is required" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_save_pipeline_requires_steps(self):
        """Test that saving requires steps."""
        resp = await save_pipeline(
            DummyContext(),
            name="Test",
            steps=[],
        )

        assert resp["success"] is False
        assert "steps must be a non-empty list" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_save_pipeline_validates_steps(self):
        """Test that saving validates step format."""
        resp = await save_pipeline(
            DummyContext(),
            name="Test",
            steps=["invalid_step"],  # Should be dict, not string
        )

        assert resp["success"] is False
        assert "must be an object" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_save_pipeline_no_overwrite(self, tmp_path, monkeypatch):
        """Test that overwrite=False prevents overwriting."""
        monkeypatch.setattr(
            "services.tools.save_pipeline._get_pipelines_directory",
            lambda: tmp_path,
        )

        # Create existing file
        (tmp_path / "Existing.json").write_text("{}")

        resp = await save_pipeline(
            DummyContext(),
            name="Existing",
            steps=[{"tool": "test", "action": "test"}],
            overwrite=False,
        )

        assert resp["success"] is False
        assert "already exists" in resp["message"].lower()


# =============================================================================
# list_pipelines Tests
# =============================================================================
class TestListPipelines:
    """Tests for list_pipelines tool."""

    @pytest.mark.asyncio
    async def test_list_pipelines(self, tmp_path, monkeypatch):
        """Test listing pipelines."""
        # Create test pipeline files
        pipeline_data = {
            "metadata": {
                "name": "TestPipeline",
                "version": "1.0",
                "description": "Test",
                "author": "TestAuthor",
                "tags": ["test"],
            },
            "steps": [{"tool": "test"}],
        }
        (tmp_path / "TestPipeline.json").write_text(json.dumps(pipeline_data))

        monkeypatch.setattr(
            "services.tools.list_pipelines._get_pipelines_directories",
            lambda: [tmp_path],
        )

        resp = await list_pipelines(
            DummyContext(),
            action="list",
        )

        assert resp["success"] is True
        assert len(resp["pipelines"]) == 1
        assert resp["pipelines"][0]["name"] == "TestPipeline"

    @pytest.mark.asyncio
    async def test_get_pipeline(self, tmp_path, monkeypatch):
        """Test getting a specific pipeline."""
        pipeline_data = {
            "metadata": {"name": "TestPipeline"},
            "steps": [{"tool": "test"}],
        }
        (tmp_path / "TestPipeline.json").write_text(json.dumps(pipeline_data))

        monkeypatch.setattr(
            "services.tools.list_pipelines._get_pipelines_directories",
            lambda: [tmp_path],
        )

        resp = await list_pipelines(
            DummyContext(),
            action="get",
            name="TestPipeline",
        )

        assert resp["success"] is True
        assert "pipeline" in resp

    @pytest.mark.asyncio
    async def test_get_pipeline_requires_name(self):
        """Test that get action requires name."""
        resp = await list_pipelines(
            DummyContext(),
            action="get",
        )

        assert resp["success"] is False
        assert "name is required" in resp["message"].lower()


# =============================================================================
# replay_pipeline Tests
# =============================================================================
class TestReplayPipeline:
    """Tests for replay_pipeline tool."""

    @pytest.mark.asyncio
    async def test_dry_run(self, tmp_path, monkeypatch):
        """Test dry run mode."""
        pipeline_data = {
            "metadata": {"name": "TestPipeline", "description": "Test"},
            "steps": [
                {"tool": "manage_gameobject", "action": "create"},
                {"tool": "manage_components", "action": "add"},
            ],
        }
        (tmp_path / "TestPipeline.json").write_text(json.dumps(pipeline_data))

        monkeypatch.setattr(
            "services.tools.replay_pipeline._find_pipeline",
            lambda name: (pipeline_data, tmp_path / "TestPipeline.json"),
        )

        resp = await replay_pipeline(
            DummyContext(),
            name="TestPipeline",
            dry_run=True,
        )

        assert resp["success"] is True
        assert "dry run" in resp["message"].lower()
        assert len(resp["steps_preview"]) == 2

    @pytest.mark.asyncio
    async def test_replay_not_found(self):
        """Test replaying non-existent pipeline."""
        resp = await replay_pipeline(
            DummyContext(),
            name="NonExistent",
        )

        assert resp["success"] is False
        assert "not found" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_replay_empty_pipeline(self, monkeypatch):
        """Test replaying empty pipeline."""
        monkeypatch.setattr(
            "services.tools.replay_pipeline._find_pipeline",
            lambda name: ({"metadata": {}, "steps": []}, None),
        )

        resp = await replay_pipeline(
            DummyContext(),
            name="EmptyPipeline",
        )

        assert resp["success"] is False
        assert "no steps" in resp["message"].lower()


# =============================================================================
# list_playbooks Tests
# =============================================================================
class TestListPlaybooks:
    """Tests for list_playbooks tool."""

    @pytest.mark.asyncio
    async def test_list_playbooks(self, monkeypatch):
        """Test listing playbooks."""
        # Mock the _get_all_playbooks function
        mock_playbooks = [
            {
                "name": "basic_player_controller",
                "description": "Creates a player",
                "built_in": True,
                "category": "gameplay",
                "tags": ["player", "controller"],
            },
        ]

        monkeypatch.setattr(
            "services.tools.list_playbooks._get_all_playbooks",
            lambda: mock_playbooks,
        )

        resp = await list_playbooks(
            DummyContext(),
            action="list",
        )

        assert resp["success"] is True
        assert len(resp["playbooks"]) == 1

    @pytest.mark.asyncio
    async def test_get_playbook(self, tmp_path, monkeypatch):
        """Test getting a specific playbook."""
        playbook_data = {
            "metadata": {"name": "TestPlaybook"},
            "steps": [{"tool": "test"}],
        }

        monkeypatch.setattr(
            "services.tools.list_playbooks._find_playbook",
            lambda name: (playbook_data, tmp_path / "TestPlaybook.json"),
        )

        resp = await list_playbooks(
            DummyContext(),
            action="get",
            playbook_id="TestPlaybook",
        )

        assert resp["success"] is True
        assert "playbook" in resp

    @pytest.mark.asyncio
    async def test_get_playbook_requires_id(self):
        """Test that get action requires playbook_id."""
        resp = await list_playbooks(
            DummyContext(),
            action="get",
        )

        assert resp["success"] is False
        assert "playbook_id is required" in resp["message"].lower()


# =============================================================================
# run_playbook Tests
# =============================================================================
class TestRunPlaybook:
    """Tests for run_playbook tool."""

    @pytest.mark.asyncio
    async def test_run_not_found(self):
        """Test running non-existent playbook."""
        resp = await run_playbook(
            DummyContext(),
            playbook_id="NonExistent",
        )

        assert resp["success"] is False
        assert "not found" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_dry_run(self, monkeypatch):
        """Test dry run mode."""
        playbook_data = {
            "metadata": {"name": "TestPlaybook"},
            "steps": [{"tool": "manage_gameobject", "action": "create"}],
            "parameters": {"player_name": {""}},
        }

        monkeypatch.setattr(
            "services.tools.run_playbook._find_playbook",
            lambda name: (playbook_data, None),
        )

        resp = await run_playbook(
            DummyContext(),
            playbook_id="TestPlaybook",
            dry_run=True,
        )

        assert resp["success"] is True
        assert "dry run" in resp["message"].lower()


# =============================================================================
# create_playbook Tests
# =============================================================================
class TestCreatePlaybookInterface:
    """Tests for tool interface."""

    def test_tool_has_required_parameters(self):
        """The create_playbook tool should have required parameters."""
        sig = inspect.signature(create_playbook)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "name" in sig.parameters


class TestCreatePlaybook:
    """Tests for create_playbook functionality."""

    @pytest.mark.asyncio
    async def test_create_from_steps(self, tmp_path, monkeypatch):
        """Test creating playbook from steps."""
        monkeypatch.setattr(
            "services.tools.create_playbook.BUILT_IN_PLAYBOOKS_DIR",
            tmp_path,
        )

        steps = [
            {"tool": "manage_gameobject", "action": "create", "params": {"name": "Player"}},
        ]

        resp = await create_playbook(
            DummyContext(),
            action="from_steps",
            name="MyPlaybook",
            description="Test playbook",
            steps=steps,
            category="gameplay",
            tags=["test"],
        )

        assert resp["success"] is True
        assert resp["step_count"] == 1

    @pytest.mark.asyncio
    async def test_create_from_steps_requires_steps(self):
        """Test that from_steps action requires steps."""
        resp = await create_playbook(
            DummyContext(),
            action="from_steps",
            name="MyPlaybook",
        )

        assert resp["success"] is False
        assert "steps are required" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_create_from_pipeline_requires_pipeline_name(self):
        """Test that from_pipeline action requires pipeline_name."""
        resp = await create_playbook(
            DummyContext(),
            action="from_pipeline",
            name="MyPlaybook",
        )

        assert resp["success"] is False
        assert "pipeline_name is required" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_create_from_pipeline_not_found(self, monkeypatch):
        """Test creating from non-existent pipeline."""
        monkeypatch.setattr(
            "services.tools.list_pipelines._get_pipelines_directories",
            lambda: [],
        )

        resp = await create_playbook(
            DummyContext(),
            action="from_pipeline",
            name="MyPlaybook",
            pipeline_name="NonExistent",
        )

        assert resp["success"] is False
        assert "not found" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_no_overwrite(self, tmp_path, monkeypatch):
        """Test that overwrite=False prevents overwriting."""
        monkeypatch.setattr(
            "services.tools.create_playbook.BUILT_IN_PLAYBOOKS_DIR",
            tmp_path,
        )

        # Create existing file
        (tmp_path / "Existing.json").write_text("{}")

        resp = await create_playbook(
            DummyContext(),
            action="from_steps",
            name="Existing",
            steps=[{"tool": "test"}],
            overwrite=False,
        )

        assert resp["success"] is False
        assert "already exists" in resp["message"].lower()
