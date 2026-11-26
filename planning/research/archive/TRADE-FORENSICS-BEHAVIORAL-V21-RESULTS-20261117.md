# V21 — giải phẫu494 lệnh và kiểm định hành vi

**Không có ứng viên V21 vượt Development; giữ V16/V19 BASE_GUARD, chưa đủ điều kiện Challenge.**

PR99/head `c9075fb` merge `a2d9c86`, nhánh V20 đã xóa. Protocol `ed96cc0`, implementation `b20fdde`, correction `9986876`, freeze Dev `ec26e5c` trước Full taxonomy. PR100 để mở; giữ Trader pin/VI WIP/nguồn/freezes/negatives.

## 1. Sáu nhóm lệnh — mô tả đường giá, chưa chứng minh skill/luck

Canonical book là V19 PRIMARY stress SYM, fixed150USD với lot floor. V16 có cùng494 signals nhưng hai timeout exits khác; V16 +42,30347R, V19 +42,39167R. Không trộn hai sổ. MFE/MAE chia natural SL, NetR chia150USD. W1/W2 tên theo yêu cầu; không suy tác nhân/quỹ/retail từ OHLC.

| Nhãn | Số lệnh | %494 | NetR đóng góp | Provisional |
|---|---|---|---|---|
| W1 | 194 | 39.271 | 170.306 | 0 |
| W2 | 24 | 4.858 | 24.516 | 16 |
| L1 | 12 | 2.429 | -12.467 | 1 |
| L2 | 28 | 5.668 | -19.372 | 3 |
| L3 | 45 | 9.109 | -20.730 | 1 |
| L4 | 191 | 38.664 | -99.861 | 19 |

494/494 rows có nhãn; **40 nhãn provisional**, gồm32 open paths thiếu và các post-stop/context chưa đủ. Hai ordering khác nhãn ở0 lệnh; cùng kết quả OHLC không chứng minh đúng tick thực.

Ưu tiên W2 trước W1; với loss ưu tiên L1>L2>L3>L4. Flags vẫn giữ chồng lấn: L2 thực có30 lệnh/21.469R lỗ, khác hàng L2 độc quyền. Có12 stop rồi hồi>=1R, trong đó5 hồi>=2R. Đây là cơ hội sau khi đã thua, không chứng minh rộng SL hoặc vào lại sẽ có lãi.

Bỏ top5 winner: **12.984R**; bỏ top10: **-6.281R**. Lợi nhuận phụ thuộc đuôi phải. Trend/range strategies có thể cần đuôi phải; điều này chưa tự chứng minh may mắn hoặc lý do xóa các lệnh đó.

W2 flags có thể chồng nhau: {'near_death': {'count': 5, 'net_R': 3.6524666666666668}, 'late_windfall': {'count': 3, 'net_R': 0.0622}, 'open_path_unknown': {'count': 16, 'net_R': 20.5916}}

### Tách theo nhánh và giai đoạn


**EURUSD|F5:tf=H4:n=5:adx=25:buffer=0.1|DAY|P0 / 2018-2023** — 194 lệnh / 25.191R.

| Nhãn | Lệnh | % nhóm | NetR | Provisional |
|---|---|---|---|---|
| W1 | 75 | 38.660 | 77.723 | 0 |
| W2 | 12 | 6.186 | 13.092 | 10 |
| L1 | 8 | 4.124 | -8.312 | 1 |
| L2 | 10 | 5.155 | -7.847 | 1 |
| L3 | 0 | 0.000 | 0 | 0 |
| L4 | 89 | 45.876 | -49.465 | 13 |

**EURUSD|F5:tf=H4:n=5:adx=25:buffer=0.1|DAY|P0 / 2024-2026YTD** — 72 lệnh / 11.750R.

| Nhãn | Lệnh | % nhóm | NetR | Provisional |
|---|---|---|---|---|
| W1 | 26 | 36.111 | 24.709 | 0 |
| W2 | 5 | 6.944 | 9.496 | 4 |
| L1 | 3 | 4.167 | -3.148 | 0 |
| L2 | 4 | 5.556 | -3.274 | 0 |
| L3 | 0 | 0.000 | 0 | 0 |
| L4 | 34 | 47.222 | -16.033 | 3 |

