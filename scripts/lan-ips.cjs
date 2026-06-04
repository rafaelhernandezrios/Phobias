#!/usr/bin/env node
/** Collect non-internal IPv4 addresses for LAN URLs and TLS SAN. */
const os = require('os');
const { execSync } = require('child_process');

function lanIpv4sFromShell() {
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
  } else if (process.platform === 'linux') {
    try {
      const out = execSync('hostname -I 2>/dev/null || true', { encoding: 'utf8' });
      out.trim().split(/\s+/).filter(Boolean).forEach((ip) => ips.push(ip));
    } catch {
      /* ignore */
    }
  } else if (process.platform === 'win32') {
    try {
      const out = execSync('ipconfig', { encoding: 'utf8', windowsHide: true });
      const re = /IPv4[^:\r\n]*:\s*(\d+\.\d+\.\d+\.\d+)/gi;
      let m;
      while ((m = re.exec(out))) {
        const ip = m[1];
        if (ip.startsWith('127.')) continue;
        ips.push(ip);
      }
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
        const fam = ni.family;
        if ((fam === 'IPv4' || fam === 4) && !ni.internal) ips.push(ni.address);
      }
    }
    if (ips.length) return [...new Set(ips)];
  } catch {
    /* ignore */
  }
  return lanIpv4sFromShell();
}

module.exports = { lanIpv4s };
