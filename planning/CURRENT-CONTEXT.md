# Current context — Naqex Workspace

`27/11/2026 01:40 ICT` · `WORK: STEP8-AND-LEARN-APPLIED-VERIFIED | 0-VND | LIVE-NODE1: ONLINE-CONNECTED-FLAT | HOLDOUT 2025+ SEALED`

`GOAL-NOW: BƯỚC 8 + /LEARN ĐÃ ÁP DỤNG & KIỂM TOÁN 5/5 PASS (6/6 ĐIỂM CUỐI ASTRA V11 ĐÃ ĐÓNG · CHÍNH THỨC DỪNG ASTRA NGOÀI | TẠO SKILL ADVERSARIAL-SELF-AUDIT + NÂNG QUANT-FACTORY-OPS §7 & NAQEX-NODE-OPS +0 B AGENTS.MD · 26 SKILLS · 0 LỖI | SẴN SÀNG TRIỂN KHAI COMBO XƯƠNG SỐNG: COMPUTE_ROUTER.PY) | GIỮ 0 VND`

## 0. Trạng Thái Hiện Tại Sau Bước 8 (`27/11/2026`)

- **Chính thức khép lại chuỗi kiểm toán Astra bên ngoài (`Vòng 1 -> Vòng 11`) & đóng trọn `6/6` điểm chính xác cuối của Vòng 11 (`73/73` pytest PASS trong `4,53s`, `system_doctor --mode fast 9/9 PASS` trong `5,79s`):**
  - **Q1 (`step7_1_l0_lot_divergence_audit.py` SHA `4a6e88c6add084bc`):** Chấm đậu pha P2 bắt buộc phẳng vị thế (`open_positions == 0` -> mốc đúng **`2024-11-15 22:55`, `10.593,54 USD`**, thay vì `18:00` còn mở `0,16` USDJPY), ghi rõ giới hạn kiểm đường equity giữa các mẫu.
  - **Q2 (`nfp_cpi_quote_collector.py` `495aedc257acb20b`, `step7_2_demo_ro_hydration_probe.py` `3b8102f21d27e8e5`):** Bắt buộc `--expected-login`/`--expected-server`, dừng fail-closed nếu `trade_allowed == True`, yêu cầu đủ `3` pha tin (`PRE_EVENT + IMPACT_CORE + POST_NORMALIZE`, chặn mẫu giả 1 giây), gắn cờ mất thứ tự cùng `1 ms`; Probe Demo đồng bộ biên `48h` theo giờ server, lỗi `None` báo cứng và chỉ kết luận trên Core7 (loại trừ shadow S6).
  - **Q3 (`prop_pricing_catalog.json` `596c830024ab72a9`, `prop_capital_promo_optimizer.py` `615d382d21b15d86`, [Report Optimizer v2](research/MULTI-FIRM-CAPITAL-PROMO-OPTIMIZER-20261126.md) `8634225c533af2ac`):** Gắn hạn `verified_utc` riêng cho **`42/42` gói**, chặn tuyệt đối `NaN`/`Inf`/`<= 0` và ngày tương lai `2099` (kể cả khi `allow_stale=True`), gắn nhãn `DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET` cho `The5ers` & `IC Funded`, và quét dày `181` ngày (`0..180`) cho chân trời trượt công bố đủ mốc liên tục / rơi đầu / dương cuối.
