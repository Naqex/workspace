# Current context — Naqex Workspace

`26/11/2026 14:40 ICT` · `WORK: STEP3-V102AB-MERGED-AND-4M-BLIND-REPLAY-COMPLETE | HALTED_AT_PARITY_GATE | 0-VND | LIVE-NODE1: ONLINE-CONNECTED-FLAT | HOLDOUT 2025+ SEALED`

`GOAL-NOW: BƯỚC 3 HOÀN TẤT (VÁ 2 LỖI NỀN 24.646/24.646 + HỢP NHẤT A+B 5/5 KHỚP A & 100% HẠCH TOÁN + PHÁT LẠI MÙ LIÊN TỤC 4 THÁNG 85/85 NY ANCHOR & 312/312 C10, 310/310 C00) | GIỮ CỔNG KINH TẾ DỪNG & 0 VND | CHỜ ASTRA VÒNG 7`

## 0. Trạng Thái Hiện Tại Sau Bước 3 (`26/11/2026`)

- **Bước 3 — Vá lỗi nền, Hợp nhất `v1.02 (A + B)` & Phát lại mù liên tục `4` tháng ([STEP3 Report](research/STEP3-V102AB-MERGED-AND-CONTINUOUS-REPLAY-AUDIT-20261126.md)):**
  - **Bước 3.1 (Vá 2 lỗi nền + hoàn thiện đếm `B`):** Loại hoàn toàn nhìn trước mốc `09:30` NY (`US100 = 20.280,45`, `US500 = 5.830,05` khớp `0,00000` với `NY_ANCHOR_LOCKED` của MT5, đạt bất biến tương lai `+1/+100` điểm); thay bộ so sánh bằng luồng hợp nhất fail-closed (`24.646/24.646` khớp, trả exit code `2` khi lỗi, chặn đúng `3/3` đột biến âm); siết runner Bước 2 buộc `3/3` `v1.02-B == v1.01` (`48/48` SHA-256 bảo toàn); lượng hóa biên `vol_step` (`5,97%` flip rate ở độ lệch `0,54%` bộ đệm `tick_value_loss`); nối hạch toán `blk_by` cho toàn bộ nhánh chặn trong MQL5 (`0 errors, 0 warnings`, `.ex5` `af2ad46b1f430ba8`, `8/8` parity, `130` SHA kit).
  - **Bước 3.2 (Hợp nhất `v1.02 A + B`, `InpSizingMode = 0`, `6` lượt `Model=4`, `36` tệp gốc):** `overall_step3_2_pass = True`; **`5/5` lượt `A + B` khớp nguyên văn `100%` với `v1.02-A` thuần** (`C10 P2 +462,38 USD`, `C00 P1 +708,89 USD`, `ADV_B2 +216,84 USD`, `ADV_PL_LT_AMBER` / `ADV_RED_LT_PL` `InitBal = 9.920 USD`); **`eval == accepted + sum(blk_by)` đạt `100%`** trên mọi cơ hội (xác nhận `E7 = 601 = 596 lmin + 5 spread` và `C00 P1` đủ `22 news`, `12 spread`, `2.120 lmin`).
  - **Bước 3.3 (3 cửa sổ biên trước → Phát lại mù liên tục `4` tháng `01/09–31/12/2024`, `5.347.386` chu kỳ/kịch bản, `0` reset số dư):**
    - `3` cửa sổ biên: Nghỉ lễ Mỹ (`16/16` deal, `638/638` sự kiện, `+0,00 USD`), Chuyển giờ DST EU/Mỹ (`30/30` deal gồm `6/6` SL `0s`, `60/60` sự kiện, `+0,00 USD`), Tuần SL + NFP (`22/22` đúng giây `0s`, chỉ rõ `+0,05 USD` quy đổi chéo `EURJPY`, trượt giá NFP `9` điểm `06/09 15:30:00` và cú nhảy biên `vol_step` ngày `06/09 18:00:17`).
    - Cả `4` tháng liên tục: **`85/85` mốc `09:30` NY khớp `100%`** trên cả hai kịch bản; `C10 P2`: **`312/312` deal** (`311/312` đúng giây `0s`, `40/40` SL `0s`, `18/18` SL không trượt lệch `0,00 USD`, `22` SL trượt dưới `1s` = `+31,46 USD` / tổng lệch `+38,28 USD`); `C00 P1` (`RedNews=ON`): **`310/310` deal** (`309/310` đúng giây `0s`, `35/35` SL `0s`, `22/22` chặn tin đỏ, `16/16` SL không trượt lệch `0,00 USD`, `19` SL trượt dưới `1s` = `+16,85 USD` / tổng lệch `+18,19 USD`). Nhánh `R1/R2` & giữ ID qua restart thật vẫn mang nhãn `chưa kiểm`.
  - Kho bằng chứng gốc: `private_vault/strategies/step3-v102ab-merged-and-replay-20261126/` (`36` tệp log thô Bước 3.2 + `28` tệp thị trường thuần Bước 3.3 trong `market_feeds/`).
