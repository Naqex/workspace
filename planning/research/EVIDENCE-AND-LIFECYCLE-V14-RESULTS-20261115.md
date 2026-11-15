# V14 — Bằng chứng gốc, A/B và vòng đời tài khoản 2018–2026

**Chưa nên mua Challenge.** A có lợi nhuận tổng Validation tốt hơn B, nhưng thời gian pass còn quá dài
và phụ thuộc giả định dữ liệu: A/SYM pass 48/105 cửa sổ,
trung vị 54.0 tháng; CLEAN_COHORT chỉ
0/105. Không coi cổng tần suất đạt là cổng time-fit đạt.
Standalone Funded giả định được cấp sẵn vốn, không phải chứng minh có thể thi quỹ nhanh hoặc có thu nhập chính ổn định.

PR #92 đã merge `65bf0c2`; A/B và mã tính khóa tại `ae575b7` trước khi mở giá 2024–2026.
Giữ nguyên ba nhánh A và thêm đúng hai nhánh độc lập theo thứ tự đã đăng ký cho B; không tìm subset/weights mới.
Toàn bộ kết quả dưới đây là mô phỏng offline, chưa đủ chứng nhận Challenge hoặc payout thực.

## 1. Bằng chứng M1/tick và tổ hợp Development

A: 340 tín hiệu, **44** đường đi qua **111** gap chưa xác minh. Danh sách timestamp đầy đủ trong JSON báo cáo và `path-evidence.json`.
Đã quét metadata 1.104.021 file D/E; 46.675 file có dấu hiệu nguồn phù hợp, 158 ZIP khớp. 256 lỗi được giữ
(253 FileNotFound, 2 VI PermissionError, 1 BadZipFile). Không coi những định dạng/archive chưa giải mã là đã tìm hết.
Tìm được 106 tick gốc trong phút EURUSD 16/11/2020 10:23 UTC: bổ sung 1 M1 vào MarketDataStore phiên bản mới.
Gold thêm 0 thanh; probe cả CSV Date/Time tách cột. Không lấp gap bằng giá giả, không thay input V1–V13.
EUR 2024–2026 ban đầu hết 07/10/2026; đã nối đúng 5.723 phút sau đó từ M1 dựng bằng tick native QDM đã có hash ở V6, đến hết 13/10.
Giữ Ask proxy Gold 0,338 USD/oz và EUR 1 pip; không gọi toàn bộ nguồn là bid/ask tick thực.

Ba nhánh gốc (BUY và SELL, không chọn lại chiều sau kết quả):

| Nhánh | Định danh | Horizon / Mode | SYM 2018→2023 |
|---|---|---|---|
| 1 | EURUSD\|F5:tf=H4:n=5:adx=25:buffer=0.1\|DAY\|P0 | DAY / P0 | +14.00 / -4.53 / -2.50 / +1.73 / +1.80 / +15.00 |
| 2 | XAUUSD\|F3:compression=BB:n=60:quantile=0.1:multiple=1\|48H\|P0 | 48H / P0 | -1.44 / -2.74 / +6.77 / +1.28 / -6.17 / +14.34 |
| 3 | XAUUSD\|F4:hour=15:impulse=1:timing=MONTH:multiple=1\|24H\|P1 | 24H / P1 | -3.26 / +3.91 / +9.70 / -0.38 / -5.12 / +7.86 |

F3 BB = breakout nén Bollinger; F4 = impulse theo lịch tháng; EUR F5 = rejection đã đăng ký ở H4.
P0 giữ SL gốc, P1 chỉ nâng stop bảo vệ sau khi đủ ngưỡng; không mở biến thể mới.
B thêm EUR F3 NR14/multiple1/DAY/P1 và Gold F3 NR14/multiple2/48H/P0.

| Dev | Lệnh/năm 2018→2023 | Trung bình | SYM tổng / bỏ năm tốt nhất |
|---|---|---|---|
| A | 43 / 47 / 57 / 51 / 66 / 76 | 56.67 | +50.23 / +13.03R |
| B | 83 / 86 / 91 / 85 / 100 / 107 | 92.00 | +47.90 / +11.10R |

