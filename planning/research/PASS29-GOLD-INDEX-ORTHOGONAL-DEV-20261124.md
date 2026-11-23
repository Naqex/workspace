---
doc_type: research_receipt
date: 2026-11-24
lane: quant-rnd
milestone: M4.1
status: COMPLETE_ZERO_PASS_HONEST_NEGATIVE
holdout_rows_analysed: 0
order_send_count: 0
---

# Pass 29 — Khám Phá Intraday Trực Giao Trên Vàng (`XAUUSD`) & Chỉ Số Toàn Cầu (`US500`, `US100`, `GER40`) — Chỉ Development (`< 2025-01-01`)

- **Ngày thực hiện:** `2026-11-24`
- **Mã nguồn tái lập:** [pass29_gold_index_dev.py](../../tooling/ai-engines/quant_factory/pass29_gold_index_dev.py)
- **Biên nhận máy:** `.runtime/quant-pod-returns/pass29_gold_index_summary.json`
- **Khóa bảo vệ Holdout `2025–2026`:**
  - `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA-256 xác nhận nguyên vẹn (`f0a6b43cb205535b...`).
  - **`holdout_rows_analysed = 0`**, **`order_send_count = 0`**.
  - Nguồn dữ liệu duy nhất: `.runtime/hot-m1-cache/` (Native M1 Bid+Ask cho `XAUUSD` `2.48M` nến, `US500` `2.26M` nến, `US100` `2.36M` nến, `GER40` `2.29M` nến; toàn bộ `max_ts < 2025-01-01T00:00:00Z`).
- **Quy chuẩn kiểm định:** Intraday `swap = 0` (đóng lệnh trước rollover), hard SL cứng trên mọi lệnh, tối đa 1 lệnh/ngày/ứng viên, phân tách **Cluster A (`2018–2021`) → Cluster B mù (`2022–2024`)**, `BH-FDR` trên toàn bộ `m_total = 24` giả thuyết đăng ký trước, Sign-Flip Permutation Null (`N = 1.000`), **Zero-Leakage Matched-Hold Random-Timing Null (`N = 500`, lấy mẫu ngẫu nhiên ngày + phút trên cùng tài sản/split/tỷ lệ Long-Short/thời lượng giữ lệnh)**, và tương quan ngày với `PORT_7E` (mục tiêu `|r| < 0.15`).

---

## 1. Kết Luận Tóm Tắt (Trung Thực 100% — `0 / 24` Ứng Viên Đạt Cổng)

> **Kết quả:** **`0 / 24` ứng viên vượt qua đầy đủ các cổng kiểm định Pass 29.** Không có ứng viên nào được đề xuất đưa vào `PORT_7E` hoặc `PORT_9E`. Toàn bộ kết quả âm được lưu trữ đầy đủ để tránh lặp lại các hướng nghiên cứu không có lợi thế thực sau chi phí thực tế.

---

## 2. Bảng Kết Quả Đầy Đủ Toàn Bộ `24` Giả Thuyết Đăng Ký Trước (`m_total = 24`)

*(Đơn vị `R` tính theo mức chi phí `FTMO Stress` thực tế trên M1 Bid/Ask; cột `2x Cost` là tầng `Double Stress`.)*

| Mã Chiến Lược | Giả Thuyết | Tài Sản | Cl.A `2018–2021` (`n`, `R`, `PF`) | **Cl.B Mù `2022–2024` (`n`, `R`, `PF`)** | Dev All `2x Cost R` | `BH q_all` | `Matched-Hold p` | `r(PORT_7E)` | Lý Do Loại |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| `P29_H1_XAU_PRE_LON_PMFIX_DRIFT` | `H1_FIX_DRIFT` | `XAUUSD` | `220 / -7.45 / 0.83` | `157 / -3.01 / 0.91` | `-24.84` | `0.171` | `0.002` | `+0.052` | Âm cả A & B, gãy 2x |
| `P29_H1_XAU_POST_AMFIX_NY` | `H1_FIX_DRIFT` | `XAUUSD` | `95 / -6.22 / 0.71` | `62 / +0.31 / 1.03` | `-11.04` | `0.443` | `0.305` | `+0.031` | Âm A, PF B `<1.05`, gãy FDR/MH |
| `P29_H1_XAU_NY_CLOSE_DRIFT` | `H1_FIX_DRIFT` | `XAUUSD` | `218 / -14.37 / 0.56` | `178 / -5.89 / 0.71` | `-32.56` | `0.610` | `0.421` | `+0.002` | Âm nặng cả A & B |
| `P29_H1_GER40_LON4PM_FIX` | `H1_FIX_DRIFT` | `GER40` | `108 / -5.56 / 0.79` | `126 / -9.96 / 0.67` | `-19.41` | `0.783` | `0.846` | `+0.034` | Âm cả A & B |
| `P29_H1_US500_NY_EOD_DRIFT` | `H1_FIX_DRIFT` | `US500` | `203 / -21.72 / 0.63` | `190 / -6.69 / 0.84` | `-40.75` | `0.610` | `0.591` | `+0.014` | Âm nặng cả A & B |
| `P29_H1_US100_NY_EOD_DRIFT` | `H1_FIX_DRIFT` | `US100` | `162 / -0.09 / 1.00` | `155 / -0.55 / 0.98` | `-5.52` | `0.258` | `0.040` | `+0.005` | Hòa vốn trước phí, âm sau Stress |
| `P29_H1_US500_LON4PM_DRIFT` | `H1_FIX_DRIFT` | `US500` | `316 / -19.43 / 0.74` | `253 / -12.71 / 0.77` | `-49.96` | `0.443` | `0.355` | `+0.062` | Âm nặng cả A & B |
| `P29_H1_US100_LON4PM_DRIFT` | `H1_FIX_DRIFT` | `US100` | `290 / -12.96 / 0.79` | `258 / +3.98 / 1.10` | `-17.81` | `0.171` | `0.096` | `+0.132` | Âm nặng A, gãy 2x & FDR |
| `P29_H2_XAU_LDN_OR60_SQZ35` | `H2_OR_VOL_SQUEEZE` | `XAUUSD` | `959 / -56.75 / 0.81` | **`733 / +21.64 / 1.11`** | `-88.87` | `0.036` | `0.034` | `+0.105` | **Đảo chế độ: âm `-56.8R` ở Cl.A** |
| `P29_H2_XAU_NY_OR30_SQZ30` | `H2_OR_VOL_SQUEEZE` | `XAUUSD` | `731 / -38.89 / 0.77` | `496 / -2.21 / 0.98` | `-79.87` | `0.036` | `0.118` | `+0.023` | Âm cả A & B, tần suất quá cao |
| `P29_H2_US500_OR30_SQZ35` | `H2_OR_VOL_SQUEEZE` | `US500` | `619 / -16.88 / 0.89` | `497 / -2.41 / 0.98` | `-53.98` | `0.012` | `0.042` | `+0.061` | Âm cả A & B |
| `P29_H2_US100_OR30_SQZ35` | `H2_OR_VOL_SQUEEZE` | `US100` | `458 / -12.31 / 0.89` | **`366 / +15.23 / 1.16`** | `-10.16` | `0.012` | `0.046` | `+0.084` | **Đảo chế độ: âm `-12.3R` ở Cl.A & gãy 2x** |
| `P29_H2_GER40_OR30_SQZ35` | `H2_OR_VOL_SQUEEZE` | `GER40` | `611 / -32.52 / 0.80` | `489 / +3.79 / 1.03` | `-45.58` | `0.171` | `0.220` | `+0.024` | Âm nặng A, PF B yếu |
| `P29_H2_GER40_OR60_SQZ45` | `H2_OR_VOL_SQUEEZE` | `GER40` | `597 / -19.79 / 0.86` | `509 / +8.08 / 1.06` | `-28.93` | `0.053` | `0.060` | `+0.045` | Âm nặng A, gãy 2x & MH |
| `P29_H3_XAU_ASIA_LDN_REV_30` | `H3_GOLD_ASIA_REV` | `XAUUSD` | `222 / -17.74 / 0.55` | `137 / -10.48 / 0.60` | `-39.50` | `0.866` | `0.880` | `-0.084` | Thất bại hoàn toàn cả A & B |
| `P29_H3_XAU_ASIA_LDN_REV_50` | `H3_GOLD_ASIA_REV` | `XAUUSD` | `55 / -3.34 / 0.74` | `36 / -1.94 / 0.73` | `-8.10` | `0.610` | `0.593` | `-0.034` | Âm cả A & B |
| `P29_H3_XAU_ASIA_LDN_REV_40_08U` | `H3_GOLD_ASIA_REV` | `XAUUSD` | `150 / -17.51 / 0.59` | `97 / +0.12 / 1.00` | `-25.14` | `0.783` | `0.713` | `-0.017` | Âm nặng A, hòa vốn B |
| `P29_H3_XAU_ASIA_LDN_CONT_40` | `H3_GOLD_ASIA_REV` | `XAUUSD` | `116 / -4.70 / 0.84` | `73 / -1.27 / 0.92` | `-11.89` | `0.496` | `0.315` | `+0.041` | Nhóm đối chứng thuận chiều cũng âm |
| `P29_H4_US500_AUCT15_MOM_25` | `H4_IDX_AUCTION` | `US500` | **`57 / +2.30 / 1.13`** | `36 / -2.17 / 0.79` | `-3.23` | `0.281` | `0.092` | `+0.011` | **Dương A nhưng gãy trên Cl.B mù** |
| `P29_H4_US100_AUCT15_MOM_25` | `H4_IDX_AUCTION` | `US100` | **`105 / +6.23 / 1.23`** | `65 / -5.63 / 0.74` | `-2.55` | `0.443` | `0.098` | `-0.013` | **Dương A nhưng gãy trên Cl.B mù** |
| `P29_H4_GER40_AUCT15_MOM_25` | `H4_IDX_AUCTION` | `GER40` | `86 / +0.02 / 1.00` | `61 / -0.06 / 1.00` | `-2.49` | `0.416` | `0.092` | `+0.021` | Hòa vốn, không vượt chi phí |
| `P29_H4_US500_AUCT15_FADE_30` | `H4_IDX_AUCTION` | `US500` | `70 / -16.38 / 0.47` | `40 / +3.38 / 1.33` | `-16.04` | `0.657` | `0.892` | `+0.017` | Âm nặng A (`PF=0.47`) |
| `P29_H4_US100_AUCT30_CONT_40` | `H4_IDX_AUCTION` | `US100` | `99 / -1.64 / 0.94` | `78 / -1.43 / 0.93` | `-6.23` | `0.416` | `0.216` | `+0.043` | Âm cả A & B |
| `P29_H4_GER40_AUCT30_CONT_40` | `H4_IDX_AUCTION` | `GER40` | `80 / -6.05 / 0.78` | `52 / -6.01 / 0.64` | `-13.96` | `0.783` | `0.862` | `-0.013` | Âm cả A & B |

---

## 3. Bài Học Cấu Trúc Thị Trường Từ Kết Quả Âm Pass 29

1. **H1 (`London/NY Fix Drift`) bị bào mòn bởi tỷ lệ lợi nhuận/chi phí quá mỏng:** Các cửa sổ giữ lệnh ngắn `1.5–3.5` giờ quanh giờ Fix (`15:00` London, `16:00` London, `14:00–15:55` ET) tạo lợi thế gộp quá nhỏ so với spread Bid/Ask thực cộng trượt giá stress (`0.50 USD/oz` trên Gold, `1.5–4.0` điểm trên US500/US100/GER40). Mọi biến thể đều âm nặng ở tầng `Double Cost`.
2. **H2 (`Opening-Range Vol Squeeze`) lộ rõ bẫy đảo chế độ (`2018–2021` vs `2022–2024`):** Phá hộp mở cửa `30m/60m` trên `US100` (`+15.23 R` Cl.B) và `XAUUSD` (`+21.64 R` Cl.B) hoạt động rất tốt trong giai đoạn lãi suất cao/biến động có xu hướng `2022–2024`, nhưng bị quét hai đầu thảm khốc trong giai đoạn `2018–2021` (`-12.31 R` và `-56.75 R` với `458–959` lệnh). Kỷ luật phân tách mù đã ngăn chặn thành công việc chọn nhầm chiến lược phụ thuộc duy nhất vào chế độ hậu-2022.
3. **H3 (`Gold Asian -> London Mean Reversion`) bị bác bỏ hoàn toàn trên dữ liệu M1 Bid/Ask thực:** Cả 3 quy tắc đảo chiều lẫn nhóm đối chứng thuận chiều đều thua lỗ trên cả 2 cụm (`PF = 0.55–0.92`). Khép lại hoàn toàn giả thuyết đánh ngược sóng Á–Âu thuần túy trên Vàng.
4. **H4 (`Index 15m/30m Opening Auction`) là ví dụ điển hình của quá khớp Cluster A:** `US100` và `US500` mở cửa thuận gap 15 phút đầu cho `+6.23 R` và `+2.30 R` trên `2018–2021` nhưng đảo chiều âm ngay lập tức trên Cluster B mù `2022–2024` (`-5.63 R` và `-2.17 R`).
5. **Giá trị thực tiễn cho `PORT_7E`:** Kết quả `0/24` củng cố kết luận rằng `PORT_7E` hiện hành (`E4_US100_SESS40`, `E5_US100_RS1130`, `S7_XAU_EXP120`) đã khai thác đúng các cấu trúc bền vững nhất trên Gold & Indices intraday; không nên cố nhồi thêm tín hiệu nhiễu làm giảm Calmar danh mục.
