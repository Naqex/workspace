# V10 — storage tầng sâu, scanner nhanh và atlas F1–F4

**Đã hoàn tất quét và kiểm định kỹ thuật; chưa có chiến lược mới đủ để thi Challenge.**
PR88 đã merge `97a44f2`. Nhánh `codex/enterprise-alpha-v10`; PR mới để owner duyệt, không tự merge.
544 cấu hình = 136 công thức × 4 thời gian giữ. Có 0 cấu hình đạt cổng kinh tế và 0 đạt đủ Stage0.
Vì vậy không ghép danh mục, không mở giá 2024–2026 và không chạy mô phỏng quỹ 9 năm.

## 1. Dung lượng D và E

Đây là logical bytes, không phải physical NTFS allocated space. Chỉ tổng phần đọc được;
hai thư mục pytest của VI Dubber vẫn PermissionError, không thay ACL. Junction/symlink không được đi theo.

| Ổ / thời điểm | Files | Folders | Bytes | GiB |
|---|---|---|---|---|
| D trước | 591222 | 76144 | 212127713693 | 197.559 |
| D sau | 575154 | 75226 | 211765450617 | 197.222 |
| E trước | 656907 | 49872 | 344880040925 | 321.195 |
| E sau | 656972 | 49880 | 345262904033 | 321.551 |

D giảm ròng 362,263,076 bytes / 16,068 files tại snapshot sau.
Số ròng có cả artifact/test/cache phát sinh; không đồng nhất với tổng bytes từng thao tác xóa.

### D: Top 15 theo số file — trước dọn

| Partition không chồng lấn | Files | Folders | GiB |
|---|---|---|---|
| `projects/integrations` | 157181 | 18891 | 3.029 |
| `projects/mt5-tradingview-backtester` | 87074 | 10268 | 34.231 |
| `projects/vi-dubber` | 82693 | 6482 | 129.058 |
| `projects/trader` | 45304 | 3909 | 13.726 |
| `.runtime/paperclip` | 39425 | 15815 | 0.582 |
| `planning/trader` | 31748 | 4301 | 3.070 |
| `tooling/strategy-engines` | 26795 | 3225 | 0.664 |
| `tooling/ui-qa` | 22006 | 1292 | 0.492 |
| `.runtime/hermes` | 16808 | 1849 | 0.524 |
| `.runtime/strategy-references` | 14681 | 2053 | 1.583 |
| `.runtime/research-statistics` | 8235 | 871 | 0.319 |
| `tooling/chatgpt-web-core` | 6756 | 773 | 0.105 |
| `.runtime/chatgpt-core-checkout-68f631d8` | 6749 | 775 | 0.107 |
| `education/research` | 6708 | 30 | 1.078 |
| `projects/quant-trading` | 4561 | 459 | 0.113 |
| Phần còn lại | 34498 | 5151 | 8.877 |

### D: Top 15 theo dung lượng — trước dọn

| Partition không chồng lấn | Files | Folders | GiB |
|---|---|---|---|
| `projects/vi-dubber` | 82693 | 6482 | 129.058 |
| `projects/mt5-tradingview-backtester` | 87074 | 10268 | 34.231 |
| `projects/trader` | 45304 | 3909 | 13.726 |
| `.runtime/linux` | 37 | 6 | 6.562 |
| `planning/trader` | 31748 | 4301 | 3.070 |
| `projects/integrations` | 157181 | 18891 | 3.029 |
| `.runtime/strategy-references` | 14681 | 2053 | 1.583 |
| `education/research` | 6708 | 30 | 1.078 |
| `tooling/strategy-engines` | 26795 | 3225 | 0.664 |
| `.runtime/paperclip` | 39425 | 15815 | 0.582 |
| `.runtime/hermes` | 16808 | 1849 | 0.524 |
| `tooling/ui-qa` | 22006 | 1292 | 0.492 |
| `.runtime/tools` | 1633 | 97 | 0.439 |
| `.git/modules` | 554 | 355 | 0.347 |
| `.runtime/research-statistics` | 8235 | 871 | 0.319 |
| Phần còn lại | 50340 | 6700 | 1.854 |

