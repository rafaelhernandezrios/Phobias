#!/usr/bin/env node
/**
 * Create .venv and install requirements.txt (Windows + macOS/Linux).
 */
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const isWin = process.platform === 'win32';
const venvPy = isWin
  ? path.join(root, '.venv', 'Scripts', 'python.exe')
  : path.join(root, '.venv', 'bin', 'python3');
const venvPip = isWin
  ? path.join(root, '.venv', 'Scripts', 'pip.exe')
  : path.join(root, '.venv', 'bin', 'pip');

function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { cwd: root, stdio: 'inherit', ...opts });
  if (r.status !== 0) process.exit(r.status === null ? 1 : r.status);
}

if (!fs.existsSync(venvPy)) {
  console.log('[python] Creating .venv…');
  const launcher = isWin ? 'py' : 'python3';
  const venvArgs = isWin ? ['-3', '-m', 'venv', '.venv'] : ['-m', 'venv', '.venv'];
  run(launcher, venvArgs, { shell: isWin });
}

console.log('[python] Installing requirements.txt…');
run(venvPip, ['install', '-q', '-r', 'requirements.txt']);

console.log('[OK] Python ready:', venvPy);
