---
doc_type: campaign-master-report
title: "Total Offensive #4 (v4.8.1 FINAL) — Báo Cáo Tổng Kết Hybrid AI, Ma Trận Pareto 81 Case & Lộ Trình Top 1% Theo 4 Tầng"
date: 2026-11-28
campaign: "Total Offensive #4 v4.8.1 FINAL"
worker: w4-p3-report
ssot_metrics_path: ".runtime/offensive4/wave4_master_metrics.json"
ssot_metrics_file_sha256: "531db653bb2e4e663515424d611663a953c5476a8aa6bc4d3cc6972aad9d6e27"
ssot_metrics_report_sha256: "4472bde6c5cda71108b79a8f7c21ff7b24be77697cee57dab596be658e4fb5c2"
reconciled_artifact_count: 40
holdout_cutoff_inclusive: "2024-12-31"
holdout_2025_plus_sealed: true
holdout_rows_analysed: 0
order_send_capable: false
order_send_count: 0
spend_vnd: 0
immutables_10_of_10_clean: true
g12_prop_support_nudges: 0
---

# Total Offensive #4 (`v4.8.1 FINAL`) — Hybrid AI, Ma Trận Pareto `81` Case & Lộ Trình Top 1%

**Kết luận hành động ngay:** Toàn bộ **`40/40`** artifact Wave 4 đã đối chiếu khớp **SHA-256** tại SSOT duy nhất `.runtime/offensive4/wave4_master_metrics.json` (`report_sha256: 4472bde6c5cda71108b79a8f7c21ff7b24be77697cee57dab596be658e4fb5c2`) với khóa an toàn cứng: **`Dev <= 2024-12-31`**, **`Holdout 2025+ SEALED`** (`holdout_rows_analysed = 0`), **`OrderSend = 0`**, **`0 VND`**, **`10/10` tệp bất biến sạch**, **`41/41` lõi `quant_core/`**, **`0` `.ex5`** trong `exports/` và `private_vault/`. Tỷ giá SSOT: **`1 USD = 25.765,94 VND`** (`26/11/2026`).

---

## Tổng Quan Điều Hành — Chấm Điểm Top 1% Theo `4` Tầng Inside-Out (Luật 15)

> **Nguyên tắc Inside-Out:** Mỗi tầng chấm theo trần riêng, không lấy trần tầng này chấm sai tầng khác. Toàn bộ số liệu đang ở cấp **Dev / Offline (`<= 2024-12-31`, `0 VND`, `OrderSend = 0`)**, chưa phải kết quả tiền thật.

### Tầng 1 — Bot Thi Quỹ CFD Đơn Lẻ (`PORT_7E v1.03` & `v1.04-ML`)
- **Bằng chứng & bộ chỉ số:** `BACKTEST_DEV_SEALED_LE_2024 + MT5_BUILD_6230_DEV_2024` (`Holdout 2025+ SEALED`, `0` lệnh thật). `PORT_7E 100K 1,0x` (`7` năm Dev): `WR 48,61%` · `RR 1,272` · `EV +0,0486R` · `PF 1,203` · `Max DD 10,78%` (`1,25x` audit) / `5,80%` (`OOF v1.03`) · `Calmar 0,860` · `Sharpe 1,232` · Lãi năm `+9,268%`. MT5 Full-2024 (`10K Funded 1x`): `v1.04-ML` `347` lệnh, `WR 51,87%`, `+639,18 USD` (`+16,47 tr VND`), `PF 1,21`, `BalDD 2,54%`, `EqDD 4,21%`. Pareto `36T` (`1,0x`): `EV/Phí` `+5,147x` (`10 tr`)..`+20,147x` (`100 tr`), cháy Funded `12T` `0,17%–0,44%` (`< 1%`), `Ruin` `0,00%–0,84%` (`< 1%`), `25 tr` `36T = 82,42/0,03/17,55%`.
- **Ngưỡng gãy:** Stress trượt giá **`1,5x`** làm `15/40/60 tr` (cấu hình mạnh) âm trung vị `36T` (`-0,38/-9,10/-10,51 tr`); hòa vốn trượt giá OOF `v1.03` `1,643x` (`v1.04-ML` `1,765x–1,778x`).
- 🔴 **Xấu:** `EV/Phí <= 0x` hoặc cháy Funded `12T > 5%` hoặc `PF < 1,05`.
- 🟡 **Đủ dùng:** `EV/Phí +1x..+2,99x` hoặc cháy Funded `12T` `1%..5%`, `PF 1,10..1,20`.
- 🟢 **Tốt — VỊ TRÍ HIỆN TẠI (`TOT`):** `EV/Phí +3x..+4,99x+`, cháy Funded `12T < 1%` (`0,17%–0,44%`), `Ruin < 1%`, `PF 1,20..1,50`, chờ `Payout #1` `5..14` tháng (hiện `410,2–431,9` ngày).
- 🏆 **Top 1% thực tế:** `EV/Phí >= +5x`, cháy Funded `12T < 1%`, `Ruin < 1%`, `Payout #1` `2..4` tháng, `P(<=0)` `24T < 15%`, xác nhận trên `Holdout 2025+` + tiền thật.
- **Khoảng cách tới Top 1%:** (1) `Payout #1` còn `410,2` ngày (`~13,7` tháng ở `25 tr`) vs `2..4` tháng; (2) `P(<=0)` `24T` thấp nhất `33,11%` (`250 tr`) vs `< 15%`; (3) chưa qua `Holdout 2025+` và gom lệnh FTMO Free Trial (`0` lệnh thật).