### E: Top 15 theo số file — trước dọn

| Partition không chồng lấn | Files | Folders | GiB |
|---|---|---|---|
| `workspace/projects` | 140989 | 11984 | 98.146 |
| `ai-engine-jobs/challenge-discovery4-20261108` | 138709 | 1722 | 38.772 |
| `naqex-migration-20261029/cargo-target` | 17521 | 1331 | 19.052 |
| `label-settings-20261029/api-target` | 12126 | 1154 | 18.394 |
| `controls-refine-20261024/rust-target` | 10930 | 926 | 15.623 |
| `grid-system-20261025/rust-target` | 10064 | 923 | 14.379 |
| `owner-system-audit-20261031/cargo-target` | 7664 | 867 | 10.734 |
| `solo-system-20261115-04e2/research` | 6626 | 14 | 1.016 |
| `mt5-tools-20261024/rust-target` | 6543 | 1071 | 5.093 |
| `dashboard-refine-20261024/rust-target` | 6083 | 834 | 7.827 |
| `ai-chat-continuation-20261023/release-target` | 5998 | 1009 | 3.557 |
| `solo-system-20261115-04e2/uv-cache` | 5827 | 570 | 0.226 |
| `trade-note-layout-20261030/source` | 5788 | 1023 | 0.169 |
| `report-period-averages-20261025/rust-target` | 5780 | 840 | 7.175 |
| `system-capabilities-20261103/isolated-owner-restore` | 5663 | 58 | 4.143 |
| Phần còn lại | 270596 | 25546 | 76.889 |

### E: Top 15 theo dung lượng — trước dọn

| Partition không chồng lấn | Files | Folders | GiB |
|---|---|---|---|
| `workspace/projects` | 140989 | 11984 | 98.146 |
| `ai-engine-jobs/challenge-discovery4-20261108` | 138709 | 1722 | 38.772 |
| `naqex-migration-20261029/cargo-target` | 17521 | 1331 | 19.052 |
| `label-settings-20261029/api-target` | 12126 | 1154 | 18.394 |
| `controls-refine-20261024/rust-target` | 10930 | 926 | 15.623 |
| `grid-system-20261025/rust-target` | 10064 | 923 | 14.379 |
| `owner-system-audit-20261031/cargo-target` | 7664 | 867 | 10.734 |
| `dashboard-refine-20261024/rust-target` | 6083 | 834 | 7.827 |
| `report-period-averages-20261025/rust-target` | 5780 | 840 | 7.175 |
| `ai-foundation-20261023/target` | 4117 | 412 | 6.492 |
| `solo-system-20261115-04e2/cargo-target` | 3261 | 420 | 6.006 |
| `mt5-tools-20261024/rust-target` | 6543 | 1071 | 5.093 |
| `activity-report-20261024/rust-target` | 5114 | 826 | 4.912 |
| `system-capabilities-20261103/isolated-owner-restore` | 5663 | 58 | 4.143 |
| `ai-foundation-20261023/backup` | 5413 | 341 | 4.011 |
| Phần còn lại | 276930 | 26163 | 60.436 |

`@direct` là file trực tiếp/thư mục cha còn dư sau khi tách các nhánh con.
Tổng mọi partition khớp 100% số đếm đọc được. Full maps ở private disjoint-D/E.json, có hash trong JSON báo cáo.

E không phải bản mirror thuần của D: có workspace backup, nhiều snapshot build lịch sử,
và `ai-engine-jobs` chứa nghiên cứu/nguồn duy nhất đang được pin path/hash. D còn VI Dubber lớn;
vì vậy so chênh lệch tổng GB không cho biết phần nào là bản trùng có thể xóa.

Các thao tác đã thực hiện:

- Repack Git root và Trader: giữ refs/HEAD/unreachable, fsck connectivity trước/sau đạt;
  không prune-now trên các checkout dùng chung.
- Xóa đúng3 node_modules của UI QA tháng9 đã đóng:15.918 regular files /357.880.116 bytes,
  cùng273 links. Không đi theo link target; giữ source/screenshots/manifests.
