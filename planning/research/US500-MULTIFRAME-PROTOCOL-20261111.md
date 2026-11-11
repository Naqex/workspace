# Đăng ký US500 pullback A/B/C — 11/11/2026

Owner yêu cầu backtest sau khi chốt [A/B/C](US500-MULTITIMEFRAME-DRAFT-20261111.md),
7 mức đệm và sáu cấu hình MA sensitivity. Đây là development screen liên quan
R004/R094, không 27 edge độc lập. Không mua challenge, broker, fetch, AI inference
hoặc đọc 2025+. Freeze protocol/code/tests bằng Git trước financial outcomes.

## Census và câu hỏi

- R096–R116: A/B/C, trong mỗi lane k=0/.05/.10/.15/.20/.25/.30,
  MA20/80. R117–R119: A/B/C MA10/40 k=.10. R120–R122: A/B/C MA40/160 k=.10.
- A=M15; B=A+H1 bias; C=B+M5 confirmation. BUY/SELL đối xứng trong mỗi book.
- 27 cấu hình × 2022/2023/2024 × reference/stress = **162 financial books**.
  Thêm 9 null books: A/B/C MA20/80 k=.10 × 3 năm, vô hiệu entry; expected 0orders,
  0PnL. Không tính null/cost/year là strategy mới. Giữ mọi negative/reject/gap.
- Câu hỏi: có cấu hình nào đáng nghiên cứu tiếp sau costs, qua ba development
  years, có hỗ trợ từ các đệm lân cận, đủ giao dịch và ít unresolved không?
  Không ép winner. Không chọn MA/k theo lợi nhuận rồi gọi là clean OOS.

## Dữ liệu và causality

Reuse đúng full four-quarter explicit paired M1 US500 Dukascopy proofs:
2022 `7a41f021c86a04345ce2591b90efa72112792ef5479c16ff6d1167f7064dc840`,
2023 `61d46d061a870e98a97b696b95d8efab2d28abe190d94f2fc04c1b2255b1909c`,
2024 `ccda74a3510986a748d11c1a9b19e2d9b62da1ce61397ed8cb5cf0af218d1c1b`.
Accepted frozen calendars must retain exact source hash and semantic equality
with current calendar. Load every scheduled cash minute, not old opening subset.
Bid OHLC for indicators, separate paired sides for execution. Preserve explicit
volume0. Calendar America/New_York DST, normal 09:30–16:00; early-close indicator
history retained, no trading. Year cold starts; no previous-year implicit data.

Closed M15 aggregate all 15 expected source minutes. Missing => day blocked
causally and M15 readiness reset, no retrospective removal of earlier trades.
H1 blocks anchored 09:30; only complete 60minute blocks, no 15:30–16:00 H1.
Missing H1 resets its 20bar readiness. At arm only last closed H1 from same or
immediately previous scheduled session; no carry across missing expected hour.
M5 complete5minutes only. No synthetic bars or invented source ticks.

**Common eligibility delta:** all 27 lanes require **161 consecutive M15 bars**
and H1SMA20 ready. This includes previous slow160 and avoids warmup differences
confounding MA20/80 vs10/40 vs40/160. This is a new comparator, not v1 rerun.
Native SMA/ATR updated in preparation; exact Decimal SMA and Decimal28 ATR
recurrence checked against native values within1e-7 price points. Native ATR14
explicit WILDER, previous cash close/firstTR seed. Compare confirmation using
Fraction of frozen Decimal28 ATR and grid closes, with strict inequality; no
threshold price rounding. Finite ATR recurrence is numerical approximation,
not a claim mathematically infinite exact rational recurrence or MT5 ATR parity.

## Rules fixed before outcome

Arm M15 closes10:00/10:15/10:30/10:45, previous/current same session and trend
fast>slow BUY / fast<slow SELL both bars. Previous close strictly trend-side of
fastMA, current close at/through fastMA against trend. Freeze armHigh BUY /
armLow SELL, ATR14 and closed H1 snapshot. One attempt/day, including H1reject,
cancel/riskreject. No reverse, add-on, martingale or rearm. B/C H1 close versus
SMA20 must match side. A ignores H1direction but shares eligibility.

