---
title: "Alpha #2 Unified Engine, Khắc Phục 5 Lỗi Shadow Runner & Ghép Danh Mục PORT_7E + Alpha #2 (Dev <= 2024-12-31)"
date: 2026-11-27
status: verified_dev_study
lane: o2-alpha2-lab
scope: dev_le_2024_12_31_only
evidence_stage: DEV_BACKTEST_LE_2024_12_31_DAILY_APPROX_NOT_HOLDOUT_NOT_LIVE
holdout_rows_analysed: 0
order_send_count: 0
holdout_lock_sha256: f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486
---

# Alpha #2 Unified Engine, Sửa 5 Lỗi Shadow & Ghép Danh Mục `PORT_7E + Alpha #2` (Dev `<= 2024-12-31`)

- **Kết luận 1 dòng:** Đã hợp nhất hoàn toàn lõi tín hiệu Backtest và Shadow thành một bộ mã nguồn thuần `numpy + pandas` duy nhất (`unified_engine.py` + `funding_carry_v2.py`), sửa dứt điểm `5/5` lỗi đối soát trên `crypto_shadow_runner.py`, và chứng minh trên dữ liệu Dev `<= 2024-12-31` rằng ghép **`PORT_7E` (FTMO 10K, đủ phanh Vàng `-3,5%` / Đỏ `-6,0%`)** với **Alpha #2 (CEX Own-Book 10K)** gần như trực giao tuyệt đối (**`|r| = 0,0130–0,0182`**) và kéo tỷ lệ tháng đói tiền về từ **`67,80%` (`66,21%` cả vòng đời)** xuống **`27,08%` (Carry 2x)** hoặc **`34,35%` (Composite 50/50)** — đạt mục tiêu **`< 35%`** với chuỗi tháng đói trung vị giảm từ **`12` tháng xuống `2–3` tháng**.
- **Khóa an toàn bất biến:** `0 VND` · `OrderSend = 0` · `MT5_PROCS = 0` · **`holdout_rows_analysed = 0`** (`Holdout 2025+` niêm phong `SHA f0a6b43cb205535b...`, mọi bộ nạp `.runtime/crypto-spot-cache/` và `.runtime/crypto-1h-cache/` đều cắt cứng `< 2025-01-01` trước khi tính toán và chống vô hiệu hóa dưới `python -O`).
- **Cấp độ bằng chứng:** **`DEV_BACKTEST <= 2024-12-31`** (`DAILY_APPROX` cho vòng đời mô phỏng; dữ liệu quá khứ đã qua nhiều vòng nghiên cứu Dev, **KHÔNG phải Holdout mù `2025+`, KHÔNG phải giao dịch tiền thật**). Quy đổi tiền Việt theo tỷ giá **`1 USD = 25.765,94 VND`** (phí thẻ VN `+2,5%`, phí rút `1,5%`, chiết khấu NPV `6,0%/năm`).

---

## 1. Bộ Chỉ Số Cân Bằng Luật 15 & Định Vị Thang `Xấu -> Top 1% Thực Tế`

### 1.1. So Sánh Trực Diện Lõi `PORT_7E` vs Ứng Viên Alpha #2 vs Ghép Đôi (Dev `<= 2024-12-31`, `1x` Phí)

Các số liệu dưới đây trích nguyên văn từ bộ chạy kiểm định [portfolio_7e_plus_alpha2_study.py](../../tooling/ai-engines/experiments/portfolio_7e_plus_alpha2_study.py) (`N = 5.000` đường bootstrap khối ghép ngày, `seed = 20261126`, `holdout_rows_analysed = 0`):

