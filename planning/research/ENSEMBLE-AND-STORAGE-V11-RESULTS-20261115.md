# V11 — dọn E, tìm lại nguồn dữ liệu và kiểm định ensemble

**Đã xóa đúng 119,79 GB cache được duyệt và kiểm xong tổ hợp 6 nhánh; chưa đủ cơ sở thi Challenge.**
Sau khi sửa lịch nguồn US500, có 42 cấu hình dương ở cả hai cụm năm. Trong đó, 33 cấu hình
qua cổng thành phần; bộ ghép giữ 6 đại diện trung tâm (medoid), với mức risk bằng nhau.
Tần suất đạt trung bình 86 tín hiệu/năm, nhưng chỉ dương 4/6 năm. Vì cổng Development
chưa đạt, không mở giá 2024–2026, không chạy đường lệnh có SL hay mô phỏng tài khoản/payout.

PR #89 đã merge tại `3dd35a7`, nhánh V10 đã xóa. Branch `codex/ensemble-and-storage-v11`;
PR mới dự kiến #90 chờ owner duyệt, không tự merge. Giữ WIP của VI Dubber, Trader pin,
dữ liệu gốc và các seal kiểm toán lịch sử.

## 1. Storage D/E và dữ liệu tìm lại được

Đã kiểm trước toàn bộ 17 thư mục: khớp manifest hash, danh sách file, size, mtime và số thư mục;
không có reparse point, Git lồng, đuôi dữ liệu thị trường hoặc process tham chiếu target.
Journal ghi ý định và kết quả từng lần xóa.
Đã xóa **119,790,227,244 bytes / 100,287 files / 12,101 folders**.
Đây là logical bytes; không đo allocated NTFS bytes hoặc suy ra toàn E là duplicate.

| Scope | Before files /folders | After files /folders | Before bytes | After bytes |
|---|---|---|---|---|
| D | 575,230 / 75,286 | 575,235 / 75,286 | 211,766,165,164 | 211,766,225,462 |
| E | 657,008 / 49,884 | 556,730 / 37,783 | 345,266,554,222 | 225,478,636,428 |

E giảm ròng tại snapshot **119,787,917,794 bytes / 100,278 files**; chênh với lượng xóa chính xác do journal/code/job mới phát sinh.
Snapshot sau purge có timestamp trong JSON; không đồng nhất nó với dung lượng sau mọi run về sau.
D không purge thêm trong V11. Hai VI permission gaps vẫn unknown, không thay ACL.

| Target được duyệt trên E | Bytes xóa | Files | Folders |
|---|---|---|---|
| activity-report-20261024\rust-target | 5273863286 | 5114 | 826 |
| controls-refine-20261024\rust-target | 16775182072 | 10930 | 926 |
| dashboard-refine-20261024\rust-target | 8404026718 | 6083 | 834 |
| grid-semantics-20261025\rust-target | 1108479479 | 2326 | 415 |
| grid-sort-20261025\rust-target | 1107546412 | 2326 | 415 |
| grid-system-20261025\rust-target | 15439465174 | 10064 | 923 |
| label-settings-20261029\api-target | 19750184032 | 12126 | 1154 |
| live-chart-stability-20261024\rust-target | 940335502 | 2215 | 394 |
| live-ledger-filters-20261029\api-target | 1299288091 | 2342 | 417 |
| live-trades-metadata-20261029\api-target | 1207996094 | 2338 | 417 |
| mt5-account-lifecycle-20261103\api-target | 546338875 | 2076 | 414 |
| mt5-tools-20261024\rust-target | 5468093924 | 6543 | 1071 |
| naqex-migration-20261029\cargo-target | 20457377810 | 17521 | 1331 |
| owner-system-audit-20261031\cargo-target | 11525243918 | 7664 | 867 |
| report-period-averages-20261025\rust-target | 7703701604 | 5780 | 840 |
| session-report-20261025\rust-target | 1675918303 | 2520 | 443 |
| trade-data-audit-20261025\rust-target | 1107185950 | 2319 | 414 |

### Kiểm kê source, không lấy tên file làm chứng nhận dữ liệu

Kiểm kê metadata D/E nhận diện 69,931 file có thể liên quan tới nguồn thị trường; có 2 lỗi quyền đọc.
Không đi theo links hoặc quét nội dung OS/apps/games/dependency trees. Không parse giá validation.
Full filename/size inventory và phạm vi bỏ qua nằm private; source index lưu path/hash, không copy raw.

