# V19 — recovery, causal feed guards and an offline MT5 shadow adapter

Owner: attachment `4725b078-3393-42d0-9bcf-4a99148570fe`.
PR #97 head `014e1eb` passed 3 CI, merged `beaabdd`; delete only its merged branch.
Branch `codex/asymmetric-recovery-and-mt5-v19`. Preserve Trader pin
`930fa76882e741702620f626986bb38755368635`, VI WIP, all original data,
freezes and failed attempts. No paid provider, account registration, broker
orders, production/runtime deployment or memory update.

## Scientific contract and correction of hypotheses

The original V16 factor-1.5 policy reduces requested risk at equity −5% and
−7%, not −1% to −3.5%. Determine whether risk or weak net alpha actually
explains slow recovery. A square-root power is concave in positive cushion,
not a mathematically convex function. It reduces risk less sharply than
linear CPPI at a given cushion; it does not guarantee survival through gaps.
House-money is still account equity; no claim that bonuses cannot lose
starting capital. `0.5*sigma^2` is the small-return log-growth approximation,
using fractional account returns over a named period, not the variance of
raw R as a percentage.

Development is 2018–2023 only for policy fitting/selection. Later prices are
already exposed historically; 2024–13/10/2026 is reused historical validation,
not clean OOS. Do not select by its outcomes. No new signals, SL/P1 parameters,
assets, entry windows or profit targets.

## Track 1: fixed budget, before outcomes

Fit one O2 inverse-volatility sleeve weight vector from Development daily
fixed-$150 sleeve PnL, including zero days. Normalize its expected daily USD
to the equal-sleeve mean; require positive finite mean and every weight
within [0.25, 2.0]. If impossible, O2 is ineligible; no retuning bounds.
Report full covariance and the variance actually achieved. Inverse volatility
does not automatically solve constrained global minimum variance; report that
distinction, not an unsupported optimality claim.

Six candidate profiles, on the same causal guarded entry/exit universe:
`BASE_GUARD`, `O1_G035`, `O1_G050`, `O2`,
`O1_G035_O2`, `O1_G050_O2`. No gamma/bonus/weight grid beyond these.

O1 uses phase base $300/$262.50/$187.50 times
`min(1,max(0,(equity-45000)/5000))**gamma`, gamma 0.35 or 0.50.
In phases 1–2 only, add `min(0.10*max(realized_balance-50000,0), phase_base)`.
Bonus is recomputed at every entry; no assumption that two losses always
erase it. Keep the inherited $1,000 aggregate stop cap and $45,800 internal
reserve. Add a shared projected daily reserve floor at midnight-Prague
balance minus $1,100 (2.2%), including planned fees/slippage. This admission
floor is not a guarantee against discontinuous execution.

Select using worst Development completion count across both M1 orderings
and PRIMARY/STRICT/base/+50% cost cases, then shortest restricted completion
time (nonfinishers remain censored), then standalone payout, then canonical
profile ID. Zero modeled breaches required. Retain incumbent if no candidate
improves the first two metrics without worse static/daily DD. Record a
diagnostic best candidate even if promotion fails. Commit selected parameters,
guard semantics and code hashes before new V19 Validation outcomes.

For +8,+5,+2,0,−2,−4,−6,−8% states, report exact target/cushion arithmetic.
Use 256 common Development-only quarter resamples, horizon 36 months, for
incumbent/selected recovery and time-to-funded estimates. Show hit rate,
conditional time and restricted mean/censoring; never call a conditional
median an unconditional finite expected hitting time. Reset boundary O3 is
analysis only: compare remaining time with twice fresh-start time, account
for unspecified challenge/retry fee explicitly. No automatic restart,
purchase, account discard or deletion of losing paths.

## Track 2: source repair and an implementable continuity guard

Inventory every source-uncertain V16 trade, sleeve/hour/gap and before/after
stop/protection. Reuse V14–V16 raw-source census and bounded tick readers,
verify file bindings before reuse; inspect any newly available D/E sources.
Ticks may repair recorded M1 when UTC/Bid/Ask/source evidence permits.
M5/M15/H1 cannot reconstruct missing intraminute first-passage or certify
absence of quotes; native extrema may only exclude specific crossings under
an explicit completeness assumption. Never fabricate continuous M1.

One guard, locked on Dev: require all preceding 30 scheduled-open M1 minutes
to be present before a new entry. Scheduled calendar closures keep the
known-before-entry flat deadline. On an unexpected >2-minute feed timeout,
stop new entries; close any paper position at the first valid quote after
the timeout. Never close at the last quote before an unforeseen gap.
Keep all residual missing-path labels and STRICT synthetic excursions. No
post-hoc deletion of trades merely because their future path is incomplete.
Freeze any source repair as a separate derived dataset; preserve originals.

## Track 3: adapter scope

Reuse native capture, account/symbol contracts, signal generators, sizing
engine and reconciliation before creating wrappers. CLI defaults READ_ONLY;
SHADOW_PAPER mutates only its private ledger. Provide recorded file bridge
and injected test gateway; broker import is lazy. Require explicit verified
binding for a read-only terminal session. Do not auto-launch or reconnect an
unrelated terminal.

Implement closed-bar-only V16/V19 signal-to-sizing paper decisions, Prague
daily guard, stale/unknown data fail-closed, phase-aware restricted news,
Friday/known holiday flatten and request/fill reconciliation. News data
must have source/time coverage; an empty/unknown calendar is not permission.
Risk liquidation versus news lock conflicts must be visible.
Keep `ALLOW_LIVE_ORDER_SEND=False` in this release; do not call OrderCheck
or OrderSend. An unverified demo-mode flag alone is not owner authorization.
External fills may be imported and joined to expected intents; quote-only
records never claim measured slippage. Validate with offline streams only.

## Tracks 4–5: performance, stress and delivery

Profile startup/imports/fixtures before editing. Keep the same 78 smoke test
IDs and functional assertions. Diagnostic paired samples are labeled; after
freezing a justified optimization run exactly ten fresh final processes,
including Python startup, target each <0.78s. Preserve outliers; do not retry
for a good streak. Full suite target <22s, preserve all 1,153 V18 IDs, add only
meaningful regression tests (owner target 1,170+, no padding).

Reuse V18 joint quarter quote/event blocks and the same 5,000 seeded draws,
36-month extension/prefix 12/18/24. Compare original V16 with frozen V19 under
PRIMARY base, PRIMARY 1.50x, STRICT base, both M1 orderings.
Translate source clocks explicitly, preserve account state across flat seams.
Retain limitations of fixed-path cost sensitivity and source uncertainty.
Audit every V19 historical and Monte Carlo account through a separately
implemented ledger/path oracle, not just its cash bridge. Benchmark a bounded
preflight before the full batch; preserve all attempts and exact audit scope.
Same author/feed is not an independent reviewer or independent data feed.

Inventory D/E with reparse points skipped; compare to V18 receipts, preserve
errors and all research evidence, no broad deletion. Export bounded report/
JSON and resumable private jobs with one writer per output. Open PR #98,
obtain 3 exact-head green CI checks, reconcile downloaded full test IDs, and
leave PR open. Success is measured, never forced by relabeling gates.
