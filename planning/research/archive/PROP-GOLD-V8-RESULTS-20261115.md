# V8 — thử chuẩn hóa Gold A, mở lại ba sleeve và kiểm định lịch sử

**Kết luận: N1, N2 và cả ba sleeve đều chưa qua cổng Development. Không hình thành danh mục V8 đủ điều kiện.** Đã hoàn thành chẩn đoán và kiểm baseline đối chứng; không gọi việc hoàn tất hạ tầng/báo cáo là đạt mục tiêu Challenge hay thu nhập chính.

PR #86 đã merge tại `c99fa7e`; branch V8 `codex/prop-gold-v8`. Quyết định No-Go được commit `91aa6701ddf5f963cd8856deb9538f158ac75553` trước mở giá lùi thời gian. 2024–2026 không dùng để chọn N1/N2/sleeve. Hai cơ chế core và ba horizon; N2 có một attempt global-stop không đúng conditional intent và một attempt sửa semantics chỉ trên Dev, giữ cả hai trong lịch sử. Không quét grid.

## 1. Hai điều cần sửa trong tiền đề

SL 28,21/58,85 USD/oz không phải hộp Á: hộp Á median là 23,33/46,06 USD/oz năm 2025/2026. Quan sát hộp/SL tăng chưa chứng minh “sóng đã chạy xong”. V8 kiểm hai giả thuyết cụ thể; thu nhỏ stop có thể làm tăng số lần bị quét và ma sát theo R.

**2018–2021 không phải clean holdout toàn dự án.** Gold R043 đã dùng 2010–2024; `GOLD-ML-SL-LABELS-PROTOCOL-20261109.md` dùng 2018/2021. Nhánh H1 dùng warmup Nov 2021; `PROP-PORTFOLIO-V3-PROTOCOL-20261114.md` dùng warmup từ Jan 2021. V8 giữ đóng toàn bộ price partitions này trong thiết kế, rồi mở trong một release sau commit, nhưng phải gọi đúng là **backward historical validation, có prior exposure**. Đây cũng không phải forward test tương lai.

**Ngoại lệ kỹ thuật được ghi nhận:** có một cấu hình strategy đã khóa nhưng **hai lượt đo backward**. Sau lần đầu, FTMO Trading Update 16/12/2021 xác nhận Metals ngày 31/12/2021 Normal Hours, khác lịch federal-observed proxy ghi CLOSED. Đã commit sửa đúng ngày này trước khi đo lại, giữ guard Dec 31 16:58 đã đăng ký và mọi ngày/entry mechanism/SL/k/risk khác. Attempt 1 (224 sổ) và oracles vẫn giữ nguyên; chỉ backward đo lại. Không gọi đây là một pristine one-shot run, không dùng kết quả để chọn lại N1/N2 hoặc sleeve.

## 2. Đã thử đúng những gì?

- **N1:** giữ SL toàn hộp, chỉ nhận Asia range / median 20 ngày Á trước đó ≤P85 Development, k=1.598513 từ 483 ngày đủ context. Không fit k theo lợi nhuận.

- **N2 đúng điều kiện:** chỉ khi natural SL cũ>25 USD/oz mới dùng Low/High của nến H1 breakout +0,1 ATR_H1 trước nến và chỉ thay khi gần hơn cấu trúc toàn hộp; còn lại giữ nguyên SL cũ. Không cắt SL đến một mức USD tùy ý, không mid-box/grid/biến thể kết hợp.

- Hai bản chỉ nhận natural SL≤25 USD/oz và stressF/SL≤12%. Với risk 125 USD, SL≤25 bảo đảm ít nhất 5 oz =0,05 lot; budget 125/150/200 đều được kiểm trên cùng trade set. Lệnh không đạt thì bỏ, không ép level/volume.

- Giữ H4 bias, H1 entry, BOTH, không TP cứng, tối đa 48 giờ lịch và Friday/holiday flat. Cổng Dev yêu cầu net dương cả hai năm/hai phí/ba budgets, ≥40 lệnh/năm, retention≥50%, scale≤12%.

## 3. Kết quả core chỉ trên 2022–2023

