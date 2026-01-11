# Sheratan Structure Migration Map

**Migration Date:** 2026-01-10  
**Migration Type:** Symlink Bridge (Option A)  
**Status:** Partial - Old structure remains, new structure added in parallel

---

## Directory Structure Changes

### Old Structure (Still Active)
```
c:\projectroot\
├── v_core\sheratan_core_v2\     # Core service
├── v_mesh\                       # Broker + Hosts
├── v_mini\                       # WebRelay
└── runtime\                      # 4-Zone system
```

### New Structure (Parallel)
```
c:\projectroot\
├── mesh\                         # Mesh-internal
│   ├── core\                     # From v_core\sheratan_core_v2\
│   ├── offgrid\                  # From v_mesh\
│   └── runtime\                  # From runtime\ (renamed zones)
├── external\                     # Mesh-external
│   ├── webrelay\                 # From v_mini\
│   ├── gatekeeper\               # From v_core\sheratan_core_v2\gatekeeper.py
│   ├── auditor\                  # From v_core\sheratan_core_v2\auditor_relay.py
│   └── final_decision\           # From v_core\sheratan_core_v2\final_decision.py
├── config\                       # From v_mini\.env
└── docs\                         # New (empty)
```

---

## File Migrations

### Core Files (v_core → mesh/core)

| Old Path | New Path | Status |
|----------|----------|--------|
| `v_core\sheratan_core_v2\main.py` | `mesh\core\main.py` | ✅ Copied |
| `v_core\sheratan_core_v2\models.py` | `mesh\core\storage\models.py` | ✅ Copied |
| `v_core\sheratan_core_v2\storage.py` | `mesh\core\storage\storage.py` | ✅ Copied |
| `v_core\sheratan_core_v2\gates\*` | `mesh\core\gates\*` | ✅ Copied (all gates) |
| `v_core\sheratan_core_v2\offgrid.py` | `mesh\core\dispatcher.py` | ✅ Copied |
| `v_core\sheratan_core_v2\webrelay_bridge.py` | `mesh\core\webrelay_bridge.py` | ⚠️ Not copied (stays in v_core) |
| `v_core\sheratan_core_v2\offgrid_bridge.py` | `mesh\core\offgrid_bridge.py` | ⚠️ Not copied (stays in v_core) |
| `v_core\sheratan_core_v2\lcp_actions.py` | `mesh\core\lcp_actions.py` | ⚠️ Not copied (stays in v_core) |
| `v_core\sheratan_core_v2\llm_analyzer.py` | `mesh\core\llm_analyzer.py` | ⚠️ Not copied (stays in v_core) |
| `v_core\sheratan_core_v2\mesh_monitor.py` | `mesh\core\mesh_monitor.py` | ⚠️ Not copied (stays in v_core) |
| `v_core\sheratan_core_v2\event_logger.py` | `mesh\core\event_logger.py` | ⚠️ Not copied (stays in v_core) |
| `v_core\sheratan_core_v2\metrics_client.py` | `mesh\core\metrics_client.py` | ⚠️ Not copied (stays in v_core) |

### Offgrid Files (v_mesh → mesh/offgrid)

| Old Path | New Path | Status |
|----------|----------|--------|
| `v_mesh\broker\auction_api.py` | `mesh\offgrid\broker\auction_api.py` | ✅ Copied |
| `v_mesh\broker\auction_logic.py` | `mesh\offgrid\broker\auction_logic.py` | ✅ Copied |
| `v_mesh\host_daemon\api_real.py` | `mesh\offgrid\host\api_real.py` | ✅ Copied |
| `v_mesh\host_daemon\*` | `mesh\offgrid\host\*` | ✅ Copied (all files) |

### External Services (v_core + v_mini → external/)

| Old Path | New Path | Status |
|----------|----------|--------|
| `v_mini\*` | `external\webrelay\*` | ✅ Copied (all files) |
| `v_core\sheratan_core_v2\gatekeeper.py` | `external\gatekeeper\gatekeeper.py` | ✅ Copied |
| `v_core\sheratan_core_v2\auditor_relay.py` | `external\auditor\auditor_relay.py` | ✅ Copied |
| `v_core\sheratan_core_v2\final_decision.py` | `external\final_decision\final_decision.py` | ✅ Copied |

