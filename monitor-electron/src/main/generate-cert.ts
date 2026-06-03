import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs'
import { join } from 'path'
import os from 'os'
// eslint-disable-next-line @typescript-eslint/no-require-imports
const selfsigned = require('selfsigned') as {
  generate: (attrs: { name: string; value: string }[], opts: object) => { cert: string; private: string }
}

function lanIpv4s(): string[] {
  const ips: string[] = []
  try {
    for (const ifaces of Object.values(os.networkInterfaces())) {
      for (const ni of ifaces || []) {
        if (ni.family === 'IPv4' && !ni.internal) ips.push(ni.address)
      }
    }
  } catch {
    /* ignore */
  }
  return [...new Set(ips)]
}

export function ensureTlsCerts(certsDir: string): { certPath: string; keyPath: string } {
  mkdirSync(certsDir, { recursive: true })
  const certPath = join(certsDir, 'cert.pem')
  const keyPath = join(certsDir, 'key.pem')

  if (existsSync(certPath) && existsSync(keyPath)) {
    return { certPath, keyPath }
  }

  const lan = lanIpv4s()
  const altNames: object[] = [
    { type: 2, value: 'localhost' },
    { type: 7, ip: '127.0.0.1' },
    ...lan.map((ip) => ({ type: 7, ip })),
  ]

  const pems = selfsigned.generate([{ name: 'commonName', value: 'localhost' }], {
    days: 365,
    keySize: 2048,
    algorithm: 'sha256',
    extensions: [
      { name: 'basicConstraints', cA: false },
      { name: 'keyUsage', digitalSignature: true, keyEncipherment: true },
      { name: 'extKeyUsage', serverAuth: true },
      { name: 'subjectAltName', altNames },
    ],
  })

  writeFileSync(certPath, pems.cert)
  writeFileSync(keyPath, pems.private)
  console.log('[certs] Created TLS cert for:', ['localhost', '127.0.0.1', ...lan].join(', '))
  return { certPath, keyPath }
}

export function readTlsPems(certPath: string, keyPath: string): { cert: Buffer; key: Buffer } {
  return {
    cert: readFileSync(certPath),
    key: readFileSync(keyPath),
  }
}
