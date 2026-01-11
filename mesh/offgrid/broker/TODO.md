# TODO: Production Features - Offgrid Broker

## Host-Health-Checks (Priority: HIGH)

**Was fehlt:**
- [ ] Host-Health-Check vor Dispatch
- [ ] Offline-Host-Detection (last_heartbeat > 30s)
- [ ] Fallback zu anderem Host bei Offline

**Code-Beispiel:**
```python
async def select_host_for_job(job: Job) -> Optional[Host]:
    hosts = await core_api.get("/api/hosts")
    
    # Filter: online + not busy + has capabilities
    available = [
        h for h in hosts
        if h.status == HostStatus.ONLINE
        and len(h.current_jobs) < h.max_concurrent
        and all(cap in h.capabilities for cap in job.required_capabilities)
    ]
    
    if not available:
        return None
    
    # Select least loaded
    return min(available, key=lambda h: len(h.current_jobs))
```

**Geschätzter Aufwand:** 2 Stunden

---

**Erstellt:** 2026-01-10  
**Status:** Nicht implementiert (Quick Refactoring)