**XAUUSD|F3:compression=BB:n=60:quantile=0.1:multiple=1|48H|P0 / 2018-2023** — 63 lệnh / -9.701R.

| Nhãn | Lệnh | % nhóm | NetR | Provisional |
|---|---|---|---|---|
| W1 | 18 | 28.571 | 8.256 | 0 |
| W2 | 2 | 3.175 | 0.809 | 0 |
| L1 | 0 | 0.000 | 0 | 0 |
| L2 | 6 | 9.524 | -4.312 | 2 |
| L3 | 17 | 26.984 | -3.885 | 0 |
| L4 | 20 | 31.746 | -10.570 | 0 |

**XAUUSD|F3:compression=BB:n=60:quantile=0.1:multiple=1|48H|P0 / 2024-2026YTD** — 40 lệnh / 10.226R.

| Nhãn | Lệnh | % nhóm | NetR | Provisional |
|---|---|---|---|---|
| W1 | 22 | 55.000 | 18.947 | 0 |
| W2 | 0 | 0.000 | 0 | 0 |
| L1 | 0 | 0.000 | 0 | 0 |
| L2 | 3 | 7.500 | -1.501 | 0 |
| L3 | 9 | 22.500 | -3.548 | 0 |
| L4 | 6 | 15.000 | -3.672 | 0 |

**XAUUSD|F4:hour=15:impulse=1:timing=MONTH:multiple=1|24H|P1 / 2018-2023** — 83 lệnh / 8.362R.

| Nhãn | Lệnh | % nhóm | NetR | Provisional |
|---|---|---|---|---|
| W1 | 36 | 43.373 | 29.365 | 0 |
| W2 | 4 | 4.819 | 1.100 | 2 |
| L1 | 1 | 1.205 | -1.007 | 0 |
| L2 | 2 | 2.410 | -1.333 | 0 |
| L3 | 10 | 12.048 | -6.974 | 1 |
| L4 | 30 | 36.145 | -12.788 | 3 |

**XAUUSD|F4:hour=15:impulse=1:timing=MONTH:multiple=1|24H|P1 / 2024-2026YTD** — 42 lệnh / -3.437R.

| Nhãn | Lệnh | % nhóm | NetR | Provisional |
|---|---|---|---|---|
| W1 | 17 | 40.476 | 11.306 | 0 |
| W2 | 1 | 2.381 | 0.019 | 0 |
| L1 | 0 | 0.000 | 0 | 0 |
| L2 | 3 | 7.143 | -1.106 | 0 |
| L3 | 9 | 21.429 | -6.324 | 0 |
| L4 | 12 | 28.571 | -7.333 | 0 |

Giveback theo mode / MFE trước thoát (bảng chồng flags, không cộng lại với sáu nhóm):

| Mode | MFE band | Lệnh | NetR |
|---|---|---|---|
| P0 | 0.80–<1.00 | 8 | -4.787 |
| P0 | 1.00–<1.50 | 7 | -5.741 |
| P0 | >=1.50 | 10 | -8.503 |
| P1 | 0.80–<1.00 | 2 | -1.729 |
| P1 | 1.00–<1.50 | 3 | -0.710 |
| P1 | >=1.50 | 0 | 0 |

## 2. B1–B3: ngân sách và kết quả Development

29 recipes logic:1 B1 +24 B2 +4 B3. B1 chỉ dùng Dev taxonomy; L2 loss13,492R > L3 loss10,858R nên chọn thêm bảo vệ net hòa vốn sau net+1R trên P0, active từ M1 kế tiếp; giữ F4 P1. Không thử thêm exhaustion gate sau kết quả.

| B1 OLHC | Baseline | Child |
|---|---|---|
| net_R | 23.852 | 22.660 |
| equity_R_DD | 12.207 | 11.094 |
| worst_daily_pct | 0.611 | 0.611 |
| Calmar | 0.326 | 0.340 |

