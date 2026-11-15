# V6 — Kết quả V4_Harvest và sát hạch 2025–2026

**Chưa đủ điều kiện Challenge/thu nhập chính.** EURUSD âm trên tick đầy đủ ở cả 2025
và 2026 YTD. Gold dương nhẹ ở các lệnh định giá được, nhưng Bid M1/Ask giả định và
một hạn thoát nghỉ lễ thiếu giá khiến phần 2026 chưa hoàn chỉnh. Có payout mô phỏng
ở một số mốc cũ; không có tiền thưởng thật nào được nhận trong công việc này.

## Cấu hình và dữ liệu đã khóa

- PR 83 đã merge `5a8dd69`; cấu hình khóa ở `665ed5ba6f6424e6e40c154a26752779e0833c86` trước mở giá holdout.
- V4_Harvest: Gold A + EUR Asia/London sweep, cả hai $200/$175/$125 theo vòng;
  cap mở $800, sàn dự phòng $46k; throttle 48k/47k và halt lỗ ngày $1k giữ nguyên.
- Bỏ D1/D2/Target Ratchet; harvester chỉ Funded. Không đổi tín hiệu/SL/chi phí
  hoặc chọn tham số sau khi mở 2025–2026. 2022–24 vẫn dùng ticks lịch sử đã duyệt.
- Gold: 632.140 Bid M1; Ask mô phỏng=Bid+0.338 USD/oz
  (trung vị spread vào lệnh Dev 2022–23), khóa trước mở giá. Hai thứ tự OHLC là
  kịch bản có điều kiện, không phải tick thật hoặc cận DD an toàn đã chứng nhận.
- EUR: 38.292.958 tick Bid/Ask gốc, gộp 663.309 M1; có cả 08–13/10/2026.
  Cache-only, không update/download. Cả hai kết thúc 13/10/2026 UTC.
- Đây là lần đánh giá đầu của chiến dịch V6 trên đoạn đó; chưa chứng nhận dữ liệu
  này chưa từng bị dự án khác sử dụng. Từ nay đoạn 2025–2026 đã có exposure.

## Đính chính nguyên nhân lịch sử

V4 qua P1 ngày 29/09/2023, P2 ngày 20/10/2023, đã Funded từ tháng 10/2023.
Số dư 49.751,56 USD là V3; V4 cuối 2024 là 49.789,71 ASYM/49.634,27 SYM.
Vì vậy, lý do payout 0 của V4 không đơn thuần là chỉ còn vài tuần cuối 2024.
Không thể cộng R hai nhánh rồi trừ 42 R để suy ra tiền còn rút: sizing từng vòng,
lệnh bị từ chối, drawdown, thời điểm chuyển vòng và reset vốn đều ảnh hưởng.
Đối soát 72 checkpoint V6 trước 2025 khớp chính xác V4 về tiền, lệnh, DD và vòng.

## Funded độc lập 2022–2024

Jan 2022 là mốc liên tục 3 năm và cũng là mốc đầu trong 12 quý, không phải mẫu thứ 13.
Risk Funded danh nghĩa 0,25%; throttle/sàn dự phòng vẫn hoạt động.

| Phí | Kỳ payout Jan 22 | Gross trừ khỏi tài khoản | Trader USD/3 năm | TB/năm | TB/quý | TB/tháng | Max daily 12 mốc | Max static 12 mốc | Breach |
|---|---|---|---|---|---|---|---|---|---|
| SYM_FLAT | 12 | 4,820.67 | 3,856.49 | 1,285.50 | 321.37 | 107.12 | 0.832% | 7.995% | 0 |
| ASYM_FLAT | 12 | 4,584.62 | 3,667.64 | 1,222.55 | 305.64 | 101.88 | 0.795% | 7.909% | 0 |

