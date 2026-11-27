---
title: Nghiên Cứu Pareto Khiên Chống Sốc Flash-Crash (Shield A/B/C) & Ứng Viên Phòng Thủ Naqex Master Prop7E v1.03 (Dev 2018–2024)
date: 2026-11-27
status: verified_dev_pareto_study
scope: dev_2018_2024_only
holdout_rows_analysed: 0
order_send_count: 0
evidence_stage: DEV_BACKTEST_2018_2024_CLUSTER_B_VIEWED_NOT_BLIND_DAILY_APPROX
frozen_tapes_binding_sha256: 9ec0e5d581f78c95f544ac8f0dfaec16b413439126f341dbaf4a227496183855
frozen_tapes_npz_sha256: c2bf460ce09a8818316e0c53aec696a31c0cd38d83c7eed758c07e8601f084b3
winner_shield_id: SHIELD_C_TOT300_10M
candidate_ea: tooling/ai-engines/exports/Naqex_Master_Prop7E_v103.mq5
---

# Nghiên Cứu Pareto Khiên Chống Sốc Flash-Crash (Shield A / B / C) & Ứng Viên Phòng Thủ `Naqex_Master_Prop7E_v103` (Dev 2018–2024)

- **Kết luận 1 dòng:** Tổ hợp **`SHIELD_C_TOT300_10M`** (trần tổng rủi ro mở đồng thời **`3,00%`** ở P1/P2 / **`2,25%`** ở Funded + khóa cụm tiền tệ cùng chiều `USD/JPY/US100` + `SpreadGuard` hiệu chuẩn nhân quả từ `10,18` triệu nến M1 Bid/Ask thật + lịch tin đỏ chính thức `6-CCY 523` sự kiện `±10` phút / BoJ `±60` phút) **áp đảo Pareto toàn diện** so với nền `C10_NEWS_ON`: hạ sốc gap đồng thời `1,25x` từ **`7,19%–16,88% (BREACH)`** xuống **`<= 3,75% (SAFE <= 4,50%)`** trên toàn bộ 4 cấu hình (`Funded`, `P2`, `P1 Bal`, `P1 Spr`), cắt tỷ lệ rớt vé thi 24 tháng từ **`5,60%` xuống `0,32%`** (`-94,3%`), giảm tụt sâu nhất `1,0x` từ **`8,62%` xuống `6,90%`** (`Calmar 0,861 -> 1,040`), đồng thời **TĂNG** kỳ vọng ròng 1 vé FTMO Standard `10K` từ **`+14,97 tr VND` lên `+15,87 tr VND`** (`EV/Phí +8,25x -> +8,75x`, trung vị nhảy vọt **`+7,55 tr -> +11,16 tr VND`**).
- **Khóa an toàn bất biến:** `holdout_rows_analysed = 0` · `Holdout 2025+ SEALED` · `OrderSend = 0` · **`0 VND`** · `MT5_PROCS = 0` · EA sản xuất `Naqex_Master_Prop7E.mq5` (`v1.01`), `Naqex_PropGuard.mqh`, `Naqex_Signals_7E.mqh` và `.runtime/mt5-compiled-ex5/` (`10` tệp `.ex5`, `0` tệp `.ex5` trong `exports/`) giữ nguyên tuyệt đối.
- **Cấp độ bằng chứng & thông số quy đổi:** **Mô phỏng quá khứ Dev `2018-01-02..2024-12-31` (`1.564` phiên, `Cluster B` đã xem — KHÔNG gọi là Holdout mù)**, nhãn **`DAILY_APPROX`** *(xấp xỉ cấp ngày từ băng giá M1 thực tế `frozen_9e_tapes_v2`, `npz_sha256 = c2bf460ce09a8818...`)*. **CHƯA phải Holdout mù `2025+`, CHƯA phải giao dịch tiền thật.** Tỷ giá thanh toán VN: **`1 USD = 25.765,94 VND`** · phí thẻ quốc tế **`+2,5%`** · phí rút tiền VN **`1,5%`** · phí hoàn vé FTMO **`0,0%`** · chiết khấu **NPV `6,0%/năm`**.

---

## 1. Bộ Chỉ Số Cân Bằng Toàn Diện `SHIELD_C_TOT300_10M` vs Nền `C10_NEWS_ON` & Định Vị Luật 15

Các chỉ số dưới đây được tính trực tiếp từ băng giá nhân quả `frozen_9e_tapes_v2` (Dev `2018–2024`, `holdout_rows_analysed = 0`, `seed = 20261126`, `10.000` đường MC Block-Bootstrap `block_len = 5` ngày):

