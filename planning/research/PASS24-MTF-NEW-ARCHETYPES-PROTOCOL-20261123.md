# Pass 24 Protocol — Multi-Timeframe (`M15/H1/D1`) New Structural Families Discovery (`m_total = 128`) & Dual-Firm 2-Layer Challenge Evaluation

- **Date:** `2026-11-23`
- **Holdout Lock:** `planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json` (`sha256: f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486`, `holdout_rows = 0`, `< 2025-01-01T00:00:00Z`).
- **Execution Safety:** `OrderSend = 0`; zero edits to `projects/vi-dubber` or `projects/trader` pin; any exported `.mq5` MUST enforce `InpDryRunLogOnly = true` and visible server-side SL.
- **Data Universe (D: SSD Hot Cache, `433.0 MB`, 100% `native_Ask = true`, zero network):**
  - FX & Metals (`5`): `USDJPY`, `GBPUSD`, `EURUSD`, `GBPJPY`, `XAUUSD` (bound FTMO Swing Demo specs `8fd77ef`).
  - Cash Indices (`3`, tagged `PROVISIONAL_SPEC_UNMEASURED_DEMO` for `US100`/`GER40`): `US500`, `US100`, `GER40` (`$0` commission; `US500` stress `0.75 pt/side`, `US100`/`GER40` stress `2.0 pts/side` on top of real M1 Bid/Ask spread).
- **Parent Baseline:** Pass 22/23 3-Engine Core (`USDJPY Tokyo-box` + `USDJPY EXP080` + `GBPUSD VOL_HIGH`, `Calmar 0.83`, `+5.07%–5.33%/yr`, Peak DD `6.09%–6.46%`).

## 6 Orthogonal New Structural Families (`16` Specs × `8` Assets = `m_total = 128`, all `swap = 0`)

All families are genuinely distinct from closed families (`ORB`, `WB_OPEN_EXPANSION`, `SuperTrend`, `DON20_POS`, academic fix/IBS/NR4). Every order enforces: max 1 trade/day/spec, hard SL attached at entry, intraday forced flat (`20:55 UTC` FX/Gold, cash session close Indices), **causal stop fill (`max(level, ask_open)` BUY / `min(level, bid_open)` SELL)**, **next-M1 fill after M15 bar close** for M15 confirmation families, and conservative `SL hit first` on the entry minute.

1. **`H1_CHANNEL_BRK` (`3` specs — H1 Multi-Session Channel Breakout):**
   - Break of causal rolling completed prior `12h` or `24h` H1 high/low inside active session (`07:00–16:00 UTC` FX/Gold; `+30..+300 min` Indices): `H1_CH12_SL75`, `H1_CH24_SL75`, `H1_CH24_TREND_SL75` (aligned with prior completed D1 EMA50).
2. **`H1_VOL_SQUEEZE` (`3` specs — Pre-Session Compression Breakout):**
   - Tight causal pre-window compression (`range <= thr * D1_ATR`) followed by breakout of the compressed envelope (`SL = 0.65 * ATR`): `SQZ_LDN_4H_045` (`03:00–07:00` box → `07:00–15:00`), `SQZ_NY_4H_045` (`08:00–12:00` → `12:00–17:00`), `SQZ_NY_6H_055` (`06:00–12:00` → `12:00–17:00`). On indices: first `60m` / `90m` / `120m` compression (`<= 0.45 / 0.55 / 0.65 * ATR`) → remainder of session breakout.
3. **`SESS_CONTINUATION` (`3` specs — Cross-Session Institutional Continuation):**
   - Strong causal London morning (`07:00–12:00 UTC`; or first `120m` on US500/US100 / first `240m` on GER40) directional close (`|move| >= k * ATR` and close in outer 30% of morning range) → NY continuation (`12:00–17:00 UTC`): `SESS_CONT_BRK_40` (stop at morning extreme), `SESS_CONT_BRK_55`, `SESS_CONT_MKT_50` (causal next-minute market continuation at `12:00 UTC` with `SL = 0.65 * ATR`).
