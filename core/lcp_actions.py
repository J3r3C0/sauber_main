# sheratan_core_v2/lcp_actions.py
# sheratan_core_v2/lcp_actions.py

"""
LCP Action Interpreter for autonomous mission execution.

Verarbeitet LCP-Resultate des Workers und erzeugt automatisch Folge-Jobs.

Unterstützte Actions (Core2 LCP):

- list_files_result:
    {
      "ok": true,
      "action": "list_files_result",
      "files": ["path/to/file1.py", "path/to/file2.py"]
    }
    → Erstellt analyze_file-Jobs

- create_followup_jobs:
    {
      "ok": true,
      "action": "create_followup_jobs",
      "new_jobs": [
        {"task": "list_files", "params": {...}},
        ...
      ]
    }
    → Erstellt neue Tasks / Jobs gemäß new_jobs-Liste

Andere Actions (write_file, patch_file, ...) erzeugen aktuell keine Auto-Jobs.
"""

from __future__ import annotations
import json
import copy
import sys
from typing import Any, Dict, List

# Force UTF-8 for Windows shell logging
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from core import models
from core import storage
from core.webrelay_bridge import WebRelayBridge
from core.metrics_client import record_module_call

# Self-Loop integration (purged legacy imports)
from core.robust_parser import extract_lcp_response, validate_lcp_response, create_safe_mode_diagnostic_jobs


