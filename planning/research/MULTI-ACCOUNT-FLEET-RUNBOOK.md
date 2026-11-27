# Sổ Tay Vận Hành Đội Tài Khoản Prop (S0–S7 & E1–E6)

**Khóa an toàn cứng:** `ORDER_SEND_CAPABLE = False` · `OrderSend = 0` · `Holdout 2025+ SEALED` · `execution_capability: false`. Toàn bộ công cụ quản trị đội và màn hình Web Cockpit chỉ đọc/kiểm chứng offline; mọi thao tác mở vé, đổi file `.set` và bật/tắt EA trên MT5 do chủ tài khoản kiểm tra và làm thủ công.

## 1. Sơ Đồ 8 Trạng Thái `S0..S7` (7 Bước Chuyển Pha)

Mỗi tài khoản đi qua 8 trạng thái chuẩn (`S0..S7`, 7 bước chuyển pha tiến), 3 trạng thái sự cố (`E1..E3`) và 1 trạng thái cuối (`CLOSED_ARCHIVED`):

```text
[S0_PRE_CHALLENGE] --(1)--> [S1_CHALLENGE_P1] --(2)--> [S2_PASS_P1_HANDOFF] --(3)--> [S3_CHALLENGE_P2]
        ^                          |                                                         |
        | (mở vé/nâng hạng mới)    +--> [E1_EVAL_FAIL_COOLDOWN] <----------------------------+
        |                                                                                    |
        |                                                                                   (4)
        |                                                                                    v
[S7_AFTER_PAYOUT_ALLOCATOR] <--(7)-- [S6_PAYOUT_AUDIT_AND_HARVEST] <--(6)-- [S5_FUNDED_ACTIVE] <--(5)-- [S4_PASS_P2_TO_FUNDED_LOCK]
        |                                                                        ^      |
        +-----------------------------(chu kỳ rút tiếp theo)---------------------+      +--> [E2_FUNDED_DD_FREEZE]
                                                                                        +--> [E3_FUNDED_BREACH_POSTMORTEM] -> [CLOSED_ARCHIVED]
```

| Trạng thái | Vai trò ngắn gọn | Preset bắt buộc | Phẳng lệnh (`0` vị thế) |
| --- | --- | --- | :---: |
| `S0_PRE_CHALLENGE` | Chưa thi — kiểm tra vốn đệm, chốt `E1..E6`, chờ mở P1 | `NONE` | Không bắt buộc |
| `S1_CHALLENGE_P1` | Thi Vòng 1 (mục tiêu `+10%` FTMO / `+8%` The5ers Classic) | `EVAL_P1_SPRINT_4_5X` | Bắt buộc khi thoát |
| `S2_PASS_P1_HANDOFF` | Đậu P1 — chốt log P1, đủ điều kiện mở vé #2 (`Gated Stagger`) | `NONE` | Bắt buộc |
| `S3_CHALLENGE_P2` | Thi Vòng 2 (mục tiêu `+5%`, giữ Best-Day & Daily DD) | `EVAL_P2_SPRINT_3_5X` | Bắt buộc |
| `S4_PASS_P2_TO_FUNDED_LOCK` | Đậu P2 — **Cổng 2 khóa bắt buộc** trước khi lên Funded | `FUNDED_1X` | Bắt buộc |
| `S5_FUNDED_ACTIVE` | Cầm Funded (`1.0x` Safe, theo dõi `OPS-4` & inactivity) | `FUNDED_1X` | Bắt buộc |
| `S6_PAYOUT_AUDIT_AND_HARVEST` | Đủ ngày & lãi -> đóng gói `OPS-5` SHA-256 -> rút tiền | `FUNDED_1X` | Bắt buộc |
| `S7_AFTER_PAYOUT_ALLOCATOR` | Tiền đã về + hoàn phí P1 -> chia 3 giỏ -> `S5` hoặc `S0` | `NONE` | Bắt buộc |
| `E1_EVAL_FAIL_COOLDOWN` | Rớt Eval — làm nguội (`>= 2` lần/30 ngày phải ký `OPS-6`) | `NONE` | Không bắt buộc |
| `E2_FUNDED_DD_FREEZE` | Đóng băng Funded (DD `>= 3.5%` Vàng hoặc `>= 6.0%` / `OPS-4` Đỏ) | `NONE` | Bắt buộc khi mở `S5` |
| `E3_FUNDED_BREACH_POSTMORTEM` | Vi phạm cứng Funded — khóa toàn đội tới khi ký `OPS-6` | `NONE` | Trạng thái sự cố |
| `CLOSED_ARCHIVED` | Đã đóng và lưu trữ vĩnh viễn (không chuyển tiếp được) | `NONE` | Kết thúc |

