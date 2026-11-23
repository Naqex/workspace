# Pass 27 Pre-Registered Protocol — Bound FTMO Demo Index Specs, Exact M1 Floating-Equity 5/6/7-Engine Audit & Phase-Based Prop Profile Architecture

- **Date:** `2026-11-23`
- **Holdout Lock:** `holdout_rows = 0` (`< 2025-01-01T00:00:00Z`, `LOCK_SHA = e7523f...`)
- **Execution Safety:** `OrderSend = 0` across all broker probes, M1 replays, and `.mq5` exports (`InpDryRunLogOnly = true`)
- **Bound FTMO Read-Only Spec Artifact:** `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\ftmo-demo-indices-spec-20261123\ftmo_indices_spec_snapshot.json` (`sha256 = 220b916e60a7...`, `server = FTMO-Demo`, `account_hash = 3215a01a09d1...`, `OrderSend = 0`)

---

## 1. Bound FTMO Demo Contract Verification (Completed Read-Only)

| Symbol | Actual Symbol | Contract Size | `1 pt × 1 lot` (USD) | Vol `min/step/max` | Margin `1 lot` (1:100 Std) | Stops Level | Live Spread `p50 / p95` (`n=60`) | Status Change |
|---|---|---:|---:|---|---:|---:|---:|---|
| `US100.cash` | `US100.cash` | `1.0` | `$1.00` | `0.01 / 0.01 / 1000` | `$517.05` (`2.0%`) | `0` | `1.95 / 1.95 pts` | **Engine #4 & #5 → `FTMO_DEMO_SPEC_BOUND`** (live deal slippage still `OrderSend=0`, covered by `+4.0 / +6.0 pt` Stress/Double) |
| `GER40.cash` | `GER40.cash` | `1.0` | `$1.09` (`EUR`) | `0.01 / 0.01 / 1000` | `$545.96` (`2.0%`) | `0` | `1.23 / 1.23 pts` | Bound for future EU index research |
| `BTCUSD` | `BTCUSD` | `1.0` | `$1.00` | `0.01 / 0.01 / 5.0` | `$18,378.20` (`30%`) | `0` | `1.00 / 2.57 USD` | Live FTMO spread tight vs historical Dukascopy (`67–120 USD`); high margin (`$183.78 / 0.01 lot`) |
| `US500.cash` | `US500.cash` | `1.0` | `$1.00` | `0.01 / 0.01 / 1000` | `$141.64` (`2.0%`) | `0` | `0.60 / 0.60 pts` | Matches `36f1535` parity |

---

## 2. Track A — Exact M1 Minute-by-Minute Floating-Equity & Prague-Reset Portfolio Audit (`2018–2024`)

Every engine trade is replayed minute-by-minute on sealed Native M1 Bid/Ask arrays (`START..STOP`, `holdout_rows = 0`) using exact `combined_marks` + Prague `00:00` daily anchor (`pass11_portfolio` / `pass7b_usdjpy_equity.EquityMetrics`), checking BOTH Standard (`1:100` FX / `1:50` Index) and conservative Swing (`1:30` FX / `1:15` Index) margin ceilings:

1. **Core 5 Engines (`PORT_5E`):**
   - E1: `USDJPY_TOKYO_BOX` (frozen Pass 7B `Stress_05`)
   - E2: `USDJPY_EXP_80` (Pass 17 `Stress_05`)
   - E3: `GBPUSD_EXP_80_VH` (Pass 22 `Stress_05`)
   - E4: `US100_SESS_CONT_BRK_40` (Pass 24 `Stress +4.0 pts`, now `FTMO_DEMO_SPEC_BOUND`)
   - E5: `US100_RS_LEAD_1130` (Pass 26 `Stress +4.0 pts`, now `FTMO_DEMO_SPEC_BOUND`)
2. **Satellites (All `swap = 0` intraday, Native M1 Bid/Ask):**
   - S6: `FX_USD_BASKET_12U_Z35` (Pass 26, 100% bound FTMO Demo FX specs)
   - S7: `XAU_EXP_DAILY_OPEN_120` (Pass 23 re-verified on TRUE Native M1 Bid/Ask XAUUSD, `swap = 0`)
