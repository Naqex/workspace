# V5 — bounded overnight campaign

Owner task `36b050c6-aa94-4b8c-bb1d-8c5520b23a61`. PR82 merged `5beeb75`;
V4 branch deleted. Branch `codex/prop-overnight-v5`.
Keep VI Dubber WIP, Trader pin, no broker/model/paid calls.

## Scope

Selection, diagnosis, new thresholds: Dev2022–2023 only. V4/2024 outcomes
remain exposed history; do not use them to select. Freeze code/composition
in Git before new Validation2024 traversal. 2025–2026 permission expanded
only to timestamp/coverage/metadata audit; no price parsing, indicators,
signals, PnL, source hash of holdout price payload or charts.

## Workstream1

Read local filename census and QDM symbol/cache inventory. No invented Ask,
M1, late quote moved backwards, or new provider download. Recover the exact
28 originally incomplete cells (24US500,4AUDUSD), compare with existing V3
clock repair, no new horizon/search. GBP existing H1 screen is not an admitted
M1/tick ledger. If no bounded native source exists, record unavailable and
continue other workstreams; do not promote conditional source or claim recovery.
Stage0 retains raw stress mean positive each Dev year and scale/retention;
Stage1 naturalSL, both corr<.25 and marginal Net/DD; max one third sleeve.

Blind audit may export **DateTime only** from existing QDM M1 caches,
2025-01-01 through2026-10-31; no update/download. Count coverage/gaps by day
07–21UTC, weekdays and closures unknown separately. M1 timestamps alone cannot
certify Bid/Ask, same-minute ordering, full path, pristine OOS or tick acceptance.

## Workstream2 — exactly two mechanism trials, no combinations

First reconstruct native EUR equity DD from joint paired ticks at $150
reference, identify peak/trough/recovery, side cash and held-exposure accounting.
Record overlap/boundary floating contributions; side diagnostic is not causality.

- D1: one preentry structural gate. Skip EUR sweep if completed Asia00–06
  range >2.0 times causal ATR14 H1 before signal. Fixed2.0 before outcome;
  no early-exit alternative or threshold grid.
- D2: sleeve shadow closed netR stream, every original admitted opportunity
  observed irrespective of funding/account rejection. Cold when reference
  cumulative netR DD>=8R; factor.5 until reference stream recovers4R from
  its cold-period trough or reaches prior peak. Canonical netR uses $150
  reference; state updated only after original closed event, never at entry
  from future trade outcome. Gold/EUR own states, reset at phase change;
  annual reference books and continuous account do not reset on NewYear.
  Skipped trades are shadow research observations, not execution fills.

Compare parent,D1,D2 on Dev at fixed-$150 reference and portfolio. Eligibility:
EUR DD and combined DD both lower, each EUR annual net >=80% of positive parent
and both models combined portfolio net >=80% parent, no added breach. Choose
largest combined DD reduction among eligible, tie lower EUR DD then name.
No eligible -> parent signal policy. No D1+D2 stacking or third trial.

## Workstream3 — sole state-machine design

Keep V4 nominal budgets/cap/reserve/dailyhalt. At phase1 peak observed equity
or balance>=53.5k latch riskcap$125. Subsequent observed equity<=52.5k
latches riskcap$90 and requests flatten of open positions; no reopening above
protected-floor reserve unless projected stop proceeds exceed52.5k.
This may park an account below target; disclose instead of silently unfreezing.
At phase2 peak>=51.75k cap$100, no additional invented floor.
Gap/slippage can cross protected floor; no absolute guarantee.

Funded: cycle firsttrade+14calendar days, then previous modeled request+14d.
Threshold$50.5k (one fixed choice, not$50.75k); if <=48h to due, latch
PRE_PAYOUT_FREEZE: reject entries and request closure at next20:30UTC
or earlier holiday flat, before due. Balance>=51k latches PROFIT_LOCK_IDLE,
reject entries and liquidate on each asset's next admitted quote.
Request only when due, flat, closed profit>=$20; debit allprofit,80/20,
zero approval delay, no account replacement. If liquidation costs erase
profit, no reward, record failure; never claim payout100%.
If due passes with no profit, cycle remains due; request at next eligible
flat event; do not roll forward to hide a missed cycle.

Dynamic liquidation uses next real quote for each asset; carried other-asset
mark cannot be an order fill. Quote absence -> pending/unknown. Process tick
thresholds chronologically. Ratchet activation does not retroactively resize.

## Workstream4 and statistical budget

Validate36starts x2swaps, plus 3rd-sleeve column only if source/Dev gates pass.
No independent probability from overlapping windows; funded uniqueness by
matching post-phase2 trade path, distinct is not necessarily non-overlapping.
Report all six columns; absent third sleeve stays N/A, never duplicate column.

Bootstrap: fixed seed20261115,10,000 paths/model,12months/252businessdays,
primary contiguous20businessday blocks,5day sensitivity predeclared.
All assets/sleeves resampled jointly, not independently. Maintain within-block
ordered daily/trade extrema and shared account state. Do not treat bootstrapped
point estimates as calibrated future probabilities or new edge evidence.
Cross-block open-position and extrema aggregation assumptions must be explicit;
if daily aggregation cannot reproduce exact V5 lifecycle, label it a stress
surrogate, show its parity gap and do not call it exact tick V5 MonteCarlo.
Funded-start experiment separate from challenge-start; annual payout after
split/fees scenario, not real cash or guaranteed salary.

## Workstream5

Fixtures for source/timestamps, D1/D2 causal boundaries, ratchet/freeze/lock,
quote freshness, full-debit reward and bootstrap indexing/accounting.
Alternate arithmetic for all72V5accounts and all dynamic closes; same operator,
not independent person/model. Source checks reuse current hashes where unchanged.
Retain negative outcomes/trials and failed attempts. ReportMD+JSON/context,
coherent commits/push and one PR with3greenCI; do not merge new PR.
