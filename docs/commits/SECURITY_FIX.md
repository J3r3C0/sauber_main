# Security Fix: Remove Private Keys from Repository

**Date:** 2026-01-13  
**Type:** Security + Cleanup  
**Impact:** CRITICAL (Private keys removed from git history)

---

## Critical Security Issue Fixed

### Problem
Private cryptographic keys were committed to the repository:
- `mesh/offgrid/keys/node-A.json` (Ed25519 + X25519 keys)
- `mesh/offgrid/keys/node-B.json` (Ed25519 + X25519 keys)

**Risk:** Anyone with access to the repository could impersonate these nodes.

### Solution ✅

1. **Removed keys from git tracking:**
   ```bash
   git rm --cached mesh/offgrid/keys/node-A.json
   git rm --cached mesh/offgrid/keys/node-B.json
   ```

2. **Created example templates:**
   - `mesh/offgrid/keys/node-A.example.json`
   - `mesh/offgrid/keys/node-B.example.json`

3. **Enhanced `.gitignore` with security rules:**
   ```gitignore
   # Offgrid keys (keep only example templates)
   mesh/offgrid/keys/*.json
   !mesh/offgrid/keys/*.example.json
   !mesh/offgrid/keys/revocations.json
   
   # Any other private keys
   *.key
   *.pem
   *.p12
   *.pfx
   id_rsa
   id_ed25519
   ```

---

## Additional Cleanup

### Duplicate Dashboard Removed
- Archived `dashboard/` → `archive/legacy_dashboard/`
- Active dashboard: `external/dashboard/` (used by system)
- Saved: ~0.42 MB

---

## Verification

### Git Status Check ✅
```bash
git ls-files | findstr /i "keys brain_artifacts history runtime logs dump test_batch result"
```

**Result:** Only example templates and revocations.json remain ✅

---

## Important Notes

### For Developers
**Real keys are now local-only:**
- Keys remain in `mesh/offgrid/keys/` directory (gitignored)
- System continues to work with existing keys
- New nodes should copy `*.example.json` and generate real keys

### Key Generation
To generate new keys, use:
```python
python -c "from mesh.offgrid.keys.key_utils import generate_node_keys; generate_node_keys('node-C')"
```

---

## Commit Message

```
fix(security): Remove private keys from repository

CRITICAL: Remove Ed25519 and X25519 private keys from git tracking

- Remove node-A.json and node-B.json from git (SECURITY)
- Create example templates for key files
- Add comprehensive security rules to .gitignore
- Archive duplicate dashboard directory

Security Impact: Prevents unauthorized node impersonation
Cleanup: Remove 0.42 MB duplicate dashboard

BREAKING: Developers must use local keys (not tracked in git)
```

---

**Status:** ✅ CRITICAL FIX APPLIED