| Bản | Năm | Baseline raw | Sau compression | Lệnh nhận | SL trước phí USD/oz | F/SL % | NetR SYM $150 |
|---|---|---|---|---|---|---|---|
| BASELINE | 2022 | 103 | 103 | 103 | 11.51 | 6.88 | 4.050 |
| BASELINE | 2023 | 107 | 107 | 107 | 8.67 | 8.62 | 13.795 |
| N1 | 2022 | 103 | 83 | 71 | 11.36 | 7.03 | -1.544 |
| N1 | 2023 | 107 | 94 | 69 | 8.32 | 9.07 | -12.772 |
| N2 | 2022 | 103 | 103 | 92 | 11.51 | 6.88 | -6.278 |
| N2 | 2023 | 107 | 107 | 82 | 8.67 | 8.62 | -4.583 |

Baseline không áp các bộ lọc mới; cột lệnh nhận của baseline gồm toàn bộ tín hiệu. SYM swap BUY/SELL−40/−40, ASYM proxy−45/−5 USD/lot/rollover; commission/slip giữ V7.

| Bản | Năm | R ở $125 | R ở $150 | R ở $200 | Max lỗi lot % |
|---|---|---|---|---|---|
| BASELINE | 2022 | 6.6518 | 5.9006 | 6.0643 | 29.03 |
| BASELINE | 2023 | 16.0550 | 16.4619 | 16.2417 | 14.87 |
| N1 | 2022 | 0.4614 | -0.2126 | 0.1740 | 14.41 |
| N1 | 2023 | -11.4898 | -11.3492 | -11.4902 | 9.90 |
| N2 | 2022 | -4.0593 | -4.7475 | -4.2442 | 14.41 |
| N2 | 2023 | -3.1977 | -2.8509 | -3.2251 | 14.87 |

**N1 không cứu được kinh tế:** năm 2023 SYM khoảng−12,77 R thay baseline+13,79 R. Năm 2022 ASYM còn đổi dấu giữa 125/150/200 dù đã có ít nhất 5 oz. Giảm sai số lot không bảo đảm bất biến dấu cho một kỳ vọng rất gần 0.

**N2 conditional vẫn fail economics:** chỉ 6 tín hiệu 2022 cần thay stop; SL median trước phí giữ 11,51/8,67 USD/oz, đủ 92/82 lệnh, nhưng SYM−6,28/−4,58 R. Không còn nguyên nhân cadence/median-scale của bản global; nguyên nhân chặn hiện tại là net âm. Năm 2023 cost gate bỏ 25 lệnh baseline từng tạo+18,38 R, nên kết quả sau lọc không còn dương.

**Giữ attempt N2 cũ để kiểm toán:** bản đầu thay stop H1 cho mọi tín hiệu, cho−15,24/+10,09 R và 45/26 lệnh. Bản này không đúng ý đồ chỉ đổi khi hộp/stop cũ quá rộng. Correction được commit 03 b 185 c trước đo lại Dev, không đổi cap 25/fee 12%/budgets; không dùng backward đã xem để chọn tham số và không chạy N2 mới ngoài Dev. JSON giữ cả kết quả global cũ và conditional đúng yêu cầu.

### Phân rã N1: những tín hiệu bị bỏ trước đây đóng góp bao nhiêu?

Dưới đây là R của **lệnh baseline gốc**, chia theo lý do N1 giữ/bỏ; không chạy trial nới filter nào.

| Năm | Nhóm | Lệnh | Baseline R SYM | Baseline R ASYM |
|---|---|---|---|---|
| 2022 | compression_or_context | 20 | -5.195 | -5.058 |
| 2022 | cost | 9 | 9.944 | 10.332 |
| 2022 | kept | 71 | -1.544 | -0.213 |
| 2022 | stop_scale | 3 | 0.845 | 0.840 |
| 2023 | compression_or_context | 13 | 8.189 | 8.498 |
| 2023 | cost | 25 | 18.378 | 19.313 |
| 2023 | kept | 69 | -12.772 | -11.349 |

Các thay đổi gồm compression, trần natural SL và cost gate; không quy toàn bộ chênh lệch cho riêng compression.

## 4. Ba Gold sleeve cũ: sửa đúng blocker, không chỉ gọi là lỗi lịch

