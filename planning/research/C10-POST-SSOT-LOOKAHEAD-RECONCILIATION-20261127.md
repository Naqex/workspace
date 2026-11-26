---
title: Đối Chiếu Trước–Sau C10_NEWS_ON Sau Khi Gỡ 6 Điểm Lookahead, 2 Lỗi Mô Phỏng & Hợp Nhất SSOT (Dev 2018–2024)
date: 2026-11-27
status: verified_dev_reconciliation
scope: dev_2018_2024_only
holdout_rows_analysed: 0
order_send_count: 0
evidence_stage: DEV_BACKTEST_2018_2024_CLUSTER_B_VIEWED_NOT_BLIND_DAILY_APPROX
holdout_lock_sha256: f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486
frozen_tapes_binding_sha256: ec21845fd2b76fb345979063b2d5b429235d9dc537b805b73a4a4adaf2de3d6d
---

# Đối Chiếu Trước–Sau `C10_NEWS_ON` Sau Khi Hợp Nhất SSOT, Gỡ 6 Điểm Nhìn Trước Tương Lai & 2 Lỗi Bộ Mô Phỏng (Dev 2018–2024)

- **Kết luận 1 dòng:** Sau khi xây dựng lại toàn bộ băng giá `frozen_9e_tapes_v2` bằng mã nguồn nhân quả sau Làn L7 (`binding_sha256 = ec21845fd2b76fb3...`), **toàn bộ biên lợi nhuận lõi của `C10_NEWS_ON` gần như giữ nguyên** (`PORT_7E` chỉ giảm `-5,31 USD` / `-0,098%` trong 7 năm; `FTMO Standard 10K` `EV/Phí` chỉ đổi `+8,26x -> +8,25x`), **NHƯNG ma trận sốc đồng thời Flash-Crash trung thực đã vạch trần lỗ hổng nghiêm trọng ở pha thi P1/P2 (`7,19%–16,88% > 5,0%`) nếu bị trượt gap đồng loạt mà không có khiên tin đỏ và khóa rủi ro nhóm tiền tệ.**
- **Khóa an toàn bất biến:** `holdout_rows_analysed = 0` · `Holdout 2025+ SEALED` (`SHA f0a6b43cb205535b`) · `OrderSend = 0` · **`0 VND`** · `MT5_PROCS = 0` · máy chủ vận hành không bị chạm.
- **Cấp độ bằng chứng & tỷ giá:** **Mô phỏng quá khứ Dev `2018-01-02..2024-12-31` (`1.564` phiên, `Cluster B` đã xem — KHÔNG gọi là Holdout mù)**, nhãn **`DAILY_APPROX`** *(xấp xỉ cấp ngày từ băng giá M1 thực tế)* + đối chứng `28` lệnh đo khớp lệnh Demo FTMO (`0,66x`). **CHƯA phải Holdout mù `2025+`, CHƯA phải giao dịch tiền thật.** Tỷ giá thanh toán Việt Nam: **`1 USD = 25.765,94 VND`** · phí thẻ quốc tế **`+2,5%`** (không hoàn lại) · phí hoàn vé về thẻ FTMO **`0,0%`** · chiết khấu **NPV `6,0%/năm`**.

---

## 1. Bộ Chỉ Số Cân Bằng Toàn Diện `C10_NEWS_ON` Sau Sửa Lỗi & Định Vị Luật 15 (`Xấu -> Top 1% Thực Tế`)

Các chỉ số dưới đây được tính lại hoàn toàn trên băng giá nhân quả mới (`frozen_9e_tapes_v2`, Dev `2018–2024`, `holdout_rows_analysed = 0`), áp dụng cho danh mục lõi **`PORT_7E`** (7 động cơ giao dịch trong ngày, `swap = 0`, có khiên tin đỏ `±5` phút, ma sát nền `1,00x`):

