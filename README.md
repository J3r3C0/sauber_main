# Sheratan Core

![Status: Production-Ready](https://img.shields.io/badge/Status-Production--Ready-green)
![Version: 2.9](https://img.shields.io/badge/Version-v2.9-blue)
![Acceptance: PASS](https://img.shields.io/badge/Acceptance-PASS-brightgreen)

Sheratan Core is a stable, high-performance orchestration and control-plane engine designed for robust mesh-based task execution. It establishes a secure, tamper-proof environment for distributed workloads with a focus on cryptographic integrity and data-plane resilience.

---

## Executive Summary

Sheratan Core has successfully passed all production readiness and stability gates. It is a reliable, manipulation-resistant system designed for production environments or high-stakes development phases.

### Core Values
- **Reliability**: Remains stable under load, detects duplicate/faulty requests, and ensures consistent results.
- **Security**: Cryptographic identity for all components, automated drift/spoof detection, and controlled security enforcement.
- **Transparency**: Fully auditable system state, automated metric tracking, and explainable decision traces.

---

## Technical Capabilities (Sheratan v2.9)

### 🛡️ Governance & Security (Track A)
- **Node Identity (A4)**: Ed25519 identity with TOFU-pinning and signed heartbeats.
- **Node Attestation (A2)**: Automated signal tracking for build-id, capability hash, and runtime drift.
- **Enforcement Layer (A3)**: Graduated response (WARN/QUARANTINE) based on attestation health.
- **Token Rotation (A1)**: Zero-downtime credential rotation.

### ⚡ Data-Plane Robustness (Track B)
- **Result Integrity (B3)**: Canonical SHA256 hashing for all results. Tamper detection triggers 403 Forbidden and audit alerts.
- **Idempotency (B2)**: At-most-once semantics with gateway hashing and collision detection.
- **Backpressure (B1)**: Queue-depth limits, inflight-limits, and DB-native lease management.

---

## Proof of Work & Verification

The system state is continuously validated via the **Sheratan Acceptance Suite**:
- `scripts/acceptance.ps1` -> **PASS**
- `verify_b2_idempotency.ps1` -> **PASS**
- `verify_b3_result_integrity.ps1` -> **PASS**

---

## Getting Started

### Quick Launch (Windows)
To start the complete system on localhost:
```powershell
.\START_COMPLETE_SYSTEM.bat
```

### Verification
To run the full production acceptance gate:
```powershell
.\scripts\acceptance.ps1
```

---

## Documentation
- [System Overview](docs/system_overview.md) - Port guide and architecture.
- [Architecture](docs/SHERATAN_REFACTORING_PLAN.md) - Technical design and state machines.
- [Track B2 Details](docs/Track%20B2%20idempotency.md) - Idempotency implementation.

---
**Status**: Track B (Reliability) is officially CLOSED. Ready for deployment.
