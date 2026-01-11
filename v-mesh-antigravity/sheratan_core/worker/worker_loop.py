import json
import os
import time
from pathlib import Path
import fnmatch
import requests

RELAY_OUT_DIR = Path("/webrelay_out")
RELAY_IN_DIR = Path("/webrelay_in")

WORKSPACE_ROOT = Path("/workspace")  # Basis für relative Pfade


def list_files_from_params(params: dict) -> dict:
    root = params.get("root", "/workspace/project")
    patterns = params.get("patterns") or ["*"]

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

    files: list[str] = []

    for p in root_path.rglob("*"):
        if not p.is_file():
            continue

        rel = p.relative_to(root_path)
        rel_str = str(rel).replace('\\', '/')  # Normalize path separators
        
        # Match against patterns
        for pattern in patterns:
            matched = False
            
            if pattern.startswith('**/'):
                # Pattern like "**/*.py" - match against full path
                # Remove **/ and match the rest against filename
                file_pattern = pattern[3:]  # Remove "**/
                if fnmatch.fnmatch(rel.name, file_pattern):
                    matched = True
            elif '/' in pattern or '\\' in pattern:
                # Pattern contains path separator - match full relative path
                if fnmatch.fnmatch(rel_str, pattern.replace('\\', '/')):
                    matched = True
            else:
                # Simple pattern like "*.py" - match filename only
                if fnmatch.fnmatch(rel.name, pattern):
                    matched = True
            
            if matched:
                files.append(rel_str)
                break

    return {
        "ok": True,
        "action": "list_files_result",
        "files": files,
        "root": str(root_path),
        "patterns": patterns,
        "info": f"Listed {len(files)} files",
    }


def resolve_file(root: str | None, rel_path: str | None, path: str | None) -> Path | None:
    if root:
        root_path = Path(root)
        if not root_path.is_absolute():
            root_path = WORKSPACE_ROOT / root_path
    else:
        root_path = WORKSPACE_ROOT / "project"

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
        "content": content,
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
        
        return {
            "ok": True,
            "action": "write_file_result",
            "path": str(file_path),
            "mode": mode,
            "message": f"Successfully {action_verb} {len(content)} characters to {file_path.name}",
        }
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