- Cold ZIP một dist cũ:3files/1.028.734bytes →265.044bytes; SHA256 từng file,
  roundtrip và rehash trước bỏ bản giải nén. Restore locator ở MANIFEST.
- Một pnpm-store chưa nén vì có reparse descendant; guard dừng trước thay đổi, nguồn còn nguyên.
- E có plan **dry-run** cho 100,287files /119,790,227,244bytes (119.79GB) build caches cũ.
  **Chưa xóa phần này, chưa chứng minh duplicate bằng content hash.** Manifest là metadata từng file.

Quy trình bảo trì dùng `tooling/WORKSPACE-MAINTENANCE.md`; không có daemon hoặc tự mirror/purge E.

## 2. Engine, tốc độ và kiểm chứng

Luồng chính: M1 đã kiểm hash → nến H1/H4/D1 đã đóng → 136 công thức → 4 endpoint
→ spread/commission/slippage/directional swap → cổng theo năm/cụm → Holm và DSR proxy.
Chỉ đủ Stage0 mới được xây SL-active/account simulation. Lượt này dừng trước bước đó.

| Đo lường | Kết quả | Giới hạn |
|---|---|---|
| Scan nguyên bản544×6 config-years | 8.576s; 380.6config-years/s | M1 đã nạp; gồm signal/markout/statistics, chưa SL/account |
| Tạo cùng136 công thức | 6.288→1.391s; 4.52× | 16 cặp xen kẽ; cùng at/side/stop/config; riêng signal phase |
| Smoke | 30tests /0.643s | Không thay full gate |
| Base serial→2 process | 40.960→21.911s | 1.87×; cùng924IDs |
| Full Windows matrix | 1030tests /29.015s | Cộng wall time các group,0skip; giữ đủ1013IDs cũ |
| Fraction oracle | 243,884priced occurrences ×2fees | max error 3.57e-13 |

Tối ưu là cache timing masks dùng lại trong cùng lần quét; không bỏ kiểm phí hoặc rủi ro.
Benchmark signal giữ nguyên output. Lần scan8,58s là trước cache và trước correction;
không gắn thời gian đó cho một lượt SL-active hoặc toàn chiến dịch đã sửa.
CI chuyển sang full suite gồm native/statistical/worker, upload test IDs và timings.
Attempt Linux đầu chạy đủ 1.030 IDs nhưng lỗi thiếu httpx, một assertion đường dẫn Windows
và 3 skip theo nền tảng. Đã thêm httpx từ lockfile và đặt contracts runner Windows
để chạy cả process ownership/sharing-race tests; giữ nguyên assertions và frozen code.
Secret scan/UI registry tiếp tục trên Linux. Kết quả CI cuối gắn đúng HEAD trong delivery receipt.

### Lỗi đã bắt và cách xử lý

- Run đầu đã lưu xong số liệu nhưng lỗi stdout cuối (`stage` truyền trùng). Giữ attempt thất bại;
  sửa event và có regression, không gọi run đầu exit-success.
- Scalar oracle bắt DAY sau20:30 lấy giá thoát trước entry. Loại endpoint đi ngược thời gian;
  đồng thời chặn entry thứSáu tại/sau20:30 khỏi bị giữ sang tuần sau.
  24ô thay mask, 176occurrences bị invalidated; không đổi at/side/SL/quotes hoặc grid.
- Cổng SCALE sửa từ worst-year sang pooled cluster medians đúng protocol. Không đổi ngưỡng15%.
- Technical registration trước tính lại; original source snapshots/pins/matrix/result giữ nguyên.
  Sau đối soát, Top 15 không đổi và vẫn0 economic/eligible.

Oracle khác arithmetic nhưng cùng người triển khai; không tự nhận independent person review.
HAC5/Holm có phép đối soát riêng. DSR là proxy gần đúng; không là DSR được chứng nhận;
trial budget544 không xóa được selection history của các chiến dịch trước.
V8 exact Dev/release seals và V7 exact snapshot view được kiểm lại; không thay old pins.

