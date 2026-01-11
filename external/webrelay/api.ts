// ========================================
// Sheratan WebRelay - HTTP API Server
// ========================================

import 'dotenv/config';
import express, { Request, Response } from 'express';
import cors from 'cors';
import { UnifiedJob, UnifiedResult } from './types.js';
import { JobRouter } from './job-router.js';
import { ChatGPTBackend } from './backends/chatgpt.js';
import { GeminiBackend } from './backends/gemini.js';
import { parseResponse } from './parser.js';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);



const app = express();
const PORT = parseInt(process.env.PORT || '3000', 10);

const isDist = __dirname.endsWith('dist') || __dirname.includes('dist' + path.sep);
const PROJECT_ROOT = isDist ? path.resolve(__dirname, '..') : __dirname;

// Load configuration
const configPath = path.join(PROJECT_ROOT, 'v_config', 'default-config.json');
const config = fs.readJSONSync(configPath);

// Initialize backend based on environment
const LLM_BACKEND = process.env.LLM_BACKEND || 'chatgpt';
const backend = LLM_BACKEND === 'gemini' ? new GeminiBackend(config) : new ChatGPTBackend();

console.log(`🤖 Using LLM Backend: ${backend.name}`);

// Middleware
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Request logging (skip health checks)
app.use((req, _res, next) => {
    if (req.path !== '/health') {
        console.log(`${new Date().toISOString()} ${req.method} ${req.path}`);
    }
    next();
});

// ========================================
// Health Check
// ========================================
app.get('/health', (_req: Request, res: Response) => {
    res.json({
        status: 'ok',
        service: 'sheratan-webrelay',
        version: '1.0.0',
        backend: 'chatgpt',
        timestamp: new Date().toISOString()
    });
});

// ========================================
// Direct LLM Call
// POST /api/llm/call
// Body: { prompt: string, session_id?: string }
// ========================================
app.post('/api/llm/call', async (req: Request, res: Response) => {
    try {
        const apiKey = req.headers['x-sheratan-key'];
        if (apiKey !== process.env.SHERATAN_API_KEY) {
            console.log(`⚠️ Blocked unauthorized LLM call (Header: ${apiKey})`);
            return res.status(403).json({ ok: false, error: 'Forbidden: API Key required' });
        }

        const { prompt, session_id, llm_backend } = req.body;

        if (!prompt || typeof prompt !== 'string') {
            return res.status(400).json({
                ok: false,
                error: 'Missing or invalid "prompt" field'
            });
        }

        // Dynamic backend selection
        const chatgpt = new ChatGPTBackend();
        const gemini = new GeminiBackend(config);
        const activeBackend = llm_backend === 'chatgpt' ? chatgpt
            : llm_backend === 'gemini' ? gemini
                : backend; // use default from startup

        console.log(`📨 LLM Call Request (${prompt.length} chars) using ${activeBackend.name}`);
        const startTime = Date.now();

        // Call LLM Backend
        const result = await activeBackend.call(prompt);

        // Parse response
        const parsed = parseResponse(result.answer, { sentinel: config.parser.sentinel });

        // Build response
        const response: any = {
            ok: true,
            llm_backend: activeBackend.name,
            execution_time_ms: Date.now() - startTime,
            convoUrl: result.url,
            session_id: session_id || null
        };

        if (parsed.type === 'lcp') {
            response.type = 'lcp';
            if (parsed.action === 'create_followup_jobs') {
                response.action = parsed.action;
                response.commentary = parsed.commentary;
                response.new_jobs = parsed.new_jobs;
            } else {
                response.thought = parsed.thought;
                response.actions = parsed.actions;
            }
        } else {
            response.type = 'plain';
            response.summary = parsed.summary;
        }

        console.log(`✅ LLM Call Complete (${response.execution_time_ms}ms)`);
        res.json(response);

    } catch (error: any) {
        console.error(`❌ LLM Call Error:`, error?.message || error);
        res.status(500).json({
            ok: false,
            error: error?.message || String(error)
        });
    }
});

