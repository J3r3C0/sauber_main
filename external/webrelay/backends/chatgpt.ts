// ========================================
// Sheratan WebRelay - ChatGPT Browser Backend
// ========================================

import puppeteer, { Browser, Page } from 'puppeteer-core';
import { LLMBackend, BackendCallResult } from '../types.js';

// ========================================
// Core2 LCP System Prompt (Boss Directive 1)
// ========================================
const BROWSER_URL = process.env.BROWSER_URL || 'http://127.0.0.1:9222';
const WEB_INTERFACE_URL = process.env.WEB_INTERFACE_URL || 'https://chatgpt.com';
const SEL_TEXTAREA = 'textarea[aria-label="Message ChatGPT"], textarea';
const SEL_SEND_BUTTON = '[data-testid="send-button"]';
const SEL_STOP_BUTTON = '[data-testid="stop-button"], [aria-label="Stop generating"]';
const SENTINEL = '}}}';
const JSON_END_PATTERN = /}\s*]\s*}\s*$/;

// Global Mutex to prevent concurrent browser access
let call_mutex: Promise<void> = Promise.resolve();

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
        await sleep(500);
    }

    try {
        const url = page.url();
        const isChatGPT = url && url.includes('chatgpt.com');

        if (!isChatGPT || url === 'about:blank') {
            console.log(`🌐 Navigating to ${WEB_INTERFACE_URL}...`);
            await page.goto(WEB_INTERFACE_URL, { waitUntil: 'load', timeout: 60000 });
            await sleep(2000);
        }

        // Wait for page to be interactive (textarea exists)
        try {
            await page.waitForSelector(SEL_TEXTAREA, { timeout: 3000 });
        } catch (e) {
            console.log('⏳ Waiting for textarea to appear...');
        }

        // --- Cloudflare Patience (reduced timeout) ---
        let attempts = 0;
        while (attempts < 3) {
            const content = await page.content();
            if (content.includes('Just a moment...') || content.includes('cloudflare')) {
                console.log('🛡️ Cloudflare Challenge detected, waiting 2s...');
                await sleep(2000);
                attempts++;
            } else {
                break;
            }
        }
    } catch (e: any) {
        console.warn('⚠️ Navigation stability warning:', e.message);
    }

    await page.bringToFront();
    return page;
}

async function focusComposer(page: Page): Promise<void> {
    // We strive for background compatibility. Try focus via evaluate.
    const focused = await page.evaluate((sel) => {
        const textarea = document.querySelector<HTMLElement>(sel);
        if (textarea) {
            textarea.focus();
            return true;
        }
        return false;
    }, SEL_TEXTAREA);

    if (focused) {
        console.log('✅ Textarea fokussiert (background-safe)');
    } else {
        console.warn('⚠️ Textarea via evaluate nicht fokussierbar');
        // Minimal fallback bring-to-front if absolutely necessary
        await page.bringToFront();
        await sleep(200);
    }
}

