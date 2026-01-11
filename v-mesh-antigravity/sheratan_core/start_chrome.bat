@echo off
echo.
echo ====================================
echo Starting Chrome for WebRelay
echo ====================================
echo.
echo Chrome wird mit Remote Debugging gestartet...
echo Port: 9222
echo.

start chrome ^
  --remote-debugging-port=9222 ^
  --remote-debugging-address=0.0.0.0 ^
  --remote-allow-origins=* ^
  --user-data-dir="%TEMP%\chrome-sheratan-debug"

echo.
echo Chrome wurde gestartet!
echo.
echo WICHTIG: Bitte jetzt bei ChatGPT einloggen:
echo https://chatgpt.com
echo.
echo Druecke eine Taste um fortzufahren...
pause >nul
