# V17 — Trọng số, hạn mức và kiểm lại tốc độ Challenge

**Chưa có nâng cấp đủ điều kiện Challenge.** Không có sleeve bổ sung qua đủ cổng; giữ toàn bộ kết quả âm và chưa mở V18.

Ở phí SYM, V17 PRIMARY hoàn tất 68/105 cửa sổ, trung vị 42,95 tháng: nhanh hơn V16 (47,08) nhưng chậm hơn V15 (34,85). STRICT V17 chỉ 0/105; cả ba phiên bản đều 0/33 starts từ 2024. V17 giảm DD PRIMARY nhưng chưa giải quyết time-fit hoặc gap.

PR #95 đã merge `0fb47ae`, nhánh V16 đã xóa. V17 đăng ký `e3a390d`, khóa code/tier/selection `d1d1d3b` trước đo chính sách mới trên 2024–13/10/2026. Đây là giá đã exposed từ nghiên cứu cũ, không phải OOS nguyên vẹn.

## 1. Điểm nghẽn thật và chính sách đã khóa

V16 có 494 tín hiệu full-period, **0 lệnh qua đêm**, còn 32 đường giá bất định. Không có vị thế 48 giờ chiếm hạn mức. Trong Dev PRIMARY, mỗi cost/ordering có 36 lần từ chối cap trên các tài khoản chồng lấn, chỉ 3 tín hiệu riêng biệt; 0 overnight blocker và 0 bóp lot một phần do cap. STRICT: 15 lần/6 tín hiệu, 4.205 lần từ chối reserve. Không suy lợi nhuận tương lai của tín hiệu bị từ chối.

Tại 20:30 không thể biết đường giá đêm tới có đầy đủ hay không. Dùng tick/HTF của tương lai để cấp phép carry sẽ nhìn trước dữ liệu. V17 giữ daily-flat, không carry/re-entry. Khung 07:00–20:30 cũng không bảo đảm M1 liên tục.

Ba sổ sleeve riêng risk 150 USD được replay/audit trên Dev, lấy tỷ số annual Net R/floating R-DD xấu nhất của hai phí × hai ordering. Đây không phải CAGR Calmar.

| Sleeve | Tier | Worst annual R/DD |
|---|---|---|
| EURUSD\|F5:tf=H4:n=5:adx=25:buffer=0.1\|DAY\|P0 | 1.0 | 0.323232 |
| XAUUSD\|F3:compression=BB:n=60:quantile=0.1:multiple=1\|48H\|P0 | 0.6 | -0.114014 |
| XAUUSD\|F4:hour=15:impulse=1:timing=MONTH:multiple=1\|24H\|P1 | 0.6 | 0.289522 |

Tier nhân sau equity throttle của V15 factor 1,5+cushion, làm tròn xuống 0,001 USD. Không tăng cược hoặc chọn lại equal/tiered sau kết quả. Cap tổng 1.000 USD; swing ≤400, dành 600 intraday; intraday mượn phần swing chưa dùng. Phân giỏ theo deadline biết tại entry. Cả danh mục thực đều intraday nên cap swing chưa hoạt động; invariant hai giỏ được kiểm bằng fixture.

Guard mới yêu cầu projected all-stop equity sau phí cao hơn balance đầu ngày Prague trừ 1.200 USD (2,4% sổ 50k), đồng thời giữ reserve tổng 8,4%, phase risk, daily halt và harvester cũ. Guard entry không là lệnh thanh lý hay bảo đảm fill xuyên gap <2,5%.

## 2. Quét intraday và độ hoàn thiện đường giá

| Asset | Cells | Stage-0 fail | SL-active reject | Qualified |
|---|---|---|---|---|
| XAUUSD | 198 | 180 | 18 | 0 |
| EURUSD | 103 | 97 | 6 | 0 |
| US500 | 202 | 202 | 0 | 0 |

