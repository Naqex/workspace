# V14 — Raw evidence, fixed portfolios and nine-year account scenarios

Registered before V14 outcomes. Owner attachment
`3a068d12-5c3e-4595-8838-da3187372d7c`; PR #92 merged `65bf0c2`,
V13 head `e501794`. Branch `codex/evidence-and-lifecycle-v14`.

## Authorization and fixed scope

Owner explicitly replaces V13's per-year cadence requirement with **mean
annual cadence >=50** over six Development years. Preserve the old V13
No-Go; this is a new authorized gate, not a retroactive claim V13 passed.
Run historical 2018–2023 diagnostics, freeze A/B, then evaluate 2024 through
13/10/2026 inclusive and run account scenarios even if results disappoint.
No new alpha, exit, risk grid, SELL-only or weight optimization. No broker,
actual payout, paid source, Astra prompt, production or runtime promotion.

Candidate A is exactly the frozen V13 three-sleeve composition. Candidate B
starts with A and takes the next at most two **complete** V13 cells, in the
existing composer's deterministic `(asset,family,id)` order, with correlation
<0.25 against every member and no >=50% decision overlap against same
asset/family. Exclude exact recipe/mode/horizon clones through these rules.
Use the 26 complete cells, including economic negatives: report whether
adding the fixed next cell helps, never search subsets for a positive B.
If no independent fourth cell exists, record no distinct Expanded candidate;
do not manufacture diversification or relabel a clone. Freeze the exact
A/B list and code/data/calendar/cost/account contract in Git before loading
2024–2026 price values. Historical 2024–2026 is post-exposure market data;
F5's first mechanism evaluation does not make that market data pristine OOS.

## Raw source search and two explicitly conditional views

Read metadata across the full D workspace/E backup, including archives,
QDM cache and native ticks; retain scan errors/unsupported formats. Read only
Development prices until composition freeze. Admit source by schema, time,
provenance/hash, side/units and transformations, never filename alone.
Preserve V1–V13 input files/seals; ingest backfill into a versioned derivative
MarketDataStore/source manifest. Do not edit canonical historical evidence
in place. Only add witnessed missing bars; conflicts produce receipts.

For A's 340 admitted occurrences and all 26 complete cells, enumerate exact
gap timestamps and distinguish known closures, native no-quote witnesses,
missing source hours and endpoint deferrals. Keep source/cost versions and
old→new accounting effects.

Required comparison views:

1. `NEXT_QUOTE`: V13 adverse gap-open stops plus stress, scheduled guards,
   no future endpoint high/low; price source uncertainty remains explicit.
2. `CLEAN_COHORT`: omit signals whose realized path crosses unresolved source
   gaps. **This uses future path knowledge and is an ex-post sensitivity
   cohort, not an executable pre-entry filter, statistical bound or deployable
   strategy.** Only a preknown session closure can authorize anticipatory
   flattening. Do not pretend excluding missing paths proves all-path edge.

Finish the evidence exercise and proceed to the authorized longitudinal and
account simulations. Completion of the exercise does not certify missing
prices, actual broker fills or universal worst-case PnL. A stop can touch and
recover in an absent minute; next-open fills are not a mathematical lower
bound. Full-source certification remains conditional if backfill is absent.

## Account contract — one fixed V4/V6 policy

Reuse CoCore/Harvest lifecycle: initial 50k, phase1 +10%, phase2 +5%,
four distinct Prague trading days/phase, resets balance at each phase,
equal requested stop risk per sleeve 200/175/125 USD in phases1/2/Funded.
No V5 phase1/2 ratchet. Throttle caps 150 at equity<=48k, 90 at<=47k,
shared initial-stop risk<=800, internal reserve>=46k, realized-day halt
at -1k. Lot floor: Gold integer ounces (.01 lot), EUR .01 lot/1000 units,
never round upward to exceed request. Preserve collision policy for same
asset/decision. Do not infer that reference R is equal to account return.

Costs remain V13: Gold .0007% notional/side, .20 USD/oz market slip/side;
SYM swaps -40/-40, ASYM -45/-5 USD/lot; FX 7 USD/lot commission plus
2 USD/lot round-trip slippage, -40 USD/lot weekday funding; Wednesday×3
at registered22UTC proxy. Limit TP avoids adverse exit slip only in ASYM.
Adapt legacy FX fee/slip helpers explicitly: legacy V4 EUR costs differ
from this contract and must not silently substitute them. Cash cent-rounded
at actual lot size; reference lot ratios are not exact small-lot PnL.

Prague midnight balance anchor, floating plus entry/exit fees and swap;
5% Daily/10% static loss. Report first observed breach, not an unbounded
missing-intrabar guarantee. Use registered session calendar including
03/07/2026 correction. Source daily break/calendar is separate from absence
of quotes. Sample-end positions are right-censored, never liquidated solely
to manufacture a final balance.

Funded harvester: 14 calendar days since first funded trade/last payout,
min profit20, modeled trader share80%, full gross-profit debit, no admin
delay; phase3 prefreeze at balance>=50.5k within48h of due, lock/flatten
at balance>=51k, fill at next available own-asset quote. No actual money
received. Persist operations/forced closes, roundtrip payout cash bridge.

Monthly starts Jan2018–Sep2026 =105, each continued to14Oct2026 exclusive.
Run standalone Funded50k from Jan2018 plus per-year standalone views if
needed to answer periods. Period summaries group starts 2018–2021,
2022–2024, 2024–2026, and all; label overlapping 2024 and shared price paths.
Do not sum overlapping-start payouts as independent income/probability.
Report unique funded paths separately from windows and all scenario counts.
Run A/B × SYM/ASYM × NEXT_QUOTE/CLEAN_COHORT, with reference annual books.
For M1-only sources, run both fixed OHLC orderings through reused account
engine; neither ordering is a true intraminute DD bound. Preserve source
uncertainty, stale marks and censoring in every account result.

## Storage, smoke and delivery

Owner authorizes deletion of unused E duplicate copies with a live canonical
D counterpart. Refresh all 106 equal-tree candidates, scan references in
superproject **and submodules**, scripts/CI/config/receipts, active executable/
command paths and dependency environments. References through import/runtime
and pinned raw/research evidence count; absence of a literal full path alone
is insufficient. Never delete VI WIP, canonical install, raw data, Git trees
or frozen evidence. Select only maximal nonoverlapping target trees, rehash
both sides before mutation, retain DEDUP_MANIFEST with file SHA256 and
restore-from-canonical instructions, journal each delete and verify remaining
canonical. Report bytes/files/folders actually removed; hardlinks/logical vs
physical bytes separate. Unsafe candidates remain held with exact reasons.

Smoke baseline is **78**, not66 tests. Preserve all1,091 prior IDs and add
meaningful new regressions. Profile actual time; optimize fixtures/import/IO
without removing cases or weakening assertions. Pre-register ten consecutive
fresh-process measurements after implementation; target each<0.85s. Keep
all failures/outliers and disclose environment variance instead of rerunning
until a lucky streak. Full suite, scalar Decimal path and account audit,
exact-head three CI, CI/local ID reconciliation. Open PR #93, do not merge.
