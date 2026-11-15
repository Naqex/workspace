# V12 — đo SL thật trên đường giá, F5 và chất lượng dữ liệu

**Đã xây kernel SL-active, quét đủ 2.888 trường hợp; chưa có ensemble đủ điều kiện Challenge.**
Có 28 path cells dương hai cụm trên phần đo được, gồm 20 F1–F4 và 8 F5.
Có 19 trường hợp đạt các cổng kinh tế trên phần có đường giá nhưng còn thiếu coverage.
Không ghép các phần thiếu thành portfolio đủ chuẩn, không mở giá 2024–2026, không mô phỏng payout.

PR #90 đã merge `2175685`, nhánh V11 đã xóa. V12 ở `codex/sl-active-ensemble-v12`;
PR mới dự kiến #91 chờ owner, không tự merge. Giữ Trader pin và WIP VI Dubber.

## 1. Kernel, accounting và kiểm chứng

P0 giữ natural SL đến horizon; P1 kích hoạt từ net +1,5R theo SYM rồi bảo vệ net +0,15R
tại lúc kích hoạt; swap tương lai có thể làm giảm mức net đó. Stop mới chỉ có hiệu lực từ
bar kế tiếp. P2 chỉ dùng TP 3R cho F5; không search 2,5R/3R rồi chọn bản đẹp hơn.
BUY thoát Bid, SELL thoát Ask; cùng bar chạm stop/TP thì stop trước. Gap qua stop khớp
open bất lợi hơn, cộng slippage; không ép lỗ lớn về đúng −1R.
Không đọc extrema của bar bắt đầu tại horizon, không dùng nến H1 chưa hoàn thành tại hạn 20:30.

64-bar extrema blocks tìm vùng có first hit, rồi xác định bar chính xác. Không Numba/new provider.
Kernel lần quét đầy đủ: **36.91s**; toàn pipeline **181.36s**, gồm IO/source hashing, F5, profiles và ghi matrix.
US500 load/proof là phần IO lớn; không gọi 36,9s là thời gian toàn bộ chiến dịch.
Lần sửa cent chỉ chạy lại US500; các tài sản khác reuse đúng matrix/hash, không rerun tài chính.

### Sai khác auditor đã phát hiện và sửa

Lần đầu oracle phát hiện 562 sai khác US500: gross theo giá 0,001 point cần làm tròn
tới cent theo từng leg trước khi cộng phí, và P1 phải tìm đúng giá quote trên plateau cent.
Ví dụ +0,805 USD gross → +0,81 −2,50 phí = −1,69; làm tròn raw net −1,695 cho −1,70.
Giữ attempt đầu và oracle fail; protocol correction commit `c88cafb` trước outcome mới.
Phí danh nghĩa, signals, stops, horizon và gates không đổi.
Đây là reference 1 lot. Khi sizing/lot grid đổi, phải replay theo quantity; không nhân R thành cash/payout.

Oracle cuối: **1,569,694 cost views tới cent**, **8,037 first-hit checks**, 0 discrepancy.
Auditor tự decode accepted inputs, dùng Decimal và lịch/fee formulas riêng; không import
Quant Core PnL/DD. Bốn tài sản giữ nguyên; US500 chỉ được audit sau correction.
Cùng implementer và cùng feed, không là independent person/feed review.
Gold/EUR vẫn Ask proxy. M1 extrema và H1 conservative bars chưa phải broker-native tick fills.
Cost/holiday assumptions giữ protocol V11/V12; chưa có target-native FTMO spec/news admission.
Một lần audit sau correction dừng vì trùng tên counter trong log; đã sửa logging, giữ receipt
và log fail, chỉ chạy lại auditor. Không chạy lại tài chính vì lỗi log này.
Prague balance anchor/DST, funding, static floor và first-hit có fixtures riêng; **chưa có
continuous account đủ điều kiện để audit daily/static prop loss trên dữ liệu thật**.

Full Windows: **1072/1072**, giữ đủ **1.048 IDs cũ**, thêm 24, 0 skip. Smoke **66 tests / 0.670s**.
Giữ các smoke attempts chậm ban đầu. Đổi scalar test từ truy cập NumPy từng phần tử sang
Python lists, giữ nguyên 400 query cases; không bỏ test để ép timing. Timings là các lượt quan sát.

## 2. SL có cứu kết quả V11 và F5 có bù được năm yếu?