| Asset | Nguồn/khung đã xác minh | Phạm vi và giới hạn |
|---|---|---|
| XAUUSD | QDM M1; ticks cho các phần đã được nhận | Metadata 2003–2026; V11 dùng lại 2018–2023. Full M1 dùng Ask proxy 0,338 USD/oz. |
| EURUSD | QDM M1 + 517.750.341 ticks | Metadata 2003–2026; V11 dùng lại 2018–2023. Full M1 dùng Ask proxy 1 pip. |
| GBPUSD / AUDUSD | H1 gốc có cả Bid/Ask, sealed books 2010–2024 | Đủ 2018–2023 + warmup; thiếu M1, đường giá trong giờ, quote 20:30 và full 2025–2026. |
| US500 | M1 Bid/Ask: nguồn dài 2013–2021, nguồn 2022–2024, metadata 2025–2026 | Quét 2018–2023 + warmup; thiếu 3 request ASK năm 2020. Không dựng giá thay thế. |
| USDJPY | M1 pilot 10/01/2019 và 15/07/2022; sample/test data | Chưa đủ 6 năm; không coi fixture 2013 hoặc tick mô phỏng 2019 là lịch sử thị trường thật. |
| BTCUSD / BTCUSDT | D1 crypto và một số file mẫu/tick mô phỏng | Chưa có full H1/M1 đủ điều kiện; không tạo M1 từ D1. |

V10 mới admission QDM Gold/EUR; điều đó không chứng minh E thiếu mọi nguồn khác.
V11 tìm lại H1 GBP/AUD và M1 US500 dài hạn thông qua sealed-books/native-source proofs.
Đây là gap reuse/inventory đã sửa; không phải nguồn mới tải về hoặc một edge đã được xác nhận.

`PairedHourlyStore`/`IndexedUs500Store` trong Quant Core đọc files gốc trên E theo index/hash.
H1 dùng nến gốc, không nhân thành 60 nến M1 giả. Adapter cô lập giữ source V10 nguyên vẹn;
test M1→H1 trên fixture giả lập xác nhận cùng at/side/stop/config. Không đổi system config.

Health command phát hiện cả cache build mới, không chỉ 17 thư mục đã xóa:

```powershell
python tooling/workspace_maintenance.py cross-drive-audit --root D:/ANNAM/TradingWorkspace --other-root E:/BACKUP-TRADINGWORKSPACE --cache-manifest <V10-manifest> --output <private-health.json>
```
Các thư mục nghi là build cache hiện đọc được 89,005,921,016 bytes; budget 120.000.000.000 bytes; exceeded=False, unknown=True.
Candidate theo tên không là delete authority. Tool chỉ đọc/cảnh báo, không tự purge, không daemon;
không thể bảo đảm cache không bao giờ mọc lại nếu không có lịch audit tương lai. Không tạo automation.

## 2. Giải phẫu dual-cluster và bộ ghép

Giữ 544 ô V10; thêm 176 GBPUSD + 176 AUDUSD + 368 US500 = **1.264 ô / 316 công thức tín hiệu**.
Không mở grid mới: F1 phá H4/D1, F2 hồi theo trend H4, F3 nén rồi bung, F4 timing/momentum.
Không đổi direction BOTH, naturalSL, horizons hoặc tối ưu trọng số.

Chi phí: Gold/EUR giữ V10. GBP/AUD dùng proxy 9 USD/lot/vòng, swap −40 USD/lot/ngày thường,
thứ Tư ×3. US500 dùng Atlas cũ: commission 1 USD/lot/vòng + slippage 1,5 points/vòng,
funding −2 USD/lot/ngày lịch, contract 1 USD/point/lot. Spread lấy từ Bid/Ask quan sát được.
Các proxy này chưa là biểu phí FTMO hiện hành được xác nhận; SYM/ASYM FX/US500 trùng scenario.

Cổng V10 thực tế là ≥20 tín hiệu được nhận/năm trung bình mỗi cụm và ≥4/6 năm dương;
không phải 80 lệnh hoặc dương mọi năm. V11 nới cổng thành phần theo owner, giữ nguyên verdict V10.
Dual-positive chỉ tính phần có endpoint, không lấp giá thiếu. Component còn cần raw/admitted cluster
dương, mean ≥0,04R, tỷ lệ qua ngưỡng phí 15% ≥50%/cụm, pooled scale ≤15% và đủ 100% endpoint.

### Hai technical views được giữ riêng

| View | Dual-positive | Components | Selected K | Kết quả |
|---|---|---|---|---|
| Ban đầu | 36 | 19 | 4 | 2018:ENSEMBLE_CADENCE_BELOW50; SYM:ENSEMBLE_FEWER_THAN5_POSITIVE_YEARS; ASYM:ENSEMBLE_FEWER_THAN5_POSITIVE_YEARS; EFFICIENCY_NOT_ABOVE_EVERY_COMPONENT |
| Sửa source clock | 42 | 33 | 6 | SYM:ENSEMBLE_FEWER_THAN5_POSITIVE_YEARS; ASYM:ENSEMBLE_FEWER_THAN5_POSITIVE_YEARS; EFFICIENCY_NOT_ABOVE_EVERY_COMPONENT |