- **Thông số lõi (`100K USD`, Funded `1,0x`, `1,00x` ma sát):**
  - **Tỷ lệ thắng (`Winrate`) & Tỷ lệ ăn/thua (`RR`):** **`48,61%`** / **`1,272x`** trên **`2.882`** lệnh (trung bình `~412` lệnh/năm).
  - **Kỳ vọng mỗi lệnh (`EV / lệnh`):** **`+0,0486R`** (`+18,01 USD/lệnh` ~ **`+464 nghìn VND/lệnh`** trên tài khoản `100K`; `+1,80 USD/lệnh` ~ `+46 nghìn VND/lệnh` trên `10K`).
  - **Hệ số sinh lời (`Profit Factor`):** **`1,203`** (cứ mất 1 đồng lỗ thu về `1,203` đồng lãi).
  - **Tụt sâu nhất (`Max DD`) & chuỗi thua liên tiếp:** **`8,62%`** (`8.615 USD` ~ `222,0 tr VND` trên `100K`; `862 USD` ~ `22,2 tr VND` trên `10K`), chuỗi thua dài nhất **`12` lệnh**, lỗ ngày lớn nhất ở `1,0x` là **`2,00%`**.
  - **Lãi trung bình năm, `Calmar` & `Sharpe`:** **`+7,415%/năm`** (`+7.415 USD/năm` ~ **`+191,1 tr VND/năm`** trên `100K`; `+711 USD/năm` ~ **`+18,3 tr VND/năm`** trên `10K` sau làm tròn `0,01` lot) · **`Calmar = 0,861`** · **`Sharpe = 1,234`**.
- **Hiệu quả 1 vé thi quỹ `FTMO 2-Step Standard 10K` (`C10_NEWS_ON`, `max_retries = 0`, `10.000` đường MC, `seed = 20261126`):**
  - **Giá Black Friday (đã gồm `+2,5%` phí thẻ VN):** **`70,42 USD`** (**`1,81 tr VND`**; giá gốc thẻ **`101,08 USD`** ~ **`2,60 tr VND`**).
  - **`EV NPV 24T` / `EV / 1 đồng phí` (ma sát `1,00x`):** Trung bình **`+580,82 USD`** (**`+14,97 tr VND`**) · Trung vị **`+293,17 USD`** (**`+7,55 tr VND`**) · Chưa chiết khấu **`+626,07 USD`** (`+16,13 tr VND`) · **`EV / Phí = +8,25x`** *(giá gốc: `+14,60 tr` / `+7,48 tr`, **`EV / Phí = +5,61x`**)*.
  - **Xác suất hòa/lỗ sau 24 tháng (`P(NPV24 <= 0)`):** **`42,05%`** trên `1` vé *(giảm còn `39,13%` nếu dự phòng `2` vé)*.
  - **Tỷ lệ `Đậu / Rớt / Chờ` theo tháng (tổng luôn đúng `100,00%`):**
    - `3` tháng: **`14,09%` Đậu / `2,40%` Rớt / `83,51%` Chờ** (`100,00%`)
    - `6` tháng: **`32,00%` Đậu / `3,23%` Rớt / `64,77%` Chờ** (`100,00%`)
    - `12` tháng: **`46,65%` Đậu / `4,27%` Rớt / `49,08%` Chờ** (`100,00%`)
    - `24` tháng: **`61,89%` Đậu / `5,60%` Rớt / `32,51%` Chờ** (`100,00%`)
  - **Cháy Funded 12 tháng & tháng không có payout:** **`0,01%`** (`cận trên Wilson 95% <= 0,08%`, trên mẫu thực tế cần `~299` tài khoản độc lập không cháy mới khẳng định `< 1%`) · tỷ lệ tháng Funded đói payout **`66,45%`** · trung vị chờ payout đầu **`287,0` ngày** (có điều kiện đã rút) / **`537,7` ngày** (không điều kiện chặn `730` ngày).
- **Ngưỡng gãy / điểm chết (Break-Even Threshold):** Chiến lược chuyển sang lỗ ròng khi chi phí trượt giá + spread thực tế vượt **`2,31x`** so với băng giá M1 chuẩn (`PORT_7E` không phanh gãy tại **`2,26x`**). Do đó khóa cứng ngưỡng **cắt chi phí chìm / dừng mua vé mới tại `> 1,75x`** (vì ngay tại `1,50x`, trung vị 1 vé `10K` đã rơi xuống **`-1,81 tr VND`** và `64,34%` kịch bản hòa/lỗ sau 24 tháng).

### Thang Định Vị Dọc Luật 15 (`Xấu -> Đủ dùng -> Tốt -> Top 1% Thực Tế`)

