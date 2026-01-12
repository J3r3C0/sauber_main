# core/state_machine.py
"""
Sheratan — minimal, production-usable State Machine (Phase A)

Goals:
- Single source of truth for "system state"
- Explicit transitions with reasons
- Transition logging (structured)
- Small persistence surface (json file) + in-memory runtime

Drop-in usage:
    from core.state_machine import SystemStateMachine, SystemState, TransitionEvent

    sm = SystemStateMachine(load_path="runtime/system_state.json",
                            log_path="logs/state_transitions.jsonl")
    sm.load_or_init()

    sm.transition(SystemState.OPERATIONAL, reason="all health checks OK",
                  meta={"checks": {"core_api": "ok", "webrelay": "ok"}})

    snapshot = sm.snapshot()
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, Optional, Tuple


# -----------------------------
# States (normative)
# -----------------------------

class SystemState(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    REFLECTIVE = "REFLECTIVE"
    RECOVERY = "RECOVERY"
    PAUSED = "PAUSED"


# -----------------------------
# Transition event (audit-friendly)
# -----------------------------

@dataclass(frozen=True)
class TransitionEvent:
    event_id: str
    ts: float
    prev_state: str
    next_state: str
    reason: str
    actor: str = "system"  # "system" | "user" | "admin" | "scheduler" | etc.
    meta: Dict[str, Any] = None  # extra structured info (checks, error codes, etc.)

    def to_json(self) -> str:
        d = asdict(self)
        if d["meta"] is None:
            d["meta"] = {}
        return json.dumps(d, ensure_ascii=False, sort_keys=True)


# -----------------------------
# Minimal state snapshot
# -----------------------------

@dataclass
class StateSnapshot:
    state: str
    since_ts: float
    last_transition: Optional[TransitionEvent] = None
    # Optional small rollup fields (keep minimal!)
    health: Dict[str, Any] = None
    counters: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "state": self.state,
            "since_ts": self.since_ts,
            "health": self.health or {},
            "counters": self.counters or {},
            "last_transition": None,
        }
        if self.last_transition is not None:
            d["last_transition"] = asdict(self.last_transition)
        return d


# -----------------------------
# State machine core
# -----------------------------

class InvalidTransition(Exception):
    pass


class SystemStateMachine:
    """
    Minimal state machine with:
    - explicit transition policy
    - atomic-ish persistence (write temp + replace)
    - JSONL transition log
    """

    def __init__(
        self,
        load_path: str = "runtime/system_state.json",
        log_path: str = "logs/state_transitions.jsonl",
        actor_default: str = "system",
    ):
        self.load_path = load_path
        self.log_path = log_path
        self.actor_default = actor_default

        self._snapshot: Optional[StateSnapshot] = None

        # Transition policy:
        # (from, to) -> allowed
        self._allowed: Dict[Tuple[str, str], bool] = self._build_default_policy()

    # -----------------------------
    # Public API
    # -----------------------------

    def load_or_init(self) -> StateSnapshot:
        """
        Load snapshot if exists, otherwise initialize to PAUSED.
        PAUSED is a safe default: "system is up but not executing".
        """
        snap = self._load_snapshot()
        if snap is None:
            snap = StateSnapshot(
                state=SystemState.PAUSED.value,
                since_ts=time.time(),
                last_transition=None,
                health={},
                counters={},
            )
            self._snapshot = snap
            self._persist_snapshot(snap)
        else:
            self._snapshot = snap
        return self._snapshot

    def snapshot(self) -> StateSnapshot:
        if self._snapshot is None:
            return self.load_or_init()
        return self._snapshot

    def set_health(self, health: Dict[str, Any]) -> StateSnapshot:
        """
        Store current health context. Does NOT auto-transition by itself.
        (Keep Phase A minimal: transition decisions remain explicit.)
        """
        snap = self.snapshot()
        snap.health = dict(health or {})
        self._persist_snapshot(snap)
        return snap

    def set_counters(self, counters: Dict[str, Any]) -> StateSnapshot:
        snap = self.snapshot()
        snap.counters = dict(counters or {})
        self._persist_snapshot(snap)
        return snap

    def transition(
        self,
        next_state: SystemState,
        *,
        reason: str,
        actor: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        allow_noop: bool = True,
    ) -> TransitionEvent:
        """
        Perform a state transition with policy enforcement + logging.
        """
        if not reason or not reason.strip():
            raise ValueError("reason must be a non-empty string")

        snap = self.snapshot()
        prev = SystemState(snap.state)

        if prev == next_state:
            if allow_noop:
                # Still log a noop transition if useful, but do not change since_ts
                ev = self._make_event(prev, next_state, reason, actor, meta, noop=True)
                self._append_event(ev)
                snap.last_transition = ev
                self._persist_snapshot(snap)
                return ev
            raise InvalidTransition(f"noop transition {prev.value} -> {next_state.value} not allowed")

        if not self._is_allowed(prev, next_state):
            raise InvalidTransition(f"transition not allowed: {prev.value} -> {next_state.value}")

        ev = self._make_event(prev, next_state, reason, actor, meta)

        # mutate snapshot
        snap.state = next_state.value
        snap.since_ts = ev.ts
        snap.last_transition = ev

        # persist + log
        self._persist_snapshot(snap)
        self._append_event(ev)

        return ev

    # -----------------------------
    # Policy
    # -----------------------------

    def _build_default_policy(self) -> Dict[Tuple[str, str], bool]:
        """
        Default minimal policy based on your Soll-definition:
        - OPERATIONAL <-> DEGRADED depending on partial failures
        - RECOVERY can follow DEGRADED/OPERATIONAL when repair routines kick in
        - REFLECTIVE can be entered from OPERATIONAL/DEGRADED (self-diagnostics)
        - PAUSED can be entered from anywhere (explicit stop)
        - From PAUSED: only to RECOVERY or OPERATIONAL (start/boot sequence)
        """
        A = SystemState
        allowed_pairs = [
            # from PAUSED
            (A.PAUSED, A.RECOVERY),
            (A.PAUSED, A.OPERATIONAL),

            # operational transitions
            (A.OPERATIONAL, A.DEGRADED),
            (A.OPERATIONAL, A.REFLECTIVE),
            (A.OPERATIONAL, A.RECOVERY),
            (A.OPERATIONAL, A.PAUSED),

            # degraded transitions
            (A.DEGRADED, A.OPERATIONAL),
            (A.DEGRADED, A.REFLECTIVE),
            (A.DEGRADED, A.RECOVERY),
            (A.DEGRADED, A.PAUSED),

            # reflective transitions
            (A.REFLECTIVE, A.OPERATIONAL),
            (A.REFLECTIVE, A.DEGRADED),
            (A.REFLECTIVE, A.RECOVERY),
            (A.REFLECTIVE, A.PAUSED),

            # recovery transitions
            (A.RECOVERY, A.OPERATIONAL),
            (A.RECOVERY, A.DEGRADED),
            (A.RECOVERY, A.PAUSED),
        ]
        out: Dict[Tuple[str, str], bool] = {}
        for fr, to in allowed_pairs:
            out[(fr.value, to.value)] = True
        return out

    def _is_allowed(self, prev: SystemState, nxt: SystemState) -> bool:
        return bool(self._allowed.get((prev.value, nxt.value), False))

    # -----------------------------
    # Persistence + logging
    # -----------------------------

    def _load_snapshot(self) -> Optional[StateSnapshot]:
        if not os.path.exists(self.load_path):
            return None
        try:
            with open(self.load_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            snap = StateSnapshot(
                state=str(data.get("state", SystemState.PAUSED.value)),
                since_ts=float(data.get("since_ts", time.time())),
                last_transition=None,
                health=dict(data.get("health") or {}),
                counters=dict(data.get("counters") or {}),
            )
            lt = data.get("last_transition")
            if isinstance(lt, dict):
                snap.last_transition = TransitionEvent(
                    event_id=str(lt.get("event_id", "")) or str(uuid.uuid4()),
                    ts=float(lt.get("ts", snap.since_ts)),
                    prev_state=str(lt.get("prev_state", snap.state)),
                    next_state=str(lt.get("next_state", snap.state)),
                    reason=str(lt.get("reason", "")),
                    actor=str(lt.get("actor", "system")),
                    meta=dict(lt.get("meta") or {}),
                )
            return snap
        except Exception:
            # For Phase A: fail-safe fallback
            return None

    def _persist_snapshot(self, snap: StateSnapshot) -> None:
        os.makedirs(os.path.dirname(self.load_path) or ".", exist_ok=True)
        tmp_path = self.load_path + ".tmp"
        payload = snap.to_dict()
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, sort_keys=True, indent=2)
        os.replace(tmp_path, self.load_path)

    def _append_event(self, ev: TransitionEvent) -> None:
        os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(ev.to_json() + "\n")

    # -----------------------------
    # Event creation
    # -----------------------------

    def _make_event(
        self,
        prev: SystemState,
        nxt: SystemState,
        reason: str,
        actor: Optional[str],
        meta: Optional[Dict[str, Any]],
        noop: bool = False,
    ) -> TransitionEvent:
        m = dict(meta or {})
        if noop:
            m.setdefault("noop", True)
        return TransitionEvent(
            event_id=str(uuid.uuid4()),
            ts=time.time(),
            prev_state=prev.value,
            next_state=nxt.value,
            reason=reason.strip(),
            actor=(actor or self.actor_default),
            meta=m,
        )