## 3. Alpha Atlas qua hai cụm chế độ

F1: phá cấu trúc H4/D1. F2: hồi trong xu hướng H4 rồi H1 tiếp diễn.
F3: nén NR/BB rồi bung. F4: xung lực phiên Mỹ/đầu tuần/đầu-cuối tháng.
XAUUSD có 92 công thức và EURUSD có 44. US500/USDJPY/GBPUSD chưa được nhận vào vì chưa
admission source M1/H1 toàn 2018–2023 kèm cost/spec. Không dùng H1 mẫu thay M1.

Bảng dưới lấy cấu hình đứng đầu từng asset/family để nhìn hướng kết quả;
không cộng lãi các cấu hình hoặc gọi cấu hình đứng đầu là chiến lược đạt.

| Asset / họ | Số ô | Raw netR cụm18–20 /21–23 (SYM) | Số ô dương2cụm | Đạt kinh tế /đủgate |
|---|---|---|---|---|
| XAUUSD F1 | 96 | -6.05 / -0.47 | 0 | 0/0 |
| XAUUSD F2 | 32 | -150.57 / -47.93 | 0 | 0/0 |
| XAUUSD F3 | 48 | +9.06 / +3.44 | 8 | 0/0 |
| XAUUSD F4 | 192 | +7.15 / +7.16 | 16 | 0/0 |
| EURUSD F1 | 96 | -7.36 / +0.17 | 0 | 0/0 |
| EURUSD F2 | 32 | -68.88 / -81.47 | 0 | 0/0 |
| EURUSD F3 | 48 | -0.86 / +2.56 | 0 | 0/0 |

### Top 15 gần đạt — vẫn No-Go

| ID | Cấu hình /horizon | RawR cụm18–20 /21–23 | AdmittedR cụm18–20 /21–23 | N admitted 18–20 /21–23 | Năm dương SYM |
|---|---|---|---|---|---|
| T01 | XAUUSD `F4:hour=15:impulse=1:timing=MONTH:multiple=1` 48H | +7.15 / +7.16 | +5.64 / +7.16 | 30 / 53 | 3 |
| T02 | XAUUSD `F4:hour=15:impulse=0.5:timing=MONTH:multiple=1` 48H | +5.65 / +5.79 | +8.59 / +5.79 | 57 / 92 | 3 |
| T03 | XAUUSD `F4:hour=15:impulse=1:timing=WEEK:multiple=1` 24H | +5.63 / +5.51 | +17.58 / +5.51 | 65 / 104 | 2 |
| T04 | XAUUSD `F4:hour=15:impulse=1:timing=MONTH:multiple=2` 48H | +3.66 / +3.63 | +3.66 / +3.63 | 42 / 53 | 3 |
| T05 | XAUUSD `F4:hour=15:impulse=1:timing=MONTH:multiple=1` DAY | +3.49 / +4.93 | +3.28 / +4.93 | 30 / 53 | 5 |
| T06 | XAUUSD `F3:compression=BB:n=60:quantile=0.1:multiple=1` FRIDAY | +9.06 / +3.44 | +7.13 / +3.44 | 26 / 37 | 4 |
| T07 | XAUUSD `F4:hour=15:impulse=1:timing=MONTH:multiple=1` 24H | +5.25 / +2.88 | +5.80 / +2.88 | 30 / 53 | 3 |
| T08 | XAUUSD `F4:hour=15:impulse=0.5:timing=MONTH:multiple=2` 48H | +2.85 / +2.85 | +2.85 / +2.85 | 76 / 92 | 3 |
| T09 | XAUUSD `F3:compression=BB:n=120:quantile=0.1:multiple=1` 24H | +6.10 / +2.83 | +1.51 / +2.83 | 22 / 38 | 4 |
| T10 | XAUUSD `F4:hour=15:impulse=1:timing=WEEK:multiple=2` 24H | +2.73 / +2.78 | +2.73 / +2.78 | 85 / 104 | 2 |
| T11 | XAUUSD `F3:compression=BB:n=60:quantile=0.1:multiple=2` FRIDAY | +4.67 / +1.88 | +4.67 / +1.88 | 37 / 37 | 4 |
| T12 | XAUUSD `F3:compression=BB:n=60:quantile=0.1:multiple=1` 24H | +4.64 / +1.86 | +2.52 / +1.86 | 26 / 37 | 5 |
| T13 | XAUUSD `F4:hour=15:impulse=1:timing=MONTH:multiple=2` DAY | +1.79 / +2.46 | +1.79 / +2.46 | 42 / 53 | 5 |
| T14 | XAUUSD `F3:compression=BB:n=120:quantile=0.1:multiple=2` 24H | +3.22 / +1.51 | +3.22 / +1.51 | 36 / 38 | 4 |
| T15 | XAUUSD `F3:compression=BB:n=60:quantile=0.15:multiple=1` 24H | +6.65 / +1.47 | +5.06 / +1.47 | 34 / 52 | 4 |

