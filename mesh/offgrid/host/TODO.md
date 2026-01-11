# TODO: Production Features - Offgrid Host

## Timeout-Handling (Priority: HIGH)

**Was fehlt:**
- [ ] Timeout-Parameter in Job-Model (`timeout_seconds`)
- [ ] `asyncio.timeout()` in Executor
- [ ] Timeout-Error-Handling

**Code-Beispiel:**
```python
async def execute_job(job: Job) -> Dict[str, Any]:
    try:
        async with asyncio.timeout(job.timeout_seconds):
            result = await _run_job_payload(job.payload)
            return result
    except asyncio.TimeoutError:
        raise JobExecutionError(f"Job timed out after {job.timeout_seconds}s")
```

**Geschätzter Aufwand:** 1 Stunde

---

## Heartbeat-System (Priority: HIGH)

**Was fehlt:**
- [ ] `heartbeat.py` - Heartbeat-Loop
- [ ] POST `/api/hosts/heartbeat` alle 10 Sekunden
- [ ] Host-Status (ONLINE, BUSY, OFFLINE)
- [ ] Current-Jobs-Tracking

**Code-Beispiel:**
```python
async def heartbeat_loop():
    while True:
        await asyncio.sleep(10)
        try:
            await core_api.post("/api/hosts/heartbeat", json={
                "host_id": HOST_ID,
                "status": get_current_status(),
                "current_jobs": get_running_job_ids(),
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
```

**Geschätzter Aufwand:** 2 Stunden

---

**Erstellt:** 2026-01-10  
**Status:** Nicht implementiert (Quick Refactoring)
