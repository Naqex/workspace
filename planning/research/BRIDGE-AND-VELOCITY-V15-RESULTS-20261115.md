# V15 — Khoảng thiếu giá, đóng góp từng nhánh và tốc độ đi vốn

**Chưa nên mua Challenge.** SYM: mức 1,5× tăng số hoàn tất từ 48 lên 63/105 và giảm median từ 54 xuống 41,03 tháng; cushion đạt 66/105 và 34,85 tháng. Vẫn chưa đạt mục tiêu dưới 18 tháng. Stress mọi gap chưa được chứng nhận chỉ đạt 0/105 hoàn tất: bất định dữ liệu vẫn là rào cản lớn. Candidate B dừng tối ưu, hai nhánh thêm chỉ được giữ để giải thích kết quả.

PR #93 đã merge `69bc7a6`; xóa nhánh V14. Đăng ký V15 tại `7ed51a5`, khóa sizing/code tại `4b426ae` sau khi kiểm toán Development và trước khi đo sizing mới trên 2024–13/10/2026. Giá và baseline giai đoạn này đã có exposure, không gọi là OOS nguyên vẹn.

## 1. Có phải việc bỏ lệnh qua gap làm lệch mẫu?

| Giai đoạn / nhóm | Lệnh | Giữ trung vị (giờ) | Thắng / thua | SYM Net R |
|---|---:|---:|---:|---:|
| DEV / NO_UNKNOWN_GAP | 296 | 5.13 | 128/168 | +33.00 |
| DEV / UNKNOWN_GAP | 44 | 18.77 | 27/17 | +17.23 |
| VALIDATION / NO_UNKNOWN_GAP | 142 | 5.52 | 60/82 | +4.30 |
| VALIDATION / UNKNOWN_GAP | 12 | 10.50 | 5/7 | +9.60 |

Nhóm qua gap giữ lâu hơn, nhưng không phải toàn bộ là lệnh thắng. Đây là bằng chứng liên hệ giữa thời gian giữ và khả năng gặp gap; không phải chứng minh nhân quả, cũng không xác nhận rằng SL chưa chạm trong phút bị thiếu.

| Giai đoạn | Lần giao cắt gap | Chỉ nghỉ đã biết | Gap có thiếu nguồn <15 / >=15 phút | Gap thiếu nguồn riêng biệt |
|---|---:|---:|---:|---:|
| DEV | 217 | 106 | 107 / 4 | 111 |
| VALIDATION | 78 | 56 | 22 / 0 | 22 |

Riêng nhóm lệnh uncertain (44 Dev / 12 Validation):

| Giai đoạn | Lần giao cắt gap | Có phút nghỉ daily | Thiếu nguồn <15 phút đêm/ngày | Thiếu nguồn >=15 phút đêm/ngày |
|---|---:|---:|---:|---:|
| DEV | 137 | 30 | 64/43 | 0/4 |
| VALIDATION | 29 | 7 | 9/13 | 0/0 |

Các khoảng có cả rollover và phút thiếu nguồn được tính là gap có thiếu nguồn; độ dài trên là toàn khoảng. Một gap có thể giao nhiều lệnh; không cộng các lần giao cắt như số sự kiện độc lập. Cột daily có thể trùng cột thiếu nguồn vì một gap có cả hai. Đêm được mô tả theo phút thiếu đầu tiên trong 22:00–06:59 UTC, không dùng làm filter. Chi tiết từng phút/loại nằm trong JSON gốc.

Trong 133 lần giao cắt thiếu nguồn toàn kỳ: **38** được extrema tick native loại trừ SL có điều kiện trên tập quote đã xuất; **95** chỉ được mô hình đánh giá rủi ro thấp. **0 chứng nhận biên giá thị trường tuyệt đối.** Metadata census không tìm được nguồn HTF standalone được admit; aggregate từ chính M1 thiếu không được coi là nguồn mới.

Brownian bridge có đuôi xác suất dương; `3σ√t` không phải mức giá tối đa có thể xảy ra. Dùng khoảng cách có dấu để không bỏ sót endpoint đã xuyên SL. Mô hình cố định không chọn gap mơ hồ nào, nên cột bridge chính bằng baseline. Điều đó không có nghĩa đã lấp hoặc chứng nhận toàn bộ dữ liệu.

Kiểm tra raw riêng đối chiếu lại hai endpoint của mọi gap. Estimator ban đầu lấy tối đa 241 increments thay vì 240 như protocol; sensitivity đúng 240 không đổi bất kỳ nhãn nào, không đổi đường stress hay kết quả tài chính. Giữ nguyên artifact gốc.

