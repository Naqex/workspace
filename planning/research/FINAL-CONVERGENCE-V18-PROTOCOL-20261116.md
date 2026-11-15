# V18 — Tournament, trade-path resampling and a guarded measurement kit

Owner request: attachment `f7a01ca4-2008-439d-8e22-12fc4ffc8a2c`.
PR96/exact head `ee97543` passed3CI and merged `92569ca`; V17 branch deleted.
Work on `codex/final-convergence-v18`, preserve Trader pin, VI WIP, original
prices/freezes/negative attempts. No strategy/risk grid, provider download,
broker/account registration/execution or deployment. Open PR97, exact-head3CI,
downloaded full test IDs; leave it open.

## Tournament, before new numeric evaluation

Inventory V1–V17, distinguishing implemented strategies, engineering campaigns
and superseded/corrected results. Include PR78 Gold A, PR82 V4, PR93 V14,
PR94 V15, PR95 V16 and PR96 V17. Confirm PR identities rather than trusting
version numbers; PR93 is V14 delivery, not a new V15 model. Preserve denominators,
source resolution, actual observation cutoff and censoring.

Do not rank 36 three-year starts against105 nine-year starts by raw pass count.
Use matching2018–13Oct2026 starts/standalone books for the final comparison.
Champion qualification requires complete certified paths, positive economics,
zero modeled breaches, daily<5% and static<10%; synthetic missing-path stress
or Brownian probability is not source certification. If none qualifies, record
NO_QUALIFIED_CHAMPION, not a forced winner.

To fulfil the requested stress with no qualified winner, select a **diagnostic
velocity reference** from the comparable frozen V14/V15/V16/V17 policies:
zero primary breaches in both orderings/costs, maximize worst primary two-phase
completion count, then minimize worst conditional median, then canonical ID.
No new weights/parameters. This full-exposed-history comparison is descriptive,
not an OOS selection claim.

For a **diagnostic Funded backup**, use comparable standalone books with
positive payout and0breaches in both costs/orderings; require worst PRIMARY
static<6%. Rank lowest worst standalone static, then highest worst payout,
then canonical ID. Source uncertainty still blocks “Ultra-Safe” certification;
do not reduce sizing to manufacture a new entrant.

## Path bootstrap and cost stress

5000 seeded paths, seed20261116, joint non-overlapping calendar-quarter blocks
with replacement. Keep all assets/trades together inside each block, including
entry/SL/exit events and the complete ordered M1-scenario excursion observations;
never resample daily terminal PnL or independently shuffle sleeves. Preserve
original unknown-path labels. Use all complete source quarters available before
13Oct2026; exclude the incomplete last quarter only, not losing trades.
If the selected reference has a cross-quarter position, use a flat seam after
the boundary and record the resulting block duration; do not silently close it.

The request says24months but also asks36month outcomes: run one36month extension
of the same5000 paths; report12/18/24month prefixes and36months, not an invented
36month probability from a24month run. Source quarter lengths/DST differ:
report actual elapsed-time checkpoints365.25days/year, with source Prague
midnight reset events and14calendar-day payout timers. Copied blocks are
synthetic scenarios, not a generative market or clean future OOS.

Report all5000 random starts plus conditional subsets whose first block comes
from a favorable/sideways source year. Labels are retrospective descriptions:
favorable = top two Dev2018–2023 annual reference Net-R years;
sideways = two lowest absolute-Net-R remaining Dev years. Only label first-block
years from those lists; other starts remain in random. Never present these
labels as a known-at-entry regime predictor or calibrated future probability.

Run PRIMARY and shared ALL_UNCERTIFIED source stress, both M1 orderings.
Stress spread+slippage at1.00/1.25/1.50 with common bootstrap draws; retain
commission and funding schedules. The incremental spread drag is a symmetric
per-leg surcharge on the frozen execution quotes, with unchanged signal/SL/P1
paths. Recompute lot/fee/reserve/account decisions at actual quantities.
This is **friction-cost sensitivity**, not a claim that widened quotes could
never change first-passage times. Do not relabel it as regenerated broker fills.
If native cost-aware parity is missing, finish the parity fix before outcomes.
Intraday absence of swaps/TP may permit exact SYM/ASYM reuse with a proof.

Reuse the native lifecycle/risk/harvest engine. Pre-extract event/quote blocks
once; no daily-extrema surrogate. Preserve chronological quote order and
next-observation forced exits. Flat boundaries carry cash/phase/harvest/throttle
and elapsed payout age; they must not reset the account. Preserve or translate
timestamp fields explicitly; test repeated blocks and DST/reset boundaries.
Run representative paths through the independent Decimal ledger oracle;
all original paths have scalar first-passage audits. “Independent” refers to
implementation, not a second author/feed. Report exact scope of verification.

For each horizon: phase1/both rates, daily/overall breach rates and Funded
standalone annual payoutP25/P50/P75, including zeros and stopped paths.
Export per-path outcomes privately. No grid or outcome-based choice of seed,
block length, regimes or friction rule. Commit implementation/freeze before
5000-path evaluation; preflight/parity fixtures do not select strategies.

## Readiness, health and delivery

Package explicit entry/SL/P1, clocks/holiday/news unknowns, lot grid, phase
risks/caps/reserves and execution-reconciliation log schema in
`FTMO-FREE-TRIAL-EXECUTION-SPEC-20261116.md`. Separate offline paper readiness,
capture-only terminal measurement and strategy order authority. This task
creates a kit, not an MT5 EA or an OrderSend permission. Verify current official
Free Trial terms if accessible; record inaccessible pages instead of claiming
verification. Fourteen days cannot prove a multi-year edge.

Run `tooling/workspace_maintenance.py inventory` on both named D/E roots,
skip reparse points, report errors and logical bytes. Compare with original
receipts and approximate owner208/320GB baselines; snapshot delta is not proof
that all removed bytes/files were junk or physical space reclaimed. Sum only
non-overlapping deletion receipts. No broad cleanup; preserve all evidence
and active environments.

Full suite: retain all1148 V17 IDs/0skip; exactly10 fresh78-test smoke samples,
keep failures/outliers. No benchmark while financial jobs contend.
Morning summary has the four requested beginner-friendly sections; detailed
JSON<=1MiB with hashes/receipts. Update current context/research index/README.
No automatic purchase/Free Trial registration or broker orders.
