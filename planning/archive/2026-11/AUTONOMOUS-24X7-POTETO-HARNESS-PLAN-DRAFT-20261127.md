---
doc_type: archived-plan-draft
domain: workspace-automation
topic: autonomous-24x7-poteto-harness-plan
created_utc: 2026-11-27
status: ARCHIVED_DEFERRED
owner_decision: deferred_focus_on_3_pending_items_first
---

# [LƯU TRỮ / TẠM HOÃN] Kế Hoạch Hệ Thống Tự Động Hóa 24/7 (`Naqex Poteto-Harness v1`)

> **Trạng thái:** **ARCHIVED / DEFERRED (`2026-11-27`)** theo quyết định của chủ sở hữu (*tạm gác lại để hoàn tất 3 hạng mục chờ duyệt trước: dọn Tier C Đợt 1+3A, đẩy 5 nhánh + mở 5 PR + cổng CI `diffq-fixed`, và đồng bộ NTP*). Bản thiết kế đầy đủ được lưu lại dưới đây để tái kích hoạt nhanh khi cần, không phải phỏng vấn lại từ đầu.

## 1. 6 Quyết Định Kiến Trúc Đã Chốt Qua `/grill-me`

- **Triết lý lõi (Lauren Tan `@poteto` / `pstack` & Harness Engineering):** *Evidence Before Confidence*, *Runtime Feature Map* (`feature_map.json`), *Independent Verifier*, và *Ratchet Principle* (biến mỗi lỗi CI/review thành quy tắc `[ARCH-*]` hoặc test đột biến âm mới thay vì nhồi `AGENTS.md`).
- **Trust Curve (`PR-First & Ratchet`):** AI Agent 24/7 tự phát hiện lỗi -> tạo worktree cô lập (`worktree_ctl.py`) -> tự sửa -> tự kiểm chứng runtime thật + Verifier độc lập -> mở PR nhánh `auto/*` + tự vá nếu CI đỏ -> **dừng trước `Merge` vào `main`** chờ chủ duyệt 1 nút.
- **Khóa an toàn bất biến:** `0 VND`, `OrderSend = 0`, `MT5_PROCS = 0`, `Holdout 2025+ SEALED`, không sửa EA live trên `naqex-node1`, không force-push, không tự merge `main`/`master`, `AGENTS.md` `+0 B`.
- **5 Trụ cột trên 1 kiến trúc native (`0` chi phí hạ tầng mới):** Antigravity Scheduled Automations (`~/.gemini/config/sidecars/`) + Windows Task Scheduler + GitHub Actions + `compute_router.py` 3 máy (`PC Dev` Mode A/B, `ThinkPad X13` AC, `naqex-node1` chỉ-đọc).
  1. **Trụ cột 1 — Lõi Lauren Tan & Self-Healing CI:** `.agents/skills/poteto-autonomous-verify/`, `configs/automation/feature_map.json`, `tooling/automation/{event_queue.py,self_healing_ci.py,ratchet_engine.py}`, mở rộng `check_architecture.py` `[ARCH-08..10]`.
  2. **Trụ cột 2 — Hạ tầng 3 máy tự chữa lành:** `install_ntp_and_watchdog_tasks.ps1` (`Naqex-NTP-Sync-6h` `SYSTEM` + `Naqex-Watchdog-15m` 0-token), `watchdog_15m.py`, `install_git_hooks.py` (`pre-commit` + `post-commit` `brain_cli.py index` `27 ms`).
  3. **Trụ cột 3 — Quant R&D & Prop ban đêm (`01:30` VN):** `nightly_quant_ops.py` (`system_doctor --mode full`, `Hypothesis` X13, `mql_contract_drift`, cảnh báo NFP/CPI trước `48h`, `daily_statement_reconciler` chỉ-đọc).
  4. **Trụ cột 4 — QA 3 Sản phẩm & Bản quyền:** `product_qa_sweep.py` (`Cockpit` HTTP ephemeral, `Trader` contracts/UI, `Quant Lab`, `VI Dubber` AST license guard, `Education`, `Integrations`).
  5. **Trụ cột 5 — Bản tin sáng `07:30` VN & Cockpit API:** `morning_briefing.py`, `cockpit/modules/automation.py` (`GET /api/automation/status`), `naqex_cli.py auto ...`, và 2 sidecars (`naqex-poteto-healer` `CRON_TZ=Asia/Ho_Chi_Minh 0 */3 * * *` + `naqex-morning-chief` `CRON_TZ=Asia/Ho_Chi_Minh 30 7 * * *`, do chủ bấm Enable thủ công).
- **Nhịp vận hành & Circuit Breaker:** Watchdog Python thuần `0` token mỗi `15` phút; AI Agent chạy khi có sự kiện thật hoặc mỗi `3` giờ với **trần cứng `3` lần thử sửa / `1` lỗi** (vượt trần tự gắn `NEEDS_HUMAN` và dừng).

## 2. Cách Tái Kích Hoạt Sau Này

Khi sẵn sàng triển khai, chỉ cần nhắc *"mở lại kế hoạch `AUTONOMOUS-24X7-POTETO-HARNESS-PLAN-DRAFT-20261127.md`"* (đặc biệt sau khi 5 PR nền tảng đã merge vào `main` và NTP 2 máy đã về `< 1.000 ms`).
