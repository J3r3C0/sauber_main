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
        await sleep(500); // Give it a moment to initialize
    }

    try {
        const url = page.url();
        if (!url || url === 'about:blank' || !url.includes(new URL(WEB_INTERFACE_URL).hostname)) {
            console.log(`🌐 Navigating to ${WEB_INTERFACE_URL}...`);
            // Use domcontentloaded for faster/more robust loading on slow connections
            await page.goto(WEB_INTERFACE_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
            await sleep(2000);
        }
    } catch (e: any) {
        console.warn('⚠️ Navigation warning:', e.message);
    }

    await page.bringToFront();
    return page;
}

async function focusComposer(page: Page): Promise<void> {
    await page.bringToFront();

    // Try direct click on textarea
    try {
        await page.waitForSelector(SEL_TEXTAREA, { timeout: 5000 });
        await page.click(SEL_TEXTAREA, { delay: 50 });
        await sleep(200);
        console.log('✅ Textarea fokussiert');
        return;
    } catch (e: any) {
        console.warn('⚠️ Textarea nicht per Selector erreichbar');
    }

    // Fallback: Find and click textarea via evaluate
    try {
        const clicked = await page.evaluate(() => {
            const textarea = document.querySelector<HTMLElement>('textarea[aria-label="Message ChatGPT"], textarea, [contenteditable="true"]');
            if (textarea) {
                textarea.focus();
                textarea.click();
                return true;
            }
            return false;
        });

        if (clicked) {
            console.log('✅ Textarea via evaluate fokussiert');
            await sleep(200);
            return;
        }
    } catch (e: any) {
        console.warn('⚠️ Evaluate-Fallback fehlgeschlagen');
    }

    // Last resort: Click in center of page
    console.log('🖱️ Last-Resort-Klick in der Mitte...');
    await page.mouse.click(500, 500);
    await sleep(200);
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

    console.log('📤 Sending message...');
    await page.keyboard.press('Enter');
    await sleep(1000);
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
        const { answer, url } = await sendQuestionAndGetAnswer(prompt);
        return { answer, url };
    }
}
