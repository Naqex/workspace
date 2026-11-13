# XAUUSD Intraday B0/A0 — kết quả cố định 2022–2024

**Không đưa B0 vào challenge.** Đã chạy đúng một phiên bản: 37 lệnh Development 2022–2023 lỗ 269,80 USD dưới phí stress; 30 lệnh Historical Validation 2024 lỗ 451,15 USD. Tổng cộng 67 lệnh: stress −720,95 USD (−4,8063R0), chuẩn −232,95 USD. Mỗi sổ năm bắt đầu lại với 50.000 USD; chưa mô phỏng một tài khoản chạy liên tục hoặc đầy đủ quy trình quỹ.

Trạng thái: `ECONOMIC_FAIL` + `CADENCE_OR_SAMPLE_SHORTFALL`; kiểm định quỹ vẫn là `PROP_UNMEASURED`. Kết quả chỉ áp dụng cho bản B0 này. EURUSD B1 đã hủy theo quyết định của chủ project, không chuyển lượt thử sang Gold. PR #72 đã merge tại `7ee9ace`, nhánh cũ đã xóa. Không đọc giá 2025–2026.

## 1. Luật và luồng dữ liệu

[Card đã duyệt](XAUUSD-INTRADAY-B0-PROPOSAL-20261113.md) và [protocol](XAUUSD-INTRADAY-B0-PROTOCOL-20261113.md) giữ luật gốc. Luồng chính: M1 Bid → nến H1/M15 đã đóng → tín hiệu → giá Bid/Ask thực tế → SL tự nhiên và khối lượng có dự phòng phí → kiểm trần phí 12% → kiểm vị thế và trần 2 lệnh/ngày → theo từng tick đến SL, TP hoặc hết 120 phút → sổ tiền chuẩn và stress.

Giữ nguyên SMA20, độ dốc qua 3 nến H1, vùng ±0,20ATR, đệm SL 0,10ATR, TP bằng 2 lần khoảng cách giá tới SL, cửa vào 09:00–16:00 UTC. R0 = 150 USD, cố định theo 0,30% vốn đầu 50.000 USD. Hai chế độ phí dùng **cùng khối lượng đã dự phòng phí stress và cùng danh sách lệnh**; không nới SL.

Commission 0,0007% giá trị danh nghĩa mỗi chiều là biểu phí tham chiếu đã được duyệt, [đối chiếu nguồn FTMO ngày 13/11/2026](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/). Chưa xác minh phí đúng tài khoản đích hoặc phí lịch sử 2022–2024. Slippage chuẩn bằng 0; stress bằng 0,20 USD/oz/chiều, tương đương 40 USD/lot cả vòng. Gross đã chứa spread từ Bid/Ask, không trừ lần hai. Contract 100 oz/lot, bước lot 0,01, bước giá 0,001 và đòn bẩy 1:10 là giả định nghiên cứu đã khai báo.

## 2. Phễu tín hiệu và chi phí

Đơn vị thay đổi từ ngày → giờ H1 → nến M15 → tín hiệu, không phải mọi cột là phép trừ cùng mẫu số. Một giờ H1 có thể bao nhiều nến M15. Không áp lịch tin/nghỉ lễ lịch sử vì chưa admit được, không gọi là đã lọc tin.

| Năm | Ngày nguồn | Giờ H1 có hướng | M15 có hướng/đủ | Trước phí | Loại phí | Tỷ lệ loại | SL loại USD/oz | SL qua phí | SL fills | Cap2 chặn | Đang giữ chặn | SLinvalid | Fills |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022 | 258 | 1317 | 5082/6963 | 399 | 372 | 93,23% | 2,143 | 6,747 | 6,740 | 0 | 1 | 2 | 24 |
| 2023 | 257 | 1263 | 4867/6934 | 414 | 400 | 96,62% | 1,692 | 7,998 | 7,998 | 0 | 0 | 1 | 13 |
| 2024 | 259 | 1323 | 5110/6992 | 390 | 359 | 92,05% | 2,243 | 7,873 | 7,994 | 0 | 1 | 0 | 30 |

Đối soát phễu: 2022 có 399 = 372 loại vì phí + 2 SL không hợp lệ + 1 đang giữ vị thế + 24 lệnh vào. Năm 2023: 414 = 400 + 1 + 13. Năm 2024: 390 = 359 + 1 đang giữ vị thế + 30 lệnh vào. Không có trường hợp thiếu giá vào, không đủ lot/margin hoặc phải chờ nến mới. **Trần 2 lệnh/ngày không chặn lệnh nào.** SL trung vị của nhóm bị loại chỉ 1,69–2,24 USD/oz, so với 6,74–7,99 USD/oz của lệnh thực vào. Chưa chạy các lệnh bị loại nên chưa biết nới trần phí sẽ cải thiện hay làm xấu kết quả.

