@echo off
chcp 65001 >nul
title VR-ATR Phobia Experiment
setlocal EnableDelayedExpansion

set "MOCK=0"
if /I "%~1"=="--mock" set "MOCK=1"
if /I "%PHOBIAS_MOCK%"=="1" set "MOCK=1"

cd /d "%~dp0"

echo ========================================
echo   VR Phobia — launcher (Windows)
echo ========================================
echo.

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install LTS from https://nodejs.org
    pause
    exit /b 1
)

if not exist "node_modules\" (
    echo [deps] npm install...
    call npm install
    echo.
)

if not exist "cert.pem" (
    echo [cert] Generating TLS...
    call npm run cert
    echo.
)

if "%MOCK%"=="1" (
    echo [preflight] Mock mode...
    call npm run preflight:mock
) else (
    echo [preflight] Full EEG...
    call npm run preflight
    if errorlevel 1 goto :prefail
    echo [python] Ensuring .venv...
    call npm run setup:python
)
if errorlevel 1 goto :prefail
echo.

if "%MOCK%"=="1" (
    echo [start] HTTPS + mock EEG — no AURA, no Electron
) else (
    echo [start] HTTPS + aura_recorder — AURA LSL required
)
echo.
call npm run lan-urls
echo.
echo   Researcher panel: https://127.0.0.1:8443/researcher.html
echo   VR participant:   https://127.0.0.1:8443/
echo   Stop: Ctrl+C
echo.

if "%MOCK%"=="1" (
    call npm run experiment:mock
) else (
    call npm run experiment
)
goto :end

:prefail
echo.
echo Fix errors above, then run again.
pause
exit /b 1

:end
echo.
pause
