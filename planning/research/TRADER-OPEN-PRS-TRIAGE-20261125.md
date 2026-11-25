---
doc_type: audit
domain: trader
topic: trader-open-prs-triage-20261125
updated_utc: 2026-11-25
status: READ_ONLY_TRIAGE_COMPLETE
repo: Naqex/trader
ordersend_count: 0
---

# Phân Loại & Chẩn Đoán Gốc Các PR Đang Mở Trên `Naqex/trader` (`25/11/2026`)

- **Chế độ kiểm tra:** **100% chỉ đọc** qua GitHub CLI (`-R Naqex/trader`), `0` chỉnh sửa/checkout cục bộ trong `projects/trader`, `0` lệnh git ghi, `OrderSend = 0`.
- **Tổng số PR đang mở lúc kiểm tra:** **`11` PR** (sau khi PR `#35` đã merge tại `b4ab46f6`), gồm `3` PR trọng tâm cần xử lý (`#29`, `#30`, `#32`), `4` PR Dependabot đang xanh `5/5` (`#26`, `#27`, `#31`, `#34`), và `4` PR sửa lỗi/tối ưu Wave 2 đang trong hàng đợi merge (`#36`–`#39`).

---

## 1. Bảng Quyết Định 1 Nhấp Cho Toàn Bộ `11` PR Đang Mở

| PR | Tiêu đề ngắn | Trạng thái CI | Nguyên nhân / Tình trạng | Khuyến nghị |
|---|---|---|---|---|
| **#29** | Bump `@vitejs/plugin-react` `5.2.0 → 6.2.1` | `4/5` (**ĐỎ** `Web build`) | Xung đột peer `vite@^8.0.0` vs `vite@7.3.7` | **`CLOSE_AND_WAIT_VITE8`** |
| **#30** | Bump `uv` nhóm `4` gói (`fastapi`, `pyarrow`, `pydantic`, `langgraph`) | `4/5` (**ĐỎ** `Python contracts`) | Trôi ảnh chụp `command_contracts.json`; có `2` vá bảo mật `pydantic` | **`FIX`** (tái xuất contract) |
| **#32** | `codex/solo-system-research` (`19` files, cũ `48` commit) | `5/5` XANH (cũ `14/11`) | `14/19` file đã vào `#33`; `2` docs chứa path máy cá nhân; `3` file có ích nhỏ | **`CHERRY_PICK`** `3` file rồi **ĐÓNG** |
| **#26** | Bump `cargo` compatible group (`2` updates) | `5/5` XANH (`BEHIND`) | Hợp lệ, chờ update branch sau `#36`–`#39` | **`MERGE_AFTER_WAVE2`** |
| **#27** | Bump `base64` `0.22.1 → 0.23.1` (`api-rust`) | `5/5` XANH (`BEHIND`) | Hợp lệ, chờ update branch sau `#36`–`#39` | **`MERGE_AFTER_WAVE2`** |
| **#31** | Update `psycopg[binary]` `>=3.3.8,<4` | `5/5` XANH (`BEHIND`) | Hợp lệ, chờ update branch sau `#36`–`#39` | **`MERGE_AFTER_WAVE2`** |
| **#34** | Bump `npm` compatible group (`7` updates) | `5/5` XANH (`BEHIND`) | Hợp lệ, chờ update branch sau `#36`–`#39` | **`MERGE_AFTER_WAVE2`** |
| **#36–#39** | Wave 2 UI/Auth/Perf/i18n (`4` PR đang mở) | Đang luồng merge | Không xung đột với `#32`; đang xử lý riêng | **`KEEP_MERGE_QUEUE`** |

---

## 2. Chẩn Đoán Gốc Chi Tiết `3` PR Trọng Tâm

### 2.1. PR #29 (`@vitejs/plugin-react` `5.2.0 → 6.2.1`) → **`CLOSE_AND_WAIT_VITE8`**

- **Bằng chứng log CI thất bại (run `43125515458`, job `Web build and browser smoke`):**
  - Lệnh `npm ci --ignore-scripts --no-audit --no-fund` dừng ngay với **`npm error code ERESOLVE`**:
    - Dự án hiện ghim **`vite@"^7.3.7"`** trong `foundation_v2/web/package.json`.
    - Gói **`@vitejs/plugin-react@6.2.1`** bắt buộc **`peer vite@"^8.0.0"`** (`Conflicting peer dependency: vite@8.3.8`) vì v6 chuyển sang nền Vite 8 / Rolldown / OXC (gỡ toàn bộ `@babel/*`).
- **Hành động đề xuất:** Đóng PR `#29` (và bình luận `@dependabot ignore this major version`). Tuyệt đối không dùng `--legacy-peer-deps`. Chỉ nâng `@vitejs/plugin-react` 6.x trong một PR riêng khi chủ động nâng `vite` 7 → 8 kèm chạy lại đủ kiểm thử trình duyệt.

### 2.2. PR #30 (`dependabot/uv/foundation_v2/compatible-88cae9a3d0`) → **`FIX`**

