#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -x ".venv/bin/python3" ]; then
  echo "[python] Creating .venv… / 仮想環境を作成中…"
  python3 -m venv .venv
fi

if ! .venv/bin/python3 -c "import pylsl, websockets, numpy, scipy" 2>/dev/null; then
  echo "[python] Installing requirements.txt… / 依存をインストール中…"
  .venv/bin/pip install -q -r requirements.txt
fi

echo "[OK] Python ready: .venv/bin/python3"
