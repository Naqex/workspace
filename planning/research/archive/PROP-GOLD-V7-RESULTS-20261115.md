# V7 — Gold A sau sửa lịch và giải phẫu 2022–2026

Ngày 15/11/2026. **Kết luận: chưa đủ điều kiện Challenge hoặc làm nguồn thu nhập chính.** Đã sửa được việc dừng đo ngày 03/07/2026, nhưng bỏ EURUSD và tăng risk chưa giải quyết được tốc độ hoàn tất hai vòng. Gold năm 2025 cũng không dương ổn định giữa hai mức sizing đã dùng.

**Phạm vi:** Post-Holdout Diagnostic / Full-Sample 2022–2026 Audit; giá chỉ đến hết 13/10/2026. Dữ liệu 2025–2026 đã được xem ở V6; V7 không phải clean OOS. PR #85 đã merge tại `70b9ba1`; V7 dùng branch `codex/prop-gold-v7-audit`, không tự merge PR mới.

## 1. Đã sửa gì và dữ liệu đi qua đâu?

Giữ nguyên tín hiệu Asian Breakout theo H4, cả BUY/SELL, entry và Natural SL. Chỉ sửa deadline nghỉ lễ từ 2025, rồi chạy lại đường giá → admission/risk → cash/equity → hai vòng Challenge → Funded/harvester. EURUSD bị chặn ở admission của hai policy Gold; vẫn giữ trong cột đối chứng và lịch sử.

FTMO Trading Update 25/06/2026 ghi Metals đóng ngày 03/07/2026 lúc 20:00 MT5 GMT+3, tức 17:00 UTC. V6 tìm quote từ đúng giờ đóng. V7 đã khóa trước phép đo: flat trước 2 phút so với `min(guard nghỉ lễ cũ, giờ đóng đích đã xác minh)`, nên ngày đó thoát lúc **16:58 UTC**. Friday thường vẫn 20:30 UTC. Không dùng quote cũ tùy ý để lấp khoảng thiếu.

**Độ phủ:** 931/931 đường lệnh được định giá, gồm 320 đường lệnh 2025–2026. Có 12 hồ sơ đổi deadline, trong đó 6 hồ sơ đổi thời điểm thoát; entry/SL/side bảo toàn. 476/476 tín hiệu Gold có điểm thoát. Mỗi policy/phí có đủ 57 cửa sổ đến cutoff, 0 data censor, 0 vị thế mở.

**Giới hạn lịch:** đã liệt kê các ngày nghỉ 2025–2026; 11 ngày có giờ đóng đích kiểm được từ FTMO. Các ngày còn lại vẫn dùng guard bảo thủ có nhãn chưa xác minh, không được gọi toàn bộ lịch đã certified. Đủ endpoint không chứng minh đường tick của broker hoặc mọi luật hãng đã được kiểm.

## 2. Bốn cột so sánh đúng cùng câu hỏi

SYM = swap BUY/SELL −40/−40 USD/lot/rollover; ASYM = proxy −45/−5. Các cột mới đều giữ SL tự nhiên, không TP cứng, tối đa 48 giờ lịch, Friday/holiday flat. Cột V6 cũ bị dừng vì thiếu đường giá nên thời gian phơi nhiễm ngắn hơn.

Risk P1/P2/Funded: co-core sửa lịch và Gold V4 = **200/175/125 USD**; Gold tăng risk = **250/200/150 USD** trên vốn đầu 50.000 USD. Cả hai giữ cap open-stop 800 USD, reserve nội bộ 46.000 USD, giảm risk khi equity ≤48k/47k, daily realized halt 1.000 USD. Reserve 8% là chốt nội bộ, khác giới hạn overall 10% của profile.

Profile mô phỏng: FTMO Standard 2-Step 50k, mục tiêu P1 +10% / P2 +5%, daily/static limits 5%/10% theo reset Prague. Gold commission 0,0007% notional/side, stress slippage 0,20 USD/oz/side; không hard TP. Swap tính theo lịch rollover đã pin, có ngày hệ số ba. Đây là cấu hình nghiên cứu, chưa phải bản xác nhận lịch sử đầy đủ từ tài khoản đích.

