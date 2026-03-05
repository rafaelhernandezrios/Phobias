/**
 * Servidor local HTTPS con certificado autofirmado.
 * Primera vez: ejecuta "npm run cert" para crear cert.pem y key.pem
 * Uso: npm run serve   (o: node server-https.js)
 * Abre: https://localhost:8443
 *
 * El navegador mostrará una advertencia (normal en desarrollo).
 * Chrome: "Avanzado" → "Continuar a localhost (no seguro)"
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8443;
const PORT_HTTP = 8080;
const ROOT = __dirname;

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

const keyPath = path.join(ROOT, 'key.pem');
const certPath = path.join(ROOT, 'cert.pem');

if (!fs.existsSync(keyPath) || !fs.existsSync(certPath)) {
  console.error('');
  console.error('  Falta el certificado. Ejecuta primero:');
  console.error('    npm run cert');
  console.error('');
  console.error('  O usa directamente:');
  console.error('    npx http-server -p 8443 -S');
  console.error('');
  process.exit(1);
}

const options = {
  key: fs.readFileSync(keyPath),
  cert: fs.readFileSync(certPath),
};

https.createServer(options, requestHandler).listen(PORT, () => {
  console.log('');
  console.log('  HTTPS: https://localhost:' + PORT);
  console.log('  (Acepta la advertencia de certificado en el navegador)');
  console.log('');
});

http.createServer((req, res) => {
  res.writeHead(301, { Location: `https://localhost:${PORT}${req.url}` });
  res.end();
}).listen(PORT_HTTP, () => {
  console.log('  HTTP → HTTPS: http://localhost:' + PORT_HTTP);
  console.log('');
});
