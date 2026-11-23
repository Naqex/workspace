---
doc_type: research-report
title: "Lab #5: Khả thi CME Micro Futures Prop (Topstep 50K & Tradeify 50K Growth vs FTMO & The5ers)"
date: 2026-11-24
scope: wave2-cycle3a-lab5-cme-futures-prop
status: completed
owner: domain-research
code_module: tooling/ai-engines/quant_factory/cme_futures_prop_lab.py
evidence_json: .runtime/cme-futures-cache/cme_prop_study_summary.json
sleeve_export: .runtime/quant-pod-returns/sleeve5_cme_futures_prop.json
order_send_count: 0
holdout_rows_analysed: 0
holdout_lock_sha256: f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486
---

# Lab #5: Nghiên cứu Khả thi CME Micro Futures Prop (Topstep & Tradeify vs FTMO & The5ers)

> **Tóm tắt điều hành (Executive Summary):** Nghiên cứu đo lường trực tiếp cấu trúc vi mô của **`6 / 6` hợp đồng CME Micro Futures** (`MES, MNQ, MGC, MCL, M6E, M6J` — tải từ Yahoo Finance v8 D1 `2018–2026` + 1H gần nhất) và ánh xạ danh mục **`PORT_7E`** trên tập **Dev niêm phong `< 2025-01-01`** (`holdout_rows_analysed = 0`, `Holdout 2025+` khóa tuyệt đối) sang phí CME Micro thực tế (`1.24 USD/RT` hoa hồng + `2` tick spread/trượt giá, **0 phí đánh dấu CFD**, làm tròn số nguyên hợp đồng), sau đó chạy **5,000 đường Circular Block-Bootstrap Monte Carlo (`seed = 20261124`)** cho **Topstep 50K Combine -> XFA** và **Tradeify 50K Growth**.
>
> **Kết luận định lượng mang tính quyết định:**
> 1. **KHÔNG ĐƯỢC chuyển nguyên trạng `PORT_7E` (thiên về FX) sang CME Micros (`Scenario A`):** Phí cố định trên hợp đồng vi mô FX (`M6J` chỉ `7,862 USD` danh nghĩa nhưng tốn `3.74 USD/RT` = **`9.810%` biên độ ngày**, tương đương **`~47 USD/lot FX tiêu chuẩn`** — đắt gấp `2.5x` CFD FTMO!) kết hợp bẫy làm tròn số nguyên hợp đồng `MNQ` tại rủi ro `200 USD` làm lợi nhuận ròng sụt từ `+23,133.52 USD` xuống **`+2,983.72 USD`**, kéo **EV trên 1 USD phí âm nặng** ở cả **Topstep (`-0.65x` đến `-0.29x`)** lẫn **Tradeify (`-0.86x` đến `-0.76x`)**.
> 2. **Nhánh Chỉ số & Vàng CME (`Scenario B: MNQ + MGC` ở mức `400 USD/R`) thực sự RẺ hơn CFD (`-77%` phí trên `MNQ`), nhưng chỉ `3` engine (`E4, E5, S7`) chưa đủ đánh bại CFD Prop hiện tại:** Trên **Topstep 50K (`2.0x` eval)** đạt **`EV/USD Fee = +1.83x`**, `CF24 = +1,196.12 USD`, `Fail 1-Try = 50.8%`, `OOP95 = 1,229 USD` — vẫn thua **FTMO Swing (`+3.25x`)**, **FTMO BF-25% (`+4.08x`)** và **The5ers HS (`+7.17x`)** từ nghiên cứu M2.2. **Tradeify 50K Growth** chỉ đạt `+0.17x` (`OOP95 = 3,197 USD`) do phí thuê bao tháng `139 USD/tháng` và luật nhất quán `40%`.
> 3. **Cận trên khi xây đủ danh mục 7 engine thuần CME (`Scenario C — Cost Parity`):** Nếu sở hữu một danh mục đa dạng 5–7 engine **chuyên biệt cho sàn CME** (`MNQ + MES + MGC + MCL`, tuyệt đối bỏ FX micro `M6J/M6E/M6B`), **Topstep 50K (`1.5x–2.5x`)** vọt lên **`EV/USD Fee = +5.43x` đến `+7.78x`** (`CF24 = +3,499.78` đến `+4,295.62 USD`, `P(Pay >= 3) = 72.2%..81.1%`, `OOP95 = 984..1,180 USD`), **ngang bằng và vượt FTMO/The5ers**. Do đó: **Giai đoạn 1 ưu tiên 100% FTMO + The5ers cho `PORT_7E`; chỉ mở Topstep 50K khi đã hoàn thiện đủ bộ động cơ thuần `MNQ/MES/MGC/MCL` (không FX micro)!**

