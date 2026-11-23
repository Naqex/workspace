# Pass 27 Report — Bound FTMO Demo Index Specs, Exact M1 Floating-Equity 5/6/7-Engine Audit & Phase-Based Prop Profile Architecture

- **Date:** `2026-11-23`
- **Protocol Commit:** `262d0e221e847065df531146b84fc584909a81e2` ([PASS27 Protocol](PASS27-DEMO-SPEC-M1-AUDIT-AND-PHASE-PROFILES-PROTOCOL-20261123.md))
- **Bound FTMO Demo Spec Snapshot:** `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\ftmo-demo-indices-spec-20261123\ftmo_indices_spec_snapshot.json` (`sha256 = 220b916e60a7...`, `server = FTMO-Demo`, `account_hash = 3215a01a09d1...`, `OrderSend = 0`)
- **Pass 27 Artifact (Cold Archive E:):** `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\pass27-m1-phase-audit-v2-20261123\pass27-result.json`
- **Holdout & Execution Invariants:** `holdout_rows = 0` (`< 2025-01-01T00:00:00Z`) · `OrderSend = 0` · `1,555 / 1,555` unit tests PASS · `6 / 6` `.mq5` exports `0` red flags (`InpDryRunLogOnly = true`)

---

## Executive Summary & Strategic Verdict

1. **`US100.cash` Bound on Live FTMO Free Trial Demo (`OrderSend = 0`) → Engine #4 & Engine #5 Upgraded to `FTMO_DEMO_SPEC_BOUND`:**
   - Exact FTMO-Demo contract spec: `trade_contract_size = 1.0`, `point = 0.01`, `tick_size = 0.01`, `tick_value = 0.01`, **`1 pt × 1.00 lot = $1.00 USD`** (exact 1:1 parity with backtest), `vol = 0.01 / 0.01 / 1000.0`, `stops_level = 0`, `margin_1lot = $517.05` (`2.0%` at `1:100` Standard), **`live spread p50 = p95 = 1.95 pts` (`n = 60` ticks)** — tighter than historical Dukascopy median (`2.88–3.41 pts`) and Stress slippage (`+4.00 pts`). *(Honest caveat: deal-level live fill slippage on `US100.cash` remains unmeasured because `OrderSend = 0`; Cash CFD `$0` commission verified live on `US500.cash` in `36f1535`.)*
   - Huge overnight swaps (`swap_long = 1076.28 / swap_short = -1677.49`) confirm why keeping all 5 core engines strictly `swap = 0` intraday (`15:55 ET` flat) is non-negotiable.
