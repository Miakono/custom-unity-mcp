"""Transaction state management for multi-step editor workflows.

This module provides in-memory transaction tracking with optional disk persistence.
Transactions are grouped collections of actions that can be previewed, committed,
or rolled back atomically.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4


class ChangeType(str, Enum):
    """Types of changes that can be recorded in a transaction."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"
    FAILED = "failed"


class TransactionStatus(str, Enum):
    """Possible states for a transaction."""
    PENDING = "pending"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class ChangeRecord:
    """A single change record within a transaction.
    
    Attributes:
        type: The type of change (created, modified, deleted, moved, failed)
        asset_path: The Unity asset path affected by this change
        description: Human-readable description of the change
        before_hash: Hash of the asset state before the change (for verification)
        after_hash: Hash of the asset state after the change
        can_undo: Whether this change type supports rollback
        action_params: Optional serialized action parameters for replay/undo
    """
    type: ChangeType
    asset_path: str
    description: str
    before_hash: str = ""
    after_hash: str = ""
    can_undo: bool = True
    action_params: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "asset_path": self.asset_path,
            "description": self.description,
            "before_hash": self.before_hash,
            "after_hash": self.after_hash,
            "can_undo": self.can_undo,
            "action_params": self.action_params,
        }


@dataclass
class Transaction:
    """A named transaction containing multiple change records.
    
    Attributes:
        transaction_id: Unique identifier for this transaction
        name: Human-readable name for the transaction
        status: Current status of the transaction
        changes: List of change records in this transaction
        started_at: When the transaction was started
        completed_at: When the transaction was completed (committed/rolled back)
        checkpoint_id: Optional reference to a file checkpoint for rollback support
        metadata: Additional metadata for the transaction
    """
    transaction_id: str
    name: str
    status: TransactionStatus = field(default=TransactionStatus.PENDING)
    changes: list[ChangeRecord] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    checkpoint_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "name": self.name,
            "status": self.status.value,
            "changes": [c.to_dict() for c in self.changes],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "checkpoint_id": self.checkpoint_id,
            "metadata": self.metadata,
        }
    
    def add_change(self, change: ChangeRecord) -> None:
        """Add a change record to this transaction."""
        if self.status != TransactionStatus.PENDING:
            raise ValueError(f"Cannot add changes to a {self.status.value} transaction")
        self.changes.append(change)
    
    def commit(self) -> None:
        """Mark the transaction as committed."""
        self.status = TransactionStatus.COMMITTED
        self.completed_at = datetime.now(timezone.utc)
    
    def rollback(self) -> None:
        """Mark the transaction as rolled back."""
        self.status = TransactionStatus.ROLLED_BACK
        self.completed_at = datetime.now(timezone.utc)
    
    def fail(self) -> None:
        """Mark the transaction as failed."""
        self.status = TransactionStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
    
    def get_summary(self) -> dict[str, Any]:
        """Get a summary of changes by category."""
        created = [c for c in self.changes if c.type == ChangeType.CREATED]
        modified = [c for c in self.changes if c.type == ChangeType.MODIFIED]
        deleted = [c for c in self.changes if c.type == ChangeType.DELETED]
        moved = [c for c in self.changes if c.type == ChangeType.MOVED]
        failed = [c for c in self.changes if c.type == ChangeType.FAILED]
        
        return {
            "transaction_id": self.transaction_id,
            "name": self.name,
            "status": self.status.value,
            "created_count": len(created),
            "modified_count": len(modified),
            "deleted_count": len(deleted),
            "moved_count": len(moved),
            "failed_count": len(failed),
            "total_changes": len(self.changes),
            "can_undo": all(c.can_undo for c in self.changes) and self.status == TransactionStatus.COMMITTED,
        }


