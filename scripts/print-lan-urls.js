#!/usr/bin/env node
/**
 * Print HTTPS / WSS URLs for VR headsets on the same LAN.
 * Usage: node scripts/print-lan-urls.js [port]
 */
const os = require('os');

const port = Number(process.argv[2]) || 8443;

function lanIpv4sFromShell() {
  const { execSync } = require('child_process');
  const ips = [];
  if (process.platform === 'darwin') {
    for (const iface of ['en0', 'en1', 'en5', 'bridge0']) {
      try {
        const ip = execSync(`ipconfig getifaddr ${iface}`, { encoding: 'utf8' }).trim();
        if (ip) ips.push(ip);
      } catch {
        /* interface absent */
      }
    }
  } else if (process.platform === 'linux') {
    try {
      const out = execSync("hostname -I 2>/dev/null || true", { encoding: 'utf8' });
      out.trim().split(/\s+/).filter(Boolean).forEach((ip) => ips.push(ip));
    } catch {
      /* ignore */
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
    /* sandbox or restricted environment */
  }
  return lanIpv4sFromShell();
}

const ips = lanIpv4s();
console.log('  VR / participant:  https://127.0.0.1:' + port + '/');
console.log('  Researcher panel:  https://127.0.0.1:' + port + '/researcher.html');
if (ips.length) {
  console.log('  Same Wi‑Fi (Quest + PC):');
  for (const ip of ips) {
    console.log('    VR:          https://' + ip + ':' + port + '/');
    console.log('    Researcher:  https://' + ip + ':' + port + '/researcher.html');
  }
} else {
  console.log('  LAN: (no IPv4 — connect Wi‑Fi for Quest URLs)');
}
