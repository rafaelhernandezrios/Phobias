#!/bin/bash
set -e
cd "$(dirname "$0")"

# Mock mode: no EEG hardware needed (mock_recorder.py replaces aura_recorder.py).
# Uso: ./run-experiment.sh --mock   or   PHOBIAS_MOCK=1 ./run-experiment.sh
MOCK=0
if [ "$1" = "--mock" ] || [ "${PHOBIAS_MOCK:-}" = "1" ]; then
    MOCK=1
fi

# Cursor/some shells set this and break Electron (Tk monitor would be the fallback).
unset ELECTRON_RUN_AS_NODE

if node -e "const s=require('./package.json').scripts.experiment||''; if(s.includes('adaptive_monitor_gui')) process.exit(1)" 2>/dev/null; then
    :
else
    echo "[ERROR] package.json still launches the legacy Tk monitor."
    echo "        Update the repo (git pull) or set scripts.experiment to use: npm run monitor"
    echo "        古いTkモニタ設定です。git pull するか experiment スクリプトを更新してください。"
    exit 1
fi

echo "========================================"
echo "  VR Phobia + EEG — full stack launcher"
echo "  VR恐怖症＋EEG 一括起動"
echo "========================================"
echo

if [ ! -d "node_modules" ]; then
    echo "[deps] Installing npm dependencies… / npm依存をインストール中…"
    npm install
    echo
fi

if [ ! -d "monitor-electron/node_modules" ]; then
    echo "[deps] Installing monitor-electron (Electron UI)… / Electronモニタをインストール中…"
    npm install --prefix monitor-electron
    echo
fi

if [ ! -f cert.pem ]; then
    echo "[1/2] Generating TLS certs… / 証明書を生成中…"
    npm run cert
    echo
else
    echo "[OK] cert.pem already exists. / 証明書は既にあります。"
fi

echo "[preflight] Checking Node, Python, certs, videos…"
if ! npm run preflight; then
    exit 1
fi
echo "[python] Ensuring .venv… / Python仮想環境を確認中…"
npm run setup:python
echo

if [ "$MOCK" = "1" ]; then
    echo "[2/2] Starting MOCK stack (no EEG — mock_recorder + HTTPS + monitor)"
    echo "       モック起動: EEG不要 — mock_recorder + HTTPS + モニタ"
else
    echo "[2/2] Starting: HTTPS app + aura_recorder + Electron adaptive monitor"
    echo "       起動: HTTPS + レコーダ + Electron適応モニタ"
fi
echo
echo "  URLs (HTTPS + WebSocket proxy on :8443):"
node scripts/print-lan-urls.js 8443 2>/dev/null || echo "    https://127.0.0.1:8443"
echo "  Flow / 流れ:        disclosure → wait for config (researcher sets ID, level 0–5)"
echo "  Monitor / モニタ:   Electron window (EEG metrics, manual levels, adaptive mood)"
echo
echo "  Stop all / 停止:    Ctrl+C"
echo

export ELECTRON_RUN_AS_NODE=
if [ "$MOCK" = "1" ]; then
    npm run experiment:mock
else
    npm run experiment
fi
