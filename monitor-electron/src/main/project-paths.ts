import { app } from 'electron'
import { existsSync } from 'fs'
import { join } from 'path'

/** Repo root (dev) or resources path (packaged). */
export function getProjectRoot(): string {
  const fromEnv = process.env.PHOBIAS_ROOT?.trim()
  if (fromEnv && existsSync(join(fromEnv, 'app', 'data', 'content.json'))) {
    return fromEnv
  }

  if (app.isPackaged && process.resourcesPath) {
    if (existsSync(join(process.resourcesPath, 'app', 'data', 'content.json'))) {
      return process.resourcesPath
    }
  }

  let dir = __dirname
  for (let i = 0; i < 12; i++) {
    if (existsSync(join(dir, 'app', 'data', 'content.json'))) return dir
    const parent = join(dir, '..')
    if (parent === dir) break
    dir = parent
  }
  return process.cwd()
}

export function getAppDir(): string {
  return join(getProjectRoot(), 'app')
}

/** TLS certs: userData when packaged (per-machine LAN IPs), project root in dev. */
export function getCertsDir(): string {
  if (app.isPackaged) {
    return join(app.getPath('userData'), 'certs')
  }
  return getProjectRoot()
}