W1/all giảm từ37.94% xuống36.18%. 18 exits đổi; cải thiện ở nhóm được lợi+8.613R, thiệt hại ở nhóm bị cắt sớm-9.805R. DD/Calmar cải thiện nhưng net/W1 không đạt; cả hai orderings bị bác. Fixed150 marked equity, không là Daily DD của adaptive account.

28 B2/B3 raw screens: **0 Stage-0 survivors**. Raw net phải dương từng năm, vượt ma sát cùng đơn vị, dual-positive, scale<=12%, retention>=50%, cadence>=40/năm. Không viết thêm SL/TP hoặc chạy validation để cứu losers.

| Asset | Recipe | Raw/6năm | ĐủF/R / cógiá+F/R | Median natural | F/SL median | Lý do |
|---|---|---|---|---|---|---|
| XAUUSD | B2:PD:sweep=0.1 | 440 | 183 / 183 | 5.455 | 0.140 | âm/thiếu: 2018,2019,2020,2021,2022; biên net chưa vượt phí; SL nhỏ so phí; giữ<50% vì phí; thưa |
| XAUUSD | B2:PD:sweep=0.3 | 219 | 132 / 132 | 7.302 | 0.104 | âm/thiếu: 2020,2021,2022; biên net chưa vượt phí; thưa |
| XAUUSD | B2:PD:sweep=0.6 | 73 | 63 / 63 | 9.448 | 0.081 | âm/thiếu: 2020,2022; biên net chưa vượt phí; thưa |
| XAUUSD | B2:ASIA:sweep=0.1 | 666 | 183 / 183 | 4.414 | 0.173 | âm/thiếu: 2018,2019,2020,2021,2022; biên net chưa vượt phí; SL nhỏ so phí; giữ<50% vì phí; thưa; thiếu endpoint |
| XAUUSD | B2:ASIA:sweep=0.3 | 318 | 159 / 159 | 6.324 | 0.121 | âm/thiếu: 2018,2020,2021,2022; biên net chưa vượt phí; SL nhỏ so phí; thưa |
| XAUUSD | B2:ASIA:sweep=0.6 | 84 | 73 / 73 | 9.970 | 0.077 | âm/thiếu: 2019,2020,2022; biên net chưa vượt phí; thưa |
| XAUUSD | B3:London15:impulse=1:ALL | 315 | 231 / 231 | 8.786 | 0.087 | âm/thiếu: 2018,2019,2020,2021,2023; biên net chưa vượt phí; thưa |
| XAUUSD | B3:London15:impulse=1:MONTH | 59 | 36 / 36 | 7.816 | 0.098 | âm/thiếu: 2018,2021; biên net chưa vượt phí; thưa |
| EURUSD | B2:PD:sweep=0.1 | 480 | 302 / 301 | 0.002 | 0.101 | âm/thiếu: 2019,2021,2022,2023; biên net chưa vượt phí; thiếu endpoint |
| EURUSD | B2:PD:sweep=0.3 | 241 | 195 / 194 | 0.002 | 0.087 | âm/thiếu: 2019,2021,2023; biên net chưa vượt phí; thưa; thiếu endpoint |
| EURUSD | B2:PD:sweep=0.6 | 50 | 47 / 46 | 0.003 | 0.058 | âm/thiếu: 2019,2021,2022; biên net chưa vượt phí; thưa; thiếu endpoint |
| EURUSD | B2:ASIA:sweep=0.1 | 598 | 342 / 342 | 0.002 | 0.110 | âm/thiếu: 2020,2021,2022; biên net chưa vượt phí; thiếu endpoint |
| EURUSD | B2:ASIA:sweep=0.3 | 316 | 239 / 239 | 0.002 | 0.090 | âm/thiếu: 2021,2022; biên net chưa vượt phí; thưa |
| EURUSD | B2:ASIA:sweep=0.6 | 60 | 59 / 59 | 0.003 | 0.066 | âm/thiếu: 2019,2021,2023; biên net chưa vượt phí; thưa |
| US500 | B2:PD:sweep=0.1 | 161 | 46 / 46 | 18.626 | 0.162 | âm/thiếu: 2018,2021,2022,2023; biên net chưa vượt phí; SL nhỏ so phí; giữ<50% vì phí; thưa |
| US500 | B2:PD:sweep=0.3 | 75 | 36 / 36 | 23.568 | 0.128 | âm/thiếu: 2018,2019,2020,2021,2022,2023; biên net chưa vượt phí; SL nhỏ so phí; giữ<50% vì phí; thưa |
| US500 | B2:PD:sweep=0.6 | 19 | 18 / 18 | 45.692 | 0.066 | âm/thiếu: 2018,2019,2020,2021,2023; biên net chưa vượt phí; thưa |
| US500 | B2:ASIA:sweep=0.1 | 139 | 52 / 52 | 19.939 | 0.151 | âm/thiếu: 2018,2020,2021; biên net chưa vượt phí; SL nhỏ so phí; giữ<50% vì phí; thưa; thiếu endpoint |
| US500 | B2:ASIA:sweep=0.3 | 64 | 40 / 40 | 28.536 | 0.105 | âm/thiếu: 2020; biên net chưa vượt phí; thưa |
| US500 | B2:ASIA:sweep=0.6 | 14 | 14 / 14 | 45.095 | 0.066 | âm/thiếu: 2018,2019,2020; biên net chưa vượt phí; thưa |
| US500 | B3:London15:impulse=1:ALL | 269 | 114 / 114 | 22.459 | 0.134 | âm/thiếu: 2018,2020,2021,2022,2023; biên net chưa vượt phí; SL nhỏ so phí; giữ<50% vì phí; thưa; thiếu endpoint |
| US500 | B3:London15:impulse=1:MONTH | 44 | 21 / 21 | 24.440 | 0.121 | âm/thiếu: 2020,2022; biên net chưa vượt phí; SL nhỏ so phí; giữ<50% vì phí; thưa |
| GBPUSD | B2:PD:sweep=0.1 | 509 | 467 / 3 | 0.003 | 0.068 | Thiếu endpoint20:30/M1; chưa đủ dữ liệu kết luận kinh tế |
| GBPUSD | B2:PD:sweep=0.3 | 285 | 277 / 1 | 0.003 | 0.061 | Thiếu endpoint20:30/M1; chưa đủ dữ liệu kết luận kinh tế |
| GBPUSD | B2:PD:sweep=0.6 | 75 | 74 / 0 | 0.004 | 0.041 | Thiếu endpoint20:30/M1; chưa đủ dữ liệu kết luận kinh tế |
| GBPUSD | B2:ASIA:sweep=0.1 | 792 | 694 / 5 | 0.002 | 0.073 | Thiếu endpoint20:30/M1; chưa đủ dữ liệu kết luận kinh tế |
| GBPUSD | B2:ASIA:sweep=0.3 | 479 | 461 / 1 | 0.003 | 0.059 | Thiếu endpoint20:30/M1; chưa đủ dữ liệu kết luận kinh tế |
| GBPUSD | B2:ASIA:sweep=0.6 | 148 | 148 / 0 | 0.004 | 0.048 | Thiếu endpoint20:30/M1; chưa đủ dữ liệu kết luận kinh tế |

