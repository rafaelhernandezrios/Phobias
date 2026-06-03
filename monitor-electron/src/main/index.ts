import { app, shell, ipcMain, BrowserWindow } from 'electron'
import { join } from 'path'
import { readFileSync, existsSync } from 'fs'
import { RecorderWsClient } from './ws-client'
import { getProjectRoot } from './project-paths'
import {
  isStandaloneMode,
  startStandaloneStack,
  stopStandaloneStack,
  getStandaloneLanUrls,
} from './standalone'
import { HTTPS_PORT } from './local-https-server'

const WEB_APP_URL = `https://127.0.0.1:${HTTPS_PORT}/`

function parseCliFlags(): { useWss: boolean; host: string; port: number } {
  const argv = process.argv
  const useWss = argv.includes('--wss') || isStandaloneMode()
  let host = '127.0.0.1'
  let port = 8765
  const hi = argv.indexOf('--host')
  if (hi >= 0 && argv[hi + 1]) host = argv[hi + 1]!
  const pi = argv.indexOf('--port')
  if (pi >= 0 && argv[pi + 1]) port = Number(argv[pi + 1]) || 8765
  return { useWss, host, port }
}

let mainWindow: BrowserWindow | null = null
let wsClient: RecorderWsClient | null = null

function registerIpcOnce(): void {
  if ((globalThis as { __monitorIpc?: boolean }).__monitorIpc) return
  ;(globalThis as { __monitorIpc?: boolean }).__monitorIpc = true

  ipcMain.handle('ws:send', (_e, payload: object) => {
    if (!wsClient) return { ok: false, error: 'No client' }
    return wsClient.send(payload)
  })

  ipcMain.handle('content:phobias', () => {
    const root = getProjectRoot()
    const path = join(root, 'app', 'data', 'content.json')
    try {
      const raw = readFileSync(path, 'utf-8')
      const data = JSON.parse(raw) as { phobias?: { id?: string; name?: string }[] }
      const out: { id: string; name: string }[] = []
      for (const p of data.phobias ?? []) {
        if (p.id) out.push({ id: p.id, name: p.name ?? p.id })
      }
      return { ok: true, phobias: out, root }
    } catch (e) {
      return {
        ok: false,
        error: String(e),
        phobias: [{ id: 'arachnophobia', name: 'Arachnophobia' }],
        root,
      }
    }
  })

  ipcMain.handle('assets:logos', () => {
    const root = getProjectRoot()
    const atr = join(root, 'app', 'assets', 'thumbnails', 'atr_logo.png')
    const mirai = join(root, 'app', 'assets', 'thumbnails', 'mirai_logo.png')
    const toDataUrl = (abs: string): string | null => {
      if (!existsSync(abs)) return null
      try {
        const b64 = readFileSync(abs).toString('base64')
        return `data:image/png;base64,${b64}`
      } catch {
        return null
      }
    }
    return { atr: toDataUrl(atr), mirai: toDataUrl(mirai) }
  })

  ipcMain.handle('shell:open', (_e, url: string) => {
    void shell.openExternal(url || WEB_APP_URL)
    return { ok: true }
  })

  ipcMain.handle('config:get', () => {
    const cfg = parseCliFlags()
    const lan = getStandaloneLanUrls()
    return {
      ...cfg,
      webAppUrl: WEB_APP_URL,
      standalone: isStandaloneMode(),
      lanUrls: lan.map((ip) => `https://${ip}:${HTTPS_PORT}`),
    }
  })
}

function createWindow(): void {
  const { useWss, host, port } = parseCliFlags()

  mainWindow = new BrowserWindow({
    width: 480,
    height: 900,
    minWidth: 360,
    minHeight: 560,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
    },
    title: isStandaloneMode()
      ? 'VR Phobia — Standalone'
      : 'VR Phobia — Adaptive Monitor / VR恐怖症—EEGモニター',
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.on('closed', () => {
    wsClient?.stop()
    wsClient = null
    mainWindow = null
  })

  wsClient = new RecorderWsClient(mainWindow, useWss, host, port)
  wsClient.start()

  const rendererUrl = process.env['ELECTRON_RENDERER_URL']
  if (rendererUrl) {
    void mainWindow.loadURL(rendererUrl)
  } else {
    void mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  if (isStandaloneMode()) {
    startStandaloneStack()
  }
  registerIpcOnce()
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  wsClient?.stop()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('will-quit', () => {
  stopStandaloneStack()
})