Mốc 20:30 UTC của US500 rơi vào giờ nghỉ 16:15–18:00 New York trong mùa hè.
Kiểm timestamp trên mọi ô US500 tìm thấy 45.738 bản ghi invalid thuộc giờ nghỉ này.
Đã dùng lại `prop_portfolio_sources.deadline`: nếu hạn thoát nằm trong giờ nghỉ thì lấy
16:00 New York cùng ngày, chỉ dời sớm hơn; không chọn giờ theo PnL hoặc lấp giá thiếu.
Giữ attempt đầu, commit correction trước outcome mới; không đổi alpha rules/gates/costs.
H1 FX vẫn thiếu giá 20:30: không dùng quote 21:00 hoặc nội suy để cứu coverage.

### Toàn bộ 42 cấu hình dương hai cụm và giữ được ≥50% tín hiệu tại ngưỡng phí 15%

N là số tín hiệu được nhận trước risk budget/lot grid/SL-active, chưa số lệnh thật.
Mean/DD là admitted SYM **endpointR proxy**, ghi PnL theo ngày entry; không floating equity/account DD.
N sáu năm theo thứ tự 2018/19/20/21/22/23. Pass% ghi cụm 2018–2020 / 2021–2023.

| ID | Asset /họ | Config /horizon | Direction | N6năm | Pass% | MeanR | Max endpointR-DD |
|---|---|---|---|---|---|---|---|
| C01 | US500 F1 | `F1:tf=D1:n=5:impulse=0.5:multiple=1` FRIDAY | BOTH | 0/3/25/15/51/13 | 100.0/100.0 | +0.0949 | 14.775 |
| C02 | US500 F1 | `F1:tf=D1:n=5:impulse=0.5:multiple=2` FRIDAY | BOTH | 0/3/25/15/51/13 | 100.0/100.0 | +0.0483 | 7.383 |
| C03 | US500 F1 | `F1:tf=H4:n=40:impulse=0.5:multiple=1` FRIDAY | BOTH | 5/3/29/17/43/34 | 100.0/98.9 | +0.1010 | 34.311 |
| C04 | US500 F1 | `F1:tf=H4:n=40:impulse=0.5:multiple=2` FRIDAY | BOTH | 5/3/29/17/43/34 | 100.0/98.9 | +0.0510 | 17.217 |
| C05 | US500 F1 | `F1:tf=H4:n=40:impulse=0:multiple=1` FRIDAY | BOTH | 11/18/49/47/63/49 | 100.0/99.4 | +0.0377 | 39.920 |
| C06 | US500 F1 | `F1:tf=H4:n=40:impulse=0:multiple=2` FRIDAY | BOTH | 11/18/49/47/63/49 | 100.0/99.4 | +0.0189 | 20.005 |
| C07 | US500 F3 | `F3:compression=BB:n=120:quantile=0.15:multiple=1` 48H | BOTH | 1/5/19/11/16/17 | 100.0/100.0 | +0.2634 | 15.478 |
| C08 | US500 F3 | `F3:compression=BB:n=120:quantile=0.15:multiple=1` FRIDAY | BOTH | 1/5/19/11/16/17 | 100.0/100.0 | +0.3445 | 18.470 |
| C09 | US500 F3 | `F3:compression=BB:n=120:quantile=0.15:multiple=2` 48H | BOTH | 1/5/19/11/16/17 | 100.0/100.0 | +0.1325 | 7.814 |
| C10 | US500 F3 | `F3:compression=BB:n=120:quantile=0.15:multiple=2` FRIDAY | BOTH | 1/5/19/11/16/17 | 100.0/100.0 | +0.1732 | 9.321 |
| C11 | US500 F3 | `F3:compression=BB:n=120:quantile=0.1:multiple=1` 48H | BOTH | 0/4/16/9/12/13 | 100.0/100.0 | +0.1588 | 11.686 |
| C12 | US500 F3 | `F3:compression=BB:n=120:quantile=0.1:multiple=1` FRIDAY | BOTH | 0/4/16/9/12/13 | 100.0/100.0 | +0.2262 | 18.663 |
| C13 | US500 F3 | `F3:compression=BB:n=120:quantile=0.1:multiple=2` 48H | BOTH | 0/4/16/9/12/13 | 100.0/100.0 | +0.0798 | 5.881 |
| C14 | US500 F3 | `F3:compression=BB:n=120:quantile=0.1:multiple=2` FRIDAY | BOTH | 0/4/16/9/12/13 | 100.0/100.0 | +0.1139 | 9.347 |
| C15 | US500 F3 | `F3:compression=BB:n=60:quantile=0.1:multiple=1` 48H | BOTH | 2/3/14/10/14/15 | 100.0/100.0 | +0.1443 | 6.888 |
| C16 | US500 F3 | `F3:compression=BB:n=60:quantile=0.1:multiple=1` FRIDAY | BOTH | 2/3/14/10/14/15 | 100.0/100.0 | +0.1845 | 13.684 |
| C17 | US500 F3 | `F3:compression=BB:n=60:quantile=0.1:multiple=2` 48H | BOTH | 2/3/14/10/14/15 | 100.0/100.0 | +0.0729 | 3.473 |
| C18 | US500 F3 | `F3:compression=BB:n=60:quantile=0.1:multiple=2` FRIDAY | BOTH | 2/3/14/10/14/15 | 100.0/100.0 | +0.0930 | 6.842 |
| C19 | XAUUSD F3 | `F3:compression=BB:n=120:quantile=0.1:multiple=1` 24H | BOTH | 3/4/15/8/15/15 | 61.1/100.0 | +0.0723 | 13.168 |
| C20 | XAUUSD F3 | `F3:compression=BB:n=120:quantile=0.1:multiple=2` 24H | BOTH | 11/10/15/8/15/15 | 100.0/100.0 | +0.0639 | 6.607 |
| C21 | XAUUSD F3 | `F3:compression=BB:n=60:quantile=0.15:multiple=1` 24H | BOTH | 5/11/18/16/18/18 | 64.2/100.0 | +0.0760 | 17.456 |
| C22 | XAUUSD F3 | `F3:compression=BB:n=60:quantile=0.15:multiple=2` 24H | BOTH | 17/18/18/16/18/18 | 100.0/100.0 | +0.0408 | 8.745 |
| C23 | XAUUSD F3 | `F3:compression=BB:n=60:quantile=0.1:multiple=1` 24H | BOTH | 3/10/13/10/12/15 | 70.3/100.0 | +0.0695 | 15.836 |
| C24 | XAUUSD F3 | `F3:compression=BB:n=60:quantile=0.1:multiple=1` FRIDAY | BOTH | 3/10/13/10/12/15 | 70.3/100.0 | +0.1678 | 19.445 |
| C25 | XAUUSD F3 | `F3:compression=BB:n=60:quantile=0.1:multiple=2` 24H | BOTH | 12/12/13/10/12/15 | 100.0/100.0 | +0.0462 | 7.962 |
| C26 | XAUUSD F3 | `F3:compression=BB:n=60:quantile=0.1:multiple=2` FRIDAY | BOTH | 12/12/13/10/12/15 | 100.0/100.0 | +0.0886 | 9.799 |
| C27 | XAUUSD F4 | `F4:hour=14:impulse=1:timing=WEEK:multiple=1` DAY | BOTH | 12/17/30/33/26/37 | 72.8/100.0 | +0.0641 | 13.621 |
| C28 | XAUUSD F4 | `F4:hour=14:impulse=1:timing=WEEK:multiple=2` DAY | BOTH | 28/23/30/33/26/37 | 100.0/100.0 | +0.0178 | 6.859 |
| C29 | XAUUSD F4 | `F4:hour=15:impulse=0.5:timing=MONTH:multiple=1` 48H | BOTH | 16/16/25/26/33/33 | 75.0/100.0 | +0.0966 | 26.141 |
| C30 | XAUUSD F4 | `F4:hour=15:impulse=0.5:timing=MONTH:multiple=2` 48H | BOTH | 26/25/25/26/33/33 | 100.0/100.0 | +0.0339 | 13.222 |
| C31 | XAUUSD F4 | `F4:hour=15:impulse=1:timing=MONTH:multiple=1` 24H | BOTH | 6/12/12/14/18/21 | 71.4/100.0 | +0.1046 | 15.923 |
| C32 | XAUUSD F4 | `F4:hour=15:impulse=1:timing=MONTH:multiple=1` 48H | BOTH | 6/12/12/14/18/21 | 71.4/100.0 | +0.1542 | 19.894 |
| C33 | XAUUSD F4 | `F4:hour=15:impulse=1:timing=MONTH:multiple=1` DAY | BOTH | 6/12/12/14/18/21 | 71.4/100.0 | +0.0990 | 4.986 |
| C34 | XAUUSD F4 | `F4:hour=15:impulse=1:timing=MONTH:multiple=2` 24H | BOTH | 12/18/12/14/18/21 | 100.0/100.0 | +0.0433 | 8.037 |
| C35 | XAUUSD F4 | `F4:hour=15:impulse=1:timing=MONTH:multiple=2` 48H | BOTH | 12/18/12/14/18/21 | 100.0/100.0 | +0.0768 | 10.026 |
| C36 | XAUUSD F4 | `F4:hour=15:impulse=1:timing=MONTH:multiple=2` DAY | BOTH | 12/18/12/14/18/21 | 100.0/100.0 | +0.0447 | 3.591 |
| C37 | XAUUSD F4 | `F4:hour=15:impulse=1:timing=WEEK:multiple=1` 24H | BOTH | 11/24/30/35/29/40 | 76.5/100.0 | +0.1366 | 17.095 |
| C38 | XAUUSD F4 | `F4:hour=15:impulse=1:timing=WEEK:multiple=1` 48H | BOTH | 11/24/30/35/29/40 | 76.5/100.0 | +0.0693 | 35.450 |
| C39 | XAUUSD F4 | `F4:hour=15:impulse=1:timing=WEEK:multiple=2` 24H | BOTH | 24/31/30/35/29/40 | 100.0/100.0 | +0.0292 | 8.680 |
| C40 | XAUUSD F4 | `F4:hour=15:impulse=1:timing=WEEK:multiple=2` 48H | BOTH | 24/31/30/35/29/40 | 100.0/100.0 | +0.0111 | 17.971 |
| C41 | XAUUSD F4 | `F4:hour=16:impulse=1:timing=MONTH:multiple=1` DAY | BOTH | 1/6/12/5/5/10 | 63.3/100.0 | +0.0643 | 6.605 |
| C42 | XAUUSD F4 | `F4:hour=16:impulse=1:timing=MONTH:multiple=2` DAY | BOTH | 7/11/12/5/5/10 | 100.0/100.0 | +0.0223 | 3.228 |

