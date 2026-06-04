#!/usr/bin/env node
/**
 * Print HTTPS URLs for VR headsets on the same LAN.
 * Usage: node scripts/print-lan-urls.js [port]
 */
const { lanIpv4s } = require('./lan-ips.cjs');

const port = Number(process.argv[2]) || 8443;
const ips = lanIpv4s();

console.log('  Quest / participant:  https://127.0.0.1:' + port + '/disclaimer-participant.html');
console.log('  Researcher panel:     https://127.0.0.1:' + port + '/researcher.html');
if (ips.length) {
  console.log('  Same Wi‑Fi (use PC IP on Quest — not 127.0.0.1):');
  for (const ip of ips) {
    console.log('    Quest:       https://' + ip + ':' + port + '/disclaimer-participant.html');
    console.log('    Researcher:  https://' + ip + ':' + port + '/researcher.html');
  }
} else {
  console.log('  LAN: no IPv4 found — connect Wi‑Fi/Ethernet, then: npm run cert');
}
if (process.platform === 'win32') {
  console.log('  Windows: allow port ' + port + ' → scripts\\open-firewall-windows.cmd (Admin)');
}
