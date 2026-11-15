# V6 — V4_Harvest, standalone Funded and one-shot holdout

Owner task `ed4d3a18-01c0-4907-8e16-5ffbd13e4440`. Work in Workspace.
PR83 `9f15532` merged as `5a8dd69`; preserve its failed trials as history.
One V6 branch/PR, do not merge the new PR. No broker, purchase, new paid/source
provider, model/Astra/subagent calls. Preserve VI Dubber WIP and Trader pin.

## Candidate and release order

Freeze `V4_Harvest` in Git before reading holdout prices. Original Gold A H4
bias/H1 Asian breakout, original EUR Asia/London sweep; no D1/D2/ratchet.
Original natural stops, Gold 48 calendar hours clamped Friday20:30 or earlier
holiday, EUR same-day20:30 or earlier holiday; no new TP, trailing or filters.
Gold has no new friction admission gate; EUR retains its original15% gate.
Both sleeves risk$200/$175/$125 at P1/P2/Funded, open initial-stop cap$800,
projected stop/funding reserve floor$46,000, equity<=48k cap150, <=47k cap90,
daily realized loss>=1k halts until Prague reset. No reset at NewYear.

Only Funded uses the V5 harvester: first funded trade+14calendar days, then
previous modeled request+14d; closed balance>=50.5k within48h of due freezes
entries and requests flat at next registered20:30/earlier holiday; >=51k
requests liquidation on each instrument's next available quote. Request
requires flat, due and closed profit>=20USD; full profit debit,80/20 share,
zero administrative delay. This is modeled eligibility, not money received.

Run standalone Funded from12quarterly2022–24starts under both swap models.
Jan2022 is the continuous3-year case and the first quarterly start, not a13th.
After the committed freeze, owner authorizes prices/signals/PnL Jan1,2025
through Oct13,2026 inclusive, end-exclusive `2026-10-14T00:00:00Z`.
One evaluation, no parameter selection from holdout. Keep older fences intact
and implement scoped V6 adapters. Fixes must preserve candidate semantics;
retain failed attempts. First evaluation for this campaign is not certification
that this data was globally pristine in every previous project.

## Data and uncertainty, locked before outcomes

Reuse admitted historical joint ticks and trade list2022–24 unchanged.
Export existing QDM cache only, no update/download. EUR native paired tick
export over the bounded holdout supplies H1 bars and exact trade paths,
including Oct8–13 absent from the old EUR M1 cache. Preserve same-ms order.
Gold cache is Bid M1 unless an already-cached paired source is documented.
No Ask=0 or forward price is an observed quote.

When only Gold Bid M1 exists, use a **conditional** constant Ask spread:
median observed Gold A entry spread on Development2022–23, fixed in decision
before release. No holdout calibration. Freeze two OHLC ordering scenarios:
O-L-H-C (primary), O-H-L-C (sensitivity), artificial offsets0/20/40/59.999s.
They are M1-envelope scenarios, never observed ticks or certified worst-case
bounds. Stop gaps fill at the first available modeled quote; inside-bar stop
fills use the scenario quote, conservatively including overshoot. Exact
intraminute order, bid/ask spikes, native stop fills and cross-asset simultaneity
remain unknown. Report scenario sensitivity, coverage and open-path gaps.
No unknown day becomes certified safe; synthetic timestamps do not prove
native quote freshness. Model liquidation on the next scenario observation is
conditional, while EUR liquidation must bind to its actual next native quote.

Use the original2022–24 session table and extend dates2025–26 before price
release: US federal metal early dates17:00 conservative guard, Good Friday
closed/Thursday20:30, observed Christmas/NewYear closures and preceding
Christmas/NewYear eves17:00. These guards are not certified FTMO historical
instrument trading hours. Historical news restrictions, margin/account terms
remain unverified; no `prop_qualified=true`.

Only complete60-minute hours feed the same causal indicator stream, seeded
from the original admitted2021November history and carried through2024 into
holdout. Price gaps remain gaps. Audit source transformations and compare
scoped signal generator against original2022–24 output before release.
No forced sample-end liquidation. Positions with unobserved natural deadline
are right-censored, separately marked; late endpoint gaps stay unresolved.
Account replay preserves the position/fees/swap and reports terminal equity.

## Runs and accounting

12quarterly standalone funded accounts/model,2022–24. Then36original monthly
starts/model2022–24 through holdout and21fresh starts/modelJan2025–Sep2026.
Original36 are recomputed from start with the frozen policy; check Dec2024
checkpoint before continuation, never reset balance/phase/open state at2025.
Annual standalone sleeve books2025,2026YTD at fixed$125 reference, no harvester
or account admission brakes; distinguish reference net from accepted-account
PnL and mark censored exposure. Report BUY/SELL, net/meanR, equityR-DD, daily.
Both swap scenarios: Gold SYM-40/-40 and ASYM-45/-5USD/lot/rollover,
EUR retains declared-40USD/lot. Gold commission0.0007%/side, stress slip
0.20USD/oz/side; EUR$5/lot RT commission and$4/lot RT slip.

Same-operator alternate rational cash-posted-funding oracle for all rolling
and standalone accounts, admissions/rejects, phase transitions, reward debit,
DD and dynamic quote binding. This is alternate accounting, not independent
human/model review. Full relevant fixture suite, source/clock tests, no broker.
Markdown+JSON, current context/index, Git commit/push, one PR with3CI green
at exact finalHEAD. No new MonteCarlo or strategy search.

## Interpretation corrections and current official reference

V4 funded began October2023, not late2024.49,751.56USD is a V3 balance;
V4 balances were49,789.71ASYM/49,634.27SYM. Verify exact checkpoints in
results. Summing sleeveR and subtracting challenge targetR ignores sizing,
admission rejects, overlaps, losses and phase resets; not a payout attribution.

FTMO reward FAQ checked15/11/2026: request from day14 after first trade,
flat positions/pending; review and invoice/payment take additional business
days. Default2-Step share80%. Zero processing delay remains a model proxy.
Source: https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/
Other historical account specifications and session guards retain their
original declared status; no claim of complete current FTMO certification.
