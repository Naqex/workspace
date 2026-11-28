---
doc_type: campaign-master-report
title: "Total Offensive #5 (v5.3 FINAL) — Nhà Máy Alpha Khép Kín, Quang Phổ Tốc Độ Thi Quỹ 5 Bậc × 4 Pha & Danh Mục Hợp Nhất"
date: 2026-11-28
campaign: "Total Offensive #5 v5.3 FINAL"
worker: w5-report-docs
gate: "W5-G19"
ssot_metrics_path: ".runtime/offensive5/wave5_master_metrics.json"
ssot_metrics_file_sha256: "3c7ca14f60cb258ef7d4de8cdb9d34830f9e0f8b12388196d7f68818a4be2d84"
ssot_metrics_report_sha256: "152b707fe0440963b9e7c8adac3c24daf280b5caa4152bb2c7ee40f5a9ff86eb"
spectrum_summary_path: ".runtime/offensive5/pareto/mc_spectrum_summary.json"
spectrum_summary_file_sha256: "5f11fb60d58a6aa05da25cda917f9e8897e31d1b500e885d10e812c6d63d0a49"
spectrum_summary_report_sha256: "604953d3649dedba58395123bb4621e0f3d7ddc0beae4ff6b392e003633f9cb2"
reconciled_artifact_count: 26
required_artifact_count: 25
holdout_cutoff_inclusive: "2024-12-31"
holdout_2025_plus_sealed: true
holdout_rows_analysed: 0
order_send_capable: false
order_send_count: 0
spend_vnd: 0
immutables_11_of_11_clean: true
g12_prop_support_nudges: 0
---

# Total Offensive #5 (`v5.3 FINAL`) — Nhà Máy Alpha Khép Kín & Quang Phổ Thi Quỹ `5` Bậc × `4` Pha

**Kết luận hành động ngay:** Toàn bộ **`26/26`** artifact Wave 5 (gồm `25` artifact lõi + làn giao diện `W5-G21`) đã đối chiếu khớp **SHA-256** (`18` tự băm, `40` liên kết chéo) tại SSOT duy nhất `.runtime/offensive5/wave5_master_metrics.json` (`report_sha256: 152b707fe0440963...`, `file_sha256: 3c7ca14f60cb258e...`). Khóa an toàn bất biến giữ trọn: **`Dev <= 2024-12-31`**, **`Holdout 2025+ SEALED`** (`holdout_rows_analysed = 0`), **`OrderSend = 0`**, **`0 VND`**, **`11/11` tệp bất biến sạch**, **`41/41` lõi `quant_core/`**, **`0` `.ex5`** trong `exports/` và `private_vault/`, **`0` tiến trình MT5**. Giữ nguyên ứng viên chạy chính bất biến **`v1.03` (`PORT_7E`, cấu hình `v1.03-Sprint` / `T3_BALANCED_EV`)** vì: (a) Đấu trường M1 `355` ứng viên trên `28` mã cho kết quả trung thực **`0/6` `TIER_1`** (`PORT_V5 == PORT_7E`, `1/6` vào `ALPHA_BENCH_RESERVE`); (b) Đấu trường `v1.05-ML` (`36` thử nghiệm, đóng triệt để lỗi lệch đặc trưng `W4-RT1-P1-01` trên `777/777` tín hiệu MT5 Build 6230) cho phán quyết trung thực **`REJECT_V105_ML_KEEP_V103`**. Tỷ giá SSOT: **`1 USD = 25.765,94 VND`** (`ALL_REGULAR_SSOT`, `FTMO 10K = 98,61 USD`, `100K = 598,35 USD`).

---

## Tổng Quan Điều Hành — Bảng Chấm Điểm `4` Tầng Inside-Out (Hợp Đồng `1.0.0` & Luật 15)

> **Nguyên tắc Inside-Out (`UI/contracts/evaluation-scorecard/1.0.0/`):** Mỗi tầng chấm theo trần riêng, tuyệt đối không lấy trần của tầng này hạ điểm sai tầng khác. Toàn bộ số liệu bên dưới ở cấp **`Dev <= 2024-12-31 · Holdout 2025+ SEALED`** (`0 VND`, `OrderSend = 0`), chưa phải kết quả tiền thật. Phiên bản phân loại chuẩn: `naqex-ssot-evaluation-taxonomy-v1` (`taxonomy_file_sha256: 2cda67d72328d1e7...`, `taxonomy_canonical_fingerprint_sha256: 5385546c2def1c98...`).

### Tầng 1 — Bot Thi Quỹ CFD Đơn Lẻ & Đội Quỹ Đa Tài Khoản (`T1_CFD_PROP` · `PORT_7E == PORT_V5`)
- **Cấp độ bằng chứng & phạm vi:** `DEV_CONSUMED_OOS + MT5_BUILD_6230_DEV_2024` (`Holdout 2025+ SEALED`, `MEASURED_DEMO_EXECUTION`, `ALL_REGULAR_SSOT`, vòng đời MC gắn nhãn **`XẤP XỈ CẤP NGÀY`**).
- **Bộ chỉ số cân bằng (`T3_BALANCED_EV` = `v1.03-Sprint`, `FTMO Standard 100K`, `1,0x`, `10.000` đường MC):**
  - Giao dịch cốt lõi: `Winrate 49,29%` · `RR 1,255` · `PF 1,219` · `Max DD 7,36%` · `Calmar 1,126` · `Sharpe 1,320`.
  - Thi quỹ đơn vé `12T` (`Đậu/Rớt/Chờ = 100,0%`): **P1** `81,74 / 16,67 / 1,59%` (`TOP_1_PCT`) · **P2** `88,39 / 10,06 / 1,55%` (`TOP_1_PCT`) · **Pass P1+P2** `69,78 / 23,92 / 6,30%` (`TOP_1_PCT`) · **Cháy Funded 12T** `0,30%` (`W95 0,45%`, `TOP_1_PCT`).
  - Hiệu quả kinh tế `24T`: **`EV/Phí +11,930x`** (`+188,52 tr VND` ~ `+7.316,64 USD`), `P(lãi ròng <= 0, 24T) = 26,93%`, **`Pay1 có ĐK = 176,8 ngày`** (`~5,9` tháng) vs **`Pay1 không ĐK (chặn 730d) = 234,8 ngày`** (`~7,8` tháng).
  - Đội quỹ `9` bậc vốn `T3_BALANCED_EV` (`1,0x`, `81` cấu hình): `69` ca `GOOD` / `9` `ADEQUATE` / `3` `BAD`, trung bình `EV/Phí 36T = +13,014x`, cháy Funded `12T = 0,01%`, `Pay1 không ĐK = 227,7 ngày` (`100 tr VND`: trung vị `36T` **`+1.193,21 tr VND`** ~ **`+46.309,63 USD`**, `Ruin 0,00%`, `P<=0 24T = 8,20%`).
- **Ngưỡng gãy:** Ở trượt giá **`1,5x`**, đơn vé `T3 100K` hạ xuống `ADEQUATE` (`EV/Phí 5,822x`, `Pay1 không ĐK 434,1 ngày`, `P<=0 24T = 44,89%`, cháy `12T = 1,14%`); ở **`2,0x`**, toàn bộ `9/9` lịch hạ về `BAD` (`PF 1,048`, `Max DD 15,25%`, `Pay1 không ĐK 730,0 ngày`).
- **Nút thắt chính (`exact_bottlenecks[]`):** `PAYOUT_1_SLOW` (`234,8 ngày > 120 ngày`) · `P_LE_ZERO_24M_HIGH` (`26,93% > 15%`) · `EVIDENCE_STAGE_DEV_ONLY`.
- 🔴 **Xấu (`BAD`):** `EV/Phí < 1,0x` hoặc cháy Funded `12T >= 5,0%` hoặc `P(<=0, 24T) >= 45%`.
- 🟡 **Đủ dùng (`ADEQUATE`):** `EV/Phí 1,0x..2,99x` hoặc cháy Funded `12T` `1,0%..4,99%` hoặc `Payout #1 > 240 ngày` *(vị trí hiện tại của `C00`, `C10_NEWS_ON`, `T1`, `T2`, `T4`, `BELLMAN_DP_6TIER` đơn vé)*.
- 🟢 **Tốt (`GOOD`) — VỊ TRÍ HIỆN TẠI (`T3_BALANCED_EV` / `V103_SPRINT`):** `EV/Phí >= 3,0x` (`11,93x`), cháy Funded `12T < 1,0%` (`0,30%`), `Ruin < 1,0%`, `P(<=0, 24T) < 35%` (`26,93%`).
- 🏆 **Top 1% thực tế (`TOP_1_PCT`):** `EV/Phí >= 5,0x`, cháy Funded `12T < 0,5%`, `Payout #1 không ĐK < 120 ngày`, `P(<=0, 24T) < 15%`, xác nhận trên `Holdout 2025+` + tiền thật.
- **Khoảng cách tới Top 1%:** (1) Kéo `Payout #1 không ĐK` từ `234,8 ngày` (đơn vé) / `227,7 ngày` (đội quỹ `T3`) xuống `< 120 ngày`; (2) Hạ `P(<=0, 24T)` đơn vé từ `26,93%` xuống `< 15%` nhờ bổ sung alpha M1 độc lập (Wave 5 đã sàng `355` ứng viên: `0/6` `TIER_1`, `1` ứng viên dự trữ); (3) Giữ khóa `Holdout 2025+` và thu đủ bằng chứng thực địa FTMO Free Trial / Shadow Demo.

