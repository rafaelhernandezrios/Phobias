#!/usr/bin/env bash
# Use project .venv when present (npm/concurrently do not inherit shell activate).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -x "$ROOT/.venv/bin/python3" ]; then
  exec "$ROOT/.venv/bin/python3" "$@"
fi
exec python3 "$@"