- **Cơ sở hiện hữu `PORT_7E` (`C10_NEWS_ON`, FTMO `10K` / `100K`, `2018–2024`):**
  - **Lõi 100K (Funded `1,0x`, `2.882` lệnh):** Tỷ lệ thắng **`48,61%`**, ăn/thua `RR` **`1,272x`**, kỳ vọng **`+0,0486R/lệnh`**, `Profit Factor` **`1,203`**, lãi năm **`+7,42%`** (`+191,1 tr VND/năm` trên `100K`), `Max DD` **`8,62%`** (`222,0 tr VND`), chuỗi thua dài nhất **`12` lệnh**, `Calmar` **`0,861`**, `Sharpe` **`1,234`**.
  - **Vòng đời `1` vé `FTMO 10K` (phí thẻ BF `70,42 USD` ~ `1,81 tr VND`):** `EV NPV 24T` **`+15,16 tr VND`** (`EV / Phí = +8,35x`), xác suất hòa/lỗ sau 24T **`41,62%`**, tỷ lệ tháng Funded đói payout **`66,21%`** (`66,29%` trên đoạn `2020–2024`; **`67,80%`** nếu xét riêng tài khoản Funded `C10_NEWS_ON` đủ phanh Vàng/Đỏ), chuỗi đói trung vị **`8` tháng** (vòng đời) / **`12` tháng** (riêng nhánh Funded `2020–2024`).
  - **Tỷ lệ `Đậu / Rớt / Chờ` `FTMO 10K` (tổng luôn `= 100,00%`):** `3T` `14,26 / 2,10 / 83,64%` · `6T` `32,06 / 2,84 / 65,10%` · `12T` `46,84 / 4,12 / 49,04%` · `24T` **`62,04 / 5,38 / 32,58%`** · cháy Funded `12T` **`0,03%`** (`Wilson 95% <= 0,16%`).
- **Ứng viên Alpha #2 Thực Chiến Số 1 — `A2_CARRY_BTC_ETH_2X` (Delta-Neutral BTC+ETH, đệm `2,0x`, `2020–2024`):**
  - **Thông số lõi (`1x = 23 bps` 1 chiều + basis MTM + phí sốc thoát):** Lãi năm **`+7,34%`** (`+18,9 tr VND/năm` trên `10K` vốn riêng), `Winrate ngày` **`81,50%`**, `RR ngày` **`1,422x`**, `EV/ngày` **`+1,94 bps`**, `Profit Factor` **`6,266`**, `Max DD` **`1,01%`** (`2,6 tr VND` trên `10K`), chuỗi lỗ dài nhất **`5` ngày**, `Calmar` **`7,291`**, `Sharpe` **`8,138`** (nhấn mạnh: Sharpe cao vì biến động nền cực thấp `0,87%/năm`, KHÔNG phải máy in tiền rủi ro bằng 0!).
  - **Sức bền chi phí & thanh lý:** Ở `2x` phí (`46 bps` + `2x` sốc thoát) vẫn lãi **`+6,48%/năm`** (`Sharpe 6,486`, `Calmar 3,071`); **ngưỡng gãy chi phí `9,89x`**; **`0` thanh lý Isolated / `0` Cross** (`max jump 30,90%`, `0` ngày cảnh báo).
  - **Độc lập thống kê vs `PORT_7E`:** Tương quan ngày **`r = +0,0182` (`|r| = 0,0182`)**; trên `5%` ngày lỗ nặng nhất của `PORT_7E`, Carry vẫn kiếm trung bình **`+3,79 bps/ngày`**!
- **Ứng viên Alpha #2 Tăng Trưởng — `A2_COMPOSITE_SPOT50_CARRY50` (`50%` Spot 4H F4 + `50%` Carry BTC+ETH `2x`, `2020–2024`):**
  - **Thông số lõi (`1x` phí):** Lãi năm **`+11,29%`** (`+29,1 tr VND/năm` trên `10K` vốn riêng), `Winrate ngày` **`61,26%`**, `RR ngày` **`1,028x`**, `EV/ngày` **`+2,96 bps`**, `Profit Factor` **`1,625`**, `Max DD` **`3,98%`** (`10,3 tr VND` trên `10K`), chuỗi lỗ **`7` ngày**, `Calmar` **`2,840`**, `Sharpe` **`2,505`**.
  - **Sức bền chi phí & độc lập:** Ở `2x` phí vẫn lãi **`+10,31%/năm`** (`Sharpe 2,297`, `Calmar 2,165`); **ngưỡng gãy chi phí `13,24x`**; **`|r|` vs `PORT_7E` = `0,0182`** (`+0,23 bps/ngày` trên `5%` ngày xấu nhất của `PORT_7E`).