// ========================================
// Submit Unified Job (Shared Logic)
// ========================================
async function handleJobSubmit(req: Request, res: Response) {
    try {
        const job: UnifiedJob = req.body;

        if (!job.job_id || !job.kind) {
            return res.status(400).json({
                ok: false,
                error: 'Missing job_id or kind'
            });
        }

        console.log(`📨 Job Submit: ${job.job_id} (${job.kind})`);
        const startTime = Date.now();

        const router = new JobRouter();
        const prompt = router.buildPrompt(job);

        // Dynamic backend selection
        const chatgpt = new ChatGPTBackend();
        const gemini = new GeminiBackend(config);
        const activeBackend = job.llm_backend === 'chatgpt' ? chatgpt
            : job.llm_backend === 'gemini' ? gemini
                : backend; // use default from startup

        // Call LLM Backend
        const result = await activeBackend.call(prompt);

        // Build unified result
        const out: UnifiedResult = {
            job_id: job.job_id,
            created_at: new Date().toISOString(),
            ok: true,
            convoUrl: result.url,
            session_id: job.session_id || null,
            llm_backend: activeBackend.name,
            execution_time_ms: Date.now() - startTime,
        };

        // Self-Loop: Return raw text, no JSON parsing
        if (job.kind === 'self_loop' || job.kind === 'sheratan_selfloop') {
            (out as any).text = result.answer;
        } else {
            // LCP: Parse JSON
            try {
                const parsed = parseResponse(result.answer, { sentinel: config.parser.sentinel });
                if (parsed.type === 'lcp') {
                    if (parsed.action === 'create_followup_jobs') {
                        out.action = parsed.action;
                        out.commentary = parsed.commentary;
                        out.new_jobs = parsed.new_jobs;
                    } else {
                        out.thought = parsed.thought;
                        out.actions = parsed.actions;
                        out.action = parsed.action;
                        out.commentary = parsed.commentary;
                    }
                } else {
                    out.summary = parsed.summary;
                }
            } catch (e: any) {
                console.warn('⚠️ Result parsing failed:', e.message);
                out.summary = result.answer;
            }
        }

        console.log(`✅ Job Complete: ${job.job_id} (${out.execution_time_ms}ms)`);
        res.json(out);

    } catch (error: any) {
        console.error(`❌ Job Error:`, error?.message || error);
        res.status(500).json({
            ok: false,
            error: error?.message || String(error)
        });
    }
}

// ========================================
// Endpoints
// ========================================

// Legacy /run alias for older Workers
app.post('/run', handleJobSubmit);

// Standard v2.1 Submit endpoint
app.post('/api/job/submit', handleJobSubmit);

// ========================================
// Root Endpoint
// ========================================
app.get('/', (_req: Request, res: Response) => {
    res.json({
        service: 'Sheratan WebRelay',
        version: '1.0.0',
        endpoints: {
            health: 'GET /health',
            llm_call: 'POST /api/llm/call',
            job_submit: 'POST /api/job/submit'
        }
    });
});

// ========================================
// Start Server
// ========================================
export function startServer() {
    return new Promise<void>((resolve) => {
        app.listen(PORT, '0.0.0.0', () => {
            console.log();
            console.log('╔═══════════════════════════════════════════════════════╗');
            console.log('║   Sheratan WebRelay HTTP API v2.0                   ║');
            console.log('╚═══════════════════════════════════════════════════════╝');
            console.log();
            console.log(`🌐 Server: http://0.0.0.0:${PORT}`);
            console.log(`🎯 LLM1 (Gemini): Writes to runtime/narrative`);
            console.log(`🛡️ LLM2 (ChatGPT): Audits via /api/llm/call`);
            console.log();
            console.log('📡 Endpoints:');
            console.log(`   GET  /health              - Health check`);
            console.log(`   POST /api/llm/call        - LLM2 Audit calls`);
            console.log(`   POST /api/job/submit      - Submit UnifiedJob`);
            console.log();
            resolve();
        });
    });
}

export default app;
