# Pass 26 Report — Cross-Asset Relative Strength, Currency-Basket Momentum & Intermarket Lead-Lag (`m_total = 34`)

- **Date:** `2026-11-23`
- **Protocol Commit:** `6b5938e7f087b2016777dd930c4657dbc0f230e0` ([PASS26 Protocol](PASS26-CROSS-ASSET-RS-LEADLAG-PROTOCOL-20261123.md))
- **Holdout Lock:** `holdout_rows = 0` (`< 2025-01-01T00:00:00Z`) · `OrderSend = 0` · `network_calls = 0`
- **Artifact on E: Cold Archive:** `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\pass26-cross-asset-rs-20261123\pass26-result.json`

## Executive Summary & Verdict

- **Verdict:** **`IDX_RS_US100_LEAD_1130_QUALIFIED_AS_PROVISIONAL_ENGINE5 (PORT5E CALMAR 1.08 -> 1.14 · 12M MEAN CF FLIPS POSITIVE ON BOTH FTMO & THE5ERS)`** — plus `FX_USD_BASKET_12U_Z35` qualified as **`TIER_2_PERSONAL_VAULT`** on 100% bound FTMO Demo FX specs!
- **Discovery Sweep (`m_total = 34` across 5 orthogonal cross-asset families on 11 synchronized Native M1 Bid/Ask assets):**
  - `6 / 34` passed Cluster A discovery gate (`28 / 34` filtered out strictly on Cluster A).
  - **`2 / 2` forensic targets PASSED all deep forensic gates (`3` cost tiers, `6/9` 2D surface, Outlier/Crisis Stress):**
    1. **`IDX_RS_US100_LEAD_1130`** (*Tech vs Broad-Market Relative Strength: `US100` vs `US500` over `09:30–11:30 ET` → `11:30 ET` entry on `US100`, `swap = 0`*):
       - `n = 261`, Cluster A `+5.7R` → **Blind Cluster B `+6.5R`**, **`6 / 7` years positive**, **`p_sf = 0.003`**, **`q_34 = 0.102`**!
       - **3 Cost Tiers ALL positive:** `Base +16.41R` · `Stress +12.22R` · **`Double Stress +8.19R`**.
       - **Perfect 2-Way Balance (zero beta):** **`BUY +5.9R` AND `SELL +6.4R`**.
       - **2D Stability (`thr × sl`):** **`6 / 9` cells** positive in BOTH A & B.
       - **Outlier/Crisis Stress:** Drop Top-3 `+7.1R`, Drop Top-5 `+4.4R`, **Excl BOTH COVID `2020-03` & `2022-09/10` = `+12.4R`**!
       - **Low correlation with 4-Engine Core (`r4E = +0.100`).** *(Honest caveat: shares `US100` symbol with Engine #4 and awaits Demo `US100.cash` spec capture.)*
    2. **`FX_USD_BASKET_12U_Z35`** (*Macro USD Basket Factor at `12:00 UTC` trading strongest aligned non-JPY USD Major `GBPUSD/EURUSD/AUDUSD/USDCAD`, `swap = 0`, 100% bound FTMO Demo specs `8fd77ef`*):
       - `n = 195`, Cluster A `+7.3R` → Blind Cluster B `+2.7R`, **`5 / 7` years positive**, **Closed DD only `4.7R`**, `p_sf = 0.014`, `q_34 = 0.238`, **`r4E = +0.128`**.
       - **3 Cost Tiers ALL positive:** `Base +11.60R` · `Stress +9.99R` · **`Double Stress +8.40R`**; `6 / 9` 2D cells; Drop Top-5 `+1.0R`, Excl BOTH crises `+2.6R`.
       - *Honest caveats:* Concentrated on `SELL (+10.9R)` vs `BUY (-0.9R)`, and adding at full `0.50%` lowers Calmar `1.08 → 0.91` (`Peak DD 7.20%`) → kept in **`TIER_2_PERSONAL_VAULT`** (candidate for smaller `0.25%` satellite weight rather than full `0.50%`).
- **5-Engine Portfolio Milestone (`PORT5E_PLUS_IDX_RS_US100_LEAD_1130`):**
  - Return jumps **`+5.99% → +6.91%/yr`** (`A +7.64%, B +6.37%`), `Peak DD = 6.06%`, **`Calmar` reaches new record `1.14`**!
  - Under `2Layer_Mod_2.0_Dyn` (`N = 2,000` bootstrap):
    - **12-Month Pass Rate reaches `47.0%`** (`24m = 82.7%`, `Br1 = 6.4%`, `AvgTix = 1.07–1.08`, `MedPass = 10.9m`)!
    - **12-Month Mean Net Cashflow FLIPS POSITIVE for the FIRST TIME on BOTH firms (`+$27` FTMO 10k, `+$11` The5ers 5k)!**
    - **24-Month Mean Net Cashflow:** **`+$552` (`P>0 = 77.0%`) on FTMO 10k** and **`+$234` (`P>0 = 66.7%`, 6× `$39` ticket!) on The5ers 5k**!
  - With all 6 engines (`PORT6E_ALL_QUALIFIED_R50`): **`+7.47%/yr`**, `12m Pass = 50.2%`, `24m Pass = 83.2%`, `CF12 = +$56 / +$23`, `CF24 = +$634 (79.1%) / +$275 (69.2%)`, though `Peak DD` rises to `7.48%` (`Calmar 1.00`).

---

## Stage 1–3 Discovery & Forensic Summary (`m_total = 34`)

| Strategy | Family | n | Cluster A → Blind B | Base / Stress / Double | yr+ | DD | `p_sf` (`q_34`) | `r4E` | Forensic Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **`IDX_RS_US100_LEAD_1130`** | `IDX_CROSS_LEADLAG` | `261` | `+5.7R → +6.5R` | `+16.4 / +12.2 / +8.2R` | `6/7` | `8.3R` | `0.003` (`0.102`) | `+0.100` | **`PASS` (`6/9`, B:`+5.9`/S:`+6.4`, exCr `+12.4R`)** |
| **`FX_USD_BASKET_12U_Z35`** | `FX_CS_MOMENTUM` | `195` | `+7.3R → +2.7R` | `+11.6 / +10.0 / +8.4R` | `5/7` | `4.7R` | `0.014` (`0.238`) | `+0.128` | **`PASS` (`6/9`, B:`-0.9`/S:`+10.9`, exCr `+2.6R`)** |
| `XAU_EXP80_USD_CONF` | `MACRO_GOLD_CROSS` | `346` | `+2.9R → +3.2R` | `+13.3 / +6.2 / -5.0R` | `5/7` | `8.3R` | `0.044` (`0.498`) | `+0.096` | `TIER_2` (fails Double `-5.0R`) |
| `IDX_RS_US500_CATCHUP_1130` | `IDX_CROSS_LEADLAG` | `174` | `+3.3R → -2.4R` | `+6.8 / +0.9 / -4.5R` | `3/7` | `8.5R` | `0.121` (`1.000`) | `+0.136` | `TIER_3_DEAD_NO_EDGE` |
| `AUD_CONF_XAU_USD_EXP65` | `INTERMARKET_CONFIRM` | `366` | `+8.3R → -17.8R` | `-5.9 / -9.5 / -13.1R` | `4/7` | `21.1R` | `0.291` (`1.000`) | `+0.104` | `TIER_3_DEAD_NO_EDGE` |
| `FX_TOP1_12U_LB5_Z50` | `FX_CS_MOMENTUM` | `686` | `+8.9R → -29.0R` | `-14.9 / -20.0 / -25.1R` | `3/7` | `37.4R` | `0.512` (`1.000`) | `+0.191` | `TIER_3_DEAD_NO_EDGE` |

---

## Stage 4 — Dual-Firm 2-Layer Upgrade Check (`FTMO Swing 10k` vs `The5ers High Stakes 5k`, `N = 2,000`)

| Portfolio (`7y Ann · PeakDD · Calmar`) | Firm | Policy | Pass `3m / 6m / 9m / 12m / 24m` | Br1 | AvgTix | MedPass | CF12 Mean | CF24 Mean (`P>0`) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| **`PORT_4E_BASE`** (`+5.99% · 5.53% · 1.08`) | FTMO 10k | `2Layer_Mod_2.0_Dyn` | `0.8 / 10.6 / 25.1 / 39.2 / 74.9%` | `5.4%` | `1.07` | `11.6m` | `-$27` | `+$399` (`69.3%`) |
| | The5ers 5k | `2Layer_Mod_2.0_Dyn` | `0.8 / 10.6 / 25.1 / 39.2 / 74.9%` | `5.4%` | `1.06` | `11.6m` | `-$6` | `+$164` (`57.2%`) |
| **`PORT_5E (+US100_RS)`** (`+6.91% · 6.06% · 1.14`) | FTMO 10k | `Flat_Safe_1.0` | `0.0 / 0.7 / 5.2 / 13.1 / 60.4%` | `1.2%` | `1.02` | `15.9m` | `-$130` | `+$221` (`54.6%`) |
| | FTMO 10k | `2Layer_Cap1Pct_Dyn` | `0.0 / 3.0 / 12.0 / 25.4 / 67.7%` | `0.8%` | `1.02` | `13.7m` | `-$85` | `+$345` (`63.9%`) |
| | **FTMO 10k** | **`2Layer_Mod_2.0_Dyn`** | **`1.6 / 14.7 / 31.1 / 47.0 / 82.7%`** | **`6.4%`** | **`1.08`** | **`10.9m`** | **`+$27`** | **`+$552` (`77.0%`)** |
| | **The5ers 5k** | **`2Layer_Mod_2.0_Dyn`** | **`1.6 / 14.7 / 31.1 / 47.0 / 82.7%`** | **`6.4%`** | **`1.07`** | **`10.9m`** | **`+$11`** | **`+$234` (`66.7%`)** |
| **`PORT_6E (+US100_RS +USD_BSK)`** (`+7.47% · 7.48% · 1.00`) | FTMO 10k | `2Layer_Mod_2.0_Dyn` | `2.5 / 18.1 / 34.4 / 50.2 / 83.2%` | `9.9%` | `1.13` | `10.3m` | `+$56` | `+$634` (`79.1%`) |
| | The5ers 5k | `2Layer_Mod_2.0_Dyn` | `2.4 / 18.1 / 34.4 / 50.2 / 83.2%` | `9.9%` | `1.12` | `10.3m` | `+$23` | `+$275` (`69.2%`) |

## Next Actionable Milestone

1. **Snapshot `US100.cash` contract spec from FTMO Free Trial (existing Demo credentials!) + optionally The5ers Free Competition** to remove `PROVISIONAL_SPEC_UNMEASURED_DEMO` on BOTH Engine #4 (`SESS_CONT_BRK_40`) and Engine #5 (`IDX_RS_US100_LEAD_1130`), and verify exact intraday overlap & inverse-DD optimal weighting across all 5–6 engines!
2. Keep Holdout `>= 2025-01-01` strictly sealed (`holdout_rows = 0`) until Demo spec verification + exact M1 floating-equity 5/6-engine Prague-reset audit are complete.
