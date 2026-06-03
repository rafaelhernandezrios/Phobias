/**
 * Servidor local HTTPS con certificado autofirmado + proxy WebSocket.
 *
 * Sirve:
 *   - HTTPS estático desde ./app en el puerto 8443
 *   - Proxy WSS de /ws hacia wss://127.0.0.1:8765 (el recorder Python)
 *
 * Así el navegador (incluido Oculus/iOS) solo necesita aceptar el cert
 * en un único puerto (8443) — el WebSocket viaja por el mismo origen.
 *
 * Primera vez: ejecuta "npm run cert" para crear cert.pem y key.pem.
 * Uso: node server-https.js   (lanzado por "npm run serve:https")
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');

const os = require('os');
const PORT = 8443;
const PORT_HTTP = 8080;
const RECORDER_URL = 'wss://127.0.0.1:8765';
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

// /ws → proxy to the Python recorder. One TLS hop for the browser; the
// upstream link to 127.0.0.1:8765 is loopback so cert validation is skipped.
const wss = new WebSocket.Server({ noServer: true });

httpsServer.on('upgrade', (req, socket, head) => {
  const urlPath = (req.url || '').split('?')[0];
  if (urlPath !== '/ws') {
    socket.destroy();
    return;
  }
  wss.handleUpgrade(req, socket, head, (clientWs) => {
    const upstream = new WebSocket(RECORDER_URL, { rejectUnauthorized: false });
    const queue = [];
    let upstreamOpen = false;

    clientWs.on('message', (data) => {
      if (upstreamOpen) upstream.send(data);
      else queue.push(data);
    });
    upstream.on('open', () => {
      upstreamOpen = true;
      while (queue.length) upstream.send(queue.shift());
    });
    upstream.on('message', (data) => {
      if (clientWs.readyState === WebSocket.OPEN) clientWs.send(data);
    });

    const closeBoth = () => {
      try { clientWs.close(); } catch (e) {}
      try { upstream.close(); } catch (e) {}
    };
    clientWs.on('close', closeBoth);
    upstream.on('close', closeBoth);
    clientWs.on('error', closeBoth);
    upstream.on('error', (err) => {
      console.error('[ws-proxy] upstream error:', err.message);
      closeBoth();
    });
  });
});

httpsServer.listen(PORT, '0.0.0.0', () => {
  const lan = lanIpv4s();
  console.log('');
  console.log('  HTTPS (this Mac):     https://127.0.0.1:' + PORT);
  console.log('                        https://localhost:' + PORT);
  if (lan.length) {
    console.log('  HTTPS (VR / Quest — same Wi‑Fi):');
    lan.forEach((ip) => console.log('    https://' + ip + ':' + PORT));
  } else {
    console.log('  HTTPS (VR / Quest):   (no LAN IPv4 — connect Wi‑Fi or Ethernet)');
  }
  console.log('  WebSocket (via proxy): wss://<host>:' + PORT + '/ws  →  ' + RECORDER_URL);
  console.log('  Tip: open the LAN URL on the headset; accept the self-signed cert once.');
  if (lan.length) {
    console.log('  If TLS fails on Quest, regenerate cert: npm run cert');
  }
  console.log('');
});

http.createServer((req, res) => {
  res.writeHead(301, { Location: `https://localhost:${PORT}${req.url}` });
  res.end();
}).listen(PORT_HTTP, () => {
  console.log('  HTTP → HTTPS: http://localhost:' + PORT_HTTP);
  console.log('');
});