def call_llm_for_plan(user_prompt: str, project_root: str, files: list | None = None) -> dict:
    """
    Ruft dein LLM auf, um einen Plan zu bauen.
    Erwartet ein OpenAI-kompatibles /v1/chat/completions-Interface.
    """
    base_url = os.getenv("SHERATAN_LLM_BASE_URL")
    model = os.getenv("SHERATAN_LLM_MODEL", "gpt-4-mini")
    api_key = os.getenv("SHERATAN_LLM_API_KEY")

    if not base_url:
        # Fallback: deterministischer PoC, wenn kein LLM konfiguriert ist
        print("[worker] No LLM configured, using static fallback plan")
        return {
            "commentary": (
                "No LLM configured, using static plan: list files + read main.py."
            ),
            "steps": [
                {
                    "name": "List project files",
                    "description": "Discover Python files in the project",
                    "kind": "list_files",
                    "params": {
                        "root": project_root,
                        "patterns": ["**/*.py"],
                    },
                    "auto_dispatch": True,
                },
                {
                    "name": "Read main.py",
                    "description": "Inspect the main entrypoint file",
                    "kind": "read_file",
                    "params": {
                        "root": project_root,
                        "rel_path": "main.py",
                    },
                    "auto_dispatch": False,
                },
            ],
        }

    system_prompt = (
        "You are a code-editing agent for the Sheratan workspace. "
        "Given a user request and a project_root, you must create a small plan "
        "as JSON: an array of steps that use tools like list_files, read_file, rewrite_file."
    )

    user_content = {
        "user_prompt": user_prompt,
        "project_root": project_root,
        "hint_files": files or [],
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Return ONLY valid JSON, no prose. "
                    "Schema: {\"commentary\": str, \"steps\": ["
                    "{"
                    "\"name\": str, "
                    "\"description\": str, "
                    "\"kind\": \"list_files\" | \"read_file\" | \"rewrite_file\", "
                    "\"params\": object, "
                    "\"auto_dispatch\": bool"
                    "}"
                    "]}\n\n"
                    f"Input:\n{json.dumps(user_content, indent=2)}"
                ),
            },
        ],
        "temperature": 0.2,
    }

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        print(f"[worker] Calling LLM at {base_url}")
        resp = requests.post(base_url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # OpenAI-kompatibel: erste Wahl aus choices nehmen
        content = data["choices"][0]["message"]["content"]

        # content sollte ein JSON-String im obigen Schema sein
        try:
            plan = json.loads(content)
            print(f"[worker] LLM returned plan with {len(plan.get('steps', []))} steps")
        except json.JSONDecodeError:
            print("[worker] LLM returned non-JSON, falling back to static plan")
            # Im Zweifelsfall harter Fallback
            return {
                "commentary": "LLM returned non-JSON, falling back to static two-step plan.",
                "steps": [
                    {
                        "name": "List project files",
                        "description": "Discover Python files in the project",
                        "kind": "list_files",
                        "params": {
                            "root": project_root,
                            "patterns": ["**/*.py"],
                        },
                        "auto_dispatch": True,
                    },
                    {
                        "name": "Read main.py",
                        "description": "Inspect the main entrypoint file",
                        "kind": "read_file",
                        "params": {
                            "root": project_root,
                            "rel_path": "main.py",
                        },
                        "auto_dispatch": False,
                    },
                ],
            }

        return plan

    except Exception as e:
        print(f"[worker] LLM call failed: {e}, using fallback plan")
        return {
            "commentary": f"LLM call failed: {e}. Using fallback plan.",
            "steps": [
                {
                    "name": "List project files",
                    "description": "Discover Python files",
                    "kind": "list_files",
                    "params": {
                        "root": project_root,
                        "patterns": ["**/*.py"],
                    },
                    "auto_dispatch": True,
                },
            ],
        }


def call_llm_generic(unified_job: dict) -> dict:
    """
    Generischer LLM Call für LCP-basierte Tasks.
    
    Macht einen HTTP Call zu WebRelay mit dem Job Payload,
    und gibt das LCP Result zurück.
    
    Supports two response formats:
    - 'lcp': JSON-based LCP format (default)
    - 'selfloop_markdown': Raw Markdown with A/B/C/D sections
    """
    base_url = os.getenv("SHERATAN_LLM_BASE_URL")
    model = os.getenv("SHERATAN_LLM_MODEL", "gpt-4-mini")
    api_key = os.getenv("SHERATAN_LLM_API_KEY")
    
    if not base_url:
        print("[worker] No SHERATAN_LLM_BASE_URL configured, cannot make LLM call")
        return {
            "ok": False,
            "action": "error",
            "error": "No SHERATAN_LLM_BASE_URL configured"
        }
    
    # Extract payload
    job_id = unified_job.get("job_id", "unknown")
    lcp = unified_job.get("payload", {}) or {}
    mission = lcp.get("mission", {}) or {}
    task = lcp.get("task", {}) or {}
    params = lcp.get("params", {}) or {}
    
    # Check response format (default: lcp)
    response_format = lcp.get("response_format", "lcp")
    
    # Build prompt from job payload
    # If there's a direct prompt field, use it (Self-Loop provides full prompt)
    prompt = lcp.get("prompt") or params.get("prompt")
    
    if not prompt:
        # Build prompt from mission/task context
        mission_desc = mission.get("description", "Complete mission")
        task_kind = task.get("kind", "analyze")
        task_params = task.get("params", {})
        user_request = task_params.get("user_prompt", mission_desc)
        project_root = task_params.get("project_root", "/workspace/project")
        
        # NEW: Strict LCP-compliant prompt
        prompt = f"""You are an autonomous agent in the Sheratan Core system.

YOUR TASK: Create a plan with 2-4 specific, actionable followup jobs based on this request:

USER REQUEST: {user_request}
PROJECT ROOT: {project_root}

CRITICAL RULES:
1. Respond with ONLY valid JSON - NO explanatory text outside JSON
2. NEVER ask questions - create jobs immediately
3. Use EXACTLY this format (no deviations):

{{
  "ok": true,
  "action": "create_followup_jobs",
  "commentary": "Brief one-sentence plan explanation",
  "new_jobs": [
    {{
      "name": "Human-readable job name",
      "description": "What this job does (optional)",
      "kind": "list_files",
      "params": {{"root": "{project_root}", "patterns": ["**/*.py"]}},
      "auto_dispatch": true
    }},
    {{
      "name": "Another job",
      "kind": "read_file",
      "params": {{"root": "{project_root}", "rel_path": "main.py"}},
      "auto_dispatch": false
    }}
  ]
}}

AVAILABLE JOB KINDS (use these EXACT strings):
- "list_files": List files matching patterns
  Required params: {{"root": "/path", "patterns": ["*.py"]}}
  
- "read_file": Read a file's content
  Required params: {{"root": "/path", "rel_path": "file.py"}}
  OR: {{"path": "/absolute/path/file.py"}}
  
- "rewrite_file": Write/update a file
  Required params: {{"root": "/path", "rel_path": "file.py", "new_content": "..."}}

REQUIRED FIELDS in each job:
- "name": string (descriptive job name)
- "kind": string (one of the kinds above)
- "params": object (parameters for the kind)

OPTIONAL FIELDS:
- "description": string
- "auto_dispatch": boolean (default: false)

EXAMPLE for "Analyze Python files in project":
{{
  "ok": true,
  "action": "create_followup_jobs",
  "commentary": "First list all Python files, then read main.py to understand entry point",
  "new_jobs": [
    {{
      "name": "List Python files",
      "description": "Discover all .py files in project",
      "kind": "list_files",
      "params": {{
        "root": "/workspace/project",
        "patterns": ["**/*.py"]
      }},
      "auto_dispatch": true
    }},
    {{
      "name": "Read main.py",
      "kind": "read_file",
      "params": {{
        "root": "/workspace/project",
        "rel_path": "main.py"
      }},
      "auto_dispatch": false
    }}
  ]
}}

NOW CREATE YOUR PLAN (JSON only, no other text):"""
    
    # Build OpenAI-compatible payload with STRICT system prompt
    # BUT: Check if this is WebRelay (expects simple {prompt} format)
    is_webrelay = "webrelay" in base_url.lower() or ":3000" in base_url
    
    if is_webrelay:
        # WebRelay format: just {prompt: "..."}
        payload = {
            "prompt": prompt,
            "session_id": f"worker_{job_id[:8]}" if 'job_id' in locals() else "worker_session"
        }
        
        # For Self-Loop, add response_format hint
        if response_format == "selfloop_markdown":
            payload["response_format"] = "selfloop_markdown"
    else:
        # OpenAI format: {messages: [...]}
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a JSON-only autonomous agent. You MUST ONLY output valid JSON. Never ask questions. Never write explanatory text. Only output the exact JSON structure requested."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}  # Force JSON mode
        }
    
    headers = {}
    if api_key and not is_webrelay:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        print(f"[worker] Calling LLM at {base_url} (format={'webrelay' if is_webrelay else 'openai'})")
        resp = requests.post(base_url, json=payload, headers=headers, timeout=300)  # 5min for Self-Loop
        resp.raise_for_status()
        data = resp.json()
        
        # Extract content based on response format
        if is_webrelay:
            # WebRelay returns: {ok, type, action?, commentary?, new_jobs?, summary?, etc}
            if not data.get("ok"):
                return {
                    "ok": False,
                    "action": "error",
                    "error": data.get("error", "WebRelay returned ok=false")
                }
            
            # Check if this is a Self-Loop Markdown response
            if response_format == "selfloop_markdown":
                # Return raw Markdown response for Self-Loop processing
                markdown_content = data.get("answer", "") or data.get("summary", "")
                print(f"[worker] Self-Loop Markdown response ({len(markdown_content)} chars)")
                return {
                    "ok": True,
                    "action": "selfloop_result",
                    "markdown": markdown_content,
                    "raw_response": data
                }
            
            # WebRelay already returns LCP format, just pass it through
            print(f"[worker] WebRelay returned: type={data.get('type')}, action={data.get('action')}")
            
            # Convert WebRelay response to worker result format
            if data.get("type") == "lcp" and data.get("action") == "create_followup_jobs":
                result = {
                    "ok": True,
                    "action": "create_followup_jobs",
                    "commentary": data.get("commentary", ""),
                    "new_jobs": data.get("new_jobs", [])
                }
            elif data.get("type") == "plain":
                result = {
                    "ok": True,
                    "action": "text_result",
                    "summary": data.get("summary", "")
                }
            else:
                # Return as-is
                result = data
            
            # WebRelay response is already structured, return it directly
            print(f"[worker] ✓ WebRelay LCP response: action={result.get('action')}, jobs={len(result.get('new_jobs', []))}")
            return result
        else:
            # OpenAI-compatible: extract content from first choice
            content = data["choices"][0]["message"]["content"]
            print(f"[worker] LLM returned response ({len(content)} chars)")
        
        # Try to parse as JSON (LCP format)
        try:
            # Strip markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Strip }}} sentinel if present
            if content.endswith("}}}"):
                content = content[:-3].strip()
            
            result = json.loads(content)
            
            # Ensure it has the expected LCP structure
            if not isinstance(result, dict):
                return {
                    "ok": False,
                    "action": "error",
                    "error": "LLM response is not a JSON object",
                    "raw_response": content
                }
            
            # Validate LCP format
            if "action" not in result:
                return {
                    "ok": False,
                    "action": "error",
                    "error": "LLM response missing 'action' field",
                    "raw_response": content
                }
            
            # Ensure new_jobs has correct format with 'kind' field
            if result.get("action") == "create_followup_jobs":
                new_jobs = result.get("new_jobs", [])
                if not isinstance(new_jobs, list):
                    return {
                        "ok": False,
                        "action": "error",
                        "error": "new_jobs must be an array",
                        "raw_response": content
                    }
                
                # Validate each job has required fields
                for idx, job in enumerate(new_jobs):
                    if not isinstance(job, dict):
                        return {
                            "ok": False,
                            "action": "error",
                            "error": f"Job {idx} is not an object",
                            "raw_response": content
                        }
                    
                    if "kind" not in job:
                        return {
                            "ok": False,
                            "action": "error",
                            "error": f"Job {idx} missing required 'kind' field (use 'kind', not 'task')",
                            "raw_response": content
                        }
                    
                    if "params" not in job:
                        return {
                            "ok": False,
                            "action": "error",
                            "error": f"Job {idx} missing required 'params' field",
                            "raw_response": content
                        }
            
            # Add ok: true if not present
            if "ok" not in result:
                result["ok"] = True
            
            print(f"[worker] ✓ Valid LCP response: action={result.get('action')}, jobs={len(result.get('new_jobs', []))}")
            return result
            
        except json.JSONDecodeError as e:
            print(f"[worker] Failed to parse LLM response as JSON: {e}")
            # Return as plain text result
            return {
                "ok": True,
                "action": "text_result",
                "summary": content
            }
    
    except Exception as e:
        print(f"[worker] LLM call failed: {e}")
        return {
            "ok": False,
            "action": "error",
            "error": f"LLM call failed: {type(e).__name__}: {e}"
        }


