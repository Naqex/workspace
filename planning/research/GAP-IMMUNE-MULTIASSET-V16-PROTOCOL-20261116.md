# V16 — Source evidence, causal pre-break exits and bounded intraday breadth

Owner: attachment `350f1c53-244d-4ff7-96f3-0fa6e69cff67`.
Use its last complete six-track specification; the earlier interrupted draft
does not create an additional stop/exit grid. PR94 merged `1c6e516`;
V15 branch deleted. Branch `codex/gap-immune-and-multiasset-v16`.
No broker/provider downloads, paid feed, deployment, Astra, memory updates
or PR95 merge. Preserve VI WIP, Trader pin, original data/freezes/attempts.

## Corrections and source contract

V15 has 133 trade-gap occurrences (95 model-low-risk,38 conditional native
envelope exclusions), not95 independent trades. All-uncertified stress
changed56 trades, including all133 occurrences, not95 forced -1R fills.
66/72 old starts completed with prices through13Oct2026, not within
Development alone; overlapping starts are not calibrated probabilities.
2026 is partial and many recent windows have short exposure.

Native tick exports are quote records, not a consolidated exchange order
book. Zero recorded ticks, endpoints close together, or a distant stop do
not prove an uninterrupted feed or complete market history. Keep
RECORDED_ZERO_TICKS and conditional source-envelope evidence separate from
continuity certification. Never pad flat M1, infer closures from gaps, or
claim a broker/market guarantee. Known closures and complete observed M1
coverage may support a declared source-path scenario, not tick-exact fills.

Refresh metadata in D workspace/E backup, including archive members.
Reuse verified schemas, UTC receipts, bounded native tick/CSV/BI5 readers.
Decode relevant Development intervals before selection; source audit and
attribution of already exposed later data may be read but not used to tune.
Unsupported/unreadable sources remain explicit. New observed M1 backfill
gets a new MarketDataStore version with raw hashes; never overwrite V14.
If38 envelope cases contain zero actual quotes in the missing minutes,
record zero backfill rather than manufacture38 bars.

## Fixed execution policy and research budget

G2 is one ex-ante policy: close by20:30 UTC every trading day (or earlier
registered holiday/Friday guard); US500 also clamps to16:00 New York under
the existing declared source-session model. Decisions/entries after the
known same-day cutoff are skipped before outcome, with counters.
Market close is at the first observed quote at/after request, never the
hindsight last bar before a later-discovered outage. Unscheduled gaps
remain unknown, including short1–5 minute gaps. Recheck zero crossings
instead of promising it. A zero-gap requirement that fails blocks
qualification; do not remove individual losing/uncertain trades ex post.

Keep A's entries, natural stops/P1 and V15 factor1.5+cushion/account
controls. Only the fixed causal deadline changes. No MAE stop-cap grid.
Report original natural SL/lot quantization by sleeve/year. Day1 stagnation
and MAE distributions, if measured, are descriptive, not extra exit trials.

Intraday scan reuses every V12 cent-corrected DAY cell (F1–F5,
P0/P1 and the already registered F5 P2),722 cells across five assets.
Exclude all same asset+recipe clones of the three A mechanisms before
outcome. No new thresholds, direction selection, exit grid or data-driven
time window. Record the final exact IDs and exclusions in registration.
H1-only GBP/AUD cannot masquerade as M1/tick SL certification: first seek
real finer sources; if absent, mark DATA_PATH_INCOMPLETE, no interpolation.

Reuse Stage0 economics/scale screen before path work: positive SYM endpoint
net in both2018–2020 and2021–2023; median friction/natural SL<=15%;
retain>=50% of natural signals per cluster. Then SL-active two-order
M1 replay. Admission: positive SYM SL-active net in both clusters,
no unclassified path crossings for any admitted signal, same-day exits,
average>=40 admissions/year, mean net>=.04R and absolute daily PnL
correlation<.20 with G2 A. Undefined correlation fails.
No proof of independence from a low sample correlation.

Pick at most2 sleeves, rank by descending worst-cluster annual SYM R,
then canonical ID, one asset+family per slot, and require pairwise absolute
correlation<.20. Equal requested CORE risk, existing shared caps/reserves;
no weights/risk search. If none qualify, freeze an empty addition and
report the multiasset column as identical to A, never invent a new alpha.
If a source-verified portfolio is unavailable, report that fact and keep
conditional and strict stress results visibly separate.

Commit selected IDs/execution/cost/source pins after Development audits
before evaluating new policy outcomes on2024–13Oct2026. Prices are already
exposed; this is not pristine OOS. Full comparison: V15 cushion baseline,
G2 A strict stress, G2 A+selected sleeves, same portfolio strict stress;
both cost scenarios/orderings,105 monthly starts and standalone Funded.
Reuse unchanged columns only with exact bindings. Report105 and recent33
denominators, censoring, phase passes, median, payouts, daily/static loss.
Targets<18–24months,100–180signals/year,15–25R/year are goals, not promises.

## Engineering, storage and delivery

Measure all1126 baseline IDs in existing four runtimes, retain top15
per-test times. Profile the measured bottleneck; reuse existing weighted
sharding before shared fixture caches. Preserve isolation, all IDs and
0skip. Compare equivalent cohorts and label any additional tests.
Register10 fresh-process smoke measurements; retain failures/outliers.

Inventory V1–V15 cache/log/intermediate artifacts. Protect source/raw data,
frozen inputs, ledger/path evidence, manifests, active consumers and every
file needed by code or CI. Compress safe closed-job intermediates with
SHA roundtrip and restoration proof before removing redundant originals.
Do not repurge V14/V15 trees or partially remove installed packages.
Keep hydration/restore locators for compacted old paths.

Extend standalone arithmetic/path/tick auditor with negative fixtures.
Same implementer/feed is not independent human/feed review. Finish a
four-part report and compact JSON<=1MiB, update current context/index,
commit/push PR95, exact-head3CI and downloaded artifact ID reconciliation.
Keep PR95 open.