### Tầng 2 — Quỹ Futures CME Intraday (`Topstep` / `MFFU` / `TakeProfitTrader` / `Tradeify`)
- **Bằng chứng & bộ chỉ số:** `BACKTEST_DEV_SEALED_LE_2024 + TERMS_VERIFIED_EXECUTION_UNMEASURED` (`10.000` MC, `XẤP XỈ CẤP NGÀY`). Nền `E4/E5` (`1.564` phiên): `WR 52,57%` · `RR 1,194` · `EV/phiên +0,048%` · `PF 1,324` · `Max DD 4,92%` · `Calmar 0,918` · `Sharpe 0,969`. Gói hợp lệ VN tốt nhất (`topstep_100k_combine`, XFA-only): `EV/Phí +1,021x`, trung vị `24T` `+149,95 USD` (`+3,86 tr VND`), `P(<=0) 48,88%`, **cháy Funded `12T` `57,85%`** (`W95 58,90%`), `Payout #1` `516,0` ngày, `24T = 43,56/56,40/0,04%`.
- **Ngưỡng gãy:** `3/4` hãng cấm KYC VN; `Topstep` khóa XFA-only và cháy Funded `32,36%–57,85%` do EOD Trailing DD chặt + phí tháng.
- 🔴 **Xấu — VỊ TRÍ HIỆN TẠI (`XAU_SKIP` — `SKIP`):** `EV/Phí <= 0x` hoặc cháy Funded `12T > 35%` (hiện `57,85%`, `1,021x`, trượt `4/4` cổng).
- 🟡 **Đủ dùng:** `EV/Phí +0,01x..+2,99x` hoặc cháy `12T` `15%..35%`.
- 🟢 **Tốt:** `EV/Phí +3,0x..+4,99x` và cháy `12T <= 15%`.
- 🏆 **Top 1% thực tế:** `EV/Phí >= +5,0x`, cháy `12T < 5%`, `P(<=0) <= 25%`, hợp lệ KYC VN + thực địa.
- **Khoảng cách tới Top 1%:** Kém FTMO `100K` (`6,628x`) `6,5` lần; cháy gấp `3,9` lần trần `15%`; chỉ xét lại khi xây đủ `5–7` động cơ thuần CME + cầu nối ngoài MT5.

### Tầng 3 — Danh Mục Đa Tài Sản Own-Book & Frontier Pod (`Macro ETF` + `Crypto Carry` + `PORT_7E`)
- **Bằng chứng & bộ chỉ số:** `DEV_CLUSTER_A_FROZEN_TO_BLIND_CLUSTER_B_LE_2024` (`27/36` DuckDB, `Holdout 2025+ SEALED`, `0 VND`). Own-Book có khiên (`2020–2024`): `CAGR +6,69%` · `AnnVol 4,83%` · `Sharpe 1,36` · `Sortino 1,24` · `Max DD 8,09%` · `Calmar 0,83` · `4/4` Stress PASS (`2022 DD 7,87%` vs `60/40` `20,69%`, `0` thanh lý). Combined Pod (`2023–2024` Blind Cluster B): **`Sharpe 2,2918–3,8172`**, **`Calmar 2,5994–4,6170`**, `Max DD 0,92%–1,89%`, **tháng đói `45,83% -> 20,83%–29,17%` (`< 30%`)**.
- **Ngưỡng gãy:** Vượt trần `CEX > 25%`; bỏ khiên funding `< 3%`; mở IBKR `< 10.000 USD` (`~257,7 tr`); chưa đạt điểm giao Own-Book `103.159,91 USD` (`~2,66 tỷ VND`).
- 🔴 **Xấu:** `Sharpe < 0,8` hoặc tháng đói `> 45%` hoặc bị thanh lý khi stress.
- 🟡 **Đủ dùng:** `Sharpe 0,8..1,2`, `Calmar 0,6..1,2`, tháng đói `35%..45%`.
- 🟢 **Tốt — VỊ TRÍ HIỆN TẠI (`TOT_CHAM_NGUONG_TOP_1_DEV`):** Vượt ngưỡng Top 1% trên Blind Cluster B Dev (`Sharpe 2,29–3,82`, `Calmar 2,60–4,62`, tháng đói `< 30%`, `|r| < 0,08`), nhưng còn ở giai đoạn Dev.
- 🏆 **Top 1% thực tế:** `Sharpe 2,0..3,0+`, `Calmar >= 2,0`, tháng đói `< 30%`, `CEX <= 25%`, xác nhận `Holdout 2025+` + `>= 12` tháng tiền thật.
- **Khoảng cách tới Top 1%:** (1) Tiến tới điểm giao **`103.159,91 USD` (`~2,66 tỷ VND`)** — quỹ đạo `36T` tối đa mới đạt `53,3%`; (2) xác nhận `F01 + F03` trên `Holdout 2025+` dưới trần cứng `CEX <= 25%`.

