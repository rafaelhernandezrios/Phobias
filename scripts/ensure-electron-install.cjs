#!/usr/bin/env node
/**
 * Ensures Electron binary is downloaded (Windows often skips it on first npm install).
 * Run: node scripts/ensure-electron-install.cjs
 */
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const monitorRoot = path.join(__dirname, '..', 'monitor-electron');
const electronDir = path.join(monitorRoot, 'node_modules', 'electron');
const pathTxt = path.join(electronDir, 'path.txt');
const installJs = path.join(electronDir, 'install.js');

function electronBinaryExists() {
  if (!fs.existsSync(pathTxt)) return false;
  try {
    const name = fs.readFileSync(pathTxt, 'utf8').trim();
    const bin =
      process.platform === 'win32'
        ? path.join(electronDir, 'dist', name + '.exe')
        : path.join(electronDir, 'dist', name + '.app', 'Contents', 'MacOS', name);
    if (process.platform === 'win32') {
      return fs.existsSync(path.join(electronDir, 'dist', 'electron.exe'));
    }
    return fs.existsSync(bin);
  } catch {
    return false;
  }
}

function runInstall() {
  if (!fs.existsSync(installJs)) {
    console.error('[electron] Missing', installJs);
    console.error('         Run: cd monitor-electron && npm install');
    return false;
  }
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  console.log('[electron] Downloading binary (may take 1–2 min)…');
  const r = spawnSync(process.execPath, [installJs], {
    cwd: monitorRoot,
    stdio: 'inherit',
    env,
  });
  return r.status === 0 && electronBinaryExists();
}

if (!fs.existsSync(electronDir)) {
  console.error('[electron] monitor-electron/node_modules/electron not found.');
  console.error('         Run: npm install --prefix monitor-electron');
  process.exit(1);
}

if (electronBinaryExists()) {
  console.log('[electron] OK — binary present');
  process.exit(0);
}

if (runInstall()) {
  console.log('[electron] OK — installed');
  process.exit(0);
}

console.error('[electron] Install failed. On Windows run: scripts\\fix-electron-windows.cmd');
process.exit(1);