Cổng trung bình >=50/năm là thay đổi được owner duyệt cho V14; không sửa lại verdict V13.
B có nhiều lệnh hơn nhưng tổng Dev SYM thấp hơn A; không mặc định nhiều nhánh tốt hơn.

## 2. Chín năm và Challenge/Funded

Bảng chính: NEXT_QUOTE, thứ tự M1 O–L–H–C. Net R đơn vị cộng theo năm phát tín hiệu, trước lot floor thực tế;
DD và lỗ ngày/static lấy từ sổ tham chiếu riêng từng năm risk 150 USD, lot thực tế. Có exposure qua giao năm
nên Net R đơn vị và PnL cash của sổ năm không đồng nhất; toàn bộ cột đối soát nằm trong JSON.
2026 là YTD đến hết 13/10, không phải cả năm. Dữ liệu 2024–2026 đã từng có exposure lịch sử, không gọi pristine OOS.

| Ứng viên | Năm | N (BUY/SELL) | Net R SYM/ASYM | Mean SYM | R-DD sổ | Daily/static % SYM |
|---|---|---|---|---|---|---|
| A | 2018 | 43 (17/26) | +9.30 / +9.21 | +0.216 | 7.28 | 0.645 / 0.845 |
| A | 2019 | 47 (27/20) | -3.37 / -3.14 | -0.072 | 7.72 | 0.345 / 1.111 |
| A | 2020 | 57 (26/31) | +13.97 / +14.37 | +0.245 | 5.85 | 0.639 / 0.392 |
| A | 2021 | 51 (34/17) | +2.63 / +2.86 | +0.051 | 10.56 | 0.436 / 0.381 |
| A | 2022 | 66 (35/31) | -9.49 / -9.06 | -0.144 | 13.07 | 0.629 / 2.822 |
| A | 2023 | 76 (42/34) | +37.20 / +38.15 | +0.489 | 7.38 | 0.668 / 0.627 |
| A | 2024 | 65 (31/34) | +5.51 / +6.12 | +0.085 | 8.35 | 0.639 / 0.981 |
| A | 2025 | 51 (22/29) | -2.03 / -1.95 | -0.040 | 12.75 | 0.585 / 3.570 |
| A | 2026 | 38 (18/20) | +10.41 / +10.49 | +0.274 | 5.74 | 0.378 / 0.290 |
| B | 2018 | 83 (37/46) | +9.75 / +10.05 | +0.117 | 11.98 | 0.647 / 1.584 |
| B | 2019 | 86 (41/45) | -16.65 / -15.60 | -0.194 | 21.33 | 0.755 / 4.861 |
| B | 2020 | 91 (45/46) | +20.96 / +21.84 | +0.230 | 7.96 | 0.943 / 0.946 |
| B | 2021 | 85 (50/35) | -1.40 / -0.88 | -0.017 | 11.46 | 0.628 / 1.083 |
| B | 2022 | 100 (52/48) | -1.55 / -0.69 | -0.016 | 9.85 | 0.629 / 1.344 |
| B | 2023 | 107 (62/45) | +36.80 / +38.08 | +0.344 | 9.99 | 0.668 / 0.627 |
| B | 2024 | 102 (55/47) | +2.40 / +3.30 | +0.024 | 11.34 | 0.961 / 1.384 |
| B | 2025 | 78 (40/38) | -2.71 / -2.60 | -0.035 | 16.08 | 0.585 / 4.163 |
| B | 2026 | 74 (33/41) | +6.49 / +6.61 | +0.088 | 7.56 | 0.532 / 0.150 |

So sánh toàn bộ 16 tổ hợp mô hình (CLEAN_COHORT dùng thông tin đường giá tương lai để loại lệnh,
**chỉ là sensitivity sau thực tế, không phải bộ lọc có thể chạy live**; cả hai thứ tự M1 đều không phải biên toán học):

