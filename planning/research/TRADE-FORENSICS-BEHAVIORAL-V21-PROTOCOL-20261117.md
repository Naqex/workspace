# V21 — trade forensics and bounded behavioral tests

Owner request: attachment `98a5dffa-eedd-4479-89d6-bafe009396d9`.
PR99/head `c9075fb` merged `a2d9c86`; V20 branch removed. Use
`codex/trade-taxonomy-and-behavioral-v21`. Preserve all inputs/freezes/failed
attempts, Trader pin and unrelated VI WIP. No broker/account/provider action,
product rollout, Astra/subagents or memory update.

## Interpretation and exposure boundary

Six labels are **path descriptions**, not identification of skill, luck,
institutional intent or retail positioning. OHLC has no trader/order identity.
SL followed by recovery is a counterfactual path event, not proof the entry
predicted direction or that a wider SL would improve account returns. ATR is
scale, not a maximum daily range. Both M1 orderings and proxy Ask remain scenarios.

Canonical 494-trade reference is V19 BASE_GUARD PRIMARY, SYM stress,
fixed $150 requested risk with existing lot floor. V16 differs at two timeout
exits; report its economics separately, never blend the books. R-money is net
USD/150; path MFE/MAE is executable-price movement/natural SL before fees.

Do Dev 2018–2023 diagnostics and lock all selections before producing the full
2024–13Oct2026 taxonomy. Later history was already exposed in older campaigns;
no clean OOS claim. Existing 2017 warmup may be read. No new future dates.

## Six-class rule fixed before new measurements

Keep every row, secondary flags and source/ATR/post-stop completeness. Exclusive
priority: positive W2 before W1; nonpositive L1 > L2 > L3 > L4. Also report
overlap counts so hierarchy cannot hide giveback in an L1 trade.

- W2: MAE magnitude >=0.80R; or source-uncertain open path; or final 15 minutes
  contribute >=80% of positive gross move while <=20% observed path points were
  profitable. Positive residual failing W1 geometry is W2 with its own reason.
- W1: positive, no W2 flag, and MAE<0.60R or MFE>=1.5*|MAE|. This is favorable
  geometry, not a verified structural economic explanation.
- L1: original reason SL, and executable quotes strictly after stop through
  the known daily/holiday cutoff show >=+1R relative to original entry. Record
  +2R too, first-passage times and original-horizon recovery separately.
- L2: net<=0 and pre-exit MFE>=0.80R; split 0.80–<1.00, 1.00–<1.50, >=1.50.
- L3: F3/F4 nonpositive, MFE<0.25R, decision-known UTC daily range / previous
  closed D1 Wilder ATR14 >0.90. No future daily high/low in this covariate.
- L4: residual nonpositive. Missing path/context makes the label provisional,
  never proof of a clean loss. All 494 rows covered does not mean all certified.

Excursions stop at the actual exit crossing, without later extrema of its M1
bar. Post-stop path ends at min(original signal's known daily cutoff, sample
end); missing expected M1 stays unknown. No missing-bar padding or source repair.
Report six-group count/share/net contribution by sleeve and Dev/later period;
remove top5/top10 only as descriptive concentration, never as a new strategy.

## Locked finite experiment budget: B1 + 24 B2 + 4 B3 = 29 trials

No threshold search beyond these registered cases; no selection on later data.

**B1 — exactly one child of BASE_GUARD.** Compare absolute closed net loss
contribution of Dev L2 versus L3, using overlapping flags, not exclusive labels.
If L2 dominates, on P0 sleeves only add net +1R trigger → net breakeven protection
active on the next M1 after trigger bar closes; keep Gold F4 P1 unchanged.
If L3 dominates, skip F3/F4 entries with decision-known daily-range/ATR>0.90.
Do not also change SL distance, side, time or sizing. No L1 wider-stop tuning.
This is one diagnostic loop, with the observed baseline exposure recorded.

**B2 — 24 raw recipes.** XAUUSD/EURUSD/US500/GBPUSD × PDH/PDL or Asia00–06UTC
range × minimum sweep {0.10,0.30,0.60} ATR_H4. H1 same-bar reclaim inside the
range, candle close in favorable half; simultaneous up/down sweep abstains.
Windows apply to the swept bar: start07–09UTC or13–14UTC (closed H1 approximation
to 12:30–15:00; no claim to 30-minute timing). First signal/day/recipe.
SL beyond sweep wick +0.10 prior H1 ATR; no artificial widening.

