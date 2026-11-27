# GBPUSD S01 · 20:00 so với 20:30 UTC

**Giữ quyết định gác S01.** Trên 287 lệnh tick cùng entry, stop,
khối lượng và phí, mốc gốc 20:30 UTC trừ **2,68R** so với 20:00.
Ở cụm 2018–2020, 30 phút cuối không tạo được mức cải thiện cần
thiết ngay cả ở cực trị thuận lợi của những ngày thường đã đo.
Phần lịch lịch sử chưa chắc chắn vẫn để ngỏ một khoảng nhỏ trong
cận rộng nhất. Chưa có bằng chứng để mở sổ tài khoản.
[Hồ sơ H1 V25](CORPUS-ISOLATION-V25-RESULTS-20261118.md) ·
[Quyết định V26](BATCH-EXACT-ISO-V26-RESULTS-20261118.md).

## Cùng 287 lệnh tick năm 2022–2023

Đọc sổ economics-v2 và tick sealed của lane S01, kiểm timestamp,
SHA và các điều kiện nguồn. Mốc thử sớm là min(20:00, hạn đã
clamp). Dùng Bid cho BUY và Ask cho SELL, quote đầu trong 60 giây.
SL xuyên trước hạn vẫn ưu tiên. Giữ 150 USD risk tham chiếu, lot
gốc, spread quan sát, commission 5 USD và slippage 4 USD/lot/vòng.
Kết quả ở 20:30 bao gồm các hạn đóng sớm gốc.

| Năm | Lệnh | Tick 20:00 | Tick hạn gốc | Gốc trừ 20:00 | Đổi mức thoát do 30 phút cuối |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022 | 142 | +5,9919R | +5,1173R | −0,8745R (−131,18 USD) | 60 |
| 2023 | 145 | +26,1925R | +24,3873R | −1,8053R (−270,79 USD) | 59 |

Trong 168 lệnh bất biến, 160 được ghi ở nhóm stop trước 20:00
ngoài nhóm lịch đóng sớm. Tám lệnh ở ngày có hạn trước 20:00, gồm
bốn lệnh đã stop trước chính hạn đó. Không có stop mới giữa 20:00
và hạn gốc trong phần so gần đây.

V25 và tick có cùng **287 mục đã nhận** trong hai năm, cùng giá
entry và trạng thái có/không stop trước hạn tương ứng. H1 20:00
trên đúng nhóm này đạt **+6,9701R / +26,7437R**, hơn tick 20:00
**0,9783R / 0,5511R**. Quy đổi chi phí theo S01 cho hai sổ không
đổi các tổng H1 này. Chênh còn lại là giá thoát mô hình H1 so với
quote và lịch tick, gồm cả khớp stop và cách gắn hạn. Không quy
toàn bộ chênh giữa V25 và S01 thành ảnh hưởng của 30 phút cuối.
Cổng gốc ≤15% nhận 287/300. Cổng ≤12% chỉ làm đối chiếu, giữ
266/300 và chưa tính lại kết quả giao dịch theo tập hẹp đó.
[Card V25](GBPUSD-V25-H1-DIAGNOSTIC-CARD-20261118.md).

## Cụm 2018–2020 · cần thêm 50,2048R

Cố định 412 lệnh đã nhận trong V25. Net 20:00 là **−30,2048R**.
Hai thứ tự H1 cho cùng tổng. Trong 393 lệnh có cận timing, 235
đã stop trước 20:00 và 158 sống tới 20:00. Với 158 lệnh, dùng
cực trị Bid/Ask đúng chiều của H1 20:00–21:00 để tạo cận rộng
cho phần thay đổi, kể cả khi stop trong 30 phút cuối. Tổng delta
nằm trong **[−37,4876R, +29,4709R]** với điều kiện giữ nguyên đường
H1 trước 20:00 cùng mô hình khớp V25. Cực trị H1 chỉ là cận.

