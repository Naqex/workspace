# Pass 14 · Protocol sàng lọc đồng loạt 13 chiến lược `"CHẤT"` còn lại từ `strategy-intel` (15/15 Top Leads · Phân loại 3 tầng)

Baseline `0521a53` (nhánh `codex/prop-research-roadmap`).
Phạm vi dữ liệu **Development UTC `2018-01-01` → `< 2025-01-01`** (`1514764800`..`1735689600`).
Khóa cứng Holdout `>= 2025-01-01` theo `NATIVE_FTMO_HOLDOUT_LOCK.json` (`sha256: f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486`, bắt buộc `holdout_rows = 0`).
`network_calls = 0`, `OrderSend = 0`, không MT5, không đọc `.env`.
Tuân thủ **Air-Gap tuyệt đối** với `D:\ANNAM\strategy-intel`: chỉ sử dụng đặc tả văn bản đã khử nhiễu (`sanitized_master_leads.json`, `SOURCE_CLAIM_ONLY`), không đọc/import code xuyên repo, không tiếp cận bất kỳ số liệu `>= 2025-01-01` nào.

## 1. Dữ liệu M1 cục bộ (Hot Cache SSD `~240 MB` đối soát SHA với ổ E)

Đọc trực tiếp từ `.runtime/hot-m1-cache/manifest.json` (bản sao SHA-verified từ dữ liệu niêm phong trên ổ E):
- **Native Tick-derived M1 Bid/Ask (`native_Ask = true`):** `EURUSD` (`pass13`), `GBPUSD` (`pass11`), `USDJPY` (`pass7b`).
- **QDM M1 Bid + Proxy Spread (`native_Ask = false`, `M1_BID_PROXY_SPREAD`):** `XAUUSD` (`pass13`). Bất kỳ ứng viên nào sống sót trên `XAUUSD` chỉ được gán tối đa mức tạm thời `PROVISIONAL_NEEDS_NATIVE_TICK_BIDASK`, chưa đủ chuẩn qualify trực tiếp.
- **Khởi tạo chỉ báo D1 dài hạn (`SMA200`, `EMA200`, mùa vụ tháng trước 2018):** Chỉ dùng chuỗi D1 hoàn tất trước `2018-01-01` từ `swing-10k-20261120/development/{SYM}-D1.parquet` (`2004–2017`) để không bị khuyết warm-up năm 2018 mà vẫn 100% nhân quả.

## 2. Đặc tả cơ học 100% nhân quả cho 13 chiến lược `"CHẤT"` còn lại

*(Hai mã `NEN022` và `SEA003` đã kiểm chứng dứt điểm và loại ở Pass 13 → Pass 14 hoàn thiện 15/15 Top Leads.)*
Mọi tín hiệu chỉ tính trên nến đã đóng hoàn toàn; vào lệnh tại `open` của phút M1 kế tiếp (`ask_open` khi BUY, `bid_open` khi SELL); không chồng vị thế trên cùng tài sản; cùng phút chạm cả SL và TP luôn tính **SL chạm trước**.

