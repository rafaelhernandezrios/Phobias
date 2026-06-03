/**
 * Genera cert.pem y key.pem con Node (no requiere OpenSSL).
 * Uso: node generate-cert.js   o   npm run cert
 */
const fs = require('fs');
const path = require('path');

let selfsigned;
try {
  selfsigned = require('selfsigned');
} catch (e) {
  console.log('Instalando "selfsigned"...');
  require('child_process').execSync('npm install selfsigned --save-dev', {
    stdio: 'inherit',
    cwd: path.join(__dirname),
  });
  selfsigned = require('selfsigned');
}

// Collect all local IPv4 addresses so the cert is valid from LAN devices (VR headset, phones).
const os = require('os');
const lanIps = [];
const ifaces = os.networkInterfaces();
for (const name of Object.keys(ifaces)) {
  for (const ni of ifaces[name] || []) {
    if (ni.family === 'IPv4' && !ni.internal) lanIps.push(ni.address);
  }
}

const altNames = [
  { type: 2, value: 'localhost' },          // DNS
  { type: 7, ip: '127.0.0.1' },             // IP
  ...lanIps.map((ip) => ({ type: 7, ip })), // LAN IPs
];

console.log('SAN entries:', ['localhost', '127.0.0.1', ...lanIps].join(', '));

const attrs = [{ name: 'commonName', value: 'localhost' }];
const opts = {
  days: 365,
  keySize: 2048,
  algorithm: 'sha256',
  extensions: [
    { name: 'basicConstraints', cA: false },
    {
      name: 'keyUsage',
      digitalSignature: true,
      keyEncipherment: true,
    },
    {
      name: 'extKeyUsage',
      serverAuth: true,
    },
    { name: 'subjectAltName', altNames },
  ],
};
const pems = selfsigned.generate(attrs, opts);

const dir = __dirname;
fs.writeFileSync(path.join(dir, 'cert.pem'), pems.cert);
fs.writeFileSync(path.join(dir, 'key.pem'), pems.private);

console.log('Certificado creado: cert.pem, key.pem');
console.log('Ahora puedes usar: npx http-server -p 8443 -S');
console.log('O: npm run serve');
