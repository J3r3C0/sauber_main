# Offgrid-Sheratan Integration Guide

## Current Status

### ✅ Integrated Components

| Component | Status | Location | Purpose |
|-----------|--------|----------|---------|
| Event Types | ✅ | `event_types.py` | Semantic event classification |
| Persistent Outbox | ✅ | `outbox.py` | Crash-safe replication queue |
| Compaction | ✅ | `main.py` (direct) | Micro-summaries via `memory/compact.py` |
| Retention | ✅ | `main.py` (direct) | Budget allocation via `memory/retention.py` |
| E2EE | ✅ | `offgrid_memory.py` | XChaCha20-Poly1305 encryption |
| Quorum | ✅ | `offgrid_memory.py` | Broker-based consensus |
| Memory Store | ✅ | Available | SQLite event store |
| Synopses | ✅ | Available | Bloom filters, Reservoir sampling |

### 🔧 Available but Not Integrated

#### Economy & Ledger
- `economy/txlog.py` - Transaction creation/signing
- `economy/wallet.py` - Balance management
- `economy/auto_settle_daemon.py` - Automatic settlement
- `ledger/local_dag.py` - DAG-based ledger
- `scripts/settle.py` - Manual settlement
- `scripts/send_tx.py` - Send transactions
- `scripts/finalize_tx.py` - Finalize transactions
- `scripts/settle_rewards.py` - Reward distribution
- `scripts/transfer.py` - Token transfers

#### Storage & Placement
- `storage/ec_encode.py` - Erasure coding (12/20)
- `placement/policy.py` - Data placement strategies
- `scripts/quorum_failover.py` - Failover logic

#### Security & Operations
- `scripts/rotate_keys.py` - Key rotation
- `scripts/smoke_test.py` - Integration tests
- `scripts/quorum_cli.py` - Quorum management CLI

---

## Integration Roadmap

### Phase 4: Economy Integration (Optional)

**Goal:** Track LCP action costs and create ledger transactions.

**Components:**
1. `economy/txlog.py` - Direct import
2. `ledger/local_dag.py` - Direct import

**Implementation:**
```python
# In lcp_actions.py or main.py
from economy.txlog import create_tx, sign_tx
from ledger.local_dag import LocalDAG

# After job completion
tx = create_tx(
    src="core-v2",
    dst="worker-host",
    amount=0.05,  # Cost for action
    fee=0.001,
    nonce=get_nonce(),
    meta={"job_id": job.id, "action": "read_file"}
)

# Sign and add to ledger
signature = sign_tx(tx, signing_key)
dag.append_block(tx)
```

**When to use:** If you want to track costs for LCP actions and maintain a local ledger.

---

### Phase 5: Erasure Coding (Optional)

**Goal:** Shard large data for resilience.

**Components:**
1. `storage/ec_encode.py` - Direct import

**Implementation:**
```python
from storage.ec_encode import ec_encode_file

# For large mission artifacts
ec_encode_file(
    input_path="./data/large_artifact.bin",
    output_dir="./data/shards/",
    k=12,  # Data shards
    n=20   # Total shards (can lose 8)
)
```

**When to use:** For large files (>10MB) that need high resilience.

---

### Phase 6: Placement Policies (Optional)

**Goal:** Smart data placement based on host capabilities.

**Components:**
1. `placement/policy.py` - Direct import

**Implementation:**
```python
from placement.policy import select_hosts_balanced

# When replicating data
hosts = select_hosts_balanced(
    available_hosts=["host-a", "host-b", "host-c"],
    required_count=3,
    placement_target="balanced"  # or "latency", "bandwidth"
)
```

**When to use:** When you have multiple hosts and want optimized placement.

---

### Phase 7: Auto-Settlement (Optional)

**Goal:** Automatic transaction settlement based on receipts.

**Components:**
1. `economy/auto_settle_daemon.py` - Background daemon

**Implementation:**
```python
# In main.py startup
from economy.auto_settle_daemon import run_auto_settle

# Start daemon
import threading
settle_thread = threading.Thread(
    target=run_auto_settle,
    args=(interval_seconds=3600,),  # Settle every hour
    daemon=True
)
settle_thread.start()
```

**When to use:** If you want automatic economic settlement without manual intervention.

---

### Phase 8: Failover & High Availability (Optional)

**Goal:** Automatic failover when hosts go down.

**Components:**
1. `scripts/quorum_failover.py` - Failover logic

**Implementation:**
```python
from scripts.quorum_failover import check_and_failover

# Periodically check quorum health
def _failover_worker():
    while True:
        time.sleep(300)  # Every 5 minutes
        check_and_failover(
            quorum_id="mission:abc123",
            broker_url="http://localhost:9000",
            available_hosts=["host-a", "host-b", "host-c"]
        )
```

**When to use:** For production deployments with high availability requirements.

---

## Quick Integration Template

For any Offgrid component:

```python
# 1. Ensure Offgrid path is in sys.path (already done in main.py)
import sys
from pathlib import Path
_offgrid_base = Path(__file__).parent.parent / "offgrid-net-v0.16.4-..."
sys.path.insert(0, str(_offgrid_base))

# 2. Direct import
from <module>.<component> import <function>

# 3. Use directly
result = <function>(...)
```

---

## Testing

### Smoke Test
```bash
cd offgrid-net-v0.16.4-with-memory-PRO-UI-POLICY-ROTATE
python scripts/smoke_test.py
```

### Quorum CLI
```bash
python scripts/quorum_cli.py create --id test123 --required 2.0
python scripts/quorum_cli.py ack --id test123 --node host-a
python scripts/quorum_cli.py status --id test123
```

### Transfer Test
```bash
python scripts/transfer.py --src core-v2 --dst host-a --amount 100
```

---

## Configuration

All components respect environment variables:

```bash
# Memory
OFFGRID_MEMORY_DB=./data/memory.db
OFFGRID_CHUNK_DIR=./data/chunks
OFFGRID_CHUNK_THRESHOLD=1048576  # 1MB

# Retention
OFFGRID_RETENTION_BASE_MB=128
OFFGRID_RETENTION_TOKEN_LEVEL=0

# Compaction
OFFGRID_COMPACTION_INTERVAL=1800  # 30 min
OFFGRID_SUMMARY_DIR=./data/summaries

# Economy
OFFGRID_SETTLEMENT_INTERVAL=3600  # 1 hour
```

---

## Summary

**Current Integration:** Core storage + Event-Types + Outbox + Compaction + Retention

**Available for Integration:** Economy, Ledger, Erasure Coding, Placement, Failover, Auto-Settlement

**All components are accessible** via direct imports. Integrate as needed based on your requirements.
