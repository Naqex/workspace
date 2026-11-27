# Exit → sleeves → phase-aware accounts: registered campaign

Owner authorization: pasted task `229f6d76-e9a1-4f58-bcf4-c1545bea757b`,
14 November 2026. PR78 merged `3307fae`; source/result HEAD `630c775` remains
Anchor0. Preserve VI Dubber WIP. Offline only, no broker/model/paid provider.
The task describes Phases0–4; its reference to Phase5 means final delivery,
not permission to invent an additional search. No2025–2026 price decoding.

## Sequence, immutable evidence and selection

Freeze this protocol before new numerical outcomes. Phase1/2 design, pruning,
correlation, ranking and allocation use **2022–2023 only**. All cross-phase
rules below are fixed before new2024 evaluation. Complete all Development
choices before releasing the new2024 outcomes; report2024 confirmation for
each frozen phase without selecting again. 2024 has substantial prior exposure,
so call it Historical Validation, not pristine OOS. Preserve negative trials.

Anchor0: the exact308 A signals, natural stops, observed entries and holiday
calendar of PR78, including210 Development trades. Keep paired SYM−40/−40
and ASYM−45/−5 gold funding,100oz/lot,.01lot steps, .000007 notional
commission per side, .20USD/oz slippage per side, observed Bid/Ask. Rollover
22UTC weekdays/Wed×3 is a declared proxy, not verified historical target terms.
No lowering costs, losing-trade deletion, artificial initial-stop widening,
SELL-only selection or new horizon search. Baseline full results are pinned
and reused, not recalculated selectively.

Cash, equity and fees in integer money units, explicit quote order and Prague
midnight balance anchor. Last observed marks at market breaks remain carried
marks, not fresh quotes or bounds on unobserved prices. Unknown target
news/spec/margin/calendar prevents a full FTMO qualification claim, but does
not prevent completing the requested conditional simulation.

## Phase1: forensics and exactly three exits

Forensics on210 Development positions at reference risk150USD: liquidation
equity after commission, two stress slippage legs and accrued funding;
day1 is entry until first22UTC rollover, exclusive. Count nested MFE
thresholds1/1.5/2/3R, final negative and >=50% giveback of peak. Compare
pre-rollover liquidation with final liquidation; report mark age and
increment after rollover, not a causal claim about a hypothetical second day.

All exits preserve A entries and the initial natural SL, and may only shorten
the parent path. Initial hard stop and registered holiday/Friday deadline
always remain active. Trigger R uses natural price-risk distance: per-ounce
net liquidation divided by initial stop distance. Published PnL R separately
uses the allocated money budget, preserving lot rounding.

Trigger net liquidation reserves actual spread, .40USD/oz roundtrip slippage,
unrounded commission, funding and .02USD/oz rounding allowance (covers the
maximum two commission-cent rounding errors even at1oz). This conservative
trigger is quantity-independent and permits exact shared price paths across
sizing policies. Actual cash costs still use native cent rounding.

- E1: at20:30UTC on entry day, close unless current net liquidation>=1.5R.
  If carried, arm a cost-reserved breakeven stop covering commission,
  slippage and all declared remaining funding to the original deadline.
- E2: first observed net liquidation>=1.5R arms the same breakeven protection.
  Thereafter close on the first completed H1 candle against the prior20
  completed H1 closes (BUY close<SMA20, SELL close>SMA20). No hard TP,
  no additional structure/trailing parameter search.
- E3: at21:30UTC on entry day, carry only if current net liquidation covers
  all remaining negative funding to the original deadline; otherwise close.
  BUY/SELL use their declared cost-model rates. No additional BE or filter.

For E1/E2 a protective stop is never loosened. If the cost-covered stop is
already beyond the executable market, close immediately. Newly armed stops
act from the next quote, with market/stop slippage; gaps can still realize
a loss. “Never become a losing trade” is an aim, not an execution guarantee.
Holiday deadlines earlier than the daily decision take precedence. If a
daily decision lacks a quote within60seconds, retain a flagged unknown
rather than invent a fill. Use the same rule for both declared cost models;
cost-dependent carry/protection is recalculated per model, not selected.

Promotion: positive each Development year in both cost models; each year's
NetR/peak-equity-DD_R improves at least10% over Anchor0 AND netR excluding
that year's top3 improves at least1R. These numerical definitions settle
"improves clearly" before measurement. At most one exit, ranked by worst
year/model Return/DD gain, then smaller worstDD, then E1/E2/E3 order.
This ratio is called Return/DD, not mislabeled as annualized Calmar.
If none pass, retain Anchor0 unchanged. Never reselect using2024.

## Phase2: three candidates, one budget slot deliberately unused

Use admitted closed H1/H4 features with the existing November2021 seed,
H4 SMA20 slope/price bias, prior H1 ATR14, first qualifying signal per
candidate/day. No raw initial-stop filter or forced widening to reach
a desired numeric range.

- S1 Gold NY pullback continuation: decisions12:00–16:00UTC inclusive.
  H4 direction, previous H1 candle against that direction, current H1 closes
  beyond previous candle high/low in trend direction. Natural SL is the
  opposite extreme of the two candles plus .10 previous H1 ATR.
  Primary markout/exit20:30UTC same day, or earlier holiday deadline.
- S2 Gold H1 inside-range breakout: decisions08:00–16:00UTC.
  Previous H1 is fully inside its predecessor, current H1 closes beyond
  that predecessor's high/low in H4 direction. Stop opposite predecessor
  extreme plus .10 prior H1 ATR. Primary48calendarhours/holiday clamp.
