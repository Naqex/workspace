# Pass 28 Pre-Registered Protocol — Final Pre-Holdout Orthogonal Discovery (`m_total = 40`), Official Red-News Guard (`±5m`) Audit & True `3–6` Month Passing Frontier

- **Date:** `2026-11-23`
- **Holdout Lock:** `holdout_rows = 0` (`< 2025-01-01T00:00:00Z`, `LOCK_SHA = e7523f...`) — strict pre-Holdout final research pass
- **Execution Safety:** `OrderSend = 0`, `network_calls = 0` during discovery/backtest
- **Baseline Frozen Core (Pass 27 Exact M1 Floating Equity):**
  - `PORT_5E_RAW`: `+6.89%/yr`, `DailyDD 1.95%`, `FloatPeakDD 6.69%`, `Calmar 1.03`
  - `PORT_7E_P1_TURBO`: `+7.70%/yr`, `DailyDD 1.96%`, `FloatPeakDD 7.38%`, `Calmar 1.04`

---

## 1. Track 1 — Final Pre-Holdout Orthogonal Discovery (`m_total = 40`, Cluster A → Blind Cluster B)

All `40` specs are strictly causal, `swap = 0` intraday, executed on 11 synchronized Native M1 Bid/Ask assets (`USDJPY`, `GBPUSD`, `EURUSD`, `GBPJPY`, `AUDUSD`, `USDCAD`, `EURJPY`, `XAUUSD`, `US500`, `US100`, `GER40`):

1. **`IDX_INTRADAY_STRUCTURE` (10):** `GER40` morning-to-afternoon continuation (`09:00–11:30 → 17:25 CET`), `GER40` post-US-open alignment, `US100`/`US500` post-`10:00 ET` macro-settle breakout (immune to `08:30`/`10:00 ET` red news), `US100`/`US500` Power-Hour (`14:00–15:55 ET`), `US100` vs `GER40` relative strength (`11:30 ET`), `GER40` vs `EURUSD` alignment.
2. **`GOLD_INSTITUTIONAL_SESSIONS` (8):** `XAUUSD` London-to-NY continuation (breakout & market), COMEX drive (`08:20–10:30 ET`) afternoon breakout & market (post-macro), Gold vs `US100` safe-haven RS (`11:30 ET`), Post-London PM Fix (`15:00` London), Multi-day compressed Gold expansion (`ATR5/ATR20 < 0.85`).
3. **`RISK_REGIME_CROSS_ASSET` (8):** Equity-confirmed `AUDUSD`, `EURJPY`, `GBPJPY`, `USDCAD` NY continuation (`11:30 ET`); `GER40`-confirmed London `EURUSD`/`GBPUSD` (`10:00 UTC`); Equity+USD aligned `USDJPY` (`10:00 ET`); Early London `08:00 UTC` G6 USD Basket.
4. **`CALENDAR_INTRADAY_FLOWS` (6):** Turn-of-Month intraday long-only `swap = 0` on `US100`, `US500`, `XAUUSD` (raw & post-`10:00 ET` confirmed); Mon–Tue early-week `US500` continuation; Month-end `14:00–16:00 London` USD basket rebalancing.
5. **`VOL_COMPRESSION_REGIME_EXP` (8):** Prior completed `ATR5/ATR20 < 0.85` compression regime → `0.75 ATR` daily-open expansion across `US100`, `US500`, `GER40`, `EURUSD`, `AUDUSD`, `USDCAD`, `EURJPY`, `GBPUSD`.

**Strict Qualification Gates (unchanged):**
- Stage 1 Cluster A (`2018–2020`): `n_A >= 40`, `net_R_A > 0`, `pf_A >= 1.05` (TOM/month-end calendar strategies allow `n_A >= 30`).
- Stage 2 Blind Cluster B (`2021–2024`): `net_R_B > 0`, full-space BH FDR across all `m = 40` specs (`p_sf < 0.05`, `q_40 <= 0.10` for Tier 1; `p_sf < 0.03` & `|r5E| <= 0.25` eligible for deep forensic), `>= 5/7` positive years, beats Fade.
- Stage 3 Deep Forensic: positive across all `3` cost tiers (`Base / Stress / Double`), `>= 50%` cells positive in BOTH A & B on 2D stability surface, positive after Drop Top-3 / Top-5 and Excl BOTH crises (`2020-03` & `2022-09/10`), exact M1 floating-equity Prague-reset upgrade check.

---

## 2. Track 2 — Official Historical Red-News Guard (`±5 min`) Impact Audit (`2018–2024`)

Using exact primary-source official US red-news release timestamps (`2018–2024`: `56` Federal Reserve FOMC `14:00 ET` statements + `84` BLS NFP first-Friday `08:30 ET` + `84` BLS US CPI `08:30 ET` = `224` official timestamps) plus a conservative US+UK superset (+ BoE/UK CPI `07:00`/`12:00` London proxies), replay exact M1 floating equity for `PORT_5E_RAW` and `PORT_7E_P1_TURBO` under:
- `N0_SWING_UNRESTRICTED` (baseline)
- `N1_FLATTEN_5M_BEFORE_NEWS` (block entries in `±5 min` AND forcibly flatten any open affected trade at `T_news - 5m` Bid/Ask so zero SL/TP can trigger inside `±2 min` — 100% compliant with FTMO Standard Funded & The5ers High Stakes!)
- `N2_SKIP_RED_NEWS_DAY` (skip affected engines entirely on red-news days)
- `N3_SUPERSET_US_PLUS_UK` (`N1` plus UK BoE/CPI proxy windows on `GBPUSD`)

---

## 3. Track 3 — True `3–6` Month Short-Horizon Passing Frontier (`N = 2,000` Exact M1 Bootstrap)

Map the exact Speed-vs-Breach-vs-Compliance Pareto frontier using the best post-Pass-28 exact M1 floating-equity ledger across:
1. **FTMO 2-Step (`10k`, `+10% / +5%`)** and **The5ers High Stakes 2-Step (`5k`, `$39`, `+10% / +5%`, `3 × 0.5%`)** at P1 multipliers `2.0×`, `2.5×`, `3.0×`, `3.5×`, `4.0×` (with internal `-3.2%` daily circuit breaker + `AMBER/RED` equity throttle), explicitly flagging single-trade risk `<= 1.0%` vs `> 1.0%` compliance boundaries!
2. **The5ers Hyper Growth 1-Step (`5k`, `+10%` SINGLE TARGET ONLY, `6%` static stop-out, `3%` non-breaching Daily Pause!)** across `1.5×`, `2.0×`, `2.5×`, `3.0×` to test empirically whether 1-Step breaks the `<= 6` month median barrier cleanly.
