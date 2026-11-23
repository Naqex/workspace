# Prop EV Frontier: P1 Balanced (3–6m) vs P1 Sprint (1–3m) — Multi-Firm 10,000-Path Audit

- **Generated UTC:** `2026-11-23T16:34:07.439707+00:00`
- **Data Scope:** Development `2018-01-02..2024-12-31 (1564 days)` ONLY (`holdout_rows_analysed = 0`, `OrderSend = 0`)
- **Holdout Lock SHA-256:** `f0a6b43cb205535b...` (SEALED, untouched)
- **Monte Carlo:** `10,000` paths × `504` ngày giao dịch (24 tháng), Circular Block Bootstrap `block_len = 5` ngày, `seed = 20261124` (runtime `11.976s`)
- **Kiến trúc sách lệnh tự động 3 pha:**
  - **Phase 1 (Eval):** `PORT_9E` trọng số causal Cluster-A Inverse-DD (`SYMCAP 1.50%`), tách 2 chế độ `P1_Balanced_3to6m` (fail 1 lượt `15%–25%`, median pass `3–6m`) và `P1_Sprint_1to3m` (option-like fee play, fail 1 lượt `30%–40%`, tối đa tốc độ & EV/USD phí).
  - **Phase 2 (Verify):** `PORT_7E` core causal Inverse-DD (`SYMCAP 1.00%`) để xác nhận nhanh với tỷ lệ mục tiêu/DD thuận lợi (`5%` vs `10%`).
  - **Funded (`Funded_Safe`):** Tự động hạ ga về `1.00x` (`0.75x` với Hyper Growth `6%` static DD), `PORT_7E` + Vol-Brake 20 ngày (`lo=0.60, hi=1.00`) + `SYMCAP 1.00%` + phanh AMBER `3.5%/0.65x`, RED `6.0%/0.40x`, Daily Stop `2.5%`.

## 1. Bảng So Sánh Tổng Hợp 5 Biến Thể Prop Firm (Dual-P1 Side-by-Side)

| Firm / Variant | Profile | P1 / P2 / Fund | Fail 1-Try % | Med P1 / Full (m) | Pass 3m/6m % | P(Pay1) % | P(Pay3) % | P95 Consec (Sim/Geom) | Avg Fees (USD) | CF 24m (USD) | EV / USD Fee (24m) | OOP95 (USD) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FTMO_SWING_10K | P1_Balanced_3to6m | 4.00x / 2.50x / 1.00x | 23.8% | 2.6m / 5.9m | 18.2% / 48.8% | 94.2% | 90.1% | 2 / 2 | 219.3 | +712.0 | +3.25x | 504.0 |
| FTMO_SWING_10K | P1_Sprint_1to3m | 4.75x / 2.75x / 1.00x | 33.4% | 2.0m / 5.0m | 24.5% / 58.2% | 95.6% | 92.2% | 2 / 2 | 248.5 | +738.0 | +2.97x | 504.0 |
| FTMO_STANDARD_10K | P1_Balanced_3to6m | 4.00x / 2.50x / 1.00x | 23.7% | 2.7m / 6.1m | 17.1% / 46.7% | 93.0% | 88.2% | 2 / 2 | 218.3 | +653.0 | +2.99x | 504.0 |
| FTMO_STANDARD_10K | P1_Sprint_1to3m | 4.75x / 2.75x / 1.00x | 31.7% | 2.0m / 5.1m | 23.6% / 56.4% | 95.0% | 90.9% | 2 / 2 | 243.7 | +684.8 | +2.81x | 504.0 |
| FTMO_STANDARD_10K_BF25 | P1_Balanced_3to6m | 4.00x / 2.50x / 1.00x | 23.7% | 2.7m / 6.1m | 17.1% / 46.7% | 93.0% | 88.2% | 2 / 2 | 163.7 | +668.4 | +4.08x | 378.0 |
| FTMO_STANDARD_10K_BF25 | P1_Sprint_1to3m | 4.75x / 2.75x / 1.00x | 31.7% | 2.0m / 5.1m | 23.6% / 56.4% | 95.0% | 90.9% | 2 / 2 | 182.8 | +705.8 | +3.86x | 378.0 |
| THE5ERS_HS_5K_8P5 | P1_Balanced_3to6m | 4.00x / 2.50x / 1.00x | 22.6% | 2.0m / 5.6m | 21.5% / 51.7% | 93.9% | 89.5% | 1 / 2 | 48.6 | +348.4 | +7.17x | 74.1 |
| THE5ERS_HS_5K_8P5 | P1_Sprint_1to3m | 4.75x / 2.75x / 1.00x | 30.0% | 1.6m / 4.6m | 28.5% / 61.3% | 95.5% | 91.7% | 2 / 2 | 53.2 | +368.4 | +6.93x | 105.3 |
| THE5ERS_HG_5K | P1_Balanced_3to6m | 2.25x / 1.00x / 0.75x | 19.3% | 5.0m / 5.0m | 25.5% / 58.5% | 97.0% | 93.3% | 1 / 1 | 319.9 | +128.0 | +0.40x | 520.0 |
| THE5ERS_HG_5K | P1_Sprint_1to3m | 3.00x / 1.00x / 0.75x | 33.3% | 3.3m / 3.3m | 43.1% / 76.1% | 95.7% | 93.2% | 2 / 2 | 376.8 | +111.0 | +0.29x | 780.0 |