1. **`BRK012` (Inside Day Breakout · D1 · 2 chiều):** Nến D1 hôm qua nằm gọn trong hôm kia (`H[d-1] <= H[d-2]`, `L[d-1] >= L[d-2]`). Ngày `d` (`00:00–20:55 UTC`) đặt OCO phá biên `H[d-1]` (BUY, `SL = L[d-1]`) / `L[d-1]` (SELL, `SL = H[d-1]`), bỏ ngày chạm 2 biên cùng phút. `TP = 2,0R`, giữ tối đa `5` ngày.
2. **`BRK035` (Hộp 4h đầu tuần · H1 · 2 chiều · `swap = 0`):** Thứ Hai `00:00–03:59 UTC` lập hộp (`top = max ask_high`, `bottom = min bid_low`). OCO phá biên trong `04:00–16:59 UTC` thứ Hai (`SL` biên đối diện), đóng phẳng bắt buộc `20:55 UTC` thứ Hai.
3. **`IND026` (Ichimoku Chikou xác nhận · D1 · Long):** Trên D1 đã đóng: `Tenkan=9`, `Kijun=26`, `SenkouB=52`, mây tại ngày `t` lấy từ `SpanA/B[t-26]` (100% nhân quả). Mua khi `C[t] > C[t-26]` và `C[t] > max(SpanA_curr, SpanB_curr)` (chuyển trạng thái mới). `SL = entry - 2,0*ATR14_D1`, thoát tại SL hoặc `C < Kijun` hoặc tối đa `20` ngày.
4. **`IND041` (ROC Momentum 10 · H4 · 2 chiều):** `ROC10 = 100*(C[t]/C[t-10] - 1)` trên UTC H4. Ngưỡng tự thích nghi nhân quả theo độ biến động từng tài sản: `X = 1,0 * std(ROC10[t-50:t])`. Cắt lên `+X` → BUY, cắt xuống `-X` → SELL. `SL = 2,0*ATR14_H4`, `TP = 3,0*ATR14_H4`, tối đa `5` ngày.
5. **`IND049` (Alligator mở miệng · H4 · 2 chiều):** SMMA giá giữa `(H+L)/2` chuẩn Bill Williams (`Jaw 13` lùi 8, `Teeth 8` lùi 5, `Lips 5` lùi 3 — nhân quả). Tại `t-1` ba đường cuộn hẹp (`spread < 0,5*ATR14_H4`); tại `t` mở rộng `>= 0,5*ATR14_H4` theo đúng thứ tự (`Lips > Teeth > Jaw` & `C > Lips` → BUY; ngược lại → SELL). `SL = 2,0*ATR14_H4`, thoát tại SL hoặc đóng ngược qua `Teeth` hoặc tối đa `5` ngày.
6. **`IND053` (Momentum 10 vượt 100 · H4 · 2 chiều):** `MOM10 = 100*C[t]/C[t-10]` trên UTC H4. Cắt lên `100` → BUY, cắt xuống `100` → SELL. `SL = 2,0*ATR14_H4`, `TP = 3,0*ATR14_H4`, tối đa `5` ngày.
7. **`MTF016` (Mùa vụ D1 + tín hiệu H1 · H1 · 2 chiều · `swap = 0`):** Hướng mùa vụ của từng tháng dương lịch cố định hoàn toàn trước `2018-01-01` từ dấu lợi nhuận trung bình tháng `2004–2017` trên D1. Trên H1, chỉ nhận tín hiệu đột phá `Donchian(20)` cùng chiều mùa vụ tháng đó; `SL = 2,0*ATR14_H1`, `TP = 3,0*ATR14_H1`, đóng phẳng trong ngày `20:55 UTC`.
8. **`MTF020` (Golden Cross D1 nền + hồi H4 · H4 · Long):** Nền D1 hoàn tất có `SMA50_D1 > SMA200_D1`. Trên H4, khi nến chạm `<= EMA20_H4` rồi đóng tăng `> EMA20_H4` (`C > O`) → BUY. `SL = min(low, EMA20 - 1,5*ATR14_H4)`, `TP = 2,0R`, tối đa `5` ngày.
9. **`NEN006` (Inside Bar thuận trend D1 · D1 · 2 chiều):** Nến D1 inside bar (`H[d-1] <= H[d-2]`, `L[d-1] >= L[d-2]`). Chỉ mua phá biên trên nếu `C[d-1] > EMA200_D1`; chỉ bán phá biên dưới nếu `C[d-1] < EMA200_D1`. `SL` biên đối diện, `TP = 2,0R`, tối đa `5` ngày.
10. **`SEA004` (Hiệu ứng đầu quý · D1 · 2 chiều):** Ngày giao dịch đầu tiên mỗi quý (T1/T4/T7/T10) xác định hướng drift (`C > O` → BUY, `C < O` → SELL) vào đầu ngày thứ 2 (`01:00 UTC`), đóng cuối ngày thứ 3 (`20:55 UTC`), `SL = 2,0*ATR14_D1` (ghi nhận thêm biến thể đối chứng Long-only 3 ngày đầu quý).
11. **`SEA011` (Thứ Ba đảo chiều · D1 · Long · `swap = 0`):** Nếu thứ Hai giảm mạnh (`C - O <= -0,75*ATR14_D1`), mua thứ Ba `01:00 UTC`, `SL = entry - 1,5*ATR14_D1`, đóng phẳng thứ Ba `20:55 UTC`.
12. **`SEA021` (Thứ Hai hồi sau NFP xấu · H1 · Long · `swap = 0`):** Thứ Sáu đầu tiên mỗi tháng (lịch NFP), nếu phiên Mỹ (`12:00–20:55 UTC`) giảm mạnh `<= -0,75*ATR14_D1`, mua thứ Hai kế tiếp `01:00 UTC`, `SL = entry - 1,5*ATR14_D1`, đóng phẳng thứ Hai `20:55 UTC`.
13. **`VIR040` (Head & Shoulders phá neckline · H4 · 2 chiều):** Bộ dò đỉnh/đáy 5 nến nhân quả (xác nhận tại `p + 2`). Khi 3 đỉnh gần nhất thỏa `Head > LS`, `Head > RS`, `|LS - RS| <= 1,0*ATR14_H4` và nến H4 đóng thủng neckline nối 2 đáy giữa → SELL (`SL = RS + buffer`, `TP = 2,0R`, tối đa `5` ngày); đối xứng cho Vai-Đầu-Vai ngược → BUY.

