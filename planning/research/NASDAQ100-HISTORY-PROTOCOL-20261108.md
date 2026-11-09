# NASDAQ100 H1: history cho hai năm development, trước strategy PnL

Sau [pilot đã khớp](NASDAQ100-SOURCE-RESULTS-20261108.md), chuẩn bị input cho
hypothesis H4SMA20/80 trên indexCFD. Không là economic experiment, không thêm
policy implementation hoặc quyền broker. Chưa có target contract đủ verified.

## Frozen source requests

Existing Dukascopy `usatechidxusd`, Bid/Ask H1,4windows:

| Role | UTC interval, end exclusive | Months / side |
|---|---|---:|
| Warmup2019 | 01/11/2018→01/01/2019 | 2 |
| Development2019 | 01/01/2019→01/01/2020 | 12 |
| Warmup2022 | 01/11/2021→01/01/2022 | 2 |
| Development2022 | 01/01/2022→01/01/2023 | 12 |

Tổng8book requests/56month sources;4month-side sources từ pilot reuse bằng
raw hashes. Không dùng giá/returns để chọn window, không2025+. Historical
development/exposure explicit, không cleanOOS. Source-label CFD price/volume
units/known-at giống pilot, không giả observed joint-mid extrema từ sideOHLC.

Driver `prepare-nasdaq-history-v1.cjs`, reviewer `check-nasdaq-history-v1.py`
tại campaign root. Output mới `execution-v1/nasdaq-history-v1`,1writer,
deadline240s/CANCEL/PID/events/progress/failure, immutable newattempt.
Pin protocol/pilot review/result/current helpers/native package/code/lock.
Reuse cachedH1 helper, noWAF/auth, native retries0; bounded transient3attempts,
budget6, strict request failure. Không silent missing month hoặc tự đổi dates.
Giữ sealed books để recovery có chủ đích nếu cần; không auto rerun toànjob.

## Admission trước economics

Mỗi returned row phải thuộc explicit source timestamp trong requestedwindow,
UTC H1/grid0,001/OHLC/volume hợp lệ, chronologicalunique. Giữ explicitvolume0,
loại decoder padding theo raw source membership, không dựa vào flatprice.
Close/high/low known-at=barend, Open intervalproxy, không native tick fill.

Review decode toàn56raw JSON sources với canonical decoder và Fraction;
so OHLC/nativevolume-round4/counts/hash/instrument/side/time. Kiểm mọi paired
Open/Close crossed/one-side gaps, không clamp/flip hoặc đổino spread. Missing
hours gồm closures/unknownfeedgaps, chưa cause classification. Báo H4groups
đủ4sourceH1 theo UTC; đây là coverage, không tín hiệu hoặc profitability.

Admission cho **registered coarse economics** chỉ khi8books/56sources đủ,
raw transformations khớp, source-grid/clock đúng, mỗi developmentyear/warmup
có dữ liệu và không crossed Open/Close trong pairedhours. Không yêu cầu24/7
coverage; missing-role/gap policy phải đăng ký trong strategy protocol.
Không claim H1bar pass thay toàn bộ actual ticks/historyjointfeed/targetbroker.

Nếu missing month/transform/crossed thì giữ failure/gaps và inconclusive;
không thay logic PnL hoặc mở simulation để bỏ qua. Mutations giá/hash/count/
clock/authority phải reject. Review cùng agent/different arithmetic, không
independent human/model audit. Lưu timings/status/nextaction; Goal C1/C2 active.

Sau nhận nguồn mới chốt recipe/cost/risk: H4 Bidchart có thể reuse indicator
core, nhưng không gọi mean(BidHigh,AskHigh) là observedmid high. Không truyền
NASDAQ dưới nhãn US500/XAUUSD để vượt guard, hoặc gắn funding/lot/commission
cũ sang asset mới. Exact ticks/prop/selection-aware OOS/forward/handover vẫn
phải có ở stage phù hợp trước đề xuất challenge.
