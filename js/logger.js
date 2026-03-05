/**
 * Event logger for VR Phobia Exposure sessions.
 * Logs: session_id, phobia_id, level, video_id, timestamps, user_actions.
 */

const VRPhobiaLogger = {
  sessionId: null,
  logs: [],

  init() {
    if (!this.sessionId) {
      this.sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).slice(2, 9);
    }
    return this.sessionId;
  },

  getSessionId() {
    return this.sessionId || this.init();
  },

  log(type, payload = {}) {
    const entry = {
      type,
      timestamp: new Date().toISOString(),
      session_id: this.getSessionId(),
      ...payload
    };
    this.logs.push(entry);
    if (typeof console !== 'undefined' && console.log) {
      console.log('[VRPhobiaLog]', type, entry);
    }
    return entry;
  },

  sessionStart() {
    return this.log('session_start', { start_time: new Date().toISOString() });
  },

  sessionEnd() {
    return this.log('session_end', { end_time: new Date().toISOString() });
  },

  consentAccepted() {
    return this.log('consent_accepted', {});
  },

  phobiaSelected(phobiaId, phobiaName) {
    return this.log('phobia_selected', { phobia_id: phobiaId, phobia_name: phobiaName });
  },

  levelSelected(phobiaId, level, videoId) {
    return this.log('level_selected', {
      phobia_id: phobiaId,
      level,
      video_id: videoId,
      timestamp_start: new Date().toISOString()
    });
  },

  videoStart(phobiaId, level, videoId) {
    return this.log('video_start', {
      phobia_id: phobiaId,
      level,
      video_id: videoId,
      timestamp_start: new Date().toISOString()
    });
  },

  videoEnd(phobiaId, level, videoId, durationSeconds) {
    return this.log('video_end', {
      phobia_id: phobiaId,
      level,
      video_id: videoId,
      timestamp_end: new Date().toISOString(),
      duration_seconds: durationSeconds
    });
  },

  userAction(action, payload = {}) {
    return this.log('user_action', { action, ...payload });
  },

  emergencyExit(phobiaId, level, reason) {
    return this.log('emergency_exit', {
      phobia_id: phobiaId || null,
      level: level || null,
      reason: reason || 'user_triggered',
      timestamp_end: new Date().toISOString()
    });
  },

  getLogs() {
    return this.logs;
  },

  exportJSON() {
    return JSON.stringify(this.logs, null, 2);
  },

  downloadLogs(filename) {
    const blob = new Blob([this.exportJSON()], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename || 'vr-phobia-session-' + this.getSessionId() + '.json';
    a.click();
    URL.revokeObjectURL(a.href);
  }
};

// Global para uso en escenas
if (typeof window !== 'undefined') window.VRPhobiaLogger = VRPhobiaLogger;