- **Bốn gói được nâng:** `fastapi` (`0.162.0 → 0.163.1`), `pyarrow` (`26.0.0 → 26.0.1`), `pydantic` (`2.13.5 → 2.14.3`, `pydantic-core` `2.46.5 → 2.50.4`), `langgraph` (`1.2.19 → 1.2.22`).
- **Bằng chứng log CI thất bại (run `44427019740`, job `Python contracts`):**
  - Toàn bộ `13/13` bài `ReleaseWorkflowTests` **ĐẠT**, sau đó dừng tại `foundation_v2/scripts/export_api_command_contracts.py` dòng `33`:
    **`ValueError: frozen command contract drift: command_contracts.json`**.
  - **Căn nguyên:** Script `export_api_command_contracts.py` dựng ứng dụng FastAPI offline, xuất `DomainCommandDispatcher(app).manifest()` và so sánh chính xác 100% với tệp đóng băng `foundation_v2/trading_workspace_v2/command_contracts.json`. Đợt nâng `pydantic 2.14.x` (đổi cách chuẩn hóa JSON Schema cho `unless-none`, `TypedDict`/dataclass) và `fastapi 0.163.1` (sửa OpenAPI cho `computed_field` lồng nhau) làm thay đổi hình thức JSON Schema xuất ra, nên cổng chống trôi hợp đồng báo lệch — không phải hỏng chức năng.
- **Lý do nên `FIX` thay vì `CLOSE`:** Ghi chú phát hành `pydantic v2.14.2` vá **`2` lỗ hổng bảo mật (`GHSA-qpmf-fgh3-ff25` và `GHSA-3r8g-cqwr-jr29`)**.
- **Cách sửa gọn (`1` bước trên nhánh riêng sau khi `#36`–`#39` merge):** Chạy `export_api_command_contracts.py --output <tmp>` trong môi trường của PR `#30`, đối chiếu diff của `command_contracts.json` (và `contracts/openapi.json` nếu có), xác nhận không đổi dây dẫn JSON mà Rust/Web đọc rồi cập nhật bản đóng băng trong cùng PR là CI xanh `5/5`.

### 2.3. PR #32 (`codex/solo-system-research`, `19` files) → **`CHERRY_PICK` rồi ĐÓNG**

- **Đối chiếu từng tệp với PR #33 đã merge (`74dad35d`, `18/11/2026`), `main` hiện tại (`behind_by = 48`) và PRs `#35`–`#39`:**
  - **`14 / 19` tệp ĐÃ BỊ THAY THẾ 100% TRÊN `main`:**
    - `9` tệp lõi (`ai_assistant.rs`, `ai_gateway.rs`, `ARTIFACT-STORAGE.md`, `run_api_platform.py`, `test_api_platform_launcher.py`, `test_artifact_verification_cache.py`, `artifact_backup.py`, `artifacts.py`, `restart_offline_api.ps1`) khớp **nguyên byte** với PR `#33` và `main`.
    - `1` tệp (`test_artifact_storage_architecture.py`) đã có bản **đầy đủ hơn** từ PR `#33` (`+34/-1` so với `+29/-0`).
    - `4` tệp chỉ format Rust (`commands.rs`, `live_ledger.rs`, `note_library.rs`, `note_types.rs`) đã khớp `100%` với `main`.
  - **`2 / 19` tệp KHÔNG NÊN GỘP:** `docs/research/SOLO-SYSTEM-EXECUTION-20261115.md` (`+101`) và `SOLO-SYSTEM-RESEARCH-20261115.md` (`+234`) là ghi chép cũ ngày `15/11` (nói về V3/V4 đã qua) và **chứa đường dẫn tuyệt đối gắn tên tài khoản Windows cục bộ**, vi phạm chuẩn di động của repo.
  - **`3 / 19` tệp còn giá trị độc nhất (chưa có trên `main`, không đụng PR `#35`–`#39`):**
    1. `foundation_v2/api-rust/src/automation_grants.rs` (`+22/-7` trong `mod tests`, commit `621f0e0b`): sửa **test dễ chập chờn (flaky)** khi 2 credential cùng đua — thay vì mặc định cứng người thắng, test đọc đúng 1 bản ghi thắng từ DB (`assert_eq!(winners.len(), 1)`).
    2. `.agents/skills/mt5-runtime-operations/SKILL.md` (`+22/-8`) và `references/rollout.md` (`+59/-5`): tài liệu vận hành tách biệt linked worktree (`--worktree-runtime-root`, `TW_AI_INTEGRATIONS_DISABLED=1`).
- **Hành động đề xuất:** **Cấm merge nguyên khối PR #32.** Nhặt riêng (`cherry-pick`) phần sửa test `automation_grants.rs` (và 2 file skill nếu muốn giữ hướng dẫn worktree) vào một PR nhỏ sạch sẽ, sau đó **đóng PR #32** (ghi chú `Superseded by #33`).

---

## 3. Lệnh Tham Khảo Cho Chủ Sở Hữu (Chỉ Chạy Khi Chủ Sở Hữu Duyệt)

```powershell
# Đóng PR #29 (chờ nâng Vite 8 đồng bộ)
gh pr close 29 -R Naqex/trader -c "@dependabot ignore this major version"

# Đóng PR #32 sau khi đã quyết định cherry-pick hoặc bỏ qua 3 tệp phụ
gh pr close 32 -R Naqex/trader -c "Superseded by #33 (14/19 files already on main; 2 legacy research notes contain local paths)."
```
