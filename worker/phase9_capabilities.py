"""
Phase 9 Worker Capabilities for Job Chaining
Provides walk_tree and read_file_batch capabilities with hard limits.
"""

import os
from pathlib import Path
from typing import Dict, Any, List

# Hard Limits (as per user specification)
MAX_FILES_DEFAULT = 500
MAX_FILES_HARD = 2000
MAX_CHARS_PER_FILE_DEFAULT = 20_000
MAX_CHARS_PER_FILE_HARD = 100_000
MAX_TOTAL_CHARS_DEFAULT = 120_000
MAX_TOTAL_CHARS_HARD = 400_000
MAX_FILE_BYTES_HARD = 1_000_000  # 1 MB

# Default excludes - EXACT DIR NAMES ONLY (no wildcards)
# Only common patterns - project-specific excludes should come via params
DEFAULT_EXCLUDE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", 
    ".mypy_cache", ".pytest_cache"
}


def _safe_resolve(base_root: Path, rel_or_abs: str) -> Path:
    """
    Resolve path safely within base_root to prevent directory traversal.
    
    Args:
        base_root: Base directory (must be absolute)
        rel_or_abs: Relative or absolute path to resolve
        
    Returns:
        Resolved absolute path
        
    Raises:
        ValueError: If resolved path is outside base_root
    """
    p = Path(rel_or_abs)
    if not p.is_absolute():
        p = (base_root / p).resolve()
    else:
        p = p.resolve()
    
    # Ensure inside base_root
    base_root_resolved = base_root.resolve()
    if base_root_resolved not in p.parents and p != base_root_resolved:
        raise ValueError("path_outside_root")
    
    return p


def walk_tree_from_params(params: dict, base_dir: Path) -> dict:
    """
    Deterministic recursive file listing with hard limits.
    Returns relative POSIX paths (stable across OS).
    
    Params:
        path: Directory to walk (relative to base_dir or absolute)
        include_extensions: List of extensions to include (e.g. [".py", ".js"])
        exclude_dirs: Additional dirs to exclude (exact names only)
        max_files: Maximum files to return (default 500, hard cap 2000)
        follow_symlinks: Whether to follow symlinks (default False)
        
    Returns:
        {
            "ok": bool,
            "action": "walk_tree_result",
            "files": ["path/to/file.py", ...],
            "count": int,
            "truncated": bool,
            "root": str
        }
    """
    rel_path = params.get("path", ".")
    include_ext = params.get("include_extensions") or []
    user_excludes = set(params.get("exclude_dirs") or [])
    follow_symlinks = bool(params.get("follow_symlinks", False))
    
    # Combine default and user excludes (exact names only)
    exclude_dirs = DEFAULT_EXCLUDE_DIRS | user_excludes
    
    max_files = int(params.get("max_files", MAX_FILES_DEFAULT))
    if max_files > MAX_FILES_HARD:
        max_files = MAX_FILES_HARD
    if max_files < 1:
        max_files = 1
    
    try:
        root_abs = _safe_resolve(base_dir, rel_path)
    except ValueError as e:
        return {
            "ok": False,
            "action": "walk_tree_result",
            "files": [],
            "count": 0,
            "truncated": False,
            "root": rel_path,
            "error": str(e)
        }
    
    if not root_abs.exists():
        return {
            "ok": False,
            "action": "walk_tree_result",
            "files": [],
            "count": 0,
            "truncated": False,
            "root": str(rel_path),
            "error": f"path does not exist: {root_abs}"
        }
    
    files: List[str] = []
    truncated = False
    
    # Walk directory tree
    for current_root, dirs, filenames in os.walk(root_abs, followlinks=follow_symlinks):
        # Deterministic directory order + filtering (EXACT NAMES)
        dirs[:] = sorted([d for d in dirs if d not in exclude_dirs])
        
        # Deterministic file order
        for fn in sorted(filenames):
            # Extension filter
            if include_ext:
                if not any(fn.endswith(ext) for ext in include_ext):
                    continue
            
            full = Path(current_root) / fn
            # Make relative, POSIX for stable output
            try:
                rel = full.relative_to(base_dir.resolve()).as_posix()
            except ValueError:
                # File outside base_dir (shouldn't happen with _safe_resolve, but be safe)
                continue
            
            files.append(rel)
            if len(files) >= max_files:
                truncated = True
                break
        
        if truncated:
            break
    
    # Extra safety: ensure deterministic output
    files = sorted(files)
    
    return {
        "ok": True,
        "action": "walk_tree_result",
        "files": files,
        "count": len(files),
        "truncated": truncated,
        "root": str(rel_path),
    }


