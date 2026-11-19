# EURUSD RSI37 · kiểm cửa chặn entry quanh giờ đóng tuần

**Tách giờ bắt buộc đóng khỏi quyền mở lệnh.** Khi khai báo rõ khoảng
phải đứng ngoài, sổ RSI37 trên tick bỏ ba lệnh và giảm lỗ **250,71 USD**.
Cả hai cụm Development vẫn âm. Giữ quyết định gác cấu hình. Các phép
sàng lọc thô và mô phỏng Challenge trước đây giữ cách diễn giải cũ.
[Phép đo RSI37 gốc](PROP-EURUSD-RSI37-POOL-EXIT-RESULTS-20261119.md).

## Tái hiện đúng lệnh 27/12/2019

Các mốc dưới đây tính theo UTC.

| Mốc | Sổ cũ hoặc nguồn đối chiếu |
| --- | --- |
| Thứ Sáu 27/12 · 20:30 | Lịch V8 đã khóa có `FRIDAY_CLOSE`. Hai ngày 27 và 29 không có hàng ngày lễ riêng. |
| Thứ Sáu 27/12 · 21:00 | Engulfing RSI37 báo SELL. Tick đầu vào lúc **21:00:00,110**, Bid **1,11760**, Ask **1,11764**. |
| Thứ Bảy 28/12 · 05:00 | +8h cũ dùng flat trong tương lai, bỏ qua mốc đã qua 20:30. V25 giữ tín hiệu và ghi thiếu endpoint. |
| Chủ nhật 29/12 · 21:00 | Hạn 48h của luật thoát source đã chuẩn hóa. Cả hai hạn đều thiếu quote hợp lệ trong 60 giây. |
| Chủ nhật 29/12 · 22:00 | Mốc mở tuần **giả định của FX** theo quy ước Chủ nhật 17:00 New York. Lịch V8 gốc chỉ có giờ flat, không có trường xác nhận reopen của tài khoản đích. |
| Chủ nhật 29/12 · 22:03:26,782 | Quote quan sát đầu tiên sau hai hạn, Bid **1,11736**, Ask **1,11820**. Sổ cũ có một kịch bản đóng muộn dùng quote này, lỗ **65,40 USD** trên tick. |

V25/V26 dùng `searchsorted(side="right")` để tìm **lần đóng kế
tiếp** khi tính giá đích. Đây là thao tác đúng cho câu hỏi đó.
Đổi sang `left` chỉ xử lý trường hợp trùng giờ, còn lệnh phát sinh
sau cutoff vẫn lọt. Source EA chạy theo nến, hướng lệnh, vị thế và
thời gian giữ, không có bộ lọc cuối tuần tương ứng trong sáu file
đã khóa. Lịch proxy được thêm bởi nghiên cứu.

## Phạm vi và chính sách mới

Bản opt-in `CORPUS_EURUSD_RESEARCH_HARD_FLAT_ENTRY_V1` cho nghiên
cứu này yêu cầu đứng ngoài trong khoảng **[hard-flat, reopen)**.
Adapter lấy mốc sớm nhất giữa 20:30 UTC thứ Sáu và mốc đóng sớm thứ
Sáu của lịch đã khóa, dùng quy ước reopen FX từ `SessionSchedule`.
Mốc thứ Sáu giữ UTC cố định, Chủ nhật 17:00 New York đổi theo DST.
Cửa chặn kiểm cả giờ quyết định và báo giá khớp đầu. Nếu quote ra
sau cutoff, ý định trước cutoff bị hủy. Quyết định mới tại reopen
được vào khi có quote hợp lệ. Cấu hình nghỉ lễ có cửa sổ cấm nhưng
chưa biết reopen được trả `HARD_FLAT_REOPEN_UNKNOWN`. Các hàng lễ
khác trong lịch proxy cũ vẫn dùng cho clamp thoát. Chưa có lịch mở
lại đã xác minh cho EURUSD vào từng kỳ nghỉ lịch sử.

Cửa chặn nạp cửa sổ do study khai báo. Study FX, futures hoặc Swing
có thể dùng cửa sổ khác theo hợp đồng của mình. Không ghép giờ reopen
của metals/futures cho EURUSD và không suy đây là quy định FTMO.
[Lịch đã khóa](PROP-V8-SESSION-CALENDAR-20261115.json) ·
[Hiệu chỉnh mốc 31/12/2021](PROP-V8-CALENDAR-CORRECTION-20261115.json) ·
[Cửa chặn](../../tooling/ai-engines/quant_core/research_entry_admission.py).