---

## 1. Đo lường Vi cấu trúc 6 Hợp đồng CME Micro Futures (Yahoo Continuous D1 & 1H)

Tất cả dữ liệu lưu cache Zstd Parquet tại `.runtime/cme-futures-cache/` (`OrderSend = 0`, không API key). Chi phí mỗi hợp đồng CME Micro bao gồm **`1.24 USD/RT`** phí sàn/NFA/thanh toán bù trừ + **`2` tick** spread & trượt giá vòng tròn (`all_in_rt_cost_usd`).

| Mã CME Micro | Mã Yahoo | Tài sản ánh xạ | D1 / 1H Rows | Danh nghĩa (`USD`) | Trung vị biên độ D1 (`USD`) | Phí + 2 Tick (`USD/RT`) | **Phí / Biên độ D1 (%)** | Nhận xét cấu trúc chi phí |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`MNQ`** | `NQ=F` | `US100` (Nasdaq) | `2,206` / `2,886` | `53,453.50` | `1,021.00` | `2.24` | **`0.219%`** | **Rẻ nhất hành tinh** cho chỉ số — rẻ hơn CFD FTMO tới `~80%` |
| **`MGC`** | `GC=F` | `XAUUSD` (Vàng) | `2,206` / `2,889` | `36,499.00` | `877.50` | `3.24` | **`0.369%`** | Rẻ hơn một nửa CFD Vàng, nhưng 1 hợp đồng = `10 oz` (`0.1` lot) |
| **`MCL`** | `CL=F` | `WTI` (Dầu thô) | `2,204` / `2,888` | `8,106.00` | `383.00` | `3.24` | **`0.846%`** | Rất hấp dẫn để phát triển engine mới (không có phí swap âm CFD) |
| **`MES`** | `ES=F` | `US500` (S&P 500) | `2,206` / `2,888` | `36,166.25` | `383.75` | `3.74` | **`0.975%`** | Thanh khoản bậc nhất thế giới, phù hợp intraday S&P 500 |
| **`M6E`** | `6E=F` | `EURUSD` (`12.5k EUR`) | `2,205` / `2,887` | `13,617.50` | `61.25` | `3.74` | **`6.106%`** | **Bẫy phí FX Micro** (~`30 USD/lot` tiêu chuẩn vs ~`12 USD` FX ECN) |
| **`M6J`** | `6J=F` | `USDJPY` (`1.25M JPY`) | `2,206` / `2,883` | `7,861.87` | `38.13` | `3.74` | **`9.810%`** | **Cực đắt (~`47 USD/lot` tiêu chuẩn)** — giết chết mọi cạnh FX tần suất cao |

*(Ghi chú thêm: `M6B` Micro GBP/USD `6,250 GBP` có `all_in_rt_cost = 2.49 USD` cho `0.0625` lot chuẩn, tức `~39.8 USD/lot` chuẩn — đắt gấp `2.5x` FTMO CFD.)*

---

## 2. Phân tách Chi phí & Bẫy Làm tròn Số nguyên trên Tập Dev Niêm phong (`2018–2024`)

Toàn bộ lệnh `PORT_7E` lấy từ băng M1 Dev niêm phong (`< 2025-01-01`, `holdout_rows_analysed = 0`, SHA-256 khóa giữ nguyên `f0a6b43cb205...`). Để tách bạch hoàn toàn **2 nguyên nhân gốc rễ** (bẫy phí FX Micro vs bẫy làm tròn số nguyên hợp đồng `floor()`), Lab #5 chạy 3 phép ánh xạ độc lập:

### 2.1 So sánh Từng Động cơ trên Lịch Dev 1,564 Phiên (`ext_days`): Scenario A (`200 USD/R`, Nguyên) vs Scenario B (`MNQ+MGC 400 USD/R`, Nguyên) vs Chuẩn Không làm tròn (`Fractional 200 USD/R`)

| Engine (`PORT_7E`) | Mã CME | Lệnh trên `ext_days` | **Sc.A (`200 USD/R` Nguyên):** Bị Skip / CME Net / CFD Net | **Sc.B (`400 USD/R` Nguyên):** Bị Skip / CME Net / CFD Net | **Fractional (`200 USD/R`):** CME Net / CFD Net (`Delta`) | Kết luận chi phí CME vs CFD |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `E1_USDJPY_TOKYO` | `M6J` | `1,437` | `32` / **`-3,331.46`** / `+4,599.08` | *(Loại khỏi Sc.B)* | `-4,228.55` / `+4,599.08` (`-8,827.62`) | Phí `M6J` `10.3k–12.9k USD` (>2x CFD) -> **LOẠI BỎ** |
| `E2_USDJPY_EXP80` | `M6J` | `498` | `0` / `+284.30` / `+5,907.55` | *(Loại khỏi Sc.B)* | `+557.16` / `+5,907.55` (`-5,350.39`) | Phí `M6J` ăn mất `95%` lãi ròng -> **LOẠI BỎ** |
| `E3_GBPUSD_VH` | `M6B` | `171` | `0` / `+2,400.06` / `+4,639.64` | *(Loại khỏi Sc.B)* | `+2,886.60` / `+4,639.64` (`-1,753.05`) | Phí `M6B` cao gấp `2.5x` CFD -> **LOẠI BỎ** |
| `E7_USDJPY_NY10ET` | `M6J` | `96` | `0` / `-10.78` / `+773.94` | *(Loại khỏi Sc.B)* | `-159.07` / `+773.94` (`-933.01`) | Phí `M6J` gấp `2.2x–2.6x` CFD -> **LOẠI BỎ** |
| **`E4_US100_SESS40`** | **`MNQ`** | `369` | `238` (`64%`!) / `+2,203.17` / `+2,557.71` | **`23` (`6%`) / `+6,090.66` / `+5,115.43`** | **`+4,447.22` / `+2,557.71` (`+1,889.51`)** | **CME THẮNG ÁP ĐẢO (`+975.23 USD` ở Sc.B, phí `-77.3%`)** |
| **`E5_US100_RS1130`** | **`MNQ`** | `223` | `161` (`72%`!) / `+221.03` / `+2,589.65` | **`15` (`7%`) / `+4,304.25` / `+5,179.30`** | **`+3,609.08` / `+2,589.65` (`+1,019.43`)** | Phí CME giảm `-76.9%` (`620` vs `2,683 USD`); fractional thắng `+1,019 USD` |
| **`S7_XAU_EXP120`** | **`MGC`** | `173` | `16` / `+1,217.39` / `+2,065.95` | `0` / `+3,608.57` / `+4,131.90` | **`+2,622.09` / `+2,065.95` (`+556.14`)** | Phí CME giảm một nửa (`1,241` vs `2,521 USD`), chỉ mất sizing do `floor(10 oz)` |
| **TỔNG DANH MỤC** | — | — | **`+2,983.72` vs `+23,133.52 USD`** | **`+14,003.48` vs `+14,426.63 USD`** | **`+9,734.53` vs `+23,133.52 USD`** | **Chỉ số & Vàng thắng phí trên CME; FX Micros là tự sát** |

*(Lưu ý kỹ thuật về bẫy làm tròn `MNQ`: Ở mức `200 USD/R`, 1 hợp đồng `MNQ` (`2 USD/điểm`) khi ATR Nasdaq rộng `150–300` điểm tạo rủi ro cắt lỗ tối thiểu `300–600 USD > 200 USD`, buộc bot phải bỏ qua tới `64%` lệnh `E4` và `72%` lệnh `E5`! Nâng đơn vị rủi ro lên `400 USD/R` ở Scenario B lập tức mở khóa `93–94%` lệnh, giúp phí `MNQ` giảm `-77%` và tổng danh mục `MNQ+MGC` tiệm cận CFD dù chịu ràng buộc số nguyên hợp đồng!)*

