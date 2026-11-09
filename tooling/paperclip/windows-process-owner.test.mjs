import assert from 'node:assert/strict'
import test from 'node:test'
import { windowsOwnerIsActive } from './windows-process-owner.mjs'

const executable = 'C:\\tools\\node.exe'
const saved = { pid: 7044, name: 'node.exe', executable, createdAt: '2026-11-03T11:23:41Z',
  commandLine: 'node tooling/paperclip/run-local.mjs' }
const active = (current, expected = saved) => windowsOwnerIsActive(7044, expected, () => current, executable)

test('recycled legacy PID belonging to Brave is not a Paperclip owner', () => {
  assert.equal(active({ pid: 7044, name: 'BraveCrashHandler.exe', executable: null }, null), false)
})
test('exact identity is active; PID reuse, path and command changes are stale', () => {
  assert.equal(active({ ...saved }), true)
  assert.equal(active({ ...saved, executable: 'c:\\TOOLS\\NODE.EXE' }), true)
  for (const changed of [ { createdAt: '2026-11-04T20:27:11Z' },
    { executable: 'C:\\other\\node.exe' }, { commandLine: 'node unrelated.mjs' }, { pid: 9999 } ]) {
    assert.equal(active({ ...saved, ...changed }), false)
  }
  assert.equal(active(null), false)
})
test('unverifiable Node or legacy live Node fails closed', () => {
  assert.throws(() => active({ ...saved, executable: null }), /Cannot verify/)
  assert.throws(() => active({ ...saved }, null), /Legacy/)
  assert.throws(() => active({ ...saved, name: null }), /Cannot verify/)
})