### Runtime Zones (runtime/ → mesh/runtime/)

| Old Path | New Path | Zone Purpose |
|----------|----------|--------------|
| `runtime\narrative\` | `mesh\runtime\inbox\` | 📥 External input |
| `runtime\input\` | `mesh\runtime\queue\approved\` | ✅ Ready for execution |
| `runtime\quarantine\` | `mesh\runtime\queue\blocked\` | ⚠️ Blocked jobs |
| `runtime\output\` | `mesh\runtime\outbox\results\` | 📤 Job results |
| `runtime\output\ledger.jsonl` | `mesh\runtime\outbox\ledger.jsonl` | 📋 Reality Ledger |
| `runtime\proofed\` | ❌ **DEPRECATED** | (Merged into queue/) |
| `runtime\audited\` | ❌ **DEPRECATED** | (Merged into queue/) |

### Config Files

| Old Path | New Path | Status |
|----------|----------|--------|
| `v_mini\.env` | `config\.env` | ✅ Copied |
| `v_config\default-config.json` | `config\default-config.json` | ⚠️ Not found |

---

## Symlink Strategy

**Current Approach:**
- Old directories (`v_core/`, `v_mesh/`, `v_mini/`, `runtime/`) remain **unchanged**
- New directories (`mesh/`, `external/`) contain **copies** of files
- Services continue to run from **old paths** (no breaking changes)
- Migration can happen **gradually** by updating imports one file at a time

**Why Symlinks?**
- ✅ Zero downtime - system keeps running
- ✅ Gradual migration - update one file at a time
- ✅ Easy rollback - just delete new directories
- ✅ Test new structure - without breaking old one

---

## TODO: Production Features (Not Implemented)

See TODO.md files in:
- `mesh\core\TODO.md` - Retry, Priorities, Dependencies
- `mesh\core\storage\TODO.md` - Idempotency, SQLite migration
- `mesh\offgrid\host\TODO.md` - Timeout, Heartbeat
- `mesh\offgrid\broker\TODO.md` - Host health checks
- `mesh\core\rate_limiter_TODO.md` - Rate limiting

**Estimated Effort:** 8-10 hours for all production features

---

## Next Steps

### Phase 1: Symlink Bridge (DONE)
- [x] Create new directory structure
- [x] Copy files to new locations
- [x] Document migrations
- [x] Place TODO markers

### Phase 2: Gradual Import Migration (TODO)
- [ ] Update imports in `mesh/core/main.py`
- [ ] Update imports in `mesh/offgrid/broker/auction_api.py`
- [ ] Update imports in `mesh/offgrid/host/api_real.py`
- [ ] Update imports in `external/gatekeeper/gatekeeper.py`
- [ ] Update imports in `external/auditor/auditor_relay.py`
- [ ] Update imports in `external/final_decision/final_decision.py`

### Phase 3: Path Updates (TODO)
- [ ] Update runtime paths in all files
- [ ] Update `START_SHERATAN.ps1` to use new paths
- [ ] Update individual start scripts

### Phase 4: Testing (TODO)
- [ ] Test with old structure (should still work)
- [ ] Test with new structure (after import updates)
- [ ] End-to-end test

### Phase 5: Cleanup (TODO)
- [ ] Remove old directories (`v_core/`, `v_mesh/`, `v_mini/`)
- [ ] Remove deprecated runtime zones (`proofed/`, `audited/`)
- [ ] Update documentation

---

## Rollback Plan

If anything breaks:
1. Delete `mesh/` and `external/` directories
2. System continues running from old structure
3. No data loss (backup in `backup_20260110_015259/`)

---

**Created:** 2026-01-10 02:03  
**Last Updated:** 2026-01-10 02:03  
**Status:** Symlink Bridge Active, Old Structure Still Primary
