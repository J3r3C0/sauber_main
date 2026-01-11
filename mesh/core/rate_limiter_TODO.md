# TODO: Production Features - Rate Limiting

## Rate-Limiter (Priority: MEDIUM)

**Was fehlt:**
- [ ] `rate_limiter.py` erstellen
- [ ] Per-Source-Limits (max_jobs_per_minute, max_concurrent_jobs)
- [ ] Rate-Limit-Config in DB
- [ ] Rate-Limit-Check vor Dispatch

**Code-Beispiel:**
```python
class RateLimiter:
    async def check_limit(self, source: str) -> bool:
        config = await storage.get_rate_limit_config(source)
        now = datetime.utcnow()
        
        # Reset window if expired
        if (now - config.window_start).total_seconds() >= 60:
            config.current_count = 0
            config.window_start = now
        
        # Check limits
        if config.current_count >= config.max_jobs_per_minute:
            return False
        
        # Check concurrent
        concurrent = await storage.count_running_jobs_by_source(source)
        if concurrent >= config.max_concurrent_jobs:
            return False
        
        # Increment counter
        config.current_count += 1
        await storage.update_rate_limit_config(config)
        
        return True
```

**Geschätzter Aufwand:** 2-3 Stunden

---

**Erstellt:** 2026-01-10  
**Status:** Nicht implementiert (Quick Refactoring)
