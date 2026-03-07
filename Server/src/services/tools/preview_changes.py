"""Change preview tool for reviewing pending modifications before commit.

This tool provides detailed preview capabilities for transactions and
individual changes, including impact analysis and conflict detection.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.resources.transaction_state import (
    TransactionManager,
    ChangeType,
    TransactionStatus,
)


def _get_txn_manager() -> TransactionManager:
    return TransactionManager()


def _get_context_transaction_id(ctx: Context) -> str | None:
    return getattr(ctx, "_copilot_transaction_id", None)


def _analyze_change_impact(change: Any) -> dict[str, Any]:
    """Analyze the impact of a single change."""
    impact = {
        "severity": "low",
        "warnings": [],
        "affected_dependencies": [],
    }
    
    # Determine severity based on change type
    if change.type == ChangeType.DELETED:
        impact["severity"] = "high"
        impact["warnings"].append("Deletion cannot be undone without checkpoint")
    elif change.type == ChangeType.MODIFIED:
        impact["severity"] = "medium"
        if not change.before_hash:
            impact["warnings"].append("No before-hash for verification")
    elif change.type == ChangeType.FAILED:
        impact["severity"] = "critical"
        impact["warnings"].append("This change failed and may leave partial state")
    
    # Check undo capability
    if not change.can_undo:
        impact["warnings"].append("This change cannot be rolled back")
    
    return impact


def _detect_conflicts(
    manager: TransactionManager,
    transaction_id: str,
) -> list[dict[str, Any]]:
    """Detect potential conflicts with other pending transactions."""
    conflicts = []
    target_txn = manager.get_transaction(transaction_id)
    if not target_txn:
        return conflicts
    
    target_paths = {c.asset_path for c in target_txn.changes}
    
    for txn_id, txn in manager._transactions.items():
        if txn_id == transaction_id:
            continue
        if txn.status != TransactionStatus.PENDING:
            continue
        
        for change in txn.changes:
            if change.asset_path in target_paths:
                conflicts.append({
                    "type": "concurrent_modification",
                    "asset_path": change.asset_path,
                    "other_transaction_id": txn_id,
                    "other_transaction_name": txn.name,
                    "other_change_type": change.type.value,
                    "resolution": "commit one transaction before the other",
                })
    
    return conflicts


@mcp_for_unity_tool(
    group="transactions",
    unity_target=None,
    description=(
        "Preview pending changes before committing a transaction. "
        "Provides detailed analysis including: change summary by category "
        "(created/modified/deleted/moved/failed), impact assessment for each change, "
        "conflict detection with other pending transactions, rollback feasibility, "
        "and verification status (hash comparisons). "
        "Use this tool to review multi-step workflows before final commit."
    ),
    annotations=ToolAnnotations(
        title="Preview Changes",
        destructiveHint=False,
    ),
)
async def preview_changes(
    ctx: Context,
    transaction_id: Annotated[
        str | None,
        "Transaction ID to preview (uses current transaction if not specified)",
    ] = None,
    include_analysis: Annotated[
        bool | str | None,
        "Include detailed impact analysis for each change (default true)",
    ] = True,
    detect_conflicts: Annotated[
        bool | str | None,
        "Detect conflicts with other pending transactions (default true)",
    ] = True,
    verify_hashes: Annotated[
        bool | str | None,
        "Verify before/after hashes for modified assets (default false)",
    ] = False,
) -> dict[str, Any]:
    """
    Preview pending changes in a transaction before committing.
    
    Provides comprehensive analysis of what will change, potential conflicts,
    and rollback feasibility.
    """
    await ctx.info("preview_changes")
    
    manager = _get_txn_manager()
    
    # Resolve transaction
    target_txn_id = transaction_id or _get_context_transaction_id(ctx)
    if target_txn_id is None:
        return {
            "success": False,
            "error": "no_active_transaction",
            "message": "No active transaction to preview. Specify transaction_id or start a transaction with manage_transactions.",
        }
    
    txn = manager.get_transaction(target_txn_id)
    if txn is None:
        return {
            "success": False,
            "error": "transaction_not_found",
            "message": f"Transaction not found: {target_txn_id}",
        }
    
    try:
        # Build change summary by category
        created = []
        modified = []
        deleted = []
        moved = []
        failed = []
        
        for change in txn.changes:
            change_dict = change.to_dict()
            
            if change.type == ChangeType.CREATED:
                created.append(change_dict)
            elif change.type == ChangeType.MODIFIED:
                modified.append(change_dict)
            elif change.type == ChangeType.DELETED:
                deleted.append(change_dict)
            elif change.type == ChangeType.MOVED:
                moved.append(change_dict)
            elif change.type == ChangeType.FAILED:
                failed.append(change_dict)
        
        # Build response
        result = {
            "success": True,
            "data": {
                "transaction_id": txn.transaction_id,
                "name": txn.name,
                "status": txn.status.value,
                "started_at": txn.started_at.isoformat(),
                "checkpoint_id": txn.checkpoint_id,
                "summary": {
                    "total_changes": len(txn.changes),
                    "created_count": len(created),
                    "modified_count": len(modified),
                    "deleted_count": len(deleted),
                    "moved_count": len(moved),
                    "failed_count": len(failed),
                },
                "changes_by_category": {
                    "created": created,
                    "modified": modified,
                    "deleted": deleted,
                    "moved": moved,
                    "failed": failed,
                },
            },
        }
        
        # Add detailed analysis if requested
        if include_analysis:
            analysis = []
            for change in txn.changes:
                impact = _analyze_change_impact(change)
                analysis.append({
                    "asset_path": change.asset_path,
                    "change_type": change.type.value,
                    "description": change.description,
                    "can_undo": change.can_undo,
                    "impact": impact,
                })
            result["data"]["detailed_analysis"] = analysis
        
        # Add conflict detection if requested
        if detect_conflicts:
            conflicts = _detect_conflicts(manager, target_txn_id)
            result["data"]["conflicts"] = conflicts
            result["data"]["has_conflicts"] = len(conflicts) > 0
        
        # Add hash verification info if requested
        if verify_hashes:
            verification = []
            for change in txn.changes:
                if change.type == ChangeType.MODIFIED:
                    verified = bool(change.before_hash and change.after_hash)
                    verification.append({
                        "asset_path": change.asset_path,
                        "before_hash_present": bool(change.before_hash),
                        "after_hash_present": bool(change.after_hash),
                        "verification_available": verified,
                    })
            result["data"]["hash_verification"] = verification
        
        # Add rollback feasibility
        undoable_count = sum(1 for c in txn.changes if c.can_undo)
        result["data"]["rollback_feasibility"] = {
            "can_rollback": undoable_count == len(txn.changes) and txn.status == TransactionStatus.PENDING,
            "undoable_changes": undoable_count,
            "total_changes": len(txn.changes),
            "checkpoint_available": txn.checkpoint_id is not None,
        }
        
        return result
    
    except Exception as exc:
        return {
            "success": False,
            "error": "preview_failed",
            "message": f"Failed to generate preview: {exc!s}",
        }