async function setTextareaValueAndSend(page: Page, text: string): Promise<void> {
    // Clear existing content
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
    console.log(`⌨️ Inserting Prompt... (${normalized.length} Zeichen)`);

    // Use robust insertText via evaluate
    await page.evaluate((txt) => {
        // Find the textarea or contenteditable element
        const editor = document.querySelector('textarea[aria-label="Message ChatGPT"], textarea, [contenteditable="true"]') as HTMLElement;

        if (editor) {
            editor.focus();

            // Try to clear existing content (if any)
            if (editor.tagName === 'TEXTAREA' || editor.tagName === 'INPUT') {
                (editor as HTMLTextAreaElement).value = '';
            } else {
                editor.innerText = '';
            }
            editor.dispatchEvent(new Event('input', { bubbles: true }));

            // Use execCommand for compatibility with ChatGPT's editor
            // This is generally safer than keyboard.type for long prompts
            const success = document.execCommand('insertText', false, txt);

            // Fallback if execCommand doesn't work
            if (!success || (editor.innerText || (editor as any).value || '').length < txt.length / 2) {
                console.log('⚠️ execCommand failed or incomplete, using direct value injection');
                if (editor.tagName === 'TEXTAREA' || editor.tagName === 'INPUT') {
                    (editor as HTMLTextAreaElement).value = txt;
                } else {
                    editor.innerText = txt;
                }
                // Trigger input events
                editor.dispatchEvent(new Event('input', { bubbles: true }));
                editor.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
    }, normalized);

    await sleep(1000); // Wait for UI to stabilize

    console.log('📤 Sending message (DOM-based)...');
    const sent = await page.evaluate((sel) => {
        const btn = document.querySelector<HTMLButtonElement>(sel);
        if (btn) {
            btn.click();
            return true;
        }
        return false;
    }, SEL_SEND_BUTTON);

    if (!sent) {
        console.log('⌨️ Send-Button not found via data-testid, falling back to Enter');
        await page.keyboard.press('Enter');
    }
    await sleep(2000);
}

async function getLatestAssistantText(page: Page): Promise<string> {
    const result = await page.evaluate(() => {
        const debug: string[] = [];

        // 1. Try modern data-testid first
        const turns = Array.from(document.querySelectorAll('[data-testid^="conversation-turn-"]'));
        debug.push(`turns: ${turns.length}`);
        if (turns.length > 0) {
            const lastTurn = turns[turns.length - 1];
            const content = lastTurn.querySelector('.markdown, .prose, [data-message-author-role="assistant"]');
            if (content) {
                const text = (content as HTMLElement).innerText || '';
                if (text.length > 10) return { text, method: 'data-testid+content', debug };
            }
            const text = (lastTurn as HTMLElement).innerText || '';
            if (text.length > 10) return { text, method: 'data-testid', debug };
        }

        // 2. Try standard author role
        const assistantNodes = Array.from(document.querySelectorAll<HTMLElement>('[data-message-author-role="assistant"]'));
        debug.push(`assistant-role: ${assistantNodes.length}`);
        if (assistantNodes.length) {
            const last = assistantNodes[assistantNodes.length - 1];
            const text = last.innerText || last.textContent || '';
            if (text.length > 10) return { text, method: 'author-role', debug };
        }

        // 3. Try generic prose/markdown
        const proseNodes = Array.from(document.querySelectorAll<HTMLElement>('.prose, .markdown, article'));
        debug.push(`prose: ${proseNodes.length}`);
        if (proseNodes.length) {
            const last = proseNodes[proseNodes.length - 1];
            const text = last.innerText || last.textContent || '';
            if (text.length > 10) return { text, method: 'prose', debug };
        }

        // 4. Try any div with substantial text content (NEW FALLBACK)
        const allDivs = Array.from(document.querySelectorAll('div'));
        const textDivs = allDivs.filter(d => {
            const text = (d as HTMLElement).innerText || '';
            return text.length > 50 && !text.includes('Message ChatGPT');
        });
        debug.push(`text-divs: ${textDivs.length}`);
        if (textDivs.length) {
            const last = textDivs[textDivs.length - 1] as HTMLElement;
            const text = last.innerText || '';
            if (text.length > 10) return { text, method: 'text-div-fallback', debug };
        }

        return { text: '', method: 'none', debug };
    });

    if (result.text.length > 0 && result.method !== 'text-div-fallback') {
        // Only log on first successful detection
        if (!lastDetectionMethod || lastDetectionMethod !== result.method) {
            console.log(`✓ Answer detected via: ${result.method}`);
            lastDetectionMethod = result.method;
        }
    } else if (result.text.length === 0) {
        console.log(`⚠ No answer found. Debug: ${result.debug.join(', ')}`);
    }

    return (result.text || '').trim();
}

let lastDetectionMethod: string | null = null;

function answerLooksComplete(raw: string): boolean {
    const trimmed = raw.trimEnd();
    if (!trimmed) return false;

    if (trimmed.endsWith(SENTINEL)) return true;
    if (JSON_END_PATTERN.test(trimmed)) return true;

    return false;
}

async function isGenerating(page: Page): Promise<boolean> {
    return await page.evaluate((sel) => {
        // 1. Check for explicit stop button
        if (document.querySelector(sel)) return true;

        // 2. Check for "Stop" text in any button
        const btns = Array.from(document.querySelectorAll('button'));
        const hasStop = btns.some(b => {
            const t = b.innerText.toLowerCase();
            return t.includes('stop') || t.includes('stopp') || t.includes('abbrechen');
        });
        if (hasStop) return true;

        // 3. Look for the "Send" button being in a disabled or loading state
        // (ChatGPT often hides the send button or replaces it with the stop button)
        const sendBtn = document.querySelector('[data-testid="send-button"]');
        if (!sendBtn || (sendBtn as HTMLButtonElement).disabled) return true;

        return false;
    }, SEL_STOP_BUTTON);
}

async function waitForStableAnswer(page: Page): Promise<string> {
    let lastText = '';
    let stableCount = 0;

    const maxStable = 4;
    const maxTimeMs = 120_000;
    const pollMs = 1_000;
    const started = Date.now();

    while (Date.now() - started < maxTimeMs) {
        const [text, busy] = await Promise.all([
            getLatestAssistantText(page),
            isGenerating(page),
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

        // If we have some significant text and it hasn't changed, and we aren't "busy",
        // we can assume it's done. 
        if (text.length > 20 && !busy && stableCount >= maxStable) {
            console.log('✅ Antwort stabil, nicht beschäftigt - Breche ab');
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

    // --- Safety Check: Wait if ChatGPT is still busy from a previous run (reduced timeout) ---
    let busyAttempts = 0;
    while (await isGenerating(page) && busyAttempts < 10) {
        if (busyAttempts === 0) console.log('⏳ ChatGPT is busy, waiting...');
        await sleep(1000);
        busyAttempts++;
    }

    await focusComposer(page);
    await setTextareaValueAndSend(page, prompt);

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
        // Global Mutex to prevent overlapping prompts on the same tab
        const result = call_mutex.then(async () => {
            return await sendQuestionAndGetAnswer(prompt);
        });

        // Update the mutex to wait for this call to finish
        call_mutex = result.then(() => { }).catch(() => { });

        return await result;
    }
}