- 🔴 **Xấu:** `EV <= 0`, `PF < 1,05`, `Max DD > 10%`, `Calmar < 0,5`, `Sharpe < 0,6`, thi quỹ `EV/Phí <= 0x` hoặc cháy Funded `> 5%`.
- 🟡 **Đủ dùng — VỊ TRÍ HIỆN TẠI CỦA CHỈ SỐ LÕI (`EV/lệnh +0,0486R`, `PF 1,203`, `Max DD 8,62%`, `Calmar 0,861`):** Biên dương thật trên dữ liệu quá khứ 7 năm nhưng vẫn còn mỏng trước sốc chi phí `>= 1,50x` và chịu nhiều tháng chờ/đói payout (`66,5%`).
- 🟢 **Tốt — VỊ TRÍ HIỆN TẠI CỦA ĐỘ ÊM & THI QUỸ MÔ PHỎNG (`Winrate 48,6% / RR 1,27x`, `Sharpe 1,234`, `10K EV/Phí +8,25x`, `100K EV/Phí +12,82x`, cháy Funded mô phỏng `0,01%–0,03%`):** Đạt tiêu chuẩn tốt trên Dev backtest, nhưng **KHÔNG được tự xếp hạng Top 1% thực tế** vì chưa qua Holdout mù và chưa chạy tiền thật.
- 🏆 **Top 1% thực tế (Mục tiêu cần vươn tới):** `EV > +0,15R`, `PF 1,50–2,00+`, `Max DD 4%–7%`, `Calmar > 2,0`, `Sharpe 2,0–3,0` **trên tiền thật `>= 12` tháng**, rút tiền ổn định mỗi `2–4` tháng nhờ ghép nhiều nhánh độc lập lệch pha.

**Khoảng cách cụ thể tới `Top 1% thực tế`:**
1. **Khoảng cách bằng chứng:** Hiện mới là `Dev 2018–2024` (`Cluster B` đã xem) + `28` lệnh Demo FTMO; cần hoàn thành cổng Demo `14` ngày / thu thập dữ liệu khớp lệnh thật, vượt Holdout mù `2025+` (chỉ mở khi có phê duyệt riêng), rồi chứng minh `>= 12` tháng tiền thật.
2. **Khoảng cách hiệu suất lõi:** Cần nâng `Calmar` từ **`0,86`** lên **`> 1,5–2,0`** (`+0,64..+1,14`) và hạ `Max DD` ở `1,0x` từ **`8,62%`** xuống **`<= 6,5%`**, rút tỷ lệ tháng đói payout từ **`66,5%`** xuống **`< 25%`** bằng cách bổ sung nguồn lợi nhuận độc lập lệch pha (không tăng đòn bẩy liều ở P1/P2).
3. **Khoảng cách sốc đuôi pha P1/P2:** Ma trận Flash-Crash trung thực sau L7 cho thấy P1/P2 (`2,5x–4,75x`) vẫn bị **`7,19%–16,88%`** nếu mọi động cơ trượt gap đồng thời `1,25x`; phải duy trì bắt buộc khiên tin đỏ `±5` phút và khóa trần rủi ro cụm USD/JPY.

---

## 2. Bảng Đối Chiếu Toàn Bộ 6 Điểm Lookahead & 2 Lỗi Bộ Mô Phỏng (Trước vs Sau)