Later closed M15 (A/B) or M5(C) confirms strictly beyond L±kATR. Not arm event.
M15 trend cancellation/equality precedes simultaneous M5 confirmation.
Final confirmation allowed at min(arm+60min,11:00NY), then expires. No 4M5bar
shortcut. Freeze H1 through setup; no future H1 retroactive cancellation.

Decision→exact next M1open **+60sec**. BUY ask+.25/.75, SELL bid−.25/.75.
Missing exact entry or causal minute immediately before it cancels entry;
no convenient late fill. Native Cfd INDEX USD multiplier1, tick.001, min/step.01,
max50lot, declared leverage10, starting10000USD, planned risk≤25USD including
entry/exit adverse slippage; quantity floor to.01, stop2×armATR from **modeled
entry fill**, outward tick rounding. Declared research contract, not verified
FTMO historical spec. No TP/trailing/breakeven. Rawquote-anchor incumbent book
is **not numerically equivalent**; retain old outputs, do not claim parity.

Native stop market remains active until canceled for scheduled exit. BUY stop
trigger Bid, SELL Ask. At adverse opening gap native trigger uses rawopen±slip;
otherwise intraminute lowBid/highAsk barrier envelope triggers native stop and
custom native FillModel supplies stop±slip. One stop/noTP => touch decidable
from M1extreme without choosing low/high ordering for competing barriers.
Envelope quote timestamp at minuteend−2ns is an explicit simulation sequence,
**not an observed synchronous bid/ask spread, exact crossing or execution**.
Open timestamp+1ns; close exactly minuteend. No entry/market action at envelope.
Native framework owns event dispatch, orders, matching, positions and account;
policy/adapter supplies rules/declared model, independent reviewer replays fills.

Exit decision when closed M15 direction lost, or12:00NY, at exact+60sec open;
protective stop wins if hit first, including exitopen. Missing exit/held path or
unclosed position => fullnet N/A; retain modeled/knownclosed separately. No
force liquidation. Heldgap before native stopfill also unresolved. Cross-day
recovery from missingpath stays unresolved; native recovery cash excludes
unverified financing/dividend. This run does not price carry as known PnL.

Costs: commission0 declared scenario, embedded observed endpoint Bid/Ask,
adverse slippage .25 vs.75 point **each fill**, actual native fillprices include
slip. No separate duplicate slippage charge. Money realized per trade rounded
to USD cents half-even in the independent Decimal ledger; native Money has
binary-float half-cent boundary differences. Each native closed-position PnL
must agree within one cent, and native cash must equal sum of its realized
positions within one cent; preserve total native-minus-Decimal rounding delta.
Exact unrounded net also retained and cash reconciled.
Independent reviewer validates quantity/stop/cash and first protective crossing.

## Outputs, gates, recovery

Each book: source/protocol/runtime/code hashes, fills/trades/attempt events,
BUY/SELL/combined net, known subset/unresolved, tradecounts/wins/reasons,
slippage, commission, endpoint equityDD and timers. Full intraminute equityDD
unknown, not endpointDD presented as fullrisk. Winrate from resolved subset
is descriptive, not evidence of edge by itself. No FTMO news/closure compliance,
cleanOOS, pass probability, target fills or qualification claim.

Before financial data run: synthetic tests for causal clocks, HTF readiness,
both directions/equality, strict expiry, stop/gap/fills/accounting, missingpath,
null plus material review mutations. No material defects may be ignored to finish.
Short development run is correctness pilot, not tuning/selection. If a material
bug changes outputs, preserve attempt and freeze amendment before retry.

One writer, O_EXCL lock, atomic per-book artifacts/seals, progress JSON/Markdown,
events.jsonl; cancellation marker checked every25sessions and book boundary;
default1800second monotonic deadline. Completed sealed books can be reused
only with identical manifest/code/protocol/input bindings, and reviewed again.
No claim intra-book state resume. Failed unsealed book may rerun, previous sealed
books stay; old failure receipts remain. No automatic restart or source edits
while a pinned job runs. Source pin drift/census failure blocks completion.

Review only after all preregistered books, keep the complete table and every
failed/incomplete attempt. A promising row is eligible for further review at
most, not challenge approval. Postrun engineering review measures phases and
fixes evidence-backed faults, without mandatory retuning or batch reruns.