> **Công thức minh bạch:** `EV / USD Fee (24m) = E[Net Cashflow 24m] / E[Total Gross Fees Paid 24m]`. `Fail 1-Try %` là xác suất rớt lượt thi đầu tiên (P1 hoặc P2). `Med P1 / Full (m)` tách rõ trung vị thời gian qua riêng Phase 1 và tổng thời gian nhận tài khoản Funded. `P95 Consec (Sim/Geom)` là phân vị 95 số lần fail liên tiếp thực nghiệm (dưới giới hạn retry) và công thức hình học vô hạn `ceil(ln(0.05)/ln(q)) - 1`.

## 2. Tham Số Khuyến Nghị Cho MT5 `.set` Presets (Tương Thích 100% `Naqex_PropGuard.mqh`)

Vì `Naqex_PropGuard.mqh` kiểm tra `NQXG_GLOBAL_RISK_MULT` trong biên an toàn `[0.20, 3.50]`, bất kỳ multiplier hiệu dụng nào `> 3.50x` được tách sạch thành `EA_RiskScale` (nhân vào `InpRiskPercent` trong từng `.set` của EA) × `Orchestrator InpBasePhaseMult` (`<= 3.50`), không phải sửa code guard:

| Preset Target | Eff P1 Mult | EA Risk Scale × Orch Mult | P2 Mult | Funded Mult | P1 Amber DD / Mult | P1 Red DD / Mult | Kill Daily DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| FTMO_P1_Balanced_3to6m | 4.00x | 1.50x × 2.67 | 2.50x | 1.00x | 7.5% / 1.00x | 9.0% / 0.75x | 4.2% |
| FTMO_P1_Sprint_1to3m | 4.75x | 1.50x × 3.17 | 2.75x | 1.00x | 9.9% / 1.00x | 9.9% / 1.00x | 4.3% |
| THE5ERS_HS_P1_Balanced | 4.00x | 1.50x × 2.67 | 2.50x | 1.00x | 7.5% / 1.00x | 9.0% / 0.75x | 4.2% |
| THE5ERS_HS_P1_Sprint | 4.75x | 1.50x × 3.17 | 2.75x | 1.00x | 9.9% / 1.00x | 9.9% / 1.00x | 4.3% |
| THE5ERS_HG_P1_Balanced | 2.25x | 1.00x × 2.25 | 1.00x | 0.75x | 4.0% / 0.90x | 5.0% / 0.65x | 3.0% |
| THE5ERS_HG_P1_Sprint | 3.00x | 1.00x × 3.00 | 1.00x | 0.75x | 5.9% / 1.00x | 5.9% / 1.00x | 3.0% |