Đây là tiền trader **mô phỏng sau chia 80/20**, chưa trừ phí challenge/retry, thuế,
vận hành hoặc thời gian duyệt/chi tiền. Bình quân chỉ khoảng 102–107 USD/tháng
trên một tài khoản 50k ở mốc Jan 2022, không đủ bằng chứng cho thu nhập ổn định.

| Start | ASYM kỳ/USD | ASYM Daily/Static | SYM kỳ/USD | SYM Daily/Static |
|---|---|---|---|---|
| 2022-01-01 | 12/3,667.64 | 0.795/7.846% | 12/3,856.49 | 0.832/7.869% |
| 2022-04-01 | 9/3,722.07 | 0.795/7.846% | 9/3,920.96 | 0.832/7.869% |
| 2022-07-01 | 4/2,890.88 | 0.653/7.909% | 4/2,805.60 | 0.653/7.995% |
| 2022-10-01 | 2/783.06 | 0.782/7.857% | 3/1,203.59 | 0.798/7.891% |
| 2023-01-01 | 6/3,550.89 | 0.782/6.139% | 6/3,306.25 | 0.798/6.231% |
| 2023-04-01 | 4/2,546.92 | 0.782/6.139% | 4/2,682.99 | 0.798/6.231% |
| 2023-07-01 | 5/4,193.13 | 0.752/6.381% | 6/3,602.81 | 0.752/6.231% |
| 2023-10-01 | 4/1,497.54 | 0.752/5.907% | 3/1,384.66 | 0.752/6.000% |
| 2024-01-01 | 2/1,038.71 | 0.752/3.779% | 2/967.35 | 0.752/3.860% |
| 2024-04-01 | 3/1,288.49 | 0.752/3.352% | 2/1,239.17 | 0.752/3.391% |
| 2024-07-01 | 3/1,483.17 | 0.752/3.118% | 2/1,446.82 | 0.752/3.125% |
| 2024-10-01 | 3/2,024.14 | 0.572/0.943% | 3/2,009.02 | 0.577/0.970% |

Thu nhập trader mô phỏng của riêng mốc Jan 2022:

| Năm | ASYM USD | SYM USD |
|---|---|---|
| 2022 | 2,909.94 | 2,644.34 |
| 2023 | 757.70 | 1,212.15 |
| 2024 | 0.00 | 0.00 |

Ví dụ ASYM: cuối 2023 balance còn 48.616,36 USD. Năm 2024 giao dịch lãi 1.127,84 USD,
nhưng cuối năm chỉ hồi lên 49.744,20 USD, vẫn dưới vốn gốc 50k nên không có payout.
**Một năm giao dịch có lãi khác với một năm rút được tiền.**

| Quý | ASYM USD | SYM USD |
|---|---|---|
| 2022 Q1 | 510.07 | 502.87 |
| 2022 Q2 | 1,049.62 | 1,018.66 |
| 2022 Q3 | 807.90 | 767.30 |
| 2022 Q4 | 542.35 | 355.51 |
| 2023 Q1 | 0.00 | 0.00 |
| 2023 Q2 | 0.00 | 0.00 |
| 2023 Q3 | 0.00 | 0.00 |
| 2023 Q4 | 757.70 | 1,212.15 |
| 2024 Q1 | 0.00 | 0.00 |
| 2024 Q2 | 0.00 | 0.00 |
| 2024 Q3 | 0.00 | 0.00 |
| 2024 Q4 | 0.00 | 0.00 |

Không cộng tiền 12 mốc thành thu nhập một tài khoản: chúng chồng lấn cùng lịch sử.

## Từng nhánh trên holdout: số lệnh và R

Bảng này đo từng tín hiệu độc lập ở risk tham chiếu 125 USD, không dùng harvester
hoặc admission của tài khoản. BUY/SELL và MeanR chỉ tính các lệnh đóng định giá
được. Gold 2026 thiếu 1 lệnh thoát và có 2 tín hiệu không đạt lot tối thiểu ở 125 USD;
tổng R còn lại là **known-cohort**, chưa phải tổng R trọn kỳ của chiến lược.

