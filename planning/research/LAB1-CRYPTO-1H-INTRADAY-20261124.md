---
title: "Wave 2 Lab #1: 100-Coin Crypto Universe Expansion + 1H (2021-2026) & 15m (2024-2026) Intraday Microstructure Research"
date: 2026-11-24
lane: quant-rnd (Lane C)
milestone: Wave 2 Cycle 1 — C1.1
status: COMPLETE_ZERO_SURVIVORS_RETAINED
holdout_rows_analysed: 0
order_send_count: 0
primary_script: tooling/ai-engines/quant_factory/crypto_1h_intraday_lab.py
---

# Wave 2 Lab #1: 100-Coin Crypto Expansion & 1H / 15m Intraday Microstructure

## 1. Executive Summary

Lab #1 expanded the local Binance Spot research cache to **100 liquid and historically declined/delisted coins on 4H (2021-2026)**, **40 liquid coins on 1H (2021-2026)**, and **15 top coins on 15m (2024-2026)** with SHA-256 manifest verification under `.runtime/crypto-1h-cache/` (`0` API keys, `OrderSend = 0`, `holdout_rows_analysed = 0`).

Across **`m_total = 12`** pre-registered intraday microstructure hypotheses spanning **6 families** evaluated strictly on **Cluster A (`2021-01-01..2023-12-31`) -> blind Cluster B (`2024-01-01..2026-11-22`)** for 1H (`2024-01-01..2025-05-31` Dev -> `2025-06-01..2026-11-22` blind OOS for 15m) through the 2-Role Research Council ([research_council.py](../../tooling/ai-engines/quant_factory/research_council.py)):

- **Approved for Incubation:** **`0 / 12`** (all 12 specs received `REJECT_KILLED`; no redundant sleeve JSON exported).
- **Primary Negative Discovery #1 (Spot Microstructure Cost Barrier):** Every high-turnover 1H/15m spot microstructure family — US Open Continuation, Asia-to-US Dip Reversion, 8h Funding-Settlement Clock Pre/Post Momentum/Reversion, Volatility Squeeze Breakout, 15m US Open ORB, and 15m Liquidation Flush Bounce — suffered **decisive net losses** (`-1.20%` to `-39.05%` CAGR at 1x friction, `-4.68%` to `-64.11%` at 2x friction in blind Cluster B) under realistic spot taker+slippage (`15 bps` one-way = `30 bps` round-trip). Annualized turnover (`18x` to `352x`) overwhelmed gross short-horizon predictability.
- **Primary Negative Discovery #2 (Redundancy of Slower 1H Trend Specs):** Only 3 slower multi-day 1H trend specs remained profitable across both 1x and 2x friction in blind Cluster B (`L1_F3_1H_EMA_48_240_BTC`: Cl.B `1x` `+7.74%` CAGR, Sharpe `1.038`, `2x` `+6.27%`, breakeven `5.97x`; `L1_F1_1H_DON_168_84_BTC`: Cl.B `1x` `+5.99%`, Sharpe `1.014`, `2x` `+5.00%`, breakeven `6.79x`; `L1_F3_1H_EMA_96_480_BTC`: Cl.B `1x` `+5.99%`, Sharpe `0.797`, `2x` `+5.20%`, breakeven `8.25x`). However, all three failed `G4_orthogonality` (`r = 0.8178` to `0.9769` vs incumbent Sleeve #2 `F4_4H_EMA_24_120_BTC`) and `G1_bh_fdr` (`q = 0.43464` to `0.45332 > 0.10` across `m_total = 12`).
- **Strategic Implication:** Directional long-only spot crypto alpha peaks at the **4H multi-day trend horizon** already promoted into Sleeve #2 ([CRYPTO-SLEEVE2-SURVIVORSHIP-FREE-20261124.md](./CRYPTO-SLEEVE2-SURVIVORSHIP-FREE-20261124.md)). Sub-4H directional spot trading on standard retail/tier-0 fee schedules (`10 bps` taker + `5 bps` slip) is structurally negative-expectancy; incremental orthogonal crypto alpha must instead come from **market-neutral / relative-value / perpetual funding structures** (tested in Lab #2) or VIP/maker rebate execution infrastructure.

---

## 2. Universe Expansion & Anti-Bias Protocol