- **Tổ Hợp Thực Chiến Hai Tài Khoản (`FTMO Funded 10K PORT_7E C10_NEWS_ON` + `CEX Own-Book 10K Alpha #2`, ngưỡng rút gộp `>= 50 USD` khớp `simulator.py`, HWM CEX):**
  - **Với `Carry BTC+ETH 2x` (`10K` CEX):** Tháng đói tiền giảm từ **`67,80%` -> `27,08%`** (**`-40,72` đ%**, vượt mục tiêu `< 35%`), chuỗi đói trung vị **`12` -> `2` tháng** (`p95 = 4` tháng), tổng tiền mặt ròng về 24T trung bình **`+3.169,9 USD` (`+81,68 tr VND`)** / trung vị **`+3.107,1 USD` (`+80,06 tr VND`)**.
  - **Với `Composite 50/50` (`10K` CEX):** Tháng đói tiền giảm từ **`67,80%` -> `34,35%`** (**`-33,45` đ%**, đạt mục tiêu `< 35%`), chuỗi đói trung vị **`12` -> `3` tháng** (`p95 = 9` tháng), tổng tiền mặt ròng về 24T trung bình **`+4.061,1 USD` (`+104,64 tr VND`)** / trung vị **`+4.005,0 USD` (`+103,19 tr VND`)**.
  - **Phân bố `Đậu / Rớt / Chờ` ở kịch bản đối chứng gộp luồng lợi suất (`COMBO_7E_PLUS_COMPOSITE_1P0X`, `1` vé `10K`, tổng `= 100,00%`):** `3T` `22,50 / 3,38 / 74,12%` · `6T` `46,72 / 4,44 / 48,84%` · `12T` `69,42 / 5,88 / 24,70%` · `24T` **`85,78 / 7,06 / 7,16%`** · `EV / Phí = +26,39x` · cháy Funded `12T` **`0,00%`** (`Wilson 95% <= 0,08%`) *(lưu ý rõ ở Mục 4: kịch bản gộp 1 tài khoản chỉ mang tính lý thuyết kiểm chứng độ êm, không chạy Carry trong tài khoản FTMO)*.

### 1.2. Định Vị Dọc Theo Luật 15 (`Xấu -> Đủ dùng -> Tốt -> Top 1% Thực Tế`)

- 🔴 **Xấu:** `EV <= 0`, `PF < 1,05`, `Max DD > 10%`, `Calmar < 0,5`, `Sharpe < 0,6`, cháy Funded `> 5%`, hoặc tháng đói tiền `> 60%` kéo dài cả năm.
- 🟡 **Đủ dùng — VỊ TRÍ HIỆN TẠI CỦA `PORT_7E` ĐƠN LẺ (`Calmar 0,861`, `PF 1,203`, `Max DD 8,62%`, tháng đói `66,2–67,8%`):** Có biên dương thật nhưng vẫn mỏng trước trượt giá `>= 1,50x` và chịu 2/3 số tháng Funded không có payout về tay.
- 🟢 **Tốt — VỊ TRÍ HIỆN TẠI CỦA `PORT_7E + ALPHA #2` TRÊN DEV (`|r| = 0,018`, `PBO = 0,0000`, `CPCV 15/15`, `Composite Calmar 2,36–2,84`, tháng đói Hai Tài Khoản `27,1%–34,4% < 35%`):** Cải thiện rõ rệt độ đều dòng tiền và khả năng chống chi phí (`BE = 9,9x–16,3x`) trên dữ liệu Dev `<= 2024-12-31`, **NHƯNG tuyệt đối chưa được gọi là Top 1% thực tế** vì mới là backtest Dev và chưa qua kiểm chứng tiền thật `>= 12` tháng.
- 🏆 **Top 1% thực tế (Mục tiêu cần vươn tới):** `PF 1,50–2,00+`, `Max DD 4%–7%`, `Calmar > 2,0`, `Sharpe 2,0–3,0` **trên tiền thật `>= 12` tháng**, dòng tiền về đều mỗi `2–3` tháng, rủi ro sàn CEX giữ trong trần `<= 25%` tổng tài sản vốn riêng.

**Ngưỡng gãy / Điểm chết thực tế cần nhớ:**
1. **Ngưỡng gãy chi phí:** `PORT_7E` gãy tại `2,31x` trượt giá (khóa dừng ở `> 1,75x`); `A2_CARRY_BTC_ETH_2X` gãy tại `9,89x` (`~227 bps` 1 chiều); `A2_SPOT_4H_F4_EMA` gãy tại `16,26x` (`~244 bps` 1 chiều).
2. **Ngưỡng gãy cấu trúc của Alpha #2 (nguy hiểm hơn phí):** (a) **Nén funding dài hạn** (như giai đoạn ETF/Ethena 2024+, lãi Carry BTC+ETH có thể tụt từ `+7,3%` trung bình 2020–2024 về `+2,5%–3,5%/năm`, làm tăng tỷ lệ tháng không đủ ngưỡng rút `50 USD` nếu vốn CEX nhỏ `< 10K`); (b) **Rủi ro lưu ký sàn tập trung (CEX)** (đóng băng rút tiền/sự cố kiểu FTX — buộc phải giới hạn tổng CEX trong `NCO_CexCap25`); (c) **Bắt buộc Cross-Margin** nếu dùng nhánh vệ tinh altcoin (`A2_CARRY_TOP5_HYST_2X` từng gặp cú nhảy giá `82,77%` trong ngày).

