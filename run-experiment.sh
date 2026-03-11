#!/bin/bash
cd "$(dirname "$0")"

echo "========================================"
echo "  VR Phobia + EEG Experiment Launcher"
echo "========================================"
echo

if [ ! -f cert.pem ]; then
    echo "[1/2] Generando certificados..."
    npm run cert
    echo
else
    echo "[OK] Certificados ya existen."
fi

echo "[2/2] Iniciando servidor HTTPS + recorder EEG + monitor..."
echo
echo "Abre en el navegador: https://127.0.0.1:8443"
echo "Para VR: https://TU_IP:8443"
echo "Se abrirá la ventana del monitor (estado EEG + Level 1/2/3)."
echo
echo "Presiona Ctrl+C para detener todo."
echo

npm run experiment
