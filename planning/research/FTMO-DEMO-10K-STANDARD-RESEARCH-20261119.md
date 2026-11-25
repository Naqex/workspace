# FTMO Demo 10k Standard · phí khớp, ATR và khả năng tăng quy mô

Phép đo sau ở quy mô 0,10–1,00 lot xác nhận commission FX 5,00 USD/lot khứ hồi
và mở rộng ATR từ 5 lên 13 mã. Xem [bản đối soát mới](FTMO-DEMO-10K-STANDARD-FULL13-AND-EXECUTION-20261119.md).

Ngày 19/11/2026. Đã xác nhận **13 mã** trên FTMO-Demo USD 10k, đòn bẩy tài khoản **1:100**. Bốn phép thử 0,01 lot khớp đủ mở và đóng. Kết thúc với **0 vị thế, 0 lệnh chờ** và đối chiếu số dư khớp đến cent. EURUSD và US500.cash có chi phí H4 thấp nhất trong năm mã có dữ liệu đại diện. XAUUSD vẫn đáng nghiên cứu ở H4 nếu kiểm soát thời gian giữ BUY.

Phép so dùng phí Demo quan sát ngày 19/11/2026 và ATR mô tả Development 2023. Các quy mô 50k, 100k và 200k dùng điều kiện 10k làm giả định. Cả ba quy mô có trong 2-Step. Biểu phí và bậc margin của từng tài khoản lớn hơn cần xác nhận riêng. [Mức vốn 2-Step](https://ftmo.com/en/2-step-challenge/) · [Scaling Plan](https://ftmo.com/en/reward-growth-and-scaling-plan/).

## 1. Spec và chi phí của 13 mã

Lot tối thiểu và bước lot đều **0,01**, stops level **0 point** trên 13 mã tại thời điểm chụp. Margin trong bảng là USD ước tính cho BUY **0,01 / 1,00 lot**. JSON có cả SELL và giá tham chiếu. Đòn bẩy theo mã là giá trị danh nghĩa quy USD chia margin 1 lot. [MT5 OrderCalcMargin](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcmargin_py).

Spread và phí gộp dùng pip với FX, USD/oz với XAUUSD và điểm với US500.cash. Phí gộp bằng spread trung vị cộng commission quy đổi, chưa gồm slippage, swap hay fee khác. Swap là USD/lot cho rollover hệ số 1, quy từ point theo tick value quan sát. [Đơn vị swap MT5](https://www.mql5.com/en/book/automation/symbols/symbols_swaps).

| Mã repo → MT5 | Contract / tick size | Margin USD 0,01 / 1 lot · leverage | Spread med / P95 / max · n | Commission USD/lot RT | Phí gộp med | Swap BUY / SELL USD · 3× |
|---|---:|---:|---:|---:|---:|---:|
| EURUSD | 100000 / 0.00001 | 10.99 / 1099.26 · 1:100 | 0.10 / 0.30 / 0.30 · 139 | 6.00 | 0.70 | −8.470 / +0.290 · T4 |
| GBPUSD | 100000 / 0.00001 | 13.15 / 1314.66 · 1:100 | 0.70 / 0.80 / 0.80 · 91 | 6.00 ước tính | 1.30 | −4.580 / −5.330 · T4 |
| AUDUSD | 100000 / 0.00001 | 6.71 / 670.57 · 1:100 | 0.40 / 0.40 / 0.40 · 77 | 6.00 ước tính | 1.00 | −2.450 / −7.050 · T4 |
| USDJPY | 100000 / 0.00100 | 10.00 / 1000.00 · 1:100 | 0.30 / 0.80 / 0.90 · 44 | 6.00 ước tính | 1.26 | +1.651 / −12.090 · T4 |
| USDCHF | 100000 / 0.00001 | 10.00 / 1000.00 · 1:100 | 0.50 / 0.60 / 0.60 · 72 | 6.00 ước tính | 1.01 | +2.314 / −16.044 · T4 |
| USDCAD | 100000 / 0.00001 | 10.00 / 1000.00 · 1:100 | 0.40 / 0.60 / 0.60 · 71 | 6.00 ước tính | 1.26 | +0.496 / −7.561 · T4 |
| NZDUSD | 100000 / 0.00001 | 5.52 / 552.23 · 1:100 | 0.60 / 0.60 / 0.60 · 55 | 6.00 ước tính | 1.20 | −4.800 / +0.000 · T4 |
| EURGBP | 100000 / 0.00001 | 10.99 / 1099.26 · 1:100 | 0.50 / 0.60 / 0.60 · 84 | 6.00 ước tính | 0.96 | −8.939 / +0.197 · T4 |
| EURJPY | 100000 / 0.00100 | 10.99 / 1099.26 · 1:100 | 0.90 / 1.10 / 1.10 · 163 | 6.00 ước tính | 1.86 | +1.320 / −6.974 · T4 |
| GBPJPY | 100000 / 0.00100 | 13.15 / 1314.66 · 1:100 | 2.40 / 2.80 / 3.10 · 117 | 6.00 | 3.36 | +3.672 / −15.731 · T4 |
| AUDJPY | 100000 / 0.00100 | 6.71 / 670.57 · 1:100 | 1.00 / 1.20 / 1.30 · 89 | 6.00 ước tính | 1.96 | +2.358 / −9.538 · T4 |
| XAUUSD | 100 / 0.01000 | 74.55 / 7455.06 · 1:50 | 0.35 / 0.39 / 0.40 · 204 | 6.00 | 0.41 | −56.560 / −4.200 · T4 |
| US500 → US500.cash | 1 / 0.01000 | 1.48 / 147.93 · 1:50 | 0.60 / 0.60 / 0.60 · 108 | 0.00 | 0.60 | −0.873 / −0.888 · T6 |

Commission gắn “ước tính” lấy EURUSD làm tham chiếu cho FX chính và GBPJPY cho FX chéo. Mỗi mã đã thử có một vòng 0,01 lot. Ví dụ, 0,03 USD mỗi phía ở 0,01 lot quy tuyến tính thành 6 USD/lot khứ hồi. Làm tròn đến cent ở lot nhỏ có thể làm số quy đổi lệch biểu phí ở 1,00 lot.

MT5 báo lịch tuần từ thứ Hai tới thứ Sáu giờ server. FX mở **00:05–23:55**, Vàng và US500.cash **01:05–23:50**. Với offset **UTC+2** đã đo, lần lượt là **22:05 hôm trước–21:55 UTC** và **23:05 hôm trước–21:50 UTC**. Cutoff 20:30 UTC còn đệm **85 / 80 phút**. Reset 00:00 Prague vào **23:00 UTC**, tức 01:00 server. Giữa tuần, FX đã mở lại lúc reset còn Vàng/chỉ số mở lại sau 5 phút. [Đồng hồ MT5 và Prague theo FTMO](https://ftmo.com/en/blog/trading-updates/trading-update-22-oct-2026//).

### Bốn vòng khớp lệnh Demo 0,01 lot

BUY thị trường rồi SELL đóng đúng ticket vị thế. Trượt giá dương nghĩa là bất lợi. Độ trễ trong bảng là từ lúc gọi SDK đến khi nhận phản hồi trên máy. JSON giữ thêm timestamp deal và thời gian xử lý theo đồng hồ server ở những lượt đọc được.

| Mã | Giá tham chiếu → khớp BUY / SELL | Vòng gọi BUY / SELL (ms) | Giữ (s) | Commission mở / đóng · fee RT (USD) | Commission RT quy 1 lot / giá | Trượt RT | Profit đóng / cashflow (USD) |
|---|---|---:|---:|---:|---:|---:|---:|
| EURUSD | 1.09994 → 1.09995 / 1.09994 → 1.09994 | 354 / 350 | 2.609 | -0.03 / -0.03 · 0.00 | 6.00 USD / 0.600 | +0.10 | −0.01 / −0.07 |
| GBPJPY | 210.407 → 210.407 / 210.392 → 210.395 | 343 / 407 | 2.623 | -0.03 / -0.03 · 0.00 | 6.00 USD / 0.960 | −0.30 | −0.08 / −0.14 |
| XAUUSD | 3726.81 → 3726.81 / 3726.48 → 3726.50 | 339 / 396 | 2.600 | -0.03 / -0.03 · 0.00 | 6.00 USD / 0.060 | −0.02 | −0.31 / −0.37 |
| US500.cash | 7405.55 → 7405.45 / 7404.65 → 7404.65 | 563 / 408 | 2.826 | 0.00 / 0.00 · 0.00 | 0.00 USD / 0.000 | −0.10 | −0.01 / −0.01 |

Tổng chênh số dư Demo **−0,59 USD**. EURUSD đo quy đổi 6 USD/lot RT, cao hơn commission B0 5 USD. B0 stress còn cộng 0,40 pip RT. Vàng đo 6 USD/lot RT, so với khoảng 5,22 USD theo công thức 0,0007% notional mỗi phía ở giá đo. Vàng stress cộng 0,40 USD/oz RT nếu hai phía đều market. US500.cash ghi 0 commission và fee ở 0,01 lot, phù hợp mô hình phí đích. GBPJPY chưa có proxy riêng trong mô hình chính. Một vòng mỗi mã chưa cho phân bố trượt giá.

## 2. Chi phí so với ATR và quy mô vị thế

ATR(14) Wilder là trung vị năm 2023, warmup từ 01/12/2022. Nến Bid H1 cần ít nhất 45 phút nếu nguồn M1, H4 cần đủ 4 H1 và D1 cần ít nhất 20 H1. Nhóm theo UTC, giữ khoảng trống. JSON có số nến và hash nguồn. Dữ liệu lịch sử 2024 trở đi chỉ tra metadata phạm vi. ATR của 8 mã thiếu chuỗi đại diện để trống.

Friction/ATR lấy spread trung vị cộng commission. Swap/ATR D1 dương khi tốn phí, âm khi được cộng. 3× là ba đơn vị swap theo snapshot. [Nguồn USDJPY R084](USDJPY-TOKYO-COMPONENT-RESULTS-20261109.md) · [Mở rộng R085](USDJPY-POSTFIX-EXTENSION-RESULTS-20261109.md).

| Mã | Nguồn local và giới hạn | ATR H1 / H4 / D1 | Friction / ATR H1 / H4 / D1 | Swap / ATR D1, BUY / SELL 1× → 3× |
|---|---|---:|---:|---:|
| EURUSD | M1 Bid V10 11/2017–2023. Metadata QDM M1/tick 2003–2026. | 13.06 / 27.70 / 74.78 | 5.36% / 2.53% / 0.94% | +1.13% / −0.04% → +3.40% / −0.12% |
| GBPUSD | H1 Bid/Ask 2017–2023. Thiếu đường M1 liên tục đã admission. | 17.38 / 36.44 / 96.16 | 7.48% / 3.57% / 1.35% | +0.48% / +0.55% → +1.43% / +1.66% |
| AUDUSD | H1 Bid/Ask 2017–2023. Thiếu đường M1 liên tục đã admission. | 12.70 / 26.64 / 67.76 | 7.88% / 3.75% / 1.48% | +0.36% / +1.04% → +1.08% / +3.12% |
| USDJPY | M1 Bid/Ask cho ngày mục tiêu rời rạc 2010–2023 theo R084/R085. | — | — | — |
| USDCHF | Chưa xác nhận H1/M1 liên tục trong kho đã rà. | — | — | — |
| USDCAD | Chưa xác nhận H1/M1 liên tục trong kho đã rà. | — | — | — |
| NZDUSD | Chưa xác nhận H1/M1 liên tục trong kho đã rà. | — | — | — |
| EURGBP | Chưa xác nhận H1/M1 liên tục trong kho đã rà. | — | — | — |
| EURJPY | Chưa xác nhận H1/M1 liên tục trong kho đã rà. | — | — | — |
| GBPJPY | Chưa xác nhận H1/M1 liên tục trong kho đã rà. | — | — | — |
| AUDJPY | Chưa xác nhận H1/M1 liên tục trong kho đã rà. | — | — | — |
| XAUUSD | M1 Bid V10 11/2017–2023. Metadata QDM 2003–2026. Ask proxy. | 4.13 / 9.40 / 23.86 | 9.92% / 4.36% / 1.72% | +2.37% / +0.18% → +7.11% / +0.53% |
| US500.cash | M1 Bid/Ask 2017–2023 theo sổ quý. Feed nghiên cứu khác FTMO, còn khoảng trống. | 9.03 / 20.63 / 52.86 | 6.64% / 2.91% / 1.14% | +1.65% / +1.68% → +4.95% / +5.04% |

### Bước lot và margin ở SL 1 × ATR

Ngân sách **0,50%** vốn mỗi vị thế, tương ứng 50 / 250 / 500 / 1.000 USD. Khoảng stop tính từ giá giữa, cộng spread trung vị và commission vào lỗ theo lot. Làm tròn xuống bước 0,01 rồi chặn theo margin ước tính ở phía tốn hơn. Chưa đưa gap, swap, slippage stress, vị thế đồng thời hoặc margin động vào phép tính. Cột 100k và số USD nằm trong JSON.

| Mã | SL | 10k lot / margin % | 50k lot / margin % | 200k lot / margin % | Lỗ ở lot sàn (USD) |
|---|---|---:|---:|---:|---:|
| EURUSD | 1 × ATR H4 | 0.17 / 1.87% | 0.88 / 1.93% | 3.52 / 1.93% | 2.84 |
| EURUSD | 1 × ATR D1 | 0.06 / 0.66% | 0.33 / 0.73% | 1.32 / 0.73% | 7.55 |
| GBPUSD | 1 × ATR H4 | 0.13 / 1.71% | 0.66 / 1.74% | 2.64 / 1.74% | 3.77 |
| GBPUSD | 1 × ATR D1 | 0.05 / 0.66% | 0.25 / 0.66% | 1.02 / 0.67% | 9.75 |
| AUDUSD | 1 × ATR H4 | 0.18 / 1.21% | 0.90 / 1.21% | 3.61 / 1.21% | 2.76 |
| AUDUSD | 1 × ATR D1 | 0.07 / 0.47% | 0.36 / 0.48% | 1.45 / 0.49% | 6.88 |
| XAUUSD | 1 × ATR H4 | 0.05 / 3.73% | 0.25 / 3.73% | 1.01 / 3.76% | 9.81 |
| XAUUSD | 1 × ATR D1 | 0.02 / 1.49% | 0.10 / 1.49% | 0.41 / 1.53% | 24.27 |
| US500.cash | 1 × ATR H4 | 2.35 / 3.48% | 11.77 / 3.48% | 47.11 / 3.48% | 0.21 |
| US500.cash | 1 × ATR D1 | 0.93 / 1.38% | 4.67 / 1.38% | 18.70 / 1.38% | 0.53 |

**5/5 mã tính được nằm trong ngân sách ở lot sàn trên 10k** với cả H4 và D1. XAUUSD D1 có bước tiền lớn nhất, khoảng 24,27 USD mỗi 0,01 lot. Với phí trung vị này, stop hơn khoảng 49,59 USD/oz khiến 0,01 lot vượt ngân sách 50 USD. US500.cash kịch bản 200k H4 ra khoảng 47 lot, cần đo lại bậc margin và thanh khoản theo khối lượng.

**Ưu tiên EURUSD và US500.cash** cho nghiên cứu chi phí và nguồn. EURUSD có M1/tick và friction H4 **2,53% ATR**. US500.cash ở **2,91%**, với swap 3× thứ Sáu khoảng **4,95–5,04% ATR D1** và yêu cầu lịch đóng sớm. **XAUUSD BUY giữ qua rollover 3×** chịu **7,11% ATR D1** và friction H1 **9,92% ATR**. **Tạm gác GBPJPY** ở cửa sổ hẹp hoặc SELL qua nhiều đêm vì spread trung vị cao nhất nhóm FX đã đo (**2,40 pip**), commission quy khoảng **0,96 pip** và thiếu ATR đại diện. GBPUSD/AUDUSD đủ H1 để đo thô, còn thiếu M1 cho kiểm đường stop. Edge, tần suất và khả năng qua quỹ vẫn chưa được kiểm trong lượt này.

## 3. Khoảng trống vận hành

| Hạng mục | Bằng chứng hiện có | Còn thiếu trước khi vận hành Standard |
|---|---|---|
| News Guard | Adapter có cửa sổ ±2 phút, có phase và chặn khi thiếu coverage. FTMO đánh dấu sự kiện Restricted. | Nguồn ingest tự động được xác minh, lưu thời điểm biết, quy UTC và mapping mã. Funded Standard áp cả SL/TP. [Luật tin FTMO](https://ftmo.com/en/faq/can-i-trade-news/) |
| Holiday / đóng sớm | MT5 có lịch tuần. FTMO công bố ngày/mã ngoại lệ. | Manifest có nguồn và hiệu lực theo ngày. 26/11/2026 US500.cash đóng 18:00 UTC, Vàng đóng 19:30 UTC, sớm hơn cutoff 20:30. Giữ exact_session_parity=false tới khi có lịch ngoại lệ. [Trading Updates](https://ftmo.com/en/trading-updates/) |
| Giờ ghi swap | Spec ghi ngày 3× theo mã. Repo có đối chiếu 17:00 New York cho EURUSD. | Timestamp hạch toán thực theo mã và qua DST. Bốn vòng thử đóng sau vài giây. [FTMO rollover](https://ftmo.com/en/blog/market-conventions-and-rollovers-on-nzd/) · [Audit repo](PROP-EUR-FX-ROLLOVER-AUDIT-20261119.md) |
| Spread theo phiên | Mẫu native cuối buổi sáng châu Âu. | Đo cửa sổ Á, Âu, Mỹ và trước/sau rollover trên nhiều ngày, giữ số quan sát và p50/p95/p99. Tách ngày tin và đóng sớm. |
| Quy mô 50k–200k | Đã tính dưới spec 10k. | Snapshot từng tài khoản đích, margin theo khối lượng, spread/slippage theo lot và margin danh mục. |

## Đối soát runner và nơi lưu

Bản cũ lưu 103 tick với thời gian giá trải **7,958 giây**, dù thời điểm nhận trải **53,407 giây**. Điểm lỗi được khoanh ở đường READ_ONLY dùng truy vấn lịch sử copy_ticks_range làm luồng live. Bản sửa lấy quote mới nhất mỗi 250 ms, bỏ bản lặp, giữ timestamp broker và thời điểm đọc riêng, ghi độ phủ từng mã. Probe ghi nhận quote trễ khoảng 5 giây so với host và truy vấn lịch sử thấy dữ liệu khi cửa sổ đủ rộng. Nguyên nhân nội bộ MT5 dẫn tới ranh giới 8 giây của lần cũ chưa xác minh. Đường đọc lịch sử trong shadow giữ hợp đồng cũ. [MT5 symbol_info_tick](https://www.mql5.com/en/docs/python_metatrader5/mt5symbolinfotick_py).

Ca hồi quy cho lịch sử đứng ở giây thứ 8 trong khi quote mới nhất tiếp tục. Bộ FTMO **66/66 PASS, 0 skip**. Một lượt native **120,016 giây** thu **1.314 báo giá**, trải **112,940 giây** theo dấu giờ broker, khoảng **110,3–112,6 giây/mã**. Mẫu đo giữ các quote thấy ở nhịp đọc và có thể bỏ qua tick giữa hai lần đọc.

Biên nhận send ban đầu trả DONE và deal=0. Đã lấy order và deal theo position để khớp 4 vòng. Một lỗi đọc tuple vị thế rỗng trong script thử đóng đã được sửa ở lượt tiếp nối. EURUSD và GBPJPY được đối soát từ ticket đã có, mỗi mã chỉ mở một lần. Toàn bộ process tree và lock đã dọn.

- [JSON đối soát](FTMO-DEMO-10K-STANDARD-RESEARCH-20261119.json).
- Kho private dưới E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/ftmo-demo-10k-standard-20261119/manifest.json. Spec và diff ở broker-spec/. Parquet Zstd tách trong prior-quotes/ và quotes-120s/. Deal giữ trong micro-probe/.
- SHA256 manifest 5a188b25ef5087c00ecfc5e11b585a19838f6c1871451ce1b0291eb7a9c9423f. Kho có 34 tệp đã đối soát hash và quét credential dạng rõ trước lưu.
- Inventory key ftmo-demo-10k-standard-20261119. Tra bằng research_inventory.py --key ftmo-demo-10k-standard-20261119 từ workspace root.