class LCPActionInterpreter:
    """Interpretiert Worker-LCP-Resultate und erzeugt Folgejobs."""

    def __init__(self, bridge: WebRelayBridge) -> None:
        self.bridge = bridge
        self._consecutive_errors = 0
        self._safe_mode_threshold = 3  # Enter safe mode after 3 consecutive errors

    # ------------------------------------------------------------------ #
    # Safe Mode Diagnostics
    # ------------------------------------------------------------------ #
    def enter_safe_mode(
        self, 
        job: models.Job, 
        error_context: Dict[str, Any]
    ) -> List[models.Job]:
        """
        Enter Safe-Mode and create diagnostic jobs instead of stopping.
        
        Args:
            job: The job that triggered safe mode
            error_context: Information about the errors
            
        Returns:
            List of diagnostic jobs to analyze the problem
        """
        print(f"⚠️ SAFE MODE: Creating diagnostic jobs for error analysis...")
        
        # Get parent task/mission
        task = storage.get_task(job.task_id)
        if not task:
            print("[lcp_actions] Safe mode: No task found, cannot create diagnostics")
            return []
        
        mission = storage.get_mission(task.mission_id)
        
        # Create diagnostic jobs using robust_parser helper
        diagnostic_specs = create_safe_mode_diagnostic_jobs(error_context)
        created_jobs = []
        
        for spec in diagnostic_specs:
            kind = spec.get("kind", "llm_call")
            
            # Find or create diagnostic task
            diag_task = storage.find_task_by_name(mission.id if mission else task.mission_id, "diagnostic")
            if not diag_task:
                task_create = models.TaskCreate(
                    name="diagnostic",
                    description="Safe-mode diagnostic analysis",
                    kind="diagnostic",
                    params={}
                )
                diag_task = models.Task.from_create(mission.id if mission else task.mission_id, task_create)
                storage.create_task(diag_task)
            
            # Create diagnostic job
            jc = models.JobCreate(payload=spec.get("params", {}))
            diag_job = models.Job.from_create(diag_task.id, jc)
            storage.create_job(diag_job)
            
            # Dispatch
            self.bridge.enqueue_job(diag_job.id)
            created_jobs.append(diag_job)
            print(f"  🔍 Diagnostic job created: {spec.get('name', kind)}")
        
        # Reset error counter after entering safe mode
        self._consecutive_errors = 0
        
        return created_jobs

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def handle_job_result(self, job: models.Job) -> List[models.Job]:
        res = job.result
        print(f"[lcp_actions] 🔍 Analyzing result for job {job.id[:8]} (action={res.get('action') if isinstance(res, dict) else 'non-dict'})")
        
        # Try robust parsing if result is not a valid dict OR is a "text_result" wrapper
        is_text_wrapper = isinstance(res, dict) and res.get("action") == "text_result"
        if not isinstance(res, dict) or is_text_wrapper:
            # Determine what to parse: the whole thing (if string) or the summary (if wrapper)
            text_to_parse = res if isinstance(res, str) else res.get("summary", "")
            
            if text_to_parse:
                extracted, attempts = extract_lcp_response(text_to_parse)
                if extracted:
                    print(f"[lcp_actions] Robust parser recovered JSON from {res.get('action') if is_text_wrapper else 'raw result'}")
                    res = extracted
                    # Update job result with parsed version
                    job.result = res
                else:
                    if not is_text_wrapper: # If it's a wrapper, we might still want to proceed with the dict
                        print(f"[lcp_actions] Robust parser failed: {attempts}")
                        return []
        
        # Validate LCP format
        is_valid, issues = validate_lcp_response(res)
        if not is_valid:
            print(f"[lcp_actions] LCP validation issues: {issues}")
            # Still try to process if we have partial data

        # Wenn ok == False → already handled in WebRelayBridge (status=failed).
        if not res.get("ok", False):
            return []

        action = res.get("action")
        # Robustness: If action is missing but new_jobs exists, default to 'create_followup_jobs'
        if not action and res.get("new_jobs"):
            action = "create_followup_jobs"
            print(f"[lcp_actions] 🛠️ Defaulting missing action to 'create_followup_jobs' since {len(res.get('new_jobs'))} jobs found.")
        
        if not isinstance(action, str):
            # Check for plural 'actions' (LCP v2 list style)
            if isinstance(res.get("actions"), list) and res.get("actions"):
                print(f"[lcp_actions] ℹ️ Found plural actions list ({len(res.get('actions'))} items). Processing sequence...")
                action = "execute_lcp_actions"
            else:
                # If it's valid OK but no action recognized, we continue to Boss Directive 5.0
                print(f"[lcp_actions] ⚠️ No explicit action string found in result. Skipping specialized handlers.")
                action = None

        # --- PHASE 1: AUTOMATED PROGRESS LOGGING ---
        try:
            task = storage.get_task(job.task_id)
            if task:
                mission_id = task.mission_id
                mission_dir = storage.DATA_DIR / "missions"
                progress_file = mission_dir / f"{mission_id}_progress.md"
                
                if progress_file.exists():
                    from datetime import datetime
                    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    status = "OK" if res.get("ok") else "FAILED"
                    # Simple summary of what happened
                    summary = f"[{ts}] Tool: {task.kind} | Status: {status}"
                    if action == "list_files_result":
                        summary += f" | Count: {len(res.get('files', []))}"
                    elif action == "create_followup_jobs":
                        summary += f" | New Jobs: {len(res.get('new_jobs', []))}"
                    
                    with progress_file.open("a", encoding="utf-8") as f:
                        f.write(summary + "\n")
                    print(f"[lcp_actions] Auto-logged progress for mission {mission_id[:8]}")
        except Exception as e:
            print(f"[lcp_actions] Warning: Progress logging failed: {e}")
        # --------------------------------------------

        created_jobs = []


        if action == "create_followup_jobs":
            print(f"[lcp_actions] ➡️ Handling create_followup_jobs with {len(res.get('new_jobs', []))} items")
            spec_list = res.get("new_jobs") or []
            if not isinstance(spec_list, list):
                return []
            created_jobs.extend(self._handle_followups(job, spec_list))

        elif action == "execute_lcp_actions":
            # LCP v2.1 plural actions support
            actions_list = res.get("actions") or []
            print(f"[lcp_actions] ➡️ Executing {len(actions_list)} plural actions")
            for act in actions_list:
                act_kind = act.get("kind")
                act_params = act.get("payload") or act.get("params") or {}
                
                if act_kind == "create_followup_jobs":
                    created_jobs.extend(self._handle_followups(job, act_params.get("new_jobs") or []))
                elif act_kind == "mission_complete":
                     action = "mission_complete" # Trigger the completion logic below
                # ... other plural actions could be handled here
        
        if not created_jobs and action in ["show_mission", "show_plan"]:
            self._handle_show_mission(job) # Updates job result

        elif not created_jobs and action == "show_progress":
            self._handle_show_progress(job) # Updates job result

        elif not created_jobs and action == "create_mission":
            created_jobs.extend(self._handle_create_mission(job, res))

        if action == "mission_complete" or action == "analysis_result":
            # Handled by setting mission status etc.
            print(f"🏁 Mission complete signal received: {action}")
            task = storage.get_task(job.task_id)
            if task:
                mission = storage.get_mission(task.mission_id)
                if mission:
                    print(f"✅ Mission '{mission.title}' marked as completed via LCP.")
                    mission.status = "completed"
                    storage.update_mission(mission)

        # Boss Directive 5.0: Auto-Agent-Plan after ANY tool result (or error)
        # This keeps the loop alive so the agent can react to what happened.
        # FIX: Only create agent_plan if NO other jobs were created by specialized handlers.
        if not created_jobs:
            task = storage.get_task(job.task_id)
            if task:
                mission = storage.get_mission(task.mission_id)
                # Only for standard missions, avoid selfloop or mesh-admin
                is_standard = mission and mission.metadata.get("created_by") in ["dashboard_quickstart", "verification_script"]
                
                # Boss Directive 5.1: If the job produced NO jobs, we MUST create an agent_plan 
                # (even if the current job WAS an agent_plan), otherwise the loop stalls.
                is_agent_plan = (task.kind == "agent_plan")
                
                if is_standard and (not is_agent_plan or not created_jobs):
                    # SAFETY: Don't spawn a new plan if one is already pending for this mission
                    # (this prevents "plan-storms" if multiple threads hit this)
                    all_jobs = storage.list_jobs()
                    mission_plans = [
                        j for j in all_jobs 
                        if j.status in ["pending", "queued", "working", "running", "failed"] 
                        and storage.get_task(j.task_id).mission_id == mission.id
                        and storage.get_task(j.task_id).kind == "agent_plan"
                    ]
                    
                    # Check if the existing plans are too many or if the failure is very recent
                    recent_failure = False
                    active_count = 0
                    for p in mission_plans:
                        if p.status in ["pending", "queued", "working", "running"]:
                            active_count += 1
                        elif p.status == "failed":
                            # If it failed less than 30 seconds ago, don't spam a new one
                            try:
                                from datetime import datetime
                                last_update = datetime.fromisoformat(p.updated_at.replace('Z', '+00:00'))
                                if (datetime.now(last_update.tzinfo) - last_update).total_seconds() < 30:
                                    recent_failure = True
                            except Exception:
                                pass

                    if active_count > 0:
                        print(f"[lcp_actions] ⏳ skipping auto-plan: mission {mission.id[:8]} already has {active_count} active plan job(s)")
                    elif recent_failure:
                        print(f"[lcp_actions] 🛑 skipping auto-plan: mission {mission.id[:8]} recently had a failed plan. Cooldown active.")
                    else:
                        print(f"[lcp_actions] 🔄 Auto-loop: Creating agent_plan after {task.kind} ({job.status})")
                        
                        # Find or create the agent_plan task for this mission
                        plan_task = storage.find_task_by_name(mission.id, "analyze_and_plan")
                        if not plan_task:
                            plan_task = models.Task.from_create(mission.id, models.TaskCreate(
                                name="analyze_and_plan",
                                description="Analyze results and plan next steps",
                                kind="agent_plan"
                            ))
                            storage.create_task(plan_task)
                        
                        # Create the job
                        # Boss Directive: Pass the current project root if we have it
                        project_root = task.params.get("root") or task.params.get("project_root") or str(storage.config.BASE_DIR)
                        
                        # --- PHASE 2: RECURSIVE RESULT INJECTION & TRUNCATION ---
                        last_result_payload = job.result
                        
                        # Check for minimal_feedback flag (silent mode)
                        if task.params.get("minimal_feedback"):
                            last_result_payload = {"status": "OK", "message": "System Proofed"}
                        else:
                            # Truncation Logic (respects full_content/recursive intent)
                            def truncate_payload(data, force_full=False):
                                if isinstance(data, dict):
                                    # Special handling for files and content
                                    files = data.get("files")
                                    # Recursive flag (or full_content) bypasses file truncation
                                    if isinstance(files, list) and len(files) > 50 and not force_full:
                                        data["files"] = files[:50] + [f"... and {len(files)-50} more files"]
                                        data["_truncated"] = True
                                    
                                    content = data.get("content")
                                    if isinstance(content, str) and len(content) > 1000 and not force_full:
                                        # Return metadata + truncated start
                                        data["content"] = content[:500] + "\n... [TRUNCATED] ...\n" + content[-500:]
                                        data["_metadata"] = {
                                            "char_count": len(content),
                                            "word_count": len(content.split()),
                                            "line_count": len(content.splitlines())
                                        }
                                        data["_truncated"] = True
                                return data

                            # Check if the job specifically wanted full content
                            # We check both task.params (defaults) and job.payload (overrides/dynamic)
                            is_full_request = (
                                task.params.get("full_content") or 
                                task.params.get("recursive") or 
                                job.payload.get("full_content") or 
                                job.payload.get("recursive")
                            )
                            last_result_payload = truncate_payload(
                                last_result_payload.copy() if isinstance(last_result_payload, dict) else last_result_payload,
                                force_full=is_full_request
                            )
                        # --------------------------------------------------------

                        # Phase 3: Track Iteration for Efficiency
                        current_iter = task.params.get("iteration") or 1
                        next_iter = current_iter + 1

                        jc = models.JobCreate(payload={
                            "task": {"kind": "agent_plan"},
                            "params": {
                                "project_root": project_root,
                                "iteration": next_iter
                            },
                            "last_result": last_result_payload
                        })
                        new_job = models.Job.from_create(plan_task.id, jc)
                        storage.create_job(new_job)
                        
                        # Dispatch it immediately
                        self.bridge.enqueue_job(new_job.id)
                        created_jobs.append(new_job)
        else:
            print(f"[lcp_actions] ℹ️ Unhandled action '{action}'")
        
        return created_jobs

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _handle_show_mission(self, job: models.Job) -> List[models.Job]:
        """Reads and returns the content of the mission's _plan.md file."""
        task = storage.get_task(job.task_id)
        if not task: return []
        
        mission_id = task.mission_id
        plan_file = storage.DATA_DIR / "missions" / f"{mission_id}_plan.md"
        
        content = "Plan file not found."
        if plan_file.exists():
            content = plan_file.read_text(encoding="utf-8")
            
        # Update job result with the content so it gets injected into next plan
        job.result = {"ok": True, "action": "show_mission_result", "content": content}
        storage.update_job(job)
        return [] # No new jobs needed, the loop handles the result injection

    def _handle_show_progress(self, job: models.Job) -> List[models.Job]:
        """Reads and returns the content of the mission's _progress.md file."""
        task = storage.get_task(job.task_id)
        if not task: return []
        
        mission_id = task.mission_id
        progress_file = storage.DATA_DIR / "missions" / f"{mission_id}_progress.md"
        
        content = "Progress file not found."
        if progress_file.exists():
            content = progress_file.read_text(encoding="utf-8")
            
        # Update job result with the content
        job.result = {"ok": True, "action": "show_progress_result", "content": content}
        storage.update_job(job)
        return []

    def _handle_create_mission(self, job: models.Job, res: dict) -> List[models.Job]:
        """Allows an agent to create a NEW mission via LCP."""
        title = res.get("title")
        description = res.get("description") or ""
        
        if not title:
            job.result = {"ok": False, "error": "Mission title is required for create_mission."}
            storage.update_job(job)
            return []
            
        # Call the same logic as the API (or just import it if possible, but simpler to repeat for now or refactor later)
        mission_create = models.MissionCreate(title=title, description=description)
        mission = models.Mission.from_create(mission_create)
        mission.metadata["created_by_agent_job"] = job.id
        storage.create_mission(mission)
        
        # Initialize files (redundant with main.py logic but needed here if not using the endpoint)
        try:
            mission_dir = storage.DATA_DIR / "missions"
            mission_dir.mkdir(parents=True, exist_ok=True)
            plan_file = mission_dir / f"{mission.id}_plan.md"
            progress_file = mission_dir / f"{mission.id}_progress.md"
            plan_file.write_text(f"# Mission Plan: {mission.title}\n\n## Objective\n{mission.description}\n", encoding="utf-8")
            progress_file.write_text(f"# Mission Progress: {mission.title}\n\n[Init] Created by agent from job {job.id[:8]}\n", encoding="utf-8")
        except Exception:
            pass

        job.result = {"ok": True, "action": "create_mission_result", "mission_id": mission.id}
        storage.update_job(job)
        return []

    def _handle_followups(
        self,
        job: models.Job,
        specs: List[Dict[str, Any]],
    ) -> List[models.Job]:
        """
        Handhabt create_followup_jobs:
        - Sucht die Mission des Jobs
        - Für jedes Spec:
            {"kind": "<task_kind>", "name": "...", "params": {...}}
          → Sucht passende Task in der Mission (by kind == task.name)
          → Erzeugt Job
          → Dispatcht ihn.
        """
        task = storage.get_task(job.task_id)
        if task is None:
            return []

        mission = storage.get_mission(task.mission_id)
        if mission is None:
            return []

        created_jobs: List[models.Job] = []

        # Determine current iteration
        current_iteration = 1
        # 1. Check loop_state (selfloop style)
        if job.payload.get("loop_state", {}).get("iteration"):
            current_iteration = job.payload["loop_state"]["iteration"]
        # 2. Check top-level payload (follow-up job style)
        elif job.payload.get("iteration"):
            current_iteration = job.payload["iteration"]
        # 3. Check nested params (first job / main.py style)
        elif job.payload.get("params", {}).get("iteration"):
            current_iteration = job.payload["params"]["iteration"]
        
        next_iteration = current_iteration + 1
        print(f"[lcp_actions] 🔄 Iteration tracking: {current_iteration} -> {next_iteration}")

        for i, spec in enumerate(specs):
            print(f"[lcp_actions]   🚀 Processing followup {i+1}: {spec.get('kind')} - {spec.get('name')}")
            if not isinstance(spec, dict):
                continue

            # NEW: use 'kind' instead of 'task'
            task_kind = spec.get("kind")
            params = spec.get("params") or {}
            job_name = spec.get("name", "Unnamed job")

            # Pass iteration to followup job params
            if "iteration" not in params:
                params["iteration"] = next_iteration
            
            # Pass last_result for context (Boss Directive 2.1)
            # CRITICAL: We must copy and prune to avoid "Circular reference detected" in storage
            if "last_result" not in params:
                clean_result = copy.deepcopy(job.result)
                if isinstance(clean_result, dict):
                    clean_result.pop("new_jobs", None)
                    clean_result.pop("actions", None)
                params["last_result"] = clean_result

            # SANITY CHECK: Replace hallucinated /workspace/project or absolute paths from other environments
            project_root = task.params.get("project_root") or task.params.get("root")
            
            # Normalize project root for comparison
            normalized_project_root = project_root.replace("\\", "/") if project_root else None

            hallucinated_roots = [
                "/workspace/project", "C:/workspace/project",
                "C:/Sheratan/2_sheratan_core",
                "/project", "project/", "C:/Sheratan/sheratan/project",
                "C:/workspace", "/workspace", "workspace/"
            ]
            
            if project_root:
                def sanitize_path(p):
                    if not isinstance(p, str): return p
                    # Normalize input for comparison (blind to slashes)
                    np = p.replace("\\", "/")
                    for h_root in hallucinated_roots:
                        nh_root = h_root.replace("\\", "/")
                        if np.lower().startswith(nh_root.lower()):
                            # Strip the root
                            suffix = np[len(nh_root):].lstrip("/")
                            # Combine with real project root
                            return f"{project_root}/{suffix}".replace("//", "/")
                    return p

                # 1. Check params['root']
                root_val = params.get("root")
                if root_val:
                    # If root is explicitly in hallucinations, replace it. 
                    # Comparison is normalized.
                    n_root_val = str(root_val).replace("\\", "/")
                    if any(n_root_val.lower() == h.replace("\\", "/").lower() for h in hallucinated_roots):
                        print(f"[lcp_actions] 🛠️ Sanitizing hallucinated root '{root_val}' -> '{project_root}'")
                        params["root"] = project_root
                
                # 2. Check params['rel_path'] (sometimes LLM puts absolute path there)
                if params.get("rel_path"):
                    old_rel = params["rel_path"]
                    new_rel = sanitize_path(old_rel)
                    if new_rel != old_rel:
                        # If it was absolute, it's now absolute-ish (project_root/suffix). 
                        # We strip project_root to keep it relative if it was intended as such.
                        if normalized_project_root and new_rel.replace("\\", "/").lower().startswith(normalized_project_root.lower()):
                             new_rel = new_rel.replace("\\", "/")[len(normalized_project_root):].lstrip("/")
                        
                        print(f"[lcp_actions] 🛠️ Sanitizing rel_path '{old_rel}' -> '{new_rel}'")
                        params["rel_path"] = new_rel
                
                # 3. Check params['path']
                if params.get("path"):
                    old_path = params["path"]
                    new_path = sanitize_path(old_path)
                    if new_path != old_path:
                        print(f"[lcp_actions] 🛠️ Sanitizing absolute path '{old_path}' -> '{new_path}'")
                        params["path"] = new_path


            if not isinstance(task_kind, str) or not task_kind:
                print(f"[lcp_actions] Skipping job spec without 'kind' field: {spec}")
                continue
            if not isinstance(params, dict):
                continue

            # Find task by kind (tasks are named by their kind: "list_files", "read_file", etc.)
            target_task = storage.find_task_by_name(mission.id, task_kind)
            if target_task is None:
                # Task doesn't exist - create it without params (each Job has own params)
                print(f"[lcp_actions] Task '{task_kind}' not found in mission, creating it...")
                
                task_create = models.TaskCreate(
                    name=task_kind,
                    description=f"Auto-created task for {task_kind}",
                    kind=task_kind,
                    params={}  # Task has no params - each Job has own params
                )
                target_task = models.Task.from_create(mission.id, task_create)
                storage.create_task(target_task)
                print(f"[lcp_actions] Created task: {target_task.id} (kind={task_kind})")

            # Create job with params in payload (Worker will merge with task.params)
            jc = models.JobCreate(payload=params)
            new_job = models.Job.from_create(target_task.id, jc)

            # Persistieren
            storage.create_job(new_job)

            # Dispatch to worker queue (async, file-based)
            self.bridge.enqueue_job(new_job.id)
            print(f"📝 Followup job created and queued: {new_job.id} (kind={task_kind}, name={job_name})")

            # Monitoring
            record_module_call(
                source="core_v2.lcp_actions.handle_job_result",
                target="webrelay_worker",
                duration_ms=0.0,
                status="ok",
                correlation_id=f"job:{new_job.id}",
            )

            created_jobs.append(new_job)

        return created_jobs

    # ------------------------------------------------------------------ #
    # Boss Directive 3.1: Section D → Jobs
    # ------------------------------------------------------------------ #
    def _create_followup_jobs_from_selfloop_d(
        self, task: models.Task, parsed: Dict[str, str]
    ) -> List[models.Job]:
        """Create followup jobs from Section D bulletpoints.
        
        Boss Directive 3.1: Convert Section D items into LCP jobs.
        
        Args:
            task: The parent task
            parsed: Parsed A/B/C/D sections
            
        Returns:
            List of created jobs
        """
        section_d = parsed.get("D", "").strip()
        if not section_d:
            return []

        jobs = []
        for line in section_d.splitlines():
            stripped = line.strip()
            if not stripped or not stripped.startswith("-"):
                continue

            item = stripped.lstrip("-").strip()
            if not item:
                continue

            # Create LCP job from each bullet point
            jc = models.JobCreate(
                payload={
                    "prompt": item,
                    "response_format": "lcp",
                    "origin": "self_loop_section_d",
                }
            )
            job = models.Job.from_create(task.id, jc)
            storage.create_job(job)
            
            # Auto-enqueue
            self.bridge.enqueue_job(job.id)
            jobs.append(job)
            print(f"📝 Created job from Section D: {item[:50]}...")

        return jobs

    # ------------------------------------------------------------------ #
    # Self-Loop Handler
    # ------------------------------------------------------------------ #

