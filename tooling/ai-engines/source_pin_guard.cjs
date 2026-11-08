// Collectors do not consume canonical inputs between initial and final checks.
const fs = require('fs');
const crypto = require('crypto');

function createPinGuard(pins, activePaths) {
  if (!pins || Array.isArray(pins) || typeof pins !== 'object' || !Object.keys(pins).length ||
      !Array.isArray(activePaths) || !activePaths.length ||
      Object.entries(pins).some(([name, value]) => !name || typeof value !== 'string' || !/^[a-f0-9]{64}$/.test(value)) ||
      activePaths.some(name => typeof name !== 'string' || !Object.hasOwn(pins, name))) {
    throw Error('explicit_full_and_active_source_pins_required');
  }
  const expected = Object.freeze({...pins});
  const active = [...new Set(activePaths)];
  const metrics = {fullChecks: 0, activeChecks: 0, hashedBytes: 0};
  let initialized = false, finalized = false, failed = false;
  function verify(paths) {
    if (failed) throw Error('source_guard_failed');
    try {
      for (const name of paths) {
        const bytes = fs.readFileSync(name);
        metrics.hashedBytes += bytes.length;
        if (crypto.createHash('sha256').update(bytes).digest('hex') !== expected[name]) {
          throw Error('source_pin_changed: '+name);
        }
      }
    } catch (error) {
      failed = true;
      throw error;
    }
  }
  function initial() {
    if (initialized || finalized) throw Error('source_guard_already_initialized');
    verify(Object.keys(expected));metrics.fullChecks++;initialized = true;
  }
  function beforeStep() {
    if (!initialized || finalized) throw Error('source_guard_phase');
    verify(active);metrics.activeChecks++;
  }
  function final() {
    if (!initialized || finalized) throw Error('source_guard_phase');
    verify(Object.keys(expected));metrics.fullChecks++;finalized = true;
    return {...metrics};
  }
  return Object.freeze({initial, beforeStep, final});
}

module.exports = {createPinGuard};
