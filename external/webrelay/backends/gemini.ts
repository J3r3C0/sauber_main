// ========================================
// Sheratan WebRelay - Gemini Backend
// ========================================

import puppeteer, { Browser, Page } from 'puppeteer-core';
import { LLMBackend, BackendCallResult } from '../types.js';

// ========================================
// Core2 LCP System Prompt
// ========================================
const BROWSER_URL = process.env.BROWSER_URL || 'http://127.0.0.1:9222';
const WEB_INTERFACE_URL = process.env.WEB_INTERFACE_URL || 'https://gemini.google.com/app';

// Gemini-specific selectors
const SEL_TEXTAREA = 'rich-textarea[placeholder], div.ql-editor[contenteditable="true"], textarea';
const SEL_SEND_BUTTON = 'button[aria-label*="Send"], button[mattooltip*="Send"]';
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

async function findGeminiPage(browser: Browser): Promise<Page | null> {
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

async function ensureGeminiPage(browser: Browser): Promise<Page> {
    let page = await findGeminiPage(browser);
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

    // Try to find and click the input area
    try {
        // Gemini uses rich-textarea or contenteditable div
        const textarea = await page.$(SEL_TEXTAREA);
        if (textarea) {
            await textarea.click({ delay: 50 });
            await sleep(300);
            return;
        }
    } catch (e: any) {
        console.warn('⚠️ Textarea nicht erreichbar, nutze Fallback');
    }

    console.log('🖱️ Fallback-Klick in der Mitte...');
    await page.mouse.click(500, 500);
    await sleep(300);
}

async function setTextareaValueAndSend(page: Page, text: string): Promise<void> {
    const normalized = text.replace(/\r\n/g, '\n').replace(/\n+$/, '');

    console.log(`⌨️ Sende Prompt... (${normalized.length} Zeichen)`);

    // Hybrid approach: Type first 10 chars to trigger focus/events, then use insertText for the rest
    const typeLimit = 10;
    const toType = normalized.substring(0, typeLimit);
    const toInsert = normalized.substring(typeLimit);

    if (toType.length > 0) {
        await page.keyboard.type(toType, { delay: 20 });
    }

    if (toInsert.length > 0) {
        console.log('📝 Füge Rest per insertText-Kommando ein...');
        await page.evaluate((txt) => {
            // Priority: find the actual editable element
            const editor = document.querySelector('div.ql-editor[contenteditable="true"], [contenteditable="true"], rich-textarea textarea') as HTMLElement;

            if (editor) {
                editor.focus();
                // insertText is the standard way to programmatically "type" into rich editors 
                // while preserving their internal state/undo history
                const success = document.execCommand('insertText', false, txt);

                // Fallback for extremely stubborn editors: check if text actually arrived
                if (!success || editor.innerText.length < txt.length / 2) {
                    console.log('⚠️ execCommand failed, using direct value injection');
                    if (editor.tagName === 'TEXTAREA' || editor.tagName === 'INPUT') {
                        (editor as HTMLTextAreaElement).value += txt;
                    } else {
                        editor.innerText += txt;
                    }
                    // Trigger input events so the UI knows something changed
                    editor.dispatchEvent(new Event('input', { bubbles: true }));
                    editor.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        }, toInsert);
        await sleep(3000); // 3 seconds as requested by User for large prompt insertion stability
    }

    console.log('📤 Sende Nachricht...');

    // Try to click send button
    try {
        const sendBtn = await page.$(SEL_SEND_BUTTON);
        if (sendBtn) {
            await sendBtn.click();
        } else {
            // Fallback: Press Enter
            await page.keyboard.press('Enter');
        }
    } catch {
        await page.keyboard.press('Enter');
    }

    await sleep(500);
}


async function getLatestResponseText(page: Page): Promise<string> {
    // Filter out known UI noise
    const noisePatterns = [

        /^Shutterstock/i,
        /^Sources/i,
        /^View other drafts/i,
        /^Show drafts/i,
        /^Regenerate/i
    ];

    const text = await page.evaluate(() => {
        // Specific Gemini response containers (Updated 2026)
        const selectors = [
            'model-response',
            '[data-test-id="model-response-content"]', // More specific
            '.model-response-text',
            'message-content'
        ];

        for (const selector of selectors) {
            const elements = Array.from(document.querySelectorAll<HTMLElement>(selector));
            if (elements.length) {
                // Get the last one
                const last = elements[elements.length - 1];
                return last.innerText || last.textContent || '';
            }
        }

        // Fallback: look for content but exclude sidebars/images
        // We look for the main chat container
        const chatHistory = document.querySelector('infinite-scroller, .chat-history');
        if (chatHistory) {
            const bubbles = Array.from(chatHistory.querySelectorAll('[data-message-id]'));
            if (bubbles.length) {
                const lastBubble = bubbles[bubbles.length - 1] as HTMLElement;
                return lastBubble.innerText || lastBubble.textContent || '';
            }
        }

        return '';
    });

    let cleanText = (text || '').trim();

    // Client-side noise filtering
    const lines = cleanText.split('\n');
    const filteredLines = lines.filter(line => {
        return !noisePatterns.some(pattern => pattern.test(line));
    });

    return filteredLines.join('\n').trim();
}

function answerLooksComplete(raw: string): boolean {
    const trimmed = raw.trimEnd();
    if (!trimmed) return false;

    if (trimmed.endsWith(SENTINEL)) return true;
    if (JSON_END_PATTERN.test(trimmed)) return true;

    return false;
}

async function isGenerating(page: Page): Promise<boolean> {
    const found = await page.evaluate(() => {
        // Look for generating indicators
        const indicators = Array.from(
            document.querySelectorAll('[class*="generating"], [class*="thinking"], [aria-label*="Stop"]')
        );
        return indicators.length > 0;
    });
    return !!found;
}

async function waitForStableAnswer(page: Page, timeoutMs: number = 120_000): Promise<string> {
    let lastText = '';
    let stableCount = 0;

    const maxStable = 4;
    const pollMs = 1_000;
    const started = Date.now();

    // First, wait for generating to stop if it's currently active
    while (Date.now() - started < timeoutMs) {
        if (!await isGenerating(page)) break;
        await sleep(pollMs);
    }

    while (Date.now() - started < timeoutMs) {
        const [text, generating] = await Promise.all([
            getLatestResponseText(page),
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

        if (!generating && stableCount >= maxStable) {
            console.log('✅ Antwort stabil, nicht mehr am generieren');
            break;
        }

        await sleep(pollMs);
    }

    return lastText;
}

async function sendQuestionAndGetAnswer(
    prompt: string,
    config: any
): Promise<{ answer: string; url: string }> {
    const browser = await getBrowser();
    const page = await ensureGeminiPage(browser);

    console.log('🌐 Verbunden mit:', await page.title());

    // Wait for idle before starting new input
    console.log('⏳ Warte auf Leerlauf (Idle)...');
    let idleStarted = Date.now();
    while (Date.now() - idleStarted < 30000) {
        if (!await isGenerating(page)) break;
        await sleep(1000);
    }

    await focusComposer(page);
    await setTextareaValueAndSend(page, prompt);

    const timeout = config?.backend?.timeout_ms || 120_000;
    const answer = await waitForStableAnswer(page, timeout);
    const url = page.url();

    console.log('✅ Antwortlänge:', answer.length);

    return { answer, url };
}

/**
 * Gemini Backend
 */
export class GeminiBackend implements LLMBackend {
    name = 'gemini';
    private config: any;

    constructor(config?: any) {
        this.config = config;
    }

    async call(prompt: string): Promise<BackendCallResult> {
        const { answer, url } = await sendQuestionAndGetAnswer(prompt, this.config);
        return { answer, url };
    }
}
