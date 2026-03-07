"""Transaction management tool for multi-step editor workflows.

This tool provides primitives for grouping multiple actions into atomic
transactions with preview, commit, and rollback capabilities.
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
    compute_asset_hash,
)
from services.tools.utils import parse_json_payload, coerce_bool


# Get the global transaction manager instance
def _get_txn_manager() -> TransactionManager:
    return TransactionManager()


def _get_context_transaction_id(ctx: Context) -> str | None:
    return getattr(ctx, "_copilot_transaction_id", None)


def _set_context_transaction_id(ctx: Context, transaction_id: str | None) -> None:
    setattr(ctx, "_copilot_transaction_id", transaction_id)


@mcp_for_unity_tool(
    unity_target=None,
    group="transactions",
    description=(
        "Manage multi-step editor transactions with rollback capability. "
        "Use this tool to group related actions into atomic units that can be "
        "previewed before commit and rolled back if needed. "
        "Actions: begin_transaction (start a named transaction), "
        "append_action (add a change to current transaction), "
        "preview_transaction (see all pending changes without applying), "
        "commit_transaction (apply all actions atomically), "
        "get_transaction_state (check current transaction status), "
        "list_transactions (view historical transactions), "
        "rollback_transaction (undo a committed transaction where possible). "
        "Integrates with manage_checkpoints for file-level rollback support."
    ),
    annotations=ToolAnnotations(
        title="Manage Transactions",
        destructiveHint=True,
    ),
)
async def manage_transactions(
    ctx: Context,
    action: Annotated[
        Literal[
            "begin_transaction",
            "append_action",
            "preview_transaction",
            "commit_transaction",
            "get_transaction_state",
            "list_transactions",
            "rollback_transaction",
        ],
        "Transaction action to perform",
    ],
    name: Annotated[
        str | None,
        "Name for the transaction (required for begin_transaction)",
    ] = None,
    transaction_id: Annotated[
        str | None,
        "Transaction ID (optional - uses current transaction if not specified)",
    ] = None,
    change_type: Annotated[
        Literal["created", "modified", "deleted", "moved", "failed"] | None,
        "Type of change for append_action",
    ] = None,
    asset_path: Annotated[
        str | None,
        "Unity asset path affected by the change",
    ] = None,
    description: Annotated[
        str | None,
        "Human-readable description of the change",
    ] = None,
    before_hash: Annotated[
        str | None,
        "Hash of asset state before change (optional, for verification)",
    ] = None,
    after_hash: Annotated[
        str | None,
        "Hash of asset state after change (optional, for verification)",
    ] = None,
    can_undo: Annotated[
        bool | str | None,
        "Whether this change supports rollback (default true)",
    ] = True,
    action_params: Annotated[
        dict[str, Any] | str | None,
        "Serialized action parameters for potential replay (JSON object or dict)",
    ] = None,
    checkpoint_id: Annotated[
        str | None,
        "Optional checkpoint ID from manage_checkpoints for file rollback support",
    ] = None,
    status_filter: Annotated[
        Literal["pending", "committed", "rolled_back", "failed"] | None,
        "Filter transactions by status (for list_transactions)",
    ] = None,
    limit: Annotated[
        int | str | None,
        "Maximum number of transactions to list (default 100)",
    ] = 100,
) -> dict[str, Any]:
    """
    Manage multi-step editor transactions with rollback capability.
    """
    await ctx.info(f"manage_transactions action={action}")
    
    manager = _get_txn_manager()
    can_undo = coerce_bool(can_undo, default=True)
    
    # Parse action_params if it's a string
    parsed_action_params: dict[str, Any] | None = None
    if action_params is not None:
        if isinstance(action_params, str):
            parsed = parse_json_payload(action_params)
            if isinstance(parsed, dict):
                parsed_action_params = parsed
            else:
                return {
                    "success": False,
                    "error": "invalid_action_params",
                    "message": "action_params must be a JSON object or dict",
                }
        elif isinstance(action_params, dict):
            parsed_action_params = action_params
        else:
            return {
                "success": False,
                "error": "invalid_action_params",
                "message": "action_params must be a JSON object or dict",
            }
    
    try:
        if action == "begin_transaction":
            if not name:
                return {
                    "success": False,
                    "error": "name_required",
                    "message": "begin_transaction requires a 'name' parameter",
                }
            
            txn_id = manager.begin_transaction(name, checkpoint_id=checkpoint_id)
            _set_context_transaction_id(ctx, txn_id)
            return {
                "success": True,
                "message": f"Started transaction: {name}",
                "data": {
                    "transaction_id": txn_id,
                    "name": name,
                    "status": "pending",
                    "checkpoint_id": checkpoint_id,
                },
            }
        
        elif action == "append_action":
            # Use current transaction if not specified
            target_txn_id = transaction_id or _get_context_transaction_id(ctx)
            if target_txn_id is None:
                return {
                    "success": False,
                    "error": "no_active_transaction",
                    "message": "No active transaction. Start one with begin_transaction or specify transaction_id.",
                }
            target_txn = manager.get_transaction(target_txn_id)
            if target_txn is None or target_txn.status != TransactionStatus.PENDING:
                if transaction_id is None:
                    _set_context_transaction_id(ctx, None)
                return {
                    "success": False,
                    "error": "no_active_transaction",
                    "message": "No active transaction. Start one with begin_transaction or specify transaction_id.",
                }
            
            if not change_type:
                return {
                    "success": False,
                    "error": "change_type_required",
                    "message": "append_action requires a 'change_type' parameter",
                }
            
            if not asset_path:
                return {
                    "success": False,
                    "error": "asset_path_required",
                    "message": "append_action requires an 'asset_path' parameter",
                }
            
            if not description:
                return {
                    "success": False,
                    "error": "description_required",
                    "message": "append_action requires a 'description' parameter",
                }
            
            change = manager.append_action(
                transaction_id=target_txn_id,
                change_type=change_type,
                asset_path=asset_path,
                description=description,
                before_hash=before_hash or "",
                after_hash=after_hash or "",
                can_undo=can_undo if isinstance(can_undo, bool) else True,
                action_params=parsed_action_params,
            )
            
            return {
                "success": True,
                "message": f"Added {change_type} action for {asset_path}",
                "data": {
                    "transaction_id": target_txn_id,
                    "change": change.to_dict(),
                },
            }
        
        elif action == "preview_transaction":
            target_txn_id = transaction_id or _get_context_transaction_id(ctx)
            if target_txn_id is None:
                return {
                    "success": False,
                    "error": "no_active_transaction",
                    "message": "No active transaction to preview. Specify transaction_id.",
                }
            target_txn = manager.get_transaction(target_txn_id)
            if target_txn is None or target_txn.status != TransactionStatus.PENDING:
                if transaction_id is None:
                    _set_context_transaction_id(ctx, None)
                return {
                    "success": False,
                    "error": "no_active_transaction",
                    "message": "No active transaction to preview. Specify transaction_id.",
                }
            
            preview = manager.preview_transaction(target_txn_id)
            return {
                "success": True,
                "message": f"Transaction preview: {preview['name']}",
                "data": preview,
            }
        
        elif action == "commit_transaction":
            target_txn_id = transaction_id or _get_context_transaction_id(ctx)
            if target_txn_id is None:
                return {
                    "success": False,
                    "error": "no_active_transaction",
                    "message": "No active transaction to commit. Specify transaction_id.",
                }
            target_txn = manager.get_transaction(target_txn_id)
            if target_txn is None or target_txn.status != TransactionStatus.PENDING:
                if transaction_id is None:
                    _set_context_transaction_id(ctx, None)
                return {
                    "success": False,
                    "error": "no_active_transaction",
                    "message": "No active transaction to commit. Specify transaction_id.",
                }
            
            txn = manager.commit_transaction(target_txn_id)
            if _get_context_transaction_id(ctx) == target_txn_id:
                _set_context_transaction_id(ctx, None)
            summary = txn.get_summary()
            
            return {
                "success": True,
                "message": f"Committed transaction: {txn.name} ({summary['total_changes']} changes)",
                "data": {
                    "transaction_id": txn.transaction_id,
                    "name": txn.name,
                    "status": txn.status.value,
                    "summary": summary,
                    "changes": [c.to_dict() for c in txn.changes],
                },
            }
        
        elif action == "rollback_transaction":
            if not transaction_id:
                return {
                    "success": False,
                    "error": "transaction_id_required",
                    "message": "rollback_transaction requires a 'transaction_id' parameter",
                }
            
            txn = manager.rollback_transaction(transaction_id)
            
            return {
                "success": True,
                "message": f"Rolled back transaction: {txn.name}",
                "data": {
                    "transaction_id": txn.transaction_id,
                    "name": txn.name,
                    "status": txn.status.value,
                },
            }
        
        elif action == "get_transaction_state":
            state = manager.get_transaction_state(transaction_id)
            return {
                "success": True,
                "data": state,
            }
        
        elif action == "list_transactions":
            txns = manager.list_transactions(
                status=status_filter,
                limit=int(limit) if limit else 100,
            )
            return {
                "success": True,
                "data": {
                    "count": len(txns),
                    "transactions": txns,
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
            "error": "transaction_error",
            "message": str(exc),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": "transaction_operation_failed",
            "message": f"Transaction operation failed: {exc!s}",
        }