**Khoảng cách cụ thể tới `Top 1% thực tế`:**
1. **Khoảng cách bằng chứng:** Hiện toàn bộ số liệu là `DEV_BACKTEST <= 2024-12-31` (`holdout_rows_analysed = 0`). Phải gom đủ nhật ký Shadow thực tế sau khi sửa `5` lỗi `crypto_shadow_runner.py` (`>= 30` ngày liên tục khớp sổ L2 TCA, `0` lỗi đối soát) và chỉ mở Holdout `2025+` khi có phê duyệt độc lập.
2. **Khoảng cách vốn triển khai Hai Tài Khoản:** Để `DUAL_10K_FTMO + 10K_CEX` kéo tháng đói xuống `27,1%–34,4%`, cần tích lũy đủ quỹ vốn riêng CEX (`10K USD ~ 258 tr VND`) từ lợi nhuận Prop theo cơ chế 3 giỏ, không đi vay và không dồn quá `25%` tài sản vào CEX.
3. **Khoảng cách thực thi lệnh thụ động (Maker):** Với nhánh vệ tinh đa coin Carry, cần chứng minh live fill Maker `<= 5 bps/chân` để giữ lợi nhuận khi thị trường nén funding.

---

## 2. Kiến Trúc Unified Engine & Khắc Phục `5/5` Lỗi Shadow Runner

Để chấm dứt vĩnh viễn tình trạng Backtest dùng một công thức còn Shadow live chạy một bản sao bị lệch, toàn bộ lõi tính tín hiệu và kế toán được hợp nhất vào `projects/quant-trading/src/quant_lab/` (chỉ phụ thuộc `numpy + pandas`, `0` import từ thư mục gốc/duckdb/pyarrow):

- **Lõi hợp nhất Spot ([unified_engine.py](../../projects/quant-trading/src/quant_lab/unified_engine.py)):** Cung cấp `UnifiedSpotEngine`, `F4EmaConfig`, `causal_ema_1d`, `causal_rolling_vol_1d`, `apply_deadband_step`, `compute_f4_ema_step`, `update_shadow_spot_accounting`, và hàm bảo vệ Holdout chống `python -O` là `enforce_pre_holdout_dates()` (dùng `if ...: raise ValueError(...)`, tuyệt đối không dùng `assert`).
- **Lõi hợp nhất Funding Carry v2 ([funding_carry_v2.py](../../projects/quant-trading/src/quant_lab/funding_carry_v2.py)):** Cung cấp `FundingCarryConfig`, `carry_btc_eth_cons_weights`, `carry_top_k_hysteresis_weights`, `carry_v2_blend_weights`, `compute_carry_btc_eth_live_step`, và `run_funding_carry_backtest` (mô phỏng đầy đủ đệm ký quỹ `2,0x`, basis MTM, phí cặp + trượt basis + phí sốc thoát lệnh và kiểm toán thanh lý Mark-Price).
- **Đối soát Backtest vs Shadow từng cây nến (bit-for-bit):** Bộ kiểm thử [test_unified_engine_and_shadow_parity.py](../../projects/quant-trading/tests/test_unified_engine_and_shadow_parity.py) và [test_portfolio_7e_plus_alpha2.py](../../tooling/ai-engines/tests/test_portfolio_7e_plus_alpha2.py) đã xác minh độ sai lệch trọng số giữa `UnifiedSpotEngine.build_f4_weights()` và vòng lặp từng bước `compute_f4_ema_step()` là **`< 1e-12`** trên toàn bộ chuỗi nến.

### Bảng Kiểm Toán `5/5` Lỗi Đã Sửa Trong [crypto_shadow_runner.py](../../tooling/ai-engines/quant_factory/crypto_shadow_runner.py)