**Sensitivity bổ sung:** chèn một đường OHLC giả định dùng chung cho mọi vị thế cùng tài sản tại mọi gap chưa được chứng nhận thị trường. Giữ nguyên các bar quan sát, entry, SL và hạn giữ; P1 được replay nhân quả. Không gán độc lập mỗi lệnh một giá giả trái ngược nhau; đây cũng không phải biên dưới toán học của PnL.

| Order | Tín hiệu / bar giả | Exit đổi (gap gốc / thứ cấp) | Net R SYM / ASYM | Cả hai vòng SYM / ASYM | Payout standalone SYM / ASYM |
|---|---:|---:|---:|---:|---:|
| OLHC | 494 / 133 | 56 (56/0) | -19.94/-17.69 | 0/105 / 0/105 | $1023.31 / $1015.83 |
| OHLC | 494 / 133 | 56 (56/0) | -19.94/-17.69 | 0/105 / 0/105 | $1023.31 / $1015.83 |

## 2. Từng nhánh đóng góp gì, và tăng risk giúp được bao nhiêu?

Net R dưới đây là cộng đơn vị R của tín hiệu theo năm ra quyết định, không phải % tài khoản. Floating R-DD dùng sổ riêng mỗi sleeve ở risk cố định 150 USD, lot được làm tròn xuống; khác closed cumulative unit-R DD cũng có trong JSON.

| Nhánh | Asset / family / horizon / exit | ID đầy đủ |
|---|---|---|
| S1 | EURUSD / F5 / DAY / P0 | `EURUSD|F5:tf=H4:n=5:adx=25:buffer=0.1|DAY|P0` |
| S2 | XAUUSD / F3 / 48H / P0 | `XAUUSD|F3:compression=BB:n=60:quantile=0.1:multiple=1|48H|P0` |
| S3 | XAUUSD / F4 / 24H / P1 | `XAUUSD|F4:hour=15:impulse=1:timing=MONTH:multiple=1|24H|P1` |
| S4 | EURUSD / F3 / DAY / P1 | `EURUSD|F3:compression=NR:n=14:multiple=1|DAY|P1` |
| S5 | XAUUSD / F3 / 48H / P0 | `XAUUSD|F3:compression=NR:n=14:multiple=2|48H|P0` |

**SYM — mỗi ô: số tín hiệu / Net R.**

| Nhánh | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 YTD | Tổng R | Floating R-DD lớn nhất 2 order |
|---|---|---|---|---|---|---|---|---|---|---:|---:|
| S1 | 34/+14.00 | 25/-4.53 | 32/-2.50 | 27/+1.73 | 36/+1.80 | 40/+15.00 | 26/+12.57 | 27/+2.58 | 19/-3.64 | +37.00 | 12.99 |
| S2 | 3/-1.44 | 10/-2.74 | 13/+6.77 | 10/+1.28 | 12/-6.17 | 15/+14.34 | 17/+0.24 | 11/-3.99 | 12/+4.36 | +12.64 | 11.89 |
| S3 | 6/-3.26 | 12/+3.91 | 12/+9.70 | 14/-0.38 | 18/-5.12 | 21/+7.86 | 22/-7.30 | 13/-0.62 | 7/+9.69 | +14.48 | 13.45 |
| S4 | 21/+2.86 | 19/-5.04 | 14/+3.63 | 20/-3.33 | 18/+4.35 | 16/-0.28 | 23/-1.93 | 13/-1.32 | 17/-3.36 | -4.42 | 9.68 |
| S5 | 19/-2.41 | 20/-8.25 | 20/+3.37 | 14/-0.70 | 16/+3.59 | 15/-0.12 | 14/-1.19 | 14/+0.64 | 19/-0.56 | -5.63 | 16.76 |

**ASYM — mỗi ô: số tín hiệu / Net R.**

| Nhánh | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 YTD | Tổng R | Floating R-DD lớn nhất 2 order |
|---|---|---|---|---|---|---|---|---|---|---:|---:|
| S1 | 34/+14.00 | 25/-4.53 | 32/-2.50 | 27/+1.73 | 36/+1.80 | 40/+15.00 | 26/+12.57 | 27/+2.58 | 19/-3.64 | +37.00 | 12.99 |
| S2 | 3/-1.51 | 10/-2.66 | 13/+7.14 | 10/+1.38 | 12/-6.01 | 15/+15.06 | 17/+0.51 | 11/-3.96 | 12/+4.42 | +14.39 | 11.73 |
| S3 | 6/-3.28 | 12/+4.05 | 12/+9.73 | 14/-0.25 | 18/-4.85 | 21/+8.10 | 22/-6.97 | 13/-0.57 | 7/+9.70 | +15.64 | 12.45 |
| S4 | 21/+2.86 | 19/-5.04 | 14/+3.63 | 20/-3.33 | 18/+4.35 | 16/-0.28 | 23/-1.93 | 13/-1.32 | 17/-3.36 | -4.42 | 9.68 |
| S5 | 19/-2.02 | 20/-7.42 | 20/+3.85 | 14/-0.41 | 16/+4.02 | 15/+0.21 | 14/-0.89 | 14/+0.67 | 19/-0.51 | -2.51 | 15.44 |

