import { WebSocketServer, WebSocket } from 'ws'
import { readTlsPems } from './generate-cert'

const WS_PORT = 8765

type JsonObj = Record<string, unknown>

export class MockRecorderServer {
  private wss: WebSocketServer | null = null
  private clients = new Set<WebSocket>()
  private recording = false
  private currentLevel = 2
  private currentPhobiaId = 'unknown'
  private currentExperimentId = 'session'
  private autoAdaptationEnabled = true
  private recordingT0 = 0
  private baselineCalibrationS = 0
  private broadcastTimer: ReturnType<typeof setInterval> | null = null

  start(certPath: string, keyPath: string): void {
    const { cert, key } = readTlsPems(certPath, keyPath)
    this.wss = new WebSocketServer({ port: WS_PORT, cert, key })
    console.log(`[mock] WSS listening on wss://0.0.0.0:${WS_PORT}`)

    this.wss.on('connection', (ws) => this.onConnection(ws))
    this.broadcastTimer = setInterval(() => this.tickAdaptive(), 2000)
  }

  stop(): void {
    if (this.broadcastTimer) clearInterval(this.broadcastTimer)
    this.broadcastTimer = null
    for (const c of this.clients) {
      try {
        c.close()
      } catch {
        /* ignore */
      }
    }
    this.clients.clear()
    this.wss?.close()
    this.wss = null
  }

  private onConnection(ws: WebSocket): void {
    this.clients.add(ws)
    console.log(`[mock] Client connected (${this.clients.size} total)`)

    ws.on('message', (raw) => {
      try {
        const data = JSON.parse(String(raw)) as JsonObj
        void this.handleMessage(ws, data)
      } catch (e) {
        ws.send(JSON.stringify({ error: String(e) }))
      }
    })

    ws.on('close', () => {
      this.clients.delete(ws)
      if (this.recording && this.clients.size === 0) {
        this.recording = false
        console.log('[mock] All clients disconnected — stopped.')
      }
    })
  }

  private broadcast(obj: object): void {
    const payload = JSON.stringify(obj)
    for (const c of [...this.clients]) {
      if (c.readyState === WebSocket.OPEN) {
        try {
          c.send(payload)
        } catch {
          this.clients.delete(c)
        }
      }
    }
  }

  private syntheticFearIndex(t: number): number {
    const base = 0.3 * Math.sin((2 * Math.PI * t) / 30)
    const noise = (Math.random() - 0.5) * 0.3
    return Math.round(Math.max(-3, Math.min(3, base + noise)) * 10000) / 10000
  }

  private tickAdaptive(): void {
    if (!this.recording || this.clients.size === 0) return
    const t = (Date.now() - this.recordingT0) / 1000
    const fi = this.syntheticFearIndex(t)
    const inCal = this.baselineCalibrationS > 0 && t < this.baselineCalibrationS
    let suggestion = 'hold'
    if (!inCal) {
      const r = Math.random()
      if (r < 0.05 && this.currentLevel < 5) suggestion = 'up'
      else if (r > 0.95 && this.currentLevel > 1) suggestion = 'down'
    }
    this.broadcast({
      type: 'adaptive_state',
      fear_index: fi,
      fear_index_aggregate: fi,
      fear_ref_mean: 0,
      fear_ref_std: 0.3,
      fear_stress_threshold: 0.45,
      dwell_above_s: 0,
      dwell_below_s: 0,
      adaptive_phase: inCal ? 'calibration' : 'adaptation',
      baseline_remaining_s: inCal ? Math.max(0, this.baselineCalibrationS - t) : null,
      baseline_calibration_total_s: this.baselineCalibrationS > 0 ? this.baselineCalibrationS : null,
      level_suggestion: suggestion,
      current_level: this.currentLevel,
      metrics: {
        theta_fz: 5 + Math.random() * 10,
        beta_alpha_fz_cz: 0.8 + Math.random() * 1.7,
        alpha_posterior: 8 + Math.random() * 12,
        faa: (Math.random() - 0.5) * 0.6,
      },
    })
  }

  private async handleMessage(ws: WebSocket, data: JsonObj): Promise<void> {
    const msgType = data.type as string
    console.log(`[mock] ← ${msgType}`)

    if (msgType === 'start' || msgType === 'controller_start') {
      this.currentPhobiaId = String(data.phobia_id ?? 'unknown')
      let lvl = Number(data.level ?? data.initial_level ?? 2)
      if (Number.isNaN(lvl)) lvl = 2
      this.currentLevel = Math.max(0, Math.min(5, Math.floor(lvl)))
      this.currentExperimentId = String(data.experiment_id ?? data.experimentId ?? 'session')
      const bcal = Number(data.baseline_calibration_seconds ?? 0)
      this.baselineCalibrationS = Number.isNaN(bcal) ? 0 : Math.max(0, bcal)
      this.recording = true
      this.recordingT0 = Date.now()

      this.broadcast({
        type: 'start_experiment',
        phobia_id: this.currentPhobiaId,
        phobia_name: data.phobia_name,
        level: this.currentLevel,
        experiment_id: this.currentExperimentId,
        duration_seconds: data.duration_seconds ?? data.durationSeconds,
        session_type: data.session_type ?? data.sessionType ?? 'hybrid',
        baseline_calibration_seconds: this.baselineCalibrationS,
      })

      ws.send(
        JSON.stringify({
          status: 'started',
          phobia_id: this.currentPhobiaId,
          level: this.currentLevel,
          experiment_id: this.currentExperimentId,
        }),
      )
      return
    }

    if (msgType === 'level_change') {
      this.currentLevel = Math.max(0, Math.min(5, Number(data.level ?? 2)))
      ws.send(JSON.stringify({ status: 'level_changed', level: this.currentLevel }))
      return
    }

    if (msgType === 'manual_level') {
      this.currentLevel = Math.max(0, Math.min(5, Number(data.level ?? 2)))
      this.broadcast({ type: 'force_level', level: this.currentLevel })
      ws.send(JSON.stringify({ status: 'manual_level_sent', level: this.currentLevel }))
      return
    }

    if (msgType === 'set_auto_adaptation') {
      this.autoAdaptationEnabled = Boolean(data.enabled ?? true)
      this.broadcast({ type: 'auto_adaptation_toggle', enabled: this.autoAdaptationEnabled })
      ws.send(JSON.stringify({ status: 'auto_adaptation_updated', enabled: this.autoAdaptationEnabled }))
      return
    }

    if (msgType === 'stop_video') {
      this.broadcast({ type: 'stop_video' })
      ws.send(JSON.stringify({ status: 'stop_video_sent' }))
      return
    }

    if (msgType === 'stop') {
      this.recording = false
      this.broadcast({ type: 'stop_video' })
      ws.send(JSON.stringify({ status: 'stopped', file: '(mock — no file)' }))
      return
    }

    ws.send(JSON.stringify({ error: `Unknown type: ${msgType}` }))
  }
}