| A/B | Order / view / phí | R 2024–26 | Dương / 3 năm | P1 / 105 | Cả 2 / 105 | Funded paths có trade | Median tháng | Standalone payout USD / số lần |
|---|---|---|---|---|---|---|---|---|
| A | OLHC / NEXT_QUOTE / SYM | +13.89 | 2 | 67 | 48 | 7 | 54.0 | 6131.27 / 40 |
| A | OLHC / NEXT_QUOTE / ASYM | +14.65 | 2 | 69 | 56 | 6 | 55.4 | 6401.71 / 41 |
| A | OLHC / CLEAN_COHORT / SYM | +4.30 | 2 | 46 | 0 | 0 | N/A | 3827.81 / 27 |
| A | OLHC / CLEAN_COHORT / ASYM | +5.03 | 2 | 46 | 9 | 1 | 59.7 | 3910.83 / 27 |
| B | OLHC / NEXT_QUOTE / SYM | +6.18 | 2 | 64 | 48 | 9 | 51.4 | 5364.37 / 30 |
| B | OLHC / NEXT_QUOTE / ASYM | +7.31 | 2 | 64 | 54 | 10 | 40.0 | 6022.52 / 37 |
| B | OLHC / CLEAN_COHORT / SYM | -5.94 | 2 | 49 | 23 | 4 | 47.0 | 4490.19 / 27 |
| B | OLHC / CLEAN_COHORT / ASYM | -4.84 | 2 | 49 | 30 | 5 | 45.4 | 4770.50 / 29 |
| A | OHLC / NEXT_QUOTE / SYM | +13.89 | 2 | 67 | 48 | 7 | 54.0 | 6131.27 / 40 |
| A | OHLC / NEXT_QUOTE / ASYM | +14.65 | 2 | 69 | 56 | 6 | 55.4 | 6401.71 / 41 |
| A | OHLC / CLEAN_COHORT / SYM | +4.30 | 2 | 46 | 0 | 0 | N/A | 3827.81 / 27 |
| A | OHLC / CLEAN_COHORT / ASYM | +5.03 | 2 | 46 | 9 | 1 | 59.7 | 3910.83 / 27 |
| B | OHLC / NEXT_QUOTE / SYM | +6.18 | 2 | 64 | 48 | 9 | 51.4 | 5364.37 / 30 |
| B | OHLC / NEXT_QUOTE / ASYM | +7.31 | 2 | 64 | 54 | 10 | 40.0 | 6022.52 / 37 |
| B | OHLC / CLEAN_COHORT / SYM | -5.94 | 2 | 49 | 23 | 4 | 47.0 | 4490.19 / 27 |
| B | OHLC / CLEAN_COHORT / ASYM | -4.84 | 2 | 49 | 30 | 5 | 45.4 | 4770.50 / 29 |

Chi tiết theo nhóm tháng bắt đầu — bảng chính O–L–H–C / NEXT_QUOTE. 2024 xuất hiện trong hai nhóm
nên các nhóm có chồng lấn; 105 cửa sổ không phải 105 đường giá độc lập. Cửa sổ chưa pass được giữ là censored.
Payout dưới đây là **tổng giả định của các cửa sổ chồng nhau**, không phải thu nhập có thể cộng lại hoặc xác suất thành công.

