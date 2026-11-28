# Current context — Naqex Workspace

`28/11/2026 16:10 ICT` · `WORK: TOTAL-OFFENSIVE-5-V5.3-FINAL | 26/26 SSOT RECONCILED | 0-VND | LIVE-NODE1: READ-ONLY | HOLDOUT 2025+ SEALED`

`GOAL-NOW: KHÓA BÁO CÁO TỔNG KẾT & SỔ ĐĂNG KÝ WAVE 5 (GATE W5-G19) | GIỮ V1.03 BẤT BIẾN + T3_BALANCED_EV (V1.03-SPRINT) | PORT_V5 == PORT_7E | REJECT_V105_ML_KEEP_V103 | CHUẨN BỊ CHUỖI MỐC THỰC ĐỊA 30/11 -> 14/12 (0 VND · ORDERSEND = 0)`

## 0. Kết Quả Đã Chốt — Chiến Dịch Total Offensive #5 (`v5.3 FINAL`, `26/26` SHA-256)

- **Nguồn sự thật duy nhất (SSOT Wave 5):** [WAVE5-DEEP-ALPHA-FACTORY-AND-CHALLENGE-SPECTRUM-20261128.md](research/WAVE5-DEEP-ALPHA-FACTORY-AND-CHALLENGE-SPECTRUM-20261128.md) · `.runtime/offensive5/wave5_master_metrics.json` (`report_sha256: cfc92c32aafe14f9...`, `26/26` artifact khớp, `18` tự băm, `40` liên kết chéo). Kế thừa toàn bộ nền Wave 4 (`40/40` SHA-256, Own-Book `4/4` stress, Frontier `2/3` PASS Cụm B, CME `SKIP`, `S0..S7` + `E1..E6`, PIT-24 `24/24`).
- **4 Trụ Cột Wave 5 (`0 VND`, `OrderSend = 0`, `Holdout 2025+ SEALED`, `MODE_A_OWNER_ACTIVE`):**
  - **Trụ cột 1 — Đấu trường Alpha M1 `28` mã (`W5-G06..G09`):** Niêm phong `28/28` mã (`67.845.762` nến, `12` `M1_BID_ASK` + `10` `M1_BID_SPREAD` + `6` `M1_SINGLE_SIDE`, cách ly `2.753` dòng `USOIL`, `18/28` sẵn sàng HCC). Quét `355/360` ứng viên Cụm A (`100%` offload `X13_WORKER`) -> `6` chung kết mù Cụm B -> trung thực **`0/6` `TIER_1`**, **`1/6` `ALPHA_BENCH_RESERVE`** (`F5D_US30_TO_UK100_CNV_L2_LB30_A`, `PF 1,1317`, `r = -0,0105`, hòa vốn `9,92x`) -> **`PORT_V5 == PORT_7E`**.
  - **Trụ cột 2 — Đóng `W4-RT1-P1-01`, `v1.05-ML` & Bellman DP (`W5-G10`, `W5-G11`, `W5-G13`):** Đóng triệt để `W4-RT1-P1-01` trên MT5 Build 6230 (`777/777` tín hiệu, `f0..f6 <= 2,20e-7`, `100%` đồng thuận `343` lệnh, `0` đuổi trễ/đảo chiều). Phát hiện `FLOAT32_ONNX_QUANTILE_CLIFF` (loại `4` mẫu GMM đồng thuận `float32` `84,4–88,6%`). `36/48` thử nghiệm (`24` Filter + `12` AsymFloor) -> **`0/36` thăng hạng** (`REJECT_V105_ML_KEEP_V103`). Bellman DP `6` bậc chống Martingale (`410/410` cặp DD) thắng sống sót `12T` (`60,29%` đậu, `22,89%` rớt) nhưng thua tốc độ `6T` (`40,71%` vs `51,42%` của `V103_SPRINT`) -> giữ `V103_SPRINT`.
  - **Trụ cột 3 — `Naqex_Master_Modular_v105` `16`-Slot & Closed-Loop Alpha Factory (`W5-G12`, `W5-G15..G17`):** Chứng nhận MT5 Build 6230 **`15/15` cổng PASS**: `Modular_v105` (nghiên cứu, chưa chạy thật) khớp **`100%` với `v1.03` tới `0,00 USD`** (`469/469` lệnh, `+616,87 USD`, `PF 1,15`, `Swap 0,00 USD`), đối khớp `4` chiều `500` mẫu `<= 5,91e-8`, `0` `.ex5` trong `exports/` & `private_vault/`. Nhà máy Alpha khép kín đạt **`5/5` diễn tập E2E** (sổ cái chuỗi băm `29` bản ghi, `auto_deploy_permitted = false`).
  - **Trụ cột 4 — Quang phổ `9` Lịch × `4` Pha, Danh mục DuckDB & Web Cockpit (`W5-G03..G05`, `W5-G14`, `W5-G21`):** `unified_eval_catalog.duckdb` (`1.342` thử nghiệm cũ + `1.250` ca MC + `122` runs, `100%` Pydantic v2), hợp đồng `UI/contracts/evaluation-scorecard/1.0.0/`, đối chiếu SQL `Wave 4 vs Wave 5` (tách `legacy_grade_code` vs `unified_grade_code`, `UNKNOWN_LEGACY_UNINSTRUMENTED` P1/P2 ở Wave 4, `funded_mult 1,25x -> 1,00x`). Quán quân cân bằng **`T3_BALANCED_EV` (`v1.03-Sprint`)**: `100K 1,0x` đơn vé đạt `GOOD` (`EV/Phí 11,93x`, `Pass12 69,78%`, cháy `Fn12 0,30%`, `Pay1 có ĐK 176,8 d` / `không ĐK 234,8 d`); đội quỹ `100 tr` đạt `GOOD` (`Med 36T +1.193,21 tr VND`, `Ruin 0,00%`, `P<=0 24T = 8,20%`); gắn cờ `T5` là `RESEARCH_BOUNDARY_ONLY` + `FTMO_GAMBLING_ALLIN_RISK` (vi phạm `5%` ngày nội nhật `42,06%` ở `1,0x`, `63,79%` dưới gap `1,25x`). Web Cockpit `?view=prop-fleet` (`W5-G21`): `118.298 B < 120 KB`, `89/89` Node, `4/4` Playwright, `0` `/api/*`.

