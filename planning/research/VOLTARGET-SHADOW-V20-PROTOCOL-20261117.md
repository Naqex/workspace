# V20 — variance scaling, source localization and bounded MT5 observation

Owner request: attachment `9f4fc25b-59c2-4e0e-a583-1ba8b326e44f`.
PR98/head `75edaa0` passed three exact-head CI checks and merged `9fba6e0`.
The merged V19 branch is removed. Work on `codex/mt5-shadow-and-voltarget-v20`.
Keep Trader pin `930fa76882e741702620f626986bb38755368635`, unrelated VI WIP,
all freezes, negative results and source observations. No broker submission,
login/account creation, paid provider, product rollout, Astra or memory update.

## Questions and corrections before outcomes

O2 means the V19 **corrected constrained covariance solution**, not the rejected
inverse-volatility heuristic. Development is 2018–2023; 2024–13Oct2026 is already
exposed historical validation. No fitting to that later period or reading new
historical prices. An authorized current terminal observation is separate from
policy fitting and does not certify missing historical minutes.

Lower unit-book variance does not guarantee lower daily or maximum static DD.
Eight percent is the owner's internal target, not the firm's ten-percent static
limit in the inherited two-step model. The supplied scaling formula and the
request for exactly the same DD as V16 are not mathematical equivalents. Report
the formula's actual result, even if outside the anticipated 1.20–1.34 interval;
do not search for another multiplier to make validation look better.

## Track1: fixed three-profile diagnostic

Use the V19 O2 correction's frozen weights/means/covariance, and its worst
realized static DD across **all eight registered Development order/source/cost
cases**. No favorable-case choice after outcomes. Compute once:

`k_sigma = sqrt(equal_variance / O2_variance)`
`k_DD = 8.0 / worst_O2_Dev_static_DD_pct`
`k_vol = min(k_sigma, k_DD)`.

Lock these profiles before new full historical/Monte Carlo outcomes:

1. `O2_UNSCALED`: k=1, existing phase1 house-money cushion enabled, matching V19
   corrected O2 exactly. V19 O2 already had this incumbent cushion.
2. `O2_VOL`: k=k_vol, existing cushion disabled.
3. `O2_VOL_CUSHION`: k=k_vol, existing cushion enabled; no new gamma or bonus.

Multiply final requested USD risk after incumbent sleeve weights/DD throttles/
cushion, before lot rounding and shared admission limits. Keep signal, natural
SL/P1, costs, daily-flat, lot rules, $1,000 shared stop cap, $45,800 internal
reserve and the 2.2% projected daily reserve unchanged. Do not alter stops,
discard source-uncertain trades or invent a future-known pre-gap exit.

Run the eight Development cases for all three, then freeze fit/code hashes.
Check realized DD against the requested <8.2% gate; do not retune if it fails.
Full historical: both M1 orderings, PRIMARY100/PRIMARY150/STRICT100, 105 starts
plus standalone Funded. Each new account gets the separate full ledger/path
oracle; prove unscaled Development equivalence with the saved V19 O2 accounts.

Bootstrap: the same V19/V18 5,000 common quarter-block draws, horizon36 months,
prefix12/18/24. Six new cases = three profiles × two orderings at PRIMARY100,
two accounts/path (Challenge and standalone Funded): **60,000 new full audits**.
Reuse hash-bound V16 PRIMARY100 results for both orderings; no redundant
baseline rerun. Historical stress covers source/cost sensitivity; no claim that
this limited Monte Carlo matrix certifies every stressed distribution. Retain
zero payouts/nonfinishers and distinguish standalone from post-Challenge income.
Same author/feed, not independent human review or calibrated future probability.

Localize the original 32/494 unknown trades by entry year and sleeve. Count
trade identities once, gap occurrences separately. Sum existing fixed-$150
PRIMARY and STRICT reference economics for 2018–2021 versus 2022–2026YTD;
do not use this localization to select a favorable start year or delete trades.

## Track2: observation and paper only

Reuse V19's adapter, generators, seed/parity checks and guards. Inspect running
terminal processes and SDK availability without restarting or logging into an
account. Only an already-running FTMO-bound DEMO/TRIAL USD account may be used;
unrelated/real accounts are not targets. Never call OrderCheck/OrderSend.

Expose the requested module CLI through one thin namespace bridge to the
existing `tooling/ai-engines` implementation. Snapshot five requested assets;
unsupported fields/symbol aliases/session APIs stay unknown, never inferred
as closed/open or zero cost. Python MT5 session availability must be verified;
provide a read-only MQL5 export bridge if required rather than fake sessions.
Collect compressed timestamped Bid/Ask and both quote-time/receive-time clocks.
Shadow uses its own ledger, not broker positions. Missing news/holiday/seed/
spec parity blocks entries; stale data cannot create backdated fills.
Measure excursions on observed quotes; no quotes cannot certify intrasecond
MFE/MAE. Quote-only runs cannot measure realized slippage.

No terminal at inspection: execute deterministic timestamp-paced replay through
the same runner/reducer, label it replay (not a terminal test), and publish a
three-step quickstart. Native shadow requires admitted seeds/calendars; a
one-command entrypoint must fail closed with actionable missing prerequisites.
Use bounded observation sessions, no permanent background service.

## Track3: reversible, source-exact evidence compaction

Inventory D workspace and E backup before/after, retaining read errors and
logical-versus-physical scope. Only the explicit completed V19 job subtree is
eligible. No raw market sources, other campaigns, freezes or failed attempts
may be lost. Wait until financial readers finish before removing original
large evidence files/NPY packs. Keep metadata/small files in place.

Zstandard level9+, per-file original and compressed SHA256/size in MANIFEST.
Verify decompressed bytes for every candidate, then preflight all current
original identities/hashes before any unlink. Reject links, scope escape,
concurrent drift, existing conflicting outputs and unsupported manifest paths.
Remove only exact admitted originals after full verification. New reader
supports archived originals and canonical original hash; provide exact restore
for frozen legacy consumers without changing their pinned source. Preserve
content and every negative attempt; report actual savings, not a forced target.

## Tracks4–5: measured performance and delivery

Smoke is **unittest**, not pytest: profile the actual 78-ID runner and startup.
Keep all IDs/assertions and isolation, count fixture setup/import/startup inside
wall time. Preserve baseline, paired diagnostics and outliers. No skip/removal,
off-clock warming or repeated final attempts to choose a good streak.
After justified optimizations and financial jobs idle, run exactly ten fresh
final processes; median target0.55–0.65s, each <0.78s. Run full four-runtime
suite with all 1,216 V19 IDs plus meaningful regressions; target <16s, zero skip.
Targets are measured outcomes, not permission to weaken correctness.

Commit coherent checkpoints with two AI trailers, inspect diffs/secrets/links/
artifact budgets, push and open PR99. Wait three green checks on exact final
HEAD, download full CI test IDs and reconcile to local IDs. Leave PR open.
Four-part report: sizing/localization, MT5/quickstart, compaction, performance.
Retain failures and unachieved targets; no qualification from technical PASS.
