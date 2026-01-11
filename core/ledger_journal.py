# core/ledger_journal.py
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Generator, Iterable, Optional, Tuple

from core.utils.atomic_io import atomic_append_jsonl, canonical_json_bytes, sha256_hex, json_lock

# -----------------------
# Defaults / file layout
# -----------------------
DEFAULT_JOURNAL_PATH = os.getenv("LEDGER_JOURNAL_PATH", "runtime/ledger_events.jsonl")
DEFAULT_DOMAIN_LOCK = os.getenv("LEDGER_DOMAIN_LOCK", "runtime/ledger_domain.lock")
DEFAULT_CURRENCY = os.getenv("LEDGER_CURRENCY", "TOK")

# Enable/disable hash-chain (recommended ON)
HASH_CHAIN_ENABLED = os.getenv("JOURNAL_HASH_CHAIN", "1") not in ("0", "false", "False", "no", "NO")


# -----------------------
# Helpers / schema
# -----------------------
def _now_ts() -> float:
    return time.time()


def _new_event_id() -> str:
    return str(uuid.uuid4())


def _require_decimal_string(amount: Any) -> str:
    """
    Enforce "amount" as decimal-string for determinism.
    Accepts str already, or numbers (converted conservatively).
    Prefer passing strings from callers.
    """
    if isinstance(amount, str):
        return amount.strip()
    return str(amount)


