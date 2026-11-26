# Current context — Naqex Workspace

`26/11/2026 12:36 ICT` · `WORK: STEP2-V102AB-ISOLATED-AND-PYTHON-SELF-REPLAY-PASS | HALTED_AT_PARITY_GATE | 0-VND | LIVE-NODE1: ONLINE-CONNECTED-FLAT | HOLDOUT 2025+ SEALED`

`GOAL-NOW: BƯỚC 2 ĐẠT 100% (PYTHON TỰ DỰNG MÙ 23/10 Δ=0,00 USD + v1.02-A RIÊNG MathMin/KILL + v1.02-B RIÊNG STABLE OPP_ID, 0 LỆNH GỬI BROKER) | GIỮ CỔNG KINH TẾ DỪNG & 0 VND | CHỜ ASTRA VÒNG 6 DUYỆT GHÉP A+B`

## 0. Trạng Thái Hiện Tại Sau Bước 2 (`26/11/2026`)

- **Bước 2 — Tự dựng mù Python ngày `23/10` & thử tách rời `v1.02-A` / `v1.02-B` trên nền `v1.01` ([STEP2 Report](research/STEP2-V102AB-ISOLATED-AND-PYTHON-REPLAY-AUDIT-20261126.md)):**
  - **Phần 2.0 (Vá 3 điểm hồ sơ Bước 1):** Đã nối kiểm `reject_lot_min` & `lot_taper` + nhãn `UNTESTED` vào cổng `PASS` của runner Bước 1 (`--reverify-existing` xác minh `44/44` SHA-256 trong `2,51s`, `0` lượt MT5), thu hẹp câu chữ cửa sổ chung và gắn nhãn phụ lục lịch sử Vòng 4.
  - **Phần 2.1 (Python tự dựng mù ngày `23/10/2024` từ chuỗi giá thuần `61.269` chu kỳ):** `0` cột trạng thái EA được đưa vào đầu vào; Python tự dựng chỉ báo, tín hiệu, vị thế, `equity`, `factor_headroom`, lot khớp **`100%`** (`11/11` sự kiện chính, **`24.635/24.635`** `INTENT_REJECT_LOT_MIN`, `0` tín hiệu thiếu/dư, `max Δbal = 0,00 USD`, `max Δeq = 0,00 USD`, `max Δfh = 0,000000%`, đúng thứ tự cùng giây `18:00:00`: đóng `E1` → giải phóng hạn mức → mở `E6 0,10 lot`, cuối ngày `10.216,84 USD`).
  - **Phần 2.2 (`v1.02-A` riêng, `pl_mode=1, opp_mode=0`, `v1.01` đối chứng `0` lệch):** Hai ca đối kháng `balance >= ProfitLock` & `equity >= AMBER/RED` đều chọn đúng hệ số thấp hơn qua `MathMin` (`AMBER+PL = 1,75×`, `RED+PL = 1,60×`) và `KILL_ACTIVATED` vẫn cắt vị thế theo `equity`; `C10 P2` `02/12 E5` giữ `0,40 lot` (`+462,38` vs `+461,44 USD`), `C00 P1` `+708,89` vs `+730,55 USD` (thay đổi chính sách sizing, không mặc định lời hơn).
  - **Phần 2.3 (`v1.02-B` riêng, `pl_mode=0, opp_mode=1`):** `ADV_B2` `E6` giữ `1` `opportunity_id` ổn định qua `24.635` lượt chặn (`root=LOW_FACTOR_HEADROOM`, `outcome=RAW_LOTS_BELOW_VOLMIN`), `C10 P2` `157` cơ hội (`1` `SESSION_ENDED`), `C00 P1` `196` cơ hội (`40` `PRICE_CONDITION_LOST`, `1` `SESSION_ENDED`), cả `3/3` khớp `100%` deal `v1.01`. Nhánh `R1/R2` & giữ ID qua restart thật vẫn mang nhãn `chưa kiểm`.
  - Kho bằng chứng gốc: `private_vault/strategies/step2-v102ab-and-replay-20261126/` (`market_feed_20241023/` + `48` tệp log thô có SHA-256 giải nén và nén).
- **Bước 1 & Sprint 6 giờ (lịch sử đã kiểm toán):** [STEP1 Report](research/STEP1-V101-PREDECISION-OBSERVABILITY-AND-FORMULA-PARITY-20261126.md) (`44/44` SHA-256, `640/640` deal ON/OFF) · [Sprint 6 giờ](research/SPRINT-6H-STANDARD-PARITY-AND-C00-VS-C10-AUDIT-20261126.md) (`90/90` SHA-256, `HALTED_AT_PARITY_GATE`, đính chính toán học ở [TOP1-SOLO-QUANT-MASTER-PLAN.md](TOP1-SOLO-QUANT-MASTER-PLAN.md)).