def run_agent_plan(unified_job: dict) -> dict:
    """
    Ruft ein LLM auf (falls konfiguriert), um aus user_prompt + project_root
    einen Plan zu machen, und übersetzt das in create_followup_jobs.
    """
    lcp = unified_job.get("payload", {}) or {}
    task = lcp.get("task", {}) or {}
    params = task.get("params", {}) or {}

    user_prompt = params.get("user_prompt", "")
    project_root = params.get("project_root", "/workspace/project")

    # Option: hier könntest du vorher schon eine list_files-Discovery machen
    # und dem LLM die Dateiliste mitgeben. Für den Anfang lassen wir das weg:
    plan = call_llm_for_plan(user_prompt=user_prompt, project_root=project_root)

    commentary = plan.get("commentary", "Plan generated by LLM.")
    steps = plan.get("steps", [])

    new_jobs = []
    for step in steps:
        new_jobs.append(
            {
                "name": step.get("name", "Agent step"),
                "description": step.get("description", ""),
                "kind": step.get("kind", "read_file"),
                "params": step.get("params") or {},
                "auto_dispatch": step.get("auto_dispatch", False),
            }
        )

    return {
        "ok": True,
        "action": "create_followup_jobs",
        "commentary": commentary,
        "new_jobs": new_jobs,
        "meta": {
            "user_prompt": user_prompt,
            "project_root": project_root,
        },
    }


