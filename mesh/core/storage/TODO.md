# TODO: Production Features - Storage Layer

## Idempotenz (Priority: HIGH)

**Was fehlt:**
- [ ] `idempotency_key` in Job-Model hinzufügen
- [ ] Deduplication-Logic in `dispatcher.py`
- [ ] Check vor Execution: `if job_already_executed(idempotency_key): return cached_result`

**Warum wichtig:**
- Verhindert doppelte Execution bei Retry
- Ermöglicht sichere Wiederholung von Requests

**Geschätzter Aufwand:** 1-2 Stunden

---

## SQLite-Migration (Priority: MEDIUM)

**Was fehlt:**
- [ ] `database.py` - SQLite Connection Pool
- [ ] `models.py` - Pydantic Models für Job, Host, RateLimitConfig
- [ ] `migrations/001_initial.sql` - DB-Schema
- [ ] Migration von File-Storage zu DB-Storage

**Warum wichtig:**
- Schnellere Queries
- Transaktionale Sicherheit
- Bessere Skalierbarkeit

**Geschätzter Aufwand:** 3-4 Stunden

---

## Implementierungs-Reihenfolge

1. SQLite-Migration (Basis für alles andere)
2. Idempotenz (kritisch für Production)
3. Retry-Logic (siehe `TODO.md` in `mesh/core/`)
4. Timeout-Handling (siehe `TODO.md` in `mesh/offgrid/host/`)

---

**Erstellt:** 2026-01-10  
**Status:** Nicht implementiert (Quick Refactoring)
