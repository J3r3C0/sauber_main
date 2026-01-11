// ========================================
// Sheratan WebRelay - Job Router & Prompt Builder
// ========================================

import { UnifiedJob } from './types.js';

// ========================================
// Core2 LCP System Prompt
// ========================================
export const CORE2_LCP_SYSTEM_PROMPT = `You are the SHERATAN AGENT [v2.0].
You operate as the cognitive driver within a V-Mesh architecture, optimized for FLOW and STABILITY.

OPERATIONAL PROTOCOL [LCP]:
1. OUTPUT: Strictly valid JSON. No prose. No markdown fences outside the JSON object.
2. JSON SCHEMA:
   {
     "ok": true,
     "action": "list_files_result" | "create_followup_jobs" | "write_file" | "analysis_result" | "error",
     "thought": "Internal reasoning and safety self-audit",
     "commentary": "External explanation for human/other agents",
     "new_jobs": [
       { "name": "...", "kind": "...", "params": {}, "auto_dispatch": boolean }
     ],
     "provenance": { "thought_chain": "...", "approved": false }
   }

MANDATORY ACTIONS:
- create_followup_jobs: Schedule future tasks.
- write_file: Write contents to a file. Params: { "path": string, "content": string }.
- list_files: List directory contents. Params: { "path": string }.
- read_file: Read file content. Params: { "path": string }.
- analysis_result: Conclude a task with a summary.

SAFETY REINFORCEMENT [GATED PIPELINE]:
- Your proposals will be reviewed by Safety Gates (G0-G4).
- If your previous attempt was BLOCKED, you will find a 'gate_report' or 'audit_report' in your context.
- MANDATORY: Analyze the 'audit_report'. You MUST adopt the 'fix_suggestions' or provide a rigorous technical justification for deviation.
- Failure to respect safety feedback will lead to recursive quarantine.

WORLD MODEL:
- The Mesh is your body. Stability is your health. Friction is your enemy.
- You are an 'offgrid' entity; rely on local resources and verified paths.
- Your 'thought' should reflect a fail-safe mindset.

End response with '}' ONLY.`;


/**
 * Build prompt from UnifiedJob
 * Extracts relevant parts based on job.kind and payload structure
 */
export class JobRouter {
  buildPrompt(job: UnifiedJob): string {
    const { payload } = job;
    const kind = job.kind || 'llm_call';

    // 1. Direct prompt with LCP wrapper (for llm_call / webrelay kinds)
    if (payload && payload.prompt && (kind === 'llm_call' || kind === 'webrelay')) {
      return `${CORE2_LCP_SYSTEM_PROMPT}\n\nUSER REQUEST:\n${payload.prompt}\n\nRESPOND NOW WITH JSON ONLY:`;
    }

    // 2. agent_plan format
    if (payload && kind === 'agent_plan' && payload.task?.params?.user_prompt) {
      const userPrompt = payload.task.params.user_prompt;
      const projectRoot = payload.task.params.project_root || '/workspace/project';

      return `${CORE2_LCP_SYSTEM_PROMPT}

You are acting as a planner for the project root: ${projectRoot}

User Request: ${userPrompt}

Construct a plan using 'create_followup_jobs' action.
Return ONLY the JSON.`;
    }

    // 3. Self-Loop format (Markdown A/B/C/D)
    if (kind === 'self_loop' || kind === 'sheratan_selfloop') {
      const p = payload || {};
      const mission = p.mission || {};
      const task = p.task as any || {};
      const state = p.state || {};

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
- Kurze Zusammenfassung.

B) Nächster sinnvoller Schritt
- 1–3 Sätze.

C) Konkrete Umsetzung (für diese Iteration)
- 3–7 konkrete Bulletpoints.

D) Vorschlag für nächsten Loop / offene Fragen
- Bulletpoints für später.

WICHTIG: NUR Markdown A/B/C/D, kein JSON.`;
    }

    // 4. LCP format tasks (Discovery/Analysis)
    if (payload && payload.task && payload.mission) {
      const taskKind = payload.task.kind || 'unknown';
      const taskParams = payload.task.params || {};
      const missionGoal = payload.mission.description || 'Complete mission';

      return `${CORE2_LCP_SYSTEM_PROMPT}

MISSION: ${missionGoal}
TASK: ${taskKind}
PARAMS: ${JSON.stringify(taskParams)}

Process this task and respond with the appropriate LCP JSON action.`;
    }

    // Fallback: Stringify entire payload
    const rawPrompt = payload.prompt || JSON.stringify(job, null, 2);
    return `${CORE2_LCP_SYSTEM_PROMPT}\n\nREQUEST:\n${rawPrompt}\n\nRESPOND NOW WITH JSON ONLY:`;
  }
}
