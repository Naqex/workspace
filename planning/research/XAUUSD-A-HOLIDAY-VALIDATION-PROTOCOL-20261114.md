# A BOTH/no hard TP — calendar repair, Historical Validation 2024, rolling accounts

Owner authorizes PR77 merge and this follow-up. PR77 merged `3406ed1`.
Only A BOTH, same closed H1/H4 features, seed01Nov2021, Asian range, natural
SL and first-A-per-day as PR76. No C/TP2R/SELL-only/filter search. Keep original
210 Development signals exactly; 2024 is Historical Validation with prior
source/M15 exposure, not pristine OOS. **No2024 price decoding before this
protocol and calendar JSON are frozen. No2025–2026 prices at any stage.**

## Calendar policy fixed before Validation prices/outcomes

All clocks UTC unless stated. Normal Friday hard-flat20:30; ordinary daily
rollover breaks are not holiday exits. Explicit calendar covers2022–2024,
plus NewYear2025 **date metadata only** to flat31Dec2024 before closed prices.
US metal early-session days: MLK, Presidents, Memorial, Juneteenth observed,
Independence, Labor, Thanksgiving and its Friday, weekday Christmas/NewYear
Eve. **Hard-flat17:00UTC**, or earlier if a verified target closure less30min
requires it. This is a conservative, common-venue liquidity guard, not a claim
that FTMO always closes17:30. It predates new Validation price inspection and
does not select the last observed quote or use PnL to choose buffers.
GoodFriday: prior Thursday20:30 hard-flat, Friday closed. Christmas/observed
Christmas and NewYear/observedNewYear closed; weekend preceding those is
already flat. Reopening/closed-day entry admission is logged separately; never
silently delete raw signals or invent a quote on a closed target day.

Exit deadline=min(entry+48calendarhours, earliest future Friday/holiday flat).
First executable quote at/after deadline, wait<=60s, must precede scheduled
closure. No last-quote hindsight, next-day fill or terminal forced close. A
natural SL may exit earlier, BUY usesBid/SELL Ask. All exits stress.20USD/oz,
entry.20, no hard TP. Calendar/source/spec gaps remain unknown, not firm pass.

Primary dated FTMO sources include:
- [23Nov2023](https://ftmo.com/en/blog/trading-updates/trading-update-23-nov-2023/):24Nov metals20:45GMT+2=18:45UTC.
- [30Mar2023](https://ftmo.com/en/blog/trading-updates/trading-update-30-mar-2023/):GoodFriday closed.
- [11Jan2024](https://ftmo.com/vi/blog/trading-updates/trading-update-11-january-2024-2-2/):MLK15Jan21:30GMT+2.
- [23May2024](https://ftmo.com/en/blog/trading-updates/trading-update-23-may-2024/):Memorial27May21:30GMT+3.
- [13Jun2024](https://ftmo.com/en/blog/trading-updates/trading-update-13-jun-2024/):Juneteenth19Jun21:30GMT+3.
- [4Jul2024](https://ftmo.com/fr/blog/trading-updates/trading-update-4-juillet-2024/):Independence4Jul21:30GMT+3.
- [29Aug2024](https://ftmo.com/en/blog/trading-updates/trading-update-29-aug-2024/):Labor2Sep20:30GMT+3=17:30UTC.
- [28Nov2024](https://ftmo.com/en/blog/trading-updates/trading-update-28-nov-2024/):Thanksgiving/Friday21:30/21:45GMT+2.
US holiday dates cross-check[OPM](https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/).
Date-known and conservative policy does not establish exhaustive historical
FTMO sessions for every date; missing primary target times labelled unknown.

## Costs, quantities and account model

Same paired models as PR77: Symmetric BUY−40/SELL−40 and asymmetric proxy
BUY−45/SELL−5 USD/lot per rollover unit. Commission.000007 notional/side,
cent-rounded; 100oz/lot,.01min/step (research specification; current/historical
target snapshot not independently retrieved). Quote spread retained. Rollover
22UTC weekdays/Wed3 remains a proxy, not verified historical FTMO swap clock.
Actual swap range/history is unavailable; do not describe scenario endpoints
as observed broker rates. No speculative swap sweep or lowered stress.

R0=$150 (.30% of50k) or$200 (.40%), fixed per account phase, no compounding.
Wholeoz floor(R0/naturalSL), same quantity in paired costs; nominal price risk
excludes fees/gaps/swap. MT5 position-accrual model: entry commission realized,
entry slip and open swap floating until exit. Prague00:00 balance anchor,
equity includes all floating costs. Native Trader prop money/lifecycle rules
reused; no policy/rule modifications to Trader, margin/news/targetfeed unverified.

Annual2022/23/24: independent50k starts, report BUY/SELL, netR in both fees,
meanR, synchronized equity peak-DD/staticloss/dailyloss. A raw210 must match
parent signals byte-for-field before funding/PnL; calendar only changes exits.
Top3/year (entry/exit/side/SL/NetR) and disjoint netR bins: `<−1`, exact`−1`,
`(−1,0)`, `[0,1)`, `[1,3]`, `>3`; exact equality uses cents/R0, zero explicitly
in `[0,1)`. Concentration diagnostic, no rules changed after reading2024.

## Continuous monthly/quartile starts — not independent trials

36 unique starts: first day of each monthJan2022–Dec2024, start flat/no inherited
positions, consume first later frozen decision. Quarterly starts are the12
Jan/Apr/Jul/Oct **subset**, not12 more independent starts. Two fixed risks ×
two costs =144 scenarios. Each ends at01Jan2025 exclusive; right censoring
retained. Earlier starts have longer follow-up; pass fractions are descriptive,
not an estimated live success probability.

Current2-Step rule scenario: phase1+10%, phase2+5%, realized balance target,
flat, >=4 distinct entry days Europe/Prague per phase, daily loss5% equity from
midnight balance and static overall loss10% below phase initial50k. Strict
below-floor breach, threshold equality allowed; breach before pass. Pass only
on a flat event, then reset50k, advance next phase at the next signal; no same
signal reuse. Zero administrative delay is an explicit assumption. No auto
retry after breach, no profit carry across phases, no risk brakes/compounding.
After phase2 pass: new50k funded risk-monitor until cutoff, same daily/static
rules, no profit target/minimum days. Report survival/breach/net funded PnL;
**no withdrawals, reward requests, fees or payout timing** are invented.
This is conditional two-loss-rule lifecycle performance, not full FTMO
qualification (news/admission/margin/targetexecution still unknown).

Ordered tick segments losslessly retain extrema/DD/prefix lows between each
entry/exit/reset/funding action, allowing exact first-loss witnesses and shared
reuse for rolling starts. Never sum trade MAEs or multiply.30 results into.40;
lot rounding and start-flat admissions are recomputed. Bind protocol/calendar/
code/source hashes before financial outcomes; fixtures for holidays, cutoff,
reset accrual, overlap, threshold order, min days, phase resets/censoring and
no inherited positions; separate arithmetic/tick audit, no ASTRA/subagents.
Reuse cached sources, only fetch required missing hours. Keep failed attempts.
