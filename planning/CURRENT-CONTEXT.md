# Current context — Naqex Workspace

`27/11/2026 13:45 ICT` · `WORK: TOTAL-OFFENSIVE-2-V2.5 | 5/5 WAVE-1 PRS MERGED | 0-VND | LIVE-NODE1: READ-ONLY | HOLDOUT 2025+ SEALED`

`GOAL-NOW: HOÀN TẤT CHIẾN DỊCH TOTAL OFFENSIVE #2 V2.5 TRÊN NHÁNH codex/total-offensive-2 (5 MẶT TRẬN: PHÒNG THỦ V1.03, TẤN CÔNG ALPHA #2 & V3, TỰ CHỮA LÀNH 24/7, NÂNG CẤP QUANT_CORE/X13/WORKFLOWS, RADAR NGHIÊN CỨU & CẦU SẠCH STRATEGY-INTEL) | NTP ĐÃ ĐỒNG BỘ (< 25–28 MS, strict_ntp_passed=true) | CHUẨN BỊ 6 MỐC SỰ KIỆN 30/11 -> 14/12 (0 VND)`

## 0. Nền Đã Chốt (`5/5` PR Wave-1 Merged) & Nâng Cấp Total Offensive #2 v2.5

- **`5/5` PR Cải Tổ Agent-First SSOT Đã Merge Xanh (`27/11/2026`):**
  - `TradingWorkspace` PR `#115` (`d1f9dfe`), `projects/trader` PR `#44` (`3f264c31`), `projects/quant-trading` PR `#6` (`36dc730`), `projects/vi-dubber` PR `#6` (`bb89a65`, lấy qua worktree cô lập `.worktrees/vi-dubber-offensive2` giữ nguyên `5/5` WIP cục bộ), `private_vault` PR `#1` (`54eab25`).
  - **Wave 0 Bootstrap (`codex/total-offensive-2`):** tái dựng sạch `frozen_9e_tapes_v2` (`max_day = 2024-12-31 < 2025-01-01`, `holdout_rows_analysed = 0`, `PORT_7E 10K 1x = 5.408,09 USD`, lệch `0,00 USD`), `system_doctor --mode fast` đạt **`10/10 PASS`**, khóa hợp đồng `.tmp/offensive2_h_contract.json`, đo NTP đồng bộ đạt **`strict_ntp_passed=true`** (`<DEV_PC> -24,2 ms` tức `< 25 ms`; `<X13_WORKER> +27,7 ms`, `AC=1`, `0` tệp cấm).
