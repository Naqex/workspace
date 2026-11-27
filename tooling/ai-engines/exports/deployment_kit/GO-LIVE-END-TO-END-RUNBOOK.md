# Naqex Go-Live End-to-End Master Runbook (Day 0 Staging -> Payout -> Multi-Account Scaling)

Sổ tay vận hành trọn vòng đời thực chiến cho hệ thống giao dịch tự động MT5 & Prop Firm (**FTMO Standard / FTMO Swing / The5ers High Stakes**) trên nút giao dịch 24/5 `naqex-node1` (Windows 10 IoT Enterprise LTSC). Tài liệu kết nối trực tiếp toàn bộ chuỗi công cụ chỉ đọc (`OrderSend = 0`) từ kiểm tra tiền thanh toán, kiểm định chiến lược mới, vận hành hằng ngày, đối soát pháp y, cho tới đóng gói hồ sơ kiểm toán bất biến cho từng kỳ rút lợi nhuận.

> **Kỷ Luật An Toàn & OPSEC Lớp 1 (Bắt Buộc — Không Ngoại Lệ):**
> - **Chiến lược `OrderSend = 0` cho toàn bộ công cụ Python/PowerShell:** Mọi script kiểm tra, đối soát, đóng gói hồ sơ đều chạy **chỉ đọc** hoặc chỉ ghi file cờ dừng `naqex_manual_halt.flag`. Tuyệt đối không dùng script Python gửi lệnh trực tiếp qua `MetaTrader5`.
> - **Môi trường Python chuẩn:** Luôn gọi `.\.runtime\quant-audit-v24\Scripts\python.exe` tại thư mục gốc `D:\ANNAM\TradingWorkspace`.
> - **Không rò rỉ dữ liệu thật Lớp 1:** Chỉ sử dụng ký hiệu thay thế (`<LAN_SUBNET>`, `<LAN_IP>`, `<TAILSCALE_IP>`, `<SSH_USER>`, `<HEROKU_DEADMAN_APP>`, `<TELEGRAM_GUARD_BOT>`, `100.64.0.0/10`, `C:\Users\<USER>`). Thông số nội bộ thật chỉ tra cứu trong `private_vault/`.
> - **Cách ly dữ liệu nghiêm ngặt:** Dữ liệu thực địa kéo về đi 1 chiều duy nhất vào `.runtime/live-vault/<account_alias>/`; tuyệt đối không trộn vào tập `Dev 2018-2024` hay tập khóa kín `Holdout 2025+`.
> - **Đơn vị tiền tệ:** Luôn ghi rõ `USD` / `VND`, không dùng ký hiệu tiền tệ trần.

---

## 0. Bản Đồ Toàn Bộ Công Cụ Tái Sử Dụng (Single Source of Truth)

| Giai đoạn / Vai trò | Công cụ chuẩn trong repo | Trạng thái quyền |
| :--- | :--- | :--- |
| Kiểm tra IP sạch, CGNAT & lịch tin đỏ 14 ngày | `tooling/ai-engines/ops_cloud/ftmo_pre_checkout_guard.py` | Chỉ đọc (`OrderSend = 0`) |
| Giám sát SSH 1 lệnh `naqex-node1` (LAN -> Tailscale) | `tooling/ai-engines/ops_cloud/node_ctl.py` | Chỉ đọc (`OrderSend = 0`) |
| Kiểm tra 10/10 cổng sẵn sàng chuyển đổi & DR | `tooling/ai-engines/ops_cloud/node_cutover_dryrun.py` | Chỉ đọc (`OrderSend = 0`) |
| Bản tin nhanh sáng / cuối tuần (<= 35 dòng) | `tooling/ai-engines/ops_cloud/node_weekly_digest.py` | Chỉ đọc (`OrderSend = 0`) |
| Gia cố VPS 24/5, FIM, xoay log, cầu dao `<= 10s`, kéo Live-Vault | `tooling/ai-engines/exports/deployment_kit/vps_kit/hardening_v3/` | `-DryRun` + chỉ đọc / ghi cờ halt |
| Khóa giai đoạn Eval vs Funded, MarketWatch, Inactivity, Best-Day | `tooling/ai-engines/quant_factory/live_ops/account_phase_preflight.py` | Chỉ đọc (`OrderSend = 0`) |
| DST Mỹ/Âu, lịch tin đỏ 8-CCY + EIA, TTL lịch & sức khỏe feed | `tooling/ai-engines/quant_factory/live_ops/feed_dst_news_guard.py` | Chỉ đọc (`OrderSend = 0`) |
| Đường ống kiểm tra hằng ngày (`GREEN / AMBER / RED`) | `tooling/ai-engines/quant_factory/live_ops/daily_live_ops_pipeline.py` | Chỉ đọc (`OrderSend = 0`) |
| Đối chiếu Broker Statement CSV/HTML vs `naqex_exec_audit.csv` | `tooling/ai-engines/quant_factory/daily_statement_reconciler.py` | Chỉ đọc (`OrderSend = 0`) |
| Đối chiếu 1-1 Python vs MT5 & pháp y lệnh `W1..L4` (`OPS-6`) | `tooling/ai-engines/quant_factory/live_ops/live_parity_forensics.py` | Chỉ đọc (`OrderSend = 0`) |
| Đóng gói hồ sơ kiểm toán bất biến kỳ rút tiền (`OPS-5`) | `tooling/ai-engines/quant_factory/live_ops/payout_audit_packager.py` | Chỉ đọc đầu vào + ghi bundle SHA-256 |
| Kiểm toán trôi điều khoản Prop Firm định kỳ | `tooling/ai-engines/quant_factory/prop_terms_auditor.py` | Chỉ đọc (`OrderSend = 0`) |
| Kiểm chứng chữ ký bộ cài `.ex5` / `.set` / CSV | `tooling/ai-engines/exports/verify_deployment_kit.py` | Chỉ đọc (`OrderSend = 0`) |
| Đồng bộ `.ex5` an toàn khi phẳng lệnh `100%` | `tooling/ai-engines/exports/deployment_kit/vps_kit/sync_updated_ex5_when_flat.ps1` | Fail-closed khi `open_positions > 0` |