### Tầng 4 — Hạ Tầng Live-Ops, Đội Tài Khoản `S0..S7`, Web Cockpit & AI Advisory
- **Bằng chứng & bộ chỉ số:** `OFFLINE_E2E_VERIFIED + LIVE_LOCAL_LOOPBACK_PIT24_PASS` (`OrderSend = 0`, `0 VND`, `2.508/2.508` CI PASS, `0` lỗi `ruff`). `0/57` thiếu `CREATE_NO_WINDOW` (`49` tệp) · FSM `S0..S7` (`19` chuyển pha) + `E1..E6` · Web Cockpit `?view=prop-fleet` (`0 B` tải khởi động, `119.421 B` raw / `31.121 B` gzip, `86/86` Node, `4/4` Playwright, tương phản `16,44:1`, `0` `/api/*`) · AI Radar (`302/468` model `<= 5 USD/tháng`, top `qwen/qwen3.7-flash` **`0,0196 USD/tháng = 500 VND/tháng`** ở tỷ giá Radar `25.500`) · PIT-24 **`24/24 PASS`** · **`28` mã M1 niêm phong** (`16/16` mới = `36,83 triệu` nến).
- **Ngưỡng gãy:** Dùng CLIProxy OAuth cho production thay Official API `<= 5 USD/tháng`; bỏ lỡ thu log Free Trial `08/12`; chạy thật khi Shadow AI chưa đủ `30` ngày (`0/30`).
- 🔴 **Xấu:** Quản lý tay bằng Excel, popup màn hình, không chốt chặn, AI hộp đen.
- 🟡 **Đủ dùng:** Watchdog đơn lẻ và các script rời rạc.
- 🟢 **Tốt — VỊ TRÍ HIỆN TẠI (`TOT_TIEM_CAN_TOP_1`):** Đủ FSM `S0..S7` + `E1..E6`, Web Cockpit, Briefing `4` tầng, `0` popup, PIT-24 `24/24`, `28` M1, AI `< 5 USD/tháng`.
- 🏆 **Top 1% thực tế:** Tầng Tốt + `>= 30` ngày `Prospective Shadow Ledger` + `>= 20–30` lệnh Free Trial sạch trên `naqex-node1` + Official API `<= 5 USD/tháng`.
- **Khoảng cách tới Top 1%:** (1) Đủ `>= 30` ngày cam kết SHA-256 thực địa (bắt đầu `30/11/2026`, hiện `0/30`); (2) gom bằng chứng FTMO Free Trial (`08/12`) + NFP/CPI (`04/12`, `10/12`); (3) chuyển Macro Supervisor sang Official API `<= 5 USD/tháng`.

---

## 1. Tầng 1 — `v1.03` Same-Feed `100,00%` & `v1.04-ML` ONNX / Pure-MQL5

- **Same-Feed Parity `100,00%` (`W4-G02`, `W4-G03`):** Trước Wave 4, so lệch giữa 2 nguồn giá khác nhau chỉ khớp `73,84%–74,44%` (`167–171` lệnh ma). Sau khi xuất **`8` mã FTMO Dev M1** (`22.274.151` nến, `<= 2024-12-31`), đối khớp cùng nguồn Model 1 đạt **`3.320/3.320` lệnh khớp (`100,00%`, `0` lệnh ma, `0` lệnh sót)**, lệch Gross R chỉ `1,27%–1,68%`, và Model 4 Q4/2024 khớp `95,48%` trong `60s`.
- **Đấu trường `v1.04-ML` `5` họ (`W4-G04` — `2/36` thăng hạng):** `24` đặc trưng nhân quả khớp bit, CV `5` nếp (`5` ngày purge + `10` ngày embargo) trên `2.799` lệnh OOF Dev `v1.03` (`WR 49,12%`, `EV +0,0546R`, `PF 1,1666`, `DD 5,80%`, hòa vốn trượt giá `1,643x`):

| Họ mô hình ML | Thử / Đậu | Ứng viên tốt nhất | `Brier Skill` | `ROC-AUC` | `PF (1x)` | `EV/lệnh (1x)` | `Max DD` | Hòa vốn trượt giá | Kết luận |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| **`regime_gmm_jump`** | `7` / **`1`** | `w4_22_gmm_tf_k2_a15` | **`+0,004454`** | `0,541643` | **`1,2524`** | **`+0,0737R`** | `6,35%` | `1,765x` | **`PROMOTE_V104_ML`** |
| **`lightgbm`** *(ONNX)* | `7` / **`1`** | `w4_09_lgbm_tf_d2_n60` | **`+0,002040`** | `0,535361` | **`1,2072`** | **`+0,0610R`** | **`5,71%`** | **`1,778x`** | **`PROMOTE_V104_ML`** |
| `logit_l2` | `7` / `0` | `w4_04_logit_l2_tf_r50p0` | `-0,001250` | `0,536448` | `1,2212` | `+0,0654R` | `4,94%` | `1,827x` | `REJECT_ML_KEEP_V103` |
| `catboost` | `7` / `0` | `w4_18_catboost_tf_d4_i100` | `+0,003503` | `0,535522` | `1,1928` | `+0,0567R` | `6,29%` | `1,649x` | `REJECT_ML_KEEP_V103` |
| `calibrated_bet_sizing` | `8` / `0` | `w4_36_cal_gmm_platt_025_125` | `+0,004881` | `0,543123` | `1,1692` | `+0,0405R` | `4,57%` | `1,653x` | `REJECT_ML_KEEP_V103` |

- **Chứng nhận MT5 `OnnxRun()` & bản vá `W4G05-F01` (`W4-G05`):**
  - Đối khớp **`4` chiều trên `500` mẫu** (`LightGBM Python <-> ORT <-> MT5 OnnxRun() <-> Pure-MQL5`): sai số tối đa **`7,28e-8`** (`<= 1e-5`), đồng thuận **`100%`**, `0` nút `ZipMap`, chặn fail-closed `NaN`/`Inf`.
  - **Vá `W4G05-F01` (`Naqex_Master_Prop7E_v104_ML.mq5:934`):** Trước khi vá, từ chối tín hiệu ML không khóa phiên nên sinh `107` lệnh đuổi trễ + `14` lệnh đảo chiều (lãi Full-2024 tụt còn `+559,44 USD`, thua `v1.03` `-57,43 USD`). Thêm `MarkEngineTraded()` khi `!mlAllowed` xóa sạch (`0` đuổi trễ, `0` đảo chiều), nâng Full-2024 MT5 (`10K Funded 1x`, `Swap 0,00 USD`):

