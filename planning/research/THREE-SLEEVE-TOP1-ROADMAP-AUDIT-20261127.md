---
title: Kiểm Toán Lộ Trình Danh Mục 3 Nhánh Lệch Pha & Khóa Pre-Registration Holdout v2 (Dev <= 2024-12-31)
date: 2026-11-27
lane: o3-macro-prereg
status: verified_dev_study
scope: dev_pre_holdout_only
dev_cutoff_day: "2025-01-01"
dev_max_date_observed: "2024-12-31"
holdout_rows_analysed: 0
post_cutoff_cache_rows_excluded: 112811
order_send_count: 0
evidence_stage: DEV_BACKTEST_2018_2024_STRICT_PRE_HOLDOUT_NOT_BLIND_2025
holdout_lock_sha256: f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486
tapes_binding_sha256: 9ec0e5d581f78c95f544ac8f0dfaec16b413439126f341dbaf4a227496183855
---

# Kiểm Toán Lộ Trình Danh Mục 3 Nhánh Lệch Pha & Niêm Phong Holdout v2 (`Dev <= 2024-12-31`)

**Kết luận 1 dòng:** Trên dữ liệu quá khứ đã khóa chặt `<= 2024-12-31` (`holdout_rows_analysed = 0`, loại sạch `112.811` dòng `2025–2026` ngay lúc đọc file), ghép **3 nhánh gần như trực giao** (`|r| <= 0,08` với `PORT_7E`, tương quan đuôi xấu nhất `<= +0,11`) gồm **Prop Core `PORT_7E` (`40%`) + Crypto Spot & Funding Carry (`20%`, khóa cứng sàn tập trung `CEX <= 25%`) + Macro ETF `0` swap (`40%`)** nâng độ êm lợi nhuận `Sharpe` từ **`1,09` lên `1,91`** (`1,78` ở phí `2x`), kéo tụt sâu nhất `Max DD` từ **`6,54%` xuống `3,91%`**, đưa `Calmar` từ **`1,05` lên `2,09`**, và giảm tỷ lệ tháng đói (`<= 0%`) từ **`41,67%` xuống `28,33%–31,67%`** — đặc biệt trong giai đoạn khó `2023–2024` khi `PORT_7E` đơn lẻ tụt xuống `Sharpe 0,43`, bộ 3 nhánh cố định `40/20/40` vẫn giữ vững **`Sharpe 1,40` (`Calmar 1,70`)**. Tuy nhiên, toàn bộ kết quả mới là **backtest quá khứ Dev (`<= 2024`)**, chưa phải tiền thật (`0 VND`), nên **chưa đạt `Top 1% thực tế`** và phải đi đúng bậc thang vốn trung thực của [TOP1-SOLO-QUANT-MASTER-PLAN.md](../TOP1-SOLO-QUANT-MASTER-PLAN.md) §3.2.

- **Khóa an toàn bất biến:** `0 VND` đã chi · `OrderSend = 0` · `MT5_PROCS = 0` · `holdout_rows_analysed = 0` · khóa `NATIVE_FTMO_HOLDOUT_LOCK.json` bất biến (`SHA f0a6b43cb205535b...`) · mã tái lập tại [three_sleeve_top1_roadmap_study.py](../../tooling/ai-engines/experiments/three_sleeve_top1_roadmap_study.py) và công cụ niêm phong `holdout_v2_prospective` tại [preregister_holdout_v2.py](../../tooling/ai-engines/quant_factory/preregister_holdout_v2.py).
- **Cấp độ bằng chứng & tỷ giá:** **Mô phỏng quá khứ trên dữ liệu Dev `2018-01-02..2024-12-31`** (cửa sổ 3 nhánh chồng lấn `2020-01-02..2024-12-31`, `1.304` ngày làm việc Mon–Fri, lãi cuối tuần Crypto ghép cộng dồn vào thứ Hai; `Cluster B` đã từng được xem ở các đợt trước — **KHÔNG gọi là Holdout mù `2025+`**). Quy đổi theo tỷ giá SSOT [fx_rates.json](../../tooling/ai-engines/configs/ssot/fx_rates.json): **`1 USD = 25.765,94 VND`**.

