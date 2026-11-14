# V4 — tăng tốc hoàn tất hai vòng, vẫn chưa tạo payout

**Đã hoàn tất V4:** chính sách song trụ tạo 3/36 cửa sổ hoàn tất hai vòng ở swap bất đối xứng và 2/36 ở swap đối xứng; **payout vẫn 0**. Sụt giảm từ đỉnh tăng lên khoảng 14,4%, còn lỗ dưới vốn đầu sát 8%. Không chọn thêm nhánh thứ ba và chưa đủ điều kiện mở ngay một bài thi holdout đầy đủ 01/2025–10/2026.

Task `d6d78dc3-c7e9-40ee-a684-61490c368f27`; PR81 đã merge `5864d8b`, xóa nhánh V3. Campaign dùng ngày UTC 14/11; kiểm/bàn giao ngày địa phương 15/11/2026. WIP VI Dubber và Trader pin giữ nguyên. Không broker, provider/model call hoặc giải mã giá 2025–2026.

## 1. Năm cột so sánh — cùng 36 mốc xuất phát tháng

| Chỉ tiêu | PR79 A/v1 ASYM | PR80 A/v2 ASYM | V3 A+EUR ASYM | V4 ASYM/14 ngày | V4 SYM/14 ngày |
|---|---:|---:|---:|---:|---:|
| Qua vòng 1 | 13/36 | 5/36 | 15/36 | 14/36 | 13/36 |
| Qua cả hai vòng | 0/36 | 0/36 | 2/36 | 3/36 | 2/36 |
| Trung vị qua vòng 1* | 10.64 tháng | 15.67 tháng | 10.64 tháng | 6.48 tháng | 7.90 tháng |
| Trung vị hoàn tất hai vòng* | N/A | N/A | 21.79 tháng | 7.68 tháng | 8.14 tháng |
| Số payout mô phỏng | 0 | 0 | 0 | 0 | 0 |
| USD trả trader trong mô hình | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 |
| Lỗ ngày lớn nhất | 1.221% | 0.979% | 1.071% | 1.280% | 1.341% |
| Lỗ dưới vốn đầu lớn nhất | 8.899% | 6.083% | 6.997% | 7.994% | 7.995% |
| Sụt giảm từ đỉnh lớn nhất | 11.849% | 8.356% | 8.790% | 14.365% | 14.468% |
| Vi phạm trong mô hình | 0 | 0 | 0 | 0 | 0 |

*Chỉ tính cửa sổ đã đạt; không phải dự báo thời gian cho mọi tài khoản. Các mốc chồng lấn, những mốc cuối mẫu có ít thời gian theo dõi hơn. V4 có ít cửa sổ qua vòng 1 hơn V3, nhưng nhiều cửa sổ hoàn tất vòng 2 hơn. Không được kết luận tăng risk chắc chắn tăng mọi chỉ tiêu.

Các tỷ lệ lỗ/DD trong bảng đều chia cho vốn đầu $50.000. Sụt giảm từ đỉnh khác lỗ dưới vốn đầu: tài khoản có thể mất cả lợi nhuận đã tích lũy rồi xuống sát 46k, tạo peak-to-valley >10% vốn đầu nhưng chưa chạm static floor 45k. Đó vẫn là tổn thất lớn với người vận hành.

Mỗi model V4 chỉ có **một đường funded riêng biệt**: các cửa sổ thành công cùng qua vòng 1 ngày 29/09/2023, vòng 2 ngày 20/10/2023 rồi trùng đường giao dịch funded. Ba cửa sổ ASYM không phải ba lần thành công độc lập.

## 2. Đã thay gì và vì sao

