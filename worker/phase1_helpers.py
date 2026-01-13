# worker/phase1_helpers.py
"""
Phase 1 Performance Improvements:
- Resilient HTTP client with retry
- Event-driven job processing with watchdog
- Idempotent job claiming
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# ============================================================================
# Resilient HTTP Client with Retry
# ============================================================================

try:
    import httpx
    from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    httpx = None

# Reusable sync HTTP client (created once)
_http_client: Optional['httpx.Client'] = None

def get_http_client():
    """Get or create the shared HTTP client"""
    global _http_client
    if _http_client is None and HAS_HTTPX:
        timeout = float(os.getenv("HTTP_TIMEOUT", "10"))
        _http_client = httpx.Client(timeout=timeout)
    return _http_client

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),  # 1s, 2s, 4s
    reraise=True
)
def notify_core_with_retry(core_url: str, job_id: str) -> bool:
    """
    Notify Core API to sync job result with automatic retry.
    
    Args:
        core_url: Base URL of Core API
        job_id: Job ID to sync
        
    Returns:
        True if successful, False otherwise
    """
    if not HAS_HTTPX:
        # Fallback to requests (no retry)
        import requests
        try:
            sync_url = f"{core_url}/api/jobs/{job_id}/sync"
            resp = requests.post(sync_url, timeout=10)
            return resp.ok
        except Exception as e:
            logger.warning(f"Failed to notify Core (requests): {e}")
            return False
    
    client = get_http_client()
    if client is None:
        return False
    
    try:
        sync_url = f"{core_url}/api/jobs/{job_id}/sync"
        response = client.post(sync_url)
        response.raise_for_status()
        logger.info(f"✓ Notified Core to sync job {job_id[:12]}...")
        return True
    except httpx.HTTPError as e:
        logger.warning(f"HTTP error notifying Core for {job_id}: {e}")
        raise  # tenacity will retry

def notify_core_safe(core_url: str, job_id: str, failed_reports_dir: Path) -> bool:
    """
    Notify Core with retry, save to disk if all retries fail.
    
    Args:
        core_url: Base URL of Core API
        job_id: Job ID to sync
        failed_reports_dir: Directory to save failed notifications
        
    Returns:
        True if successful (or saved for later), False on error
    """
    try:
        return notify_core_with_retry(core_url, job_id)
    except (RetryError, Exception) as e:
        logger.error(f"Failed to notify Core for {job_id} after retries: {e}")
        
        # Save failed notification for manual recovery
        try:
            failed_reports_dir.mkdir(parents=True, exist_ok=True)
            failed_file = failed_reports_dir / f"{job_id}.failed_notify.txt"
            failed_file.write_text(f"{core_url}/api/jobs/{job_id}/sync\n{time.time()}\n")
            logger.info(f"Saved failed notification to {failed_file}")
            return True  # Saved for later
        except Exception as save_error:
            logger.error(f"Failed to save notification: {save_error}")
            return False

# ============================================================================
# Event-Driven Job Processing with Watchdog
# ============================================================================

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    Observer = None
    FileSystemEventHandler = None

class JobEventHandler(FileSystemEventHandler):
    """
    Filesystem event handler for job files with debounce and stability checks.
    
    Features:
    - Debounce: Wait for file stability before processing
    - Idempotent claiming: Prevent double-processing
    - Windows-safe: Handles duplicate events and incomplete writes
    """
    
    def __init__(self, process_callback: Callable[[Path], None], debounce_ms: int = 200):
        """
        Args:
            process_callback: Function to call with stable job file path
            debounce_ms: Milliseconds to wait for file stability
        """
        super().__init__()
        self.process_callback = process_callback
        self.debounce_seconds = debounce_ms / 1000.0
        self.pending = {}  # {filepath: first_seen_time}
        
    def on_created(self, event):
        """Called when a file is created"""
        if event.is_directory:
            return
        
        if event.src_path.endswith('.job.json'):
            # Don't process immediately - wait for stability
            self.pending[event.src_path] = time.time()
            logger.debug(f"Job file detected: {event.src_path}")
    
    def check_stable_files(self):
        """Process files that have been stable for debounce period"""
        now = time.time()
        stable_files = []
        
        for filepath, first_seen in list(self.pending.items()):
            path = Path(filepath)
            
            # Check if file still exists
            if not path.exists():
                del self.pending[filepath]
                continue
            
            # Check if file size is stable
            try:
                size1 = path.stat().st_size
                time.sleep(0.05)  # 50ms
                
                if not path.exists():
                    del self.pending[filepath]
                    continue
                    
                size2 = path.stat().st_size
                
                # File is stable if size unchanged and debounce period elapsed
                if size1 == size2 and (now - first_seen) >= self.debounce_seconds:
                    stable_files.append(path)
                    del self.pending[filepath]
                    
            except (OSError, FileNotFoundError):
                # File disappeared or locked
                del self.pending[filepath]
        
        # Process stable files
        for path in stable_files:
            try:
                self.process_callback(path)
            except Exception as e:
                logger.error(f"Error processing {path}: {e}")

def claim_job_file(job_file: Path) -> bool:
    """
    Atomically claim a job file to prevent double-processing.
    
    Args:
        job_file: Path to job file
        
    Returns:
        True if claimed successfully, False if already claimed
    """
    claim_file = Path(str(job_file) + ".claimed")
    
    try:
        # Atomic claim: create .claimed file exclusively
        fd = os.open(claim_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        # Already claimed by another worker/thread
        logger.debug(f"Job {job_file.name} already claimed")
        return False
    except Exception as e:
        logger.warning(f"Error claiming {job_file}: {e}")
        return False

def release_job_claim(job_file: Path):
    """Release job claim file"""
    claim_file = Path(str(job_file) + ".claimed")
    try:
        claim_file.unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Error releasing claim for {job_file}: {e}")

def check_for_unclaimed_jobs(directory: Path, process_callback: Callable[[Path], None]):
    """
    Fallback: Check for jobs that might have been missed by watchdog.
    
    Args:
        directory: Directory to scan
        process_callback: Function to call with unclaimed job files
    """
    try:
        for job_file in directory.glob("*.job.json"):
            claim_file = Path(str(job_file) + ".claimed")
            
            # Skip if already claimed
            if claim_file.exists():
                # Check if claim is stale (> 5 minutes)
                try:
                    claim_age = time.time() - claim_file.stat().st_mtime
                    if claim_age > 300:  # 5 minutes
                        logger.warning(f"Stale claim detected: {job_file.name}")
                        claim_file.unlink(missing_ok=True)
                    else:
                        continue
                except:
                    continue
            
            # Process unclaimed job
            try:
                process_callback(job_file)
            except Exception as e:
                logger.error(f"Error processing unclaimed job {job_file}: {e}")
                
    except Exception as e:
        logger.error(f"Error checking for unclaimed jobs: {e}")
