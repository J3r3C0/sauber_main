@echo off
REM ======================================================
REM Antigravity Process Cleanup Script
REM Beendet unnötige Antigravity-Instanzen sicher
REM ======================================================

echo.
echo ========================================
echo Antigravity Process Cleanup
echo ========================================
echo.

REM Zähle aktive Antigravity Prozesse
for /f %%a in ('tasklist ^| find /c "Antigravity.exe"') do set COUNT=%%a

echo Aktuell laufende Antigravity-Prozesse: %COUNT%
echo.

if %COUNT% LEQ 3 (
    echo ✓ Prozessanzahl ist OK ^(≤3^)
    echo Keine Aktion erforderlich.
    echo.
    pause
    exit /b 0
)

echo ⚠ Zu viele Antigravity-Prozesse gefunden ^(%COUNT%^)!
echo.
echo WICHTIG: Bitte schließe MANUELL alle nicht benötigten Antigravity-Fenster
echo bevor du dieses Script verwendest!
echo.
echo Empfehlung:
echo 1. Task Manager öffnen ^(Ctrl+Shift+Esc^)
echo 2. Sortiere nach "Arbeitssatz" ^(RAM-Nutzung^)
echo 3. Finde Antigravity.exe Prozesse mit hohem RAM
echo 4. Rechtsklick → Task beenden
echo.
echo Alternative: Alle Antigravity-Prozesse beenden und neu starten
echo.

choice /C YN /M "Alle Antigravity-Prozesse jetzt beenden"
if errorlevel 2 goto :CANCEL
if errorlevel 1 goto :CLEANUP

:CLEANUP
echo.
echo Beende alle Antigravity-Prozesse...
taskkill /F /IM Antigravity.exe /T >nul 2>&1

timeout /t 2 /nobreak >nul

echo.
echo ✓ Alle Antigravity-Prozesse beendet!
echo.
echo WICHTIG: 
echo - Starte Antigravity NEU
echo - Öffne nur die Tabs die du wirklich brauchst
echo - Jeder Tab = neuer Prozess!
echo.
goto :END

:CANCEL
echo.
echo Abgebrochen. Keine Prozesse beendet.
echo.

:END
echo ========================================
echo.
pause