| Thành phần | V3 | V4 đã khóa |
|---|---|---|
| Gold risk P1/P2/Funded | $200/$175/$125 | Giữ nguyên |
| EUR risk P1/P2/Funded | $100/$100/$75 | $200/$175/$125 |
| Trần tổng initial-stop đang mở | $500 / 1% | $800 / 1,6% |
| Cổng equity dự phóng sau SL/phí/funding | $46.500 / −7% | $46.000 / −8% |
| Throttle theo equity hiện tại | Chạm −4%: cap $150; −6%: cap $90 | Giữ nguyên cho cả hai nhánh |
| Cầu dao lỗ thực hiện ngày | −2%, nghỉ đến Prague reset | Giữ nguyên |
| Reward proxy | 30 ngày | So sánh 14 và 30 ngày |

Không đổi entry, natural SL, phía BUY/SELL, lịch đóng, phí hoặc swap. Không D1 filter mới, TP, trailing hay kéo SL. Chỉ một trial equal-risk trên 48 cửa sổ Dev; worst static 7,9359%, worst daily 1,34082%, không modeled breach. Không thử thêm trọng số hoặc nới cổng sau kết quả.

ASYM giữ swap Gold BUY −45 / SELL −5 USD/lot/rollover; SYM −40/−40, thứ Tư nhân ba theo profile kế thừa. Gold commission 0,0007% notional/side, stress slippage 0,20 USD/oz/side; EUR commission $5 + slippage $4/lot/vòng và spread Bid/Ask quan sát. EUR đóng trong ngày nên không phát sinh rollover. Đây là profile nghiên cứu, chưa là biểu phí lịch sử đã chứng nhận của tài khoản FTMO cụ thể.

Composition commit `8b1bfba9f9dc4a2bed73b2c39a2cf5f680ff871b` trước release `2026-11-14T17:07:38.404622+00:00` và lần traversal 2024 mới. Code/rule/input hashes khớp bản đã khóa. 2024 đã exposed, chỉ Historical Validation, không clean OOS.

**EUR không có đường vốn mượt:** nâng ngang hàng chỉ là trial owner cho phép, không phải kết luận EUR ít rủi ro hơn Gold. Corr ngày thấp không bảo đảm hai lệnh không cùng lỗ trong một giờ. Trần 1,6% vẫn cộng rủi ro tuyệt đối, không net BUY/SELL hoặc trừ theo correlation.

## 3. Giải phẫu EUR riêng ở risk tham chiếu $150

| Năm | Lệnh | Net R | Peak-to-valley DD (R) | Worst daily loss (R) |
|---|---:|---:|---:|---:|
| 2022 | 112 | +3.771 | 23.205 | 1.170 |
| 2023 | 124 | +10.562 | 17.388 | 1.315 |
| 2024 | 67 | +6.337 | 11.290 | 1.392 |
| 2022–2023 liên tục | 236 | +14.334 | 35.757 | 1.315 |
| 2022–2024 liên tục | 303 | +20.671 | 35.757 | 1.392 |

Đây là đường equity tick của EUR riêng, 1R=$150, không annual-reset để ghép sổ liên tục. DD gộp Dev 35,757R lớn hơn tổng lợi nhuận 14,334R; không gọi là ít drawdown chỉ vì cuối hai năm dương. Top3 lệnh thắng mỗi năm vẫn quyết định hơn toàn bộ lợi nhuận EUR năm đó theo V3.

| Swap Gold | Corr ngày 2022 | Corr ngày 2023 | Corr gộp Dev |
|---|---:|---:|---:|
| SYM_FLAT | 0.071 | 0.121 | 0.100 |
| ASYM_FLAT | 0.071 | 0.124 | 0.102 |

Dùng thay đổi equity cuối ngày Prague trên cùng business-day grid, có ngày 0. Đây là tương quan trong Development, không phải bảo đảm tương lai.

## 4. Top10 và quyết định không thêm nhánh thứ ba

Giữ thứ hạng screen V3: EUR là #6, không phải #1. Các con số còn lại là screen M1/H1 có điều kiện; EUR được thay bằng tick đã xác nhận. Bảng dùng ASYM; JSON giữ cả hai models và toàn bộ lý do loại.

