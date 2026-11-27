# V18 — Tournament, Monte Carlo đường lệnh và bộ kit Free Trial

**Chưa có Champion đủ chứng cứ; chưa promote bot lên Free Trial/Challenge.** V16 là diagnostic velocity reference; V17 là diagnostic Funded backup theo rule đã khóa. Đây là kết luận chốt chiến dịch, không phải yêu cầu mở thêm grid.

PR #96/exact head `ee97543` đạt 3CI, merge `92569ca`; V17 branch đã xóa. Protocol `50c474f`, code/stress freeze `bec7fe1` trước batch 5.000 paths. Giữ VI WIP, Trader pin, nguồn, freezes và negative attempts.

## 1. Tournament V1–V17

17 hồ sơ/version có hash trong JSON. V9/V10 chủ yếu engineering; V11–V13 là discovery/kiểm dữ liệu; không coi mọi version là một chiến lược độc lập. PR78 Gold A và PR82 V4 giữ mẫu 36 starts/2022–2024; không cộng hoặc so raw pass count với 105 starts/2018–13Oct2026. PR93 là delivery V14; PR94 là V15.

| Bản (PRIMARY, xấu nhất hai phí/order) | Hai vòng/105 | Median tháng | Standalone static % | Standalone daily % | Standalone payout USD |
|---|---|---|---|---|---|
| V14 | 48 | 55,37 | 4,9442 | 0,5628 | 6.131,27 |
| V15 | 66 | 34,85 | 7,2315 | 0,8580 | 8.834,15 |
| V16 | 71 | 47,08 | 4,3908 | 0,7579 | 6.457,11 |
| V17 | 68 | 42,95 | 3,5945 | 0,6041 | 6.314,27 |

Champion gate cần source/path đủ chứng cứ và modeled daily<5%/static<10%; không candidate nào đạt source gate. Reference chọn bằng completion count rồi conditional median; V15 vẫn có median nhanh hơn V16. Backup chọn static thấp trong standalone PRIMARY và payout dương; tên Ultra-Safe chưa được chứng nhận, nhất là khi bật strict gap.

Sổ Funded riêng của backup V17, giữ nguyên risk/tier, không tuning lại:

| Order/phí/source | Static % | Daily % | Peak DD % | Payout count/USD |
|---|---|---|---|---|
| OLHC/SYM_FLAT/PRIMARY | 3,5945 | 0,6041 | 4,2525 | 35/6.314,27 |
| OLHC/ASYM_FLAT/PRIMARY | 3,5945 | 0,6041 | 4,2525 | 35/6.314,27 |
| OLHC/SYM_FLAT/STRICT | 8,3525 | 0,4554 | 8,4861 | 11/2.098,35 |
| OLHC/ASYM_FLAT/STRICT | 8,3525 | 0,4554 | 8,4861 | 11/2.098,35 |
| OHLC/SYM_FLAT/PRIMARY | 3,5945 | 0,6041 | 4,2525 | 35/6.314,27 |
| OHLC/ASYM_FLAT/PRIMARY | 3,5945 | 0,6041 | 4,2525 | 35/6.314,27 |
| OHLC/SYM_FLAT/STRICT | 8,3525 | 0,4554 | 8,4861 | 11/2.098,35 |
| OHLC/ASYM_FLAT/STRICT | 8,3525 | 0,4554 | 8,4861 | 11/2.098,35 |

Target static<6% chỉ được kiểm trong đúng cột nêu trên; kết quả PRIMARY không thay thế STRICT hoặc chứng nhận nguồn.

## 2. Kiểm định phí trên lịch sử nguyên thứ tự

Không đổi tín hiệu/SL/P1. Phí tăng thêm là half-spread+slippage mỗi side, làm tròn lên cent ở actual quantity. Lot, cushion/throttle, admission, equity, pass và payout được tính lại bằng native engine. Commission/funding không tự hạ. V16 intraday/noTP nên SYM/ASYM giống nhau; reuse có điều kiện này được ghi ở freeze.