| Trường hợp | Net tối đa có điều kiện trong cụm |
| --- | ---: |
| Cộng cực trị thuận lợi của phần có cận vào sổ gốc, trước phần lịch chưa biết | −0,7339R |
| Cho cả 19 ngày còn vướng lịch thoát ở cực trị tốt nhất khả dĩ hoặc bỏ lệnh | +22,8189R |
| Sau khi thay một cực trị bằng delta tick đã quan sát | +21,7105R |

Lịch clamp S01 đóng băng chỉ bao phủ từ 2022. Mười chín ngày
2018–2020 có cờ nghỉ/đóng sớm theo lịch tham chiếu V8 được giữ
riêng. Cận ngoài cho phép thoát ở bất kỳ cực trị có lợi nào từ
entry đến hết giờ 20:00, bị chặn sau giờ chạm stop đầu tiên, hoặc
đứng ngoài. Mức tăng tối đa giả định của 19 ngày là +23,5528R.
Sau mẫu tick, để đạt +20R vẫn cần **+21,8423R** từ nhóm này ngay
cả khi phần còn lại đạt cực trị, tức khoảng **92,7%** cận riêng
của 19 ngày. Cận này không nhận diện được giờ đóng thật và chưa
loại trừ toàn bộ khả năng toán học trên sổ H1. Nó không ràng
buộc cùng mức cho một sổ tick khác đường giá, geometry hoặc cohort.

### Mẫu tick cũ, khóa theo ngày trước khi lấy dữ liệu

Chọn hai ngày sống tới 20:00 sớm nhất mỗi quý 2018–2020, tổng 24,
không xem PnL khi chọn. Kho S01 có tick từ 2022. Trong 24 yêu cầu
cố định tới dữ liệu lịch sử Dukascopy, có **1** giờ khớp đủ
Bid/Ask OHLC, **7** lỗi 503 và **16** timeout. Một lượt qua kênh
Jetta dùng trong S01 trả HTTP 202 cho cả 23 giờ còn lại, giữ
trạng thái thiếu. Giờ 06/10/2020 có 3.557 tick, không stop trong
nửa giờ, delta **+0,2686R** so với cận gốc +1,3770R. Chỉ thay
đúng một dòng của cận, không ngoại suy 23 giờ thiếu hoặc ngụ ý
đã kiểm tick trước 20:00. [Dữ liệu lịch sử Dukascopy](https://www.dukascopy.com/api/data/get/historical-data-export).

## Ý nghĩa đối với BASE

S01 tick 20:30 đã yếu khi bỏ ba lệnh thắng nhất: **−11,5454R**
năm 2022 và **+0,3017R** năm 2023. V25 đã đo DD tăng từ 12,2065R
lên 15,5620R hoặc 26,5211R khi thêm hai mức risk GBP. Với ảnh
hưởng timing âm ở dữ liệu tick gần, cụm cũ chỉ gần đủ trong cận
rộng nhất và nguồn tick cũ chưa đủ, chưa đáng kéo thêm dữ liệu
hay mở replay chung. `BASE_GUARD` vẫn `NOT_QUALIFIED`. Không
mở giá 2024–2026, giữ sổ và worktree lane nguồn ở chế độ đọc.

## Tái hiện

Đối soát 287 phép tính bằng cent, 412 định danh H1, cả hai kịch
bản thứ tự, dấu chênh theo Bid/Ask, và hash nén. Artifacts private,
cả hai lần thử nguồn và danh sách 24 yêu cầu đã khóa nằm ở
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-gbp-s01-exit-clock-20261119/`.
Protocol SHA256 `25bd422b27177522b6b4d3e09e39db93b2e4390a6f7bff4718fac6e0a9a1ec6c`.
Ledger SHA256 `66f10a332dd3854a168b9b685d9e8d39bc73a2766cf3c2fb4b8a079a95c93159`.
Mẫu SHA256 `53859c9f5ccd2fd94578a2b623bb7334ed768f87a1c83980d9006451e5589caf`.
