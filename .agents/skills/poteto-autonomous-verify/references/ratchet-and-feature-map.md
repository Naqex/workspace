# Ratchet, Circuit Breaker & Feature Map Reference

Detailed specification for [poteto-autonomous-verify](../SKILL.md), covering the Lauren Tan (`@poteto`) 5-pillar autonomous verification harness for Naqex `TradingWorkspace`.

## Pillar 1: Declarative Feature Map

Location: [feature_map.json](../../../../tooling/automation/configs/feature_map.json)

Every feature entry defines an offline-safe, Mode-A-safe verification command with `order_send_count: 0` and `holdout_rows_analysed: 0`.

| Feature ID | Domain | Read-Only / Source Edits | Max Workers | Verification Target |
| --- | --- | --- | --- | --- |
| `quant_core_ssot` | `TradingWorkspace` quant core | `read_only: true` | `1` | `test_quant_ssot_core.py`, `test_holdout_and_tca_guards.py`, `test_quant_core_io_utils.py` |
| `architecture_gate` | `TradingWorkspace` architecture | `read_only: true` | `1` | `tooling/check_architecture.py --strict` (`ARCH-01..10`) |
| `opsec_and_skill_links` | `TradingWorkspace` OPSEC & skills | `read_only: true` | `1` | `test_layer1_opsec_guard.py` + `check_skill_links.py --review-triggers` |
| `cockpit_api_facade` | `Cockpit` | `read_only: true` | `1` | `test_l8_facade_sync.py` + `test_wave2_cockpit_and_treasury.py` |
| `naqex_cli_runner` | `naqex_cli` | `read_only: true` | `1` | `tooling/tests/test_check_architecture.py` (CLI + worktree + ARCH) |
| `quant_trading_lab` | `projects/quant-trading` | `read_only: true` | `1` | `projects/quant-trading` offline pytest via bundled/project venv |
| `trader_readonly_qa` | `projects/trader` | `read_only: true`, `allow_src_edits: false` | `1` | `projects/trader/scripts/check_paths.py` + `test_release_workflow.py` (0 `src/` edits) |
| `education_tutor_setup` | `education` | `read_only: true` | `1` | `education/check_setup.py` |
| `strategy_intel_bridge` | `strategy-intel` cleanroom | `read_only: true`, `writes_back: 0` | `1` | `naqex_cli.py auto intel-sync --offline --dry-run` (immutable 15 master leads) |

### Mode-A Safety Rules

- `pytest -n auto` is strictly forbidden in `feature_map.json` and automation scripts; use single-process (`max_workers: 1`) or `-n 2` maximum.
- Root `uv run` is strictly forbidden in `TradingWorkspace`; always invoke `.runtime/quant-audit-v24/Scripts/python.exe` (or [naqex_cli.py](../../../../tooling/naqex_cli.py)).
- `projects/trader` entries are strictly read-only QA (`allow_src_edits: false`, zero edits to `projects/trader/src/` or `foundation_v2/`).

## Pillar 2: Atomic Secret-Scrubbed Event Queue

Implementation: [event_queue.py](../../../../tooling/automation/event_queue.py)
Runtime artifact: `.runtime/automation/event_queue.jsonl`

- **Atomic writes:** Every append and prune acquires an in-process `RLock` plus an exclusive sidecar lockfile (`O_CREAT | O_EXCL` with bounded retry and stale-lock recovery), writes the updated JSONL to a same-directory temp file, calls `flush()` + `os.fsync()`, and commits via `os.replace()`.
- **Fail-closed OPSEC scrubbing:** Before serialization, every string value is scrubbed for:
  - Telegram bot tokens, Discord/Slack webhooks, generic credential URLs, Bearer headers, and `token=` / `api_key=` / `secret=` query parameters.
  - GitHub (`ghp_` / `github_pat_`), OpenAI (`sk-`), Google (`AIza`), and Postgres credential DSNs.
  - Environment variable values listed in `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ALERT_WEBHOOK_URL`, `NAQEX_DEADMAN_URL`.
  - Hardcoded local Windows user profile paths (replaced with `<USER_HOME>`) and raw private/CGNAT IPv4 literals (replaced with `<REDACTED_IP>`).