| Cấu hình MT5 Full-2024 (`10K Funded 1x`) | Số lệnh | `Winrate` | Lãi ròng (`USD` / `tr VND`) | Chênh vs `v1.03` | `PF` | `Bal DD` | `Eq DD` |
|---|---:|---:|---:|---:|---:|---:|---:|
| **`v1.03` gốc** *(và `v1.04-ML` tắt lọc)* | `469` | `50,11%` | `+616,87 USD` (`+15,89 tr`) | `0,00 USD` | `1,15` | `3,46%` | `4,09%` |
| **`v1.04-ML` ONNX (`OnnxRun()`)** | **`347`** *(`-26,0%`)* | **`51,87%`** | **`+639,18 USD` (`+16,47 tr`)** | **`+22,31 USD`** | **`1,21`** | **`2,54%`** | `4,21%` |
| **`v1.04-ML` Pure-MQL5** *(khớp từng xu)* | **`347`** *(`-26,0%`)* | **`51,87%`** | **`+639,18 USD` (`+16,47 tr`)** | **`+22,31 USD`** | **`1,21`** | **`2,54%`** | `4,21%` |

- **Cảnh báo trung thực:** Đánh giá nằm trên `CONSUMED_DEV_CLB_TEMPORAL_OOS`; **khoảng tin cậy bootstrap 95% của `Brier Skill` chạm `0`** (`P(BS > 0) = 93,9%` GMM-k2, `68,5%` LGBM-d2) và cải thiện EV tập trung ở lọc đuôi âm `E1_USDJPY_TOKYO` (`233 -> 120` lệnh). **Điều kiện tiên quyết trước khi mở `Holdout 2025+` hoặc đưa lên chạy thật (`W4-RT1-P1-01`):** cần đối khớp lại định nghĩa đặc trưng train-serve giữa `ml_features_24.py` và `BuildCausalMLFeaturesV104` trong `Naqex_Master_Prop7E_v104_ML.mq5` (đối khớp ONNX `7,28e-8` mới chứng nhận vector tính sẵn; còn lệch trên `76/180` nhánh cây do `D1 ATR(14)` Wilder RMA ngày `UTC` vs MQL5 `iATR` SMA ngày sàn `EET/EEST`, `parkinson_vol_10d` `UTC` vs broker-day, và `rolling_dd_pct_causal` cố định `1,0x` vs theo `InpBasePhaseMult`) kèm kiểm thử parity đặc trưng đầu-cuối. Giữ `v1.03` bất biến, chỉ xét lên `v1.04-ML` sau khi xử lý xong lệch này, qua `Holdout 2025+` và shadow thực địa.

---

## 2. Ma Trận Pareto `81` Case (`10 tr..500 tr VND` × `3` Đa Vé × `3` Hậu Payout)

> **Nhãn bắt buộc:** **`XẤP XỈ CẤP NGÀY`** (`APPROX_DAILY_RESOLUTION`) · `BACKTEST_DEV_SEALED_LE_2024` · `MEASURED_DEMO_EXECUTION` (FTMO, giá gốc `ALL_REGULAR_SSOT`, `1 USD = 25.765,94 VND`) · `10.000` **Shared Market Paths** (khối `5` ngày, `seed = 20261126`, `36` tháng / `756` phiên). Tương quan lãi/lỗ ngày giữa tài khoản cùng bot: **`rho = 0,999987`** (`0,999979..0,999994`). Tổng **`Đậu + Rớt + Chờ == 100,0%`** khớp **`810/810`** ô (`162` case × `5` mốc).

### 2.1. Bảng Đường Cong Vốn `9` Bậc (`1,0x` Baseline vs `1,5x` Stress — Cấu Hình Cân Bằng)

