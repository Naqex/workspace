# V16 — Đóng trong ngày, quét đa tài sản và kiểm lại chứng cứ

**Chưa có nâng cấp đủ điều kiện Challenge.** Không có nhánh bổ sung qua đủ cổng trong 715 cấu hình.
Đóng A trước 20:30 UTC vẫn còn **32 đường giá chưa đủ**, mô phỏng chính hoàn tất **71/105**, strict **1/105**.
Không đạt mục tiêu zero gap hoặc trung vị <18–24 tháng. Không promote G2 chỉ vì số gap giảm.

PR #94 đã merge `1c6e516`; nhánh V15 đã xóa. Bám bản sáu track hoàn chỉnh cuối attachment, không mở thêm grid MAE-stop/Day1 từ đoạn draft bị ngắt. PR #95 giữ mở để review.

[JSON số liệu](GAP-IMMUNE-MULTIASSET-V16-RESULTS-20261116.json) ·
[Protocol](GAP-IMMUNE-MULTIASSET-V16-PROTOCOL-20261116.md) ·
[Freeze](GAP-IMMUNE-MULTIASSET-V16-FREEZE-20261116.json).
Khóa code/selection tại `985df06` trước khi đo chính sách mới trên 2024–2026.

## 1. Gap nào đã chứng minh được, gap nào còn thiếu?

V15 có **133 lượt trade–gap**: 95 model-low-risk và 38 loại trừ SL có điều kiện bằng native envelope. Đây không phải 95 lệnh độc lập. Strict cũ đổi 56 lệnh, không phải gán 95 lệnh thua đúng -1R.

38 trường hợp đều là EURUSD và có **0 tick ghi trong phút thiếu**. Có quote trước/sau, jump nhỏ hoặc SL xa không chứng minh feed liên tục hay sổ lệnh toàn thị trường. Không tự điền 38 nến M1 phẳng; **0 nến mới được admission**.

| Nhóm V15 | Lượt gap | Asset | Flat morphology |
|---|---|---|---|
| SOURCE_ENVELOPE_EXCLUDES_SL | 38 | {'EURUSD': 38} | 34 |
| MODEL_LOW_RISK | 95 | {'XAUUSD': 85, 'EURUSD': 10} | 81 |

Trong 95 lượt model: 81 gap dài 1 phút, 7 dài 2 phút, 2 dài 3 phút,
1 dài 5 phút, 3 dài 61 phút và 1 dài 62 phút. 61 lượt bắt đầu trong
21:00–23:59 UTC; 20 lượt khác ở 20:00–20:59 UTC. **81/95** đạt hình thái
jump ≤1,5 spread, gap 1–5 phút, SL cách >10 spread; đây chỉ là hình thái
rủi ro thấp, không xác minh nguyên nhân gap hay tính liên tục của feed.
Phân bố asset/năm/giờ đầy đủ ở `source_groups` của JSON và danh tính từng
lượt trong private `gap-identities.json`.

Census hai project roots D/E: 1,103,898 files; 64,209 candidates; 168 ZIP khớp; 256 lỗi giữ nguyên. Không phải quét tuyệt đối toàn ổ D/E. Các archive/format chưa giải mã và đường dẫn không đọc được vẫn unknown.
Đọc 122 CSV, thêm 62 tick fixtures khớp giờ/ngày: không thấy quote mới trong khoảng thiếu. Các view B0 theo phiên không được coi là tick trọn ngày. H1/H4 gộp lại từ cùng M1 thiếu không trở thành nguồn containment độc lập.

G2 chỉ dùng đồng hồ/lịch đã biết trước: đóng cùng ngày 20:30 UTC hoặc holiday sớm hơn; US500 thêm mốc 16:00 New York theo DST. Fill là quote quan sát đầu tiên tại/sau yêu cầu; không đóng hồi tố ở quote trước một outage chưa biết.

| Scope / order / mode | Tín hiệu | Uncertain còn giữ | Qua đêm | Bar stress giả |
|---|---|---|---|---|
| Dev / OLHC / PRIMARY | 340 | 25 | 0 | 0 |
| Dev / OLHC / STRICT | 340 | 25 | 0 | 43 |
| Dev / OHLC / PRIMARY | 340 | 25 | 0 | 0 |
| Dev / OHLC / STRICT | 340 | 25 | 0 | 43 |
| Full / OLHC / PRIMARY | 494 | 32 | 0 | 0 |
| Full / OLHC / STRICT | 494 | 32 | 0 | 55 |
| Full / OHLC / PRIMARY | 494 | 32 | 0 | 0 |
| Full / OHLC / STRICT | 494 | 32 | 0 | 55 |