**B3 — 4 raw recipes.** XAUUSD/US500 × all weekdays or first/last two business
days/month. Decide15:00 Europe/London (DST-aware, one hour before16:00 fix),
closed H1 body>=1 prior H1 ATR, side agrees with UTC day move, close in outer
quartile of decision-known day's range. Natural SL beyond signal wick +0.10ATR.
This tests transfer of a fixing-time momentum hypothesis; WMR is an FX benchmark,
not the Gold auction or US stock closing auction. Dedup with incumbent by asset,
decision and side before any portfolio addition.

**Stage-0 before SL/TP packaging:** primary horizon known daily cutoff20:30UTC,
US500 also clamps16:00 New York, and inherited registered early guards.
No overnight. Stress costs reuse kernel: Gold spread0.338 + commission
0.0007%/side + slippage0.20/side; FX native/proxy spread + $7 commission/lot
roundtrip + $2 slippage/lot; US500 observed spread + $1 fee +1.5 points slippage.
These are inherited declared scenarios, not newly verified target specs.

Raw mean net stress must be positive in **each** Dev year and both three-year
clusters, and exceed mean execution friction in those same units. Median
friction/median natural SL<=12%, per-intent retention>=50% at12%, cadence>=40/year
on six-year average, all endpoints valid. Native H1 GBP can be screened but no
M1 replay claim without admitted M1. Keep all raw signals, rejects and missing.

Only Stage-0 survivors get P0 natural-SL M1 replay (both orderings), no TP.
Require zero unknown paths, dual-positive net, mean net>=0.04R and cadence>=40/year.
Compare adding one survivor to the baseline at unchanged risk; do not assemble
a retrospectively selected subset. At most one candidate may pass onward, ranked
by worst-cluster NetR / equity DD, ID lexical tie break; B1 considered first.

Promotion gates against baseline on Dev, BOTH orderings and stress: higher net,
Calmar and W1/all-trades share; lower L2/L3 loss contribution, no greater peak-to-
valley marked equity DD or worst daily loss, no signal/risk inflation. Unknown
cannot pass. Same-trade winner relabeling is a diagnostic, never edge proof.

If no candidate clears gates, stop new historical/lifecycle/MC work and reuse
hash-bound V16/V19 baseline receipts. If one clears, freeze its exact source,
rules/trades before 2024–2026 evaluation; replay105 monthly starts and the same
5,000 quarter draws, both orderings, source/cost historical stresses, full separate
ledger audits. Reject a later failure; no second candidate selected using it.

## Storage, engineering and delivery

Private job `execution-v1/trade-forensics-behavioral-v21-20261117`. One writer
per stage, events/logs/receipts; source inputs read-only. Emit large per-trade
tables directly as Zstd9 with original/compressed SHA256/size manifest and
roundtrip verification; do not duplicate source price caches. Small bounded
JSON/MD in Git. Keep negatives and unknowns.

Keep all1,239 V20 test IDs; add meaningful classifier/timing/selection regressions
to reach1,250+. Full target<15s, stretch<14s. Ten fresh serial smoke processes,
unchanged78 IDs, each<0.78s, stretch<0.70s. Keep outliers, no retry for a streak.
Merge99 only; push PR100 and leave open, wait three green exact-head CI checks,
download and reconcile every test ID. Four-part report: taxonomy, B1–B3 tests,
promotion/lifecycle decision, engineering/storage. No requirement to invent winner.

## Primary-source research (checked17Nov2026)

- [NY Fed Osler](https://www.newyorkfed.org/research/staff_reports/sr150.html):
  evidence of stop-loss-driven FX cascades; not proof that this data's PDH/PDL
  sweeps are retail manipulation or that every cascade reverses.
- [Bank of Canada SWP2021-48](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/):
  FX drifts/reversals around benchmark fixes; transfer to Gold/US500 is unproven.
- [LSEG WMR](https://www.lseg.com/en/ftse-russell/benchmarks/wmr-fx-benchmarks):
  16:00 London, not fixed16:00UTC. Five-minute methodology does not imply an H1 edge.
- [LBMA Gold Price](https://www.lbma.org.uk/prices-and-data/lbma-gold-price):
  Gold auction is distinct from WMR FX fixing.