| Vốn (`VND` / `USD`) | Cấu hình cân bằng | Med `24T` `1,0x` (`tr` / `USD`) | Med `36T` `1,0x` (`tr` / `USD`) | Med `36T` `1,5x` (`tr` / `USD`) | `EV/Phí 36T` (`1x` / `1,5x`) | `P<=0` `24/36T` | `Ruin 36T` (`1x` / `1,5x`) | Cháy `12T` (`W95`) | `36T Đậu/Rớt/Chờ` (`=100%`) | `OwnBook 36T` (`USD` / `%`) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| **`10 tr`** (`388,11`) | `GATED` + `P1_RECOUP` | `9,13` (`354,49`) | `34,38` (`1.334,14`) | `+0,65` (`+25,21`) | `5,147x` / `2,371x` | `36,25 / 23,29%` | `0,28 / 0,69%` | `0,17%` (`0,29%`) | `80,81/0,27/18,92%` | `3.484` (`22,8%`) |
| **`15 tr`** (`582,16`) | `GATED` + `P2_40_40_20` | `26,47` (`1.027,38`) | `76,09` (`2.952,96`) | `-0,38` (`-14,85`) | `6,482x` / `2,824x` | `36,85 / 24,39%` | `0,25 / 0,66%` | `0,22%` (`0,35%`) | `81,02/0,25/18,73%` | `3.684` (`14,4%`) |
| **`25 tr`** (`970,27`) | `GATED` + `P2_40_40_20` | `56,84` (`2.205,95`) | `161,64` (`6.273,23`) | `+4,15` (`+161,07`) | `8,974x` / `3,757x` | `35,81 / 23,03%` | `0,03 / 0,12%` | `0,30%` (`0,45%`) | `82,42/0,03/17,55%` | `7.797` (`18,6%`) |
| **`40 tr`** (`1.552,44`) | `AGGR` + `P2_40_40_20` | `229,48` (`8.906,29`) | `630,56` (`24.472,50`) | `-9,10` (`-353,34`) | `15,689x` / `6,571x` | `37,17 / 25,22%` | `0,10 / 0,18%` | `0,34%` (`0,49%`) | `84,95/0,07/14,98%` | `20.641` (`27,7%`) |
| **`60 tr`** (`2.328,66`) | `AGGR` + `P3_80_20` | `384,69` (`14.930,17`) | `967,77` (`37.560,21`) | `-10,51` (`-407,82`) | `17,562x` / `7,055x` | `36,05 / 24,23%` | `0,12 / 0,25%` | `0,39%` (`0,54%`) | `85,24/0,10/14,66%` | `42.864` (`48,9%`) |
| **`100 tr`** (`3.881,09`) | `AGGR` + `P3_80_20` | `548,18` (`21.275,45`) | `1.246,07` (`48.361,10`) | `+144,57` (`+5.610,73`) | `20,147x` / `7,459x` | `33,66 / 20,95%` | `0,84 / 3,19%` | `0,44%` (`0,60%`) | `82,36/0,83/16,81%` | `51.354` (`51,2%`) |
| **`150 tr`** (`5.821,64`) | `AGGR` + `P3_80_20` | `586,65` (`22.768,36`) | `1.294,08` (`50.224,37`) | `+211,29` (`+8.200,20`) | `20,094x` / `7,188x` | `33,21 / 20,10%` | `0,08 / 0,21%` | `0,44%` (`0,60%`) | `82,57/0,08/17,35%` | `53.849` (`52,2%`) |
| **`250 tr`** (`9.702,73`) | `AGGR` + `P1_RECOUP` | `589,38` (`22.874,26`) | `1.297,28` (`50.348,45`) | `+223,94` (`+8.691,16`) | `20,044x` / `7,093x` | `33,11 / 19,88%` | `0,00 / 0,00%` | `0,44%` (`0,60%`) | `82,61/0,00/17,39%` | `52.504` (`50,6%`) |
| **`500 tr`** (`19.405,46`) | `AGGR` + `P1_RECOUP` | `589,38` (`22.874,26`) | `1.297,28` (`50.348,45`) | `+224,21` (`+8.701,86`) | `20,044x` / `7,091x` | `33,11 / 19,86%` | `0,00 / 0,00%` | `0,44%` (`0,60%`) | `82,61/0,00/17,39%` | `45.327` (`43,7%`) |

### 2.2. Bốn Điểm Rẽ Chiến Lược & Tham Chiếu The5ers
1. **Bão hòa trần `400.000 USD` FTMO (`100–150 tr -> 250 tr VND`):** Lãi cận biên trên mỗi `10 tr` nạp thêm đạt đỉnh `25 -> 40 tr` (`+312,61 tr/10 tr`) và `40 -> 60 tr` (`+168,61 tr/10 tr`), giảm mạnh từ `100 -> 150 tr` (`+9,60 tr/10 tr`, `1.246,07 -> 1.294,08 tr`), gần `0` ở `150 -> 250 tr` (`+0,32 tr/10 tr`) và bằng **`0,00 VND`** từ `250 -> 500 tr` (vốn Funded gốc chạm `330.089–330.160 USD`). Phần vốn dư từ `250–500 tr` nên đổ sang Own-Book thay vì dồn một hãng FTMO.
2. **Bảo vệ stress `1,5x`:** Ở vốn `10–25 tr`, chạy `AGGRESSIVE_PARALLEL` đẩy `Ruin 36T` lên `8,71%–10,52%` (`1,0x`) và `20,97%–23,98%` (`1,5x`, trung vị `-2,93`..`-19,28 tr` trên cả `9` cấu hình gồm `B15M__AGGRESSIVE_PARALLEL__P1_RECOUP_FIRST` đạt `-2,93 tr`). Chế độ `CONSERVATIVE_1_TICKET + P1_RECOUP_FIRST` giữ **trung vị `36T` dương ở mọi bậc vốn cả dưới `1,5x`** (`+2,78 / +0,11 / +2,66 / +9,40 / +30,92 tr` từ `10 -> 60 tr`, `Ruin 0,00%–0,17%`). Ở `100–500 tr` dưới `1,5x`, cháy Funded `12T` tăng lên `1,25%–1,32%` (`W95 1,56%–1,63%`).
3. **Điểm giao Own-Book (`Crossover`):** Ở mốc đỉnh `Own-Book = 54.934,44 USD` (`1,415 tỷ VND`) vs quy mô Prop danh nghĩa `328.369,50 USD` (lãi kỳ vọng Prop `22.695,18 USD/năm` vs Own-Book `12.085,58 USD/năm`), điểm Own-Book vượt Prop là **`103.159,91 USD` (`~2,658 tỷ VND`)** — tiến độ tối đa `36T` đạt `53,3%` (`PHASE_3_HYBRID_BARBELL`).
4. **The5ers (`TERMS_VERIFIED_EXECUTION_UNMEASURED` — khóa chạy thật tới khi đo thông số Demo):** Ở `10–25 tr` (`CONSERVATIVE + P2_40_40_20`), `the5ers_hs_5k_classic` đạt trung vị `24T/36T` `180,17 / 622,78 USD` (`16,05 tr VND`), `EV/Phí 8,769x`, `Ruin 0,00%`, cháy `12T 0,04%` (`W95 0,11%`), `36T = 81,22/0,00/18,78%`; `the5ers_hs_5k_new` đạt `133,89 / 537,48 USD` (`13,85 tr VND`), `EV/Phí 9,254x`, `Ruin 0,00%`, cháy `12T 0,03%` (`W95 0,09%`), `36T = 79,25/0,00/20,75%` (tháng đói `80,08%`, `Payout #1` `582,6` ngày).

---