---

## 1. Bộ Chỉ Số Cân Bằng Toàn Diện & Thang Định Vị Luật 15 (`Xấu -> Top 1% Thực Tế`)

### 1.1. So Sánh Nhánh Đơn Lẻ vs Danh Mục Ghép (`2020-01-02..2024-12-31`, `60` Tháng, `CEX <= 25%`)

*Ghi chú minh bạch: Tỷ lệ thắng (`Winrate`), tỷ lệ ăn/thua (`RR`) và hệ số sinh lời (`PF`) bên dưới tính theo ngày giao dịch có phát sinh PnL (`daily`) và theo tháng (`monthly`) trên cùng lưới ngày làm việc để so ngang công bằng giữa 3 nhánh khác nhịp giao dịch. Thông số lệnh chi tiết và tỷ lệ `Đậu / Rớt / Chờ = 100%` của 1 vé thi quỹ `FTMO 10K` được giữ nguyên từ đối chiếu [C10-POST-SSOT-LOOKAHEAD-RECONCILIATION-20261127.md](C10-POST-SSOT-LOOKAHEAD-RECONCILIATION-20261127.md) (băng giá `frozen_9e_tapes_v2`, `10.000` đường MC).*

| Cấu hình danh mục (`Dev 2020–2024`, phí nền `1x`, `swap ETF/Prop = 0`) | Tỷ trọng (`S1/Spot/Carry/ETF`) | `CEX%` | Lãi năm (`CAGR`) | `Max DD` | `Sharpe` | `Calmar` | `WR / RR` (ngày) | `PF` (ngày / tháng) | Tháng đói `<= 0%` (chuỗi dài nhất) | `Dev OOS 2023–2024` (`Sharpe / Calmar`) |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|
| **`S1_PORT_7E_ONLY`** *(Prop lõi `1,0x`, `SYMCAP 1%`, Tin đỏ BẬT)* | `100 / 0 / 0 / 0` | `0,0%` | `+6,88%` | `6,54%` | `1,09` | `1,05` | `45,1% / 1,54x` | `1,27 / 2,53` | **`41,67%`** (`4` tháng) | `0,43 / 0,38` |
| **`S2_CRYPTO_SPOT`** *(`F1_TSMOM_D1_L60`, Top-15 nhân quả, `15 bps`)* | `0 / 100 / 0 / 0` | `100%` | `+8,74%` | `9,84%` | `1,19` | `0,89` | `51,8% / 1,21x` | `1,30 / 2,44` | `51,67%` (`7` tháng) | — |
| **`S3A_FUND_CARRY`** *(`TOP5_HYST`, đệm `2x`, `23 bps` + basis, `0` liq)* | `0 / 0 / 100 / 0` | `100%` | `+7,57%` | `0,91%` | `5,30`* | `8,34`* | `69,2% / 2,00x` | `4,49* / 27,37*` | `21,67%` (`4` tháng) | — |
| **`S3_MACRO_L7_TOP2`** *(Macro Quad + MM17 Var, `0` swap, `5 bps`)* | `0 / 0 / 0 / 100` | `0,0%` | `+9,14%` | `12,25%` | `1,12` | `0,75` | `56,1% / 0,94x` | `1,21 / 2,24` | `38,33%` (`3` tháng) | — |
| **`S3_MACRO_S3B_RP`** *(12-ETF Risk-Parity + SMA200, `0` swap, `5 bps`)* | `0 / 0 / 0 / 100` | `0,0%` | `+4,85%` | `7,64%` | `0,78` | `0,63` | `54,5% / 0,96x` | `1,15 / 1,97` | `40,00%` (`3` tháng) | — |
| **`OWNBOOK_ONLY` (Vốn tự có thuần, 0 đếm trùng Prop)** | `0 / 12,5 / 12,5 / 75` | `25,0%` | **`+8,94%`** | `9,98%` | `1,38` | `0,90` | `56,0% / 0,99x` | `1,26 / 2,53` | `36,67%` (`3` tháng) | **`1,36 / 2,07`** |
| **`3-SLEEVE FIXED 40/20/40 (L7_TOP2)` — Đề xuất đơn giản** | `40 / 10 / 10 / 40` | `20,0%` | **`+8,16%`** | **`3,91%`** | **`1,91`** | **`2,09`** | `56,7% / 1,06x` | **`1,39 / 3,68`** | **`31,67%`** (`3` tháng) | **`1,40 / 1,70`** |
| **`3-SLEEVE FIXED 40/20/40 (S3B_RP)` — Ít tháng đói nhất** | `40 / 10 / 10 / 40` | `20,0%` | `+6,42%` | **`3,78%`** | `1,72` | `1,70` | `54,5% / 1,14x` | `1,36 / 3,81` | **`28,33%`** (`3` tháng) | `1,20 / 1,18` |
| **`3-SLEEVE ERC_CEXCAP25 (L7_TOP2)`** *(fit `2020–2022`)* | `45 / 6,1 / 18,9 / 30` | `25,0%` | `+7,91%` | **`3,27%`** | `2,08` | `2,42` | `55,5% / 1,15x` | `1,44 / 4,22` | `35,00%` (`3` tháng) | `1,30 / 1,44` |
| **`3-SLEEVE NCO_CEXCAP25 (L7_TOP2)`** *(fit `2020–2022`)* | `45 / 2,9 / 22,2 / 30` | `25,0%` | `+7,87%` | **`3,27%`** | `2,09` | `2,41` | `55,4% / 1,16x` | `1,45 / 4,36` | `35,00%` (`3` tháng) | `1,26 / 1,35` |

