from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass
class ScoreBreakdown:
    # Raw inputs (expected in [0..1] except latency/cost which are raw numbers)
    S: float  # success
    Q: float  # quality
    R: float  # reliability
    L_norm: float  # normalized latency
    C_norm: float  # normalized cost
    K: float  # risk (0..1)
    # Weights
    wS: float = 3.0
    wQ: float = 1.5
    wR: float = 1.0
    wL: float = 0.8
    wC: float = 1.2
    wK: float = 2.0
    # Output
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

def _clamp01(x: float) -> float:
    return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)

def normalize_positive(value: float, baseline_p50: float, baseline_p95: float) -> float:
    """
    Normalize a positive metric (latency_ms or cost) into [0..1] using robust baselines.
    - <= p50 -> ~0
    - >= p95 -> ~1
    Linear in between.
    """
    v = max(0.0, float(value))
    p50 = max(1e-9, float(baseline_p50))
    p95 = max(p50 + 1e-9, float(baseline_p95))
    t = (v - p50) / (p95 - p50)
    return _clamp01(t)

def compute_score_v1(
    *,
    success: float,
    quality: float,
    reliability: float,
    latency_ms: float,
    cost: float,
    risk: float,
    # baselines for normalization (rolling or fixed)
    latency_p50: float = 500.0,
    latency_p95: float = 2000.0,
    cost_p50: float = 1.0,
    cost_p95: float = 10.0,
    # optional override weights
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Sheratan Score v1 (exact breakdown):
      score = + wS*S + wQ*Q + wR*R - wL*norm(L) - wC*norm(C) - wK*K
    """
    w = {
        "wS": 3.0, "wQ": 1.5, "wR": 1.0,
        "wL": 0.8, "wC": 1.2, "wK": 2.0,
    }
    if weights:
        for k, v in weights.items():
            if k in w and v is not None:
                w[k] = float(v)

    S = _clamp01(float(success))
    Q = _clamp01(float(quality))
    R = _clamp01(float(reliability))
    K = _clamp01(float(risk))

    L_norm = normalize_positive(latency_ms, latency_p50, latency_p95)
    C_norm = normalize_positive(cost, cost_p50, cost_p95)

    score = (
        + w["wS"] * S
        + w["wQ"] * Q
        + w["wR"] * R
        - w["wL"] * L_norm
        - w["wC"] * C_norm
        - w["wK"] * K
    )

    bd = ScoreBreakdown(
        S=S, Q=Q, R=R, L_norm=L_norm, C_norm=C_norm, K=K,
        wS=w["wS"], wQ=w["wQ"], wR=w["wR"], wL=w["wL"], wC=w["wC"], wK=w["wK"],
        score=score
    )
    return bd.to_dict()