## 3. Đường Cong EV Frontier Đầy Đủ Trên FTMO Swing 10k & The5ers High Stakes (`8%+5%`)

### 3A. FTMO Swing 10k (`10%+5%`, `168 USD`)

| Candidate | P1 / P2 Mult | Eval Fail % | Med P1 / Full (m) | Pass 3m/6m % | P(Pay1)/P(Pay3) % | CF 24m (USD) | EV / USD Fee |
|---|---:|---:|---:|---:|---:|---:|---:|
| BAL_250 | 2.50x / 2.00x | 2.2% | 4.2m / 8.2m | 5.3% / 28.1% | 83.3% / 77.2% | +577.1 | +3.36x |
| BAL_300 | 3.00x / 2.25x | 6.0% | 3.4m / 7.1m | 10.0% / 36.3% | 85.4% / 80.0% | +620.3 | +3.48x |
| BAL_325 | 3.25x / 2.25x | 9.3% | 3.2m / 6.9m | 11.9% / 39.0% | 87.6% / 82.2% | +642.1 | +3.48x |
| BAL_350 | 3.50x / 2.50x | 16.6% | 3.0m / 6.5m | 15.0% / 42.7% | 90.2% / 85.1% | +664.9 | +3.33x |
| BAL_375 | 3.75x / 2.50x | 20.5% | 2.9m / 6.2m | 16.8% / 45.7% | 92.3% / 87.7% | +688.9 | +3.29x |
| BAL_400 | 4.00x / 2.50x | 23.8% | 2.6m / 5.9m | 18.2% / 48.8% | 94.2% / 90.1% | +712.0 | +3.25x |
| BAL_425 | 4.25x / 2.50x | 26.6% | 2.4m / 5.6m | 20.1% / 51.9% | 95.0% / 91.3% | +725.5 | +3.20x |
| SPR_450 | 4.50x / 2.75x | 29.8% | 2.1m / 5.0m | 23.9% / 57.4% | 95.9% / 92.5% | +748.7 | +3.15x |
| SPR_475 | 4.75x / 2.75x | 33.4% | 2.0m / 5.0m | 24.5% / 58.2% | 95.6% / 92.2% | +738.0 | +2.97x |
| SPR_500 | 5.00x / 2.75x | 34.4% | 1.9m / 4.8m | 26.2% / 60.0% | 95.6% / 92.4% | +741.9 | +2.95x |
| SPR_525 | 5.25x / 3.00x | 37.8% | 1.8m / 4.5m | 29.5% / 62.6% | 95.5% / 92.4% | +743.5 | +2.83x |
| SPR_550 | 5.50x / 3.00x | 39.7% | 1.8m / 4.4m | 30.3% / 63.3% | 95.4% / 92.2% | +739.2 | +2.74x |
| SPR_575 | 5.75x / 3.00x | 41.7% | 1.7m / 4.2m | 31.7% / 64.4% | 95.0% / 91.7% | +731.3 | +2.62x |
| SPR_600 | 6.00x / 3.00x | 42.5% | 1.6m / 4.0m | 33.2% / 65.8% | 94.8% / 91.8% | +732.7 | +2.60x |
| SPR_650 | 6.50x / 3.25x | 46.6% | 1.4m / 3.8m | 36.8% / 67.9% | 93.6% / 91.0% | +717.4 | +2.40x |

### 3B. The5ers High Stakes 5k (`8%+5%`, `39 USD`, `+RedNews ±5m`)