### Tầng 2 — Quỹ Futures CME Intraday (`T2_CME_FUTURES` · Giữ Nguyên Quyết Định `SKIP`)
- **Cấp độ bằng chứng:** `DEV_CONSUMED_OOS + TERMS_VERIFIED_EXECUTION_UNMEASURED` (không chạy lại CME trong Wave 5; bảo lưu kết quả kiểm định `4` hãng từ Wave 4: `3/4` hãng chặn KYC Việt Nam, `Topstep` XFA-only bị siết EOD Trailing DD cháy Funded `12T = 57,85%`, `EV/Phí = 1,021x`).
- **Ngưỡng gãy:** Khóa KYC Việt Nam ở `3/4` hãng + EOD Trailing DD gãy chuỗi lệnh CFD ghép sang CME.
- 🔴 **Xấu (`BAD` — `SKIP`) — VỊ TRÍ HIỆN TẠI:** `EV/Phí <= 1,02x`, cháy Funded `12T > 35%` (`57,85%`).
- 🟡 **Đủ dùng (`ADEQUATE`):** `EV/Phí 1,01x..2,99x` và cháy `12T` `15%..35%`.
- 🟢 **Tốt (`GOOD`):** `EV/Phí 3,0x..4,99x` và cháy `12T <= 15%`.
- 🏆 **Top 1% thực tế (`TOP_1_PCT`):** `EV/Phí >= 5,0x`, cháy `12T < 5%`, `P(<=0) <= 25%`, hợp lệ KYC Việt Nam + thực địa.
- **Khoảng cách tới Top 1%:** Cần xây bộ động cơ intraday thuần CME (`MNQ/MES/MGC/MCL`) và cầu nối ngoài MT5 trước khi mở đánh giá lại.

### Tầng 3 — Danh Mục Đa Tài Sản Own-Book & Kho Dự Bị Alpha (`T3_MULTI_ASSET_OWNBOOK`)
- **Cấp độ bằng chứng:** `DEV_BLIND_OOS` (`Cluster A -> Blind Cluster B <= 2024-12-31`, `Holdout 2025+ SEALED`, `0 VND`).
- **Bộ chỉ số & nâng cấp Wave 5:** Giữ vững nền Own-Book (`4/4` stress PASS, `CEX <= 25%`) và Frontier Pod (`2/3` PASS Cụm B, `Sharpe 2,29–3,82`, tháng đói `< 30%`) từ Wave 4; Wave 5 bổ sung đầy đủ quy trình **Closed-Loop Alpha Factory** (`5/5` diễn tập E2E xanh, sổ cái băm `29` bản ghi, `auto_deploy_permitted = false`) và đưa `1` ứng viên M1 lệch pha vào **`ALPHA_BENCH_RESERVE`** (`F5D_US30_TO_UK100_CNV_L2_LB30_A`, `PF_B 1,1317`, `Sharpe_B 0,4569`, `|r| = 0,0105` vs `PORT_7E`, hòa vốn chi phí `9,9236x`).
- **Ngưỡng gãy:** Thiếu dữ liệu MT5 HCC cho nhóm chỉ số/hàng hóa (`10/28` mã chưa có HCC); vượt trần `CEX > 25%`; chưa đạt điểm giao Own-Book (`~2,66 tỷ VND`).
- 🔴 **Xấu (`BAD`):** `Sharpe < 0,8`, tháng đói `> 45%`, hoặc có thanh lý khi stress.
- 🟡 **Đủ dùng (`ADEQUATE`):** `Sharpe 0,8..1,2`, `Calmar 0,6..1,2`, tháng đói `35%..45%`.
- 🟢 **Tốt (`GOOD`) — VỊ TRÍ HIỆN TẠI:** Nền Own-Book/Frontier vững trên Dev Blind OOS + quy trình Alpha Factory `5/5` khép kín + `1` ứng viên dự trữ.
- 🏆 **Top 1% thực tế (`TOP_1_PCT`):** `Sharpe 2,0..3,0+`, `Calmar >= 2,0`, tháng đói `< 30%`, `CEX <= 25%`, đủ dữ liệu HCC + `>= 12` tháng shadow/live đa tài sản.
- **Khoảng cách tới Top 1%:** Bổ sung dữ liệu tick/M1 MT5 HCC cho nhóm chỉ số/hàng hóa (hiện `18/28` mã sẵn sàng HCC) và tích lũy `>= 12` tháng shadow/tiền thật đa tài sản.

### Tầng 4 — Hạ Tầng Vận Hành, Danh Mục Hợp Nhất DuckDB, Modular EA & Cockpit UI (`T4_LIVE_OPS`)
- **Cấp độ bằng chứng:** `OFFLINE_CERTIFIED_DEV_2024 + MT5_BUILD_6230_ZERO_ERRORS` (`OrderSend = 0`, `0 VND`).
- **Bộ chỉ số Wave 5:** Danh mục hợp nhất `unified_eval_catalog.duckdb` (`1.342` thử nghiệm cũ + `1.250` ca MC + `122` lượt chạy, **`100%` hợp chuẩn Pydantic v2**) · MT5 Build 6230 **`15/15` cổng PASS** (`Modular_v105 == v1.03` khớp `0,00 USD` trên `469/469` lệnh; đóng `W4-RT1-P1-01` trên `777/777` tín hiệu `f0..f6 <= 2,20e-7`) · Alpha Factory **`5/5` diễn tập** · **`100%` offload X13** (`355` thử nghiệm M1 + `107/107` job MC) · Web Cockpit **`?view=prop-fleet`** đạt chuẩn `W5-G21` (`118.298 B < 120 KB`, `89/89` Node, `4/4` Playwright, tương phản `16,59:1 / 17,93:1`, `0` gọi `/api/*`).
- **Ngưỡng gãy:** Bỏ lỡ thu thập thực địa trước hạn Free Trial `08/12`; mở giao dịch khi chưa đủ `30` ngày shadow thực địa.
- 🔴 **Xấu (`BAD`):** Script rời rạc, file rời không chuẩn hóa, không kiểm chứng đồng nhất MT5.
- 🟡 **Đủ dùng (`ADEQUATE`):** Có watchdog/CI cơ bản nhưng thiếu catalog hợp nhất và kiểm chứng end-to-end.
- 🟢 **Tốt (`GOOD`) — VỊ TRÍ HIỆN TẠI (Tiệm cận Top 1% kỹ thuật):** Đủ catalog DuckDB/SQLite, hợp đồng UI `1.0.0`, `Modular_v105` 16 slot, `5/5` diễn tập Alpha Factory, `100%` X13 offload, Cockpit `?view=prop-fleet` `RECONCILED`.
- 🏆 **Top 1% thực tế (`TOP_1_PCT`):** Tầng Tốt + `>= 30` ngày vận hành shadow/trial thực địa trên `naqex-node1` (`0` lỗi parity/swap).
- **Khoảng cách tới Top 1%:** Tích lũy `>= 30` ngày vận hành shadow/trial thực địa và gom trọn bằng chứng thực địa chuỗi mốc `01/12 -> 13/12`.

---

## 1. Quang Phổ Tốc Độ Thi Quỹ `9` Lịch × `4` Pha & Đối Chứng `v1.05-ML` (`W5-G05`, `W5-G14`)

> **Nhãn bắt buộc:** **`XẤP XỈ CẤP NGÀY`** (`APPROX_DAILY_RESOLUTION`, riêng `T4/T5` có thêm kiểm toán nội nhật cấp lệnh ở §1.3) · `CONSUMED_DEV_CLB_TEMPORAL_OOS` (`<= 2024-12-31`, `holdout_rows_analysed = 0`) · `ALL_REGULAR_SSOT` (`10K = 98,61 USD`, `100K = 598,35 USD`, phí thẻ `2,5%`, `1 USD = 25.765,94 VND`) · `N = 10.000` đường MC dùng chung, `max_retries = 0`, kiểm tra tổng **`Đậu + Rớt + Chờ == 100,0%`** khớp **`280/280`** ô đơn vé. Tách riêng **`Pay1 có ĐK`** (`cond_med_pay1_days`, chỉ tính vé rút được tiền) và **`Pay1 không ĐK`** (`uncond_med_pay1_cap730`, tính mọi vé, chặn trần `730 ngày`).