*(\*) Cảnh báo trung thực cho `S3A_FUND_CARRY`: `Sharpe 5,30` và `PF 4,49` xuất phát từ bản chất ăn lãi suất funding độ biến động rất thấp (`Vol 1,38%/năm`), nhưng ẩn chứa rủi ro đuôi đối tác sàn tập trung (FTX/đóng băng rút tiền) và bị xói mòn nhanh khi phí tăng gấp đôi (`46 bps` -> `CAGR` tụt `+7,83% -> +4,79%`, `Calmar 8,64 -> 1,67`, tháng đói nhảy lên `48,33%`). Vì vậy **cấm** nhìn Sharpe đẹp để dồn tỷ trọng — khóa cứng tổng `Spot + Carry <= 25%`.*

- **Đối chứng 2 nhánh dài hạn `2018–2024` (`1.826` ngày làm việc, `84` tháng, `0% CEX` — áp dụng cho bậc `10k–25k USD`):**
  - `S1_PORT_7E_1X` đơn lẻ: `CAGR +6,77%`, `Max DD 6,54%`, `Sharpe 1,10`, `Calmar 1,04`, tháng đói `40,48%` (`34/84` tháng).
  - `50% S1 + 50% L7_TOP2`: `CAGR +7,24%`, **`Max DD 4,61%`**, **`Sharpe 1,52`**, **`Calmar 1,57`**, `PF ngày 1,30`, tháng đói `40,48%` (chuỗi đói giảm `4 -> 3` tháng).
  - `50% S1 + 50% S3B_RP`: `CAGR +5,86%`, **`Max DD 4,34%`**, **`Sharpe 1,40`**, **`Calmar 1,35`**, `PF ngày 1,29`, **tháng đói tụt xuống `29,76%`** (`25/84` tháng, thắng `70,24%` số tháng!).
