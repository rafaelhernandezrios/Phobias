@echo off
chcp 65001 >nul
echo Opening Windows Firewall for VR Phobia HTTPS (port 8443)...
netsh advfirewall firewall delete rule name="VR Phobia HTTPS 8443" >nul 2>&1
netsh advfirewall firewall add rule name="VR Phobia HTTPS 8443" dir=in action=allow protocol=TCP localport=8443 profile=private
if errorlevel 1 (
    echo [ERROR] Run this .cmd as Administrator ^(right-click → Run as administrator^)
    pause
    exit /b 1
)
echo [OK] Rule added for TCP 8443 on private networks.
echo Now run on this PC: npm run cert
echo Then: npm run experiment:mock
pause
