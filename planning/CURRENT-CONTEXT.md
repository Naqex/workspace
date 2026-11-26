# Current context — Naqex Workspace

`26/11/2026 11:39 ICT` · `WORK: STEP1-PREDECISION-OBSERVABILITY-PASS | V101-ON-EQ-OFF-100PCT | HALTED_AT_PARITY_GATE | 0-VND | LIVE-NODE1: ONLINE-CONNECTED-FLAT | HOLDOUT 2025+ SEALED`

`GOAL-NOW: BƯỚC 1 ĐẠT 100% (ON==OFF 640/640 DEAL + 320/320 ACCEPT + 27.351/27.351 REJECT_LOT_MIN + 114/114 TAPER + 1/1 KILL, MAX ΔBAL=0,00 USD, 0 LỆNH GỬI BROKER) | GIỮ HALTED_AT_PARITY_GATE & 0 VND | CHỜ ASTRA VÒNG 5 DUYỆT BƯỚC 2 v1.02-A/B`

## 0. Trạng Thái Hiện Tại Sau Bước 1 Quan Sát Trước Quyết Định (`26/11/2026`)

- **Bước 1 — Nhật ký trạng thái trước quyết định không đổi hành vi `v1.01` ([STEP1 Report](research/STEP1-V101-PREDECISION-OBSERVABILITY-AND-FORMULA-PARITY-20261126.md)):**
  - Thêm cờ tắt mặc định `InpTesterEmitDecisionLog = false` vào `Naqex_Master_Prop7E.mq5` (`0 errors, 0 warnings`, `ex5 sha16=f395512e39508552`), giữ nguyên 100% hành vi `v1.01`.
  - **Gate A1 (`ON == OFF`, 4 ca / 8 lượt `Model=4`):** Khớp **`100,00%`** (`640/640` deal, `0` lệch, `0,00 USD`, `swap = 0,00`, khớp nguyên văn `v1.01` chưa gắn log; lượt `OFF` tạo `0` CSV).
  - **Gate A2 & A3 (Công thức Python không nhìn trước từ ảnh chụp trước quyết định):** Khớp **`320/320`** `INTENT_ACCEPT_FILL`, **`27.351/27.351`** `INTENT_REJECT_LOT_MIN`, **`114/114`** `LOT_TAPER`, **`1/1`** `KILL_ACTIVATED`, `max_balance_diff = 0,0000 USD`; `ADV_A` tách bạch sạch `LOT_TAPER → KILL_ACTIVATED → CLOSE_REQUEST → CLOSE_FILL`.
  - **Bằng chứng mới từ log thật:** `C10 P2 02/12 18:30` xác nhận trực tiếp lỗ nổi `-63,35 USD` (`bal 10.380,28`, `eq 10.316,93`, `3,169% < 3,50%`) là nguyên nhân duy nhất thoát `ProfitLock`; `ADV_B2` (`23/10`) `E6` không dừng ở `L631` mà rơi vào nhánh thoát im `L653` (`lots < volMin`) đúng `24.635` lần (và `596` / `2.120` lần trong `C10 P2` / `C00 P1` — trước đây tàng hình ở cả Live lẫn Tester!).
  - Kho bằng chứng gốc: `private_vault/strategies/step1-predecision-observability-20261126/raw_mt5_logs/` (`44` tệp gốc có cả SHA-256 giải nén và nén).
- **Phán quyết chính thức Sprint 6 giờ ([Hồ sơ Kiểm toán Sprint 6 giờ — đã đính chính 3 điểm Vòng 4](research/SPRINT-6H-STANDARD-PARITY-AND-C00-VS-C10-AUDIT-20261126.md)):**
  - **DỪNG CHẶNG 3 KINH TẾ (`HALTED_AT_PARITY_GATE`):** Giữ cứng `0 VND` (`0` lệnh gửi tới broker), `C10` chưa thăng hạng, `C00` không tự động được công nhận có edge; `R1/R2` giữ nhãn `SKIPPED_IN_TESTER / chưa kiểm nhánh MQL khi restart`; chờ Astra Vòng 5 duyệt để thử riêng từng thay đổi `v1.02-A` (`ProfitLock` balance + `MathMin`) và `v1.02-B` (mã cơ hội ổn định + hết hiệu lực theo setup + log `L653`).
  - **Chẩn đoán tháng `9–12/2024` (`4/12` tháng giao `.tkc` trên `8/8` mã, thiếu `47/96` tháng-mã — KHÔNG phải `Full-2024`):** `0 ms / 500 ms`: `C00` P1 `+730,55 / +790,52 USD` (`EqDD 6,25% / 6,24%`) vs `C10` P1 `+371,25 / +419,41 USD` (`EqDD 8,82% / 8,72%`); `C00` P2 `+371,00 / +404,99` vs `C10` P2 `+461,44 / +517,31`. Pháp y `28` lệnh sống (`2` SL `US100.cash`): `KHÔNG TÁCH ĐƯỢC`; mẫu đo chỉ đọc `QUOTE_ONLY` cho NFP `04/12` & CPI `10/12` sẵn sàng.
  - **Hiệu chính kế hoạch tổng thể:** Đã thêm hộp hiệu chính toán học đầu trang [TOP1-SOLO-QUANT-MASTER-PLAN.md](TOP1-SOLO-QUANT-MASTER-PLAN.md) (`Đậu + Rớt + Chờ` Ngày 180 = `100%`; ghép 4 nhánh không tự nhân lãi `1×` lên `18–30%`; Năm 1 = `0 VND` thu nhập trading).

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

1. **Gửi Prompt Astra Vòng 4** trong mục 7 của [SPRINT-6H-STANDARD-PARITY-AND-C00-VS-C10-AUDIT-20261126.md](research/SPRINT-6H-STANDARD-PARITY-AND-C00-VS-C10-AUDIT-20261126.md) để chốt thiết kế cho 4 bản vá `v1.02`.
2. **Thực hiện 4 hạng mục vá gốc cho `v1.02` trước mọi vòng kiểm định lại:** (a) cờ nhật ký Tester cho `LogMasterShadowRow` / `LogExecAuditFor` / `lots < volMin`; (b) thống nhất `ProfitLock` (Balance vs Equity + hysteresis) giữa MQL5 và Python; (c) thống nhất khóa cùng ngày vs thử lại cho tín hiệu bị chặn cụm/margin (`ADV_B2`); (d) đồng bộ cắt lệnh mở giữa ngày vào Python (`Step 2B`) + diễn tập khởi động lại sống `R1/R2` trên Demo thật.
3. **Thu thập chỉ đọc `QUOTE_ONLY` (`OrderSend = 0`) quanh NFP `04/12` & CPI `10/12`** theo đúng mẫu [NFP-CPI-READONLY-CAPTURE-TEMPLATE.md](../tooling/ai-engines/exports/deployment_kit/NFP-CPI-READONLY-CAPTURE-TEMPLATE.md) (ghi đủ `time_msc`, tách rạch ròi `QUOTE_ONLY` khỏi `FILL_VERIFIED`).
4. **Giữ cứng `0 VND` & không mở Holdout `2025+`:** Chỉ đánh giá lại lựa chọn vé trả phí sau khi `v1.02` vượt cổng Parity 7 mắt xích và có dữ liệu đo chỉ đọc NFP/CPI.
