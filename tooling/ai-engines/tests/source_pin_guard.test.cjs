const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const {createPinGuard} = require('../source_pin_guard.cjs');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'naqex-pin-guard-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const code = path.join(root, 'code'), input = path.join(root, 'input');
  fs.writeFileSync(code, 'code'); fs.writeFileSync(input, 'input');
  const pins = {[code]: sha('code'), [input]: sha('input')};
  return {code, input, pins};
}

test('full binding before use and commit, only active bytes per step', t => {
  const {code, input, pins} = fixture(t);
  const guard = createPinGuard(pins, [code, code]);
  guard.initial(); guard.beforeStep(); guard.beforeStep();
  assert.deepEqual(guard.final(), {fullChecks: 2, activeChecks: 2, hashedBytes: 26});
  assert.throws(() => guard.beforeStep(), /phase/);
  assert.throws(() => guard.final(), /phase/);
  assert.throws(() => guard.initial(), /already_initialized/);
  assert.ok(fs.existsSync(input));
});

test('explicit valid pins and active subset required', () => {
  for (const [pins, active] of [[null, []], [{}, ['x']], [{x: null}, ['x']],
    [{x: 'a'.repeat(64)}, []], [{x: 'a'.repeat(64)}, ['y']],
    [{x: 'A'.repeat(64)}, ['x']], [{'': 'a'.repeat(64)}, ['']]]) {
    assert.throws(() => createPinGuard(pins, active), /explicit_full_and_active/);
  }
});

test('phase sequence and caller maps cannot bypass checks', t => {
  const {code, pins} = fixture(t), active = [code];
  const guard = createPinGuard(pins, active);
  assert.throws(() => guard.beforeStep(), /phase/);
  assert.throws(() => guard.final(), /phase/);
  pins[code] = sha('changed'); active.length = 0;
  guard.initial();
  assert.throws(() => guard.initial(), /already_initialized/);
  fs.writeFileSync(code, 'changed');
  assert.throws(() => guard.beforeStep(), /source_pin_changed/);
  fs.writeFileSync(code, 'code');
  assert.throws(() => guard.final(), /source_guard_failed/);
});

test('input changes caught at admission and final, failures latch', t => {
  const {code, input, pins} = fixture(t);
  fs.writeFileSync(input, 'changed');
  const early = createPinGuard(pins, [code]);
  assert.throws(() => early.initial(), /source_pin_changed/);
  fs.writeFileSync(input, 'input');
  assert.throws(() => early.initial(), /source_guard_failed/);
  const late = createPinGuard(pins, [code]); late.initial();
  fs.writeFileSync(input, 'changed'); late.beforeStep();
  assert.throws(() => late.final(), /source_pin_changed/);
  fs.writeFileSync(input, 'input');
  assert.throws(() => late.final(), /source_guard_failed/);
});

test('missing files reject rather than becoming unverified inputs', t => {
  const {code, input, pins} = fixture(t);
  const guard = createPinGuard(pins, [code]); guard.initial();
  fs.unlinkSync(input);
  assert.throws(() => guard.final(), /ENOENT/);
  const missing = createPinGuard(pins, [code]);
  assert.throws(() => missing.initial(), /ENOENT/);
});