---

## 3. So sánh Trực diện Monte Carlo (5,000 đường, `seed = 20261124`): Topstep 50K & Tradeify 50K Growth vs FTMO & The5ers

### 3.1 Bộ Luật Hợp đồng Futures Prop được Mô phỏng Chính xác
- **`TOPSTEP_50K_COMBINE` (`Topstep 50K Combine -> XFA`):** Mục tiêu `3,000 USD`, EOD Trailing DD `2,000 USD` (khóa cứng tại `0 USD` khi đạt buffer `2,000 USD` hoặc sau lần rút đầu tiên), DLL `1,000 USD`, Luật nhất quán `50%` trong vòng thi, Phí thuê bao `49 USD/tháng` (reset `49 USD`), Phí kích hoạt `149 USD` khi đậu. Rút tiền XFA: tối thiểu `5` ngày thắng `>= 200 USD`, giữ lại đệm `2,000 USD`, tối đa `50%` số dư (trần `5,000 USD/lần`), chia `100%` cho `10,000 USD` đầu rồi `90%`.
- **`TRADEIFY_50K_GROWTH` (`Tradeify 50K Growth`):** Mục tiêu `3,000 USD`, EOD Trailing DD `2,000 USD`, DLL `1,250 USD`, Luật nhất quán khắt khe `40%`, Phí thuê bao **`139 USD/tháng`** (reset `139 USD`), **không phí kích hoạt (`0 USD`)**. Rút tiền giữ đệm `2,000 USD`, chia `100%` cho `15,000 USD` đầu rồi `90%`.

### 3.2 Bảng So sánh EV trên 1 USD Phí — Toàn bộ 18 Cấu hình CME vs 3 Chuẩn CFD M2.2