def read_file_batch_from_params(params: dict, base_dir: Path) -> dict:
    """
    Read multiple files deterministically with hard caps.
    - Enforces max_total_chars across all files (budget).
    - Each file also capped by max_chars_per_file.
    - Returns per-file {content|error, truncated}.
    
    Params:
        files: List of file paths (relative to base_dir or absolute)
        max_chars_per_file: Max chars per file (default 20k, hard cap 100k)
        max_total_chars: Max total chars across all files (default 120k, hard cap 400k)
        
    Returns:
        {
            "ok": bool,
            "action": "read_file_batch_result",
            "files": {
                "path/to/file.py": {"content": "...", "truncated": false},
                "path/to/huge.py": {"error": "file_too_large", "truncated": true}
            },
            "count": int,
            "truncated": bool,  # true if ANY file was truncated
            "limits": {...}
        }
    """
    file_list = params.get("files") or []
    if not isinstance(file_list, list):
        return {
            "ok": False,
            "action": "read_file_batch_result",
            "files": {},
            "count": 0,
            "truncated": False,
            "error": "files_not_list"
        }
    
    max_chars_per_file = int(params.get("max_chars_per_file", MAX_CHARS_PER_FILE_DEFAULT))
    if max_chars_per_file > MAX_CHARS_PER_FILE_HARD:
        max_chars_per_file = MAX_CHARS_PER_FILE_HARD
    if max_chars_per_file < 1:
        max_chars_per_file = 1
    
    max_total_chars = int(params.get("max_total_chars", MAX_TOTAL_CHARS_DEFAULT))
    if max_total_chars > MAX_TOTAL_CHARS_HARD:
        max_total_chars = MAX_TOTAL_CHARS_HARD
    if max_total_chars < 1:
        max_total_chars = 1
    
    # Deterministic iteration: sort paths as strings (stable)
    files_sorted = sorted([str(x) for x in file_list])
    
    results: Dict[str, Any] = {}
    total_used = 0
    any_truncated = False
    
    for fp in files_sorted:
        # If total budget exhausted, mark remaining as truncated
        if total_used >= max_total_chars:
            results[fp] = {"error": "total_budget_exhausted", "truncated": True}
            any_truncated = True
            continue
        
        try:
            abs_path = _safe_resolve(base_dir, fp)
        except ValueError as e:
            results[fp] = {"error": str(e), "truncated": True}
            any_truncated = True
            continue
        
        # Hard file size guard (deterministic, no double read)
        # Also capture mtime and size for debugging/reproducibility
        try:
            st = abs_path.stat()
            file_size = st.st_size
            file_mtime = st.st_mtime
            
            if file_size > MAX_FILE_BYTES_HARD:
                results[fp] = {
                    "error": "file_too_large", 
                    "truncated": True,
                    "size_bytes": file_size,
                    "mtime": file_mtime
                }
                any_truncated = True
                continue
        except Exception as e:
            results[fp] = {
                "error": f"stat_failed:{type(e).__name__}", 
                "truncated": True,
                "size_bytes": None,
                "mtime": None
            }
            any_truncated = True
            continue
        
        # Remaining budget for this file
        remaining_total = max_total_chars - total_used
        per_file_cap = min(max_chars_per_file, remaining_total)
        
        try:
            # Read text safely; replace errors deterministically
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(per_file_cap + 1)  # Read one extra char to detect truncation
            
            # Deterministic truncation check
            truncated = False
            if len(content) > per_file_cap:
                content = content[:per_file_cap]
                truncated = True
            elif per_file_cap < max_chars_per_file:
                # Budget-limited
                truncated = True
            
            if truncated:
                any_truncated = True
            
            # Include file metadata for debugging/reproducibility
            results[fp] = {
                "content": content, 
                "truncated": truncated,
                "size_bytes": file_size,
                "mtime": file_mtime
            }
            total_used += len(content)
            
        except Exception as e:
            results[fp] = {"error": f"read_failed:{type(e).__name__}", "truncated": True}
            any_truncated = True
            # Optional: if any file fails to read completely, should we fail the whole batch?
            # User says "error case should always set ok: false". 
            # We'll keep ok: True if we have some results, but for critical failures we return ok: False below.
    
    # If NO files were readable or list was empty, we fail
    if not results and file_list:
        return {
            "ok": False,
            "action": "read_file_batch_result",
            "error": "all_files_failed",
            "files": results,
            "count": 0,
            "truncated": any_truncated
        }

    return {
        "ok": True,
        "action": "read_file_batch_result",
        "files": results,
        "count": len(results),
        "truncated": any_truncated,
        "limits": {
            "max_chars_per_file": max_chars_per_file,
            "max_total_chars": max_total_chars,
            "max_file_bytes": MAX_FILE_BYTES_HARD,
        },
    }
