---
title: "Wave 2 Lab #2: Crypto Stat-Arb, Cointegrated Pairs & Market-Neutral (beta ~ 0) Research"
date: 2026-11-24
lane: quant-rnd (Lane C)
milestone: Wave 2 Cycle 1 — C1.2
status: COMPLETE_ZERO_SURVIVORS_RETAINED
holdout_rows_analysed: 0
order_send_count: 0
primary_script: tooling/ai-engines/quant_factory/crypto_statarb_pairs_lab.py
---

# Wave 2 Lab #2: Crypto Stat-Arb, Pairs & Market-Neutral (`beta ~ 0`) Research

## 1. Executive Summary

Lab #2 tested whether **market-neutral Long/Short perpetual strategies (`beta_vs_BTC ~ 0`)** over the expanded 100-coin 4H / 40-coin 1H Binance universe and 20-perp exact 8h Binance funding history (`.runtime/crypto-1h-cache/` + `.runtime/crypto-spot-cache/funding/`) can deliver an orthogonal Sleeve #4 uncorrelated with directional Sleeve #2 (`F4_4H_EMA`) and Sleeve #3A (`CARRY_BTC_ETH_2XBUF`).

Across **`m_total = 12`** pre-registered specs spanning **4 market-neutral families** evaluated strictly on **Cluster A (`2021-01-01..2023-12-31`) -> blind Cluster B (`2024-01-01..2026-11-22`)** with exact atomic dollar-neutral rebalancing, gross leverage strictly `<= 1.0x` (`0.50x` Long / `-0.50x` Short => `>= 2x` margin buffer), full 2-leg friction (`1x = 15 bps` one-way per leg / `30 bps` RT per leg; `2x = 30 bps` one-way per leg), and realized 8h Binance USD-M perpetual funding cashflows (`-w_j * funding_j`), routed through the 2-Role Research Council ([research_council.py](../../tooling/ai-engines/quant_factory/research_council.py)):

- **Approved for Incubation:** **`0 / 12`** (all 12 specs received `REJECT_KILLED`; no new sleeve JSON exported).
- **Market Neutrality Verified:** Every spec achieved strict neutrality (`|beta_vs_BTC|` between `0.0079` and `0.1274` in blind Cluster B; `avg_abs_net_exp <= 0.00008` on all pure dollar-neutral books).
- **Structural Finding #1 (Mean-Reversion & Pairs Are Gross-Negative):** Both **Sector-Neutral Residual Reversion** (`price_pnl_b = -26.76%` to `-73.29%`) and **Rolling Cointegrated Pairs** (`W180` `-32.74%`, `1H W240` `-19.11%`; slow `W360` only `+10.49%` gross vs `17.12%` cost drag) failed **before or barely above zero friction**. Crypto altcoin dispersion is trend-dominated rather than mean-reverting: fading sector winners and relative-value divergences suffers severe structural regime-break losses.
- **Structural Finding #2 (Real Gross Alpha in Funding Dislocation & L/S Momentum, Blocked by Taker Friction):** Two families exhibited genuine positive gross alpha AND low/negative correlation with Sleeve #2 in blind Cluster B (`2024–2026`):
  - **`S3_FUND_DISLOC_4H_7D_K4`** (Short Top-4 crowded high-funding perps vs Long Bot-4 low-funding perps): Cluster A `+47.06%` CAGR (Sharpe `1.474`, `2x` `+31.88%`) -> blind Cluster B **`+49.50%` gross price PnL + `+15.42%` realized funding PnL** vs `33.04%` 1x cost drag => **`+8.76%` net CAGR (Sharpe `0.476`)**, **`beta_BTC = -0.1274`**, **`corr vs Sleeve #2 = -0.1872`** (worst-5% tail `corr = -0.1807`), full 2021-2026 Sharpe **`1.033`** (`DSR_full = 0.8196`). However, it failed `G3_cost_stress` at `2x` (`-2.99%` CAGR, breakeven `1.77x < 2.00x`), `G2` (`Sharpe 0.476 < 0.60`), and `G1` (`BH-q = 1.0`).
  - **`S4_MKT_NEUT_MOM_4H_14D`** (Long Top-5 / Short Bot-5 vol-managed 14d XSMOM): Cluster A `+13.16%` CAGR (Sharpe `0.527`) -> blind Cluster B **`+80.17%` gross price PnL + `+0.42%` funding PnL** vs `48.98%` 1x cost drag => **`+6.66%` net CAGR (Sharpe `0.364`)**, **`beta_BTC = -0.1013`**, **`corr vs Sleeve #2 = +0.0205`**. Also failed `G3` at `2x` (`-9.93%` CAGR, breakeven `1.44x`), `G2`, and `G1`.