### 1.1. Bảng Quang Phổ Đơn Vé `FTMO Standard 100K` (`9` Lịch × `4` Pha × Ma Sát `1,0x / 1,5x / 2,0x`)

- **Hệ số rủi ro `9` lịch (`P1 / P2 / Funded`):** `T1_ULTRA_SAFE` (`2,5 / 1,75 / 1,0x`) · `T2_SAFE_C00` (`3,5 / 2,25 / 1,0x`) · `T3_BALANCED_EV` = `V103_SPRINT` (`4,5 / 3,5 / 1,0x`, `KS 8,0%`) · `T4_TURBO_FAST` (`6,0 / 4,75 / 1,0x`) · `T5_MAX_THROTTLE_YOLO` (`8,5 / 6,5 / 1,0x`, **CHỈ NGHIÊN CỨU BIÊN**) · `C00` (`4,0 / 2,0 / 1,0x`) · `C10_NEWS_ON` (`4,0 / 3,5 / 1,25x`) · `BELLMAN_DP_6TIER` (6 bậc động `0,5..3,0x` P1 / `0,5..2,0x` P2 / `1,0x` Funded).

| Lịch / Hạng (`100K`, `1,0x`) | `P1` Đậu/Rớt/Chờ (`12T`) | `P2` Đậu/Rớt/Chờ (`12T`) | `Pass P1+P2` (`12T`) | Cháy `Fn12` (`W95`) | `Pay1` có ĐK / không ĐK | `EV/Phí 24T` (`tr VND`) | `P<=0` `24T` | `PF` / `DD` / `Cal` / `Shp` |
|---|---|---|---|---:|---:|---:|---:|---|
| **`T1_ULTRA_SAFE`** (`ADEQUATE`) | `79,17/7,28/13,55%` *(T)* | `87,86/2,59/9,55%` *(T)* | `55,13/8,20/36,67%` *(G)* | `0,38%` (`0,54%`) *(T)* | `339,2` / `385,5 d` | `9,887x` (`156,24`) | **`21,68%`** | `1,219 / 7,36% / 1,126 / 1,320` |
| **`T2_SAFE_C00`** (`ADEQUATE`) | `81,72/14,22/4,06%` *(T)* | **`88,92/6,65/4,43%`** *(T)* | `65,27/18,27/16,46%` *(T)* | `0,31%` (`0,46%`) *(T)* | `247,8` / `308,7 d` | `11,026x` (`174,24`) | `24,13%` | `1,219 / 7,36% / 1,126 / 1,320` |
| **`T3_BALANCED_EV`** (`GOOD`) | **`81,74/16,67/1,59%`** *(T)* | `88,39/10,06/1,55%` *(T)* | **`69,78/23,92/6,30%`** *(T)* | **`0,30%`** (`0,45%`) *(T)* | `176,8` / **`234,8 d`** | **`11,930x`** (`188,52`) | `26,93%` | `1,219 / 7,36% / 1,126 / 1,320` |
| **`V103_SPRINT`** (`GOOD`) | **`81,74/16,67/1,59%`** *(T)* | `88,39/10,06/1,55%` *(T)* | **`69,78/23,92/6,30%`** *(T)* | **`0,30%`** (`0,45%`) *(T)* | `176,8` / **`234,8 d`** | **`11,930x`** (`188,52`) | `26,93%` | `1,219 / 7,36% / 1,126 / 1,320` |
| **`T4_TURBO_FAST`** (`ADEQUATE`) *(\*)* | `68,97/31,00/0,03%` *(G)* | `82,78/17,21/0,01%` *(G)* | `56,95/42,85/0,20%` *(G)* | `0,30%` (`0,48%`) *(T)* | `116,0` / `236,2 d` | `10,039x` (`158,65`) | `43,42%` | `1,219 / 7,36% / 1,126 / 1,320` |
| **`T5_MAX_THROTTLE_YOLO`** (`BAD`) *(\*\*)* | `46,08/53,92/0,00%` *(A)* | `72,16/27,84/0,00%` *(G)* | `33,25/66,75/0,00%` *(A)* | `0,39%` (`0,67%`) *(T)* | `73,9` / **`730,0 d`** | `5,824x` (`92,03`) | **`67,03%`** | `1,219 / 7,36% / 1,126 / 1,320` |
| **`C00`** (`ADEQUATE`) | `78,67/18,73/2,60%` *(T)* | `88,76/6,65/4,59%` *(T)* | `61,42/22,67/15,91%` *(G)* | `0,87%` (`1,10%`) *(G)* | `263,8` / `337,7 d` | `10,212x` (`161,37`) | `27,46%` | `1,219 / 7,36% / 1,126 / 1,320` |
| **`C10_NEWS_ON`** (`ADEQUATE`) | `78,48/19,33/2,19%` *(T)* | `82,98/16,83/0,19%` *(G)* | `62,69/31,91/5,40%` *(G)* | **`3,54%`** (`4,02%`) *(A)* | `189,9` / `283,4 d` | `12,603x` (`199,16`) | `34,70%` | `1,218 / 9,04% / 1,132 / 1,314` |
| **`BELLMAN_DP_6TIER`** (`ADEQUATE`) | `79,22/6,23/14,55%` *(T)* | `87,21/6,51/6,28%` *(T)* | `59,55/9,71/30,74%` *(G)* | `0,35%` (`0,50%`) *(T)* | `285,5` / `345,0 d` | `10,525x` (`166,32`) | `23,07%` | `1,219 / 7,36% / 1,126 / 1,320` |

*Chú giải bậc pha: `(T) = TOP_1_PCT`, `(G) = GOOD`, `(A) = ADEQUATE`, `(B) = BAD`. (\*) `T4_TURBO_FAST` gắn cờ `EXCEEDS_V103_SHIELD_A_3PCT_EVAL_CAP_RESEARCH_ONLY`. (\*\*) `T5_MAX_THROTTLE_YOLO` gắn cờ cứng **`RESEARCH_BOUNDARY_ONLY` + `FTMO_GAMBLING_ALLIN_RISK` + `EXCEEDS_V103_SHIELD_A_3PCT_EVAL_CAP_RESEARCH_ONLY`** — cấm dùng cho thi thật.*

#### Độ Bền Stress `1,5x` & `2,0x` (`FTMO Standard 100K`) + Đối Chiếu Nhanh `FTMO Standard 10K`

| Lịch (`100K` Stress `1,5x` / `2,0x` & `10K 1,0x`) | `100K 1,5x` Hạng / `Pass12` / `Fn12` / `Pay1U` / `EV/Phí` | `100K 2,0x` Hạng / `Pass12` / `Fn12` / `EV/Phí` | `10K 1,0x` Hạng / `Pass12` / `Fn12` / `Pay1C..U` / `EV/Phí` (`tr VND`) | `10K 1,5x` Hạng / `EV/Phí` / `Pay1U` |
|---|---|---|---|---|
| **`T1_ULTRA_SAFE`** | `BAD` · `34,62%` · `0,96%` · `644,2 d` · `4,239x` | `BAD` · `19,04%` · `2,75%` · `1,071x` | `ADEQUATE` · `53,76%` · `0,14%` · `371,0/416,0 d` · `5,445x` (`14,18`) | `BAD` · `2,091x` · `702,9 d` |
| **`T2_SAFE_C00`** | `BAD` · `45,20%` · `0,97%` · `553,7 d` · `5,074x` | `BAD` · `27,15%` · `2,81%` · `1,554x` | `ADEQUATE` · `64,47%` · `0,15%` · `272,5/334,8 d` · `6,184x` (`16,10`) | `BAD` · `2,628x` · `627,6 d` |
| **`T3_BALANCED_EV`** (`=V103_SPRINT`) | **`ADEQUATE`** · **`53,15%`** · `1,14%` · **`434,1 d`** · **`5,822x`** | `BAD` · **`36,54%`** · `3,12%` · **`2,187x`** | **`GOOD`** · **`69,85%`** · **`0,12%`** · `197,1/`**`259,4 d`** · **`6,769x`** (`17,63`) | **`ADEQUATE`** · **`3,119x`** · **`500,8 d`** |
| **`T4_TURBO_FAST`** | `BAD` · `43,92%` · `1,04%` · `730,0 d` · `4,824x` | `BAD` · `31,58%` · `2,69%` · `1,743x` | `ADEQUATE` · `57,31%` · `0,10%` · `131,9/274,7 d` · `5,651x` (`14,72`) | `BAD` · `2,517x` · `730,0 d` |
| **`T5_MAX_THROTTLE_YOLO`** | `BAD` · `26,33%` · `1,29%` · `730,0 d` · `2,697x` | `BAD` · `20,29%` · `3,40%` · `0,840x` | `BAD` · `33,69%` · `0,18%` · `88,4/730,0 d` · `3,139x` (`8,17`) | `BAD` · `1,230x` · `730,0 d` |
| **`C00`** | `BAD` · `41,06%` · `2,46%` · `663,1 d` · `4,573x` | `BAD` · `24,25%` · `6,28%` · `1,313x` | `ADEQUATE` · `60,35%` · `0,40%` · `287,7/366,7 d` · `5,691x` (`14,82`) | `BAD` · `2,335x` · `730,0 d` |
| **`C10_NEWS_ON`** *(Fn 1,25x)* | `BAD` · `44,96%` · **`9,55%`** · `730,0 d` · `5,732x` | `BAD` · `28,23%` · **`18,39%`** · `1,878x` | `ADEQUATE` · `62,88%` · **`2,28%`** · `205,8/305,8 d` · `7,240x` (`18,86`) | `BAD` · `3,157x` · `730,0 d` |
| **`BELLMAN_DP_6TIER`** | `BAD` · `38,65%` · `1,18%` · `647,9 d` · `4,553x` | `BAD` · `22,42%` · `2,99%` · `1,223x` | `ADEQUATE` · `58,59%` · `0,16%` · `311,6/376,8 d` · `5,865x` (`15,27`) | `BAD` · `2,296x` · `722,5 d` |