| Consumer | Bằng chứng từ caller và receipt |
| --- | --- |
| V25 Engulfing EURUSD | Markout riêng, 85 tín hiệu. Chỉ mốc 27/12 nằm trong cửa sổ mới và vốn có `priced=false`. V25 chưa có sổ SL-active cho cấu hình này. |
| V26 batch | Dùng helper `deadlines()` cho markout, chỉ gọi `normalize_trades()` nếu Stage-0 đạt. Receipt 115 ô có 0 lần chạy SL-active. |
| V26 EURUSD MFI | Import cùng helper deadline. Sáu ô chỉ có Stage-0, 0 lần chạy SL-active. Receipt tổng hợp chưa có định danh từng dòng để đếm cơ hội thô ngoài giờ. |
| RSI37 pool | Adapter private mới là consumer thực thi một-vị-thế được chỉnh. 446 cơ hội thô vẫn có đủ trong receipt. |
| V14/V15 và các sổ Reward | Tape `prop_v14_paths` / `prop_v15_paths` và state machine riêng. Không có dependency đến cổng corpus. Không chạy lại sổ Challenge. |
| V16/V19 BASE_GUARD và V26 ISO | V16 chặn entry tại cutoff ngày qua `CausalFlatSchedule`; V19/V26 ISO dùng lại tape V16 qua block replay. Bốn tape Dev, mỗi tape 340 vị thế, đều có entry trước cutoff của chính tape. Một exit PRIMARY mỗi order định giá trễ 60 giây, là hành vi báo giá thoát riêng. |

P1, P2 và Reward của phiên bản mới là **N/A**. Không có sổ Challenge
dùng đường thực thi corpus này cần tính lại.

## Đối chiếu trước và sau

Cửa chặn đánh dấu **5/446 thời điểm duy nhất** trên cả tick và hai thứ
tự M1. Theo mẫu sở hữu là Engulfing **1**, Harami **3**, StarDoji **1**.
Hammer, BlackCrows và MeetingLines **0**. Hai mốc 02/03/2018 và
26/02/2021 vốn thiếu quote vào lúc 22:00 nên không tạo thay đổi PnL.
Ba lệnh còn lại đều có quote vào hợp lệ theo sổ cũ và được ghi tách
lý do lịch. Hai phiên 23/11/2018 và 26/11/2021 đóng sớm theo mốc
proxy 16:58 UTC.

| Tín hiệu bị loại khỏi sổ | Quote vào native UTC | Net source exit cũ · tick |
| --- | --- | ---: |
| Harami · 23/11/2018 18:00 | 18:00:00,061 · giá vào 1,13351 | −35,50 USD |
| Engulfing · 27/12/2019 21:00 | 21:00:00,110 · giá vào 1,11760 | −65,40 USD, kịch bản thoát muộn |
| Harami · 26/11/2021 17:00 | 17:00:00,110 · giá vào 1,13017 | −149,81 USD |

Sổ trước là kịch bản liên tục có lần thoát muộn đã ghi riêng. Sổ sau dùng
cùng quote, phí, kích thước và luật thoát cho mọi lệnh còn lại.

| Nguồn và cách thoát | Lệnh trước → sau | PnL trước → sau | Delta | Chặn do overlap trước → sau |
| --- | ---: | ---: | ---: | ---: |
| Tick, source exit | 386 → 383 | −5.719,88 → −5.469,17 USD | +250,71 USD | 48 → 48 |
| Tick, +8h | 344 → 341 | −3.230,75 → −2.992,11 USD | +238,64 USD | 90 → 90 |
| M1, source exit | 395 → 392 | −6.715,84 → −6.506,69 USD | +209,15 USD | 49 → 49 |
| M1, +8h | 353 → 350 | −4.777,96 → −4.578,75 USD | +199,21 USD | 91 → 91 |

Cả hai thứ tự M1 cho cùng số lệnh/PnL, có thể khác giờ khớp nội phút.
Không có lệnh thay thế do giải phóng vị thế. Các lệnh chung giữ đúng
quote và tiền tới cent. Sau kiểm lịch, 431/431 cơ hội tick đủ điều
kiện có cả hai giá thoát đúng hạn, từ 433/434 ở sổ trước gate. Phép
so cùng cặp còn **−7.164,54 USD** theo source và **−4.444,93 USD**
theo +8h. Sổ một vị thế theo source còn **−609,38 USD** cụm
2018–2020 và **−4.859,79 USD** cụm 2021–2023. Các giới hạn về
coverage nội phút và spread proxy của phép đo trước vẫn áp dụng.

**Kết luận.** Đây là sửa độ tin cậy của lần sàng thực thi kế tiếp.
Không có ứng viên nào đổi quyết định. Chạy 31 test tập trung, gồm
trước/tại/sau cutoff, quote trễ qua cutoff, mở lại đúng giờ, DST,
cửa sổ FX/futures khác nhau và reopen lễ chưa biết. So lại 446
cơ hội, sổ trước gate và chênh lệch đến cent từ receipt 2018–2023.

Hồ sơ riêng `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-eurusd-rsi37-entry-calendar-20261119/`,
gồm card, adapter, bảng và manifest. SHA-256 `corrected.json` là
`ed337ea5ae6efb692e4de06ff2c70da69754ceb0b9b5897be2312cc36e8a5642`.
