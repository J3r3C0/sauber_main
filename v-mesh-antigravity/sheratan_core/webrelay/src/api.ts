// ========================================
// Sheratan WebRelay - HTTP API Server
// ========================================

import express, { Request, Response } from 'express';
import cors from 'cors';
import { UnifiedJob, UnifiedResult } from './types.js';
import { JobRouter } from './job-router.js';
import { ChatGPTBackend } from './backends/chatgpt.js';
import { parseResponse } from './parser.js';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ========================================
// Core2 LCP System Prompt
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

const app = express();
const PORT = parseInt(process.env.PORT || '3000', 10);

// Load configuration
const configPath = path.join(__dirname, '..', 'config', 'default-config.json');
const config = fs.readJSONSync(configPath);

// Initialize ChatGPT backend
const backend = new ChatGPTBackend();

// Middleware
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Request logging
app.use((req, _res, next) => {
    console.log(`${new Date().toISOString()} ${req.method} ${req.path}`);
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
        const { prompt, session_id } = req.body;

        if (!prompt || typeof prompt !== 'string') {
            return res.status(400).json({
                ok: false,
                error: 'Missing or invalid "prompt" field'
            });
        }

        console.log(`📨 LLM Call Request (${prompt.length} chars)`);
        const startTime = Date.now();

        // Call ChatGPT
        const result = await backend.call(prompt);

        // Parse response
        const parsed = parseResponse(result.answer, { sentinel: config.parser.sentinel });

        // Build response
        const response: any = {
            ok: true,
            llm_backend: 'chatgpt',
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
// Submit Unified Job (Async)
// POST /api/job/submit
// Body: UnifiedJob
// ========================================
app.post('/api/job/submit', async (req: Request, res: Response) => {
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

        // Call ChatGPT
        const result = await backend.call(prompt);

        // Build unified result
        const out: UnifiedResult = {
            job_id: job.job_id,
            created_at: new Date().toISOString(),
            ok: true,
            convoUrl: result.url,
            session_id: job.session_id || null,
            llm_backend: 'chatgpt',
            execution_time_ms: Date.now() - startTime,
        };

        // Self-Loop: Return raw text, no JSON parsing
        if (job.payload?.job_type === 'sheratan_selfloop') {
            console.log(`✅ Self-Loop Job Complete: ${job.job_id}`);
            out.text = result.answer;  // Raw markdown response
            out.action = 'selfloop_result';
            res.json(out);
            return;
        }

        // Parse response (for LCP/plain jobs)
        const parsed = parseResponse(result.answer, { sentinel: config.parser.sentinel });

        // Add type-specific fields
        if (parsed.type === 'lcp') {
            if (parsed.action === 'create_followup_jobs') {
                out.action = parsed.action;
                out.commentary = parsed.commentary;
                out.new_jobs = parsed.new_jobs;
            } else {
                out.thought = parsed.thought;
                out.actions = parsed.actions;
            }
        } else {
            out.summary = parsed.summary;
        }

        console.log(`✅ Job Complete: ${job.job_id}`);
        res.json(out);

    } catch (error: any) {
        console.error(`❌ Job Error:`, error?.message || error);
        res.status(500).json({
            ok: false,
            error: error?.message || String(error)
        });
    }
});

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
            console.log('║   Sheratan WebRelay HTTP API v1.0                   ║');
            console.log('╚═══════════════════════════════════════════════════════╝');
            console.log();
            console.log(`🌐 Server running on http://0.0.0.0:${PORT}`);
            console.log(`🤖 Backend: ChatGPT Browser (Puppeteer)`);
            console.log();
            console.log('📡 Endpoints:');
            console.log(`   GET  /health              - Health check`);
            console.log(`   POST /api/llm/call        - Direct LLM call`);
            console.log(`   POST /api/job/submit      - Submit UnifiedJob`);
            console.log();
            resolve();
        });
    });
}

export default app;
