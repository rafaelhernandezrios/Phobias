/// <reference types="vite/client" />

interface MonitorAPI {
  sendWs: (payload: Record<string, unknown>) => Promise<{ ok: boolean; error?: string }>
  onWsMessage: (cb: (msg: unknown) => void) => () => void
  onWsStatus: (cb: (s: { connected: boolean; url?: string }) => void) => () => void
  loadPhobias: () => Promise<{
    ok: boolean
    phobias: { id: string; name: string }[]
    root: string
    error?: string
  }>
  getLogos: () => Promise<{ atr: string | null; mirai: string | null }>
  openUrl: (url: string) => Promise<{ ok: boolean }>
  getConfig: () => Promise<{ useWss: boolean; host: string; port: number; webAppUrl: string }>
}

interface Window {
  monitorAPI: MonitorAPI
}