| Order | Source | Friction | P1/105 | Hai vòng/105 | Median tháng | Daily % | Static % | Breach | Standalone USD |
|---|---|---|---|---|---|---|---|---|---|
| OLHC | PRIMARY | 1.0 | 81 | 71 | 47,08 | 1,9630 | 6,3825 | 0 | 6.457,11 |
| OLHC | PRIMARY | 1.25 | 80 | 69 | 68,89 | 1,9089 | 6,6027 | 0 | 5.403,33 |
| OLHC | PRIMARY | 1.5 | 74 | 7 | 87,09 | 1,9248 | 7,7228 | 0 | 4.170,00 |
| OLHC | STRICT | 1.0 | 18 | 1 | 18,95 | 1,9628 | 8,3997 | 0 | 1.824,95 |
| OLHC | STRICT | 1.25 | 10 | 0 | — | 1,9125 | 8,3998 | 0 | 1.716,67 |
| OLHC | STRICT | 1.5 | 4 | 0 | — | 2,0746 | 8,3996 | 0 | 1.608,79 |
| OHLC | PRIMARY | 1.0 | 81 | 71 | 47,08 | 1,9630 | 6,3825 | 0 | 6.457,11 |
| OHLC | PRIMARY | 1.25 | 80 | 69 | 68,89 | 1,9089 | 6,6027 | 0 | 5.403,33 |
| OHLC | PRIMARY | 1.5 | 74 | 7 | 87,09 | 1,9248 | 7,7228 | 0 | 4.170,00 |
| OHLC | STRICT | 1.0 | 18 | 1 | 18,95 | 1,9628 | 8,3997 | 0 | 1.824,95 |
| OHLC | STRICT | 1.25 | 10 | 0 | — | 1,9125 | 8,3998 | 0 | 1.716,67 |
| OHLC | STRICT | 1.5 | 4 | 0 | — | 2,0746 | 8,3996 | 0 | 1.608,79 |

Bảng reference dưới đây dùng cùng risk 150 USD/lệnh và lot floor, bỏ riêng entry không đạt minimum lot với counter minh bạch. Không có account cap/harvester trong sổ reference; Net R không là % return của tài khoản.

| Order/source | Friction | Reference net R | Reference net USD |
|---|---|---|---|
| OLHC/PRIMARY | 1.0 | 42,3035 | 6.345,52 |
| OLHC/PRIMARY | 1.25 | 35,4681 | 5.320,22 |
| OLHC/PRIMARY | 1.5 | 28,6652 | 4.299,78 |
| OLHC/STRICT | 1.0 | -5,0474 | -757,11 |
| OLHC/STRICT | 1.25 | -11,8827 | -1.782,41 |
| OLHC/STRICT | 1.5 | -18,6857 | -2.802,85 |
| OHLC/PRIMARY | 1.0 | 42,3035 | 6.345,52 |
| OHLC/PRIMARY | 1.25 | 35,4681 | 5.320,22 |
| OHLC/PRIMARY | 1.5 | 28,6652 | 4.299,78 |
| OHLC/STRICT | 1.0 | -5,0474 | -757,11 |
| OHLC/STRICT | 1.25 | -11,8827 | -1.782,41 |
| OHLC/STRICT | 1.5 | -18,6857 | -2.802,85 |

JSON giữ per-year economics, kể cả 2026 YTD. Tổng dương không che các năm yếu. Surcharge là cost sensitivity trên đường SL/P1 đã đóng băng; chưa tái tạo mọi stop crossing khác khi Ask/Bid giãn. Không gọi đây là broker-fill stress đã chứng nhận.

## 3. 5.000 đường quote/event bootstrap

Một seed và cùng 5.000 draw sequences cho 12 ca: hai ordering × PRIMARY/STRICT × ba mức phí. Giữ mọi asset/trade cùng quý, toàn bộ ordered quote excursions khi có cơ hội mở, các clock/entry/exit và native risk/harvest state. Quý thiếu cuối mẫu không lấy; không loại lệnh thua/gap. Bốn preflight tái hiện đúng 105 starts+standalone bản V16; baseline và bản tối ưu giữ riêng.

