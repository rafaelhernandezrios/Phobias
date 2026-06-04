#!/bin/bash
set -e
cd "$(dirname "$0")"

# Mock: single Node process (HTTPS + mock EEG + researcher panel). No Electron, no Python.
# Usage: ./run-experiment.sh --mock   or   PHOBIAS_MOCK=1 ./run-experiment.sh
MOCK=0
if [ "$1" = "--mock" ] || [ "${PHOBIAS_MOCK:-}" = "1" ]; then
    MOCK=1
fi

echo "========================================"
echo "  VR Phobia + EEG — launcher"
echo "========================================"
echo

if [ ! -d "node_modules" ]; then
    echo "[deps] npm install…"
    npm install
    echo
fi

if [ ! -f cert.pem ]; then
    echo "[cert] Generating TLS…"
    npm run cert
    echo
else
    echo "[OK] cert.pem exists"
fi

if [ "$MOCK" = "1" ]; then
    echo "[preflight] Mock mode…"
    npm run preflight:mock
else
    echo "[preflight] Full EEG stack…"
    npm run preflight
    echo "[python] Ensuring .venv…"
    npm run setup:python
fi
echo

if [ "$MOCK" = "1" ]; then
    echo "[start] HTTPS + mock EEG (one process)"
    echo "  VR participant:  https://<LAN-IP>:8443/"
    echo "  Researcher PC:   https://<LAN-IP>:8443/researcher.html"
else
    echo "[start] HTTPS + aura_recorder (open researcher panel in browser)"
    echo "  VR:         https://<LAN-IP>:8443/"
    echo "  Researcher: https://<LAN-IP>:8443/researcher.html"
fi
echo
node scripts/print-lan-urls.js 8443 2>/dev/null || true
echo "  Stop: Ctrl+C"
echo

if [ "$MOCK" = "1" ]; then
    npm run experiment:mock
else
    npm run experiment
fi
