import puppeteer, { Browser, Page } from 'puppeteer-core';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isDist = __dirname.endsWith('dist') || __dirname.includes('dist' + path.sep);
const PROJECT_ROOT = isDist ? path.resolve(__dirname, '..', '..') : path.resolve(__dirname, '..');

// Runtime folders (canonical)
const RUNTIME_DIR = process.env.SHERATAN_RUNTIME_DIR
    ? path.resolve(process.env.SHERATAN_RUNTIME_DIR)
    : path.join(PROJECT_ROOT, 'runtime');

const OUTPUT_DIR = path.join(RUNTIME_DIR, 'output');
const STOP_FILE = path.join(RUNTIME_DIR, 'STOP_AUTOPILOT');

// Keep legacy compatibility: you can still redirect to v_mesh_output if you REALLY want
const STREAM_FILE = process.env.SHERATAN_STREAM_FILE
    ? path.resolve(process.env.SHERATAN_STREAM_FILE)
    : path.join(OUTPUT_DIR, 'live_stream.txt');

const BROWSER_URL = 'http://127.0.0.1:9222';

// Hard limits (G5_AUTOPILOT_LIMITS)
const MAX_TURNS = Number(process.env.SHERATAN_MAX_TURNS || '20');          // hard stop
const OPERATOR_ACK_AFTER = Number(process.env.SHERATAN_ACK_AFTER || '10'); // require operator after N
const FIRST_WAIT_MS = Number(process.env.SHERATAN_FIRST_WAIT_MS || '369000'); // legacy default 369s

// Escalation markers (G4_ESCALATION_DETECT) – minimal effective set
const ESCALATION_MARKERS: RegExp[] = [
    /\bewig\b/i,
    /naturgesetz/i,
    /unver[aä]nderlich/i,
    /keine\s+fragen/i,
    /\bfinal\b/i,
    /\bperfect\b/i,
    /law\s+of\s+reality/i,
    /singularity/i,
    /no\s+more\s+questions/i,
];

// Selectors copied from gemini.ts for consistency
const SEL_TEXTAREA = 'rich-textarea[placeholder], div.ql-editor[contenteditable="true"], textarea';
const SEL_SEND_BUTTON = 'button[aria-label*="Send"], button[mattooltip*="Send"]';

const FILTER_PATTERNS = [
    /^Copy/i,
    /^Share/i,
    /^Save/i,
    /^Thumbs/i,
    /^Good response/i,
    /^Bad response/i,
    /^Rate/i,
    /^Try again/i,
    /^New chat/i,
    /^Regenerate/i,
].filter(Boolean);

function ensureDir(p: string) {
    if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true });
}

function stopRequested(): boolean {
    try {
        return fs.existsSync(STOP_FILE);
    } catch {
        return false;
    }
}

function containsEscalation(text: string): boolean {
    return ESCALATION_MARKERS.some((rx) => rx.test(text));
}

function cleanText(raw: string): string {
    const lines = raw.split(/\r?\n/);
    const kept = lines.filter((l) => {
        const s = l.trim();
        if (!s) return false;
        return !FILTER_PATTERNS.some((rx) => rx.test(s));
    });
    return kept.join('\n').trim();
}

function nowIso() {
    return new Date().toISOString();
}

async function sleep(ms: number) {
    return new Promise((r) => setTimeout(r, ms));
}

async function connectBrowser(): Promise<Browser> {
    return await puppeteer.connect({ browserURL: BROWSER_URL });
}

async function getActivePage(browser: Browser): Promise<Page> {
    const pages = await browser.pages();
    if (!pages.length) throw new Error('No pages found. Is Gemini open?');
    // Heuristic: active page is last page
    return pages[pages.length - 1];
}

async function isGenerating(page: Page): Promise<boolean> {
    return await page.evaluate(() => {
        const indicators = Array.from(
            document.querySelectorAll('[class*="generating"], [class*="thinking"], [aria-label*="Stop"]')
        );
        return indicators.length > 0;
    });
}

async function getLatestResponse(page: Page): Promise<string> {
    const text = await page.evaluate(() => {
        const selectors = [
            'model-response',
            'message-content',
            '[data-message-author-role="assistant"]',
            '.markdown',
        ];

        const nodes: Element[] = [];
        for (const sel of selectors) {
            document.querySelectorAll(sel).forEach((n) => nodes.push(n));
        }
        // Use last visible chunk as "latest"
        const last = nodes.filter(Boolean).slice(-1)[0] as any;
        return last?.innerText || '';
    });
    return cleanText(text || '');
}