def handle_job(unified_job: dict) -> dict:
    """
    unified_job ist das JSON aus <job_id>.job.json>.

    Struktur (vereinfacht):
    {
      "job_id": "...",
      "kind": "llm_call" | "write_file" | ...,
      "payload": {
        "response_format": "lcp",
        "mission": {...},
        "task": {
          "kind": "read_file" | "list_files" | "rewrite_file",
          "params": {...}
        },
        "params": {...}  // Job-spezifische Parameter (z.B. new_content)
      }
    }
    """
    job_id = unified_job.get("job_id")
    job_kind = unified_job.get("kind")

    lcp = unified_job.get("payload", {}) or {}
    task = lcp.get("task", {}) or {}
    task_kind = task.get("kind")
    tool_params = task.get("params", {}) or {}
    job_params = lcp.get("params", {}) or {}
    
    # Merge params: tool_params (from Task) + job_params (from Job payload)
    # job_params takes precedence (allows per-job customization)
    merged_params = {**tool_params, **job_params}

    print(f"[worker] handle_job job_id={job_id} job_kind={job_kind} task_kind={task_kind}")

    if task_kind == "list_files":
        return list_files_from_params(merged_params)

    if task_kind == "read_file":
        return read_file_from_params(merged_params)

    if task_kind == "write_file":
        return write_file_from_params(merged_params)

    if task_kind == "rewrite_file":
        return rewrite_file_from_params(job_id, merged_params, job_params)

    if task_kind == "llm_call":
        return call_llm_generic(unified_job)

    if task_kind == "agent_plan":
        # agent_plan should also use call_llm_generic for WebRelay support
        return call_llm_generic(unified_job)
    
    # Self-Loop Handler - check job_type in multiple locations:
    # 1. payload.params.job_type (nested format)
    # 2. payload.job_type (selfloop API format - job_type at root)
    selfloop_type = job_params.get("job_type") or lcp.get("job_type")
    if selfloop_type == "sheratan_selfloop":
        print(f"[worker] Self-Loop job detected: {job_id}")
        # Self-Loop jobs use WebRelay with special prompt format
        return call_llm_generic(unified_job)

    # Fallback
    return {
        "ok": True,
        "action": "noop",
        "message": (
            f"Completed job {job_id} with kind={job_kind} "
            f"(no specific handler for task_kind={task_kind})"
        ),
        "payload_echo": lcp,
    }

