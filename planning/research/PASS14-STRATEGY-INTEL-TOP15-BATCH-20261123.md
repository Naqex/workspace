# Pass 14 · Sàng lọc đồng loạt 13 chiến lược `"CHẤT"` còn lại từ `strategy-intel` (Hoàn tất 15/15 Top Leads)

- **Protocol khóa trước thực nghiệm:** [PASS14-STRATEGY-INTEL-TOP15-BATCH-PROTOCOL-20261123.md](PASS14-STRATEGY-INTEL-TOP15-BATCH-PROTOCOL-20261123.md) (commit `079ea0a`)
- **Hạ tầng tốc độ:** Chạy toàn bộ **52 cặp (`13` chiến lược × `4` tài sản, ~10,3 triệu nến M1, `52.000` lượt Monte Carlo Null + FDR)** trong **`35.47s`** trên **Hot M1 Parquet Cache SSD (`249,3 MB`, ổ D còn trống `151,4 GB`)**.
- **An toàn & kiểm định:** `holdout_rows = 0` (`>= 2025-01-01` khóa cứng), `network_calls = 0`, `OrderSend = 0`, Air-Gap 100%, `quant_test_suite` **`1517/1517 PASS (0 skip, 15.68s)`**.
- **Phán quyết tổng hợp (gộp Pass 13 + Pass 14 = 15/15 Top Leads `"CHẤT"`):**
  - **`TIER_1_FTMO_READY`: `0 / 52`** (chưa có chiến lược nào trong Top 15 đủ chuẩn ghép thi FTMO Challenge ngay; tiếp tục giữ Engine #1 `USDJPY` Pass 7B/8 và `ENGINE_1_NEEDS_PARTNER`).
  - **`TIER_2_PERSONAL_VAULT_PROVISIONAL_XAU`: `2 / 52`** (`NEN006 XAUUSD` và `IND026 XAUUSD` — cất vào kho dự trữ cho tài khoản riêng/Exness với 2 lưu ý thận trọng bắt buộc: cần xác nhận lại trên Tick Bid/Ask thật và `FDR q = 0,416` do kiểm định 52 cặp).
  - **`TIER_3_DEAD_NO_EDGE`: `50 / 52`** (cộng thêm `NEN022` và `SEA003` từ Pass 13 → loại dứt điểm cho mọi sàn).

---

## 1. Hai ứng viên lọt kho dự trữ tài khoản riêng (`TIER_2_PERSONAL_VAULT_PROVISIONAL_XAU`)

| Chiến lược · Mã | `n` lệnh | FTMO Stress (Net R · Cụm A/B · Năm+ · DD · Top10) | Exness Normal / Swap-Free | MC Null (`p_g / p_f`) & FDR (`q_g`) | Độ bền tham số ±30% |
| --- | ---: | --- | --- | --- | --- |
| **`NEN006` · `XAUUSD`** *(Inside bar + EMA200 D1)* | `161` | **`+14,89R`** (`+4,5 / +10,4` · `5/7` năm · DD `9,8R` · Top10 `18,9R`) | `+20,13R` / **`+30,30R`** | `p = 0,016 / 0,010` · `q = 0,416` | **4/4 ô dương cả Cụm A & B** (`TP 1,5–3,0R`: `+7,7R..+14,9R` FTMO; `+24,3R..+30,4R` ExSF) |
| **`IND026` · `XAUUSD`** *(Ichimoku Chikou D1 Long)* | `43` | **`+10,49R`** (`+5,8 / +4,7` · `5/7` năm · DD `3,3R` · Top10 `21,4R`) | `+10,99R` / **`+19,70R`** | `p = 0,014 / 0,050` · `q = 0,416` | **3/3 ô dương cả Cụm A & B** (`SL 1,5–2,5 ATR`: `+7,8R..+13,9R` FTMO; `+15,2R..+25,6R` ExSF) |

**Vì sao cả 2 chỉ xếp `TIER_2_PERSONAL_VAULT_PROVISIONAL_XAU` (chưa lên `TIER_1_FTMO_READY`):**
1. **Tác động của Swap 3× FTMO & tốc độ quá chậm cho Challenge:** Dưới phí Swap Vàng `-56,28 USD/đêm` (thứ Tư `3×`), `NEN006` chỉ còn `+2,13R/năm` và `IND026` còn `+1,50R/năm`; khi loại top 10 lệnh thắng dưới phí FTMO thì không giữ được dương (`14,89 < 18,9` và `10,49 < 21,4`). Khi bỏ Swap Vàng (Exness Swap-Free có điều kiện), cả hai tăng gấp đôi hiệu suất (`+30,3R` và `+19,7R`) với sụt giảm rất thấp (`3,3R–9,8R`).
2. **Hiệu chỉnh đa kiểm định & giới hạn dữ liệu:** Khi quét 52 cặp cùng lúc, `p = 0,014–0,016` tương ứng `FDR q = 0,416` (chưa loại trừ hoàn toàn may mắn đa kiểm định), và nguồn `XAUUSD_TW` là M1 Bid + spread proxy (`native_Ask = false`), cần kiểm lại trên Tick Bid/Ask thật trước khi dùng tiền thật.

---

## 2. Toàn bộ ma trận 52 cặp (`13` chiến lược × `4` tài sản, M1 thật 2018–2024)

| Chiến lược | `XAUUSD` (FTMO R / ExSF R / p) | `EURUSD` (FTMO R / ExSF R / p) | `GBPUSD` (FTMO R / ExSF R / p) | `USDJPY` (FTMO R / ExSF R / p) | Tầng cao nhất |
| --- | --- | --- | --- | --- | --- |
| **`BRK012`** | `+2.3R` / `+21.1R` (p=0.11) | `+2.8R` / `+8.9R` (p=0.10) | `+7.7R` / `+12.9R` (p=0.45) | `+12.6R` / `+20.8R` (p=0.14) | `TIER_3_DEAD_NO_EDGE` |
| **`BRK035`** | `-51.1R` / `-32.0R` (p=0.49) | `-52.7R` / `-43.9R` (p=0.83) | `-53.4R` / `-46.4R` (p=0.91) | `+22.7R` / `+30.6R` (p=0.25) | `TIER_3_DEAD_NO_EDGE` |
| **`IND026`** | `+10.5R` / `+19.7R` (p=0.01) | `-10.7R` / `-7.8R` (p=0.70) | `-2.0R` / `-0.6R` (p=0.31) | `+20.0R` / `+18.8R` (p=0.18) | `TIER_2_PERSONAL_VAULT_PROVISIONAL_XAU` |
| **`IND041`** | `-33.0R` / `+8.4R` (p=0.19) | `-12.5R` / `+3.7R` (p=0.28) | `+7.7R` / `+20.9R` (p=0.11) | `+5.1R` / `+21.4R` (p=0.09) | `TIER_3_DEAD_NO_EDGE` |
| **`IND049`** | `-0.8R` / `+16.1R` (p=0.21) | `-23.6R` / `-18.3R` (p=0.85) | `+7.9R` / `+12.6R` (p=0.22) | `+15.3R` / `+21.2R` (p=0.07) | `TIER_3_DEAD_NO_EDGE` |
| **`IND053`** | `-34.6R` / `+6.0R` (p=0.11) | `-5.3R` / `+11.2R` (p=0.15) | `-9.6R` / `+2.6R` (p=0.11) | `-16.5R` / `+4.8R` (p=0.23) | `TIER_3_DEAD_NO_EDGE` |
| **`MTF016`** | `-125.7R` / `-87.0R` (p=0.83) | `-76.4R` / `-59.9R` (p=0.64) | `-67.3R` / `-55.2R` (p=0.47) | `-45.8R` / `-31.7R` (p=0.24) | `TIER_3_DEAD_NO_EDGE` |
| **`MTF020`** | `-30.9R` / `+4.3R` (p=0.67) | `-24.8R` / `-16.1R` (p=0.41) | `-28.3R` / `-22.7R` (p=0.68) | `-7.1R` / `-8.1R` (p=0.83) | `TIER_3_DEAD_NO_EDGE` |
| **`NEN006`** | `+14.9R` / `+30.3R` (p=0.02) | `-1.8R` / `+2.0R` (p=0.14) | `-4.6R` / `-1.4R` (p=0.83) | `+5.3R` / `+9.9R` (p=0.44) | `TIER_2_PERSONAL_VAULT_PROVISIONAL_XAU` |
| **`SEA004`** | `+0.4R` / `+1.0R` (p=0.17) | `+2.5R` / `+2.7R` (p=0.03) | `-2.4R` / `-2.2R` (p=0.66) | `+0.3R` / `+0.6R` (p=0.36) | `TIER_3_DEAD_NO_EDGE` |
| **`SEA011`** | `-3.1R` / `-2.8R` (p=0.96) | `-0.1R` / `+0.1R` (p=0.43) | `-4.6R` / `-4.5R` (p=0.99) | `-1.5R` / `-1.3R` (p=0.48) | `TIER_3_DEAD_NO_EDGE` |
| **`SEA021`** | `+0.2R` / `+0.4R` (p=0.25) | `-0.8R` / `-0.8R` (p=0.76) | `-0.4R` / `-0.4R` (p=0.64) | `-0.6R` / `-0.6R` (p=0.89) | `TIER_3_DEAD_NO_EDGE` |
| **`VIR040`** | `-7.5R` / `-3.0R` (p=0.44) | `+2.0R` / `+3.7R` (p=0.25) | `-7.8R` / `-6.7R` (p=0.64) | `-13.2R` / `-11.2R` (p=0.71) | `TIER_3_DEAD_NO_EDGE` |

---

## 3. Bằng chứng định lượng về "cái bẫy Swap Vàng FTMO" vs "Không có lợi thế"

- **Hiệu ứng Swap Vàng FTMO rất thật:** Hàng loạt chiến lược giữ nhiều ngày trên `XAUUSD` bị phí Swap 3× FTMO kéo tụt từ dương về âm sâu (`BRK012 +21,1R → +2,3R`; `IND049 +16,1R → -0,8R`; `IND041 +8,5R → -33,0R`; `IND053 +6,0R → -34,6R`; `MTF020 +4,3R → -30,9R`).
- **Nhưng đổi sàn vẫn KHÔNG cứu được 50/52 cặp:** Ngay cả khi giả định Exness miễn 100% Swap qua đêm, vẫn có tới **`50 / 52` cặp trượt** vì không thắng nổi chọn ngẫu nhiên (`p >= 0,05`) hoặc gãy ở Cụm A/B (`2018–2020` vs `2021–2024`).
- **Gợi ý quan trọng cho bước tiếp theo tìm Engine #2 FTMO (`Pass 15`):**
  1. **Quét tiếp kho tài nguyên sẵn có:** Nhóm **`27` EA có luật rõ ràng (`REPLICABLE_RULE_SET`)** trong `strategy-intel/sources/ea-directory-2026` (35/45 EA là dòng Trend-Following) + nhóm chiến lược **`M15/H1` đánh trong ngày (`swap = 0`)** trong 39 mã `"TÌNH HUỐNG"` của Source 1.
  2. **Thiết kế Engine #2 tối ưu riêng cho cấu trúc phí FTMO:** `XAUUSD` đánh sóng trong ngày (`swap = 0`, tránh mất `15–40R` vì Swap qua đêm) hoặc FX thuận chiều Swap dương trên FTMO (`USDJPY` Long có `swap_long = +2,61` — trong bảng trên, chính `USDJPY` có nhiều chiến lược dương nhất: `BRK035 +22,7R`, `IND026 +20,0R`, `IND049 +15,3R` `p_f=0,057`, `BRK012 +12,6R`).
