# Pass 25 Report — 4 New Native M1 Bid/Ask Assets (`AUDUSD`, `USDCAD`, `EURJPY`, `BTCUSD`) & Orthogonal Engine #5/#6 Discovery (`m_total = 136`)

- **Date:** `2026-11-23`
- **Protocol Commit:** `504232d819e82064bc273ddba96762bb760c0115` ([PASS25 Protocol](PASS25-4NEW-ASSETS-ENGINE56-PROTOCOL-20261123.md))
- **Holdout Lock:** `holdout_rows = 0` (`< 2025-01-01T00:00:00Z`) · `OrderSend = 0`
- **Artifact on E: Cold Archive:** `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\pass25-4new-assets-20261123\pass25-result.json`

## Executive Summary & Verdict

- **Verdict:** **`NO_ENGINE5_PROMOTED_KEEP_4ENGINE_CORE_CALMAR_108 · HOT_CACHE_EXPANDED_TO_12_NATIVE_BIDASK_ASSETS (626.8 MB)`**
- **Lane A (Data Sealing — `COMPLETE`):** Fetched, SHA-sealed, and cached **4 new paired M1 Bid/Ask assets** (`>11.2M` bars, `< 2025-01-01`, `holdout_rows = 0`):
  - **`AUDUSD`** (`2,604,015` mins, `39.2 MB`), **`USDCAD`** (`2,603,221` mins, `39.4 MB`), **`EURJPY`** (`2,610,264` mins, `41.4 MB`, median spread `0.5–1.2 pip`), and **`BTCUSD`** (`3,385,938` mins, `74.0 MB`, real CFD median spread **`67.7–120.0 USD`**).
  - Total D: SSD Hot Cache now holds **`12` Native M1 Bid/Ask assets (`626.8 MB`, ~30.9M paired M1 bars, `holdout_rows = 0`)**.
- **Lane B (Causal Discovery `m_total = 136` — `0 / 136 TIER_1 · 1 / 136 TIER_2 REJECTED BY 2D SURFACE`):**
  - `130 / 136` filtered out strictly on Cluster A (`2018–2020`).
  - **`USDCAD`: `0 / 34`** passed Cluster A; **`AUDUSD`: `0 / 34`** survived Blind Cluster B (`3` passed A, all `3` went negative `-6.5R .. -14.8R` in B).
  - **`BTCUSD`: `0 / 34`** passed Cluster A — **crucial structural finding:** real Dukascopy CFD M1 spreads on `BTCUSD` were `112–120 USD` in `2018–2020` (`~1.2%–3.5%` per round-turn!), mathematically killing intraday `swap = 0` breakouts on retail CFD feeds. Crypto alpha requires low-fee spot/perpetual venues (e.g., `0.02%–0.05%` fee) and multi-day trend horizons rather than wide-spread CFD intraday rules.
  - **`EURJPY WB_EXP_80_VOL_LOW` (sole `TIER_2`):** `n = 183`, `A +2.7R → B +7.1R`, Tot `+9.84R` (`Base +11.2R`, `Double +8.5R`, `6/7` yr+, `p = 0.020`, `q = 1.000`, `r4E = +0.112`) — **FAILED deep forensic gate**: Dual 2D stability surfaces scored only **`3 / 9` (`trig × sl`)** and **`2 / 9` (`trig × vol_mult`)**, with returns concentrated in `BUY (+10.32R)` vs `SELL (-0.48R)` → **NOT promoted**!
- **Retained Core Portfolio (`PORT_4E_BASE`):** `USDJPY Tokyo` + `USDJPY EXP080` + `GBPUSD VOL_HIGH` + `US100 SESS_CONT_BRK_40*` (`7y Ann = +5.99%`, `Peak DD = 5.53%`, **`Calmar = 1.08`**; `2Layer_Mod_2.0_Dyn` 24m Pass **`74.9%`**, `Br1 = 5.4%`, `CF24 = +$399` FTMO 10k / `+$164` The5ers 5k).

---

## Lane A — Newly Sealed Native M1 Bid/Ask Assets (`2018–2024`, `holdout_rows = 0`)

| Asset | Dukascopy ID | Minutes (`2018–2024`) | Median Spread | Parquet Size | `native_Ask` |
|---|---|---:|---:|---:|:---:|
| **`EURJPY`** | `eurjpy` | `2,610,264` | `0.5–1.2 pip` | `41.4 MB` | **True** |
| **`USDCAD`** | `usdcad` | `2,603,221` | `~0.5–1.0 pip` | `39.4 MB` | **True** |
| **`AUDUSD`** | `audusd` | `2,604,015` | `~0.4–0.8 pip` | `39.2 MB` | **True** |
| **`BTCUSD`** | `btcusd` | `3,385,938` | `67.7–120.0 USD` | `74.0 MB` | **True** |