| Năm | Ngày có fills | Tháng0 lệnh | Monthly fills Jan→Dec | Friction/R0 kế hoạch median |
|---|---|---|---|---|
| 2022 | 23 | 2 | 3,7,4,1,1,1,3,1,0,2,1,0 | 10,38% |
| 2023 | 13 | 4 | 2,1,1,4,1,0,0,1,0,1,0,2 | 8,26% |
| 2024 | 28 | 2 | 1,2,2,0,5,6,2,3,1,6,2,0 | 9,42% |

Đối chiếu phí trên lệnh đã vào: lấy spread tại entry cộng commission thực tế và slippage khai báo, chia R0. Đây là thước đo ma sát tham chiếu; chưa phải phép so khớp với một lệnh giả định trên giá mid độc lập.

| Năm | Median stress | P90 stress | Cao nhất stress | Vượt trần 12% |
|---|---|---|---|---|
| 2022 | 10,36% | 11,62% | 11,84% | 0 |
| 2023 | 8,25% | 11,05% | 11,88% | 0 |
| 2024 | 9,40% | 11,27% | 11,57% | 0 |

## 3. Phân rã lý do thoát

Chuẩn/Stress viết tắt C/S. Winrate tính theo số lệnh **lãi ròng > 0**. Danh sách lệnh và lý do thoát giống nhau ở hai chế độ phí.

| Năm | Exit | Lệnh | Winrate C | Winrate S | NetR C | NetR S |
|---|---|---|---|---|---|---|
| 2022 | TP_2R | 2 | 100,0% | 100,0% | 3,6073 | 3,4766 |
| 2022 | SL | 6 | 0,0% | 0,0% | -5,5711 | -5,8858 |
| 2022 | TIME_STOP_2H | 16 | 62,5% | 62,5% | 4,2794 | 3,4501 |
| 2022 | SESSION_CLOSE_1800 | 0 | — | — | 0,0000 | 0,0000 |
| 2023 | TP_2R | 0 | — | — | 0,0000 | 0,0000 |
| 2023 | SL | 5 | 0,0% | 0,0% | -4,5721 | -4,8147 |
| 2023 | TIME_STOP_2H | 8 | 50,0% | 50,0% | 2,3219 | 1,9752 |
| 2023 | SESSION_CLOSE_1800 | 0 | — | — | 0,0000 | 0,0000 |
| 2024 | TP_2R | 1 | 100,0% | 100,0% | 1,7930 | 1,7503 |
| 2024 | SL | 8 | 0,0% | 0,0% | -7,4447 | -7,8527 |
| 2024 | TIME_STOP_2H | 21 | 57,1% | 52,4% | 4,0334 | 3,0947 |
| 2024 | SESSION_CLOSE_1800 | 0 | — | — | 0,0000 | 0,0000 |

| Cộng3năm | Lệnh | Winrate C | Winrate S | NetR C | NetR S | NetUSD S |
|---|---|---|---|---|---|---|
| TP_2R | 3 | 100,0% | 100,0% | 5,4003 | 5,2269 | 784,04 |
| SL | 19 | 0,0% | 0,0% | -17,5879 | -18,5533 | -2.782,99 |
| TIME_STOP_2H | 45 | 57,8% | 55,6% | 10,6347 | 8,5200 | 1.278,00 |
| SESSION_CLOSE_1800 | 0 | — | — | 0,0000 | 0,0000 | 0,00 |

45/67 lệnh (67,2%) thoát do hết 120 phút; chỉ 3 lệnh (4,5%) chạm TP. Nhóm hết giờ đang **lãi 1.278 USD dưới phí stress**, chưa đủ bù nhóm SL lỗ 2.782,99 USD, dù nhóm TP đóng góp 784,04 USD. Bảng này chưa chứng minh bỏ giới hạn 2 giờ sẽ lời hơn, hoặc đã cắt non lệnh thắng. Không đọc giá sau khi thoát để thử cách giữ mới.

Không có `SESSION_CLOSE_1800` vì mọi lần vào đều trước 16:00 UTC, nên hạn 120 phút đến trước 18:00. TP đặt theo khoảng cách giá tới SL; sau phí và làm tròn lot, nhóm TP đạt trung bình khoảng 1,74R0/lệnh dưới phí stress.

## 4. BUY/SELL theo năm

Gross là lãi/lỗ sau spread thực tế. Phí chuẩn gồm commission; phí stress thêm slippage. Đơn vị các cột tiền là USD.