| # | Lỗi đã phát hiện trên Shadow Runner cũ | Hậu quả thực tế trước khi sửa | Cách sửa dứt điểm (đã nối thẳng vào `unified_engine.py`) | Kiểm thử chứng minh |
|---|---|---|---|---|
| **1** | `_causal_ema_1d` không kiểm `valid_streak >= span`, không reset khi gặp `NaN` / giá `<= 0` | Phát tín hiệu giả sớm hơn `causal_universe.py` khi coin mới lên sàn hoặc dính nến thiếu dữ liệu | Ủy quyền trực tiếp cho `quant_lab.unified_engine.causal_ema_1d` (`valid_streak >= span` khớp 100% `causal_universe.py`) | `test_shadow_bug1_ema_warmup_and_nan_reset_parity` |
| **2** | Thiếu cơ chế `deadband = 0,015` khi tính trọng số live | Xoay vòng nhiễu từng chút mỗi nến 4H, làm phồng turnover và chi phí trượt giá so với backtest | Truyền `prev_weights=s2_prev_w` vào `compute_f4_4h_ema_live_weights` -> gọi `apply_deadband_step(..., deadband=0.015)` | `test_shadow_bug2_deadband_and_backtest_step_parity` |
| **3** | `L293` tải `limit = 325` nến 4H cho `EMA(300)` | Sau `324` nến đóng, trọng số điểm mồi đầu chuỗi vẫn còn `(299/301)^323 = 11,6%`, gây lệch `EMA(300)` nghiêm trọng | Nâng `SHADOW_4H_KLINE_LIMIT = 1000` (`>= 600`), giảm sai số mồi xuống còn `0,13%` (không tốn thêm API request); chặn fail-closed nếu `< 600` | `test_ema_warmup_gap_reset_and_kline_limit_drift_reduction` + `test_shadow_bugs_3_4_5` |
| **4** | `L355–367` không khóa theo mốc đóng nến `last_4h_close_ms` | Daemon chạy mỗi `5` phút trừ trùng phí `s2_turnover` lặp đi lặp lại trong cùng một cây nến 4H | Bổ sung khóa idempotency theo `s2_last_4h_close_ms` trong `update_shadow_spot_accounting`: cùng nến 4H giữ nguyên trọng số khóa, `turnover = 0`, `cost = 0` | `test_shadow_bugs_3_4_5_end_to_end_mocked_snapshot` (Poll 2 cùng nến 4H) |
| **5** | `L284/349–353` chỉ tải `mid` cho `top15 \| {BTC, ETH}` | Coin đang giữ vị thế nhưng rớt khỏi Top-15 bị nhận `p1 = 0,0`, làm mất sạch lợi nhuận/lỗ MTM phiên thoát lệnh | Đọc `s2_prev_w` trước khi dựng danh sách theo dõi: `build_shadow_watch_symbols(top15, s2_prev_w)` = `top15 \| {BTC, ETH} \| set(s2_prev_w.keys())` | `test_shadow_bugs_3_4_5_end_to_end_mocked_snapshot` (Poll 3 `DROPPEDUSDT +20%`) |

---

## 3. Kết Quả Kiểm Định Toàn Bộ `M = 8` Ứng Viên Alpha #2 (Dev `<= 2024-12-31`)

Toàn bộ `8` ứng viên được chạy từ cùng kho dữ liệu Dev đã cắt cứng `<= 2024-12-31` (`.runtime/crypto-spot-cache/4h`, `.runtime/crypto-1h-cache/1h`, `.runtime/crypto-spot-cache/funding+1d`, **`holdout_rows_analysed = 0`**).

- **Chống học vẹt toàn danh mục (trên đoạn giao chung `2021-01-01..2024-12-31`, `1.461` ngày):**
  - **CSCV `PBO` (`S = 16` lát cắt, `12.870` tổ hợp):** **`PBO = 0,0000`** (`is_overfit = False`, xác suất ứng viên thắng IS bị Sharpe OOS `<= 0` là **`0,0000`**).
  - **CPCV (`6` nhóm, chọn `2` nhóm test = `15` đường OOS, `purge = 5` ngày, `embargo = 5` ngày):** **`100,0%` (`15/15`)** đường OOS của ứng viên chọn từ IS đạt Sharpe dương (trung vị **`10,705`**, tối thiểu **`4,030`**).
- **Ghi chú minh bạch về `DSR` thực nghiệm (`deflated_sharpe_ratio_empirical`):** Vì 2 họ chiến lược có độ biến động nền khác nhau ~10 lần (Spot Trend `Sharpe 1,19–1,65` vs Delta-Neutral Carry `Sharpe 6,55–8,14`), nếu trộn chung phương sai thử nghiệm 2 họ sẽ làm phồng ngưỡng cắt `E[max SR] ~ 4,6`. Do đó bảng dưới báo **DSR thực nghiệm đúng trong từng họ** (`SPOT_TREND_4` và `FUNDING_CARRY_3`) kèm đối chiếu `DSR proxy (M=8)`.