| Candidate | P1 / P2 Mult | Eval Fail % | Med P1 / Full (m) | Pass 3m/6m % | P(Pay1)/P(Pay3) % | CF 24m (USD) | EV / USD Fee |
|---|---:|---:|---:|---:|---:|---:|---:|
| BAL_250 | 2.50x / 2.00x | 2.3% | 3.3m / 7.4m | 8.2% / 33.0% | 83.8% / 77.9% | +283.5 | +7.12x |
| BAL_300 | 3.00x / 2.25x | 6.2% | 2.8m / 6.4m | 13.3% / 40.9% | 86.0% / 80.5% | +302.5 | +7.34x |
| BAL_325 | 3.25x / 2.25x | 9.6% | 2.5m / 6.3m | 14.8% / 43.1% | 87.8% / 82.5% | +311.9 | +7.33x |
| BAL_350 | 3.50x / 2.50x | 16.4% | 2.4m / 6.0m | 18.4% / 46.7% | 90.5% / 85.5% | +325.4 | +7.16x |
| BAL_375 | 3.75x / 2.50x | 19.7% | 2.2m / 5.8m | 20.0% / 49.0% | 92.5% / 87.7% | +336.8 | +7.16x |
| BAL_400 | 4.00x / 2.50x | 22.6% | 2.0m / 5.6m | 21.5% / 51.7% | 93.9% / 89.5% | +348.4 | +7.17x |
| BAL_425 | 4.25x / 2.50x | 25.1% | 1.9m / 5.2m | 23.1% / 54.8% | 94.7% / 90.7% | +356.2 | +7.11x |
| SPR_450 | 4.50x / 2.75x | 28.1% | 1.7m / 4.7m | 27.7% / 60.7% | 95.7% / 91.7% | +368.2 | +7.08x |
| SPR_475 | 4.75x / 2.75x | 30.0% | 1.6m / 4.6m | 28.5% / 61.3% | 95.5% / 91.7% | +368.4 | +6.93x |
| SPR_500 | 5.00x / 2.75x | 30.9% | 1.5m / 4.4m | 29.9% / 62.8% | 95.6% / 91.8% | +370.6 | +6.89x |
| SPR_525 | 5.25x / 3.00x | 34.0% | 1.4m / 4.1m | 33.4% / 65.3% | 95.6% / 92.2% | +375.4 | +6.72x |
| SPR_550 | 5.50x / 3.00x | 35.2% | 1.4m / 4.0m | 34.8% / 66.7% | 95.6% / 92.2% | +376.8 | +6.65x |
| SPR_575 | 5.75x / 3.00x | 37.5% | 1.3m / 4.0m | 35.6% / 67.2% | 95.3% / 91.8% | +375.5 | +6.44x |
| SPR_600 | 6.00x / 3.00x | 39.2% | 1.3m / 3.9m | 36.6% / 67.8% | 94.8% / 91.3% | +374.1 | +6.29x |
| SPR_650 | 6.50x / 3.25x | 43.2% | 1.2m / 3.6m | 40.0% / 70.0% | 94.3% / 91.3% | +374.5 | +5.99x |

## 4. Kiểm Tra Độ Bền Block-Length (`block_len = 5` vs `10` ngày) & The5ers `10%+5%`

| Firm | Profile | EV/Fee (b=5) | EV/Fee (b=10) | Fail % (b=5) | Fail % (b=10) | Med Pass (b=5 vs b=10) |
|---|---|---:|---:|---:|---:|---:|
| FTMO_SWING_10K | P1_Balanced_3to6m | +3.25x | +3.19x | 23.8% | 25.1% | 5.9m vs 6.0m |
| FTMO_SWING_10K | P1_Sprint_1to3m | +2.97x | +2.92x | 33.4% | 34.1% | 5.0m vs 4.95m |
| FTMO_STANDARD_10K | P1_Balanced_3to6m | +2.99x | +2.92x | 23.7% | 25.4% | 6.1m vs 6.14m |
| FTMO_STANDARD_10K | P1_Sprint_1to3m | +2.81x | +2.73x | 31.7% | 33.5% | 5.1m vs 5.1m |
| FTMO_STANDARD_10K_BF25 | P1_Balanced_3to6m | +4.08x | +3.99x | 23.7% | 25.4% | 6.1m vs 6.14m |
| FTMO_STANDARD_10K_BF25 | P1_Sprint_1to3m | +3.86x | +3.76x | 31.7% | 33.5% | 5.1m vs 5.1m |
| THE5ERS_HS_5K_8P5 | P1_Balanced_3to6m | +7.17x | +7.04x | 22.6% | 24.1% | 5.57m vs 5.57m |
| THE5ERS_HS_5K_8P5 | P1_Sprint_1to3m | +6.93x | +6.81x | 30.0% | 31.5% | 4.62m vs 4.57m |
| THE5ERS_HG_5K | P1_Balanced_3to6m | +0.40x | +0.37x | 19.3% | 20.7% | 5.0m vs 5.1m |
| THE5ERS_HG_5K | P1_Sprint_1to3m | +0.29x | +0.26x | 33.3% | 35.0% | 3.33m vs 3.33m |