## 3. Tầng 3 — Own-Book `4/4` Stress, Frontier Mù `2/3` PASS & Sổ Tay Việt Nam

- **Sổ Vốn Riêng có khiên (`W4-G08`, `2020–2024`, `1.305` phiên):** Cơ cấu `60% Macro ETF / 10% Crypto Spot / 15% Carry / 15% T-Bill`, trần **`CEX <= 25,0%`**, đạt **`CAGR +6,69%`**, `AnnVol 4,83%`, **`Sharpe 1,36`**, `Sortino 1,24`, **`Max DD 8,09%`**, `Calmar 0,83`. Qua **`4/4` bài kiểm sốc**: vỡ sàn CEX khóa lỗ `<= 25%`; nén funding `< 3%` xoay `15%` Carry sang T-Bill; khủng hoảng `2022` chỉ tụt **`7,87%`** vs `60/40` **`20,69%`**; Flash Crash `-35%` ghi **`0` thanh lý**. Lô nguyên IBKR sạch từ `50.000 USD` (`144,43 bps/năm`). Chi tiết `4` ngưỡng vốn VN (`<100` -> `>=500 tr`), chuyển **UCITS Ireland** `< 60.000 USD` và pháp lý/thuế xem tại [VN-OWNBOOK-EXECUTION-PLAYBOOK.md](VN-OWNBOOK-EXECUTION-PLAYBOOK.md) (`17.805 B`, SHA-256 `1401901c...5739`).
- **Kiểm định mù Frontier Cụm B (`W4-G09`, `27/36` DuckDB, `Holdout = 0`) & Combined Pod:** **`2/3` PASS, `1/3` bị khai tử trung thực**:

| Nhánh / Tổ hợp (`2023–2024` overlap) | Trạng thái / Tỷ trọng | `Sharpe` | `Calmar` | `Max DD` | `2022 DD` / `CAGR` | `PBO` / `DSR` | `|r|` vs `7E` | Tháng đói |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **`FRONTIER_01`** *(SJM-NCO Risk Parity)* | **`PASS_BLIND_CLUSTER_B`** | **`1,2030`** | `0,8108` | `4,57%` | **`1,68%`** *(DD 2022)* | `0,2497` / `0,9848` | `-0,0312` | *(đơn nhánh)* |
| **`FRONTIER_03`** *(Crypto Perp Carry)* | **`PASS_BLIND_CLUSTER_B`** | **`7,1683`** | `30,5085` | `0,11%` | `+3,40%` *(CAGR, `0` liq)* | `0,3224` / `1,0000` | `-0,0707` | *(đơn nhánh)* |
| **`FRONTIER_02`** *(VRP VIX Multifactor)* | **`KILLED_ON_BLIND_CLUSTER_B`** | `0,7884` | — | — | `15,81%` *(DD 2022)* | `0,7609` *(trượt `5` cổng)* | — | *(đã loại)* |
| `PORT_7E` đơn lẻ (`23–24` / `19–24`) | `100% PORT_7E` | `0,8724` / `1,2976` | `0,8428` / `1,2680` | `5,51%` / `5,52%` | `+4,64%` / `+7,00%` | — | `1,0000` | **`45,83%`** (`37,5%`) |
| **Combined Pod — `Equal Weight`** | `33,3 / 33,3 / 33,3%` | **`2,2918`** | **`2,5994`** | **`1,89%`** | `+4,90%` *(CAGR)* | — | — | **`29,17%`** (`-16,66` đ%) |
| **Combined Pod — `Causal Inv-Vol`** *(\*)* | `13,8 / 22,9 / 63,3%` | **`3,8172`** | **`4,6170`** | **`0,92%`** | `+4,27%` *(CAGR)* | — | — | **`20,83%`** (`-25,00` đ%) |
| **Combined Pod — `Core 50 / Frontier 50`** | `50 / 25 / 25%` *(đúng trần CEX)* | `1,7134` | `1,7795` | `2,73%` | — | — | — | `41,67%` |

*(\*) `FRONTIER_01` đạt `BH-FDR q = 0,002575`. Tỷ trọng `Causal Inv-Vol` gán `63,30%` crypto perp nên khi triển khai thật bắt buộc khóa cứng `CEX <= 25,0%`. Tháng đói giảm từ `45,83%` xuống **`20,83%–29,17%` (`< 30%` ngưỡng Top 1% trên Dev Cluster B)**.*

---

## 4. Tầng 4 — Prop Fleet `S0..S7`, Web Cockpit, Zero-Popup `0/57`, AI Radar & Live PIT-24

