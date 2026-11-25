---
doc_type: audit
domain: workspace
topic: integrations-capability-audit-20261125
updated_utc: 2026-11-25
status: READ_ONLY_AUDIT_COMPLETE
deletions_performed: 0
ordersend_count: 0
---

# Kiểm Toán Năng Lực & Giá Trị Thực Tế `projects/integrations/` (`25/11/2026`)

- **Chế độ kiểm toán:** **100% chỉ đọc** trên `projects/integrations/*` (`0` sửa đổi, `0` cài gói, `0` lệnh git ghi, `0` gọi API LLM trả phí, `0` mở MT5, `OrderSend = 0`).
- **Mục tiêu:** Đối chiếu sức khỏe kiểm thử offline, dung lượng/chi phí bảo trì và giá trị thực chiến của `4` nguồn tích hợp ngoài với lộ trình [Naqex 2026–2027](../../knowledge/playbooks/naqex-master-roadmap-2026-2027.md) (trọng tâm hiện tại: Phase 0–1 chạy chuẩn `Master Prop7E` trên `FTMO Standard BF / Swing 10K` + dây chuyền nội bộ `quant_factory`, hoãn Own-Book phức hợp dưới `10k USD`).

---

## 1. Bảng Phán Quyết Nhanh (`4` Tích Hợp Ngoài)

| Tích hợp | Commit ghim | Dung lượng tổng (`source + .runtime`) | Kiểm thử offline (`25/11/2026`) | Lần chạy thật gần nhất | Phán quyết |
|---|---|---:|---|---|---|
| **Paperclip** | `5501757` (`codex/naqex-integration`) | **`2,931 GiB`** (`2,597` + `0,334`) | **ĐẠT:** `doctor` OK, `windows-process-owner` `3/3`, wrapper `PASS` | `04–05/11/2026` (ngủ `~20` ngày) | **`KEEP_STANDBY`** |
| **Hermes** | `bf0203a7` (`v0.22.5`) | **`0,741 GiB`** (`0,217` + `0,524`) | **ĐẠT:** `doctor` OK, import SDK `AIAgent` OK, wrapper `PASS` | `02/11/2026` (pilot phản biện) | **`KEEP_STANDBY`** |
| **TradingAgents** | `ecaafe5` (`codex/integration-layout`) | **`0,202 GiB`** (`0,189` là `.venv`) | **ĐẠT:** `doctor` OK, **`82/82`** unit test lõi (`5,57s`), wrapper `PASS` | `01–02/11/2026` (`NAQ-4`) | **`KEEP_STANDBY`** |
| **RD-Agent** | `484776c2` (`v1.0.0`) | **`6,714 GiB`** (`0,011` + `6,703` WSL2) | **ĐẠT (source):** `doctor` OK, wrapper `PASS`; WSL2 `NaqexResearch` đang `Stopped` | `02/11/2026` (`NAQ-6`, không đạt) | **`ARCHIVE_CANDIDATE`** |

- **Kiểm chứng chung lớp cầu nối Naqex (`tooling/ai-engines/tests/`):** Chạy `8` bộ kiểm thử offline (`test_engine_worker`, `test_paperclip_auth`, `test_paperclip_strategy_skills`, `test_rd_research`, `test_hermes_plugin`, `test_hermes_worker`, `test_spot_workflow`, `test_studio_workflows`, `0` gọi mạng/LLM) đạt **`76 passed, 76 subtests passed` (`4,59s`)**. Toàn bộ `4/4` submodule giữ sạch **`0` file bẩn** theo [doctor.mjs](../../tooling/integrations/doctor.mjs).

---

## 2. Phân Tích Chi Tiết Từng Tích Hợp

### 2.1. `paperclip` — **`KEEP_STANDBY`** *(Control-plane UI cho Trader Studio, tắt nền ở Phase 0–1)*

- **Hiện trạng kỹ thuật:** Fork Naqex ([tooling/paperclip/README.md](../../tooling/paperclip/README.md)) đã đầu tư lớn: nhúng iframe tĩnh vào `projects/trader` (**Studio → Đội AI**), Việt hóa `10.923` chuỗi, cầu nối ngôn ngữ VI/EN, OAuth MCP cục bộ và PostgreSQL riêng trong `.runtime/paperclip/instances/trader-ui/`. Bài kiểm tra khóa PID Windows (`windows-process-owner.test.mjs`) đạt `3/3`.
- **Chi phí & giới hạn:** Chiếm **`2,597 GiB` (`121.797` files)**, riêng `node_modules` monorepo `pnpm@9.15.4` đã là `2,313 GiB` (`105.626` files). Bản ghim còn nợ upstream (`106` lỗi token gate sẵn có, Copilot bị chặn trên `win32`, Antigravity `qualified=false`, Gemini CLI dừng tài khoản cá nhân từ `06/2026`). DB `pg_wal` đứng yên từ `05/11/2026`.
- **Khuyến nghị:** Không bật chạy nền trong sprint Prop Phase 0–1 (Antigravity Swarm + Cockpit cục bộ đang gọn và nhanh hơn nhiều). Giữ nguyên ở chế độ chờ vì đây là hạ tầng UI đã hoàn thiện của sản phẩm `projects/trader`; không nâng cấp upstream khi chưa mở lại làn phát triển Studio UI.

