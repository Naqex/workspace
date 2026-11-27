# V26 — P80_ISO_EXACT qua Development, giữ BASE_GUARD sau kiểm định vòng đời

[Kết quả JSON](BATCH-EXACT-ISO-V26-RESULTS-20261118.json) · [Protocol](BATCH-EXACT-ISO-V26-PROTOCOL-20261118.md) · [Trọng số đã khóa](BATCH-EXACT-ISO-V26-FREEZE-20261118.json)

PR #104 đã merge vào main tại `9ac2044`, nhánh V25 đã xóa. V26 dùng nhánh `codex/batch-24bots-and-exact-iso-v26`. Hồ sơ GBPUSD S01 được đóng với quyết định không thêm vào danh mục. Số đo DD 15,56–26,52R của V25 thuộc kịch bản H1 20:00 và vẫn mang giới hạn độ phân giải đó.

## 1. Danh mục 24 bot và kết quả Stage-0

[Danh mục 24 hồ sơ](CORPUS-BATCH-V26-CARD-20261118.json) lưu hạng, SHA256, nguồn, alias, mẫu nến, chỉ báo và defaults. Cả 24 thuộc sáu mẫu nến với bốn chỉ báo xác nhận. Symbol và timeframe gốc do biểu đồ chọn. Benchmark khóa H1 trên XAUUSD, EURUSD, US500, GBPUSD và AUDUSD. SL/TP mặc định 200 point, có spread tối thiểu theo source, thời hạn 10 nến và điều kiện thoát theo oscillator.

Engulfing–RSI kế thừa phép thử EURUSD H1 của V25. V26 có 115 ô cho 23 hồ sơ còn lại. Kết quả theo từng ô gồm số tín hiệu từng năm, tỷ lệ qua phí, markout sau phí và lý do dừng.

| Tài sản | Đã đo Stage-0, đều rớt | Thiếu dữ liệu MFI | Nguồn giá |
|---|---:|---:|---|
| EURUSD | 23 | 0 | M1, thêm H1 từ tick cho MFI |
| XAUUSD | 17 | 6 | M1 |
| US500 | 17 | 6 | M1 |
| GBPUSD | 17 | 6 | H1 |
| AUDUSD | 17 | 6 | H1 |
| **Tổng** | **91** | **24** | |

Stage-0 chính dùng +8 giờ, ngưỡng phí/SL 12%, giữ ít nhất 50% tín hiệu và tối thiểu 40 tín hiệu mỗi năm. Markout sau phí phải dương từng năm và ít nhất bằng ma sát trung bình. +4 giờ là số đo phụ. Không ô nào qua cổng nên Net R hai cụm, DD và tương quan PnL ngày để trống. Đây là các chỉ số của SL-active.

Lần chạy đầu chặn cả 30 ô MFI. Kiểm tra bổ sung tìm được số tick quan sát của EURUSD, đối soát 35.588/35.590 giờ. Hai giờ thiếu, 22 giờ có Bid OHLC khác nguồn M1. Sáu ô EURUSD được chạy chẩn đoán với OHLC và volume cùng nguồn tick, sau đó định giá trên M1 đã khóa. Cả sáu rớt Stage-0. Bốn tài sản còn lại cần chuỗi tick volume có nguồn xác minh đủ kỳ để chấm MFI.

## 2. Nghiệm lot rời rạc và vòng đời tài khoản

V25 đã dùng tỷ số từ số liệu chưa làm tròn. DD vượt 5,31 USD vì khối lượng và tiền được tính theo bước rời rạc. V26 kiểm tra 92 vector lot đại diện toàn bộ 11.001 điểm của khoảng `[0,820000; 0,831000]`, vì chia đôi đơn thuần có thể bỏ qua trạng thái khả thi khi DD đổi theo bước lot. Nghiệm lớn nhất thỏa hai trần ở cả hai thứ tự giá là **0,824717**. Trọng số F5 là 1,0721321 và F3/F4 là 0,5773019. Commit `6bf0d85` khóa cấu hình trước khi mở dữ liệu sau Development cho ứng viên.

| Số đo với 1R = 150 USD | BASE_GUARD | P80_ISO_EXACT |
|---|---:|---:|
| Development 2018–2023 | +23,8524R | **+26,3791R** |
| DD Development | 12,2065R | **12,1885R** |
| Rủi ro mở tối đa, Development | 312,80 USD | **257,52 USD** |
| 2024–13/10/2026 | **+18,5393R** | +16,1026R |
| Toàn kỳ | +42,3917R | +42,4817R |
| DD toàn kỳ | 12,2065R | 12,1885R |

Mỗi kịch bản lịch sử chạy 105 mốc Challenge và một tài khoản Funded độc lập ở cả hai thứ tự giá. Hai thứ tự cho cùng số dưới đây.

