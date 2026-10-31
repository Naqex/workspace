import { mkdir, open, readFile, unlink, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { execFileSync, spawn } from 'node:child_process'
import { connect } from 'node:net'
import { readFileSync, unlinkSync } from 'node:fs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const source = path.join(root, 'projects/paperclip')
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
  const response = await fetch('http://127.0.0.1:3100/api/health', { signal: AbortSignal.timeout(4000) }).catch(() => null)
  const health = response?.ok ? await response.json() : null
  if (owner.source !== source || !health || health.status !== 'ok' || health.commit !== commit) throw new Error('An existing Paperclip owner is starting, unavailable or on a different revision. Inspect owner.json before restarting.')
  console.log('Paperclip is already running: http://127.0.0.1:3100')
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
const occupied = await new Promise(resolve => {
  const socket = connect({ host: '127.0.0.1', port: 3100 })
  const finish = value => { socket.destroy(); resolve(value) }
  socket.once('connect', () => finish(true)); socket.once('error', () => finish(false))
  socket.setTimeout(1000, () => finish(true))
})
if (occupied) { await unlink(lockPath); throw new Error('Port 3100 is owned by another process; refusing to start Paperclip') }
try {
  await readFile(configPath)
} catch (error) {
  if (error.code !== 'ENOENT') throw error
  await writeFile(configPath, JSON.stringify({
    $meta: { version: 1, updatedAt: new Date().toISOString(), source: 'configure' },
    database: { mode: 'embedded-postgres', embeddedPostgresDataDir: path.join(instance, 'db'), embeddedPostgresPort: 54339,
      backup: { enabled: true, dir: path.join(instance, 'backups'), intervalMinutes: 60, retentionDays: 7 } },
    logging: { mode: 'file', logDir: path.join(instance, 'logs') },
    server: { deploymentMode: 'local_trusted', exposure: 'private', host: '127.0.0.1', port: 3100, serveUi: true },
    storage: { provider: 'local_disk', localDisk: { baseDir: path.join(instance, 'storage') } },
    secrets: { provider: 'local_encrypted', localEncrypted: { keyFilePath: path.join(instance, 'secrets/master.key') } },
    telemetry: { enabled: false }, updates: { checkEnabled: false },
  }, null, 2), { flag: 'wx' })
}
// Do not inherit Trader's database, provider credentials or runtime settings.
const inherited = ['PATH', 'SystemRoot', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'NUMBER_OF_PROCESSORS']
const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => inherited.some(name => name.toLowerCase() === key.toLowerCase())))
Object.assign(env, {
  PAPERCLIP_HOME: home, PAPERCLIP_INSTANCE_ID: 'trader-ui', PAPERCLIP_CONFIG: configPath,
  HOST: '127.0.0.1', PORT: '3100', PAPERCLIP_UI_DEV_MIDDLEWARE: 'true',
  HEARTBEAT_SCHEDULER_ENABLED: 'false', PAPERCLIP_ANNOUNCEMENTS_ENABLED: 'false',
})
const child = spawn(process.execPath, ['--import', './node_modules/tsx/dist/loader.mjs', 'src/index.ts'], {
  cwd: path.join(source, 'server'), env, stdio: 'inherit', windowsHide: true,
})
await writeFile(ownerPath, JSON.stringify({
  launcherPid: process.pid, serverPid: child.pid, startedAt: new Date().toISOString(), source, commit,
  origin: 'http://127.0.0.1:3100', configPath,
}, null, 2))
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal))
child.on('error', error => { console.error(error.message); process.exitCode = 1 })
child.on('exit', code => { process.exitCode = code ?? 1 })