Chi tiết từng năm/raw/priced/net units trong JSON và các raw Zstd tables. Gold đơn vịUSD/oz, FX là giá tỷ giá, US500 points; không so trực tiếp tổng unit khác asset. GBP chỉ có pairedH1; thiếu endpoint20:30 nên giữ DATA_PATH_INCOMPLETE, không gọi mean missing là thua hay phí0. Một vài endpoint early-guard có giá không đại diện cả kỳ.

Audit publication tách cost-only retention khỏi priced+cost retention: scanner đầu gộp cả hai vào trường retention. Đã đối chiếu28 raw arrays đã lưu, sửa cột lý do/giữ mẫu do phí; cả28 verdict không đổi. Receipt `admission-cost-vs-coverage-reconciliation.json` giữ nguồn và delta; không replay quotes hoặc đổi ngưỡng.

Self-review phát hiện B2 hai-sided sweep: phải abstain trước khi áp close-direction, thay vì kiểm hai directional triggers vốn không thể cùng true. Giữ attempt đầu, registration sửa trước đo lại24 B2;4 B3 không đổi được reuse. 53 cell evaluations thực tế gồm29 đầu +24 sửa lỗi, không giấu exposure hoặc biến thành53 hypotheses độc lập.

## 3. Quyết định và lifecycle

