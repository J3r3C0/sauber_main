import json
import sys
import os
import time
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 for Windows shell logging
# Force UTF-8 for Windows shell logging
_original_print = print
def safe_print(*args, **kwargs):
    try:
        _original_print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fallback to ASCII with replacement for problematic chars
        new_args = []
        for arg in args:
            if isinstance(arg, str):
                new_args.append(arg.encode('ascii', errors='replace').decode('ascii'))
            else:
                new_args.append(arg)
        _original_print(*new_args, **kwargs)

# Override print with safe_print
print = safe_print

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, Exception):
        pass

# Load environment variables from .env
load_dotenv()

# Import mesh registry from local mesh/registry module
import requests
import fnmatch
import sys
from pathlib import Path

# Add parent directory to path since we are in worker/
_this_dir = Path(__file__).parent
_project_root = _this_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from mesh.registry.mesh_registry import WorkerRegistry, WorkerInfo, WorkerCapability
except ImportError:
    # Minimal fallback
    WorkerRegistry = None
    WorkerInfo = None
    WorkerCapability = None
    # Fallback to local or direct import if needed
    try:
        from mesh_registry import WorkerRegistry, WorkerInfo, WorkerCapability
    except ImportError:
        WorkerRegistry = None

# Environment-aware paths
# Standard location in the clean structure: data/
BASE_DIR = Path(__file__).parent.parent
RELAY_OUT_DIR = Path(os.getenv("RELAY_OUT_DIR", str(BASE_DIR / "data" / "webrelay_out")))
RELAY_IN_DIR = Path(os.getenv("RELAY_IN_DIR", str(BASE_DIR / "data" / "webrelay_in")))
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", str(BASE_DIR)))
WORKER_ID = os.getenv("WORKER_ID", "default_worker")

