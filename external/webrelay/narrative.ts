/**
 * SystemNarrative: The Unified Truth of a Job's Lifecycle
 * 
 * This interface bridges the gap between:
 * 1. LLM1's Intent (What it wanted to do)
 * 2. The System's Gates (What rules were checked)
 * 3. LLM2's Judgment (How it was fixed/approved)
 */
export interface SystemNarrative {
    event_id: string;      // usually job_id
    timestamp: string;     // ISO8601

    // 1. The Actor's Intent (LLM1)
    actor: {
        id: "LLM1_PLANNER";
        intent: string;    // e.g. "FILE_WRITE" or "RUN_COMMAND"
        target: string;    // The primary object (file path, url)
        summary: string;   // Human-readable summary of intent
    };

    // 2. The System's Reality (Gates)
    system_status: "PENDING" | "APPROVED" | "BLOCKED" | "MODIFIED" | "QUARANTINED";
    gate_results: {
        passed: string[];
        failed: string[];
        warnings: string[];
    };

    // 3. The Resolution (LLM2 / WebRelay)
    resolution: {
        decision: "ALLOW" | "MANUAL_REVIEW" | "PAUSE" | "N/A";
        by: "LLM1" | "LLM2" | "SYSTEM" | "HUMAN";
        intervention: string; // Description of fix applied (e.g. "Path traversal fixed")
        feedback_to_actor: string; // The message sent back to LLM1
    };

    // Raw links (for deep dive)
    artifacts: {
        job_path?: string;
        gate_report_path?: string;
        audit_report_path?: string;
    };
}