Không có child qua Dev nên **không mở backtest V21 mới trên2024–2026, không chạy105 starts/5.000 bootstrap mới**. Chỉ Full taxonomy của baseline được mở sau freeze. Dùng lại baseline history/MC có binding từ V19 để đối chiếu; các cửa sổ overlap, bootstrap là resampling frequency, không là xác suất tương lai.

| Baseline đã có | Hai vòng/105 | Median tháng có điều kiện | Worst daily% | Worst static% |
|---|---|---|---|---|
| V16 | 71 | 47.075 | 1.963 | 6.383 |
| V19 | 71 | 48.061 | 2.027 | 6.383 |

| Baseline MC OLHC /5.000 | Hai vòng12/18/24/36% |
|---|---|
| V16 | 1.240 / 6.080 / 14.320 / 33.360 |
| V19 | 1.380 / 6.200 / 14.500 / 33.560 |

Bước tiếp có ích là prospective account/feed reconciliation hoặc một giả thuyết mới có nguồn/cơ chế rõ và budget riêng. Không có căn cứ từ V21 để tăng risk, bỏ SL hay mua Challenge.

## 4. Engineering, storage và bàn giao

**1261 tests PASS/0skip**, giữ đủ1.239 V20 IDs; full wall13.176s. Target<15s:True; stretch<14s:True.

Smoke đúng10 fresh serial processes/cùng78 IDs: 10/10 <0,78s; 6/10 <0,70s; median0.692s, max0.719s. Startup/import/disk fixture IO nằm trong timer; giữ outliers, không retry chọn streak.

60 bảng Zstd9: 5,112,249 → 766,456 bytes; SHA/roundtrip mọi bảng, giữ cả attempt lỗi. Job riêng khoảng3.25MiB tại snapshot. Không tạo price cache mới/xóa nguồn.

| Kho logical | V20 baseline GiB | Sau GiB | Delta GiB | Read errors |
|---|---|---|---|---|
| D | 197.377 | 197.378 | 0.001 | 2 |
| E | 215.362 | 215.366 | 0.004 | 0 |

Baseline inventory tái dùng snapshot cuốiV20; non-atomic, có thể gồm hoạt động khác. Không là physical free bytes. D giữ hai lỗi đọc VI; không sửa quyền hoặc WIP của dự án đó.

Audit riêng arithmetic cash/extrema đủ340 Dev +494 Full ở hai ordering; cùng tác giả/feed, chưa independent human review. Tests gồm stop-minute truncation, post-stop side/time, unknown/provisional, overlap, DST, nonempty causal prefix, dual-sweep abstention, early protection next-minute và gate DD. Skill/workflow hiện có đủ bao phủ; không tạo policy/skill mới từ nhãn hồi tố.

PR100 để mở; exact-head3CI và downloaded test IDs chốt trong private `ci-exact-head-reconciliation.json`/`completion-receipt.json` sau push. Không broker orders/account/login/provider/deploy/Astra/memory updates.

[Protocol](TRADE-FORENSICS-BEHAVIORAL-V21-PROTOCOL-20261117.md) · [Freeze](TRADE-FORENSICS-BEHAVIORAL-V21-FREEZE-20261117.json) · [JSON](TRADE-FORENSICS-BEHAVIORAL-V21-RESULTS-20261117.json)

Research primary: [NY Fed stop cascades](https://www.newyorkfed.org/research/staff_reports/sr150.html), [Bank of Canada fixing returns](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/), [LSEG WMR clock](https://www.lseg.com/en/ftse-russell/benchmarks/wmr-fx-benchmarks). Các nguồn hỗ trợ nghiên cứu cơ chế; không chứng minh các recipe này có edge.