| Hạng mục sửa lỗi (Làn L7 / L3 / L4 / L12) | Trước khi sửa (Báo cáo cũ) | Sau khi sửa (Nhân quả & Trung thực) | Chênh lệch (`Sau - Trước`) | Đánh giá tác động |
|---|---|---|---|---|
| **1–4. Gỡ `entry_conv_rate` lookahead** (`pass24/27/28/whitebox_discovery`, `PORT_7E` `10K` 1,0x Swing) | Lãi `7` năm **`+5.413,40 USD`** (`+7,73%/năm`, `DD 6,36%`, `Calmar 1,22`, gãy `2,26x`) | Lãi `7` năm **`+5.408,09 USD`** (`+7,73%/năm`, `DD 6,36%`, `Calmar 1,21`, gãy `2,26x`) | **`-5,31 USD`** (**`-0,098%`**), `0` lệnh đổi | **Rất nhỏ** — khẳng định lợi nhuận lõi không phải ảo giác tỷ giá đóng lệnh |
| **1–4b. Gỡ `entry_conv_rate` lookahead (`PORT_9E` `10K` 1,0x Swing)** | Lãi `7` năm **`+6.182,54 USD`** (`+8,83%/năm`, `DD 6,37%`, `Calmar 1,39`, gãy `2,23x`) | Lãi `7` năm **`+6.170,95 USD`** (`+8,82%/năm`, `DD 6,37%`, `Calmar 1,38`, gãy `2,22x`) | **`-11,59 USD`** (**`-0,187%`**), `0` lệnh đổi | **Rất nhỏ** — chỉ ảnh hưởng 3 engine JPY/chéo (`E6 -1,75`, `E7 -3,56`, `S6 -6,28 USD`) |
| **5. Gỡ full-sample `std` trong `apply_vol_targeting_causal`** (`prop_engine.py`, `PORT_7E`) | Lãi năm **`+8,78%`**, EOD DD `6,35%`, Sharpe `1,20` *(dùng `std` toàn mẫu `2018–2024`)* | Lãi năm **`+8,51%`**, EOD DD `6,28%`, Sharpe `1,20` *(khóa vol Cluster A `< 2021` / `t-1`)* | **`-0,27 đ%/năm`**, EOD DD `-0,07 đ%` | **Nhỏ nhưng có thật** — loại bỏ thiên lệch nhìn trước độ biến động |
| **6a. Gỡ full-sample quantile trong Vol Terciles** (`red_team_auditor.py` Test 5, `PORT_7E`) | Thấp `+7,20%` (`S=1,30`) · Trung `+5,02%` (`S=0,85`) · Cao `+11,59%` (`S=1,82`) (`515/514/515` ngày) | Thấp `+8,69%` (`S=1,61`) · Trung `+3,15%` (`S=0,51`) · Cao `+11,17%` (`S=1,80`) (`455/466/593` ngày) | Cao `-0,42 đ%`, Trung `-1,87 đ%`, Thấp `+1,49 đ%` | **Kết luận giữ nguyên** — pha biến động cao vẫn mạnh nhất (`Sharpe 1,80`) |
| **6b. Bỏ kẹp `< 5%` trong Ma trận Sốc Flash-Crash** (`red_team_auditor.py` Test 6) | `Funded 2,75% (SAFE)` · `P2 3,75% (SAFE)` · `P1 Bal 4,45% (SAFE)` · `P1 Spr 4,55% (SAFE)` | `Funded 4,06% (SAFE)` · **`P2 7,19% (BREACH)`** · **`P1 Bal 15,00% (BREACH)`** · **`P1 Spr 16,88% (BREACH)`** | **`+1,31` đến `+12,33 đ%`** (`3/4` pha đổi từ `SAFE` giả -> `BREACH` thật) | **CẢNH BÁO ĐỎ QUAN TRỌNG NHẤT** — phanh phần mềm không chặn được gap `1,25x` đồng thời ở P1/P2 |
| **7. Lỗi Mô Phỏng #1: Raw DD kiểm trước `ea_cut`** (`prop_engine` + `quant_core.prop_sim`) | Cắt `dd = min(dd, ea_cut)` trước khi kiểm sàn `5%` ngày / `10%` tĩnh (che mất ngày sốc `-5,2%`) | Kiểm `raw_dd >= daily_cap` và `bal - raw_dd <= static_floor` **TRƯỚC** khi áp `ea_cut` | Bắt chết 100% ngày vượt sàn (`Mutant #7` + `15.000` mẫu Hypothesis trên `15` bài `@given` khớp từng xu `decimal_oracle`) | **Sửa triệt để rủi ro ảo** — không còn che cháy tài khoản sau lệnh cắt EA |
| **8. Lỗi Mô Phỏng #2: Khóa cứng `0` Infinite Mulligan** (`prop_engine._simulate_lifecycle_numba`) | Đường cháy hết `max_retries` có nguy cơ tự hồi sinh tạo vé ảo | Đường cháy khóa chết `stage = 0` tới hết chân trời (`Mutant #8`; `avg_tix = 1,00` khi `max_retries=0`) | `prop_engine` `FTMO 10K 1` vé: cháy P1 **`17,4%`**, `Pass 24T = 51,6%`, `CF24 +566,8 USD` | **Loại bỏ hoàn toàn ảo giác sống lại** khi hết ngân sách vé |

---

## 3. Phân Rã Chi Tiết 9 Động Cơ (`entry_conv_rate` Nhân Quả vs Cũ — `10K` `1,0x` Swing)

