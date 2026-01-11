// ========================================
// Sheratan WebRelay - ChatGPT Browser Backend
// ========================================

import puppeteer, { Browser, Page } from 'puppeteer-core';
import { LLMBackend, BackendCallResult } from '../types.js';

// ========================================
// Core2 LCP System Prompt (Boss Directive 1)
// ========================================
const CORE2_LCP_SYSTEM_PROMPT = `You are the Sheratan Core v2 worker brain.

You MUST always answer with a single JSON object that follows the Core2 LCP schema:

Common fields:
- ok: boolean
- action: one of ["list_files_result", "analysis_result", "create_followup_jobs", "write_file", "patch_file"]
- error: string (only if ok=false)

1) list_files_result
{
  "ok": true,
  "action": "list_files_result",
  "files": ["path/to/file1.py", "path/to/file2.py"]
}

2) analysis_result
{
  "ok": true,
  "action": "analysis_result",
  "target_file": "project/main.py",
  "summary": "One short paragraph summary.",
  "issues": ["bullet 1", "bullet 2"],
  "recommendations": ["next thing the agent should do"]
}

3) create_followup_jobs
{
  "ok": true,
  "action": "create_followup_jobs",
  "commentary": "One-sentence explanation of the plan",
  "new_jobs": [
    {
      "name": "Human readable job name",
      "description": "Optional description",
      "kind": "list_files | read_file | write_file | ...",
      "params": { "root": "/workspace/project", "patterns": ["**/*.py"] },
      "auto_dispatch": true
    }
  ]
}

4) write_file
{
  "ok": true,
  "action": "write_file",
  "root": "/workspace/project",
  "rel_path": "some/file.py",
  "mode": "overwrite",
  "content": "new file content here"
}

5) patch_file
{
  "ok": true,
  "action": "patch_file",
  "root": "/workspace/project",
  "rel_path": "some/file.py",
  "patch": "unified diff or minimal patch instructions"
}

Rules:
- Answer with JSON ONLY, no prose outside JSON.
- Never ask the user questions, always propose concrete followup jobs.
- Maximum 3 items in new_jobs.
- End your response with the closing curly brace of the JSON.`;

const BROWSER_URL = process.env.BROWSER_URL || 'http://127.0.0.1:9222';
const WEB_INTERFACE_URL = process.env.WEB_INTERFACE_URL || 'https://chatgpt.com';
const SEL_TEXTAREA = 'textarea[aria-label="Message ChatGPT"], textarea';
const SENTINEL = '}}}';
const JSON_END_PATTERN = /}\s*]\s*}\s*$/;

function sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getBrowser(): Promise<Browser> {
    return puppeteer.connect({
        browserURL: BROWSER_URL,
        defaultViewport: null,
    });
}

async function findChatPage(browser: Browser): Promise<Page | null> {
    const pages = await browser.pages();
    if (!pages.length) return null;

    const targetHost = new URL(WEB_INTERFACE_URL).hostname;
    const byHost = pages.find((p) => {
        const url = p.url();
        try {
            const u = new URL(url);
            return u.hostname === targetHost;
        } catch {
            return false;
        }
    });
    if (byHost) return byHost;

    return pages[0];
}

async function ensureChatPage(browser: Browser): Promise<Page> {
    let page = await findChatPage(browser);
    if (!page) {
        page = await browser.newPage();
    }

    const url = page.url();
    if (!url || url === 'about:blank') {
        await page.goto(WEB_INTERFACE_URL, { waitUntil: 'networkidle2' });
    } else if (!url.includes(new URL(WEB_INTERFACE_URL).hostname)) {
        await page.goto(WEB_INTERFACE_URL, { waitUntil: 'networkidle2' });
    }

    await page.bringToFront();
    return page;
}

async function focusComposer(page: Page): Promise<void> {
    await page.bringToFront();

    try {
        await page.click(SEL_TEXTAREA, { delay: 50 });
        await sleep(200);
        return;
    } catch (e: any) {
        console.warn('⚠️ Textarea nicht erreichbar, nutze Fallback');
    }

    console.log('🖱️ Fallback-Klick in der Mitte...');
    await page.mouse.click(500, 500);
    await sleep(200);
}

