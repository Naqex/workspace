import { readFileSync, existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { execFileSync } from 'node:child_process'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const git = (cwd, args) => execFileSync('git', args, { cwd, encoding: 'utf8', windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] }).trim()

export function inspectSource(workspace, entry) {
  const source = path.resolve(workspace, entry.path)
  if (!source.startsWith(path.resolve(workspace) + path.sep)) throw new Error('Integration path escapes workspace')
  if (!existsSync(path.join(source, '.git'))) return { id: entry.id, status: 'missing-source' }
  try {
    const revision = git(source, ['rev-parse', 'HEAD'])
    const indexed = git(workspace, ['ls-files', '--stage', '--', entry.path]).split(/\s+/)
    const origin = git(source, ['remote', 'get-url', 'origin'])
    const licensePresent = existsSync(path.join(source, entry.licenseFile))
    const dirty = Boolean(git(source, ['status', '--porcelain', '--untracked-files=normal']))
    const pinMatches = indexed[0] === '160000' && indexed[1] === revision
    return { id: entry.id, status: pinMatches && origin === entry.repository && licensePresent && !dirty ? 'source-ready' : 'inspect',
      revision, pinMatches, originMatches: origin === entry.repository, licensePresent, dirty }
  } catch { return { id: entry.id, status: 'git-unavailable' } }
}

async function main() {
  if (process.argv.slice(2).some(arg => arg !== '--runtime')) throw new Error('Usage: node tooling/integrations/doctor.mjs [--runtime]')
  const catalog = JSON.parse(readFileSync(new URL('./catalog.json', import.meta.url), 'utf8'))
  const result = { sources: catalog.sources.map(entry => inspectSource(root, entry)) }
  if (process.argv.includes('--runtime')) {
    const services = JSON.parse(readFileSync(path.join(root, 'projects/trader/foundation_v2/local-services.json'), 'utf8'))
    if (services.host !== '127.0.0.1' || !Number.isInteger(services.paperclipPort) || services.paperclipPort < 1024 || services.paperclipPort > 65535) throw new Error('Invalid Paperclip loopback configuration')
    try {
      const response = await fetch(`http://127.0.0.1:${services.paperclipPort}/api/health`, { signal: AbortSignal.timeout(4000) })
      const health = response.ok ? await response.json() : null
      const source = result.sources.find(entry => entry.id === 'paperclip')
      result.paperclip = { status: health?.status === 'ok' && health.commit === source?.revision ? 'healthy' : 'inspect' }
    } catch { result.paperclip = { status: 'unavailable' } }
  }
  console.log(JSON.stringify(result, null, 2))
  if (result.sources.some(entry => entry.status !== 'source-ready') || result.paperclip && result.paperclip.status !== 'healthy') process.exitCode = 1
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main()