| Ứng viên Alpha #2 (`<= 2024-12-31`) | Nguồn Cache | `1x` CAGR | `1x` Sharpe | `1x` MaxDD | `1x` Calmar | `1x` PF | `2x` CAGR / SR | Ngưỡng gãy | `DSR` (Họ / Proxy) | `CPCV` Med OOS SR (`%+`) | `\|r\|` vs `PORT_7E` | `A2` trên `5%` ngày xấu `7E` |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| `A2_SPOT_4H_F4_EMA` | `spot-cache/4h` | +14,53% | 1,650 | 9,85% | 1,475 | 1,403 | +13,49% / 1,541 | 16,26x | 0,9999 / 0,9951 | 1,773 (80,0%) | **0,0130** | -0,22 bps |
| `A2_SPOT_4H_F3_DON` | `spot-cache/4h` | +11,72% | 1,421 | 9,93% | 1,181 | 1,306 | +10,92% / 1,331 | 16,84x | 0,9989 / 0,9778 | 1,375 (86,7%) | **0,0019** | -2,21 bps |
| `A2_SPOT_1H_EMA_96_480` | `1h-cache/1h` | +8,84% | 1,187 | 9,62% | 0,919 | 1,279 | +7,54% / 1,024 | 8,28x | 0,9793 / 0,8194 | 1,145 (86,7%) | **0,0884** | -12,26 bps |
| `A2_SPOT_1H_DON_168_84` | `1h-cache/1h` | +8,33% | 1,492 | 5,13% | 1,625 | 1,403 | +7,15% / 1,291 | 8,45x | 0,9961 / 0,9370 | 1,620 (86,7%) | **0,0863** | -3,82 bps |
| **`A2_CARRY_BTC_ETH_2X`** | `funding+1d` | **+7,34%** | **8,138** | **1,01%** | **7,291** | **6,266** | **+6,48% / 6,486** | **9,89x** | **1,0000 / 1,0000** | **10,705 (100%)** | **0,0182** | **+3,79 bps** |
| `A2_CARRY_TOP5_HYST_2X` | `funding+1d` | +7,32% | 6,551 | 0,98% | 7,446 | 5,339 | +5,04% / 4,178 | 4,30x | 1,0000 / 1,0000 | 6,011 (100%) | **0,0119** | +3,92 bps |
| `A2_CARRY_V2_BLEND_70_30` | `funding+1d` | +7,33% | 8,030 | 0,99% | 7,429 | 7,175 | +6,05% / 6,260 | 6,90x | 1,0000 / 1,0000 | 10,427 (100%) | **0,0164** | +3,83 bps |
| **`A2_COMPOSITE_SPOT50_CARRY50`** | `4h+funding` | **+11,29%** | **2,505** | **3,98%** | **2,840** | **1,625** | **+10,31% / 2,297** | **13,24x** | **1,0000 / 1,0000** | **2,330 (86,7%)** | **0,0182** | **+0,23 bps** |

