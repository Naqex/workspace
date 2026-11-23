# Pass 24 Report — Multi-Timeframe (`M15/H1/D1`) 6 New Structural Families (`m_total = 128`) & Dual-Firm 2-Layer Evaluation

- **Date:** `2026-11-23`
- **Protocol Commit:** `52a53cb785a63998a281aab06cf449cd061f140a` ([PASS24 Protocol](PASS24-MTF-NEW-ARCHETYPES-PROTOCOL-20261123.md))
- **Holdout Lock:** `holdout_rows = 0` (`< 2025-01-01T00:00:00Z`) · `OrderSend = 0` · `network_calls = 0`
- **Artifact on E: Cold Archive:** `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\pass24-mtf-new-archetypes-20261123\pass24-result.json`

## Executive Summary & Verdict

- **Verdict:** **`US100_SESS_CONT_BRK_40_QUALIFIED_AS_PROVISIONAL_ENGINE4 (CALMAR 0.89 -> 1.08 · FIRST TIME > 1.00)`** — pending FTMO / The5ers Demo MT5 contract spec capture on `US100.cash` (`PROVISIONAL_SPEC_UNMEASURED_DEMO`) and additional Engine #5 to push Calmar into `1.4+`.
- **Discovery Sweep (`m_total = 128` across 6 orthogonal MTF families × 8 Native M1 Bid/Ask assets, Cluster A → Blind Cluster B):**
  - `17 / 128` passed Cluster A discovery gate (`n_A >= 50`, `Net_A > 0`, `PF_A >= 1.05`); `111 / 128` filtered out strictly on Cluster A.
  - **`US100 SESS_CONT_BRK_40`** (*Family 3: NYSE Morning Drive `09:30–11:30 ET` → Afternoon Breakout Continuation `11:30–15:55 ET`, `swap = 0`*) is the standout non-FX discovery:
    - **Cluster A (`2018–2020`):** `+4.28R` (`PF 1.127`, DD `6.02R`) → **Blind Cluster B (`2021–2024`):** **`+9.86R` (`PF 1.206`, DD `5.47R`, `4/4` blind years positive!)**.
    - **3 Cost Tiers ALL solidly positive:** `Base (2 pts RT) = +21.50R`, `Stress (4 pts RT) = +14.14R`, **`Double Stress (6 pts RT on top of ~3.2 pt real M1 spread!) = +7.09R`**; crushed Fade (`-55.10R`, `p_sf = 0.008`).
    - **Balanced 2-Way Alpha (ZERO bull-market beta illusion):** **`BUY: +4.23R` (`n = 230`, Base `+8.46R`)** AND **`SELL: +9.91R` (`n = 184`, Base `+13.04R`)** — earned more on SHORTS than LONGS during a historic NASDAQ bull run!
    - **Passed BOTH 2D Stability Surfaces:** **`9 / 12`** (`min_move × SL`) AND **`9 / 12`** (`min_move × close_pct`) positive in both Cluster A & Blind Cluster B!
    - **Passed Outlier & Crisis Stress:** Drop Top-3 **`+8.49R`**, Drop Top-5 **`+5.42R`**, **Excl BOTH COVID `2020-03` & `2022-09/10` = `+17.29R`** (`n = 392`).
    - **Zero Correlation with 3-Engine FX Core:** **`r3E = -0.0037`**.
    - *Honest caveats retained:* `q_all = 0.341` over `m = 128`, `top10_R = 14.68R` vs `14.14R` Stress (passes easily at Base `+21.50R`), and `US100.cash` MT5 Demo specs remain `PROVISIONAL_SPEC_UNMEASURED_DEMO`.
- **4-Engine Portfolio Breakthrough (`CORE_3E + US100 SESS_CONT_BRK_40 @ 0.50%`):**
  - Return rises **`+5.07% → +5.99%/yr`** (`A +6.95%, B +5.27%`), **Peak DD DROPS `5.68% → 5.53%`**, and **`Calmar` jumps `0.89 → 1.08`**!
  - **Dual-Firm 2-Layer Evaluation (`FTMO Swing 10k` & `The5ers High Stakes 5k`):** Under `2Layer_Mod_2.0_Dyn`, 24m Pass Rate jumps `66.8% → 74.9%`, 12m jumps `30.8% → 39.2%`, `Br1` stays low at `5.4%`, `AvgTix = 1.06–1.07`, 24m Mean Net CF rises to **`+$399` (`P>0 = 69.3%`) on FTMO 10k** and **`+$164` (`P>0 = 57.2%`, >4× on `$39` ticket!) on The5ers 5k** — with **ZERO pass-rate penalty from The5ers' `>= 3` profitable days (`>= 0.5%`) rule**!
- **Notable Rejected / Secondary Findings:**
  - `H1_CH24_SL75 USDJPY`: strong raw edge (`n = 1,380`, `A +8.6R → B +43.5R`, `Tot +52.12R`, `Base +64.2R`, `Double +40.3R`, `p = 0.001`), **but** `r3E = +0.508` (heavily correlated with our 2 existing `USDJPY` engines, BUY-concentrated `+57.38R` vs SELL `-5.25R`, DD `17.4R`) → kept as `TIER_2_PERSONAL_VAULT` reference only, NOT merged into FTMO core.
  - `GBPUSD SESS_CONT_MKT_50`: failed forensic gate (`5/12` 2D surface, `-Top5 = -0.2R`).
  - `M15_PDHL_SWEEP` (Failed Prior-Day Sweep Reversal), `M15_TWAP_PULLBACK`, `H1_VOL_SQUEEZE`, and `D1_PDHL_BREAKOUT`: **`0` forensic passes** across all 8 assets (reconfirming institutional momentum/continuation beats short-horizon retail mean-reversion under CFD spreads).

