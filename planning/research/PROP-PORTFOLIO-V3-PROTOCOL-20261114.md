# V3 — D1 scaling, satellite contribution and causal funding reserve

Owner task `ded836a8-3f42-4204-9742-9fc0ad3c369e`, 14/11/2026.
PR #80 merged `91dd2d5`; preserve VI Dubber. No 2025–2026 prices,
broker/model/paid calls or Astra dispatch. One branch and one new PR, not merged.
Commit this registration before new financial outcomes.

## Existing evidence and data roles

V2's 84 complete-endpoint configurations failed Stage-0 before the +6R/year
SL-active gate; 28 others have incomplete endpoints. Complete endpoints do
not certify full SL paths. SELL 2022 on the corrected holiday baseline is
+6.934R, not the earlier +11.19R. Keep V2 outcomes unchanged.

V3 is a new, owner-authorized re-examination of these same 112 recipes with
SL-active and portfolio marginal criteria. It supersedes the old raw-mean
and standalone +6R performance gate for this experiment only, not historical
verdicts. No new signal formulas, entry windows, assets or horizons.
Retain registered costs, natural stops, causal entry friction <=15%, median
friction/median natural stop <=15%, and >=60% raw signals passing that screen
in each Dev year. Never widen stops or drop missing observations as losers.
Cadence is reported for satellite suitability, not a new 40/year hard gate.

Development/selection: 2022–2023 only, with past-only warmup. Existing 2024
is exposed Historical Validation; no 2024 outcomes/prices in Phases 1–2.
Freeze and **commit** exact composition, weights, costs, calendars, source
versions and risk policy before releasing Phase 3. No reselection afterward.

## Phase 0 — causal reserve repair

Shared stop reserve projects negative funding from entry through the
pre-locked `deadline_msc`, never realized `exit_msc`. Deadline is the
registered calendar/Friday/holiday maximum holding time, known at entry.
Missing/invalid deadline fails closed. Initial SL, position size, commission
and stress market-exit allowance remain known pretrade. Positive funding
does not enlarge a reserve. Test future-exit perturbations and Wednesday x3.
This fixes that helper; it does not certify broker readiness/news/margin.

## Phase 1 — exactly one D1 weighting trial

Use completed UTC D1 bars: at least 20 complete H1 bars (or 1,200 observed
M1 records) in a source day; do not treat partial days as completed full days.
Warmup begins 2021-01-01 from the existing admitted Gold cache, bounded reads.
SMA50 on completed qualifying daily closes; slope is SMA50 minus its value
five qualifying daily bars earlier. Last D1 must have ended before decision,
no more than four calendar days old. Unknown regime is recorded, not inferred
from future prices; insufficient history blocks qualification.

Bull: prior D1 close > SMA50 and positive slope. Bear: below and negative
slope. Otherwise neutral. Counter-regime A signals receive **0.5x** nominal
risk; aligned/neutral signals receive 1.0x. No outright direction switch-off.
Entry, SL and exit unchanged. Exactly A_Original versus A_RegimeScaled.

At fixed $150 reference risk, report net/reference-R and equity-DD/reference-R;
do not erase the weight by dividing every PnL by its smaller allocated risk.
Select scaled only if combined 2022–2023 NetR/peak-equity-DD strictly improves
under both SYM and ASYM, with >=95% original filled entries retained and
complete regime/source paths. Report both years and concentration separately.
No SMA/threshold alternatives after outcomes.

## Phase 2 — existing 112 cells, one natural-SL realization each

Use frozen V2 raw signals and actual Bid/Ask entry roles. Natural SL, no TP,
original DAY/24h/48h deadline, same calendar guard/costs. Friction rejects
occur at entry, based on known quotes/fees, never future exit quotes.
Rank all priceable configurations; preserve unavailable and rejected ones.

Sources: admitted Gold tick/M1 cache, EURUSD paired tick/M1, explicit US500
paired M1, and admitted GBPUSD/AUDUSD H1 summaries/existing native endpoint
ticks. H1-only path results may be reported as conditional screens with
unknown intrahour timing; they cannot qualify as execution-ready satellite
or substitute for M1/tick portfolio equity.

For the 28 incomplete cells, inspect missing-role timestamps. Recover only
deterministic weekend/holiday/early-close mistakes from an admitted calendar
and existing quotes. No backfill, future-first-quote fill or new arbitrary
exit hour. Unknown entry quotes/source gaps remain unknown. Any newly needed
source work is bounded to registered 2022–2023 roles and recorded before PnL.
US500 overnight dividend/carry target unknown continues to block selection.

