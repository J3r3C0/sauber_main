@echo off
REM Wrapper to call START.ps1 from scripts folder
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\START.ps1"