- **Gated Stagger (Mặc định):** Không mở song song 2 vé P1 từ đầu; chỉ mở vé #2 (hoặc nâng `25K`/`50K`) khi vé #1 đã đậu P1 (`S2_PASS_P1_HANDOFF` trở lên) và `E1..E6` đều xanh.
- **FTMO Scaling Plan (`+25%` mỗi `4` tháng):** Tài khoản FTMO Funded (`S5..S7`) đủ `>= 120` ngày, tổng lãi ròng `>= 10%`, `>= 2` lần rút, đang có lãi và `OPS-4 != RED` sẽ đạt điều kiện tăng `+25%` vốn gốc (tối đa `2,000,000 USD`) và nâng chia lãi lên `90%`.

## 2. Checklist Thao Tác Tay Từng Pha

### Trước `S0 -> S1` (Mở vé P1 — chạy `OPS-2` trước khi bật EA)
1. Kiểm tra mã hợp đồng còn mở ở VN trong `tooling/ai-engines/configs/ssot/firms_catalog.json` (`ftmo_swing_50k/100k/200k` không mở tại VN và bị chặn tự động).
2. Chạy `fleet_admission_and_edge_cases.py` xác nhận `allowed = true`.
3. Cấp **1 thư mục MT5 Portable riêng** trên ổ `C:` (`C:\Naqex\mt5\<ACCOUNT_ID>`, cấm ổ `E:`) và **1 dải `MagicNumber` riêng** không trùng tài khoản nào.
4. Chạy **`OPS-2`** (`account_phase_preflight.py`) khóa đúng login P1 (`<DEMO_ID>`), đòn bẩy, đủ 28 mã MarketWatch và preset Eval P1 Sprint `4.5x` (Taper `>= 8.5%`).
5. Đối chiếu 64 ký tự `preset_sha256 == expected_preset_sha256`, ghi chuyển pha `S0 -> S1` rồi mới bật EA.

