---
doc_type: evergreen
domain: knowledge
topic: darwinex-zero-7e-quantitative-fit-2026
updated_utc: 2026-11-25
holdout_rows_analysed: 0
order_send_count: 0
sources:
  - "T1 (Chính thức 2026): Darwinex Zero Risk Engine (3.25%-6.50% mVaR), DarwinIA Silver/Gold & 15% HWM (darwinexzero.com, darwinex.com — FCA FRN 586466)"
  - "T1 (Mô phỏng nội bộ < 2025-01-01): N = 5.000 đường bootstrap khối 7 ngày lịch trên băng Dev PORT_7E 2018-2024 & Own-Book 75% SGOV / 25% B06+B02 (2019-2024), holdout_rows_analysed = 0, OrderSend = 0"
  - "T1 (Liên kết nội bộ): prop-firm-2026-landscape-and-multi-firm-portfolio.md, alpha-hypothesis-ledger.md"
---

# Mô phỏng Định lượng `PORT_7E` trên `Darwinex Zero` (`36–60` Tháng) & Danh mục Đa Quỹ Hợp nhất (`2026`)

> **Kỷ luật Bằng chứng & Ranh giới Bảo mật:** Toàn bộ mô phỏng chạy **100% trên dữ liệu Phát triển niêm phong `< 2025-01-01`** (`assert max_date < 2025-01-01`, `holdout_rows_analysed = 0`, `OrderSend = 0`), **`N = 5.000` kịch bản Monte Carlo khối `7` ngày lịch thật** ở `3` mức ma sát (`1,00× / 1,25× / 1,50×`). Tài liệu công khai Layer 1 chỉ trình bày kết quả tổng hợp & quy tắc vận hành, **không tiết lộ công thức riêng tư tại Layer 2**.

## Bảng Kết luận Nhanh (Executive Summary)

| Hạng mục kiểm định (`N = 5.000` đường, `1,065 USD/EUR`, `25.500 VND/USD`) | Mức `1,00×` (Chuẩn) | Mức `1,25×` (Stress vừa) | Mức `1,50×` (Stress nặng) | Ý nghĩa Quyết định |
|---|---:|---:|---:|---|
| **1. Darwinex Zero Độc lập `36` tháng (`35 EUR/th`, `Silver Floor` -> `Silver+Gold`)** | **`+1.906` -> `+3.307 EUR`** *(TB `+3.054..+5.052 EUR`)* | **`+856` -> `+1.507 EUR`** *(TB `+1.894..+3.274 EUR`)* | `+26` -> `+206 EUR` *(gói `45 EUR`: âm `-164..-344 EUR`)* | **+EV rõ ở `<= 1,25×`**; biên độ mỏng nếu trượt giá `>= 1,50×` |
| **2. Xác suất Lãi ròng `36t` / `60t` & Tháng Hòa vốn Trung vị** | `76%–80%` / `89%–94%` · **Tháng `14`** | `65%–68%` / `78%–85%` · **Tháng `18`** | `51%–54%` / `62%–70%` · Tháng `24–25` | Cần kiên nhẫn **ủ vốn `12–18` tháng** trước khi có dòng tiền đều |
| **3. Gộp `60` tháng (`Hybrid 500 Prop + 5K OB`: `FTMO + 75/25` -> `+DZ M6`)** | `11.475` -> **`15.321–18.993 USD`** (`+34%..+66%`, `MDD 5,2%`) | `8.876` -> **`10.765–12.716 USD`** (`+21%..+43%`, `MDD 5,8%`) | `7.768` -> **`8.158–8.889 USD`** (`+5%..+14%`, `MDD 6,8%`) | **Tăng mạnh trung vị 5 năm** mà `MaxDD` toàn rổ vẫn chỉ `~5%–7%` |
| **4. Stress Sập Đối tác (`FTMO` đóng băng ở Tháng `30` — Không DZ vs Có DZ)** | `7.604` -> **`10.990–14.541 USD`** (**`+45%..+91%`**) | `7.366` -> **`8.965–10.859 USD`** (**`+22%..+47%`**) | `7.178` -> **`7.436–8.142 USD`** (`+4%..+13%`) | **Khiên bảo hiểm đối tác thực thụ** tách khỏi rủi ro CFD prop |