Total Hot Cache (`.runtime/hot-m1-cache/`): **`626.8 MB` / 12 assets** (`USDJPY`, `GBPUSD`, `EURUSD`, `GBPJPY`, `AUDUSD`, `USDCAD`, `EURJPY`, `XAUUSD`, `US500`, `US100`, `GER40`, `BTCUSD`).

---

## Lane B — Cluster A Survivors & Forensic Disposition (`m_total = 136`)

| Strategy | Asset | Family | n | Cluster A → Blind B | Stress R (Base / Dbl) | yr+ | `p_sf` (`q_136`) | `r4E` | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| `WB_EXP_80_VOL_LOW` | `EURJPY` | `WB_OPEN_EXPANSION` | `183` | `+2.7R → +7.1R` | `+9.84R` (`+11.2 / +8.5`) | `6/7` | `0.020` (`1.000`) | `+0.112` | **`TIER_2` · FAILED 2D (`3/9` & `2/9`), BUY-only (`+10.3/-0.5`) — NOT PROMOTED** |
| `SESS_CONT_MKT_50` | `AUDUSD` | `SESS_CONTINUATION` | `134` | `+5.8R → -6.6R` | `-0.79R` (`+0.8 / -2.3`) | `3/7` | `0.074` (`1.000`) | `+0.034` | `TIER_3_DEAD_NO_EDGE` |
| `SESS_CONT_BRK_40` | `AUDUSD` | `SESS_CONTINUATION` | `199` | `+4.4R → -10.8R` | `-6.46R` (`-4.2 / -8.7`) | `3/7` | `0.141` (`1.000`) | `+0.073` | `TIER_3_DEAD_NO_EDGE` |
| `SESS_CONT_BRK_40` | `EURJPY` | `SESS_CONTINUATION` | `300` | `+4.4R → -12.6R` | `-8.26R` (`-5.9 / -10.6`) | `4/7` | `0.460` (`1.000`) | `+0.107` | `TIER_3_DEAD_NO_EDGE` |
| `SESS_CONT_BRK_55` | `EURJPY` | `SESS_CONTINUATION` | `155` | `+1.4R → -10.2R` | `-8.78R` (`-7.5 / -10.0`) | `2/7` | `0.664` (`1.000`) | `+0.113` | `TIER_3_DEAD_NO_EDGE` |
| `WB_EXP_80_EMA50_TREND` | `AUDUSD` | `WB_OPEN_EXPANSION` | `286` | `+2.2R → -14.8R` | `-12.61R` (`-9.7 / -15.4`) | `1/7` | `0.247` (`1.000`) | `+0.083` | `TIER_3_DEAD_NO_EDGE` |

## Strategic Diagnosis After 12 Assets × Intraday Single-Day Rules

Across **Passes 5–25**, we have systematically exhausted single-day intraday breakout/mean-reversion rules (`swap = 0`) across **12 Native M1 Bid/Ask assets (`30.9M` bars)**, discovering **4 clean orthogonal intraday engines (`Calmar 1.08`)**:
1. `USDJPY` Tokyo-Box OCO (Engine #1)
2. `USDJPY` Daily-Open Expansion 0.80 (Engine #2)
3. `GBPUSD` Daily-Open Expansion 0.80 + `VOL_HIGH` (Engine #3)
4. `US100` NYSE Morning→Afternoon Session Continuation `SESS_CONT_BRK_40` (Engine #4 provisional — awaiting Demo MT5 spec capture)

**What clearly works vs what is saturated:**
- Simple single-day FX intraday breakouts have largely been harvested across all 7 FX pairs.
- To push from **`Calmar 1.08` → `1.45+`** without overfitting, the next orthogonal alpha frontier lies in **3 untapped structural domains**:
  1. **Cross-Asset / Relative-Strength & Basket Signals across our 12-asset Hot Cache** (e.g., USD-index / JPY-basket / Gold-vs-USDJPY / US100-vs-US500 relative intraday momentum — using 11 other assets' real-time causal M1 returns to pick the single strongest/weakest pair of the session, zero lookahead, `swap = 0`!).
  2. **Multi-Day Trend / Volatility-Breakout with Controlled Swap (`<= 2–3` days holding or zero-swap / positive-swap filtering)** on `XAUUSD`, `BTCUSD` (perpetual/spot), and `FX` (recall `NEN006 XAUUSD` had `r = -0.052` negative correlation with FX intraday core!).
  3. **Live Demo Spec Capture (`US100.cash` on FTMO Free Trial & The5ers Free Competition)** + external open-source leads placed in `D:\ANNAM\strategy-intel\inbox\`.