Cột cluster dưới: rawR/admittedR; sáu cột năm dùng admitted SYM.

| ID | 18–20 raw/admit | 21–23 raw/admit | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|
| C01 | +1.82/+1.82 | +8.33/+8.33 | +0.00 | +1.94 | -0.12 | -8.68 | +8.24 | +8.77 |
| C02 | +0.95/+0.95 | +4.21/+4.21 | +0.00 | +0.97 | -0.02 | -4.34 | +4.15 | +4.40 |
| C03 | +9.84/+9.84 | +3.39/+3.39 | +5.28 | +1.09 | +3.47 | -14.39 | +16.50 | +1.27 |
| C04 | +4.97/+4.97 | +1.71/+1.71 | +2.64 | +0.55 | +1.78 | -7.21 | +8.29 | +0.63 |
| C05 | +8.50/+8.50 | +0.44/+0.44 | +4.33 | -1.82 | +5.99 | -22.25 | +7.92 | +14.77 |
| C06 | +4.32/+4.32 | +0.16/+0.16 | +2.16 | -0.91 | +3.07 | -11.15 | +3.89 | +7.42 |
| C07 | +10.06/+10.06 | +8.11/+8.11 | +0.94 | -0.62 | +9.74 | -8.50 | +0.76 | +15.86 |
| C08 | +16.90/+16.90 | +6.87/+6.87 | +3.86 | +1.12 | +11.92 | -7.43 | -3.67 | +17.97 |
| C09 | +5.08/+5.08 | +4.07/+4.07 | +0.47 | -0.31 | +4.91 | -4.29 | +0.38 | +7.98 |
| C10 | +8.51/+8.51 | +3.43/+3.43 | +1.93 | +0.57 | +6.02 | -3.74 | -1.87 | +9.05 |
| C11 | +8.24/+8.24 | +0.34/+0.34 | +0.00 | -0.49 | +8.73 | -3.71 | -3.61 | +7.65 |
| C12 | +10.26/+10.26 | +1.96/+1.96 | +0.00 | +0.76 | +9.50 | -0.06 | -7.07 | +9.10 |
| C13 | +4.16/+4.16 | +0.15/+0.15 | +0.00 | -0.24 | +4.41 | -1.87 | -1.82 | +3.84 |
| C14 | +5.19/+5.19 | +0.97/+0.97 | +0.00 | +0.38 | +4.80 | -0.03 | -3.58 | +4.58 |
| C15 | +2.75/+2.75 | +5.62/+5.62 | -0.94 | -0.70 | +4.39 | -3.99 | +2.34 | +7.26 |
| C16 | +6.67/+6.67 | +4.03/+4.03 | +1.98 | -0.71 | +5.40 | -2.91 | -2.82 | +9.76 |
| C17 | +1.41/+1.41 | +2.82/+2.82 | -0.47 | -0.35 | +2.22 | -2.01 | +1.18 | +3.65 |
| C18 | +3.38/+3.38 | +2.02/+2.02 | +0.99 | -0.36 | +2.74 | -1.46 | -1.44 | +4.92 |
| C19 | +6.10/+1.51 | +2.83/+2.83 | +3.04 | +2.07 | -3.60 | +5.23 | -6.41 | +4.01 |
| C20 | +3.22/+3.22 | +1.51/+1.51 | +1.21 | +3.81 | -1.79 | +2.61 | -3.17 | +2.07 |
| C21 | +6.65/+5.06 | +1.47/+1.47 | +2.24 | -0.91 | +3.73 | +1.21 | -5.84 | +6.10 |
| C22 | +3.42/+3.42 | +0.87/+0.87 | -2.41 | +3.95 | +1.88 | +0.61 | -2.88 | +3.13 |
| C23 | +4.64/+2.52 | +1.86/+1.86 | +1.63 | +0.38 | +0.50 | +5.52 | -10.44 | +6.78 |
| C24 | +9.06/+7.13 | +3.44/+3.44 | -1.73 | -6.21 | +15.07 | +1.16 | -16.42 | +18.70 |
| C25 | +2.41/+2.41 | +1.01/+1.01 | +0.33 | +1.81 | +0.27 | +2.77 | -5.22 | +3.46 |
| C26 | +4.67/+4.67 | +1.88/+1.88 | +0.73 | -3.74 | +7.69 | +0.60 | -8.27 | +9.56 |
| C27 | +0.94/+4.65 | +5.29/+5.29 | +1.79 | -2.98 | +5.84 | -10.23 | +4.55 | +10.97 |
| C28 | +0.47/+0.47 | +2.68/+2.68 | -0.80 | -1.67 | +2.95 | -5.15 | +2.27 | +5.56 |
| C29 | +5.65/+8.59 | +5.79/+5.79 | -4.19 | +3.25 | +9.54 | -6.72 | -11.21 | +23.73 |
| C30 | +2.85/+2.85 | +2.85/+2.85 | -7.01 | +5.05 | +4.80 | -3.39 | -5.71 | +11.95 |
| C31 | +5.25/+5.80 | +2.88/+2.88 | -6.18 | +3.15 | +8.83 | -2.85 | -6.98 | +12.71 |
| C32 | +7.15/+5.64 | +7.16/+7.16 | -3.50 | +4.53 | +4.60 | -2.62 | -7.20 | +16.98 |
| C33 | +3.49/+3.28 | +4.93/+4.93 | -2.81 | +2.49 | +3.60 | +0.07 | +1.54 | +3.32 |
| C34 | +2.65/+2.65 | +1.46/+1.46 | -6.40 | +4.63 | +4.43 | -1.43 | -3.55 | +6.44 |
| C35 | +3.66/+3.66 | +3.63/+3.63 | -5.54 | +6.89 | +2.31 | -1.33 | -3.62 | +8.58 |
| C36 | +1.79/+1.79 | +2.46/+2.46 | -2.84 | +2.82 | +1.81 | +0.02 | +0.76 | +1.67 |
| C37 | +5.63/+17.58 | +5.51/+5.51 | -4.68 | +1.34 | +20.92 | -7.06 | -1.42 | +13.99 |
| C38 | +0.67/+7.82 | +3.89/+3.89 | +5.15 | -2.22 | +4.89 | -6.16 | -9.21 | +19.25 |
| C39 | +2.73/+2.73 | +2.78/+2.78 | -7.17 | -0.62 | +10.52 | -3.61 | -0.71 | +7.10 |
| C40 | +0.36/+0.36 | +1.74/+1.74 | -0.55 | -1.49 | +2.40 | -3.24 | -4.70 | +9.67 |
| C41 | +1.25/+1.50 | +1.01/+1.01 | +0.47 | +2.50 | -1.47 | +0.04 | -3.37 | +4.34 |
| C42 | +0.59/+0.59 | +0.52/+0.52 | +0.14 | +1.21 | -0.77 | +0.02 | -1.70 | +2.20 |

