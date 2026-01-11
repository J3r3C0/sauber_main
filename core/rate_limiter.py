from datetime import datetime
from typing import Optional
from core import storage

class RateLimiter:
    """Handles per-source job limits and concurrency."""
    
    def check_limit(self, source: str) -> bool:
        config = storage.get_rate_limit_config(source)
        if not config:
            # Default limits if not configured
            config = {
                "source": source,
                "max_jobs_per_minute": 60,
                "max_concurrent_jobs": 10,
                "current_count": 0,
                "window_start": datetime.utcnow().isoformat()
            }
            storage.update_rate_limit_config(**config)
            return True

        now = datetime.utcnow()
        window_start = datetime.fromisoformat(config["window_start"])
        
        # Reset window if expired (1 minute)
        if (now - window_start).total_seconds() >= 60:
            config["current_count"] = 1
            config["window_start"] = now.isoformat()
            storage.update_rate_limit_config(**config)
            return True
        
        # Check jobs per minute
        if config["current_count"] >= config["max_jobs_per_minute"]:
            print(f"[rate-limit] Blocked {source}: Max jobs per minute reached ({config['max_jobs_per_minute']})")
            return False
        
        # Check concurrency
        concurrent = storage.count_running_jobs_by_source(source)
        if concurrent >= config["max_concurrent_jobs"]:
            print(f"[rate-limit] Blocked {source}: Max concurrent jobs reached ({config['max_concurrent_jobs']})")
            return False
        
        # Increment counter
        config["current_count"] += 1
        storage.update_rate_limit_config(**config)
        
        return True