### 36 mốc khởi đầu 2022–2024 — SYM_FLAT

| Chỉ số | V6 co-core dừng sớm | Co-core sửa lịch | Gold V4 | Gold tăng risk |
|---|---|---|---|---|
| Qua P1 /36 | 23 | 23 | 17 | 19 |
| Qua cả 2 /36 | 7 | 7 | 0 | 0 |
| Cửa sổ có payout /36 | 7 | 7 | 0 | 0 |
| Sự kiện payout | 23 | 23 | 0 | 0 |
| Data-censored /36 | 20 | 0 | 0 | 0 |
| Tổng trader USD, cửa sổ chồng lấn | 6,678.20 | 6,665.67 | 0.00 | 0.00 |
| Daily loss cao nhất % | 1.341 | 1.341 | 1.071 | 1.335 |
| Static loss cao nhất % | 8.064 | 8.064 | 7.363 | 7.980 |
| Peak-to-valley cao nhất % vốn đầu | 14.468 | 14.468 | 9.094 | 11.416 |
| Tháng tới cả 2, median trong số thành công | 17.38 | 17.38 | N/A | N/A |

### 36 mốc khởi đầu 2022–2024 — ASYM_FLAT

| Chỉ số | V6 co-core dừng sớm | Co-core sửa lịch | Gold V4 | Gold tăng risk |
|---|---|---|---|---|
| Qua P1 /36 | 26 | 26 | 23 | 22 |
| Qua cả 2 /36 | 7 | 7 | 0 | 1 |
| Cửa sổ có payout /36 | 6 | 6 | 0 | 1 |
| Sự kiện payout | 21 | 21 | 0 | 2 |
| Data-censored /36 | 21 | 0 | 0 | 0 |
| Tổng trader USD, cửa sổ chồng lấn | 6,369.78 | 6,359.04 | 0.00 | 408.04 |
| Daily loss cao nhất % | 1.280 | 1.280 | 0.979 | 1.221 |
| Static loss cao nhất % | 8.061 | 8.061 | 6.267 | 7.878 |
| Peak-to-valley cao nhất % vốn đầu | 14.365 | 14.365 | 8.356 | 10.812 |
| Tháng tới cả 2, median trong số thành công | 16.36 | 16.36 | N/A | 37.38 |

### 21 mốc mới 01/2025–09/2026

| Chỉ số | V6 co-core dừng sớm | Co-core sửa lịch | Gold V4 | Gold tăng risk |
|---|---|---|---|---|
| SYM_FLAT: P1 / cả 2 /21 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| SYM_FLAT: data-censored /21 | 17 | 0 | 0 | 0 |
| ASYM_FLAT: P1 / cả 2 /21 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| ASYM_FLAT: data-censored /21 | 17 | 0 | 0 | 0 |

Các mốc mới **0/21 qua P1** ở cả ba policy và hai phí. Những mốc gần cutoff có ít thời gian; đây là kết quả lịch sử có giới hạn thời gian, không phải xác suất thất bại tương lai. Các cửa sổ chồng lấn dùng chung tín hiệu nên không cộng payout thành thu nhập một tài khoản. `RIGHT_CENSORED` còn xuất hiện khi vòng đời chưa đạt mục tiêu trước cutoff; khác `path_censor` do thiếu giá, nay bằng 0.

**Bỏ EURUSD giảm rủi ro nhưng làm số mốc hoàn tất hai vòng giảm trong mẫu này.** Không thể lấy −18,11R EUR rồi cộng ngược vào danh mục: admission, lot, throttle, thời điểm đổi phase và rút lợi nhuận đều thay đổi theo đường vốn.

### Standalone Funded: khởi đầu 01/2022, nối đến 13/10/2026

Sổ này giả định đã có Funded ngay từ đầu, không chứng minh vượt Challenge. Tiền dưới đây là phần thưởng mô phỏng sau chia 80/20, chưa trừ phí mua/retry/vận hành, không phải khoản đã nhận. V6 cũ Jan2022 chỉ đo 2022–2024 nên khác thời lượng.

