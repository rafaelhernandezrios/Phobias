#!/usr/bin/env node
/**
 * Ensures Electron binary is present. Delegates to install-electron-force.cjs if needed.
 */
const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const root = path.join(__dirname, '..');
const exe = path.join(root, 'monitor-electron', 'node_modules', 'electron', 'dist', 'electron.exe');
const exeMac = path.join(
  root,
  'monitor-electron',
  'node_modules',
  'electron',
  'dist',
  'Electron.app',
  'Contents',
  'MacOS',
  'Electron',
);

function ready() {
  if (process.platform === 'win32') return fs.existsSync(exe);
  return fs.existsSync(exeMac);
}

if (ready()) {
  console.log('[electron] OK — binary present');
  process.exit(0);
}

const force = path.join(__dirname, 'install-electron-force.cjs');
const r = spawnSync(process.execPath, [force], { cwd: root, stdio: 'inherit' });
process.exit(r.status === 0 && ready() ? 0 : 1);