| Năm | Chiều | Lệnh | GrossUSD | Commission | Stressslip | NetUSD C | NetUSD S | NetR C | NetR S |
|---|---|---|---|---|---|---|---|---|---|
| 2022 | BUY | 13 | 331,64 | 6,55 | 100,00 | 325,09 | 225,09 | 2,1673 | 1,5006 |
| 2022 | SELL | 11 | 27,95 | 5,71 | 91,20 | 22,24 | -68,96 | 0,1483 | -0,4597 |
| 2023 | BUY | 7 | -507,41 | 3,16 | 46,00 | -510,57 | -556,57 | -3,4038 | -3,7105 |
| 2023 | SELL | 6 | 175,95 | 2,91 | 42,40 | 173,04 | 130,64 | 1,1536 | 0,8709 |
| 2024 | BUY | 24 | -133,96 | 14,60 | 172,00 | -148,56 | -320,56 | -0,9904 | -2,1371 |
| 2024 | SELL | 6 | -91,14 | 3,05 | 36,40 | -94,19 | -130,59 | -0,6279 | -0,8706 |

BUY cộng ba năm lỗ 652,04 USD dưới phí stress; SELL lỗ 68,91 USD. Chiều tốt thay đổi theo năm: BUY dương năm 2022 nhưng âm 2023–2024; SELL dương 2023 nhưng âm 2022 và 2024. Chưa có cơ sở chuyển sang chỉ BUY hoặc chỉ SELL.

Tổng gross ba năm −196,97 USD, commission 35,98 USD, slippage 488 USD → net stress −720,95 USD. Ngay cả phí chuẩn cũng âm. Riêng Development, gross chỉ +28,13 USD trên 6,99 lot, tức 4,02 USD/lot, so với commission + slippage stress 42,62 USD/lot. Không mang tỷ lệ chi phí 6,4% của Gold R043 giữ nhiều ngày sang chiến lược intraday mới.

## 5. Đối chiếu Prop Target Envelope

Drawdown dưới đây tính cả **lãi/lỗ thả nổi trên tick**, mỗi sổ bắt đầu năm với 50.000 USD. Mốc lỗ ngày lấy balance đầu ngày. Tất cả vị thế đóng trước 18:00 UTC, nên trong mô hình này không có vị thế hoặc phí đi qua mốc reset 00:00 Europe/Prague. Chưa mô phỏng chuyển giai đoạn challenge, chốt target hoặc payout.

| Năm | Phí | Cadence | NetUSD | MeanNetR | AnnualNetR | Max equityR-DD | EquityDD USD | WorstdayUSD | Worstday%50k | Maxfills/ngày |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022 | C | 24 | 347,33 | 0,0965 | 2,3155 | 4,0830 | 612,45 | 279,43 | 0,5589% | 2 |
| 2022 | S | 24 | 156,13 | 0,0434 | 1,0409 | 4,5514 | 682,71 | 293,03 | 0,5861% | 2 |
| 2023 | C | 13 | -337,53 | -0,1731 | -2,2502 | 3,6442 | 546,63 | 140,41 | 0,2808% | 1 |
| 2023 | S | 13 | -425,93 | -0,2184 | -2,8395 | 4,0255 | 603,83 | 149,61 | 0,2992% | 1 |
| 2024 | C | 30 | -242,75 | -0,0539 | -1,6183 | 4,8087 | 721,31 | 248,65 | 0,4973% | 2 |
| 2024 | S | 30 | -451,15 | -0,1003 | -3,0077 | 5,1849 | 777,74 | 257,65 | 0,5153% | 2 |

| Gateowner | Kết quả | Quyết định |
|---|---|---|
| Cadence≥60/năm; ưu tiên120 | 24/13/30; 2/4/2tháng trắng | FAIL |
| NetR/year dương bền; dải25–40R banđầu | Stress+1,0409/−2,8395/−3,0077R | FAIL |
| EquityDD≤15R; internaldaily<2,5%; staticloss<6,5% | Worstannual5,1849R=777,74USD=1,5555%; worstdaily0,5861%; worststatic521,55USD=1,0431% | Trongbuffer của conditionalmodel; không prop-pass |
| Tốc độ planning12tháng tại0,30% | Cần khoảng50R tổng2phase; chưa có pacebền | FAIL/phasepathchưađo |
| Targetspec/calendar/news/datedsession | Chưaadmit | BLOCKED/PROP_UNMEASURED |

Lệnh lỗ lớn nhất dưới phí stress là 151,79 USD = 1,0119R0, vượt ngân sách 150 USD do giá khớp SL thực tế. Vì vậy 2 × 0,30% = 0,60% chỉ là rủi ro dự kiến, **không phải trần lỗ ngày được bảo đảm**. Cả 67 lệnh có giá thoát trước 18:00 UTC; không khoảng trống quote nào khi đang giữ lệnh vượt 60 giây, lớn nhất là 26,095 giây. Swap bằng 0 trong kịch bản phiên thông thường đã khai báo; chưa chứng minh giờ rollover của tài khoản đích. Không quét tăng sizing để cứu kỳ vọng đang âm.