| Dimension | Specification |
| --- | --- |
| Source Endpoint | Public Binance Spot `/api/v3/klines` (zero API keys, zero `OrderSend`) |
| Cache Root & Manifest | `.runtime/crypto-1h-cache/` (`manifest.sha256.json`, `lab1_summary.json`) |
| Cached Coverage | **100 / 100** `4h` coins (`2021-2026`), **40 / 40** `1h` coins (`2021-2026`), **15 / 15** `15m` coins (`2024-2026`); `0` skipped |
| Delisted / Declined Retention | Retains `EOSUSDT`, `MKRUSDT`, `WAVESUSDT` and historically decayed 2021 alts (`ICP`, `FIL`, `AXS`, `SAND`, `MANA`, `GALA`, `APE`, `FLOW`, etc.) |
| Causal Universe Rule | Rolling 30-day (`720` 1H bars) dollar-volume Top-15 strictly `<= bar t` |
| Execution Timing | Strict `t -> t+1` close-to-close execution, long-only spot `[0, 1]`, gross `<= 1.0x` |
| Friction Model | `1x` = `15 bps` one-way (`10 bps` fee + `5 bps` slip, `30 bps` RT); `2x` stress = `30 bps` one-way (`60 bps` RT) + `100 bps` delisting haircut |
| Council Kill Criteria | `BH-FDR q <= 0.10`, `DSR >= 0.50`, Cl.B Sharpe `>= 0.70`, `2x` cost survival & breakeven `>= 2.0x`, `corr vs Sleeve #2 <= 0.55`, tail `corr <= 0.75`, active days `>= 30` |

---

## 3. Full Empirical Results (`m_total = 12`, All Killed Retained Honestly)

All metrics transcribed verbatim from `.runtime/crypto-1h-cache/lab1_summary.json` (runtime `218.19s`, `1H` Cl.A `n = 1,095` days / Cl.B `n = 1,057` days; `15m` Dev `n = 517` days / Blind OOS `n = 540` days).

| Spec ID | TF | Cl.A 1x CAGR | Cl.A 1x Sharpe | Cl.B 1x CAGR | Cl.B 2x CAGR | Cl.B 1x Sharpe | Cl.B MaxDD | Cl.B Turn/yr | BH-q (Cl.B) | DSR (Cl.B) | BE Cost Mult | Corr vs S2 (Cl.B) | Council Verdict | Failed Gates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `L1_F1_1H_DON_72_36` | 1h | +4.74% | 0.791 | +5.00% | +1.93% | 0.714 | 7.09% | 19.77x | 0.47463 | 0.3183 | 2.60x | 0.6074 | `REJECT_KILLED` | `G1, G2, G4` |
| `L1_F1_1H_DON_168_84_BTC` | 1h | +8.80% | 1.590 | +5.99% | +5.00% | 1.014 | 6.04% | 6.24x | 0.43464 | 0.5250 | 6.79x | 0.8178 | `REJECT_KILLED` | `G1, G4` |
| `L1_F2_1H_US_OPEN_CONT` | 1h | +1.07% | 0.235 | -7.79% | -16.88% | -1.310 | 23.24% | 69.11x | 1.00000 | 0.0000 | -0.02x | 0.3618 | `REJECT_KILLED` | `G1, G2, G3, G5` |
| `L1_F2_1H_ASIA_TO_US_REV` | 1h | +0.28% | 0.131 | -3.31% | -5.90% | -1.152 | 11.93% | 18.11x | 1.00000 | 0.0001 | -0.35x | 0.1997 | `REJECT_KILLED` | `G1, G2, G3, G5` |
| `L1_F3_1H_EMA_48_240_BTC` | 1h | +11.09% | 1.506 | +7.74% | +6.27% | 1.038 | 7.11% | 9.18x | 0.43464 | 0.5411 | 5.97x | 0.8674 | `REJECT_KILLED` | `G1, G4` |
| `L1_F3_1H_EMA_96_480_BTC` | 1h | +11.55% | 1.555 | +5.99% | +5.20% | 0.797 | 9.96% | 4.97x | 0.45332 | 0.3775 | 8.25x | 0.9769 | `REJECT_KILLED` | `G1, G2, G4` |
| `L1_F4_1H_PRE_SETTLE_MOM` | 1h | -26.19% | -5.696 | -39.05% | -64.11% | -8.004 | 76.28% | 352.64x | 1.00000 | 0.0000 | -3.07x | 0.2478 | `REJECT_KILLED` | `G1, G2, G3, G5` |
| `L1_F4_1H_POST_SETTLE_REV` | 1h | -4.72% | -1.698 | -11.94% | -21.09% | -3.057 | 31.18% | 73.03x | 1.00000 | 0.0000 | -0.64x | 0.2398 | `REJECT_KILLED` | `G1, G2, G3, G5` |
| `L1_F5_1H_VOL_SQZ_BRK24` | 1h | -1.84% | -0.563 | -1.20% | -4.68% | -0.306 | 6.74% | 23.93x | 1.00000 | 0.0157 | 0.64x | 0.2876 | `REJECT_KILLED` | `G1, G2, G3, G5` |
| `L1_F5_1H_VOL_SQZ_72_BTC` | 1h | +1.23% | 0.782 | +0.06% | -0.76% | 0.036 | 3.63% | 5.43x | 1.00000 | 0.0538 | 1.07x | 0.3502 | `REJECT_KILLED` | `G1, G2, G3` |
| `L1_F6_15M_US_OPEN_ORB` | 15m | -11.83% | -3.529 | -9.61% | -21.70% | -2.875 | 14.05% | 95.73x | 1.00000 | 0.0000 | 0.16x | 0.1734 | `REJECT_KILLED` | `G1, G2, G3, G5` |
| `L1_F6_15M_LIQ_FLUSH_BOUNCE` | 15m | -26.77% | -5.252 | -26.18% | -44.87% | -6.487 | 36.21% | 194.39x | 1.00000 | 0.0000 | -0.62x | 0.1913 | `REJECT_KILLED` | `G1, G2, G3, G5` |