class StateStore:
    """Persistent store for worker state and job idempotency."""
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_cache (
                    job_id TEXT PRIMARY KEY,
                    result TEXT,
                    timestamp TEXT
                )
            """)
            conn.commit()

    def get_job_result(self, job_id: str) -> Optional[dict]:
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("SELECT result FROM job_cache WHERE job_id = ?", (job_id,)).fetchone()
                return json.loads(row[0]) if row else None
        except Exception:
            return None

    def save_job_result(self, job_id: str, result: dict):
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO job_cache (job_id, result, timestamp) VALUES (?, ?, ?)",
                    (job_id, json.dumps(result), datetime.utcnow().isoformat() + "Z")
                )
                conn.commit()
        except Exception as e:
            print(f"[state] Error saving result: {e}")

# Initialize StateStore
STATE_DB = BASE_DIR / "data" / f"worker_state_{WORKER_ID}.db"
state_store = StateStore(STATE_DB)

def truncate_result(content: str, threshold: int = 1000, full_content: bool = False) -> dict:
    """
    Returns truncated content + metadata if over threshold,
    otherwise returns just the content.
    If full_content is True, truncation is bypassed.
    """
    if full_content or len(content) <= threshold:
        return {"content": content}
    
    return {
        "content": content[:500] + "\n... [TRUNCATED] ...\n" + content[-500:],
        "_metadata": {
            "char_count": len(content),
            "word_count": len(content.split()),
            "line_count": len(content.splitlines()),
            "is_truncated": True
        }
    }


def list_files_from_params(params: dict) -> dict:
    # Support multiple parameter names for the root path
    root = params.get("root") or params.get("root_path") or params.get("path") or params.get("project_root") or "."
    
    # Path Sanitization: Strip common LLM sham-paths
    if isinstance(root, str):
        for sham in ["/workspace/project/", "/workspace/", "/app/"]:
            if root.startswith(sham):
                root = root[len(sham):]
                break

    patterns = params.get("patterns") or ["*"]
    recursive = params.get("recursive", False)

    # Boss Directive: Ignore system-internal directories that bloat context
    DEFAULT_EXCLUDES = {
        ".git", ".chrome-debug", "node_modules", "__pycache__", 
        ".venv", "venv", ".next", "dist", "build", ".DS_Store",
        "data/webrelay_out", "data/webrelay_in"
    }

    root_path = Path(root)
    if not root_path.is_absolute():
        root_path = WORKSPACE_ROOT / root_path

    if not root_path.exists():
        return {
            "ok": False,
            "action": "list_files_result",
            "error": f"root path does not exist: {root_path}",
            "root": str(root_path),
            "patterns": patterns,
        }

    files_set: set[str] = set()
    skipped_count = 0
    
    for pattern in patterns:
        try:
            # If pattern contains ** or recursive is true, use recursive search
            is_recursive_pattern = "**" in pattern or recursive
            
            # Use glob/rglob based on recursion needs
            search_func = root_path.rglob if is_recursive_pattern else root_path.glob
            
            # Clean pattern for pathlib (strip leading slash)
            clean_pattern = pattern.lstrip('/')
            
            for p in search_func(clean_pattern):
                if p.is_file():
                    try:
                        rel = p.relative_to(root_path)
                        rel_str = str(rel).replace('\\', '/')
                        
                        # Exclusion Filter
                        is_excluded = False
                        for part in rel.parts:
                            if part in DEFAULT_EXCLUDES:
                                is_excluded = True
                                break
                        
                        if is_excluded:
                            skipped_count += 1
                            continue
                            
                        files_set.add(rel_str)
                    except ValueError:
                        continue # Outside root
        except Exception as e:
            print(f"[worker] Invalid pattern '{pattern}': {e}")
            continue

    files = sorted(list(files_set))
    files_str = "\n".join(files)
    
    res = {
        "ok": True,
        "action": "list_files_result",
        "root": str(root_path),
        "patterns": patterns,
        "recursive": recursive,
        "info": f"Listed {len(files)} files (skipped {skipped_count} internal/excluded files)",
        "files": files,
    }
    # Add truncated string version for easier LLM consumption
    res.update(truncate_result(files_str))
    return res


def resolve_file(root: str | None, rel_path: str | None, path: str | None) -> Path | None:
    # Path Sanitization for root and path
    if isinstance(root, str):
        for sham in ["/workspace/project/", "/workspace/", "/app/"]:
            if root.startswith(sham):
                root = root[len(sham):]
                break
    if isinstance(path, str):
        for sham in ["/workspace/project/", "/workspace/", "/app/"]:
            if path.startswith(sham):
                path = path[len(sham):]
                break

    if root:
        root_path = Path(root)
        if not root_path.is_absolute():
            root_path = WORKSPACE_ROOT / root_path
    else:
        root_path = WORKSPACE_ROOT

    if rel_path is not None:
        file_path = root_path / rel_path
    elif path is not None:
        p = Path(path)
        file_path = p if p.is_absolute() else (root_path / p)
    else:
        print("[worker] no rel_path or path given")
        return None

    return file_path


def read_file_from_params(params: dict) -> dict:
    root = params.get("root")
    rel_path = params.get("rel_path")
    path = params.get("path")

    file_path = resolve_file(root, rel_path, path)
    if file_path is None:
        return {
            "ok": False,
            "action": "read_file_result",
            "error": "missing path / rel_path",
        }

    if not file_path.exists():
        return {
            "ok": False,
            "action": "read_file_result",
            "error": f"file does not exist: {file_path}",
        }

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "ok": False,
            "action": "read_file_result",
            "error": f"failed to read file: {file_path}",
            "details": str(e),
        }

    return {
        "ok": True,
        "action": "read_file_result",
        "path": str(file_path),
        **truncate_result(content, full_content=params.get("full_content", False))
    }


def read_file_batch_from_params(params: dict) -> dict:
    """Read multiple files in a single job.
    
    Params:
        paths: List of file paths to read
        root: Optional root directory
        limit: Optional max files (default 10)
    """
    paths = params.get("paths") or params.get("files") or []
    # If paths is a string (e.g. from a malformed LLM response), split it
    if isinstance(paths, str):
        paths = [p.strip() for p in paths.split(",") if p.strip()]
        
    limit = params.get("limit", 10)
    root = params.get("root")
    
    results = {}
    any_truncated = False
    
    for p_str in paths[:limit]:
        # Minimal individual read
        res = read_file_from_params({"root": root, "path": p_str, "full_content": params.get("full_content")})
        if res.get("ok"):
            results[p_str] = {
                "content": res.get("content"),
                "truncated": res.get("_metadata", {}).get("is_truncated", False)
            }
            if results[p_str]["truncated"]:
                any_truncated = True
    
    return {
        "ok": True,
        "action": "read_file_batch_result",
        "files": results,
        "truncated": any_truncated,
        "count": len(results),
        "limits": {"max_files": limit}
    }


def write_file_from_params(params: dict) -> dict:
    """Write content to a file, creating it if it doesn't exist.
    
    Supports mode parameter:
    - mode="overwrite" (default): Replace file contents
    - mode="append": Append to existing file
    """
    root = params.get("root")
    rel_path = params.get("rel_path")
    path = params.get("path")
    content = params.get("content", "")
    mode = params.get("mode", "overwrite")  # "overwrite" or "append"

    file_path = resolve_file(root, rel_path, path)
    if file_path is None:
        return {
            "ok": False,
            "action": "write_file_result",
            "error": "missing path / rel_path",
        }

    try:
        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write or append content
        if mode == "append" and file_path.exists():
            # Read existing content and append
            existing = file_path.read_text(encoding="utf-8")
            final_content = existing + content
            file_path.write_text(final_content, encoding="utf-8")
            action_verb = "appended"
        else:
            # Overwrite (default behavior)
            file_path.write_text(content, encoding="utf-8")
            action_verb = "wrote"
        
        result = {
            "ok": True,
            "action": "write_file_result",
            "path": str(file_path),
            "mode": mode,
            "message": f"Successfully {action_verb} {len(content)} characters to {file_path.name}",
        }
        
        if mode == "append":
            # Per user request: return FULL content after append
            full_content = file_path.read_text(encoding="utf-8")
            result.update(truncate_result(full_content))
            
        return result
    except Exception as e:
        return {
            "ok": False,
            "action": "write_file_result",
            "error": f"failed to write file: {file_path}",
            "details": str(e),
        }


def rewrite_file_from_params(job_id: str | None, tool_params: dict, job_params: dict) -> dict:
    root = tool_params.get("root")
    rel_path = tool_params.get("rel_path")
    path = tool_params.get("path")

    # new_content kann entweder in job_params oder tool_params stehen
    new_content = job_params.get("new_content", tool_params.get("new_content"))

    if not isinstance(new_content, str):
        return {
            "ok": False,
            "action": "rewrite_file_result",
            "error": "missing new_content in params",
        }

    file_path = resolve_file(root, rel_path, path)
    if file_path is None:
        return {
            "ok": False,
            "action": "rewrite_file_result",
            "error": "missing path / rel_path",
        }

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(new_content, encoding="utf-8")
    except Exception as e:
        return {
            "ok": False,
            "action": "rewrite_file_result",
            "error": f"failed to write file: {file_path}",
            "details": str(e),
        }

    preview = new_content[:200]

    return {
        "ok": True,
        "action": "rewrite_file_result",
        "path": str(file_path),
        "info": f"rewrote file for job {job_id}",
        "new_content_preview": preview,
    }


def pdf_to_json_from_params(params: dict) -> dict:
    """
    Extract text content from PDF and return as structured JSON.
    
    Params:
        path: Absolute or relative path to PDF file
        root: Optional root directory
        extract_tables: Optional, attempt to extract tables (default: false)
        max_pages: Optional, limit pages to extract (default: all)
    
    Returns:
        JSON with extracted text, page count, and optional table data
    """
    root = params.get("root")
    path = params.get("path")
    rel_path = params.get("rel_path")
    extract_tables = params.get("extract_tables", False)
    max_pages = params.get("max_pages")
    
    file_path = resolve_file(root, rel_path, path)
    if file_path is None:
        return {
            "ok": False,
            "action": "pdf_to_json_result",
            "error": "missing path / rel_path"
        }
    
    if not file_path.exists():
        return {
            "ok": False,
            "action": "pdf_to_json_result",
            "error": f"PDF file does not exist: {file_path}"
        }
    
    if not str(file_path).lower().endswith('.pdf'):
        return {
            "ok": False,
            "action": "pdf_to_json_result",
            "error": f"Not a PDF file: {file_path}"
        }
    
    try:
        # Try to import PDF library
        try:
            import PyPDF2
            use_pypdf2 = True
        except ImportError:
            try:
                import pdfplumber
                use_pypdf2 = False
            except ImportError:
                # Fallback: return file info without extraction
                return {
                    "ok": True,
                    "action": "pdf_to_json_result",
                    "path": str(file_path),
                    "warning": "No PDF library installed (PyPDF2 or pdfplumber). Install with: pip install PyPDF2",
                    "file_size_bytes": file_path.stat().st_size,
                    "text": None,
                    "pages": None
                }
        
        pages_data = []
        full_text = []
        
        if use_pypdf2:
            # Use PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)
                pages_to_read = min(total_pages, max_pages) if max_pages else total_pages
                
                for i in range(pages_to_read):
                    page = reader.pages[i]
                    text = page.extract_text() or ""
                    pages_data.append({
                        "page": i + 1,
                        "text": text,
                        "char_count": len(text)
                    })
                    full_text.append(text)
        else:
            # Use pdfplumber
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                pages_to_read = min(total_pages, max_pages) if max_pages else total_pages
                
                for i in range(pages_to_read):
                    page = pdf.pages[i]
                    text = page.extract_text() or ""
                    page_data = {
                        "page": i + 1,
                        "text": text,
                        "char_count": len(text)
                    }
                    
                    # Extract tables if requested
                    if extract_tables:
                        tables = page.extract_tables()
                        if tables:
                            page_data["tables"] = tables
                    
                    pages_data.append(page_data)
                    full_text.append(text)
        
        combined_text = "\n\n".join(full_text)
        
        return {
            "ok": True,
            "action": "pdf_to_json_result",
            "path": str(file_path),
            "total_pages": total_pages,
            "pages_extracted": len(pages_data),
            "total_chars": len(combined_text),
            "text": combined_text,
            "pages": pages_data,
            "has_tables": any("tables" in p for p in pages_data)
        }
        
    except Exception as e:
        return {
            "ok": False,
            "action": "pdf_to_json_result",
            "error": f"Failed to extract PDF: {type(e).__name__}: {e}",
            "path": str(file_path)
        }


# ------------------------------------------------------------------ #


# Simulation Mode: Path to simulation responses
SIMULATION_RESPONSES_DIR = Path(__file__).parent / "simulation_responses"


def _get_simulation_response(unified_job: dict) -> dict:
    """Return deterministic simulation response for testing."""
    lcp = unified_job.get("payload", {}) or {}
    job_params = lcp.get("params", {}) or {}
    task = lcp.get("task", {}) or {}
    task_kind = task.get("kind", "")
    job_type = job_params.get("job_type") or lcp.get("job_type")
    
    if job_type == "sheratan_selfloop":
        sim_file = SIMULATION_RESPONSES_DIR / "selfloop.json"
    elif task_kind == "agent_plan":
        sim_file = SIMULATION_RESPONSES_DIR / "agent_plan.json"
    elif task_kind == "list_files":
        sim_file = SIMULATION_RESPONSES_DIR / "list_files.json"
    else:
        sim_file = SIMULATION_RESPONSES_DIR / "llm_call.json"
    
    if sim_file.exists():
        try:
            with open(sim_file, "r", encoding="utf-8") as f:
                response = json.load(f)
            response["_simulation"] = True
            job_id = unified_job.get("job_id", "unknown")
            print(f"[worker] 🎭 SIMULATION: Loaded {sim_file.name} for {job_id}")
            return response
        except Exception as e:
            print(f"[worker] 🎭 SIMULATION: Failed to load {sim_file}: {e}")
    
    return {"ok": True, "action": "text_result", "text": "[SIMULATION] Fallback", "_simulation": True}


def call_llm_generic(unified_job: dict) -> dict:
    """
    Generischer LLM Call für LCP-basierte Tasks.
    
    Delegiert das Prompt-Building an den WebRelay (/api/job/submit), 
    indem der gesamte unified_job gesendet wird.
    """
    # SIMULATION MODE
    simulation_mode = os.getenv("SHERATAN_SIMULATION_MODE", "").lower() == "true"
    if simulation_mode:
        return _get_simulation_response(unified_job)
    
    base_url = os.getenv("SHERATAN_LLM_BASE_URL")
    if base_url:
        base_url = base_url.strip()
    model = os.getenv("SHERATAN_LLM_MODEL", "gpt-4-mini")
    api_key = os.getenv("SHERATAN_LLM_API_KEY")
    
    if not base_url:
        print("[worker] No SHERATAN_LLM_BASE_URL configured, cannot make LLM call")
        return {"ok": False, "action": "error", "error": "No SHERATAN_LLM_BASE_URL configured"}
    
    # WebRelay Check
    is_webrelay_submit = "/api/job/submit" in base_url.lower()
    
    try:
        if is_webrelay_submit:
            # V2.1 Weg: Wir schicken den ganzen Job. 
            # Der WebRelay nutzt seinen JobRouter (Iteration 1: full rules, Iteration 2+: minimal).
            print(f"[worker] Sending job to WebRelay at {base_url}...")
            print(f"[worker] Payload keys: {list(unified_job.keys())}")
            resp = requests.post(base_url, json=unified_job, timeout=300)
            print(f"[worker] WebRelay responded with status {resp.status_code}")
        else:
            # Legacy/External Weg: Wir müssen selbst ein Prompt bauen (nicht empfohlen für v2.1)
            print("[worker] Using legacy prompting for external LLM (OpenAI style)...")
            prompt = f"Mission: {unified_job.get('payload', {}).get('mission', {}).get('description', '')}\nTask: {unified_job.get('payload', {}).get('task', {}).get('name', '')}\nRespond in LCP format."
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            }
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            resp = requests.post(base_url, json=payload, headers=headers, timeout=300)

        resp.raise_for_status()
        data = resp.json()

        # Transformation: WebRelay (v2.1) → Worker Result
        if is_webrelay_submit:
            # WebRelay submit returns a UnifiedResult: {ok, convoUrl, action, commentary, new_jobs, ...}
            # Wir mappen das zurück in das Format, das der Core erwartet.
            # WICHTIG: Wir geben ALLES zurück, was der WebRelay geliefert hat (inkl. summary/text)
            result = {
                "ok": data.get("ok", True),
                "action": data.get("action", "create_followup_jobs"),
                "commentary": data.get("commentary", "Plan updated by agent"),
                "new_jobs": data.get("new_jobs", []),
                "convoUrl": data.get("convoUrl"),
                "_webrelay_response": True,
                "worker_id": WORKER_ID
            }
            # Ergänze fehlende Felder (wie summary, text, etc. vom Parser)
            for k, v in data.items():
                if k not in result:
                    result[k] = v
            return result
        else:
            # Legacy OpenAI parsing
            content = data["choices"][0]["message"]["content"]
            try:
                return json.loads(content)
            except:
                return {"ok": True, "action": "text_result", "summary": content}

    except Exception as e:
        print(f"[worker] call_llm_generic FAILED: {e}")
        return {"ok": False, "action": "error", "error": str(e)}



# ------------------------------------------------------------------ #


WORKER_ID = os.getenv("WORKER_ID", "default_worker")


def handle_job(unified_job: dict) -> dict:
    """
    unified_job ist das JSON aus <job_id>.job.json>.
    """
    job_id = unified_job.get("job_id")
    
    # 1. Idempotency Check
    cached = state_store.get_job_result(job_id)
    if cached:
        print(f"[worker] ♻ Returning cached result for job {job_id[:12]}...")
        return cached

    job_kind = unified_job.get("kind")

    lcp = unified_job.get("payload", {}) or {}
    task = lcp.get("task", {}) or {}
    task_kind = task.get("kind")
    tool_params = task.get("params", {}) or {}
    job_params = lcp.get("params", {}) or {}
    
    # Merge params: tool_params (from Task) + job_params (from Job payload)
    # job_params takes precedence (allows per-job customization)
    merged_params = {**tool_params, **job_params}

    print(f"[worker] handle_job job_id={job_id} job_kind={job_kind} task_kind={task_kind} worker={WORKER_ID}")

    # Standard handlers
    result = {"ok": True}
    if task_kind == "list_files" or task_kind == "walk_tree":
        result = list_files_from_params(merged_params)
    elif task_kind == "read_file":
        result = read_file_from_params(merged_params)
    elif task_kind == "read_file_batch":
        result = read_file_batch_from_params(merged_params)
    elif task_kind == "write_file":
        result = write_file_from_params(merged_params)
    elif task_kind == "rewrite_file":
        result = rewrite_file_from_params(job_id, merged_params, job_params)
    elif task_kind == "pdf_to_json":
        result = pdf_to_json_from_params(merged_params)
    elif task_kind == "llm_call" or task_kind == "agent_plan":
        result = call_llm_generic(unified_job)
    elif job_params.get("job_type") or lcp.get("job_type") == "sheratan_selfloop":
        print(f"[worker] Self-Loop job detected: {job_id}")
        result = call_llm_generic(unified_job)
    else:
        # Fallback
        result = {
            "ok": True,
            "action": "noop",
            "message": f"Completed job {job_id} with kind={job_kind} (no specific handler)",
            "payload_echo": lcp,
        }

    # IMPORTANT: Include worker_id in the result for payment confirmation
    if isinstance(result, dict):
        result["worker_id"] = WORKER_ID
    
    # 2. Persist Result for Idempotency
    if result.get("ok", False):
        state_store.save_job_result(job_id, result)
    
    return result

def main_loop():
    print(f"--- Sheratan Worker 2.0 Starting (ID: {WORKER_ID}) ---")
    print(f"[worker] Monitoring {RELAY_OUT_DIR}")
    
    # --- AUTO-REGISTRATION ---
    print(f"[worker] Debug: WorkerRegistry is {WorkerRegistry}")
    if WorkerRegistry:
        try:
            registry_file = Path(__file__).parent.parent / "mesh" / "registry" / "workers.json"
            print(f"[worker] Debug: Registry file path: {registry_file}")
            registry = WorkerRegistry(registry_file)
            
            # Capability: File operations + LLM calls
            capabilities = [
                WorkerCapability(kind="list_files", cost=10),
                WorkerCapability(kind="read_file", cost=10),
                WorkerCapability(kind="write_file", cost=50),
                WorkerCapability(kind="patch_file", cost=40),
                WorkerCapability(kind="pdf_to_json", cost=20),
                WorkerCapability(kind="agent_plan", cost=100),
                WorkerCapability(kind="llm_call", cost=100),
                WorkerCapability(kind="walk_tree", cost=20),
                WorkerCapability(kind="read_file_batch", cost=50),
            ]
            
            registry.register(WorkerInfo(
                worker_id=WORKER_ID,
                capabilities=capabilities,
                status="online"
            ))
            print(f"[worker] ✓ Registered with ID {WORKER_ID} and {len(capabilities)} capabilities")
        except Exception as e:
            print(f"[worker] ⚠ Registration failed: {e}")
            import traceback
            traceback.print_exc()
    # -------------------------


    RELAY_OUT_DIR.mkdir(parents=True, exist_ok=True)
    RELAY_IN_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        for path in list(RELAY_OUT_DIR.glob("*.job.json")):
            try:
                raw = path.read_text(encoding="utf-8")
                unified_job = json.loads(raw)
            except Exception as e:
                print("[worker] Failed to read job file", path, e)
                # If we cannot read it, we cannot check worker_id, so we skip and don't delete
                continue

            job_id = unified_job.get("job_id") or path.stem.split(".")[0]
            target_worker = unified_job.get("worker_id")
            
            # --- WORKER ARBITRAGE FILTERING ---
            if target_worker and target_worker != WORKER_ID:
                # This job is for another worker, skip it!
                continue
            # -----------------------------------

            print(f"[worker] Processing job file {path} (job_id={job_id})")

            try:
                result = handle_job(unified_job)
            except Exception as e:
                print("[worker] ERROR in handle_job for", job_id, e)
                result = {
                    "ok": False,
                    "action": "error",
                    "error": f"Exception in worker: {type(e).__name__}: {e}",
                    "worker_id": WORKER_ID
                }

            result_file = RELAY_IN_DIR / f"{job_id}.result.json"
            try:
                result_file.write_text(json.dumps(result), encoding="utf-8")
                print("[worker] Wrote result file", result_file)
                
                # Notify Core to sync result and process follow-ups
                try:
                    core_url = os.getenv("SHERATAN_CORE_URL", "http://127.0.0.1:8001")
                    sync_url = f"{core_url}/api/jobs/{job_id}/sync"
                    sync_resp = requests.post(sync_url, timeout=10)
                    if sync_resp.ok:
                        print(f"[worker] ✓ Notified Core to sync job {job_id[:12]}...")
                    else:
                        print(f"[worker] ⚠ Core sync returned {sync_resp.status_code}")
                except Exception as e:
                    print(f"[worker] ⚠ Failed to notify Core: {e}")
                
            except Exception as e:
                print("[worker] FAILED to write result file", result_file, e)

            print("[worker] Done job", job_id)
            path.unlink(missing_ok=True)

        time.sleep(1.0)


if __name__ == "__main__":
    main_loop()