Strict chèn excursion giả định chung cho các vị thế trên cùng asset/time, giữ toàn bộ observed bars và nhãn bất định gốc. Đây là sensitivity, không phải dữ liệu khôi phục hay biên dưới toán học. Uncertainty bằng 0 sau chèn không được dùng làm chứng nhận nguồn.

## 2. Vì sao chưa có đội hình nhanh hơn?

A giữ nguyên ba cơ chế, entry, SL/P1 và risk V15 factor 1,5 + cushion; chỉ đổi hạn thoát G2. Ngân sách DAY cũ 722 cells, bỏ 7 bản cùng asset+recipe A trước outcome, còn **715**. Không tạo tín hiệu, giờ giao dịch hoặc weight mới sau kết quả.

| Asset | Cells | Trạng thái |
|---|---|---|
| XAUUSD | 198 | {'STAGE0_ECONOMIC_OR_SCALE_FAIL': 180, 'REJECTED': 18} |
| EURUSD | 103 | {'STAGE0_ECONOMIC_OR_SCALE_FAIL': 92, 'REJECTED': 11} |
| US500 | 202 | {'STAGE0_ECONOMIC_OR_SCALE_FAIL': 202} |
| GBPUSD | 106 | {'DATA_PATH_INCOMPLETE': 106} |
| AUDUSD | 106 | {'DATA_PATH_INCOMPLETE': 106} |

Gold 18 và EURUSD 11 cells qua endpoint screen đều còn path gap; các lý do kinh tế, cadence và correlation theo từng cell nằm trong JSON/private job. US500 202 cells không qua Stage-0 economics/scale trên nguồn quarterly đã sửa; không gọi nguồn M1 này là đủ chỉ vì có loader. GBP/AUD có H1 sáu năm nhưng tick fixtures rời rạc, không dựng M1 giả. Vì vậy additions khóa **rỗng**.

Riêng US500, 185/202 cells qua cổng scale/retention nhưng **0/202 dương
cả hai cụm Development sau phí đã đăng ký**. Vì vậy không thể quy thất bại
chỉ cho thiếu dữ liệu hay bug cent cũ. Trong các cell đã đi tới SL-active,
16/18 Gold và 11/11 EUR thiếu ngưỡng trung bình 40 lệnh/năm; các lý do loại
có thể chồng lên nhau. Không kết luận mọi chiến lược trên các tài sản này
đều không có edge.

Attribution V15 theo nhánh (R của tín hiệu, chưa phải % tài khoản):

- S1 `EURUSD|F5:tf=H4:n=5:adx=25:buffer=0.1|DAY|P0`: Development +25.4908R; 2024–2026 +11.5134R.
- S2 `XAUUSD|F3:compression=BB:n=60:quantile=0.1:multiple=1|48H|P0`: Development +12.0342R; 2024–2026 +0.6024R.
- S3 `XAUUSD|F4:hour=15:impulse=1:timing=MONTH:multiple=1|24H|P1`: Development +12.7070R; 2024–2026 +1.7768R.
- S4 `EURUSD|F3:compression=NR:n=14:multiple=1|DAY|P1`: Development +2.1861R; 2024–2026 -6.6087R.
- S5 `XAUUSD|F3:compression=NR:n=14:multiple=2|48H|P0`: Development -4.5209R; 2024–2026 -1.1060R.

S4/S5 là hai nhánh B bổ sung trong V14; giữ riêng làm attribution, không chọn lại chiều/weights để cứu kết quả. Tổng A ở 2024–2026 chỉ +13,8926R; B thêm hai nhánh làm tổng giảm còn +6,1779R. Đó là đóng góp lịch sử đã exposed, không chứng minh nguyên nhân theo regime.

