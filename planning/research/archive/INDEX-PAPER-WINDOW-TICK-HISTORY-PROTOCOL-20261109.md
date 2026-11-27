# Tick history cho paper-window recipe: đăng ký nguồn, chưa PnL

Sau [boundary pilot](INDEX-CASH-CLOSE-BOUNDARY-RESULTS-20261109.md), nguồn hỗ
trợ quote quanh close trên các ngày đã khóa. Cần kiểm coverage toàn development
trước đăng ký economic outcomes mới; 8 ngày/asset không thay full history.
Hai price components cũ R076/R077 giữ negative, không rerun hoặc repin.

## Universe/census biết trước outcome mới

US500 `usa500idxusd` và NASDAQ `usatechidxusd`, 2019 và 2022 đã consumed.
Lấy **mọi regular cashday** theo sealed R076/R077 row/calendar census, không
lọc theo old returns, side, predictor availability hay có lời. Mỗi asset:
249 ngày 2019 + 250 ngày 2022 = 499 ngày; tổng 998 asset-days × 2 giờ =
**1.996 instrument-hours**. Halfdays giữ ở inherited census, không fetch như
regular days; previous-close/first-half predictors kế thừa source M1 có pin.

Mỗi ngày thu 15:00–16:00 và 16:00–17:00 New York, đổi UTC theo calendar/DST.
15:29 source-minute BidClose phục vụ kiểm late predictor; entry từ decision
15:30, exit scheduled16:00. Chưa signal/PnL trong job source. Nguồn chỉ tới2022,
không own2025+, tài khoản/provider/OAuth/paid service/broker/runtime change.

Reuse 16 sealed pilot hours và cache đúng instrument-hour URL, raw hash, decode
và scope. Không bắt fetch lại cache. Source-only view mới không sửa canonical
M1, old proofs hoặc raw. Native joint Bid/Ask/volume tick JSON, grid0,001,
millions volume, timestamp/ordinal theo stream; không sort/dedup/pad.

## Long intake, checkpoint và thời gian

- Same pinned native package1.51.1/recovery helper, batch1/request interval300ms,
  retry0/WAFoff/token cacheoff. Bounded existing transient recovery cap6,
  max2retries/request; 403/429/auth/schema không retry/fallback.
- Source job mới `execution-v1/index-paperwindow-tick-source-v1/`, one writer
  lock/PID, deadline1500s mỗi invocation, CANCEL/progress/events/failure/seals.
  1.996 requests không đồng nghĩa 1.996 new network calls; giữ actual cachehits.
  ETA chưa đo; đọc tiến độ từ completed/total và elapsed, không hứa full source
  mất cùng thời gian với pilot. Không model/broker calls.
- Full pins trước dùng/final, active code/protocol/package/config checks giữa
  loop, raw/output/proof seals mỗi hour. Canonical M1 không đọc giữa loop.
  Từng source/hour output giữ riêng, JSON config/manifest có version/code/runtime.
- Resume chỉ đúng job/config/code/input pins: kiểm mọi prefix seal/raw/output/
  proof/identity/census trước skip. Prefix gap, duplicate, tamper hoặc source
  revision phải fail, không bỏ file lỗi và tiếp. Live lock không được giành;
  stale lock chỉ sau xác minh PID không còn, lưu owner history. Failure/events
  giữ, không rewrite history hoặc result completed để giả hoàn tất.
- Cache-only preflight trên16pilot hours cùng code path, không network: output
  hash exact cũ, kiểm actual second invocation reuse và forged-seal mutations
  trước long intake. Không gọi native cache hit là admission khi chưa review.

## Review/admission trước economics

Consumer full-hash inputs trước dùng và final; integer inspector kiểm mọi native
tick fields trên raw delta/order/grid/volumes. Helper đã khớp frozen Fraction
trên115.502pilot ticks và thêm14.847boundary ticks; giữ Fraction oracle/pins.
Kiểm Fraction đầy đủ cho16pilot hours, thêm một giờ mỗiasset/year có nhiều ticks
nhất (chọn bằng source count, không returns) và mọi source-conflict hour, trước
conclude admission. Ghi rõ phần nào integer/full Fraction; không claim toàn
history độc lập Fraction nếu chưa chạy.

So common M1 side OHLC và late15:29 close; ghi missing/gap/crossed/common
conflicts theo role. Ticks có mà source M1 vắng là coverage extension có ghi
nhãn, không tự repair missing predictor. M1 có mà không tick giữ unavailable;
common price conflict chặn affected source use, không nới tolerance hoặc chọn
side/clock vì outcome. Phút cùng vắng không thành carried quote hay outage
đã xác minh. Different same-provider endpoints không independent feed.

Tìm first archived quote ở entry15:30 và exit16:00 +200ms/1s/2s/60s; target
và first/wait/ordinal/Bid/Ask giữ exact. Pilot là source timestamps, chưa broker
arrival/fill/SL/account path. Không compute candidate net returns trong intake.

Sau terminal/review mới chốt economic recipe/version riêng: primary1s,
stress2s và60sproxy, max wait60s sau target, missing/unresolved vẫn trong census,
same declared spread/slip0,25/0,75 mỗiside/commission0, five matched controls.
Không chọn delay/filter/fee từ outcome; 200ms chỉ diagnostic. Giữ source và
selection history, chưa cleanOOS hoặc challenge permission. Cần gate riêng cho
target costs/risk/prop equity/time-fit/forward/owner handover trước C1/C2.