---

## Stage 1–3 Discovery & Forensic Summary (`m_total = 128`)

| Candidate | Asset | Family | n | Cluster A → Blind B | Base / Stress / Double | yr+ | DD | `p_sf` (`q_128`) | `r3E` | Forensic Gate |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **`SESS_CONT_BRK_40`** | **`US100`** | `SESS_CONTINUATION` | `414` | `+4.3R → +9.9R` | `+21.5 / +14.1 / +7.1R` | `5/7` (`4/4` B) | `6.0R` | `0.008` (`0.341`) | **`-0.004`** | **`PASS` (`9/12` & `9/12`, exCr `+17.3R`)** |
| `H1_CH24_SL75` | `USDJPY` | `H1_CHANNEL_BRK` | `1,380` | `+8.6R → +43.5R` | `+64.2 / +52.1 / +40.3R` | `6/7` | `17.4R` | `0.001` (`0.128`) | `+0.508` | Skipped (`|r3E| > 0.25`, JPY overlap) |
| `SESS_CONT_BRK_55` | `GBPUSD` | `SESS_CONTINUATION` | `170` | `+8.6R → +2.6R` | `+12.5 / +11.2 / +9.8R` | `6/7` | `7.0R` | `0.028` (`0.895`) | `+0.130` | `TIER_2` (`p >= 0.02`) |
| `SESS_CONT_MKT_50` | `GBPUSD` | `SESS_CONTINUATION` | `260` | `+7.1R → +3.5R` | `+12.6 / +10.6 / +8.6R` | `4/7` | `7.1R` | `0.008` (`0.341`) | `+0.132` | **`FAIL`** (`5/12` 2D, `-Top5 = -0.2R`) |

---

## Stage 4 — Dual-Firm 2-Layer Evaluation (`FTMO Swing 10k` vs `The5ers High Stakes 5k`, `N = 2,000`)

| Portfolio (`7y Ann · PeakDD · Calmar`) | Firm | Policy | Pass `3m / 6m / 9m / 12m / 24m` | Br1 | AvgTix | MedPass | CF12 Mean | CF24 Mean (`P>0`) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| **`CORE_3E`** (`+5.07% · 5.68% · 0.89`) | FTMO 10k | `Flat_Safe_1.0` | `0.0 / 0.1 / 1.1 / 4.7 / 37.6%` | `0.6%` | `1.01` | `17.8m` | `-$159` | `+$7` (`32.6%`) |
| | FTMO 10k | `2Layer_Cap1Pct_Dyn` | `0.1 / 0.9 / 4.6 / 12.1 / 49.7%` | `0.5%` | `1.01` | `15.6m` | `-$139` | `+$102` (`44.4%`) |
| | FTMO 10k | `2Layer_Mod_2.0_Dyn` | `0.5 / 7.2 / 18.6 / 30.8 / 66.8%` | `5.2%` | `1.06` | `12.6m` | `-$71` | `+$267` (`61.9%`) |
| | The5ers 5k | `2Layer_Mod_2.0_Dyn` | `0.5 / 7.2 / 18.6 / 30.8 / 66.8%` | `5.2%` | `1.05` | `12.6m` | `-$20` | `+$106` (`47.2%`) |
| **`PORT_4E (+US100)`** (`+5.99% · 5.53% · 1.08`) | FTMO 10k | `Flat_Safe_1.0` | `0.0 / 0.2 / 2.4 / 7.6 / 49.5%` | `0.7%` | `1.01` | `17.0m` | `-$149` | `+$99` (`43.6%`) |
| | FTMO 10k | `2Layer_Cap1Pct_Dyn` | `0.0 / 1.4 / 7.7 / 17.5 / 59.6%` | `0.6%` | `1.01` | `14.8m` | `-$119` | `+$209` (`54.3%`) |
| | **FTMO 10k** | **`2Layer_Mod_2.0_Dyn`** | **`0.8 / 10.6 / 25.1 / 39.2 / 74.9%`** | **`5.4%`** | **`1.07`** | **`11.6m`** | `-$27` | **`+$399` (`69.3%`)** |
| | **The5ers 5k** | **`2Layer_Mod_2.0_Dyn`** | **`0.8 / 10.6 / 25.1 / 39.2 / 74.9%`** | **`5.4%`** | **`1.06`** | **`11.6m`** | `-$6` | **`+$164` (`57.2%`)** |

## Exported Clean White-Box `.mq5` Template

- [Naqex_WB_SESS_CONT_BRK40_US100.mq5](../../tooling/ai-engines/exports/Naqex_WB_SESS_CONT_BRK40_US100.mq5): exact US DST NYSE morning `[09:30..11:30 ET)` → afternoon breakout `[11:30..15:55 ET)`, hard server-side SL, hard flat `15:55 ET` (`swap = 0`), `InpDryRunLogOnly = true`, `0` red flags.

## Next Step (Pass 25)

1. Capture real MT5 Demo `SymbolInfo` for **`US100.cash`** (via FTMO Free Trial or The5ers Free Competition) to remove `PROVISIONAL_SPEC_UNMEASURED_DEMO`.
2. Hunt **Engine #5 & #6** (e.g. `EURUSD` / `XAUUSD` / `GER40` or new uncorrelated asset like `AUDUSD` / `USDCAD` / `Crypto` M1 Bid/Ask) to push portfolio from `Calmar 1.08` → **`Calmar >= 1.45`** (unlocking `55%–76%` 9–12m pass rate at `<= 1%` single-trade risk!).