S4+S5 cộng **-7.7147R SYM** vào 2024–2026: thêm lệnh nhưng làm tổng A từ +13,8926R xuống +6,1779R. Đây là lý do giữ A, không tiếp tục tìm weights/subset của B.

V14 xin risk 200 / 175 / 125 USD = 0,40% / 0,35% / 0,25%, có throttle 150 USD ở equity 48k và 90 USD ở 47k. Lot floor khiến số tiền tới SL thực thấp hơn ngân sách xin. V14 đã dùng đến **6,56362% static DD** và **0,910508% lỗ ngày** trong 105 starts; không phải mới dùng 3%. Không có breach lịch sử chưa chứng minh tăng risk là an toàn.

| Chính sách Development | Worst pass cả 2 / 72 | Median chậm nhất (tháng, chỉ cửa sổ pass) | Worst static % | Worst daily % | Eligible |
|---|---:|---:|---:|---:|---|
| V14 | 25 | 59.0 | 6.5636 | 0.9105 | True |
| D1 | 25 | 59.0 | 6.8500 | 0.9105 | True |
| D1.25 | 34 | 54.52 | 7.6983 | 1.1484 | True |
| D1.5 | 50 | 41.13 | 8.1310 | 1.3683 | True |
| D2 | 51 | 26.19 | 8.3683 | 1.8210 | False |
| D2.5 | 31 | 21.58 | 8.3924 | 2.1837 | False |
| D3 | 42 | 16.96 | 8.3997 | 2.6151 | False |

Chọn **D1.5** theo đúng thứ tự đăng ký: đạt target static 7,5–8,2%, rồi tối đa hóa số hoàn tất yếu nhất qua hai phí/hai order. Risk 300 / 262,50 / 187,50 USD (0,60% / 0,525% / 0,375%). Equity <=47.500 cap risk 150 USD; <=46.500 cap 75 USD; open-stop cap 1.000 USD, reserve có funding >45.800 USD, daily realized halt -1.000 USD. D1 cũng khác V14 vì controls đã đổi. Các mức D2 trở lên không được chọn dù chạy nhanh hơn.

Cushion là đúng một biến thể: chỉ Vòng 1, arm khi balance lãi >=1.500 USD; thêm min(20% lãi thực hiện, 250 USD), chỉ khi equity >50k; về balance <=50k thì disarm. Vòng 2/Funded không đổi. Cả throttle, cap và reserve vẫn áp dụng.

**Bốn cột so sánh được đặt thành bốn dòng cho mỗi phí/order:**

| Order / phí | Cột | P1 / 105 | Cả 2 / 105 | Median tháng | Standalone payout USD | Post-challenge payout USD chồng lấn | Daily % | Static % | Breach |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| OLHC / SYM | V14_ORIGINAL | 67 | 48 | 53.99 | 6131.27 | 42952.74 | 0.9105 | 6.5636 | 0 |
| OLHC / ASYM | V14_ORIGINAL | 69 | 56 | 55.37 | 6401.71 | 49226.94 | 0.8979 | 6.5524 | 0 |
| OLHC / SYM | V14_PRIMARY_BRIDGE | 67 | 48 | 53.99 | 6131.27 | 42952.74 | 0.9105 | 6.5636 | 0 |
| OLHC / ASYM | V14_PRIMARY_BRIDGE | 69 | 56 | 55.37 | 6401.71 | 49226.94 | 0.8979 | 6.5524 | 0 |
| OLHC / SYM | V15_CALIBRATED | 75 | 63 | 41.03 | 8834.15 | 150322.64 | 1.3683 | 8.1310 | 0 |
| OLHC / ASYM | V15_CALIBRATED | 75 | 63 | 38.10 | 9422.51 | 176940.20 | 1.3494 | 8.0459 | 0 |
| OLHC / SYM | V15_CUSHION | 78 | 66 | 34.85 | 8834.15 | 157249.14 | 2.3672 | 8.1310 | 0 |
| OLHC / ASYM | V15_CUSHION | 78 | 67 | 33.05 | 9422.51 | 196514.91 | 2.3659 | 8.0540 | 0 |
| OHLC / SYM | V14_ORIGINAL | 67 | 48 | 53.99 | 6131.27 | 42952.74 | 0.9105 | 6.5636 | 0 |
| OHLC / ASYM | V14_ORIGINAL | 69 | 56 | 55.37 | 6401.71 | 49226.94 | 0.8979 | 6.5524 | 0 |
| OHLC / SYM | V14_PRIMARY_BRIDGE | 67 | 48 | 53.99 | 6131.27 | 42952.74 | 0.9105 | 6.5636 | 0 |
| OHLC / ASYM | V14_PRIMARY_BRIDGE | 69 | 56 | 55.37 | 6401.71 | 49226.94 | 0.8979 | 6.5524 | 0 |
| OHLC / SYM | V15_CALIBRATED | 75 | 63 | 41.03 | 8834.15 | 150322.64 | 1.3683 | 8.1310 | 0 |
| OHLC / ASYM | V15_CALIBRATED | 75 | 63 | 38.10 | 9422.51 | 176940.20 | 1.3494 | 8.0459 | 0 |
| OHLC / SYM | V15_CUSHION | 78 | 66 | 34.85 | 8834.15 | 157249.14 | 2.3672 | 8.1310 | 0 |
| OHLC / ASYM | V15_CUSHION | 78 | 67 | 33.05 | 9422.51 | 196514.91 | 2.3659 | 8.0540 | 0 |

