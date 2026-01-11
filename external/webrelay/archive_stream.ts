import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isDist = __dirname.endsWith('dist') || __dirname.includes('dist' + path.sep);
const PROJECT_ROOT = isDist ? path.resolve(__dirname, '..', '..') : path.resolve(__dirname, '..');

const STREAM_FILE = path.join(PROJECT_ROOT, 'runtime/narrative/live_stream.txt');
const V_MESH_ROOT = path.join(PROJECT_ROOT, 'v-mesh-antigravity');
const ARCHIVE_DIR = path.join(V_MESH_ROOT, 'history');
const INBOX_DIR = path.join(V_MESH_ROOT, 'synapses/messages/inbox');
const ARCHIVE_MSG_DIR = path.join(V_MESH_ROOT, 'synapses/messages/archive');

async function archive() {
    console.log('📦 Starting V-Mesh Stream & Inbox Archiving...');

    // 1. Archive legacy stream file
    if (fs.existsSync(STREAM_FILE)) {
        const content = fs.readFileSync(STREAM_FILE, 'utf8');
        if (content.trim()) {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const archivePath = path.join(ARCHIVE_DIR, `legacy_stream_${timestamp}.txt`);
            console.log(`📝 Archiving legacy stream to ${path.basename(archivePath)}...`);
            fs.writeFileSync(archivePath, content);
            fs.writeFileSync(STREAM_FILE, '');
        }
    }

    // 2. Archive individual inbox messages
    if (fs.existsSync(INBOX_DIR)) {
        if (!fs.existsSync(ARCHIVE_MSG_DIR)) {
            fs.mkdirSync(ARCHIVE_MSG_DIR, { recursive: true });
        }

        const files = fs.readdirSync(INBOX_DIR);
        console.log(`📂 Found ${files.length} messages in inbox.`);

        for (const file of files) {
            const src = path.join(INBOX_DIR, file);
            const dest = path.join(ARCHIVE_MSG_DIR, file);

            console.log(`🚚 Moving ${file} to archive...`);
            fs.renameSync(src, dest);
        }
    }

    console.log('✅ Archiving complete.');
}

archive().catch(console.error);