| # | Asset / cơ chế / giữ | Net R 2022 | Net R 2023 | Corr Gold | Corr EUR | Lý do chưa thêm |
|---:|---|---:|---:|---:|---:|---|
| 1 | GBPUSD.SWEEP.ASIA.LONDON.DAY | +5.617 | +26.075 | -0.015 | 0.200 | Thiếu M1/tick |
| 2 | XAUUSD.SWEEP.PREVDAY.LONDON.DAY | +17.099 | +9.930 | 0.111 | -0.032 | Retention/scale, Gold Ask/path |
| 3 | XAUUSD.SWEEP.PREVDAY.LONDON.24H | +11.542 | +13.215 | 0.100 | -0.045 | Retention/scale, Gold Ask/path |
| 4 | XAUUSD.SWEEP.PREVDAY.LONDON.48H | +6.131 | +17.378 | 0.120 | -0.021 | Retention/scale, Gold Ask/path |
| 5 | US500.SWEEP.PREVDAY.NY.48H | +12.337 | +8.163 | -0.008 | -0.012 | Retention/scale và carry/cổ tức chưa xác minh |
| 6 | EURUSD.SWEEP.ASIA.LONDON.DAY | +3.771 | +10.562 | 0.102 | 1.000 | Đã là co-core |
| 7 | GBPUSD.SWEEP.PREVDAY.LONDON.DAY | +14.361 | -1.973 | -0.066 | 0.046 | Thiếu M1/tick; không ổn định kinh tế |
| 8 | US500.SWEEP.PREVDAY.LONDON.48H | +5.785 | +4.928 | 0.012 | -0.006 | Retention/scale và carry/cổ tức chưa xác minh |
| 9 | US500.SWEEP.PREVDAY.LONDON.24H | +6.171 | +2.819 | 0.032 | -0.009 | Retention/scale và carry/cổ tức chưa xác minh |
| 10 | US500.SWEEP.PREVDAY.NY.24H | +8.881 | -0.470 | -0.027 | 0.022 | Retention/scale và carry/cổ tức chưa xác minh; không ổn định kinh tế |

SWEEP = quét qua biên rồi quay lại; ASIA/PREVDAY = phiên Á/ngày trước; LONDON/NY = phiên London/New York; DAY = đóng trong ngày. DAY/24H/48H trên cùng cohort không phải ba nguồn lợi nhuận độc lập.

GBPUSD Asia/London là hướng đáng kiểm chất lượng nguồn tiếp: dương hai năm, corr EUR khoảng 0,20 và corr Gold gần 0. Nhưng chỉ H1 không đủ kết luận SL fill/equity M1; QDM metadata hiện không có GBP cached dataset. Không lấy screen H1 đẹp để cấp vốn thật. Gold sweep mất hơn 50% raw signals ở cổng phí; US500 thiếu carry/dividend và scale. Vì vậy **không thêm sleeve #3** trong ngân sách hiện tại.

## 5. Lệnh bị chặn và giảm risk

| Model / policy | Asset | Nhận | Risk bị throttle* | Chặn cap | Chặn reserve nội bộ | Chặn daily halt |
|---|---|---:|---:|---:|---:|---:|
| SYM_FLAT / V3 | XAUUSD | 4977 | 786 | 87 | 603 | 0 |
| SYM_FLAT / V3 | EURUSD | 4607 | 67 | 0 | 468 | 0 |
| SYM_FLAT / V4 | XAUUSD | 4432 | 825 | 0 | 1235 | 0 |
| SYM_FLAT / V4 | EURUSD | 3982 | 833 | 0 | 1093 | 0 |
| ASYM_FLAT / V3 | XAUUSD | 5179 | 636 | 85 | 403 | 0 |
| ASYM_FLAT / V3 | EURUSD | 4760 | 113 | 0 | 315 | 0 |
| ASYM_FLAT / V4 | XAUUSD | 4244 | 747 | 0 | 1423 | 0 |
| ASYM_FLAT / V4 | EURUSD | 3775 | 801 | 0 | 1300 | 0 |

*So với nominal risk riêng của nhánh/phase; lượng lot làm tròn xuống không tính là throttle. Cap từ chối nguyên lệnh, không tự giảm size để lách cap. Counts cộng trên 36 cửa sổ chồng lấn, không là số tín hiệu độc lập bị bỏ lỡ. JSON giữ cả phase/prestart/collision/lot rejects.