503 cells reuse budget V16, chỉ thêm hàng rào giờ entry ≥07:00; giữ recipes, cost, clone exclusions và hai cluster 2018–2020/2021–2023. Báo cả unconditional endpoint; Stage-0 gate kế thừa dùng admitted cohort. Không chọn horizon/cohort mới sau outcome. Mỗi endpoint được tính lại bằng Decimal; mọi SL-active path của cells qua Stage-0 được scalar audit hai ordering. Các lý do từng cell nằm trong private scan JSON.

**Selection rỗng.** Không dựng adapter multiasset suy đoán. GBP/AUD tiếp tục data-incomplete; không biến tick rời rạc thành M1. Danh mục A vẫn giữ gap labels của V16; không bỏ trade sau khi thấy thiếu giá và không dùng synthetic stress để chứng nhận nguồn. Không đạt mục tiêu hội tụ PRIMARY/STRICT.

## 3. V15–V17: cùng 105 starts, hai phí và hai ordering

V15 PRIMARY reuse CUSHION có hash. **V15 STRICT cũ dùng risk V14**, nên lượt này replay cùng shared stress tape tại factor 1,5+cushion rồi audit để so đúng policy. V16 hai chế độ reuse ledgers có hash; V17 là sổ mới. SYM/ASYM là hai proxy swap đã đăng ký; V16/V17 intraday không có rollover nên không nhận lợi thế từ đổi proxy swap.

| Order/phí | Bản | Mode | P1/105 | Hai vòng/105 | Recent/33 | Median tháng | Daily % | Static % | Breach |
|---|---|---|---|---|---|---|---|---|---|
| OLHC/SYM | V15 | PRIMARY | 78 | 66 | 0 | 34.85 | 2.3672 | 8.131 | 0 |
| OLHC/ASYM | V15 | PRIMARY | 78 | 67 | 0 | 33.05 | 2.3659 | 8.054 | 0 |
| OLHC/SYM | V15 | STRICT | 16 | 0 | 0 | None | 2.5182 | 8.3995 | 0 |
| OLHC/ASYM | V15 | STRICT | 19 | 2 | 0 | 12.56 | 2.3271 | 8.399 | 0 |
| OLHC/SYM | V16 | PRIMARY | 81 | 71 | 0 | 47.08 | 1.963 | 6.3825 | 0 |
| OLHC/ASYM | V16 | PRIMARY | 81 | 71 | 0 | 47.08 | 1.963 | 6.3825 | 0 |
| OLHC/SYM | V16 | STRICT | 18 | 1 | 0 | 18.95 | 1.9628 | 8.3997 | 0 |
| OLHC/ASYM | V16 | STRICT | 18 | 1 | 0 | 18.95 | 1.9628 | 8.3997 | 0 |
| OLHC/SYM | V17 | PRIMARY | 74 | 68 | 0 | 42.95 | 1.6434 | 5.3626 | 0 |
| OLHC/ASYM | V17 | PRIMARY | 74 | 68 | 0 | 42.95 | 1.6434 | 5.3626 | 0 |
| OLHC/SYM | V17 | STRICT | 14 | 0 | 0 | None | 1.8295 | 8.3988 | 0 |
| OLHC/ASYM | V17 | STRICT | 14 | 0 | 0 | None | 1.8295 | 8.3988 | 0 |
| OHLC/SYM | V15 | PRIMARY | 78 | 66 | 0 | 34.85 | 2.3672 | 8.131 | 0 |
| OHLC/ASYM | V15 | PRIMARY | 78 | 67 | 0 | 33.05 | 2.3659 | 8.054 | 0 |
| OHLC/SYM | V15 | STRICT | 16 | 0 | 0 | None | 2.5182 | 8.3995 | 0 |
| OHLC/ASYM | V15 | STRICT | 19 | 2 | 0 | 12.56 | 2.3271 | 8.399 | 0 |
| OHLC/SYM | V16 | PRIMARY | 81 | 71 | 0 | 47.08 | 1.963 | 6.3825 | 0 |
| OHLC/ASYM | V16 | PRIMARY | 81 | 71 | 0 | 47.08 | 1.963 | 6.3825 | 0 |
| OHLC/SYM | V16 | STRICT | 18 | 1 | 0 | 18.95 | 1.9628 | 8.3997 | 0 |
| OHLC/ASYM | V16 | STRICT | 18 | 1 | 0 | 18.95 | 1.9628 | 8.3997 | 0 |
| OHLC/SYM | V17 | PRIMARY | 74 | 68 | 0 | 42.95 | 1.6434 | 5.3626 | 0 |
| OHLC/ASYM | V17 | PRIMARY | 74 | 68 | 0 | 42.95 | 1.6434 | 5.3626 | 0 |
| OHLC/SYM | V17 | STRICT | 14 | 0 | 0 | None | 1.8295 | 8.3988 | 0 |
| OHLC/ASYM | V17 | STRICT | 14 | 0 | 0 | None | 1.8295 | 8.3988 | 0 |