Payout post-challenge cộng các tài khoản giả định chồng lấn, **không thể cộng thành thu nhập**. 105 starts là cùng một lịch sử, không phải 105 lần thử độc lập. Median chỉ tính những cửa sổ hoàn tất; các cửa sổ chưa xong vẫn được giữ là censored, không force-close cuối mẫu. Riêng 33 starts từ tháng 01/2024 đến 09/2026, cả bốn cột vẫn **0/33 hoàn tất hai vòng** tính đến 13/10/2026; SYM V15 có 4/33 qua Vòng 1, cushion 6/33. Median tốt hơn chủ yếu phản ánh những starts cũ, không chứng minh tài khoản mới sẽ pass trong 35 tháng. Mọi số tiền risk thực theo phase/sleeve nằm trong JSON.

| Profile OLHC | Chặn cap (tổng các tài khoản chồng lấn) | Chặn reserve | Chặn do thu hoạch Funded |
|---|---:|---:|---:|
| V14_ORIGINAL | 0 | 0 | 0 |
| V15_CALIBRATED | 0 | 0 | 15 |
| V15_CUSHION | 370 | 0 | 7 |

Các ngưỡng trên là mô hình FTMO 2-Step đã khóa; swap và Ask là proxy, không phải lịch sử spec/bid-ask của tài khoản đích. Chưa có xác nhận lịch tin, khớp lệnh broker, owner handover, shadow/demo và chi phí challenge/retry.

## 3. Đóng sổ 47 cây trùng và dung lượng D/E

| Nhóm | Số targets | Cây không chồng nhau | Bytes không chồng nhau | Files không chồng nhau | Quyết định |
|---|---:|---:|---:|---:|---|
| HISTORICAL_CHART_LIBRARY_COPY | 2 | 2 | 11,875,972 | 442 | Nén, thử restore, xóa bản dư |
| INSTALLED_ENVIRONMENT_SUBTREE | 9 | 6 | 7,207,050 | 121 | Giữ package/RECORD toàn vẹn |
| UV_PACKAGE_ARCHIVE_SUBTREE | 36 | 25 | 96,365,877 | 1518 | Giữ package/RECORD toàn vẹn |

47 targets = **115,448,899 bytes / 2081 files** sau bỏ trùng subtree (cộng thô có chồng là 117,958,793 bytes). Hai cây `charting_library/bundles` giảm 11,875,972 bytes logic, archive mới 3,247,516 bytes; chênh lệch logic 8,628,456 bytes trước các receipts nghiên cứu mới. Không claim số bytes vật lý đã giải phóng.

45 subtree package nhỏ được KEEP có quyết định rõ, không còn trạng thái chưa xử lý. RECORD và từng Merkle manifest nằm trong private job. Xóa một phần package trong khi giữ dist-info sẽ làm sai môi trường; D và E khác volume nên không hardlink xuyên ổ. Không lặp lại đợt xóa bốn cây V14. Các locator cũ được giữ nguyên trong bằng chứng lịch sử; disposition mới chỉ tới archive và D canonical.

Bản đồ dung lượng là snapshot metadata khi các job đang chạy; các ledger được tạo sau snapshot không nằm trong số tổng này. Giới hạn chỉ hai project roots đã nêu, không phải toàn bộ ổ D/E.