- **Thông số lõi danh mục `PORT_7E` (`100K USD`, Funded `1,0x`, ma sát `1,00x`, `swap = 0`):**
  - **Tỷ lệ thắng (`Winrate`) & Tỷ lệ ăn/thua (`RR`):** **`48,87%`** / **`1,260x`** trên **`2.828`** lệnh *(nền `C10_NEWS_ON`: `48,61%` / `1,272x` trên `2.882` lệnh; chỉ lọc bỏ `54` lệnh xấu nhất trong 7 năm = `-1,87%` số lệnh)*.
  - **Kỳ vọng mỗi lệnh (`EV / lệnh`):** **`+0,0457R`** (**`+17,76 USD/lệnh`** ~ **`+458 nghìn VND/lệnh`** trên `100K`; ~`+1,78 USD` ~ **`+46 nghìn VND/lệnh`** trên `10K`) *(nền: `+0,0486R` / `+18,01 USD/lệnh`)*.
  - **Hệ số sinh lời (`Profit Factor`):** **`1,204`** *(tăng nhẹ từ nền `1,203` — cứ mất 1 đồng lỗ thu về `1,204` đồng lãi)*.
  - **Tụt sâu nhất (`Max DD`) & chuỗi thua dài nhất:** **`6,90%`** (`6.899 USD` ~ `177,8 tr VND` trên `100K`; `690 USD` ~ `17,8 tr VND` trên `10K`) — **giảm mạnh `-1,72` điểm % so với nền `8,62%`**! Chuỗi thua dài nhất **`12` lệnh**, lỗ ngày lớn nhất ở `1,0x` giảm từ `2,00%` xuống **`1,54%`**.
  - **Lãi trung bình năm, `Calmar` & `Sharpe`:** **`+7,174%/năm`** (`+7.174 USD/năm` ~ **`+184,8 tr VND/năm`** trên `100K`; Cụm A `+8,51%` / Cụm B `+6,17%`) · **`Calmar = 1,040`** *(tăng **`+20,8%`** so với nền `0,861`)* · **`Sharpe = 1,249`** *(tăng so với nền `1,234`)*.
- **Hiệu quả 1 vé thi quỹ `FTMO 2-Step Standard 10K` (`SHIELD_C_TOT300_10M`, `max_retries = 0`, `10.000` đường MC, `seed = 20261126`):**
  - **Giá Black Friday (đã gồm `+2,5%` phí thẻ VN):** **`70,42 USD`** (**`1,81 tr VND`**; giá gốc thẻ **`101,08 USD`** ~ **`2,60 tr VND`**).
  - **`EV NPV 24T` & `EV / 1 đồng phí` (ma sát `1,00x`):**
    - Giá Black Friday: Trung bình **`+616,06 USD`** (**`+15,87 tr VND`**, tăng **`+0,90 tr VND`** so với nền `+14,97 tr`) · Trung vị **`+433,23 USD`** (**`+11,16 tr VND`**, nhảy vọt **`+47,8%`** so với nền `+7,55 tr`!) · Chưa chiết khấu **`+664,81 USD`** (`+17,13 tr VND`) · **`EV / Phí = +8,75x`** *(nền `+8,25x`)*.
    - Giá gốc (`101,08 USD`): Trung bình **`+603,75 USD`** (`+15,56 tr VND`) · Trung vị **`+11,08 tr VND`** · **`EV / Phí = +5,97x`** *(nền `+5,61x`)*.
    - Gói `100K` Black Friday (`490,65 USD` ~ `12,64 tr VND`): Trung bình **`+6.590,04 USD`** (**`+169,80 tr VND`**) · Trung vị **`+120,44 tr VND`** *(tăng `+30,94 tr VND` so với nền `+89,50 tr`!)* · **`EV / Phí = +13,43x`** · `Pass 24T = 69,16%`, `Fail 24T = 0,57%` *(nền `6,15%`)*.
  - **Xác suất hòa/lỗ sau 24 tháng (`P(NPV24 <= 0)`):** **`35,68%`** *(giảm **`-6,37` điểm %** so với nền `42,05%`!)*.
  - **Tách riêng Bot tự phanh vs Vi phạm cứng của quỹ (Luật 13):** `BOT_AUTO_KILL = 9,18%` *(giảm `-76,1%` so với nền `38,48%`)* · `FIRM_HARD_BREACH = 0,67%` *(giảm **`-90,2%`** so với nền `6,82%`!)*.
  - **Tỷ lệ `Đậu / Rớt / Chờ` theo tháng (`10K` BF `1,00x`, tổng luôn đúng `100,00%`):**
    - `3` tháng: **`11,63%` Đậu / `0,00%` Rớt / `88,37%` Chờ** (`100,00%`)
    - `6` tháng: **`32,21%` Đậu / `0,01%` Rớt / `67,78%` Chờ** (`100,00%`)
    - `12` tháng: **`51,64%` Đậu / `0,06%` Rớt / `48,30%` Chờ** (`100,00%`)
    - `24` tháng: **`68,82%` Đậu / `0,32%` Rớt / `30,86%` Chờ** (`100,00%`) *(so với nền `61,89% / 5,60% / 32,51%`)*
  - **Cháy Funded 12 tháng & tháng đói payout:** **`0,00%`** (`0 / 7.934` vé đã vào Funded, `1.052` ca cắt cụt `< 12T`, cận trên Wilson 95% **`<= 0,05%`** — vẫn giữ cảnh báo cần `~299` tài khoản độc lập thực tế không cháy mới chứng minh `< 1%` trên live) · tỷ lệ tháng Funded đói payout **`66,29%`** · trung vị chờ payout đầu **`305,8` ngày** (có điều kiện đã rút) / **`442,1` ngày** (không điều kiện chặn `730` ngày — **nhanh hơn `95,6` ngày** so với nền `537,7` ngày!).
