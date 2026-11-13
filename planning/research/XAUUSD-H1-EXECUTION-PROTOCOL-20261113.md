# XAUUSD H1 — SL-active / intra-week diagnostic

Owner authorizes this follow-up to PR76, merged as `7ab3311`. Development
2022–2023 only; no 2024–2026 prices. User explicitly chose **48 calendar hours**,
not 48 open-market hours. Preserve the frozen 608 signals and natural stops;
no signal/cost filter, no parameter search, no resurrection of cancelled B1.

## Frozen comparisons, before new outcomes

- All 608: endpoint availability at `min(observed entry+48h, Friday20:30UTC)`.
  Do not promise 100%: missing/holiday quotes remain missing; wait <=60 seconds.
- SL-active paths: A BOTH (210 signals) and C BOTH (146), A BUY/SELL attribution.
  Exactly two exits: natural SL + deadline, and natural SL + TP2R + deadline.
  TP3R not run. TP2R is measured from observed executable entry to natural SL;
  entry slippage is charged separately, without moving frozen stop/TP geometry.
- Four paired cost cells, same entries/quantities/trigger paths: symmetric
  swap -40/-40 USD/lot vs asymmetric **proxy** -45/-5; flat slippage .20/side
  vs order-aware .20 entry/SL/time/Friday, zero adverse TP slip. This separates
  swap and TP assumptions; no sweep over alternative swap rates.
- BUY at Ask/close Bid, SELL at Bid/close Ask. TP exact level when corresponding
  executable side crosses it; no price improvement, no adverse TP slip only in
  order-aware cell. SL first executable quote after crossing, adverse .20 added.
  Ordered ticks resolve all same-minute SL/TP ambiguity; no OHLC ordering guess.
- Commission .000007 x execution price x ounces per side. Slip is an explicit
  dollar expense; commission uses quote/limit price, not slipped price. Funding
  inherited proxy: weekdays22UTC, Wednesday x3, entry<event<=exit. These are
  declared scenarios, not verified historical FTMO specifications/swaps.
- R0=$150 on $50,000, fixed, no compounding. Common quantity = floor(150 / natural
  stop distance) whole ounces (100oz/lot, .01lot step). Nominal **price-only** stop
  budget <=.30%; fees, gap and swap can exceed it. No risk optimization. Preserve
  overlapping signals in separate A/C virtual hedged books, no admission caps,
  no margin enforcement. Report concurrency; this is not a deployable prop book.
- Synchronized tick equity includes entry fees/slip, floating executable PnL,
  accrued swap and realized exits. R-DD uses peak equity; daily loss uses Prague
  midnight **balance** minus equity, /fixed50k, DST-aware. Report equity-start
  daily change separately. Never sum independent trade MAEs as account DD.
  Entry slippage is represented as an equity expense to keep paired geometry
  fixed. Reconstruct true realized balance at resets by adding back the entry
  slip of still-open positions; entry slip remains floating until their exit.
  Swap also accrues on each open position and realizes at exit, rather than
  pretending every overnight charge is already a balance operation. Reconstruct
  reset balance by removing the accrued swap of open positions from the equity
  cash component. This is the ordinary MT5 position-accrual model; broker swap
  by reopening/balance-operation modes remain outside this declared scenario.
  Reset can occur without a quote: retain balance exactly, flag stale floating
  marks for equity-start comparison. Closed quote gaps remain unknown paths.
  At coincident timestamps: reset from pre-event balance/last observed mark,
  charge scheduled swap, then consume quotes in original source order and
  process exits/entries on their exact quote ordinals. Milliseconds alone do
  not order multiple quotes with the same timestamp.
- No later-than-deadline fill invented. If endpoint unavailable, noTP stays
  unresolved; TP/SL observed earlier can resolve an individual path. Missing
  intervals/known closures >2h flag Standard compliance unknown, not a pass.
  Holidays/news/target feed and historical specification not exhaustively known.
  If a full-cohort book is blocked by unresolved exits, optionally report a
  separately labelled resolved-subcohort book with excluded IDs. Its PnL/DD is
  conditional selection, never a replacement/full-cohort performance estimate.

## Sources and admission

Reuse hashed native Dukascopy raw tick hours from prior jobs, strictly filter
manifest timestamps to Development before opening prices. Collect only needed
path/endpoint hours via existing bounded native provider (two requests, finite
retries, one-hour deadline, cancel/status/sealed-hours). Decode on .001 grid;
compare Bid M1 OHLC to corrected admitted source, before PnL. Preserve mismatches
and attempts; no silent candle correction. Full ordered tick replay where quotes
are available is stronger than a synthetic M1 excursion envelope, but does not
prove missing historical quote intervals or FTMO execution/liquidity.

Checks: Friday/year boundary/calendar-hour semantics; SELL Ask stops/TP; gap SL;
TP adverse-slip contrast; asymmetric and Wed3 swap; overlapping equity; midnight
balance vs equity anchor/DST; source/cutoff bindings. Pin code/config/data before
outcomes; preserve failures. Self-audit is not independent agent review.

Official sources checked 13/11/2026:
[FTMO holding rule](https://ftmo.com/faq/can-i-hold-positions-overnight-or-over-the-weekend/),
[MT5 basic principles](https://www.metatrader5.com/en/terminal/help/trading/general_concept),
[symbol properties](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants).
FTMO excludes Swing and evaluation from its >2h holding restriction; trading
hours vary with holidays. Friday clamp is the owner's research policy aimed at
funded Standard, not proof of complete historical rule compliance.

Target-specific caveat: [FTMO order types](https://ftmo.com/en/blog/order-types/)
explicitly allows negative slippage for limit orders; its
[execution explanation](https://ftmo.com/en/blog/slippage-order-execution/)
also discusses SL/TP gap execution. Therefore zero-adverse TP is a requested
**TP-limit proxy scenario**, not a verified improvement in FTMO realism. Keep
full-slippage cell as the conservative comparator. [30Mar2023 update](https://ftmo.com/en/blog/trading-updates/trading-update-30-mar-2023/)
states metals closed on Good Friday07Apr2023; [23Nov2023 update](https://ftmo.com/de/blog/trading-updates/trading-update-23-november-2023/)
reports early metal closure. These are counterexamples to universal Friday
coverage/compliance; no hindsight calendar/backfill or new exit scenario added.

Accounting source: [MQL5 deal properties](https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties)
defines DEAL_SWAP as cumulative swap on close; [MT5 reporting](https://www.metatrader5.com/en/terminal/help/trading_advanced/history_report)
separates balance from open-position results. Attempt1 was cancelled during
source review, before any new PnL, to correct reset balance for unrealized entry
slippage and open-position swap. Preserve its failure/snapshot; v2 freezes this
correction without changing signals, trigger paths, quantities or final net PnL.
