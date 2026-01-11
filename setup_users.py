"""
Quick-Fix: Create user accounts with initial balance
"""
import sys
from pathlib import Path

root = Path(__file__).parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from mesh.registry.ledger_service import LedgerService, LedgerConfig

def setup_users():
    """Create default users with initial balance."""
    config = LedgerConfig()
    ledger = LedgerService(config)
    
    print("Setting up user accounts...")

    # Create users with initial balance
    users = [
        ("default_user", 20000),
        ("test_user", 20000),
        ("mobile_user", 20000),
        ("alice", 50000),  # For LLM jobs (cost 30 TOK)
    ]

    for user_id, balance in users:
        try:
            ledger.credit(user_id, balance, reason="Initial balance")
            current = ledger.get_balance(user_id)
            print(f"  ✅ {user_id}: {current} TOK")
        except Exception as e:
            print(f"  ❌ {user_id}: {e}")
    
    print("\nDone! Users can now dispatch jobs.")

if __name__ == "__main__":
    setup_users()
