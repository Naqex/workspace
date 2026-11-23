---
doc_type: research_receipt
date: 2026-11-24
lane: quant-rnd
milestone: M8.1
status: COMPLETE_ZERO_PASS_REDTEAM_KILLED
holdout_rows_analysed: 0
order_send_count: 0
m_total_cap: 20
m_total_tested: 18
---

# Pass 31 — Khám Phá Intraday Có Hội Đồng Red-Team Kiểm Soát (`m_total = 18 <= 20`, Chỉ Dev `< 2025-01-01`)

- **Ngày thực hiện:** `2026-11-24`
- **Mã nguồn tái lập:** [pass31_redteam_discovery_dev.py](../../tooling/ai-engines/quant_factory/pass31_redteam_discovery_dev.py)
- **Tích hợp Hội Đồng Nghiên Cứu (`M2.3`):** [research_council.py](../../tooling/ai-engines/quant_factory/research_council.py) (`Proposer HypothesisCard` → `SkepticalRedTeamCritic` 6 cổng fail-closed + chữ ký `verdict_sha256`).
- **Biên nhận máy:** `.runtime/quant-pod-returns/pass31_redteam_summary.json`
- **Khóa bảo vệ Holdout `2025–2026`:**
  - `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA-256 xác nhận nguyên vẹn (`f0a6b43cb205535b...`).
  - **`holdout_rows_analysed = 0`**, **`order_send_count = 0`**, **`m_total = 18 <= 20`** (tuân thủ nghiêm ngặt trần `m_total_cap = 20`).
- **Tiêu chuẩn loại cứng (`PASS31_KILL_CRITERIA` + Matched-Hold Null):**
  - `G0`: Holdout niêm phong (`0` dòng) & thẻ giả thuyết có cơ chế kinh tế/đối tác rõ ràng;
  - `G1`: `BH-FDR q_all <= 0.10` trên toàn bộ `18` giả thuyết;
  - `G2`: `DSR_B >= 0.50` & `Sharpe_B >= 0.40`;
  - `G3`: Dương ở tầng chi phí `2x` (`Double Stress`) và hệ số hòa vốn chi phí `>= 2.00x`;
  - `G4`: Trực giao với `PORT_7E` trên Cluster B (`|r| <= 0.15`, tương quan đuôi `5%` xấu nhất `<= 0.35`);
  - `G5`: `n_B >= 30` và **cùng dấu dương trên cả Cluster A (`2018–2021`) lẫn Cluster B mù (`2022–2024`)**;
  - `G_MH`: Zero-Leakage Matched-Hold Random-Timing Null `p < 0.05`.

---

## 1. Kết Luận Tóm Tắt (`0 / 18` Ứng Viên Vượt Cổng Red-Team)

> **Kết quả:** **`18 / 18` giả thuyết bị `SkepticalRedTeamCritic` loại cứng (`REJECT_KILLED`), `0` ứng viên được chuyển sang ủ (`APPROVE_FOR_INCUBATION`).** Cả 3 họ mới (Nén biến động liên phiên `P30`, Quét thanh khoản/Stop-Run hồi quy `15–30m`, Lan tỏa liên tài sản phiên Mỹ) đều không vượt qua được kiểm định kết hợp giữa **đồng nhất hai cụm A/B**, **chi phí thực M1 Bid/Ask** và **tính trực giao với `PORT_7E`**.

---

## 2. Bảng Phán Quyết Hội Đồng Red-Team Cho Toàn Bộ `18` Giả Thuyết (`m_total = 18`)

*(Mọi `R` ở tầng `FTMO Stress`; `2x R` là `Double Stress`; `BE` là bội số chi phí hòa vốn; `r(7E)` là tương quan Cluster B với `PORT_7E`.)*

| Mã Giả Thuyết | Họ | Tài Sản | Cl.A `2018–2021` (`n`, `R`) | **Cl.B Mù `2022–2024` (`n`, `R`)** | `2x Cost R` (`BE`) | `BH q` | `DSR_B` | `MH p` | `r(7E)` | Phán Quyết Council |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `P31_FA_EURUSD_ASIA_P30_LDN_BRK` | `FA_VOL_COMP` | `EURUSD` | `338 / -6.81` | `246 / +5.27` | `-7.08` (`0.72x`) | `0.139` | `0.046` | `0.136` | `+0.008` | `REJECT_KILLED` (`G1,G2,G3,G5,MH`) |
| `P31_FA_GBPUSD_ASIA_P30_LDN_BRK` | `FA_VOL_COMP` | `GBPUSD` | `329 / +2.56` | `251 / -6.40` | `-7.73` (`0.01x`) | `0.114` | `0.004` | `0.218` | `+0.093` | `REJECT_KILLED` (`G1,G2,G3,G5,MH`) |
| `P31_FA_USDJPY_ASIA_P30_LDN_BRK` | `FA_VOL_COMP` | `USDJPY` | `301 / -8.61` | **`231 / +23.33`** | **`+10.16` (`4.23x`)** | **`0.072`** | `0.491` | **`0.020`** | `+0.229` | **`REJECT_KILLED` (`G2,G4,G5`)** |
| `P31_FA_XAUUSD_ASIA_P30_LDN_BRK` | `FA_VOL_COMP` | `XAUUSD` | `322 / -26.27` | `244 / -13.58` | `-55.56` (`<0`) | `0.549` | `0.001` | `0.844` | `+0.093` | `REJECT_KILLED` (mọi cổng) |
| `P31_FA_US100_MORN_P30_NY_BRK` | `FA_VOL_COMP` | `US100` | `236 / -10.62` | `200 / +3.87` | `-13.28` (`<0`) | `0.108` | `0.101` | `0.216` | `+0.008` | `REJECT_KILLED` (`G1,G2,G3,G5,MH`) |
| `P31_FA_XAUUSD_LDN_P30_NY_BRK` | `FA_VOL_COMP` | `XAUUSD` | `295 / -33.21` | `220 / -3.23` | `-50.71` (`<0`) | `0.448` | `0.023` | `0.810` | `+0.044` | `REJECT_KILLED` (mọi cổng) |
| `P31_FB_EURUSD_ASIA_SWEEP_15M` | `FB_LIQ_SWEEP` | `EURUSD` | `69 / -6.37` | `46 / +1.30` | `-6.27` (`<0`) | `0.667` | `0.056` | `0.519` | `-0.040` | `REJECT_KILLED` (mọi cổng) |
| `P31_FB_GBPUSD_ASIA_SWEEP_15M` | `FB_LIQ_SWEEP` | `GBPUSD` | `52 / -2.83` | `46 / +0.32` | `-3.25` (`<0`) | `0.667` | `0.046` | `0.439` | `-0.045` | `REJECT_KILLED` (mọi cổng) |
| `P31_FB_USDJPY_ASIA_SWEEP_30M` | `FB_LIQ_SWEEP` | `USDJPY` | `93 / -1.40` | `71 / -3.23` | `-6.04` (`<0`) | `0.667` | `0.019` | `0.525` | `-0.122` | `REJECT_KILLED` (mọi cổng) |
| `P31_FB_XAUUSD_ASIA_SWEEP_30M` | `FB_LIQ_SWEEP` | `XAUUSD` | `118 / +0.91` | `98 / -9.83` | `-15.71` (`<0`) | `0.667` | `0.002` | `0.353` | `-0.011` | `REJECT_KILLED` (mọi cổng) |
| `P31_FB_EURUSD_LDN_SWEEP_NY_30M` | `FB_LIQ_SWEEP` | `EURUSD` | `161 / +2.02` | `133 / -2.27` | `-3.47` (`0.92x`) | `0.448` | `0.014` | `0.148` | `-0.082` | `REJECT_KILLED` (mọi cổng) |
| `P31_FB_US100_OR30_SWEEP_15M` | `FB_LIQ_SWEEP` | `US100` | **`102 / +13.17`** | **`86 / -18.02`** | `-7.96` (`<0`) | `0.549` | `0.000` | `0.365` | `+0.017` | **`REJECT_KILLED` (Sập nặng Cl.B!)** |
| `P31_FC_US500_TO_XAU_INV_1015ET` | `FC_SPILLOVER` | `XAUUSD` | `167 / -7.72` | `127 / -1.20` | `-18.41` (`0.06x`) | `0.448` | `0.012` | `0.186` | `+0.070` | `REJECT_KILLED` (mọi cổng) |
| `P31_FC_US100_TO_XAU_ALIGN_1015ET` | `FC_SPILLOVER` | `XAUUSD` | `224 / -24.01` | `181 / -6.34` | `-42.80` (`<0`) | `0.785` | `0.007` | `0.822` | `+0.005` | `REJECT_KILLED` (mọi cổng) |
| `P31_FC_EURUSD_TO_XAU_NY_1330U` | `FC_SPILLOVER` | `XAUUSD` | `404 / -31.66` | `280 / -5.56` | `-56.92` (`<0`) | `0.667` | `0.003` | `0.585` | `+0.110` | `REJECT_KILLED` (mọi cổng) |
| `P31_FC_EURUSD_TO_USDJPY_NY_1330U` | `FC_SPILLOVER` | `USDJPY` | `404 / -3.42` | `281 / +3.75` | `-5.40` (`1.06x`) | `0.155` | `0.034` | `0.078` | `+0.134` | `REJECT_KILLED` (mọi cổng) |
| `P31_FC_US500_TO_USDJPY_1030ET` | `FC_SPILLOVER` | `USDJPY` | `190 / -11.03` | `155 / -3.43` | `-17.45` (`<0`) | `0.667` | `0.002` | `0.685` | `+0.057` | `REJECT_KILLED` (mọi cổng) |
| `P31_FC_XAU_TO_USDJPY_INV_1015ET` | `FC_SPILLOVER` | `USDJPY` | `250 / -7.48` | `216 / -1.10` | `-12.31` (`<0`) | `0.448` | `0.026` | `0.268` | `+0.019` | `REJECT_KILLED` (mọi cổng) |

---

## 3. Phân Tích Red-Team Về 3 Bẫy Kinh Điển Đã Được Chặn Đứng

1. **Bẫy Liquidity Sweep / Stop-Run Reversal (`P31_FB_US100_OR30_SWEEP_15M`) — Thắng lớn `2018–2021` (`+13.17 R`), sập thảm `2022–2024` (`-18.02 R`):** Đây là ví dụ mẫu mực giải thích tại sao các mẫu hình SMC/Liquidity Sweep nổi tiếng trên mạng thường nhìn rất đẹp ở giai đoạn biến động êm hoặc tăng chữ V (`2018–2021`) nhưng gãy hoàn toàn khi thị trường chuyển sang pha có xu hướng vĩ mô mạnh (`2022–2024`). Cả `5/6` biến thể Liquidity Sweep còn lại đều âm tổng trên Dev (`-3.25 R` đến `-15.71 R` ở `2x` phí).
2. **Bẫy Trùng Lặp & Đảo Chế Độ (`P31_FA_USDJPY_ASIA_P30_LDN_BRK`):** Đạt `+23.33 R` trên `2022–2024`, vượt `BH-FDR` (`0.072`), `Matched-Hold` (`0.020`) và `2x Cost` (`BE = 4.23x`), **nhưng `SkepticalRedTeamCritic` vẫn loại cứng vì 3 lỗi độc lập:** (a) lỗ `-8.61 R` trên Cluster A `2018–2021` (thuần túy ăn sóng phân kỳ BoJ hậu-2022), (b) tương quan `r = +0.229 > 0.15` với `PORT_7E` (trùng trực tiếp với `E1_USDJPY_TOKYO` + `E2_USDJPY_EXP80`), và (c) `DSR_B = 0.491 < 0.50`.
3. **Lan Tỏa Liên Tài Sản Đơn Lẻ (`FC_NY_OPEN_SPILLOVER`) không đủ độ lọc nhiễu:** Cả `6/6` quy tắc truyền dẫn đơn cặp (`US500/US100/EURUSD/XAU -> XAU/USDJPY`) đều âm trên Dev (`-5.40 R` đến `-56.92 R` ở `2x` phí). Điều này giải thích tại sao `E7_USDJPY_NY10ET` (đòi hỏi đồng thuận **cả** `US100` lẫn rổ USD đa tiền tệ G6) là ngoại lệ có chọn lọc cao mới sống sót được qua chi phí thực.
4. **Hành động tiếp theo:** Chuyển sang **Pass 32 (`M8.2`)** với `0` ứng viên bổ sung từ Pass 31 — tập trung kiểm định **Leave-One-Out (LOO) pruning** và **phân bổ / điều tiết biến động nhân quả** trên đúng `9` động cơ đã niêm phong của `PORT_7E` / `PORT_9E`.
