# Pass 25 Protocol — 4 New Native M1 Bid/Ask Assets (`AUDUSD`, `USDCAD`, `EURJPY`, `BTCUSD`) & Orthogonal Engine #5/#6 Discovery (`m_total = 136`)

- **Date:** `2026-11-23`
- **Holdout Lock:** `planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json` (`sha256: f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486`, `holdout_rows = 0`, hard exclusive ceiling `< 2025-01-01T00:00:00Z`).
- **Execution Safety:** `OrderSend = 0`; zero edits to `projects/vi-dubber` or `projects/trader` pin; any exported `.mq5` MUST enforce `InpDryRunLogOnly = true` and visible server-side SL.
- **Parent Baseline:** Pass 24 4-Engine Core (`PORT_4E`: `USDJPY Tokyo` + `USDJPY EXP080` + `GBPUSD VOL_HIGH` + `US100 SESS_CONT_BRK_40*`, `7y Ann = +5.99%`, `Peak DD = 5.53%`, **`Calmar = 1.08`**).

## Lane A — Paired M1 Bid/Ask Data Sealing (`2018–2024`, `< 2025-01-01T00:00:00Z`)

Fetch paired M1 `bid` + `ask` via pinned local `dukascopy-node` (`fetch_asset_m1_seal.mjs`), clamp any 1-tick crossed anomaly conservatively (`ask = max(ask, bid)`), assert `START <= first <= last < STOP` (`holdout_rows = 0`), SHA-seal to Zstd Parquets on E: Cold Archive and sync into D: SSD Hot Cache (expanding Hot Cache from `8` → **`12` Native Bid/Ask assets**):

1. **`AUDUSD`** (`audusd`, scale `100000`, `native_Ask: true`): bound FTMO Swing Demo spec (`8fd77ef`, `$5/lot`, `currency_profit = USD`, pre-2018 D1 warm-up sealed).
2. **`USDCAD`** (`usdcad`, scale `100000`, `native_Ask: true`): bound FTMO Swing Demo spec (`8fd77ef`, `$5/lot`, `currency_profit = CAD`, exact conversion `1.0 / exit_price`, pre-2018 D1 warm-up sealed).
3. **`EURJPY`** (`eurjpy`, scale `1000`, `native_Ask: true`): bound FTMO Swing Demo spec (`8fd77ef`, `$5/lot`, `currency_profit = JPY`, exact conversion `1.0 / usdjpy_close`, pre-2018 D1 warm-up sealed).
4. **`BTCUSD`** (`btcusd`, scale `100`, `native_Ask: true`): 24/7 crypto CFD, tagged **`PROVISIONAL_CRYPTO_SPEC_UNMEASURED_DEMO`**; conservative percentage slippage stress on top of real M1 Bid/Ask spread (`Base = 0.05%` RT, `Stress = 0.15%` RT, `Double = 0.30%` RT, `$0` fixed commission).

## Lane B — Strict Causal Discovery (`34` Specs × `4` Assets = `m_total = 136`, all `swap = 0`)

Every spec uses 100% causal stop fills (`max(level, ask_open)` BUY / `min(level, bid_open)` SELL), next-M1 fill after M15 close for M15 families, conservative same-minute SL-first check, max 1 trade/day, intraday hard flat (`20:55 UTC`, `swap = 0`):

1. **Proven Expansion & Session-Box Grammar (`18` specs/asset):**
   - `WB_OPEN_EXPANSION` (`12` specs: `trig ∈ {0.65, 0.80, 1.00}` × `regime ∈ {NONE, EMA50_TREND, VOL_HIGH, VOL_LOW}`, `SL = 0.75 ATR`)
   - `WB_SESSION_BOX` (`6` specs: `[00..07)`, `[02..08)`, `[07..11)` UTC × `max_box_atr`, `SL = 0.75 ATR`)
2. **Pass 24 MTF 6-Family Grammar (`16` specs/asset):**
   - `H1_CHANNEL_BRK` (`3`), `H1_VOL_SQUEEZE` (`3`), `SESS_CONTINUATION` (`3`), `M15_PDHL_SWEEP` (`3`), `M15_TWAP_PULLBACK` (`2`), `D1_PDHL_BREAKOUT` (`2`).

## Strict Discovery, Forensic & Dual-Firm Upgrade Gates

1. **Stage 1 — Cluster A Discovery ONLY (`2018–2020`, blind to `2021–2024`):** `n_A >= 50`, `FTMO Stress Net_A > 0`, `PF_A >= 1.05`.
2. **Stage 2 — Blind Cluster B OOS (`2021–2024`) + Full-Space BH FDR (`m_total = 136`):**
   - `TIER_1_FTMO_READY` requires: `n_total >= 150`, `Cluster B > 0`, `Tot > Top10`, `Tot > Fade`, `pos_years >= 5/7`, `closed_DD <= 15R`, `p_sf < 0.05`, `q_all <= 0.10`, `|r4E| <= 0.25`.
   - `TIER_2_PERSONAL_VAULT`: `Cluster B > 0`, `Tot > 0`, `Tot > Fade`, `pos_years >= 4/7`, `p_sf < 0.10`.
3. **Stage 3 — Mandatory Deep Forensic (`validation-gates.md` §6–8):**
   - All `TIER_1` + top orthogonal `TIER_2` (`p_sf < 0.02`, `|r4E| <= 0.25`) MUST pass: 3 cost tiers (`Base`, `Stress`, `Double`), **Dual 2D stability surfaces** (`>= 50%` cells positive in BOTH A & B), and **Outlier/Crisis Stress** (`Drop Top-3 > 0`, `Excl COVID 03/2020 & 2022-09/10 > 0`).
4. **Stage 4 — Dual-Firm 2-Layer Upgrade Evaluation (`FTMO Swing 10k` + `The5ers High Stakes 5k`):**
   - Compare `PORT_4E (Calmar 1.08)` vs `PORT_5E` / `PORT_6E` across `3m / 6m / 9m / 12m / 24m` under `Flat_Safe_1.0`, `2Layer_Cap1Pct_Dyn`, and `2Layer_Mod_2.0_Dyn`.
