---
name: poteto-autonomous-verify
description: Run Lauren Tan (@poteto) 5-pillar autonomous verification, feature-map checks, metric ratchets, and fail-closed 3-attempt circuit breakers across Naqex offline tooling. Do not use for trivial Q&A, copy-only edits, live trading, or Holdout unlock.
---

# Poteto Autonomous Verification (5-Pillar Self-Healing Gate)

Enforce deterministic, fail-closed verification loops across Naqex repositories using Lauren Tan (`@poteto`) 5-pillar engineering principles: declarative feature maps, atomic event queues, monotonic metric ratchets, a hard 3-attempt circuit breaker, and AST-enforced architecture rules (`ARCH-01..10`).

## Hard Invariants (Fail-Closed)

- **Zero live spend & zero execution:** `spend_vnd = 0`, `OrderSend = 0`, `MT5_PROCS = 0`. Never trigger broker orders or disable dry-run / read-only guards.
- **Holdout 2025+ SEALED:** `holdout_rows_analysed = 0`. Never unlock, read, or mutate `NATIVE_FTMO_HOLDOUT_LOCK.json`.
- **Mode-A Dev PC safety:** Never run `pytest -n auto` or root `uv run`. Always use `.runtime/quant-audit-v24/Scripts/{python,ruff,ty,pytest}.exe` with worker cap `<= 2`.
- **`python -O` immunity:** Never rely on bare Python `assert` for security, holdout, or circuit-breaker enforcement (checked by `ARCH-09`). Use explicit `if ...: raise`.
- **2-Layer OPSEC:** Never persist usernames, real LAN/Tailscale IPs, bot tokens, or webhook URLs into `.runtime/automation/event_queue.jsonl` or tracked files (checked by `ARCH-10`).

## 5-Pillar Verification Loop

1. **Feature Map (`feature_map.json`):** Resolve the exact offline-safe verification command(s) for each touched domain from [feature_map.json](../../../tooling/automation/configs/feature_map.json) (`TradingWorkspace` quant core, `Cockpit`, `naqex_cli`, `projects/quant-trading`, read-only `projects/trader` QA, `education/check_setup.py`, and read-only `strategy-intel` bridge).
2. **Atomic Event Queue (`event_queue.py`):** Record every scan, verification result, ratchet decision, and escalation atomically (temp file + `fsync` + `os.replace`) via [event_queue.py](../../../tooling/automation/event_queue.py) into `.runtime/automation/event_queue.jsonl` with automatic secret/IP/path scrubbing.
3. **Monotonic Metric Ratchet (`ratchet_engine.py`):** Compare current metrics (`tests_passed`, `tests_failed`, `ruff_errors`, `ty_errors`, `arch_errors`, `opsec_leaks`) against the recorded baseline in [ratchet_engine.py](../../../tooling/automation/ratchet_engine.py). Quality only moves upward; any regression fails closed without weakening the baseline.
4. **Hard 3-Attempt Circuit Breaker (`ratchet_engine.py`):** Allow at most `max_attempts = 3` bounded consecutive repair attempts per target. On attempt #4 (4th consecutive failure), trip HARD to `CIRCUIT_OPEN_ESCALATE_OWNER` — zero infinite retry loops, explicit owner reset required.
5. **Architecture Gate (`check_architecture.py`):** Run [check_architecture.py](../../../tooling/check_architecture.py) with `--strict` to enforce `ARCH-01..10` (including `ARCH-08` offline no-`OrderSend`, `ARCH-09` zero bare `assert` guards, `ARCH-10` zero hardcoded user paths/raw IPs, and `tooling/workflows/` AST exclusion).

## Detailed Specification & Schemas

Read [ratchet-and-feature-map.md](references/ratchet-and-feature-map.md) for the full 5-pillar contract, feature-map schema, event-queue payload format, ratchet rules, and circuit-breaker state transitions.

## Workflow Handoffs

- **Defect diagnosis before bounded retry:** [evidence-debugging](../evidence-debugging/SKILL.md)
- **Quant infrastructure health & regression parity:** [quant-factory-ops](../quant-factory-ops/SKILL.md)
- **Pre-handoff adversarial falsification & negative mutants:** [adversarial-self-audit](../adversarial-self-audit/SKILL.md)
- **Durable evidence & delta persistence across sessions:** [evidence-continuity](../evidence-continuity/SKILL.md)

## Negative Triggers

- Do NOT use for trivial factual Q&A, wording/copy-only edits, or routine read-only status replies.
- Do NOT use to unlock Holdout 2025+, weaken ratchet floors, auto-reset an open circuit without owner approval, or send live orders.