- S3 EURUSD H1 Asian-range/H4 continuation: same causal A mechanism and
 08:00–15:00UTC decision window, applied to admitted EURUSD H1 candles.
  Stop opposite00:00–06:00UTC Asian range plus .10 prior H1 ATR.
  Primary24calendarhours/Friday/holiday clamp.

S1 raw signals simultaneous with A are counted; an entry collision is rejected
causally with A priority, not removed from the raw opportunity ledger. A can
enter after noon; do not assume its entire cohort is a European-only strategy.
S3 is the authorized "EURUSD or US500" choice because EURUSD has admitted
full Bid/Ask tick infrastructure. No US500 expansion/dividend assumptions or
fourth hypothesis are needed merely to exhaust the maximum budget.

Stage0 unconditional endpoint markout uses observed Bid/Ask, all stress costs
and funding; primary horizon only, no secondary-horizon rescue. Both years
require >=40 raw signals, valid natural geometry, median friction/medianSL
<=.12 and >=50% signals passing.12; net mean positive and >=mean execution
friction in each year/model. Missing endpoints, undefined scale/costs or
negative either year block promotion. EURUSD uses existing5USD/lot roundtrip
commission +4USD/lot stress slippage and a conservative declared−40USD/lot
per rollover, both sides; this is a stress scenario, not verified real swap.
Gold costs unchanged. EURUSD annual source partitions only; no reserved data.

Only Stage0 survivors receive natural-SL-active Stage1 with the same primary
time exit (no TP or exit tuning). Both years/model must remain net positive.
Measure Pearson correlation of aligned daily marked equity changes at Prague
midnight, including zero-trade weekdays, against chosen A; require<.35 in
both models. Undefined correlation fails, never becomes zero. Select at most
two sleeves by worst-year netR/DD, tie smaller DD then S1/S2/S3. The two
also need mutual correlation<.35; otherwise keep the higher-ranked one.
No independently profitable sleeve is assumed merely from a different name.

## Phase3: one frozen phase-aware policy, 36 starts

Same frozen entries/exits, no2024 selection. Start first of each month
Jan2022–Dec2024, flat, end01Jan2025 exclusive. Overlapping starts are
descriptive scenarios, not independent observations or probabilities.
Reuse Anchor0's .30/.40 baseline cases. Improved policy:

- Step1 .50% initial50k per position, Step2 .35%, funded .25%.
- If net realized daily balance change<-1.8% initialcapital, cap NEW entries
  at.25% until next Prague reset. If current marked equity<95.5% initialcapital,
  cap NEW entries at.25% until equity recovers above that floor.
- Existing positions/exits unchanged. Before entry reserve all open-position
  stop losses, projected negative funding, exit commissions and stress slip;
  reject a new position if full requested size would cross daily5% or static
 10% floors. Reject rather than widen SL or introduce a hidden size grid.
  This is a guard under the declared model; it does not bound gap risk.
- Entry priority A,S1,S2,S3. Same-asset same-decision collisions rejected,
  retained in admission statistics. Other overlap allowed subject to shared
  account reserve, not independent account budgets.
- Targets +10%/+5%, >=4 entry days per phase, pass only flat, breach before
  pass; reset50k and consume next later decision. No auto-retry or reused
  signal. Zero administrative transition delay is a simulation assumption.

Annual economics comparison uses fixed150USD/position for both baseline and
improved signals to separate strategy change from sizing. Report whole-account
concurrent exposure/DD, not a sum of standalone sleeves. The monthly lifecycle
then applies the frozen phase-aware policy. Under variable risk, trade NetR is
netPnL divided by that trade's original allocated risk; USD/% are authoritative.

Funded reward proxy: evaluate at first flat Prague reset or flat exit after
>=30calendar days since first funded trade/previous extraction. Only positive
closed profit is removable; never restore a loss to50k with invented cash.
Debit100% of profit from account; trader entitlement=.80×profit and firm
share=.20×profit. Then next cycle starts50k under a declared zero-delay new
account/reset convention. Never "withdraw80% yet reset100%" without accounting
for the other20%. A payout is a simulated eligible/approved-proxy amount,
not actual money received or verified FTMO acceptance. If current official
minimums require more than this, use the stricter metadata before running.
Official reward FAQ checked14November2026: requests from day14, flat account,
minimum closed profit20USD for bank/card transfers (50USD crypto), default
2-Step share80%. This campaign keeps the stricter30-day clock and20USD bank
minimum. Review/payment delays are excluded; eligible proxy is not receipt.
Report gross removed, trader amount, firm amount, count, dates and balance
bridge separately. Do not tune payout timing after seeing outcomes.

## Phase4 and final delivery

Timing/gap/cost, protected-stop, causal H1, size/rounding, collision, throttle,
shared risk, exact loss floors, phase resets, no inheritance, right censoring,
withdrawal accounting and negative-profit/no-injection fixtures. Run existing
research regression suites; no unrelated broker/product integration tests.
Separate arithmetic/tick-parity implementation and event cash reconciliation,
not a claim of independent human/agent review. Record all unknowns.

One consolidated before/after Markdown + JSON, negative results, exact
registrations/source bindings and attempt history. Coherent commits and one
new PR with3green required checks. Do not assume its number in advance.
No fee/strategy changes to force success, no purchased challenge or broker
activation, no new holdout. Finish even if every proposed improvement fails:
the requested36-window result can legitimately show zero completions/payouts.