| A sleeve / năm | Lệnh | Net SYM R | SL trung vị | 150 USD: risk dùng % | Actual standalone: risk dùng % |
|---|---|---|---|---|---|
| S1 / 2018 | 34 | +13.997 | 0.00333 | 99.08 | 99.38 |
| S1 / 2019 | 25 | -4.532 | 0.0021 | 99.59 | 99.33 |
| S1 / 2020 | 32 | -2.503 | 0.00337 | 98.89 | 99.06 |
| S1 / 2021 | 27 | +1.731 | 0.00367 | 99.12 | 99.33 |
| S1 / 2022 | 36 | +1.801 | 0.00365 | 98.61 | 99.25 |
| S1 / 2023 | 40 | +14.996 | 0.00278 | 99.0 | 99.2 |
| S1 / 2024 | 26 | +12.570 | 0.00339 | 98.5 | 99.24 |
| S1 / 2025 | 27 | +2.578 | 0.00293 | 99.12 | 99.3 |
| S1 / 2026 | 19 | -3.635 | 0.00269 | 99.61 | 99.2 |
| S2 / 2018 | 3 | -1.439 | 5.335 | 99.35 | 98.75 |
| S2 / 2019 | 10 | -2.741 | 8.0955 | 97.87 | 97.87 |
| S2 / 2020 | 13 | +6.767 | 10.146 | 96.1 | 97.56 |
| S2 / 2021 | 10 | +1.277 | 8.513 | 98.34 | 97.68 |
| S2 / 2022 | 12 | -6.173 | 9.0965 | 98.03 | 98.26 |
| S2 / 2023 | 15 | +14.345 | 9.317 | 98.38 | 98.04 |
| S2 / 2024 | 17 | +0.239 | 11.261 | 96.57 | 97.22 |
| S2 / 2025 | 11 | -3.992 | 19.287 | 94.41 | 93.8 |
| S2 / 2026 | 12 | +4.355 | 36.514 | 85.31 | 86.62 |
| S3 / 2018 | 6 | -3.257 | 5.4105 | 98.34 | 98.2 |
| S3 / 2019 | 12 | +3.908 | 5.6595 | 98.72 | 98.06 |
| S3 / 2020 | 12 | +9.702 | 10.2385 | 98.07 | 97.41 |
| S3 / 2021 | 14 | -0.382 | 9.6285 | 97.47 | 97.26 |
| S3 / 2022 | 18 | -5.121 | 9.49 | 96.35 | 98.15 |
| S3 / 2023 | 21 | +7.857 | 8.727 | 96.22 | 97.79 |
| S3 / 2024 | 22 | -7.296 | 12.3095 | 96.08 | 96.4 |
| S3 / 2025 | 13 | -0.620 | 17.269 | 91.53 | 93.77 |
| S3 / 2026 | 7 | +9.692 | 42.288 | 84.58 | 90.21 |

Gold SL đơn vị USD/oz; EURUSD SL đơn vị USD/EUR (nhân 10.000 thành pips). Giá Gold tăng riêng lẻ không làm lot giảm nếu khoảng SL giữ nguyên. Lot floor phụ thuộc risk USD / khoảng SL / contract và bước 0,01 lot. JSON có số lượt bị floor và cả reference 150 USD lẫn lot thực của standalone; không gộp tài khoản chồng lấn thành số trade độc lập.

## 3. Bốn cột 105 cửa sổ và payout mô phỏng

V16_MULTI = A G2 vì không có sleeve đủ chuẩn. Cột 2 và 4 dùng cùng ledger strict có hash; không chạy lặp một portfolio giống hệt để tạo cảm giác có thêm chiến lược. Cột 1 reuse ledger V15 CUSHION nguyên vẹn. 66/72 starts cũ hoàn tất nhờ dùng giá đến 13/10/2026, không phải hoàn tất toàn bộ trong Development.