- **Schema per JSONL line:**

```json
{
  "schema_version": "naqex-automation-event-v1",
  "event_id": "evt-0123456789abcdef",
  "ts_utc": "2026-11-27T06:40:00Z",
  "event_type": "ratchet.evaluated",
  "source": "ratchet_engine",
  "severity": "info",
  "status": "pass",
  "summary": "All ratchet floors satisfied",
  "details": {},
  "order_send_count": 0
}
```

## Pillar 3: Monotonic Metric Ratchet

Implementation: [ratchet_engine.py](../../../../tooling/automation/ratchet_engine.py)

The ratchet persists high-water / low-water marks so code health cannot drift downward:

- **Higher-is-better floors:** `tests_passed` (`observed >= baseline`), plus optional `extra_floors`.
- **Lower-is-better ceilings:** `tests_failed`, `ruff_errors`, `ty_errors`, `arch_errors`, `arch_warnings`, plus optional `extra_ceilings` (`observed <= baseline`).
- **Hard zero invariants:** `opsec_leaks == 0`, `holdout_rows_analysed == 0`, `order_send_count == 0`.
- **Poisoned-input rejection (`-O` safe):** `bool`, `None`, `NaN`, `Inf`, and negative integer counts raise `ValueError` via explicit `if ...: raise` checks (zero bare `assert`).
- **Ratchet tightening:** Passing evaluations tighten floors upward (`max`) and ceilings downward (`min`). Failing evaluations preserve the stricter baseline unchanged and return structured `regressions`.

## Pillar 4: Hard 3-Attempt Circuit Breaker

Implementation: [ratchet_engine.py](../../../../tooling/automation/ratchet_engine.py)

```text
CLOSED (failures = 0)
  -- failure #1 --> CLOSED (failures = 1, retries_remaining = 2)
  -- failure #2 --> CLOSED (failures = 2, retries_remaining = 1)
  -- failure #3 --> CLOSED (failures = 3, retries_remaining = 0)
  -- failure #4 (or pre-flight check for attempt #4) --> CIRCUIT_OPEN_ESCALATE_OWNER (HARD TRIP)
```

- `DEFAULT_MAX_ATTEMPTS = 3`.
- Attempt #4 (4th consecutive failure, or calling `guard_attempt` / `check_attempt` once `consecutive_failures >= max_attempts`) transitions the target into `CIRCUIT_OPEN_ESCALATE_OWNER` (`tripped = True`, `escalate_owner = True`, `allowed = False`).
- Once open, the circuit **never self-resets**: autonomous `record_success()` raises `CircuitOpenError` until the owner explicitly calls `reset_circuit(target_id, owner_reason=...)`.
- Every check uses explicit `if ...: raise` so `python -O` and `python -OO` cannot strip protection.

## Pillar 5: Architecture Enforcement (`ARCH-01..10`)

Implementation: [check_architecture.py](../../../../tooling/check_architecture.py)

- `ARCH-08`: AST-safe ban on live broker order calls (`OrderSend`, `order_send`, `place_order`, `submit_order`, `MetaTrader5` imports) inside `tooling/automation/` and `tooling/ai-engines/experiments/`.
- `ARCH-09`: AST-safe ban on bare Python `assert` guards inside `tooling/automation/` and `tooling/ai-engines/quant_core/holdout_guard.py`.
- `ARCH-10`: Ban on hardcoded Windows user profile paths and raw IPv4 literals inside `tooling/automation/`.
- `tooling/workflows/` is excluded from all AST parsing checks because `run_workflow` scripts legitimately use top-level `await`.