def _strip_hash_fields(ev: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(ev)
    out.pop("hash", None)
    out.pop("prev_hash", None)
    return out


def _compute_hash(prev_hash: str, ev_no_hash: Dict[str, Any]) -> str:
    payload = canonical_json_bytes(ev_no_hash) + prev_hash.encode("utf-8")
    return sha256_hex(payload)


def _read_last_hash_fast(journal_path: str) -> str:
    """
    Best-effort: read last non-empty line and return its "hash".
    Returns "GENESIS" if file missing/empty/no-hash.
    """
    if not os.path.exists(journal_path):
        return "GENESIS"

    try:
        with open(journal_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                return "GENESIS"

            # Read tail chunk
            chunk_size = min(8192, size)
            f.seek(-chunk_size, os.SEEK_END)
            tail = f.read(chunk_size)

        # Split lines, find last non-empty
        lines = [ln for ln in tail.split(b"\n") if ln.strip()]
        if not lines:
            return "GENESIS"

        last_line = lines[-1].decode("utf-8", errors="replace")
        last = json.loads(last_line)
        return str(last.get("hash") or "GENESIS")
    except Exception:
        return "GENESIS"


# -----------------------
# Public API
# -----------------------
@dataclass(frozen=True)
class LedgerEvent:
    raw: Dict[str, Any]

    @property
    def event_id(self) -> str:
        return str(self.raw.get("event_id", ""))

    @property
    def ts(self) -> float:
        return float(self.raw.get("ts", 0.0))

    @property
    def type(self) -> str:
        return str(self.raw.get("type", ""))

    @property
    def hash(self) -> str:
        return str(self.raw.get("hash", ""))

    @property
    def prev_hash(self) -> str:
        return str(self.raw.get("prev_hash", ""))


def append_event(
    event: Dict[str, Any],
    *,
    journal_path: str = DEFAULT_JOURNAL_PATH,
    domain_lock: str = DEFAULT_DOMAIN_LOCK,
    lock: bool = True,
) -> Dict[str, Any]:
    """
    Append a ledger event to the append-only journal, optionally hash-chained.
    """
    os.makedirs(os.path.dirname(journal_path) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(domain_lock) or ".", exist_ok=True)

    # Normalize/complete required fields
    ev: Dict[str, Any] = dict(event)
    ev.setdefault("schema", "ledger_event.v1")
    ev.setdefault("event_id", _new_event_id())
    ev.setdefault("ts", _now_ts())
    ev.setdefault("currency", DEFAULT_CURRENCY)

    if "amount" in ev:
        ev["amount"] = _require_decimal_string(ev["amount"])

    def _do_append():
        prev_hash = "GENESIS"
        if HASH_CHAIN_ENABLED:
            prev_hash = _read_last_hash_fast(journal_path)

        # Fill hash fields deterministically
        if HASH_CHAIN_ENABLED:
            ev_no_hash = _strip_hash_fields(ev)
            ev["prev_hash"] = prev_hash
            ev["hash"] = _compute_hash(prev_hash, ev_no_hash)
        else:
            ev.pop("prev_hash", None)
            ev.pop("hash", None)

        # Append one-line JSON with fsync durability
        atomic_append_jsonl(journal_path, ev, timeout=10.0)

    # Domain lock ensures strict ordering across journal+state writes.
    if lock:
        with json_lock(domain_lock, timeout=10.0):
            _do_append()
    else:
        _do_append()

    return ev


def read_events(journal_path: str = DEFAULT_JOURNAL_PATH) -> Generator[LedgerEvent, None, None]:
    """
    Stream events from journal in file order. Skips empty lines.
    """
    if not os.path.exists(journal_path):
        return

    with open(journal_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            yield LedgerEvent(raw=raw)


def verify_chain(journal_path: str = DEFAULT_JOURNAL_PATH) -> Tuple[bool, Dict[str, Any]]:
    """
    Verify hash-chain integrity of ledger_events.jsonl.
    """
    if not os.path.exists(journal_path):
        return True, {"status": "ok", "reason": "journal_missing_or_empty"}

    if os.path.getsize(journal_path) == 0:
        return True, {"status": "ok", "reason": "journal_missing_or_empty"}

    prev = "GENESIS"
    idx = 0
    try:
        for idx, ev in enumerate(read_events(journal_path), start=1):
            raw = ev.raw
            if "hash" not in raw or "prev_hash" not in raw:
                return False, {
                    "status": "error",
                    "reason": "missing_hash_fields",
                    "at_line": idx,
                }

            if raw["prev_hash"] != prev:
                return False, {
                    "status": "error",
                    "reason": "prev_hash_mismatch",
                    "at_line": idx,
                    "expected_prev_hash": prev,
                    "found_prev_hash": raw["prev_hash"],
                }

            expected = _compute_hash(prev, _strip_hash_fields(raw))
            if raw["hash"] != expected:
                return False, {
                    "status": "error",
                    "reason": "hash_mismatch",
                    "at_line": idx,
                    "expected_hash": expected,
                    "found_hash": raw["hash"],
                }

            prev = raw["hash"]

        return True, {"status": "ok", "events": idx, "last_hash": prev}
    except json.JSONDecodeError as e:
        return False, {"status": "error", "reason": "json_decode_error", "at_line": idx, "error": str(e)}
    except Exception as e:
        return False, {"status": "error", "reason": "unexpected_error", "at_line": idx, "error": str(e)}


def replay(
    journal_path: str = DEFAULT_JOURNAL_PATH,
    *,
    initial_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Deterministically reconstruct ledger state from journal events.
    """
    state = dict(initial_state) if initial_state else {}
    balances = state.setdefault("balances", {})
    state["total_events"] = 0
    state["last_event_ts"] = 0.0

    def _add(account: str, delta: float) -> None:
        balances[account] = float(balances.get(account, 0.0)) + float(delta)

    for ev in read_events(journal_path):
        raw = ev.raw
        et = str(raw.get("type", ""))
        account = str(raw.get("account", ""))
        to_account = str(raw.get("to_account", ""))
        amount_str = raw.get("amount", "0")
        try:
            amount = float(amount_str)
        except Exception:
            amount = float(str(amount_str))

        if to_account:
            # Double-entry move
            _add(account, -amount)
            _add(to_account, +amount)
        elif et == "credit":
            _add(account, +amount)
        elif et == "debit":
            _add(account, -amount)
        elif et == "charge":
            _add(account, -amount)
        elif et == "adjust":
            _add(account, amount)
        elif et == "reconcile":
            pass
        elif et == "transfer" and not to_account:
            # Transfer without to_account is treated as a debit
            _add(account, -amount)
        else:
            # Keep unknown types for extensibility but log or warn if needed
            pass

        state["total_events"] += 1
        state["last_event_ts"] = float(raw.get("ts", state["last_event_ts"]))

    return state

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Ledger Journal Tools (v1)")
    p.add_argument("cmd", choices=["verify", "replay"])
    p.add_argument("--journal", default=DEFAULT_JOURNAL_PATH)
    p.add_argument("--out", default="runtime/replayed_ledger.json")
    args = p.parse_args()

    if args.cmd == "verify":
        ok, details = verify_chain(args.journal)
        # Use simple print for CLI
        print(json.dumps({"ok": ok, **details}, indent=2, ensure_ascii=False))
        import sys
        sys.exit(0 if ok else 2)

    if args.cmd == "replay":
        st = replay(args.journal)
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2, ensure_ascii=False, sort_keys=True)
        print(f"Wrote replayed state to {args.out}")