### Pha `S1 -> S2 -> S3` (Đậu P1 -> Sang P2)
1. Đạt mục tiêu P1 và đủ ngày giao dịch (`4` ngày FTMO / `3` ngày The5ers) -> đưa về **phẳng lệnh (`open_positions == 0`)**, sao lưu `naqex_exec_audit.csv` + Statement, ghi `S1 -> S2` (mở quyền xét vé #2 `Gated Stagger`).
2. Nhận login P2 -> chạy lại **`OPS-2`** cho P2, đổi `.set` sang **Eval P2 Sprint `3.5x`** (`+5%`, bảo vệ Best-Day & Daily DD), khớp `preset_sha256`, ghi `S2 -> S3`.

### CỔNG 2 KHÓA BẮT BUỘC `S4 -> S5` (Chống gắn nhầm `.set` Eval lên Funded)
Chốt chặn sinh tử — hệ thống tự từ chối nếu thiếu bất kỳ điều kiện nào trong 5 khóa:
1. **Phẳng lệnh tuyệt đối:** `open_positions == 0` (số nguyên `0`, cấm `None`/boolean/số âm).
2. **Đạt `OPS-2` pha `FUNDED`:** `account_phase_preflight.py` với `account_phase = "FUNDED"` và login Funded trả `passed = true`, `can_launch = true`.
3. **Đúng preset Funded:** `preset_mode == "FUNDED_1X"`; tên file `.set` **không được chứa** `EVAL`, `P1`, `P2`, `PHASE1`, `PHASE2`, `SPRINT`, `CHALLENGE`, `VERIFY`.
4. **Đúng tham số Safe `1.0x`:** `InpBasePhaseMult = 1.0`, `InpProfitLockMult = 1.0`, `InpAmberDdPct = 3.5`, `InpRedDdPct = 6.0`, `InpKillDailyDdPct = 2.5`, `InpKillStaticDdPct = 8.0`, `InpTargetProfitPct = 0.0`.
5. **Khớp dấu vân tay SHA-256:** `preset_sha256 == expected_preset_sha256` (64-hex).

> Hai đường quay lại Funded (`S7 -> S5` và `E2 -> S5`) cũng phải vượt qua lại đủ 5 khóa này; riêng `E2 -> S5` chặn nếu `OPS-4 == RED`.

### Pha `S5 -> S6` (Đóng gói `OPS-5` SHA-256 trước khi rút tiền)
1. Theo dõi hàng ngày đèn `OPS-4` (`daily_live_ops_pipeline.py`: Xanh `1.0x` / Vàng `0.5x` / Đỏ `0.0x`) và inactivity (`21/27/30` ngày).
2. Đủ chu kỳ (`>= 14` ngày FTMO), lãi `>=` ngưỡng rút (`50 USD` FTMO / `150 USD` The5ers) và `OPS-4 != RED` -> đóng toàn bộ lệnh về `open_positions == 0`.
3. Chạy **`OPS-5`** (`payout_audit_packager.py package` rồi `verify`) để tạo gói hộp trắng SHA-256 (`ops5_audit_bundle_sha256`, xác nhận 0 lưới/martingale, 0 lệnh thiếu SL, 0 vi phạm tin đỏ, 0 lệnh mồ côi).
4. Chỉ khi `certified = true`, ghi `S5 -> S6` kèm `ops5_audit_bundle_sha256` rồi thực hiện rút tiền trên cổng tài khoản.

### Pha `S6 -> S7` (Tiền về ví -> Phân bổ 3 giỏ & Hoàn phí P1)
1. Chỉ ghi `S6 -> S7` khi tiền đã **về ví/ngân hàng** (`settled_date`), điền đủ `payout_gross_usd`, phí rút/FX và `fee_refund_usd` (FTMO hoàn `100%` tiền mặt lần rút đầu; The5ers hoàn `70%` tiền mặt + `30%` Hub Credit không rút được).
2. Chính sách `PARETO_3_BUCKET_DEFAULT` chia tổng tiền mặt thực nhận thành **3 giỏ**:
   - **30% House Money:** thu hồi vốn gốc ban đầu, thuế và phí VPS.
   - **30% Nâng cấp / Thêm vé (`S0`):** mua vé `25K`/`50K` hoặc vé mới (trần dự phòng `5` vé tham chiếu; phần vượt trần tự đổ sang Own-Book).
   - **40% Own-Book:** tích lũy tài khoản vốn tự có độc lập.
3. Chốt xong `S7`: quay lại `S5` cho vòng mới (`S7 -> S5`) hoặc về `S0` (`S7 -> S0`) khi tái cơ cấu suất.

## 3. Bảng Xử Lý Sự Cố `E1..E6` (Fail-Closed)

| Mã chốt | Ngưỡng kích hoạt | Hệ quả hệ thống | Thao tác xử lý & mở khóa |
| --- | --- | --- | --- |
| `E1_EVAL_FAIL_COOLDOWN` | `1` lần rớt/30 ngày -> Cảnh báo; **`>= 2` lần/30 ngày** -> **CHẶN** | Khóa mở mọi vé mới (`S0 -> S1`) chống tâm lý gỡ gạc | Dừng mua vé. Chạy **`OPS-6`** (`live_parity_forensics.py`), ký biên bản (`signed_utc >=` lần rớt cuối, 64-hex `report_sha256`, `approved_to_resume = true`; nếu `BOT_BUG` bắt buộc `fix_verified = true`). |
| `E2_FUNDED_DD_FREEZE` | Bất kỳ Funded (`S5/S6/E2`) có DD `>= 3.5%` / `OPS-4 AMBER` (`0.5x`) hoặc DD `>= 6.0%` / `OPS-4 RED` / trạng thái `E2` (`0.0x`) | **Đóng băng mở Challenge mới trên toàn đội** | Giữ đóng băng mở vé. Ở mức Đỏ: phẳng lệnh, chuyển `E2_FUNDED_DD_FREEZE`, điều tra theo `OPS-4`/`OPS-6`. Chỉ mở `E2 -> S5` khi `OPS-4 != RED` và đạt lại Cổng 2 khóa `FUNDED_1X`. |
| `E3_FUNDED_BREACH_POSTMORTEM` | Có tài khoản Funded vi phạm cứng (`E3`), kể cả đã `CLOSED_ARCHIVED` | **Khóa tuyển dụng toàn đội** | Chạy **`OPS-6`**, ký biên bản phân loại đúng 1 trong 3 nhóm `BOT_BUG | SLIPPAGE | VARIANCE` có `report_sha256` (`BOT_BUG` buộc `fix_verified = true`). Không xóa lịch sử vi phạm. |
| `E4_CAP_OR_VPS_OVERFLOW` | Vốn Funded gốc FTMO `> 400,000 USD`; 1 vé FTMO `> 200,000 USD`; vượt slot hãng; hợp đồng cấm VN; hoặc `naqex-node1` vượt CPU `> 75%`, RAM trống `< 2.0 GB`, ổ `C: < 20 GB`, `> 6` MT5 | Chặn mở thêm vé / thêm terminal lên VPS | Hạ cỡ vé hoặc đa dạng sang hãng khác trong trần vốn. Với `naqex-node1`: tắt terminal đã đóng, dọn ổ `C:` và đo lại thông số node trước khi thêm mới. |
| `E5_CROSS_ACCOUNT_OPPOSITE_HEDGE` | Đối hướng cùng hãng trên cùng gốc mã (`US100` vs `US100.cash` trong `3600s`); trùng `MagicNumber`/dải magic; trùng thư mục Portable; hoặc ổ `E:` | Chặn để tránh phạm luật đối lệnh cùng hãng và đè log | Cấp dải `MagicNumber` tách biệt (cách nhau `100` số), tách riêng thư mục MT5 trên ổ `C:`, đồng bộ chiến lược trong cùng 1 hãng (khác hãng được phép độc lập). |
| `E6_INACTIVITY_OR_FEED_STALE_LOCK` | Nghỉ `21` ngày (Cảnh báo) / `27` ngày (Khẩn) / **`>= 30` ngày (Khóa)**; heartbeat `> 180s` hoặc `< flag_write_utc_ts` hoặc thiếu `open_positions`; NTP `>= 1000 ms`; `PRESET_SHA256_DRIFT` | Chặn vận hành/mở vé do dữ liệu cũ, sai giờ hoặc lệch `.set` | Sắp xếp lệnh hợp lệ trước mốc `30` ngày; kiểm tra kết nối MT5 và đồng bộ Windows NTP trên `naqex-node1` (`< 100 ms`); nếu lệch SHA-256 thì dừng EA, nạp lại `.set` chuẩn và chạy `OPS-2`. |

## 4. Dùng `fleet_ledger.json` Với CLI, `morning_briefing.py` & Web Cockpit

### 4.1. Lệnh CLI chuẩn (từ thư mục gốc workspace)
Sổ mẫu chuẩn: `.runtime/offensive4/fleet/sample_fleet_ledger.json` (bản vận hành thật lưu cục bộ ngoài Git, không đẩy lên kho công khai).

```powershell
# 1. Xác thực schema, khóa an toàn và chuỗi băm SHA-256 sổ cái
.runtime/quant-audit-v24/Scripts/python.exe tooling/ai-engines/quant_factory/wave4/prop_lifecycle_orchestrator.py --validate-ledger .runtime/offensive4/fleet/sample_fleet_ledger.json

# 2. Xem tóm tắt toàn đội (USD/VND), 3 giỏ tiền và next_actions
.runtime/quant-audit-v24/Scripts/python.exe tooling/ai-engines/quant_factory/wave4/prop_lifecycle_orchestrator.py --status --ledger .runtime/offensive4/fleet/sample_fleet_ledger.json

# 3. Kiểm tra 6 chốt chặn E1..E6 + FTMO Scaling trước khi mở vé mới
.runtime/quant-audit-v24/Scripts/python.exe tooling/ai-engines/quant_factory/wave4/fleet_admission_and_edge_cases.py --ledger .runtime/offensive4/fleet/sample_fleet_ledger.json --proposed-contract ftmo_standard_25k --proposed-account-id <ACCOUNT_ID>

# 4. Tiền kiểm OPS-2 và xác thực gói rút tiền OPS-5
.runtime/quant-audit-v24/Scripts/python.exe tooling/ai-engines/quant_factory/live_ops/account_phase_preflight.py --config-json <PREFLIGHT_JSON> --set-file <SET_FILE>
.runtime/quant-audit-v24/Scripts/python.exe tooling/ai-engines/quant_factory/live_ops/payout_audit_packager.py verify --bundle-dir <OPS5_BUNDLE_DIR>
```

### 4.2. Phối hợp `morning_briefing.py` (07:30 ICT hàng ngày)
```powershell
.runtime/quant-audit-v24/Scripts/python.exe tooling/automation/morning_briefing.py --offline
```
Bỏ `--offline` khi `naqex-node1` trực tuyến qua `<LAN_IP>` / `<TAILSCALE_IP>` để đọc thêm trạng thái node. Đối chiếu song song `morning_briefing.py` (6 Mốc Chiến Lược, Radar Tin Đỏ 48h, Daily Ops, `naqex-node1`) với `prop_lifecycle_orchestrator.py --status`: nếu có `CRITICAL_ATTENTION`, tin đỏ Tier-1 trong 48h, hoặc node `DEGRADED/OFFLINE` -> tạm hoãn mở vé mới và chuyển pha.

### 4.3. Dùng Màn Hình Web Cockpit `?view=prop-fleet`
Mở trong Naqex Trader tại `/?workspace=<workspace>&view=prop-fleet&area=live&section=prop-fleet` (menu trái **Live -> Prop Fleet**).
- **Khóa đọc cứng:** Hiển thị `execution_capability: false` (`order_send_capable: false`), chạy 100% phía trình duyệt, **0 gọi `/api/*`**, không mở SSE/WebSocket.
- **Chu trình Import -> Soát nháp -> Export -> Xác thực Python:**
  1. Bấm **Import JSON** nạp `fleet_ledger.json` (tự chặn fail-closed nếu `order_send_capable != false`, `holdout_rows_analysed != 0`, đứt chuỗi `seq`/`prev_event_sha256`, hoặc `S5` sai `FUNDED_1X`; giữ nguyên dữ liệu cũ nếu lỗi).
  2. Xem dải KPI (Quỹ dự phòng, Vốn Funded gốc so với trần `400,000 USD`, đèn rủi ro), bảng 8 trạng thái `S0..S7`, chốt `E1..E6`, và bảng bậc vốn Pareto (`10..500` triệu VND).
  3. Ghi nháp chuyển pha qua hộp thoại (chặn `S4 -> S5` nếu chọn `.set` Eval, thiếu `OPS-2`, hoặc `open_positions != 0`); bản nháp lưu cục bộ tại `localStorage` (`naqex.prop-fleet.draft.v1:<workspace>`).
  4. Bấm **Export JSON** tải `fleet_ledger.json`, rồi **luôn chạy lại** `prop_lifecycle_orchestrator.py --validate-ledger` trên máy (Python CLI là thẩm quyền SHA-256 chuẩn cuối cùng do JS và Python in số thực `10000` vs `10000.0` khác nhau).

## 5. Checklist Đầu Ngày Nhanh (< 2 Phút)
1. Chạy `morning_briefing.py` -> kiểm tra tin đỏ 48h và `naqex-node1` (CPU `<= 75%`, RAM `>= 2.0 GB`, NTP `< 1000 ms`).
2. Chạy `prop_lifecycle_orchestrator.py --status` -> soát `next_actions`, inactivity `< 21` ngày và đèn `OPS-4` của các tài khoản `S5`.
3. Nạp `fleet_ledger.json` vào `?view=prop-fleet` khi cần kiểm tra nhanh 3 giỏ tiền và tiến độ Scaling `+25%/4m`.
4. Trước khi mở vé / lên Funded: chạy `fleet_admission_and_edge_cases.py` + `OPS-2`, khớp đủ 64 ký tự `preset_sha256`.
5. Trước khi rút tiền: về `0` vị thế -> `OPS-5` `certified = true` -> chỉ chia 3 giỏ `S7` sau khi tiền đã về tài khoản.