| Nhánh/năm/phí | Paths (BUY/SELL) | BUY/SELL đã đóng | Lot reject/thiếu | Net R đã biết | Mean R đã biết | Đủ kỳ? |
|---|---|---|---|---|---|---|
| XAUUSD/2025/SYM_FLAT | 96 (72/24) | 72/24 | 0/0 | 2.8191 | 0.0294 | Có trong mô hình nguồn |
| XAUUSD/2025/ASYM_FLAT | 96 (72/24) | 72/24 | 0/0 | 2.9583 | 0.0308 | Có trong mô hình nguồn |
| XAUUSD/2026/SYM_FLAT | 72 (39/33) | 36/33 | 2/1 | 1.7012 | 0.0247 | Không |
| XAUUSD/2026/ASYM_FLAT | 72 (39/33) | 36/33 | 2/1 | 2.0392 | 0.0296 | Không |
| EURUSD/2025/SYM_FLAT | 95 (49/46) | 49/46 | 0/0 | -14.5963 | -0.1536 | Có trong mô hình nguồn |
| EURUSD/2025/ASYM_FLAT | 95 (49/46) | 49/46 | 0/0 | -14.5963 | -0.1536 | Có trong mô hình nguồn |
| EURUSD/2026/SYM_FLAT | 57 (26/31) | 26/31 | 0/0 | -3.5090 | -0.0616 | Có trong mô hình nguồn |
| EURUSD/2026/ASYM_FLAT | 57 (26/31) | 26/31 | 0/0 | -3.5090 | -0.0616 | Có trong mô hình nguồn |

DD cần đường vốn liên tục. Các sổ đo sau dừng trước điểm thiếu giá, không nối
giá tương lai vào một vị thế chưa biết đã đóng hay chưa. Daily tính trên 50k ở
125 USD/lệnh; DD R gồm floating và chi phí theo mô hình đã nêu.
Riêng Gold 2026: NetR của sổ dưới đây chỉ đến 03/07; bảng known-cohort phía trên
có thêm các lệnh định giá được sau 03/07, nên hai tổng này khác phạm vi.

| Nhánh/năm/phí | Lệnh vào/đóng | Net closed R đến điểm đo | Equity R-DD | Worst daily | Đo đến |
|---|---|---|---|---|---|
| XAUUSD/2025/SYM_FLAT | 96/96 | 2.8191 | 13.3765 | 0.5365% | 2026-01-01 T 00:00:00+00:00 |
| XAUUSD/2026/SYM_FLAT | 46/45 | 9.9773 | 5.5531 | 0.3411% | 2026-07-03 T 17:00:00+00:00 |
| XAUUSD/2025/ASYM_FLAT | 96/96 | 2.9583 | 13.1661 | 0.5377% | 2026-01-01 T 00:00:00+00:00 |
| XAUUSD/2026/ASYM_FLAT | 46/45 | 10.2029 | 5.5491 | 0.3412% | 2026-07-03 T 17:00:00+00:00 |
| EURUSD/2025/SYM_FLAT | 95/95 | -14.5963 | 21.8410 | 0.3305% | 2026-01-01 T 00:00:00+00:00 |
| EURUSD/2026/SYM_FLAT | 57/57 | -3.5090 | 16.1919 | 0.2800% | 2026-10-14 T 00:00:00+00:00 |
| EURUSD/2025/ASYM_FLAT | 95/95 | -14.5963 | 21.8410 | 0.3305% | 2026-01-01 T 00:00:00+00:00 |
| EURUSD/2026/ASYM_FLAT | 57/57 | -3.5090 | 16.1919 | 0.2800% | 2026-10-14 T 00:00:00+00:00 |