2. **Exact Minute-by-Minute M1 Floating-Equity Prague-Reset Audit (`2018–2024`, `0` Margin Failures on Both Swing `1:30/1:15` & Standard `1:100/1:50`):**
   - **`US100` Overlap Forensics (Engine #4 `n = 414` vs Engine #5 `n = 261`):** `94` overlap days (`36.0%` of E5), **`94 / 94` same direction (`0` opposing hedges)**, only **`4` double-SL days in 7 years (`4.3%`)**, producing **`+22.29R` combined** on overlap days (`+0.24R/day`). Because overlap days are high-conviction consensus days, cutting them via `CAP75` slightly lowered exact M1 Calmar (`1.03 → 0.94`) while trimming worst daily DD (`1.95% → 1.69%`).
   - **`PORT_5E_RAW` (Exact M1 Floating Equity):** **`+6.89%/yr`** (`A +7.67%, B +6.31%`), **`DailyDD = 1.95%`**, **`FloatPeakDD = 6.69%`**, **`Calmar = 1.03`**, `UW = 18.6m`, `MgnSw = 17.6% / Std = 5.3%`, `MgnFail = 0`.
   - **`PORT_7E_P1_TURBO` (`PORT_5E` + `FX_USD_BASKET` + `XAU_EXP_120`, all `swap = 0` & Demo-bound):** **`+7.70%/yr`** (`A +9.27%, B +6.52%`), **`DailyDD = 1.96%`**, **`FloatPeakDD = 7.38%`** (LOWER DD than 6E because Gold diversifies FX/Indices!), **`Calmar = 1.04`** (highest exact M1 floating Calmar!), `MgnSw = 22.6% / Std = 6.1%`, `MgnFail = 0`.
3. **Empirical Verdict on Phase-Based Prop Portfolio Profiles (`N = 2,000` Exact M1 Floating-Equity Bootstrap):**
   - Replacing approximate daily MAE sums with **exact minute-by-minute M1 floating equity** revealed huge true safety headroom: with automatic `AMBER (-3.5% → 0.65×)` and `RED (-6.0% → 0.40×)` drawdown throttling, **`Br1` collapses to `0.2%–0.3%` and `BrF` (Funded breach rate) collapses to `0.0%–0.1%` (`AvgTix = 1.00`)**!
   - **Recommended Sweet-Spot Architecture: `3` Clean Operational Profiles + `1` Automatic Equity Governor (NEVER `8–10` manual "market-regime" profiles):**
     - **Profile 1 (`CHALLENGE_SPRINT`, Phase 1 `+10%`):** Either **`B2_2REGIME_FAST_25X`** (`PORT_5E @ 2.5× P1`, `1.4× P2` → **`MedPass = 9.3m`, `Pay1 = 10.5m`, `12m = 47.1%`, `Br1 = 0.2%`, `CF12 = +$50` FTMO / `+$47` The5ers, `CF24 = +$471 / +$242`**) OR **`D_2PROF_P1_7E_2X_THEN_5E`** (turn ON `USD_BASKET + XAU_EXP_120` in P1 at `2.0×`, switch OFF in P2/Funded → **`24m = 73.8%` highest pass rate, `Br1 = 0.3%`, `BrF = 0.0%`, `MedPass = 10.6m`, `CF12 = +$21 / +$35`, `CF24 = +$451 / +$231`**).
     - **Profile 2 (`VERIFY_AND_FUNDED_CORE`, Phase 2 `+5%` & Funded):** Pure `PORT_5E` core (`1.25–1.4×` P2 → `1.0×` Funded), `BrF = 0.0%–0.1%`, **withdraw 100% profit per payout** (leaving a `2%` funded buffer reduced CF24 by `-$88` FTMO / `-$43` The5ers with `0.0%` extra survival!).
     - **Profile 3 (`PERSONAL_VAULT`, Exness/IC Swap-Free funded by Prop Payouts):** Houses overnight/swap-sensitive `TIER_2` alpha (`NEN006 +28.18R`, `IND026 +19.70R`, `XAU_EXP_120 +16.26R`) without prop daily DD caps or payout cushion resets.
     - **Empirical Surprise — Early Target Lock-In Hurt Speed Without Saving Breaches:** Stepping down at `+7.0%` (`E_GLIDEPATH_FAST_25X_5E`) slowed `MedPass` from `9.3m → 11.1m` (`+1.8m`) and dropped `CF12` from `+$50 → -$15` with `0.0%` reduction in `Br1` (`0.2% → 0.2%`), because at `+7.0%` equity sits `17%` above the `-10%` floor. Only trim sizing right near the finish line (`>= +9.2%`).
     - **Dual-Firm Multi-Account Ladder (Synchronized Real Market Timeline):**
       - **Parallel (`FTMO 10k + The5ers 5k`):** **`CF12 = +$97`**, **`CF24 = +$713` (`P>0 = 69.0%`)**, **`Med First Payout from EITHER firm = 10.5m`**, `P05 = -$207`.
       - **Self-Funded Ladder (Start ONLY `$39` The5ers 5k → launch FTMO 10k from profits):** **`Max Out-of-Pocket (95th pct) = $39`**, launches FTMO in `65.7%` of paths (`med = 11.1m`), `CF24 = +$254`.

---

## Track A — Exact M1 Minute-by-Minute Floating-Equity Audit (`Swing 10k`, `2018–2024`, Prague Reset)

| Portfolio | `7y Ann` (`A / B`) | `DailyDD` | `FloatPeakDD` | `Calmar` | `UW` | `MaxConc` | `Mgn Sw / Std` | `CapHit` | `MgnFail` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `PORT_3E_FROZEN` | `+5.09%` (`+6.30 / +4.18%`) | `1.53%` | `6.09%` | `0.84` | `19.9m` | `3` | `15.1% / 4.5%` | `0` | `0` |
| `PORT_4E` | `+5.99%` (`+6.99 / +5.24%`) | `1.60%` | `6.17%` | `0.97` | `18.8m` | `4` | `15.1% / 4.5%` | `0` | `0` |
| **`PORT_5E_RAW`** | **`+6.89%` (`+7.67 / +6.31%`)** | **`1.95%`** | **`6.69%`** | **`1.03`** | **`18.6m`** | `4` | `17.6% / 5.3%` | `0` | `0` |
| `PORT_5E_US100_CAP75` | `+6.60%` (`+7.52 / +5.91%`) | `1.69%` | `7.00%` | `0.94` | `18.8m` | `4` | `15.8% / 4.7%` | `81` | `0` |
| `PORT_5E_US100_CAP50` | `+6.32%` (`+7.38 / +5.52%`) | `1.53%` | `7.38%` | `0.86` | `18.8m` | `4` | `15.1% / 4.5%` | `81` | `0` |
| `PORT_5E_INVDD_A` | `+5.75%` (`+6.43 / +5.25%`) | `1.42%` | `5.98%` | `0.96` | `18.6m` | `4` | `14.0% / 4.2%` | `282` | `0` |
| `PORT_6E_SAT25` | `+6.85%` (`+8.03 / +5.96%`) | `1.77%` | `7.58%` | `0.90` | `14.9m` | `5` | `16.6% / 5.0%` | `81` | `0` |
| `PORT_6E_SAT50` | `+7.11%` (`+8.60 / +6.00%`) | `1.86%` | `8.36%` | `0.85` | `14.3m` | `5` | `18.3% / 5.5%` | `81` | `0` |
| **`PORT_7E_P1_TURBO`** | **`+7.70%` (`+9.27 / +6.52%`)** | **`1.96%`** | **`7.38%`** | **`1.04`** | `18.8m` | `6` | `22.6% / 6.1%` | `81` | `0` |

---

## Track B — Phase-Based Prop Profile Benchmark (`N = 2,000` Exact M1 Floating-Equity Bootstrap)

| Policy Architecture | Firm | Pass `3 / 6 / 9 / 12 / 24m` | `Br1` / `BrF` | `Tix` | `MedPass` / `Pay1` | `CF12` | `CF24` (`P>0`) | `OOP95` |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `A_FLAT_CORE5` (`1.0×` all) | FTMO 10k / 5ers 5k | `0.0 / 0.4 / 4.7 / 11.8 / 56.0%` | `0.8% / 0.4%` | `1.01` | `16.8m / 17.2m` | `-$135 / -$27` | `+$165 (49.7%) / +$100 (48.5%)` | `$168 / $39` |
| `B_2REGIME_PURE_SCALE_2X` | FTMO 10k / 5ers 5k | `1.6 / 12.4 / 27.4 / 41.2 / 72.6%` | `0.2% / 0.1%` | `1.00` | `11.0m / 12.1m` | `+$4 / +$28` | `+$433 (69.2%) / +$222 (68.3%)` | `$168 / $39` |
| **`B2_2REGIME_FAST_25X`** | **FTMO 10k / 5ers 5k** | **`3.7 / 19.9 / 35.5 / 47.1 / 72.5%`** | **`0.2% / 0.1%`** | **`1.00`** | **`9.3m / 10.5m`** | **`+$50 / +$47`** | **`+$471 (69.3%) / +$242 (68.4%)`** | **`$168 / $39`** |
| `C_2PROF_P1_6E_2X_THEN_5E` | FTMO 10k / 5ers 5k | `1.9 / 14.0 / 28.8 / 43.1 / 73.2%` | `0.2% / 0.0%` | `1.00` | `10.8m / 11.9m` | `+$11 / +$30` | `+$442 (69.3%) / +$227 (68.4%)` | `$168 / $39` |
| **`D_2PROF_P1_7E_2X_THEN_5E`** | **FTMO 10k / 5ers 5k** | **`2.6 / 15.2 / 29.8 / 44.4 / 73.8%`** | **`0.3% / 0.0%`** | **`1.00`** | **`10.6m / 11.5m`** | **`+$21 / +$35`** | **`+$451 (69.5%) / +$231 (68.4%)`** | **`$168 / $39`** |
| `E_GLIDEPATH_FAST_25X_5E` (`+7%` brake) | FTMO 10k / 5ers 5k | `0.8 / 9.3 / 24.4 / 39.1 / 70.7%` | `0.2% / 0.0%` | `1.00` | `11.1m / 12.5m` | `-$15 / +$19` | `+$402 (67.2%) / +$208 (66.2%)` | `$168 / $39` |
| `F_4STATE_7E_2X_TO_5E` (early brake) | FTMO 10k / 5ers 5k | `0.6 / 6.9 / 20.9 / 34.5 / 70.7%` | `0.3% / 0.0%` | `1.00` | `12.2m / 13.3m` | `-$46 / +$6` | `+$366 (66.5%) / +$190 (65.0%)` | `$168 / $39` |
| `G_4STATE_FUNDED_2PCT_BUF` (2% lock) | FTMO 10k / 5ers 5k | `0.6 / 6.9 / 20.9 / 34.5 / 70.7%` | `0.3% / 0.0%` | `1.00` | `12.2m / 13.3m` | `-$73 / -$7` | `+$278 (66.5%) / +$147 (63.2%)` | `$168 / $39` |

### Dual-Firm Multi-Account Architecture (Synchronized Real Market Timeline)

- **`H_PARALLEL` (`FTMO 10k + The5ers 5k` on `B2_2REGIME_FAST_25X`):** `CF12 = +$97.4`, **`CF24 = +$713.1` (`P>0 = 69.0%`)**, `P05 = -$207`, `OOP95 = $207`, `Either First Payout Med = 10.5m`.
- **`H_PARALLEL` (`FTMO 10k + The5ers 5k` on `D_2PROF_P1_7E_2X_THEN_5E`):** `CF12 = +$55.8`, **`CF24 = +$682.2` (`P>0 = 69.0%`)**, `P05 = -$207`, `OOP95 = $207`, `Either First Payout Med = 11.5m`.
- **`I_5ERS5K_FIRST_SELF_FUND_FTMO` (Spend ONLY `$39` on The5ers → self-fund FTMO 10k from payouts):** **`OOP95 = $39.0`**, launches FTMO in `65.7%` of paths (`med = 11.1m`), `CF24 = +$254.2` (`P>0 = 53.5%`, `P05 = -$88.6`).

---

## Track C — Clean White-Box `.mq5` Suite (`6 / 6` Zero Red Flags, `InpDryRunLogOnly = true`)

1. [Naqex_WB_TOKYO_BOX_USDJPY.mq5](../../tooling/ai-engines/exports/Naqex_WB_TOKYO_BOX_USDJPY.mq5) — Engine #1 (`USDJPY`, EU DST `18:00 Helsinki`)
2. [Naqex_WB_EXP080_USDJPY.mq5](../../tooling/ai-engines/exports/Naqex_WB_EXP080_USDJPY.mq5) — Engine #2 (`USDJPY`, Daily-Open Expansion)
3. [Naqex_WB_EXP080_VOLHIGH_GBPUSD.mq5](../../tooling/ai-engines/exports/Naqex_WB_EXP080_VOLHIGH_GBPUSD.mq5) — Engine #3 (`GBPUSD`, Vol-High Expansion)
4. [Naqex_WB_SESS_CONT_BRK40_US100.mq5](../../tooling/ai-engines/exports/Naqex_WB_SESS_CONT_BRK40_US100.mq5) — Engine #4 (`US100.cash`, upgraded to `TIER_1_FTMO_DEMO_SPEC_BOUND`)
5. [Naqex_WB_IDX_RS_US100_LEAD_1130.mq5](../../tooling/ai-engines/exports/Naqex_WB_IDX_RS_US100_LEAD_1130.mq5) — Engine #5 (`US100.cash` vs `US500.cash`, `InpMinRsDiffAtr = 0.25`, `TIER_1_FTMO_DEMO_SPEC_BOUND`)
6. [Naqex_WB_FX_USD_BASKET_12U_Z35.mq5](../../tooling/ai-engines/exports/Naqex_WB_FX_USD_BASKET_12U_Z35.mq5) — Satellite #6 (`G6 USD Basket`, `InpMinUsdBasketZ = 0.35`, `TIER_2_SATELLITE_DEMO_BOUND`)

## Next Gate Before Real Challenge Spend

1. Holdout `>= 2025-01-01` remains **strictly locked (`holdout_rows = 0`)** until user explicitly authorizes the one-shot **Holdout Unseal Gate** on frozen `PORT_5E` + `PORT_7E_P1_TURBO` (and optional The5ers Free Monthly Competition MT5 spec capture + Terms §11 custom-EA support confirmation email).
