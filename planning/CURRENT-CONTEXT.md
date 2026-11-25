# Current context — Naqex Workspace

`26/11/2026 02:15 ICT` · `WORK: SPRINT-6H-PARITY-HALTED-AT-GATE | C10-UNPROMOTED | 0-VND | LIVE-NODE1: ONLINE-CONNECTED-FLAT | HOLDOUT 2025+ SEALED`

`GOAL-NOW: ĐÃ DỪNG CHẶNG 3 KINH TẾ TẠI CỔNG PARITY (THEO LUẬT ASTRA V3.1) -> GIỮ CỨNG 0 VND (C10 CHƯA THĂNG HẠNG, C00 CHƯA TỰ ĐỘNG ĐƯỢC CÔNG NHẬN CÓ EDGE) | CHUYỂN SANG VÁ 4 LỖI ĐỒNG BỘ PYTHON<->MT5 CHO v1.02 + THU THẬP CHỈ ĐỌC QUOTE_ONLY QUANH NFP 04/12 & CPI 10/12`

## 0. Trạng Thái Hiện Tại Sau Sprint 6 Giờ Parity (`26/11/2026`)

- **Phán quyết chính thức ([Hồ sơ Kiểm toán Sprint 6 giờ](research/SPRINT-6H-STANDARD-PARITY-AND-C00-VS-C10-AUDIT-20261126.md)):**
  - **DỪNG CHẶNG 3 KINH TẾ (`HALTED_AT_PARITY_GATE`):** Không chạy Monte Carlo thăng hạng vì kiểm định 7 mắt xích trên `Naqex_Master_Prop7E.ex5` (`v1.01`, `sha16=2e0006ad786bdad6`) phát hiện sai lệch thực thi thực chất ở **cả `C00` đối chứng lẫn `C10` ứng viên** và điểm mù quan sát trong MT5 Tester:
    1. **Link #4 (Đổi chế độ trong ngày theo `ACCOUNT_EQUITY` nổi):** Nhảy khối lượng `1,77×` trên `C00` P1 (`19/11`: `0,47 -> 0,83`), `1,91×` trên `C00` P2 (`19/11`: `0,23 -> 0,44`), và `2,00×` trên `C10` P2 (`02/12`: `0,40 -> 0,80`); phanh `AMBER` giữa ngày `05/11` làm Step 2A đánh lố `+49,2%`.
    2. **Link #2 (Từ chối tín hiệu & vào trễ):** `UNOBSERVABLE_IN_TESTER` (`LogMasterShadowRow` L373 & `LogExecAuditFor` L993 thoát sớm, `lots < volMin` L653/L667 không log -> `0` dòng log); trong kịch bản `ADV_B2` (`23/10`), `E6` bị chặn cụm JPY lúc `10:00:00` rồi **vào trễ `8` tiếng lúc `18:00:00` (`0,10` lot)** khi `E1` đóng.
    3. **Link #5 (Tự ngắt giữa ngày & giới hạn `OnTick` `1` giây):** `ADV_A` (`19/11`) xác nhận MT5 cắt cả 2 lệnh mở lúc `18:36:02` (`-181,03 -> -84,56 USD`) còn Step 2A để lệnh sống; `OnTick` `1` giây bỏ lọt cú xuyên sàn dưới `1` giây; `12/12` lượt chạy pha đều `swap = 0,00 USD`.
    4. **`R1` & `R2` Restart Hydration:** Cả hai đều `SKIPPED_IN_TESTER`; bài kiểm thử Python ngoại tuyến đạt nhưng gắn nhãn `PYTHON_LOGIC_VERIFIED_MQL_BRANCH_UNEXECUTED / UNTESTED_ON_LIVE_RESTART`.
  - **Bước 2A (Chứng minh đổi hồ sơ `Swing -> Standard`):** Đã chứng minh lỗi rơi ngầm tại `pass27_portfolio_m1_phase_audit.py:318` (truyền `"ftmo_standard_10k"` âm thầm dùng ký quỹ Swing); khi truyền `"Standard"`, ký quỹ `1` lot giảm đúng `3,3333×` (`-70,0%`) trên cả `4` mã lõi, `0` margin rejects.
  - **Chẩn đoán Q4/2024 theo cặp (`4/12` tháng có đủ `.tkc` cho `8/8` mã; `47/96` tháng-mã 2024 bị thiếu — KHÔNG phải `Full-2024`):** Tại `0 ms / 500 ms` (`L1:100`, `20,02M` tick, `swap = 0,00`): `C00` P1 `+730,55 / +790,52 USD` (`EqDD 6,25% / 6,24%`) vs `C10` P1 `+371,25 / +419,41 USD` (`EqDD 8,82% / 8,72%`); `C00` P2 `+371,00 / +404,99` (`EqDD 3,73% / 3,72%`) vs `C10` P2 `+461,44 / +517,31` (`EqDD 7,61% / 7,48%`); `C00` Funded `+119,53 / +144,97` vs `C10` Funded `+161,83 / +194,94`.
  - **Pháp y `28` lệnh sống (`2` lần SL `US100.cash` `#26 +385 pts` & `#28 -45 pts`):** Chốt **`KHÔNG TÁCH ĐƯỢC` (`UNSEPARABLE_MISSING_TRIGGER_QUOTE`)** do khoảng mù quét `5.000 ms` & thiếu `DEAL_TIME_MSC`; sốc `750 / 1.000` pts gắn nhãn `STRESS_ASSUMPTION`.
  - **Hiệu chính kế hoạch tổng thể:** Đã thêm hộp hiệu chính toán học đầu trang [TOP1-SOLO-QUANT-MASTER-PLAN.md](TOP1-SOLO-QUANT-MASTER-PLAN.md) (`Đậu + Rớt + Chờ` Ngày 180 = `100%`; ghép 4 nhánh không tự nhân lãi `1×` lên `18–30%`; Năm 1 = `0 VND` thu nhập trading).
  - **Lưu trữ bằng chứng gốc:** `private_vault/strategies/sprint-6h-standard-parity-20261126/` lưu đủ `manifest_locked.json`, `step2a_profile_ablation.json`, `first_divergence_report.json`, `tick_and_28fills_forensics.json`, và `raw_mt5_logs/` (`18` lượt chạy / `90` tệp `.htm`/`.log`/`.set`/`.ini` gốc + `raw_logs_index.json`).

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
