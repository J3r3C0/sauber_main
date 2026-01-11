// ========================================
// Sheratan WebRelay - Job Router & Prompt Builder
// ========================================

import { UnifiedJob } from './types.js';

/**
 * Build prompt from UnifiedJob
 * Extracts relevant parts based on job.kind and payload structure
 */
export class JobRouter {
  buildPrompt(job: UnifiedJob): string {
    const { payload } = job;

    // Direct prompt field (simple llm_call)
    if (payload.prompt) {
      return payload.prompt;
    }

    // agent_plan format: task.params.user_prompt
    if (job.kind === 'agent_plan' && payload.task?.params?.user_prompt) {
      const userPrompt = payload.task.params.user_prompt;
      const projectRoot = payload.task.params.project_root || '/workspace/project';

      return `You are a code-editing agent for the Sheratan workspace.

User Request: ${userPrompt}
Project Root: ${projectRoot}

Create a plan as JSON with this exact structure:
{
  "action": "create_followup_jobs",
  "commentary": "Brief explanation of the plan",
  "new_jobs": [
    {
      "name": "Task name",
      "description": "What this task does",
      "kind": "list_files" | "read_file" | "rewrite_file",
      "params": { ... },
      "auto_dispatch": true/false
    }
  ]
}

Available task kinds:
- list_files: {root, patterns: ["**/*.py"]}
- read_file: {root, rel_path: "main.py"}
- rewrite_file: {root, rel_path: "file.py", new_content: "..."}

Return ONLY the JSON, no explanation text. End with }}}`;
    }

    // Self-Loop format (Boss directive 2.2)
    if (job.kind === 'self_loop') {
      const mission = payload.mission || {};
      const task = payload.task as any || {};  // Type assertion for name/description
      const state = payload.state || {}; // history_summary, constraints, open_questions

      return `Sheratan Self-Loop (A/B/C/D Format)

Mission:
- Title: ${mission.title || ''}
- Description: ${mission.description || ''}

Current Task:
- Name: ${task.name || ''}
- Description: ${task.description || ''}

Current Loop State (JSON):
${JSON.stringify(state, null, 2)}

Write your answer in EXACTLY this Markdown format:

A) Lagebild / Stand der Dinge
- Kurze, knappe Zusammenfassung der Situation und des Fortschritts.

B) Nächster sinnvoller Schritt
- 1–3 Sätze, was der Agent als nächstes tun sollte.

C) Konkrete Umsetzung (für diese Iteration)
- 3–7 Bulletpoints, sehr konkret, was in dieser Iteration gemacht wird.
- Gern mit Referenzen auf Dateien / Pfade (z.B. project/main.py).

D) Vorschlag für nächsten Loop / offene Fragen
- Bulletpoints mit offenen Fragen oder To-Dos für den nächsten Loop.

WICHTIG:
- Schreibe NUR dieses A/B/C/D-Markdown.
- Kein JSON, keine Erklärungen außerhalb der Sections.
`;
    }    // LCP format tasks
    if (payload.task && payload.mission) {
      const taskKind = payload.task.kind || 'unknown';
      const taskParams = payload.task.params || {};
      const missionGoal = payload.mission.description || 'Complete mission';

      return `You are an autonomous agent. Respond in LCP format.

MISSION: ${missionGoal}
TASK: ${taskKind}
PARAMS: ${JSON.stringify(taskParams)}

RESPOND WITH:
{
  "ok": true,
  "action": "create_followup_jobs",
  "commentary": "Brief plan",
  "new_jobs": [
    {"task": "analyze_file", "params": {"file": "path.py"}},
    {"task": "write_file", "params": {"file": "report.md", "content": "..."}}
  ]
}

AVAILABLE TASKS: list_files, analyze_file, write_file, patch_file

RULES:
- Create 1-3 followup jobs
- Keep commentary brief 
- End with }}}

Now respond:`;
    }

    // Fallback: stringify entire payload
    return `Process this job:
${JSON.stringify(job, null, 2)}

Provide a helpful response ending with }}}`;
  }
}
