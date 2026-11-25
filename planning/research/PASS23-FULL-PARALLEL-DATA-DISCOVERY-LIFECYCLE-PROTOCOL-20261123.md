# Pass 23 Protocol — Full Parallel Multi-Lane Execution (Data Seal · Nhịp 3 FTMO 2-Step Lifecycle · Engine #1 `.mq5` · Engine #4 Discovery)

- **Date:** `2026-11-23`
- **Holdout Lock:** `planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json` (`sha256: f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486`, `holdout_rows = 0`, hard exclusive ceiling `< 2025-01-01T00:00:00Z`).
- **Execution Safety:** `OrderSend = 0`; all generated `.mq5` templates MUST enforce `InpDryRunLogOnly = true` by default.
- **Parent Baseline:** Pass 22 (`5664ac2`, 3-Engine Core `USDJPY Tokyo-box` + `USDJPY EXP080` + `GBPUSD VOL_HIGH`, Prague Reset `PORT3E_075_GBP075`: `+5,07%–5,33%/yr`, Peak DD `6,09%–6,46%`, Daily `1,52%–1,53%`, Calmar `0,82–0,84`, `0` margin fails).

## Lane A — Paired M1 Bid/Ask Data Sealing (`2018–2024`, `< 2025-01-01T00:00:00Z`)

Fetch paired M1 `bid` and `ask` via pinned local `dukascopy-node` (`ignoreFlats: true`), clamp any 1-tick crossed anomaly conservatively (`ask = max(ask, bid)`), assert `START <= first <= last < STOP` (`holdout_rows = 0`), seal to SHA-verified Zstd Parquets on E: Cold Archive and sync into D: SSD Hot Cache (`.runtime/hot-m1-cache/`):

1. **`XAUUSD`** (`xauusd`, scale `100`, `native_Ask: true`): replaces `native_Ask: false` Bid-only cache to resolve `PROVISIONAL_XAU` permanently; FTMO Demo contract specs already bound (`8fd77ef` Swing / `36f1535` Standard: `contract = 100`, `commission = $0/lot`, `swap_long = -56.28`, `swap_short = -4.20`).
2. **`US100`** (`usatechidxusd`, scale `1000`, `native_Ask: true`): NYSE cash session (`09:30–15:55 America/New_York`, exact DST calendar), intraday `swap = 0`, commission `$0/lot`, **DECLARED_INDEX_PROXY** slippage (`Base = 1.0 pt/side`, `Stress = 2.0 pts/side` on top of real M1 Bid/Ask spread; contract `1.0 USD/pt`). Tagged `PROVISIONAL_SPEC_UNMEASURED_DEMO` until verified on FTMO Demo.
3. **`GER40`** (`deuidxeur`, scale `1000`, `native_Ask: true`): Xetra cash session (`08:00–16:30 Europe/Berlin`, exact CET/CEST DST calendar), intraday `swap = 0`, commission `$0/lot`, **DECLARED_INDEX_PROXY** slippage (`Base = 1.0 pt/side`, `Stress = 2.0 pts/side` on top of real M1 Bid/Ask spread; contract `1.0 EUR/pt`). Tagged `PROVISIONAL_SPEC_UNMEASURED_DEMO` until verified on FTMO Demo.

## Lane B — Nhịp 3 FTMO 2-Step Lifecycle & Reward Cashflow Simulation (Frozen 3-Engine Core)

Using exact Prague-reset M1 floating equity daily ledgers (`net_usd`, `day_equity_minimum`, `day_equity_maximum`, `orders`) from frozen 3-Engine Core (`USDJPY Tokyo-box` + `USDJPY EXP080` + `GBPUSD VOL_HIGH`), evaluate FTMO 2-Step rules:

- **Rules modeled:** Phase 1 Target `+10%`, Phase 2 Target `+5%`, Min Trading Days `>= 4` per phase, Hard Daily Equity Breach `>= 5.0%` from Prague start-of-day balance/equity anchor (`day_equity_minimum`), Hard Static Initial Loss Breach `>= 10.0%` below initial balance (`0.90 * initial`), Profit Split `80%`, Bi-weekly `14`-day Funded Reward cycle with fee refund on first Reward.
- **Declared Fee Schedule (`FTMO_PUBLIC_FEE_DECLARED`):** `Swing 10k = $168`, `Swing 25k = $270`, `Standard 50k = $373`.
- **Portfolios compared (fixed before outcome):**
  - `SOLO_USDJPY_030` (Pass 7B/8 reference)
  - `BASE_2E_USDJPY_075` (Pass 17 reference)
  - `PORT3E_INVDD_125` (Pass 22 Cluster-A inverse-DD weights)
  - `PORT3E_075_GBP075` (Pass 22 balanced 3-engine)
  - `PORT3E_075_GBP075_X125` and `PORT3E_075_GBP075_X150` (explicit risk-scaling frontier test to measure pass-rate vs breach-rate trade-off)
  - **Stress Sensitivity:** `PORT3E_075_GBP075_STRESS10` (`M1_Real_Stress_10`, `+1.00 pip` extra slippage on all 3 engines).