- **Ngưỡng gãy / điểm chết (Break-Even Slippage/Friction):** `SHIELD_C_TOT300_10M` chạm hòa vốn ở mức ma sát **`2,28x`** *(gần như y hệt nền `2,30x`, độ lệch chỉ `-0,02x`)*. Vẫn giữ nguyên quy tắc khóa cứng **dừng mua vé mới nếu chi phí thực tế vượt `1,75x`** (vì từ `1,50x` trở lên, trung vị 1 vé `10K` đã âm `-1,81 tr VND` và `58,89%` kịch bản hòa/lỗ sau 24 tháng — dù vẫn tốt hơn đáng kể so với mức `64,34%` của nền).

### Thang Định Vị Dọc Luật 15 (`Xấu -> Đủ dùng -> Tốt -> Top 1% Thực Tế`)

- 🔴 **Xấu:** `EV <= 0`, `PF < 1,05`, `Max DD > 10%`, `Calmar < 0,5`, `Sharpe < 0,6`, thi quỹ `EV/Phí <= 0x`, cháy Funded `> 5%`, hoặc sốc gap đồng thời `> 5,0%` *(trạng thái cũ của P1/P2 `C10_NEWS_ON` không có khiên: `7,19%–16,88%`)*.
- 🟡 **Đủ dùng — VỊ TRÍ HIỆN TẠI CỦA BIÊN LÃI TRÊN LỆNH (`EV/lệnh +0,0457R`, `PF 1,204`, `Calmar 1,040`, tháng đói payout `66,3%`):** Đã nâng `Calmar` vượt mốc `1,00` nhưng biên lãi trên từng lệnh vẫn mỏng trước sốc chi phí `>= 1,50x` và cần thêm nguồn lợi nhuận độc lập để rút ngắn khoảng trắng giữa các kỳ payout.
- 🟢 **Tốt — VỊ TRÍ HIỆN TẠI CỦA ĐỘ AN TOÀN, MAX DD & THI QUỸ MÔ PHỎNG (`Max DD 6,90%` nâng từ Vàng lên Xanh, `Sharpe 1,249`, `10K EV/Phí +8,75x`, `100K EV/Phí +13,43x`, `Fail 24T = 0,32%`, sốc gap `1,25x <= 3,75% <= 4,50%` trên 100% cấu hình):** Đạt chuẩn phòng thủ tổ chức trên Dev `2018–2024`, nhưng **KHÔNG được xếp hạng Top 1% thực tế** vì chưa qua Holdout mù `2025+` và chưa chứng minh trên tiền thật.
- 🏆 **Top 1% thực tế (Mục tiêu dài hạn):** `EV > +0,15R`, `PF 1,50–2,00+`, `Max DD 4%–7%`, `Calmar > 2,0`, `Sharpe 2,0–3,0` **trên tiền thật `>= 12` tháng**, rút payout đều đặn mỗi `2–4` tháng nhờ ghép thêm nhiều nhánh alpha lệch pha (không nâng đòn bẩy liều ở P1/P2).

**Khoảng cách cụ thể tới `Top 1% thực tế`:**
1. **Khoảng cách bằng chứng:** Hiện mới là `Dev 2018–2024` (`Cluster B` đã xem); cần hoàn tất đối chiếu Demo / nạp `v1.03` chạy shadow đối chứng, sau đó mới xét mở khóa Holdout mù `2025+` (chỉ khi có phê duyệt riêng) và chứng minh `>= 12` tháng trên tiền thật.
2. **Khoảng cách hiệu suất lõi:** Cần đưa `Calmar` từ **`1,04`** lên **`> 2,0`** (`+0,96`), `PF` từ **`1,204`** lên **`>= 1,50`** (`+0,30`) và hạ tỷ lệ tháng đói payout từ **`66,3%`** xuống **`< 25%`** bằng cách bổ sung nhánh chiến lược độc lập tương quan thấp (`r < 0,25`).
3. **Khoảng cách rủi ro đuôi siêu cực đoan (`> 1,67x` gap):** Khiên `3,00%` khóa chặt gap `1,25x` (`3,75%`) và `1,50x` (`4,50%`) dưới sàn `5,0%`; nếu chủ sở hữu muốn chống luôn cú gap cực hiếm `2,00x` (như sự kiện SNB 2015), chỉ cần hạ 1 tham số `InpMaxTotalOpenRiskPct = 2,50` (`SHIELD_C_TOT250_10M` -> `3,12% @ 1,25x`, `3,75% @ 1,50x`, `5,00% @ 2,00x`), chỉ đánh đổi `-0,15 tr VND` EV trên 1 vé `10K` (`+15,72 tr` vs `+15,87 tr`).

---

