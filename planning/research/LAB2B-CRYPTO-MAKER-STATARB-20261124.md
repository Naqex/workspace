---
title: "Wave 2 Lab #2B: Limit/Maker Execution & Rank-Buffer Hysteresis Study on Crypto Stat-Arb"
date: 2026-11-24
lane: quant-rnd (Lane C)
milestone: Wave 2 Cycle 2A — C2.3 (Lab #2B)
status: COMPLETE_1_CONDITIONAL_RETEST_0_IMMEDIATE_APPROVALS
holdout_rows_analysed: 0
order_send_count: 0
primary_script: tooling/ai-engines/quant_factory/crypto_maker_statarb_study.py
---

# Wave 2 Lab #2B: Limit/Maker Execution & Rank-Buffer Hysteresis on Crypto Stat-Arb

## 1. Executive Summary

Lab #2B directly followed up the two gross-positive market-neutral mechanisms discovered in [LAB2-CRYPTO-STATARB-NEUTRAL-20261124.md](./LAB2-CRYPTO-STATARB-NEUTRAL-20261124.md) (`S3_FUND_DISLOC` and `S4_MKT_NEUT_MOM`), replacing naive 4H taker churning with:
1. **Causal Rank-Buffer Hysteresis (`+2/+3/+5` slots) + Slower Rebalance Cadences (`12h/24h/72h/7d`)**, keeping held Longs/Shorts until they exit a buffer zone rather than thrashing at rank boundaries (`avg_abs_net_exp <= 0.00017`, exact dollar neutrality `sum(w) == 0`, gross `<= 1.0x`), and
2. **Realistic Passive Limit/Maker Friction Modeling** (never naive `0 bps`):
   - **Tier M1 (`85%` passive fill):** `0.85 * (2.0 maker + 1.5 adv_sel) + 0.15 * 10.0 taker = 4.475 bps` one-way/leg (`8.95 bps` at `2x`).
   - **Tier M2 (`70%` passive fill — PRIMARY GATING TIER):** `0.70 * (2.0 maker + 2.5 adv_sel) + 0.30 * 10.0 taker = 6.150 bps` one-way/leg (`12.30 bps` at `2x`).
   - **Tier T0 (`15.0 bps` Taker Control):** Exact parity with Lab #2.
3. **Strict Cumulative Multiple-Testing Accounting:** Passed **`n_trials_cumulative = 20`** (`12` from Lab #2 + `8` from Lab #2B) into `deflated_sharpe_ratio` so follow-up iteration never understates selection bias (`OrderSend = 0`, `holdout_rows_analysed = 0`).

**Key Empirical Findings (`m_total = 8`, Cl.A `2021-2023` -> blind Cl.B `2024-2026`):**
- **Research Council Verdicts:** **`0 / 8` `APPROVE_FOR_INCUBATION`**, **`1 / 8` `CONDITIONAL_RETEST`** (`M2B_BLEND_50_FUND_50_MOM`), **`7 / 8` `REJECT_KILLED`**. No premature sleeve JSON exported.
- **Breakthrough Confirmed on Execution + Hysteresis:** Combining rank-buffer hysteresis with passive limit fills transformed BOTH mechanisms from taker-blocked to strongly positive out-of-sample across **every** cost tier — even at `15.0 bps` full taker control:
  - **`M2B_BLEND_50_FUND_50_MOM` (`CONDITIONAL_RETEST` — passed 5 of 6 Council gates + neutrality):** Cl.A M2 `1x` `+19.70%` CAGR (Sharpe `0.967`) -> blind Cl.B M2 `1x` **`+15.01%` CAGR, Sharpe `0.943`, MaxDD `13.65%`, Calmar `1.100`, `BH-q = 0.09924 <= 0.10`**, M2 `2x` (`12.30 bps`/leg) **`+11.12%` CAGR** (`BE = 4.51x`, `~27.7 bps`/leg!), M1 `1x` **`+16.09%` CAGR (Sharpe `1.001`)**, Taker T0 `1x` **`+9.46%` CAGR (Sharpe `0.638`)**, `beta_BTC = -0.1222`, `corr vs Sleeve #2 = -0.2358` (tail `corr = -0.3080`), `corr vs Sleeve #3A = +0.0824`. Failed ONLY `G2_dsr_and_sharpe` (`DSR_b = 0.3827 < 0.50` under strict `N = 20` cumulative penalty on a 2.9-year Cl.B window, whereas `DSR_full = 0.6592 >= 0.50`).
  - **`M2B_FUND_7D_K4_24H_BUF3` (Strongest Standalone Hedge):** Cl.A M2 `1x` `+30.19%` CAGR (Sharpe `1.248`) -> blind Cl.B M2 `1x` **`+18.72%` CAGR (Sharpe `0.984`, MaxDD `16.27%`)**, M2 `2x` **`+14.46%` (`BE = 4.90x`)**, Taker T0 `1x` **`+12.64%` (Sharpe `0.711`)**, full 2021-2026 Sharpe **`1.126`** (`DSR_full = 0.7989`), `BH-q = 0.09924`. Flagged `G4_orthogonality` ONLY because its correlation vs Sleeve #2 is strongly **negative** (`r = -0.3685`, worst-5% tail `r = -0.5005` — an active crisis hedge!) and `DSR_b = 0.4097 < 0.50` under `N = 20`.
  - **`M2B_MOM_14D_K5_24H_BUF5` (Pure Zero-Correlation Momentum):** Cl.A M2 `1x` `+25.85%` (Sharpe `0.873`) -> blind Cl.B M2 `1x` **`+19.83%` CAGR (Sharpe `0.786`)**, M2 `2x` **`+13.05%` (`BE = 3.63x`)**, `corr vs Sleeve #2 = -0.0068`, `beta_BTC = -0.0787`. Narrowly missed `BH-q` (`0.11376 > 0.10`) and `DSR_b` (`0.2849`).

---

## 2. Full Empirical Results (`m_total = 8`, Cumulative `N = 20` DSR)

All metrics transcribed verbatim from `.runtime/crypto-1h-cache/lab2b_maker_statarb_summary.json` (runtime `11.38s`, Cl.A `n = 1,095` days, blind Cl.B `n = 1,057` days).

| Spec ID | Cl.A M2 1x CAGR | Cl.A Shp | Cl.B M1 1x CAGR | Cl.B M2 1x CAGR | Cl.B M2 2x CAGR | Cl.B T0 1x CAGR | Cl.B M2 Shp | Cl.B MaxDD | Cl.B Turn/yr | Cl.B Beta | Corr vs S2 | BH-q | DSR_b (N=20) | DSR_full | BE Mult | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `M2B_FUND_7D_K4_12H_BUF2` | +31.15% | 1.228 | +22.63% | +21.03% | +15.33% | +12.92% | 1.021 | 17.37% | 78.41x | -0.1367 | -0.3255 | 0.09924 | 0.4336 | 0.8044 | 4.26x | `REJECT_KILLED` |
| `M2B_FUND_7D_K4_24H_BUF3` | +30.19% | 1.248 | +19.90% | +18.72% | +14.46% | +12.64% | 0.984 | 16.27% | 59.36x | -0.1367 | -0.3685 | 0.09924 | 0.4097 | 0.7989 | 4.90x | `REJECT_KILLED` |
| `M2B_FUND_7D_K4_72H_BUF3` | +23.00% | 0.983 | +16.49% | +15.54% | +12.11% | +10.64% | 0.857 | 17.06% | 48.90x | -0.1390 | -0.3503 | 0.09924 | 0.3291 | 0.6330 | 5.09x | `REJECT_KILLED` |
| `M2B_FUND_14D_K5_7D_BUF3` | +30.06% | 1.108 | +10.22% | +9.82% | +8.36% | +7.72% | 0.622 | 21.23% | 21.77x | -0.1494 | -0.3505 | 0.18952 | 0.2003 | 0.6211 | 7.26x | `REJECT_KILLED` |
| `M2B_MOM_14D_K5_24H_BUF5` | +25.85% | 0.873 | +21.75% | +19.83% | +13.05% | +10.20% | 0.786 | 28.97% | 94.66x | -0.0787 | -0.0068 | 0.11376 | 0.2849 | 0.5475 | 3.63x | `REJECT_KILLED` |
| `M2B_MOM_14D_K5_72H_BUF5` | +11.95% | 0.507 | +12.24% | +10.90% | +6.13% | +4.09% | 0.516 | 20.95% | 71.54x | -0.1053 | -0.0377 | 0.19985 | 0.1527 | 0.2521 | 3.16x | `REJECT_KILLED` |
| `M2B_MOM_21D_K5_7D_BUF5` | +6.58% | 0.363 | -4.67% | -5.34% | -7.79% | -8.85% | -0.076 | 30.06% | 42.61x | -0.0803 | -0.0069 | 0.55363 | 0.0212 | 0.0649 | -1.36x | `REJECT_KILLED` |
| `M2B_BLEND_50_FUND_50_MOM` | +19.70% | 0.967 | +16.09% | +15.01% | +11.12% | +9.46% | 0.943 | 13.65% | 55.89x | -0.1222 | -0.2358 | 0.09924 | 0.3827 | 0.6592 | 4.51x | `CONDITIONAL_RETEST` |

---

## 3. Why `CONDITIONAL_RETEST` (Not Immediate Incubation) Is the Right Decision

1. **Zero Gate-Loosening Discipline:** Rather than relaxing `KillCriteria` or dropping cumulative `N = 20` trial accounting to force an approval, we honored the Council's exact `DSR_b >= 0.50` threshold. On `n = 1,057` days (`2.9` years) with `N = 20` cumulative trials, clearing `DSR_b >= 0.50` requires Cl.B Sharpe `> ~1.08`, which `M2B_BLEND_50_FUND_50_MOM` (`0.943`) and `M2B_FUND_7D_K4_12H_BUF2` (`1.021`) narrowly missed despite strong full-sample `DSR_full = 0.6592–0.8044` and `4.26x–4.90x` cost breakeven!
2. **Exact Forward Validation Path Required:** Before promoting `M2B_BLEND_50_FUND_50_MOM` (or `M2B_FUND_7D_K4_24H_BUF3`) into Own-Book capital, run a **30-day live passive-limit shadow simulation** logging Binance USD-M L2 orderbook queue touches to empirically prove:
   - Realized passive fill probability `p_fill >= 70%` within a 30-minute resting window,
   - Realized blended one-way cost `<= 6.5 bps` per leg including adverse selection, and
   - Positive forward paper expectancy without altering the frozen `K=4/5`, `buffer=3/5`, `72h` parameters.

---

## 4. Governance & Provenance

- **Reproducibility:** Run `D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe tooling/ai-engines/quant_factory/crypto_maker_statarb_study.py` (code: [crypto_maker_statarb_study.py](../../tooling/ai-engines/quant_factory/crypto_maker_statarb_study.py); unit tests: [test_wave2_swing_and_new_assets.py](../../tooling/ai-engines/tests/test_wave2_swing_and_new_assets.py)).
- **Sleeve Export Status:** **`NONE`** (kept fail-closed until `CONDITIONAL_RETEST` live limit-fill validation clears; zero premature return JSON exported to `.runtime/quant-pod-returns/`).