async function setTextareaValueAndSend(page: Page, text: string): Promise<void> {
    try {
        await page.keyboard.down('Control');
        await page.keyboard.press('A');
        await page.keyboard.up('Control');
        await page.keyboard.press('Backspace');
        await sleep(100);
    } catch (e: any) {
        console.warn('⚠️ Konnte Text nicht löschen');
    }

    const normalized = text.replace(/\r\n/g, '\n').replace(/\n+$/, '');
    const lines = normalized.split('\n');

    console.log(`⌨️ Tippe Prompt ein... (${lines.length} Zeile${lines.length === 1 ? '' : 'n'})`);

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.length > 0) {
            await page.keyboard.type(line, { delay: 10 });
        }
        const isLast = i === lines.length - 1;

        if (!isLast) {
            await page.keyboard.down('Shift');
            await page.keyboard.press('Enter');
            await page.keyboard.up('Shift');
            await sleep(80);
        }
    }

    console.log('📤 Sende Nachricht mit Enter...');
    await page.keyboard.press('Enter');
    await sleep(300);
}

async function getLatestAssistantText(page: Page): Promise<string> {
    const text = await page.evaluate(() => {
        const assistantNodes = Array.from(
            document.querySelectorAll<HTMLElement>('[data-message-author-role="assistant"]')
        );
        if (assistantNodes.length) {
            const last = assistantNodes[assistantNodes.length - 1];
            return last.innerText || last.textContent || '';
        }

        const markdowns = Array.from(
            document.querySelectorAll<HTMLElement>('.markdown, article')
        );
        if (markdowns.length) {
            const last = markdowns[markdowns.length - 1];
            return last.innerText || last.textContent || '';
        }

        return document.body?.innerText || '';
    });

    return (text || '').trim();
}

function answerLooksComplete(raw: string): boolean {
    const trimmed = raw.trimEnd();
    if (!trimmed) return false;

    if (trimmed.endsWith(SENTINEL)) return true;
    if (JSON_END_PATTERN.test(trimmed)) return true;

    return false;
}

async function hasStopButton(page: Page): Promise<boolean> {
    const found = await page.evaluate(() => {
        const candidates: HTMLElement[] = Array.from(
            document.querySelectorAll('button')
        ) as HTMLElement[];
        const stop = candidates.find((btn) => {
            const txt = (btn.innerText || '').toLowerCase();
            return txt.includes('stop generating') || txt.includes('stopp') || txt.includes('stop');
        });
        return !!stop;
    });
    return !!found;
}

async function waitForStableAnswer(page: Page): Promise<string> {
    let lastText = '';
    let stableCount = 0;

    const maxStable = 4;
    const maxTimeMs = 120_000;
    const pollMs = 1_000;
    const started = Date.now();

    while (Date.now() - started < maxTimeMs) {
        const [text, stopVisible] = await Promise.all([
            getLatestAssistantText(page),
            hasStopButton(page),
        ]);

        if (text && text !== lastText) {
            lastText = text;
            stableCount = 0;
        } else if (text) {
            stableCount += 1;
        }

        const complete = answerLooksComplete(text);

        if (complete && stableCount >= 1) {
            console.log('✅ Antwort vollständig (Sentinel/JSON-Ende)');
            break;
        }

        if (!stopVisible && stableCount >= maxStable) {
            console.log('✅ Antwort stabil, kein Stop-Button');
            break;
        }

        await sleep(pollMs);
    }

    return lastText;
}

async function sendQuestionAndGetAnswer(
    prompt: string
): Promise<{ answer: string; url: string }> {
    const browser = await getBrowser();
    const page = await ensureChatPage(browser);

    console.log('🌐 Verbunden mit:', await page.title());

    // Wrap prompt with Core2 LCP system instructions
    const fullPrompt = `${CORE2_LCP_SYSTEM_PROMPT}

USER REQUEST:
${prompt}

RESPOND NOW WITH JSON ONLY (no other text):`;

    await focusComposer(page);
    await setTextareaValueAndSend(page, fullPrompt);

    const answer = await waitForStableAnswer(page);
    const url = page.url();

    console.log('✅ Antwortlänge:', answer.length);

    return { answer, url };
}

/**
 * ChatGPT Browser Backend
 */
export class ChatGPTBackend implements LLMBackend {
    name = 'chatgpt';

    async call(prompt: string): Promise<BackendCallResult> {
        const { answer, url } = await sendQuestionAndGetAnswer(prompt);
        return { answer, url };
    }
}
