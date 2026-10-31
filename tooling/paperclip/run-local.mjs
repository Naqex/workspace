import { mkdir, open, readFile, unlink, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { execFileSync, spawn } from 'node:child_process'
import { connect } from 'node:net'
import { readFileSync, unlinkSync } from 'node:fs'
import services from '../../projects/trader/foundation_v2/local-services.json' with { type: 'json' }

const ports = [services.paperclipPort, services.paperclipHmrPort, services.paperclipDatabasePort]
if (services.host !== '127.0.0.1' || ports.some(port => !Number.isInteger(port) || port < 1024 || port > 65535)
  || new Set(ports).size !== ports.length || services.paperclipHmrPort !== services.paperclipPort + 10000) {
  throw new Error('Invalid loopback Paperclip ports in Trader local-services.json')
}
const origin = `http://${services.host}:${services.paperclipPort}`

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const source = path.join(root, 'projects/integrations/paperclip')
const home = path.join(root, '.runtime/paperclip')
const instance = path.join(home, 'instances/trader-ui')
const configPath = path.join(instance, 'config.json')
const ownerPath = path.join(instance, 'owner.json')
const lockPath = path.join(instance, 'launch.lock')
const commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: source, encoding: 'utf8', windowsHide: true }).trim()
const alive = pid => {
  if (!Number.isInteger(pid) || pid <= 0) return false
  try { process.kill(pid, 0); return true } catch (error) { return error.code !== 'ESRCH' }
}
await mkdir(instance, { recursive: true })
let owner
try { owner = JSON.parse(await readFile(ownerPath, 'utf8')) } catch (error) { if (error.code !== 'ENOENT') throw error }
if (owner && (alive(owner.serverPid) || alive(owner.launcherPid))) {
  if (owner.origin !== origin) throw new Error('The owned Paperclip instance uses another port. Stop it and update its config before restarting; see tooling/paperclip/README.md.')
  const response = await fetch(`${origin}/api/health`, { signal: AbortSignal.timeout(4000) }).catch(() => null)
  const health = response?.ok ? await response.json() : null
  if (owner.source !== source || !health || health.status !== 'ok' || health.commit !== commit) throw new Error('An existing Paperclip owner is starting, unavailable or on a different revision. Inspect owner.json before restarting.')
  console.log(`Paperclip is already running: ${origin}`)
  process.exit(0)
}
// Atomic startup ownership also covers the interval before owner.json is written.
try {
  const previous = JSON.parse(await readFile(lockPath, 'utf8'))
  if (alive(previous.pid)) throw new Error('Paperclip launcher is already active')
  await unlink(lockPath)
} catch (error) { if (error.code !== 'ENOENT') throw error }
const lock = await open(lockPath, 'wx')
await lock.writeFile(JSON.stringify({ pid: process.pid }))
await lock.close()
process.on('exit', () => {
  try { if (JSON.parse(readFileSync(lockPath, 'utf8')).pid === process.pid) unlinkSync(lockPath) } catch { /* A crash can leave a stale lock, checked on the next start. */ }
})
const occupied = port => new Promise(resolve => {
  const socket = connect({ host: services.host, port })
  const finish = value => { socket.destroy(); resolve(value) }
  socket.once('connect', () => finish(true)); socket.once('error', () => finish(false))
  socket.setTimeout(1000, () => finish(true))
})
for (const port of ports) {
  if (await occupied(port)) throw new Error(`Port ${port} is occupied; refusing to start Paperclip or attach to another instance`)
}
let config
try {
  config = JSON.parse(await readFile(configPath, 'utf8'))
} catch (error) {
  if (error.code !== 'ENOENT') throw error
  await writeFile(configPath, JSON.stringify({
    $meta: { version: 1, updatedAt: new Date().toISOString(), source: 'configure' },
    database: { mode: 'embedded-postgres', embeddedPostgresDataDir: path.join(instance, 'db'), embeddedPostgresPort: services.paperclipDatabasePort,
      backup: { enabled: true, dir: path.join(instance, 'backups'), intervalMinutes: 60, retentionDays: 7 } },
    logging: { mode: 'file', logDir: path.join(instance, 'logs') },
    server: { deploymentMode: 'local_trusted', exposure: 'private', host: services.host, port: services.paperclipPort, serveUi: true },
    storage: { provider: 'local_disk', localDisk: { baseDir: path.join(instance, 'storage') } },
    secrets: { provider: 'local_encrypted', localEncrypted: { keyFilePath: path.join(instance, 'secrets/master.key') } },
    telemetry: { enabled: false }, updates: { checkEnabled: false },
  }, null, 2), { flag: 'wx' })
  config = JSON.parse(await readFile(configPath, 'utf8'))
}
if (config.server?.host !== services.host || config.server?.port !== services.paperclipPort
  || config.database?.mode !== 'embedded-postgres' || config.database?.embeddedPostgresPort !== services.paperclipDatabasePort) {
  throw new Error('Paperclip config ports differ from local-services.json. Back up and update the stopped instance config; do not reset its database.')
}
// Do not inherit Trader's database, provider credentials or runtime settings.
const inherited = ['PATH', 'SystemRoot', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'NUMBER_OF_PROCESSORS']
const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => inherited.some(name => name.toLowerCase() === key.toLowerCase())))
Object.assign(env, {
  PAPERCLIP_HOME: home, PAPERCLIP_INSTANCE_ID: 'trader-ui', PAPERCLIP_CONFIG: configPath,
  HOST: services.host, PORT: String(services.paperclipPort), PAPERCLIP_UI_DEV_MIDDLEWARE: 'true',
  VITE_NAQEX_WORKSPACE_ORIGIN: `http://${services.host}:${services.aiPreviewPort}`,
  HEARTBEAT_SCHEDULER_ENABLED: 'false', PAPERCLIP_ANNOUNCEMENTS_ENABLED: 'false',
})
const child = spawn(process.execPath, ['--import', './node_modules/tsx/dist/loader.mjs', 'src/index.ts'], {
  cwd: path.join(source, 'server'), env, stdio: 'inherit', windowsHide: true,
})
await writeFile(ownerPath, JSON.stringify({
  launcherPid: process.pid, serverPid: child.pid, startedAt: new Date().toISOString(), source, commit,
  origin, hmrPort: services.paperclipHmrPort, databasePort: services.paperclipDatabasePort, configPath,
}, null, 2))
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal))
child.on('error', error => { console.error(error.message); process.exitCode = 1 })
child.on('exit', code => { process.exitCode = code ?? 1 })
