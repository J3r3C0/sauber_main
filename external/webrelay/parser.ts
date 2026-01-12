// ========================================
// Sheratan WebRelay - Response Parser
// ========================================

import { ParseResult, LCPAction } from './types.js';

/**
 * Strip sentinel marker from end of response
 */
export function stripSentinel(text: string, sentinel: string): string {
    if (text.endsWith(sentinel)) {
        return text.slice(0, -sentinel.length).trimEnd();
    }
    return text;
}

/**
 * Try to extract JSON from markdown code block or find JSON in mixed text
 */
function extractJsonFromMarkdown(text: string): string | null {
    // 1. Try markdown code block first
    const codeBlockMatch = text.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
    if (codeBlockMatch) {
        return codeBlockMatch[1].trim();
    }

    // 2. Look for potential JSON objects greedily (first { to last })
    // Non-greedy /\{[\s\S]*?\}/g often fails on nested objects.
    // We try to find the outermost bounds.
    const startIdx = text.indexOf('{');
    const endIdx = text.lastIndexOf('}');

    if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
        return text.slice(startIdx, endIdx + 1);
    }

    return null;
}

/**
 * Parse LLM response - auto-detect LCP format or return plain text
 */
export function parseResponse(rawAnswer: string, config: { sentinel: string }): ParseResult {
    // Strip sentinel first
    const cleaned = stripSentinel(rawAnswer, config.sentinel);

    // Try to find JSON in response
    let jsonText = extractJsonFromMarkdown(cleaned);
    if (!jsonText) {
        // Try direct JSON parse
        jsonText = cleaned.trim();
    }

    // Try to parse as LCP JSON
    try {
        let parsed = JSON.parse(jsonText);

        // 1. Unwrap common semantic wrappers
        if (parsed.LCP_AGENT_RESPONSE) {
            parsed = parsed.LCP_AGENT_RESPONSE;
        }

        // 2. Map Execution Plan to Action if needed
        if (parsed.EXECUTION_PLAN && !parsed.action) {
            if (parsed.EXECUTION_PLAN.current_op) {
                parsed.action = parsed.EXECUTION_PLAN.current_op.command;
                parsed.params = parsed.EXECUTION_PLAN.current_op.params;
                if (parsed.EXECUTION_PLAN.job_queue) {
                    parsed.new_jobs = parsed.EXECUTION_PLAN.job_queue;
                }
            } else if (parsed.EXECUTION_PLAN.job_queue) {
                parsed.action = 'create_followup_jobs';
                parsed.new_jobs = parsed.EXECUTION_PLAN.job_queue;
            }
        }

        // 3. Fallback for 'commentary' from 'COMMENTARY.assessment'
        if (!parsed.commentary && parsed.COMMENTARY?.assessment) {
            parsed.commentary = parsed.COMMENTARY.assessment;
        }

        // 4. Final check for LCP format (actions array)
        if (parsed.actions && Array.isArray(parsed.actions)) {
            return {
                type: 'lcp',
                thought: parsed.thought || parsed.commentary || '',
                actions: parsed.actions as LCPAction[],
            };
        }

        // 5. Generic LCP Action handle (singleton action or followup jobs)
        if (parsed.action) {
            return {
                type: 'lcp',
                action: parsed.action,
                ok: parsed.ok ?? true,
                commentary: parsed.commentary || parsed.thought || '',
                new_jobs: parsed.new_jobs || [],
                ...parsed
            } as any;
        }

        // 6. Audit Report (from LLM2 Auditor)
        if (parsed.decision && (parsed.violations || parsed.fix_suggestions)) {
            return {
                type: 'text',
                summary: JSON.stringify(parsed),  // Return as stringified JSON for auditor to parse
            };
        }

        // Some other JSON format - treat as text
        return {
            type: 'text',
            summary: JSON.stringify(parsed, null, 2),
        };
    } catch (e) {
        // Not valid JSON - return as plain text
        return {
            type: 'text',
            summary: cleaned,
        };
    }
}