*Tại `10K 2,0x`, cả `9/9` lịch đạt `BAD` (`PF 1,047–1,048`, `DD 14,24%–17,79%`, `Pay1U = 730,0 d`; `T3_BALANCED_EV` cao nhất đạt `EV/Phí 0,944x`, `Pass12 = 36,06%`, `Fn12 = 1,82%`, `C10_NEWS_ON` cháy `Fn12 = 14,65%`). Điểm khác biệt sống còn: hạ `Funded` từ `1,25x` (`C10`) xuống `1,0x` (`T3_BALANCED_EV`) cắt cháy Funded `12T` từ **`3,54% -> 0,30%`** (`-11,8` lần ở `100K 1,0x`) và **`9,55% -> 1,14%`** ở `1,5x`.*

### 1.2. Đối Chứng Cặp OOF: `v1.05-ML` (Filter & AsymFloor) vs `PORT_7E OOF Control` (và `v1.04-ML` Baseline `W5-G05`)

> **Nhãn bắt buộc:** Mọi nhánh ML đều gắn cờ **`OOF_SUBSET_WINDOW` + `RESEARCH_PROTOTYPE_NOT_LIVE_APPROVED` + `CONSUMED_DEV_CLB_TEMPORAL_OOS`** (cửa sổ `1.455` ngày / `2.799` lệnh OOF); riêng `v1.04-ML` từ Wave 4 còn gắn thêm cờ **`FEATURE_SKEW_UNFIXED`**.

| Nhánh OOF (`100K`, `T3_BALANCED_EV`) | Ma sát | Hạng | `Pass P1+P2` (`12T`) | Cháy `Fn12` | `Pay1` có ĐK / không ĐK | `EV/Phí 24T` (`Delta` vs Control) | `PF` / `DD` |
|---|---:|---|---:|---:|---:|---:|---|
| **`PORT_7E OOF Control`** *(mẫu chuẩn)* | `1,0x` | `GOOD` | `68,22%` | `0,36%` | `176,8` / `243,5 d` | `11,403x` (`0,000x`) | `1,209 / 7,36%` |
| **`V105_ML_FILTER`** (`w5_05_lgbm`) | `1,0x` | `GOOD` | `68,54%` (`+0,32`) | `0,13%` (`-0,23`) | `204,4` / `265,2 d` (`+21,7 d`) | **`9,876x`** (**`-1,527x`**) | `1,225 / 5,70%` |
| **`V105_ML_ASYMFLOOR`** (`w5_30_lgbm`) | `1,0x` | `GOOD` | `68,75%` (`+0,53`) | `0,34%` (`-0,02`) | `179,7` / `244,9 d` (`+1,4 d`) | `11,427x` (`+0,024x`) | `1,213 / 6,91%` |
| **`PORT_7E OOF Control`** *(mẫu chuẩn)* | `1,5x` | `ADEQUATE` | `50,75%` | `1,24%` | `194,2` / `522,5 d` | `5,554x` (`0,000x`) | `1,121 / 8,89%` |
| **`V105_ML_FILTER`** (`w5_05_lgbm`) | `1,5x` | `ADEQUATE` | `52,23%` (`+1,48`) | `0,43%` (`-0,81`) | `230,5` / `452,2 d` (`-70,3 d`) | `5,053x` (`-0,501x`) | `1,134 / 7,09%` |
| **`V105_ML_ASYMFLOOR`** (`w5_30_lgbm`) | `1,5x` | `ADEQUATE` | `51,06%` (`+0,31`) | `1,20%` (`-0,04`) | `201,5` / `497,1 d` (`-25,4 d`) | `5,592x` (`+0,038x`) | `1,124 / 9,12%` |
| **`V105_ML_FILTER`** (`10K`, `1,0x`) | `1,0x` | `GOOD` | `68,62%` (`+0,29`) | `0,05%` (`-0,16`) | `229,0` / `294,2 d` (`+23,2 d`) | `5,548x` (`-0,877x`) | `1,224 / 5,58%` |
| **`V105_ML_ASYMFLOOR`** (`10K`, `1,0x`) | `1,0x` | `GOOD` | `68,99%` (`+0,66`) | `0,15%` (`-0,06`) | `201,5` / `271,0 d` (`+0,0 d`) | `6,483x` (`+0,058x`) | `1,213 / 6,63%` |

*Kiểm toán Baseline `W5-G05` trên `v1.04-ML` (`FEATURE_SKEW_UNFIXED`) cũng xác nhận cùng quy luật: cắt lệnh làm giảm `EV/Phí` (`-1,688x` ở `100K 1,0x`, `-0,990x` ở `10K 1,0x`) và kéo chậm `Pay1` (`+29,0` ngày không ĐK / `+36,3..+39,1` ngày có ĐK). `V105_ML_ASYMFLOOR` giữ gần nguyên `EV/Phí` (`+0,024x..+0,058x`) nhưng không vượt ngưỡng hòa vốn trượt giá `1,75x` -> **giữ `v1.03` thuần**.*

### 1.3. Kiểm Toán Nội Nhật Cấp Lệnh (`5%` Daily DD Drift trên `T4_TURBO_FAST` & `T5_MAX_THROTTLE_YOLO`)

Đo trực tiếp trên `1.718` ngày Dev (`<= 2024-12-31`) × `10.000` đường MC (`756` phiên) đối chiếu `4` chế độ đo DD ngày (`Đóng cửa ngày` -> `Xấp xỉ M1 ngày` -> `Trình tự lệnh nội nhật` -> `Lệnh nội nhật + sốc gap 1,25x`):

| Lịch / Gói | Ngày Dev `>= 5%` (Đóng/M1/Lệnh) | DD ngày cực đại (Đóng/Lệnh) | Vi phạm `5%` ngày (`Đóng` -> `M1` -> `Lệnh` -> `Gap 1,25x`) | Chênh `Lệnh - Đóng` / `Gap - M1` | Tỷ lệ `P1 Đậu` (`Đóng` -> `Lệnh` -> `Gap 1,25x`) |
|---|---|---|---|---|---|
| **`T4_TURBO_FAST` `10K`** | `2 / 3 / 3` ngày | `5,25% / 5,25%` | `3,74% -> 6,96% -> 7,08% -> 18,10%` | **`+3,34`** / **`+11,14 đ%`** | `74,27% -> 70,79% -> 60,29%` |
| **`T4_TURBO_FAST` `100K`** | `2 / 3 / 3` ngày | `5,26% / 5,26%` | `3,81% -> 7,11% -> 7,25% -> 19,18%` | **`+3,44`** / **`+12,07 đ%`** | `73,91% -> 70,52% -> 59,02%` |
| **`T5_MAX_THROTTLE_YOLO` `10K`** | **`24 / 38 / 40`** ngày | `8,45% / 8,88%` | `26,06% -> 38,71% ->` **`41,72%`** `->` **`63,56%`** | **`+15,66`** / **`+24,85 đ%`** | `57,10% ->` **`45,13%`** `->` **`31,60%`** |
| **`T5_MAX_THROTTLE_YOLO` `100K`** | **`24 / 38 / 40`** ngày | `8,48% / 8,94%` | `26,28% -> 39,12% ->` **`42,06%`** `->` **`63,79%`** | **`+15,78`** / **`+24,67 đ%`** | `57,03% ->` **`44,93%`** `->` **`31,45%`** |