Lý do V10 và V11 được tách; US500 mới không bị gán là đã quét ở V10.

| ID | V10: thiếu cadence/năm cũ /mới; thiếu năm dương; lý do khác | V11 component /selection |
|---|---|---|
| C01 | Chưa source admission/chưa quét ở V10 | SELECTED |
| C02 | Chưa source admission/chưa quét ở V10 | admitted, cùng cụm với medoid khác |
| C03 | Chưa source admission/chưa quét ở V10 | ENDPOINT_INCOMPLETE |
| C04 | Chưa source admission/chưa quét ở V10 | ENDPOINT_INCOMPLETE |
| C05 | Chưa source admission/chưa quét ở V10 | ENDPOINT_INCOMPLETE, MEAN_NET_R_BELOW004 |
| C06 | Chưa source admission/chưa quét ở V10 | ENDPOINT_INCOMPLETE, MEAN_NET_R_BELOW004 |
| C07 | Chưa source admission/chưa quét ở V10 | admitted, cùng cụm với medoid khác |
| C08 | Chưa source admission/chưa quét ở V10 | SELECTED |
| C09 | Chưa source admission/chưa quét ở V10 | admitted, cùng cụm với medoid khác |
| C10 | Chưa source admission/chưa quét ở V10 | admitted, cùng cụm với medoid khác |
| C11 | Chưa source admission/chưa quét ở V10 | admitted, cùng cụm với medoid khác |
| C12 | Chưa source admission/chưa quét ở V10 | admitted, cùng cụm với medoid khác |
| C13 | Chưa source admission/chưa quét ở V10 | admitted, cùng cụm với medoid khác |
| C14 | Chưa source admission/chưa quét ở V10 | admitted, cùng cụm với medoid khác |
| C15 | Chưa source admission/chưa quét ở V10 | admitted, cùng cụm với medoid khác |
| C16 | Chưa source admission/chưa quét ở V10 | admitted, cùng cụm với medoid khác |
| C17 | Chưa source admission/chưa quét ở V10 | admitted, cùng cụm với medoid khác |
| C18 | Chưa source admission/chưa quét ở V10 | admitted, cùng cụm với medoid khác |
| C19 | 12.67/7.33; 0; 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C20 | 8.00/7.33; 0; 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C21 | 8.67/2.67; 0; 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C22 | 2.33/2.67; 0; 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C23 | 11.33/7.67; 0; 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | SELECTED |
| C24 | 11.33/7.67; 0; 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C25 | 7.67/7.67; 0; 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C26 | 7.67/7.67; 0; 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C27 | 0.33/0.00; 1; 2018:CADENCE, SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | SELECTED |
| C28 | 0.00/0.00; 1; SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | MEAN_NET_R_BELOW004 |
| C29 | 1.00/0.00; 1; 2018:CADENCE, SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C30 | 0.00/0.00; 1; SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | MEAN_NET_R_BELOW004 |
| C31 | 10.00/2.33; 1; 2018:CADENCE, 2021:CADENCE, SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | SELECTED |
| C32 | 10.00/2.33; 1; 2018:CADENCE, 2021:CADENCE, SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C33 | 10.00/2.33; 0; 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C34 | 6.00/2.33; 1; 2018:CADENCE, 2021:CADENCE, SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C35 | 6.00/2.33; 1; 2018:CADENCE, 2021:CADENCE, SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C36 | 6.00/2.33; 0; 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C37 | 0.00/0.00; 2; SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C38 | 0.00/0.00; 2; SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | admitted, cùng cụm với medoid khác |
| C39 | 0.00/0.00; 2; SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | MEAN_NET_R_BELOW004 |
| C40 | 0.00/0.00; 2; SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | MEAN_NET_R_BELOW004 |
| C41 | 13.67/13.33; 0; 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | SELECTED |
| C42 | 10.00/13.33; 0; 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY | MEAN_NET_R_BELOW004 |

