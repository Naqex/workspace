import { execFileSync } from 'node:child_process'
import path from 'node:path'

export function readWindowsProcess(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return null
  // Numeric PID only; neither paths nor process command lines become shell code.
  const command = `$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); $p=Get-CimInstance Win32_Process -Filter 'ProcessId = ${pid}'; if ($p) { [pscustomobject]@{pid=[int]$p.ProcessId; name=$p.Name; executable=$p.ExecutablePath; createdAt=$p.CreationDate.ToUniversalTime().ToString('o'); commandLine=$p.CommandLine} | ConvertTo-Json -Compress }`
  const raw = execFileSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', command], {
    encoding: 'utf8', windowsHide: true, timeout: 10000,
  }).trim()
  return raw ? JSON.parse(raw) : null
}

export function windowsOwnerIsActive(pid, saved, inspect = readWindowsProcess, executable = process.execPath) {
  if (!Number.isInteger(pid) || pid <= 0) return false
  const current = inspect(pid)
  if (!current) return false
  const expectedName = path.win32.basename(executable).toLowerCase()
  if (typeof current.name !== 'string') throw new Error('Cannot verify Paperclip process name')
  if (current.name.toLowerCase() !== expectedName) return false
  if (!current.executable || !current.createdAt || !current.commandLine) {
    throw new Error('Cannot verify Paperclip process identity; inspect the existing owner before starting')
  }
  const normalize = value => path.win32.normalize(value).toLowerCase()
  if (normalize(current.executable) !== normalize(executable)) return false
  if (!saved) {
    throw new Error('Legacy Paperclip Node PID has no creation identity; inspect it before starting')
  }
  return current.pid === pid && saved.pid === pid &&
    current.createdAt === saved.createdAt && current.commandLine === saved.commandLine &&
    typeof saved.executable === 'string' && normalize(current.executable) === normalize(saved.executable)
}
