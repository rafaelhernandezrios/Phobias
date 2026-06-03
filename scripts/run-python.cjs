#!/usr/bin/env node
/**
 * Run Python using project .venv (cross-platform: Windows + macOS/Linux).
 * Usage: node scripts/run-python.cjs scripts/mock_recorder.py --wss
 */
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const venvPy =
  process.platform === 'win32'
    ? path.join(root, '.venv', 'Scripts', 'python.exe')
    : path.join(root, '.venv', 'bin', 'python3');

const py = fs.existsSync(venvPy) ? venvPy : process.platform === 'win32' ? 'python' : 'python3';
const args = process.argv.slice(2);

if (!args.length) {
  console.error('Usage: node scripts/run-python.cjs <script.py> [args...]');
  process.exit(2);
}

const result = spawnSync(py, args, {
  cwd: root,
  stdio: 'inherit',
  env: process.env,
  shell: process.platform === 'win32',
});

process.exit(result.status === null ? 1 : result.status);