SL-active M1 screen uses same-side extrema, adverse gap-open execution,
market-exit slippage, no ambiguous TP/SL ordering. Missing held minutes
outside admitted market breaks are unknown. No assumed perfect SL fill
through a gap. Mixed-asset equity requires synchronized marks; summing
independent high/low extrema is a conservative envelope, not an exact path.

Top 10 ranked by minimum combined net R across SYM/ASYM, then smaller combined
equity DD, then lexical ID. Report raw/filled counts per year, friction
retention, net R/year/combined, DD and daily PnL correlation with A_Original.
Daily correlation uses aligned Prague weekdays including zero-PnL days;
undefined is unknown, not zero. Report per-year and pooled correlations.

Satellite gate, both cost models: combined net R >=8; either both years >=0
or weak year >=-1 and strong year >=10; pooled daily correlation <0.25;
full admitted M1/tick path; retained cost-scale/source gates above.
At fixed reference budgets core $150, satellite $75 (0.5x), require combined
Dev net/equity-DD to improve versus the selected core under both cost models.
Choose at most two greedily by worst-model improvement ratio, then lower
worst DD, then lexical ID. The second must improve the already selected
portfolio. Do not grid weights or optimize correlation after outcomes.
Standalone preselection PnL addition is not shared-account proof.

## Phase 3 — exactly one balanced policy, 36 starts/model/system

Core phase risk: $200/$175/$125 on $50k; satellites $100/$100/$75.
Apply any selected 0.5x D1 factor to core new-entry risk only.
Current equity shortfall versus phase initial capital >=4% caps new risk at
$150; >=6% caps it at $90. Caps never raise satellite/funded base risk.
Recovery follows current equity, not the historical maximum drawdown.
Daily realized loss <=-2% initial latches a new-entry halt until Prague reset.
Existing positions keep their quantities and protective exits.

Max total initial-stop exposure: **1.00% ($500)**, all open positions and
the prospective order. Reject whole order, no artificial resize.
Retain internal projected-stop floor 7% ($46,500), now causal, plus firm
5% daily/10% static model floors. Record rejects and idle periods. These
are research budgets, not a no-breach guarantee. Priority core then ranked
satellites; same asset/decision collision fails closed. Hedging-capable
account is an explicit assumption, not a verified broker mode.

Compare pinned PR #79 / PR #80, balanced selected core alone, and balanced
core+selected satellites. If zero satellites qualify, column four equals
column three and reuses its replay; do not call that a multi-strategy result.
36 monthly starts Jan 2022–Dec 2024, end before Jan 2025; continuous Jan 2022
is the first monthly case, not independent. Preserve positions, funding and
cash across years. Keep +10/+5 targets, four entry days, flat phase pass,
breach-before-pass, fresh $50k phase capital and zero admin-delay assumption.
Keep prior reward proxy, no retries/cash injection; distinguish modeled
eligibility from actual payout and include dataset-end censoring.

## Phase 4

Focused causal/source/accounting fixtures and alternate numerical checks.
Same-implementer alternate arithmetic is not independent human/model review.
Keep all trials, missing paths and deviations. Full Markdown+JSON report,
context/index update, coherent commits, one PR with three green checks on
exact HEAD; never infer an assigned PR number or merge the new PR.

## Source-clock clarification before Phase 2 PnL

The timestamp-only US500 census shows its daily source break starts at
16:15 New York (20:15 UTC in summer, 21:15 in winter), ending at 18:00 NY.
The inherited Friday/DAY 20:30 UTC can fall inside that break. If a registered
exit falls in this deterministic interval, close at **16:00 NY** instead;
otherwise retain the original deadline. This changes neither entries nor
holding-horizon choices and is a new source-calendar scenario, not a claim
that FTMO has these exact hours. Keep raw missing-endpoint results unchanged.
No clock chosen from PnL. US500 overnight dividend uncertainty remains blocked.

M1 observed-feed screens record every interval with no quote. Normal declared
NY maintenance breaks use the last known mark, with no invented bars or fills.
Other gaps >15 minutes are path-incomplete; shorter no-quote intervals remain
explicit stale-source intervals, with adverse reopening fills and M1-envelope
equity bounds. Thus "priceable" means this declared M1 source model, never
unconditional exact tick equity or verified FTMO execution. Gold bid-only
M1 cannot certify SELL ask triggers; require admitted paired ticks there.
H1-only GBPUSD/AUDUSD remain conditional and ineligible without M1/tick paths.
Reference lot grids in this screen: Gold one ounce, FX 1,000 base units
(0.01 lot), US500 one index contract under the legacy multiplier-one model.
US500 target lot/margin specifications remain unverified. Report priceable
source-model outcomes separately from broker/prop qualification.
