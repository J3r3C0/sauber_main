"""Add balance to alice account"""
import sys
from pathlib import Path

root = Path(__file__).parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from mesh.registry.ledger_service import LedgerService, LedgerConfig

config = LedgerConfig()
ledger = LedgerService(config)

# Add 100k tokens to alice
ledger.credit("alice", 100000, reason="Initial balance for LLM jobs")
balance = ledger.get_balance("alice")
print(f"alice: {balance} TOK")
