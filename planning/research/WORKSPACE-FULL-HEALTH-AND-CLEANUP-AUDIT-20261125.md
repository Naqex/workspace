---
doc_type: audit
domain: workspace
topic: workspace-full-health-and-cleanup-audit-20261125
updated_utc: 2026-11-25
status: READ_ONLY_AUDIT_PENDING_OWNER_APPROVAL
deletions_performed: 0
ordersend_count: 0
---

# Kiểm Toán Sức Khỏe Workspace, Giáo Dục, UI, Tích Hợp & Lưu Trữ (`25/11/2026`)

- **Chế độ:** **100% chỉ đọc** (`0` xóa/sửa trong `projects/*`, `UI-Systems/`, `UI/`, `education/`, `.runtime/`, `private_vault/`; `0` git ghi; `0` mở MT5; không mở `education/assessments/`).
- **Tổng quan:** `5/5` công cụ kiểm tra **ĐẠT (`exit 0`)**. Ổ `D:` trống **`159,94 GiB`** (`+8,91 GiB` so với `24/11` vì `.runtime/ftmo-demo-full13-20261119` `12,08 GiB` đã thu hồi); `E:` trống **`495,13 GiB`**. Sẵn sàng sao lưu lạnh **`4,58 GiB`** (Tầng 1), cộng **`17,97 GiB`** (Tầng 2) và **`108,20 GiB`** ở `projects/vi-dubber/work/` chờ duyệt.

---

## 1. Sức Khỏe Lõi & Nhất Quán `UI-Systems/` + `UI/`

| Công cụ (chỉ đọc) | Kết quả | Chi tiết đo (`25/11/2026`) |
|---|---|---|
| [check_workspace.py](../../tooling/check_workspace.py) | **ĐẠT** | `9` tài liệu hướng dẫn và `8` submodule ghim trong [.gitmodules](../../.gitmodules) hợp lệ. |
| [education/check_setup.py](../../education/check_setup.py) | **ĐẠT** | `4` mục đầu vào, `8` chặng, `24` bài/rubric, `56` lượt học hợp lệ (`0` lỗi → giữ `education/` chỉ đọc). |
| [check_skill_links.py](../../tooling/check_skill_links.py) | **ĐẠT** | `17` skill trong `.agents/skills`, `0` lỗi, `0` cảnh báo. |
| [ui-registry-check.mjs](../../tooling/ui-qa/ui-registry-check.mjs) | **ĐẠT** | `2` dự án (`trader`, `vi-dubber`), `3` bản ghim token, `0` lỗi lệch mã băm SHA-256. |
| [integrations/doctor.mjs](../../tooling/integrations/doctor.mjs) | **ĐẠT** | `4/4` nguồn tích hợp `source-ready`, khớp pin/origin/`LICENSE`, `0` file bẩn. |

- **Token & hợp đồng UI:** Cả `6` gói token DTCG (`annam-productivity@1.0.0`, `1.1.0`; `annam-compact@0.1.0..0.3.0`) đủ sáng/tối, **`0` biến thiếu** (`23`–`112` biến CSS/gói). Hai bản ghim [projects/trader/ui/project-ui.json](../../projects/trader/ui/project-ui.json) (`productivity@1.0.0` + `compact@0.3.0`) và [projects/vi-dubber/ui/project-ui.json](../../projects/vi-dubber/ui/project-ui.json) (`productivity@1.0.0`) khớp 100% mã băm và CSS xuất.
- **Ba điểm lệch nhẹ (không chặn chạy):**
  1. [ui-platform.json](../../UI-Systems/ui-platform.json) để `systemFamilies: []`, `defaultSystemFamily: null` và [domain-ui.json](../../UI/domain-ui.json) để `supportedSystemFamilies: []`, dù đã có `2` họ token đang dùng.
  2. `UI/` mới có [TRADING-UI-CONTRACT.md](../../UI/docs/TRADING-UI-CONTRACT.md); `4` thư mục `components/`, `data-visualization/`, `patterns/`, `tokens/` đang trống (đúng trạng thái `foundation`).
  3. Cả `4` manifest `annam-compact` (`0.1.0..0.3.0`) và [UI-Systems/README.md](../../UI-Systems/README.md) vẫn ghi tên cũ `WMREPLAY` và đường dẫn `projects/mt5-tradingview-backtester/.../RECEIPT.md`. Kiểm tra vẫn đỗ nhờ `projects/trader/ui/project-ui.json` đã ghi đè `focusedReceipt` sang `projects/trader/` (cả `4` file `RECEIPT.md` đã có ở `projects/trader/`). Không sửa manifest đóng băng nếu chưa muốn đổi SHA-256 đã ghim.