V11 đo raw endpoint; đó là screen đã đăng ký, không là lỗi giả sử bot không có SL.
V12 là trial exit mới do owner duyệt. Stop vừa cắt lỗ vừa có thể loại lệnh sau đó hồi phục.
Không mặc định −4R/−8R là nguyên nhân đã được chứng minh cho toàn bộ năm 2021/2022.

1.264 cells cũ × P0/P1 = 2.528; F5 5 assets × H1/H4 × N=3/5/10 ×4 horizons ×3 modes
=360; tổng 2.888. Direction BOTH; ADX14 ≤25; wick +0,1 ATR; tối đa 1 event/ngày/recipe.
F5 là phá biên nhiều ngày rồi đóng lại trong biên; không tự động được xem là counter-cyclical edge.

| Asset | Path cells | Dương 2 cụm (phần đo được) | Chỉ còn vướng path | Đủ path & có tín hiệu | Priced /raw cell-events |
|---|---|---|---|---|---|
| XAUUSD | 808 | 18 | 13 | 0 | 260,958/318,808 (81.9%) |
| EURUSD | 424 | 10 | 6 | 0 | 135,242/199,060 (67.9%) |
| GBPUSD | 424 | 0 | 0 | 0 | 146,115/212,192 (68.9%) |
| AUDUSD | 424 | 0 | 0 | 0 | 142,041/214,560 (66.2%) |
| US500 | 808 | 0 | 0 | 4 | 100,491/218,888 (45.9%) |

Số liệu trên là cell-records; P0/P1/P2 cùng recipe không là các edge độc lập.
Invalid không đồng nghĩa mọi trường hợp đều là gap: có cả hạn DAY trước entry, entry sau
Friday flat hoặc natural stop không hợp lệ. Các flag có thể trùng nhau; JSON tách counter.
V11 có 42 endpoint cells dương; V12 F1–F4 còn 8 P0 +12 P1 dương trên phần có path.
F5 thêm 3 P0 +3 P1 +2 P2 dương, đều EURUSD; chưa có F5 đủ coverage.
Bản JSON có toàn bộ 42 hồ sơ V11, sáu năm, P0/P1, sample count, phí, exits và nguyên nhân dừng.

### Đối chứng 6 nhánh V11 — so trên cùng các lệnh có thể đo cả ba cách

Chỉ giữ common cohort có endpoint V11, P0 và P1 cùng xác định và qua phí. Đây là diagnostic
có điều kiện, không là portfolio 6 năm đầy đủ; các lệnh giữ lâu dễ gặp gap hơn nên censoring
có thể làm mẫu này thiên về lệnh bị stop. Không dùng bảng này để tự kết luận toàn bộ SL có edge/không edge.
SYM, risk 1R/tín hiệu, chưa sizing/shared-account constraints. US500 có thêm correction cent đã nêu.

| Năm | N common | V11 endpoint R | P0 R | P1 R | Lệnh lãi endpoint bị P0 cắt lỗ | Lệnh lỗ được P0 giảm lỗ |
|---|---|---|---|---|---|---|
| 2018 | 19 | -1.351 | -1.050 | -1.050 | 1 | 6 |
| 2019 | 35 | -4.633 | -7.504 | -7.504 | 2 | 8 |
| 2020 | 87 | +18.458 | +4.098 | +1.115 | 10 | 15 |
| 2021 | 69 | -22.885 | -14.813 | -13.562 | 2 | 20 |
| 2022 | 92 | -27.980 | -11.556 | -6.390 | 7 | 27 |
| 2023 | 82 | +36.097 | +22.323 | +22.323 | 6 | 8 |

Toàn bộ V11 cũ là +59,421R trên 516 admissions; không đặt tổng đó cạnh P0/P1 thiếu path
rồi gọi chênh lệch là tác động thuần của SL. Chi tiết full/paired counts của từng sleeve trong JSON.

### Các nhánh dẫn đầu theo từng asset/mode, vẫn chỉ là chẩn đoán

Xếp theo min(raw R hai cụm), cần có giá ở cả hai cụm; không lấy cohort rỗng 0R làm best.
Sáu giá trị năm dưới là admitted SYM R theo thứ tự 2018/19/20/21/22/23, chỉ phần xác định.
Không dùng thứ hạng này để đổi composer hoặc ghép các mẫu bị thiếu.