---

## 1. Day 0 Staging — Chuẩn Bị Hạ Tầng, IP Sạch & Gia Cố Hardening v3

Hoàn thành toàn bộ bước Day 0 trước khi nạp bất kỳ tài khoản Demo hay trả phí nào lên `naqex-node1`.

### Bước 1.1 — Kiểm chứng bộ cài cục bộ trên máy Dev (`~1 phút`)
```powershell
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\exports\verify_deployment_kit.py --require-ex5
```
- Yêu cầu: **`Deployment Kit Verify: PASS`**, `0` lỗi chữ ký SHA-256, đủ `492` dòng lịch tin đỏ chuẩn `naqex_red_news_utc.csv`.

### Bước 1.2 — Kiểm tra Geo-IP, CGNAT & 10/10 cổng hạ tầng `naqex-node1` (`~2 phút`)
```powershell
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\ftmo_pre_checkout_guard.py --live-readonly --days 14
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\node_cutover_dryrun.py --live-readonly --preset FTMO_Std10K_MasterProp7E_P1_Sprint_4x.set
```
- Yêu cầu **ĐẠT CỨNG:**
  1. `non_us_verified == true` và `is_us_ip_blocked == false` (IP dân dụng sạch ngoài Mỹ).
  2. `is_cgnat == false` (không bị kẹt dải `100.64.0.0/10` trên giao diện WAN ngoài Tailscale) và `double_nat_suspected == false`.
  3. `node_cutover_dryrun.py` đạt **`READY_FOR_CUTOVER (10/10)`**: `KeepPrivate=1`, không có `Login=` ghi đè trong `connector.ini`, `AutoAdminLogon=1`, `wu_reboot=false`, `cbs_reboot=false`, `NoAutoUpdate=1`, `D:\NaqexBackup\daily\` mới `<= 2` ngày, ổ `C:` trống `> 20 GB`, `0` dòng `FILL_UNRESOLVED`.

### Bước 1.3 — Kiểm toán Hardening v3 & diễn tập cầu dao `<= 10s` (`~10 phút`)
Chạy chế độ `-DryRun` trước đối với bộ 5 script trong `tooling/ai-engines/exports/deployment_kit/vps_kit/hardening_v3/`:
1. **Tường lửa tối thiểu:** `audit_firewall_minimal.ps1 -DryRun` (xác nhận chỉ mở 4 luồng outbound cần thiết: MT5 TCP 443, NTP UDP 123, `<HEROKU_DEADMAN_APP>` TCP 443, Tailscale UDP 41641).
2. **Toàn vẹn file FIM hằng ngày:** `fim_sha256_daily.ps1 -Mt5Root C:\Naqex\mt5 -ManifestPath C:\Naqex\ops\fim_manifest_sha256.json -DryRun` (khóa SHA-256 cho `.ex5`, `.set`, `naqex_red_news_utc.csv`, `Config\common.ini`).
3. **Xoay vòng log bảo vệ ổ `C:`:** `rotate_mt5_logs.ps1 -Mt5Root C:\Naqex\mt5 -ArchiveRoot D:\NaqexBackup\mt5-logs-archive -DryRun` (không bao giờ đụng ổ `E:`, bảo vệ log ngày hôm nay, giữ trống `C: > 20 GB`).
4. **Cầu dao khẩn cấp có xác nhận ACK `<= 10s`:** `emergency_killswitch_guard.ps1 -Mt5FilesDir C:\Naqex\mt5\MQL5\Files -Action HALT_NEW_ENTRIES -AckTimeoutSec 10 -DryRun`. Khi chạy thật, preset **BẮT BUỘC** bật `InpAllowManualHaltFile=true`; nếu `manual_halt_ack != true` sau `10s`, script trả mã lỗi `2` (`CRITICAL_RED_ESCALATION`) để kích hoạt cứu hộ tay qua MT5 Mobile ngay lập tức.
5. **Diễn tập đủ 5 kịch bản sự cố:** Thực hiện theo `tooling/ai-engines/exports/deployment_kit/vps_kit/hardening_v3/CHAOS-DRILL-PLAYBOOK.md` (rớt cáp quang 15p, mất điện vượt UPS cứu hộ `< 3` phút trước `20:50 UTC`, treo `terminal64.exe`, đầy ổ `C:`, broker đổi spec/suffix).

### Bước 1.4 — Kiểm tra khóa giai đoạn & MarketWatch (`account_phase_preflight.py`)
Trước khi gắn EA hoặc đổi giai đoạn tài khoản, chạy bộ kiểm tra fail-closed:
```powershell
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\quant_factory\live_ops\account_phase_preflight.py `
  --config-json private_vault\ops\preflight_target_account.json `
  --set-file tooling\ai-engines\exports\deployment_kit\presets\FTMO_Std10K_MasterProp7E_P1_Sprint_4x.set