Cả ba là **PREVDAY sweep/reversal trên H1**, tín hiệu 08–11 UTC London: giá xuyên high/low ngày trước rồi đóng trở lại và nến xác nhận cùng chiều. SL ở extreme H1+0,1 ATR; ba horizon DAY 20:30,24 h,48 h đều chịu Friday/holiday clamp. Không có H4 trend filter cho sweep này; không mô tả nhầm là trend breakout.

Hồ sơ V3 đã có endpoint: không có `ENDPOINT_UNKNOWN` và không có ngày gap chưa giải quyết trong các lệnh FILLED. DAY/24 H có 12/45 lệnh thiếu observed Ask path;48 H có 14/45, đều liên quan SELL/proxy. V8 dùng observed paired tick hours sẵn có, giờ thiếu thì M1 Bid+Ask proxy 0,338 có nhãn. Đạt 100% endpoint trong model **không biến proxy Ask thành dữ liệu broker thật**.

| Horizon | Năm | Raw | Nhận | Giữ % | F/SL % | Endpoint % | NetR SYM |
|---|---|---|---|---|---|---|---|
| DAY | 2022 | 51 | 23 | 45.1 | 15.82 | 100.0 | 14.994 |
| DAY | 2023 | 56 | 21 | 37.5 | 16.92 | 100.0 | 10.267 |
| 24 H | 2022 | 51 | 23 | 45.1 | 15.82 | 100.0 | 9.828 |
| 24 H | 2023 | 56 | 21 | 37.5 | 16.92 | 100.0 | 13.365 |
| 48 H | 2022 | 51 | 23 | 45.1 | 15.82 | 100.0 | 7.411 |
| 48 H | 2023 | 56 | 21 | 37.5 | 16.92 | 100.0 | 17.563 |

**Cả ba dương nhưng chưa đạt scale/retention:**23/51 và 21/56, tức 45,1%/37,5%; medianF/medianSL 15,82%/16,92%, quá trần 15%. Không tự hạ gate hoặc nới SL để “giải cứu”. So với V7,2023 trước đây 22 lệnh nay 21 do nguồn Bid/Ask và fills được thống nhất; outcomes mới không được ghi đè lên artifacts V3. Cổng 50% là chính sách sàng lọc đã khóa của project, không phải định lý thống kê chứng minh các sleeve dương này không có edge.

## 5. Chốt trước mở backward và các cột bị hủy

Không core mới nào đạt và không sleeve nào đạt. **NORMALIZED và ALL-GOLD PORTFOLIO bị dừng ở Development.** Không dùng 2018–2021 hay 2024–2026 để chọn lại k/stop/horizon. Theo fallback đã đăng ký trước outcome, Phase 3 chỉ chạy baseline control. Không có các con số “SL 2025 đã giảm” hoặc “portfolio vượt quỹ” cho cấu hình không qua gate.

| Giai đoạn | V7 baseline | Gold normalized | All-Gold portfolio |
|---|---|---|---|
| Dev 2022–2023 | Đã đối soát | N1/N2: No-Go | 3 horizon: No-Go |
| Full 2022–13/10/2026 | Đã đo đủ 57 mốc | N/A — canceled trước đánh giá | N/A — không composition đủ gate |
| Backward 2018–2021 | Control đã đo 48 mốc | N/A — canceled trước mở | N/A — không composition đủ gate |

## 6. Baseline control: annual và lifecycle

Risk lifecycle V4:200/175/125 USD P1/P2/Funded; cap 800, reserve 46k, throttle 150/90 và harvester Funded giữ nguyên. Annual reference: 150 USD=0,30% vốn 50k, không throttle/harvester. Hai orders M1 là độ nhạy O-L-H-C và O-H-L-C, không phải observed intraminute path.

### 2022–2026 YTD đến 13/10