3. **Portfolio Variants Audited on Exact M1 Floating Equity:**
   - `PORT_3E_FROZEN` (baseline)
   - `PORT_4E` (`E1..E4`)
   - `PORT_5E_RAW` (`E1..E5`, `US100` `0.50%` each)
   - `PORT_5E_US100_CAP75` (`E1..E5`, causal overlap cap: if E4 and E5 trigger same-day same-direction on `US100`, second trade capped at `0.25%` so combined `US100` risk `<= 0.75%` base / `<= 1.50%` at `2x`, or `CAP50` strictly `<= 0.50%` base / `<= 1.00%` at `2x`!)
   - `PORT_5E_INVDD_A` (Cluster-A-only inverse-DD weights evaluated blind on Cluster B)
   - `PORT_6E_SAT25` (`PORT_5E` + `S6` at `0.25%`)
   - `PORT_6E_SAT50` (`PORT_5E` + `S6` at `0.50%`)
   - `PORT_7E_P1_TURBO` (`PORT_5E` + `S6 @ 0.50%` + `S7 @ 0.50%`)
4. **US100 Overlap Forensics:** exact count of overlap days, same-side vs opposite-side counts, worst single-day Prague floating loss on overlap days, and impact on Calmar / Peak Floating DD / Longest Underwater.

---

## 3. Track B — Empirical Phase-Based Prop Profile Architecture Benchmark (`N = 2,000` Block Bootstrap, `SEED = 20261123`)

Using the exact M1 floating-equity daily ledgers (`net_usd`, `worst_prague_intraday_dd_usd`, `traded_flag`) across **FTMO Swing 10k (`$168`, `80%`, `4` min days)** and **The5ers High Stakes 5k (`$39`, `80%`, `3` profitable days `>= +0.5%`, `10%/20%` Hub Credit + `70%` refund)**, benchmark **8 Phase-Based Profile Architectures**:

1. `A_FLAT_CORE5`: Flat `1.0x` on `PORT_5E` across all phases (baseline).
2. `B_2REGIME_PURE_SCALE`: Pure multiplier scaling on `PORT_5E` (`2.0x` P1 → `1.25x` P2 → `1.0x` Funded + basic DD throttle).
3. `C_2PROFILE_P1_6E_THEN_5E`: **2-Profile Strategy Switch** — P1 activates Satellite S6 (`PORT_6E_SAT50 @ 1.8x`), then switches S6 OFF in P2 & Funded (pure `PORT_5E`).
4. `D_2PROFILE_P1_7E_THEN_5E`: **2-Profile Turbo Switch** — P1 activates Satellites S6 + S7 (`PORT_7E_P1_TURBO @ 1.5x`), then switches BOTH OFF in P2 & Funded (pure `PORT_5E`).
5. `E_GLIDEPATH_LOCKIN`: **Target Lock-In Glidepath** on `PORT_5E` — P1 runs `2.0x`, steps down to `1.0x` once `>= +7.0%` and `0.5x` once `>= +8.5%`; P2 runs `1.25x`, steps down to `0.6x` once `>= +3.2%`.
6. `F_4STATE_MACHINE`: **Full 4-State Equity Machine** (`GREEN / LOCK-IN / AMBER / RED` + `Funded Survival 0..+3% = 0.80x` → `Funded Harvest = 1.0x`) running `PORT_6E_SAT50` in P1-`GREEN`, automatically turning OFF satellites in `AMBER` (`-3.5%..-6.0%`), `RED` (`< -6.0%`), `LOCK-IN`, `P2`, and `FUNDED`.
7. `G_4STATE_FUNDED_2PCT_BUFFER`: Same as `F_4STATE_MACHINE`, except after the first payout (which secures the fee refund), Funded keeps a `2.0%` cushion inside the account (withdrawing only profits above `+2.0%`) to quantify Funded breach reduction vs cashflow delay.
8. `H_DUAL_FIRM_PARALLEL_LADDER`: Synchronized real-market parallel execution of **The5ers High Stakes 5k (`$39`) + FTMO Swing 10k (`$168`)** using `F_4STATE_MACHINE` on identical bootstrapped market paths (honestly preserving cross-firm correlation!), measuring combined 12m/24m net cashflow, P(profitable), worst 5th-percentile loss, and time-to-first-payout.

---

## 4. Track C — White-Box `.mq5` Exports & Regression Gate

- Export `Naqex_WB_IDX_RS_US100_LEAD_1130.mq5` (Engine #5) and `Naqex_WB_FX_USD_BASKET_12U_Z35.mq5` (Satellite #6) into `tooling/ai-engines/exports/` with `InpDryRunLogOnly = true` and `0` static red flags.
- Add `tooling/ai-engines/tests/test_pass27_suite.py` and run full `unittest discover` + `check_workspace.py`.
