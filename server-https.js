/**
 * Servidor local HTTPS con certificado autofirmado + proxy WebSocket.
 *
 * Sirve:
 *   - HTTPS estático desde ./app en el puerto 8443
 *   - Proxy WSS de /ws hacia el recorder en 127.0.0.1:8765 (ws:// en mock, wss:// con Python --wss)
 *
 * Así el navegador (incluido Oculus/iOS) solo necesita aceptar el cert
 * en un único puerto (8443) — el WebSocket viaja por el mismo origen.
 *
 * Primera vez: ejecuta "npm run cert" para crear cert.pem y key.pem.
 * Uso:
 *   node server-https.js           — HTTPS + proxy /ws → recorder externo (Python)
 *   node server-https.js --mock    — HTTPS + mock EEG en Node (sin Python ni Electron)
 */

const https = require('https');
const USE_MOCK = process.argv.includes('--mock');
const http = require('http');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');

const os = require('os');
const PORT = 8443;
const PORT_HTTP = 8080;
const RECORDER_HOST = process.env.RECORDER_HOST || '127.0.0.1';
const RECORDER_PORT = process.env.RECORDER_PORT || '8765';
// Browser uses wss://host:8443/ws (TLS). Loopback recorder is usually plain ws:// (mock / default).
const RECORDER_UPSTREAM_URLS = process.env.RECORDER_WS_URL
  ? [process.env.RECORDER_WS_URL]
  : USE_MOCK
    ? [`ws://${RECORDER_HOST}:${RECORDER_PORT}`]
    : [
        `wss://${RECORDER_HOST}:${RECORDER_PORT}`,
        `ws://${RECORDER_HOST}:${RECORDER_PORT}`,
      ];
const ROOT = path.join(__dirname, 'app');

function lanIpv4sFromShell() {
  const { execSync } = require('child_process');
  const ips = [];
  if (process.platform === 'darwin') {
    for (const iface of ['en0', 'en1', 'en5', 'bridge0']) {
      try {
        const ip = execSync(`ipconfig getifaddr ${iface}`, { encoding: 'utf8' }).trim();
        if (ip) ips.push(ip);
      } catch {
        /* absent */
      }
    }
  }
  return [...new Set(ips)];
}

function lanIpv4s() {
  try {
    const ips = [];
    for (const ifaces of Object.values(os.networkInterfaces())) {
      for (const ni of ifaces || []) {
        if (ni.family === 'IPv4' && !ni.internal) ips.push(ni.address);
      }
    }
    if (ips.length) return [...new Set(ips)];
  } catch {
    /* ignore */
  }
  return lanIpv4sFromShell();
}

function getMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const mimes = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.css': 'text/css',
    '.ico': 'image/x-icon',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
  };
  return mimes[ext] || 'application/octet-stream';
}

function serveFile(res, urlPath) {
  const cleanPath = urlPath.replace(/\?.*$/, '') || '/';
  const fullPath = path.join(ROOT, cleanPath === '/' ? 'index.html' : cleanPath);

  if (!fs.existsSync(fullPath)) {
    const asDir = path.join(ROOT, cleanPath, 'index.html');
    if (fs.existsSync(asDir)) {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(fs.readFileSync(asDir));
      return;
    }
    res.writeHead(404);
    res.end('Not found');
    return;
  }

  if (fs.statSync(fullPath).isDirectory()) {
    const index = path.join(fullPath, 'index.html');
    if (fs.existsSync(index)) {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(fs.readFileSync(index));
      return;
    }
    res.writeHead(404);
    res.end('Not found');
    return;
  }

  res.writeHead(200, { 'Content-Type': getMimeType(fullPath) });
  res.end(fs.readFileSync(fullPath));
}

function requestHandler(req, res) {
  serveFile(res, req.url === '/' ? '/index.html' : req.url);
}

const keyPath = path.join(__dirname, 'key.pem');
const certPath = path.join(__dirname, 'cert.pem');

if (!fs.existsSync(keyPath) || !fs.existsSync(certPath)) {
  console.error('\n  Falta el certificado. Ejecuta primero:\n    npm run cert\n');
  process.exit(1);
}

const options = {
  key: fs.readFileSync(keyPath),
  cert: fs.readFileSync(certPath),
};

