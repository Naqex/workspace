# R025: chưa ưu tiên bot đầu/cuối tháng

**Cập nhật source correction:** bảng trong file này giữ historical native-expanded
view. [Kết quả hiện hành](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md) xác định
ba ngày dùng padding, sửa đúng ba ngày và reuse1507 ngày; kết luận không đổi.
Kiểm raw-file binding trước đây chưa chứng minh từng nến được raw response
liệt kê; không dùng các bảng cũ như source-only hoặc execution proof.

**Không đạt tiêu chí đã đăng ký để ưu tiên xây bot.** Hiệu ứng đầu/cuối tháng
không hơn ngày thường ở cả hai giai đoạn và hai mức chi phí. Giữ kết quả này;
không chọn riêng giai đoạn đẹp, đổi ngày/giờ hoặc chuyển sang giữ qua đêm.
[Protocol](US500-TURN-OF-MONTH-COMPONENT-PROTOCOL-20261108.md) và code/test đã
commit `6e5795f` trước khi xem kết quả. Đây là phép đo thành phần giá trên dữ
liệu đã có exposure, chưa là chiến lược có SL, sizing, kiểm định ngoài mẫu hay
bằng chứng đủ để đề xuất challenge.

## Kết quả dễ đọc

TOM gồm ngày giao dịch cuối tháng và ba ngày đầu tháng; REST là các ngày còn
lại. Đơn vị là **bps của giá trung bình mỗi phiên; 100 bps = 1% giá**, không
phải phần trăm lời trên tài khoản hoặc USD trên vốn10k.

Giả định: mua tại Ask mở phút09:32 New York, bán tại Bid mở phút cuối phiên,
spread đã nằm trong hai bên giá, commission0 theo public profile FTMO. Trượt
giá chuẩn/cao lần lượt0,25/0,75 mỗi chiều. Chưa có SL, sizing hoặc account.

| Giai đoạn | TOM phí chuẩn | REST phí chuẩn | TOM phí cao | REST phí cao | Tiêu chí đã khóa |
|---|---:|---:|---:|---:|---|
|2019–2021|+1,1293|+1,4950|−1,8692|−1,4797|Không đạt ở cả hai mức phí|
|2022–2024|+6,9646|−2,5293|+4,7489|−4,7431|Đạt ở cả hai mức phí|

Tiêu chí yêu cầu trung bình TOM >0 và >REST trong **cả hai giai đoạn** ở cả
mức phí. Đạt2/4 điều kiện không đủ. Đây là cách sắp thứ tự nghiên cứu tiếp,
không phải kiểm định thống kê hoặc loại bỏ toàn bộ họ chiến lược calendar.

| Năm | TOM đủ/planned | TOM chuẩn/cao,bps | REST đủ/planned | REST chuẩn/cao,bps |
|---|---:|---:|---:|---:|
|2019|48/48|−4,2416/−7,7095|204/204|+5,1514/+1,7130|
|2020|48/48|+19,1407/+15,9842|202/205|−5,0586/−8,1997|
|2021|48/48|−11,5113/−13,8823|204/204|+4,3281/+1,9816|
|2022|48/48|+7,5865/+5,1582|203/203|−9,8491/−12,3052|
|2023|48/48|+15,0661/+12,7149|201/202|+2,4461/+0,1047|
|2024|48/48|−1,7588/−3,6263|204/204|−0,1476/−1,9946|

## Trong phiên và qua đêm là hai thành phần khác nhau

Bảng dưới dùng log return trước chi phí, từ exact Bid close phiên liền trước.
Chỉ những ngày đủ previous close/open/close vào cùng một mẫu. Phép đo mua/bán
trong phiên dùng mẫu đủ dữ liệu riêng; không lấy chênh lệch hai means khác mẫu
để suy account PnL.