- **Tóm tắt thi quỹ 1 vé không thử lại của Nhánh 1 (`FTMO 2-Step Standard 10K`, `C10_NEWS_ON`, `1,00x`, phí BF thẻ VN `70,42 USD` ~ `1,81 tr VND`):**
  - `Winrate / RR / EV lệnh`: `48,61%` / `1,272x` / `+0,0486R` (`PF = 1,203`, `2.882` lệnh, `Max DD 1,0x = 8,62%` trên `100K`, `Calmar 0,86`, `Sharpe 1,23`).
  - **Tỷ lệ `Đậu / Rớt / Chờ` (tổng luôn `100,00%`):** `3T`: `14,09% / 2,40% / 83,51%` · `6T`: `32,00% / 3,23% / 64,77%` · `12T`: `46,65% / 4,27% / 49,08%` · `24T`: **`61,89% / 5,60% / 32,51%`**.
  - **`EV NPV 24T` / `EV / 1 đồng phí`:** Trung bình **`+580,82 USD`** (**`+14,97 tr VND`**, `EV/Phí = +8,25x`) · Trung vị **`+293,17 USD`** (`+7,55 tr VND`) · Xác suất lỗ ròng `P(<=0) = 42,05%` · Cháy Funded `12T = 0,01%` (mô phỏng) · Tháng Funded đói payout **`66,45%`** · Chờ lần rút đầu trung vị `287` ngày (có điều kiện) / `538` ngày (mọi vé).
- **Quy đổi tiền thật minh họa cho Vốn Tự Có `OWNBOOK_ONLY` (`75% ETF L7_TOP2 + 25% Crypto`, `1x`, quá khứ Dev `2020–2024`):**
  - Mức `25.000 USD` (`644,1 tr VND`): lãi trung bình quá khứ `~2.235 USD/năm` (**`~57,6 tr VND/năm`**), tụt sâu nhất `~2.495 USD` (`~64,3 tr VND`).
  - Mức `50.000 USD` (`1,29 tỷ VND`): lãi trung bình quá khứ `~4.470 USD/năm` (**`~115,2 tr VND/năm`**), tụt sâu nhất `~4.990 USD` (`~128,6 tr VND`).
- **Ngưỡng gãy / điểm chết (Break-Even & Stress):**
  - Nhánh 1 `PORT_7E`: hòa vốn kỳ vọng ở ma sát **`2,31x`**, cắt cứng dừng mua vé mới ở **`> 1,75x`** (vì tại `1,50x`, trung vị 1 vé `10K` đã âm `-1,81 tr VND`).
  - Danh mục 3 nhánh `40/20/40 (L7_TOP2)` khi **nhân đôi toàn bộ chi phí Own-Book (`2x` = Spot `30 bps`, Carry `46 bps`, ETF `10 bps`)**: vẫn giữ **`CAGR +7,56%`, `Sharpe 1,78`, `Max DD 3,98%`, `Calmar 1,90`** trên `2020–2024` và **`Sharpe 1,24`, `Calmar 1,37`** trên `Dev OOS 2023–2024` (chỉ tụt `-0,60 đ%/năm` và `-0,13` Sharpe).

### 1.2. Thang Định Vị Dọc Luật 15 (`Xấu -> Đủ dùng -> Tốt -> Top 1% Thực Tế`)

- 🔴 **Xấu:** `EV/lệnh <= 0R`, `PF < 1,05`, `Max DD > 10%`, `Calmar < 0,5`, `Sharpe < 0,6`, thi quỹ `EV/Phí <= 0x` hoặc cháy Funded `> 5%`, hoặc dồn `> 25%` tài sản lên CEX.
- 🟡 **Đủ dùng — VỊ TRÍ HIỆN TẠI CỦA TỪNG NHÁNH ĐƠN LẺ (`PORT_7E` `EV +0,049R`, `PF 1,20`, `Calmar 0,86–1,05`, tháng đói `41,7%–66,5%`; `L7_TOP2` `Calmar 0,63–0,75`, `DD 12,25%`; `Crypto Spot` `Calmar 0,89`, tháng đói `51,7%`):** Mỗi nhánh chạy một mình đều có điểm yếu rõ rệt (tháng đói kéo dài hoặc pha chững `2023–2024`).
- 🟢 **Tốt — VỊ TRÍ HIỆN TẠI CỦA MÔ HÌNH GHÉP 3 NHÁNH `40/20/40` TRÊN QUÁ KHỨ DEV (`Sharpe 1,91`, `Calmar 2,09`, `Max DD 3,91%`, `PF ngày 1,39 / tháng 3,68`, tháng đói `28,3%–31,7%`, `Dev OOS 2023–2024 Sharpe 1,40`):** Đạt tiêu chuẩn tốt trên dữ liệu quá khứ `<= 2024-12-31`, **NHƯNG KHÔNG ĐƯỢC GỌI LÀ `Top 1% thực tế`** vì mới là backtest và hiện có **`0` tháng tiền thật**.
- 🏆 **Top 1% thực tế (Mục tiêu cần chứng minh):** `Sharpe 2,0–3,0`, `Calmar > 2,0`, `Max DD 4%–7%`, `PF >= 1,50`, tháng đói `< 30%` **đo trên tiền thật đã rút `>= 12` tháng liên tục** từ `2–3` nguồn lợi nhuận độc lập, kèm kiểm toán GIPS-Lite và `0` vi phạm kỷ luật.