- **Actionable Capital Decision:** Do **NOT** deploy taker-rebalanced crypto stat-arb at `15 bps` one-way per leg (`0` false positives promoted). Retain `S3_FUND_DISLOC_4H_7D_K4` and `S4_MKT_NEUT_MOM_4H_14D` strictly as **Conditional Execution-Blocked Candidates** to re-test ONLY if Naqex gains Binance USD-M Maker/VIP passive limit execution (`<= 4 bps` one-way per leg, cutting Cl.B friction drag from `33%–49%` to `< 10%–13%`).

---

## 2. Methodology, Friction & Neutrality Guarantees

| Dimension | Specification |
| --- | --- |
| Universe & Data | `100` coins `4H` (`2021-2026`), `40` coins `1H` (`2021-2026`) from `.runtime/crypto-1h-cache/`; `20` liquid USD-M perps exact 8h funding from `.runtime/crypto-spot-cache/funding/rates/` (median-funding fallback on non-cached altcoins) |
| Safety & Seal | Zero API keys, `OrderSend = 0`, `holdout_rows_analysed = 0` (FX Holdout 2025+ untouched) |
| Execution & Neutrality | Strict `t -> t+1` close-to-close execution; atomic portfolio-level cadence + L1 deadband preserving exact dollar neutrality `sum(w) == 0`; gross leverage strictly `<= 1.0x` (`>= 2x` equity margin buffer) |
| 2-Leg Friction Model | `1x = 15 bps` one-way per leg (`30 bps` RT per leg); `2x = 30 bps` one-way per leg (`60 bps` RT per leg); `100 bps` delisting NaN haircut; exact 8h Binance funding PnL `-w_j * funding_j` |
| Council Kill Criteria | `BH-FDR q <= 0.10`, `DSR >= 0.50`, Cl.B Sharpe `>= 0.60`, `2x` cost survival & breakeven `>= 2.0x`, `corr vs Sleeve #2 <= 0.25`, tail `corr <= 0.40`, `|beta_BTC| <= 0.20`, active days `>= 30` |

Note on implementation audit: an initial prototype using the long-only per-coin `_apply_rebalance_deadband` helper introduced `0.03–0.07` net dollar drift and `500x–3,300x/yr` rank-boundary churn. Replacing it with atomic portfolio-level horizon-matched rebalancing (`_apply_neutral_rebalance_cadence`) restored exact machine-precision dollar neutrality (`avg_abs_net_exp <= 0.00008`), eliminated all NumPy empty-slice warnings, and reduced turnover `3x–6x` without peeking at Cluster B.

---

## 3. Full Empirical Results (`m_total = 12`, All Killed Retained Honestly)

All metrics transcribed verbatim from `.runtime/crypto-1h-cache/lab2_statarb_summary.json` (runtime `109.72s`, Cl.A `n = 1,095` days, blind Cl.B `n = 1,057` days).

| Spec ID | TF | Cl.A 1x CAGR | Cl.A Shp | Cl.B 1x CAGR | Cl.B 2x CAGR | Cl.B Shp | Cl.B Turn/yr | Cl.B Beta BTC | Corr vs S2 | Cl.B Price PnL | Cl.B Fund PnL | Cl.B 1x Cost | BE Mult | Verdict |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `S1_SECTOR_RES_REV_4H_12B` | 4h | -48.96% | -2.538 | -60.06% | -79.12% | -4.391 | 431.17x | +0.0400 | -0.0292 | -73.29% | +1.16% | 187.42% | -14.65x | `REJECT_KILLED` |
| `S1_SECTOR_RES_REV_4H_24B` | 4h | -39.06% | -1.788 | -35.40% | -53.41% | -2.009 | 217.33x | +0.0463 | -0.0069 | -26.76% | +0.88% | 94.40% | -3.16x | `REJECT_KILLED` |
| `S1_SECTOR_RES_REV_1H_24B` | 1h | -66.08% | -3.521 | -63.39% | -84.16% | -4.315 | 556.64x | +0.0183 | -0.0237 | -43.49% | +2.39% | 241.83% | -18.02x | `REJECT_KILLED` |
| `S2_COINT_PAIRS_4H_W180` | 4h | -34.66% | -2.290 | -27.24% | -40.39% | -2.466 | 132.79x | +0.0281 | +0.0019 | -32.74% | +0.63% | 57.70% | -2.44x | `REJECT_KILLED` |
| `S2_COINT_PAIRS_4H_W360` | 4h | -25.17% | -1.829 | -2.68% | -8.27% | -0.255 | 39.40x | -0.0079 | -0.0371 | +10.49% | -0.04% | 17.12% | 0.48x | `REJECT_KILLED` |
| `S2_COINT_PAIRS_1H_W240` | 1h | -39.78% | -3.508 | -38.77% | -59.87% | -4.685 | 281.51x | +0.0128 | -0.0280 | -19.11% | +0.90% | 122.38% | -3.45x | `REJECT_KILLED` |
| `S3_FUND_DISLOC_4H_3D_K4` | 4h | +31.48% | 1.067 | -20.43% | -38.89% | -1.196 | 175.67x | -0.0931 | -0.2276 | -1.11% | +15.86% | 76.31% | -0.76x | `REJECT_KILLED` |
| `S3_FUND_DISLOC_4H_7D_K4` | 4h | +47.06% | 1.474 | +8.76% | -2.99% | 0.476 | 76.06x | -0.1274 | -0.1872 | +49.50% | +15.42% | 33.04% | 1.77x | `REJECT_KILLED` |
| `S3_FUND_DISLOC_4H_14D_K5` | 4h | +35.64% | 1.307 | +0.93% | -4.11% | 0.140 | 34.10x | -0.1274 | -0.3273 | +9.10% | +12.62% | 14.81% | 1.19x | `REJECT_KILLED` |
| `S4_MKT_NEUT_MOM_4H_14D` | 4h | +13.16% | 0.527 | +6.66% | -9.93% | 0.364 | 112.54x | -0.1013 | +0.0205 | +80.17% | +0.42% | 48.98% | 1.44x | `REJECT_KILLED` |
| `S4_MKT_NEUT_MOM_4H_30D_BN` | 4h | +5.95% | 0.345 | -5.96% | -12.84% | -0.162 | 50.50x | -0.0396 | -0.0377 | +9.63% | +1.92% | 22.02% | 0.01x | `REJECT_KILLED` |
| `S4_MKT_NEUT_MOM_1H_7D` | 1h | +7.87% | 0.399 | -10.80% | -41.20% | -0.337 | 277.29x | -0.0499 | +0.0594 | +99.27% | -3.00% | 120.54% | 0.44x | `REJECT_KILLED` |