**EURUSD không tiếp tục dương:** năm 2025 là -14,5963 R;2026 là -3,5090 R trên tick đầy đủ.
Gold 2025 khoảng+2,82 R/+2,96 R; Gold 2026 known-cohort+1,70 R/+2,04 R nhưng thiếu
đường thoát nên chưa kết luận dương trọn kỳ. Không chuyển sang Gold-only từ
kết quả này rồi gọi lại cùng dữ liệu là OOS mới.

## Các tài khoản chạy liên tục và mốc mới

Dừng đo riêng tài khoản còn giữ lệnh Gold không định giá được tại 03/07/2026
17:00 UTC. Tài khoản đã bỏ qua/đóng trước tín hiệu đó vẫn chạy tiếp đến 13/10.
Pass/payout dưới đây là những gì xảy ra **trước cutoff thực đo** của từng sổ.

| Nhóm/phí | P1 | Cả 2 | Sổ có payout | Lần payout | USD cộng sổ | Censored | Đủ đến 13/10 | Breach đã đo |
|---|---|---|---|---|---|---|---|---|
| 36 mốc cũ/SYM_FLAT | 23/36 | 7/36 | 7 | 23 | 6,678.20 | 20 | 16 | 0 |
| 36 mốc cũ/ASYM_FLAT | 26/36 | 7/36 | 6 | 21 | 6,369.78 | 21 | 15 | 0 |
| 21 mốc mới/SYM_FLAT | 0/21 | 0/21 | 0 | 0 | 0.00 | 17 | 4 | 0 |
| 21 mốc mới/ASYM_FLAT | 0/21 | 0/21 | 0 | 0 | 0.00 | 17 | 4 | 0 |

**USD cộng sổ là tổng của các mô phỏng chồng lấn**, không phải thu nhập một
tài khoản, tiền thật hoặc xác suất payout. Các mốc mới chưa có pass trước điểm
dừng;17/21 bị censor, vì vậy không tuyên bố đã kiểm đầy đủ 21 mốc đến 13/10.

| Nhóm/phí | Max daily | Max static | Max peak→valley | Median tháng P1 / cả 2 trong mẫu qua |
|---|---|---|---|---|
| 36 cũ/SYM_FLAT | 1.3408% | 8.0642% | 14.4682% | 8.93/17.38 |
| 36 cũ/ASYM_FLAT | 1.2799% | 8.0609% | 14.3649% | 7.91/16.36 |
| 21 mới/SYM_FLAT | 1.0181% | 7.9772% | 12.6933% | N/A/N/A |
| 21 mới/ASYM_FLAT | 1.0189% | 7.9632% | 12.6679% | N/A/N/A |

Không breach trên phần đã đo không chứng nhận an toàn phần bị thiếu. Sàn 8%
là reserve trước lệnh, không bảo đảm equity không bao giờ đi xuống hơn 8%.
Static so với 50k khác peak-to-valley từ đỉnh cao trước đó.

Các sổ đã Funded ngay tại checkpoint cuối 2024:

| Start/phí | Balance 31/12/24 | Balance cuối phần đo | Payout trader USD | Censor? |
|---|---|---|---|---|
| 2023-02-01/SYM_FLAT | 49,634.27 | 47,512.64 | 1,108.25 | True |
| 2023-03-01/SYM_FLAT | 49,634.27 | 47,512.64 | 1,108.25 | True |
| 2023-02-01/ASYM_FLAT | 49,789.71 | 47,869.23 | 1,229.52 | True |
| 2023-03-01/ASYM_FLAT | 49,789.71 | 47,869.23 | 1,229.52 | True |
| 2023-07-01/ASYM_FLAT | 49,789.71 | 47,869.23 | 1,229.52 | True |

## Nhạy cảm thứ tự M1 và khoảng thiếu

| M1 order/phí | 36 cũ P1/cả 2/payout events | 21 mới P1/cả 2 | Censor cũ/mới |
|---|---|---|---|
| OPEN_LOW_HIGH_CLOSE/SYM_FLAT | 23/7/23 | 0/0 | 20/17 |
| OPEN_LOW_HIGH_CLOSE/ASYM_FLAT | 26/7/21 | 0/0 | 21/17 |
| OPEN_HIGH_LOW_CLOSE/SYM_FLAT | 23/7/23 | 0/0 | 20/17 |
| OPEN_HIGH_LOW_CLOSE/ASYM_FLAT | 26/7/21 | 0/0 | 21/17 |