| Động cơ | Lệnh (Trước -> Sau) | Lãi `1,0x` Trước (USD) | Lãi `1,0x` Sau (USD) | Chênh lệch (USD) | Điểm gãy (Trước -> Sau) |
|---|---:|---:|---:|---:|---:|
| `E1_USDJPY_TOKYO` | `1.437 -> 1.437` (`+0`) | `1.021,29` | `1.021,29` | `+0,00` | `1,70x -> 1,70x` |
| `E2_USDJPY_EXP80` | `569 -> 569` (`+0`) | `1.450,29` | `1.450,29` | `+0,00` | `2,61x -> 2,61x` |
| `E3_GBPUSD_VH` | `198 -> 198` (`+0`) | `1.096,55` | `1.096,55` | `+0,00` | `3,81x -> 3,81x` |
| `E4_US100_SESS40` | `414 -> 414` (`+0`) | `629,17` | `629,17` | `+0,00` | `1,80x -> 1,80x` |
| `E5_US100_RS1130` | `261 -> 261` (`+0`) | `630,76` | `630,76` | `+0,00` | `2,48x -> 2,48x` |
| `E6_EURJPY_VOLCOMP` | `138 -> 138` (`+0`) | `393,77` | `392,02` | **`-1,75`** | `3,25x -> 3,24x` |
| `E7_USDJPY_NY10ET` | `105 -> 105` (`+0`) | `191,58` | `188,02` | **`-3,56`** | `2,13x -> 2,11x` |
| `S6_FX_USD_BSK` | `195 -> 195` (`+0`) | `360,84` | `354,56` | **`-6,28`** | `2,35x -> 2,33x` |
| `S7_XAU_EXP120` | `204 -> 204` (`+0`) | `408,30` | `408,30` | `+0,00` | `1,87x -> 1,87x` |
| **Tổng `PORT_7E`** | **`3.122 -> 3.122` (`+0`)** | **`5.413,40`** | **`5.408,09`** | **`-5,31` (`-0,098%`)** | **`2,26x -> 2,26x`** |
| **Tổng `PORT_9E`** | **`3.521 -> 3.521` (`+0`)** | **`6.182,54`** | **`6.170,95`** | **`-11,59` (`-0,187%`)** | **`2,23x -> 2,22x`** |

---

## 4. Đối Chiếu Trước–Sau `FTMO 2-Step Standard 10K & 100K` (Phí Thực VN, `10.000` Đường MC, `seed = 20261126`)

### 4.1. So Sánh Trực Tiếp Trước (Optimizer v2, 26/11) vs Sau (Băng Nhân Quả Mới, 27/11)

| Kịch bản (`FTMO 2-Step Standard`, `max_retries = 0`, ma sát `1,00x`) | `24T` Đậu / Rớt / Chờ (Trước -> Sau, tổng `100%`) | `NPV 24T` TB / TV Trước (tr VND) | `NPV 24T` TB / TV Sau (tr VND) | `EV / Phí` (Trước -> Sau) | `P(NPV24 <= 0)` (Trước -> Sau) |
|---|---|---|---|---:|---:|
| **`10K` · `C10_NEWS_ON` · BF thẻ `70,42 USD` (`1,81 tr`)** | `61,9/5,6/32,5%` -> **`61,89/5,60/32,51%`** | `+15,0` / `+7,6` | **`+14,97`** / **`+7,55`** | `+8,26x` -> **`+8,25x`** | `42,1%` -> **`42,05%`** |
| **`10K` · `C10_NEWS_ON` · Gốc thẻ `101,08 USD` (`2,60 tr`)** | `61,9/5,6/32,5%` -> **`61,89/5,60/32,51%`** | `+14,6` / `+7,5` | **`+14,60`** / **`+7,48`** | `+5,61x` -> **`+5,61x`** | `42,1%` -> **`42,05%`** |
| **`10K` · `C00` (Đối chứng) · BF thẻ `70,42 USD` (`1,81 tr`)** | `67,0/3,6/29,3%` -> **`67,14/3,60/29,26%`** | `+12,7` / `+8,9` | **`+12,63`** / **`+8,83`** | `+6,97x` -> **`+6,96x`** | `37,1%` -> **`37,20%`** |
| **`100K` · `C10_NEWS_ON` · BF thẻ `490,65 USD` (`12,64 tr`)** | `62,7/6,1/31,2%` -> **`62,75/6,15/31,10%`** | `+161,9` / `+85,9` | **`+162,13`** / **`+89,50`** | `+12,81x` -> **`+12,82x`** | `40,2%` -> **`40,09%`** |
| **`100K` · `C10_NEWS_ON` · Gốc thẻ `613,31 USD` (`15,80 tr`)** | `62,7/6,1/31,2%` -> **`62,75/6,15/31,10%`** | `+160,6` / `+85,6` | **`+160,73`** / **`+89,18`** | `+10,16x` -> **`+10,17x`** | `40,2%` -> **`40,10%`** |
| **`100K` · `C00` (Đối chứng) · BF thẻ `490,65 USD` (`12,64 tr`)** | `67,9/4,1/28,0%` -> **`68,00/4,18/27,82%`** | `+138,4` / `+97,3` | **`+138,46`** / **`+98,37`** | `+10,94x` -> **`+10,95x`** | `35,1%` -> **`34,94%`** |

