#!/usr/bin/env node
/**
 * Pre-flight checks (Windows + macOS/Linux).
 */
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const root = path.join(__dirname, '..');
const isWin = process.platform === 'win32';
const venvPy = isWin
  ? path.join(root, '.venv', 'Scripts', 'python.exe')
  : path.join(root, '.venv', 'bin', 'python3');

let err = 0;
const ok = (m) => console.log('[OK]  ', m);
const warn = (m) => console.log('[WARN]', m);
const fail = (m) => {
  console.log('[ERROR]', m);
  err = 1;
};

console.log('=== VR Phobia — preflight ===');
console.log('Project:', root);
console.log('OS:', process.platform);
console.log();

const nv = spawnSync('node', ['-v'], { encoding: 'utf8' });
if (nv.error || nv.status !== 0) {
  fail('Node.js not found — install from https://nodejs.org');
} else {
  ok('Node ' + (nv.stdout || '').trim());
}

if (!fs.existsSync(path.join(root, 'node_modules'))) {
  warn('node_modules missing — run: npm install');
  err = 1;
} else ok('npm dependencies (root)');

if (!fs.existsSync(path.join(root, 'monitor-electron', 'node_modules'))) {
  warn('monitor-electron/node_modules missing — run: npm install');
  err = 1;
} else ok('monitor-electron dependencies');

if (!fs.existsSync(venvPy)) {
  warn('No .venv — run: npm run setup:python');
  err = 1;
} else {
  const w = spawnSync(venvPy, ['-c', 'import websockets'], { encoding: 'utf8' });
  if (w.status === 0) ok('Python venv + websockets');
  else fail('Python venv missing websockets — run: npm run setup:python');

  const p = spawnSync(venvPy, ['-c', 'import pylsl'], { encoding: 'utf8' });
  if (p.status === 0) ok('pylsl (real EEG / AURA)');
  else warn('pylsl not installed — OK for mock; required for npm run experiment');
}

if (!fs.existsSync(path.join(root, 'cert.pem')) || !fs.existsSync(path.join(root, 'key.pem'))) {
  warn('cert.pem/key.pem missing — run: npm run cert');
  err = 1;
} else ok('TLS cert.pem / key.pem');

const videoDir = path.join(root, 'app', 'assets', 'videos');
let videoCount = 0;
if (fs.existsSync(videoDir)) {
  videoCount = fs.readdirSync(videoDir).filter((f) => f.toLowerCase().endsWith('.mp4')).length;
}
if (videoCount < 1) {
  fail('No .mp4 in app/assets/videos/');
} else {
  ok(`Videos: ${videoCount} .mp4 in app/assets/videos/`);
}

if (!fs.existsSync(path.join(root, 'app', 'data', 'content.json'))) {
  fail('Missing app/data/content.json');
} else ok('content.json');

console.log();
if (err) {
  console.log('Preflight FAILED. Fix the items above.');
  process.exit(1);
}
console.log('Preflight OK — run: npm run experiment:mock');
process.exit(0);
