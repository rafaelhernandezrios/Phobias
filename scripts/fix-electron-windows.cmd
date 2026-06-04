@echo off
chcp 65001 >nul
title Fix Electron (Windows)
cd /d "%~dp0\.."
set "ELECTRON_RUN_AS_NODE="
set ELECTRON_RUN_AS_NODE=
set ELECTRON_SKIP_BINARY_DOWNLOAD=

echo ========================================
echo   Reparar Electron en Windows
echo ========================================
echo.

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Instala Node.js LTS desde https://nodejs.org
    pause
    exit /b 1
)

echo [1/4] Borrar Electron corrupto...
if exist "monitor-electron\node_modules\electron" (
    rmdir /s /q "monitor-electron\node_modules\electron"
)
echo.

echo [2/4] npm install electron en monitor-electron...
cd monitor-electron
call npm install electron@33.4.11 --save-dev --no-fund --no-audit
if errorlevel 1 (
    echo [ERROR] Revisa monitor-electron\package.json — debe ser JSON valido
    cd ..
    pause
    exit /b 1
)
cd ..
echo.

echo [3/4] Descargar electron.exe (forzado)...
rem Opcional si GitHub falla — descomenta la siguiente linea:
rem set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
node scripts\install-electron-force.cjs
if errorlevel 1 (
    echo.
    echo === Reintento con mirror alternativo ===
    set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
    node scripts\install-electron-force.cjs
)
if errorlevel 1 (
    pause
    exit /b 1
)
echo.

echo [4/4] Compilar monitor...
call npm run build --prefix monitor-electron
echo.

if exist "monitor-electron\node_modules\electron\dist\electron.exe" (
    echo [OK] Listo. Ejecuta: run-experiment-mock.bat
) else (
    echo [ERROR] Sigue sin electron.exe
)
echo.
pause