def main_loop():
    print("Worker loop started, watching", RELAY_OUT_DIR)
    RELAY_OUT_DIR.mkdir(parents=True, exist_ok=True)
    RELAY_IN_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        for path in list(RELAY_OUT_DIR.glob("*.job.json")):
            try:
                raw = path.read_text(encoding="utf-8")
                unified_job = json.loads(raw)
            except Exception as e:
                print("[worker] Failed to read job file", path, e)
                path.unlink(missing_ok=True)
                continue

            job_id = unified_job.get("job_id") or path.stem.split(".")[0]
            print(f"[worker] Processing job file {path} (job_id={job_id})")

            try:
                result = handle_job(unified_job)
            except Exception as e:
                print("[worker] ERROR in handle_job for", job_id, e)
                result = {
                    "ok": False,
                    "action": "error",
                    "error": f"Exception in worker: {type(e).__name__}: {e}",
                }

            result_file = RELAY_IN_DIR / f"{job_id}.result.json"
            try:
                result_file.write_text(json.dumps(result), encoding="utf-8")
                print("[worker] Wrote result file", result_file)
                
                # Notify Core to sync result and process follow-ups
                try:
                    core_url = os.getenv("SHERATAN_CORE_URL", "http://core:8000")
                    sync_url = f"{core_url}/api/jobs/{job_id}/sync"
                    sync_resp = requests.post(sync_url, timeout=5)
                    if sync_resp.ok:
                        print(f"[worker] ✓ Notified Core to sync job {job_id[:12]}...")
                    else:
                        print(f"[worker] ⚠ Core sync returned {sync_resp.status_code}")
                except Exception as e:
                    print(f"[worker] ⚠ Failed to notify Core: {e}")
                    # Don't crash - Core will eventually poll for result
                
            except Exception as e:
                print("[worker] FAILED to write result file", result_file, e)

            print("[worker] Done job", job_id)
            path.unlink(missing_ok=True)

        time.sleep(1.0)


if __name__ == "__main__":
    main_loop()
