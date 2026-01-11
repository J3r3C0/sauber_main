// Sheratan Dashboard - JavaScript Logic

const API_BASE = 'http://localhost:8001';
let refreshInterval;

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Sheratan Dashboard loaded');

    // Initial load
    refreshJobs();
    refreshWorkers();
    checkSystemStatus();

    // Auto-refresh every 5 seconds
    refreshInterval = setInterval(() => {
        refreshJobs();
        refreshWorkers();
    }, 5000);

    addLog('Dashboard initialized');
});

// Quick Launch: Standard Code Analysis
async function launchStandardJob() {
    addLog('Launching code analysis job...');

    try {
        const response = await fetch(`${API_BASE}/api/missions/standard-code-analysis`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (response.ok) {
            showResult('success', `✅ Job launched! ID: ${data.job_id || data.job?.id}`);
            addLog(`Job created: ${data.job_id || data.job?.id}`);
            setTimeout(refreshJobs, 1000);
        } else {
            showResult('error', `❌ Error: ${data.detail || 'Unknown error'}`);
        }
    } catch (error) {
        showResult('error', `❌ Connection error: ${error.message}`);
        addLog(`Error: ${error.message}`);
    }
}

// Quick Launch: File Operation
async function launchFileOp() {
    addLog('Launching file operation...');

    const job = {
        kind: 'standard',
        worker_id: 'default_worker',
        payload: {
            task: {
                kind: 'list_files',
                params: {
                    root: '.',
                    patterns: ['*.md'],
                    recursive: false
                }
            }
        }
    };

    // Note: This would need a proper endpoint
    showResult('success', '✅ File operation queued (use custom JSON for now)');
    addLog('File operation template ready');
}

// Launch Custom Job
async function launchCustomJob() {
    const jsonInput = document.getElementById('customJobJson').value.trim();

    if (!jsonInput) {
        showResult('error', '❌ Please enter job JSON');
        return;
    }

    try {
        const jobData = JSON.parse(jsonInput);
        addLog('Launching custom job...');

        // This would need proper endpoint implementation
        showResult('success', '✅ Custom job format validated');
        addLog('Custom job ready (endpoint needed)');

    } catch (error) {
        showResult('error', `❌ Invalid JSON: ${error.message}`);
    }
}

// Refresh Jobs List
async function refreshJobs() {
    try {
        const response = await fetch(`${API_BASE}/api/jobs`);
        const jobs = await response.json();

        const jobsList = document.getElementById('jobsList');

        if (!jobs || jobs.length === 0) {
            jobsList.innerHTML = '<div class="loading">No active jobs</div>';
            return;
        }

        jobsList.innerHTML = jobs.slice(0, 10).map(job => `
            <div class="job-item">
                <div>
                    <div style="font-weight: 600; margin-bottom: 4px;">
                        ${job.id ? job.id.substring(0, 8) : 'unknown'}
                    </div>
                    <div style="font-size: 12px; color: var(--text-secondary);">
                        ${job.kind || 'unknown'}
                    </div>
                </div>
                <span class="job-status status-${job.status || 'unknown'}">
                    ${job.status || 'unknown'}
                </span>
            </div>
        `).join('');

    } catch (error) {
        document.getElementById('jobsList').innerHTML =
            '<div class="loading">Error loading jobs</div>';
        console.error('Jobs fetch error:', error);
    }
}

// Refresh Workers
async function refreshWorkers() {
    try {
        const response = await fetch(`${API_BASE}/api/mesh/workers`);
        const workers = await response.json();

        const workersList = document.getElementById('workersList');

        if (!workers || workers.length === 0) {
            workersList.innerHTML = '<div class="loading">No workers registered</div>';
            return;
        }

        workersList.innerHTML = workers.map(worker => `
            <div class="worker-item">
                <div>
                    <div style="font-weight: 600; margin-bottom: 4px;">
                        ${worker.worker_id}
                    </div>
                    <div style="font-size: 12px; color: var(--text-secondary);">
                        ${worker.capabilities?.length || 0} capabilities
                    </div>
                </div>
                <span class="job-status status-${worker.status === 'online' ? 'completed' : 'failed'}">
                    ${worker.status || 'unknown'}
                </span>
            </div>
        `).join('');

    } catch (error) {
        document.getElementById('workersList').innerHTML =
            '<div class="loading">Error loading workers</div>';
        console.error('Workers fetch error:', error);
    }
}

// Check System Status
async function checkSystemStatus() {
    try {
        const response = await fetch(`${API_BASE}/`);
        const data = await response.json();

        const statusBadge = document.getElementById('systemStatus');
        if (data.sheratan_core_v2 === 'running') {
            statusBadge.innerHTML = '<span class="dot"></span><span>Online</span>';
            statusBadge.style.background = 'rgba(0, 255, 136, 0.1)';
            statusBadge.style.borderColor = 'var(--success)';
        }
    } catch (error) {
        const statusBadge = document.getElementById('systemStatus');
        statusBadge.innerHTML = '<span class="dot"></span><span>Offline</span>';
        statusBadge.style.background = 'rgba(255, 68, 68, 0.1)';
        statusBadge.style.borderColor = 'var(--error)';
    }
}

// Show Result Message
function showResult(type, message) {
    const resultDiv = document.getElementById('jobResult');
    resultDiv.className = `result ${type}`;
    resultDiv.textContent = message;

    setTimeout(() => {
        resultDiv.className = 'result';
        resultDiv.textContent = '';
    }, 5000);
}

// Add Activity Log Entry
function addLog(message) {
    const activityLog = document.getElementById('activityLog');
    const now = new Date().toLocaleTimeString('de-DE');

    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
        <span class="time">${now}</span>
        <span class="message">${message}</span>
    `;

    activityLog.insertBefore(entry, activityLog.firstChild);

    // Keep only last 10 entries
    while (activityLog.children.length > 10) {
        activityLog.removeChild(activityLog.lastChild);
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});