---

## 2. Trạng Thái `projects/integrations/` ([README](../../tooling/integrations/README.md) · [catalog.json](../../tooling/integrations/catalog.json))

| Tích hợp | Commit (`HEAD`) | Nhánh / Remote | Git | Dung lượng | Số file | Ghi chú |
|---|---|---|---|---:|---:|---|
| `paperclip` | `5501757` | `codex/naqex-integration` (Naqex + upstream) | Sạch | **`2,597 GiB`** | `121.797` | `node_modules` `2,313 GiB`; runtime ở `.runtime/paperclip/` (`0,334 GiB`). |
| `hermes-agent` | `bf0203a7` (`v0.22.5`) | Detached (NousResearch) | Sạch | `0,217 GiB` | `20.803` | Hồ sơ chạy riêng ở `.runtime/hermes/` (`0,524 GiB`). |
| `TradingAgents` | `ecaafe5` | `codex/integration-layout` (Naqex + upstream) | Sạch | `0,202 GiB` | `12.678` | `.venv` cục bộ `0,189 GiB` (`12.149` files). |
| `rd-agent` | `484776c2` (`v1.0.0`) | Detached (Microsoft) | Sạch | `0,011 GiB` | `921` | Chạy qua WSL2 `.runtime/linux/NaqexResearch/ext4.vhdx` (`6,703 GiB`). |
| **Tổng** | **4/4 khớp pin** | **4/4 khớp catalog** | **Sạch** | **`3,027 GiB`** | **`156.199`** | `100% source-ready`. |

- **Submodule sản phẩm khác (chỉ đọc):** `projects/trader` (`feat/typesafe-jev114-provider`, sạch, vượt pin), `projects/quant-trading` (`feat/causal-top15-sleeve2`, sạch, vượt pin), `projects/vi-dubber` (`main`, `5` file đang sửa dở), `tooling/reverse-skill` (`main`, sạch).

---

## 3. Dung Lượng Đĩa & Phân Loại Giữ / Lưu Trữ Lạnh (`D:` → `E:`)

- **Thực đo `25/11/2026`:** Tổng các thư mục gốc (bỏ qua junction) = **`212,347 GiB`** (`598.887` files); tổng `.venv` và `node_modules` toàn workspace = **`14,609 GiB`**. So với [STORAGE-HYGIENE-AUDIT-20261124.md](STORAGE-HYGIENE-AUDIT-20261124.md), `.runtime/ftmo-demo-full13-20261119` (`12,08 GiB`) đã thu hồi xong; `.artifacts/` giảm từ `848,1 MB` xuống `564,8 MB`.

| Thư mục nặng trên `D:` | `GiB` | Số file | Thành phần chính |
|---|---:|---:|---|
| `projects/vi-dubber` | **`129,058`** | `82.693` | `work/` (`108,20`), `models/` (`12,24`), `.venv/` (`8,09`) |
| `projects/mt5-tradingview-backtester` | **`41,740`** | `100.293` | `foundation_v2/.runtime/` (`30,02` + **junction về `E:`**), `api-rust/target` (`8,86`) |
| `.runtime` | **`17,708`** | `104.023` | `linux/` (`6,70`), `ftmo-demo-portable-1515343166` (`4,55`), `strategy-references` (`1,58`), `quant-audit-v24` (`0,80`), `hot-m1-cache` (`0,65`) |
| `projects/trader` | **`13,551`** | `45.893` | `api-rust/target` (`12,19`, riêng `debug/incremental` `6,19`), `engine_runtime/.venv` (`0,48`) |
| `planning` | **`3,231`** | `33.303` | `planning/trader/research/foundation-validation/20260921T115933Z-315e8ddd/` (`3,07`) |
| `projects/integrations` | **`3,027`** | `156.200` | `paperclip/node_modules` (`2,31`), `TradingAgents/.venv` (`0,19`) |
| `education` | **`1,212`** | `8.693` | `research/br01-screen/quality-data/` (`1,08`: `ftmo` `844 MB`, `histdata` `250 MB`), `real-example` (`90 MB`) |
| `.artifacts` + `tmp` + `.tmp` | **`1,150`** | `16.384` | `.artifacts/` (`564,8 MB`), `tmp/` (`327,9 MB`), `.tmp/` (`284,4 MB`) |
| `tooling` | **`1,096`** | `44.975` | `strategy-engines/` (`0,79`), `ui-qa/` (`0,16`, `artifacts/` `126 MB`), `chatgpt-web-core` (`0,11`) |

### Phân loại 3 tầng an toàn