### 4.2. Độ Nhạy Trượt Giá & Số Vé `FTMO 2-Step Standard 10K` Sau Sửa Lỗi (`C10_NEWS_ON`, Phí Thực VN)

| Ma sát & Chế độ vé | Phí thẻ (`USD` / `tr VND`) | `3T` Đậu/Rớt/Chờ | `6T` Đậu/Rớt/Chờ | `12T` Đậu/Rớt/Chờ | `24T` Đậu/Rớt/Chờ (`100%`) | `NPV 24T` TB / TV (tr VND) | `EV/Phí` | `P(<=0)` | Cháy Funded `12T` |
|---|---:|---|---|---|---|---:|---:|---:|---:|
| **`0,66x`** *(Demo)* · `1` vé BF | `70,42` (`1,81 tr`) | `18,64/2,48/78,88%` | `40,80/3,41/55,79%` | `58,63/4,44/36,93%` | `74,63/5,39/19,98%` | **`+24,38`** / `+21,89` | **`+13,44x`** | `27,92%` | `0,00%` (`<=0,05%`) |
| **`1,00x`** *(Nền)* · `1` vé BF | `70,42` (`1,81 tr`) | `14,09/2,40/83,51%` | `32,00/3,23/64,77%` | `46,65/4,27/49,08%` | `61,89/5,60/32,51%` | **`+14,97`** / `+7,55` | **`+8,25x`** | `42,05%` | `0,01%` (`<=0,08%`) |
| **`1,00x`** *(Nền)* · `2` vé BF | `70,42` (`1,81 tr`) | `14,32/2,17/83,51%` | `32,98/2,25/64,77%` | `48,65/2,27/49,08%` | `65,16/2,33/32,51%` | **`+15,60`** / `+9,41` | **`+8,60x`** | `39,13%` | `0,01%` (`<=0,08%`) |
| **`1,00x`** *(Nền)* · `1` vé Gốc | `101,08` (`2,60 tr`) | `14,09/2,40/83,51%` | `32,00/3,23/64,77%` | `46,65/4,27/49,08%` | `61,89/5,60/32,51%` | **`+14,60`** / `+7,48` | **`+5,61x`** | `42,05%` | `0,01%` (`<=0,08%`) |
| **`1,50x`** *(Stress)* · `1` vé BF | `70,42` (`1,81 tr`) | `8,44/2,29/89,27%` | `20,60/3,30/76,10%` | `30,59/4,40/65,01%` | `40,51/7,07/52,42%` | **`+5,89`** / **`-1,81`** | `+3,24x` | **`64,34%`** | `0,02%` (`<=0,12%`) |
| **`1,50x`** *(Stress)* · `2` vé BF | `70,42` (`1,81 tr`) | `8,62/2,11/89,27%` | `21,27/2,63/76,10%` | `31,95/3,04/65,01%` | `43,14/4,44/52,42%` | **`+6,14`** / **`-1,81`** | `+3,38x` | **`62,33%`** | `0,02%` (`<=0,12%`) |
| **`1,75x`** *(Đỏ)* · `1` vé BF | `70,42` (`1,81 tr`) | `6,43/2,21/91,36%` | `15,77/3,15/81,08%` | `23,63/4,55/71,82%` | `30,70/9,19/60,11%` | `+2,97` / **`-1,81`** | `+1,64x` | **`73,68%`** | `0,03%` (`<=0,16%`) |