Hai thứ tự OHLC không đo được spread thật, đường tick trong phút hay cú nhảy
giá tài khoản đích. Kết quả gần nhau cũng không biến M1 thành tick.

Cả hai nguồn có 442 ngày thường không phải ngày lễ đủ timestamp 07–21 UTC;
23 ngày lễ/đóng sớm được phân loại riêng,186 ngày cuối tuần. Đây là kiểm timestamp,
không đồng nghĩa toàn bộ bid/ask và đường vốn được chứng nhận.
Có 320 đường tín hiệu: 152 EUR ticks và 168 Gold có điều kiện.319/320 đủ trong mô hình
đường giá đã khai báo;1/320 thiếu endpoint Gold 02/07/2026→03/07/2026. Không
sửa lịch thành một giờ có giá sau khi nhìn kết quả để lấp điểm này.

## Kiểm chứng, sửa lỗi đo và giới hạn

- 967 test riêng biệt đã được đối chiếu qua các môi trường sẵn có;
 11 fixture V 6. Lượt Python mặc định 895 tests có 15 error do thiếuhttpx/statsmodels/
 Nautilus; chạy lại đúng module trong 3 venv đã có, tất cả đạt. Không bỏ test.
- Oracle tiền hữu tỷ:24 sổ Funded độc lập +114 sổ/scenario× 2, tổng 252 sổ đạt.
 Cùng người triển khai, cách hạch toán khác; không phải reviewer/model độc lập.
- Oracle chạy từ 2022 xuyên 2026 xác nhận state nối checkpoint, admissions/rejects,
 phí/swap, phase/reward, DD và từng dynamic fill theo đúng nguồn tick/kịch bản.
- Giữ attempt lỗi: timestamp pandas microsecond→millisecond; fixed-risk book
 chưa reject lot dưới tối thiểu; và post-gap exposure giữ quá hạn. Chỉ sửa parser/
 measurement boundary, không đổi candidate đã freeze. Outputs attempt 1 không
 dùng nghiệm thu; không chạy lại historical batch vốn đã khớp.
- FTMO FAQ hiện tại fetch lỗiTLS. Đoạn protocol ghi 'checked 15/11' chỉ là lần
 thử truy cập, **không phải xác minh thành công**.14 ngày/80:20/zero admin delay
 tiếp tục là proxy đã đăng ký. News/session đích, margin và chi tiền chưa xác minh.
- Không broker execution, challenge purchase, nguồn trả phí, Astra hoặc subagent.
 VI Dubber WIP và Trader pin giữ nguyên. Toàn bộ 252 oracle không chứng minh giá
 Gold giả định đúng với sàn hoặc đã khép được endpoint bị thiếu.

## Quyết định

**NOT_QUALIFIED; không mua Challenge từ báo cáo này.** Đã chứng minh cơ chế Funded
có thể tạo payout trong mô hình lịch sử, nhưng số tiền thấp và không đều; holdout
EUR không giữ được lợi thế, Gold còn thiếu nguồn. Ưu tiên đóng gap dữ liệu/đặc tả
thực thi bằng một scope mới trước mọi promote. Nếu đổi portfolio, đó là trial mới
và cần dữ liệu prospective mới;2025–2026 này không còn là holdout chưa nhìn.

Full JSON: `PROP-V4-HARVEST-V6-RESULTS-20261115.json`. Private job:`E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\prop-v4-harvest-v6-20261115`.
Các sổ/ledger đầy đủ, logs và failed attempts ở private job; JSON public giữ kết quả
từng mốc, payout ledger, source hashes, censor witnesses và receipts để đối soát.