```
- Tự động chặn cứng (`REJECT`, exit `2`) nếu sai `expected_login`, sai `DEMO` vs `REAL`, gắn nhầm `.set` Eval/Sprint lên tài khoản Funded, sai đòn bẩy theo nhóm tài sản (`FX / Indices / Metals / Oil / Crypto`), thiếu symbol trong Market Watch, hoặc lệch hậu tố `.cash`.

---

## 2. Cổng Thăng Hạng 2 Bước Cho Engine Mới & Demo Burn-In (2-Step Promotion Gate)

Không một chiến lược hay phiên bản `.ex5` mới nào được phép chạy tiền thật nếu chưa vượt qua **cả 2 bước cổng cứng** dưới đây:

### Bước 2A — MT5 Strategy Tester Parity `>= 98%` Trên Tập Dev (`2018–2024`)
- Chạy backtest trên MT5 Strategy Tester trong cửa sổ Dev (`2018–2024`, tuyệt đối không chạm `Holdout 2025+`), trích xuất `naqex_exec_audit.csv` và `naqex_decision_blackbox_*.jsonl` (`InpBlackboxEnableInTester=true`).
- Chấm cổng tự động bằng `live_parity_forensics.py` (`evaluate_tester_parity_gate`):
  - **Tỷ lệ khớp lệnh (`trade_match_rate`):** `>= 98%` trong sai số thời gian `<= 1` nến (`bar`).
  - **Lệnh ma (`BOT_BUG_GHOST_TRADE`):** Bắt buộc bằng **`0`**.
  - **Độ lệch khối lượng / Stop Loss (`max_lot_sl_drift`):** `<= 2%` (chặn tuyệt đối lỗi `TICK_VALUE_LOSS` hoặc quy đổi cặp chéo).
  - **Độ lệch hiệu suất gộp (`gross_r_drift`):** `<= 5%`.
- Nếu bất kỳ tiêu chí nào trượt -> **CHẶN CỨNG**, sửa lỗi mã MQL5/Python và chạy lại Tester Parity.

### Bước 2B — Demo / Shadow Burn-In Thực Địa `10–14` Ngày Giao Dịch
1. Đồng bộ phẳng lên tài khoản **FTMO Demo / Free Trial** trên thư mục MT5 portable riêng (đặt `InpDryRunLogOnly=true` trong 1–2 ngày đầu để kiểm tra heartbeat & tin đỏ, sau đó mở Demo fills `1.0x`).
2. Kéo dữ liệu thực địa 1 chiều về `.runtime/live-vault/<demo_alias>/` bằng `hardening_v3/sync_live_vault_readonly.ps1` (không ghi ngược lên `naqex-node1`, không trộn Dev/Holdout).
3. Chạy đối chiếu `live_parity_forensics.py` trên **quote tape M1 Bid/Ask thật của broker** để phân loại 5 trạng thái:
   - `MATCH_CLEAN`: khớp symbol/chiều, lệch giờ `<= 60s`, lệch lot/SL `<= 5%`, ma sát trong ngân sách.
   - `BOT_BUG_GHOST_TRADE` / `BOT_BUG_MISSED_TRADE`: lỗi kỹ thuật ĐỎ -> **SỬA NGAY (`IMMEDIATE_FIX_REQUIRED`)**.
   - `LOT_OR_SL_DRIFT` (`> 5%`): lỗi tính kích cỡ/SL -> **SỬA NGAY**.
   - `EXECUTION_FRICTION_DRIFT`: chuyển sang kiểm toán TCA & Markout (`+1s / +10s / +60s / +5m`).
4. **Ngưỡng tốt nghiệp Burn-In:** Tối thiểu **`10–14` ngày giao dịch** liên tục và **`>= 15–20` lệnh khớp** phân loại `MATCH_CLEAN`, `0` lệnh ma, `0` lệnh sót ngoài guard, `0` `FILL_UNRESOLVED`, `swap = 0.00 USD` (với nhánh intraday `swap=0`), và ma sát thực địa nằm trong ngân sách backtest.
5. **Kỷ luật chống Overfit (`Anti-Overfit Feedback Protocol`):**
   - Lỗi kỹ thuật (`GHOST / MISSED / LOT_DRIFT`) được sửa ngay lập tức.
   - Mọi ý tưởng tinh chỉnh tham số từ nhóm lệnh thua `L1 / L2 / L3` **BỊ KHÓA CỨNG khi `N_live < 30`** (khuyến nghị `>= 50` lệnh). Khi đủ mẫu, `live_parity_forensics.py` chỉ xuất bản nháp `HypothesisCard` gắn nhãn `MUST_VALIDATE_ON_7YR_DEV_BEFORE_CHANGE` — tuyệt đối không tự chỉnh tham số sống trên mẫu nhỏ.

---

## 3. Giai Đoạn Evaluation (P1 & P2) — Quy Tắc Bankroll, Chống Cháy Quỹ & Cài Đặt

### 3.1 — Quy Tắc Bankroll & Phòng Chống Rủi Ro Cháy Vốn (`Sprint Eval 20%–30% Fail Budget`)
Chế độ Sprint Eval (`P1` chấp nhận ngân sách trượt `20%–30%` mỗi vé để tối ưu tốc độ vượt vòng và `EV/Fee`) **chỉ an toàn về toán học khi có quỹ dự phòng nhiều vé liên tiếp**:

- **Quỹ dự phòng bắt buộc: `4–5` vé Challenge liên tiếp** (xác suất mất sạch quỹ dự phòng `< 0.5%`):
  - Với tỷ lệ trượt `25%` mỗi vé: trượt `4` vé liên tiếp = `0.39%` (`< 0.5%`).
  - Với tỷ lệ trượt `30%` mỗi vé: trượt `5` vé liên tiếp = `0.24%` (`< 0.5%`).
- **Quy đổi vốn dự phòng thực tế (theo bảng giá SSOT `ftmo_standard_10k`):**
  - Giá vé chuẩn `98.61 USD` (hoặc `68.70 USD` kỳ ưu đãi) + phí thẻ ngoại tệ `~2.5%`:
  - Quỹ `5` vé `10K` dự phòng: **`355–505 USD`** (khoảng **`9.0–12.8 triệu VND`**).
  - **Không bao giờ dùng tiền sinh hoạt hoặc mua 1 vé cỡ lớn (`50K / 100K`) làm mất đệm `4–5` vé dự phòng!**
- **Quy tắc Hoàn Vốn Bắt Buộc Trước Khi Nhân Quy Mô:**
  - **Thu hồi `100%` toàn bộ vốn phí mua Challenge đã bỏ ra ngay tại kỳ `Payout #1`** (nhờ chia lợi nhuận `80%` + hoàn phí thi `100%` vào lần rút đầu tiên của FTMO) **TRƯỚC KHI** trích tiền lãi mua thêm gói `25K / 50K / 100K`.
  - Mọi đợt mở rộng sau Payout #1 chỉ dùng **tiền lãi đã rút về tài khoản cá nhân**, giữ nguyên đệm `4–5` vé cho cấp tài khoản mới.

