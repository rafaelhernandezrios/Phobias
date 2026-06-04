#!/usr/bin/env node
/**
 * Quick check: HTTPS + WS proxy + mock recorder deliver start_experiment.
 * Run while npm run experiment:mock is active.
 */
const WebSocket = require('ws');

const url = process.env.WS_URL || 'wss://127.0.0.1:8443/ws';
let ok = false;

const ws = new WebSocket(url, { rejectUnauthorized: false });
ws.on('open', () => {
  console.log('[test] connected', url);
  ws.send(
    JSON.stringify({
      type: 'controller_start',
      phobia_id: 'arachnophobia',
      level: 1,
      experiment_id: 'test',
    }),
  );
});
ws.on('message', (raw) => {
  const d = JSON.parse(String(raw));
  if (d.type === 'recorder_ready') console.log('[test] recorder_ready OK');
  if (d.type === 'start_experiment') {
    ok = true;
    console.log('[test] start_experiment OK', d.phobia_id, 'level', d.level);
    process.exit(0);
  }
});
ws.on('error', (e) => {
  console.error('[test] error:', e.message);
  process.exit(1);
});
setTimeout(() => {
  console.error('[test] FAIL — no start_experiment in 5s. Is npm run experiment:mock running?');
  process.exit(1);
}, 5000);