*Kết luận rủi ro nội nhật: Ở `T5`, mô hình đóng cửa ngày đánh giá thấp nguy cơ cháy ngày tới `15,7–15,8 đ%` (và `3,0 đ%` ngay cả so với xấp xỉ M1 ngày); cộng thêm gap `1,25x`, gần `2/3` số vé (`63,6%–63,8%`) gãy luật `5%` ngày của FTMO và rớt vào vùng rủi ro cờ bạc (`FTMO_GAMBLING_ALLIN_RISK`). Do đó `T5` chỉ phục vụ vẽ biên lý thuyết (`RESEARCH_BOUNDARY_ONLY`).*

---

## 2. Đội Quỹ `9` Bậc Vốn (`10..500 tr VND`) & Đối Chiếu SQL Trực Tiếp `Wave 4 vs Wave 5`

> **Bằng chứng Đường Thị Trường Dùng Chung (`Shared Market Path`):** Tương quan lợi suất ngày giữa các tài khoản cùng bot đạt **`rho = 0,999995`** (`0,999990..0,999998`, đối chứng đột biến độc lập âm `mean = -0,002652`). Toàn bộ `972` ca Tier B (`6` bậc lịch × `9` vốn × `3` chế độ đa vé × `3` chính sách hậu Payout × `2` mức ma sát `1,0x/1,5x`, thực thi `100%` trên `X13_WORKER` với `107/107` job trong `393,4s`) đã vượt qua **`6.820/6.820`** kiểm tra tổng `Đậu/Rớt/Chờ = 100,0%` và trần cứng tĩnh không ratchet `s_bal`.

### 2.1. Đường Cong Vốn `9` Bậc Của Quán Quân Cân Bằng `T3_BALANCED_EV` (`1,0x` vs `1,5x`)

| Vốn (`tr VND`) | Cấu hình Pareto `1,0x` (`Đa vé` + `Hậu Payout`) | Hạng `1,0x` / `1,5x` | `P1 / P2 / Pass12` (`1,0x`) | Med `24T` `1,0x` (`tr VND`) | Med `36T` `1,0x` (`tr VND` / `USD`) | Med `36T` `1,5x` (`tr VND` / `USD`) | `EV/Phí 36T` (`1x` / `1,5x`) | `P<=0` `24T` (`1x` / `1,5x`) | `Ruin 36T` (`1x` / `1,5x`) | Cháy `Fn12` (`1x` / `1,5x`) | `Pay1` không ĐK (`1x` / `1,5x`) |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`10 tr`** | `CONSERVATIVE` + `P3_80_20` | `GOOD` / `ADEQ` | `82,5/88,5/81,5%` | `23,32` | `65,22` (`2.531,07`) | `17,10` (`663,48`) | `4,288x` / `2,508x` | `12,35` / `24,58%` | `1,61` / `6,95%` | `0,00` / `0,02%` | `244,2` / `339,2 d` |
| **`15 tr`** | `CONSERVATIVE` + `P3_80_20` | `GOOD` / `ADEQ` | `82,5/88,5/81,6%` | `25,09` | `82,96` (`3.219,85`) | `23,14` (`897,98`) | `4,645x` / `2,332x` | `12,88` / `32,55%` | `0,09` / `0,75%` | `0,00` / `0,02%` | `243,5` / `339,2 d` |
| **`25 tr`** | `CONSERVATIVE` + `P3_80_20` | `GOOD` / `ADEQ` | `82,4/88,5/82,0%` | `49,96` | `200,02` (`7.762,87`) | `38,32` (`1.487,18`) | `6,456x` / `2,715x` | `14,69` / `31,85%` | `0,00` / `0,07%` | `0,00` / `0,03%` | `231,9` / `323,2 d` |
| **`40 tr`** | `CONSERVATIVE` + `P3_80_20` | `GOOD` / `ADEQ` | `82,4/88,2/82,2%` | `130,18` | `430,28` (`16.699,75`) | `87,49` (`3.395,69`) | `8,459x` / `3,799x` | `12,16` / `32,17%` | `0,00` / `0,01%` | `0,01` / `0,04%` | `226,1` / `310,2 d` |
| **`60 tr`** | `CONSERVATIVE` + `P3_80_20` | `GOOD` / `ADEQ` | `82,4/88,5/82,3%` | `276,52` | `724,90` (`28.134,05`) | `204,38` (`7.932,07`) | `11,361x` / `5,157x` | `9,52` / `27,42%` | `0,00` / `0,00%` | `0,01` / `0,05%` | `221,8` / `308,0 d` |
| **`100 tr`** | `CONSERVATIVE` + `P2_40_40_20` | `GOOD` / `ADEQ` | `82,4/88,5/82,3%` | `565,56` | `1.193,21` (`46.309,63`) | `421,03` (`16.340,64`) | `15,735x` / `6,987x` | `8,20` / `24,07%` | `0,00` / `0,00%` | `0,01` / `0,06%` | `221,8` / `304,4 d` |
| **`150 tr`** | `GATED_STAGGER` + `P3_80_20` | `GOOD` / `ADEQ` | `82,4/88,5/82,8%` | `811,92` | `1.460,55` (`56.685,41`) | `681,62` (`26.454,48`) | `17,906x` / `7,813x` | `8,18` / `24,18%` | `0,00` / `0,00%` | `0,01` / `0,07%` | `220,3` / `302,2 d` |
| **`250 tr`** | `GATED_STAGGER` + `P1_RECOUP` | `GOOD` / `ADEQ` | `82,4/88,5/82,8%` | `817,91` | `1.473,93` (`57.204,49`) | `717,93` (`27.863,69`) | `18,028x` / `7,815x` | `7,39` / `22,40%` | `0,00` / `0,00%` | `0,01` / `0,07%` | `220,3` / `302,2 d` |
| **`500 tr`** | `AGGR_PARALLEL` + `P1_RECOUP` | `GOOD` / `ADEQ` | `82,4/88,5/82,3%` | `967,23` | `1.615,14` (`62.685,18`) | `856,82` (`33.254,15`) | `19,590x` / `8,630x` | `5,38` / `16,77%` | `0,00` / `0,00%` | `0,01` / `0,06%` | `221,8` / `304,4 d` |

*Tại mốc vốn chuẩn **`100 tr VND`** (`1,0x`), so sánh `6` bậc lịch đội quỹ: `T1_ULTRA_SAFE` (`ADEQUATE`, Med `36T` `1.033,36 tr`, `Pay1U 388,4 d`, `Ruin 0,00%`) · `T2_SAFE_C00` (`GOOD`, `1.240,21 tr`, `298,6 d`, `0,00%`) · **`T3_BALANCED_EV`** (`GOOD`, `1.193,21 tr`, `221,8 d`, `P<=0 = 8,20%`, `0,00%`) · `T4_TURBO_FAST` (`GOOD`, `1.346,12 tr`, `160,9 d`, `Ruin 0,01%`, nhưng có rủi ro DD ngày nội nhật) · `T5_MAX_THROTTLE_YOLO` (`1.122,81 tr`, `EV/Phí` tụt còn `6,952x`, `Ruin 0,67%`, cờ `RESEARCH_BOUNDARY_ONLY`) · `BELLMAN_DP_6TIER` (`ADEQUATE`, `1.085,84 tr`, `342,1 d`, `Ruin 0,00%`, `Fn12 = 0,00%`).*

### 2.2. Đối Chiếu SQL Trực Tiếp `Wave 4 vs Wave 5` (`unified_eval_catalog.duckdb::mc_cases_catalog`)

> **Công khai minh bạch so sánh (`apples_to_apples_disclosure`):** Wave 4 (`offensive4`, `168` ca: `87` ở `1,0x` + `81` ở `1,5x`) chấm cấu hình cũ `C10_NEWS_ON` ở mức **`funded_mult = 1,25x`** và **chưa tách riêng pha P1/P2** — do đó toàn bộ **`168/168`** dòng Wave 4 mang nhãn **`UNKNOWN_LEGACY_UNINSTRUMENTED`** (`"Chưa tách riêng P1/P2 ở dữ liệu Đợt 4"`, tuyệt đối không hiển thị `0%` hay màu xanh). Wave 5 (`offensive5_spectrum`) hạ **`funded_mult = 1,00x`** và tách đủ `4` pha (`P1 / P2 / Pass / Funded`) theo cùng chuẩn `unified_eval_taxonomy v1.0.0`. Cả hai cột **`legacy_grade_code`** và **`unified_grade_code`** được lưu song song không ghi đè lịch sử: trên `168` ca Wave 4, đối chiếu ra **`DU_DUNG -> ADEQUATE: 9`**, **`DU_DUNG -> BAD: 69`**, **`TOT -> ADEQUATE: 75`**, **`TOT -> BAD: 15`** (`0/168` ca Wave 4 đạt `GOOD` dưới chuẩn chặt mới vì `Pay1` `421,3 ngày` ở `1,0x` và cháy Funded cao ở `1,5x`).