| Kịch bản | Qua hai vòng, BASE → ISO | Trung vị tháng trong nhóm hoàn tất, BASE → ISO | Payout Funded độc lập, BASE → ISO |
|---|---:|---:|---:|
| Phí chuẩn | 71 → 69 | 48,06 → 41,82 | 6.471,13 → 6.742,25 USD |
| Phí +50% | 15 → 57 | 40,93 → 43,00 | 4.184,00 → 5.062,70 USD |
| Stress giá thiếu | 0 → 1 | — → 22,63 | 1.824,95 → 2.301,85 USD |

Tổng payout mô phỏng qua các cửa sổ Challenge chồng lấn lần lượt là 61.933,06 → 97.059,05 USD, 3.275,95 → 30.823,98 USD và 0 → 0 USD. Cửa sổ chồng lấn là các lần mô phỏng cùng lịch sử. Các tổng này không đại diện cho một tài khoản.

| Hoàn tất hai vòng trong | BASE_GUARD | P80_ISO_EXACT |
|---|---:|---:|
| 12 tháng | 1,38% | 1,42% |
| 18 tháng | 6,20% | 5,40% |
| 24 tháng | 14,50% | 12,50% |
| 36 tháng | 33,56% | 30,06% |

Bootstrap chuẩn dùng cùng 5.000 chuỗi cho mỗi thứ tự giá, với 20.000 sổ Challenge/Funded được đối soát ở phía ISO. Payout Funded độc lập trung bình năm giảm từ 946,41 xuống 924,28 USD trong bootstrap. Phí +50% và stress giá thiếu được so trên 105 mốc lịch sử. Lịch sử 2024–2026 đã được dùng trong các chiến dịch trước.

ISO giảm DD và chịu kịch bản tăng phí tốt hơn. Kết quả chuẩn vẫn hụt hai mốc lịch sử và giảm tỷ lệ hoàn tất bootstrap từ tháng 18. Kịch bản thiếu giá chỉ có 1/105 mốc hoàn tất. **Giữ BASE_GUARD làm baseline nghiên cứu và giữ trạng thái chưa đủ điều kiện Challenge.**

## 3. Bot Lab và kho preset/report

`--inspect` nhận `.set/.ini/.chr` và `.htm/.html/.xml`. Bộ đọc giữ giá trị tham số và các trường optimization riêng. Báo cáo được tách header, Orders và Deals. `--clone-log` nhận bảng giao dịch đóng hoặc các cặp có ticket/position xác định và khối lượng khớp. Múi giờ báo cáo phải được khai báo khi timestamp thiếu offset. [Hướng dẫn Bot Lab](BOT-REVERSE-LAB-PLAYBOOK.md) · [MT4 Results](https://www.metatrader4.com/en/trading-platform/help/overview/strategy_tester/strategy_tester_results) · [MT5 Testing Report](https://www.metatrader5.com/en/terminal/help/algotrading/testing_report)

Rà 55.744 đường dẫn trong phạm vi D/E đã khai báo, mở 75 file có ngữ cảnh phù hợp, gồm 60 file `.set` (12 hash khác nhau), 14 file `.ini` và một HTML nhận diện nhầm. Sáu hồ sơ nhận gợi ý liên kết theo tên hoặc thư mục. Không có báo cáo Strategy Tester sử dụng được trong các file đã mở. Bộ đọc được kiểm với fixture MT4/MT5 và XML. Hai lượt rà đầu được giữ vì đã phát hiện liên kết tên quá rộng và lỗi dùng đuôi file cho tên phiên bản artifact.

## 4. Cách ly job, tính toàn vẹn và hiệu năng

Các tiến trình scan, replay và phân tích V26 đã chạy với thư mục kết quả, thư mục tạm, manifest và khóa writer riêng. Tiến trình thử ghi vào một job còn chạy bị từ chối và khóa hiện tại giữ nguyên. Sau khi dispatcher bị ngắt, đối soát PID và journal cho phép giữ phần đã hoàn tất và chạy tiếp các dải còn thiếu. 43 bảng Zstandard được giải nén và kiểm SHA256, từ 192.112.163 xuống 7.710.942 byte. Journal gốc và các lần thử được giữ lại.

Launcher Trader PR #33 đã qua kiểm tra cấu hình cách ly trên workspace. Kiểm chứng vận hành thực tế thuộc các job nghiên cứu V26. API Trader và cơ sở dữ liệu dịch vụ chưa được chuyển sang một runtime mới.

Lần đo cuối có **1.400 test pass, 0 skip**, giữ 1.358 ID của V25. Full suite mất **32,38 giây** và **0/10** lượt smoke dưới 0,70 giây, tối đa **1,321 giây**. Cả hai mục tiêu tốc độ chưa đạt. Đo trên ổ D đã phát hiện lỗi tuổi tick do lấy giờ trước khi đọc báo giá. Bản sửa chuyển mốc đo đến sau lần đọc và kiểm lại bằng đồng hồ cố định. Receipt giữ cả lần đo ổ E và lần fail trước bản sửa.