| Hãng Prop / Kịch bản | Nhánh dữ liệu (`Sleeve Subset`) | Scale (`Eval/Fund`) | Fail 1-Try | Pass Ever (`<=24m`) | Med Pass (`tháng`) | `P(Pay>=1)` / `P(Pay>=3)` | Phí TB (`USD`) | **CF 24m (`USD`)** | **`EV / 1 USD Phí`** | **`OOP95` (`USD`)** |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Topstep 50K** | `A_CME_7E_MICROS_200R` | `1.5x / 1.0x` | `69.4%` | `77.8%` | `9.62m` | `25.1%` / `7.9%` | `991.34` | `-644.41` | **`-0.65x`** | `1,372.0` |
| **Topstep 50K** | `A_CME_7E_MICROS_200R` | `2.5x / 1.0x` | `73.8%` | `91.9%` | `5.71m` | `38.6%` / `14.4%` | `826.09` | `-240.75` | **`-0.29x`** | `1,278.0` |
| **Tradeify 50K** | `A_CME_7E_MICROS_200R` | `1.5x / 1.0x` | `69.9%` | `76.8%` | `9.76m` | `24.6%` / `7.7%` | `2,460.33` | `-2,121.70` | **`-0.86x`** | `3,753.0` |
| **Tradeify 50K** | `A_CME_7E_MICROS_200R` | `2.5x / 1.0x` | `79.1%` | `85.2%` | `6.86m` | `33.2%` / `12.0%` | `2,052.25` | `-1,560.73` | **`-0.76x`** | `3,475.0` |
| **Topstep 50K** | `B_CME_MNQ_MGC_400R` | `1.0x / 0.75x` | `33.3%` | `83.6%` | `10.62m` | `37.4%` / `8.2%` | `848.48` | `-365.32` | **`-0.43x`** | `1,274.0` |
| **Topstep 50K** | `B_CME_MNQ_MGC_400R` | `1.5x / 1.0x` | `45.8%` | `95.0%` | `7.00m` | `62.8%` / `30.2%` | `750.37` | `+710.80` | **`+0.95x`** | `1,276.0` |
| **Topstep 50K** | `B_CME_MNQ_MGC_400R` *(Thực tế tốt nhất)* | `2.0x / 1.0x` | `50.8%` | `98.7%` | `5.05m` | `72.7%` / `39.6%` | `653.06` | **`+1,196.12`** | **`+1.83x`** | `1,229.0` |
| **Tradeify 50K** | `B_CME_MNQ_MGC_400R` | `1.0x / 0.75x` | `34.1%` | `81.9%` | `10.86m` | `36.0%` / `7.4%` | `2,102.40` | `-1,647.72` | **`-0.78x`** | `3,475.0` |
| **Tradeify 50K** | `B_CME_MNQ_MGC_400R` | `1.5x / 1.0x` | `46.9%` | `94.1%` | `7.24m` | `61.6%` / `29.4%` | `1,706.20` | `-284.23` | **`-0.17x`** | `3,475.0` |
| **Tradeify 50K** | `B_CME_MNQ_MGC_400R` | `2.0x / 1.0x` | `54.7%` | `97.8%` | `5.71m` | `69.3%` / `36.0%` | `1,464.42` | `+252.46` | **`+0.17x`** | `3,197.0` |
| **Topstep 50K** | `C_7E_CME_COST_PARITY` *(Cận trên 7E)* | `1.0x / 0.75x` | `29.2%` | `97.0%` | `7.00m` | `74.3%` / `48.9%` | `669.78` | `+1,426.48` | **`+2.13x`** | `1,227.0` |
| **Topstep 50K** | `C_7E_CME_COST_PARITY` | `1.5x / 1.0x` | `42.2%` | `99.7%` | `4.33m` | `88.1%` / `72.2%` | `644.56` | `+3,499.78` | **`+5.43x`** | `1,180.1` |
| **Topstep 50K** | `C_7E_CME_COST_PARITY` | `2.0x / 1.0x` | `50.8%` | `99.7%` | `3.29m` | `91.8%` / `78.3%` | `589.67` | `+3,997.65` | **`+6.78x`** | `1,082.0` |
| **Topstep 50K** | `C_7E_CME_COST_PARITY` *(Cận trên đỉnh)* | `2.5x / 1.0x` | `56.0%` | `99.2%` | `2.71m` | `93.2%` / `81.1%` | `552.01` | **`+4,295.62`** | **`+7.78x`** | `984.0` |
| **Tradeify 50K** | `C_7E_CME_COST_PARITY` | `1.0x / 0.75x` | `29.2%` | `97.0%` | `7.00m` | `74.3%` / `48.9%` | `1,449.44` | `+646.36` | **`+0.45x`** | `3,058.0` |
| **Tradeify 50K** | `C_7E_CME_COST_PARITY` | `1.5x / 1.0x` | `45.5%` | `99.3%` | `4.76m` | `86.1%` / `69.2%` | `1,349.61` | `+2,583.44` | **`+1.91x`** | `2,919.0` |
| **Tradeify 50K** | `C_7E_CME_COST_PARITY` | `2.0x / 1.0x` | `56.6%` | `99.0%` | `3.95m` | `89.0%` / `73.9%` | `1,225.62` | `+3,047.19` | **`+2.49x`** | `2,641.0` |
| **Tradeify 50K** | `C_7E_CME_COST_PARITY` | `2.5x / 1.0x` | `64.0%` | `97.4%` | `3.38m` | `88.6%` / `75.9%` | `1,127.68` | `+3,328.41` | **`+2.95x`** | `2,363.0` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| *Chuẩn M2.2:* **`FTMO_SWING_10K`** | *`PORT_7E` CFD Balanced* | *Balanced* | **`23.8%`** | — | `5.90m` | — | `219.30` | `+712.00` | **`+3.25x`** | `504.0` |
| *Chuẩn M2.2:* **`FTMO_STD_10K_BF25`** | *`PORT_7E` CFD Balanced* | *Balanced* | **`23.7%`** | — | `6.10m` | — | `163.70` | `+668.40` | **`+4.08x`** | `378.0` |
| *Chuẩn M2.2:* **`THE5ERS_HS_5K_8P5`** | *`PORT_7E` CFD Balanced* | *Balanced* | **`22.6%`** | — | `5.60m` | — | **`48.60`** | `+348.40` | **`+7.17x`** | **`74.1`** |