V4 loại được cap rejects trong mẫu đã đo nhưng reserve chặn nhiều hơn vì EUR nhận vốn lớn hơn và đường vốn đi sát floor. Khi tài khoản đã flat sát floor, cổng này có thể chặn mọi cơ hội mới và tài khoản đứng lại dù chưa vi phạm luật hãng. Không gọi những cửa sổ đó là an toàn và chỉ cần chờ thêm chắc chắn sẽ hồi phục.

## 6. Vì sao chưa payout dù từng có equity dương?

Trong 13 cửa sổ V3 chưa xong vòng 2, **7 dương và 6 âm** lúc hết mẫu. Các cửa sổ đều right-censored, nhưng không đồng nghĩa tất cả chỉ thiếu thời gian.

Đường funded V3: equity cao nhất $50.379,30 (cũng xảy ra sau mốc 14/30 ngày), nhưng closed balance cao nhất chỉ $50.000. Khi flat và đủ 14 hoặc 30 ngày, balance cao nhất $49.849,38. Equity dương khi còn giữ lệnh không phải lợi nhuận có thể rút; đóng cưỡng bức tại một đỉnh biết sau sẽ là một biến thể exit mới, không phải sửa lịch payout.

| V4 / mốc bắt đầu | Pass P1 / P2 | Balance cuối funded | Max equity funded | Max balance flat ≥14d |
|---|---|---:|---:|---:|
| SYM_FLAT / 2023-02-01 | 2023-09-29 / 2023-10-20 | $49,634.27 | $50,207.80 | $49,946.01 |
| SYM_FLAT / 2023-03-01 | 2023-09-29 / 2023-10-20 | $49,634.27 | $50,207.80 | $49,946.01 |
| ASYM_FLAT / 2023-02-01 | 2023-09-29 / 2023-10-20 | $49,789.71 | $50,309.71 | $49,984.86 |
| ASYM_FLAT / 2023-03-01 | 2023-09-29 / 2023-10-20 | $49,789.71 | $50,309.71 | $49,984.86 |
| ASYM_FLAT / 2023-07-01 | 2023-09-29 / 2023-10-20 | $49,789.71 | $50,309.71 | $49,984.86 |

| Swap | Proxy | Qua P1 | Qua cả hai | Số payout | USD trader |
|---|---:|---:|---:|---:|---:|
| SYM_FLAT | 14 ngày | 13/36 | 2/36 | 0 | $0.00 |
| SYM_FLAT | 30 ngày | 13/36 | 2/36 | 0 | $0.00 |
| ASYM_FLAT | 14 ngày | 14/36 | 3/36 | 0 | $0.00 |
| ASYM_FLAT | 30 ngày | 14/36 | 3/36 | 0 | $0.00 |

**Đổi 30 sang 14 ngày không tạo payout trong mẫu này.** Có closed balance V4 trên 50k khi còn vị thế khác/đầu kỳ, nhưng không có lãi flat đủ điều kiện ở cửa sổ request được mô phỏng.

14 ngày là mốc eligibility/request, không phải cam kết nhận tiền đều đặn mỗi hai tuần. Mô hình giữ cùng account, debit toàn bộ profit, chia 80/20, minimum $20, zero admin delay và đếm lại interval từ request trước; đây là assumptions của proxy. Không mô phỏng approval/chuyển khoản/thuế/phí challenge, thay tài khoản hay rút một phần.

Lượt kiểm FAQ chính thức FTMO `https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/` không đọc được do lỗi TLS; không nâng bằng chứng lịch sử 12/11 thành xác minh điều khoản mới ngày 15/11. Historical source ở Gold cost audit vẫn giữ. 14/30-day results là scenario có khai báo, không FTMO acceptance.

## 7. Readiness cho 01/2025–10/2026

Chỉ gọi QDM `-symbol action=list`, không export/update, không hash/giải mã nội dung giá holdout.

