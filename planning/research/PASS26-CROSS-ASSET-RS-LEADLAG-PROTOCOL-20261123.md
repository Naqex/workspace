# Pass 26 Protocol — Cross-Asset Relative Strength, Currency-Basket Momentum & Intermarket Lead-Lag (`m_total = 34`, 12 Native M1 Bid/Ask Assets)

- **Date:** `2026-11-23`
- **Holdout Lock:** `planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json` (`sha256: f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486`, `holdout_rows = 0`, `< 2025-01-01T00:00:00Z`).
- **Execution Safety:** `OrderSend = 0`; `network_calls = 0`; all signals 100% causal on completed prior minutes/windows; hard server-side SL on every trade; intraday hard flat (`swap = 0`).
- **Parent Baseline:** Pass 24/25 4-Engine Core (`PORT_4E`: `USDJPY Tokyo` + `USDJPY EXP080` + `GBPUSD VOL_HIGH` + `US100 SESS_CONT_BRK_40*`, `7y Ann = +5.99%`, `Peak DD = 5.53%`, **`Calmar = 1.08`**).
- **Synchronized Data Universe:** D: SSD Hot Cache (`626.8 MB`, `12` assets, 100% `native_Ask = true`, ~30.9M paired M1 bars): `USDJPY`, `GBPUSD`, `EURUSD`, `GBPJPY`, `AUDUSD`, `USDCAD`, `EURJPY`, `XAUUSD`, `US500`, `US100`, `GER40`, `BTCUSD`.

## 5 Orthogonal Cross-Asset / Intermarket Families (`m_total = 34`, all `swap = 0`)

1. **`FX_CS_MOMENTUM` (`8` specs — Cross-Sectional FX Strongest/Weakest Pair Selection):**
   - At causal decision timestamp (`07:00`, `09:00`, or `12:00 UTC`), compute ATR-normalized return over completed prior `K` hours for all 7 FX pairs. Trade ONLY the #1 extreme pair exceeding `min_z` (`SL = 0.75 ATR`, flat `20:55 UTC`):
     - `FX_TOP1_07U_LB6_Z30`, `FX_TOP1_07U_LB12_Z40`, `FX_TOP1_09U_LB6_Z30`, `FX_TOP1_12U_LB5_Z35`, `FX_TOP1_12U_LB5_Z50`, `FX_TOP1_12U_LB12_Z40`, `FX_REV1_12U_LB5_Z70` (extreme fade), `FX_USD_BASKET_12U_Z35` (macro USD basket factor driving strongest non-JPY USD major).
2. **`CURRENCY_FACTOR_PAIRING` (`6` specs — Decomposed G6 Currency Strength Matrix `USD/EUR/GBP/JPY/AUD/CAD`):**
   - Decompose causal `00→07 UTC` or `07→12 UTC` returns into 6 individual currency factors, rank all 7 pairs by `S(BASE) - S(QUOTE)`, and enter the #1 ranked pair exceeding threshold (including dedicated `NOJPY` variants strictly excluding `USDJPY` for zero overlap!):
     - `CCY_MAT_07U_ALL_S40`, `CCY_MAT_07U_NOJPY_S40`, `CCY_MAT_12U_ALL_S40`, `CCY_MAT_12U_ALL_S60`, `CCY_MAT_12U_NOJPY_S40`, `CCY_MAT_12U_NOJPY_S60`.
3. **`IDX_CROSS_LEADLAG` (`8` specs — Europe→US Lead-Lag & `US100` vs `US500` Relative Strength):**
   - `EU_LEAD_US100_MOM_40`, `EU_LEAD_US100_MOM_60`, `EU_LEAD_US500_MOM_40`, `EU_LEAD_US100_FADE_60` (causal `GER40` move from `08:00 Berlin` to `09:30 ET` strictly BEFORE NYSE open → trade `US100`/`US500` NYSE cash session `SL = 0.75 ATR`, flat `15:55 ET`).
   - `IDX_RS_US100_LEAD_1130`, `IDX_RS_US500_CATCHUP_1130`, `IDX_RS_BOTH_AGREE_US500_1130` (causal `09:30–11:30 ET` relative performance of `US100` vs `US500` → afternoon trade on `US100`/`US500`), `IDX_RS_GER40_NY_OPEN` (causal first 15m NYSE `US100` impulse → `GER40` late-session continuation to `16:30 Berlin`).
4. **`MACRO_GOLD_CROSS` (`6` specs — Intermarket Macro Signals for `XAUUSD`):**
   - `XAU_MACRO_CONF_07U_35`, `XAU_MACRO_CONF_12U_35`, `XAU_MACRO_CONF_12U_50` (trade `XAUUSD` only when Gold return agrees with `-USD_factor`), `XAU_USD_LEADLAG_12U_40` (USD basket moved strongly while Gold lagged → catch-up), `XAU_EXP80_USD_CONF` (`XAUUSD` Daily-Open 0.80 breakout confirmed by causal `-USD_factor` at trigger minute), `XAU_RISKOFF_CONF_12U` (`XAUUSD` + `JPY` aligned vs `GER40` weak).
5. **`INTERMARKET_CONFIRM_BREAKOUT` (`6` specs — Peer-Confirmed Intraday Breakouts):**
   - `EUR_CONF_GBP_EXP65`, `EUR_CONF_GBP_EXP80`, `AUD_CONF_XAU_USD_EXP65`, `CAD_CONF_USD_EXP65`, `GER40_CONF_US_PRE_EXP65`, `GBP_CONF_EUR_EXP80` (daily-open expansion breakout ONLY when peer asset is causally moving in the same macro direction `>= 0.25 ATR` at the trigger minute!).

## Strict Discovery, Forensic & Dual-Firm Promotion Gates

1. **Stage 1 — Cluster A Discovery ONLY (`2018–2020`):** `n_A >= 40`, `FTMO Stress Net_A > 0`, `PF_A >= 1.05`.
2. **Stage 2 — Blind Cluster B OOS (`2021–2024`) + Full-Space BH FDR (`m_total = 34`):**
   - `TIER_1_FTMO_READY`: `n_total >= 120`, `Cluster B > 0`, `Tot > Top10`, `Tot > Fade`, `pos_years >= 5/7`, `DD <= 15R`, `p_sf < 0.05`, `q_all <= 0.10`, `|r4E| <= 0.25`.
   - `TIER_2_PERSONAL_VAULT`: `Cluster B > 0`, `Tot > 0`, `Tot > Fade`, `pos_years >= 4/7`, `p_sf < 0.10`.
3. **Stage 3 — Deep Forensic (`validation-gates.md` §6–8):** All `TIER_1` + top orthogonal `TIER_2` (`p_sf < 0.03`, `|r4E| <= 0.25`) MUST pass 3 cost tiers (`Base / Stress / Double`), 2D stability surface (`>= 50%` cells positive in BOTH A & B), and Outlier/Crisis Stress (`Drop Top-3 > 0`, `Excl COVID 03/2020 & 2022-09/10 > 0`).
4. **Stage 4 — Dual-Firm 2-Layer Upgrade Check (`PORT_4E Calmar 1.08` → `PORT_5E/6E` on FTMO Swing 10k & The5ers High Stakes 5k).**
