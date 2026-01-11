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
    // Try markdown code block first
    const codeBlockMatch = text.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
    if (codeBlockMatch) {
        return codeBlockMatch[1].trim();
    }

    // Try to find JSON object in text (handles "ChatGPT said: {json}" cases)
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
        return jsonMatch[0];
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
        const parsed = JSON.parse(jsonText);

        // Check if it's LCP format (has actions array)
        if (parsed.actions && Array.isArray(parsed.actions)) {
            return {
                type: 'lcp',
                thought: parsed.thought || '',
                actions: parsed.actions as LCPAction[],
            };
        }

        // Check if it's create_followup_jobs format (from agent_plan)
        if (parsed.action === 'create_followup_jobs' && parsed.new_jobs) {
            return {
                type: 'lcp',
                action: parsed.action,
                commentary: parsed.commentary || '',
                new_jobs: parsed.new_jobs,
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
