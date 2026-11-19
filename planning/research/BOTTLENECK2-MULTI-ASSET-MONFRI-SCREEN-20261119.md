# Sàng lọc H4/D1 Mon–Fri từ dữ liệu FTMO native

**Gác cả ba họ trong cấu hình đã đăng ký.** Danh mục BREAKOUT, PULLBACK và SWEEP đều âm ở cả hai cụm Development, kể cả ở phí Base-Real trên toàn kỳ. Giữ qua đêm làm kết quả xấu thêm trên cả ba. USDJPY BREAKOUT là lát dương đáng lưu ý, nhưng chưa dương ở cụm đầu.

Protocol `f42ed22` đã commit trước phép đo. Lock được ghi trước khi runner tính tín hiệu. Mốc niêm phong **01/01/2025, giờ nền tảng**. Development gồm **2018–2024**, với A **2018–2020** và B **2021–2024**. Runner chỉ mở 18 Parquet Development. [Protocol](BOTTLENECK2-MULTI-ASSET-MONFRI-PROTOCOL-20261119.md) · [Lock](NATIVE_FTMO_HOLDOUT_LOCK.json) · [SHA256](NATIVE_FTMO_HOLDOUT_LOCK.sha256).

## Độ sâu, khoảng trống và exposure

Đã kiểm đủ **39 chuỗi, 1.740.707 bar** bằng dấu giờ và hash trước khi niêm phong. Ngày tháng theo đồng hồ server. H1/H4 chốt đến 19/11/2026, D1 đến 18/11/2026. Các số trong cột gap dùng H1 >3 giờ, H4 >12 giờ và D1 >36 giờ, sau khi tách mẫu cuối tuần thường và gap sát các ngày cuối năm. Chưa có lịch ngoại lệ broker cho mọi năm, vì vậy những gap còn lại có thể gồm ngày nghỉ, lịch phiên hoặc mất dữ liệu.

| Mã | Ngày đầu H1 / H4 / D1 | Bar H1 / H4 / D1 | Gap nghi vấn H1 / H4 / D1 |
|---|---|---:|---:|
| US500.cash | 2017-12-29 / 2017-12-29 / 2017-12-29 | 35235 / 9794 / 2298 | 667 / 626 / 9 |
| EURUSD | 2010-10-13 / 2000-03-29 / 2000-03-29 | 99998 / 41490 / 6924 | 1 / 1 / 1 |
| USDJPY | 2010-10-14 / 2000-03-29 / 2000-03-29 | 99998 / 41478 / 6923 | 1 / 2 / 1 |
| EURJPY | 2014-10-22 / 2002-09-10 / 2000-03-29 | 75062 / 37658 / 6797 | 1 / 1 / 7 |
| GBPUSD | 2010-10-04 / 2000-03-29 / 2000-03-29 | 99998 / 41454 / 6923 | 11 / 9 / 1 |
| XAUUSD | 2010-03-19 / 2004-06-11 / 2004-06-11 | 99998 / 34406 / 5774 | 151 / 61 / 57 |

**Có dữ liệu theo năm từ 2018 nhưng độ sâu H1/H4 của US500.cash chỉ đủ từ 2021.** Năm 2018–2020 có đúng 258–259 quan sát H1 và H4 mỗi năm, bằng quy mô D1. Vì vậy US500.cash ở cụm A thiếu đường intraday để định giá hầu hết intent. Cụm B vẫn đo được H1 và cũng âm trên danh mục. Mô phỏng dừng path thiếu giá, giữ reason và bỏ khỏi kinh tế đã định giá.

| Năm | H1 nhỏ nhất trong 6 mã | H4 nhỏ nhất | D1 nhỏ nhất |
|---:|---:|---:|---:|
| 2018 | 258 | 258 | 258 |
| 2019 | 259 | 259 | 258 |
| 2020 | 259 | 259 | 259 |
| 2021 | 5621 | 1479 | 259 |
| 2022 | 5893 | 1540 | 258 |
| 2023 | 5893 | 1540 | 257 |
| 2024 | 5920 | 1548 | 259 |
| 2025 | 5883 | 1540 | 258 |
| 2026 | 5240 | 1369 | 228 |

EURUSD, US500 và XAUUSD có exposure ở các kỳ cũ. GBPUSD đã có S01/F5. USDJPY từng được nghiên cứu qua R084/R085. Chưa tìm thấy kết quả chiến lược EURJPY trong chỉ mục. Cả 13 mã đã có exposure ATR tổng hợp tại `36f1535`. Lock bảo vệ phần giá và PnL của phép thử mới, với giới hạn exposure đã biết được ghi ngay trong lock. [USDJPY R084](USDJPY-TOKYO-COMPONENT-RESULTS-20261109.md) · [USDJPY R085](USDJPY-POSTFIX-EXTENSION-RESULTS-20261109.md).

## Kinh tế danh mục Mon–Fri

