#!/bin/bash
set -e
cd "$(dirname "$0")"

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

if [ ! -f cert.pem ]; then
    echo "[1/2] Generating TLS certs… / 証明書を生成中…"
    npm run cert
    echo
else
    echo "[OK] cert.pem already exists. / 証明書は既にあります。"
fi

if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
    echo "[OK] Python venv activated (.venv) / Python仮想環境を有効化"
    echo
else
    echo "[WARN] No .venv — recorder/GUI may miss packages. Create:"
    echo "       python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    echo
fi

echo "[2/2] Starting: HTTPS app + aura_recorder + adaptive monitor GUI"
echo "       起動: HTTPS + レコーダ + 適応モニタGUI"
echo
echo "  Browser / ブラウザ:  https://127.0.0.1:8443"
echo "  VR (same LAN):      https://<YOUR_IP>:8443"
echo "  Flow / 流れ:        disclosure → wait for config (researcher sets ID, level 0–5)"
echo "  Monitor / モニタ:   Tk window (EEG metrics, manual levels, adaptive mood)"
echo
echo "  Stop all / 停止:    Ctrl+C"
echo

npm run experiment