Pool 35 quý đầy đủ giữ 493 tín hiệu; 1 tín hiệu của quý cuối chưa đủ được giữ trong historical table, không ghép vào pool như một quý hoàn chỉnh. Source proof xác nhận spread proxy cố định Gold 0,338 USD/oz và EUR 1 pip trên toàn bộ quote path, không có lượt rollover nào trong tape. Đây không phải biểu phí tài khoản đích.

Yêu cầu 24 tháng kèm horizon 36 được đáp ứng bằng một extension 36 tháng của cùng các paths; 12/18/24 là prefix. Reset Prague của nguồn được sao chép trong mỗi quý, payout timer theo elapsed calendar days. Đây là synthetic source-clock tape, không phát sinh một lịch tương lai mới. Vì reference intraday và seams flat, không có vị thế bị cắt ở biên quý.

### Cohort `random`

Favorable/sideways là nhãn hồi tố của năm nguồn đầu tiên đã khóa trên Dev; chỉ quý đầu mang nhãn đó, các quý sau vẫn draw ngẫu nhiên. Không giả định giữ nguyên một năm thuận lợi hoặc nhận diện được regime tại entry.

| Order/source/phí | N | P1 12/18/24/36 % | Hai vòng 12/18/24/36 % | Daily breach36 % | Static breach36 % | Funded mean annual USD P25/P50/P75 |
|---|---|---|---|---|---|---|
| OLHC/PRIMARY/1.0 | 5000 | 22,68/39,22/52,24/67,88 | 1,24/6,08/14,32/33,36 | 0,00 | 0,00 | 544,92/908,19/1.301,19 |
| OLHC/PRIMARY/1.25 | 5000 | 19,02/33,98/45,90/61,18 | 0,96/4,54/10,86/27,26 | 0,00 | 0,00 | 459,24/815,41/1.196,95 |
| OLHC/PRIMARY/1.5 | 5000 | 16,36/29,42/40,40/54,88 | 0,78/3,48/8,54/21,70 | 0,00 | 0,00 | 388,07/721,66/1.093,53 |
| OLHC/STRICT/1.0 | 5000 | 6,64/11,70/16,54/23,06 | 0,06/0,40/1,48/4,54 | 0,00 | 0,00 | 142,07/343,91/626,56 |
| OLHC/STRICT/1.25 | 5000 | 4,68/9,10/12,68/18,06 | 0,04/0,20/0,76/2,94 | 0,00 | 0,00 | 110,46/292,87/550,22 |
| OLHC/STRICT/1.5 | 5000 | 3,36/6,56/9,54/13,54 | 0,04/0,10/0,54/1,72 | 0,00 | 0,00 | 81,69/242,97/478,51 |
| OHLC/PRIMARY/1.0 | 5000 | 22,68/39,22/52,24/67,88 | 1,24/6,08/14,32/33,36 | 0,00 | 0,00 | 544,92/908,19/1.301,19 |
| OHLC/PRIMARY/1.25 | 5000 | 19,02/33,98/45,90/61,18 | 0,96/4,54/10,86/27,26 | 0,00 | 0,00 | 459,24/815,41/1.196,95 |
| OHLC/PRIMARY/1.5 | 5000 | 16,36/29,42/40,40/54,88 | 0,78/3,48/8,54/21,70 | 0,00 | 0,00 | 388,07/721,66/1.093,53 |
| OHLC/STRICT/1.0 | 5000 | 6,64/11,70/16,54/23,06 | 0,06/0,40/1,48/4,54 | 0,00 | 0,00 | 142,07/343,91/626,56 |
| OHLC/STRICT/1.25 | 5000 | 4,68/9,10/12,68/18,06 | 0,04/0,20/0,76/2,94 | 0,00 | 0,00 | 110,46/292,87/550,22 |
| OHLC/STRICT/1.5 | 5000 | 3,36/6,56/9,54/13,54 | 0,04/0,10/0,54/1,72 | 0,00 | 0,00 | 81,69/242,97/478,51 |
### Cohort `favorable_start`

