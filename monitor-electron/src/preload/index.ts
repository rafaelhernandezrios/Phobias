import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('monitorAPI', {
  sendWs: (payload: Record<string, unknown>) =>
    ipcRenderer.invoke('ws:send', payload) as Promise<{ ok: boolean; error?: string }>,

  onWsMessage: (cb: (msg: unknown) => void) => {
    const fn = (_e: Electron.IpcRendererEvent, msg: unknown) => cb(msg)
    ipcRenderer.on('ws:message', fn)
    return () => ipcRenderer.removeListener('ws:message', fn)
  },

  onWsStatus: (cb: (s: { connected: boolean; url?: string }) => void) => {
    const fn = (_e: Electron.IpcRendererEvent, s: { connected: boolean; url?: string }) => cb(s)
    ipcRenderer.on('ws:status', fn)
    return () => ipcRenderer.removeListener('ws:status', fn)
  },

  loadPhobias: () =>
    ipcRenderer.invoke('content:phobias') as Promise<{
      ok: boolean
      phobias: { id: string; name: string }[]
      root: string
      error?: string
    }>,

  getLogos: () =>
    ipcRenderer.invoke('assets:logos') as Promise<{ atr: string | null; mirai: string | null }>,

  openUrl: (url: string) => ipcRenderer.invoke('shell:open', url) as Promise<{ ok: boolean }>,

  getConfig: () =>
    ipcRenderer.invoke('config:get') as Promise<{
      useWss: boolean
      host: string
      port: number
      webAppUrl: string
    }>,
})