class TransactionManager:
    """Manages active and historical transactions.
    
    This class provides thread-safe (within asyncio context) transaction
    management with optional disk persistence.
    """
    
    _instance: TransactionManager | None = None
    
    def __new__(cls) -> TransactionManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._transactions: dict[str, Transaction] = {}
        self._current_transaction_id: str | None = None
        self._persistence_dir: Path | None = None
    
    def set_persistence_dir(self, path: Path | str) -> None:
        """Set the directory for persisting transaction state to disk."""
        self._persistence_dir = Path(path)
        self._persistence_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_transaction_id(self, name: str) -> str:
        """Generate a unique transaction ID based on name and timestamp."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique = uuid4().hex[:8]
        safe_name = "".join(c if c.isalnum() else "_" for c in name.lower())[:32]
        return f"txn_{safe_name}_{timestamp}_{unique}"
    
    def begin_transaction(self, name: str, checkpoint_id: str | None = None) -> str:
        """Start a new transaction.
        
        Args:
            name: Human-readable name for the transaction
            checkpoint_id: Optional checkpoint ID for file-level rollback support
            
        Returns:
            The unique transaction ID
        """
        transaction_id = self.generate_transaction_id(name)
        transaction = Transaction(
            transaction_id=transaction_id,
            name=name,
            checkpoint_id=checkpoint_id,
        )
        self._transactions[transaction_id] = transaction
        self._current_transaction_id = transaction_id
        self._persist_transaction(transaction)
        return transaction_id
    
    def get_current_transaction(self) -> Transaction | None:
        """Get the currently active transaction, if any."""
        if self._current_transaction_id is None:
            return None
        txn = self._transactions.get(self._current_transaction_id)
        if txn and txn.status == TransactionStatus.PENDING:
            return txn
        return None
    
    def get_transaction(self, transaction_id: str) -> Transaction | None:
        """Get a transaction by ID."""
        return self._transactions.get(transaction_id)
    
    def append_action(
        self,
        transaction_id: str,
        change_type: ChangeType | str,
        asset_path: str,
        description: str,
        before_hash: str = "",
        after_hash: str = "",
        can_undo: bool = True,
        action_params: dict[str, Any] | None = None,
    ) -> ChangeRecord:
        """Append an action to a transaction.
        
        Args:
            transaction_id: The transaction to append to
            change_type: Type of change being recorded
            asset_path: Path to the affected asset
            description: Human-readable description
            before_hash: Hash of state before change
            after_hash: Hash of state after change
            can_undo: Whether this change supports rollback
            action_params: Serialized action parameters for potential replay
            
        Returns:
            The created ChangeRecord
        """
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise ValueError(f"Transaction not found: {transaction_id}")
        if txn.status != TransactionStatus.PENDING:
            raise ValueError(f"Cannot append to {txn.status.value} transaction")
        
        if isinstance(change_type, str):
            change_type = ChangeType(change_type)
        
        change = ChangeRecord(
            type=change_type,
            asset_path=asset_path,
            description=description,
            before_hash=before_hash,
            after_hash=after_hash,
            can_undo=can_undo,
            action_params=action_params or {},
        )
        txn.add_change(change)
        self._persist_transaction(txn)
        return change
    
    def commit_transaction(self, transaction_id: str) -> Transaction:
        """Commit a transaction and apply all changes atomically.
        
        Args:
            transaction_id: The transaction to commit
            
        Returns:
            The committed Transaction
        """
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise ValueError(f"Transaction not found: {transaction_id}")
        if txn.status != TransactionStatus.PENDING:
            raise ValueError(f"Cannot commit {txn.status.value} transaction")
        
        txn.commit()
        self._persist_transaction(txn)
        
        # Clear current transaction if this was it
        if self._current_transaction_id == transaction_id:
            self._current_transaction_id = None
        
        return txn
    
    def rollback_transaction(self, transaction_id: str) -> Transaction:
        """Rollback a committed transaction where possible.
        
        Args:
            transaction_id: The transaction to rollback
            
        Returns:
            The rolled back Transaction
        """
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise ValueError(f"Transaction not found: {transaction_id}")
        if txn.status != TransactionStatus.COMMITTED:
            raise ValueError(f"Cannot rollback {txn.status.value} transaction")
        
        # Check if all changes can be undone
        undoable_changes = [c for c in txn.changes if c.can_undo]
        if len(undoable_changes) != len(txn.changes):
            raise ValueError("Transaction contains changes that cannot be undone")
        
        txn.rollback()
        self._persist_transaction(txn)
        return txn
    
    def preview_transaction(self, transaction_id: str) -> dict[str, Any]:
        """Get a preview of changes in a transaction without applying.
        
        Args:
            transaction_id: The transaction to preview
            
        Returns:
            Dictionary with change summary
        """
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        return {
            "transaction_id": txn.transaction_id,
            "name": txn.name,
            "status": txn.status.value,
            "changes": [c.to_dict() for c in txn.changes],
            "summary": txn.get_summary(),
        }
    
    def list_transactions(
        self,
        status: TransactionStatus | str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List transactions with optional filtering.
        
        Args:
            status: Filter by status (optional)
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction summaries
        """
        if isinstance(status, str):
            status = TransactionStatus(status)
        
        transactions = list(self._transactions.values())
        transactions.sort(key=lambda t: t.started_at, reverse=True)
        
        if status:
            transactions = [t for t in transactions if t.status == status]
        
        return [t.get_summary() for t in transactions[:limit]]
    
    def get_transaction_state(self, transaction_id: str | None = None) -> dict[str, Any]:
        """Get the current transaction state.
        
        Args:
            transaction_id: Specific transaction ID, or None for current/active
            
        Returns:
            Dictionary with transaction state information
        """
        if transaction_id is None:
            transaction_id = self._current_transaction_id
        
        if transaction_id is None:
            return {
                "has_active_transaction": False,
                "active_transaction_id": None,
                "total_transactions": len(self._transactions),
            }
        
        txn = self._transactions.get(transaction_id)
        if txn is None:
            return {
                "has_active_transaction": False,
                "active_transaction_id": None,
                "error": f"Transaction {transaction_id} not found",
            }
        
        return {
            "has_active_transaction": txn.status == TransactionStatus.PENDING,
            "active_transaction_id": transaction_id if txn.status == TransactionStatus.PENDING else None,
            "transaction": txn.to_dict(),
            "summary": txn.get_summary(),
            "total_transactions": len(self._transactions),
        }
    
    def _persist_transaction(self, txn: Transaction) -> None:
        """Persist a transaction to disk if persistence is enabled."""
        if self._persistence_dir is None:
            return
        
        file_path = self._persistence_dir / f"{txn.transaction_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(txn.to_dict(), f, indent=2, default=str)
        except Exception:
            # Persistence is best-effort
            pass
    
    def load_persisted_transactions(self) -> int:
        """Load persisted transactions from disk.
        
        Returns:
            Number of transactions loaded
        """
        if self._persistence_dir is None:
            return 0
        
        count = 0
        for file_path in self._persistence_dir.glob("txn_*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                txn = Transaction(
                    transaction_id=data["transaction_id"],
                    name=data["name"],
                    status=TransactionStatus(data["status"]),
                    changes=[
                        ChangeRecord(
                            type=ChangeType(c["type"]),
                            asset_path=c["asset_path"],
                            description=c["description"],
                            before_hash=c.get("before_hash", ""),
                            after_hash=c.get("after_hash", ""),
                            can_undo=c.get("can_undo", True),
                            action_params=c.get("action_params", {}),
                        )
                        for c in data.get("changes", [])
                    ],
                    started_at=datetime.fromisoformat(data["started_at"]),
                    completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
                    checkpoint_id=data.get("checkpoint_id"),
                    metadata=data.get("metadata", {}),
                )
                self._transactions[txn.transaction_id] = txn
                count += 1
            except Exception:
                # Skip corrupted files
                continue
        
        return count


# Global singleton instance
transaction_manager = TransactionManager()


def compute_asset_hash(content: str | bytes) -> str:
    """Compute a SHA256 hash for asset content verification."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()[:16]