| Bậc lịch Wave 5 vs Wave 4 `C10_NEWS_ON` (`162` ô khớp `1,0x + 1,5x`) | `Fn Mult` (W4 -> W5) | Ô `W4` (`legacy TOT` / `unified GOOD`) | Ô `W5` `unified GOOD` | Chênh `Med 36T` (`tr VND`) | Chênh `Pay1U` (`ngày`) | Chênh `Fn12` (`đ%`) | Chênh `P<=0 24T` (`đ%`) | Chênh `Ruin 36T` (`đ%`) | Ô nhanh hơn / an toàn hơn `Fn12` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`BELLMAN_DP_6TIER`** | `1,25x -> 1,00x` | `84` / `0` | `0` | `+108,90` | `-94,1 d` | **`-0,656`** | `-12,98` | **`-0,845`** | `162` / `162` |
| **`T1_ULTRA_SAFE`** | `1,25x -> 1,00x` | `84` / `0` | `0` | `+92,15` | `-62,9 d` | `-0,677` | `-13,23` | `-0,798` | `156` / `162` |
| **`T2_SAFE_C00`** | `1,25x -> 1,00x` | `84` / `0` | `45` | `+208,94` | `-187,9 d` | `-0,659` | `-20,76` | `+1,005` | `162` / `162` |
| **`T3_BALANCED_EV`** *(khuyên dùng)* | `1,25x -> 1,00x` | `84` / `0` | **`69`** | **`+324,39`** | **`-294,7 d`** | **`-0,672`** | **`-25,30`** | `+3,485` | **`162` / `162`** |
| **`T4_TURBO_FAST`** | `1,25x -> 1,00x` | `84` / `0` | `76` | `+336,53` | `-345,4 d` | `-0,674` | `-22,01` | `+8,248` | `153` / `162` |
| **`T5_MAX_THROTTLE_YOLO`** *(biên)* | `1,25x -> 1,00x` | `84` / `0` | `41` | `+137,09` | `-333,3 d` | `-0,692` | `-8,11` | **`+19,373`** | `141` / `162` |

*Chính sách `GATED_STAGGER + P2_40_40_20` ở `1,0x`: `T3_BALANCED_EV` nâng trung vị `36T` ở mốc `25 tr` từ `161,64 tr` (`W4 C10`, `Pay1 410,2 d`) lên **`404,67 tr VND`** (`Pay1 224,7 d`, `Fn12 = 0,01%`, `GOOD`), và ở mốc `100 tr` từ `890,53 tr` lên **`1.399,95 tr VND`** (`Pay1 220,3 d`, `Fn12 = 0,01%`, `Ruin 0,03%`, `GOOD`).*

---

## 3. Bốn Trụ Cột Chiến Dịch Total Offensive #5 (`W5-G01..W5-G21`)

### Trụ Cột 1 — Đấu Trường Alpha M1 `28` Mã × `355` Ứng Viên (`W5-G06..G09` · `100%` Offload `X13_WORKER`)
- **Kho dữ liệu `28` mã M1 niêm phong (`W5-G06`):** Đủ `28/28` mã (`67.845.762` nến, `global_max_date_utc = 2024-12-31`, `holdout_rows_analysed = 0`), phân rõ `3` cấp độ phân giải: `12` mã **`M1_BID_ASK`** (kho cũ `DEV_CLB_CONSUMED_12OLD`), `10` mã **`M1_BID_SPREAD`** (FTMO Demo), `6` mã **`M1_SINGLE_SIDE`** (QDM: `JP225`, `UK100`, `UKOIL`, `US30`, `USDCHF`, `USOIL`). Đã cách ly `2.753` dòng dị thường `USOIL`; `18/28` mã sẵn sàng MT5 HCC (`10` mã chưa có HCC).
- **Sàng lọc Cụm A (`2018–2020`, `355/360` thử nghiệm, `100%` trên `X13_WORKER`) -> Chung kết mù Cụm B (`2021–2024`):**
  - `5` họ chiến lược: `F5A_SESSION_OR_BREAKOUT` (`70` thử / `2` chung kết), `F5B_LIQUIDITY_SWEEP_MEANREV` (`77` / `1`), `F5C_VOL_COMPRESSION_CROSS` (`72` / `0`), `F5D_CROSS_ASSET_LEAD_LAG` (`70` / `3`), `F5E_TWAP_AND_ASIAN_RANGE_FADE` (`66` / `0`). Tổng `17` ứng viên dương đạt sơ tuyển -> khử trùng còn **`6` ứng viên chung kết** (`cluster_a_frozen_sha256: bb5c12e2a27f8800...`).
  - **Kết quả trung thực trên Cụm B mù (`8` cổng khắc nghiệt):** **`0/6` đạt `TIER_1` (`8/8` cổng)**, **`5/6` bị khai tử (`KILLED`)**, **`1/6` vào `ALPHA_BENCH_RESERVE`**:
    - `F5D_US30_TO_UK100_CNV_L2_LB30_A` (`UK100`, dẫn dắt từ `US30`): `414` lệnh B, **`PF 1,1317`**, `Sharpe 0,4569`, tương quan **`r = -0,0105`** với `PORT_7E`, hòa vốn chi phí **`9,9236x`**, đạt `4/8` cổng (trượt `G1` BH-FDR, `G2` DSR, `G3` PBO-CSCV, `G4` Sharpe `>= 0,60`).
    - `5` ứng viên bị loại: `F5A_UK100` (`PF 0,8706`, `Sharpe -0,7407`), `F5A_US30` (`PF 0,8984`, `Sharpe -0,5143`), `F5B_CHFJPY` (`PF 0,9185`, `Sharpe -0,1575`), `F5D_USOIL->UKOIL` (`28` lệnh `< 60`), `F5D_UKOIL->USOIL` (`25` lệnh `< 60`).
  - **Kết luận danh mục (`W5-G09`):** **`PORT_V5 == PORT_7E`** (`n_core7_engines = 7`, `n_added_engines = 0`, `port_v5_tapes.npz` `sha256: 0a9a2abe0ebf354c...`) — giữ kỷ luật tuyệt đối, không hạ chuẩn nhồi thêm động cơ yếu.

### Trụ Cột 2 — Đóng `W4-RT1-P1-01`, Đấu Trường `v1.05-ML` & Bellman DP Chống Martingale (`W5-G10`, `W5-G11`, `W5-G13`)
- **Đóng triệt để lỗ hổng `W4-RT1-P1-01` (`W5-G10`):** Đồng bộ `20` đặc trưng nhân quả giữa Python và MQL5 (xuất `8` đặc trưng cốt lõi: `d1_range_over_atr14`, `parkinson_vol_10d`, `prev_bar_close_loc`, `hour_sin_utc`, `hour_cos_utc`, `engine_id_code`, `same_dir_concurrent_count`, `rolling_dd_pct_1x_equiv`), bất biến pha DD (`dd_phase_invariance_max_err = 0,0`), không lệch bit nhân quả (`causality_zero_bit_drift = true`). Trên chứng nhận live MT5 Build 6230 năm 2024: khớp **`777/777`** mốc thời gian, sai số đặc trưng `f0..f6` tối đa **`2,20e-7`**, sai số chuẩn hóa đơn vị **`2,91e-5 <= 1e-4`**, sai số thô `f7` `0,00113 đ%` (do làm tròn phí sàn `0,23 vs 0,22 USD` ở `0,09` lot và `1-pt iATR`, **`0` nhánh cây bị lệch**), sai số xác suất `p_win` ONNX **`5,73e-8`** (`Pure-MQL5 = 0,0`), đồng thuận quyết định **`100,0%`** (`650` qua / `127` chặn / `343` lệnh, `0` đuổi trễ/đảo chiều), ONNX khớp từng xu Pure-MQL5 (`+586,17 USD`, `PF 1,19`, `EqDD 4,58%`).
- **Phát hiện `FLOAT32_ONNX_QUANTILE_CLIFF` & phán quyết trung thực `v1.05-ML` (`W5-G11`):** Chạy `36/48` thử nghiệm (`24` Filter + `12` AsymFloor) trên nền OOF `v1.03` (`2.799` lệnh, `WR 49,12%`, `EV +0,0546R`, `PF 1,1666`, `DD 5,80%`, hòa vốn `1,6430x`):
  - **Vách đá `float32`:** `4` ứng viên `regime_gmm_jump` (`w5_21..w5_24`) đẹp trên `float64` (`PF 1,222–1,262`, hòa vốn `1,762x–1,830x`) nhưng rơi mạnh khi ép sang `float32` ONNX (đồng thuận quyết định tụt còn **`84,39%–88,64% < 99%`**, hòa vốn tụt xuống `1,687x–1,720x`) -> tự động chặn fail-closed.
  - **Không ứng viên nào qua cổng (`0/36` thăng hạng):** Filter tốt nhất (`w5_05_lgbm_flt_d2_n80_r25_q20`: `PF 1,1887`, `EV +0,0559R`, `DD 5,70%`, `float32 agreement 100%`) chỉ đạt hòa vốn `1,6515x < 1,75x`; AsymFloor tốt nhất (`w5_30_lgbm_asym_ramp_d2_n80_f050`: `PF 1,1687`, `EV +0,0534R`, `DD 5,75%`) đạt hòa vốn `1,6338x < 1,75x`. Phán quyết cuối: **`REJECT_V105_ML_KEEP_V103`** (`RESEARCH_PROTOTYPE_NOT_LIVE_APPROVED`).