### 2.2. `hermes-agent` — **`KEEP_STANDBY`** *(Bộ phản biện SDK nhẹ, giữ dự phòng cho Studio)*

- **Hiện trạng kỹ thuật:** Thiết kế sạch nhất trong `4` tích hợp ([tooling/ai-engines/hermes.md](../../tooling/ai-engines/hermes.md)): chạy thẳng `AIAgent` SDK trong tiến trình con (không daemon ngầm), chỉ mở `3` công cụ tối giản (`research_publish`, `memory`, `session_search`), cấm quyền terminal/file/broker và bắt buộc đối chiếu SHA-256 đầu vào/đầu ra. Kiểm tra import SDK trên Python `3.14.9` PM venv đỗ tức thì (`HERMES_IMPORT_OK True`).
- **Giá trị so với công cụ hiện hành:** Chiếm rất ít dung lượng (`0,741 GiB` tổng, `0` áp lực bảo trì). Tuy nhiên, ở Phase 0–1, vai trò phản biện đa họ model đã có **Astra (GPT-6.2) + `@verifier` + TypeSafe `jev-1.14.0`** đảm nhiệm trực tiếp với chi phí thấp và độ phủ mã nguồn sâu hơn (Hermes không đọc được file ngoài đoạn trích trong task).
- **Khuyến nghị:** Giữ ở chế độ chờ (`KEEP_STANDBY`) để phục vụ các luồng phản biện tự động trong Paperclip Studio ở Phase 2+. Không cần chạy định kỳ ngay lúc này.

### 2.3. `TradingAgents` — **`KEEP_STANDBY`** *(Không dùng cho FX Prop; giữ nhẹ nhờ `.venv` phục vụ CLI/test)*

- **Hiện trạng kỹ thuật:** Kiểm thử offline cực khỏe — `82/82` test lõi (chống nhìn trước báo cáo tài chính/mạng xã hội, bộ nhớ point-in-time, ranh giới ngày, crypto mode, tách lớp) đỗ trong `5,57s`. Chiếm chỉ **`0,202 GiB`** (trong đó `.venv` `0,189 GiB`).
- **Giá trị thực tế đối với lộ trình 2026–2027:**
  - **Không dùng cho đường lệnh hay FX Prop:** Adapter chỉ hỗ trợ `crypto` và `stock`, không nối Forex/MT5 ([tooling/ai-engines/README.md](../../tooling/ai-engines/README.md)). Kết quả là văn bản tranh luận cảm tính/tin tức từ LLM, không phải luật định lượng kiểm chứng được (`Lab #6` đã xác nhận ngay cả Meta-Labeler ML còn âm `Brier Skill`, còn lõi Naqex chạy `100%` luật trắng xác định).
  - **Lý do chưa xếp `ARCHIVE_CANDIDATE` ngay:** Thứ nhất, `.venv` của `TradingAgents` (`0,189 GiB`) hiện là môi trường Python chạy bộ test `tooling/ai-engines/tests/` (`76/76` đỗ) và các script `spot_workflow.py`, `studio_workflows.py`, `paperclip_setup.py`. Thứ hai, ở Phase 2–3 khi cầm Own-Book cổ phiếu/ETF, công cụ này có thể dùng thủ công kiểu **kiểm tra bối cảnh vĩ mô/tin tức chỉ đọc** nếu muốn.
- **Khuyến nghị:** Giữ ở `KEEP_STANDBY` (tuyệt đối không chạy tự động tốn phí API LLM). Ở đợt dọn môi trường sau, nếu chuyển toàn bộ test/CLI `tooling/ai-engines/` sang `.runtime/quant-audit-v24/`, có thể đánh giá lại để đưa `TradingAgents` sang `ARCHIVE_CANDIDATE`.

### 2.4. `rd-agent` — **`ARCHIVE_CANDIDATE`** *(Đề xuất xuất lạnh đĩa WSL2 `6,70 GiB` sang `E:`)*