**Nhận xét lựa chọn thực chiến (nhất quán với Lab #1 & Lab #9):**
1. Các bản 1H (`A2_SPOT_1H_EMA_96_480`, `A2_SPOT_1H_DON_168_84`) xoay vòng cao hơn (`7,3–8,0x/năm`), tương quan cao hơn (`|r| ~ 0,086–0,088`) và bị trùng pha với Spot 4H — không nên thêm trùng lặp.
2. Trong họ Carry, `A2_CARRY_V2_BLEND_70_30` nhỉnh hơn về `2x Calmar` (`4,009` vs `3,071`), nhưng có `3` ngày cảnh báo nhảy giá Mark altcoin (`82,77%`), nên **ưu tiên triển khai trước `A2_CARRY_BTC_ETH_2X` (`0` cảnh báo, `max jump 30,90%`, `TO = 3,30x/năm`)**, kết hợp cùng **`A2_SPOT_4H_F4_EMA`** tạo thành cặp **`A2_COMPOSITE_SPOT50_CARRY50`** (`Max DD 3,98%`, `Calmar 2,84`).

---

## 4. Giảm Tỷ Lệ Tháng Đói Payout (`60–66%` -> Mục Tiêu `< 35%`): Hai Kiến Trúc Đối Chiếu

### 4.1. Kiến Trúc Thực Thi Thật — Hai Tài Khoản Độc Lập (`FTMO Funded 10K` + `CEX Own-Book Alpha #2`, `2020–2024`, `5.000` Đường MC Ghép Ngày)

Đây là mô hình **100% đúng luật thực tế**: `PORT_7E` chạy trên tài khoản FTMO `10K` (`C10_NEWS_ON`, đủ phanh Vàng `-3,5%` / Đỏ `-6,0%`, `80%` split, chu kỳ `10` phiên, xét điều kiện đạt ngưỡng rút theo **số gộp `>= 50 USD`** khớp `simulator.py:365-397` và ghi nhận tiền ròng sau phí rút `1,5%`), còn Alpha #2 chạy trên tài khoản vốn riêng Binance (đệm `2,0x`, **chỉ tính có tiền mặt rút tháng khi vượt đỉnh High-Water-Mark `>= 50 USD`**, không bao giờ tự rút vào vốn gốc). Một tháng (`21` phiên) chỉ bị tính là **đói tiền** khi **FTMO không có đợt rút hợp lệ nào và tổng rút gộp cả 2 nguồn `< 50 USD`**.

| Cấu hình Hai Tài Khoản (`DAILY_APPROX`, `2020–2024`, phanh Vàng/Đỏ, HWM `>= 50 USD`) | Tháng đói tiền (`FTMO` đơn lẻ) | Tháng đói tiền (Ghép Hai Tài Khoản) | Giảm tuyệt đối | Chuỗi đói `p50` / `p95` (tháng) | Tiền mặt ròng 24T TB (`USD` / `tr VND`) | Tiền mặt ròng 24T TV (`USD` / `tr VND`) | Đạt `< 35%`? |
|---|---:|---:|---:|---:|---:|---:|---|
| **`FTMO 10K` + `CEX 10K Carry BTC+ETH 2x`** | 67,80% | **27,08%** | **-40,72 đ%** | **2 / 4** *(từ 12)* | +3.169,9 / **+81,68 tr** | +3.107,1 / **+80,06 tr** | **ĐẠT** |
| **`FTMO 10K` + `CEX 10K Composite 50/50`** | 67,80% | **34,35%** | **-33,45 đ%** | **3 / 9** *(từ 12)* | +4.061,1 / **+104,64 tr** | +4.005,0 / **+103,19 tr** | **ĐẠT** |
| **`FTMO 10K` + `CEX 20K Composite 50/50`** | 67,80% | **30,44%** | **-37,36 đ%** | **3 / 8** *(từ 12)* | +6.570,4 / **+169,29 tr** | +6.492,5 / **+167,29 tr** | **ĐẠT** |
| `FTMO 10K` + `CEX 10K Spot 4H F4` đơn lẻ | 67,80% | 39,01% | -28,79 đ% | 4 / 11 *(từ 12)* | +4.998,6 / +128,79 tr | +4.954,5 / +127,66 tr | Chưa (`>35%`) |

### 4.2. Kịch Bản Đối Chứng Lý Thuyết — Gộp Luồng Lợi Suất Kiểu Xếp Chồng Notional (`FTMO 10K C10_NEWS_ON`, Ghép DD Bảo Thủ `1,5x`)

Bảng dưới kiểm tra hiệu ứng đa dạng hóa ở mức luồng tiền gộp nếu một tài khoản duy nhất nhận cả 2 nguồn lợi suất (phạt bảo thủ `+1,5x` lỗ ngày Alpha #2 cộng thẳng lên intraday DD của `PORT_7E`). **Hai cảnh báo trung thực bắt buộc theo Luật 13:**
1. **Xếp chồng notional (gross overlay `1,75x–2,75x`), KHÔNG phải chia vốn 50/50 không đòn bẩy:** Mọi dòng `COMBO` đều cộng thêm `+0,75x` / `+1,0x` Alpha #2 **chồng lên trên `1,0x PORT_7E`** (`1,75x` tới `2,75x` tổng quy mô danh nghĩa so với `1,0x` gốc), nên lãi năm và `EV / Phí` tăng mạnh nhờ vừa có đa dạng hóa vừa tăng tổng phơi nhiễm rủi ro; nếu so trên cùng vốn thực phải dùng bảng **Hai Tài Khoản tách vốn `10K + 10K`** ở Mục 4.1.
2. **Không chạy được trực tiếp trên 1 tài khoản FTMO:** FTMO không cho chạy Binance Perp Carry trong tài khoản MT5, nên bảng này chỉ dùng làm đối chứng lý thuyết; cấu hình triển khai thực chiến duy nhất là Mục 4.1.

| Cấu hình Gộp Luồng (`2020–2024`, `1` vé `10K`, phí thẻ `70,42 USD`) | Lãi năm / `Sharpe` / `Calmar` | `Max DD` | Tháng Funded đói payout (`p50` chuỗi) | `24T` Đậu / Rớt / Chờ (`100%`) | `EV NPV 24T` TB / TV (`tr VND`) | `EV / Phí` | Cháy Funded `12T` |
|---|---:|---:|---:|---|---:|---:|---:|
| `BASE_PORT_7E_ONLY` *(Chuẩn gốc `1,0x`)* | +8,77% / 1,23 / 1,15 | 7,64% | **66,29%** (`8`T) | 59,02 / 7,56 / 33,42% | +14,61 / +5,88 | +8,05x | 0,03% (`<=0,17%`) |
| `COMBO_7E + Spot 4H (0,75x)` *(Tổng `1,75x`)* | +22,81% / 2,09 / 1,85 | 12,31% | **53,04%** (`6`T) | 83,50 / 7,42 / 9,08% | +43,57 / +41,94 | +24,01x | 0,31% (`<=0,53%`) |
| `COMBO_7E + Carry 2x (1,0x)` *(Tổng `2,00x`)* | +17,90% / 2,32 / 2,40 | 7,45% | **45,52%** (`5`T) | 81,00 / 7,76 / 11,24% | +37,00 / +37,32 | +20,39x | 0,00% (`<=0,09%`) |
| `COMBO_7E + Composite 50/50 (1,0x)` *(Tổng `2,00x`)* | +22,85% / 2,42 / 2,36 | 9,68% | **45,62%** (`5`T) | 85,78 / 7,06 / 7,16% | +47,87 / +48,13 | +26,39x | 0,00% (`<=0,08%`) |
| `COMBO_7E + Spot (0,75x) + Carry (1,0x)` *(Tổng `2,75x`)* | +33,10% / 2,80 / 3,01 | 11,00% | **39,31%** (`4`T) | 89,90 / 6,98 / 3,12% | +72,72 / +74,56 | +40,08x | 0,02% (`<=0,12%`) |

**Bài học kiến trúc cực kỳ quan trọng:** Gộp chung 1 tài khoản (dù đã xếp chồng notional `1,75x–2,75x`) vẫn chỉ kéo tháng đói xuống `39,31%–45,62%` vì tháng lỗ của nhánh này nuốt lãi của nhánh kia trước khi đạt ngưỡng rút. Ngược lại, **tách Hai Tài Khoản độc lập (`FTMO Funded PORT_7E` + `CEX Own-Book Alpha #2`)** vừa đúng luật hãng, vừa giải phóng dòng tiền thực xuống **`27,08%–34,35%` tháng đói** (`< 35%`), cắt chuỗi chờ trung vị từ `12` tháng còn **`2–3` tháng** mà không cần tăng đòn bẩy FTMO!

---

## 5. Khả Năng Tái Lập & Bước Tiếp Theo (Chỉ Đọc, `0 VND`)

- **Tái lập bộ lõi thuần `numpy + pandas`:** Chạy `uv run --locked ruff check src tests` và `uv run --locked pytest -n 2` trong `projects/quant-trading` (xác minh [unified_engine.py](../../projects/quant-trading/src/quant_lab/unified_engine.py), [funding_carry_v2.py](../../projects/quant-trading/src/quant_lab/funding_carry_v2.py), và [test_unified_engine_and_shadow_parity.py](../../projects/quant-trading/tests/test_unified_engine_and_shadow_parity.py)).
- **Tái lập nghiên cứu ghép danh mục & kiểm thử `5` lỗi Shadow:** Chạy [portfolio_7e_plus_alpha2_study.py](../../tooling/ai-engines/experiments/portfolio_7e_plus_alpha2_study.py) và [test_portfolio_7e_plus_alpha2.py](../../tooling/ai-engines/tests/test_portfolio_7e_plus_alpha2.py) bằng Python `quant-audit-v24` (cả chế độ thường và `python -O`).
- **Quyết định vận hành hiện tại:** Giữ **`0 VND`**, giữ **`Holdout 2025+ SEALED`**, chưa mở live execution cho Alpha #2 cho đến khi hoàn thành `>= 30` ngày chạy Shadow read-only trên bản `crypto_shadow_runner.py` đã sửa `5/5` lỗi và đạt đủ chuẩn `PaperSoakReceipt`.