---

## 1. Thiết kế Mô phỏng Chống Thổi Phồng (`T1` Quy tắc Darwinex + Băng Dev `2018–2024`)

Để tránh ảo giác lợi nhuận từ các giả định lạc quan, mô hình áp dụng `5` chốt bảo thủ:
1. **Băng lợi suất `PORT_7E` thực tế `2018–2024` (`2.556` ngày lịch, giữ nguyên khóa tin đỏ `±5m`):** `1,00×` đạt `CAGR +7,16%`, `Vol 6,06%`, `Sharpe 1,17`, `MaxDD 7,48%`; `1,25×` còn `+5,72%` (`Sharpe 0,96`); `1,50×` còn `+4,14%` (`Sharpe 0,72`).
2. **Động cơ Rủi ro VaR Nhân quả ([darwinexzero.com](https://www.darwinexzero.com)):** Co giãn đòn bẩy theo biến động `90` ngày quá khứ hướng tới **VaR tháng `95%` = `5,50%`** (nằm giữa dải `3,25%–6,50%`, giới hạn `[0,5×..2,5×]`; có bảng độ nhạy ở mức `6,50%`), trừ thêm **`0,60%/năm`** phí sai lệch khớp DARWIN (*divergence drag*).
3. **Tách hai kịch bản phân bổ minh bạch (`0` giả định vốn nhà đầu tư ngoài):**
   - **`Silver Floor` (Phi cạnh tranh — Sàn cứng):** Chỉ tính **DarwinIA SILVER** (tháng 1 hiệu chuẩn `0` vốn; từ tháng 2 đạt Rating `>= 75` từ `22%` lãi `1t` + `67%` lãi `6t` + `11%` DD ngày `6t` nhận chắc chắn `30.000 EUR` trong `3` tháng, bậc tối đa khóa ở `125.000 EUR`).
   - **`Silver + Gold` (Cận thực tế):** Cổng **DarwinIA GOLD** kiểm tra bằng **MaxDD ngày thật** (`> 8` tháng lịch sử, lãi `1–4` năm vượt `20%–35%` và `Lãi / Daily_MDD > 2,5`), đồng thời chỉ cấp vốn Gold (`50K–250K EUR`, `6` tháng) ở những tháng đạt **`r_1m >= +2,5%`** (phản ánh tính cạnh tranh bảng xếp hạng tháng của Gold), khóa trần tổng AUM cộng dồn **`500.000 EUR`**.
4. **Chi phí đầy đủ cho cư dân Việt Nam:** Phí hiệu suất `15%` theo *High-Water Mark* trả từng quý / khi đáo hạn lô, **trừ `2,5%` phí điện SWIFT + ngân hàng VN** (`0%` phí phía Darwinex), kiểm đủ cả gói trả tháng **`45 EUR/tháng`** (`540 EUR/năm`) và gói năm **`35 EUR/tháng`** (`420 EUR/năm`, [darwinex.com](https://www.darwinex.com)).

---

## 2. Kết quả `PORT_7E` Độc lập trên `Darwinex Zero` (`12 / 24 / 36 / 60` Tháng)

| Ma sát & Cấu hình (`N = 5.000` đường, `EUR`) | `M12` TV | `M24` TV | **`M36` Trung vị (`USD`)** | **`M36` Trung bình (`USD`)** | **`M36` `[P25 ; P75]` (`EUR`)** | `P(M36>0)` | `M60` TV (`P>0`) | Hòa vốn (TV toàn mẫu) | AUM TB `36t` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`1,00×` · `Silver Floor` · `45 EUR`** | `-347` | `+456` | **`+1.536`** (`+1.636`) | `+2.684` (`+2.858`) | `[-282 ; +4.535]` | `70,4%` | `+3.943` (`83,6%`) | **`Tháng 16`** | `62.821 EUR` |
| **`1,00×` · `Silver Floor` · `35 EUR`** | `-217` | `+706` | **`+1.906`** (`+2.030`) | `+3.054` (`+3.253`) | `[+88 ; +4.905]` | **`76,4%`** | **`+4.543`** (`88,6%`) | **`Tháng 14`** | `62.821 EUR` |
| **`1,00×` · `Silver+Gold` · `45 EUR`** | `-347` | `+611` | **`+2.937`** (`+3.128`) | `+4.682` (`+4.986`) | `[+22 ; +7.660]` | `75,2%` | `+10.145` (`91,2%`) | **`Tháng 16`** | `95.449 EUR` |
| **`1,00×` · `Silver+Gold` · `35 EUR`** | `-217` | `+861` | **`+3.307`** (`+3.522`) | **`+5.052`** (`+5.380`) | `[+392 ; +8.030]` | **`79,5%`** | **`+10.745`** (`93,6%`) | **`Tháng 14`** | `95.449 EUR` |
| *`1,00×` · Độ nhạy `mVaR 6,5%` · `35 EUR`* | `-129` | `+1.508` | `+5.039` (`+5.367`) | `+7.215` (`+7.684`) | `[+1.026 ; +11.323]` | `84,0%` | `+15.285` (`95,7%`) | `Tháng 13` | `112.586 EUR` |
| **`1,25×` · `Silver Floor` · `35 EUR`** | `-355` | `+131` | **`+856`** (`+912`) | `+1.894` (`+2.017`) | `[-506 ; +3.276]` | `65,0%` | `+2.588` (`77,9%`) | **`Tháng 18`** | `51.758 EUR` |
| **`1,25×` · `Silver+Gold` · `35 EUR`** | `-355` | `+174` | **`+1.507`** (`+1.605`) | `+3.274` (`+3.487`) | `[-423 ; +5.321]` | **`68,1%`** | **`+6.498`** (`85,1%`) | **`Tháng 18`** | `77.243 EUR` |
| **`1,25×` · `Silver+Gold` · `45 EUR`** | `-485` | `-76` | `+1.137` (`+1.211`) | `+2.904` (`+3.093`) | `[-793 ; +4.951]` | `63,0%` | `+5.898` (`81,0%`) | `Tháng 20` | `77.243 EUR` |
| **`1,50×` · `Silver Floor` · `35 EUR`** | `-455` | `-308` | `+26` (`+28`) | `+920` (`+980`) | `[-912 ; +1.833]` | `50,5%` | `+926` (`62,2%`) | `Tháng 25` | `41.055 EUR` |
| **`1,50×` · `Silver+Gold` · `35 EUR`** | `-455` | `-294` | **`+206`** (`+219`) | `+1.755` (`+1.869`) | `[-898 ; +2.912]` | `53,5%` | `+2.718` (`70,4%`) | `Tháng 24` | `59.128 EUR` |
| **`1,50×` · `Silver+Gold` · `45 EUR`** | `-585` | `-544` | **`-164`** (`-175`) | `+1.385` (`+1.475`) | `[-1.268 ; +2.542]` | `47,6%` | `+2.118` (`64,9%`) | `Tháng 29` | `59.128 EUR` |

**Ba quy luật định lượng rút ra từ Bảng 2:**
1. **Giai đoạn ủ vốn là thực tế toán học không thể rút gọn:** Cả `100%` kịch bản đều **âm nhẹ ở Tháng `12` (`-217 .. -585 EUR`)** vì cần `6–9` tháng xây điểm `Rating >= 75` và chờ chu kỳ trả thưởng quý. Điểm hòa vốn trung vị rơi vào **Tháng `14–16` (`1,00×`)** và **Tháng `18–20` (`1,25×`)**.
2. **Đòn bẩy cộng dồn cực mạnh từ Năm `3` đến Năm `5`:** Do **không bao giờ bị cháy ở `-10%` Static DD**, tài khoản sống sót `100%` qua mọi đợt sụt giảm của `7E` (`DARWIN MaxDD` trung vị `13,6%–15,0%` ở `mVaR 5,5%`), giúp trung vị `60` tháng nhảy lên **`+4.543 .. +10.745 EUR` (`1,00×`)** và **`+2.588 .. +6.498 EUR` (`1,25×`)** — chưa tính vốn nhà đầu tư thực ngoài sàn!
3. **Ngưỡng cắt ma sát `1,25×` & lợi thế gói năm `35 EUR/tháng`:** Tại `1,50×`, gói `45 EUR/tháng` âm trung vị suốt `36` tháng (`-164 .. -344 EUR`), trong khi gói năm `35 EUR/tháng` (`420 EUR/năm`) tiết kiệm `120 EUR/năm` giúp nâng `P(M36 > 0)` thêm `+4%..+7%` ở mọi kịch bản.

---

## 3. Danh mục Đa Quỹ Hợp nhất `60` Tháng (`FTMO + Darwinex Zero + 75% SGOV / 25% B06+B02`)

Chạy đồng bộ ngày lịch thật `2019-03-01..2024-12-31` (`1.800` ngày = `60` tháng, `5.000` đường khớp cặp) trên hai cấu hình vốn khởi điểm: **`Hybrid` (`500 USD Prop + 5.000 USD Own-Book`)** và **`Lean` (`500 USD Prop + 0 USD Own-Book`)**. `Darwinex Zero` chỉ bật từ **Tháng `6+`** khi `FTMO` đã sinh lãi dư (tối thiểu `250 USD` cho `Hybrid`, `600 USD` cho `Lean`), trả thuê bao từ Own-Book và đổ toàn bộ phí hiệu suất `15%` thẳng về Own-Book (`75% SGOV + 25% B06+B02`, trần `CEX <= 25%`):

| Ma sát | Danh mục `60` Tháng (`N = 5.000` đường khớp cặp) | `M36` TV (USD) | **`M60` TV (USD / tr VND)** | `M60` TB (USD) | Đóng góp DZ `60t` (TV / TB) | `Sharpe` Rổ (TV) | `MaxDD` Rổ (TV / `P90`) |
|---|---|---:|---:|---:|---:|---:|---:|
| **`1,00×`** | `Hybrid (500+5K)` · FTMO + `100% SGOV` | `6.706` | `10.526` (`268,4 tr`) | `15.874` | `0 / 0` | `1,49` | `4,0%` (`6,3%`) |
| **`1,00×`** | `Hybrid (500+5K)` · FTMO + `75% SGOV / 25% B06+B02` | `7.216` | `11.475` (`292,6 tr`) | `16.978` | `0 / 0` | **`1,79`** | **`4,0%`** (`6,1%`) |
| **`1,00×`** | **`Hybrid` · Full + `DZ 35 EUR` (`Silver Floor`, M9)** | `8.206` | **`15.321` (`390,7 tr`)** | `21.299` | `+2.839 / +3.962` | `1,46` | `5,4%` (`10,1%`) |
| **`1,00×`** | **`Hybrid` · Full + `DZ 35 EUR` (`Silver+Gold`, M9)** | `8.368` | **`18.993` (`484,3 tr`)** | **`25.511`** | **`+6.099 / +7.945`** | `1,41` | `5,2%` (`10,0%`) |
| **`1,00×`** | *Stress `FTMO` đóng băng Tháng `30`* (Không DZ vs Có DZ) | `6.909` vs `7.947` | `7.604` vs **`10.990–14.541`** | `8.327` vs `16.860` | **`+2.839 .. +6.099`** | `1,71` vs `1,21` | `2,9%` vs `4,9%` |
| **`1,25×`** | `Hybrid (500+5K)` · FTMO + `75/25` | `6.862` | `8.876` (`226,3 tr`) | `12.548` | `0 / 0` | `1,74` | `3,5%` (`5,9%`) |
| **`1,25×`** | **`Hybrid` · Full + `DZ 35 EUR` (`Silver` -> `Silver+Gold`)** | `7.013–7.065` | **`10.765–12.716` (`275–324 tr`)** | `15.158–18.006` | `+1.344 .. +3.163` | `1,16–1,20` | `5,8%–5,9%` (`12,0%`) |
| **`1,50×`** | `Hybrid (500+5K)` · FTMO + `75/25` -> `+DZ 35 EUR` | `6.647` -> `6.280` | `7.768` -> **`8.158–8.889`** | `9.729` -> `12.615` | `+205 .. +800` | `1,70` -> `0,90` | `3,2%` -> `6,8%` |
| **`1,00×`** | `Lean (500+0)` · FTMO + `75/25` -> `+DZ 35 EUR` *(M29)* | `1.360` -> `1.095` | `4.974` -> **`5.592–5.839`** | `10.522` -> `13.647` | `+191 .. +362` | `1,16` -> `1,07` | `21,0%` -> `23,4%` |
| **`1,25×`** | `Lean (500+0)` · FTMO + `75/25` -> `+DZ 35 EUR` *(M32)* | `993` -> `924` | `2.383` -> **`1.964–1.971`** | `6.101` -> `7.568` | `+0 / +824..+1.399` | `0,89` -> `0,73` | `21,0%` -> `24,6%` |

---

## 4. Quy tắc Kích hoạt Khóa cứng (Chống Rút Cạn Vốn Nhỏ)

Kết quả so sánh `Hybrid` vs `Lean` phơi bày một quy luật quản trị vốn quan trọng mà mô phỏng trên giấy dễ bỏ sót: **khi tổng vốn thanh khoản quá mỏng (`Lean 500 USD`, không có Own-Book đệm), thuê bao `35–45 EUR/tháng` trong giai đoạn ủ `14–18` tháng kéo giảm nhẹ trung vị ở ma sát `>= 1,25×` và đẩy `MaxDD` lên `25%–32%`.** Ngược lại, khi đã có nền Own-Book `>= 3.000–5.000 USD`, Darwinex Zero nâng trung vị tài sản 5 năm thêm **`+34% đến +66%`** (`1,00×`) và **`+21% đến +43%`** (`1,25×`) với `MaxDD` rổ giữ gọn ở **`5,2%–5,9%`**, đồng thời cứu **`+45% đến +91%`** tài sản nếu FTMO gặp sự cố đối tác ở năm thứ 3!

**Cổng 3 điều kiện bắt buộc để kích hoạt Firm #2 (`Darwinex Zero`):**
1. **Ma sát thực chiến FTMO `<= 1,25×`:** Xác nhận qua đối soát TCA thật từ Mũi 1–2 và `>= 1–2` kỳ payout FTMO đầu tiên (`> 1,25×` thì tạm hoãn).
2. **Đệm thanh khoản trả trước `>= 1` năm thuê bao:** Chỉ mở khi quỹ Own-Book / lãi rút ròng đã về ngân hàng đạt tối thiểu **`1.500–3.000 USD`** (bảo đảm `420 EUR` phí năm `<= 15%–30%` đệm, **tuyệt đối không rút từ quỹ mua vé `500 USD` ban đầu**).
3. **Chế độ thuê bao tối ưu:** Chạy `2–3` tháng gói lẻ `45 EUR/tháng` để kiểm khớp MT5 `Naqex_Master_Prop7E.ex5` & hoàn tất hiệu chuẩn; khi ổn định lập tức chuyển sang **gói `1` năm `420 EUR` (`35 EUR/tháng`)** để rút ngắn điểm hòa vốn xuống **Tháng `14–18`** và nâng xác suất có lãi `36` tháng thêm `+4%..+7%`.