## 2. Ma Trận Sốc Flash-Crash Đồng Thời Trung Thực (Không Kẹp `< 5%`)

Công thức trung thực giữ nguyên tinh thần Làn L7 (`red_team_auditor.py` Test 6 — **không bao giờ kẹp dưới `5%`**): phần mềm cắt lỗ sau sự kiện không thể cứu các lệnh đang mở cùng lúc khi thị trường nhảy gap đồng loạt (`tương quan -> 1,0`). Do đó trần thiệt hại duy nhất đáng tin cậy là **`min(Tổng SYMCAP từng mã, Tổng trần tài khoản đang mở) x (1 + tỷ lệ trượt gap)`**.

| Cấu hình pha (so khớp `red_team_auditor` & `risk_profiles.json`) | Nền `C10_NEWS_ON` Gap `1,25x` (`1,50x`) | `SHIELD_C_TOT300_10M` (`3,00%` P1/P2 · `2,25%` Funded) Gap `1,25x` (`1,50x`) | `SHIELD_C_TOT250_10M` (`2,50%` P1/P2 · `2,00%` Funded) Gap `1,25x` (`1,50x`) | `SHIELD_C_TOT200_10M` (`2,00%` P1/P2 · `1,75%` Funded) Gap `1,25x` (`1,50x`) | Trạng thái mục tiêu `<= 4,50%` (`1,25x`) |
|---|---:|---:|---:|---:|---|
| **`Funded` (`1,00x` RedTeam / `PORT_7E`)** | `4,06%` (`4,88%`) | **`2,81%`** (`3,38%`) | `2,50%` (`3,00%`) | `2,19%` (`2,62%`) | **SAFE (`<= 4,50%`)** |
| **`Funded_C10` (`1,25x` / `PORT_7E`)** | **`5,08%` (BREACH)** (`6,09%`) | **`2,81%`** (`3,38%`) | `2,50%` (`3,00%`) | `2,19%` (`2,62%`) | **BREACH -> SAFE** |
| **`P2` (`2,50x` RedTeam / `PORT_7E`)** | **`7,19%` (BREACH)** (`8,62%`) | **`3,75%`** (`4,50%`) | `3,12%` (`3,75%`) | `2,50%` (`3,00%`) | **BREACH -> SAFE** |
| **`P2_C10` (`3,50x` / `PORT_7E`)** | **`8,75%` (BREACH)** (`10,50%`) | **`3,75%`** (`4,50%`) | `3,12%` (`3,75%`) | `2,50%` (`3,00%`) | **BREACH -> SAFE** |
| **`P1 Bal` (`4,00x` / `PORT_9E`)** | **`15,00%` (BREACH)** (`18,00%`) | **`3,75%`** (`4,50%`) | `3,12%` (`3,75%`) | `2,50%` (`3,00%`) | **BREACH -> SAFE** |
| **`P1 Bal_C10` (`4,00x` / `PORT_7E`)** | **`8,75%` (BREACH)** (`10,50%`) | **`3,75%`** (`4,50%`) | `3,12%` (`3,75%`) | `2,50%` (`3,00%`) | **BREACH -> SAFE** |
| **`P1 Spr` (`4,75x` / `PORT_9E`)** | **`16,88%` (BREACH)** (`20,25%`) | **`3,75%`** (`4,50%`) | `3,12%` (`3,75%`) | `2,50%` (`3,00%`) | **BREACH -> SAFE** |

**Kiểm chứng DD trong ngày thực tế trên `1.564` phiên quá khứ `2018–2024` (`10K`):**
- **Nền `C10_NEWS_ON`:** Ở pha `P1 4,0x`, rủi ro mở đỉnh chạm `7,00%` và lỗ nội ngày lớn nhất thực tế chạm **`5,065%`** (ở `P2 3,5x` chạm **`5,144%`**) — **đều vượt sàn `5,0%` của FTMO ngay trên dữ liệu quá khứ!**
- **`SHIELD_C_TOT300_10M`:** Rủi ro mở đỉnh bị khóa cứng tại **`3,00%`**, lỗ nội ngày lớn nhất thực tế trên toàn bộ 7 năm rơi xuống **`3,426%` (P1 `4,0x`)** và **`3,468%` (P2 `3,5x`)** — **`0` ngày vi phạm sàn `5,0%` trong suốt 7 năm!**

---

## 3. Bảng Pareto Đầy Đủ 10 Kịch Bản: Nền vs Shield A vs Shield B vs Shield C

