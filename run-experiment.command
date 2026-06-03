#!/bin/bash
# Double-click in Finder (macOS) → same stack as ./run-experiment.sh:
# HTTPS app + aura_recorder + Electron adaptive monitor (not Tk).
# Requires AURA (or LSL EEG) streaming. For mock without hardware, use:
#   run-experiment-mock.command  or  ./run-experiment.sh --mock
# Finder用: run-experiment.sh と同じ。AURA必須。モックは run-experiment-mock.command

cd "$(dirname "$0")"

# Finder often has a minimal PATH; Homebrew Node is common on Mac.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
unset ELECTRON_RUN_AS_NODE
export ELECTRON_RUN_AS_NODE=

exec bash ./run-experiment.sh
