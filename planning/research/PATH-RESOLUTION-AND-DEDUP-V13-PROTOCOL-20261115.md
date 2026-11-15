# V13 — Path resolution, ensemble and directory deduplication

Registered 15/11/2026 before new financial outcomes. Owner instruction:
attachment `09a78309-e655-4925-898e-19e34aa2cdef`. Parent PR #91 merged
`ad362ea`; V12 head `6b063dc`. Branch `codex/path-resolution-and-dedup-v13`.

## Fixed experiment

Only the 28 V12 available-path dual-positive cells, including the 19 cells
whose sole recorded failure is `PATH_OR_ENDPOINT_INCOMPLETE`. Reuse immutable
V12 decisions, entries, natural stops, P0/P1/P2, admission ratios and costs.
No new entry grid, side selection, trail, bar-close stop, horizon or weights.
Original V12 matrices/attempts/seals remain unchanged. This resolver is a
new declared execution scenario, not a retroactive correction to V12 PnL.

Development is 2018–2023, with only the inherited 2017 warmup/source slice.
Do not load price values from 2024–2026 before the Development decision and
a committed composition/account-admission freeze. Cutoff, if released, stays
13/10/2026 from prior campaigns; do not load later observations.

## Path evidence and causal execution

For all 28 cells, record every unresolved event and the exact crossed gaps
and missing endpoints, timestamps, scheduled minutes and unclassified minutes.
Keep raw counts and cost-admitted counts separate. Gold has a declared New
York 17:00–18:00 daily break; FX has no equivalent CME daily break. Preserve
the V8 source-confirmed 31/12/2021 normal-hours correction and its explicitly
conservative 16:58 eve guard; do not silently restore a full-day closure.

Calendar closures must be registered from deterministic external calendars,
never selected by their PnL or inferred as true closures from absent prices.
Historical FTMO times which cannot be verified remain declared proxies.
An early-close/pre-break flat uses a predetermined last complete minute before
the declared boundary, not the retrospectively last observed quote before an
unknown feed gap. For a daily break deadline, defer to the scheduled reopen
and charge every crossed rollover. For a known break longer than two hours,
clamp before closure. Missing quotes at a scheduled target defer to the next
observed open; they cannot justify an anticipatory close.

Two distinct coverage labels:

- `SOURCE_OBSERVED_OR_SCHEDULED`: observed path with only registered closures.
- `DECLARED_NEXT_QUOTE_SCENARIO`: unscheduled source gaps traversed by the
  owner-authorized next-available-open policy. This is deterministic pricing,
  **not** proof of full source coverage or a conservative bound on a missing
  excursion. A stop may have touched and recovered inside a storage gap.

Stop crossed by the next observed open fills at the adverse open plus normal
stress execution costs. Otherwise traverse observed OHLC, stop before TP on
same-bar ambiguity; P1 protection activates on the next observed bar after
the trigger, never within the trigger bar. At a deferred horizon, process the
open against the currently active stop before time-close; do not read the
future high/low of that endpoint bar. Missing-bar uncertainty is never erased.
Keep verified-only and declared-scenario eligibility separate. Scenario
ensemble/lifecycle, if admitted, must carry the same conditional label.

## Component and ensemble gates

Keep V12 component economics/scale/retention gates: both three-year clusters
positive under SYM for raw and admitted cohorts; median friction/natural-stop
ratio <=15%, retention >=50%, mean admitted SYM >=0.04R. Require deterministic
pricing for every event. Report source uncertainty separately from pricing.
Do not treat multiple path modes of one recipe as independent discoveries.

Reuse mechanical correlation/decision-overlap graph, medoid and lexical tie
rules, equal risk, maximum eight components, threshold 0.25. No subset search
or asset quotas. A surviving pair with correlation >=0.25 is not accepted
merely because another member of the same connected component is its medoid.
Report actual selected-pair correlations. No minimum K=4 inherited from V12;
at least two distinct mechanisms/assets are required for a multi-mechanism
ensemble. If selection yields zero components, report no ensemble, not zero
returns.

Owner V13 cadence gate: >=50 trades in **each** Development year; 120 is a
target, not an upper limit. Stability gate, under both cost models:
`positive_years >=5 OR (2018–2020 >0 AND 2021–2023 >0 AND ex_best_year_R >0)`.
This deliberately replaces V12's >=60/year and AND interpretation. Do not
relax further after outcomes. Report raw and admitted results and concentration.

If the Development gate passes, commit composition, exact code/input/calendar/
cost hashes, lot quantization, account risk and overlap policy **before**
opening 2024–2026. Reuse existing lifecycle/account engines and risk profile
rather than invent a new machine. Verify actual account path, Prague midnight,
fees, swap and lot sizing before claiming daily/static qualification. The
historically exposed 2024–2026 market data are post-exposure evaluation; F5
may be first evaluation of that mechanism on already exposed market data,
not independently clean market OOS. If Development fails, do not open those
prices or run an empty/failed portfolio through a nominal nine-year replay.

## Storage and independent verification

Compare D snapshots at the same root, logical-byte scope and decimal GB/GiB;
test the asserted +15GB growth rather than assuming it. Jobs/matrices stay
on E. Inventory does not certify inaccessible VI directories.

For candidates from all 1,998 verified file pairs, hash every relative path,
file size and SHA256 in each proposed directory tree; include empty folders.
Refuse symlinks/reparse points, unreadable files, changed-during-hash files,
active consumers, unique files, canonical-role ambiguity or required installs.
Byte equality alone does not make an installed dependency redundant. Check
hardlinks and distinguish logical bytes removed from physical space freed.
Only remove proven redundant, unused copies with an intact canonical and
restoration manifest; preserve raw/research evidence, V1–V12 pins, VI WIP and
active runtimes. No deletion just to produce a positive savings number.

Extend the independent Decimal/scalar auditor without importing producer
accounting or execution. Verify all 28-cell path records and cost legs,
including unresolved-origin events, next-open stops, holiday clamps and P1.
Preserve every prior 1,072 test ID; add meaningful gap/causality regressions.
Smoke target <1s; disclose the measured machine/runtime. No new background
service, broker calls, paid source, Astra prompt, runtime promotion or skill
changes. Finish report/context/index, commits and PR #92, exact-head 3/3 CI
and test-ID reconciliation. Do not merge the new PR.