- **Bước 2, Bước 1 & Sprint 6 giờ (lịch sử đã kiểm toán):** [STEP2 Report](research/STEP2-V102AB-ISOLATED-AND-PYTHON-REPLAY-AUDIT-20261126.md) (`48/48` SHA-256) · [STEP1 Report](research/STEP1-V101-PREDECISION-OBSERVABILITY-AND-FORMULA-PARITY-20261126.md) (`44/44` SHA-256, `640/640` deal ON/OFF) · [Sprint 6 giờ](research/SPRINT-6H-STANDARD-PARITY-AND-C00-VS-C10-AUDIT-20261126.md) (`90/90` SHA-256, `HALTED_AT_PARITY_GATE`, đính chính toán học ở [TOP1-SOLO-QUANT-MASTER-PLAN.md](TOP1-SOLO-QUANT-MASTER-PLAN.md)).

## 1. Kiến Trúc Đã Khóa & Khóa An Toàn Bất Biến

- **Hợp đồng chuẩn:** [prop_contracts_v2.json](../tooling/ai-engines/configs/prop_contracts_v2.json) đã có đủ `ftmo_swing_10k`, `ftmo_standard_10k` (chính thức mới), `the5ers_hs_5k`; `3` preset `C10` mới giữ cứng `DryRun = true`, `4` preset `C00` v1.01 giữ nguyên.
- **Kiến trúc `2` trụ cột gọn sạch (`3 / 56 PASS` ngoài CFD):** (1) Prop Cash-Flow (`PORT_7E` cố định `E1..E7`, `swap = 0`, loại vĩnh viễn `S7_XAU_EXP120`, khóa cụm hướng `USD/JPY/US100`); (2) Own-Book (`75% SGOV/IB01 + 25% Crypto Spot B06/B02 Shadow`, trần `CEX <= 25%`, hoãn dưới `10k USD`).
- **Khóa bảo mật 2 tầng & Holdout:** [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json) niêm phong tuyệt đối (`holdout_rows_analysed = 0`); Layer-2 `private_vault/` tách hoàn toàn khỏi Layer-1 Public (được bảo vệ bởi `test_layer1_opsec_guard.py` và bộ kiểm thử biên mới [test_standard_parity_and_boundaries.py](../tooling/ai-engines/tests/test_standard_parity_and_boundaries.py)).

## 2. Trạng Thái Hạ Tầng `naqex-node1` & `3` Repo Sản Phẩm (`projects/`)

| Thành phần | Trạng thái xác minh | Ghi chú & Điểm kiểm soát |
|---|---|---|
| **Home-VPS `naqex-node1`** | **`ONLINE GREEN / UNTOUCHED`** | Không chạm suốt Bước 1–3; Free Trial Demo phẳng (`open=0`, `order_send_count=0`, `orphan=0`, `KeepPrivate=1`, `NTP -0,054s`, Heroku EU Deadman v4 `OK`, Geo-IP `VN`). |
| **MT5 Dev Portable cục bộ** | **`0% CPU / 0 tiến trình`** | Đã đóng sạch sau toàn bộ lượt `Model=4` Real-Tick & xuất chuỗi giá thuần (`ToDate=2024.12.31`), `0` tệp tạm `step3_*.htm/png/set`. |
| **`projects/trader` (`Naqex/trader`)** | **`main @ c5a44c4f` (`15/15` CI PASS)** | Không chạm trong Sprint 6 giờ. |
| **`projects/quant-trading`** | **`master @ 25fc67d` (`pytest` 100% PASS)** | Không chạm trong Sprint 6 giờ. |
| **`projects/vi-dubber`** | **`origin/main @ 5da3c65` (TẠM DỪNG)** | 4 tệp WIP cục bộ của chủ sở hữu giữ nguyên 100%. |
| **Giáo dục (`education/`)** | **`check_setup.py` exit `0`** | Đã có `education/tools/drill_generator.py` (`leverage_margin_vs_pnl`). |

## 3. Việc Kế Tiếp (Ưu Tiên Theo Thứ Tự Khóa Cổng — `0 VND`)

1. **Gửi Prompt Astra Vòng 7** trong mục 2 của [STEP3-V102AB-MERGED-AND-CONTINUOUS-REPLAY-AUDIT-20261126.md](research/STEP3-V102AB-MERGED-AND-CONTINUOUS-REPLAY-AUDIT-20261126.md) để chốt `4` câu hỏi: thăng hạng `v1.02 (A + B)` mặc định, xử lý `profit_pct` sau đóng cùng giây `18:00:00`, mở Bước 4 diễn tập restart `R1/R2` ngoài Tester & đối chứng kinh tế `C00` vs `C10` có tính trượt giá SL.
2. **Giữ cổng kinh tế dừng & `0 VND`, không mở Holdout `2025+`:** Chỉ thay đổi quyết định tài chính sau khi có phán quyết rõ ràng của chủ sở hữu & Astra Vòng 7.
3. **Thu thập chỉ đọc `QUOTE_ONLY` (`OrderSend = 0`) quanh NFP `04/12` & CPI `10/12`** theo mẫu [NFP-CPI-READONLY-CAPTURE-TEMPLATE.md](../tooling/ai-engines/exports/deployment_kit/NFP-CPI-READONLY-CAPTURE-TEMPLATE.md).
