/**
 * Mock EEG recorder — Node.js WebSocket server (no Python, no Electron).
 * Same protocol as scripts/mock_recorder.py
 */
const { WebSocketServer, WebSocket } = require('ws');

const WS_PORT = parseInt(process.env.MOCK_WS_PORT || '8765', 10);

let wss = null;
const clients = new Set();
let recording = false;
let currentLevel = 2;
let currentPhobiaId = 'unknown';
let currentExperimentId = 'session';
let autoAdaptationEnabled = true;
let recordingT0 = 0;
let baselineCalibrationS = 0;
let currentSessionType = 'hybrid';
let currentDurationSeconds = 0;
let broadcastTimer = null;

function sessionSnapshotMessage() {
  if (!recording) return null;
  return {
    type: 'start_experiment',
    phobia_id: currentPhobiaId,
    phobia_name: currentPhobiaId,
    level: currentLevel,
    experiment_id: currentExperimentId,
    duration_seconds: currentDurationSeconds,
    session_type: currentSessionType,
    baseline_calibration_seconds: baselineCalibrationS,
  };
}

function syntheticFearIndex(t) {
  const base = 0.3 * Math.sin((2 * Math.PI * t) / 30);
  const noise = (Math.random() - 0.5) * 0.3;
  return Math.round(Math.max(-3, Math.min(3, base + noise)) * 10000) / 10000;
}

function broadcast(obj) {
  const payload = JSON.stringify(obj);
  for (const c of [...clients]) {
    if (c.readyState === WebSocket.OPEN) {
      try {
        c.send(payload);
      } catch {
        clients.delete(c);
      }
    }
  }
}

function tickAdaptive() {
  if (!recording || clients.size === 0) return;
  const t = (Date.now() - recordingT0) / 1000;
  const fi = syntheticFearIndex(t);
  const inCal = baselineCalibrationS > 0 && t < baselineCalibrationS;
  let suggestion = 'hold';
  if (!inCal) {
    const r = Math.random();
    if (r < 0.05 && currentLevel < 5) suggestion = 'up';
    else if (r > 0.95 && currentLevel > 1) suggestion = 'down';
  }
  broadcast({
    type: 'adaptive_state',
    fear_index: fi,
    fear_index_aggregate: fi,
    fear_ref_mean: 0,
    fear_ref_std: 0.3,
    fear_stress_threshold: 0.45,
    dwell_above_s: 0,
    dwell_below_s: 0,
    adaptive_phase: inCal ? 'calibration' : 'adaptation',
    baseline_remaining_s: inCal ? Math.max(0, baselineCalibrationS - t) : null,
    baseline_calibration_total_s: baselineCalibrationS > 0 ? baselineCalibrationS : null,
    level_suggestion: suggestion,
    current_level: currentLevel,
    metrics: {
      theta_fz: 5 + Math.random() * 10,
      beta_alpha_fz_cz: 0.8 + Math.random() * 1.7,
      alpha_posterior: 8 + Math.random() * 12,
      faa: (Math.random() - 0.5) * 0.6,
    },
  });
}

function handleMessage(ws, data) {
  const msgType = data.type;

  if (msgType === 'start' || msgType === 'controller_start') {
    currentPhobiaId = String(data.phobia_id || 'unknown');
    let lvl = Number(data.level ?? data.initial_level ?? 2);
    if (Number.isNaN(lvl)) lvl = 2;
    currentLevel = Math.max(0, Math.min(5, Math.floor(lvl)));
    currentExperimentId = String(data.experiment_id || data.experimentId || 'session');
    currentSessionType = String(data.session_type || data.sessionType || 'hybrid');
    const dur = Number(data.duration_seconds ?? data.durationSeconds ?? 0);
    currentDurationSeconds = Number.isNaN(dur) ? 0 : Math.max(0, dur);
    const bcal = Number(data.baseline_calibration_seconds || 0);
    baselineCalibrationS = Number.isNaN(bcal) ? 0 : Math.max(0, bcal);
    recording = true;
    recordingT0 = Date.now();
    console.log('[mock] Recording:', currentPhobiaId, 'level', currentLevel);

    broadcast({
      type: 'start_experiment',
      phobia_id: currentPhobiaId,
      phobia_name: data.phobia_name,
      level: currentLevel,
      experiment_id: currentExperimentId,
      duration_seconds: currentDurationSeconds,
      session_type: currentSessionType,
      baseline_calibration_seconds: baselineCalibrationS,
    });

    ws.send(
      JSON.stringify({
        status: 'started',
        phobia_id: currentPhobiaId,
        level: currentLevel,
        experiment_id: currentExperimentId,
      }),
    );
    return;
  }

  if (msgType === 'level_change') {
    currentLevel = Math.max(0, Math.min(5, Number(data.level ?? 2)));
    ws.send(JSON.stringify({ status: 'level_changed', level: currentLevel }));
    return;
  }

  if (msgType === 'manual_level') {
    currentLevel = Math.max(0, Math.min(5, Number(data.level ?? 2)));
    broadcast({ type: 'force_level', level: currentLevel });
    ws.send(JSON.stringify({ status: 'manual_level_sent', level: currentLevel }));
    return;
  }

  if (msgType === 'set_auto_adaptation') {
    autoAdaptationEnabled = Boolean(data.enabled ?? true);
    broadcast({ type: 'auto_adaptation_toggle', enabled: autoAdaptationEnabled });
    ws.send(JSON.stringify({ status: 'auto_adaptation_updated', enabled: autoAdaptationEnabled }));
    return;
  }

  if (msgType === 'stop_video') {
    broadcast({ type: 'stop_video' });
    ws.send(JSON.stringify({ status: 'stop_video_sent' }));
    return;
  }

  if (msgType === 'stop') {
    recording = false;
    broadcast({ type: 'stop_video' });
    ws.send(JSON.stringify({ status: 'stopped', file: '(mock — no file)' }));
    return;
  }

  ws.send(JSON.stringify({ error: 'Unknown type: ' + msgType }));
}

function startMockRecorder() {
  if (wss) return wss;

  // Plain ws on loopback — TLS only on :8443 via server-https /ws proxy.
  wss = new WebSocketServer({ port: WS_PORT, host: '127.0.0.1' });
  console.log('[mock] WebSocket ws://127.0.0.1:' + WS_PORT);

  wss.on('connection', (ws) => {
    clients.add(ws);
    console.log('[mock] Client connected (' + clients.size + ')');
    const snap = sessionSnapshotMessage();
    if (snap) {
      try {
        ws.send(JSON.stringify(snap));
        ws.send(JSON.stringify({ type: 'force_level', level: currentLevel }));
        console.log('[mock] Sent session snapshot to new client (level', currentLevel + ')');
      } catch (_) {}
    }
    ws.on('message', (raw) => {
      try {
        handleMessage(ws, JSON.parse(String(raw)));
      } catch (e) {
        ws.send(JSON.stringify({ error: String(e) }));
      }
    });
    ws.on('close', () => {
      clients.delete(ws);
      if (recording && clients.size === 0) recording = false;
    });
  });

  broadcastTimer = setInterval(tickAdaptive, 2000);
  return wss;
}

function stopMockRecorder() {
  if (broadcastTimer) clearInterval(broadcastTimer);
  broadcastTimer = null;
  if (wss) wss.close();
  wss = null;
  clients.clear();
}

module.exports = { startMockRecorder, stopMockRecorder, WS_PORT };
