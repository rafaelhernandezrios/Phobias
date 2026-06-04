@echo off
chcp 65001 >nul
title Fix Electron (monitor-electron)
cd /d "%~dp0\.."
set "ELECTRON_RUN_AS_NODE="
set ELECTRON_RUN_AS_NODE=

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

echo [1/5] Borrar Electron corrupto...
if exist "monitor-electron\node_modules\electron" (
    rmdir /s /q "monitor-electron\node_modules\electron"
    echo       Eliminado monitor-electron\node_modules\electron
)
echo.

echo [2/5] Reinstalar paquete electron...
cd monitor-electron
call npm install electron@33.4.11 --save-dev --no-fund --no-audit
if errorlevel 1 (
    echo [ERROR] npm install electron fallo
    cd ..
    pause
    exit /b 1
)
echo.

echo [3/5] Descargar electron.exe (install.js)...
if not exist "node_modules\electron\install.js" (
    echo [ERROR] No existe install.js — revisa red / antivirus
    cd ..
    pause
    exit /b 1
)
node node_modules\electron\install.js
if errorlevel 1 (
    echo [ERROR] install.js fallo — prueba VPN off, o ejecuta como administrador
    cd ..
    pause
    exit /b 1
)
cd ..
echo.

echo [4/5] Verificar con script del proyecto...
node scripts\ensure-electron-install.cjs
if errorlevel 1 (
    echo.
    echo Si sigue fallando:
    echo   - Desactiva antivirus un momento
    echo   - npm config set proxy / https-proxy si usas proxy corporativo
    echo   - npm config set electron_mirror https://npmmirror.com/mirrors/electron/
    pause
    exit /b 1
)
echo.

echo [5/5] Compilar monitor...
call npm run build --prefix monitor-electron
echo.

if exist "monitor-electron\node_modules\electron\dist\electron.exe" (
    echo [OK] electron.exe listo
) else (
    echo [ERROR] Sigue sin existir electron.exe
    pause
    exit /b 1
)

echo.
echo Listo. Ejecuta: run-experiment-mock.bat
pause
