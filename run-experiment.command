#!/bin/bash
# Double-click in Finder (macOS) to run the same stack as: npm run experiment
cd "$(dirname "$0")"
exec bash ./run-experiment.sh