| Order/phí | Cột | P1/105 | Cả 2/105 | Cả 2 recent/33 | Median tháng | Daily % | Static % | Breach |
|---|---|---|---|---|---|---|---|---|
| OLHC/SYM | V15_BASELINE | 78 | 66 | 0 | 34.85 | 2.3672 | 8.131 | 0 |
| OLHC/SYM | V16_A_STRICT | 18 | 1 | 0 | 18.95 | 1.9628 | 8.3997 | 0 |
| OLHC/SYM | V16_MULTI_PRIMARY | 81 | 71 | 0 | 47.08 | 1.963 | 6.3825 | 0 |
| OLHC/SYM | V16_MULTI_STRICT | 18 | 1 | 0 | 18.95 | 1.9628 | 8.3997 | 0 |
| OLHC/ASYM | V15_BASELINE | 78 | 67 | 0 | 33.05 | 2.3659 | 8.054 | 0 |
| OLHC/ASYM | V16_A_STRICT | 18 | 1 | 0 | 18.95 | 1.9628 | 8.3997 | 0 |
| OLHC/ASYM | V16_MULTI_PRIMARY | 81 | 71 | 0 | 47.08 | 1.963 | 6.3825 | 0 |
| OLHC/ASYM | V16_MULTI_STRICT | 18 | 1 | 0 | 18.95 | 1.9628 | 8.3997 | 0 |
| OHLC/SYM | V15_BASELINE | 78 | 66 | 0 | 34.85 | 2.3672 | 8.131 | 0 |
| OHLC/SYM | V16_A_STRICT | 18 | 1 | 0 | 18.95 | 1.9628 | 8.3997 | 0 |
| OHLC/SYM | V16_MULTI_PRIMARY | 81 | 71 | 0 | 47.08 | 1.963 | 6.3825 | 0 |
| OHLC/SYM | V16_MULTI_STRICT | 18 | 1 | 0 | 18.95 | 1.9628 | 8.3997 | 0 |
| OHLC/ASYM | V15_BASELINE | 78 | 67 | 0 | 33.05 | 2.3659 | 8.054 | 0 |
| OHLC/ASYM | V16_A_STRICT | 18 | 1 | 0 | 18.95 | 1.9628 | 8.3997 | 0 |
| OHLC/ASYM | V16_MULTI_PRIMARY | 81 | 71 | 0 | 47.08 | 1.963 | 6.3825 | 0 |
| OHLC/ASYM | V16_MULTI_STRICT | 18 | 1 | 0 | 18.95 | 1.9628 | 8.3997 | 0 |

Median chỉ tính cửa sổ hoàn tất; chưa hoàn tất vẫn censored và có mặt trong mẫu. 2026 là YTD đến 13/10. Cửa sổ gần có ít thời gian hơn, tỷ lệ này không phải xác suất pass độc lập.

Strict 18,95 tháng chỉ đến từ **một start tháng 02/2023**; không diễn giải
1/105 thành đạt mục tiêu tốc độ cho hệ thống. Với 66 starts mà cả V15 và G2
primary đều hoàn tất, trung vị chênh lệch thời gian G2 − V15 là **+9,15 tháng**
(chi tiết từng start trong `paired-completers.json`). So sánh cùng start
giúp tránh chỉ nhìn hai median với tập người hoàn tất khác nhau.
Hai chế độ phí G2 bằng nhau vì không qua rollover và không dùng limit TP.

| Order/phí | Cột | Post-challenge count | Post-challenge USD (chồng lấn) | Standalone count | Standalone USD |
|---|---|---|---|---|---|
| OLHC/SYM | V15_BASELINE | 836 | 157249.14 | 42 | 8834.15 |
| OLHC/SYM | V16_A_STRICT | 2 | 132.61 | 11 | 1824.95 |
| OLHC/SYM | V16_MULTI_PRIMARY | 608 | 68232.22 | 40 | 6457.11 |
| OLHC/SYM | V16_MULTI_STRICT | 2 | 132.61 | 11 | 1824.95 |
| OLHC/ASYM | V15_BASELINE | 923 | 196514.91 | 42 | 9422.51 |
| OLHC/ASYM | V16_A_STRICT | 2 | 132.61 | 11 | 1824.95 |
| OLHC/ASYM | V16_MULTI_PRIMARY | 608 | 68232.22 | 40 | 6457.11 |
| OLHC/ASYM | V16_MULTI_STRICT | 2 | 132.61 | 11 | 1824.95 |
| OHLC/SYM | V15_BASELINE | 836 | 157249.14 | 42 | 8834.15 |
| OHLC/SYM | V16_A_STRICT | 2 | 132.61 | 11 | 1824.95 |
| OHLC/SYM | V16_MULTI_PRIMARY | 608 | 68232.22 | 40 | 6457.11 |
| OHLC/SYM | V16_MULTI_STRICT | 2 | 132.61 | 11 | 1824.95 |
| OHLC/ASYM | V15_BASELINE | 923 | 196514.91 | 42 | 9422.51 |
| OHLC/ASYM | V16_A_STRICT | 2 | 132.61 | 11 | 1824.95 |
| OHLC/ASYM | V16_MULTI_PRIMARY | 608 | 68232.22 | 40 | 6457.11 |
| OHLC/ASYM | V16_MULTI_STRICT | 2 | 132.61 | 11 | 1824.95 |