### Top 15 V10 đối chiếu lại

| Rank V10 | ID ở bảng trên | V11 |
|---|---|---|
| 1 | C32 | Xem component/medoid reason phía trên |
| 2 | C29 | Xem component/medoid reason phía trên |
| 3 | C37 | Xem component/medoid reason phía trên |
| 4 | C35 | Xem component/medoid reason phía trên |
| 5 | C33 | Xem component/medoid reason phía trên |
| 6 | C24 | Xem component/medoid reason phía trên |
| 7 | C31 | SELECTED |
| 8 | C30 | Xem component/medoid reason phía trên |
| 9 | C19 | Xem component/medoid reason phía trên |
| 10 | C39 | Xem component/medoid reason phía trên |
| 11 | C26 | Xem component/medoid reason phía trên |
| 12 | C23 | SELECTED |
| 13 | C36 | Xem component/medoid reason phía trên |
| 14 | C20 | Xem component/medoid reason phía trên |
| 15 | C21 | Xem component/medoid reason phía trên |

42 cấu hình dương hai cụm gồm 24 Gold + 18 US500. Cổng thành phần giữ 19 Gold + 14 US500;
các cặp FX mới không có thành phần đạt. Bộ ghép nối cùng asset/family nếu corr ≥0,30 hoặc
trùng ≥50% thời điểm tín hiệu; chọn medoid trung tâm, hòa thì theo ID. Khác họ cũng cần corr <0,30.
Không thử mọi tổ hợp, side hoặc trọng số. 33 thành phần → 6 đại diện, mỗi tín hiệu cược 1R.
Correlation dùng endpoint proxy ghi theo ngày entry, không chứng nhận
independent bets hoặc actual daily mark-to-market covariance. Equal weights vẫn có selection bias.