| Dataset metadata hiện có | Ngày cuối quảng bá | Kết luận giới hạn |
|---|---|---|
| EURUSD_TICK_TW / TICK | 2026.11.01 | Có metadata, chưa kiểm từng ngày/giá |
| EURUSD_TW / M1 | 2026.10.07 | Có metadata, chưa kiểm từng ngày/giá |
| XAUUSD_TW / M1 | 2026.10.13 | Có metadata, chưa kiểm từng ngày/giá |

**Chưa sẵn sàng để bấm chạy ngay full window:** Gold M1 mới tới 13/10/2026, EUR M1 tới 07/10; EUR tick quảng bá tới 01/11 nhưng chưa kiểm coverage. Không có XAUUSD tick dataset được list; paired Gold ticks 2025–2026 chưa được chứng nhận. Metadata không chứng minh nguồn hoàn toàn sạch OOS; các task khác có thể đã dùng dữ liệu đó.

Trước một lần release holdout cần owner duyệt riêng: khóa một final policy/horizon/cost/stop criterion, seed causal, lịch holiday/session 2025–2026 và news/spec profile; admission/coverage/raw integrity và exposure manifest cho đúng hai tài sản. Không đổi tham số sau khi mở hoặc dùng phần thiếu để chọn lại khoảng ngày. Không tự tải thêm/mở giá hoặc cam kết chỉ duyệt PR là đủ mọi gate.

## 8. Kiểm chứng, hậu kiểm và quyết định

- 209 tests đạt, gồm 12 fixtures V4 về co-core risk, throttle, default V3, cap/floor, reward 14/30/flat/full-debit và source gates.
- 72 tài khoản V3 tái hiện khớp chính xác accepted/closed/rejections, cash, DD, phase và payout; không đổi kết quả lịch sử vì thêm policy hooks.
- 144 tài khoản V4 khớp oracle cash-posted funding: 32,866 admissions, 10,102 rejections, 32,866 cost bridges, 104,985,511 quote updates kiểm theo timestamp.
- Reuse raw-source parity V3 (25.447.523 tick EUR khớp CSV); source không đổi, loader hiện tại kiểm hash từng giờ giá được đọc.
- Cùng implementer dùng hạch toán khác; không độc lập người/model, không Astra. Chưa có live fills, forward, broker/model/provider call.
- Target contract/lot/margin/leverage, swap thực tế, lịch tin hạn chế và phiên đúng feed chưa xác minh đủ. Carried quotes khi thị trường nghỉ không thành fresh reset quotes. Không modeled breach trong profile không phải chứng nhận account FTMO thực tế.

| Hậu kiểm | Quyết định |
|---|---|
| Lịch payout30 từng bị xem là nguyên nhân chính | Kiểm proxy14: vẫn0, không có lãi flat đủ điều kiện |
| Satellite ít risk có phải nút thắt duy nhất | Co-core tăng completion, nhưng peak DD tăng và payout0; không tiếp tục nới risk |
| Correlation thấp bị hiểu thành an toàn đồng thời | Giữ gross cap và reserve, không net correlation |
| V3 thiếu reject reasons theo tài sản | Reproduce72defaults và instrument reason; khớp archived outcomes |
| Native source census đã có | Reuse source pins, không lặp fullCSVscan hoặc tạo engine/account state song song |

V4 chưa đạt mục tiêu thu nhập chính. Dừng vòng tăng risk/đổi chu kỳ để ép payout ở đây. Giữ hai cơ chế làm research benchmark; GBP chỉ source-readiness, không thêm sleeve yếu. Một đợt kiểm tiếp phải giải quyết uncertainty đã nêu, không được gọi số cửa sổ pass là xác suất tương lai hoặc biến 2024 đã exposed thành OOS sạch.

Private evidence: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\prop-cocore-v4-20261114`. Báo cáo JSON giữ composition/release, Top10, comparisons, 144 summary ledgers, EUR books, source/check hashes và readiness metadata; full ledgers và oracle records ở private job.
