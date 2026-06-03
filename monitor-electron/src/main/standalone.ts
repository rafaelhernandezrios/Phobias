import { app } from 'electron'
import { ensureTlsCerts } from './generate-cert'
import { getCertsDir } from './project-paths'
import { MockRecorderServer } from './mock-recorder'
import { LocalHttpsServer, HTTPS_PORT } from './local-https-server'

let mockRecorder: MockRecorderServer | null = null
let httpsServer: LocalHttpsServer | null = null
let lanUrls: string[] = []

export function isStandaloneMode(): boolean {
  return app.isPackaged || process.argv.includes('--standalone')
}

export function getStandaloneLanUrls(): string[] {
  return lanUrls
}

export function startStandaloneStack(): void {
  if (mockRecorder || httpsServer) return

  const certsDir = getCertsDir()
  const { certPath, keyPath } = ensureTlsCerts(certsDir)

  mockRecorder = new MockRecorderServer()
  mockRecorder.start(certPath, keyPath)

  httpsServer = new LocalHttpsServer()
  lanUrls = httpsServer.start(certPath, keyPath)

  console.log('')
  console.log('=== VR Phobia — standalone (no Node/Python install) ===')
  console.log(`  PC:    https://127.0.0.1:${HTTPS_PORT}`)
  if (lanUrls.length) {
    console.log('  Quest:')
    lanUrls.forEach((ip) => console.log(`    https://${ip}:${HTTPS_PORT}`))
  }
  console.log('')
}

export function stopStandaloneStack(): void {
  httpsServer?.stop()
  mockRecorder?.stop()
  httpsServer = null
  mockRecorder = null
}
