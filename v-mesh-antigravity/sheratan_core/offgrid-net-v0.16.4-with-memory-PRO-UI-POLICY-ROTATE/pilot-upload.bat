@echo off
setlocal
cd /d "%~dp0"
echo [pilot] Creating test file and simulating upload...
powershell -NoProfile -Command "$p = Join-Path $pwd 'test.bin'; $bytes = New-Object Byte[] (32KB); (New-Object System.Random).NextBytes($bytes); [IO.File]::WriteAllBytes($p, $bytes); Write-Output $p"
python scripts\transfer_demo.py --outfile receipts_node-A.json
echo [pilot] Done.
pause
