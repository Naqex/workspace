# Pass 23 Report — Full Parallel Multi-Lane Execution (Data Seal · Nhịp 3 FTMO 2-Step Lifecycle · Engine #1 `.mq5` · Engine #4 Discovery)

- **Date:** `2026-11-23`
- **Protocol Commit:** `5eb0506089d12ffbd047a8eab1871cc618f4850c` ([PASS23 Protocol](PASS23-FULL-PARALLEL-DATA-DISCOVERY-LIFECYCLE-PROTOCOL-20261123.md))
- **Holdout Lock:** `holdout_rows = 0` (`< 2025-01-01T00:00:00Z`, `NATIVE_FTMO_HOLDOUT_LOCK.json` verified) · `OrderSend = 0`
- **Artifacts on E: Cold Archive:**
  - `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\pass23-lifecycle-20261123\pass23-lifecycle-result.json`
  - `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\pass23-lane-d-20261123-causal\pass23-lane-d-result.json`
  - `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\pass23-{xauusd,us100,ger40}-m1-20261123\development-m1\manifest.json`

## Executive Summary & Verdict

1. **Lane A (Data Sealing — `COMPLETE`):** Upgraded **`XAUUSD`** from Bid-only to **TRUE Native M1 Bid/Ask** (`2.48M` bars, median spread `0.234–0.397 USD/oz`, permanently resolving `PROVISIONAL_XAU`) and sealed **`US100`** (`2.36M` bars, median `2.88–3.41 pts`) and **`GER40`** (`2.29M` bars, median `1.84–2.62 pts`) into D: SSD Hot Cache (`433.0 MB` total across **8 assets**, ALL `native_Ask = true`, `holdout_rows = 0`).
2. **Lane B (Nhịp 3 FTMO 2-Step Lifecycle on Frozen 3-Engine Core — `NHIP3_PACE_INSUFFICIENT_KEEP_HOLDOUT_LOCKED`):**
   - `PORT3E_075_GBP075` has near-zero blowup risk (`24m Breach = 0.6%–0.8%`), **but** at `+5.07%–5.33%/yr`, single-attempt 2-Step Pass Rate is only **`4.7%–6.0%` at 12m** and **`37.6%–41.8%` at 24m** (`24m median cashflow = -1× fee`, `P>0 = 32.6%–36.6%`).
   - Scaling risk `1.50×` pushes `Boot24` to `64.7%–66.8%` (`Roll24 = 89.8%–93.2%`, 24m median cashflow `+$222 / +$718 / +$1,513`), **but** Peak DD rises to **`9.43%–9.70%`** (dangerously close to FTMO's `10%` static wall, lifting `Breach24` to `7.7%–8.4%`).
   - Under simultaneous **`+1.00 pip` double-slippage stress (`STRESS10`)**, the 3-engine core remains cleanly profitable (`+4.01%–4.27%/yr`, `Breach24 = 1.3%–1.9%`), proving durable underlying alpha.
3. **Lane C (Engine #1 `.mq5` Export & Full 3-EA Audit — `COMPLETE`):** Exported [Naqex_WB_TOKYO_BOX_USDJPY.mq5](../../tooling/ai-engines/exports/Naqex_WB_TOKYO_BOX_USDJPY.mq5) (exact Pass 6/7B Tokyo-box OCO + EU DST `18:00 Europe/Helsinki` hard flat). All **3** exported `.mq5` templates pass static red-flag audit (`0` red flags, `InpDryRunLogOnly = true`).
4. **Lane D (Engine #4 Discovery & Forensic Audit — `0/78 TIER_1 · CRITICAL LOOKAHEAD BUG CAUGHT & FIXED · XAUUSD PROVISIONAL RESOLVED`):**
   - **Critical G1 Audit Victory:** Caught and fixed an intraminute stop-fill lookahead bug in `sim_index_trade` (filling stop breakouts at bar `ask_open`/`bid_open` instead of `max(top, ask_open)` / `min(bot, bid_open)`), which had falsely inflated `US100` (`+42.97R`) and `GER40` (`+32.47R`). Fixed in both `pass23_xau_indices_discovery.py` and `whitebox_discovery.py` + locked with unit test `test_index_stop_breakout_never_fills_better_than_trigger`. FX core & `XAUUSD` were completely unaffected.
   - **Clean Causal Discovery (`m_total = 78`):** **`0 / 78 TIER_1`** (`GER40: 0/24` passed Cluster A; `US100`: `1` weak `TIER_2_PROVISIONAL` `+5.80R`, `q_all = 0.935`; `XAUUSD WB_EXP_80_NONE` failed Double Stress `-8.80R` & lowered 3E Calmar `0.83 → 0.73`).
   - **Provisional `XAUUSD` Leads Confirmed Real on TRUE Native Bid/Ask:**
     - `XAU_EXP_DAILY_OPEN_120` (`swap = 0`): confirmed real (`Base +16.26R`, `Stress +11.83R`, `Double +4.88R`, `p = 0.001`, ExclBothCrises `+11.33R`, `r3E = 0.092`), but lowers 3E Calmar (`0.83 → 0.78`) → stays **`TIER_2_PERSONAL_VAULT`**.
     - `NEN006 XAUUSD` (`Inside Bar + EMA200 D1`, full FTMO Swap 3×): confirmed real (`FTMO +15.66R`, `A +5.34 / B +10.32`, DropTop5 `+6.13R`, ExclBothCrises `+12.06R`, **`r3E = -0.052`**, Honest Exness Swap-Free **`+28.18R`**); merging at `0.50%` lifts return `+5.07% → +6.48%/yr` (`Boot24: 37.6% → 54.8%`, `Calmar 0.84`, `Peak DD 7.70%`), but FTMO swap `-16,286 USD/lot` (~44% drag) keeps it in **`TIER_2_PERSONAL_VAULT`** (top personal-account asset).

---

## Lane A — Sealed Native M1 Bid/Ask Datasets (`2018–2024`)

| Asset | Dukascopy ID | Minutes (`2018–2024`) | Median Spread | p90 Spread | Parquet Size | `native_Ask` | `holdout_rows` |
|---|---|---:|---:|---:|---:|:---:|---:|
| **`XAUUSD`** (Upgraded) | `xauusd` | `2,480,548` | `0.234–0.397 USD/oz` | `0.294–0.787 USD/oz` | `42.8 MB` | **True** | `0` |
| **`US100`** (New) | `usatechidxusd` | `2,358,750` | `2.881–3.406 pts` | `3.081–3.540 pts` | `57.2 MB` | **True** | `0` |
| **`GER40`** (New) | `deuidxeur` | `2,285,370` | `1.840–2.624 pts` | `3.892–7.302 pts` | `51.7 MB` | **True** | `0` |

Total D: SSD Hot Cache (`.runtime/hot-m1-cache/`): **`433.0 MB`** across **8 Native Bid/Ask assets** (`USDJPY`, `GBPUSD`, `EURUSD`, `GBPJPY`, `US500`, `XAUUSD`, `US100`, `GER40`).

---

## Lane B — Nhịp 3 FTMO 2-Step Lifecycle & 24m Solo-Operator Cashflow (`N = 2,000` Block Bootstrap)

*Declared FTMO fee schedule (`FTMO_PUBLIC_FEE_DECLARED`): Swing 10k = `$168`, Swing 25k = `$270`, Standard 50k = `$373`. Conservative breach-before-target ordering; 5-trading-day circular blocks; max 3 retries over 24m.*

### Swing 10k (`$168` fee)

| Portfolio | Ann % | Peak DD | Daily | Calmar | Roll 12m / 24m | Boot 12m / 24m | Breach 24m | 24m Med Net CF (`P>0`) | 0-Pay Cycles |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `SOLO_USDJPY_030` | `+2.93%` | `9.08%` | `0.30%` | `0.32` | `0.0% / 0.0%` | `2.0% / 18.6%` | `5.2%` | `-$168` (`15.1%`) | `67.6%` |
| `BASE_2E_USDJPY_075` | `+3.51%` | `5.45%` | `0.74%` | `0.64` | `0.0% / 0.0%` | `1.2% / 17.8%` | `0.8%` | `-$168` (`14.4%`) | `64.0%` |
| `PORT3E_INVDD_125` | `+4.23%` | `5.18%` | `1.21%` | `0.82` | `0.0% / 15.3%` | `0.8% / 23.0%` | `0.2%` | `-$168` (`18.5%`) | `64.5%` |
| **`PORT3E_075_GBP075`** | **`+5.07%`** | **`6.09%`** | **`1.53%`** | **`0.83`** | `4.2% / 33.9%` | `4.7% / 37.6%` | **`0.6%`** | `-$168` (`32.6%`) | `62.8%` |
| `PORT3E_075_GBP075_X125` | `+6.39%` | `7.77%` | `1.90%` | `0.82` | `20.8% / 71.2%` | `15.0% / 54.8%` | `2.8%` | `-$59` (`49.9%`) | `64.8%` |
| `PORT3E_075_GBP075_X150` | `+7.66%` | `9.43%` | `2.28%` | `0.81` | `25.0% / 89.8%` | `25.9% / 64.7%` | `7.7%` | `+$222` (`60.1%`) | `66.6%` |
| `PORT3E_075_GBP075_STRESS10` | `+4.01%` | `7.32%` | `1.47%` | `0.55` | `0.0% / 16.9%` | `3.0% / 26.0%` | `1.3%` | `-$168` (`22.1%`) | `66.5%` |

### Swing 25k (`$270` fee) & Standard 50k (`$373` fee) — Key Portfolios

| Account · Portfolio | Ann % | Peak DD | Calmar | Roll 12m / 24m | Boot 12m / 24m | Breach 24m | 24m Med Net CF (`P>0`) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `Swing 25k · PORT3E_075_GBP075` | `+5.30%` | `6.30%` | `0.84` | `6.9% / 37.3%` | `5.9% / 40.9%` | `0.7%` | `-$270` (`36.0%`) |
| `Swing 25k · PORT3E_075_GBP075_X125` | `+6.62%` | `8.05%` | `0.82` | `25.0% / 83.1%` | `16.2% / 56.8%` | `3.4%` | `+$115` (`52.3%`) |
| `Swing 25k · PORT3E_075_GBP075_X150` | `+7.98%` | `9.67%` | `0.82` | `26.4% / 93.2%` | `28.1% / 66.7%` | `8.2%` | `+$718` (`62.4%`) |
| `Std 50k · PORT3E_075_GBP075` | `+5.33%` | `6.46%` | `0.82` | `6.9% / 39.0%` | `6.0% / 41.8%` | `0.8%` | `-$373` (`36.6%`) |
| `Std 50k · PORT3E_075_GBP075_X125` | `+6.67%` | `8.13%` | `0.82` | `25.0% / 83.1%` | `16.8% / 57.2%` | `3.5%` | `+$295` (`53.1%`) |
| `Std 50k · PORT3E_075_GBP075_X150` | `+8.04%` | `9.70%` | `0.83` | `26.4% / 93.2%` | `28.6% / 66.8%` | `8.4%` | `+$1,513` (`62.8%`) |

---

## Lane C — Complete 3-Engine Clean White-Box `.mq5` Suite (`OrderSend = 0`)

| Exported `.mq5` File | Engine Role | Lines | Inputs | Red Flags | `InpDryRunLogOnly` |
|---|---|---:|---:|---:|:---:|
| [Naqex_WB_TOKYO_BOX_USDJPY.mq5](../../tooling/ai-engines/exports/Naqex_WB_TOKYO_BOX_USDJPY.mq5) | Engine #1 (`USDJPY` Tokyo-box OCO, 18h Helsinki) | `200` | `8` | `0` | `true` |
| [Naqex_WB_EXP080_USDJPY.mq5](../../tooling/ai-engines/exports/Naqex_WB_EXP080_USDJPY.mq5) | Engine #2 (`USDJPY` Daily-Open Expansion 0.80) | `160` | `11` | `0` | `true` |
| [Naqex_WB_EXP080_VOLHIGH_GBPUSD.mq5](../../tooling/ai-engines/exports/Naqex_WB_EXP080_VOLHIGH_GBPUSD.mq5) | Engine #3 (`GBPUSD` Expansion 0.80 + `VOL_HIGH`) | `166` | `12` | `0` | `true` |

---

## Lane D — Causal Discovery (`m_total = 78`) & True Native Bid/Ask `XAUUSD` Re-Audit

### D1. True Native Bid/Ask Re-Audit of Pass 14–16 `XAUUSD` Provisional Leads

| Lead (`XAUUSD`, `native_Ask = true`) | n | FTMO Stress R (A / B) | yr+ | Excl Both Crises | Drop Top5 | `r3E` | Honest Exness SF R | Final Tier |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **`XAU_EXP_DAILY_OPEN_120`** (`swap=0`) | `204` | `+11.83R` (`+4.73 / +7.10`) *(Base `+16.26R`)* | `5/7` | `+11.33R` | `-1.75R` *(Base `+2.37R`)* | `+0.092` | `+16.26R` | **`TIER_2_PERSONAL_VAULT`** *(removes `PROVISIONAL_XAU`)* |
| **`NEN006` Inside Bar + EMA200 D1** | `160` | `+15.66R` (`+5.34 / +10.32`) *(Swap `-$16,286/lot`)* | `5/7` | `+12.06R` | `+6.13R` | **`-0.052`** | **`+28.18R`** | **`TIER_2_PERSONAL_VAULT`** *(removes `PROVISIONAL_XAU`)* |
| **`IND026` Ichimoku Chikou D1 Long** | `43` | `+10.62R` (`+5.89 / +4.73`) *(Swap `-$31,798/lot`)* | `5/7` | `+9.91R` | `-3.90R` | `+0.015` | `+19.56R` | **`TIER_2_PERSONAL_VAULT`** *(removes `PROVISIONAL_XAU`)* |

### D2. Clean Causal White-Box Discovery (`m_total = 78`: `30 XAUUSD` + `24 US100` + `24 GER40`)

- **Passed Cluster A Gate (`n_A >= 60`, `Net_A > 0`, `PF_A >= 1.05`):** **`5 / 78`** (`0` `TIER_1`, `3` `TIER_2`, `2` `TIER_3`; `73 / 78` filtered out on Cluster A).
- **`GER40`:** `0 / 24` passed Cluster A under causal stop/limit execution.
- **`US100`:** `1` weak `TIER_2_PROVISIONAL` (`WB_EXP_65_VOL_LOW`: `n = 272`, `A +4.7R → B +1.1R`, `Tot +5.80R`, `q_all = 0.935`) → **NOT promoted**.
- **`XAUUSD`:** `WB_EXP_80_NONE` (`+9.79R`, `q_all = 0.078`) collapsed to `-8.80R` under Double Stress, scored `4/9` on 2D `trig × sl`, and degraded 3E Calmar `0.83 → 0.73` → **NOT promoted**.

### D3. 4-Engine Merge Sensitivity (Swing 10k)

- `PORT3E + XAU_EXP120 (0.50%)`: `+5.80%/yr`, Peak DD `7.41%`, `Calmar 0.78` (`Boot24 = 45.1%`, `Br24 = 0.8%`) — **Calmar declines (`0.83 → 0.78`), NOT promoted**.
- `PORT3E + XAU_NEN006 (0.50%)`: `+6.48%/yr` (`A +6.67% / B +6.34%`), Peak DD `7.70%`, Daily `1.55%`, **`Calmar 0.84`**, `Boot12 = 12.2%`, **`Boot24 = 54.8%`**, `Br24 = 1.2%` — improves return & pass rate without lowering Calmar, **but** carries `-$16,286/lot` FTMO swap drag and requires exact floating-equity intraday M1 swap/gap replay before any FTMO consideration.

## Next Strategic Direction (Post-Pass 23)

1. **Keep Holdout `>= 2025-01-01` LOCKED** — Nhịp 3 proved the 3-engine core is `TIER_2_PERSONAL_VAULT` (excellent survival `0.6%` breach, suitable for Personal Capital or Shadow Demo testing) but **too slow (`4.7%–6.0%` 12m pass rate)** to waste the single Holdout shot on FTMO Challenge yet.
2. **Shift Engine #4 discovery beyond single-day Open Expansion:** `WB_OPEN_EXPANSION` has now been exhaustively tested across all 8 Native Bid/Ask assets (succeeding on `USDJPY` + `GBPUSD VOL_HIGH` + weakly `XAUUSD`, failing on `US500`/`US100`/`GER40`/`EURUSD`/`GBPJPY`). Next discovery wave (Pass 24) should expand to **genuinely different white-box structural families** on the 8-asset Hot Cache (e.g., multi-day causal trend/breakout with `swap >= 0` or intraday volatility-contraction/compression breakouts, cross-session London→NY continuation, or structured external leads dropped into `D:\ANNAM\strategy-intel\inbox\`).
3. **Optional Immediate Parallel Action (Zero-Cost Value):** Run FTMO **Free Trial / Demo Shadow (`G5`)** on the complete 3-EA `.mq5` suite (`InpDryRunLogOnly = true` first → paper execution) to begin collecting real-broker spread/slippage parity data while Engine #4 discovery continues offline.
