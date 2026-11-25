---
doc_type: research_receipt
date: 2026-11-24
lane: quant-rnd
milestone: M4.2
status: COMPLETE_ZERO_PASS_HONEST_NEGATIVE
holdout_rows_analysed: 0
order_send_count: 0
---

# Pass 30 — Khám Phá Intraday FX Mở Rộng (`AUDUSD`, `USDCAD`, `EURJPY`, `GBPJPY`) — Chỉ Development (`< 2025-01-01`)

- **Ngày thực hiện:** `2026-11-24`
- **Mã nguồn tái lập:** [pass30_fx_extended_dev.py](../../tooling/ai-engines/quant_factory/pass30_fx_extended_dev.py)
- **Biên nhận máy:** `.runtime/quant-pod-returns/pass30_fx_extended_summary.json`
- **Khóa bảo vệ Holdout `2025–2026`:**
  - `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA-256 xác nhận nguyên vẹn (`f0a6b43cb205535b...`).
  - **`holdout_rows_analysed = 0`**, **`order_send_count = 0`**.
  - Dữ liệu duy nhất từ `.runtime/hot-m1-cache/` (Native M1 Bid+Ask cho `AUDUSD` `2.60M` nến, `USDCAD` `2.60M` nến, `EURJPY` `2.61M` nến, `GBPJPY` `2.61M` nến; toàn bộ `max_ts < 2025-01-01T00:00:00Z`).
- **Quy chuẩn kiểm định:** Intraday `swap = 0`, hard SL trên mọi lệnh, phân tách **Cluster A (`2018–2021`) → Cluster B mù (`2022–2024`)**, `BH-FDR` trên toàn bộ `m_total = 24` ứng viên, Sign-Flip Permutation Null (`N = 1.000`), Zero-Leakage Matched-Hold Random-Timing Null (`N = 500`), tương quan ngày vs `PORT_7E`, và đo trực tiếp tác động lên `Cluster B Calmar` & thời gian vượt P1 FTMO Swing (`2.000` đường Block-Bootstrap Numba).

---

## 1. Kết Luận Tóm Tắt (Trung Thực 100% — `0 / 24` Ứng Viên Đạt Cổng)

> **Kết quả:** **`0 / 24` ứng viên đạt cổng kiểm định Pass 30.** Không có ứng viên nào dương trên Cluster A (`2018–2021`), không có ứng viên nào dương ở tầng `Double Cost`, không có ứng viên nào vượt `BH-FDR` (`q_all >= 0.575`) hoặc `Matched-Hold Timing Null` (`p >= 0.118`). Kết quả xác nhận rõ ràng không nên bổ sung bất kỳ biến thể nào trong 3 họ này vào `PORT_7E`.

---

## 2. Bảng Kết Quả Đầy Đủ Toàn Bộ `24` Ứng Viên Đăng Ký Trước (`m_total = 24`)

*(Đơn vị `R` ở tầng `FTMO Stress`; cột `2x Cost` là tầng `Double Stress`.)*

| Mã Chiến Lược | Họ Kinh Tế | Cặp Tiền | Cl.A `2018–2021` (`n`, `R`, `PF`) | **Cl.B Mù `2022–2024` (`n`, `R`, `PF`)** | Dev All `2x Cost R` | `BH q_all` | `Matched-Hold p` | `r(PORT_7E)` | Kết Luận |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| `P30_F1_AUDUSD_ON_GAP_FADE_35_TP` | `F1_OVERNIGHT_GAP_FADE` | `AUDUSD` | `300 / -16.02 / 0.75` | `211 / -8.94 / 0.80` | `-30.33` | `0.898` | `0.407` | `-0.049` | LOẠI |
| `P30_F1_AUDUSD_ON_GAP_FADE_50_RAW` | `F1_OVERNIGHT_GAP_FADE` | `AUDUSD` | `141 / -8.72 / 0.78` | `106 / +1.37 / 1.05` | `-9.89` | `0.898` | `0.291` | `-0.047` | LOẠI |
| `P30_F1_USDCAD_ON_GAP_FADE_35_TP` | `F1_OVERNIGHT_GAP_FADE` | `USDCAD` | `156 / -10.98 / 0.69` | `100 / -8.12 / 0.67` | `-21.14` | `0.898` | `0.862` | `-0.051` | LOẠI |
| `P30_F1_USDCAD_ON_GAP_FADE_50_RAW` | `F1_OVERNIGHT_GAP_FADE` | `USDCAD` | `51 / -14.56 / 0.39` | `37 / -0.27 / 0.98` | `-15.42` | `0.898` | `0.976` | `-0.086` | LOẠI |
| `P30_F1_EURJPY_ON_GAP_FADE_35_TP` | `F1_OVERNIGHT_GAP_FADE` | `EURJPY` | `233 / -13.13 / 0.76` | `171 / -9.72 / 0.78` | `-25.58` | `0.898` | `0.896` | `-0.221` | LOẠI |
| `P30_F1_EURJPY_ON_GAP_FADE_50_RAW` | `F1_OVERNIGHT_GAP_FADE` | `EURJPY` | `95 / -2.19 / 0.92` | `94 / -10.89 / 0.68` | `-14.22` | `0.898` | `0.846` | `-0.217` | LOẠI *(ít âm nhất Cl.A)* |
| `P30_F1_GBPJPY_ON_GAP_FADE_35_TP` | `F1_OVERNIGHT_GAP_FADE` | `GBPJPY` | `181 / -13.33 / 0.72` | `178 / -10.15 / 0.77` | `-25.21` | `0.898` | `0.934` | `-0.201` | LOẠI |
| `P30_F1_GBPJPY_ON_GAP_FADE_50_RAW` | `F1_OVERNIGHT_GAP_FADE` | `GBPJPY` | `84 / -7.80 / 0.75` | `90 / -10.89 / 0.66` | `-19.43` | `0.898` | `0.972` | `-0.251` | LOẠI |
| `P30_F2_AUDUSD_LDN_ORB90_VOLCOMP` | `F2_LONDON_ORB_VOL` | `AUDUSD` | `300 / -11.93 / 0.83` | `222 / -14.59 / 0.75` | `-31.55` | `0.740` | `0.489` | `+0.013` | LOẠI |
| `P30_F2_AUDUSD_LDN_ORB120_VOLEXP` | `F2_LONDON_ORB_VOL` | `AUDUSD` | `328 / -15.26 / 0.82` | `256 / -5.07 / 0.92` | `-26.02` | `0.711` | `0.258` | `+0.040` | LOẠI |
| `P30_F2_USDCAD_LDN_ORB90_VOLCOMP` | `F2_LONDON_ORB_VOL` | `USDCAD` | `290 / -14.75 / 0.82` | `216 / -23.99 / 0.67` | `-42.66` | `0.898` | `0.904` | `+0.021` | LOẠI |
| `P30_F2_USDCAD_LDN_ORB120_VOLEXP` | `F2_LONDON_ORB_VOL` | `USDCAD` | `344 / -41.93 / 0.65` | `264 / -10.80 / 0.86` | `-57.21` | `0.898` | `0.974` | `+0.052` | LOẠI |
| `P30_F2_EURJPY_LDN_ORB90_VOLCOMP` | `F2_LONDON_ORB_VOL` | `EURJPY` | `330 / -7.79 / 0.90` | `263 / +8.69 / 1.16` | `-3.03` | `0.575` | `0.118` | `+0.105` | LOẠI *(âm Cl.A & 2x)* |
| `P30_F2_EURJPY_LDN_ORB120_VOLEXP` | `F2_LONDON_ORB_VOL` | `EURJPY` | `299 / -7.06 / 0.91` | `212 / -3.90 / 0.92` | `-14.24` | `0.575` | `0.385` | `+0.066` | LOẠI |
| `P30_F2_GBPJPY_LDN_ORB90_VOLCOMP` | `F2_LONDON_ORB_VOL` | `GBPJPY` | `334 / -21.26 / 0.75` | `281 / +3.44 / 1.06` | `-20.68` | `0.575` | `0.535` | `+0.035` | LOẠI |
| `P30_F2_GBPJPY_LDN_ORB120_VOLEXP` | `F2_LONDON_ORB_VOL` | `GBPJPY` | `276 / -8.94 / 0.87` | `206 / +1.60 / 1.03` | `-9.55` | `0.575` | `0.365` | `+0.074` | LOẠI |
| `P30_F3_AUDUSD_CCY_RS_10UTC` | `F3_CROSS_CCY_RS` | `AUDUSD` | `380 / -18.44 / 0.81` | `280 / -27.06 / 0.66` | `-51.64` | `0.898` | `0.818` | `+0.101` | LOẠI |
| `P30_F3_AUDUSD_CCY_RS_13UTC` | `F3_CROSS_CCY_RS` | `AUDUSD` | `431 / -16.11 / 0.83` | `334 / -41.40 / 0.57` | `-64.74` | `0.898` | `0.924` | `+0.095` | LOẠI |
| `P30_F3_USDCAD_CCY_RS_10UTC` | `F3_CROSS_CCY_RS` | `USDCAD` | `319 / -10.85 / 0.89` | `258 / -37.95 / 0.60` | `-53.05` | `0.898` | `0.960` | `+0.035` | LOẠI |
| `P30_F3_USDCAD_CCY_RS_13UTC` | `F3_CROSS_CCY_RS` | `USDCAD` | `404 / -5.89 / 0.94` | `315 / -34.61 / 0.64` | `-46.03` | `0.898` | `0.798` | `+0.042` | LOẠI |
| `P30_F3_EURJPY_CCY_RS_10UTC` | `F3_CROSS_CCY_RS` | `EURJPY` | `416 / -11.49 / 0.89` | `354 / +5.82 / 1.08` | `-10.71` | `0.585` | `0.144` | `+0.142` | LOẠI |
| `P30_F3_EURJPY_CCY_RS_13UTC` | `F3_CROSS_CCY_RS` | `EURJPY` | `493 / -10.05 / 0.90` | `354 / -17.04 / 0.78` | `-32.68` | `0.898` | `0.547` | `+0.127` | LOẠI |
| `P30_F3_GBPJPY_CCY_RS_10UTC` | `F3_CROSS_CCY_RS` | `GBPJPY` | `468 / -25.29 / 0.80` | `372 / +2.84 / 1.03` | `-26.38` | `0.740` | `0.399` | `+0.122` | LOẠI |
| `P30_F3_GBPJPY_CCY_RS_13UTC` | `F3_CROSS_CCY_RS` | `GBPJPY` | `525 / -20.43 / 0.82` | `363 / -23.47 / 0.71` | `-48.02` | `0.898` | `0.870` | `+0.123` | LOẠI |

---

## 3. Định Lượng Tác Động Lên `PORT_7E` (Phản Chứng Chẩn Đoán — KHÔNG ĐỀ XUẤT THÊM)

Vì `0/24` ứng viên đạt cổng, phép đo dưới đây sử dụng ứng viên ít âm nhất trên Cluster A (`P30_F1_EURJPY_ON_GAP_FADE_50_RAW`, `189` lệnh, thêm `+0.50%` rủi ro/lệnh) làm **phép thử phản chứng (`counterfactual_only_do_not_promote = true`)** nhằm lượng hóa hậu quả nếu cố thêm chiến lược yếu vào `PORT_7E`:

| Danh Mục (M1 Floating Prague-Reset, FTMO Swing 10k) | Dev `2018–2024` (`Ann / PeakDD / Calmar`) | **Cluster B `2022–2024` (`Ann / PeakDD / Calmar`)** | FTMO Swing MC `Pass 3m / 6m` | **Trung Vị Vượt P1+P2 (`tháng`)** | `BR1 %` | `CF 24m` (`USD`) |
|---|---:|---:|---:|---:|---:|---:|
| **`PORT_7E` Đóng Băng (Baseline)** | `+7.73% / 6.36% / 1.22` | **`+9.16% / 6.36% / 1.44`** | `14.2% / 36.9%` | **`6.1 tháng`** | `6.6%` | **`+693.1 USD`** |
| `PORT_7E` + `P30_F1_EURJPY_ON_GAP_FADE` *(Phản chứng)* | `+6.85% / 7.47% / 0.92` | `+7.32% / 7.47% / 0.98` | `11.8% / 33.0%` | `6.3 tháng` | `6.0%` | `+546.9 USD` |
| *Chênh lệch (`Delta`)* | `-0.88 pp / +1.11 pp / -0.30` | **`-1.84 pp / +1.11 pp / -0.46`** | `-2.4 pp / -3.9 pp` | **`+0.2 tháng (chậm hơn)`** | `-0.6 pp` | **`-146.2 USD`** |

---

## 4. Kết Luận Cấu Trúc Thị Trường Cho Alpha Hypothesis Ledger

1. **Đánh ngược sóng qua đêm (`F1_OVERNIGHT_GAP_FADE`) thất bại đồng loạt trên cả 4 cặp tiền:** Không chỉ lỗ trên `AUDUSD` và `USDCAD`, việc fade `EURJPY`/`GBPJPY` còn mang tương quan âm `-0.20` đến `-0.25` với `PORT_7E` — tức đánh ngược lại động lượng phiên Á→Âu thật sự của cặp Yên.
2. **London Open Range Breakout (`F2_LONDON_ORB_VOL`) không phù hợp cặp tiền hàng hóa (`AUDUSD`, `USDCAD`):** Hai cặp này tạo xung lực chính tại phiên Á/Úc và phiên Mỹ (giờ dầu/dữ liệu Canada–Mỹ), nên hộp mở cửa London `07:00–09:00 UTC` bị quét giả liên tục (`-26 R` đến `-57 R` ở `2x` phí). Trên `EURJPY`, hộp London ORB (`-7.79 R` Cl.A) thua xa động cơ đã niêm phong `E6_EURJPY_VOLCOMP` (đo nén `ATR5/ATR20 < 0.85` rồi phá ngưỡng `0.75 ATR` từ giá mở cửa ngày).
3. **Đuổi đà chéo tiền tệ bằng lệnh thị trường (`F3_CROSS_CCY_RS`) bị gãy nặng trên `AUDUSD`/`USDCAD` (`-40 R` đến `-65 R`):** Cho thấy các cặp tiền hàng hóa mang tính hồi quy nội ngày cao hơn nhiều so với nhóm JPY/US100; đồng thời xác nhận lý do `S6_FX_USD_BSK` (Pass 26, lọc rổ USD tổng hợp ở ngưỡng `z >= 0.35`) và `E7_USDJPY_NY10ET` (Pass 28, xác nhận dòng tiền cổ phiếu Mỹ `US100`) mới là hai cơ chế cross-asset có ích thật sự.
4. **Quyết định cuối cùng cho Tier 4 (Pass 29 & Pass 30):** Giữ nguyên trạng **100% nguyên vẹn `PORT_7E` và `PORT_9E`** — không pha loãng bằng ứng viên FX/Gold/Index intraday yếu. Nguồn tăng trưởng Sharpe/Calmar lớn nhất của Quant Pod nằm ở **đa dạng hóa liên lớp tài sản (Sleeve #2 Crypto Spot + Sleeve #3A Funding Carry theo chế độ + Sleeve #3B 18-Year Macro ETF Risk Parity)**, không phải cố vắt thêm các tín hiệu FX nội ngày biên mỏng.