| Năm | Phí | Lệnh | BUY/SELL | NetR | MeanR | Peak-DD % | Static % | Daily % |
|---|---|---|---|---|---|---|---|---|
| 2022 | SYM_FLAT | 103 | 54/49 | 4.050 | 0.0393 | 4.985 | 1.112 | 0.686 |
| 2023 | SYM_FLAT | 107 | 57/50 | 13.795 | 0.1289 | 6.653 | 3.202 | 0.799 |
| 2024 | SYM_FLAT | 98 | 61/37 | 1.845 | 0.0188 | 3.970 | 3.486 | 0.623 |
| 2025 | SYM_FLAT | 96 | 72/24 | -0.285 | -0.0030 | 4.410 | 0.555 | 0.655 |
| 2026 | SYM_FLAT | 71 | 38/33 | 3.174 | 0.0447 | 2.733 | 0.663 | 0.528 |
| 2022 | ASYM_FLAT | 103 | 54/49 | 5.901 | 0.0573 | 4.792 | 1.112 | 0.698 |
| 2023 | ASYM_FLAT | 107 | 57/50 | 16.462 | 0.1538 | 6.268 | 2.818 | 0.731 |
| 2024 | ASYM_FLAT | 98 | 61/37 | 2.645 | 0.0270 | 3.893 | 3.409 | 0.624 |
| 2025 | ASYM_FLAT | 96 | 72/24 | -0.135 | -0.0014 | 4.346 | 0.509 | 0.657 |
| 2026 | ASYM_FLAT | 71 | 38/33 | 3.532 | 0.0497 | 2.682 | 0.664 | 0.527 |

| Phí | Mốc | P1 | Cả 2 | Median tháng cả 2 | Mốc payout | Payout events | Trader USD chồng lấn | Daily % | Static % |
|---|---|---|---|---|---|---|---|---|---|
| SYM_FLAT | 36 cũ | 17 | 0 | N/A | 0 | 0 | 0.00 | 1.071 | 7.363 |
| SYM_FLAT | 21 mới | 0 | 0 | N/A | 0 | 0 | 0.00 | 0.892 | 5.406 |
| ASYM_FLAT | 36 cũ | 23 | 0 | N/A | 0 | 0 | 0.00 | 0.979 | 6.267 |
| ASYM_FLAT | 21 mới | 0 | 0 | N/A | 0 | 0 | 0.00 | 0.895 | 5.423 |

Standalone Funded giả định có tài khoản ngay đầu kỳ, nối liên tục:

| Phí | Payout events | Trader USD | Balance cuối | Daily % | Static % |
|---|---|---|---|---|---|
| SYM_FLAT | 18 | 3,656.35 | 48,967.89 | 0.654 | 4.749 |
| ASYM_FLAT | 19 | 4,145.22 | 48,981.94 | 0.597 | 4.438 |

### 2018–2021, backward có prior exposure

| Năm | Phí | Lệnh | BUY/SELL | NetR | MeanR | Peak-DD % | Static % | Daily % |
|---|---|---|---|---|---|---|---|---|
| 2018 | SYM_FLAT | 84 | 35/49 | -30.996 | -0.3690 | 11.294 | 10.377 | 0.747 |
| 2019 | SYM_FLAT | 55 | 29/26 | -13.852 | -0.2519 | 5.444 | 4.324 | 1.022 |
| 2020 | SYM_FLAT | 98 | 63/35 | -3.031 | -0.0309 | 5.838 | 1.254 | 0.795 |
| 2021 | SYM_FLAT | 106 | 60/46 | -12.000 | -0.1132 | 6.809 | 4.087 | 0.695 |
| 2018 | ASYM_FLAT | 84 | 35/49 | -27.205 | -0.3239 | 10.197 | 9.237 | 0.712 |
| 2019 | ASYM_FLAT | 55 | 29/26 | -12.624 | -0.2295 | 5.337 | 3.991 | 1.024 |
| 2020 | ASYM_FLAT | 98 | 63/35 | -2.471 | -0.0252 | 5.698 | 1.205 | 0.796 |
| 2021 | ASYM_FLAT | 106 | 60/46 | -9.857 | -0.0930 | 6.537 | 3.543 | 0.703 |

| Phí | Mốc | P1 | Cả 2 | Median tháng cả 2 | Mốc payout | Payout events | Trader USD chồng lấn | Daily % | Static % |
|---|---|---|---|---|---|---|---|---|---|
| SYM_FLAT | 48 backward | 0 | 0 | N/A | 0 | 0 | 0.00 | 1.368 | 8.025 |
| ASYM_FLAT | 48 backward | 0 | 0 | N/A | 0 | 0 | 0.00 | 1.372 | 8.007 |