## 6. Dữ liệu, đối soát và giới hạn

- 30.403.243 tick trong 2.255 giờ được chọn; 135.281/135.281 phút Bid OHLC khớp sau ba hiệu chỉnh. Không có phút có tick mà thiếu M1. Phạm vi chỉ gồm các giờ cần cho tín hiệu và giữ lệnh, chưa chứng nhận toàn bộ dữ liệu ba năm hoặc một feed độc lập.
- Giữ lần kiểm tra `tick-view-v1` bị chặn: ba phút M1 lệch, 237 quote ngoài khoảng giá M1 cũ. Đã đối soát 58.483 quote của ba giờ liên quan với bộ giải mã gốc về thời gian, Bid/Ask, volume và thứ tự. Sửa lớp M1 dẫn xuất trước khi có kết quả tài chính; CSV/cache gốc giữ nguyên. Số tín hiệu, thời điểm tín hiệu và SL không đổi. Giữ các lần preflight lỗi cùng snapshot và bản ghi thay đổi.
- 11 kiểm thử đạt; thêm suite XAU vào CI. **Tự đối soát bằng cách tính riêng**, không phải review độc lập của agent khác: 134 lượt đối chiếu lệnh/chế độ phí bằng Decimal và 2.035.213 lần đo giá thả nổi. Giá vào, thứ tự tick cùng thời điểm, lần chạm SL/TP đầu tiên, hạn thoát, phí, cash, drawdown và tổng theo chiều/lý do thoát/tháng đều khớp.
- Đóng băng 125 tệp code/protocol/native/provider; Python 3.12.10, Pydantic 2.13.5. Trader giữ pin `930fa76`; không stage WIP của VI Dubber.
- Năm 2024 đã có exposure lịch sử, chưa là OOS sạch. Không đọc giá 2025–2026, không gọi broker hoặc thử A1/B1.
- Lịch tin, phiên nghỉ lễ và thông số tài khoản đích chưa đủ: `BLOCKED_BY_CALENDAR_AND_TARGET_SPEC`. Không loại lệnh sau khi biết kết quả bằng lý do tin tức.

Privateevidence: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\xauusd-intraday-b0-20261113`. Registration`registration.json`, source`tick-view-v2/seal.json`, frozen`source-snapshot-v2`, outcomes`attempt-1/result.json`, trades`2022/2023/2024-details.json`, review`arithmetic-path-review.json`. [JSONdossier](XAUUSD-INTRADAY-B0-RESULTS-20261113.json) giữ hash/locator/số liệu.

## 7. Thời gian và hậu kiểm kỹ thuật

| Phase | Wallđo được | Kết luận |
|---|---|---|
| Downloadnative2255hours | 1.061,31s | I/O lớn nhất; có boundedtimeouts/recovery, không tải lại khi sửaM1 |
| Firstsourcecheck bị chặn | 145,53s | Guard bắt3source revisions trước PnL |
| Correctedsourcecheck | 147,75s | 30,4Mticks + exactOHLCcheck; giữ semantics |
| Financialrun3năm×2cost | 20,25s / CPU19,91s | Đã đủ nhanh; không có bằng chứng cầnGPU/Rust |
| Code/review/manual/report | Chưa đo đủ | Không suy thời gianLlm từ CPUtimer |

Độ đúng: giữ kiểm tra nguồn và làm tròn tiền; đã sửa lỗi biên giờ và hiệu chỉnh nguồn trước kết quả tài chính. Độ ổn định: tải dữ liệu có một writer, deadline, ngân sách retry, cache và lịch sử lỗi. Hiệu năng: dùng lại toàn bộ dữ liệu thô 2.255 giờ sau hiệu chỉnh, không tải lại mạng; chưa làm benchmark để tuyên bố tỷ lệ tăng tốc. Bảo trì: dùng lại native sizing, Account, decoder và provider; phần Gold chỉ bổ sung phí theo giá trị danh nghĩa từng chiều. Không cần tạo skill mới: guard đã có bắt được lỗi, kiểm thử hồi quy giữ bài học cụ thể.

**Đề xuất:** gác bản A0/B0 này khỏi challenge. Chưa tự chạy A1/B1, tăng risk, bỏ SELL hoặc giữ lâu hơn sau khi xem kết quả. Nghiên cứu kế tiếp cần một cơ chế kinh tế và khả năng tạo đủ cơ hội sau phí được đăng ký trước. Giữ lịch sử 67 lệnh và ba hiệu chỉnh dữ liệu; không đặt lại ngân sách thử nghiệm.