| Asset | Mode | ID | Net R sáu năm (partial) | Path đủ /raw |
|---|---|---|---|---|
| XAUUSD | P0 | `XAUUSD\|F3:compression=BB:n=60:quantile=0.1:multiple=1\|48H\|P0` | -0.14 / -5.31 / +6.77 / -3.37 / -5.10 / +13.46 | 61/74 |
| XAUUSD | P1 | `XAUUSD\|F4:hour=15:impulse=1:timing=MONTH:multiple=1\|DAY\|P1` | -1.68 / +3.17 / +3.37 / +1.67 / -0.79 / +2.88 | 89/95 |
| EURUSD | P0 | `EURUSD\|F5:tf=H4:n=5:adx=25:buffer=0.1\|DAY\|P0` | +14.00 / -4.56 / -2.50 / -2.85 / +0.23 / +13.70 | 181/200 |
| EURUSD | P1 | `EURUSD\|F5:tf=H4:n=10:adx=25:buffer=0.1\|DAY\|P1` | +9.47 / +0.55 / -3.21 / -3.41 / +5.80 / +12.06 | 98/116 |
| GBPUSD | P0 | `GBPUSD\|F3:compression=BB:n=60:quantile=0.1:multiple=2\|DAY\|P0` | -6.07 / -2.03 / +0.00 / -1.01 / -1.01 / -5.31 | 16/116 |
| GBPUSD | P1 | `GBPUSD\|F3:compression=BB:n=60:quantile=0.1:multiple=2\|DAY\|P1` | -6.07 / -2.03 / +0.00 / -1.01 / -1.01 / -5.31 | 16/116 |
| AUDUSD | P0 | `AUDUSD\|F3:compression=BB:n=60:quantile=0.1:multiple=2\|DAY\|P0` | -1.02 / +0.00 / -1.03 / -2.04 / +0.00 / -2.04 | 6/97 |
| AUDUSD | P1 | `AUDUSD\|F3:compression=BB:n=60:quantile=0.1:multiple=2\|DAY\|P1` | -1.02 / +0.00 / -1.03 / -2.04 / +0.00 / -2.04 | 6/97 |
| US500 | P0 | `US500\|F4:hour=13:impulse=0.5:timing=MONTH:multiple=2\|FRIDAY\|P0` | +0.18 / -0.09 / +0.96 / -0.10 / +0.32 / +0.05 | 25/71 |
| US500 | P1 | `US500\|F4:hour=13:impulse=0.5:timing=MONTH:multiple=2\|FRIDAY\|P1` | +0.18 / -0.09 / +0.96 / -0.10 / +0.32 / +0.05 | 25/71 |

### F5 theo từng asset — xếp hạng chẩn đoán, chưa là ứng viên được tuyển

| Asset | Cấu hình có min(cluster R) cao nhất | 18–20 raw R | 21–23 raw R | Path đủ /raw | Trạng thái |
|---|---|---|---|---|---|
| XAUUSD | `XAUUSD\|F5:tf=H4:n=10:adx=25:buffer=0.1\|24H\|P2` | -0.557 | +7.726 | 84/105 | 2018:ECONOMIC, PATH_OR_ENDPOINT_INCOMPLETE |
| EURUSD | `EURUSD\|F5:tf=H4:n=5:adx=25:buffer=0.1\|DAY\|P0` | +7.119 | +11.079 | 181/200 | PATH_OR_ENDPOINT_INCOMPLETE |
| GBPUSD | `GBPUSD\|F5:tf=H4:n=10:adx=25:buffer=0.1\|24H\|P2` | -9.825 | -8.126 | 92/112 | 2018:ECONOMIC, 2021:ECONOMIC, PATH_OR_ENDPOINT_INCOMPLETE, MEAN_BELOW004 |
| AUDUSD | `AUDUSD\|F5:tf=H4:n=10:adx=25:buffer=0.1\|DAY\|P1` | -16.559 | -16.853 | 38/123 | 2018:RETENTION, 2018:ECONOMIC, 2021:RETENTION, 2021:ECONOMIC, PATH_OR_ENDPOINT_INCOMPLETE, MEAN_BELOW004 |
| US500 | `US500\|F5:tf=H4:n=10:adx=25:buffer=0.1\|48H\|P1` | -4.641 | -1.673 | 20/50 | 2018:RETENTION, 2018:ECONOMIC, 2021:RETENTION, 2021:ECONOMIC, PATH_OR_ENDPOINT_INCOMPLETE, MEAN_BELOW004 |

Bảng best theo từng mode/asset và đủ sáu năm nằm trong JSON. Không lấy available-only
positive mean để promote: phải sửa path bằng nguồn có chứng cứ, giữ nguyên rule rồi mới kết luận.
19 trường hợp chỉ còn vướng path gồm 13 Gold và 6 EURUSD; đây là danh sách cần xác minh dữ liệu,
không phải 19 chiến lược đã chứng minh có edge.

