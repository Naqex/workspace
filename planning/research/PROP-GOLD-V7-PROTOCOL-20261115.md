# V7 — sửa lịch nghỉ, decommission EURUSD và giải phẫu Gold A

Task `66e95afe-4594-4ddf-a63c-0278e67b3b78`. Đây là **Post-Holdout
Diagnostic / Full-Sample 2022–2026 Audit**, không phải clean OOS mới.
Giá chỉ đến hết 13/10/2026; không mở thêm khoảng sau đó. Giữ VI Dubber WIP,
Trader pin, không broker/challenge purchase/paid source/Astra/subagent.
PR85 `5c7fe4e` đã được owner giao merge. Một branch/PR V7, không merge PR mới.

## Sửa lịch và giới hạn bằng chứng

Giữ nguyên lịch/quotes/entry/SL 2022–2024. Từ 2025, lịch liệt kê đủ các ngày
nghỉ US metals và ngày trước kỳ nghỉ, gồm Independence Observed 03/07/2026.
FTMO là CFD; giờ CME dùng đối chiếu, không thay lịch contract của FTMO.

FTMO Trading Update25/06/2026: Metals CFD đóng03/07/2026 lúc20:00 MT5
GMT+3 =17:00UTC. V6 yêu cầu quote từ17:00 trở đi, trùng lúc đóng cửa.
V7 đăng ký trước số liệu: **đóng trước2phút** so với
`min(giờ guard nghỉ lễ bảo thủ cũ, giờ đóng đích đã xác minh)`.
Friday20:30 thường giữ nguyên. Lịch khai báo cả giờ đóng đích, effective flat,
timezone/nguồn và verified vs declared guard. Khi chưa có thông báo FTMO cho
một ngày, giữ guard bảo thủ có nhãn unknown; không giả toàn bộ lịch đã certified.
Không chọn giờ theo PnL, không lấp khoảng thiếu tùy ý bằng quote quá khứ.
Thiếu quote ở giờ flat mới vẫn là lỗi nguồn; mục tiêu100% không cho phép bịa fill.

Chỉ reprice deadline/exit các tín hiệu sẵn có2025–2026 dưới hai thứ tự M1 đã
đăng ký ở V6. Bảo toàn toàn bộ intent, phía giao dịch, entry và SL tự nhiên.
Gold holdout vẫn Bid M1, Ask proxy0,338USD/oz; không thành observed tick.
SL/forced fills trên đường M1 là có điều kiện. Không thêmTP hoặc chọn SELL-only.
Giữ cả V6 censor history và mọi attempt lỗi V7.

## Ba cột mới và một cột lịch sử

1. V6 co-core censored: chỉ đọc kết quả đã công bố.
2. COCORE_FIXED: cùng Gold+EUR và V4_Harvest, chỉ sửa lịch2025–2026.
   Đây là counterfactual để tách calendar effect, không EUR còn active candidate.
3. GOLD_V4: chỉ Gold A BOTH, $200/$175/$125 theo P1/P2/Funded.
4. GOLD_SCALED: chỉ Gold A BOTH, $250/$200/$150, đúng một policy được giao.

Hai policy Gold giữ cap open initial-stop$800, reserve floor$46k (8%),
equity<=48k cap150/<=47k cap90, daily realized loss>=1k halt tới Prague reset.
10% là giới hạn hãng, **không** biến45000 thành sàn nội bộ sát giới hạn.
Không ratchet. Harvester chỉ Funded, các tham số14ngày/50.5k/51k/80:20/
full profit debit/zero administrative delay giữ nguyên V6 và vẫn là proxy.
Tăng sizing không tự có buffer an toàn; phải đo daily/static DD thực trong model.

57 monthly starts:36 từ2022–24 và21 từJan2025–Sep2026. Mỗi policy/model
khởi tạo từ đầu, không cộng R riêng lẻ để suy ra account. Standalone Funded:
5 annual starts Jan2022..Jan2026, tất cả nối tới13/10/2026; Jan2022 là sổ
liên tục gần5năm. Giữ state liên năm, không reset do đổi năm.

Annual signal books: fixed$150 trên50k (0,30%), BOTH/BUY/SELL chỉ để phân rã,
không chọn phía tối ưu. Báo raw priced intents và min-lot rejects riêng; khi
biên độ SL lớn hơn$150/oz thì minimum0.01lot không thể khớp đúng budget150.
Không nới SL/tăng risk lén để biến mọi intent thành giao dịch.

## Giải phẫu cố định, không tối ưu lại

Qua5năm: median entry price, Asian00–06UTC range, natural SL, ATR trước signal,
SL/Asia range theo%price/ATR; số lệnh và đóng góp BUY/SELL. R tính cùng risk/
commission/slippage/swap definition; không dùng mức giá chủ quan1800→3000.

24h vs48h: liquidation mark ở min(entry+24h, actual exit), so final48h/clamp/SL;
MFE trên đường sống của vị thế, ngày1<=24h/ngày2>24h; tách số lệnh có ngày2.
Sau SL không coi cơ hội giả định là lệnh vẫn còn sống. Đây là markout chẩn đoán,
không đổi exit policy sang24h hoặc chọn horizon từ kết quả.

Top10 cũ PR80: chỉ3Gold PREVDAY/LONDON SWEEP DAY/24H/48H đã có trong bảng.
Tái dùng curve Development2022–23 đã có, tính GoldA+half-budget sleeve không
EUR, correlation/marginal Net-DD và source/scale/economic gates. Không mở
catalog mới, không gọi kết quả các cells này là qualified hoặc OOS2025–26.

## Kiểm chứng và bàn giao

Fixtures cho timezone/holiday/flat-before-close, parent entry-SL parity,
source fence, hai sizing/throttle policies và decommission. Hạch toán hữu tỷ
khác implementation cho tất cả sổ lifecycle/Funded/reference, cash/swap,
admissions/rejects, DD, phase/rewards, dynamicfill. Cùng implementer, không
independent person/model review. Reuse tests không đổi; chạy full test matrix
trong các môi trường dependency sẵn có, không bỏ test.

Report Markdown+JSON, source/decision bindings và failed attempts ở private job;
cập nhật context/index, commit/push và một PR (dự kiến86, số thực do GitHub cấp)
với3required CI xanh ở đúng finalHEAD. Không tự merge hoặc promote.
