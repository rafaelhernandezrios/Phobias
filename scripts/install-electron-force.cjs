#!/usr/bin/env node
/**
 * Force-download Electron binary into monitor-electron/node_modules/electron/dist
 * Use when install.js fails silently on Windows (firewall, proxy, antivirus).
 *
 * Optional: set ELECTRON_MIRROR before running, e.g.:
 *   set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
 */
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const root = path.join(__dirname, '..');
const monitorRoot = path.join(root, 'monitor-electron');
const electronDir = path.join(monitorRoot, 'node_modules', 'electron');
const distDir = path.join(electronDir, 'dist');

function log(msg) {
  console.log('[electron] ' + msg);
}

function electronReady() {
  const exe = path.join(distDir, 'electron.exe');
  const pathTxt = path.join(electronDir, 'path.txt');
  return fs.existsSync(exe) && fs.existsSync(pathTxt);
}

function tryRequire(modPath) {
  try {
    return require(modPath);
  } catch {
    return null;
  }
}

async function downloadWithElectronGet() {
  const electronPkg = path.join(electronDir, 'package.json');
  if (!fs.existsSync(electronPkg)) {
    log('ERROR: Run: cd monitor-electron && npm install electron --save-dev');
    return false;
  }
  const { version } = require(electronPkg);

  const getPath = path.join(electronDir, 'node_modules', '@electron/get');
  const extractPath = path.join(electronDir, 'node_modules', 'extract-zip');
  let getMod = tryRequire(getPath) || tryRequire(path.join(monitorRoot, 'node_modules', '@electron/get'));
  let extract = tryRequire(extractPath) || tryRequire(path.join(monitorRoot, 'node_modules', 'extract-zip'));
  const downloadArtifact = getMod && (getMod.downloadArtifact || getMod.default?.downloadArtifact);
  if (!downloadArtifact || !extract) {
    log('ERROR: Missing @electron/get or extract-zip. Run: npm install --prefix monitor-electron');
    return false;
  }

  const platform = process.platform === 'win32' ? 'win32' : process.platform;
  const arch = process.env.npm_config_arch || process.arch;

  if (process.env.ELECTRON_MIRROR) {
    log('Using ELECTRON_MIRROR=' + process.env.ELECTRON_MIRROR);
  }

  log('Downloading Electron v' + version + ' for ' + platform + '-' + arch + ' …');
  log('(1–3 minutes — wait, do not close this window)');

  try {
    const zipPath = await downloadArtifact.downloadArtifact({
      version,
      artifactName: 'electron',
      platform,
      arch,
      force: true,
    });

    log('Extracting to ' + distDir + ' …');
    if (fs.existsSync(distDir)) {
      fs.rmSync(distDir, { recursive: true, force: true });
    }
    fs.mkdirSync(distDir, { recursive: true });

    await extract(zipPath, { dir: distDir });

    const platformPath =
      platform === 'win32' ? 'electron.exe' : platform === 'darwin' ? 'Electron.app/Contents/MacOS/Electron' : 'electron';

    fs.writeFileSync(path.join(electronDir, 'path.txt'), platformPath);
    fs.writeFileSync(path.join(distDir, 'version'), version.startsWith('v') ? version : 'v' + version);

    if (platform === 'win32' && fs.existsSync(path.join(distDir, 'electron.exe'))) {
      log('OK — electron.exe installed');
      return true;
    }
    if (platform === 'darwin') {
      log('OK — Electron.app installed');
      return true;
    }
    log('WARN: Extract finished but binary not found at expected path');
    return false;
  } catch (err) {
    log('ERROR: ' + (err && err.message ? err.message : String(err)));
    if (err && err.stack) console.error(err.stack);
    return false;
  }
}

function runInstallJs() {
  const installJs = path.join(electronDir, 'install.js');
  if (!fs.existsSync(installJs)) return false;
  const env = { ...process.env, force_no_cache: 'true' };
  delete env.ELECTRON_RUN_AS_NODE;
  delete env.ELECTRON_SKIP_BINARY_DOWNLOAD;
  log('Trying electron/install.js …');
  const r = spawnSync(process.execPath, [installJs], {
    cwd: electronDir,
    stdio: 'inherit',
    env,
    timeout: 600000,
  });
  if (r.status !== 0) {
    log('install.js exited with code ' + (r.status ?? 'null'));
    if (r.error) log(String(r.error));
  }
  return r.status === 0 && electronReady();
}

async function main() {
  if (!fs.existsSync(electronDir)) {
    log('ERROR: ' + electronDir + ' missing. npm install --prefix monitor-electron');
    process.exit(1);
  }

  if (electronReady()) {
    log('Already installed: ' + path.join(distDir, 'electron.exe'));
    process.exit(0);
  }

  if (runInstallJs()) {
    process.exit(0);
  }

  const ok = await downloadWithElectronGet();
  if (ok) process.exit(0);

  log('');
  log('Failed. Try in CMD:');
  log('  set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/');
  log('  node scripts\\install-electron-force.cjs');
  log('Or: INSTALAR-ELECTRON-WINDOWS.cmd (in project root)');
  log('Or disable antivirus briefly and retry.');
  log('Your fix-electron script is OLD if it shows [1/5] — run git pull.');
  process.exit(1);
}

main();