| Policy | Phí | Payout | Trader USD | Balance cuối | Daily % | Static % |
|---|---|---|---|---|---|---|
| V6 co-core chỉ 2022–2024 | SYM_FLAT | 12 | 3,856.49 | 49,693.25 | 0.832 | 7.869 |
| COCORE_FIXED | SYM_FLAT | 16 | 5,010.13 | 46,245.77 | 0.832 | 7.869 |
| GOLD_V4 | SYM_FLAT | 18 | 3,656.35 | 48,967.89 | 0.654 | 4.749 |
| GOLD_SCALED | SYM_FLAT | 15 | 4,048.26 | 48,768.68 | 0.799 | 5.730 |
| V6 co-core chỉ 2022–2024 | ASYM_FLAT | 12 | 3,667.64 | 49,744.20 | 0.795 | 7.846 |
| COCORE_FIXED | ASYM_FLAT | 16 | 4,858.96 | 46,715.91 | 0.795 | 7.846 |
| GOLD_V4 | ASYM_FLAT | 19 | 4,145.22 | 48,981.94 | 0.597 | 4.438 |
| GOLD_SCALED | ASYM_FLAT | 15 | 4,732.30 | 48,787.83 | 0.731 | 5.355 |

| Policy | Phí | 2022 lần/USD | 2023 | 2024 | 2025 | 2026 tới cutoff |
|---|---|---|---|---|---|---|
| COCORE_FIXED | SYM_FLAT | 9 / 2,644.34 | 3 / 1,212.15 | 0 / 0.00 | 4 / 1,153.64 | 0 / 0.00 |
| GOLD_V4 | SYM_FLAT | 5 / 1,275.69 | 5 / 1,341.13 | 0 / 0.00 | 5 / 679.57 | 3 / 359.96 |
| GOLD_SCALED | SYM_FLAT | 5 / 1,510.91 | 5 / 1,721.42 | 0 / 0.00 | 4 / 770.46 | 1 / 45.47 |
| COCORE_FIXED | ASYM_FLAT | 10 / 2,909.94 | 2 / 757.70 | 0 / 0.00 | 4 / 1,191.32 | 0 / 0.00 |
| GOLD_V4 | ASYM_FLAT | 5 / 1,241.45 | 6 / 1,738.56 | 0 / 0.00 | 5 / 763.29 | 3 / 401.92 |
| GOLD_SCALED | ASYM_FLAT | 5 / 1,555.43 | 5 / 2,204.98 | 0 / 0.00 | 4 / 874.22 | 1 / 97.67 |

JSON kèm đủ 5 mốc Funded 01/2022…01/2026 và payout theo quý của sổ 01/2022. Không mô hình nào ghi nhận breach trên đường đã dựng; chưa thành bảo đảm an toàn broker. Gold tăng risk cho nhiều tiền mô phỏng hơn ở một số sổ Funded, nhưng **không được chọn để promote** vì challenge time-fit vẫn yếu và static loss ở nhóm rolling cũ đã gần reserve nội bộ 8%.

## 3. Gold A từng năm ở cùng budget 150 USD/lệnh

1R ở bảng này = 150 USD, tức 0,30% vốn đầu 50k. Đây là sổ tham chiếu annual, không áp throttle/harvester của lifecycle. BUY và SELL là phân rã, không chọn phía tốt sau kết quả. 2026 là YTD đến 13/10, không phải cả năm.

| Năm | BUY/SELL thô | Tín hiệu | Thực thi | Có giá thoát | Net R SYM | Net R ASYM |
|---|---|---|---|---|---|---|
| 2022 | 54/49 | 103 | 103 | 103/103 | 4.0499 | 5.9006 |
| 2023 | 57/50 | 107 | 107 | 107/107 | 13.7949 | 16.4619 |
| 2024 | 61/37 | 98 | 98 | 98/98 | 1.8453 | 2.6449 |
| 2025 | 72/24 | 96 | 96 | 96/96 | -0.2847 | -0.1347 |
| 2026 | 39/33 | 72 | 71 | 72/72 | 3.1745 | 3.5321 |

Năm 2026 có **72 tín hiệu có giá, 71 lệnh thực thi**: 1 tín hiệu vượt budget ở minimum lot. Không tự tăng risk để ép tín hiệu đó thành lệnh.

### Phân rã SYM_FLAT