| A/B/phí | Start cohort | N | P1 | Cả 2 | Funded paths | Tháng median | Payout lần / USD chồng lấn | Daily/static % | Breach |
|---|---|---|---|---|---|---|---|---|---|
| A/SYM | 2018–2021 | 48 | 48 (100.0%) | 37 (77.1%) | 7 | 60.1 | 330 / 41385.80 | 0.911/6.564 | 0 |
| A/SYM | 2022–2024 | 36 | 19 (52.8%) | 11 (30.6%) | 2 | 46.9 | 14 / 1566.94 | 0.911/4.826 | 0 |
| A/SYM | 2024–2026 | 33 | 0 (0.0%) | 0 (0.0%) | 0 | N/A | 0 / 0.00 | 0.861/4.826 | 0 |
| A/SYM | 2018–2026 | 105 | 67 (63.8%) | 48 (45.7%) | 7 | 54.0 | 344 / 42952.74 | 0.911/6.564 | 0 |
| A/ASYM | 2018–2021 | 48 | 48 (100.0%) | 42 (87.5%) | 6 | 60.1 | 352 / 47381.34 | 0.898/6.552 | 0 |
| A/ASYM | 2022–2024 | 36 | 21 (58.3%) | 14 (38.9%) | 2 | 48.4 | 18 / 1845.60 | 0.898/4.784 | 0 |
| A/ASYM | 2024–2026 | 33 | 0 (0.0%) | 0 (0.0%) | 0 | N/A | 0 / 0.00 | 0.855/4.784 | 0 |
| A/ASYM | 2018–2026 | 105 | 69 (65.7%) | 56 (53.3%) | 6 | 55.4 | 370 / 49226.94 | 0.898/6.552 | 0 |
| B/SYM | 2018–2021 | 48 | 48 (100.0%) | 37 (77.1%) | 8 | 58.9 | 173 / 28637.54 | 1.138/7.416 | 0 |
| B/SYM | 2022–2024 | 36 | 16 (44.4%) | 11 (30.6%) | 4 | 21.6 | 24 / 2296.71 | 1.300/5.836 | 0 |
| B/SYM | 2024–2026 | 33 | 0 (0.0%) | 0 (0.0%) | 0 | N/A | 0 / 0.00 | 1.300/5.527 | 0 |
| B/SYM | 2018–2026 | 105 | 64 (61.0%) | 48 (45.7%) | 9 | 51.4 | 197 / 30934.25 | 1.300/7.416 | 0 |
| B/ASYM | 2018–2021 | 48 | 48 (100.0%) | 42 (87.5%) | 8 | 45.5 | 284 / 46132.80 | 1.048/7.189 | 0 |
| B/ASYM | 2022–2024 | 36 | 16 (44.4%) | 12 (33.3%) | 6 | 20.5 | 41 / 5192.07 | 1.197/5.431 | 0 |
| B/ASYM | 2024–2026 | 33 | 0 (0.0%) | 0 (0.0%) | 0 | N/A | 0 / 0.00 | 1.197/5.431 | 0 |
| B/ASYM | 2018–2026 | 105 | 64 (61.0%) | 54 (51.4%) | 10 | 40.0 | 325 / 51324.87 | 1.197/7.189 | 0 |

Standalone Funded 50k từ 01/2018 (không cần pass Challenge):

| A/B / phí | Entries | Payout lần / USD | Balance cuối | Daily/static/peak DD % | Breach |
|---|---|---|---|---|---|
| A/SYM | 490 | 40 / 6131.27 | 49992.13 | 0.563/4.944/5.100 | False |
| A/ASYM | 490 | 41 / 6401.71 | 49996.33 | 0.555/4.814/4.969 | False |
| B/SYM | 794 | 30 / 5364.37 | 49825.83 | 0.799/5.624/5.864 | False |
| B/ASYM | 793 | 37 / 6022.52 | 49831.18 | 0.736/5.375/5.396 | False |

**Hạn chế còn chặn việc dùng tiền thật:** dữ liệu thiếu và proxy Ask; thứ tự M1 giả định; tin tức/historical
broker calendar chưa chứng nhận; chưa shadow/demo/owner handover; challenge fee/retry, admin delay, thay đổi spec
và điều kiện nhận payout thực tế chưa mô phỏng. Reference R không bằng % lợi nhuận tài khoản.
Risk giữ đúng V4 200/175/125 USD, throttle/cap/reserve và V6 harvester; không dùng ratchet phase1/2 V5.
Payout 80%, debit 100% gross profit, kỳ 14 ngày là giả định hợp đồng nghiên cứu; không có chuyển tiền thật.

## 3. Dọn 106 cặp directory

