"""Rollback tool for reverting committed transactions and individual changes.

This tool provides rollback capabilities for transactions, with integration
to the checkpoint system for file-level restoration when needed.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.resources.transaction_state import (
    TransactionManager,
    TransactionStatus,
)


def _get_txn_manager() -> TransactionManager:
    return TransactionManager()


@mcp_for_unity_tool(
    group="transactions",
    unity_target=None,
    description=(
        "Rollback committed transactions and revert changes. "
        "Supports rolling back entire transactions (where all changes are undoable), "
        "using checkpoint restoration for file-level rollback, "
        "and partial rollback of specific change types. "
        "Integrates with manage_checkpoints for checkpoint-based restoration. "
        "Use get_rollback_summary first to assess rollback feasibility."
    ),
    annotations=ToolAnnotations(
        title="Rollback Changes",
        destructiveHint=True,
    ),
)
async def rollback_changes(
    ctx: Context,
    action: Annotated[
        Literal[
            "rollback_transaction",
            "rollback_to_checkpoint",
            "get_rollback_summary",
            "list_rollback_history",
        ],
        "Rollback action to perform",
    ],
    transaction_id: Annotated[
        str | None,
        "Transaction ID to rollback or summarize",
    ] = None,
    checkpoint_id: Annotated[
        str | None,
        "Checkpoint ID for checkpoint-based rollback",
    ] = None,
    change_types: Annotated[
        list[str] | str | None,
        "Filter by change types for partial rollback (created, modified, deleted, moved)",
    ] = None,
    dry_run: Annotated[
        bool | str | None,
        "Preview rollback without applying changes (default false)",
    ] = False,
) -> dict[str, Any]:
    """
    Rollback committed transactions and revert changes.
    
    This tool provides multiple rollback strategies:
    - rollback_transaction: Roll back an entire committed transaction
    - rollback_to_checkpoint: Restore files from a checkpoint
    - get_rollback_summary: Assess rollback feasibility before executing
    - list_rollback_history: View rollback history
    """
    await ctx.info(f"rollback_changes action={action}")
    
    manager = _get_txn_manager()
    
    # Parse dry_run
    dry_run_bool = False
    if isinstance(dry_run, str):
        dry_run_bool = dry_run.lower() in ("true", "1", "yes")
    elif isinstance(dry_run, bool):
        dry_run_bool = dry_run
    
    try:
        if action == "get_rollback_summary":
            if not transaction_id:
                return {
                    "success": False,
                    "error": "transaction_id_required",
                    "message": "get_rollback_summary requires a transaction_id",
                }
            
            txn = manager.get_transaction(transaction_id)
            if txn is None:
                return {
                    "success": False,
                    "error": "transaction_not_found",
                    "message": f"Transaction not found: {transaction_id}",
                }
            
            # Calculate rollback feasibility
            undoable = [c for c in txn.changes if c.can_undo]
            non_undoable = [c for c in txn.changes if not c.can_undo]
            
            created = [c for c in txn.changes if c.type.value == "created"]
            modified = [c for c in txn.changes if c.type.value == "modified"]
            deleted = [c for c in txn.changes if c.type.value == "deleted"]
            
            return {
                "success": True,
                "data": {
                    "transaction_id": txn.transaction_id,
                    "name": txn.name,
                    "status": txn.status.value,
                    "can_rollback_fully": len(undoable) == len(txn.changes),
                    "rollbackable_changes": len(undoable),
                    "non_rollbackable_changes": len(non_undoable),
                    "checkpoint_available": txn.checkpoint_id is not None,
                    "checkpoint_id": txn.checkpoint_id,
                    "changes_summary": {
                        "created": len(created),
                        "modified": len(modified),
                        "deleted": len(deleted),
                        "total": len(txn.changes),
                    },
                    "non_undoable_details": [
                        {
                            "asset_path": c.asset_path,
                            "type": c.type.value,
                            "description": c.description,
                        }
                        for c in non_undoable
                    ],
                    "recommendations": _generate_rollback_recommendations(
                        txn, len(undoable) == len(txn.changes)
                    ),
                },
            }
        
        elif action == "rollback_transaction":
            if not transaction_id:
                return {
                    "success": False,
                    "error": "transaction_id_required",
                    "message": "rollback_transaction requires a transaction_id",
                }
            
            txn = manager.get_transaction(transaction_id)
            if txn is None:
                return {
                    "success": False,
                    "error": "transaction_not_found",
                    "message": f"Transaction not found: {transaction_id}",
                }
            
            # Check if rollback is possible
            undoable = [c for c in txn.changes if c.can_undo]
            if len(undoable) != len(txn.changes):
                non_undoable = [c for c in txn.changes if not c.can_undo]
                return {
                    "success": False,
                    "error": "non_undoable_changes",
                    "message": f"Transaction contains {len(non_undoable)} changes that cannot be undone",
                    "data": {
                        "non_undoable": [
                            {"asset_path": c.asset_path, "type": c.type.value}
                            for c in non_undoable
                        ],
                    },
                }
            
            if txn.status != TransactionStatus.COMMITTED:
                return {
                    "success": False,
                    "error": "invalid_transaction_status",
                    "message": f"Cannot rollback transaction with status: {txn.status.value}",
                }
            
            if dry_run_bool:
                return {
                    "success": True,
                    "message": f"Rollback preview for transaction: {txn.name}",
                    "data": {
                        "dry_run": True,
                        "transaction_id": transaction_id,
                        "changes_to_rollback": len(txn.changes),
                        "affected_assets": [c.asset_path for c in txn.changes],
                    },
                }
            
            # Execute rollback
            txn = manager.rollback_transaction(transaction_id)
            
            return {
                "success": True,
                "message": f"Rolled back transaction: {txn.name}",
                "data": {
                    "transaction_id": txn.transaction_id,
                    "name": txn.name,
                    "status": txn.status.value,
                    "rolled_back_at": txn.completed_at.isoformat() if txn.completed_at else None,
                    "changes_rolled_back": len(txn.changes),
                },
            }
        
        elif action == "rollback_to_checkpoint":
            if not checkpoint_id:
                return {
                    "success": False,
                    "error": "checkpoint_id_required",
                    "message": "rollback_to_checkpoint requires a checkpoint_id from manage_checkpoints",
                }
            
            if dry_run_bool:
                return {
                    "success": True,
                    "message": f"Checkpoint rollback preview: {checkpoint_id}",
                    "data": {
                        "dry_run": True,
                        "checkpoint_id": checkpoint_id,
                        "note": "Use manage_checkpoints with action=restore to execute",
                    },
                }
            
            # This action delegates to manage_checkpoints
            # Return instructions for using manage_checkpoints
            return {
                "success": True,
                "message": "Use manage_checkpoints to restore from checkpoint",
                "data": {
                    "checkpoint_id": checkpoint_id,
                    "instructions": "Call manage_checkpoints with action='restore' and the checkpoint_id",
                    "delegation": "manage_checkpoints",
                },
            }
        
        elif action == "list_rollback_history":
            # List rolled back transactions
            rolled_back = [
                txn for txn in manager._transactions.values()
                if txn.status == TransactionStatus.ROLLED_BACK
            ]
            
            # Sort by completed_at descending
            rolled_back.sort(
                key=lambda t: t.completed_at or t.started_at,
                reverse=True
            )
            
            return {
                "success": True,
                "data": {
                    "count": len(rolled_back),
                    "transactions": [
                        {
                            "transaction_id": t.transaction_id,
                            "name": t.name,
                            "rolled_back_at": t.completed_at.isoformat() if t.completed_at else None,
                            "change_count": len(t.changes),
                        }
                        for t in rolled_back[:50]  # Limit to recent 50
                    ],
                },
            }
        
        else:
            return {
                "success": False,
                "error": "unsupported_action",
                "message": f"Unsupported action: {action}",
            }
    
    except ValueError as exc:
        return {
            "success": False,
            "error": "rollback_error",
            "message": str(exc),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": "rollback_operation_failed",
            "message": f"Rollback operation failed: {exc!s}",
        }


def _generate_rollback_recommendations(
    txn: Any,
    fully_undoable: bool,
) -> list[str]:
    """Generate rollback recommendations based on transaction state."""
    recommendations = []
    
    if txn.status == TransactionStatus.PENDING:
        recommendations.append("Transaction is still pending - changes have not been committed yet")
        return recommendations
    
    if txn.status != TransactionStatus.COMMITTED:
        recommendations.append(f"Transaction status is {txn.status.value} - cannot rollback")
        return recommendations
    
    if fully_undoable:
        recommendations.append("Transaction can be fully rolled back")
    else:
        recommendations.append("Transaction contains non-undoable changes")
        
        # Check for deletions
        has_deletions = any(c.type.value == "deleted" for c in txn.changes)
        if has_deletions:
            if txn.checkpoint_id:
                recommendations.append(
                    "Deletions detected - use checkpoint rollback for file restoration"
                )
            else:
                recommendations.append(
                    "Deletions detected without checkpoint - files cannot be restored"
                )
    
    if txn.checkpoint_id:
        recommendations.append(
            f"Checkpoint {txn.checkpoint_id} available for file-level rollback"
        )
    
    return recommendations
