import WebSocket from 'ws'
import type { BrowserWindow } from 'electron'

function candidateUrls(useWss: boolean, host: string, port: number): string[] {
  const hp = `${host}:${port}`
  if (useWss) return [`wss://${hp}`, `ws://${hp}`]
  return [`ws://${hp}`, `wss://${hp}`]
}

function isLocalHost(host: string): boolean {
  return host === '127.0.0.1' || host === 'localhost' || host === '::1'
}

export class RecorderWsClient {
  private ws: WebSocket | null = null
  private urlIndex = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private stopped = false

  constructor(
    private readonly win: BrowserWindow,
    private readonly useWss: boolean,
    private readonly host: string,
    private readonly port: number,
  ) {}

  start(): void {
    this.stopped = false
    this.scheduleConnect(0)
  }

  stop(): void {
    this.stopped = true
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      try {
        this.ws.removeAllListeners()
        this.ws.close()
      } catch {
        /* ignore */
      }
      this.ws = null
    }
  }

  send(payload: object): { ok: boolean; error?: string } {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return { ok: false, error: 'WebSocket not connected' }
    }
    try {
      this.ws.send(JSON.stringify(payload))
      return { ok: true }
    } catch (e) {
      return { ok: false, error: String(e) }
    }
  }

  private scheduleConnect(delayMs: number): void {
    if (this.stopped) return
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.reconnectTimer = setTimeout(() => this.connectAttempt(), delayMs)
  }

  private connectAttempt(): void {
    if (this.stopped) return
    const urls = candidateUrls(this.useWss, this.host, this.port)
    const url = urls[this.urlIndex % urls.length]!
    const local = isLocalHost(this.host)
    const opts: WebSocket.ClientOptions = {}
    if (url.startsWith('wss:') && local) {
      opts.rejectUnauthorized = false
    }

    try {
      this.ws = new WebSocket(url, opts)
    } catch {
      this.bumpUrlAndRetry(1500)
      return
    }

    this.ws.on('open', () => {
      if (!this.win.isDestroyed()) {
        this.win.webContents.send('ws:status', { connected: true, url })
      }
    })

    this.ws.on('message', (data) => {
      try {
        const text = data.toString()
        const msg = JSON.parse(text) as unknown
        if (!this.win.isDestroyed()) {
          this.win.webContents.send('ws:message', msg)
        }
      } catch {
        /* ignore */
      }
    })

    this.ws.on('error', () => {
      /* close will follow */
    })

    this.ws.on('close', () => {
      if (!this.win.isDestroyed()) {
        this.win.webContents.send('ws:status', { connected: false })
      }
      this.ws = null
      if (!this.stopped) {
        this.bumpUrlAndRetry(2000)
      }
    })
  }

  private bumpUrlAndRetry(delayMs: number): void {
    this.urlIndex += 1
    this.scheduleConnect(delayMs)
  }
}