Standalone Funded giả định có tài khoản ngay đầu kỳ, nối liên tục:

| Phí | Payout events | Trader USD | Balance cuối | Daily % | Static % |
|---|---|---|---|---|---|
| SYM_FLAT | 1 | 180.26 | 46,057.49 | 0.624 | 7.885 |
| ASYM_FLAT | 1 | 179.50 | 46,059.02 | 0.595 | 7.882 |

Không cộng các mốc chồng lấn thành thu nhập của một account. Payout là **mô phỏng đủ điều kiện/request proxy**, không tiền nhận thật; chưa trừ challenge/retry/vận hành. Không suy tỷ lệ pass mẫu thành xác suất tương lai.

**Annual reference và lifecycle khác nhau:** reference không có throttle/reserve; riêng 2018 SYM có Static Loss 10,377% trên đường M1. Các sổ lifecycle có risk guard mới là nhóm được thống kê không modeled breach; không lấy kết quả đó để gọi bản risk 150 cố định là an toàn.

### Backward: âm do tín hiệu hay chỉ do phí?

| Năm | M1 bars | H1 đủ 60 phút | Gross sau spread R | Commission R | Slip R | Swap R ASYM | NetR ASYM |
|---|---|---|---|---|---|---|---|
| 2018 | 353923 | 5720 | -18.064 | 0.281 | 6.371 | -2.489 | -27.205 |
| 2019 | 353349 | 5436 | -5.521 | 0.182 | 3.741 | -3.180 | -12.624 |
| 2020 | 355495 | 5866 | 3.980 | 0.195 | 3.144 | -3.112 | -2.471 |
| 2021 | 354346 | 5877 | -3.486 | 0.250 | 3.963 | -2.159 | -9.857 |

2018,2019,2021 đã âm gross sau spread trước commission/slip/swap; năm 2020 gross dương nhỏ rồi bị ma sát/carry ăn hết. Vì vậy không thể giải thích cả bốn năm chỉ bằng phí swap. Đây là kết quả dưới nguồn/calendar/Ask model đã khai báo, không chứng minh mọi Asian breakout đều không có edge.

## 7. Kiểm chứng và hậu kiểm

| Kỳ | Order | Sổ | Oracle | Admissions | Rejects | Costs | Dynamic fills |
|---|---|---|---|---|---|---|---|
| full | OPEN_LOW_HIGH_CLOSE | 134 | PASS | 30615 | 129 | 30615 | 0 |
| full | OPEN_HIGH_LOW_CLOSE | 134 | PASS | 30615 | 129 | 30615 | 0 |
| backward | OPEN_LOW_HIGH_CLOSE | 112 | PASS | 13930 | 6896 | 13930 | 0 |
| backward | OPEN_HIGH_LOW_CLOSE | 112 | PASS | 13930 | 6896 | 13930 | 0 |

**995 tests PASS**,17 fixtures V8; **492 sổ account** đối soát bằng rational/cash-posted oracle và **3936 bridges** cho economics Dev ba budgets. Cùng implementer, không có independent human/model reviewer.

492 sổ ở bảng là kết quả authoritative sau sửa lịch (268 full+224 backward). 224 sổ backward attempt 1 cũng đã đối soát nhưng archived vì calendar sai; không cộng các lượt đo trùng profile thành mẫu độc lập. Correction chỉ bổ sung tín hiệu ngày 31/12/2021, không mở vòng tìm tham số mới.

Hai full orders khớp V7 Gold V4 về accepted/closed/cash/phase/payout/DD sau remap trade IDs, tổng 268 sổ. Full/backward đều giữ nguồn, không force-close cuối mẫu để tạo lãi hoặc fallback last quote tùy ý.

Backward chỉ có Bid M1 và Ask proxy, các giờ holiday 2018–2021 là conservative guards chưa certified từ FTMO lịch sử. Lịch 2022–2026 giữ V7, gồm các giờ đã xác minh và những guard còn unknown. Không ghi nhận modeled breach trong các sổ lifecycle đã dựng không bảo đảm mọi đường tick thực đều an toàn. JSON giữ riêng danh sách khoảng trống>15 phút khi vị thế đang sống, loại trừ giờ rollover thường lệ; đủ endpoint không thay thế kiểm đường giá.

