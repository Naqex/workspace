# V11 source admission addendum — trước numeric GBPUSD/AUDUSD

Metadata `fx-h1-history-v3/sealed-books.json` xác nhận H1 BID/ASK đã seal
cho GBPUSD/AUDUSD2010–2024, gồm đầy đủ2018–2023 và warmup2017.
V10 chưa admission hai nguồn này cho full M1/path; không được suy thành
không có H1 full Development. Giữ verdict/source pins V10, sửa inventory V11.

Rà tiếp các manifest cũ tìm thêm US500 M1 explicit2013–2021 trên E,
ghép nguồn đã admit2022–2023. Native oracle/proof cũ có sẵn;2020 có3
source requests unavailable, không reconstruct các ngày thiếu. Đây là
conditional scan có declared source gaps, không chứng nhận clean path.

Quét thêm đúng44recipes F1–F3 ×4horizons ×2FX =352cells và92recipes
F1–F4 ×4horizons US500 =368cells. Global budget1264cells (544V10 +720new).
Không F4FX,
không đổi lookbacks, stops, sides, horizons hoặc composer thresholds.
Code/source hashes và commit phải lưu trước lần đọc giá Dev đầu tiên.

Source là native H1, không tạo60M1 giả. Index read-only file path/hash
trực tiếp trên E, không copy quote files. Parse chỉ2017warmup–2023;
2024books chỉ metadata, không đọc OHLC. Timestamps strictly hourly,
Bid/Ask paired, OHLC/units validated;0,00001 quote-unit grid.

Closed H1/H4/D1 dùng cùng frozen formulas/ATR/recipes V10 qua một module
adapter cô lập; không sửa frozen V10 files hoặc monkeypatch global module.
Test cùng H1 từ syntheticM1 phải cho cùng at/side/stop/config.

USD-quoted FX costs là **declared EUR-like stress proxy**:100.000base units/lot,
9USD/lot commission+slippage roundtrip, observed H1-open Bid/Ask spread,
−40USD/lot/weekday rollover, Wednesday×3; SYM/ASYM cùng proxy cho hai FX này.
Đây không là target-native GBPUSD/AUDUSD fee/swap admission hoặc 2edges.
Ghi thiếu target specs; không dùng Gold costs cho FX hoặc bỏ financing.

Endpoint vẫn firstquote≥deadline≤60s. H1 không có giá20:30 hoặc16:58:
DAY/FRIDAY/holiday-clamped endpoints thiếu thì **invalid**, không interpolate,
không đẩy exit sang21:00 hoặc tạo M1. Báo raw/valid coverage riêng.
Các cell không100%endpoint không vào component composer.
Không có intrahour path thì chưa SL-active, equity/DD hoặc Challenge-qualified.

US500 dùng legacy Atlas conservative stress đã có:contract1USD/point/lot,
commission1USD/lot RT +slippage1,5indexpoints RT, funding−2USD/lot/calendar
day. Spread là observed paired M1. SYM/ASYM cùng proxy; không gọi là
live FTMO spec. Không dùng Gold commission/swap cho US500. Vẫn dùng
calendar clamp bảo thủ đã đăng ký, ghi khác biệt broker/asset calendar.
Giữ index trực tiếp vào canonical quarterly JSON, không copy full source.

Thống kê Holm1264/DSR proxy là diagnostics, không gate mới để cứu/tắt selection.
Daily correlation dùng proxy của cùng schema đã khóa. Cổng component/ensemble
và điều kiện commit trước validation giữ nguyên protocol620b28b.
