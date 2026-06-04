(function () {
  var ws = null;
  var phobias = [];
  var autoAdapt = true;

  var el = {
    wsStatus: document.getElementById('ws-status'),
    vrUrl: document.getElementById('vr-url'),
    panelUrl: document.getElementById('panel-url'),
    phobiaSelect: document.getElementById('phobia-select'),
    startLevel: document.getElementById('start-level'),
    sessionType: document.getElementById('session-type'),
    experimentId: document.getElementById('experiment-id'),
    durationSec: document.getElementById('duration-sec'),
    baselineSec: document.getElementById('baseline-sec'),
    sendError: document.getElementById('send-error'),
    btnStart: document.getElementById('btn-start'),
    fearIndex: document.getElementById('fear-index'),
    moodLabel: document.getElementById('mood-label'),
    levelSuggestion: document.getElementById('level-suggestion'),
    currentLevel: document.getElementById('current-level'),
    mTheta: document.getElementById('m-theta'),
    mBeta: document.getElementById('m-beta'),
    mAlpha: document.getElementById('m-alpha'),
    mFaa: document.getElementById('m-faa'),
  };

  function baseUrl() {
    return window.location.origin;
  }

  function wsUrl() {
    var p = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return p + '//' + window.location.host + '/ws';
  }

  function setWsStatus(klass, text) {
    if (!el.wsStatus) return;
    el.wsStatus.className = 'ws-pill ' + klass;
    el.wsStatus.textContent = text;
  }

  function send(msg) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      if (el.sendError) el.sendError.textContent = 'WebSocket not connected';
      return;
    }
    if (el.sendError) el.sendError.textContent = '';
    ws.send(JSON.stringify(msg));
  }

  function fmt(v) {
    if (v == null || !Number.isFinite(Number(v))) return '—';
    return Number(v).toFixed(3);
  }

  function moodFromFear(fi, thr) {
    if (fi == null || !Number.isFinite(fi)) return '—';
    if (thr != null && Number.isFinite(thr)) {
      return fi >= thr ? 'STRESSED' : 'CALM';
    }
    if (fi <= -0.3) return 'CALM';
    if (fi >= 0.8) return 'STRESSED';
    return 'MEDIUM';
  }

  function onWsMessage(data) {
    if (data.type === 'adaptive_state') {
      if (el.fearIndex && data.fear_index != null) el.fearIndex.textContent = fmt(data.fear_index);
      if (el.moodLabel) el.moodLabel.textContent = moodFromFear(data.fear_index, data.fear_stress_threshold);
      if (el.levelSuggestion) el.levelSuggestion.textContent = data.level_suggestion || '—';
      if (el.currentLevel) el.currentLevel.textContent = String(data.current_level ?? '—');
      var m = data.metrics || {};
      if (el.mTheta) el.mTheta.textContent = fmt(m.theta_fz);
      if (el.mBeta) el.mBeta.textContent = fmt(m.beta_alpha_fz_cz);
      if (el.mAlpha) el.mAlpha.textContent = fmt(m.alpha_posterior);
      if (el.mFaa) el.mFaa.textContent = fmt(m.faa);
    } else if (data.type === 'force_level') {
      if (el.currentLevel) el.currentLevel.textContent = String(data.level);
    }
  }

  function connectWs() {
    setWsStatus('connecting', 'WebSocket: Connecting…');
    try {
      ws = new WebSocket(wsUrl());
      ws.onopen = function () {
        setWsStatus('connected', 'WebSocket: Connected');
      };
      ws.onmessage = function (ev) {
        try {
          onWsMessage(JSON.parse(ev.data));
        } catch (e) {}
      };
      ws.onclose = function () {
        setWsStatus('disconnected', 'WebSocket: Disconnected');
      };
      ws.onerror = function () {
        setWsStatus('disconnected', 'WebSocket: Error');
      };
    } catch (e) {
      setWsStatus('disconnected', 'WebSocket: ' + e.message);
    }
  }

  function loadPhobias() {
    var url = typeof assetUrl === 'function' ? assetUrl('data/content.json') : 'data/content.json';
    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        phobias = (data.phobias || []).map(function (p) {
          return { id: p.id, name: p.name || p.id };
        });
        if (!phobias.length) phobias = [{ id: 'arachnophobia', name: 'Arachnophobia' }];
        fillPhobiaSelect();
      })
      .catch(function () {
        phobias = [{ id: 'arachnophobia', name: 'Arachnophobia' }];
        fillPhobiaSelect();
      });
  }

  function fillPhobiaSelect() {
    if (!el.phobiaSelect) return;
    el.phobiaSelect.innerHTML = '';
    phobias.forEach(function (p, i) {
      var opt = document.createElement('option');
      opt.value = String(i);
      opt.textContent = p.name;
      el.phobiaSelect.appendChild(opt);
    });
    if (el.btnStart) el.btnStart.disabled = false;
  }

  function initUrls() {
    var vr = baseUrl() + '/disclaimer-v2.html';
    var panel = baseUrl() + '/researcher.html';
    if (el.vrUrl) {
      el.vrUrl.href = vr;
      el.vrUrl.textContent = vr;
    }
    if (el.panelUrl) el.panelUrl.textContent = panel;
  }

  function initManualLevels() {
    var box = document.getElementById('manual-levels');
    if (!box) return;
    for (var lv = 0; lv <= 5; lv++) {
      (function (level) {
        var b = document.createElement('button');
        b.type = 'button';
        b.textContent = String(level);
        b.title = 'Send manual_level ' + level;
        b.addEventListener('click', function () {
          send({ type: 'manual_level', level: level });
          if (el.currentLevel) el.currentLevel.textContent = String(level);
        });
        box.appendChild(b);
      })(lv);
    }
  }

  function initTabs() {
    document.querySelectorAll('.tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var tab = btn.getAttribute('data-tab');
        document.querySelectorAll('.tab').forEach(function (b) {
          b.classList.toggle('active', b === btn);
        });
        document.getElementById('tab-session').classList.toggle('hidden', tab !== 'session');
        document.getElementById('tab-metrics').classList.toggle('hidden', tab !== 'metrics');
      });
    });
  }

  if (el.btnStart) el.btnStart.disabled = true;

  document.getElementById('btn-start').addEventListener('click', function () {
    var idx = parseInt(el.phobiaSelect.value, 10) || 0;
    var p = phobias[idx] || phobias[0] || { id: 'arachnophobia', name: 'Arachnophobia' };
    if (!p || !p.id) {
      if (el.sendError) el.sendError.textContent = 'Phobias still loading — wait a moment';
      return;
    }
    var st = el.sessionType.value;
    var lvl = parseInt(el.startLevel.value, 10);
    if (st === 'auto_sequence') lvl = 0;
    send({
      type: 'controller_start',
      phobia_id: p.id,
      phobia_name: p.name,
      level: lvl,
      experiment_id: (el.experimentId.value || 'session').trim(),
      duration_seconds: parseFloat(el.durationSec.value) || 0,
      session_type: st,
      baseline_calibration_seconds: parseFloat(el.baselineSec.value) || 0,
    });
    document.querySelector('[data-tab="metrics"]').click();
  });

  document.getElementById('btn-stop').addEventListener('click', function () {
    send({ type: 'stop' });
  });

  document.getElementById('auto-adapt').addEventListener('change', function (ev) {
    autoAdapt = !!ev.target.checked;
    send({ type: 'set_auto_adaptation', enabled: autoAdapt });
  });

  if (el.experimentId) {
    el.experimentId.value = 'exp_' + Math.floor(Date.now() / 1000);
  }

  initUrls();
  initTabs();
  initManualLevels();
  loadPhobias();
  connectWs();
})();