## 1. Khóa An Toàn Bất Biến & Chuỗi Mốc Thực Địa (`30/11 -> 14/12`)

| Thành phần / Mốc | Trạng thái xác minh | Ghi chú & Ràng buộc |
|---|---|---|
| **Ứng viên chạy chính** | **`v1.03` + `T3_BALANCED_EV` · `0 VND`** | `Naqex_Master_Prop7E_v103.mq5` (`e6b1b88b...`) bất biến; `PORT_V5 == PORT_7E`; `Modular_v105` chỉ nghiên cứu; `OrderSend = 0`; `MT5_PROCS = 0`. |
| **`11/11` tệp khóa & Holdout** | **SẠCH (`11/11`) · NIÊM PHONG (`0` dòng)** | Lock `f0a6b43c...`; `naqex_red_news_utc.csv` `235722ed...`; `41/41` `quant_core/` sạch; `0` `.ex5` trong `exports/` & `private_vault/`. |
| **Bảng điểm `4` tầng Inside-Out** | **T1 `GOOD` · T2 `SKIP` · T3 `GOOD` · T4 `GOOD`** | Toàn bộ ở cấp `Dev <= 2024-12-31` (chưa lên `TOP_1_PCT` vì `Pay1U 234,8 d > 120 d` và chưa đủ `>= 30` ngày thực địa). |
| **Mốc 1–2 (`30/11` & `01/12`)** | **`30/11 16:00 ICT` · `01/12 07:00 ICT`** | Mở ngày `1/30` `Prospective Shadow Ledger` & giữ hóa đơn Black Friday (`0 VND`) · Khóa tiền đăng ký `holdout_v2_prospective`. |
| **Mốc 3–4 (`04/12` & `08/12`)** | **`04/12 20:30 ICT` · trước `08/12 23:59`** | Thu băng báo giá `QUOTE_ONLY` `US_NFP` · **Thu hoạch chỉ-đọc FTMO Free Trial trên `naqex-node1`** (`harvest_free_trial_forensics.py`). |
| **Mốc 5–6 (`10/12` & `11–14/12`)** | **`10/12 20:30 ICT` · hạn `14/12 16:00`** | Thu băng `QUOTE_ONLY` `US_CPI` · Tổng hợp `Go/No-Go` nội bộ trên `?view=prop-fleet` (giữ `0 VND` nếu trượt giá `> 1,50x` hoặc còn lỗi parity/swap). |

## 2. Việc Kế Tiếp (`0 VND` · `OrderSend = 0`)

1. **Chốt Wave 3B & Kiểm toán toàn repo (`W5-G19..G20`):** hoàn tất báo cáo/sổ đăng ký Wave 5, bộ visual trực quan, kiểm tra `check_architecture.py --strict`, `check_workspace.py`, `test_layer1_opsec_guard.py` và `system_doctor.py --mode fast`.
2. **Thu thập bằng chứng thực địa chuỗi `01/12 -> 10/12` (chỉ đọc, `0 VND`):** xác thực tiền đăng ký `holdout_v2_prospective` (`01/12`), thu băng `QUOTE_ONLY` NFP (`04/12`) & CPI (`10/12`), và thu hoạch trọn log/sao kê FTMO Free Trial trên `naqex-node1` trước hạn `08/12`.
3. **Quyết định cổng `G6` nội bộ trước `14/12 16:00 ICT` (`0 VND` mặc định):** chỉ xem xét bước tiếp theo nếu trượt giá thực đo `<= 1,50x`, `0` lỗi parity/swap và toàn bộ điều kiện Mốc 0 đạt `100%`.