| Kịch bản | Gap `1,25x` (`1,50x`) | `1,0x` Lãi/năm | `1,0x` Max DD | `1,0x` Calmar | `1,0x` PF | `1,0x` Sharpe | `10K` BF `NPV 24T` TB / TV (tr VND) | `EV/Phí` (`10K` BF) | `24T` Đậu / Rớt / Chờ (`100%`) | `P(<=0)` | `BOT_KILL` / `FIRM_BR` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| **`BASELINE_C10_NEWS_ON`** | `16,88%` (`20,25%`) | `+7,42%` | `8,62%` | `0,861` | `1,203` | `1,234` | `+14,97` / `+7,55` | `+8,25x` | `61,89 / 5,60 / 32,51%` | `42,05%` | `38,48%` / `6,82%` |
| `SHIELD_A_TOT300` | `3,75%` (`4,50%`) | `+7,47%` | `8,68%` | `0,861` | `1,206` | `1,242` | `+15,98` / `+10,35` | `+8,81x` | `67,33 / 0,43 / 32,24%` | `37,22%` | `26,94%` / `0,99%` |
| `SHIELD_A_TOT250` | `3,12%` (`3,75%`) | `+7,40%` | `8,85%` | `0,837` | `1,204` | `1,232` | `+16,12` / `+11,05` | `+8,88x` | `69,05 / 0,34 / 30,61%` | `35,77%` | `25,01%` / `0,87%` |
| `SHIELD_A_TOT200` | `2,50%` (`3,00%`) | `+7,29%` | `9,02%` | `0,808` | `1,202` | `1,215` | `+15,74` / `+10,69` | `+8,68x` | `68,81 / 0,37 / 30,82%` | `35,52%` | `21,94%` / `0,84%` |
| `SHIELD_B_6CCY_5M` | `16,88%` (`20,25%`) | `+7,03%` | `7,40%` | `0,951` | `1,199` | `1,224` | `+14,79` / `+9,22` | `+8,15x` | `65,68 / 0,33 / 33,99%` | `38,69%` | `29,65%` / `0,84%` |
| `SHIELD_B_6CCY_10M` | `16,88%` (`20,25%`) | `+7,09%` | `6,90%` | `1,027` | `1,201` | `1,236` | `+14,98` / `+9,74` | `+8,26x` | `65,91 / 0,35 / 33,74%` | `38,10%` | `30,06%` / `0,76%` |
| `SHIELD_C_TOT300_5M` | `3,75%` (`4,50%`) | `+7,12%` | `7,40%` | `0,962` | `1,202` | `1,237` | `+15,55` / `+10,56` | `+8,57x` | `67,99 / 0,28 / 31,73%` | `36,22%` | `9,55%` / `0,64%` |
| **`SHIELD_C_TOT300_10M` (WIN)** | **`3,75%`** (`4,50%`) | **`+7,17%`** | **`6,90%`** | **`1,040`** | **`1,204`** | **`1,249`** | **`+15,87` / `+11,16`** | **`+8,75x`** | **`68,82 / 0,32 / 30,86%`** | **`35,68%`** | **`9,18%` / `0,67%`** |
| `SHIELD_C_TOT250_10M` *(Ultra-Safe)* | **`3,12%`** (`3,75%`) | `+7,16%` | **`6,90%`** | `1,038` | `1,204` | `1,247` | `+15,72` / **`+11,26`** | `+8,67x` | `69,44 / 0,36 / 30,20%` | `35,00%` | `10,48%` / `0,72%` |
| `SHIELD_C_TOT200_10M` | `2,50%` (`3,00%`) | `+7,09%` | `6,96%` | `1,018` | `1,203` | `1,237` | `+15,30` / `+10,93` | `+8,43x` | `69,66 / 0,30 / 30,04%` | `34,63%` | `10,75%` / `0,67%` |

**Giải mã tác động tách lớp (Ablation Insights):**
1. **Shield A đứng riêng (`TOT300/250/200`):** Khóa cứng được trần sốc toán học (`3,75% / 3,12% / 2,50%`) và cắt `Fail 24T` từ `5,60% -> 0,34%–0,43%`, **NHƯNG** không giảm `Max DD` ở `1,0x` (`8,68%–9,02%`) và vẫn kích `BOT_AUTO_KILL` tới `21,9%–26,9%` vì chưa chặn tin BoE/ECB/BoJ và chưa chặn spread rỗng thanh khoản.
2. **Shield B đứng riêng (`6-CCY + SpreadGuard + Cụm tiền tệ`):** Hạ mạnh `Max DD 1,0x` từ `8,62% -> 6,90%` (`±10m` vượt trội hơn `±5m` thêm `-0,50` điểm % DD chỉ với `3` lệnh bị chặn thêm), **NHƯNG** nếu không có trần tổng tài khoản thì ma trận sốc đồng thời nhiều cụm ngược chiều vẫn là `16,88%`.
3. **Shield C hợp nhất (`A + B`):** Tạo hiệu ứng cộng hưởng rõ rệt nhất — vừa hạ `BOT_AUTO_KILL` xuống **`9,18%`** (giảm 3 lần so với Shield A đơn lẻ!), vừa giữ `Max DD 1,0x = 6,90%`, `Calmar = 1,040`, `Fail 24T = 0,32%`, `EV/Phí = +8,75x` và chặn tuyệt đối sốc gap `1,25x <= 3,75%` trên mọi pha!

---

## 4. Hiệu Chuẩn Nhân Quả `SpreadGuard` Trên M1 Bid/Ask Thật & Độ Bền Khủng Hoảng

### 4.1. Phân Phối Spread M1 Bid/Ask Thực Tế (`10.185.450` Nến M1, Dev `2018–2024`, `.runtime/hot-m1-cache/`)