NetR ở đây là endpoint move sau phí chia naturalSL, chưa đặt SL chạy thật.
244.264 raw occurrences là tổng cell-records;4 horizons và recipes có trùng tín hiệu,
không phải244.264 lệnh độc lập. Các cột raw giữ cả tín hiệu trước cost filter.

### Top 15: netR SYM từng năm và lý do dừng

| ID | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | Lý do |
|---|---|---|---|---|---|---|---|
| T01 | -10.93 | +13.48 | +4.60 | -2.62 | -7.20 | +16.98 | 2018:CADENCE, 2021:CADENCE, SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T02 | -13.73 | +9.83 | +9.54 | -6.72 | -11.21 | +23.73 | 2018:CADENCE, SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T03 | -14.06 | -1.23 | +20.92 | -7.06 | -1.42 | +13.99 | SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T04 | -5.54 | +6.89 | +2.31 | -1.33 | -3.62 | +8.58 | 2018:CADENCE, 2021:CADENCE, SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T05 | -5.66 | +5.55 | +3.60 | +0.07 | +1.54 | +3.32 | 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T06 | +1.36 | -7.37 | +15.07 | +1.16 | -16.42 | +18.70 | 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T07 | -12.60 | +9.01 | +8.83 | -2.85 | -6.98 | +12.71 | 2018:CADENCE, 2021:CADENCE, SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T08 | -7.01 | +5.05 | +4.80 | -3.39 | -5.71 | +11.95 | SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T09 | +2.33 | +7.37 | -3.60 | +5.23 | -6.41 | +4.01 | 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T10 | -7.17 | -0.62 | +10.52 | -3.61 | -0.71 | +7.10 | SYM:FEWER_THAN_4_POSITIVE_YEARS, ASYM:FEWER_THAN_4_POSITIVE_YEARS, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T11 | +0.73 | -3.74 | +7.69 | +0.60 | -8.27 | +9.56 | 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T12 | +0.62 | +3.52 | +0.50 | +5.52 | -10.44 | +6.78 | 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T13 | -2.84 | +2.82 | +1.81 | +0.02 | +0.76 | +1.67 | 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T14 | +1.21 | +3.81 | -1.79 | +2.61 | -3.17 | +2.07 | 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |
| T15 | -4.72 | +7.64 | +3.73 | +1.21 | -5.84 | +6.10 | 2018:CADENCE, 2021:CADENCE, HOLM_MULTIPLE_TESTING, DEFLATED_SHARPE_PROXY |

Toàn bộ 544 ô có Holm p=1; DSRproxy lớn nhất chỉ 0.01225. t-stat lớn nhất=0.899.
Không cấu hình nào đã qua toàn cổng kinh tế trước thống kê; không thể đổ kết quả 0
chỉ cho việc Holm bảo thủ. Counts lý do có chồng lấn, không cộng thành tổng 544.