Favorable/sideways là nhãn hồi tố của năm nguồn đầu tiên đã khóa trên Dev; chỉ quý đầu mang nhãn đó, các quý sau vẫn draw ngẫu nhiên. Không giả định giữ nguyên một năm thuận lợi hoặc nhận diện được regime tại entry.

| Order/source/phí | N | P1 12/18/24/36 % | Hai vòng 12/18/24/36 % | Daily breach36 % | Static breach36 % | Funded mean annual USD P25/P50/P75 |
|---|---|---|---|---|---|---|
| OLHC/PRIMARY/1.0 | 1146 | 31,76/48,87/60,56/74,78 | 2,09/8,38/19,02/40,84 | 0,00 | 0,00 | 664,93/1.023,97/1.410,55 |
| OLHC/PRIMARY/1.25 | 1146 | 25,04/41,36/53,75/67,54 | 1,66/6,20/14,14/32,72 | 0,00 | 0,00 | 572,76/927,34/1.305,78 |
| OLHC/PRIMARY/1.5 | 1146 | 21,64/36,13/47,99/61,26 | 1,40/4,54/10,99/26,53 | 0,00 | 0,00 | 495,55/830,08/1.196,20 |
| OLHC/STRICT/1.0 | 1146 | 14,83/21,73/27,31/32,55 | 0,17/0,96/3,32/8,64 | 0,00 | 0,00 | 232,36/469,78/766,51 |
| OLHC/STRICT/1.25 | 1146 | 9,69/15,97/20,07/25,13 | 0,09/0,44/1,83/5,06 | 0,00 | 0,00 | 206,74/404,25/676,98 |
| OLHC/STRICT/1.5 | 1146 | 7,59/12,91/16,58/20,51 | 0,09/0,35/1,48/3,23 | 0,00 | 0,00 | 175,46/353,97/610,47 |
| OHLC/PRIMARY/1.0 | 1146 | 31,76/48,87/60,56/74,78 | 2,09/8,38/19,02/40,84 | 0,00 | 0,00 | 664,93/1.023,97/1.410,55 |
| OHLC/PRIMARY/1.25 | 1146 | 25,04/41,36/53,75/67,54 | 1,66/6,20/14,14/32,72 | 0,00 | 0,00 | 572,76/927,34/1.305,78 |
| OHLC/PRIMARY/1.5 | 1146 | 21,64/36,13/47,99/61,26 | 1,40/4,54/10,99/26,53 | 0,00 | 0,00 | 495,55/830,08/1.196,20 |
| OHLC/STRICT/1.0 | 1146 | 14,83/21,73/27,31/32,55 | 0,17/0,96/3,32/8,64 | 0,00 | 0,00 | 232,36/469,78/766,51 |
| OHLC/STRICT/1.25 | 1146 | 9,69/15,97/20,07/25,13 | 0,09/0,44/1,83/5,06 | 0,00 | 0,00 | 206,74/404,25/676,98 |
| OHLC/STRICT/1.5 | 1146 | 7,59/12,91/16,58/20,51 | 0,09/0,35/1,48/3,23 | 0,00 | 0,00 | 175,46/353,97/610,47 |
### Cohort `sideways_start`

Favorable/sideways là nhãn hồi tố của năm nguồn đầu tiên đã khóa trên Dev; chỉ quý đầu mang nhãn đó, các quý sau vẫn draw ngẫu nhiên. Không giả định giữ nguyên một năm thuận lợi hoặc nhận diện được regime tại entry.