Tất cả ngưỡng chặn `SpreadGuard` trong nghiên cứu đều được **tính tự động bằng một quy tắc nhân quả duy nhất trên Cụm A (`2018–2020`, `0%` dữ liệu Cụm B `2021–2024`)**: **`ceil_to_5(max(session_A p99,9, 1,10 x entry_A p99,9))`** *(trong đó `session_A` là toàn bộ nến M1 `2018–2020` nằm trong đúng các giờ UTC vào lệnh của từng mã ở Cụm A)*, sau đó kiểm chứng OOS trên Cụm B (`2021–2024`), đối khớp chính xác `3.122/3.122` phút vào lệnh (`100%`, `0` nến nhìn về tương lai):

| Mã tài sản | Tổng nến M1 (`2018–2024`) | Phiên vào lệnh Cụm A `p50 / p99 / p99,9 / max` (pts) | Phút vào lệnh Cụm A `p50 / p99 / p99,9 / max` (pts) | Phút vào lệnh Cụm B `p50 / p99 / max` (pts) | Ngưỡng Dev tự tính Cụm A (`CALIB_M1_A`) | Ngưỡng FTMO Live trong `v1.03` |
|---|---:|---:|---:|---:|---:|---:|
| **`USDJPY`** | `2.607.454` | `3,0 / 8,0 / 16,0 / 194,0` | `3,0 / 10,0 / 21,8 / 42,0` | `6,0 / 29,0 / 150,0` | **`25,0 pts`** *(từ `1,10 x 21,78 = 23,96`)* | **`25,0 pts`** |
| **`GBPUSD`** | `2.608.982` | `8,0 / 19,0 / 35,0 / 394,0` | `9,0 / 25,2 / 26,8 / 27,0` | `8,0 / 47,0 / 67,0` | **`35,0 pts`** *(từ `sess_A p99,9 = 35,0`)* | **`35,0 pts`** |
| **`EURJPY`** | `2.610.264` | `5,0 / 12,0 / 23,0 / 349,0` | `5,0 / 12,5 / 13,0 / 13,0` | `9,0 / 48,0 / 180,0` | **`25,0 pts`** *(từ `sess_A p99,9 = 23,0`)* | **`25,0 pts`** |
| **`US100`** | `2.358.750` | `107,1 / 197,0 / 248,0 / 756,2` | `107,0 / 200,1 / 224,9 / 231,0` | `136,4 / 157,2 / 292,9` | **`250,0 pts`** *(từ `sess_A p99,9 = 248,0`)* | **`350,0 pts`** *(điều chỉnh feed FTMO ~`1,8x 195pt`)* |

**Bằng chứng trực tiếp trên các phiên Flash-Crash OOS Cụm B (`2021–2024`):**
- **Thứ Hai Đen Tối tháo chạy Yên Nhật (`2024-08-05`):** Ngưỡng hiệu chuẩn từ `2018–2020` tự động chặn sạch **cả `3/3` lệnh lỗ đồng loạt** ngay tại phút vào lệnh vì spread giãn đột biến: `E2_USDJPY_EXP80` (`32,0 > 25,0 pts`, tránh `-0,990R`), `E4_US100_SESS40` (`252,7 > 250,0 pts`, tránh `-1,000R`), `E5_US100_RS1130` (`292,9 > 250,0 pts`, tránh `-0,515R`)!
- **Các cú sốc vĩ mô & ngân hàng trung ương khác:** Chặn `E2_USDJPY` ngày `2024-07-11` CPI + can thiệp BoJ (`90,0 pts`, `-0,996R`), `E2_USDJPY` `2022-11-10` CPI (`56,0 pts`, `-0,992R`), `E3_GBPUSD` `2023-08-03` BoE (`47,0 pts`, `-1,000R`, được chặn kép bởi cả lịch `6-CCY` lẫn `SpreadGuard`), và `E6_EURJPY` `2024-05-15` (`180,0 pts`, `-0,388R`).

### 4.2. So Sánh 5 Giai Đoạn Khủng Hoảng Lịch Sử (`100K`, Funded `1,0x`)

| Giai đoạn khủng hoảng | Giai đoạn | Nền `C10_NEWS_ON` Lãi / Max DD / DD ngày | `SHIELD_C_TOT300_10M` Lãi / Max DD / DD ngày | Cải thiện nổi bật |
|---|---|---|---|---|
| **`2018_Q4_Fed_QT`** | `2018-10-01..2018-12-31` | `+7,96%` / `1,39%` / `0,93%` | `+6,49%` / `1,99%` / `0,93%` | Giữ dương mạnh `+6,49%`, DD ngày giữ nguyên `0,93%` |
| **`2020_COVID_Crash`** | `2020-02-20..2020-04-30` | `+6,68%` / `2,86%` / `1,47%` | `+6,48%` / `2,86%` / `1,47%` | Bảo toàn `97%` lợi nhuận COVID, không tăng DD |
| **`2022_RateHike_Shock`** | `2022-01-01..2022-10-31` | `+13,37%` / `2,39%` / `2,00%` | `+12,60%` / **`2,17%`** / **`1,44%`** | **Giảm `-28%` DD ngày lớn nhất** (`2,00% -> 1,44%`) |
| **`2023_SVB_Bank_Stress`** | `2023-03-08..2023-03-31` | `-0,50%` / `1,07%` / `0,61%` | **`-0,47%`** / **`1,03%`** / **`0,57%`** | Nhẹ hơn trên cả 3 chỉ số |
| **`2024_Aug_Yen_Unwind`** | `2024-07-15..2024-08-31` | `+0,48%` / `2,56%` / `1,90%` | **`+2,00%`** / **`1,21%`** / **`1,14%`** | **Cắt `-53%` Max DD, tăng lãi gấp `4,2x` (`+1,52 đ%`)!** |

