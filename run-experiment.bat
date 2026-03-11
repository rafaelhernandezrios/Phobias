@echo off
title VR-ATR EEG Experiment
echo ========================================
echo   VR Phobia + EEG Experiment Launcher
echo ========================================
echo.

cd /d "%~dp0"

if not exist "cert.pem" (
    echo [1/2] Generando certificados...
    call npm run cert
    echo.
) else (
    echo [OK] Certificados ya existen.
)

echo [2/2] Iniciando servidor HTTPS + recorder EEG + monitor...
echo.
echo Abre en el navegador: https://127.0.0.1:8443
echo Para VR: https://TU_IP:8443
echo Se abrira la ventana del monitor (estado EEG + Level 1/2/3).
echo.
echo Presiona Ctrl+C para detener todo.
echo.

call npm run experiment

pause
