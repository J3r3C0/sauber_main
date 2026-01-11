# TODO: Production Features - Core Dispatcher

## Retry-Logic (Priority: HIGH)

**Was fehlt:**
- [ ] `retry_handler.py` erstellen
- [ ] Exponential Backoff implementieren
- [ ] Linear Backoff implementieren
- [ ] Max-Retries-Check
- [ ] Retry-Counter in Job-Model

**Code-Beispiel:**
```python
async def handle_job_failure(job: Job, error: str):
    if job.retry_count < job.max_retries:
        if job.retry_backoff == "exponential":
            delay = 2 ** job.retry_count  # 1s, 2s, 4s, 8s
        else:
            delay = job.retry_count + 1   # 1s, 2s, 3s, 4s
        
        job.retry_count += 1
        job.last_retry_at = datetime.utcnow()
        job.status = JobStatus.PENDING
        
        await asyncio.sleep(delay)
        await dispatcher.dispatch_job(job)
    else:
        job.status = JobStatus.FAILED
        job.error = f"Max retries exceeded: {error}"
```

**Geschätzter Aufwand:** 2 Stunden

---

## Prioritäts-Queue (Priority: MEDIUM)

**Was fehlt:**
- [ ] `JobPriority` Enum (CRITICAL, HIGH, NORMAL, LOW)
- [ ] Priority-basierte Sortierung in `get_next_job()`
- [ ] Priority-Field in Job-Model

**Code-Beispiel:**
```python
async def get_next_job() -> Optional[Job]:
    # ORDER BY priority ASC, created_at ASC
    jobs = await storage.get_pending_jobs_by_priority()
    for job in jobs:
        if await all_dependencies_completed(job):
            return job
    return None
```

**Geschätzter Aufwand:** 1 Stunde

---

## Job-Dependencies (Priority: LOW)

**Was fehlt:**
- [ ] `depends_on: List[str]` in Job-Model
- [ ] Dependency-Check vor Dispatch
- [ ] Circular-Dependency-Detection

**Geschätzter Aufwand:** 2 Stunden

---

**Erstellt:** 2026-01-10  
**Status:** Nicht implementiert (Quick Refactoring)