4. **`M15_PDHL_SWEEP` (`3` specs — Causal M15 Failed Prior-Day High/Low Sweep Reversal):**
   - Price sweeps beyond prior completed D1 High (`PDH`) or Low (`PDL`) during active session, then an M15 bar closes strictly back inside `[PDL, PDH]`; enter on next M1 open with SL beyond sweep extreme (clamped `[0.35, 1.00] * ATR`): `PDHL_SWEEP_FLAT`, `PDHL_SWEEP_TP2R` (hard `2.0R` TP or flat), `PDHL_SWEEP_TREND` (only trend-aligned sweeps vs D1 EMA50).
5. **`M15_TWAP_PULLBACK` (`2` specs — Causal Session Equilibrium Pullback Continuation):**
   - Early drive (`|price - open| >= k * ATR` within first 3h) followed by M15 pullback touching cumulative session causal `TWAP` (equal-weighted M1 mid since session open) and closing back in trend direction; enter next M1 open, `SL = 0.60 * ATR`: `TWAP_PB_40`, `TWAP_PB_55`.
6. **`D1_PDHL_BREAKOUT` (`2` specs — Causal Prior-Day Range Breakout):**
   - Breakout beyond exact `PDH`/`PDL` inside active window (`SL = 0.75 * ATR`): `PDHL_BRK_ALL`, `PDHL_BRK_NR` (only after narrow prior day `prev_range <= 0.80 * ATR`).

## Strict Discovery, Forensic & Dual-Firm Promotion Gates

1. **Stage 1 — Cluster A Discovery ONLY (`2018–2020`, blind to `2021–2024`):** `n_A >= 50`, `FTMO Stress Net_A > 0`, `PF_A >= 1.05`.
2. **Stage 2 — Blind Cluster B OOS (`2021–2024`) + Full-Space BH FDR (`m_total = 128`):**
   - `TIER_1_FTMO_READY` requires: `n_total >= 150`, `Cluster B > 0`, `Tot > Top10`, `Tot > Fade`, `pos_years >= 5/7`, `closed_DD <= 15R`, `p_sf < 0.05`, `q_all <= 0.10` (over ALL `128` specs), and `|r3E| <= 0.25`.
   - `TIER_2_PERSONAL_VAULT`: `Cluster B > 0`, `Tot > 0`, `Tot > Fade`, `pos_years >= 4/7`, `p_sf < 0.10`.
3. **Stage 3 — Mandatory Deep Forensic (per `validation-gates.md` §6–8):**
   - All `TIER_1` (and top orthogonal `TIER_2` with `p < 0.02`) MUST pass: 3 cost tiers (`Base`, `Stress`, `Double Stress`), **Dual 2D parameter surfaces**, **Outlier/Crisis Stress** (`-Top3`, `-Top5`, Excl COVID `2020-03` & `2022-09/10`), and 4-axis breakdown (`BUY`/`SELL`).
4. **Stage 4 — Dual-Firm 2-Layer Challenge Evaluation (`3m / 6m / 9m / 12m / 24m`):**
   - Compare **3-Engine Core** vs **4/5-Engine Upgraded Core** across BOTH:
     - **FTMO 2-Step Swing `10k`** (`$168` fee, `10%/5%`, `>= 4` trading days, `100%` fee refund on 1st payout), AND
     - **The5ers High Stakes `5k`** (`$39` fee, `THE5ERS_DECLARED_UNMEASURED_MT5`: `10%/5%`, `>= 3` profitable days `>= +0.5%` per phase, `10%/20%` Hub Credit + `70%` cash refund, min `$150` payout after 80% split),
   - Under BOTH `Flat Safe (1.0/1.0/1.0)` AND `2-Layer Dynamic Cushion / Two-Regime` **strictly enforcing `<= 1.0%` max single-trade-idea risk** for full compliance with FTMO/The5ers rules.
