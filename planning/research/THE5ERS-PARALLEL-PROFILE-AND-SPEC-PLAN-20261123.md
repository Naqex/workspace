# The5ers Parallel Prop Profile — Rules, Ban Triggers, Payouts & MT5 Spec Acquisition Plan

- **Date:** `2026-11-23` · **Status:** `DOCUMENTATION_AND_SPEC_PLAN_ONLY` (no purchase, no account creation, no live MT5 login, `OrderSend = 0`)
- **Continues / Extends:** [PROP-FIRM-FIT-20261102.md](PROP-FIRM-FIT-20261102.md#the5ers-phí-vào-nhỏ-có-thêm-ràng-buộc-chiến-lược) · [PROP-TERMS-SNAPSHOT-20261106.md](PROP-TERMS-SNAPSHOT-20261106.md)
- **Verification Scope:** Official `the5ers.com` FAQ/program pages cross-checked `23/11/2026`; live checkout card, KYC, personal tax, and MT5 `SymbolInfo` contract snapshot remain `UNMEASURED_MT5_DEMO` until captured from a real The5ers MT5 server.

---

## 1. Strategic Verdict: Should We Evaluate FTMO + The5ers in Parallel Now?

**YES — with clean separation of roles, ZERO bloat to core signal discovery:**

- **Core Alpha Discovery stays 100% shared:** Both FTMO and The5ers run on MT5 CFDs (`FX`, `XAUUSD`, `Indices`), allow custom white-box EAs with owned source code and hard server-side SL, and reward low-DD intraday `swap = 0` edges.
- **Why adding The5ers in parallel helps right now:**
  1. **4–8× lower ticket cost for testing & multi-attempt `Two-Regime` passing:** High Stakes small tiers (`$5K` `$39` or `$2.5K` `$19` if offered at checkout) vs FTMO `$10K` (`~$168`) make iterative shadow/live validation and asymmetric challenge sizing dramatically cheaper.
  2. **Lower FX commission & higher leverage:** Declared FX commission is **`$4/lot` round-turn** (20% below FTMO's `$5/lot`) and High Stakes FX leverage is **`1:100`** (3.3× FTMO Swing's `1:30`), removing margin ceilings when running 5–6 engines concurrently on small `$5K` books.
  3. **Alternative 1-Step track (`Hyper Growth`):** Single `+10%` target with **`3%` Daily Pause (non-breaching lock until next day)** instead of hard daily termination — viable later *only if* core portfolio reaches `Calmar >= 1.5` (because max static stop-out is tighter at `6%`).
  4. **Firm/rule diversification:** Protects solo-operator cashflow from single-firm policy/payout risk once funded.
- **Important discipline:** Do **NOT** optimize strategy rules separately for The5ers vs FTMO; keep **one** causal white-box core, and run **two separate profile evaluators** in Nhịp 3 (`FTMO_SWING_2STEP` and `THE5ERS_HIGH_STAKES` — checking The5ers' stricter `3 × 0.5%` profitable-day rule and `±2 min` high-impact news restriction explicitly!).

---

## 2. FTMO vs The5ers — Verified Rule & Economics Matrix (`23/11/2026`)

| Dimension | FTMO 2-Step Swing (Pinned Demo `8fd77ef`) | The5ers High Stakes (2-Step · Declared) | The5ers Hyper Growth (1-Step · Declared) |
|---|---|---|---|
| **Vietnam Eligibility** | Not on restricted list (verify KYC at signup) | Not on restricted list (verify KYC at signup) | Not on restricted list (verify KYC at signup) |
| **Targets** | Step 1: `10%` · Step 2: `5%` | Step 1: **`10%`** (New) / `8%` (Classic if available) · Step 2: `5%` | **Single Step: `10%`** |
| **Max Daily Loss** | `5%` hard breach (Prague `00:00` CE(S)T equity) | `5%` hard breach (`4%` on some `50k/100k` cards) from `max(bal, eq)` at `00:00` MT5 server | **`3%` Daily Pause** (closes trades & locks day; **does NOT breach account**) |
| **Max Overall Loss** | `10%` static initial equity | `10%` static initial (`8%` on some `50k/100k` cards) | **`6%` static** initial (tighter!) |
| **Min Days Rule** | `>= 4` trading days/phase (any opened trade) | **`>= 3` profitable days/phase** (`>= +0.5%` net of initial balance via `min(bal, eq)` at midnight!) | None on Step 1 (verify current card at checkout) |
| **Inactivity Expiration** | `30` consecutive calendar days without opening a trade | `30` days Evaluation (`60` days Pro per FAQ; program page cites `30` days — verify at checkout) | `30` days |
| **Overnight / Weekend** | Allowed (Swing exempt from >2h break close) | Allowed (swaps apply; **no swap-free accounts**) | Allowed (swaps apply; **no swap-free**) |
| **High-Impact News** | **Allowed** on Swing (within forbidden practices) | Holding allowed, **execution (open/close/SL/TP) BANNED `±2 min`** around Forex Factory high-impact news (profit deducted, losses kept!) | Verify card; news bracketing always banned |
| **Leverage (FX / Gold / Idx)** | `1:30` / `1:9` / `1:15` (measured Demo) | Up to **`1:100`** FX / `1:20–1:25` Metals & Indices | Lower (`1:30` FX — verify live card) |
| **Declared Commissions** | `$5/lot` FX · `$0` Gold/Indices (measured Demo) | **`$4/lot` FX** · `$0` Indices · `%`-based Metals/Energy/Crypto (`UNMEASURED_MT5`) | Same broker feed (`UNMEASURED_MT5`) |
| **Entry Fee (Ref.)** | Free Trial `$0` · `$10K` `~$168` (`€155` / promo `€89`) | No standalone free trial · `$5K` `$39` (`$2.5K` `$19` when offered) | Higher entry fee per `$10K` (1-step instant funding style) |
| **Fee Refund Mechanics** | `100%` cash refund on first Reward | **`10%` Hub Credit (P1) + `20%` Hub Credit (P2, non-withdrawable) + `70%` cash-eligible on 1st funded payout** | Non-refundable (check promo terms) |
| **Payouts & Scaling** | Bi-weekly (`14d`), `80%` → `90%` split, up to `$400k` initial allocation | Bi-weekly (`14d`), `80%` → `100%` split, min `$150` after split; `+10%` milestone scaling up to `$500k+` | `50%` → `100%` split, `2×` capital doubling every `+10%` up to `$4M` |

---

## 3. EA Rules, Ban Triggers & Compliance Guardrails on The5ers

Every white-box EA deployed on The5ers MUST satisfy **all** of the following (verified from `the5ers.com` FAQs & Prohibited Trading Practices):

1. **100% Owned Custom Source Code (No 3rd-Party / Commercial EAs):**
   - Allowed ONLY if the trader owns and controls the EA source code. Purchased, rented, shared, or Signal/Telegram-copied bots (including warez `.ex4`/`.ex5` bots) trigger immediate ban & payout forfeiture.
   - *Project fit:* Our white-box `.mq5` suite (`Naqex_WB_*`) natively satisfies source-ownership!
2. **Written Support Confirmation Before Live Deployment (Terms §11 Discrepancy):**
   - Official FAQs allow custom EAs, whereas legal Terms & Conditions retain strict language around automated software / prior written clearance. **Mandatory pre-live gate:** open a support ticket describing our exact self-coded MQL5 EAs (low frequency 0–2 trades/day, hard SL, zero grid/martingale) and archive written confirmation before funding/evaluation deployment.
3. **Mandatory Server-Visible Stop-Loss (`SL`) on Every Order:**
   - Stealth / virtual / hidden stop-losses are strictly banned. Every order sent by our EAs MUST attach a hard server-side SL on execution (already enforced across all 3 `Naqex_WB_*.mq5` exports).
4. **Hard Ban Triggers (Zero Tolerance — Account Termination & Forfeited Payout):**
   - **News Bracketing:** Placing opposing pending Buy-Stop / Sell-Stop orders around high-impact news releases.
   - **High-Impact News Execution (`±2 min` on High Stakes):** Opening, closing, or triggering SL/TP within `±2 min` of red-folder news forfeits trade profit while retaining losses → **Required engineering addition before The5ers live use:** add a `±5 min` high-impact news execution guard in `.mq5` + simulate news-window impact in Python!
   - **Gambling / One-Sided Betting / All-In Sizing:** Oversized single-direction bets without coherent risk management (keep per-trade-idea risk `<= 1.0%` and diversify across instruments/directions).
   - **Arbitrage & Feed Exploits:** Latency arbitrage, reverse arbitrage, cross-account hedge arbitrage, glitch exploitation, tick scalping, rollover scalping.
   - **Server Overload / Bulk Trading:** High-frequency order spam or mass simultaneous modifications.
   - **External Copy Trading:** Copying third-party master accounts or coordinated group trading. Copying **only between your own personal accounts** up to The5ers' capital cap (`~$500k`) is permitted.

---

## 4. How to Obtain Verified The5ers MT5 Contract Specs (Same Rigor as FTMO `8fd77ef` / `36f1535`)

Unlike FTMO (which offers renewable 14-day Free Trial MT5 Demo accounts), **The5ers does NOT offer a standalone public MT5 Free Trial**. To capture real, verified MT5 `SymbolInfo` snapshots (`bid`, `ask`, `spread`, `commission`, `swap_long`, `swap_short`, `swap_rollover3days`, `trade_contract_size`, `margin`, `server_timezone/DST`), follow this exact 3-step ladder:

| Stage | Cost | How to Capture | Evidence Tag | When to Use |
|---|---:|---|---|---|
| **Stage 1 (Now · Offline)** | `$0` | Use declared `the5ers.com` Trading Assets specs (`$4/lot` FX, `$0` Indices, `1:100` FX / `1:20` Gold & Indices) + our existing Dukascopy Native M1 Bid/Ask spreads + conservative FTMO Swap 3× proxy (`swap = 0` for intraday engines!) | `THE5ERS_DECLARED_UNMEASURED_MT5` | Immediately for Pass 24+ dual-profile Nhịp 3 evaluation |
| **Stage 2 (Zero-Cost Real MT5 Server)** | **`$0`** | Owner signs up for a **The5ers Free Monthly Trading Competition** (grants real The5ers MT5 Demo credentials on their live-mirror server) → run read-only `SymbolInfo` snapshot script (`OrderSend = 0`) across `USDJPY`, `GBPUSD`, `EURUSD`, `XAUUSD`, `US500`, `US100`, `GER40` | `THE5ERS_COMPETITION_MT5_SNAPSHOT` | As soon as owner wants exact live spreads, swaps & server timezone at `$0` cost |
| **Stage 3 (Exact Program Verification)** | `$19–$39` | Only AFTER core portfolio passes Nhịp 3 (`Calmar >= 1.4`) & Holdout (`>= 2025`): purchase smallest High Stakes tier (`$2.5K` `$19` or `$5K` `$39`) to confirm exact live evaluation fills, slippage, news enforcement & written EA support clearance | `THE5ERS_HIGH_STAKES_LIVE_MEASURED` | Nhịp 4 (`G5` forward shadow / small live test before scaling to `$25K–$100K`) |

## 5. Exact Gaps Still Required Before Any The5ers Numerical Qualification

1. Capture real MT5 `SymbolInfo` snapshot (Stage 2 Free Competition or Stage 3 small account) — especially `XAUUSD` percentage commission, exact `swap_long`/`swap_short`/`swap_rollover3days`, and exact `00:00` MT5 server timezone/DST offset.
2. Add **The5ers High Stakes Evaluator** alongside FTMO in `pass23_ftmo_lifecycle_sim.py` (modeling `>= 3` profitable days `>= +0.5%` per phase, `10% + 20%` Hub Credit vs `70%` refund, `$150` min payout after split, and `±2 min` Forex Factory red-news execution filter).
3. Obtain written support confirmation from The5ers for custom white-box MQL5 EAs (resolving Terms §11 ambiguity) before any paid evaluation.