1. **Tầng 1 — An toàn cao, sao lưu lạnh ngay sang `E:` (`4,581 GiB` · `0` file Git-tracked, `0` tham chiếu `tooling/`):**
   - `5` thư mục untracked dưới `planning/trader/research/foundation-validation/20260921T115933Z-315e8ddd/`: `pg-dist` (`1,664`), `f5-client-r2` (`0,764`), `.f5-venv` (`0,529`), `f5-fixtures` (`0,091`), `f5-fresh-r1` (`0,017`) → **`3,065 GiB`** (**GIỮ** `293` file Git-tracked: `STATE.json`, `RESUME.md`, `artifacts/`, `work/`).
   - `.artifacts/` (`0,552 GiB`), `tmp/` (`0,320 GiB`), `.tmp/` (`0,278 GiB`), `.runtime/chatgpt-core-upstream-20261019` + `.runtime/chatgpt-core-checkout-68f631d8` (`0,243 GiB`), `tooling/ui-qa/artifacts/` (`0,123 GiB`).
2. **Tầng 2 — Tiềm năng lớn, chờ chủ sở hữu chọn (`17,970 GiB` + riêng `vi-dubber/work` `108,201 GiB`):**
   - `projects/mt5-tradingview-backtester/foundation_v2/api-rust/target` (`8,858 GiB`, **chỉ đụng `target`, cấm đụng `.runtime/`**).
   - `projects/trader/foundation_v2/api-rust/target/debug/incremental` (`6,188 GiB`, tái tạo khi build, theo [WORKSPACE-MAINTENANCE.md](../../tooling/WORKSPACE-MAINTENANCE.md)).
   - `.runtime/strategy-references/` (`1,583 GiB`, `0` tham chiếu), `education/research/br01-screen/quality-data/{ftmo,histdata}` (`1,069 GiB`, `0` tracked; **GIỮ** `br01-engine/`, `qdm/`), `.runtime/ftmo-demo-portable-1515343318/` (`0,272 GiB`, `0` tham chiếu).
   - `projects/vi-dubber/work/` (`108,201 GiB`: `job-8dc51f8a892aba21` `52,77 GiB`, `benchmarks` `27,48 GiB`, `job-2b2f54da0f4a1f34` `8,22 GiB`) — chỉ chuyển job đã xong.
3. **Tầng 3 — BẮT BUỘC GIỮ trên `D:`:**
   - Lõi quant: `.runtime/hot-m1-cache/` (`0,645`), `.runtime/holdout-m1-cache/` (`0,116`, **niêm phong**), `.runtime/quant-audit-v24/`, `.runtime/research-tools/`, `.runtime/knowledge/`, `.runtime/swing-10k-20261120/` (`4` tham chiếu), `.runtime/mt5-compiled-ex5/`, `.runtime/mt5-realtick-results/`.
   - Hạ tầng sống: `.runtime/ftmo-demo-portable-1515343166/` (`4,55`), `.runtime/linux/NaqexResearch/ext4.vhdx` (`6,70`, dùng `25/11`), `.runtime/paperclip/`, `.runtime/hermes/`, `projects/vi-dubber/models/` (`12,24`), các `.venv`/`node_modules` hoạt động.
   - **CẢNH BÁO JUNCTION:** `projects/mt5-tradingview-backtester/foundation_v2/.runtime/` chứa nhiều **Windows Junction trỏ về `E:`** và chứa `quantdatamanager/` (`24,01 GiB`) còn bị `prop_v5_data.py` và `prop_v6_data.py` tham chiếu → cấm xóa/di chuyển.

---

## 4. Tiến Độ Khóa Học Trading (`education/`, Không Mở Đáp Án)

Đọc từ [course.json](../../education/course.json), [COURSE.md](../../education/COURSE.md), [progress.json](../../education/progress.json):