Median chỉ trên cửa sổ hoàn tất; chưa hoàn tất vẫn censored. Starts mỗi tháng chồng lấn, không là xác suất pass độc lập; gần cuối mẫu ít thời gian theo dõi hơn. JSON có P1/P2 censoring, recent median/DD/payouts và toàn bộ ledger bindings.

| Order/phí | Bản/mode | Post-challenge count | USD (chồng lấn) | Standalone count | Standalone USD |
|---|---|---|---|---|---|
| OLHC/SYM | V15/PRIMARY | 836 | 157249.14 | 42 | 8834.15 |
| OLHC/ASYM | V15/PRIMARY | 923 | 196514.91 | 42 | 9422.51 |
| OLHC/SYM | V15/STRICT | 0 | 0 | 10 | 1552.23 |
| OLHC/ASYM | V15/STRICT | 2 | 42.5 | 10 | 1540.95 |
| OLHC/SYM | V16/PRIMARY | 608 | 68232.22 | 40 | 6457.11 |
| OLHC/ASYM | V16/PRIMARY | 608 | 68232.22 | 40 | 6457.11 |
| OLHC/SYM | V16/STRICT | 2 | 132.61 | 11 | 1824.95 |
| OLHC/ASYM | V16/STRICT | 2 | 132.61 | 11 | 1824.95 |
| OLHC/SYM | V17/PRIMARY | 590 | 77456.6 | 35 | 6314.27 |
| OLHC/ASYM | V17/PRIMARY | 590 | 77456.6 | 35 | 6314.27 |
| OLHC/SYM | V17/STRICT | 0 | 0 | 11 | 2098.35 |
| OLHC/ASYM | V17/STRICT | 0 | 0 | 11 | 2098.35 |
| OHLC/SYM | V15/PRIMARY | 836 | 157249.14 | 42 | 8834.15 |
| OHLC/ASYM | V15/PRIMARY | 923 | 196514.91 | 42 | 9422.51 |
| OHLC/SYM | V15/STRICT | 0 | 0 | 10 | 1552.23 |
| OHLC/ASYM | V15/STRICT | 2 | 42.5 | 10 | 1540.95 |
| OHLC/SYM | V16/PRIMARY | 608 | 68232.22 | 40 | 6457.11 |
| OHLC/ASYM | V16/PRIMARY | 608 | 68232.22 | 40 | 6457.11 |
| OHLC/SYM | V16/STRICT | 2 | 132.61 | 11 | 1824.95 |
| OHLC/ASYM | V16/STRICT | 2 | 132.61 | 11 | 1824.95 |
| OHLC/SYM | V17/PRIMARY | 590 | 77456.6 | 35 | 6314.27 |
| OHLC/ASYM | V17/PRIMARY | 590 | 77456.6 | 35 | 6314.27 |
| OHLC/SYM | V17/STRICT | 0 | 0 | 11 | 2098.35 |
| OHLC/ASYM | V17/STRICT | 0 | 0 | 11 | 2098.35 |

Payout là số mô phỏng trước phí mua/retry challenge, vận hành và thuế; tổng nhiều tài khoản chồng lấn không phải thu nhập. Chưa có payout hay lệnh broker thật.

## 4. Kiểm toán, hiệu năng, lưu trữ và quyết định

