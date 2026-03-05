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

const attrs = [{ name: 'commonName', value: 'localhost' }];
const opts = { days: 365, keySize: 2048, algorithm: 'sha256' };
const pems = selfsigned.generate(attrs, opts);

const dir = __dirname;
fs.writeFileSync(path.join(dir, 'cert.pem'), pems.cert);
fs.writeFileSync(path.join(dir, 'key.pem'), pems.private);

console.log('Certificado creado: cert.pem, key.pem');
console.log('Ahora puedes usar: npx http-server -p 8443 -S');
console.log('O: npm run serve');
