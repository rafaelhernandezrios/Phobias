@echo off
chcp 65001 >nul
title VR-ATR Phobia Experiment
setlocal EnableDelayedExpansion

set "MOCK=0"
if /I "%~1"=="--mock" set "MOCK=1"
if /I "%PHOBIAS_MOCK%"=="1" set "MOCK=1"

cd /d "%~dp0"
set ELECTRON_RUN_AS_NODE=

echo ========================================
echo   VR Phobia — full stack launcher
echo   VR恐怖症 一括起動 (Windows)
echo ========================================
echo.

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install LTS from https://nodejs.org
    pause
    exit /b 1
)

node -e "const s=require('./package.json').scripts.experiment||''; if(s.includes('adaptive_monitor_gui')) process.exit(1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] package.json uses legacy Tk monitor. Update the repo.
    pause
    exit /b 1
)

if not exist "node_modules\" (
    echo [deps] npm install...
    call npm install
    echo.
)

if not exist "monitor-electron\node_modules\" (
    echo [deps] monitor-electron...
    call npm install --prefix monitor-electron
    echo.
)

if not exist "cert.pem" (
    echo [cert] Generating TLS...
    call npm run cert
    echo.
)

echo [preflight] Checking environment...
call npm run preflight
if errorlevel 1 (
    echo.
    echo Fix errors above, then run again.
    pause
    exit /b 1
)

echo [python] Ensuring .venv...
call npm run setup:python
echo.

if "%MOCK%"=="1" (
    echo [start] MOCK stack — no AURA / EEG hardware
) else (
    echo [start] Full stack — aura_recorder + AURA LSL required
)
echo.
echo   URLs (HTTPS + WebSocket on port 8443^):
call npm run lan-urls
echo.
echo   PC browser:  https://127.0.0.1:8443
echo   Quest (Wi-Fi): use the LAN URL printed above
echo   Monitor:     Electron window opens automatically
echo.
echo   Stop: Ctrl+C in this window
echo.

if "%MOCK%"=="1" (
    call npm run experiment:mock
) else (
    call npm run experiment
)

echo.
pause
