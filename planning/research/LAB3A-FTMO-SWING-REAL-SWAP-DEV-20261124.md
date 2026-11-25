---
title: "Wave 2 Lab #3A: FTMO Multi-Day Swing Using Real Harvested FTMO Swaps (Dev < 2025-01-01)"
date: 2026-11-24
lane: quant-rnd (Lane C)
milestone: Wave 2 Cycle 2A — C2.1 (Lab #3A)
status: COMPLETE_ZERO_SURVIVORS_RETAINED
holdout_rows_analysed: 0
order_send_count: 0
primary_script: tooling/ai-engines/quant_factory/ftmo_swing_real_swap_lab.py
---

# Wave 2 Lab #3A: FTMO Multi-Day Swing Using Real FTMO Swaps (Dev `< 2025-01-01`)

## 1. Executive Summary

Lab #3A evaluated whether multi-day (`2–10` day) swing holding on FTMO Swing accounts adds orthogonal alpha (`|r| < 0.15` vs frozen `PORT_7E`) once **real harvested FTMO Swing overnight swaps** from [FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json](./FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json) and empirical M1 Bid-Ask spreads from `.runtime/hot-m1-cache/` are modeled accurately. Holdout `2025-2026` remained 100% sealed (`max_date_analysed = 2024-12-31`, `holdout_rows_analysed = 0`, `OrderSend = 0`).

Across **`m_total = 12`** pre-registered multi-day specs spanning **4 swing families** evaluated strictly on **Cluster A (`2018-01-01..2021-12-31`) -> blind Cluster B (`2022-01-01..2024-12-31`)** through the 2-Role Research Council ([research_council.py](../../tooling/ai-engines/quant_factory/research_council.py)) plus an explicit FTMO Swing drawdown safety gate (`MaxDD < 10.0%`, `worst_1d > -5.0%`):

- **Approved for Incubation:** **`0 / 12`** (all 12 specs received `REJECT_KILLED`; zero `.mq5` swing EA templates or sleeve JSONs exported).
- **Primary Discovery #1 (Overnight Swap Bleed Destroys Unfiltered Swing Breakouts):** Two-way multi-day breakout strategies (`SW_F2_*`) bled `-4.52%` to `-14.44%` in pure overnight swap drag over Cluster B (`2022-2024`) alone — turning `SW_F2_D1_DON_20_10_ALL11`'s modest `+4.07%` gross price PnL into `-13.98%` cumulative net return (`-4.74%` CAGR, `-14.44%` swap drag dominated by `XAUUSD -54.46` and negative index/FX swaps). This mathematically validates why our intraday **`swap = 0` `PORT_7E`** architecture outperforms naive multi-day FTMO Swing breakouts.
- **Primary Discovery #2 (Positive-Carry FX Regime & FTMO Drawdown Trap):** Pure positive-swap FX carry (`SW_F4_FX_CARRY_PURE`: Long `GBPJPY +5.96`, `EURJPY +2.18`, `USDJPY +1.78`) delivered `+11.52%` CAGR in blind Cluster B (`Sharpe 0.953`, `corr vs PORT_7E = -0.0160`, `+10.48%` even with zero positive-swap credit) during the 2022–2024 Fed/BoE vs BoJ divergence. However, it suffered **`MaxDD = 15.33%`** (worst 1-day `-4.44%` during the July–August 2024 Yen carry unwind — breaching FTMO's `10%` hard total loss limit!), weak Cluster A (`2018-2021` Sharpe `0.285`), and failed `BH-FDR` (`q = 0.38048`).
- **Primary Discovery #3 (Index Short-Term Dip Reversion Survives Financing Safely, Too Modest for Standalone Prop):** `SW_F3_IDX_3D_DIP_REV` (`US500/US100/GER40` 3-day dip above SMA100) remained positive in both Cluster A (`+1.53%` CAGR) and blind Cluster B (`+2.54%` CAGR, `Sharpe 0.735`, `MaxDD 3.86%` safe for FTMO, `corr = -0.0256`) even after conservative index financing (`-1.97%` swap drag), but failed `BH-FDR` (`q = 0.38048`) and `DSR_b` (`0.3548`).

---

## 2. Real Harvested FTMO Swap Audit & Anti-Fake-Swap Guard

| Asset | FTMO Symbol | Swap Long (pts) | Swap Short (pts) | Rollover 3x Day | Empirical 1x Cost (bps) | Anti-Fake-Swap Modeling Rule |
| --- | --- | ---: | ---: | --- | ---: | --- |
| `EURUSD` | `EURUSD` | -8.44 | +0.19 | Wed (3) | 1.237 | Exact `swap_mode=1` triple-Wed |
| `GBPUSD` | `GBPUSD` | -4.47 | -5.88 | Wed (3) | 1.460 | Exact `swap_mode=1` triple-Wed |
| `USDJPY` | `USDJPY` | +1.78 | -17.83 | Wed (3) | 1.276 | Exact + zero-pos-swap sensitivity |
| `AUDUSD` | `AUDUSD` | -2.42 | -7.38 | Wed (3) | 1.828 | Exact `swap_mode=1` triple-Wed |
| `USDCAD` | `USDCAD` | +0.48 | -10.81 | Wed (3) | 1.543 | Exact + zero-pos-swap sensitivity |
| `EURJPY` | `EURJPY` | +2.18 | -11.39 | Wed (3) | 1.500 | Exact + zero-pos-swap sensitivity |
| `GBPJPY` | `GBPJPY` | +5.96 | -25.49 | Wed (3) | 1.950 | Exact + zero-pos-swap sensitivity |
| `XAUUSD` | `XAUUSD` | -54.46 | -15.00 | Wed (3) | 2.039 | Exact `swap_mode=1` (`~-7.6%/yr` Long) |
| `US500` | `US500.cash` | +32.83* | -198.56 | Fri (5) | 1.879 | *Capped to `-5.0%/yr` Long (ex-div guard) |
| `US100` | `US100.cash` | +1076.28* | -1677.49 | Fri (5) | 2.249 | *Capped to `-5.0%/yr` Long (ex-div guard) |
| `GER40` | `GER40.cash` | -485.36 | -48.98 | Fri (5) | 1.941 | Exact `swap_mode=1` triple-Fri |

*Forensic Note:* On the `2026-11-23` snapshot, `US100.cash` (`+1076.28`) and `US500.cash` (`+32.83`) showed positive point-in-time ex-dividend/roll adjustments. To prevent phantom `+19%/yr` free index carry across 2018–2024, our simulator explicitly capped positive cash-index `swap_long` to realistic `-5.0%/yr` financing (`min(raw_swap, -0.05/365*mult)`), while charging 100% of all negative swaps verbatim.

---

## 3. Full Empirical Results (`m_total = 12`, All Killed Retained Honestly)

All metrics transcribed verbatim from `.runtime/hot-m1-cache/lab3a_ftmo_swing_real_swap_summary.json` (runtime `21.57s`, Cl.A `n = 1,044` days `2018-2021`, blind Cl.B `n = 782` days `2022-2024`).

| Spec ID | TF | Cl.A 1x CAGR | Cl.A Shp | Cl.B 1x CAGR | Cl.B 2x CAGR | Cl.B 0-PosSw | Cl.B Shp | Cl.B MaxDD | Cl.B Swap PnL | Corr vs P7E | BH-q | DSR_b | Verdict | Failed Gates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `SW_F1_POSCARRY_EMA_10_40` | D1 | +0.78% | 0.164 | +5.52% | +5.13% | +4.92% | 0.687 | 12.60% | +1.77% | +0.0200 | 0.38048 | 0.3263 | `REJECT_KILLED` | `G1, G2, DD` |
| `SW_F1_POSCARRY_EMA_20_60` | D1 | -0.78% | -0.105 | +5.01% | +4.72% | +4.39% | 0.599 | 12.09% | +1.86% | -0.0142 | 0.38048 | 0.2727 | `REJECT_KILLED` | `G1, G2, G5, DD` |
| `SW_F1_POSCARRY_H4_DON_20_10` | H4 | -0.22% | -0.013 | +3.39% | +1.52% | +2.96% | 0.470 | 13.66% | +1.29% | +0.1419 | 0.38048 | 0.2007 | `REJECT_KILLED` | `G1, G2, G5, DD` |
| `SW_F2_D1_DON_20_10_FX` | D1 | -5.85% | -0.783 | -3.87% | -4.71% | -4.18% | -0.389 | 16.69% | -5.21% | +0.1594 | 0.87709 | 0.0096 | `REJECT_KILLED` | `All 6` |
| `SW_F2_H4_KELTNER_20_FX` | H4 | -5.42% | -0.783 | -10.35% | -13.96% | -10.56% | -1.206 | 38.24% | -4.52% | +0.1707 | 0.98610 | 0.0001 | `REJECT_KILLED` | `All 6` |
| `SW_F2_D1_DON_20_10_ALL11` | D1 | -7.65% | -0.906 | -4.74% | -5.70% | -4.97% | -0.440 | 16.64% | -14.44% | +0.1578 | 0.87709 | 0.0074 | `REJECT_KILLED` | `All 6` |
| `SW_F3_IDX_RSI2_TREND` | D1 | +3.40% | 0.484 | +0.09% | -0.94% | +0.09% | 0.046 | 12.63% | -5.86% | +0.0171 | 0.62163 | 0.0566 | `REJECT_KILLED` | `G1, G2, G3, DD` |
| `SW_F3_IDX_3D_DIP_REV` | D1 | +1.53% | 0.285 | +2.54% | +2.23% | +2.54% | 0.735 | 3.86% | -1.97% | -0.0256 | 0.38048 | 0.3548 | `REJECT_KILLED` | `G1, G2` |
| `SW_F3_IDX_WEEKLY_REVERSAL` | D1 | -0.43% | -0.074 | +1.77% | +1.45% | +1.77% | 0.491 | 6.22% | -2.35% | -0.0354 | 0.38048 | 0.2073 | `REJECT_KILLED` | `G1, G2, G5` |
| `SW_F4_FX_CARRY_PURE` | D1 | +2.15% | 0.285 | +11.52% | +11.42% | +10.48% | 0.953 | 15.33% | +2.92% | -0.0160 | 0.38048 | 0.5053 | `REJECT_KILLED` | `G1, DD` |
| `SW_F4_FX_CARRY_PLUS_MOM20` | D1 | -1.50% | -0.225 | +2.58% | +1.85% | +2.06% | 0.372 | 12.26% | -2.34% | +0.1386 | 0.38048 | 0.1558 | `REJECT_KILLED` | `G1, G2, G5, DD` |
| `SW_F4_FX_CARRY_PLUS_MOM60` | D1 | +0.24% | 0.069 | +3.15% | +2.63% | +2.59% | 0.424 | 16.87% | -1.95% | +0.0812 | 0.38048 | 0.1798 | `REJECT_KILLED` | `G1, G2, DD` |

---

## 4. Governance & Operational Takeaway

- **Reproducibility:** Run `D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe tooling/ai-engines/quant_factory/ftmo_swing_real_swap_lab.py` (code: [ftmo_swing_real_swap_lab.py](../../tooling/ai-engines/quant_factory/ftmo_swing_real_swap_lab.py); tests: [test_wave2_swing_and_new_assets.py](../../tooling/ai-engines/tests/test_wave2_swing_and_new_assets.py)).
- **Sleeve & MQL5 Handoff Status:** **`NONE`** (zero swing strategies cleared Research Council + FTMO DD safety; `@mql5-builder` keeps `PORT_7E` intraday `swap = 0` untouched as the optimal FTMO prop engine).
- **Capital Routing Principle:** Multi-day equity/macro trend belongs in zero-swap Own-Book ETFs ([SLEEVE3B-MACRO-ETF-TREND-18YR-20261124.md](./SLEEVE3B-MACRO-ETF-TREND-18YR-20261124.md)) rather than swap-bearing CFDs.