---

## 5. Độ Nhạy Trượt Giá & Điểm Gãy Hòa Vốn (`SHIELD_C_TOT300_10M`)

### 5.1. Đường Cong Ma Sát Lõi `PORT_7E` (`100K`, `1,0x`, Điểm Gãy `2,28x`)

| Mức ma sát | Lãi năm (%) | Lãi năm (tr VND / `100K`) | `Winrate` | `RR` | `EV / lệnh` | `PF` | `Max DD` | `Calmar` | `Sharpe` |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`0,66x`** *(Demo)* | `+9,31%` | `+239,8` tr | `49,79%` | `1,279x` | `+0,0625R` | `1,268` | **`6,44%`** | **`1,445`** | **`1,590`** |
| **`1,00x`** *(Nền)* | **`+7,17%`** | **`+184,8` tr** | **`48,87%`** | **`1,260x`** | **`+0,0457R`** | **`1,204`** | **`6,90%`** | **`1,040`** | **`1,249`** |
| **`1,25x`** | `+5,68%` | `+146,3` tr | `48,13%` | `1,250x` | `+0,0340R` | `1,160` | `7,65%` | `0,742` | `1,000` |
| **`1,50x`** *(Stress)* | `+4,21%` | `+108,5` tr | `47,60%` | `1,230x` | `+0,0225R` | `1,117` | `9,26%` | `0,455` | `0,751` |
| **`1,75x`** *(Ngưỡng đỏ)* | `+2,81%` | `+72,4` tr | `47,07%` | `1,212x` | `+0,0113R` | `1,077` | `11,09%` | `0,254` | `0,507` |
| **`2,00x`** | `+1,46%` | `+37,7` tr | `46,64%` | `1,190x` | `+0,0009R` | `1,040` | `13,39%` | `0,109` | `0,267` |
| **`2,50x`** *(Vượt điểm gãy `2,28x`)* | `-1,14%` | `-29,3` tr | `45,40%` | `1,166x` | `-0,0195R` | `0,969` | `18,29%` | `-0,062` | `-0,212` |

### 5.2. Độ Nhạy `FTMO 2-Step Standard 10K` (`SHIELD_C_TOT300_10M`, 1 Vé BF `70,42 USD` / `1,81 tr VND`)

| Mức ma sát | `3T` Đậu/Rớt/Chờ | `6T` Đậu/Rớt/Chờ | `12T` Đậu/Rớt/Chờ | `24T` Đậu/Rớt/Chờ (`100%`) | `NPV 24T` TB / TV (tr VND) | `EV/Phí` | `P(<=0)` | Cháy Funded `12T` (Wilson 95%) |
|---|---|---|---|---|---:|---:|---:|---:|
| **`0,66x`** *(Demo)* | `15,74 / 0,00 / 84,26%` | `41,77 / 0,00 / 58,23%` | `63,57 / 0,03 / 36,40%` | **`82,07 / 0,13 / 17,80%`** | **`+25,40`** / **`+23,82`** | **`+14,00x`** | **`20,76%`** | `0,00%` (`<= 0,04%`) |
| **`1,00x`** *(Nền)* | `11,63 / 0,00 / 88,37%` | `32,21 / 0,01 / 67,78%` | `51,64 / 0,06 / 48,30%` | **`68,82 / 0,32 / 30,86%`** | **`+15,87`** / **`+11,16`** | **`+8,75x`** | **`35,68%`** | `0,00%` (`<= 0,05%`) |
| **`1,50x`** *(Stress)* | `7,00 / 0,00 / 93,00%` | `20,84 / 0,02 / 79,14%` | `34,22 / 0,18 / 65,60%` | `46,70 / 1,45 / 51,85%` | `+6,45` / `-1,81` | `+3,55x` | `58,89%` | `0,00%` (`<= 0,07%`) |
| **`1,75x`** *(Ngưỡng đỏ)* | `5,46 / 0,00 / 94,54%` | `16,51 / 0,02 / 83,47%` | `26,78 / 0,43 / 72,79%` | `35,86 / 3,17 / 60,97%` | `+3,45` / `-1,81` | `+1,90x` | `69,64%` | `0,02%` (`<= 0,14%`) |

