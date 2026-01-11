# reconciliation_report.py
import sys
import json
from pathlib import Path
from decimal import Decimal
from typing import Dict, List, Any

# Add root to sys.path
root = Path(__file__).parent.parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.ledger_journal import read_events

def run_reconciliation(journal_path: str):
    """Audits the ledger journal and reports on settlement flows."""
    print(f"--- Sheratan Ledger Reconciliation Report ---")
    print(f"Source: {journal_path}\n")

    if not Path(journal_path).exists():
        print("Error: Journal not found.")
        return

    stats = {
        "total_events": 0,
        "total_payouts": Decimal("0"),
        "total_revenue": Decimal("0"), # Operator profit
        "user_costs": Decimal("0"),
        "anomalies": [],
        "worker_earnings": {} # worker_id -> earnings
    }

    # Tracking job_ids to match charge -> transfer
    job_map: Dict[str, Dict[str, Any]] = {}

    for ev in read_events(journal_path):
        stats["total_events"] += 1
        raw = ev.raw
        etype = raw.get("type")
        amount = Decimal(str(raw.get("amount", "0")))
        jid = raw.get("job_id")
        worker_id = raw.get("worker_id", "unknown")

        if etype == "charge":
            # Payer -> Operator
            stats["user_costs"] += amount
            if jid:
                job_map[jid] = {"charged": amount, "worker_id": worker_id}
        
        elif etype == "transfer":
            # Usually Operator -> Worker
            stats["total_payouts"] += amount
            if worker_id not in stats["worker_earnings"]:
                stats["worker_earnings"][worker_id] = Decimal("0")
            stats["worker_earnings"][worker_id] += amount
            
            if jid and jid in job_map:
                job_map[jid]["payout"] = amount
                # Revenue = Charge - Payout
                stats["total_revenue"] += (job_map[jid]["charged"] - amount)

    print(f"Summary Statistics:")
    print(f"  Total Events:      {stats['total_events']}")
    print(f"  Total User Costs:  {stats['user_costs']:>12.4f} TOK")
    print(f"  Total Payouts:     {stats['total_payouts']:>12.4f} TOK")
    print(f"  Operator Revenue:  {stats['total_revenue']:>12.4f} TOK")
    
    # Margin health
    if stats["user_costs"] > 0:
        avg_margin = (stats["total_revenue"] / stats["user_costs"]) * 100
        print(f"  Avg. Margin:       {avg_margin:>11.1f}%")

    print(f"\nWorker Breakdown:")
    for wid, earnings in sorted(stats["worker_earnings"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {wid[:20]:<20}: {earnings:>12.4f} TOK")

    # Anomaly Check
    unsettled = [jid for jid, data in job_map.items() if "payout" not in data]
    if unsettled:
        print(f"\n⚠️ Potential Anomalies:")
        print(f"  Unsettled Charges: {len(unsettled)} (Jobs charged but no worker payout seen)")
        for jid in unsettled[:5]:
            print(f"    - {jid}")

    print("\n--- End of Report ---")

if __name__ == "__main__":
    jpath = "ledger_events.jsonl"
    if len(sys.argv) > 1:
        jpath = sys.argv[1]
    run_reconciliation(jpath)