| Giai đoạn/nhóm | Close→close | Qua đêm | Trong phiên | Đủ/planned |
|---|---:|---:|---:|---:|
|2019–2021 TOM|+13,2011|+8,1066|+5,0945|144/144|
|2019–2021 REST|+6,9910|+3,1441|+3,8469|607/613|
|2022–2024 TOM|−1,0460|−9,0372|+7,9912|144/144|
|2022–2024 REST|+3,7402|+2,5666|+1,1736|607/609|

Đơn vị vẫn là log bps. Identity close→close = overnight + cash được kiểm từng
ngày. Chưa kết luận giữ qua đêm có lời vì thiếu swap, dividend và hợp đồng của
broker đích. McConnell/Xu2008 xét daily indices; phép đo CFD này chưa là bản
tái hiện phương pháp và kết quả của tác giả.

## Dữ liệu, kiểm lại và thời gian

- Có1510 phiên dự kiến trong2019–2024:288 TOM và1222 REST. Phép đo mua/bán có
  đủ288 TOM +1218 REST; decomposition có288 TOM +1214 REST. Mỗi năm có cả hai
  nhóm và các metric cần thiết nên qua admission. Thiếu giữ unknown, không
  điền giá hoặc biến thành lợi nhuận0.
- Lịch NYSE đầy đủ chọn nhóm ngày trước khi đọc giá. Q4/2018 chỉ cung cấp giá
  phiên trước. Đã validate2.728.293 nến M1 **mỗi bên giá**,50 raw files theo
  quý/bên; không coi đây là toàn bộ lịch sử CFD đầy đủ.
- Reviewer đọc lại raw đã seal, đối chiếu4709 cặp endpoint, tự dựng lịch/giờ/
  nhóm và tính1510 ngày bằng `math.log`/`math.fsum`, không gọi helper đang kiểm.
  Counts, means, giá Bid/Ask, trượt giá và quyết định khớp trong1e−8 bps.
  Ba case cố ý sửa group, predecessor và net cost đều bị reject. Cách tính
  riêng trong cùng agent, chưa là review độc lập bởi người/model khác.
- Hai ngày REST2020 và một ngày TOM2024 có phút entry/exit mà volume cả hai
  bên bằng0. Giữ flag theo protocol; chưa chứng minh có tick thực để khớp.
  Volume của provider không tự là khối lượng giao dịch trên sở.

| Phần việc | Đo thực tế | Ghi chú |
|---|---:|---|
|V1 kiểm input|0,703s|Dừng trước outcome: driver đặt nhầm grid0,01|
|V2 validate + tính + ghi artifact|27,906s|Dùng grid0,001 đúng existing US500 loader|
|Reviewer đọc raw/lịch/tính riêng|11,906s|Không chạy lại phép đo|
|Thiết kế, viết code, tài liệu|Chưa có timer đầu/cuối nhất quán|Không suy thời gian active từ commit|

Giữ failure, source và log V1. V2 sửa cấu hình grid, không sửa giá hoặc nới
validation. Sáu test trước outcome chạy0,035s: tính phí tay, thiếu predecessor,
DST, half-day và counts khi các metric thiếu dữ liệu khác nhau. Code số học
không đổi sau outcome; không cần GPU/Rust hoặc chạy lại chỉ để benchmark.

## Nơi lưu và bước tiếp

Private root: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.

- `execution-v1/us500-turn-month-component-v1`: failure được giữ.
- `execution-v1/us500-turn-month-component-v2`: manifest/source-snapshot,
  input-receipts/endpoints/daily-components/result/independent-arithmetic-review-v1.
- `run-us500-turn-month-component-v{1,2}.py`, `review-turn-month-component-v2.py`;
  stdout/stderr được giữ. Controller22628/launcher22164 đã kết thúc.

R025 vẫn chưa có bot, không tăng số policy. Cơ chế tiếp theo được đọc tại
[R026 method review](FX-MONTH-END-FIXING-METHOD-20261108.md), cần preflight
input/clock trước khi triển khai. C1/C2 chưa hoàn tất. Probe/reviewer không
đọc holdout2025+, không network/model/broker calls hoặc cập nhật runtime/UI.