| Năm | BUY R | SELL R | Mean R/lệnh | Peak-valley R | Peak % vốn đầu | Static % | Daily % |
|---|---|---|---|---|---|---|---|
| 2022 | -0.763 | 4.813 | 0.0393 | 16.617 | 4.985 | 1.112 | 0.686 |
| 2023 | 3.206 | 10.589 | 0.1289 | 22.177 | 6.653 | 3.202 | 0.799 |
| 2024 | 14.934 | -13.089 | 0.0188 | 13.233 | 3.970 | 3.486 | 0.623 |
| 2025 | 1.487 | -1.772 | -0.0030 | 14.701 | 4.410 | 0.555 | 0.655 |
| 2026 | 3.654 | -0.480 | 0.0447 | 9.111 | 2.733 | 0.663 | 0.528 |

### Phân rã ASYM_FLAT

| Năm | BUY R | SELL R | Mean R/lệnh | Peak-valley R | Peak % vốn đầu | Static % | Daily % |
|---|---|---|---|---|---|---|---|
| 2022 | -1.033 | 6.934 | 0.0573 | 15.975 | 4.792 | 1.112 | 0.698 |
| 2023 | 2.858 | 13.604 | 0.1538 | 20.893 | 6.268 | 2.818 | 0.731 |
| 2024 | 14.689 | -12.044 | 0.0270 | 12.977 | 3.893 | 3.409 | 0.624 |
| 2025 | 1.287 | -1.422 | -0.0014 | 14.486 | 4.346 | 0.509 | 0.657 |
| 2026 | 3.620 | -0.088 | 0.0497 | 8.942 | 2.682 | 0.664 | 0.527 |

### Hiệu chỉnh kết luận “Gold dương bốn năm liên tiếp”

V6 đo Gold 2025 tại risk 125 USD; bảng annual V7 dùng 150 USD để nhất quán với 2022–2024. Cùng tập 96 tín hiệu, số ounce phải làm tròn xuống theo minimum/step 0,01 lot = 1 oz. Tăng budget có thể tăng lượng ở lệnh thua mà chưa tăng ở lệnh thắng; tổng R không bất biến theo sizing.

| Phí | Lịch cũ $125 | Lịch cũ $150 | Lịch sửa $125 | Lịch sửa $150 |
|---|---|---|---|---|
| SYM_FLAT | 2.8191 | -0.2764 | 2.8098 | -0.2847 |
| ASYM_FLAT | 2.9583 | -0.1264 | 2.9490 | -0.1347 |

**Vì vậy không thể coi Gold dương bền bốn năm ở cùng cách thực thi.** Hiệu ứng sửa lịch chỉ khoảng −0,01R; phần chênh lớn là trọng số khối lượng. Hai budget đã thuộc policy được giao; phép đối chiếu để giải thích, không chọn 125 USD để cứu năm 2025.

## 4. Vì sao Gold chậm lại?

| Năm | Giá entry median | Asia range USD/oz | SL USD/oz | SL/ATR | SL/giá % | Dùng budget % |
|---|---|---|---|---|---|---|
| 2022 | 1,808.84 | 7.93 | 11.51 | 2.60 | 0.64 | 96.29 |
| 2023 | 1,935.39 | 6.93 | 8.67 | 2.38 | 0.45 | 97.25 |
| 2024 | 2,399.08 | 11.06 | 15.37 | 2.79 | 0.62 | 95.05 |
| 2025 | 3,333.66 | 23.33 | 28.21 | 3.14 | 0.89 | 90.35 |
| 2026 | 4,495.20 | 46.06 | 58.85 | 3.00 | 1.28 | 82.46 |

Vùng Á và stop tăng không chỉ vì giá vàng cao hơn: SL/giá tăng từ 0,64% lên 1,28%; SL/ATR cũng thay đổi. Cùng một quãng đi tiếp bằng USD nay đem lại ít R hơn khi stop lớn; minimum lot làm sizing thô hơn. Đây là mô tả đo được, chưa chứng minh một nguyên nhân duy nhất. Sự đổi vai BUY/SELL cũng rõ: SELL tạo phần lớn lãi 2022–2023, nhưng mất khoảng 12R năm 2024; BUY bù lại. Không suy rằng cứ chọn BUY là sẽ giải quyết được.

