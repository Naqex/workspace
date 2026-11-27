# Phân biệt thiếu quote cuối tháng với giờ giao dịch CFD

Đăng ký trước response mới. Input-clock audit tìm bốn month endpoints thiếu:
2013-09, 2014-12, 2015-12, 2016-10. Không chọn theo PnL. Mục tiêu là xem raw
ticks có quote đúng mốc NYSE reference hay không, chưa sửa dữ liệu/backtest.

Provider/package cũ `dukascopy-node@1.51.1`, public tick capability đã dùng cho
range oracle; không provider/account/auth mới. Bốn requests `usa500idxusd`:

| Ngày | Khoảng UTC, end exclusive | NY reference |
|---|---|---|
| 2013-09-30 | 19:58–20:00 | 15:58–16:00 EDT |
| 2014-12-31 | 20:58–21:00 | 15:58–16:00 EST |
| 2015-12-31 | 20:58–21:00 | 15:58–16:00 EST |
| 2016-10-31 | 19:58–20:00 | 15:58–16:00 EDT |

Chỉ metadata/quotes đã consumed giai đoạn 2013–2024, không 2025+. Retry0,
batch1/pause300ms, WAF off/token false, deadline120s, CANCEL giữa requests.
Empty result giữ như quan sát chưa có quote; **không tự chứng minh thị trường
đóng**. Error/auth/403/429/schema dừng, không bypass hoặc tải cả ngày để thử lại.
Source/config/raw/protocol/runtime hashes và status/log giữ output mới.

Nếu có ticks: kiểm order/grid/spread, tổng hợp OHLC Bid/Ask bằng oracle đã có;
so với raw M1 side còn tồn tại để phân biệt thiếu response/paired view với lệch
aggregation. Không điền nến thiếu từ giá cũ hoặc sửa calendar để làm đẹp PnL.
Muốn tạo dataset có reconstruction phải có transformation/provenance và kiểm
overlap riêng, giữ dataset cũ; oracle này tự nó không cấp quyền rerun/promote,
broker execution hoặc chứng nhận phí/prop. Không simulation/model/broker calls.
