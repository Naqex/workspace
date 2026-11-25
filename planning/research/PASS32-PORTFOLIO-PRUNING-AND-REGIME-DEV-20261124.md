---
doc_type: research_receipt
date: 2026-11-24
lane: quant-rnd
milestone: M8.2
status: COMPLETE_PROPOSED_V2_CANDIDATE_ONLY
holdout_rows_analysed: 0
order_send_count: 0
m_total_cap: 20
m_total_variants: 12
registry_mutated: false
---

# Pass 32 — Kiểm Định Cắt Tỉa Động Cơ Leave-One-Out (LOO) & Phân Bổ / Điều Tiết Chế Độ Nhân Quả (`m_total = 12 <= 20`, Chỉ Dev `< 2025-01-01`)

- **Ngày thực hiện:** `2026-11-24`
- **Mã nguồn tái lập:** [pass32_portfolio_pruning_and_regime_dev.py](../../tooling/ai-engines/quant_factory/pass32_portfolio_pruning_and_regime_dev.py)
- **Biên nhận máy:** `.runtime/quant-pod-returns/pass32_pruning_regime_summary.json`
- **Khóa bảo vệ Holdout & Registry:**
  - `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA-256 xác nhận nguyên vẹn (`f0a6b43cb205535b...`).
  - **`holdout_rows_analysed = 0`**, **`order_send_count = 0`**, **`PORTFOLIO-REGISTRY.json` không bị sửa đổi**.
  - `pass31_survivors_integrated = []` (Pass 31 cho `0/18` ứng viên vượt cổng Red-Team -> Pass 32 chạy thuần trên `9` động cơ đóng băng `E1..E7, S6, S7`).
- **Quy chuẩn nhân quả tuyệt đối:** Toàn bộ trọng số phân bổ (`Inv-DD`, `HRP`, `ERC`), thứ hạng cắt tỉa LOO (`Top-6`, `Top-7`), và mục tiêu độ biến động (`Vol-Regime Throttle` 20 ngày) **chỉ khớp trên Cluster A (`2018–2021`)**, sau đó đánh giá mù hoàn toàn trên **Cluster B (`2022–2024`)** bằng mô phỏng M1 Prague-reset (`SYMCAP = 1.00%`) + `2.000` đường Numba Block-Bootstrap FTMO Swing 10k (`P1_Balanced 4.0x / P2 2.5x / Funded 1.0x`, `seed = 20261124`).

---

## 1. Kết Luận Tóm Tắt (Trung Thực & Cảnh Báo Cắt Tỉa Quá Khớp)

1. **Cảnh báo cắt tỉa LOO trong mẫu (In-Sample Pruning Trap):** Nếu chỉ chọn theo `Cluster A Calmar` (`2018–2021`), biến thể cắt tỉa **`V09_PRUNED_TOP6_CAUSAL_INVDD`** (bỏ `E6_EURJPY_VOLCOMP`, `E1_USDJPY_TOKYO`, `S7_XAU_EXP120`) đạt đỉnh `Calmar Cl.A = 2.045` — nhưng trên **Cluster B mù (`2022–2024`) sập thảm xuống `Calmar = 0.387` (`Ann +2.84%`, `DD 7.33%`, `CF24 = +88.4 USD`)!** Lý do: chính 3 động cơ chậm trên `2018–2021` lại trở thành **3 động cơ đóng góp lớn nhất toàn danh mục trên `2022–2024`** (`+0.54`, `+0.32`, `+0.31` Calmar LOO).
2. **Đương kim `PORT_7E` đóng băng (`V01_INCUMBENT_PORT7E_BASE`) vẫn là lựa chọn tốt nhất cho sản xuất / Free Trial hiện tại:** Đạt `Ann Cl.B = +9.15%`, `MaxDD = 6.26%`, `Calmar = 1.463`, **vượt P1+P2 nhanh nhất (`4.9 tháng`)** và **`CF24 = +764.4 USD` cao nhất** trong nhóm DD thấp. Ứng viên chọn cứng từ Cluster A (`V09`) **KHÔNG đánh bại được** `PORT_7E` (`beats_7e_b = false`, `beats_9e_b = false`).
3. **Ứng viên nghiên cứu v2 đáng lưu ý (CHỈ ghi nhận nghiên cứu, KHÔNG thay thế `PORT_7E` hiện hành và KHÔNG mở Holdout):** **`V08_PORT9E_CAUSAL_ERC`** (Equal Risk Contribution nhân quả trên cả `9` động cơ, **không cắt tỉa**) đạt **Cluster B mù `Calmar = 1.596`**, `Sharpe = 1.518`, `MaxDD = 5.20%` (`BR1 = 3.3%`, `CF24 = +759.2 USD`) và **Calmar toàn Dev cao nhất (`1.315`)** — vượt trội hẳn `V03_INCUMBENT_PORT9E_INVDD` (`Calmar Cl.B = 0.982`) vì `ERC` không dồn quá nặng `0.943%` vào vệ tinh `S6_FX_USD_BSK` như `Inv-DD`.

---

## 2. Kiểm Toán Đóng Góp Biên Leave-One-Out (LOO) Trên `9` Động Cơ Đóng Băng

*(Cột `LOO ΔCalmar` = `Calmar(PORT_9E) - Calmar(PORT_9E \ {e})`: giá trị **dương** nghĩa là giữ động cơ giúp danh mục tốt hơn; giá trị **âm** nghĩa là động cơ đó kéo tụt Calmar danh mục.)*

| Động Cơ | Vai Trò | Lệnh `A / B` | Độc Lập Cl.A (`Ann / DD / Calmar`) | **Độc Lập Cl.B (`Ann / DD / Calmar`)** | `r(Rest)` Cl.A | `LOO ΔCalmar` Cl.A | **`LOO ΔCalmar` Cl.B** | `LOO ΔAnn` Cl.B | `LOO ΔDD` Cl.B | Nhận Xét Chế Độ |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `E1_USDJPY_TOKYO` | `CORE_7E` | `768 / 669` | `+1.32% / 15.23% / 0.09` | **`+9.95% / 11.47% / 0.87`** | `+0.139` | `+0.030` | **`+0.540`** | **`+2.88%`** | **`-0.69%`** | Chậm Cl.A -> **Số 1 Cl.B!** |
| `E2_USDJPY_EXP80` | `CORE_7E` | `261 / 237` | `+2.19% / 3.47% / 0.63` | `+1.10% / 3.51% / 0.31` | `+0.106` | **`+0.660`** | `+0.140` | `+1.31%` | `+0.30%` | Trụ cột bền bỉ cả A & B |
| `E3_GBPUSD_VH` | `CORE_7E` | `92 / 79` | `+0.96% / 2.21% / 0.43` | `+1.03% / 1.99% / 0.52` | `+0.068` | `+0.190` | `-0.030` | `+1.24%` | `+0.94%` | Độc lập ổn định cả A & B |
| `E4_US100_SESS40` | `CORE_7E` | `185 / 184` | `+0.97% / 3.22% / 0.30` | `+0.80% / 3.11% / 0.26` | **`-0.011`** | `+0.230` | `+0.210` | `+0.80%` | **`-0.47%`** | Cắt DD & trực giao tuyệt đối |
| `E5_US100_RS1130` | `CORE_7E` | `134 / 89` | `+0.95% / 2.38% / 0.40` | `+0.84% / 2.50% / 0.34` | `+0.103` | `+0.070` | `+0.210` | `+0.84%` | **`-0.45%`** | Đóng góp đều & giảm DD |
| `E6_EURJPY_VOLCOMP` | `CORE_7E` | `62 / 56` | `+0.07% / 2.82% / 0.03` | **`+1.22% / 1.73% / 0.70`** | `+0.096` | `+0.060` | **`+0.310`** | `+1.22%` | **`-0.70%`** | Chậm Cl.A -> **Số 3 Cl.B!** |
| `E7_USDJPY_NY10ET` | `CORE_7E` | `61 / 35` | `+0.05% / 1.48% / 0.04` | `+0.57% / 1.06% / 0.53` | `+0.065` | `+0.150` | `+0.050` | `+0.56%` | `+0.16%` | Thưa lệnh nhưng dương cả A & B |
| `S6_FX_USD_BSK` | `SATELLITE` | `93 / 71` | **`+1.15% / 1.25% / 0.92`** | **`-0.33% / 2.53% / -0.13`** | `+0.123` | `+0.300` | **`-0.390`** | `-0.66%` | `+1.00%` | **Mạnh nhất Cl.A -> Âm duy nhất Cl.B!** |
| `S7_XAU_EXP120` | `SATELLITE` | `97 / 76` | `+0.27% / 2.22% / 0.12` | **`+1.00% / 1.46% / 0.68`** | `+0.132` | `-0.010` | **`+0.320`** | `+1.00%` | **`-0.93%`** | Chậm Cl.A -> **Số 2 Cl.B!** |

---

## 3. So Sánh `12` Biến Thể Phân Bổ, Cắt Tỉa & Điều Tiết Biến Động Nhân Quả (`m_total = 12 <= 20`)

*(Mọi trọng số & mục tiêu vol khớp hoàn toàn trên `2018–2021`; kiểm định mù trên `2022–2024`; MC FTMO Swing 10k `P1=4.0x / P2=2.5x / Funded=1.0x`, `2.000` đường, `seed=20261124`.)*

| Mã Biến Thể | Mô Tả (`SYMCAP 1.00%`) | Cl.A `Calmar` (`DD`) | **Cl.B Mù `Ann`** | **Cl.B `PeakDD`** | **Cl.B `Calmar`** | **Cl.B `Sharpe`** | Dev All `Calmar` | **MC Cl.B `Pass 6m` / `Med Pass`** | **MC Cl.B `BR1%` / `CF24`** | Đánh Giá |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **`V01_INCUMBENT_PORT7E_BASE`** | Đương kim `PORT_7E` registry | `1.399` (`4.84%`) | **`+9.15%`** | `6.26%` | **`1.463`** | `1.353` | `1.246` | **`43.1% / 4.9m`** | `11.4% /` **`+764 USD`** | **ĐƯƠNG KIM GIỮ NGUYÊN** |
| `V02_INCUMBENT_PORT7E_INVDD` | `PORT_7E` Causal Cl.A Inv-DD | `1.495` (`3.59%`) | `+7.61%` | `5.78%` | `1.316` | `1.484` | `1.095` | `43.9% / 5.6m` | **`2.2%`** `/ +708 USD` | Đương kim an toàn cao |
| `V03_INCUMBENT_PORT9E_INVDD` | `PORT_9E` Causal Cl.A Inv-DD | `1.713` (`3.97%`) | `+6.20%` | `6.31%` | `0.982` | `1.139` | `1.036` | `35.9% / 5.8m` | `7.4% / +465 USD` | Bị `S6` (`0.94%`) kéo tụt |
| `V04_PORT9E_EQUAL_RISK` | `9E` Equal Risk (`0.50%`/engine) | `0.792` (`10.33%`) | `+16.20%` | `12.70%` | `1.276` | `1.307` | `0.915` | `47.0% / 4.9m` | `33.1% / +1434 USD` | `PeakDD 12.7%` vượt trần 10%! |
| `V05_PORT7E_EQUAL_RISK` | `7E` Equal Risk (`0.50%`/engine) | `0.660` (`10.24%`) | `+15.54%` | `11.75%` | `1.322` | `1.290` | `0.895` | `46.9% / 5.0m` | `31.2% / +1421 USD` | `PeakDD 11.8%` vượt trần 10%! |
| `V06_PORT9E_CAUSAL_HRP` | `9E` Causal Cl.A HRP | `1.173` (`3.28%`) | `+6.01%` | **`4.11%`** | `1.462` | `1.352` | `1.161` | `30.8% / 7.6m` | **`1.1%`** `/ +501 USD` | DD cực thấp nhưng qua P1 chậm |
| `V07_PORT7E_CAUSAL_HRP` | `7E` Causal Cl.A HRP | `0.785` (`3.36%`) | `+5.40%` | `5.14%` | `1.050` | `1.377` | `0.743` | `25.0% / 8.3m` | `0.4% / +435 USD` | Quá thận trọng (`E1=0.015%`) |
| **`V08_PORT9E_CAUSAL_ERC`** | **`9E` Causal Cl.A ERC** | `1.406` (`4.09%`) | `+8.31%` | **`5.20%`** | **`1.596`** | **`1.518`** | **`1.315`** | **`44.0% / 5.6m`** | **`3.3% / +759 USD`** | **Ứng viên v2 nghiên cứu #1** |
| `V09_PRUNED_TOP6_CAUSAL_INVDD` | Cắt 3 engine yếu Cl.A + Inv-DD | **`2.045`** (`3.04%`) | `+2.84%` | `7.33%` | **`0.387`** | `0.621` | `0.651` | `18.7% / 7.2m` | `9.2% / +88 USD` | **LOẠI — Quá khớp cắt tỉa!** |
| `V10_PRUNED_TOP7_CAUSAL_HRP` | Cắt 2 engine yếu Cl.A + HRP | `1.268` (`2.68%`) | `+4.85%` | `4.12%` | `1.177` | `1.273` | `0.976` | `20.9% / 8.9m` | `0.4% / +355 USD` | Kém hơn `V06` không cắt tỉa |
| `V11_PORT7E_CAUSAL_VOL_THROTTLE` | `PORT_7E` + Vol Throttle 20d | `1.290` (`5.13%`) | `+8.64%` | `6.39%` | `1.352` | `1.278` | `1.171` | `38.9% / 5.2m` | `11.3% / +669 USD` | Không cải thiện `V01` |
| `V12_PORT9E_HRP_VOL_THROTTLE` | `9E` HRP + Vol Throttle 20d | `1.002` (`3.99%`) | `+7.40%` | `4.75%` | **`1.556`** | `1.413` | `1.148` | `30.3% / 7.2m` | `8.4% / +542 USD` | Nâng Calmar HRP nhưng chậm P1 |

---

## 4. Bài Học Quản Trị Danh Mục & Khuyến Nghị Cho Kiến Trúc v2

1. **Tuyệt đối không cắt tỉa động cơ dựa trên hiệu suất 3–4 năm gần nhất:** Bằng chứng LOO chỉ ra tính luân phiên chế độ cực mạnh — `E1`, `E6`, `S7` yếu trên `2018–2021` nhưng kéo toàn bộ danh mục đi lên trên `2022–2024`, trong khi `S6` đảo ngược đúng chiều ngược lại. Cắt bỏ động cơ đang "ngủ đông" chính là nguyên nhân khiến `V09` sụp đổ từ `Calmar 2.045 -> 0.387`.
2. **Tại sao `V08_PORT9E_CAUSAL_ERC` vượt trội `V03_INCUMBENT_PORT9E_INVDD`:** Trọng số `Inv-DD` nhạy cảm quá mức với MaxDD một mẫu đơn lẻ trên Cluster A (đẩy `S6_FX_USD_BSK` lên `0.943%` vì nó tình cờ có DD `1.25%` ở `2018–2021`), trong khi `ERC` cân bằng phương sai + hiệp phương sai toàn ma trận 9 động cơ (`E1=0.099%, E2=0.280%, E3=0.442%, E4=0.416%, E5=0.482%, E6=0.769%, E7=0.979%, S6=0.513%, S7=0.520%`), cắt giảm `PeakDD Cl.B` từ `6.31% -> 5.20%` và nâng `Calmar Cl.B` từ `0.982 -> 1.596` (`BR1 = 3.3%`).
3. **Vol-Regime Throttle 20 ngày (`V11`) không giúp ích cho `PORT_7E`:** Bởi vì các động cơ cốt lõi giao dịch thưa (`35–260` lệnh/cụm) nên độ lệch chuẩn lợi nhuận 20 ngày chứa nhiều nhiễu lấy mẫu hơn là tín hiệu chế độ biến động; giữ nguyên quy tắc `AMBER/RED` dựa trên Equity Drawdown của `Naqex_AccountOrchestrator` đơn giản và hiệu quả hơn.
4. **Hành động được đề xuất:**
   - **Sản xuất / Free Trial ngay lập tức:** Giữ nguyên **`PORT_7E` (`V01` / `V02`)** đã niêm phong và đã qua kiểm định Holdout một lần duy nhất — không thay đổi bất kỳ tệp `.set` hay `PORTFOLIO-REGISTRY.json` nào.
   - **Hồ sơ nghiên cứu v2 (tương lai sau 90 ngày Demo/Live):** Lưu **`V08_PORT9E_CAUSAL_ERC`** làm ứng viên nâng cấp trọng số v2 cho kỳ review quý tiếp theo (chỉ kiểm chứng trên dữ liệu forward thực tế mới phát sinh, không dùng lại Holdout 2025–2026 để tối ưu).