Bảng theo **Stress-Real**, sổ 10k trừ cột USD 50k. Phí và swap tính theo tổng R của bảy năm. Swap âm nghĩa là bị thu. Top 5/10 tính theo phần đóng góp trong tổng lãi của các lệnh dương. DD dùng đường H1 mark-to-market. Model 50k dùng spec 10k.

| Họ | Lệnh/năm | Win | R/lệnh | R/năm A / B | R/năm Base / Stress | Max DD (R) | Net R / DD | USD/năm 10k / 50k | Spread+com / slip / swap (R) | Top 5 / 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BREAKOUT | 293.3 | 29.6% | -0.11 | -21.58 / -38.25 | -26.26 / -31.10 | 260.30 | -0.84 | -1555.18 / -8118.38 | 55.86 / 40.53 / -41.68 | 4.9% / 8.7% |
| PULLBACK | 200.9 | 27.5% | -0.18 | -29.54 / -39.52 | -31.47 / -35.24 | 267.45 | -0.92 | -1762.07 / -9194.09 | 41.00 / 31.25 / -34.64 | 6.6% / 11.9% |
| SWEEP | 326.0 | 30.6% | -0.12 | -47.23 / -34.99 | -33.03 / -40.24 | 298.64 | -0.94 | -2011.98 / -10449.21 | 100.71 / 69.13 / -46.34 | 3.9% / 7.3% |

R tính theo ngân sách 50 hoặc 250 USD, có làm tròn lot và chặn tổng margin. Mức tối thiểu để xét tiếp là 15R/năm, còn 30R/năm tương ứng 1.500 USD/năm trên 10k hoặc 7.500 USD/năm trên 50k. DD trong bảng đo trên nến H1 theo mô phỏng, nên chưa đo giới hạn Daily/Overall Loss của FTMO.

### Stage-0 và nguyên nhân dừng

Markout cố định +24 giờ hoặc chặn thứ Sáu sớm hơn, trước SL/TP. Số liệu tính theo R chuẩn hóa từng tín hiệu và có chồng lấn. Phí/stop và tỷ lệ giữ dùng lưới kiểm 12% trên mẫu có giá.

| Họ | Tín hiệu thô / có markout | Gross (R) | Spread + commission | Slippage | Swap (R) | Net (R) | Năm dương / 7 | Phí/stop · giữ ở 12% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BREAKOUT | 4744 / 4223 | +28.05 | 116.52 | 86.45 | -73.78 | -248.71 | 2/7 | 3.5% · 94.7% |
| PULLBACK | 1648 / 1601 | -183.99 | 48.88 | 36.53 | -40.14 | -309.55 | 0/7 | 4.2% · 93.1% |
| SWEEP | 3213 / 3032 | -304.25 | 144.99 | 106.89 | -121.80 | -677.92 | 1/7 | 5.6% · 76.7% |

- **BREAKOUT · `REJECTED_AT_DEV`.** Gross Stage-0 hơi dương, không đủ phí. Khi bật SL/thoát cấu trúc, gross danh mục đã âm 79,65R. Bỏ Top 10 còn −309,15R.
- **PULLBACK · `REJECTED_AT_DEV`.** Gross markout âm sâu, stress âm cả bảy năm. Bỏ Top 10 còn −328,52R.
- **SWEEP · `REJECTED_AT_DEV`.** Gross markout yếu nhất. Có 76,7% mẫu có giá đạt trần phí/stop nhưng directional move vẫn âm. Bỏ Top 10 còn −367,05R.

Đường H1 gap dài trước điểm thoát đã làm mất giá ở 222 intent BREAKOUT, 41 PULLBACK và 65 SWEEP trong Mon–Fri. Các count này trước lọc một vị thế/mã và sizing. JSON giữ cả reject trước entry, stop đã bị vượt và intent ngoài cutoff. Cả ba đều rớt tất cả các cổng danh mục đã khóa. Kiểm định SL-active giữ vai trò chẩn đoán cho Stage-0.

### Giữ qua đêm so với cutoff ngày

Đối chứng dùng H1 open lúc 20:00 UTC để đại diện điểm đóng trước 20:30 UTC. Chênh cùng intent dùng những lệnh xuất hiện ở cả hai policy. Chênh cả sổ còn có ảnh hưởng vì số cơ hội chồng vị thế thay đổi.

| Họ | R/năm cutoff ngày → Mon–Fri | Δ cả kỳ (R) | Cùng intent | Δ net cùng intent (R) | Trong đó Δ swap (R) |
|---|---:|---:|---:|---:|---:|
| BREAKOUT | -18.00 → -31.10 | -91.69 | 2035 | -98.63 | -41.24 |
| PULLBACK | -25.22 → -35.24 | -70.16 | 1399 | -83.16 | -34.38 |
| SWEEP | -25.66 → -40.24 | -102.03 | 2268 | -94.36 | -45.72 |