---

## 4. Phản biện Cấu trúc & Lộ trình Triển khai Đề xuất cho Owner

1. **Tại sao Topstep (`49 USD/tháng`) thắng áp đảo Tradeify (`139 USD/tháng`) với hệ thống định lượng đa động cơ?**
   - Hệ thống định lượng kỷ luật có tốc độ vượt vòng thi trung bình `3–7` tháng để giữ `Fail 1-Try` dưới `50%`. Trong chu kỳ này, phí thuê bao tháng của Tradeify (`139 USD/tháng`, đắt gần `3x` Topstep) nhanh chóng xóa sổ lợi thế miễn phí kích hoạt `149 USD`, đồng thời đẩy rủi ro tiền túi `OOP95` lên `2,363–3,475 USD` (so với `984–1,276 USD` của Topstep và chỉ `74–504 USD` của The5ers/FTMO).
2. **Tại sao CFD Prop (`FTMO + The5ers`) vẫn là Cửa vào Số 1 trong 6–12 tháng đầu?**
   - **Phí một lần, không đồng hồ đếm ngược tháng:** FTMO và The5ers không trừ tiền mỗi tháng khi thị trường đi ngang.
   - **Không có bẫy số nguyên hợp đồng & thân thiện FX:** Cả 4 động cơ FX (`E1, E2, E3, E7`) chạy mượt từ `0.01` lot với spread ECN rẻ gấp `2–2.5x` `M6J/M6B`.
   - **Tỷ lệ trượt vòng 1 thấp gấp đôi:** `22.6%–23.8%` (Static Drawdown `10%`) so với `42%–56%` trên Topstep/Tradeify (EOD Trailing Drawdown chỉ `2,000 USD` cho mục tiêu `3,000 USD`, tức tỷ lệ `Reward/DD = 1.5x` thay vì `1.0x`).
3. **Điều kiện Mở khóa Nhánh CME Futures (`Topstep 50K` -> Sleeve Prop thứ 3):**
   - Chỉ kích hoạt **Topstep 50K** (để đa dạng hóa rủi ro đối tác prop ngoài CFD và hưởng lợi ích sàn giao dịch tập trung CME) **SAU KHI** xây thêm ít nhất `2–3` động cơ trực giao trên **`MES` (S&P 500)** và **`MCL` (Dầu thô WTI)** ghép cùng **`MNQ` (`E4, E5`)** + **`MGC` (`S7`)**, tạo đủ tổ hợp `5–6` engine không dùng FX micro. Khi đó, hiệu năng thực tế sẽ tiệm cận **Scenario C (`EV/USD Fee = +5.43x` đến `+7.78x`, `CF24 > +3,500 USD`)**!

---

## 5. Tài sản & Tích hợp Hệ thống

- **Mã nguồn chuẩn hóa:** [cme_futures_prop_lab.py](../../tooling/ai-engines/quant_factory/cme_futures_prop_lab.py)
- **Kiểm thử tự động (Determinism, EOD Trailing DD, Consistency, Holdout Seal):** [test_wave2_etf40_and_cme_labs.py](../../tooling/ai-engines/tests/test_wave2_etf40_and_cme_labs.py)
- **Đường lợi suất Dev CME (`MNQ+MGC`, `< 2025-01-01`):** `.runtime/quant-pod-returns/sleeve5_cme_futures_prop.json` (`n_days = 1,564`, `Cl.A Sharpe 1.151`, `Cl.B Sharpe 0.729`, `Full Dev Sharpe 0.969`, `MaxDD 4.83%`, `holdout_rows_analysed = 0`).
- **Tài liệu so sánh nền M2.2 & Lộ trình vốn:** [PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md](PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md) | [capital-scaling-prop-to-own-book.md](../../knowledge/topics/capital-scaling-prop-to-own-book.md)