Các khoản payout là số mô phỏng trước phí challenge/retry/vận hành. Không cộng các starts chồng lấn thành thu nhập, không phải tiền đã rút thật. Không suy risk thấp một đoạn lịch sử thành an toàn chắc chắn của FTMO.

## 4. Kiểm toán, hiệu năng, lưu trữ và bước tiếp

Auditor riêng kiểm **85,387 endpoint cash calculations**, **7,624 đường scanner** qua hai ordering. Thêm **3,336 A paths** và **1,432 account ledgers** mới. Cùng implementer/feed; độc lập phép tính và scalar traversal, không phải reviewer/người hay nguồn giá độc lập.

Audit tìm 2 Gold DAY/P1 levels lệch 0,001 USD/oz do thiếu kiểm ô giá liền trước sau commission rounding. Sửa cùng cơ chế đã dùng cho US500; giữ failed audit và chạy lại đủ 29 SL-active cells. Activation, exit, cash và active protection của mọi A path không đổi; một unused level của A được ghi riêng, không bị coi là lệnh đã thay đổi. Không chọn lại subset từ lỗi này.

| Phép đo | Trước | Sau |
|---|---|---|
| Full four-runtime wall (giây) | 34.015 | 28.226 |
| Tests / giữ IDs cũ | 1126 | 1138 / 1126 |
| Base shard walls | [15.332074099977035, 25.755292199959513] | [20.29119710001396, 20.136282099992968] |

Giảm wall 17.0% trên phép đo này; dùng profile thật để cân hai shard của runner đã có, giữ process isolation, tất cả test IDs và 0 skip. Không thêm cache fixture dùng chung chỉ để tiết kiệm vài giây. Bản sau có các test V16 bổ sung, không gọi đó là benchmark cohort hoàn toàn giống nhau. Top15 timings giữ trong JSON.

Smoke 10 fresh processes, đủ 78 tests/lượt: median/max wall 0.733/0.758s; 10/10 <0,80s: **True**. Giữ mọi mẫu và outlier.


Inventory 3764 log/stdout D/E (96,721,725 bytes). Nén 8 console logs của các job đóng, 53,155,811 bytes → 2,657,786 bytes; giảm logic 50,498,025 bytes trước receipts. Đã extract và SHA từng member trước xóa bản gốc; mỗi đường cũ có `.v16-cold.json` chỉ archive/member/hash. Không xóa raw/tick/M1/column store/freeze/ledger/path hay package; không lặp purge V14/V15. Không claim dung lượng vật lý đã giải phóng.

Luồng dữ liệu: nguồn V14 giữ nguyên → A entry/SL tape cố định → clock G2 được đăng ký → hai đường M1 ordering + shared-gap stress → engine account cũ → scalar/Decimal audit → freeze commit trước đo chính sách mới trên giá 2024–2026. Scanner DAY dùng riêng Dev 2018–2023.

**Khuyến nghị:** giữ V15 làm baseline nghiên cứu, gác G2 và không tăng risk/chọn thêm biến thể để đạt chỉ tiêu. Nút thắt còn lại là tín hiệu có R-velocity đủ cao trên đường giá kiểm được, không phải thiếu engine hoặc cần nới chuẩn. Một chiến dịch mới cần cơ chế/nguồn dữ liệu mới có lý do rõ và budget riêng; các failed attempts hiện tại giữ nguyên.

Hậu kiểm: không biến quote absence thành continuity; dùng lịch biết trước, không hindsight outage exits; sửa lỗi arithmetic bằng regression rồi đối soát delta; reuse ledger chỉ sau parity; nén log có restore proof trước thay vì xóa nguồn. Không cần thêm skill trùng với source-transformations/qualification/evidence-continuity đang có.

Private evidence `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\gap-immune-and-multiasset-v16-20261116`; JSON báo cáo <1 MiB. PR #95 giữ mở, 3 checks trên đúng HEAD và CI quant IDs được đối soát bằng artifact tải về, receipt `ci-exact-head-reconciliation.json` ghi sau push. Không sửa HEAD chỉ để tự nhét hash CI vào cùng commit.

VI Dubber WIP và Trader pin giữ nguyên. Không broker, deploy, provider download, Astra hay memory update; chưa owner handover/shadow/demo/target-account execution validation.