### 4.3. Độ Bền Trượt Giá Lõi `PORT_7E` (`100K`, Funded `1,0x`, Khiên Tin Đỏ Bật)

| Mức ma sát | Lãi năm (%) | Lãi năm (tr VND / `100K`) | `Winrate` | `RR` | `EV / lệnh` | `PF` | `Max DD` | `Calmar` | `Sharpe` |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`0,66x`** *(Demo)* | `+9,59%` | `+247,0` tr | `49,55%` | `1,289x` | `+0,0654R` | `1,266` | `8,12%` | `1,181` | `1,567` |
| **`1,00x`** *(Nền)* | **`+7,42%`** | **`+191,1` tr** | **`48,61%`** | **`1,272x`** | **`+0,0486R`** | **`1,203`** | **`8,62%`** | **`0,861`** | **`1,234`** |
| **`1,25x`** | `+5,90%` | `+152,1` tr | `47,78%` | `1,268x` | `+0,0370R` | `1,160` | `8,99%` | `0,657` | `0,994` |
| **`1,50x`** *(Stress)* | `+4,42%` | `+113,8` tr | `47,33%` | `1,245x` | `+0,0254R` | `1,119` | `9,71%` | `0,455` | `0,751` |
| **`1,75x`** *(Ngưỡng đỏ)* | `+2,99%` | `+77,1` tr | `46,74%` | `1,230x` | `+0,0143R` | `1,080` | `11,15%` | `0,268` | `0,514` |
| **`2,00x`** | `+1,63%` | `+41,9` tr | `46,29%` | `1,210x` | `+0,0039R` | `1,043` | `13,72%` | `0,118` | `0,282` |
| **`2,50x`** *(Vượt ngưỡng gãy `2,31x`)* | `-1,02%` | `-26,3` tr | `45,11%` | `1,185x` | `-0,0166R` | `0,974` | `18,66%` | `-0,055` | `-0,181` |

*(Ghi chú độ kéo do làm tròn `0,01` lot ở `1,00x`: `5K` tụt `-10,77%` bỏ `31` lệnh; `10K` tụt `-4,48%` bỏ `4` lệnh; `50K` tụt `-0,91%` bỏ `0` lệnh; `100K` tụt `-0,32%` bỏ `0` lệnh — khớp gần như tuyệt đối với bản cũ.)*

---

## 5. Chứng Chỉ Kiểm Chứng Kỹ Thuật Độc Lập (Làn L12)

- **Băng giá nhân quả mới (`frozen_9e_tapes_v2`):** Xây lại sạch trong `16,84s` (`binding_sha256 = ec21845fd2b76fb3...`, `holdout_rows_analysed = 0`); độ trễ nạp lại tiến trình sạch (`python -B`): **`0,249s–0,253s`** (`< 0,30s`, `0` nạp `pyarrow`/`pass28`/`scipy`).
- **Fuzzing bất biến toán học (`Hypothesis`) trên `<X13_WORKER>`:** Chạy qua `compute_router.py` (`--allow-ntp-drift`, ghi nhận minh bạch lệch đồng hồ `<DEV_PC> = -1.614,9 ms`, `<X13_WORKER> = -4.689,8 ms`; chế độ mặc định vẫn chặn đóng fail-closed `< 1.000 ms`): **`15` bài `@given` × `1.000` mẫu = `15.000` kịch bản ngẫu nhiên Hypothesis + `1` bài kiểm tra AST xác định (`0` import `scipy`) = `16/16` ĐẠT 100%** trong `39,58s` + vượt `python -O`, xác thực chữ ký `manifest.sha256.json` **`VERIFIED_PASS`** (`5/5` tệp, `0` lỗi).
- **20 đột biến âm phản biện (`test_gate_mutations_20.py`):** **`20/20` ĐẠT 100%** dưới cả `pytest` thường lẫn `python -O -m pytest` (không bị vô hiệu hóa khi trình thông dịch lược bỏ `assert`).
- **Quyết định tài chính hiện tại:** Giữ nguyên **`0 VND`**, giữ khóa **`Holdout 2025+ SEALED`**, chưa thay đổi EA mặc định `v1.01`, chỉ chuyển bước tiếp theo khi hoàn tất kiểm toán thực địa và có phê duyệt rõ ràng của chủ sở hữu.