Trong nhóm cùng intent, giữ qua đêm làm **gross xấu đi 48,78–57,40R mỗi họ**, đồng thời tăng thêm **34,38–45,72R** phí swap. Vì vậy swap là một phần của tác động, cùng với diễn biến giá trong thời gian giữ thêm.

### Sáu mã riêng lẻ

Stress-Real, sổ 10k, làm tròn lot và tính riêng từng mã. Giá trị 0 do thiếu đường giá có ghi chú. Per-asset Base/Stress, đủ metric từng năm, chi phí và tương quan ngày 6 × 6 có trong JSON private.

| Họ | Mã | Lệnh/năm | R/năm A / B / toàn kỳ | DD (R) |
|---|---|---:|---:|---:|
| BREAKOUT | US500.cash | 35.3 | -2.33 / -10.83 / -7.19 | 59.53 |
| BREAKOUT | EURUSD | 54.6 | -5.17 / -9.64 / -7.72 | 61.05 |
| BREAKOUT | USDJPY | 53.4 | -0.07 / +15.71 / +8.95 | 23.75 |
| BREAKOUT | EURJPY | 54.7 | -1.88 / -3.94 / -3.06 | 34.41 |
| BREAKOUT | GBPUSD | 60.3 | -10.50 / -15.35 / -13.27 | 107.70 |
| BREAKOUT | XAUUSD | 35.0 | -1.63 / -14.20 / -8.81 | 72.42 |
| PULLBACK | US500.cash | 22.3 | thiếu đường H1 / -2.36 / -1.35 | 18.27 |
| PULLBACK | EURUSD | 39.9 | -4.99 / -6.84 / -6.04 | 60.22 |
| PULLBACK | USDJPY | 38.0 | -7.84 / -8.06 / -7.97 | 63.45 |
| PULLBACK | EURJPY | 32.6 | -5.41 / -3.94 / -4.57 | 35.72 |
| PULLBACK | GBPUSD | 36.4 | -7.22 / -8.21 / -7.79 | 66.93 |
| PULLBACK | XAUUSD | 31.7 | -4.07 / -10.11 / -7.52 | 57.20 |
| SWEEP | US500.cash | 34.7 | thiếu đường H1 / -19.68 / -11.25 | 87.42 |
| SWEEP | EURUSD | 70.3 | -11.01 / +8.29 / +0.02 | 67.94 |
| SWEEP | USDJPY | 50.6 | -14.40 / -8.76 / -11.17 | 84.59 |
| SWEEP | EURJPY | 61.9 | -6.07 / -3.27 / -4.47 | 36.76 |
| SWEEP | GBPUSD | 59.0 | -12.41 / -1.20 / -6.00 | 49.55 |
| SWEEP | XAUUSD | 49.6 | -3.35 / -10.38 / -7.37 | 54.55 |

USDJPY BREAKOUT đạt **+8,95R/năm** toàn kỳ, tập trung ở B (+15,71R/năm), A −0,07R/năm. EURUSD SWEEP gần hòa vốn toàn kỳ (+0,02R/năm), A −11,01R/năm, B +8,29R/năm. Cả hai chỉ là kết quả chẩn đoán từ cùng lượt chọn, chưa có cơ sở mở holdout.

## Giới hạn vận hành và đối soát

Đã đưa sự cố XAUUSD **90,839 giây** vào checklist khôi phục và xác minh ticket. H1 OHLC chưa phân giải thứ tự tick, và mô hình dùng spread London cố định, phí snapshot và giờ rollover 00:00 server giả định. Chưa có bằng chứng spread Á/Mỹ/rollover đủ dày và lịch FTMO news/early-close theo mã qua nhiều năm. Quy tắc funded Standard áp cả kỳ nghỉ dài hơn hai giờ, nên Friday hard-flat thường chỉ bao phủ một phần. [Checklist](QUICKSTART-FTMO-FREE-TRIAL.md#checklist-trước-shadow-hoặc-gửi-lệnh) · [FTMO về kỳ nghỉ](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/).

Lượt đầu tính xong nhưng ghi JSON thất bại do kiểu số NumPy, có giữ tệp dở. Lượt kế tiếp sửa dữ liệu đầu ra và giữ markout thô với intent đã vượt stop trước entry. Điều đó không làm đổi kết quả SL-active. Đối soát lại từ 50.764 dòng ledger Parquet, gồm các kịch bản, thời điểm, phí, PnL và khóa cutoff.

[JSON danh mục và đường dẫn dữ liệu](BOTTLENECK2-MULTI-ASSET-MONFRI-SCREEN-20261119.json). Kho private trên ổ E có CLOCK_CENSUS.json chứa gap theo ngày giờ, RESULTS.json chứa từng mã/từng năm và PORTFOLIO_TRADES.parquet chứa ledger Development. Inventory key là bottleneck2-monfri-20261119. SHA256 manifest là ea4a22aa4af11131e266b785a7f9dd820f12f8b1d7f1b56cfa30f8c496fd6275.
