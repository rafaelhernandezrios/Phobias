@echo off
chcp 65001 >nul
title Fix Electron (monitor-electron)
cd /d "%~dp0\.."
set "ELECTRON_RUN_AS_NODE="
set ELECTRON_RUN_AS_NODE=

echo === Reparar Electron en Windows ===
echo.

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Instala Node.js LTS desde https://nodejs.org
    pause
    exit /b 1
)

echo [1/3] npm install (raiz + monitor-electron)...
call npm install
call npm install --prefix monitor-electron
echo.

echo [2/3] Reinstalar binario de Electron...
cd monitor-electron
call npx electron@33.4.11 install
cd ..
echo.

echo [3/3] Compilar monitor...
call npm run build --prefix monitor-electron
echo.

if exist "monitor-electron\node_modules\electron\dist\electron.exe" (
    echo [OK] Electron listo: monitor-electron\node_modules\electron\dist\electron.exe
) else (
    echo [WARN] No se encontro electron.exe — revisa antivirus / proxy de red
)

echo.
echo Prueba: run-experiment-mock.bat
pause
