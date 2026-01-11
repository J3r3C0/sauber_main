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
from typing import Any, Dict, List

from . import models
from . import storage
from .webrelay_bridge import WebRelayBridge
from .metrics_client import record_module_call

# Self-Loop integration
from .selfloop_utils import parse_selfloop_markdown, build_next_loop_state


class LCPActionInterpreter:
    """Interpretiert Worker-LCP-Resultate und erzeugt Folgejobs."""

    def __init__(self, bridge: WebRelayBridge) -> None:
        self.bridge = bridge

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def handle_job_result(self, job: models.Job) -> List[models.Job]:
        """
        Verarbeitet das LCP-Result eines Jobs und erzeugt ggf. neue Folgejobs.

        Args:
            job: Das Job-Objekt mit einem LCP-Result in job.result.

        Returns:
            Liste aller neu erzeugten Jobs (kann leer sein).
        """
        res = job.result
        if not isinstance(res, dict):
            # Kein valides Result → nichts tun
            return []   

        # Wenn ok == False → already handled in WebRelayBridge (status=failed).
        if not res.get("ok", False):
            return []

        action = res.get("action")
        if not isinstance(action, str):
            return []

        created_jobs = []

        # NEW: Self-Loop Handler (check job_type first)
        if job.payload.get("job_type") == "sheratan_selfloop":
            return self._handle_selfloop_result(job)

        if action == "list_files_result":
            files = res.get("files") or []
            if not isinstance(files, list):
                return []
            created_jobs.extend(self._handle_list_files(job, files))

        elif action == "create_followup_jobs":
            spec_list = res.get("new_jobs") or []
            if not isinstance(spec_list, list):
                return []
            created_jobs.extend(self._handle_followups(job, spec_list))
        
        # NEUE FEATURE: Auto-agent_plan nach Tool-Results
        # Wenn es ein Tool-Result ist (list_files, read_file, etc.), erstelle automatisch
        # einen agent_plan Job der das Result analysiert und nächste Schritte plant
        task = storage.get_task(job.task_id)
        if task and task.kind in ["list_files", "read_file", "write_file", "rewrite_file"]:
            # Erstelle agent_plan Job mit Result als Kontext
            # Erstelle agent_plan Job mit Result als Kontext
            print(f"[lcp_actions] Tool '{task.kind}' completed, creating auto-agent_plan for analysis...")
            
            mission = storage.get_mission(task.mission_id)
            if mission:
                # Finde oder erstelle agent_plan Task
                agent_task = storage.find_task_by_name(mission.id, "agent_plan")
                if not agent_task:
                    task_create = models.TaskCreate(
                        name="agent_plan",
                        description="Auto-analysis of tool results",
                        kind="agent_plan",
                        params={}
                    )
                    agent_task = models.Task.from_create(mission.id, task_create)
                    storage.create_task(agent_task)
                    print(f"[lcp_actions] Created agent_plan task: {agent_task.id}")
                
                # Erstelle Job mit Result als Kontext
                analysis_prompt = f"""Previous step completed: {task.kind}

Result: {json.dumps(res, indent=2)}

Based on this result, what should be the next steps to accomplish the mission goal: "{mission.description}"?

Create followup jobs to continue the analysis."""

                job_payload = {
                    "prompt": analysis_prompt,
                    "previous_result": res,
                    "mission_goal": mission.description
                }
                
                jc = models.JobCreate(payload=job_payload)
                analysis_job = models.Job.from_create(agent_task.id, jc)
                storage.create_job(analysis_job)
                
                # Dispatch
                self.bridge.enqueue_job(analysis_job.id)
                print(f"📝 Auto-agent_plan job created and queued: {analysis_job.id}")
                
                created_jobs.append(analysis_job)

        return created_jobs

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _handle_list_files(
        self,
        job: models.Job,
        files: List[str],
    ) -> List[models.Job]:
        """
        Handhabt list_files_result:
        - Sucht die Mission des Jobs
        - Sucht Task "analyze_file" in dieser Mission
        - Erzeugt für jede Datei einen analyze_file-Job und dispatcht ihn.
        """
        task = storage.get_task(job.task_id)
        if task is None:
            return []

        mission = storage.get_mission(task.mission_id)
        if mission is None:
            return []

        analyze_task = storage.find_task_by_name(mission.id, "analyze_file")
        if analyze_task is None:
            # Kein analyze_file Task in der Mission registriert
            return []

        created_jobs: List[models.Job] = []
        for path in files:
            if not isinstance(path, str) or not path:
                continue

            payload = {"file": path}
            jc = models.JobCreate(payload=payload)
            new_job = models.Job.from_create(analyze_task.id, jc)

            # Persistieren
            storage.create_job(new_job)

            # Dispatch to worker queue (async, file-based)
            self.bridge.enqueue_job(new_job.id)
            print(f"📝 Followup job created and queued: {new_job.id}")

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

        for spec in specs:
            if not isinstance(spec, dict):
                continue

            # NEW: use 'kind' instead of 'task'
            task_kind = spec.get("kind")
            params = spec.get("params") or {}
            job_name = spec.get("name", "Unnamed job")

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
    def _handle_selfloop_result(self, job: models.Job) -> List[models.Job]:
        """Handle Self-Loop job result and create follow-up iteration.
        
        Args:
            job: The completed Self-Loop job
            
        Returns:
            List containing the next iteration job (or empty if max iterations reached)
        """
        if job.status != "done":
            return []
        
        # Extract result text
        result = job.result or {}
        if isinstance(result, dict):
            result_text = result.get("text", "") or result.get("output", "") or result.get("summary", "") or str(result)
        else:
            result_text = str(result)
        
        # Parse A/B/C/D sections
        parsed = parse_selfloop_markdown(result_text)
        
        # Build next loop state
        prev_state = job.payload.get("loop_state", {})
        next_state = build_next_loop_state(prev_state, parsed)
        
        # Check max iterations (default: 10)
        max_iterations = job.payload.get("max_iterations", 10)
        if next_state["iteration"] > max_iterations:
            print(f"[lcp_actions] Self-Loop max iterations ({max_iterations}) reached for job {job.id}")
            return []
        
        # Build next job payload
        next_payload = {
            **job.payload,
            "loop_state": next_state,
            "current_task": parsed.get("D", "Continue iteration").strip()  # Section D becomes next focus
        }
        
        # Create follow-up job
        jc = models.JobCreate(payload=next_payload)
        next_job = models.Job.from_create(job.task_id, jc)
        storage.create_job(next_job)
        
        # Boss Directive 3.1: Create jobs from Section D
        task = storage.get_task(job.task_id)
        if task:
            section_d_jobs = self._create_followup_jobs_from_selfloop_d(task, parsed)
            print(f"🔄 Self-Loop iteration {next_state['iteration']} created: {next_job.id}")
            if section_d_jobs:
                print(f"  + {len(section_d_jobs)} job(s) from Section D")
        else:
            section_d_jobs = []
            print(f"🔄 Self-Loop iteration {next_state['iteration']} created: {next_job.id}")
        
        # Monitoring
        record_module_call(
            source="core_v2.lcp_actions.handle_selfloop_result",
            target="webrelay_worker",
            duration_ms=0.0,
            status="ok",
            correlation_id=f"job:{next_job.id}",
        )
        
        # Return both the next iteration job AND Section D jobs
        return [next_job] + section_d_jobs