### MFE và markout 24 giờ so với kết quả giữ tối đa 48 giờ

MFE là mức lãi nổi lớn nhất sau spread trên đường lệnh còn sống, trước commission/slip/swap. Ngày 1 ≤24h, ngày 2 >24h. Mark24 lấy giá tại min(entry+24h, actual exit), có phí; lệnh đã SL không được giả định tiếp tục sống.

| Năm | MFE ngày 1/2 | Còn sống sang ngày 2 | Mark24 R ASYM | Ngày 2 thêm R | Final R |
|---|---|---|---|---|---|
| 2022 | 77/26 | 47 | -2.347 | 8.247 | 5.901 |
| 2023 | 78/29 | 48 | 5.743 | 10.719 | 16.462 |
| 2024 | 75/23 | 47 | -8.465 | 11.110 | 2.645 |
| 2025 | 67/29 | 54 | 1.596 | -1.731 | -0.135 |
| 2026 | 54/18 | 39 | 11.994 | -8.462 | 3.532 |

MFE thường ở ngày 1 **không chứng minh thoát 24h tốt hơn**. Ngày 2 cứu lợi nhuận ở 2022–2024, nhưng lấy bớt lợi nhuận ở 2025–2026. Đây là chẩn đoán trên dữ liệu đã xem; không đăng ký/thử một policy 24h mới và không chọn horizon sau khi thấy bảng.

## 5. Các cấu hình Gold có sẵn trong Top 10 PR #80

| Cell cũ | Own R 2022/23 | Tương quan Gold | Gold+cell Net R | DD R | Source complete |
|---|---|---|---|---|---|
| XAUUSD.SWEEP.PREVDAY.LONDON.DAY | 17.10/9.93 | 0.111 | 35.63 | 18.82 | False |
| XAUUSD.SWEEP.PREVDAY.LONDON.24H | 11.54/13.22 | 0.100 | 34.54 | 19.47 | False |
| XAUUSD.SWEEP.PREVDAY.LONDON.48H | 6.13/17.38 | 0.120 | 34.02 | 20.40 | False |

Tái dùng đúng curves Development 2022–2023, Gold risk 150 USD + sleeve 75 USD, không EUR. Ba cell là cùng ý tưởng sweep với ba horizon, không phải ba alpha độc lập. Ví dụ DAY cải thiện sơ bộ ASYM từ 22,36R/DD20,89R thành 35,63R/DD18,82R.

**Chưa thêm cell nào:** source path chưa hoàn chỉnh; natural SL median 4,83/4,52 USD/oz, phí/SL 16,2%/16,7%, chỉ giữ 23/51 và 22/56 tín hiệu (45,1%/39,3%). Không đạt scale/retention gate. Chưa đo mới 2024–2026 cho các cell này; không gọi là winner ngoài mẫu.

## 6. Kiểm chứng, hậu kiểm kỹ thuật và giới hạn

| Thứ tự OHLC | Oracle | Sổ | Admissions | Rejects | Cost bridges | Dynamic fills |
|---|---|---|---|---|---|---|
| OPEN_LOW_HIGH_CLOSE | PASS | 402 | 103287 | 71271 | 103287 | 5 |
| OPEN_HIGH_LOW_CLOSE | PASS | 402 | 103287 | 71271 | 103287 | 5 |

**978 tests riêng biệt PASS**, gồm 11 fixtures V7; matrix dùng bốn môi trường dependency sẵn có. Alternate accounting dùng phân số hữu tỷ, cash-posted, đối chiếu admission/lot/risk, swap/commission/slip, phase/reward và DD cho 402 sổ mỗi thứ tự (342 rolling +30 Funded +30 reference). Cùng implementer, không có reviewer độc lập.

Gold 2025–2026 vẫn là **Bid M1 + Ask proxy 0,338 USD/oz**; hai thứ tự OHLC giả định là kiểm độ nhạy, không phải tick thật và không bao hết mọi intraminute path. Hai thứ tự cho cùng kết quả annual; số mốc pass/payout/breach cũng không đổi. Chênh aggregate là peak-DD co-core nhóm mới 0,0005 điểm phần trăm và thời điểm P1 Gold ở cấp giây; JSON giữ riêng toàn bộ lifecycle/sensitivity. Peak-to-valley co-core nhóm mới có thể vượt 14% vốn đầu dù static loss chưa chạm giới hạn: hai thước đo có mốc gốc khác nhau. Phí/swap là scenarios, lịch tin và thông số đích lịch sử chưa certified đầy đủ.