- **Kiểm Toán Khoảng Trống Top 1% Toàn Diện (`6` trụ cột · `22` nguồn chuẩn `T1` · `27/27` link sạch):** [TOP1-PCT-QUANT-SYSTEMS-AND-AI-AGENT-GAP-AUDIT-20261127.md](research/TOP1-PCT-QUANT-SYSTEMS-AND-AI-AGENT-GAP-AUDIT-20261127.md) (`SHA 917c33532bd0f386`) chốt `5` lỗ hổng cấu trúc phi-chỉ-số (1 họ intraday CFD -> `60%` tháng đói Funded; thuế 2 ngôn ngữ Python↔MQL5 & `0` đường cong Markout; thiếu PBO/CPCV/Hansen SPA + `0` tháng live; `390` script rời & `run_registry` `0` chỗ gọi; thiếu Harness tự săn lỗi `hypothesis`/`mutmut`/`ruff` + CI mới quét `12/238` tệp) kèm lộ trình `30/60/90` ngày cho Solo Builder (`0` rác hạ tầng doanh nghiệp).
- **Kiến Trúc Điều Phối Tính Toán & Đồng Bộ 3 Máy (`Star Topology` · đã khóa `/grill-me Q1`):** [THREE-NODE-COMPUTE-ORCHESTRATION-AND-SYNC-BLUEPRINT-20261127.md](research/THREE-NODE-COMPUTE-ORCHESTRATION-AND-SYNC-BLUEPRINT-20261127.md) (`SHA 67abc4d031747aaf`) quy định `<DEV_PC>` là trung tâm Git/Holdout duy nhất, tự điều phối không hỏi cho lô offline `<= 60` phút (`Mode A 2–3` nhân `BelowNormal` `0%` GPU khi chủ dùng/chơi game; `Mode B 5/6` nhân + song song `60/40` `10` mảnh nhỏ khi rảnh `>= 15p`/đêm + tự nhường quyền `30s`; `<X13_WORKER>` kiểm tiền kiểm `1,5s` LAN/TS + bắt buộc cắm sạc AC, tự lùi êm về `<DEV_PC>` khi tắt/dùng pin), và thiết kế đặc tả `compute_router.py` (`~250` dòng).
- **Đợt `/learn` Đã Áp Dụng & Kiểm Toán Sạch (`27/11/2026` · `+0 B` vào `AGENTS.md`):** Tạo mới `.agents/skills/adversarial-self-audit/SKILL.md` (thay hẳn Astra bên ngoài bằng quy trình 7 mũi phản biện nội bộ), nâng `.agents/skills/quant-factory-ops/SKILL.md` (§7 điều phối 3 máy + Star Sync + NTP `< 1s`) và `.agents/skills/naqex-node-ops/SKILL.md` (cô lập 3 máy), cập nhật bộ nhớ Layer-2 (`private_vault/owner/`) + `docs/development/SKILL-MAINTENANCE.md`. Kiểm toán đạt `5/5`: `audit-ai-environment` (`26` skill, `0` lỗi/`0` cảnh báo), `check_skill_links` (`18` repo skill, `0` lỗi), `OPSEC 6/6`, `System Doctor 9/9`, `brain_cli` (`743` tệp / `5.304` đoạn).
- **Lịch sử kiểm toán trước đó:** [STEP7](research/STEP7-ASTRA-R10-CLOSURES-AND-ROUND11-AUDIT-20261126.md) · [STEP6](research/STEP6-C10-NEWS-ON-DEMO-RO-AND-ASTRA-ROUND10-AUDIT-20261126.md) · [STEP5](research/STEP5-C00-VS-C10-AND-ASTRA-ROUND9-AUDIT-20261126.md) · [STEP4](research/STEP4-HARDENING-RESTART-Q2-AND-DECOMP-AUDIT-20261126.md) · [STEP3](research/STEP3-V102AB-MERGED-AND-CONTINUOUS-REPLAY-AUDIT-20261126.md) · [STEP2](research/STEP2-V102AB-ISOLATED-AND-PYTHON-REPLAY-AUDIT-20261126.md) · [STEP1](research/STEP1-V101-PREDECISION-OBSERVABILITY-AND-FORMULA-PARITY-20261126.md).

## 1. Khóa An Toàn Bất Biến & Trạng Thái Hạ Tầng

| Thành phần | Trạng thái xác minh | Ghi chú |
|---|---|---|
| **Ứng viên duy nhất & tài chính** | **`C10_NEWS_ON` (Standard 10K) · `0 VND`** | EA giữ nguyên `v1.01` (`3` cờ mặc định `0`); `OrderSend = 0`. |
| **Holdout `2025+` & `step3` gốc** | **NIÊM PHONG (`0` dòng / bất biến)** | Lock SHA `f0a6b43cb205535b`; `step3` SHA `a3b6538016614e1d`. |
| **Home-VPS `naqex-node1`** | **`ONLINE GREEN / UNTOUCHED`** | Tầng thực thi cô lập 24/5; không chạm suốt Bước 1–8. |
| **ThinkPad X13 (`<X13_WORKER>`)** | **`READY (LAN/TS SSH + Numba 8T)`** | `13,56M paths/s`, AC-only gập nắp không sleep, `0` Holdout/secrets (chi tiết Layer-2). |
| **Đồng hồ PC Dev (`NTP`)** | **Cảnh báo trôi `-1.410 ms`** | Bộ thu thập chặn fail-closed (`RC=2`); cần Admin `w32tm /resync` trước `04/12`. |
| **MT5 cục bộ & `projects/`** | **`0` tiến trình MT5 · `projects/` sạch** | `trader`, `quant-trading`, `vi-dubber` không bị sửa. |

## 2. Việc Kế Tiếp (`0 VND`)

1. **Triển khai Combo Xương Sống — Chặng 1 (`~25–35` phút):** viết `tooling/ai-engines/ops_cloud/compute_router.py` (`~250` dòng) + `x13_probe.py` kèm unit test đột biến âm (`adversarial-self-audit`) và chạy thử 1 lô Numba thật sang `<X13_WORKER>`.
2. **Cài bộ săn lỗi gọn vào `.runtime/quant-audit-v24`:** `hypothesis`, `ruff`, `duckdb` + nâng `.github/workflows/workspace.yml` tự quét test offline.
3. **Đồng bộ đồng hồ NTP (`w32tm /resync` quyền Admin)** trước cửa sổ thu thập `QUOTE_ONLY` quanh **NFP `04/12/2026`** & **CPI `10/12/2026` (`20:25 ICT`)**.