| Lý do | Số ô |
|---|---|
| HOLM_MULTIPLE_TESTING | 544 |
| DEFLATED_SHARPE_PROXY | 544 |
| SYM:FEWER_THAN_4_POSITIVE_YEARS | 521 |
| ASYM:FEWER_THAN_4_POSITIVE_YEARS | 511 |
| 2018:SYM:CLUSTER_ECONOMIC | 482 |
| 2018:ASYM:CLUSTER_ECONOMIC | 475 |
| 2021:SYM:CLUSTER_ECONOMIC | 475 |
| 2021:ASYM:CLUSTER_ECONOMIC | 458 |
| 2018:CADENCE | 120 |
| 2021:CADENCE | 120 |
| 2018:ENDPOINT | 58 |
| 2021:ENDPOINT | 52 |
| 2018:RETENTION | 31 |
| 2018:SCALE | 16 |

Giá Ask là proxy (Gold0,338USD/oz; EUR1pip), swap là scenarios (GoldSYM−40/−40,
ASYM−45/−5USD/lot; EUR−40USD/lot hai chiều). Không phải lịch sử phí FTMO đã chứng nhận.
Không SL-active, grid lots, concurrency hoặc floating equity; không suy ra Worst Daily Loss
từ bảng endpoint. Mọi2018–2026 đã exposed trước đây; validation sau này chỉ là reused historical.

## 4. Challenge và payout 9 năm

Không có composition đủ điều kiện nên lượt này không có con số pass, payout hay drawdown
của danh mục V10. N/A khác tỷ lệ pass 0%. Không mượn danh mục V8 để điền thành tích V10.

| Năm | Stage0 | Stage1 /danh mục | Challenge /payout |
|---|---|---|---|
| 2018 | DEVELOPMENT_MEASURED | N/A — failed Stage0 | N/A — không chạy |
| 2019 | DEVELOPMENT_MEASURED | N/A — failed Stage0 | N/A — không chạy |
| 2020 | DEVELOPMENT_MEASURED | N/A — failed Stage0 | N/A — không chạy |
| 2021 | DEVELOPMENT_MEASURED | N/A — failed Stage0 | N/A — không chạy |
| 2022 | DEVELOPMENT_MEASURED | N/A — failed Stage0 | N/A — không chạy |
| 2023 | DEVELOPMENT_MEASURED | N/A — failed Stage0 | N/A — không chạy |
| 2024 | NOT_OPENED_IN_V10 | N/A — failed Stage0 | N/A — không chạy |
| 2025 | NOT_OPENED_IN_V10 | N/A — failed Stage0 | N/A — không chạy |
| 2026 | NOT_OPENED_IN_V10 | N/A — failed Stage0 | N/A — không chạy |

Khuyến nghị: chốt No-Go lô 544 ô này, giữ scanner và source đã kiểm. Chưa tăng risk
hoặc mua Challenge. Một chiến dịch tiếp theo cần cơ chế kinh tế khác và budget đăng ký
mới, hoặc source/cost admission cho tài sản còn thiếu; không nới gate để cứu Top 15.

### Hậu kiểm kỹ thuật và bàn giao

| Mặt | Kết quả /quyết định |
|---|---|
| Correctness | Sửa backward DAY, post-Friday entry và cluster aggregation; giữ original attempts. |
| Reliability | Event cuối không crash; regression và receipts; không tự rerun một financial job đã lưu. |
| Performance | Timing-mask cache giữ output;2 process giữ đủ IDs; smoke cho vòng phát triển. |
| Storage | Xóa generated dependencies đã đóng; E dry-run, giữ private research và VI WIP. |
| Method | Không thêm grid sau outcome, không mở validation cho nhánh fail. |

Không cần sửa skill/AGENTS: đây là lỗi engine và bằng chứng performance, đã đặt regression/runbook
ở đúng owner; không tạo một lớp instruction trùng lặp. Không broker/runtime promotion/Astra/paid provider.

Private job: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\enterprise-alpha-v10-20261115`. JSON có Top 15/annual/cluster/top-partitions/artifact SHA256.
PR được giao với 3 CI đúng HEAD rồi dừng, không tự merge. Chi tiết terminal failures và
các technical attempts vẫn có trong private job; không thay seal để làm đẹp.