- **Bellman DP Chống Martingale `6` Bậc (`W5-G13`):** Huấn luyện nhân quả trên Cụm A (`666` ngày `2018–2020`), đánh giá mù trên Cụm B (`898` ngày `2021–2024`, `10.000` đường dùng chung). Đã chứng minh đơn điệu chống Martingale (`410/410` cặp theo DD + `220/220` cặp theo lỗ tĩnh, trần rủi ro mở `3,0%`), rút gọn thành `6` bậc tải trực tiếp vào MQL5 (`P1`: `+4,5..+8% -> 3,0x`, `>= +8% -> 2,0x`, `-1,5..+4,5% -> 2,5x`, `-4,5..-1,5% -> 2,0x`, `-6,5..-4,5% -> 1,0x`, `< -6,5% -> 0,5x`; `P2`: `>= -1,5% -> 2,0x`, `-4,5..-1,5% -> 1,5x`, `-6,5..-4,5% -> 1,0x`, `< -6,5% -> 0,5x`).
  - **Đánh đổi Pareto trên Cụm B mù:** Trên cửa sổ `12T/pha` (không giới hạn thời gian kiểu FTMO), `BELLMAN_DP_6TIER` thắng mọi đối thủ về sống sót (**`60,29%` đậu** vs `59,34%` Sprint / `58,55%` Barrier Taper / `58,10%` C10; rớt chỉ **`22,89%`** vs `39,23%–40,78%`; `EV/Phí 2,617x` vs `2,486x–2,560x`; `P95 DD 14,14%` vs `15,18%–16,68%`). Tuy nhiên ở tốc độ `6T/pha`, `V103_SPRINT` thắng rõ (`51,42%` đậu, `63` ngày, `17,14%/tháng` vs DP `40,71%`, `100` ngày, `48,54%` đang chờ) -> phán quyết trung thực **`BASELINES_HOLD_EDGE_OVER_DP_ON_BLIND_CLUSTER_B_NO_PROMOTION`**.

### Trụ Cột 3 — `Naqex_Master_Modular_v105` (`16` Slot) & Nhà Máy Alpha Khép Kín (`W5-G12`, `W5-G15..G17`)
- **Chứng nhận MT5 Build 6230 đạt `15/15` cổng PASS** (`W5-G10`, `W5-G12`, `W5-G15`):**
  - Kiến trúc mô-đun `16` slot (`Naqex_EngineSlotRegistry.mqh` + `Naqex_ML_Filter_v105.mqh` + `Naqex_Master_Modular_v105.mq5` biên dịch `0` lỗi / `0` cảnh báo, `.ex5` `206.890 B` lưu trong `.runtime/mt5-compiled-ex5/`, `0` `.ex5` trong `exports/` hay `private_vault/`).
  - **Tương thích ngược `100%` với `v1.03` tới `0,00 USD` (`W5-G15`):** Cùng chạy Full-2024 `10K Funded 1x`: `v1.03` và `Modular_v105` đều khớp **`469/469` lệnh**, lãi **`+616,87 USD`** (`+15,89 tr VND`, chênh **`0,00 USD`**), `PF 1,15`, `EqDD 4,09%`, `Swap 0,00 USD`.
  - **Đối khớp `4` chiều trên `500` vector (`W5-G12`):** `Python LightGBM <-> ORT <-> MT5 OnnxRun() (API 1.25.1) <-> Pure-MQL5`: sai số lớn nhất **`5,91e-8 <= 1e-5`**, đồng thuận `100%`, `0` nút `ZipMap`, chặn fail-closed `NaN`/`Inf`.
  - **Khói kiểm tra `Bellman DP` P1 trên MT5 (`10K 2024`):** `6` bậc chạy sạch (`0` dòng lỗi), `471` lệnh, **`+1.216,15 USD`** (`+31,34 tr VND`), `PF 1,13`, `EqDD 7,21%`.
- **Nhà máy Alpha khép kín (`W5-G16`, `W5-G17` — `5/5` Diễn Tập E2E PASS):** Tích hợp `live_decay_monitor`, sổ cái chuỗi băm `29` bản ghi (`ledger_root_sha256: 7d509eaf6045cadc...`), khóa cứng **`auto_deploy_permitted = false`**:
  1. `DRILL_1_NORMAL_GREEN`: đánh giá `7` động cơ khỏe, `0` đề xuất thay đổi.
  2. `DRILL_2_AMBER_HALVED`: phát hiện suy giảm mức Vàng ở `E3_GBPUSD_VH`, phát đề xuất giảm nửa tỷ trọng (`0,5x`, trạng thái `PENDING_OWNER_APPROVAL`).
  3. `DRILL_3_RED_WITH_BENCH_SWAP`: suy giảm mức Đỏ ở `E6_EURJPY_VOLCOMP`, tự khóa ứng viên kém (`KILLED`) và đề xuất thay thế từ kho dự bị hợp lệ `B1_XAGUSD_ORTH_VOL` (`PENDING_OWNER_APPROVAL`).
  4. `DRILL_4_RED_EMPTY_BENCH_FAIL_CLOSED`: suy giảm mức Đỏ khi kho dự bị chưa qua kiểm chứng (`DISCOVERED`) -> tự phanh `HALT_ONLY_EMPTY_BENCH`, tuyệt đối không đôn ứng viên chưa kiểm định.
  5. `DRILL_5_POISONED_INPUT_AND_TAMPERED_LEDGER`: chặn fail-closed **`8/8`** mẫu dữ liệu độc / giả mạo chuỗi băm sổ cái.

### Trụ Cột 4 — Chuẩn Phân Loại `2` Tầng, Danh Mục Hợp Nhất DuckDB, Hợp Đồng UI `1.0.0` & Cockpit `?view=prop-fleet` (`W5-G03`, `W5-G04`, `W5-G21`)
- **Hệ phân loại `2` tầng & Danh mục hợp nhất (`W5-G03`):** `tooling/ai-engines/configs/ssot/evaluation_taxonomy.json` chuẩn hóa `9` chỉ số theo khoảng nửa mở liên tục (`0` vùng chết, `ARCH-06` `0` lỗi). Cơ sở dữ liệu hợp nhất `.runtime/experiments/unified_eval_catalog.duckdb` (`10.498.048 B`, `sha256: 6da12129ffa1b879...`) + sổ đăng ký `.runtime/experiments/unified_eval_registry.sqlite3` (`380.928 B`, `126` sự kiện) hợp nhất trọn: **`1.342` thử nghiệm cũ** (`1.279` core + `27` Frontier + `36` ML Wave 4), **`1.250` ca MC** (`168` Wave 4 + `20` Wave 5 Baseline + `1.062` Wave 5 Spectrum), và **`122` lượt chạy** — **`100%` qua kiểm định Pydantic v2 (`1.250/1.250` MC & `122/122` runs)**.
- **Hợp đồng Hệ Thống Thiết Kế `UI/contracts/evaluation-scorecard/1.0.0/` (`W5-G04`):** `CONTRACT.md` + `schema.json` khớp chính xác `export_scorecard_json_schema()`, `0` phụ thuộc `jsonschema`, bảo toàn `presentation-state@1.0.0`, giữ nguyên `UI-Systems/` và `sharedUiPins`.
- **Nâng cấp Web Cockpit `?view=prop-fleet` (`W5-G21` — `PASS_W5_G21_TRADER_PROP_FLEET_WAVE5_UPGRADE`):** Bổ sung panel Quang phổ `5` bậc × `4` pha và Kho Dự Bị Alpha; giữ chunk gốc **`118.298 B` raw (`< 120.000 B`, dư `1.702 B`) / `31.144 B` gzip (`< 35.000 B`)**, `0` stale dist assets, **`89/89` Node tests** (`13` suites), **`4/4` Playwright browser suites** (tương phản `16,59:1` chế độ tối / `17,93:1` chế độ sáng), **`0` gọi `/api/*`**, `0` mã màu hex cứng, khóa chỉ đọc `execution_capability = false` và `auto_deploy_permitted = false`.