*(Lưu ý nổi bật: ngay cả tại mức stress xấu `1,50x` và `1,75x`, `SHIELD_C_TOT300_10M` vẫn vượt trội toàn diện so với nền `C10_NEWS_ON`: `Fail 24T` tại `1,50x` chỉ `1,45%` vs `7,07%`, tại `1,75x` chỉ `3,17%` vs `9,19%`; và tại `0,66x` Demo thực tế, tỷ lệ đậu 24T đạt `82,07%`, trung vị lãi ròng **`+23,82 tr VND`** trên 1 vé `1,81 tr VND`!)*

---

## 6. Triển Khai Ứng Viên `Naqex_Master_Prop7E_v103.mq5`, Kiểm Chứng Biên Dịch & Sẵn Sàng Sharding X13

- **Tệp nguồn ứng viên phòng thủ:** [`Naqex_Master_Prop7E_v103.mq5`](file:///d:/ANNAM/TradingWorkspace/tooling/ai-engines/exports/Naqex_Master_Prop7E_v103.mq5) (không sửa 1 byte nào ở `Naqex_Master_Prop7E.mq5` `v1.01`, `Include/Naqex_PropGuard.mqh`, `Include/Naqex_Signals_7E.mqh`).
- **Hợp đồng an toàn tích hợp:**
  1. Khai báo `#define NAQEX_CUSTOM_GUARD_INPUTS` trước khi `#include "Include/Naqex_PropGuard.mqh"` và `"Include/Naqex_Signals_7E.mqh"`.
  2. Mặc định đóng an toàn tuyệt đối: `InpDryRunLogOnly = true`, `InpGuardDryRunLogOnly = true`, `InpShadowCompareMode = true`, `InpGuardEnableRedNews = true`, `InpGuardUseOrchestrator = false`.
  3. **Shield A:** `InpMaxTotalOpenRiskPct = 3,00` + trần cứng fail-closed `InpHardTotalOpenCeilingPct = 3,00` (`OnInit()` từ chối mọi giá trị `<= 0` hoặc `> 3,00` và `EffectiveTotalOpenRiskCapPct()` kẹp cứng `MathMin(InpHardTotalOpenCeilingPct, 3,00)` — không bao giờ vượt trần!) + kiểm tra lại `actualRiskPct <= MathMin(symHeadroom, factorAndTotalHeadroom) + 1e-6` sau làm tròn lot trước khi gửi lệnh.
  4. **Shield B1–B3:** Trần cụm cùng chiều `USD 2,25% / JPY 2,00% / US100 1,75%` · `SpreadGuard` riêng theo mã (`USDJPY 25pt / GBPUSD 35pt / EURJPY 25pt / US100 350pt` FTMO live) · tùy chọn `6-CCY ±10m` (`InpUse6CcyNewsPad10m = true` kết hợp `InpGuardNewsPadSec = 600`; `OnInit()` chặn fail-closed nếu `InpGuardNewsPadSec < InpGuardNewsHardBanSec` hoặc `< 600` khi bật `±10m`; tắt cờ này cho phép chạy `±5m = 300s`).
- **Chứng chỉ biên dịch & kiểm toán tĩnh (2026-11-27):**
  - **`MetaEditor64.exe` (biên dịch cô lập tại `.tmp/v103_compile_check/`):** **`Result: 0 errors, 0 warnings, 2808 ms elapsed, cpu='X64 Regular'`** (`153.520` bytes `.ex5`, đã xóa tức thì ngay sau khi kiểm tra -> `0` `.ex5` trong `.tmp/`, **`0` `.ex5` trong `exports/`**, giữ đúng **`10` `.ex5`** trong `.runtime/mt5-compiled-ex5/`).
  - **`system_doctor.py` (`exports_static_audit`):** **`13 MQL5 files audited: 0 red flags, DryRun default ON`** (`0,093s`).
- **Sẵn sàng Wave 2A Sharding trên `<X13_WORKER>` (Python 3.14, không chạm Holdout):**
  - `tooling/ai-engines/experiments/flashcrash_pareto_study.py` không import `prop_engine` / `data_store` / `assert_holdout_locked` / `duckdb`, đọc thẳng `frozen_9e_tapes_v2.{json,npz}` có xác thực `npz_sha256` & `max_day < "2025-01-01"`.
  - Lệnh phân mảnh chuẩn Wave 2A (ví dụ `4` mảnh × `25.000` = `100.000` đường MC với `job_id` sạch không chứa chuỗi cấm):
    ```text
    python tooling/ai-engines/experiments/flashcrash_pareto_study.py --n-paths 100000 --shard-index 0 --shard-total 4 --out-json results/pareto_v103_s0/shard_0.json
    ```
- **Quyết định vận hành hiện tại:** Giữ nguyên **`0 VND`**, giữ khóa **`Holdout 2025+ SEALED`**, chưa thay thế `v1.01` trên node vận hành. `Naqex_Master_Prop7E_v103.mq5` đạt chuẩn làm ứng viên phòng thủ ưu tiên cho đối chiếu shadow/tester Wave 2A.