### 3.2 — Kích Hoạt Phase 1 (`P1`) & Chuyển Pha Phase 2 (`P2`)
1. **Đồng bộ khi phẳng lệnh:** Luôn tạo thư mục MT5 portable riêng cho từng tài khoản trả phí (không đè lên tài khoản Demo đang chạy), xác nhận bằng `sync_updated_ex5_when_flat.ps1 -RequireManifest -DryRun` rồi mới chạy thật.
2. **Kiểm tra khóa preset trước khi gắn chart:**
   - **Phase 1 (`P1`):** Dùng bộ `.set` riêng của Eval P1 (`FTMO_Std10K_MasterProp7E_P1_Sprint_4x.set` hoặc `P1_Balanced_3x.set` / bản Sprint v1.03 đã kiểm định), xác nhận bật **`InpAllowManualHaltFile=true`**, `InpGuardEnableRedNews=true`, `InpWritePrimaryHeartbeat=true`.
   - **Mở khóa thủ công 2 bước:** Gắn EA ở chế độ khóa mặc định `InpDryRunLogOnly=true` & `InpGuardDryRunLogOnly=true` trong `5–10` phút đầu -> kiểm tra tab **Experts** thấy `[PROPGUARD-OK] Loaded 492 red-news events`, `naqex_heartbeat.json` xanh, `orphan_no_sl == 0` -> đối chiếu đúng **Login tài khoản trả phí** -> mới tự tay đổi cả `2` cờ `DryRun` sang `false`.