---

## 4. Sổ Cái Chứng Thực SHA-256 (`26/26` Artifact Wave 5 + SSOT Tổng Hợp)

> **Đối chiếu toàn vẹn:** `11/11` tệp bất biến sạch (`AGENTS.md`, `NATIVE_FTMO_HOLDOUT_LOCK.json`, `firms_catalog.json`, `ftmo_specs_28.json`, `risk_profiles.json`, `naqex_red_news_utc.csv`, `Naqex_PropGuard.mqh`, `Naqex_Signals_7E.mqh`, `Naqex_Master_Prop7E.mq5`, `Naqex_Master_Prop7E_v103.mq5`, `red_news.py`), `18` tự băm khớp, `40` liên kết SHA-256 chéo khớp, `0` dòng Holdout 2025+, `OrderSend = 0`, `0 VND`.
> - **Master SSOT Wave 5 (`W5-G18`):** `.runtime/offensive5/wave5_master_metrics.json` · `508.069 B` · `file: 3c7ca14f60cb258e` · `report: 152b707fe0440963` (`PASS_ALL_WAVE5_ARTIFACTS_RECONCILED_WITH_TRADER_UI`).

| # | Mã Artifact | Đường dẫn tương đối | Dung lượng | `file_sha256` (16 ký tự) | Tự băm / `embedded_sha256` | Cổng | Trạng thái |
|---:|---|---|---:|---|---|---|---|
| 1 | `w5_t0_env_receipt` | `.runtime/offensive5/audits/w5_t0_env_receipt.json` | `17.103 B` | `77d752a7af2b4d38` | `334527fc608f53cc` *(OK)* | `G01,G02` | `PASS` |
| 2 | `w5_taxonomy_ui_receipt` | `.runtime/offensive5/audits/w5_taxonomy_ui_receipt.json` | `8.853 B` | `81c750fdb0446d1b` | `dd4276fbea5e4d54` *(OK)* | `G03,G04` | `PASS` |
| 3 | `w5_baseline_receipt` | `.runtime/offensive5/audits/w5_baseline_receipt.json` | `41.439 B` | `b17bd443c06e5b82` | `7e5b9b200863af30` *(OK)* | `G05` | `PASS` |
| 4 | `w5_baseline_4profiles` | `.runtime/offensive5/audits/w5_baseline_4profiles.json` | `567.286 B` | `d1d9ad01331cbe51` | `0e56f383443d8fdc` *(OK)* | `G05` | `VERIFIED` |
| 5 | `w5_m1_loader_fam_receipt` | `.runtime/offensive5/audits/w5_m1_loader_fam_receipt.json` | `62.368 B` | `f4b19590c46c36aa` | `f1b56209d8aa882a` *(OK)* | `G06` | `PASS` |
| 6 | `w5_m1_arena_receipt` | `.runtime/offensive5/audits/w5_m1_arena_receipt.json` | `24.368 B` | `1c4e5ad50b19cdff` | `6f99a7ad36d2292e` *(OK)* | `G07..G09` | `PASS (0 ADD)` |
| 7 | `wave5_m1_arena_summary` | `.runtime/offensive5/alpha/wave5_m1_arena_summary.json` | `547.933 B` | `3cb057badbdb2b0a` | `87fa578f5bf5a255` *(OK)* | `G07..G09` | `VERIFIED` |
| 8 | `wave5_m1_cluster_a_frozen` | `.runtime/offensive5/alpha/wave5_m1_cluster_a_frozen.json` | `10.499 B` | `3a66dab0a7e37321` | `bb5c12e2a27f8800` *(OK)* | `G07` | `VERIFIED` |
| 9 | `port_v5_tapes_npz` | `.runtime/offensive5/alpha/port_v5_tapes.npz` | `212.147 B` | `0a9a2abe0ebf354c` | *(binary SHA-256)* | `G09` | `VERIFIED` |
| 10 | `w5_ml_v105_arena_receipt` | `.runtime/offensive5/audits/w5_ml_v105_arena_receipt.json` | `19.520 B` | `da4fa0f5049c62a1` | `b58d21a9944e02b9` *(OK)* | `G10P,G11` | `PASS` |
| 11 | `wave5_ml_arena_summary` | `.runtime/offensive5/ml/wave5_ml_arena_summary.json` | `183.479 B` | `9dad692a8e907063` | `b789943b2b300644` *(OK)* | `G11` | `REJECT_ML` |
| 12 | `wave5_ml_oof_series` | `.runtime/offensive5/ml/wave5_ml_oof_series.json` | `557.456 B` | `2b42adf56cfc74dd` | *(N/A)* | `G11` | `VERIFIED` |
| 13 | `naqex_v105_lgbm_onnx` | `.runtime/offensive5/ml/naqex_v105_lgbm.onnx` | `21.476 B` | `cb8c757cab971f09` | *(binary SHA-256)* | `G11,G12` | `VERIFIED` |
| 14 | `wave5_ml_parity_500_csv` | `.runtime/offensive5/ml/wave5_ml_parity_500.csv` | `48.585 B` | `da217c51577cc965` | *(binary SHA-256)* | `G11,G12` | `VERIFIED` |
| 15 | `wave5_2024_features_ref_csv` | `.runtime/offensive5/ml/wave5_2024_features_ref.csv` | `162.600 B` | `e4ba9db191393cb4` | *(binary SHA-256)* | `G10,G11` | `VERIFIED` |
| 16 | `w5_modular_mt5_receipt` | `.runtime/offensive5/audits/w5_modular_mt5_receipt.json` | `45.530 B` | `6c5bb0e2028b0318` | *(N/A)* | `G10,12,15` | `PASS (15/15)` |
| 17 | `w5_dp_closedloop_receipt` | `.runtime/offensive5/audits/w5_dp_closedloop_receipt.json` | `15.400 B` | `1b8aaf864ce03da4` | `b4c4def75fcfb4c0` *(OK)* | `G13,16,17` | `PASS` |
| 18 | `bellman_dp_schedule` | `.runtime/offensive5/pareto/bellman_dp_schedule.json` | `32.581 B` | `7558e476f176667c` | `f0537eeee9f34621` *(OK)* | `G13` | `VERIFIED` |
| 19 | `alpha_factory_ledger` | `.runtime/offensive5/factory/alpha_factory_ledger.json` | `33.649 B` | `f5b58ea6d879aa27` | `43c563d995bebe84` *(OK)* | `G16,G17` | `VERIFIED` |
| 20 | `alpha_factory_e2e_drills` | `.runtime/offensive5/factory/alpha_factory_e2e_drills.json` | `18.908 B` | `f45d80f3284ef0ef` | `ea71ae70678afbca` *(OK)* | `G16,G17` | `PASS (5/5)` |
| 21 | `w5_spectrum_mc_receipt` | `.runtime/offensive5/audits/w5_spectrum_mc_receipt.json` | `52.037 B` | `dd798d6caeb5b63d` | `f909615b5164ba4e` *(OK)* | `G14` | `PASS` |
| 22 | `mc_spectrum_summary` | `.runtime/offensive5/pareto/mc_spectrum_summary.json` | `305.179 B` | `5f11fb60d58a6aa0` | `604953d3649dedba` *(OK)* | `G14` | `VERIFIED` |
| 23 | `mc_spectrum_all_cases` | `.runtime/offensive5/pareto/mc_spectrum_all_cases.json` | `9.326.112 B` | `711c6b4712683c22` | `9cdc9f4dc6302b36` *(OK)* | `G14` | `VERIFIED` |
| 24 | `unified_eval_catalog_duckdb` | `.runtime/experiments/unified_eval_catalog.duckdb` | `10.498.048 B` | `6da12129ffa1b879` | *(binary SHA-256)* | `G03,05,14` | `VERIFIED` |
| 25 | `unified_eval_registry_sqlite3` | `.runtime/experiments/unified_eval_registry.sqlite3` | `380.928 B` | `7804b75e1c541b6d` | *(binary SHA-256)* | `G03,05,14` | `VERIFIED` |
| 26 | `w5_trader_ui_receipt` | `.runtime/offensive5/audits/w5_trader_ui_receipt.json` | `8.852 B` | `f0d24cfe3d4d5a0f` | `4bb78e4a4145ad6c` *(OK)* | `G21` | `PASS` |

---

## 5. Hành Động Kế Tiếp (`< 2` Phút · `0 VND` · `OrderSend = 0`)

Chạy lệnh chỉ đọc kiểm tra toàn vẹn danh mục hợp nhất DuckDB (`1.342` thử nghiệm cũ + `1.250` ca MC + `122` lượt chạy) và `11/11` tệp khóa trước chuỗi mốc thực địa `01/12 -> 13/12`:

```powershell
python tooling/check_architecture.py --strict; python tooling/check_workspace.py
```