| Phần | Phát hiện | Xử lý / kiểm chứng | Còn hạn chế |
|---|---|---|---|
| Verifier | Đến ngưỡng harvest giữa hai clock events | Observe threshold ngay trước admission; 2 regression; oracle 804 sổ PASS | Cùng người viết; không independent person review |
| Source/lịch | Quote được yêu cầu đúng lúc holiday đóng | Rule trước 2 phút đã freeze; 0 endpoint thiếu | Chỉ 11 ngày có giờ FTMO đã xác minh |
| Reuse | Đã có đủ ledgers/Top10 và test environments | Tái dùng artifacts; không rerun producer sau sửa verifier | Không đo speedup/quota tiết kiệm |
| Skill/workflow | Rule hiện có đã yêu cầu giữ attempt và kiểm transition | Giữ failed attempts; cập nhật report/context, không thêm skill/config | Không mở vòng tối ưu mới |

Hai lần oracle đầu thất bại được giữ trong `parity-primary.log`, `parity-secondary.log`, `oracle-attempt1.json`. Lỗi ở verifier: chưa observe ngưỡng harvest đến hạn tại thời điểm entry; đã sửa verifier, không sửa producer hoặc số liệu giao dịch để pass.

## 7. Quyết định và bước tiếp

**EURUSD Sweep đã decommission khỏi ứng viên active. Gold A BOTH giữ làm baseline nghiên cứu, chưa promote Gold tăng risk, chưa thêm sleeve và chưa đổi sang exit 24h.** Nút thắt hiện tại là lợi nhuận không đều, quá chậm so với mục tiêu Challenge/payout, nhạy sizing và thiếu bằng chứng execution đích; chưa phải do chạm trần Daily Loss trong các đường mô phỏng.

Bước hợp lý tiếp theo là chốt khoảng thiếu về quote/cost/news của tài khoản đích và đăng ký một kiểm định hữu hạn trên dữ liệu thực sự mới khi có; không tiếp tục chỉnh trên 2025–2026 rồi gọi đó là kiểm định độc lập. V7 không mua Challenge, không gửi broker order, không nhận tiền thực.

## Bằng chứng và tái hiện

- Freeze trước outcome: `b5e5f08205c512264ac4c257bea70a27462c1513`.

- Protocol: `PROP-GOLD-V7-PROTOCOL-20261115.md`; decision: `PROP-GOLD-V7-DECISION-20261115.json`; calendar: `PROP-V7-SESSION-CALENDAR-20261115.json`.

- Báo cáo JSON cùng tên giữ 4 cột theo model/path, annual/side, rolling/Funded summaries, payout quý và hashes của ledgers đầy đủ.

- Full private ledgers/tests/failed attempts: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/prop-gold-v7-20261115`.

- Chỉ dựng lại báo cáo từ artifact: `python tooling/ai-engines/prop_v7_report.py` với PYTHONPATH hiện có; không chạy lại backtest.

- Nguồn FTMO/CME đã kiểm ở lượt sửa lịch, receipt: `calendar-source-receipt.json`. Các URL:

  - https://ftmo.com/en/blog/trading-updates/trading-update-12-feb-2026/

  - https://ftmo.com/en/blog/trading-updates/trading-update-15-jan-2026/

  - https://ftmo.com/en/blog/trading-updates/trading-update-18-dec-2025/

  - https://ftmo.com/en/blog/trading-updates/trading-update-20-nov-2025/

  - https://ftmo.com/en/blog/trading-updates/trading-update-21-may-2026/

  - https://ftmo.com/en/blog/trading-updates/trading-update-25-jun-2026/

  - https://ftmo.com/en/blog/trading-updates/trading-update-3-jul-2025/

  - https://ftmo.com/en/blog/trading-updates/trading-updates-27-aug-2026/

  - https://www.cmegroup.com/trading-hours.html