## 3. Ensemble, validation 9 năm và Challenge/payout

Composer vẫn medoid/equal-risk; threshold V12 cố định 0,25, default 0,30 giữ V11 semantics.
Exact V11 composer source lưu từ Git; không sửa historical pins. Graph ghép cùng asset/family
nếu correlation cao hoặc trùng quyết định, không thử mọi subset/weights hoặc ép chọn F5.
Không có component đồng thời đạt kinh tế và coverage, nên **K=0, composition=None**. Chưa hình thành ensemble để
đo thật 5/6 năm dương hoặc ex-best-year >0; không diễn giải các giá trị rỗng thành hiệu suất 0.

| Phạm vi | Trạng thái |
|---|---|
| 2018–2023 | Đã đo SL-active từng cell, còn path gaps; chưa có qualified ensemble |
| 2024 | Không mở giá trong V12; không có annual portfolio performance |
| 2025 | Không mở giá trong V12 |
| 2026 YTD đến 13/10/2026 | Không mở giá trong V12 |
| Monthly FTMO 2-Step /Standalone Funded50k | Không chạy — gate Dev chưa đạt |
| Pass rate /tháng hoàn tất /payout count /payout USD | N/A, không phải 0 |
| Worst Daily Loss /Static Loss của tài khoản thật | PROP_UNMEASURED |

2024–2026 từng có exposure các chiến dịch khác: chưa đo cho V12 không biến chúng thành clean OOS.
Không tăng risk, hạ gate, thêm filter/subset hoặc chạy validation để cứu outcome.

## 4. Storage D/E, nguồn nén và việc còn thiếu

| Scope | Logical bytes đọc được | Files | Folders | Timestamp UTC |
|---|---|---|---|---|
| D | 211767375854 | 575377 | 75350 | 2026-11-15T07:02:59.809495+00:00 |
| E | 225818788404 | 556857 | 37787 | 2026-11-15T07:02:29.552931+00:00 |

V11 đã xóa đúng 119,79 GB; **V12 không xóa thêm hoặc nén raw/WIP**. Snapshot là logical readable
bytes ở thời điểm ghi, không allocated NTFS/free space. Hai VI permission gaps vẫn unknown.

Đã kiểm metadata 2,576 containers: {'LISTED_NO_EXTRACTION': 1070, 'UNSUPPORTED_METADATA_CONTAINER': 1504, 'METADATA_ERROR': 2}.
Có 5 member matches: 3 ảnh GBP/US500 và 2 GBPUSD D1 sample của LEAN. Không nguồn M1 đầy đủ
được admission mới; GBP/AUD vẫn H1. Gzip/zstd không phải archive có index member thì giữ
unsupported, không giải nén/đọc payload validation để tìm kiếm. Không tuyên bố đã chứng minh
toàn bộ E không có thêm dữ liệu. Full container list, exclusions và errors ở private artifacts.

Cross-path code/docs: 2,000 candidate pairs, 1,998 cặp byte-identical, 26,120,672 bytes đã hash.
Chỉ code/docs 4KB–2MB, budget 2.000 pairs; không raw data. Backup cố ý giống source vẫn có thể
cần giữ. File giống nhau chưa chứng minh cả thư mục dư hoặc cho phép xóa source đang được pin.

Đã nhóm thành 887 cặp thư mục có file giống trong mẫu.
Các ví dụ lớn là thư mục thư viện Pygments trong uv cache/venv và bản backup; chưa chứng minh
toàn bộ cây byte-identical hoặc không còn consumer. Danh sách đầy đủ ở private JSON, không tự xóa.

**Khuyến nghị:** chưa mua Challenge. Ưu tiên xác minh đường giá của danh sách 19 trường hợp
giữ nguyên rule, nhất là EURUSD F5 và Gold; chưa mở thêm grid hay tối ưu weights/risk.
Nếu không tìm được nguồn đủ chứng cứ thì giữ inconclusive, không gọi đó là economic fail toàn bộ.
Việc này cần scope/source-path budget tiếp theo; V12 chốt tại các gate đã đăng ký.

Data flow: frozen source/index →observed bar paths →SL/P1/TP + cost legs →coverage/economics
→component gate →stop. Account/validation chỉ mở sau gate và freeze đủ.
Private job `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\sl-active-ensemble-v12-20261115`. JSON chứa registry, paired cohorts, source/hash, failed-attempt history,
counts và oracle. Delivery receipt ghi PR/HEAD/CI thực tế sau bàn giao; không tự merge PR mới.