| Order/source/phí | N | P1 12/18/24/36 % | Hai vòng 12/18/24/36 % | Daily breach36 % | Static breach36 % | Funded mean annual USD P25/P50/P75 |
|---|---|---|---|---|---|---|
| OLHC/PRIMARY/1.0 | 1160 | 12,41/29,57/44,05/61,98 | 0,17/2,67/9,40/26,81 | 0,00 | 0,00 | 469,44/819,35/1.182,83 |
| OLHC/PRIMARY/1.25 | 1160 | 9,74/25,34/37,07/55,17 | 0,17/1,98/6,64/21,21 | 0,00 | 0,00 | 387,24/717,87/1.079,68 |
| OLHC/PRIMARY/1.5 | 1160 | 7,59/20,60/31,21/47,93 | 0,17/1,81/5,26/15,95 | 0,00 | 0,00 | 310,07/623,12/980,10 |
| OLHC/STRICT/1.0 | 1160 | 2,93/8,02/13,45/20,43 | 0,00/0,26/0,95/3,62 | 0,00 | 0,00 | 130,15/317,77/590,43 |
| OLHC/STRICT/1.25 | 1160 | 1,81/5,60/9,83/16,21 | 0,00/0,09/0,26/2,33 | 0,00 | 0,00 | 91,56/266,45/505,02 |
| OLHC/STRICT/1.5 | 1160 | 1,03/3,88/6,81/11,64 | 0,00/0,00/0,17/1,03 | 0,00 | 0,00 | 80,23/214,52/433,40 |
| OHLC/PRIMARY/1.0 | 1160 | 12,41/29,57/44,05/61,98 | 0,17/2,67/9,40/26,81 | 0,00 | 0,00 | 469,44/819,35/1.182,83 |
| OHLC/PRIMARY/1.25 | 1160 | 9,74/25,34/37,07/55,17 | 0,17/1,98/6,64/21,21 | 0,00 | 0,00 | 387,24/717,87/1.079,68 |
| OHLC/PRIMARY/1.5 | 1160 | 7,59/20,60/31,21/47,93 | 0,17/1,81/5,26/15,95 | 0,00 | 0,00 | 310,07/623,12/980,10 |
| OHLC/STRICT/1.0 | 1160 | 2,93/8,02/13,45/20,43 | 0,00/0,26/0,95/3,62 | 0,00 | 0,00 | 130,15/317,77/590,43 |
| OHLC/STRICT/1.25 | 1160 | 1,81/5,60/9,83/16,21 | 0,00/0,09/0,26/2,33 | 0,00 | 0,00 | 91,56/266,45/505,02 |
| OHLC/STRICT/1.5 | 1160 | 1,03/3,88/6,81/11,64 | 0,00/0,00/0,17/1,03 | 0,00 | 0,00 | 80,23/214,52/433,40 |

JSON có cả payout quantiles từng năm 1/2/3, zeros và stopped paths. Các tỷ lệ trên là tần suất có điều kiện của resampling lịch sử đã exposed, không phải xác suất đậu tương lai được hiệu chỉnh. SOURCE uncertainty giữ nguyên; strict chỉ là giả định excursion chung, không phục hồi dữ liệu hoặc tạo source certificate.

Payout Funded 50k từng năm của cohort random; mỗi ô là P25/P50/P75 USD:

| Order/source/phí | Năm 1 | Năm 2 | Năm 3 |
|---|---|---|---|
| OLHC/PRIMARY/1.0 | 543,13/1.064,91/1.714,63 | 98,42/676,03/1.357,12 | 0,00/578,97/1.305,08 |
| OLHC/PRIMARY/1.25 | 481,39/981,99/1.613,13 | 26,38/561,39/1.230,50 | 0,00/442,86/1.164,75 |
| OLHC/PRIMARY/1.5 | 440,21/895,47/1.513,11 | 0,00/447,78/1.103,09 | 0,00/310,30/1.018,60 |
| OLHC/STRICT/1.0 | 188,73/584,73/1.056,28 | 0,00/0,00/519,80 | 0,00/0,00/313,83 |
| OLHC/STRICT/1.25 | 145,22/539,31/986,41 | 0,00/0,00/414,51 | 0,00/0,00/162,67 |
| OLHC/STRICT/1.5 | 111,16/482,72/909,15 | 0,00/0,00/303,92 | 0,00/0,00/35,55 |
| OHLC/PRIMARY/1.0 | 543,13/1.064,91/1.714,63 | 98,42/676,03/1.357,12 | 0,00/578,97/1.305,08 |
| OHLC/PRIMARY/1.25 | 481,39/981,99/1.613,13 | 26,38/561,39/1.230,50 | 0,00/442,86/1.164,75 |
| OHLC/PRIMARY/1.5 | 440,21/895,47/1.513,11 | 0,00/447,78/1.103,09 | 0,00/310,30/1.018,60 |
| OHLC/STRICT/1.0 | 188,73/584,73/1.056,28 | 0,00/0,00/519,80 | 0,00/0,00/313,83 |
| OHLC/STRICT/1.25 | 145,22/539,31/986,41 | 0,00/0,00/414,51 | 0,00/0,00/162,67 |
| OHLC/STRICT/1.5 | 111,16/482,72/909,15 | 0,00/0,00/303,92 | 0,00/0,00/35,55 |

