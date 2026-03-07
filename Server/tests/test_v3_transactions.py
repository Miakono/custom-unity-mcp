"""Validation tests for V3 Transaction tools (Phase 1).

Tests for:
- manage_transactions
- preview_changes
- rollback_changes
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.tools.manage_transactions import manage_transactions
from services.tools.preview_changes import preview_changes
from services.tools.rollback_changes import rollback_changes
from services.resources.transaction_state import TransactionManager, ChangeType
from tests.integration.test_helpers import DummyContext


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def ctx():
    """Provide a dummy context for testing."""
    return DummyContext()


@pytest.fixture
def fresh_transaction_manager():
    """Provide a fresh transaction manager with clean state."""
    manager = TransactionManager()
    # Clear any existing transactions
    manager._transactions.clear()
    return manager


@pytest.fixture
def mock_unity_response():
    """Provide a standard mock Unity success response."""
    return {"success": True, "data": {}}


# =============================================================================
# Phase 1: Transactions - manage_transactions
# =============================================================================

@pytest.mark.asyncio
class TestManageTransactions:
    """Tests for the manage_transactions tool."""

    async def test_begin_transaction_requires_name(self, ctx):
        """test_begin_transaction: begin_transaction requires a name parameter."""
        result = await manage_transactions(ctx, action="begin_transaction")
        
        assert result["success"] is False
        assert result["error"] == "name_required"
        assert "name" in result["message"].lower()

    async def test_begin_transaction_creates_transaction(self, ctx):
        """test_begin_transaction: Successfully creates a named transaction."""
        result = await manage_transactions(ctx, action="begin_transaction", name="TestTransaction")
        
        assert result["success"] is True
        assert "transaction_id" in result["data"]
        assert result["data"]["name"] == "TestTransaction"
        assert result["data"]["status"] == "pending"

    async def test_begin_transaction_with_checkpoint(self, ctx):
        """test_begin_transaction: Creates transaction with checkpoint ID."""
        result = await manage_transactions(
            ctx, 
            action="begin_transaction", 
            name="TestWithCheckpoint",
            checkpoint_id="chk_12345"
        )
        
        assert result["success"] is True
        assert result["data"]["checkpoint_id"] == "chk_12345"

    async def test_append_actions_requires_change_type(self, ctx):
        """test_append_actions: append_action requires change_type parameter."""
        # First begin a transaction
        await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        
        result = await manage_transactions(
            ctx, 
            action="append_action",
            asset_path="Assets/Test.prefab",
            description="Test change"
        )
        
        assert result["success"] is False
        assert result["error"] == "change_type_required"

    async def test_append_actions_requires_asset_path(self, ctx):
        """test_append_actions: append_action requires asset_path parameter."""
        await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        
        result = await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            description="Test change"
        )
        
        assert result["success"] is False
        assert result["error"] == "asset_path_required"

    async def test_append_actions_requires_description(self, ctx):
        """test_append_actions: append_action requires description parameter."""
        await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        
        result = await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab"
        )
        
        assert result["success"] is False
        assert result["error"] == "description_required"

    async def test_append_actions_without_active_transaction(self, ctx):
        """test_append_actions: Returns error when no active transaction exists."""
        result = await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Test change"
        )
        
        assert result["success"] is False
        assert result["error"] == "no_active_transaction"

    async def test_append_actions_success(self, ctx):
        """test_append_actions: Successfully appends action to transaction."""
        tx_result = await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        tx_id = tx_result["data"]["transaction_id"]
        
        result = await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Modified prefab",
            before_hash="hash_before",
            after_hash="hash_after"
        )
        
        assert result["success"] is True
        assert result["data"]["transaction_id"] == tx_id
        assert result["data"]["change"]["type"] == "modified"
        assert result["data"]["change"]["asset_path"] == "Assets/Test.prefab"

    async def test_append_actions_with_action_params(self, ctx):
        """test_append_actions: Appends action with serialized action_params."""
        await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        
        action_params = {"field": "value", "count": 42}
        result = await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Modified with params",
            action_params=action_params
        )
        
        assert result["success"] is True
        assert result["data"]["change"]["action_params"] == action_params

    async def test_commit_transaction_without_active_transaction(self, ctx):
        """test_commit_transaction: Returns error when no active transaction exists."""
        result = await manage_transactions(ctx, action="commit_transaction")
        
        assert result["success"] is False
        assert result["error"] == "no_active_transaction"

    async def test_commit_transaction_success(self, ctx):
        """test_commit_transaction: Successfully commits pending transaction."""
        await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Test change"
        )
        
        result = await manage_transactions(ctx, action="commit_transaction")
        
        assert result["success"] is True
        assert result["data"]["status"] == "committed"
        assert "summary" in result["data"]
        assert result["data"]["summary"]["total_changes"] == 1

    async def test_rollback_transaction_requires_transaction_id(self, ctx):
        """test_rollback_transaction: rollback_transaction requires transaction_id."""
        result = await manage_transactions(ctx, action="rollback_transaction")
        
        assert result["success"] is False
        assert result["error"] == "transaction_id_required"

    async def test_rollback_transaction_success(self, ctx):
        """test_rollback_transaction: Successfully rolls back committed transaction."""
        # Create and commit a transaction
        tx_result = await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        tx_id = tx_result["data"]["transaction_id"]
        await manage_transactions(ctx, action="commit_transaction")
        
        # Now rollback
        result = await manage_transactions(
            ctx, 
            action="rollback_transaction",
            transaction_id=tx_id
        )
        
        assert result["success"] is True
        assert result["data"]["status"] == "rolled_back"

    async def test_preview_transaction_without_transaction(self, ctx):
        """test_preview_transaction: Returns error when no transaction to preview."""
        result = await manage_transactions(ctx, action="preview_transaction")
        
        assert result["success"] is False
        assert result["error"] == "no_active_transaction"

    async def test_preview_transaction_success(self, ctx):
        """test_preview_transaction: Successfully previews current transaction."""
        await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Test change"
        )
        
        result = await manage_transactions(ctx, action="preview_transaction")
        
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["name"] == "TestTx"

    async def test_get_transaction_state(self, ctx):
        """test_get_transaction_state: Returns current transaction state."""
        tx_result = await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        tx_id = tx_result["data"]["transaction_id"]
        
        result = await manage_transactions(
            ctx, 
            action="get_transaction_state",
            transaction_id=tx_id
        )
        
        assert result["success"] is True
        assert "data" in result

    async def test_list_transactions(self, ctx):
        """test_list_transactions: Lists all transactions with optional filtering."""
        await manage_transactions(ctx, action="begin_transaction", name="Tx1")
        await manage_transactions(ctx, action="commit_transaction")
        await manage_transactions(ctx, action="begin_transaction", name="Tx2")
        
        result = await manage_transactions(ctx, action="list_transactions")
        
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["count"] >= 2

    async def test_list_transactions_with_status_filter(self, ctx):
        """test_list_transactions: Filters transactions by status."""
        await manage_transactions(ctx, action="begin_transaction", name="PendingTx")
        
        result = await manage_transactions(
            ctx, 
            action="list_transactions",
            status_filter="pending"
        )
        
        assert result["success"] is True
        # Should only return pending transactions
        for tx in result["data"]["transactions"]:
            assert tx["status"] == "pending"

    async def test_transaction_with_json_string_action_params(self, ctx):
        """test_append_actions: Handles JSON string action_params."""
        await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        
        action_params_json = '{"field": "value", "count": 42}'
        result = await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Modified with JSON params",
            action_params=action_params_json
        )
        
        assert result["success"] is True

    async def test_transaction_with_invalid_action_params(self, ctx):
        """test_append_actions: Returns error for invalid action_params."""
        await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        
        result = await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Test",
            action_params="invalid json"
        )
        
        assert result["success"] is False
        assert result["error"] == "invalid_action_params"


# =============================================================================
# Phase 1: Transactions - preview_changes
# =============================================================================

@pytest.mark.asyncio
class TestPreviewChanges:
    """Tests for the preview_changes tool."""

    async def test_preview_changes_no_active_transaction(self, ctx):
        """test_preview_scene_changes: Returns error when no active transaction."""
        result = await preview_changes(ctx)
        
        assert result["success"] is False
        assert result["error"] == "no_active_transaction"

    async def test_preview_changes_success(self, ctx):
        """test_preview_scene_changes: Successfully previews changes."""
        # Setup: Create transaction with changes
        await manage_transactions(ctx, action="begin_transaction", name="PreviewTx")
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Scene.unity",
            description="Scene modification"
        )
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="created",
            asset_path="Assets/NewPrefab.prefab",
            description="New prefab"
        )
        
        result = await preview_changes(ctx)
        
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["name"] == "PreviewTx"
        assert result["data"]["summary"]["total_changes"] == 2
        assert result["data"]["summary"]["modified_count"] == 1
        assert result["data"]["summary"]["created_count"] == 1

    async def test_preview_changes_with_analysis(self, ctx):
        """test_preview_scene_changes: Includes detailed analysis when requested."""
        await manage_transactions(ctx, action="begin_transaction", name="PreviewTx")
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Test change"
        )
        
        result = await preview_changes(ctx, include_analysis=True)
        
        assert result["success"] is True
        assert "detailed_analysis" in result["data"]

    async def test_preview_changes_without_analysis(self, ctx):
        """test_preview_scene_changes: Excludes analysis when not requested."""
        await manage_transactions(ctx, action="begin_transaction", name="PreviewTx")
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Test change"
        )
        
        result = await preview_changes(ctx, include_analysis=False)
        
        assert result["success"] is True
        assert "detailed_analysis" not in result["data"]

    async def test_preview_changes_with_conflict_detection(self, ctx):
        """test_preview_scene_changes: Detects conflicts when enabled."""
        await manage_transactions(ctx, action="begin_transaction", name="PreviewTx")
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Test change"
        )
        
        result = await preview_changes(ctx, detect_conflicts=True)
        
        assert result["success"] is True
        assert "conflicts" in result["data"]
        assert "has_conflicts" in result["data"]

    async def test_preview_prefab_changes(self, ctx):
        """test_preview_prefab_changes: Can preview prefab-specific changes."""
        await manage_transactions(ctx, action="begin_transaction", name="PrefabTx")
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Prefabs/Character.prefab",
            description="Prefab modification"
        )
        
        result = await preview_changes(ctx)
        
        assert result["success"] is True
        assert result["data"]["summary"]["modified_count"] == 1


# =============================================================================
# Phase 1: Transactions - rollback_changes
# =============================================================================

@pytest.mark.asyncio
class TestRollbackChanges:
    """Tests for the rollback_changes tool."""

    async def test_get_rollback_summary_requires_transaction_id(self, ctx):
        """test_get_rollback_summary: Requires transaction_id parameter."""
        result = await rollback_changes(ctx, action="get_rollback_summary")
        
        assert result["success"] is False
        assert result["error"] == "transaction_id_required"

    async def test_get_rollback_summary_success(self, ctx):
        """test_get_rollback_summary: Returns rollback feasibility summary."""
        # Create and commit a transaction
        await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Test change",
            can_undo=True
        )
        tx_result = await manage_transactions(ctx, action="commit_transaction")
        tx_id = tx_result["data"]["transaction_id"]
        
        result = await rollback_changes(
            ctx, 
            action="get_rollback_summary",
            transaction_id=tx_id
        )
        
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["can_rollback_fully"] is True
        assert "recommendations" in result["data"]

    async def test_rollback_transaction_requires_transaction_id(self, ctx):
        """test_rollback_scene: Requires transaction_id parameter."""
        result = await rollback_changes(ctx, action="rollback_transaction")
        
        assert result["success"] is False
        assert result["error"] == "transaction_id_required"

    async def test_rollback_transaction_not_found(self, ctx):
        """test_rollback_scene: Returns error for non-existent transaction."""
        result = await rollback_changes(
            ctx, 
            action="rollback_transaction",
            transaction_id="non_existent_id"
        )
        
        assert result["success"] is False
        assert result["error"] == "transaction_not_found"

    async def test_rollback_transaction_wrong_status(self, ctx):
        """test_rollback_scene: Returns error for non-committed transaction."""
        # Create but don't commit transaction
        tx_result = await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        tx_id = tx_result["data"]["transaction_id"]
        
        result = await rollback_changes(
            ctx, 
            action="rollback_transaction",
            transaction_id=tx_id
        )
        
        assert result["success"] is False
        assert result["error"] == "invalid_transaction_status"

    async def test_rollback_transaction_with_non_undoable_changes(self, ctx):
        """test_rollback_scene: Returns error when changes cannot be undone."""
        # Create transaction with non-undoable change
        await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="deleted",
            asset_path="Assets/Test.prefab",
            description="Deleted prefab",
            can_undo=False
        )
        tx_result = await manage_transactions(ctx, action="commit_transaction")
        tx_id = tx_result["data"]["transaction_id"]
        
        result = await rollback_changes(
            ctx, 
            action="rollback_transaction",
            transaction_id=tx_id
        )
        
        assert result["success"] is False
        assert result["error"] == "non_undoable_changes"

    async def test_rollback_transaction_dry_run(self, ctx):
        """test_rollback_scene: Supports dry-run mode."""
        await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Test change"
        )
        tx_result = await manage_transactions(ctx, action="commit_transaction")
        tx_id = tx_result["data"]["transaction_id"]
        
        result = await rollback_changes(
            ctx, 
            action="rollback_transaction",
            transaction_id=tx_id,
            dry_run=True
        )
        
        assert result["success"] is True
        assert result["data"]["dry_run"] is True

    async def test_rollback_transaction_success(self, ctx):
        """test_rollback_scene: Successfully rolls back committed transaction."""
        await manage_transactions(ctx, action="begin_transaction", name="TestTx")
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Test change",
            can_undo=True
        )
        tx_result = await manage_transactions(ctx, action="commit_transaction")
        tx_id = tx_result["data"]["transaction_id"]
        
        result = await rollback_changes(
            ctx, 
            action="rollback_transaction",
            transaction_id=tx_id
        )
        
        assert result["success"] is True
        assert result["data"]["status"] == "rolled_back"

    async def test_rollback_to_checkpoint_requires_checkpoint_id(self, ctx):
        """test_rollback_prefab: checkpoint rollback requires checkpoint_id."""
        result = await rollback_changes(ctx, action="rollback_to_checkpoint")
        
        assert result["success"] is False
        assert result["error"] == "checkpoint_id_required"

    async def test_rollback_to_checkpoint_delegates(self, ctx):
        """test_rollback_prefab: Delegates to manage_checkpoints."""
        result = await rollback_changes(
            ctx, 
            action="rollback_to_checkpoint",
            checkpoint_id="chk_12345"
        )
        
        # Should return delegation info rather than executing directly
        assert result["success"] is True
        assert result["data"]["checkpoint_id"] == "chk_12345"

    async def test_list_rollback_history(self, ctx):
        """test_rollback_prefab: Lists rolled back transactions."""
        # Create and rollback a transaction
        await manage_transactions(ctx, action="begin_transaction", name="TxToRollback")
        await manage_transactions(
            ctx, 
            action="append_action",
            change_type="modified",
            asset_path="Assets/Test.prefab",
            description="Test change",
            can_undo=True
        )
        tx_result = await manage_transactions(ctx, action="commit_transaction")
        tx_id = tx_result["data"]["transaction_id"]
        await rollback_changes(ctx, action="rollback_transaction", transaction_id=tx_id)
        
        result = await rollback_changes(ctx, action="list_rollback_history")
        
        assert result["success"] is True
        assert result["data"]["count"] >= 1