- **Đội Tài Khoản Prop (`W4-G10`):** FSM `8` pha `S0..S7` (`19` bước chuyển, Cổng 2 khóa cứng chặn nhầm `.set` Eval vào Funded) + **`6` chốt đồng thời `E1..E6`** + sổ cái chuỗi băm chống giả mạo + diễn tập E2E `PASS` -> xem [MULTI-ACCOUNT-FLEET-RUNBOOK.md](MULTI-ACCOUNT-FLEET-RUNBOOK.md) (`15.368 B`, SHA-256 `ca88cbe9...ad91`).
- **Web Cockpit `?view=prop-fleet` (`W4-G11`):** `PropFleetWorkspace.jsx` tải lười (**`0 B`** tăng tải khởi động, `119.421 B` raw / `31.121 B` gzip đạt ngân sách), **`86/86` Node tests**, **`4/4` Playwright suites**, tương phản `>= 16,44:1`, **`0` gọi `/api/*`**, `0` mã màu hex cứng, khóa chỉ đọc `execution_capability: false`.
- **Zero-Popup `0/57` & Briefing Hợp Nhất (`W4-G17`):** Vá `9` vị trí cũ; kiểm toán AST **`49` tệp / `57` lời gọi `subprocess` -> `0/57` thiếu `CREATE_NO_WINDOW`** (`12` automation + `14` ops_cloud + `23` wave4, `pythonw` exit `0`), hợp nhất `4` tầng vào `1` bản tin sáng; CI-parity **`2.508/2.508` PASS** (`0` lỗi `ruff`, `10/10` immutables sạch).
- **AI Radar (`W4-G13`), Live PIT-24 & Bảng Chấm `6` Tiêu Chí (`W4-G14`):** Quét `477` model OpenRouter (`468` có giá, **`302` model `<= 5 USD/tháng`**), **`12` model vừa VRAM RTX 2070S**, quán quân tiết kiệm **`qwen/qwen3.7-flash`** (**`0,0196 USD/tháng = 500 VND/tháng`** theo tỷ giá quy đổi `25.500 VND/USD` của AI Radar/Rubric, trần `5,00 USD = 127.500 VND/tháng`; quy theo tỷ giá SSOT `25.765,94 VND/USD` tương đương `505 VND` và `128.830 VND/tháng`). Live **PIT-24** (`gpt-6-luna` loopback): **`24/24 PASS`**, `100%` schema & đồng thuận regime, `p50 3.708,25 ms`, `p95 6.287,86 ms`. `Prospective Shadow Ledger` khởi tạo phiên đầu `30/11/2026` (`0/30` ngày).
  - **Xếp hạng `6` tiêu chí AI (`/ 5,00`):** (1) **MT5 ONNX / Pure-MQL5 `v1.04-ML` `5,000`** (`PRIMARY_EXECUTION_PATH`) > (2) **Local Ollama RTX 2070S `4,417`** (`OFFLINE_DEGRADED_FALLBACK`) > (3) **Official API `<= 5 USD/tháng` `4,083`** (`PRIMARY_MACRO_ADVISORY`) > (4) **CLIProxyAPI `17852` `3,250`** (`DEV_RESEARCH_ONLY`) > (5) **Neurobro `1,750`** (`REJECT_BLACKBOX_SAAS`).

---

## 5. Tầng 2 (CME `4` Hãng -> `SKIP`), `16/16` Mã M1 Mới & Kit `01/12–10/12`

- **CME Futures `4` hãng (`W4-G15` -> `SKIP`):** `10.000` đường MC (`seed = 42`, giữ nguyên Wave 2 `edfe6dfa...677b`). `3/4` hãng (`MFFU`, `TakeProfitTrader`, `Tradeify`) cấm KYC VN; `Topstep` (`ALLOWED_XFA_ONLY`) chỉ đạt `EV/Phí 1,021x` (`topstep_100k_combine`, trung vị `+149,95 USD` ~ `+3,86 tr VND`, `P<=0 48,88%`, **cháy `12T` `57,85%`** `W95 58,90%`) và `0,799x` (`topstep_50k_combine`, trung vị `-211,10 USD` ~ `-5,44 tr`, cháy `32,36%`). Gói kỹ thuật cao nhất bị cấm VN (`tradeify_50k_growth`: `2,851x`, cháy `31,89%`) vẫn thua FTMO (`10K: 3,485x`, `100K: 6,628x`) -> **`SKIP`**.
- **Thu hoạch `16/16` mã M1 mới (`W4-G16` — `36,83 triệu` nến, `0` WAF Bypass):** Niêm phong trọn **`16/16`** mã (`36.825.451` nến, `480.381.807 B` Parquet, `0` giá `<= 0`, `0` dòng `2025+`, `0` lách WAF), nâng tổng kho lên **`28` mã M1** (giữ nguyên `12` mã cũ `650641b7...`):
  - **`6` mã `QDM CLI` (`FULL_DEV_7Y_DENSE_M1`, `2018–2024`):** `USDCHF`, `US30`, `JP225`, `UK100`, `USOIL`, `UKOIL`.
  - **`10` mã `FTMO-Demo` (`FTMO_BID_PLUS_SPREAD`):** `2` mã `7` năm (`NZDUSD`, `EURGBP`) + `8` mã `6` năm `2019–2024` (`PARTIAL_DEV_DENSE_M1`: `EURAUD`, `GBPAUD`, `EURCAD`, `AUDJPY`, `CADJPY`, `CHFJPY`, `NZDJPY`, `XAGUSD`).
- **Bộ Kit `01/12–10/12` (`W4-G12`, `0 VND`, `OrderSend = 0`, `0` ghi SSH):** `01/12` xác thực `8/8` tệp `preregister_holdout_v2.py` (`adb70736...`); `04/12` (NFP) & `10/12` (CPI) `nfp_cpi_quote_collector.py` `PREFLIGHT_OK` (`QUOTE_ONLY`, `23` cột, NTP `85,78 ms < 1.000 ms`); `08/12` `harvest_free_trial_forensics.py` đọc-thuần khớp fixture `100%` (`1,0`, `0` ghost, `0` swap).

---

## 6. Bảng Đối Chiếu SHA-256 (`40/40` SSOT) & Lộ Trình Thực Địa `01/12 -> 13/12`

### 6.1. Dấu Vân Tay SHA-256 Trọng Yếu (`wave4_master_metrics.json`)