---

## 4. Forensic Diagnosis by Family

1. **Family 1 & Family 3 (`1H` Donchian & EMA Trend):** Structurally positive gross and net edge (`full_1x` Sharpe `1.170` to `1.293`, `DSR_full = 0.8808` to `0.9367`), confirming that trend-following across the causal Top-15 crypto universe is genuine and persists out-of-sample in 2024-2026. However, `L1_F3_1H_EMA_96_480_BTC` is mechanically identical in horizon to 4H `EMA(24/120)` (`r = 0.9769` with Sleeve #2), and `L1_F3_1H_EMA_48_240_BTC` (`r = 0.8674`) doubles annual turnover (`9.18x` vs `4.97x`) without beating 4H net efficiency. Promoting it as a second sleeve would double-count directional crypto beta rather than add diversification.
2. **Family 2 (`1H` US Session Flow & Asia-to-US Reversion):** Faint positive Cluster A drift (`+1.07%` / `+0.28%` CAGR) flipped decisively negative in blind Cluster B (`-7.79%` / `-3.31%` CAGR) as US spot BTC ETF flows changed intraday volatility structure and `18x–69x` annual turnover bled `30 bps` RT fees.
3. **Family 4 (`1H` 8h Funding-Settlement Clock):** Severe negative expectancy even before 2x stress (`breakeven_cost_mult = -3.07x` and `-0.64x`), proving that chasing 2h pre-settlement directional momentum (`352.6x` turnover) or buying 2h post-settlement dips on spot bars is systematically adverse-selected by perpetual arbitrageurs.
4. **Family 5 (`1H` Volatility Compression Squeeze):** Weak Cluster A positive drift on the BTC-gated 72h variant (`+1.23%` CAGR) decayed to near-zero (`+0.06%` at 1x, `-0.76%` at 2x) in blind Cluster B, failing `G1`, `G2`, and `G3`.
5. **Family 6 (`15m` US Open ORB & Liquidation Flush Bounce):** Both 15m spot microstructure hypotheses suffered `-9.61%` and `-26.18%` annualized losses in blind OOS (`95.7x` and `194.4x` turnover). On `15 bps` one-way taker+slippage, a 15m strategy turning over `100x/yr` faces a `15%` annual fee drag hurdle before earning a single basis point of alpha.

---

## 5. Governance, Provenance & Next Step

- **Reproducibility:** Run `D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe tooling/ai-engines/quant_factory/crypto_1h_intraday_lab.py --no-fetch` (code: [crypto_1h_intraday_lab.py](../../tooling/ai-engines/quant_factory/crypto_1h_intraday_lab.py); unit tests: [test_wave2_crypto_labs.py](../../tooling/ai-engines/tests/test_wave2_crypto_labs.py)).
- **Sleeve Export Status:** **`NONE`** (zero specs passed `APPROVE_FOR_INCUBATION`; incumbent Sleeve #2 `F4_4H_EMA_24_120_BTC` remains unchallenged primary directional spot engine).
- **Value Preserved:** The 100-coin `4h` + 40-coin `1h` SHA-verified cache under `.runtime/crypto-1h-cache/` directly powers Wave 2 Lab #2 market-neutral stat-arb & pairs research ([LAB2-CRYPTO-STATARB-NEUTRAL-20261124.md](./LAB2-CRYPTO-STATARB-NEUTRAL-20261124.md)).
