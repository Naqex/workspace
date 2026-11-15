# V15 — Missing paths, sleeve attribution and bounded sizing calibration

Owner authorization: attachment `29ac4240-5409-49a1-bc75-f2a49da8e10b`.
PR #93 merged `69bc7a6`; V14 head `c6090ef`. New branch
`codex/bridge-certification-and-velocity-v15`. Register before V15 financial
outcomes. Preserve V1–V14 attempts, original freezes/errata, source data,
Trader pin and unrelated VI Dubber WIP. No broker, paid feed, deployment,
actual payout, Astra message or new alpha/exit/sleeve/weight search.

## Scope, hypotheses and limits of inference

Candidate A remains exactly the three V14 sleeves. Candidate B is retired
from new account research; reuse its five-sleeve V14 tape for attribution.
Both M1 orderings and SYM/ASYM costs stay as in V14. 2024–13Oct2026 already
has price and baseline outcome exposure. The new sizing selection uses only
2018–2023 outcomes; commit selection/code before evaluating later sizing.
This separation does not turn exposed prices into pristine OOS.

Measure duration, wins/losses, exit reasons, known closures, unknown small
and large gaps, and duration strata for 296 clean vs 44 uncertain Dev trades
and corresponding later trades. Longer exposure can induce selection in
the clean cohort, but association does not prove every omitted trade is a
winner or that no stop occurred. Keep all missing-path trades in stress.

An HTF envelope can exclude a level only with correct bid/ask, interval,
active stop and justified quote-universe coverage. An aggregate of the
same incomplete M1 is not additional evidence. Distinguish native recorded
quote extrema under an explicit complete-export assumption from complete
market/broker extrema. Never erase original source-uncertainty labels.
Inventory native HTF candidates and existing native tick exports; bind raw
schema/UTC/side/units/hash and provenance. Unsupported files stay unknown.

Brownian/ATR distances are statistical assumptions, not deterministic
price bounds. Use signed distances: endpoints on the stopped side are not
safe. Estimate price-change sigma using up to 240 prior one-minute
increments, requiring >=60 valid contiguous increments. Report the
conditional Brownian bridge crossing model
`exp(-2*d_before*d_after/(sigma^2 * minutes))` for positive distances,
including its log probability; Gaussian diffusion/jump-free assumptions
are not a model of every actual price path.

Fixed diagnostics, not parameter search:

- Native/HTF extrema must exclude the active stop throughout the gap
  under their stated source coverage to receive a conditional exclusion.
- Otherwise call a bridge `MODEL_LOW_RISK` only if positive minimum
  endpoint distance exceeds BOTH `3*sigma*sqrt(gap minutes)` and
  `2*max(adjacent M1 range)`. No `BRIDGE_SAFE_CERTIFIED` label from sigma.
- All other unknown bridges are ambiguous. Primary bridge stress forces
  stop excursions there. Also publish all-uncertified-gap stress at V14
  sizing. Neither is a mathematical lower PnL bound: stop gaps can exceed
  -1R, fees matter, and joint account admissions/harvesting are nonlinear.

Stress must use one shared synthetic price path per asset, not mutually
inconsistent per-trade fills. Insert explicitly synthetic missing-minute
OHLC excursions through active stops, replay the unchanged signal tape/
SL/P1/deadlines, and expose any case where a time-close/order prevents the
intended forced stop. Keep observed prices intact; no synthetic bar is
admitted to MarketDataStore as observed data. Check secondary stops and
two OHLC orderings. Reject incoherent price/ledger claims rather than
assigning every trade -1R by fiat. Synthetic extrema are a sensitivity,
not evidence the excursion actually happened.

## Fixed sizing budget, selected only on Development

Reuse V14 cost adapter and V4/V6 lifecycle. No duplicate phase or payout
engine. All account replay uses actual lot floor/cent cash, Prague anchors,
four trading days per phase, static 10%/daily 5% modeled limits, and V6
Funded harvester. Original V14 baseline remains unchanged and is reused
where exact inputs match.

Test exactly six proportional phase-risk schedules:
`factor = [1, 1.25, 1.5, 2, 2.5, 3]` times `[200,175,125] USD`
(phase1/phase2/Funded on 50k). Equal requested risk across A sleeves.
All V15 grid schedules have the same new controls:

- equity <=47,500 USD (static DD >=5%): cap requested risk at150 USD;
- equity <=46,500 USD (static DD >=7%): cap at75 USD;
- shared initial stop-risk cap1,000 USD (2%); funding-inclusive stop reserve
  strictly above45,800 USD (8.4%); realized daily halt remains -1,000 USD;
- no phase1/2 V5 ratchet and no widening SL, changing entry, TP or horizon.

These controls themselves form part of each V15 version; factor1 is not
mislabelled as the V14 policy. Report rejections/cap parking and actual
risk by phase/sleeve, not just nominal percentages.

Run the primary bridge-stress tape on monthly Jan2018–Dec2023 starts,
censored at01Jan2024, plus standalone Funded. Assess both cost models and
both M1 orderings; do not force-close at sample end.

Eligibility: zero modeled breaches; maximum daily loss<2.5%; maximum static
loss<=8.2% across all four model/order combinations. Among eligible
schedules, prefer the observed static-DD target band7.5–8.2% if available,
then rank by highest worst-combination count completing both phases,
lowest worst-combination conditional median time, then smaller factor.
Median with no completions is infinity. Report the pass-count denominator
and censoring. If no eligible schedule exists, declare calibration failed
and use factor1 only as a diagnostic comparator; never call it qualified.
Do not change thresholds/grid after seeing results or force DD into a band.

One additional cushion version, no grid: same selected phase schedule and
controls; phase1 arms on realized balance>=51,500 USD, disarms at<=50,000,
and only while equity>50,000 adds `min(20% * positive realized profit,
250 USD)` to requested risk. Base/throttle/cap/reserve still apply.
Phase2/Funded unchanged. Count this as a seventh policy exposure. No
independent optimization of cushion trigger, fraction or cap.

Freeze exact selection plus code/data/calendar/cost/account pins in Git
before new 2024–2026 sizing outcomes. Then run 105 monthly Jan2018–Sep2026
starts and standalone Funded through14Oct2026 exclusive for four columns:
V14 original; V14 primary bridge stress; V15 calibrated bridge stress;
V15 cushion bridge stress. Include both costs/orders and supplemental
all-uncertified stress baseline. Goal median<18 months is a test target,
not promised and not sufficient by itself for promotion.

## Storage, audit and delivery

Refresh all47 held targets; group purpose/reference/distribution ownership,
size/files and overlapping subtree totals. D/E are different volumes:
hardlinks cannot deduplicate a D file into E. Do not corrupt installed
environments by deleting package subtrees while leaving dist-info claiming
they exist. Metadata/import consumers count as references. For small
installed subsets or live references, explicit keep with quantified reason
closes the disposition; do not delete solely to claim completion.
Safe unused copies may be archived with SHA roundtrip/restore proof before
deletion. Preserve Git/raw evidence, active environments and VI WIP.

Extend the standalone auditor with independent envelope/bridge/duration
checks and independent sizing/admission/cash/phase/payout checks. It is the
same implementer/feed, not independent human review. Preserve1,110 test IDs,
add behavioral regressions, zero skip. Profile before optimizing. Register
ten consecutive fresh-process smoke measurements, retain all outliers;
body target<0.85s (heading<0.80s also reported), without case removal.

Publish four-part report/compact JSON, context/index links, exact-head
3CI and downloaded test-ID reconciliation. Open PR #94; do not merge.
Keep failed attempts and trial history; no memory or global config edits.