**Khoảng cách trung thực tới `Top 1% thực tế` (4 khoảng trống còn thiếu):**
1. **Khoảng trống bằng chứng thực địa (`0` tháng tiền thật):** Toàn bộ bảng trên mới dừng ở Dev `<= 2024-12-31`; cần vượt trọn `Mốc 0` (Demo + thư xác nhận EA từ quỹ), `Mốc 1` (`>= 2` payout thực nhận + hoàn gốc `100%`), và kiểm chứng `1` lần duy nhất trên `holdout_v2_prospective (>= 2026-12-01, >= 90 ngày)`.
2. **Khoảng trống vốn triển khai (`0 USD` Own-Book hiện tại):** Lợi ích của bộ 3 nhánh chỉ kích hoạt thật khi vốn tự có tích lũy vượt mốc **`10.000 USD`** (mở ETF) và **`25.000 USD`** (mở thêm Crypto `CEX <= 25%`); trước mốc đó, ép mở sẽ bị phí tối thiểu ăn mòn.
3. **Khác biệt giữa danh mục cộng tỷ trọng `40/20/40` và thực tế dòng tiền Prop vs Own-Book:** Trong thực chiến, Nhánh 1 chạy bằng *vốn danh nghĩa của quỹ* (phải vượt 2 vòng thi và chịu ngưỡng rút), còn Nhánh 2 & 3 chạy bằng *tiền mặt tự có* (lãi kép trực tiếp không đòn bẩy). Do đó báo cáo tách riêng dòng **`OWNBOOK_ONLY` (`Sharpe 1,38`, `CAGR +8,94%`, `DD 9,98%`)** để không gây ảo giác gộp sai mẫu số vốn.
4. **Rủi ro đối tác CEX & chế độ lãi suất:** Nhánh `Funding Carry` phụ thuộc thanh khoản Binance/Bybit và chu kỳ phí dương; cần duy trì giới hạn cứng `CEX <= 25%` và tách sàn khi vốn vượt `50k USD`.

---

## 2. Ma Trận Tương Quan Cặp & Khả Năng Chống Sập Đồng Thời (`2020–2024`)

Dữ liệu trên toàn bộ `1.304` ngày làm việc Mon–Fri (`2020-01-02..2024-12-31`, `holdout_rows_analysed = 0`) xác nhận 3 nhánh lệch pha thực sự, **kể cả trong `5%` ngày lỗ nặng nhất của `PORT_7E` (`66` ngày xấu nhất)**:

| Nhánh so sánh | `S1_PORT_7E` | `S2_CRYPTO_SPOT` | `S3A_FUND_CARRY` | `S3_L7_TOP2_ETF` | Tương quan đuôi `Worst-5%` ngày xấu nhất của `S1` |
|---|---:|---:|---:|---:|---:|
| **`S1_PORT_7E` (Prop Core)** | `+1,0000` | `+0,0039` | `-0,0181` | `-0,0753` | `+1,0000` *(tham chiếu `66` ngày)* |
| **`S2_CRYPTO_SPOT` (`F1_TSMOM`)** | `+0,0039` | `+1,0000` | `+0,0775` | `+0,1922` | **`+0,0113`** *(không sập cùng `S1`)* |
| **`S3A_FUND_CARRY` (`TOP5_HYST`)** | `-0,0181` | `+0,0775` | `+1,0000` | `+0,0466` | **`+0,1130`** *(rất thấp)* |
| **`S3_L7_TOP2_ETF` (`0` swap)** | `-0,0753` | `+0,1922` | `+0,0466` | `+1,0000` | **`+0,0523`** *(phòng thủ tốt)* |

- Khi gộp thành đúng 3 cột (`S1_PORT_7E` · `S2_CRYPTO_BLEND 50/50` · `S3_MACRO_L7_TOP2`): `r(S1, S2) = +0,0005`, `r(S1, S3) = -0,0753`, `r(S2, S3) = +0,1949`; tương quan đuôi với `S1` chỉ là `+0,0306` (`S2`) và `+0,0523` (`S3`).
- Nếu thay `L7_TOP2` bằng `S3B_RISK_PARITY_TREND_GUARD`: `r(S1, S3B) = -0,0521` (7 năm `2018–2024`: `-0,0569`), `r(S2, S3B) = +0,1797`, tương quan đuôi `+0,2126`.
- **Bài học chống học vẹt trọng số (`Fixed 40/20/40` thắng `ERC` & `NCO` trên `2023–2024`):** Khi huấn luyện `ERC` và `NCO` trên `2020–2022`, bộ tối ưu hiệp phương sai dồn `18,9%–22,2%` vào `S3A_FUND_CARRY` (vì vol cực thấp) và cắt `S2_CRYPTO_SPOT` xuống `2,9%–6,1%`. Sang `Dev OOS 2023–2024`, bản **trọng số cố định không tối ưu `40/20/40` (`Sharpe 1,40`, `Calmar 1,70`, tháng đói `37,5%`)** vượt trội cả `ERC` (`1,30 / 1,44`, tháng đói `45,8%`) lẫn `NCO` (`1,26 / 1,35`, tháng đói `45,8%`). -> **Khóa lựa chọn thiết kế: ưu tiên quy tắc phân bổ cố định đơn giản `40/20/40` (và `75/25` cho Own-Book thuần), không tối ưu hóa rườm rà.**

---

## 3. Lộ Trình Ngưỡng Vốn Trung Thực & Kiểm Toán Phí Lô Nguyên IBKR (`Dev 2018–2024`)

Kiểm toán khớp lệnh trực tiếp theo giá cổ phiếu ETF thực tế trên giai đoạn `2018-01-02..2024-12-31` (`holdout_rows_analysed = 0`, biểu phí IBKR US Tiered `0,0035 USD/cp`, tối thiểu `0,35 USD/lệnh`, trần `1%` + `2,5 bps` spread một chiều) chứng minh bằng số học các ngưỡng vốn trong [TOP1-SOLO-QUANT-MASTER-PLAN.md](../TOP1-SOLO-QUANT-MASTER-PLAN.md) §3.2:

| Bậc vốn tự có (`USD` / `VND`) | Nhánh Own-Book được phép mở | Trần `CEX` | Phí thực IBKR trên `L7_TOP2` (`Integer OFF` vs `Fractional ON`) | Sai số bám (`TE`) & tiền chết (`Integer OFF`) | Lý do trung thực (tại sao không nhảy cóc) |
|---|---|---:|---|---|---|
| **`< 10.000 USD`** (`< 257,7 tr`) | **Chỉ Cash / T-Bill** (`0%` ETF, `0%` Crypto) | **`0%`** | `5k`: `159,0` vs `137,4 bps/năm` (`SUPER_ETF_6ENG`: **`515,9–533,7 bps/năm`**!) | `TE 82,9 bps`, tiền chết `6,74%` (`Sharpe 1,01 -> 0,83`) | Bẫy phí tối thiểu `0,35 USD/lệnh` + làm tròn lô nguyên ăn mòn lợi thế; tập trung hoàn gốc `100%` + `>= 2` payout từ `FTMO 10K` / `The5ers HS 5K`. |
| **`10.000 – 25.000 USD`** (`257,7 – 644,1 tr`) | **Macro ETF gọn `0` swap** (`S3B` `turn 2,0x` hoặc `L7_TOP2` `turn 10,0x`, bật Fractional) | **`0%`** | `10k`: `114,1` vs `112,5 bps/năm` (`Net CAGR +7,10%`, `Sh 0,93` với Fractional) | `TE 41,8 -> 15,6 bps`, tiền chết `3,39% -> 0,02%` | Đủ chạy 2 nhánh lệch pha (`Prop 7E + ETF`), rút tháng đói xuống `29,8%` (với `S3B`), không gánh rủi ro sàn CEX. Tránh `SUPER_ETF_6ENG` (`304 bps/năm`). |
| **`25.000 – 50.000 USD`** (`644,1 tr – 1,29 tỷ`) | **Macro ETF (`>= 75%`) + Crypto Spot `S2` & Carry `S3A` (`<= 25%`)** | **`<= 25%`** | `25k`: `86,1` vs `98,1 bps/năm` (`L7_TOP2` **ĐẠT SẠCH LÔ NGUYÊN**, `Net Sh 0,96`) | **`TE 17,7 bps`, tiền chết `1,27%`** (`PASS` không cần Fractional) | Kích hoạt trọn bộ 3 nhánh khi phần `25%` CEX đạt `>= 6.250 USD` (`~161 tr VND`) đủ chia coin an toàn, đồng thời `>= 75%` tài sản giữ tại IBKR. |
| **`50.000 – 100.000 USD`** (`1,29 – 2,58 tỷ`) | **Rổ ETF đầy đủ lô nguyên** (`L7_TOP2` / `SUPER_ETF_6ENG`) + Crypto (`<= 25%`) | **`<= 25%`** | `50k`: `L7_TOP2` `71,6 bps/yr` (`Net Sh 0,98`); `SUPER_ETF_6ENG` **ĐẠT SẠCH LÔ NGUYÊN** (`TE 17,0 bps`) | `TE 10,9 bps`, tiền chết `0,63%` | Hiệu ứng quy mô giúp chạy toàn bộ rổ ETF đa yếu tố mà không cần lô lẻ; tiến gần mốc Crossover (Own-Book >= Prop). |
| **`>= 100.000 USD`** (`>= 2,58 tỷ`) | Full ETF + Crypto (`<= 25%`) + **xem xét CME Micro Futures** | **`<= 25%`** | `100k`: `L7_TOP2` `59,0 bps/yr` (`Net CAGR +7,62%`, `Net Sh 1,00`) | `TE 8,2 bps`, tiền chết `0,31%` | Chỉ xét CME Micro Futures từ `100k USD` để yêu cầu ký quỹ và phí dữ liệu không bóp nghẹt quản trị rủi ro. |

---

## 4. Hợp Đồng Niêm Phong Mật Mã `holdout_v2_prospective (>= 2026-12-01)`

Để chống hoàn toàn thiên lệch nhìn lại kết quả (post-hoc rationalization) trước khi mở cửa sổ thực địa mới `holdout_v2_prospective` từ `2026-12-01T00:00:00Z`, công cụ [preregister_holdout_v2.py](../../tooling/ai-engines/quant_factory/preregister_holdout_v2.py) đã được xây dựng và kiểm định tự động (kể cả dưới `python -O`, `0` câu lệnh `assert`):