- **Evaluators:**
  1. **Historical Rolling-Start Windows** across every month start (`2018–2024`) for `6m / 12m / 18m / 24m / 36m` horizons (reporting unfinished/censored windows honestly — never dropping failures).
  2. **Block Bootstrap (`N = 2,000` paths, `block = 5` trading days, `seed = 20261123`)** reporting 2-Step pass rate (`6m/12m/18m/24m`), breach rate (`daily` vs `static`), median/p75 time-to-pass, and 12m/24m Funded Net Reward Cashflow after challenge + retry fees + `% zero-payout months`.

## Lane C — Engine #1 Clean White-Box `.mq5` Export & Full 3-EA Static Audit

- Implement `export_tokyo_box_oco_mq5(spec)` in `tooling/ai-engines/mq5_whitebox_exporter.py` reproducing frozen Pass 6/7B rules: Tokyo box `[00:00..03:00 UTC)` mid-extrema, first-touch activation `[03:00..10:00 UTC)`, hard SL at opposite box edge, DST-aware `18:00 Europe/Helsinki` hard flat (`swap = 0`), `InpDryRunLogOnly = true`, `2.5%` internal daily loss breaker, zero grid/martingale.
- Export `tooling/ai-engines/exports/Naqex_WB_TOKYO_BOX_USDJPY.mq5` and statically audit all 3 exported `.mq5` files (`0` red flags each) with pytest unit coverage.

## Lane D — White-Box Engine #4 Discovery & Forensic Upgrade Check (`XAUUSD` Native Ask · `US100` · `GER40`)

1. **Strict Cluster A (`2018–2020`) Discovery → Blind Cluster B (`2021–2024`) OOS Validation:**
   - Grammar: `30` specs on `XAUUSD` (`WB_SESSION_BOX`, `WB_OPEN_EXPANSION`, `WB_OVEREXT_FADE`, `WB_IMPULSE_PULLBACK`), `24` specs on `US100` (NYSE cash session), `24` specs on `GER40` (Xetra cash session) → `m_total = 78` specs (BH FDR computed over ALL `78` specs!).
   - Cluster A discovery gate: `n_A >= 60`, `FTMO Stress Net_A > 0`, `PF_A >= 1.05`.
   - Blind Cluster B promotion gate: `n_total >= 150`, `Cluster B > 0`, `Tot > Top10`, `Tot > Fade`, `pos_years >= 5/7`, `DD <= 15R`, `p_sf < 0.05`, `q_all <= 0.10`, daily correlation vs 3-engine core `|r| <= 0.25`.
2. **True Native Bid/Ask Re-Audit of Pass 14–16 `XAUUSD` Provisional Leads:**
   - Re-test `XAUUSD EXP_DAILY_OPEN_120`, `NEN006` (Inside Bar + EMA200 D1), and `IND026` (Ichimoku Chikou D1 Long) with **real M1 Bid/Ask spreads** (zero proxy!) under FTMO Swing real costs + Swap 3× (`swap_long = -56.28`, `swap_short = -4.20`).
3. **Automatic Deep Forensic + 4-Engine Upgrade Check (if any Engine #4 qualifies):**
   - Must pass: 3 cost tiers (`Base`, `Stress +0.5/mid`, `Stress +1.0/double`), **Dual 2D stability surfaces** (`trig × sl` AND `trig × filter`), **Outlier/Crisis Stress** (`-Top3`, `-Top5`, excl COVID `2020-03` & `2022` rate-shock/Gilt), 4-axis decomposition, and Prague-reset 4-engine portfolio + Nhịp 3 FTMO 2-Step lifecycle comparison against the 3-engine core.

## Stop & Integrity Rules

- Holdout `>= 2025-01-01` remains strictly sealed (`holdout_rows = 0`).
- Zero tuning on Cluster B; all negative/failed variants retained in JSON output and report.
- `US100`/`GER40` winners carry explicit `PROVISIONAL_SPEC_UNMEASURED_DEMO` flag until Demo symbol specs are snapshotted.
