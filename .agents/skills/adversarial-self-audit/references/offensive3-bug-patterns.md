# Field-Proven Red-Team Bug Patterns (Offensive #3 & Wave 4)

On-demand falsification catalog loaded from [adversarial-self-audit/SKILL.md](../SKILL.md). Every item below caught a real P0 or P1 defect during independent Naqex red-team audits and MUST be checked whenever touching matching code paths.

## 1. Zero-Gap External Feed Artifacts & Leader-Inclusive Blindness (`RT1 P0-01 / P1-01..03`)
- **Zero-gap D1 trap:** External Yahoo feeds (notably `UK100` / `^FTSE`, `16:30 UTC` close) exhibit `zero_gap_frac >= 0.90` (`99.66%` `open[t] == close[t-1]`). Pairing them with later-close M1-resampled indices (`GER40`, `US500`, `US100`) creates fake same-day lookahead alpha (e.g., `+0.824` collapsing to `-0.386` under a `+1` bar lag). Always enforce a strictly causal prefix `zero_gap_frac >= 0.90` check applying a `+1` bar lag to signals, rankings, and slot releases.
- **No whole-array or future-snapshot signal features:** Never use full-array `np.nanmedian(prices)` or current-year live broker swap snapshots inside historical signal generation (apply swap costs only during execution replay).
- **Leader-inclusive blindness enum:** Compute `blindness_tier` over the **union** of ALL participating symbols (target + leaders + pairs + peer-graph universe), strictly normalized into the canonical enum set with `0` garbled/concatenated labels.

## 2. PowerShell Coercion & Stale Kill-Switch ACK (`RT3 P1-01 / P1-02`)
- **Never trust PowerShell `[bool]` on strings:** In PowerShell, `[bool]"false"` evaluates to **`$true`**. Always parse JSON boolean fields via a strict helper (`-NativeBoolOnly` for `manual_halt_ack`; reject arbitrary strings or parse `"false"/"0"/"no"` strictly as `$false`).
- **Post-write ACK timestamp & flatten check:** Emergency kill-switch guards MUST record `flag_write_utc_ts` immediately before writing the halt flag, require `heartbeat.utc_ts >= flag_write_utc_ts` (rejecting stale pre-write `manual_halt_ack = true`), AND require `open_positions == 0` when `Action == FLATTEN_ALL` before returning exit `0`.

## 3. Windows `tzdata`-Free `ZoneInfo` & `NaN`/`bool` Fail-Open (`RT3 P1-03..05`, `RT4 P1-02`)
- **System Python on Windows often lacks `tzdata`:** Always wrap `ZoneInfo(...)` with a deterministic PEP-495 stdlib DST fallback verified at `0` mismatches against `ZoneInfo` across US/EU/NZ transitions (`fold = 0/1`), and smoke-test imports on system Windows Python without `tzdata`.
- **`bool` is an `int` subclass & `NaN` comparisons return `False`:** In Python, `isinstance(False, int)` is `True` and `float("nan") > 0.10` is `False` (silently passing gates!). Every numeric risk/gate/threshold validator MUST reject `isinstance(x, bool)` and `not math.isfinite(x)` fail-closed with `ValueError`, and fail closed when required receipt provenance hashes (e.g., `inputs.audit_csv_sha256`) are missing or blank.
- **Corrupt 1-line JSONL:** Never silently swallow a corrupted single-line decision blackbox JSONL as `[]` — raise `ValueError` fail-closed.

## 4. Preset/Receipt Single Source of Truth & Per-SKU `0.01`-Lot Replay (`RT4 P1-01 / P1-03 / P1-04`)
- **Zero preset-vs-optimizer drift:** Never patch exported `.set` files (e.g., `InpKillStaticDdPct = 8.00`) in a downstream stage while leaving the upstream optimizer default (`8.50`) unchanged. Assert byte-identical SHA-256 reconciliation (`PRESET_SHA256_DRIFT` fail-closed) across optimizer output, portfolio receipt, and disk `.set` presets.
- **No linear EV scaling across account sizes:** Linearly scaling `100K` per-trade EV down to `5K` or `10K` hides `0.01`-lot floor drops (up to `+12.7%` overstatement on `5K`). Always replay Funded `1.0x` Law-15 metrics directly at each SKU's actual capital and leverage.
- **Provisional unmeasured broker aliases:** Any preset referencing unmeasured broker symbol aliases (e.g., The5ers `.cash` placeholders under `TERMS_VERIFIED_EXECUTION_UNMEASURED`) MUST carry explicit header warnings and metadata blocking non-DryRun use until real MarketWatch specs are captured.

## 5. LLM Retrospective Training-Data Contamination (`Wave 4 Audit`)
- Modern LLMs have seen historical news through `2025–2026`. Never feed un-anonymized historical dates or named shocks (`2024-08-05 BoJ`, `SVB`, `COVID`) into an LLM to claim backtest alpha improvement.
- Anonymize dates, institutions, and tickers strictly for structural JSON, latency, cost, and degrade-on-`429` tests; measure real trading value exclusively via SHA-256 stamped **Prospective Shadow** forward logs (`>= 30` live calendar days).