## 4. Kiểm toán, health và bàn giao

Native kiểm **120,000 cash bridges** của challenge/standalone. Independent Decimal oracle kiểm đầy đủ sổ và quote path ở 32 sampled paths/ca ×2 loại account: **768 sổ mẫu**, cùng 48 historical cases stress mới và 24 cases baseline preflight. Các source first-pass paths kế thừa audit V16/V17 có binding. Không gọi sample oracle là audit độc lập 100% Monte Carlo; cùng implementer/feed.

Các lỗi padding/quote-key/multi-close trong adapter audit đã được ghi nhận trước full batch và sửa bằng regression; không sửa tín hiệu hay chọn lại mẫu. Bỏ memmap subclass overhead/flat excursion dispatch chỉ sau full ledger parity; không bỏ reset/session/entry/exit clocks.

Full **1153 PASS/0 skip**, giữ đủ 1148 V17 IDs. Wall **22,062s**, V17 **21,144s**; smoke 10 fresh ×78 tests, max **0,853s**, **7/10 lần <0,80s; chưa đạt mục tiêu 10/10**. Cả 10 lần đều PASS về chức năng, 0 skip. Giữ nguyên outliers, không thử lại để lấy chuỗi đẹp. Không chạy performance benchmark khi financial jobs còn tranh CPU; không suy ra speedup toàn máy.

| Root | Baseline GiB | Hiện tại GiB | Giảm ròng GiB | Files hiện tại | Lỗi đọc |
|---|---|---|---|---|---|
| D | 208,59 | 197,23 | 11,36 | 575771 | 2 |
| E | 319,68 | 215,00 | 104,68 | 557620 | 0 |

Snapshot đọc được giảm ròng **116,04GiB**, **156,924 files** so canonical V9 receipts. Theo mốc file owner 633.488/656.692 là **156,789 files**; hai mốc khác thời điểm. Purge cache/build disjoint có biên nhận **153,058 lượt tệp / 122,37GiB**. Archive/copy/log removals V9/V10/V14–17 dẫn riêng để tránh cộng trùng; con số purge không bằng snapshot net vì có output phát sinh và archive giữ lại. Chưa đo physical reclaimed bytes. Hai lỗi đọc D thuộc VI pytest được giữ nguyên; không đụng WIP, source, data, matrices hay ledger.

Kit: [FTMO-FREE-TRIAL-EXECUTION-SPEC-20261116.md](FTMO-FREE-TRIAL-EXECUTION-SPEC-20261116.md). Có thể chuẩn bị quote/spec capture sau khi binding/terms đích được kiểm; chưa có EA/parity/news guard/owner handover cho strategy orders. Free Trial terms hiện hành chưa truy cập lại thành công; dùng snapshot 02/11 làm tham chiếu có nhãn. Quote-only không đo được slippage. Không mua Challenge/đăng ký account/gửi lệnh trong V18.

Morning brief: [MORNING-EXECUTIVE-SUMMARY-20261116.md](MORNING-EXECUTIVE-SUMMARY-20261116.md). PR #97 giữ mở; exact-head 3CI và downloaded test IDs phải được đối soát bằng receipt private sau push. Không sửa HEAD chỉ để tự đóng dấu. Evidence `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\final-convergence-v18-20261116`; JSON≤1MiB. Giữ tất cả freezes/attempts và Trader pin/VI WIP.