## 3. Khung chi phí, đối chứng chống ăn may & Phân loại 3 tầng

Mỗi chiến lược chạy trên **4 tài sản** (`XAUUSD` gốc + 3 cặp FX native M1 Bid/Ask: `EURUSD`, `GBPUSD`, `USDJPY` → tổng **`52` cặp chiến lược × tài sản**):
- **Chi phí chính (`FTMO_Stress`):** Bám SHA `36f1535`/`8fd77ef` (FX: observed Bid/Ask + comm `5 USD/lot` + stress slippage `+0,50 pip` RT + FTMO Swap 3× thứ Tư; XAUUSD: proxy spread `0,50 USD/oz` + comm FTMO + stress slippage `0,25 USD/oz/chiều` + FTMO Swap 3× thứ Tư `swap_long = -56,56`).
- **Chi phí tham chiếu phụ (`Exness_Personal_Ref`, non-binding):** Đánh giá đồng thời trên cùng tập lệnh với bảng phí website `Exness Raw Spread` (`EXNESS_WEBSITE_SNAPSHOT_UNMEASURED_DEMO`: comm `5 USD/lot` FX, Swap chuẩn Exness `USDJPY 0/0`, `GBPUSD -0,14/-0,14`, `EURUSD -0,55/0`, kèm báo cáo riêng trường hợp Swap-Free có điều kiện).
- **Chống ăn may đa kiểm định:**
  1. **Monte Carlo Random-Entry Null Test (`N = 1.000`, `seed = 20261123`)** cho từng cặp trong 52 cặp (khớp đúng số lệnh BUY/SELL và thời lượng giữ trung bình trên cùng chuỗi M1).
  2. **Hiệu chỉnh FDR Benjamini–Hochberg (`q_value`)** trên toàn bộ 52 phép thử.
  3. **Kiểm độ bền tham số `±30%`** & **ghép danh mục với Engine #1 `USDJPY`** tự động cho mọi ứng viên lọt cửa `TIER_1_FTMO_READY`.
- **Quy tắc gán nhãn 3 tầng (`validation-gates.md`):**
  - `TIER_1_FTMO_READY`: `n >= 30`, `FTMO_Stress net_R > 0`, dương cả Cụm A (`2018–2020`) và Cụm B (`2021–2024`), `>= 5/7` năm dương, `net_R > top10_R`, `MC Null p < 0,05` (báo cả `FDR q_value`), `closed_dd_R <= 25R`.
  - `TIER_2_PERSONAL_VAULT`: Trượt `TIER_1` do đặc thù FTMO (Swap 3× nặng hoặc tần suất/tốc độ chậm), **NHƯNG** chứng minh lợi thế giá thật (`MC Null p < 0,05`, `Exness_Personal_Ref` dương cả Cụm A và Cụm B, `>= 5/7` năm dương, `net_R > top10_R`).
  - `TIER_3_DEAD_NO_EDGE`: Còn lại (loại vĩnh viễn cho mọi sàn).
