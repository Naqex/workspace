# rROD paper-window v2: khóa economics trước kết quả mới

Đăng ký sau [source pilots](INDEX-CASH-CLOSE-BOUNDARY-RESULTS-20261109.md), trong
lúc [full source intake/review](INDEX-PAPER-WINDOW-TICK-HISTORY-PROTOCOL-20261109.md)
đang chạy, chưa PnL mới. Chỉ chạy economics khi full source đã terminal/reviewed,
không common price conflicts chưa giải quyết và đúng code/input/receipt pins.

Hai exact revisions: `us500-restofday-cashclose-tick-component-v2` (parent R076),
`nasdaq-restofday-cashclose-tick-component-v2` (parent R077). Price components,
không account policies. Parent 15:31→15:59 negative vẫn giữ; đây là thay window/
execution model có selection history, không sửa bug để biến old result thành pass.
Published futures method là nguồn giả thuyết, CFD adaptation chưa replication.

## Nguồn và tín hiệu khóa

Same consumed development years2019/2022 và calendars: 503 cashdays/asset gồm
499regular/4halfdays. Fullsource1.996hours bao gồm cả invalid-predictor days,
không chọn source theo returns. Không own2025+ hoặc gọi đây là cleanOOS.

Previous close / first-half09:59 / late15:29 BidClose, common-mask và previous
**expected** cashsession kế thừa frozen R076/R077 source/specs. Mỗi regular day
cần đủ cả3predictors (paired sides/clock/grid/noncrossed đã review); late15:29
phải được new raw ticks xác nhận exact BidClose và có quote trước decision.
Missing/crossed/mismatched late predictor ghi unavailable, không tick-repair
missing canonical predictor, lấy last available day hoặc dùng future quality.

Nếu late>previous BUY, late<previous SELL, bằng nhau no primary exposure.
Decision15:30 NewYork, scheduled exit decision16:00. Không ATR/SL/TP/news/
gamma/volume/filter/threshold thêm. Warmup/prior data chỉ features, không PnL.

## Causal quote và chi phí

3 scenarios dùng cùng tín hiệu và cohort: **primary delay1s**, delay2s stress,
delay60s proxy. Delay áp cảentry/exit; first joint quote có timestamp≥decision+
delay và wait≤60s sau target. Không chọn quote tốt nhất trong interval hoặc
carryforward; equal timestamp giữ source ordinal. 200ms chỉ source diagnostic.
Quote tại target không chứng minh arrival/fill thật. Cả 3 phải giữ riêng,
không chọn winner delay hoặc thay primary sau PnL.

Entry thiếu/expired ghi unresolved entry, không fake fills; exit thiếu/expired
giữ unresolved endpoint, không PnL0/forceclose/skip khỏi denominator. Source
views/statistics ở exit không được dùng để xóa entry trước đó. Parent planned
count có thể giảm vì tick-confirmation late predictor biết trước entry; giữ
reason/census. Exact quote wait/ordinal/source hashes và every unknown được lưu.

Một hypothetical unit=1USD/index point; BUY Ask→Bid, SELL Bid→Ask. Same declared
costs: reference slip0,25point/mỗi side, stress0,75point/mỗi side; observed BidAsk
spread nằm trong quote, commission0/funding0 theo same-day scenario. Reuse
existing market/cost primitives/cents rounding và no-exposure semantics;
chưa historical target-broker costs/fills/lot/margin/account10k/risk0,25%.

**5 roles tổng cộng**: primary, opposite-rROD control, alwayslong, alwaysshort,
first-half sign control. Nghĩa là 4controls, làm rõ chữ “five matched controls”
trong intake protocol; không thêm control thứ5 hoặc auto-promote control nếu
primary fail. Firsthalf bằng0: costs=None, no_exposure=True/net0, không fake
fill. Mỗi role/cost cùng resolved primary mask, không so old ATR/account PnL.

## Triage và review

Mỗi asset retain chỉ khi **mỗi năm ở cả3delay scenarios**: ≥100planned signals,
≥98%regular days valid predictor, ≥98%planned days resolved endpoints, stress
primary known sum>0 và > alwayslong/alwaysshort/firsthalf trên cùng mask. Đây
là frozen workload triage, có false negatives, không statistical chứng nhận.
Unknowns giữ trong census; known sum không full annual net khi còn unknown.
Không cộng USD/unit giữa2assets thành portfolio return.

Fail→gác exactv2, không fee/clock/expiry/SL/side/filter grid cứu. Retain chỉ
đủ ưu tiên đăng ký riskwrapper/selection-awareOOS/prop-equity/timefit/prospective/
ownerhandover, không C1/C2 hoặc challenge permission. Báo net/controls/paired
deltas/trade count/concentration/cost sensitivity và remaining gaps.

Trước numeric: fixtures tính tay/Fraction trên cả2markets/2costs/3delays/side,
causality/expiry boundary/census/flat control/unknown/future mutation/identity/
false authority/rounding. Source bindings và invariant checks trước net.
Separate Fraction reviewer toàn features/quote selection/roles/costs/census/
summary/gate, actual mutations; cùng agent nhưng arithmetic khác, không human
hoặc model độc lập. Không sửa old helper consumers hoặc source đang được pin.

Output mới `execution-v1/index-paperwindow-components-v2/`, one writer,
PID/events/progress/CANCEL/deadline180s producer/reviewer riêng, raw samples
và phase timings; no-overwrite result. Nếu source chưa đạt thì không PnL và
lưu admission gap. Không network/broker/model calls trong economic run.
