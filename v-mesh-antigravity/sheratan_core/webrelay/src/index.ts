// ========================================
// Sheratan WebRelay Worker - Main Entry Point
// ========================================

import dotenv from 'dotenv';
dotenv.config();

import path from 'path';
import fs from 'fs-extra';
import chokidar from 'chokidar';
import { fileURLToPath } from 'url';
import { UnifiedJob, UnifiedResult } from './types.js';
import { JobRouter } from './job-router.js';
import { ChatGPTBackend } from './backends/chatgpt.js';
import { parseResponse } from './parser.js';
import { startServer } from './api.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const RELAY_OUT = path.join(PROJECT_ROOT, process.env.RELAY_OUT_DIR || 'webrelay_out');
const RELAY_IN = path.join(PROJECT_ROOT, process.env.RELAY_IN_DIR || 'webrelay_in');

// Load configuration
const configPath = path.join(__dirname, '..', 'config', 'default-config.json');
const config = fs.readJSONSync(configPath);

// Initialize ChatGPT backend
const backend = new ChatGPTBackend();

// Job queue
type Job = { filename: string; fullPath: string };
const PENDING = new Map<string, NodeJS.Timeout>();
const QUEUE: Job[] = [];
let processing = false;

async function ensureDirs() {
    await fs.ensureDir(RELAY_OUT);
    await fs.ensureDir(RELAY_IN);
}

async function enqueue(job: Job) {
    QUEUE.push(job);
    if (!processing) {
        processing = true;
        try {
            while (QUEUE.length > 0) {
                const next = QUEUE.shift()!;
                await handleJob(next);
            }
        } finally {
            processing = false;
        }
    }
}

async function handleJob(job: Job) {
    try {
        const data: UnifiedJob = await fs.readJSON(job.fullPath).catch(() => null);
        if (!data) {
            console.warn(`⚠️ Invalid JSON: ${job.filename}`);
            return;
        }

        console.log(`\n📨 Processing Job: ${data.job_id} (${data.kind})`);

        const router = new JobRouter();
        const startTime = Date.now();

        try {
            // Build prompt
            const prompt = router.buildPrompt(data);
            console.log(`📝 Prompt length: ${prompt.length} chars`);

            // Call ChatGPT
            console.log(`🤖 Calling ChatGPT...`);
            const result = await backend.call(prompt);

            // Parse response
            const parsed = parseResponse(result.answer, { sentinel: config.parser.sentinel });
            console.log(`✅ Response type: ${parsed.type}`);

            // Build unified result
            const out: UnifiedResult = {
                job_id: data.job_id,
                created_at: new Date().toISOString(),
                ok: true,
                convoUrl: result.url,
                session_id: data.session_id || null,
                llm_backend: 'chatgpt',
                execution_time_ms: Date.now() - startTime,
            };

            // Add type-specific fields
            if (parsed.type === 'lcp') {
                if (parsed.action === 'create_followup_jobs') {
                    // agent_plan result format
                    out.action = parsed.action;
                    out.commentary = parsed.commentary;
                    out.new_jobs = parsed.new_jobs;
                } else {
                    // Standard LCP format
                    out.thought = parsed.thought;
                    out.actions = parsed.actions;
                }
            } else {
                // Plain text
                out.summary = parsed.summary;
            }

            await writeResult(job.filename, out);
            console.log(`✅ Job Result: ${data.job_id}`);

        } catch (err: any) {
            console.error(`❌ Job failed:`, err?.message || err);
            const errorResult: UnifiedResult = {
                job_id: data.job_id,
                created_at: new Date().toISOString(),
                ok: false,
                error: err?.message || String(err),
                session_id: data.session_id || null,
                llm_backend: 'chatgpt',
                execution_time_ms: Date.now() - startTime,
            };

            await writeResult(job.filename, errorResult);
        }
    } catch (err: any) {
        console.error(`❌ Error processing ${job.filename}:`, err?.message || err);
    }
}

async function writeResult(jobFilename: string, result: UnifiedResult) {
    const resultFilename = jobFilename.replace(/\.job\.json$/, '.result.json').replace(/\.json$/, '.result.json');
    const outPath = path.join(RELAY_IN, resultFilename);
    await fs.writeJSON(outPath, result, { spaces: 2 });
}

function debounceFile(fullPath: string) {
    const filename = path.basename(fullPath).toLowerCase();
    if (!filename.endsWith('.json')) return;

    const prev = PENDING.get(fullPath);
    if (prev) clearTimeout(prev);

    const timer = setTimeout(() => {
        PENDING.delete(fullPath);
        enqueue({ filename: path.basename(fullPath), fullPath });
    }, config.watcher.debounce_ms);

    PENDING.set(fullPath, timer);
}

async function startFileWatcher() {
    await ensureDirs();

    console.log('📂 File Watcher Mode:');
    console.log(`   OUT: ${RELAY_OUT}`);
    console.log(`   IN:  ${RELAY_IN}`);
    console.log();

    // Process existing files
    const files = (await fs.readdir(RELAY_OUT)).filter((f: string) => f.endsWith('.json'));
    for (const f of files) debounceFile(path.join(RELAY_OUT, f));

    console.log(`👀 Watcher aktiv auf: ${RELAY_OUT}`);
    console.log();

    const watcher = chokidar.watch(RELAY_OUT, {
        ignoreInitial: true,
        depth: 0,
        awaitWriteFinish: {
            stabilityThreshold: config.watcher.stability_threshold,
            pollInterval: config.watcher.poll_interval
        }
    });

    watcher
        .on('add', debounceFile)
        .on('change', debounceFile)
        .on('error', (e) => console.error('❌ Watcher-Fehler:', e));
}

async function main() {
    console.log('╔═══════════════════════════════════════════════════════╗');
    console.log('║   Sheratan WebRelay Worker v1.0                     ║');
    console.log('╚═══════════════════════════════════════════════════════╝');
    console.log();
    console.log('🤖 Backend: ChatGPT Browser (Puppeteer)');
    console.log();

    // Start HTTP API Server
    await startServer();

    // Start File Watcher (for backward compatibility)
    await startFileWatcher();

    console.log('✨ WebRelay Ready! Supports HTTP API + File Mode');
    console.log();
}

main();

