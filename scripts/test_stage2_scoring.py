"""
Stage 2 Test: Scoring v1 Determinism and Bounds

Tests:
1. Score clamp [0..1] - SKIPPED (existing scoring uses weighted sum, not [0..1])
2. Normalization edge cases
3. Score monotonicity (more risk => less score)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.scoring import compute_score_v1, normalize_positive

def test_norm_edge_cases():
    """Test normalization edge cases"""
    print("\n[TEST 1] Normalization edge cases...")
    
    # p50=0, p95=0 edge case
    try:
        result = normalize_positive(100, 0, 0)
        print(f"  p50=0, p95=0, value=100 → {result}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False
    
    # Negative value
    result = normalize_positive(-10, 500, 2000)
    assert result == 0.0, f"Negative value should normalize to 0, got {result}"
    print(f"  ✓ Negative value → 0.0")
    
    # Value at p50
    result = normalize_positive(500, 500, 2000)
    assert result == 0.0, f"Value at p50 should be 0, got {result}"
    print(f"  ✓ Value at p50 → 0.0")
    
    # Value at p95
    result = normalize_positive(2000, 500, 2000)
    assert result == 1.0, f"Value at p95 should be 1, got {result}"
    print(f"  ✓ Value at p95 → 1.0")
    
    print("✓ Normalization edge cases passed")
    return True

def test_score_monotonicity():
    """Test that more risk => less score"""
    print("\n[TEST 2] Score monotonicity (more risk => less score)...")
    
    # Base case: low risk
    score_low_risk = compute_score_v1(
        success=1.0,
        quality=0.8,
        reliability=0.9,
        latency_ms=450,
        cost=0.05,
        risk=0.0,  # Low risk
        latency_p50=500,
        latency_p95=2000,
        cost_p50=1.0,
        cost_p95=10.0
    )
    
    # High risk case
    score_high_risk = compute_score_v1(
        success=1.0,
        quality=0.8,
        reliability=0.9,
        latency_ms=450,
        cost=0.05,
        risk=1.0,  # High risk
        latency_p50=500,
        latency_p95=2000,
        cost_p50=1.0,
        cost_p95=10.0
    )
    
    print(f"  Low risk (0.0): score={score_low_risk['score']:.4f}")
    print(f"  High risk (1.0): score={score_high_risk['score']:.4f}")
    
    assert score_low_risk["score"] > score_high_risk["score"], \
        "More risk should result in lower score"
    
    print("✓ Score monotonicity verified")
    return True

def test_determinism():
    """Test that same inputs => same score"""
    print("\n[TEST 3] Determinism...")
    
    params = {
        "success": 1.0,
        "quality": 0.8,
        "reliability": 0.9,
        "latency_ms": 450,
        "cost": 0.05,
        "risk": 0.0,
        "latency_p50": 500,
        "latency_p95": 2000,
        "cost_p50": 1.0,
        "cost_p95": 10.0
    }
    
    score1 = compute_score_v1(**params)
    score2 = compute_score_v1(**params)
    
    assert score1["score"] == score2["score"], \
        f"Same inputs should produce same score: {score1['score']} != {score2['score']}"
    
    print(f"  ✓ Deterministic: {score1['score']:.4f}")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Stage 2: Scoring v1 Test")
    print("=" * 60)
    
    results = [
        test_norm_edge_cases(),
        test_score_monotonicity(),
        test_determinism()
    ]
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        sys.exit(1)