- **5 Mặt Trận Total Offensive #2 v2.5 (`0 VND`, `OrderSend = 0`, `MT5_PROCS = 0`, `Holdout 2025+ SEALED`):**
  - **Mặt trận 1 — Phòng Thủ (`D1–D4`):** đóng 6 `assert` dưới `python -O` + tái dựng đường DD equity M1 nội nhật (`< 5%`); quét Pareto Flash-Crash Khiên `A/B/C` & ứng viên `Naqex_Master_Prop7E_v103.mq5` (`InpDryRunLogOnly=true`); bật `InpGuardEnableRedNews=true` trên 2 preset `C10` P1/P2 (`0` active blocking drifts); khóa script staging chỉ chạy khi phẳng lệnh `stage_total_offensive_2_when_flat.ps1` & kiểm toán `naqex-node1`.
  - **Mặt trận 2 — Tấn Công (`O1–O4`):** Capital Optimizer V3 (`flat_at_reset_verified`, sốc floating rollover `00:00`, quyền chọn hóa đơn BF `14` ngày, X13 shard); động cơ đơn nhất Backtest/Shadow `projects/quant-trading` + vá `5` lỗi `crypto_shadow_runner.py` + nghiên cứu `7E + Alpha #2`; lộ trình 3 nhánh + đăng ký trước mã hóa `preregister_holdout_v2.py` (`>= 2026-12-01`); chặn runtime `demucs/diffq` trong `vi-dubber` & xử lý false positive Gitleaks `private_vault`.
  - **Mặt trận 3 — Tự Chữa Lành 24/7 (`H1–H4`):** thêm skill `poteto-autonomous-verify`, gói `tooling/automation/` (`event_queue`, `ratchet_engine` cầu dao cứng ở lần thử #4, `self_healing_ci`, `watchdog_15m`, `nightly_quant_ops`, `product_qa_sweep`, `morning_briefing`), mở cổng `ARCH-08..10`, gắn `naqex_cli.py auto` (`9` lệnh con), API Cockpit chỉ-đọc `/api/automation/{status,events,features}` & `2` mẫu sidecar.
  - **Mặt trận 4 — Nâng Cấp Lõi (`U1–U4`):** chuẩn hóa `41/41` tệp `quant_core/` (`0` ruff/format/ty/CRLF); vá đo CPU tuần tự `compute_router.py`/`x13_probe.py` + `PARALLEL_20_80_MODE_A`/`PARALLEL_60_40` + đồng bộ Dev-only `tar.gz` (loại `holdout_guard.py`); bổ sung `tooling/workflows/` (`audit_19_gates.py`, `pareto_strategy_sweep.py`), cập nhật `docs/REPO-MAP.md` & `planning/research/README.md` (`9` báo cáo mới).
  - **Mặt trận 5 — Radar & Cầu Sạch (`R1–R5`):** `auto_research_radar.py`, `prop_terms_radar.py`, `frontier_alpha_candidates.json`, `knowledge/topics/frontier-agent-harness-2026.md`, và cầu đọc 1 chiều `strategy_intel_bridge.py` từ `D:/ANNAM/strategy-intel` (`0` ghi ngược, `4/4` cổng sạch, gắn nhãn `untrusted_external_data: true`).
- **Điểm Neo Dev `C10_NEWS_ON` (`DEV_BACKTEST_2018_2024`, `holdout_rows_analysed = 0`, KHÔNG phải Holdout/tiền thật):**
  - [C10-POST-SSOT-LOOKAHEAD-RECONCILIATION-20261127.md](research/C10-POST-SSOT-LOOKAHEAD-RECONCILIATION-20261127.md): `Core7 100K 1x` (`WR 48,61%` · `RR 1,272x` · `EV +0,0486R` · `PF 1,203` · `Max DD 8,62%` · `Calmar 0,861` · `Sharpe 1,234` · hòa vốn trượt giá `2,31x`); `FTMO Standard 10K` (`1` vé BF `70,42 USD` ~ `1,81 tr VND`, `1,00x`): `24T` `61,89% Đậu / 5,60% Rớt / 32,51% Chờ` (`100%`), `EV/Phí +8,25x`, tháng Funded đói payout `66,45%`.

## 1. Khóa An Toàn Bất Biến & 6 Mốc Thời Gian Trọng Yếu (`30/11 -> 14/12`)

| Thành phần / Mốc | Trạng thái xác minh | Ghi chú & Ràng buộc |
|---|---|---|
| **Ứng viên & tài chính** | **`C10_NEWS_ON` (`7E`) · `0 VND`** | `Naqex_Master_Prop7E.mq5` (`6b7ea2ee...`) & `.mqh` bất biến; `10` `.ex5` nguyên vẹn; `OrderSend = 0`; `MT5_PROCS = 0`. |
| **Holdout & tệp khóa** | **NIÊM PHONG (`0` dòng)** | Lock `f0a6b43c...`; `step3` `a3b65380...`; CSV tin đỏ `235722ed...`; `AGENTS.md` `10.901 B` (`+0 B`); `5/5` WIP `vi-dubber` nguyên vẹn. |
| **Đồng hồ NTP & 3 Máy** | **`strict_ntp_passed = true`** | `<DEV_PC>` `-24,2 ms` (`< 25 ms`, `MODE_A`); `<X13_WORKER>` `+27,7 ms` (`AC=1`, `0` tệp cấm); `naqex-node1` cô lập chỉ-đọc. |
| **Mốc 1–2 (`30/11` & `01/12`)** | **`30/11 16:00 ICT` · `01/12 00:00 UTC`** | Khóa hóa đơn chưa thanh toán Black Friday (`0 VND`) · Khóa đăng ký trước `holdout_v2_prospective`. |
| **Mốc 3–4 (`04/12` & `08/12`)** | **`04/12 20:30 ICT` · `08/12 23:59 ICT`** | Thu băng `QUOTE_ONLY` NFP · **Hết hạn FTMO Free Trial trên `naqex-node1`** (bắt buộc gom đủ log/sao kê trước hạn). |
| **Mốc 5–6 (`10/12` & `14/12`)** | **`10/12 20:30 ICT` · `14/12 16:00 ICT`** | Thu băng `QUOTE_ONLY` CPI · **Hạn cuối thanh toán hóa đơn BF `14` ngày** (Go/No-Go cuối ở `0 VND` nếu Mốc 0 chưa xanh). |

## 2. Việc Kế Tiếp (`0 VND`)

1. **Hoàn tất hội tụ Wave 2A/2B (19 cổng bắt buộc):** chạy `verify_deployment_kit.py --build`, `preregister_holdout_v2.py --freeze`, phân tán shard X13 hợp lệ, kiểm toán 19 cổng (`tooling/workflows/audit_19_gates.py`), và nghiệm thu toàn bộ `9` báo cáo mới tại [research/README.md](research/README.md).
2. **Thu thập bằng chứng thực địa Mốc 0 (`04/12` NFP -> trước `08/12` hết hạn Free Trial -> `10/12` CPI):** thu đủ log/sao kê đọc-thuần & chốt thư xác nhận EA bằng văn bản từ FTMO / The5ers.
3. **Quyết định cổng `G6` trước `14/12 16:00 ICT` (`0 VND` mặc định):** chỉ xem xét thanh toán nếu trượt giá thực đo `<= 1,50x`, `0` lỗi parity/swap và toàn bộ điều kiện Mốc 0 đạt `100%`.