---

## 4. PnL Attribution & Factor Insights

1. **Why Sector-Neutral Reversion (`S1`) and Cointegrated Pairs (`S2`) Failed:** Across all 6 reversion/pairs specs, cumulative gross price PnL in blind Cluster B was negative on 5 of 6 specs (`-19.11%` to `-73.29%`) and barely positive (`+10.49%` over 2.9 years) on `W360`. Crypto sector pairs do not share stable fundamental earnings anchors like US equities; token emissions, ETF approvals, and ecosystem migrations create permanent cointegration breaks where shorting the outperformer and longing the decaying token loses before costs.
2. **Why Funding-Dislocation L/S (`S3`) Worked Grossly Yet Failed 2x Taker Stress:** Across all three lookbacks (`3d`, `7d`, `14d`), realized 8h funding PnL in blind Cluster B was consistently positive (`+12.62%` to `+15.86%` over 2.9 years = `~+4.4% to +5.5%/yr` pure funding carry!). On `S3_FUND_DISLOC_4H_7D_K4`, fading over-leveraged perp longs added `+49.50%` gross price spread PnL (`+64.92%` combined gross PnL), with negative correlation (`-0.1872`) to directional Sleeve #2 and zero correlation (`-0.0096`) to Sleeve #3A BTC/ETH carry. However, rebalancing `76x/yr` across 2 legs at `15 bps` taker (`33.04%` cost drag) left a `1.77x` breakeven multiple, below our `2.00x` council floor.
3. **Why Market-Neutral Momentum (`S4`) Was Blocked Strictly by Execution Friction:** Both `S4_MKT_NEUT_MOM_4H_14D` (`+80.17%` gross price PnL in Cl.B) and `S4_MKT_NEUT_MOM_1H_7D` (`+99.27%` gross price PnL in Cl.B) confirm strong cross-sectional crypto momentum dispersion with near-zero BTC beta (`-0.10` / `-0.05`) and near-zero correlation vs Sleeve #2 (`+0.02` / `+0.06`). However, `112.5x–277.3x/yr` 2-leg taker turnover (`48.98%–120.54%` cost drag) consumed `61%–121%` of gross alpha. Adding a rolling BTC beta hedge (`30D_BN`) introduced `0.118` average net exposure and diluted cross-sectional dispersion without improving Sharpe.

---

## 5. Governance, Provenance & Handoff

- **Reproducibility:** Run `D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe tooling/ai-engines/quant_factory/crypto_statarb_pairs_lab.py` (code: [crypto_statarb_pairs_lab.py](../../tooling/ai-engines/quant_factory/crypto_statarb_pairs_lab.py); unit tests: [test_wave2_crypto_labs.py](../../tooling/ai-engines/tests/test_wave2_crypto_labs.py)).
- **Sleeve Export Status:** **`NONE`** (zero specs passed `APPROVE_FOR_INCUBATION` at conservative `15 bps` taker friction; `@risk-auditor` notified that Lab #1 and Lab #2 export `0` new sleeves so NCO Pod v2 uses verified Sleeves #1, #2, #3A, #3B plus any verified Wave-2 Cycle 2 sleeves).
- **Future Research Gate (Not Curve-Fit Here):** If passive post-only limit execution on Binance USD-M Futures is validated in live shadow testing at `<= 4 bps` realized one-way cost per leg, re-test ONLY the two pre-identified economic mechanisms (`S3` 7d Funding-Dislocation L/S + `S4` 14d Vol-Managed XSMOM) on an independent forward paper-soak window.