const httpsServer = https.createServer(options, requestHandler);

// /ws → proxy to recorder on loopback (ws:// or wss:// depending on mock / Python --wss).
const wss = new WebSocket.Server({ noServer: true });

function proxyToRecorder(clientWs) {
  const queue = [];
  let upstream = null;
  let upstreamOpen = false;
  let urlIndex = 0;

  const closeBoth = () => {
    try {
      clientWs.close();
    } catch (_) {}
    try {
      if (upstream) upstream.close();
    } catch (_) {}
  };

  clientWs.on('message', (data) => {
    if (upstreamOpen && upstream && upstream.readyState === WebSocket.OPEN) upstream.send(data);
    else queue.push(data);
  });
  clientWs.on('close', closeBoth);
  clientWs.on('error', closeBoth);

  function connectNext() {
    if (urlIndex >= RECORDER_UPSTREAM_URLS.length) {
      console.error('[ws-proxy] recorder not reachable on', RECORDER_UPSTREAM_URLS.join(', '));
      closeBoth();
      return;
    }
    const url = RECORDER_UPSTREAM_URLS[urlIndex];
    upstream = new WebSocket(url, { rejectUnauthorized: false });

    upstream.on('open', () => {
      upstreamOpen = true;
      console.log('[ws-proxy] connected →', url);
      while (queue.length) upstream.send(queue.shift());
    });
    upstream.on('message', (data) => {
      if (clientWs.readyState === WebSocket.OPEN) clientWs.send(data);
    });
    upstream.on('close', () => {
      if (upstreamOpen) closeBoth();
    });
    upstream.on('error', (err) => {
      if (!upstreamOpen) {
        console.warn('[ws-proxy]', url, '—', err.message);
        urlIndex += 1;
        connectNext();
      } else {
        console.error('[ws-proxy] upstream error:', err.message);
        closeBoth();
      }
    });
  }

  connectNext();
}

httpsServer.on('upgrade', (req, socket, head) => {
  const urlPath = (req.url || '').split('?')[0];
  if (urlPath !== '/ws') {
    socket.destroy();
    return;
  }
  wss.handleUpgrade(req, socket, head, proxyToRecorder);
});

function printUrls() {
  const lan = lanIpv4s();
  const mode = USE_MOCK
    ? 'MOCK (Node EEG, no AURA)'
    : 'recorder @ ' + RECORDER_UPSTREAM_URLS.join(' | ');
  console.log('');
  console.log('  Mode: ' + mode);
  console.log('');
  console.log('  Participant / VR (Quest):');
  console.log('    https://127.0.0.1:' + PORT + '/');
  console.log('    https://localhost:' + PORT + '/');
  if (lan.length) {
    lan.forEach((ip) => console.log('    https://' + ip + ':' + PORT + '/'));
  } else {
    console.log('    (no LAN IPv4 — connect Wi‑Fi for Quest URL)');
  }
  console.log('');
  console.log('  Researcher panel / Panel investigador (PC browser):');
  console.log('    https://127.0.0.1:' + PORT + '/researcher.html');
  console.log('    https://localhost:' + PORT + '/researcher.html');
  if (lan.length) {
    lan.forEach((ip) =>
      console.log('    https://' + ip + ':' + PORT + '/researcher.html'),
    );
  }
  console.log('');
  console.log('  WebSocket: wss://<host>:' + PORT + '/ws  →  ' + RECORDER_UPSTREAM_URLS.join(' | '));
  console.log('  Flow: disclosure → wait → Start from researcher panel');
  console.log('  Tip: accept self-signed cert on Quest and PC (npm run cert if needed).');
  console.log('');
}

if (USE_MOCK) {
  const { startMockRecorder, stopMockRecorder } = require('./scripts/mock-recorder-node.js');
  startMockRecorder();
  const shutdown = () => {
    stopMockRecorder();
    process.exit(0);
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

httpsServer.listen(PORT, '0.0.0.0', () => {
  printUrls();
});

http.createServer((req, res) => {
  res.writeHead(301, { Location: `https://localhost:${PORT}${req.url}` });
  res.end();
}).listen(PORT_HTTP, () => {
  console.log('  HTTP → HTTPS: http://localhost:' + PORT_HTTP);
  console.log('');
});
