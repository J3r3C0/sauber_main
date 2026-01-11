"""
Core ledger module - Internal logic for account and transfer management.

This module provides the low-level state management for the mesh fake ledger,
including JSON persistence, account operations, and transfer validation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Optional
from uuid import uuid4
from core.utils.atomic_io import atomic_write_json


class Account(TypedDict):
    """Account data structure."""
    balance: float
    created_at: str
    meta: dict


class TransferRecord(TypedDict):
    """Transfer record data structure."""
    id: str
    timestamp: str
    from_account: str
    to_account: str
    amount: float
    job_id: Optional[str]
    note: Optional[str]


class LedgerState(TypedDict):
    """Complete ledger state structure."""
    accounts: dict[str, Account]
    transfers: list[TransferRecord]


class LedgerError(Exception):
    """Base exception for ledger errors."""
    pass


class AccountNotFoundError(LedgerError):
    """Raised when an account does not exist."""
    pass


class InsufficientBalanceError(LedgerError):
    """Raised when an account has insufficient balance for a transfer."""
    pass


def create_empty_state() -> LedgerState:
    """Create a new empty ledger state."""
    return {
        "accounts": {},
        "transfers": []
    }


def load_state(path: Path) -> LedgerState:
    """
    Load ledger state from a JSON file.
    
    Args:
        path: Path to the JSON file
        
    Returns:
        LedgerState loaded from file, or empty state if file doesn't exist
    """
    if not path.exists():
        return create_empty_state()
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise LedgerError(f"Failed to parse ledger file: {e}")


def save_state(state: LedgerState, path: Path) -> None:
    """
    Save ledger state to a JSON file atomically.
    
    Args:
        state: Ledger state to save
        path: Path to the JSON file
    """
    atomic_write_json(str(path), state)


def ensure_account(
    state: LedgerState,
    account_id: str,
    initial_balance: float = 0
) -> bool:
    """
    Ensure an account exists, creating it if necessary.
    
    Args:
        state: Ledger state
        account_id: Account identifier
        initial_balance: Initial balance for new accounts (default: 0)
    
    Returns:
        True if account was created, False otherwise.
    """
    if account_id not in state["accounts"]:
        state["accounts"][account_id] = {
            "balance": initial_balance,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "meta": {}
        }
        return True
    return False


def get_balance(state: LedgerState, account_id: str) -> float:
    """
    Get the balance of an account.
    
    Args:
        state: Ledger state
        account_id: Account identifier
        
    Returns:
        Account balance
        
    Raises:
        AccountNotFoundError: If account doesn't exist
    """
    if account_id not in state["accounts"]:
        raise AccountNotFoundError(f"Account '{account_id}' does not exist")
    
    return state["accounts"][account_id]["balance"]


def can_pay(state: LedgerState, payer_id: str, amount: float) -> bool:
    """
    Check if an account can pay the specified amount.
    
    Args:
        state: Ledger state
        payer_id: Payer account identifier
        amount: Amount to check
        
    Returns:
        True if payer has sufficient balance, False otherwise
    """
    try:
        balance = get_balance(state, payer_id)
        return balance >= amount
    except AccountNotFoundError:
        return False


def transfer(
    state: LedgerState,
    payer_id: str,
    receiver_id: str,
    amount: float,
    job_id: Optional[str] = None,
    note: Optional[str] = None
) -> TransferRecord:
    """
    Execute a transfer between two accounts.
    
    Args:
        state: Ledger state
        payer_id: Payer account identifier
        receiver_id: Receiver account identifier
        amount: Amount to transfer
        job_id: Optional job identifier
        note: Optional transfer note
        
    Returns:
        TransferRecord of the completed transfer
        
    Raises:
        AccountNotFoundError: If either account doesn't exist
        InsufficientBalanceError: If payer has insufficient balance
        ValueError: If amount is not positive
    """
    if amount <= 0:
        raise ValueError("Transfer amount must be positive")
    
    # Validate accounts exist
    if payer_id not in state["accounts"]:
        raise AccountNotFoundError(f"Payer account '{payer_id}' does not exist")
    if receiver_id not in state["accounts"]:
        raise AccountNotFoundError(f"Receiver account '{receiver_id}' does not exist")
    
    # Validate sufficient balance
    payer_balance = state["accounts"][payer_id]["balance"]
    if payer_balance < amount:
        raise InsufficientBalanceError(
            f"Insufficient balance: {payer_id} has {payer_balance}, needs {amount}"
        )
    
    # Execute transfer
    state["accounts"][payer_id]["balance"] -= amount
    state["accounts"][receiver_id]["balance"] += amount
    
    # Create transfer record
    record: TransferRecord = {
        "id": str(uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "from_account": payer_id,
        "to_account": receiver_id,
        "amount": amount,
        "job_id": job_id,
        "note": note
    }
    
    # Append to transfer history
    state["transfers"].append(record)
    
    return record


def get_transfers(
    state: LedgerState,
    account_id: Optional[str] = None,
    limit: Optional[int] = None
) -> list[TransferRecord]:
    """
    Get transfer history, optionally filtered by account.
    
    Args:
        state: Ledger state
        account_id: Optional account to filter by (shows transfers where account is sender or receiver)
        limit: Optional limit on number of records to return (most recent first)
        
    Returns:
        List of transfer records, newest first
    """
    transfers = state["transfers"]
    
    # Filter by account if specified
    if account_id:
        transfers = [
            t for t in transfers
            if t["from_account"] == account_id or t["to_account"] == account_id
        ]
    
    # Reverse to get newest first
    transfers = list(reversed(transfers))
    
    # Apply limit if specified
    if limit is not None:
        transfers = transfers[:limit]
    
    return transfers