3. **Chuyển sang Phase 2 (`P2 Verification` — mục tiêu `+5%`):**
   - Khi đậu P1, nhận tài khoản P2 mới -> **chạy lại `account_phase_preflight.py`** với login P2 mới và nạp preset riêng của P2 (`FTMO_Std10K_MasterProp7E_P2_Verify_2x.set`, rủi ro dịu hơn, tắt vệ tinh S6, bật `InpAllowManualHaltFile=true`).
   - Theo dõi đủ số ngày giao dịch tối thiểu (`>= 4` ngày với FTMO; `>= 3` ngày lãi `>= +0.5%` với The5ers) và giữ **Best-Day Share `< 45%`** để lịch sử giao dịch đều và sạch.

---

## 4. Giai Đoạn Funded Live — Khóa Bảo Toàn Vốn `1.0x`

Nguyên tắc tối thượng của tài khoản Funded: **đổi mục tiêu từ "Tốc độ" sang "Sống sót dài hạn & Lĩnh lương đều"**.

1. **Khóa cứng Eval-vs-Funded (`account_phase_preflight.py`):**
   - **CẤM TUYỆT ĐỐI** chạy `.set` Eval/Sprint (`risk_mult > 1.25x` hoặc `amber_dd_pct > 4.0%`) trên tài khoản Funded.
   - Nạp đúng preset Funded độc lập (`FTMO_Std10K_MasterProp7E_Funded_Safe_1x.set` hoặc `FTMO_Std10K_v103_Funded_1x.set`):
     - Hệ số rủi ro cố định **`1.00x`** (`InpBasePhaseMult=1.00`), không tăng tốc theo kiểu Eval.
     - Phanh mềm chặt: **Amber `3.5%` (`0.65x`) / Red `6.0%` (`0.40x`)**, trần lỗ ngày mềm `2.5%`, trần lỗ tĩnh `7.5%`, tổng rủi ro mở `<= 2.00%–2.25%`.
     - Bật bắt buộc **`InpAllowManualHaltFile=true`** và lọc tin đỏ `±300s` (cấm cứng `±135s` bảo vệ ngưỡng `±120s` của FTMO Standard / The5ers).
2. **Kiểm soát nhịp sống tài khoản Funded:**
   - **Cảnh báo Không hoạt động (`Inactivity Watch < 21/30d`):** Không để tài khoản trống lệnh quá `21` ngày (`AMBER` từ ngày `21`, `RED` từ ngày `27`, giới hạn khóa tài khoản là `30` ngày).
   - **Cảnh báo Tỷ trọng Ngày Lãi Lớn Nhất (`Best-Day Share < 45%`):** Theo dõi hằng ngày trong `account_phase_preflight.py` và `daily_live_ops_pipeline.py`.

---

## 5. First Payout & Đóng Gói Hồ Sơ Kiểm Toán Bất Biến (`OPS-5`)