106 cặp quy về 51 E targets. Đã xóa **4 cây**, **212 file**, **106 thư mục**,
**16,305,540 bytes = 0.01630554 GB** logic; giữ **47 cây**.
Không gọi bytes logic là bytes vật lý đã giải phóng. D canonical được hash trước/sau, có manifest SHA256 từng file và hướng dẫn restore.
Giữ package/cache subtree để không phá metadata môi trường; giữ Git backup, references và các trường hợp không chứng minh được an toàn.
Không xóa dữ liệu nghiên cứu cũ hoặc VI WIP. Reference scan ban đầu gồm tracked superproject/submodules + process;
scan bổ sung bao gồm cả ignored/untracked text/config. Lỗi đọc và giới hạn dynamic references giữ trong receipt, không tuyên bố scan tuyệt đối.

| Bản E đã xóa | Bytes | File/thư mục |
|---|---|---|
| E:\BACKUP-TRADINGWORKSPACE\activity-report-20261024\source\foundation_v2\engine_runtime | 54703 | 8/1 |
| E:\BACKUP-TRADINGWORKSPACE\session-report-20261025\source\foundation_v2\engine_runtime | 54703 | 8/1 |
| E:\BACKUP-TRADINGWORKSPACE\session-report-20261025\source\foundation_v2\evidence\rust-native-20261018 | 8098067 | 98/52 |
| E:\BACKUP-TRADINGWORKSPACE\trade-note-layout-20261030\source\foundation_v2\evidence\rust-native-20261018 | 8098067 | 98/52 |

## 4. Kiểm toán, kiểm thử và hiệu năng

Decimal oracle kiểm **1612 paths** và **1840 account ledgers**.
Kiểm riêng entry/cost/grid/reserve, first-hit/P1 timing, Prague reset, equity DD, phase passes, forced-close next quote và payout cash bridge.
Không import accounting producer trong `independent_ledger_auditor.py`; đây là phép tính riêng cùng implementer/feed, không phải reviewer/người hay nguồn giá độc lập.
**1110 tests PASS**, **0 skip**; giữ nguyên **1091/1091 IDs** và thêm **19** regressions.
Smoke giữ đúng 78 bài (đề bài ghi 66 là baseline cũ). Profile đầu lượt: suite 0,660s, import 0,241s;
không có một test 150–200ms: test lâu nhất khoảng 71ms, tổng I/O fixtures là phần lớn thời gian.
10 lần fresh-process đã đăng ký trước: median suite **0.587s**, max **0.603s**;
median wall **0.762s**, max wall **0.783s**.
10/10 suite <0,85s: **True**; 10/10 wall <0,85s: **True**.
Giữ mọi outlier, không retry để kiếm streak đẹp; không giảm test/case/assertion. Đo đủ rồi dừng, không refactor vòng đời chỉ để đổi số benchmark.
Exact-head CI và artifact ID reconciliation được lưu trong receipt CI sau khi PR chạy.

## Kết luận sử dụng

A/B đã được chạy đến lifecycle theo quyền V14, không dừng ở gate tần suất cũ. Xem các bảng trên để phân biệt
dương tổng, ổn định từng năm, tốc độ pass, và payout. Không tự tăng risk hay chọn lại nhánh sau Validation.
Giữ A làm ứng viên nghiên cứu ưu tiên nếu so sánh nhất quán; B là đối chứng thêm tần suất, không mặc định được promote.
Cần owner xem kết quả và phê duyệt giai đoạn kiểm chứng tiếp; PR V14 mở để review, **không merge**.

Nguồn máy đọc + hash toàn bộ receipts: `EVIDENCE-AND-LIFECYCLE-V14-RESULTS-20261115.json`. Private job: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\evidence-and-lifecycle-v14-20261115`.
Mã chạy/flow: source admission → frozen recipes → two M1 paths → V4/V6 reused lifecycle → standalone Decimal audit → report.
Erratum-01: sổ tham chiếu bỏ lệnh không vừa lot tối thiểu thay vì crash, không nới risk. Chỉ B chưa xong được resume;
giữ bốn kết quả A và hai log thất bại. Erratum-02 chỉ mở rộng kiểm toán nguồn/chi phí và thứ tự event cùng timestamp.
Giữ freeze, nguồn cũ, thử nghiệm âm và các lần rehearsal không đạt; không xóa lịch sử lựa chọn.
