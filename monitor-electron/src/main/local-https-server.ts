import http from 'http'
import https from 'https'
import fs from 'fs'
import path from 'path'
import os from 'os'
import { WebSocketServer, WebSocket } from 'ws'
import { readTlsPems } from './generate-cert'
import { getAppDir } from './project-paths'

const PORT = 8443
const RECORDER_URL = 'wss://127.0.0.1:8765'

function getMimeType(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase()
  const mimes: Record<string, string> = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.css': 'text/css',
    '.ico': 'image/x-icon',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
  }
  return mimes[ext] || 'application/octet-stream'
}

function lanIpv4s(): string[] {
  const ips: string[] = []
  try {
    for (const ifaces of Object.values(os.networkInterfaces())) {
      for (const ni of ifaces || []) {
        if (ni.family === 'IPv4' && !ni.internal) ips.push(ni.address)
      }
    }
  } catch {
    /* ignore */
  }
  return [...new Set(ips)]
}

export class LocalHttpsServer {
  private httpsServer: https.Server | null = null
  private httpServer: http.Server | null = null

  start(certPath: string, keyPath: string): string[] {
    const appRoot = getAppDir()
    const { cert, key } = readTlsPems(certPath, keyPath)

    const serveFile = (res: http.ServerResponse, urlPath: string): void => {
      const clean = urlPath.replace(/\?.*$/, '') || '/'
      let full = path.join(appRoot, clean === '/' ? 'index.html' : clean)
      if (!fs.existsSync(full)) {
        const asDir = path.join(appRoot, clean, 'index.html')
        if (fs.existsSync(asDir)) {
          res.writeHead(200, { 'Content-Type': 'text/html' })
          res.end(fs.readFileSync(asDir))
          return
        }
        res.writeHead(404)
        res.end('Not found')
        return
      }
      if (fs.statSync(full).isDirectory()) {
        full = path.join(full, 'index.html')
        if (!fs.existsSync(full)) {
          res.writeHead(404)
          res.end('Not found')
          return
        }
      }
      res.writeHead(200, { 'Content-Type': getMimeType(full) })
      res.end(fs.readFileSync(full))
    }

    this.httpsServer = https.createServer({ key, cert }, (req, res) => {
      serveFile(res, req.url === '/' ? '/index.html' : req.url || '/')
    })

    const wss = new WebSocketServer({ noServer: true })
    this.httpsServer.on('upgrade', (req, socket, head) => {
      const urlPath = (req.url || '').split('?')[0]
      if (urlPath !== '/ws') {
        socket.destroy()
        return
      }
      wss.handleUpgrade(req, socket, head, (clientWs) => {
        const upstream = new WebSocket(RECORDER_URL, { rejectUnauthorized: false })
        const queue: Buffer[] = []
        let upstreamOpen = false

        clientWs.on('message', (data) => {
          if (upstreamOpen) upstream.send(data)
          else queue.push(data as Buffer)
        })
        upstream.on('open', () => {
          upstreamOpen = true
          while (queue.length) upstream.send(queue.shift()!)
        })
        upstream.on('message', (data) => {
          if (clientWs.readyState === WebSocket.OPEN) clientWs.send(data)
        })
        const closeBoth = (): void => {
          try {
            clientWs.close()
          } catch {
            /* ignore */
          }
          try {
            upstream.close()
          } catch {
            /* ignore */
          }
        }
        clientWs.on('close', closeBoth)
        upstream.on('close', closeBoth)
        clientWs.on('error', closeBoth)
        upstream.on('error', (err) => {
          console.error('[ws-proxy]', err.message)
          closeBoth()
        })
      })
    })

    this.httpsServer.listen(PORT, '0.0.0.0')

    this.httpServer = http.createServer((req, res) => {
      res.writeHead(301, { Location: `https://127.0.0.1:${PORT}${req.url}` })
      res.end()
    })
    this.httpServer.listen(8080)

    const lan = lanIpv4s()
    console.log(`[https] https://127.0.0.1:${PORT}`)
    lan.forEach((ip) => console.log(`[https] https://${ip}:${PORT}`))
    return lan
  }

  stop(): void {
    this.httpsServer?.close()
    this.httpServer?.close()
    this.httpsServer = null
    this.httpServer = null
  }
}

export const HTTPS_PORT = PORT
