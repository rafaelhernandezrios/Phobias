#!/bin/bash
# Double-click in Finder → mock stack (NO EEG hardware needed).
# Uses mock_recorder.py instead of aura_recorder.py — no pylsl/numpy/scipy required.
# Finder用: モック（EEG不要）— mock_recorder + HTTPS + Electronモニタ

cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
unset ELECTRON_RUN_AS_NODE
export ELECTRON_RUN_AS_NODE=
export PHOBIAS_MOCK=1

exec bash ./run-experiment.sh --mock