- **Cơ chế khóa thời gian & phát hiện sửa đổi 1 byte (`--freeze`, `--verify`, `--out-dir`, `--dry-run`):**
  - Chỉ cho phép `--freeze` khi `frozen_utc < 2026-12-01T00:00:00Z` (sau thời điểm đó tự động chặn lỗi `PREREGISTRATION_WINDOW_CLOSED`).
  - Sinh cặp tệp `HOLDOUT-V2-PREREGISTRATION-20261127.json` + `HOLDOUT-V2-PREREGISTRATION-20261127.sha256` chứa mã băm SHA-256 của toàn bộ `7` tệp cốt lõi bắt buộc (`Naqex_Master_Prop7E.mq5`, `Naqex_PropGuard.mqh`, `Naqex_Signals_7E.mqh`, `firms_catalog.json`, `risk_profiles.json`, `naqex_red_news_utc.csv`, `NATIVE_FTMO_HOLDOUT_LOCK.json` — chỉ đọc) và `1` khe tùy chọn (`Naqex_Master_Prop7E_v103.mq5` nếu hiện diện tại thời điểm đóng băng).
  - Lệnh `--verify` kiểm tra đồng thời chữ ký sidecar `.sha256`, mã băm nội bộ `manifest_payload_sha256`, hợp đồng ngưỡng Đạt/Dừng, và từng byte của mọi tệp trên đĩa — **chỉ cần sửa đúng 1 byte hoặc thêm tệp chưa đăng ký sau khi đóng băng là trả về mã lỗi khác `0`**.
- **Bộ ngưỡng Đạt / Dừng cứng đã khóa trong bản Pre-Registration:**
  - **Thời gian thực địa tối thiểu:** **`>= 90` ngày lịch** chạy Live/Demo sạch (`< 90` ngày -> `BLOCKED_INSUFFICIENT_DAYS`).
  - **Trượt giá bất lợi thực tế:** Đạt khi **`<= 1,50x`** · Cắt cứng (`KILL`) ngay nếu **`> 1,75x`** · Vùng giữa `1,50x..1,75x` -> `CONDITIONAL`.
  - **Kỷ luật vận hành tuyệt đối (`0` ngoại lệ):** **`swap_usd == 0,00`** · **`0` lần chỉnh tham số sau khi mở khóa** (`max_parameter_retunes_after_unlock == 0`) · `0` lệnh mất cắt lỗ · `0` `FILL_UNRESOLVED` · `0` lỗi parity/restart · mở khóa **1 lần duy nhất** (`single_shot_unlock_only = true`), có phê duyệt `G6` của chủ sở hữu và thư xác nhận EA bằng văn bản của quỹ.
  - **Tiêu chí kinh tế (`PASS` / `KILL`):** `PASS` khi lãi năm `>= +4,0%`, `Calmar >= 0,70`, `Float Peak DD <= 7,5%`, `Daily DD <= 3,0%`, và `>= 5/7` động cơ lõi khỏe; `KILL` ngay nếu lãi năm `<= 0,0%`, `Peak DD > 9,0%`, hoặc `Daily DD > 4,0%`.
- **Thời điểm chạy `--freeze` chính thức:** Theo kế hoạch điều phối, **Wave 2A** sẽ chạy `--freeze` vào `planning/research/` ngay sau khi toàn bộ các làn Wave-1 chốt xong tệp cuối cùng (bao gồm `Naqex_Master_Prop7E_v103.mq5` nếu được đưa vào gói ứng viên). Hiện tại chỉ chạy kiểm thử `--dry-run` trên kho chính và `--freeze`/`--verify` trên thư mục tạm (`tmp_path`), giữ sạch `0 VND` và `0` thay đổi trái phép.

---

## 5. Bước Hành Động Kế Tiếp (`< 2` Phút)

- **1 hành động ngay sau Wave-1:** Ở bước tổng hợp **Wave 2A**, chạy một lệnh duy nhất `.runtime\quant-audit-v24\Scripts\python.exe -O tooling/ai-engines/quant_factory/preregister_holdout_v2.py --freeze` rồi chạy ngay `--verify` để niêm phong vĩnh viễn cặp tệp `HOLDOUT-V2-PREREGISTRATION-20261127.{json,sha256}` trước mốc `01/12/2026 00:00 UTC`.