async function typeInto(page: Page, content: string) {
    const el = await page.waitForSelector(SEL_TEXTAREA, { timeout: 20000 });
    if (el) {
        await el.focus();
        await page.keyboard.type(content, { delay: 10 });
    }
}

async function clickSend(page: Page) {
    const btn = await page.waitForSelector(SEL_SEND_BUTTON, { timeout: 20000 });
    if (btn) {
        await btn.click();
    }
}

async function sendWeiter(page: Page) {
    await typeInto(page, 'weiter');
    await clickSend(page);
}

async function saveResponse(content: string, isInitial: boolean = false) {
    ensureDir(OUTPUT_DIR);
    const header = isInitial ? `\n\n=== INITIAL @ ${nowIso()} ===\n` : `\n\n=== UPDATE @ ${nowIso()} ===\n`;
    fs.appendFileSync(STREAM_FILE, header + content + '\n', 'utf-8');
}

async function run() {
    ensureDir(OUTPUT_DIR);

    const browser = await connectBrowser();
    const page = await getActivePage(browser);

    console.log(`✅ Connected. STREAM_FILE=${STREAM_FILE}`);
    console.log(`🧱 Limits: MAX_TURNS=${MAX_TURNS}, OPERATOR_ACK_AFTER=${OPERATOR_ACK_AFTER}`);
    console.log(`🛑 Stop file: ${STOP_FILE}`);

    let lastSeenText = '';
    let turns = 0;

    // Save initial response if present
    const initialText = await getLatestResponse(page);
    if (initialText && initialText.length > 5) {
        console.log('💾 Initial response detected!');
        await saveResponse(initialText, true);
        lastSeenText = initialText;
    }

    // If Gemini idle, optionally start after delay (but only if safe)
    if (!(await isGenerating(page)) && !stopRequested()) {
        console.log(`🤖 Gemini is idle, waiting ${Math.round(FIRST_WAIT_MS / 1000)}s before first "weiter"...`);
        await sleep(FIRST_WAIT_MS);
    }

    while (true) {
        try {
            if (stopRequested()) {
                console.log('🛑 STOP_AUTOPILOT detected. Exiting cleanly.');
                break;
            }

            if (turns >= MAX_TURNS) {
                console.log(`🛑 MAX_TURNS reached (${MAX_TURNS}). Exiting.`);
                break;
            }

            // Require operator acknowledgement after N turns
            if (turns >= OPERATOR_ACK_AFTER) {
                console.log(`⛔ Operator acknowledgement required after ${OPERATOR_ACK_AFTER} turns.`);
                console.log(`   Create file: ${path.join(RUNTIME_DIR, 'ACK_AUTOPILOT')} to continue, or STOP_AUTOPILOT to stop.`);
                const ackFile = path.join(RUNTIME_DIR, 'ACK_AUTOPILOT');
                // wait until ack or stop
                while (true) {
                    if (stopRequested()) break;
                    if (fs.existsSync(ackFile)) {
                        // consume ack once
                        try { fs.unlinkSync(ackFile); } catch { }
                        break;
                    }
                    await sleep(1000);
                }
                if (stopRequested()) {
                    console.log('🛑 STOP_AUTOPILOT detected during ACK wait. Exiting.');
                    break;
                }
            }

            if (await isGenerating(page)) {
                await sleep(2000);
                continue;
            }

            const latestText = await getLatestResponse(page);
            if (latestText && latestText !== lastSeenText) {
                console.log('📥 New response detected');

                if (containsEscalation(latestText)) {
                    console.log('⛔ Escalation marker detected. PAUSING autopilot (no "weiter").');
                    await saveResponse(latestText, false);
                    // Write a PAUSE note to output; operator must decide next step.
                    fs.appendFileSync(STREAM_FILE, `\n=== PAUSE_REASON @ ${nowIso()} ===\nEscalation marker hit. Autopilot stopped.\n`, 'utf-8');
                    break;
                }

                await saveResponse(latestText, false);
                lastSeenText = latestText;

                // Only send "weiter" if safe
                console.log('➡️ Sending "weiter"...');
                await sendWeiter(page);
                turns += 1;

                // give time for generation to start
                await sleep(5000);
            } else {
                await sleep(2000);
            }
        } catch (err) {
            console.error('❌ Loop Error:', err);
            await sleep(5000);
        }
    }

    try { await browser.disconnect(); } catch { }
    console.log('✅ Autopilot stopped.');
}

run().catch((e) => {
    console.error(e);
    process.exit(1);
});
