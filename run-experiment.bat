@echo off
chcp 65001 >nul
title VR-ATR EEG Experiment
echo ========================================
echo   VR Phobia + EEG — full stack launcher
echo   VR恐怖症＋EEG 一括起動
echo ========================================
echo.

cd /d "%~dp0"

if not exist "node_modules\" (
    echo [deps] Installing npm dependencies...
    call npm install
    echo.
)

if not exist "cert.pem" (
    echo [1/2] Generating TLS certs...
    call npm run cert
    echo.
) else (
    echo [OK] cert.pem already exists.
)

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [OK] Python venv activated (.venv^)
    echo.
) else (
    echo [WARN] No .venv — create: py -3 -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    echo.
)

echo [2/2] Starting: HTTPS app + aura_recorder + adaptive monitor GUI
echo.
echo   Browser:   https://127.0.0.1:8443
echo   VR (LAN):  https://YOUR_IP:8443
echo   Flow:      disclosure -^> wait for config (researcher: ID, level 0-5^)
echo   Monitor:   Tk window (EEG, manual levels, adaptive mood^)
echo.
echo   Stop: Ctrl+C
echo.

call npm run experiment

pause