Đủ 20 receipts mới về đường giá/sổ tài khoản (Dev/Full, hai ordering, hai mode và V15 CUSHION strict). Oracle scalar/Decimal kiểm entry/SL/deadline, cash, phí, MTM, tier/cap/daily floor và payout; test có negative contract và replay 4-loss từ chối lệnh thứ tư. US500 oracle bổ sung contract=1, grid 0,001 và giờ nghỉ NY; hồi quy Gold/FX giữ nguyên. Receipt parent-code-binding đầu lượt giữ nguyên phiên bản cũ; oracle mở rộng có pin mới ở freeze V17. Độc lập implementation, **cùng tác giả và feed**, không giả reviewer độc lập.

Full suite **1148 PASS, 0 skip**, giữ đủ 1138 ID V16. Wall **28.226 → 21.144s**, giảm **25.1%**. Baseline lịch sử, thêm 10 tests; không gọi hai workload hoàn toàn giống nhau. Bốn base worker cân bằng bằng profile thay hai; shared immutable bytes ở capture fixture, mỗi test vẫn có file/state riêng, có kiểm không sửa baseline. Không mock bỏ process/recovery assertions.

Chưa đo peak process-tree RAM hay speedup riêng fixture; không quy toàn bộ cải thiện cho chia sẻ bộ nhớ. Process isolation và CPU trade-off được ghi rõ.

Smoke đúng 10 fresh processes ×78 tests: median/max **0.717/0.733s**; 10/10 <0,80s: **True**. Không retry lấy streak đẹp.

| Job E | Files trước nén | Bytes trước nén |
|---|---|---|
| bridge-certification-and-velocity-v15-20261115 | 223 | 1491024075 |
| gap-immune-and-multiasset-v16-20261116 | 174 | 550708827 |
| adaptive-velocity-v17-20261116 | 116 | 614144865 |

Nén 64 test/console logs V15/V16 đã đóng: 1,181,834 → 243,001 bytes, giảm logic trước receipts 938,833 bytes. Extract/SHA mọi member trước khi xóa bản log nóng; đường cũ có hydration locator. Reuse retention inventory V16; census chỉ các roots đã nêu và D campaign files, bỏ qua reparse/junction. Không scan lại toàn ổ, không xóa dữ liệu/matrix/path/ledger/freeze/package/failed attempt. Chưa đo physical freed; không claim zero bloat tuyệt đối.

Luồng chính: A paths V16 giữ nguyên → Dev sleeve books → tier freeze → account guard V17 → PRIMARY/shared-gap stress replay → independent oracle → comparison. Điều này giữ được nguồn gốc từng con số mà không tạo strategy mới sau outcome.

**Khuyến nghị: không dùng V17 để mua Challenge, không tăng risk để cứu time-fit.** Trọng số và hạn mức không tạo thêm lợi thế tín hiệu hay lấp đường giá thiếu. Giữ baseline V15 và toàn bộ V16/V17 làm evidence; không promote cho đến khi có lý do/nguồn dữ liệu mới qua budget riêng. V18 chưa được thực thi.

Hậu kiểm: phân biệt occurrences/unique signals; không đổ lỗi concurrency cho overnight khi thực tế daily-flat; không dùng future completeness làm carry gate; so đúng risk profile; lưu fail và kiểm ID thay vì chỉ số test count. Các skill hiện hành đã bao phủ các guard này; không thêm skill hoặc instruction trùng lặp.

Đã thử truy cập official FTMO FAQ ngày 16/11/2026 nhưng web tool không trả nội dung đối soát được, HTTP fallback lỗi SSL; receipt `official-terms-check.json`. Chưa xác minh lại terms hiện hành. Giữ proxy lịch/news đã đăng ký, không coi chúng là chứng nhận đầy đủ lịch news/terms/spec execution lịch sử hay 100% tuân thủ FTMO.

Evidence `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\adaptive-velocity-v17-20261116`; JSON <1MiB. PR #96 giữ mở; receipt `ci-exact-head-reconciliation-v2.json` được ghi sau push/check/download artifact, không sửa HEAD chỉ để nhét SHA CI vào cùng commit. VI WIP/Trader pin giữ nguyên; không broker, deploy, provider download, Astra hay memory update.