Trước mỗi lần bấm yêu cầu rút lợi nhuận (đặc biệt **Payout #1** — mốc hoàn vốn phí ban đầu):

### Bước 5.1 — Đóng phẳng tài khoản & xuất Broker Statement
1. Đảm bảo `open_positions == 0`, `pending_orders == 0` (sau giờ cắt `20:50 UTC` hoặc cuối tuần).
2. Kéo dữ liệu thực địa mới nhất về `.runtime/live-vault/<funded_alias>/` qua `hardening_v3/sync_live_vault_readonly.ps1`.
3. Xuất báo cáo giao dịch chuẩn (CSV/HTML) từ MT5 / Client Area vào `.runtime/live-vault/<funded_alias>/statement.csv`.

### Bước 5.2 — Chạy đối chiếu Statement vs Execution Audit (`OrderSend = 0`)
```powershell
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\quant_factory\daily_statement_reconciler.py `
  --audit-csv .runtime\live-vault\funded_10k\naqex_exec_audit.csv `
  --statement .runtime\live-vault\funded_10k\statement.csv `
  --out-json .runtime\live-vault\funded_10k\reconcile_receipt.json
```
- Yêu cầu: `status == "PASS"`, `orphan_audit_count == 0`, `orphan_statement_count == 0`, `unresolved_fill_rows == 0`, `missing_swap_count == 0`, `nonzero_swap_count == 0`.

### Bước 5.3 — Đóng gói & chứng nhận chuỗi băm SHA-256 bất biến (`payout_audit_packager.py`)
```powershell
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\quant_factory\live_ops\payout_audit_packager.py package `
  --output-dir .runtime\live-vault\funded_10k\payout_bundles\cycle_2026_12_p1 `
  --cycle-id cycle_2026_12_p1 `
  --audit-csv .runtime\live-vault\funded_10k\naqex_exec_audit.csv `
  --reconcile-receipt .runtime\live-vault\funded_10k\reconcile_receipt.json `
  --decision-blackbox .runtime\live-vault\funded_10k\blackbox `
  --set-preset tooling\ai-engines\exports\deployment_kit\presets\FTMO_Std10K_MasterProp7E_Funded_Safe_1x.set `
  --ex5-path .runtime\mt5-compiled-ex5\Naqex_Master_Prop7E.ex5 `
  --firm-profile FTMO_STANDARD `
  --account-phase FUNDED
```
- Công cụ tự động chứng nhận **6 tiêu chí White-Box** trực tiếp từ nhật ký khớp lệnh (chặn cứng exit `2` nếu vi phạm bất kỳ tiêu chí nào):
  1. `hard_sl_attached_pct == 100%` (100% lệnh mở có Stop Loss cứng hợp lệ đúng chiều).
  2. `zero_grid_verified == true` (tối đa `<= 1` vị thế mở đồng thời trên cùng mã/magic).
  3. `zero_martingale_verified == true` (không gấp thếp khối lượng `>= 1.8x` sau chuỗi thua).
  4. `zero_hft_tick_scalping == true` (thời gian giữ lệnh tối thiểu đạt chuẩn `>= 60s`).
  5. `red_news_ban_clean == true` (`0` lệnh khớp trong vùng cấm cứng `±120s` tin đỏ).
  6. `reconciliation_orphan_count == 0` (`0` lệnh mồ côi giữa audit CSV và Broker Statement + khớp SHA-256).
- Mặc định bật chế độ **ẩn danh Lớp 1 (`redact_for_layer1=True`)** giúp che toàn bộ số Login, ticket/deal ID, IP và đường dẫn người dùng mà vẫn giữ liên kết nội bộ và SHA-256 nguồn gốc. Chỉ dùng `--no-redact` khi lưu bản gốc nội bộ bên trong `private_vault/`.

### Bước 5.4 — Kiểm chứng độc lập chuỗi băm trước khi lưu trữ lâu dài
```powershell
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\quant_factory\live_ops\payout_audit_packager.py verify `
  --bundle-dir .runtime\live-vault\funded_10k\payout_bundles\cycle_2026_12_p1
```
- Xác nhận `"verified": true`, `"hash_chain_valid": true`, `"certified": true`. Sao lưu thư mục bundle đã niêm phong sang `D:\NaqexBackup\payout-bundles\` (chỉ đọc, không ghi đè).

---

## 6. Multi-Account Scaling & Vệ Sinh IP / Chống Vi Phạm Đa Tài Khoản

Chỉ kích hoạt mở rộng sang **`25K -> 50K -> 100K`** hoặc mở thêm hãng thứ hai (**The5ers High Stakes**) **SAU KHI hoàn vốn phí từ Payout #1** và tuân thủ 5 quy tắc bắt buộc:

1. **Vệ Sinh IP Tập Trung (`1` IP Dân Dụng Sạch Duy Nhất):**
   - Toàn bộ các phiên MT5 đặt trên **1 nút Home-VPS duy nhất `naqex-node1`** dùng đường truyền cáp quang dân dụng sạch ngoài Mỹ, kiểm tra định kỳ qua `ftmo_pre_checkout_guard.py` (không dùng VPN chia sẻ, không dùng VPS thương mại chung IP với người lạ, không chạy qua CGNAT `100.64.0.0/10`).
2. **Cách Ly Hoàn Toàn Thư Mục MT5 Portable & Số Magic:**
   - Mỗi tài khoản chạy một thư mục MT5 portable riêng biệt (`C:\Naqex\mt5_ftmo_funded_10k`, `C:\Naqex\mt5_ftmo_eval_25k`, `C:\Naqex\mt5_the5ers_5k`), mỗi tài khoản có `account_phase_preflight.py` kiểm tra riêng và không dùng chung file `MQL5\Files\`.
3. **Cấm Tuyệt Đối Group-Hedging & Mở Lệnh Ngược Chiều Cùng Hãng:**
   - `account_phase_preflight.py` kiểm tra chéo danh sách tín hiệu/EA đang hoạt động giữa các tài khoản cùng một Prop Firm để chặn cứng mọi tình huống mở `BUY` ở tài khoản A và `SELL` ở tài khoản B trên cùng symbol trong cửa sổ xung đột.
4. **Giới Hạn Vốn Tổng & Đệm Rủi Ro Đa Tài Khoản:**
   - Không nhân đôi quy mô tài khoản trong cùng tháng nếu chưa vượt qua `1` kỳ rút lương xanh ở cấp hiện tại.
   - Tách rõ bộ `.set` **Eval** vs **Funded** cho từng tài khoản; mọi tài khoản đều bật `InpAllowManualHaltFile=true` và gắn watchdog kiểm tra `naqex_heartbeat.json`.
5. **Thang Điểm Sẵn Sàng Vận Hành (Operational Readiness Scorecard):**
   - 🔴 **Xấu (Chưa được chạy thật):** Chưa đạt Tester Parity `>= 98%`, chưa đủ `10–14` ngày Demo Burn-In, thiếu đệm `4–5` vé, bật sai `.set` Eval lên Funded, `InpAllowManualHaltFile=false`, hoặc `node_cutover_dryrun` chưa đủ `10/10`.
   - 🟡 **Đủ dùng (Chỉ chạy Demo / Shadow):** Đã xong Day 0, `node_cutover_dryrun` đạt `10/10`, đang tích lũy `15–20` lệnh `MATCH_CLEAN` và kiểm toán ma sát TCA hằng tuần.
   - 🟢 **Tốt (Chuẩn Challenge 10K & Funded Đầu Tiên):** Vượt đủ 2 bước Promotion Gate, đủ quỹ dự phòng `4–5` vé (`< 0.5%` ruin), chạy kỷ luật 3 chu kỳ bảo trì, hồ sơ `payout_audit_packager.py` đạt `CERTIFIED` với `0` vi phạm.
   - 🏆 **Top 1% thực tế (Chuẩn Funded Đa Tài Khoản `25K–100K`):** Đã hoàn `100%` vốn phí từ Payout #1, đa dạng hóa động cơ không tương quan, `0` lỗi parity/orphan liên tục nhiều chu kỳ, diễn tập 5 kịch bản Chaos Drill đạt SLA hằng quý, hồ sơ chuỗi băm SHA-256 đầy đủ mọi kỳ rút tiền.

---

## 7. Lịch Bảo Trì Sống 3 Chu Kỳ (3-Cycle Living Maintenance Calendar)

### Chu Kỳ 1 — Hằng Ngày (`2 phút` mỗi sáng trước phiên London / sau đóng phiên Mỹ)
Chạy bộ lệnh chỉ đọc từ máy Dev:
```powershell
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\quant_factory\live_ops\daily_live_ops_pipeline.py --help
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\node_weekly_digest.py --live-readonly
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\node_ctl.py status
```
- **Checklist 2 phút:**
  1. Trạng thái tổng hợp `GREEN / AMBER / RED` (nếu `RED` -> dừng điều tra ngay, không bỏ qua).
  2. Nhịp tim `naqex_heartbeat.json` mới **`< 120s`** (cảnh báo `<TELEGRAM_GUARD_BOT>` từ `<HEROKU_DEADMAN_APP>` không báo stale).
  3. `terminal_connected == true`, `orphan_no_sl == 0`, `kill_switch == false`, `propguard_warn_count == 0`.
  4. Kiểm tra đệm Daily DD / Static DD, lịch tin đỏ hôm nay, và cảnh báo Inactivity `< 21d` / Best-Day `< 45%`.

### Chu Kỳ 2 — Hằng Tuần (`10 phút` sáng Thứ Bảy khi thị trường đóng cửa & `open_positions == 0`)
1. **Kéo dữ liệu 1 chiều về Live-Vault:**
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\tooling\ai-engines\exports\deployment_kit\vps_kit\hardening_v3\sync_live_vault_readonly.ps1 -DryRun
   ```
   *(Kiểm tra danh sách file rồi bỏ `-DryRun` để kéo có xác minh SHA-256.)*
2. **Chạy đối soát Statement + `OPS-6` Parity & Pháp Y `W1..L4`:**
   - Chạy `daily_statement_reconciler.py` (xác nhận `0` orphan, `swap = 0.00 USD`, Markout không xấu bất thường).
   - Chạy `live_parity_forensics.py` (kiểm tra 5 lớp parity `MATCH_CLEAN / GHOST / MISSED / LOT_SL_DRIFT / FRICTION_DRIFT` và phân bổ `W1/W2/L1/L2/L3/L4`; khóa cứng chỉnh tham số nếu `N_live < 30`).
3. **Vệ sinh ổ cứng, sao lưu, toàn vẹn FIM & lịch tin đỏ:**
   - Kiểm tra `node_ctl.py maint` và chạy `hardening_v3/rotate_mt5_logs.ps1` giữ ổ **`C:` trống `> 20 GB`** (chỉ lưu nén sang `D:\NaqexBackup\mt5-logs-archive\`, tuyệt đối không chạm ổ `E:`).
   - Kiểm tra `D:\NaqexBackup\daily\` mới `<= 2` ngày và `hardening_v3/fim_sha256_daily.ps1` khớp 100% SHA-256.
   - Kiểm tra hạn lịch tin đỏ (`feed_dst_news_guard.py` `check_calendar_ttl`): **làm mới ngay khi TTL tiến gần `<= 14` ngày (`AMBER`)**, không bao giờ để chạm `<= 3` ngày (`RED` fail-closed).

### Chu Kỳ 3 — Hằng Tháng & `2 lần/năm` Chuyển Đổi Giờ Mùa Hè DST (Tháng 3 & Tháng 10/11)
1. **Kiểm toán 2 cửa sổ lệch giờ DST Mỹ vs Âu (Tháng 3 và cuối Tháng 10 / đầu Tháng 11):**
   - Trong `2–3` tuần tháng 3 và `1` tuần cuối tháng 10 / đầu tháng 11, Mỹ (`America/New_York`, mốc `17:00 NY` = `00:00` máy chủ `NY+7` cho FTMO/The5ers) và châu Âu (`Europe/Prague` / `Europe/London` / `Europe/Athens`) chuyển DST lệch nhau `1` giờ.
   - Chạy kiểm tra qua `feed_dst_news_guard.py` (`resolve_dst_snapshot`, `get_dst_divergence_windows`, `resolve_firm_daily_reset_utc`, `resolve_strategy_session_utc`) để đảm bảo giờ reset ngày, giờ cắt `swap=0` (`20:50 UTC`), và cửa sổ phiên chiến lược không bị lệch `1` giờ.
2. **Kiểm toán trôi điều khoản Prop Firm (`prop_terms_auditor.py`):**
   ```powershell
   .\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\quant_factory\prop_terms_auditor.py `
     --file private_vault\ops\ftmo_terms_snapshot.md `
     --firm ftmo_standard
   ```
   - Lưu bản chụp trang điều khoản/FAQ công khai vào `private_vault/ops/` mỗi tháng và quét phát hiện thay đổi luật (`HALT_RULE_DRIFT_REVIEW` nếu hãng thay đổi quy định giữ qua đêm, tin đỏ, consistency cap, hay trailing DD).
3. **Đánh giá suy hao Alpha & Diễn tập Chaos Drill (Hằng tháng / Hằng quý):**
   - So sánh hiệu suất thực địa tích lũy (Expectancy, PF, Winrate, RR, trượt giá thực) với đường chuẩn Dev + chạy kiểm tra `ftmo_pre_checkout_guard.py --live-readonly` xác nhận IP không bị chuyển sang CGNAT.
   - Diễn tập lại cầu dao `emergency_killswitch_guard.ps1` (`manual_halt_ack == true` trong `<= 10s`) trên môi trường Demo và diễn tập cứu hộ MT5 Mobile `< 3` phút theo `CHAOS-DRILL-PLAYBOOK.md`.

---

## 8. Bảng Phản Ứng Nhanh Khi Có Cảnh Báo Đỏ (RED Escalation Matrix)

| Tình huống báo ĐỎ | Hành động tức thời (`< 3 phút`) | Điều kiện mở lại |
| :--- | :--- | :--- |
| `heartbeat > 120s` hoặc rớt mạng/mất điện | Mở **MT5 Mobile** bằng 4G/5G kiểm tra SL cứng trên server broker; nếu gần `20:50 UTC` hoặc tin đỏ mà máy chưa hồi -> đóng tay sạch lệnh | `node_ctl.py status` xanh, `positions_state=CONFIRMED`, `orphan_no_sl=0` |
| `orphan_no_sl > 0` hoặc `BOT_BUG_GHOST_TRADE` | Chạy `emergency_killswitch_guard.ps1 -Action FLATTEN_ALL -AckTimeoutSec 10`; nếu quá `10s` không ACK -> tắt nút **Algo Trading** + đóng tay qua MT5 Mobile | Tìm rõ nguyên nhân gốc trong `.runtime/live-vault/`, sửa lỗi + vượt lại Tester Parity `>= 98%` |
| `RED` Calendar TTL (`<= 3d`) hoặc lỗi tin đỏ | Dừng vào lệnh mới (`HALT_NEW_ENTRIES`), cập nhật lịch tin đỏ đã xác minh T1, đồng bộ khi phẳng lệnh | `check_calendar_ttl == GREEN (> 14d)` & `fim_sha256_daily.ps1` khớp 100% |
| `C:` trống `<= 20 GB` | Chạy `rotate_mt5_logs.ps1 -DryRun` rồi chạy thật chuyển log `> 7` ngày sang `D:\NaqexBackup\mt5-logs-archive\` | `disk_c_free_gb > 20 GB` và `pagefile.sys` chỉ nằm trên `C:` |
| `HALT_RULE_DRIFT_REVIEW` từ `prop_terms_auditor.py` | Tạm ngưng mua vé mới và đặt `HALT_NEW_ENTRIES` trên tài khoản bị ảnh hưởng tới khi cập nhật bộ luật & `.set` tương thích | Đã cập nhật SSOT `firms_catalog.json`, `.set`, và `account_phase_preflight.py` đạt `PASS` |
