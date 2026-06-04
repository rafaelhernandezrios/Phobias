#!/bin/bash
# Double-click in Finder → mock (no EEG, no Electron). One Node process.

cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export PHOBIAS_MOCK=1
exec bash ./run-experiment.sh --mock
