# V17 — Causal session screen and one Development-derived risk policy

Owner: attachment `daced458-63a4-48d2-ba7b-4e052d20ccd5`.
PR95 merged `0fb47ae`; V16 branch deleted. Branch
`codex/adaptive-velocity-v17`. Preserve raw sources, old freezes/attempts,
Trader pin `930fa76882e741702620f626986bb38755368635` and VI WIP.
No broker, deployment, new providers/downloads, Astra or memory updates.
Finish PR96/exact-head3CI and keep it open; V18 is not authorized here.

## State and causal corrections

V16 is not a swing+intraday portfolio: all494 full-period signals close the
same day, with32 source-uncertain paths. No48h open position can explain its
admission rejections. Count cap/reserve rejections and unique signals separately
from overlapping accounts; never call a skipped signal profitable/high quality
using its subsequent outcome. The cap rejects rather than partly shrinking lots.
Equity throttle, lot floor and explicit tier weights are separate mechanisms.

Before20:30, tomorrow's quote completeness and absence of future SL excursions
are unknown. An archive/HTF bar covering the coming night is future information,
not a carry certificate available at20:30. None of the current sources provides
an ex-ante lossless future-path guarantee. Thus conditional overnight carry
remains disabled: keep V16 daily-flat/known early-close policy; no re-entry
variant. Positive floating profit alone cannot certify a future gap.
07:00–20:30 avoids overnight exposure but does not guarantee uninterrupted M1.
Keep uncertainty and strict stress; never erase gaps or drop individual trades
because of future missingness. A whole candidate with any unknown path cannot
qualify. M1 two-order replay/fixed Ask are declared scenarios, not broker fills.

FTMO Standard historical calendar/news/spec coverage is not certified. Current
official FAQ distinguishes Evaluation news flexibility from selected-event
restrictions on Standard FTMO Accounts, and requires flat before market breaks
longer than2h. Existing controls are not proof of100% broker compliance. Record
official references and unmeasured news/forward execution separately.

## Fixed experiments, Development2018–2023 only

1. Diagnose V16 Dev PRIMARY and STRICT admissions without rerunning unchanged
   accounts. Attribute cap skips to already-open accepted positions; report
   swing blockers0, unique events and account occurrences. Do not optimize a
   controller around later2024–2026 outcomes.
2. Replay each of the three unchanged A sleeves separately at fixed150USD stop
   risk on Dev, two costs/orderings, with existing quantity/cash/MTM accounting.
   Rank by worst of four annual-Net-R / floating-R-DD ratios (6years, no CAGR
   claim, same costs and reference risk). Highest finite positive score gets
   Core1.0; other A sleeves Support0.6. Tie: canonical ID. If no finite positive
   score, mark rank inconclusive and retain canonical-first diagnostic tiers.
   New eligible additions are Support0.6; no redistribution or risk increase.
   No other tier/weight/grid. Tier multiplies the parent V15 factor1.5+cushion
   request **after** its equity throttle, floored to0.001USD, conservatively. No performance-based
   choice between V16 equal risk and the tiered result.
3. One bucket contract: total initial-stop cap1000USD; swing cap400USD and
   intraday reserved600USD. Intraday may borrow unused swing headroom; swing
   cannot borrow intraday reserve. Classification uses intended causal deadline,
   not realized exit or original name containing24H/48H. This reserves600 for a
   fresh intraday request when swing<=400; it cannot promise unlimited admissions.
   Intraday self-concurrency, lot grid, harvest and global loss controls still
   reject. With carry disabled all real V17 core trades are intraday, so the
   swing cap is dormant; validate the two-bucket invariant with synthetic cases.
4. Add one prospective daily reservation floor: projected all-position loss
   including entry/exit costs and declared funding must remain strictly above
   Prague-day balance anchor minus1200USD (2.4% of50k). Keep V15 total cap,
   8.4% overall reserve, realized daily halt, phase risks and Funded harvest.
   It is an entry guard, not a guaranteed fill/forced-exit bound through gaps.
   Actual equity DD remains measured. Do not introduce another exit search.
5. Session discovery reuses all503 V16 registered DAY cells on XAUUSD198,
   EURUSD103 and US500202, same recipes/P0/P1/registeredP2 and clone exclusions.
   Only known clock changes: entry>=07:00UTC, before same-day20:30/earlier
   registered close (US500 also16:00NY). GBP/AUD remain data-incomplete.
   Stage0: unconditional and admitted-cohort endpoint economics reported;
   inherited gate positive admitted SYM endpoints in both2018–2020/2021–2023,
   median friction/median natural SL<=15%, retention>=50% in each cluster.
   Then scalar/two-order SL-active: positive both clusters under both orderings,
   every admitted path priced/no unknown crossing/same-day, >=40/year,
   mean>=0.04R, absolute closure-day reference-R correlation<0.20 with the
   frozen tiered A reference. Undefined correlation fails.
   Select at most2 by worst-cluster annual SYM R, canonical-ID tie break;
   distinct asset+family, pairwise absolute correlation<0.20. Do not tune
   thresholds, time window or trade subset after outcomes. Empty selection
   is valid; do not build speculative multiasset accounting unless needed.

Commit source/code/tier/selection freeze after Dev audits, before measuring the
new policy on2024–13Oct2026. Later prices have already been exposed, not pristine
OOS. Original V15/V16 pins remain immutable; record line-ending-only checkout
transformations using matching Git blobs rather than rewriting old pins.

## Longitudinal comparison and verification

Compare V15 CUSHION, V16 daily-flat, V17 tiered/bucket/guard under PRIMARY and
ALL_UNCERTIFIED stress, both costs/orderings,105 monthly starts + standalone.
For V15 strict, the archived V15 stress used V14 risk: do not mislabel it as
CUSHION. Replay the original V15 shared stress tape at fixed CUSHION if exact
matching archived results are unavailable; this is historical attribution,
never a new selection trial. Reuse other identical evidence only with hashes.
Report recent33, phase passes, censoring, conditional median, payouts/counts,
daily/static loss and actual lot usage. Overlapping starts are not independent
success probabilities; payout sums are not income. Target<18–24months/zero
breaches/gap convergence may fail; do not manufacture success.

Reuse independent scalar/Decimal path/account auditor; add independent tier,
bucket and daily-reservation arithmetic with rejection negative fixtures.
Same implementer/feed is not an independent reviewer/feed.

## Engineering and delivery budget

V16 after-matrix28.226s/1138tests is the unchanged-runner baseline. Retain exact
IDs,0skip, test isolation and every failed attempt. Read-only in-memory fixtures
only where profile shows repeated immutable construction; writable copies/state
remain per test, and mutation must fail or remain isolated. Do not replace
recovery/process tests with mocks to meet speed targets. Profile-balanced4-worker
base execution may be measured once against the2-worker baseline; record memory/
worker count and extra V17 tests. Target20–40% is a measurement target, not grounds
for weakening tests. Keep exactly10 fresh78-test smoke attempts, wall<0.80s;
retain outliers, no retry for a good streak.

Storage: reuse V16 retention inventory, refresh V15/V16 job metadata and current
writer/dependency bindings. Protect sources, frozen inputs, price/path/ledger
matrices and complete packages. Cold-pack only closed console/test logs with
SHA extraction/restore proof and hydration locators before removal; no broad
purge, no claim absolute zero bloat or physical reclaimed bytes.
Report results/JSON<=1MiB, update context/index/README, coherent commits, push,
PR96 exact-head3CI and downloaded quant IDs; keep PR open.
