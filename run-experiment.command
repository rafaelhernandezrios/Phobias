#!/bin/bash
# Double-click in Finder (macOS) → full EEG stack (HTTPS + aura_recorder).
# Researcher: open https://<IP>:8443/researcher.html in the PC browser.
# Mock (no EEG): run-experiment-mock.command

cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
exec bash ./run-experiment.sh