**Gap còn lại được phát hiện khi audit full:** hai vị thế SELL mở 08/10 và 09/10/2024 cùng đi qua khoảng thiếu native ticks từ 09/10/2024 23:05:51,002 đến 10/10/2024 00:11:48,930 UTC (khoảng 66 phút, ngoài rollover thông thường). Có giá entry/exit không chứng minh floating DD trong khoảng đó. Giữ sealed results V7/V8, gắn DATA_PATH_INCOMPLETE ở đúng claim full-path; không tự chèn tick giả hoặc sửa policy nguồn sau outcome. Backward không phát hiện long-gap đang giữ lệnh theo tiêu chí này, nhưng vẫn là M1/Ask proxy, không tick certification.

| Phần | Phát hiện | Đã làm | Giới hạn |
|---|---|---|---|
| Packaging | Registration cần tạo private directory trước write | Sửa trước khi mở dữ liệu; regression 17 fixtures | Không đổi strategy outcome |
| CI portability | LF/CRLF làm khác byte-hash của cùng lịch | Chỉ chấp nhận chuyển newline theo frozen Windows hash; content mutation vẫn fail; calendar-v 2 parity PASS | Không sửa source prices hoặc rerun tài chính |
| Calendar | Federal observance khác giờ Metals 31 Dec 2021 | Nguồn FTMO xác minh; giữ attempt 1; commit fix và rerun riêng backward | Hai technical attempts, không pristine one-shot |
| Reuse | V6/V7 đã có lifecycle/harvester/oracle | Adapter chỉ đổi inputs/observer; restore bindings trong finally; parent parity 268 sổ | Không gọi self-review là independent person |
| Selection | Cả 2 core/3 sleeve failDev | Khóa No-Go trước backward; không tuning cứu kết quả | Chưa có all-Gold candidate mới |
| N2 semantics | Attempt đầu thay stop cả các hộp đã vừa budget | Giữ attempt cũ; chỉ trigger naturalSL>25; đo lại Dev và rational bridges | Hai N2 implementations; corrected No-Go, không reuse backward làm OOS |
| Source/exposure | 2018–21 đã có prior use; M1 không thành tick | Giữ fence tới release; ghi nhãn đúng; seek partitions | Không sạch OOS, không broker validation |

## Quyết định cuối

**Không promote N1/N2 hoặc sleeve; chưa mua Challenge hoặc tăng risk.** V8 bác bỏ hai cách sửa cụ thể dưới chi phí/gates đã khóa; không bác toàn bộ trend-following hoặc Gold. Bước tiếp có ích phải là một giả thuyết kinh tế mới với budget/gates đăng ký rõ, hoặc cải thiện bằng chứng execution đích; không tiếp tục nới điều kiện chỉ để các bản này thành winner. Mục tiêu thu nhập chính vẫn chưa đạt.

## Bằng chứng

- Freeze trước backward: `91aa6701ddf5f963cd8856deb9538f158ac75553`; decision/protocol/calendar cùng prefixV 8 trong thư mục này.

- Full ledgers, tests, release, source proof, Development raw/outcomes: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/prop-gold-v8-20261115`.

- JSON cùng tên giữ baseline/control, annual/lifecycle, diagnostic attribution, canceled columns, oracle counts và hashes.

- Phép dựng lại báo cáo: `python tooling/ai-engines/prop_v8_report.py`; không phát sinh trial hoặc backtest mới.

- Nguồn lịch: V7 FTMO receipt và các declared guards; CME https://www.cmegroup.com/trading-hours.html ; https://www.cmegroup.com/trading/metals/files/metals-prod-guide-2020.pdf . Không dùng giờ NYSE thay giờ CFD được chứng nhận.

- FTMO correction 31/12/2021: https://ftmo.com/es/blog/trading-update-16-12-2021/ ; `PROP-V8-CALENDAR-CORRECTION-20261115.json` giữ source/old hash/scope.