## 1. Kiến Trúc Đã Khóa & Khóa An Toàn Bất Biến

- **Hợp đồng chuẩn:** [prop_contracts_v2.json](../tooling/ai-engines/configs/prop_contracts_v2.json) đã có đủ `ftmo_swing_10k`, `ftmo_standard_10k` (chính thức mới), `the5ers_hs_5k`; `3` preset `C10` mới giữ cứng `DryRun = true`, `4` preset `C00` v1.01 giữ nguyên.
- **Kiến trúc `2` trụ cột gọn sạch (`3 / 56 PASS` ngoài CFD):** (1) Prop Cash-Flow (`PORT_7E` cố định `E1..E7`, `swap = 0`, loại vĩnh viễn `S7_XAU_EXP120`, khóa cụm hướng `USD/JPY/US100`); (2) Own-Book (`75% SGOV/IB01 + 25% Crypto Spot B06/B02 Shadow`, trần `CEX <= 25%`, hoãn dưới `10k USD`).
- **Khóa bảo mật 2 tầng & Holdout:** [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json) niêm phong tuyệt đối (`holdout_rows_analysed = 0`); Layer-2 `private_vault/` tách hoàn toàn khỏi Layer-1 Public (được bảo vệ bởi `test_layer1_opsec_guard.py` và bộ kiểm thử biên mới [test_standard_parity_and_boundaries.py](../tooling/ai-engines/tests/test_standard_parity_and_boundaries.py)).

## 2. Trạng Thái Hạ Tầng `naqex-node1` & `3` Repo Sản Phẩm (`projects/`)

| Thành phần | Trạng thái xác minh | Ghi chú & Điểm kiểm soát |
|---|---|---|
| **Home-VPS `naqex-node1`** | **`ONLINE GREEN / UNTOUCHED`** | Không chạm suốt Sprint 6 giờ; Free Trial Demo phẳng (`open=0`, `orphan=0`, `KeepPrivate=1`, `NTP -0,029s`, Heroku EU Deadman v4 `OK`, Geo-IP `VN`). |
| **MT5 Dev Portable cục bộ** | **`0% CPU / 0 tiến trình`** | Đã đóng sạch sau `18` lượt `Model=4` Real-Tick (`ToDate=2024.12.31`), `0` tệp `*transient*.ini`. |
| **`projects/trader` (`Naqex/trader`)** | **`main @ c5a44c4f` (`15/15` CI PASS)** | Không chạm trong Sprint 6 giờ. |
| **`projects/quant-trading`** | **`master @ 25fc67d` (`pytest` 100% PASS)** | Không chạm trong Sprint 6 giờ. |
| **`projects/vi-dubber`** | **`origin/main @ 5da3c65` (TẠM DỪNG)** | 4 tệp WIP cục bộ của chủ sở hữu giữ nguyên 100%. |
| **Giáo dục (`education/`)** | **`check_setup.py` exit `0`** | Đã có `education/tools/drill_generator.py` (`leverage_margin_vs_pnl`). |

## 3. Việc Kế Tiếp (Ưu Tiên Theo Thứ Tự Khóa Cổng — `0 VND`)

1. **Gửi Prompt Astra Vòng 6** trong mục 3 của [STEP2-V102AB-ISOLATED-AND-PYTHON-REPLAY-AUDIT-20261126.md](research/STEP2-V102AB-ISOLATED-AND-PYTHON-REPLAY-AUDIT-20261126.md) để duyệt ghép `v1.02 (A + B)` và bước mở rộng Python tự dựng mù sang dải `9–12/2024`.
2. **Giữ cổng kinh tế dừng & `0 VND`, không mở Holdout `2025+`:** Chỉ cân nhắc mở lại đánh giá kinh tế `C00` vs `C10` sau khi `v1.02 (A + B)` vượt đối chiếu độc lập và `R1/R2` có diễn tập restart ngoài Tester.
3. **Thu thập chỉ đọc `QUOTE_ONLY` (`OrderSend = 0`) quanh NFP `04/12` & CPI `10/12`** theo mẫu [NFP-CPI-READONLY-CAPTURE-TEMPLATE.md](../tooling/ai-engines/exports/deployment_kit/NFP-CPI-READONLY-CAPTURE-TEMPLATE.md).