- **Hiện trạng kỹ thuật:** Bản mã nguồn gitlink chỉ nặng `11,5 MB`, sạch `source-ready`, nhưng để chạy được phải gánh cả máy ảo WSL2 Ubuntu 24.04 + Docker Engine tại `.runtime/linux/NaqexResearch/ext4.vhdx` nặng **`6,703 GiB`** ([rd-agent-runtime.md](../../tooling/ai-engines/rd-agent-runtime.md)). Hiện `wsl --list --verbose` xác nhận distro `NaqexResearch` đang **`Stopped`** và lần chạy thật cuối cùng là bài thử `NAQ-6` ngày `02/11/2026` (ứng viên `crypto-momentum-3d-v1` không đạt chuẩn).
- **Đối chiếu thực chứng với năng lực nội bộ:** Toàn bộ kết quả nghiên cứu định lượng thực chiến suốt tháng 11 (`Pass 1 → Pass 32`, `Labs #1 → #12`, Holdout `2025–2026`, kiểm toán `Master Prop7E` và `Lab #7` trên `21` năm `40` ETF — xem [LAB7-OVERNIGHT-DRIFT-AND-RD-LOOP-20261124.md](LAB7-OVERNIGHT-DRIFT-AND-RD-LOOP-20261124.md)) **100% được thực hiện bằng dây chuyền Python + Numba JIT nội bộ (`tooling/ai-engines/quant_factory/auto_research_loop.py`)** với tốc độ mili-giây, **không dùng tới container Linux của `rd-agent`**.
- **Chi phí giữ nóng so với lợi ích:** Giữ `6,70 GiB` VHDX trên SSD `D:` kèm nghĩa vụ vá bảo mật Ubuntu/Docker trong khi chưa dựng image Qlib/CUDA và chưa dùng suốt `3` tuần là dư thừa cho Phase 0–2.
- **Khuyến nghị cụ thể (giữ sạch hợp đồng Git):**
  - **GIỮ** gitlink mã nguồn `projects/integrations/rd-agent` (`11,5 MB`) để `check_workspace.py`, `catalog.json` và `doctor.mjs` tiếp tục đạt `100%`.
  - **XUẤT LẠNH** máy ảo WSL2 `NaqexResearch` sang ổ `E:` bằng lệnh chuẩn của WSL (không tự xóa, chỉ lưu bản nén `.tar` trước để chủ sở hữu kiểm tra rồi mới quyết định `wsl --unregister` thu hồi `6,70 GiB` trên `D:`!).

---

## 3. Lệnh PowerShell Xuất Lạnh WSL2 `rd-agent` An Toàn (Chờ Chủ Sở Hữu Duyệt)

> Chỉ thực hiện bước xuất bản sao lưu sang `E:` (**`0` tự động xóa**). Tuyệt đối không xóa thẳng file `ext4.vhdx` bằng tay khi distro còn đăng ký trong WSL; chỉ chạy lệnh `wsl --unregister` (đã ghi chú sẵn, bị comment) sau khi đã kiểm tra file `.tar` trên `E:` hoàn chỉnh và không có job nào đang dùng WSL.

```powershell
# Bước 1 (chỉ đọc): kiểm tra chắc chắn NaqexResearch đang Stopped
wsl.exe --list --verbose

# Bước 2 (chỉ sao lưu, 0 xóa): tạo thư mục và xuất lạnh nguyên trạng distro sang ổ E:
New-Item -ItemType Directory -Force -Path 'E:\BACKUP-TRADINGWORKSPACE\wsl-backups' | Out-Null
wsl.exe --export NaqexResearch 'E:\BACKUP-TRADINGWORKSPACE\wsl-backups\NaqexResearch-20261125.tar'

# Bước 3 (kiểm tra dung lượng file .tar trên E:)
Get-Item 'E:\BACKUP-TRADINGWORKSPACE\wsl-backups\NaqexResearch-20261125.tar' | Select-Object Name, Length, LastWriteTime

# Bước 4 (CHỈ chạy thủ công sau khi chủ sở hữu xác nhận file .tar ở Bước 3 đạt chuẩn để thu hồi 6,70 GiB trên D:):
# wsl.exe --unregister NaqexResearch
# Khi cần khôi phục ở Phase 3-4:
# wsl.exe --import NaqexResearch 'D:\ANNAM\TradingWorkspace\.runtime\linux\NaqexResearch' 'E:\BACKUP-TRADINGWORKSPACE\wsl-backups\NaqexResearch-20261125.tar' --version 2
```
