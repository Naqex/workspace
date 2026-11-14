# V4 — Co-core allocation and payout extraction

Owner task `d6d78dc3-c7e9-40ee-a684-61490c368f27`.
PR81 merged `5864d8b`; V3 branch deleted. Work on `codex/prop-cocore-v4`.
V3 results remain immutable, including failed/conditional source scenarios.

## Scope and selection budget, registered before new numeric outcomes

- Phase0 reads archived V3 outcomes, including already-exposed 2024, only for
  requested diagnosis. Selection/rebalancing uses 2022–2023 exclusively.
- No 2025–2026 price files, decoding, hashes of raw contents, charts or outcome
  queries. Readiness may inspect filenames, file sizes and existing metadata.
  File presence is not quality, complete coverage or pristine-OOS certification.
- Keep VI Dubber WIP, Trader pin and broker/provider/model authority unchanged.
- No new signal parameters, symbols, exits or source downloads. A and EUR
  natural SL/entries/deadlines/cost assumptions remain exactly V3.
- Audit exactly the archived Top10, retaining original rank (EUR is rank6,
  not rank1). Compute daily correlations against both A and native EUR on
  aligned Prague business days, including zero days. Require complete M1/tick
  path, verified carry assumption, median friction/SL <=15% and >=50% retention
  in each Dev year, plus owner economics/correlation/marginal gates.
  Conditional H1-only candidates cannot be promoted. Existing source gaps are
  not economic failures. At most one third sleeve; no source rescue by tuning.
- Marginal screen uses A + 0.5 EUR plus a 0.5 reference-risk candidate, fixed
  before measurement, both swap scenarios. Horizons sharing entries are not
  independent. No candidate without source/scale admission can enter replay.

## Exactly one co-core policy trial

Use equal risk, not inverse-DD weighting: a noisy two-year DD estimate is not
enough to justify a fitted weighting. Both Gold and EUR receive:

| Phase | Nominal USD risk per trade / initial 50k |
|---|---|
| Step1 | 200 / 0.40% |
| Step2 | 175 / 0.35% |
| Funded | 125 / 0.25% |

Keep V3 causal equity throttles: equity <=48k caps new orders at $150;
<=47k caps at $90. Existing positions retain size. Daily realized loss >=$1k
latches entry halt until Prague reset. Raise gross initial-stop cap from
$500 to $800 (1.6%); no hedge/correlation netting. Raise internal causal
projected stop/funding floor from $46,500 to $46,000 (8%); actual measured
Dev static loss must remain <=8.2%, daily <5%, no modeled rule breach.
Low daily correlation does not guarantee intraday independence. The ~2%
remaining to the static rule is a model-error buffer, not free risk.

Run 24 monthly Dev starts x 2 swap scenarios at 14-day reward proxy.
Retain V4 only if all safety gates hold; no second policy/risk grid to rescue
failure. Regardless of performance, freeze the sole tested policy and verdict
before requested Historical Validation; failed Dev remains failed, never
promote using 2024. No hard TP, stop widening or side deletion.

## Reward semantics and validation

14 days means earliest request eligibility after first funded trade, flat
positions/pending, positive realized balance; approval and actual transfer
are outside the model. Compare 14- and 30-day **scheduled request proxies**,
with full profit debit, 80/20 split, minimum $20, no administrative delay,
same account retained and next interval measured from previous modeled payout.
This repeated scheduling/reset is an explicit research assumption, not a
guaranteed FTMO bi-weekly cash flow. Confirm current official terms; 2-Step
rules differ from 1-Step. No challenge fee/retry/tax/cash injection.

Commit code/rules/composition before new 2024 price traversal. Validate
36 starts x 2 swaps x 2 reward schedules =144 V4 accounts; one joint traversal.
Add bounded diagnostic accounts: EUR fixed-$150 annual/combined books and
the two archived V3 funded paths. V3 rejections/throttles are extracted from
archived full ledgers; diagnostics must reproduce V3 cash/DD/pass dates.
Report five requested comparison columns, plus the reward-schedule comparison.
Overlapping starts and shared funded paths are not independent pass estimates.

## Verification and delivery

Reuse Account lifecycle and paired-tick replay; expose only policy hooks with
V3 defaults unchanged. Test deadline causality, default parity, new cap/floor,
throttle boundaries, reward eligibility/flatness/full debit, and source gates.
Alternate accounting oracle checks every V4 account, entry and rejection.
Same-implementer arithmetic review is disclosed; not independent human/model
review. Preserve source checks already verified; do not rerun raw tick census
unless source bindings change.

Keep full results/negative cases, source/rule hashes, progress and receipt in
`execution-v1/prop-cocore-v4-20261114`. Update context/index. One PR, three CI
green at exact HEAD; no auto-merge, no holdout release, no purchase/trading.