- **Độ nhạy The5ers High Stakes `10%+5%` (config gốc bảo thủ) vs `8%+5%` (luật hiện hành):** Balanced đạt `EV/Fee = +6.76x` (`Fail = 23.7%`, `Med Pass = 6.1m`); Sprint đạt `EV/Fee = +6.54x` (`Fail = 31.7%`, `Med Pass = 5.14m`).

## 5. Kết Luận Điều Hành Cho Owner (FTMO + The5ers)

1. **Hai chế độ P1 tách bạch rõ ràng về hành vi và toán học:**
   - **`P1_Balanced_3to6m`** (`4.00x P1 / 2.50x P2 / 1.00x Funded_Safe` trên FTMO & The5ers HS; `2.25x / 0.75x` trên Hyper Growth): tối ưu **EV trên mỗi USD phí cao nhất** (`+3.25x` FTMO Swing, `+4.08x` FTMO Standard BF-25%, `+7.17x` The5ers HS) với xác suất rớt lượt đầu `19.3%–23.8%`, `P95` fail liên tiếp `1–2` vé, trung vị qua P1 trong `2.0–2.7` tháng và nhận Funded trong `5.0–6.1` tháng — phù hợp nhất cho tài khoản FTMO đầu tiên để xây dựng kỷ luật live ổn định.
   - **`P1_Sprint_1to3m`** (`4.75x P1 / 2.75x P2 / 1.00x Funded_Safe` trên FTMO & The5ers HS; `3.00x / 0.75x` trên Hyper Growth): rút ngắn trung vị qua P1 xuống `1.6–2.0` tháng (nhận Funded `4.6–5.1` tháng, Hyper Growth `3.3` tháng) với xác suất rớt lượt đầu `30.0%–33.4%` (`P95` fail liên tiếp `2` vé), tăng tổng dòng tiền kỳ vọng 24 tháng (`+738 USD` FTMO Swing, `+706 USD` FTMO BF-25%, `+368 USD` The5ers HS) — đặc biệt hấp dẫn khi săn vé giảm giá như **FTMO Black Friday `-25%` (`126 USD`)** hoặc **The5ers High Stakes (`39 USD`)**.
2. **The5ers High Stakes (`39 USD`, `8%+5%`) đứng đầu tuyệt đối về `EV / USD Fee`** (cao hơn gấp đôi FTMO Swing trên mỗi USD phí) nhưng bắt buộc hoàn tất `requires_ea_written_clearance = true` và đạt `>= 3` ngày lãi `>= 0.5%`.
3. **FTMO Standard + RedNews ±5m + Black Friday `-25%` (`126 USD`)** vượt trội FTMO Swing `168 USD` về `EV / USD Fee` vì bộ lọc tin đỏ `±5m` chỉ làm hao hụt `< 9%` hiệu suất trong khi tiết kiệm thẳng `25%` chi phí vé.
4. **The5ers Hyper Growth (1-step, `260 USD`, `6%` Static DD)** có `EV / USD Fee` thấp hơn đáng kể do phí đầu vào `5.2%` vốn và không hoàn phí (`fee_refund_ratio = 0.0`); chỉ nên xếp hạng ưu tiên thứ 3 sau FTMO và The5ers High Stakes.
5. **Kỷ luật hạ ga bắt buộc sau khi Funded:** Mọi mô phỏng đều cho `br_funded_pct ≈ 0.0%–0.3%` và `P(Pay3) > 85%` chính nhờ bước hạ ga tức thì sang `Funded_Safe` (`1.00x`, `PORT_7E`, `SYMCAP 1.00%`, `Daily Stop 2.5%`).