| Hạng mục / Tài liệu | Đường dẫn chuẩn | Kích thước | `file_sha256` (16 ký tự) | Đối khớp (`40/40` PASS) |
|---|---|---:|---|---|
| **Master SSOT Wave 4** | `.runtime/offensive4/wave4_master_metrics.json` | `474.733 B` | `531db653bb2e4e66` | `report: 4472bde6c5cda711` · `18` tự băm · `16` chéo |
| **Same-Feed Parity** | `.runtime/offensive4/audits/w4_t0_parity98_receipt.json` | `123.487 B` | `0a7d212bfe17b019` | `3.320/3.320` khớp · `0` ghost |
| **Bộ Kit `01/12–10/12`** | `.runtime/offensive4/audits/w4_t0_milestones_receipt.json` | `5.308 B` | `15de48b1d0d2dab0` | `8/8` Holdout v2 · NTP `85,78 ms` |
| **`v1.04-ML` Arena & MT5** | `.runtime/offensive4/ml/wave4_ml_arena_summary.json` | `411.210 B` | `748298d6402c72ab` | MT5 ONNX `c9d199c5e1ad0a05` · `7,28e-8` · `+639,18 USD` |
| **Pareto `81` Case `10k`** | `.runtime/offensive4/pareto/wave4_pareto_summary.json` | `444.752 B` | `8f672e855ad7ce0f` | `81cases` `7bafa43e111f2444` · `810/810` ô |
| **Own-Book & Frontier** | `.runtime/offensive4/frontier/frontier_cluster_b_blind_verdict.json` | `45.688 B` | `c4a8c541c9ab8d3d` | OwnBook `6f7f5ca48649fb6a` · `4/4` stress · `2/3` PASS |
| **Fleet E2E & Cockpit** | `.runtime/offensive4/fleet/fleet_e2e_drill_receipt.json` | `5.941 B` | `547e86a5c6249a7a` | Web UI `ea0c524f1aa5baf4` · `86/86` Node · `4/4` PW |
| **AI Radar & PIT-24** | `.runtime/offensive4/ai/wave4_pit24_and_ai_rubric.json` | `49.801 B` | `8687f92302a78acc` | Radar `b44c3491046065b8` · Shadow `42db0a6d1183bd12` |
| **CME `4` Hãng & `16` M1** | `.runtime/offensive4/futures/wave4_cme_intraday_feasibility.json` | `50.530 B` | `8eab90f27e0d0242` | `16sym` `a6e4be7a322562d6` (`36,83 tr` nến) · `SKIP` |
| **Briefing & Tests CI** | `.runtime/offensive4/audits/w4_tests_all_receipt.json` | `12.688 B` | `3e97b8ecdecfc798` | Briefing `a69726b763d0bda2` · `2.508` CI · `0/57` |
| **Playbook Own-Book VN** | [VN-OWNBOOK-EXECUTION-PLAYBOOK.md](VN-OWNBOOK-EXECUTION-PLAYBOOK.md) | `17.805 B` | `1401901c0d9de23b` | `4` ngưỡng vốn VN · UCITS Ireland · `OPS-4` |
| **Runbook Đội Prop** | [MULTI-ACCOUNT-FLEET-RUNBOOK.md](MULTI-ACCOUNT-FLEET-RUNBOOK.md) | `15.368 B` | `ca88cbe94bfb4d0a` | `S0..S7` · Cổng 2 khóa `S4->S5` · `E1..E6` |

### 6.2. Lộ Trình Thực Địa `30/11 -> 13/12/2026` (`0 VND` · `OrderSend = 0` · `0` G12)

| Mốc lịch | Cửa sổ hành động (`0 VND`, chỉ đọc / kiểm chứng) | Công cụ & điều kiện chốt |
|---|---|---|
| **`30/11/2026`** | Mở ngày `1/30` trên `Prospective Shadow Ledger` (chỉ tư vấn) & tạo hóa đơn giữ giá Black Friday ở mức `0 VND` (chưa thanh toán). | `morning_briefing.py` · `prospective_shadow_ledger.json` |
| **`01/12/2026`** *(07:00 ICT)* | Chốt khóa tiền đăng ký `holdout_v2_prospective`, giữ niêm phong `Holdout 2025+` (`0` dòng đọc). | `preregister_holdout_v2.py --verify` (`8/8` khớp `adb70736...`) |
| **`04/12/2026`** *(20:30 ICT)* | Thu băng báo giá thực địa `US_NFP` chế độ `QUOTE_ONLY` (`OrderSend = 0`). | `nfp_cpi_quote_collector.py` (`23` cột, NTP `< 1.000 ms`) |
| **`07–08/12/2026`** *(trước hạn `08/12`)* | **Thu hoạch khẩn FTMO Free Trial trên `naqex-node1` (chỉ đọc):** xuất trọn log MT5, `naqex_exec_audit.csv`, MT5 Statement & đo trượt giá/swap. | `harvest_free_trial_forensics.py` (cổng trượt giá `<= 1,50x`, giết `1,75x`, `0` lỗi parity/swap) |
| **`10/12/2026`** *(20:30 ICT)* | Thu băng báo giá thực địa `US_CPI` chế độ `QUOTE_ONLY` (`OrderSend = 0`). | `nfp_cpi_quote_collector.py` |
| **`11–13/12/2026`** *(trước hạn `14/12`)* | Tổng hợp toàn bộ bằng chứng thực địa (`Free Trial` + `NFP/CPI` + `OPS-2` + `E1..E6` trên `?view=prop-fleet`), chốt `Go/No-Go` nội bộ — giữ nguyên **`0 VND`** nếu bất kỳ cổng nào chưa xanh. | `prop_lifecycle_orchestrator.py` · `fleet_admission_and_edge_cases.py` · `?view=prop-fleet` |

**Hành động kế tiếp (`< 2` phút, `0 VND`, `OrderSend = 0`):** Chạy không cửa sổ bản tin sáng hợp nhất `4` tầng xác nhận đếm ngược các mốc `30/11 -> 14/12`:

```powershell
.\.runtime\quant-audit-v24\Scripts\pythonw.exe tooling\automation\morning_briefing.py --offline-dry-run
```
