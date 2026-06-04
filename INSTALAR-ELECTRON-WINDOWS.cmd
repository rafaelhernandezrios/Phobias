@echo off
chcp 65001 >nul
title Instalar Electron (manual, sin git pull)
cd /d "%~dp0"
set "ELECTRON_RUN_AS_NODE="
set ELECTRON_SKIP_BINARY_DOWNLOAD=
set "force_no_cache=true"

echo Si ves [1/5] en otro .bat, ese archivo esta VIEJO. Usa ESTE script o git pull.
echo.

where node >nul 2>&1 || (echo Instala Node.js LTS & pause & exit /b 1)

if not exist "scripts\install-electron-force.cjs" (
    echo [ERROR] Falta scripts\install-electron-force.cjs
    echo        En Mac: git push. En Windows: git pull
    echo        O copia la carpeta scripts desde el Mac.
    pause
    exit /b 1
)

if exist "monitor-electron\node_modules\electron" rmdir /s /q "monitor-electron\node_modules\electron"

cd monitor-electron
call npm install electron@33.4.11 --save-dev --no-fund --no-audit
cd ..

echo.
echo Intento 1 — descarga directa...
node scripts\install-electron-force.cjs
if errorlevel 1 (
    echo.
    echo Intento 2 — mirror China / red lenta...
    set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
    node scripts\install-electron-force.cjs
)

if exist "monitor-electron\node_modules\electron\dist\electron.exe" (
    echo.
    echo [OK] electron.exe instalado
    call npm run build --prefix monitor-electron
    echo Ejecuta: run-experiment-mock.bat
) else (
    echo.
    echo [ERROR] No se pudo descargar. Prueba:
    echo   - Desactivar antivirus 1 minuto
    echo   - Otra red / hotspot del movil
    echo   - git pull y FIX-ELECTRON-NOW.bat
)
pause