## 3. Ensemble: Development và bảng 9 năm

| Sleeve | Asset /setup /exit | N/năm | Mean admittedR |
|---|---|---|---|
| C01 | US500 F1:tf=D1:n=5:impulse=0.5:multiple=1 /FRIDAY | 17.83 | +0.0949 |
| C08 | US500 F3:compression=BB:n=120:quantile=0.15:multiple=1 /FRIDAY | 11.50 | +0.3445 |
| C23 | XAUUSD F3:compression=BB:n=60:quantile=0.1:multiple=1 /24H | 10.50 | +0.0695 |
| C27 | XAUUSD F4:hour=14:impulse=1:timing=WEEK:multiple=1 /DAY | 25.83 | +0.0641 |
| C31 | XAUUSD F4:hour=15:impulse=1:timing=MONTH:multiple=1 /24H | 13.83 | +0.1046 |
| C41 | XAUUSD F4:hour=16:impulse=1:timing=MONTH:multiple=1 /DAY | 6.50 | +0.0643 |

| Năm | N tín hiệu | SYM NetR | ASYM NetR | SYM MeanR | SYM endpointR-DD | Worst daily/static loss% |
|---|---|---|---|---|---|---|
| 2018 | 23 | +1.567 | +1.635 | +0.0681 | 7.633 | N/A — chưa equity path |
| 2019 | 53 | +6.126 | +6.361 | +0.1156 | 5.914 | N/A — chưa equity path |
| 2020 | 111 | +25.500 | +25.872 | +0.2297 | 12.307 | N/A — chưa equity path |
| 2021 | 88 | -23.622 | -23.370 | -0.2684 | 27.622 | N/A — chưa equity path |
| 2022 | 128 | -11.672 | -11.098 | -0.0912 | 31.920 | N/A — chưa equity path |
| 2023 | 113 | +61.522 | +62.002 | +0.5444 | 7.664 | N/A — chưa equity path |
| 2024 | N/A | N/A | N/A | N/A | N/A | Không mở validation |
| 2025 | N/A | N/A | N/A | N/A | N/A | Không mở validation |
| 2026 | N/A | N/A | N/A | N/A | N/A | Không mở validation |

