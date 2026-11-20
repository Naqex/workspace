# Pass 12 · Protocol US500 M1 và pháp y USDJPY Tokyo-box

Baseline `67d1a42`. Development UTC 2018–2024. Giữ khóa giá từ
01/01/2025. Không MT5, OrderSend, Challenge, Monte Carlo, GBPUSD
hay tối ưu. Giữ Git local. Chi phí target theo SHA của `36f1535` và
`8fd77ef`. PnL từ QDM là proxy feed, chưa là broker fill.

## US500

QDM 125.2692, `USA500IDXUSD_PASS12_QUARANTINE`, upstream
`USA500IDXUSD`. QDM update có thể ghi rộng hơn Development vào
cache riêng, chỉ export tick UTC 2018–2024. Không đọc cache thô.
Sau rate limit, thử export đã tải. Nếu thiếu năm do 429, chỉ retry
update sau ít nhất 60 giây rồi export phần thiếu. Kiểm clock của
từng export trước khi đọc giá. Parquet/Zstd có manifest SHA.
Nếu thiếu Cụm A hoặc năm không có cơ hội hợp lệ, dừng Track 1
với US500_M1_DATA_UNAVAILABLE, giữ Track 2.

Dùng NYSE full days 390 phút, DST New York. Hộp 09:30–10:30,
OCO từ 10:30 đến trước 14:00, hard flat 15:55. Cạnh trên dùng
max Ask high, cạnh dưới dùng min Bid low của 60 phút hộp theo
Bid/Ask M1 Pass 10. Buy chạm Ask và Sell chạm Bid, fill ở
stop hoặc open nếu gap bất lợi. Bỏ tín hiệu hai cạnh cùng phút
first-touch Stage-0 theo Pass 10. Dùng same setup và timestamp
cho Fade đổi hướng, executable quote đối diện. H+2/H+4 tính
từ close phút trigger, chỉ khi còn trong phiên tới 15:55, không
đổi sang endpoint khác. Báo Primary 15:55 theo năm/A/B/side.
Dùng observed Bid/Ask, 0 commission, 0 swap. Base 0,25, Mid
0,50 và High 0,75 **index point mỗi chiều**, primary High đã
dùng ở Pass 10. Báo spread tick tại giờ hộp, thuộc QDM. Điểm
giá index và contract FTMO 1 USD/point/lot có vai trò riêng.

Strict có đủ cả 386 phút 09:30–15:55. Nhóm A tối đa 5 phút
rời rạc, cả hai side lệch hai đầu ≤0,2 index point, đủ mốc
09:30/10:30/14:00/15:55 và endpoints horizon; không nhận khe
kẹt bên cạnh fill/exit hoặc nằm qua barrier còn active. Không
bù nến, nhóm còn lại B. Đo cổng Pass 10 trên cả strict/+A ở
High: dương A/B, ≥5/7 năm, dương bỏ top 2 năm, net mean ít
nhất mean friction, thắng Fade ở hai cụm ít nhất mean friction,
friction/stop median ≤12% và ≥50% individually ≤12%. Gate dùng
cohort gốc, không lọc từng lệnh để làm đẹp. Nếu qua, chạy
duy nhất opposite-edge SL, worst-side exit gap và SL cùng phút
entry trước hard flat. Đối chiếu strict/+A, 3 bậc phí. Sống sót
nếu High dương hai cụm, ≥5/7 và còn dương bỏ top 10 lệnh.
Khi đủ điều kiện ghép USDJPY Pass 7B/8, USDJPY 0,30% solo,
Equal 0,15%+0,15%, inverse peak DD Cụm A tổng 0,30%. Vốn đầu cố
định, Prague reset, M1 envelope, FX/CFD margin và floor lot hiển
thị theo snapshot. Portfolio chưa đủ news/calendar broker và
cộng envelope đồng phút là một bound.

## USDJPY

Tái dựng đúng 1.228 và 1.437 lệnh Stress_05, 1.334 và 1.564 ngày
đủ điều kiện Pass 7B/8. Kiểm số lệnh, net R, baseline sổ và
hash. Giữ cách xử lý gap, số bước lot, path, giá và chi phí gốc.

Estimated stress cost gắn tại phút trigger theo giá đã biết:
spread Bid/Ask ở open của phút (proxy có trước/đồng thời fill),
commission 5 USD quy đổi thành khoảng giá ở midpoint open và
slippage 0,20 pip mỗi chiều + 0,50 pip ở entry. Chia cho độ
rộng hộp Tokyo midpoint 00:00–03:00 đã khóa. Chỉ áp một rule
giữ ≤12%, không dùng phí thực nhận hoặc spread ở exit.
Bucket cost <6%, 6–12%, >12%. Bucket width/ATR <0,25;
0,25–<0,50; ≥0,50 và unknown. ATR Wilder 14 lấy từ D1 native
đã đóng trước **03:00 UTC**, xác nhận timestamp. Side, UTC
03:00–06:59 và 07:00–09:59. Đây là phân rã, không tạo side
filter hoặc thay giờ. Báo n, winrate, net, gross losing R, DD
vốn nổi khi gom từng nhóm như sổ riêng, và đóng góp vào khoảng
peak/recovery của baseline. Mỗi trục riêng để tránh đếm trùng.

Tái chạy cash/floating 10k/25k Swing và 50k Standard ở 0,30%
và 0,40% theo engine cũ, cùng ngày, baseline vs ≤12%. Báo
A/B và toàn kỳ. Xác định peak DD và underwater dài nhất
riêng theo timestamp M1 gốc, censor nếu chưa hồi ở mốc khóa.
Báo sổ Swing 10k stress risk 0,40% và đối chiếu 25k/50k;
phân rã đoạn underwater 21 tháng, năm/quý và lệnh đã vào kể
cả lệnh đang mở khi bắt đầu đoạn. Không coi DD của các nhóm
cộng được hoặc thống kê subgroup là quan hệ nhân quả. Giữ
variant để nghiên cứu tiếp chỉ nếu cải thiện net và DD ở cả
hai mẫu, net dương hai cụm và không làm underwater dài hơn;
không nâng risk từ các bảng này.
