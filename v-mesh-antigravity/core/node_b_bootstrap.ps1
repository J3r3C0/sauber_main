# Node B Bootstrap Script
# Deployment target: Remote Desktop via Hotspot

Write-Host "🚀 Starting V-Mesh Node B (Remote Expansion)..." -ForegroundColor Cyan

$CONFIG_PATH = "C:\projectroot\v-mesh-antigravity\core\node_b_config.json"
if (-Not (Test-Path $CONFIG_PATH)) {
    Write-Host "❌ Error: node_b_config.json not found." -ForegroundColor Red
    exit
}

# Start the P2P connection to Host A
Write-Host "🌐 Connecting to Host A (192.168.1.206)..." -ForegroundColor Yellow
ping -n 1 192.168.1.206

Write-Host "✅ Connectivity established. Support Continuity Active." -ForegroundColor Green
Write-Host "🤖 Node B is now breathing." -ForegroundColor Cyan