Sáu năm có 516 tín hiệu được nhận = 86.00/năm. Hai cụm đạt 62,33 và 109,67/năm,
nhưng 2018 chỉ có 23 tín hiệu. Chưa đạt 5/6 năm dương: 2021 và 2022 vẫn âm; hiện chỉ 4/6.
SYM tổng +59.421R, endpointR-DD 47.585R; ratio 1.2487 thấp hơn sleeve tốt nhất 1.2868.
Năm 2023 đạt +61,52R, lớn hơn tổng cả 6 năm; bỏ 2023 thì tổng còn âm. Tổng hai cụm
có thể che giấu nhiều năm yếu, nên chưa đủ suy ra lợi thế đều hoặc thu nhập chính.

Không đổi medoid sang highest-profit, bỏ năm xấu hoặc thêm filter/GoldA để cứu result.
GoldA variant được đăng ký chỉ sau khi base ensemble qua Dev path gate; điều kiện chưa tới.
IR=IC×sqrt(breadth) không có nghĩa thêm nhiều cấu hình tương quan thấp sẽ tự sinh IC dương bền.

2024–2026 chưa đo cho V11 nhưng đã có exposure qua nghiên cứu trước: nếu mở sau này
chỉ là kiểm định lịch sử tái sử dụng. Lượt này không mở giá đó; không gọi đây là clean OOS.

## 4. Challenge/payout, kiểm chứng và chốt sổ

| Hạng mục yêu cầu | Trạng thái |
|---|---|
| SL-active / ngân sách mở chung 800 USD / risk tham chiếu 150 USD | CANCELED — endpoint Dev gate chưa đạt |
| Bắt đầu mỗi tháng: 2018–2021 (48), 2022–2024 (36), 2024–10/2026 (34) | Không chạy; cửa sổ chồng lấn, không giả độc lập |
| FTMO 2-Step: mục tiêu 10%/5%, daily 5%/static 10% theo scenario | PROP_UNMEASURED; chưa có pass-rate mới |
| Standalone Funded 50k / rút tiền mỗi hai tuần | Không chạy; Payout Count/USD = N/A, không phải 0 |
| Floating Peak-to-Valley /Worst Daily /Static loss | N/A; endpoint proxy không thay equity path |
| Validation 2024/2025/2026 YTD | Chưa mở trong V11; không lấy đối chứng V8 làm hiệu suất V11 |

Full Windows matrix **1048/1048**, 0 skip, giữ đủ 1.030 IDs cũ; group wall time 28.47s.
Smoke **44 tests / 0.673s**, vẫn <1s.
Timings là từng lượt quan sát, không benchmark capacity hoặc so host CI với local.
Oracle: 1264 cấu hình / 7584 ô năm, 172,294 bản ghi nguồn mới có giá × 2 chế độ phí; 2,030 quote nguồn được kiểm mẫu; sai số tối đa 1.99e-13.
Scalar/Fraction kiểm fees/funding/netR, source JSON decoder riêng đối chiếu entry/exit/spread,
scalar graph/medoid chọn đúng 6 nhánh; tổng từng ngày, từng năm và endpoint DD đều khớp.
Cùng implementer, khác arithmetic/code path; không tự nhận independent person review hoặc feed.
V10 source/matrix/old oracle bindings và V8 exact/V7 snapshot seals đã kiểm lại.

### Bài học và bước tiếp

- Storage: đã thực hiện purge được giao; mọi target khác chỉ được health-audit read-only.
- Data: source discovery phải đi qua E/source proofs, không dừng ở QDM symbol list.
- Engine: port lịch source đã có trước khi gán missing-price thành thiếu alpha; giữ cả failed attempt.
- Method: giảm cadence gate ở sleeve đã làm đúng mục đích; ensemble vẫn có thể không đều qua năm.
- Decision: **No-Go V11**, chưa tăng risk hoặc mua Challenge. Đợt sau cần hypothesis/source-path
  budget mới, không tiếp tục tìm subset/weights trong cùng lô cho tới khi đẹp.

Không sửa skill/AGENTS hoặc thêm daemon; thay đổi nằm ở engine/helper/tests/runbook đúng owner.
Data flow: source index read-only →closed bars →registered recipes →cost/coverage gate →medoid
→equal-risk endpoint screen →stop. SL-active/validation/account chỉ mở khi các gate trước đạt.

Private job `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\ensemble-and-storage-v11-20261115`. JSON báo cáo có registry 42 cấu hình, Top 15 cũ, correlation/overlap,
lịch sử các lần chạy, trạng thái 9 năm và artifact path/SHA256. Delivery receipt ghi PR/HEAD/3 CI
thực tế sau khi checks đạt. Không tự merge PR mới, không broker/Astra/paid/provider calls.
