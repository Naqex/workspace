---
title: "Wave 2 Lab #3B: 10 Brand-New Unexplored FTMO Instruments Research (Dev < 2025-01-01)"
date: 2026-11-24
lane: quant-rnd (Lane C)
milestone: Wave 2 Cycle 2A — C2.2 (Lab #3B)
status: COMPLETE_ZERO_SURVIVORS_RETAINED
holdout_rows_analysed: 0
order_send_count: 0
primary_script: tooling/ai-engines/quant_factory/new_assets_10_dev_lab.py
---

# Wave 2 Lab #3B: 10 Brand-New Unexplored FTMO Instruments (Dev `< 2025-01-01`)

## 1. Executive Summary

Lab #3B expanded Development research (`< 2025-01-01` strictly sealed; `holdout_rows_analysed = 0`, `OrderSend = 0`, `0` API keys) across **10 brand-new unexplored FTMO instruments** (`USOIL.cash`, `UKOIL.cash`, `XAGUSD`, `USDCHF`, `NZDUSD`, `EURCHF`, `US30.cash`, `UK100.cash`, `JP225.cash`, `AUDJPY`), caching public Yahoo Finance v8 D1 OHLC strictly `< 2025-01-01` under `.runtime/new-assets-10-cache/` (`10/10` loaded, `0` skipped, `max_date_analysed = 2024-12-31`) and mapping every instrument to its exact live FTMO Swing swap & rollover specification from [FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json](./FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json).

Across **`m_total = 9`** pre-registered specs spanning **3 orthogonal families** evaluated on **Cluster A (`2015-01-01..2021-12-31`, `n = 1,827` days) -> blind Cluster B (`2022-01-01..2024-12-31`, `n = 782` days)** through [research_council.py](../../tooling/ai-engines/quant_factory/research_council.py) with `|r| < 0.15` vs `PORT_7E` and FTMO DD safety (`< 10%`):

- **Approved for Incubation:** **`0 / 9`** (all 9 specs received `REJECT_KILLED`; zero sleeve JSON exported).
- **Decisive Structural Finding (Catastrophic CFD Overnight Swap Burden on Commodities & Global Indices):**
  - Shorting Crude Oil (`USOIL.cash -66.11`, `UKOIL.cash -233.25`), holding Silver (`XAGUSD -11.86`), and holding Global Equity Indices (`US30.cash -391.97`, `UK100.cash -260.59`, `JP225.cash -841.60`) overnight on FTMO CFDs generated **`-8.60%` to `-30.14%` pure cumulative swap drag over just 3 years (Cluster B 2022–2024)**!
  - `N10_F3_COMM_VS_IDX_ROTATION` actually generated **`+17.75%` positive gross price PnL** in blind Cluster B (`corr = +0.0457` vs `PORT_7E`), yet **`-13.54%` negative swap drag** wiped out 76% of its gross edge (`+0.52%` net CAGR, `Sharpe 0.102`).
  - `N10_F1_TSMOM_60D_ALL10` suffered **`-30.14%` cumulative swap drag** (`-18.43%` net CAGR); even Long-Only `N10_F1_EMA_20_60_LO_COMM_IDX` bled **`-21.83%` swap drag** (`-8.46%` net CAGR).
  - Restricting strictly to positive-swap FX + long oil (`N10_F2_POSCARRY_DON20_FX_OIL`, with point-in-time positive oil roll conservatively capped at `0.0` so we never hallucinate `+25%/yr` Brent backwardation) eliminated swap bleed (`+1.68%` FX carry) yet delivered only `+1.11%` Cl.B CAGR (`Sharpe 0.192`, `MaxDD 16.84%`).
- **Strategic Portfolio Conclusion:** Do **NOT** trade multi-day swing strategies on FTMO Energy, Silver, or Global Index CFDs! The underlying cross-asset momentum/rotation economics (`+17.75%` gross in 2022–2024) are real, but belong exclusively in **zero-swap ETFs (IBKR Own Book Sleeves #3B / #4)** or **exchange-cleared CME Micro Futures**, NOT swap-bearing retail CFDs.

---

## 2. 10-Asset Universe & Real FTMO Swap Mapping

| Asset ID | Public Ticker | FTMO Symbol | Class | Swap Long (pts) | Swap Short (pts) | 3x Roll Day | 1x Cost (bps) | Anti-Fake-Swap Cap |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | --- |
| `USOIL` | `CL=F` | `USOIL.cash` | COMMODITY | +12.47* | -66.11 | Fri (5) | 3.5 | *Pos roll capped `0.0`; full neg charged |
| `UKOIL` | `BZ=F` | `UKOIL.cash` | COMMODITY | +50.76* | -233.25 | Fri (5) | 4.0 | *Pos roll capped `0.0`; full neg charged |
| `XAGUSD` | `SI=F` | `XAGUSD` | METAL | -11.86 | -1.92 | Wed (3) | 4.5 | Exact triple-Wed negative swap |
| `USDCHF` | `USDCHF=X` | `USDCHF` | FX | +1.34 | -14.93 | Wed (3) | 1.8 | Exact + zero-pos-swap floor |
| `NZDUSD` | `NZDUSD=X` | `NZDUSD` | FX | -4.31 | -0.17 | Wed (3) | 2.0 | Exact triple-Wed negative swap |
| `EURCHF` | `EURCHF=X` | `EURCHF` | FX | +1.83 | -12.20 | Wed (3) | 2.2 | Exact + zero-pos-swap floor |
| `US30` | `^DJI` | `US30.cash` | INDEX | -391.97 | -760.67 | Fri (5) | 1.8 | Exact triple-Fri negative swap |
| `UK100` | `^FTSE` | `UK100.cash` | INDEX | -260.59 | +8.59* | Fri (5) | 2.0 | *Pos short capped `0.0`; full neg charged |
| `JP225` | `^N225` | `JP225.cash` | INDEX | -841.60 | -346.54 | Fri (5) | 2.5 | Exact triple-Fri negative swap |
| `AUDJPY` | `AUDJPY=X` | `AUDJPY` | FX | +4.50 | -14.78 | Wed (3) | 2.4 | Exact + zero-pos-swap floor |

---

## 3. Full Empirical Results (`m_total = 9`, All Killed Retained Honestly)

All metrics transcribed verbatim from `.runtime/new-assets-10-cache/lab3b_new10_assets_summary.json` (runtime `4.78s`, Cl.A `2015-2021` `n = 1,827` days, blind Cl.B `2022-2024` `n = 782` days).

| Spec ID | Cl.A 1x CAGR | Cl.A Shp | Cl.B 1x CAGR | Cl.B 2x CAGR | Cl.B Shp | Cl.B MaxDD | Cl.B Price PnL | Cl.B Swap PnL | Cl.B 1x Cost | Corr vs P7E | BH-q | DSR_b | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `N10_F1_TSMOM_60D_ALL10` | -12.21% | -1.578 | -18.43% | -19.14% | -2.779 | 47.13% | -29.54% | -30.14% | 2.71% | +0.0366 | 1.0000 | 0.0000 | `REJECT_KILLED` |
| `N10_F1_EMA_20_60_LO_COMM_IDX` | -8.33% | -0.722 | -8.46% | -8.85% | -0.785 | 30.96% | -2.53% | -21.83% | 1.34% | +0.0335 | 1.0000 | 0.0016 | `REJECT_KILLED` |
| `N10_F1_TSMOM_DUAL_FX4` | -4.25% | -0.609 | -7.31% | -8.07% | -1.052 | 23.83% | -13.67% | -6.56% | 2.56% | +0.0274 | 1.0000 | 0.0004 | `REJECT_KILLED` |
| `N10_F2_POSCARRY_DON20_FX_OIL` | +1.20% | 0.191 | +1.11% | +0.78% | 0.192 | 16.84% | +3.50% | +1.68% | 1.00% | +0.0163 | 1.0000 | 0.1187 | `REJECT_KILLED` |
| `N10_F2_POSCARRY_EMA10_40_FX3` | -2.02% | -0.344 | -0.21% | -0.50% | -0.011 | 12.94% | -1.67% | +2.39% | 0.91% | +0.0043 | 1.0000 | 0.0618 | `REJECT_KILLED` |
| `N10_F2_COMM3_DON20_LONG` | -0.68% | -0.040 | -1.93% | -2.19% | -0.221 | 19.69% | -0.65% | -3.65% | 0.85% | +0.0142 | 1.0000 | 0.0279 | `REJECT_KILLED` |
| `N10_F3_IDX3_RSI2_MEAN_REV` | -4.46% | -0.678 | -4.75% | -5.88% | -0.855 | 15.31% | -2.33% | -8.60% | 3.70% | +0.0466 | 1.0000 | 0.0011 | `REJECT_KILLED` |
| `N10_F3_COMM_VS_IDX_ROTATION` | -6.33% | -0.656 | +0.52% | +0.13% | 0.102 | 18.48% | +17.75% | -13.54% | 1.20% | +0.0457 | 1.0000 | 0.0901 | `REJECT_KILLED` |
| `N10_F3_FX4_CARRY_MOM_LS` | -3.95% | -0.696 | -0.37% | -0.76% | -0.033 | 16.66% | +1.76% | -1.14% | 1.23% | -0.0019 | 1.0000 | 0.0571 | `REJECT_KILLED` |

---

## 4. Governance & Provenance

- **Reproducibility:** Run `D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe tooling/ai-engines/quant_factory/new_assets_10_dev_lab.py --no-fetch` (code: [new_assets_10_dev_lab.py](../../tooling/ai-engines/quant_factory/new_assets_10_dev_lab.py); unit tests: [test_wave2_swing_and_new_assets.py](../../tooling/ai-engines/tests/test_wave2_swing_and_new_assets.py)).
- **Holdout Seal Proof:** Every Parquet in `.runtime/new-assets-10-cache/` was truncated strictly `< 2025-01-01` prior to disk write (`manifest.sha256.json`: `holdout_rows = 0`, `max_date_analysed = 2024-12-31`).
- **Sleeve Export Status:** **`NONE`** (all 9 specs killed cleanly; `@risk-auditor` notified).