- **Trạng thái:** Khóa *Forex từ nền tảng đến thực hành có kiểm chứng* v1.1 (`8` chặng, `24` bài). Đánh giá đầu vào đã đóng (`07/09/2026`); đang ở `main_course` (`in_progress`) với **`56` lượt học** và **`15` sản phẩm** (`M01-DEMO-01`..`M08-L01-OBS01`). Đã đi qua khung `24/24` chủ đề tới `M08-L03`, nhưng hoàn tất chính thức **`4/24` bài** (`M01-L03`, `M02-L01`, `M02-L02`, `M04-L01`) và **`0/8` chặng**. (Trường `updated_on` ở đầu file còn ghi `2026-09-13`, trong khi mục `br01_*` mới nhất ghi `16/09/2026`.)
- **Năng lực (`19` mục):** **`11` độc lập** (phần trăm, phí/P/L ròng, pip/lot/unit, cỡ lệnh SL, trạng thái tài khoản, rủi ro tích hợp), **`2` có hỗ trợ** (`probability`, `buy_position_pnl`), **`1` cần luyện thêm** (`leverage_margin_vs_pnl`), **`5` chưa đánh giá** (`chart_reading`, `forex_order_mechanics`, `risk_plan`, `english_*`); `9` mục chờ ôn nhắc (`review_queue`).
- **Bước học tiếp theo sẵn sàng (không lặp toán cơ bản, không đặt lệnh):**
  1. Tiếp tục [BR-01 v0](../../education/practice/eurusd-breakout-retest-v0.md) ở ca **`BR-01-APPLY-02`** (luật hết hạn `6` nến sau breakout không chạm vùng) và minh họa khoảng TP bằng `2` lần Entry–SL.
  2. Hoặc hoàn thiện sản phẩm chặng còn mở: ghi chú biểu đồ thật `M04-L02/L03`, phần thực hành `M05/M06` từng hoãn, hoặc đối chiếu pháp lý/thuế/hợp đồng Việt Nam ở `M07-L03`. Ngân sách `1 triệu VND` giữ ở mức kế hoạch.

---

## 5. Lệnh PowerShell Sao Lưu Lạnh An Toàn (Copy-Paste, `0` Tự Động Xóa)

> Toàn bộ lệnh dùng **`/E /XJ /COPY:DAT`** (chỉ **sao chép** sang `E:`, **không xóa trên `D:`**, bỏ qua junction nhờ `/XJ`). Mã thoát `0`–`7` là thành công. Khi đã kiểm đủ trên `E:`, tự đổi `/COPY:DAT` thành `/MOVE` ở dòng muốn giải phóng `D:`.

```powershell
# Bước 0: vào gốc workspace và tạo thư mục đích trên E:
Set-Location 'D:\ANNAM\TradingWorkspace'
New-Item -ItemType Directory -Force -Path 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\fv','E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\dot-artifacts','E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\tmp','E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\dot-tmp','E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\chatgpt-old','E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\ui-qa-artifacts' | Out-Null

# Tầng 1A: 5 thư mục untracked dưới foundation-validation (3,065 GiB; giữ 293 file tracked)
robocopy 'planning\trader\research\foundation-validation\20260921T115933Z-315e8ddd\pg-dist' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\fv\pg-dist' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy 'planning\trader\research\foundation-validation\20260921T115933Z-315e8ddd\f5-client-r2' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\fv\f5-client-r2' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy 'planning\trader\research\foundation-validation\20260921T115933Z-315e8ddd\.f5-venv' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\fv\.f5-venv' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy 'planning\trader\research\foundation-validation\20260921T115933Z-315e8ddd\f5-fixtures' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\fv\f5-fixtures' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy 'planning\trader\research\foundation-validation\20260921T115933Z-315e8ddd\f5-fresh-r1' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\fv\f5-fresh-r1' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL

# Tầng 1B: .artifacts (564,8 MB), tmp (327,9 MB), .tmp (284,4 MB), chatgpt-core cũ (248,5 MB), ui-qa/artifacts (126,4 MB)
robocopy '.artifacts' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\dot-artifacts' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy 'tmp' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\tmp' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy '.tmp' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\dot-tmp' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy '.runtime\chatgpt-core-upstream-20261019' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\chatgpt-old\upstream' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy '.runtime\chatgpt-core-checkout-68f631d8' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\chatgpt-old\checkout' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy 'tooling\ui-qa\artifacts' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\ui-qa-artifacts' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL

# Tầng 2 (tùy chọn): tham khảo & tick cũ (2,92 GiB)
robocopy '.runtime\strategy-references' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\t2-strategy-refs' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy 'education\research\br01-screen\quality-data\ftmo' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\t2-edu-raw\ftmo' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy 'education\research\br01-screen\quality-data\histdata' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\t2-edu-raw\histdata' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy '.runtime\ftmo-demo-portable-1515343318' 'E:\BACKUP-TRADINGWORKSPACE\hygiene-20261125\t2-ftmo-1515343318' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL

# Kiểm chứng lại (chỉ đọc)
git status --short
& '.runtime\quant-audit-v24\Scripts\python.exe' 'tooling\check_workspace.py'
& '.runtime\quant-audit-v24\Scripts\python.exe' 'education\check_setup.py'
node 'tooling\integrations\doctor.mjs'
node 'tooling\ui-qa\ui-registry-check.mjs' --json
```
