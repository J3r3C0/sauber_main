import json
import os
import tempfile
import shutil
import contextlib
import errno
import random
import time
from typing import Any, Dict, List

@contextlib.contextmanager
def json_lock(path: str, timeout: float = 30.0, stale_after: float = 60.0):
    """
    Cross-platform advisory file lock for JSON persistence.
    Protects against Lost Updates by wrapping Read-Modify-Write cycles.
    """
    lock_path = path + ".lock"
    start = time.time()
    retries = 0

    while True:
        try:
            # Atomic lock creation
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            try:
                payload = f"pid={os.getpid()} time={time.time()}\n"
                os.write(fd, payload.encode("utf-8"))
                yield
            finally:
                try:
                    os.close(fd)
                finally:
                    # Best-effort unlock with retry for Windows stability
                    for _ in range(5):
                        try:
                            os.remove(lock_path)
                            break
                        except FileNotFoundError:
                            break
                        except PermissionError:
                            time.sleep(0.01)
            return

        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

            # Stale lock detection (best-effort)
            try:
                st = os.stat(lock_path)
                age = time.time() - st.st_mtime
                if age > stale_after:
                    try:
                        os.remove(lock_path)
                        continue # Re-try immediately after clearing stale lock
                    except OSError:
                        pass
            except FileNotFoundError:
                continue

            if time.time() - start > timeout:
                raise TimeoutError(f"Could not acquire lock on {path} within {timeout}s")

            # Backoff + jitter to prevent thundering herd
            retries += 1
            base = min(0.5, 0.01 * (2 ** min(retries, 6)))
            time.sleep(base + random.uniform(0.0, 0.05))

def atomic_write_json(path: str, data: Any, *, indent: int = 2) -> None:
    """
    Saves data to a JSON file atomically with durability guarantees.
    
    Args:
        path: Target file path.
        data: JSON-serializable data.
        indent: JSON indentation.
    """
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    # Use same directory for atomic swap capability
    fd, tmp_path = tempfile.mkstemp(
        dir=directory,
        prefix=os.path.basename(path) + ".tmp."
    )
    
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            # Ensure data is on disk
            try:
                os.fsync(f.fileno())
            except OSError:
                # Some filesystems might not support fsync (e.g. certain network shares)
                pass

        # Robust backup: Copy instead of move to preserve meta and prevent loss if swap fails
        if os.path.exists(path):
            bak = str(path) + ".bak"
            try:
                shutil.copy2(path, bak)
            except Exception:
                # Backup is best-effort
                pass

        # Atomic Swap with retry logic for Windows concurrency
        max_retries = 10
        for attempt in range(max_retries):
            try:
                os.replace(tmp_path, path)
                break
            except PermissionError:
                if attempt == max_retries - 1:
                    raise
                import time
                time.sleep(0.01 * (attempt + 1)) # Exponential backoff light
        
        # Best-effort Directory fsync (Linux/macOS) for entry durability
        try:
            if hasattr(os, "O_DIRECTORY"):
                # Open directory for reading only
                dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
        except Exception:
            pass
            
    finally:
        # Cleanup temporary file if it still exists (e.g. if os.replace failed)
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

def canonical_json_bytes(obj: Dict[str, Any]) -> bytes:
    """
    Deterministic JSON serialization (canonical form):
    - UTF-8
    - sorted keys
    - no whitespace
    - ensure_ascii=False
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def atomic_append_jsonl(path: str, obj: Dict[str, Any], *, timeout: float = 10.0) -> None:
    """
    Append exactly one JSON object as one line to a .jsonl file, with:
    - advisory lock via json_lock(path)
    - flush + fsync for durability
    - best-effort Windows retry on transient access errors
    """
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    # Serialize once (avoid partial writes of different representations)
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    data = line.encode("utf-8")

    # We lock the journal itself to prevent interleaved lines.
    with json_lock(path, timeout=timeout):
        # Windows can transiently deny access when multiple processes contend.
        # Retry a few times with backoff.
        retries = 0
        while True:
            try:
                with open(path, "ab", buffering=0) as f:
                    f.write(data)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
                return
            except PermissionError:
                retries += 1
                if retries >= 8:
                    raise
                # jittered backoff
                time.sleep(min(0.5, 0.01 * (2 ** min(retries, 6))) + random.uniform(0.0, 0.05))