| Root | Decimal GB | GiB | Files | Folders | Lỗi metadata |
|---|---:|---:|---:|---:|---:|
| D:\ANNAM\TradingWorkspace | 211.770 | 197.227 | 575567 | 75401 | 2 |
| E:\BACKUP-TRADINGWORKSPACE | 228.055 | 212.393 | 556940 | 37689 | 0 |

Các nhóm dung lượng lớn không chồng nhau:

| Root / nhóm | GB | Files |
|---|---:|---:|
| D / projects/vi-dubber | 138.575 | 82693 |
| D / projects/mt5-tradingview-backtester | 36.756 | 87074 |
| D / projects/trader | 14.738 | 45305 |
| D / .runtime/linux | 7.046 | 37 |
| D / planning/trader | 3.296 | 31748 |
| D / projects/integrations | 3.252 | 157181 |
| D / .runtime/strategy-references | 1.700 | 14681 |
| D / education/research | 1.158 | 6708 |
| E / workspace/projects | 105.384 | 140989 |
| E / ai-engine-jobs/challenge-discovery4-20261108 | 44.624 | 139683 |
| E / ai-foundation-20261023/target | 6.971 | 4117 |
| E / solo-system-20261115-04e2/cargo-target | 6.449 | 3261 |
| E / system-capabilities-20261103/isolated-owner-restore | 4.448 | 5663 |
| E / ai-foundation-20261023/backup | 4.307 | 5413 |
| E / ui-system-20261031/trade-merge-release | 4.288 | 4339 |
| E / ui-system-20261031/note-picker-release | 4.287 | 4322 |

## 4. Kiểm toán, hiệu năng và bàn giao

Oracle độc lập về phép tính đã đối soát **2656 đường giá** và **4052 sổ** trong V15; gồm cả full baseline được reuse trên cùng quote grid, mọi policy Development và full, strict stress và năm sleeve riêng. Đây là cùng implementer/feed, không phải người review hoặc nguồn giá độc lập. Auditor không import code tính tiền của producer.

**1126 tests PASS, 0 skip**; giữ **1110/1110 ID cũ**, thêm 16 kiểm thử signed bridge, Ask/extrema, nguồn thiếu, cushion arm/disarm/phase, lot floor số lẻ, shared path và đối soát sổ.

10 fresh-process liên tiếp giữ nguyên 78 smoke tests: suite median/max **0.586/0.609s**, wall median/max **0.745/0.777s**. 10/10 wall <0,85s: **True**; 10/10 wall <0,80s: **True**. Giữ mọi mẫu, không retry tìm streak đẹp hay bỏ test. Lượt trước tối ưu giữ nguyên trong `smoke-results.json`: max wall 0.891s, có một lượt vượt 0,85s. Profile chỉ ra filesystem import probes; runner bỏ đường dẫn import lặp và chỉ import ThreadPool/subprocess khi chạy parallel. Không đổi modules, test IDs hay assertions.

Luồng: nguồn V14 immutable → entry/SL/deadline tape cố định → kiểm gap và shared-path sensitivity → reuse engine V4/V6/costs → scalar Decimal audit → chọn sizing Dev → commit freeze → full historical evaluation. Không thêm alpha, TP hay exit grid.

Hậu kiểm kỹ thuật: reuse baseline chỉ sau financial tape parity và đối soát lại sổ; mô hình xác suất không được nâng thành chứng nhận giá; không phá package để báo thành tích cleanup. Điểm còn cần xử lý trước Challenge là bằng chứng đường giá/tin tức/broker và tốc độ kiếm R bền vững, không tiếp tục tăng risk ngoài budget đã thử.

PR #94 để review, **không merge**. Receipt 3 CI đúng HEAD và đối soát artifact test IDs được ghi sau push tại `ci-exact-head-reconciliation.json` trong private job; không sửa HEAD chỉ để tự tham chiếu hash CI trong chính commit đó.

JSON gọn: `BRIDGE-AND-VELOCITY-V15-RESULTS-20261115.json` (<1 MiB). Private job: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\bridge-certification-and-velocity-v15-20261115`. VI Dubber WIP và Trader pin giữ nguyên; không broker, không deploy, không tiền rút thực.

Nguồn đối chiếu quy tắc hiện hành: FTMO Trading Objectives (2-Step) https://ftmo.com/en/trading-objectives/ và overnight/Standard FAQ https://ftmo.com/en/faq/do-i-have-to-close-my-positions-overnight/ . Các nguồn này không xác nhận dữ liệu giá hoặc khả năng pass tương lai.
