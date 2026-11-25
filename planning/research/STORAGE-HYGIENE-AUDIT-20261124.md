---
doc_type: audit
domain: workspace
topic: storage-hygiene-audit-20261124
updated_utc: 2026-11-23
status: READ_ONLY_AUDIT_PENDING_OWNER_APPROVAL
deletions_performed: 0
---

# Kiểm toán Vệ sinh Lưu trữ Chỉ Đọc (Storage Hygiene Audit — `2026-11-24`)

- **Chế độ thực thi:** **`100% READ-ONLY`** (`0` file bị xóa, `0` file bị di chuyển, `0` file bị chỉnh sửa trong các thư mục kiểm toán).
- **Trạng thái dung lượng đĩa hiện tại (đo trực tiếp `23/11/2026`):**
  - Ổ **`D:` (SSD làm việc):** còn trống **`151,03 GiB`**.
  - Ổ **`E:` (Kho lưu trữ lạnh `E:\BACKUP-TRADINGWORKSPACE\`):** đã tồn tại sẵn, còn trống **`505,15 GiB`**.
- **Tổng phát hiện trên `5` vùng trọng điểm:** **`16.681,71 MB` (`~16,29 GiB`) / `77.077` files**, trong đó **`16.641,09 MB` (`99,76%`) / `~76.601` files** là dữ liệu tạm/sandbox nhân bản/cài đặt cũ **không được Git theo dõi và không bị `tooling/` tham chiếu**, có thể chuyển an toàn sang `E:\BACKUP-TRADINGWORKSPACE\storage-hygiene-20261124\` sau khi owner phê duyệt vào buổi trưa!

---

## 1. Bảng Tổng hợp 5 Vùng Kiểm toán & Phân loại An toàn (Keep vs Archive)

| Vùng kiểm toán trên `D:\ANNAM\TradingWorkspace\` | Thực đo (`MB`) | Số file | Git-tracked | Tham chiếu từ `tooling/` | Phân loại & Phần cần GIỮ trên `D:` | Phần an toàn ARCHIVE sang `E:` (`MB`) |
|---|---:|---:|---:|---|---|---:|
| **1. `.runtime/ftmo-demo-full13-20261119`** | **`12.079,20`** (`11,80 GiB`) | `15.726` | `0` | `0` | **GIỮ** `36,90 MB` (`183` file: `native-deep-*`, `native-bars`, `native-staged-*`, `spread-london-smoke`, các biên nhận JSON/JSONL) | **`12.042,30 MB`** (`19` thư mục sandbox `owned-*`) |
| **2. `planning/trader/research/`** | **`3.142,07`** (`3,07 GiB`) | `31.678` | **`293`** | Có (`research_inventory.py`, lịch sử F5) | **BẮT BUỘC GIỮ** toàn bộ `293` file Git-tracked (`~3,72 MB`: `RESUME.md`, `STATE.json`, `RUN.json`, `artifacts/`, `work/`, `webgpt-native-v2/`, các `.py`) | **`3.138,35 MB`** (đúng `5` thư mục untracked: `pg-dist`, `f5-client-r2`, `.f5-venv`, `f5-fixtures`, `f5-fresh-r1`) |
| **3. `.artifacts/`** | **`848,14`** (`0,83 GiB`) | `23.255` | `0` | `0` | Không cần giữ nóng trên `D:` (`83` thư mục QA UI & cleanup từ tháng `10/2026`) | **`848,14 MB`** (toàn bộ `.artifacts/`) |
| **4. `tmp/`** | **`327,91`** (`0,32 GiB`) | `2.814` | `0` | `0` | Không cần giữ nóng trên `D:` (chủ yếu clone tham chiếu cũ `dubber-upstream` + `yt-dlp`) | **`327,91 MB`** (toàn bộ `tmp/`) |
| **5. `.tmp/`** | **`284,39`** (`0,28 GiB`) | `3.604` | `0` | `0` | Không cần giữ nóng trên `D:` (chủ yếu clone nguồn cũ `xerj-source` + `f5fresh`) | **`284,39 MB`** (toàn bộ `.tmp/`) |
| **TỔNG CỘNG** | **`16.681,71 MB`** | **`77.077`** | `293` | — | **Giữ lại tại chỗ: `~40,62 MB`** (chỉ dữ liệu sạch + Git-tracked) | **Giải phóng `D:`: `16.641,09 MB` (`16,25 GiB`)** |

---

## 2. Phân tích Chi tiết từng Thư mục (Top Thư mục con & Loại file)

### 2.1. `.runtime/ftmo-demo-full13-20261119` (`12.079,20 MB`, `15.726` files)
- **Nguyên nhân phình dung lượng:** Đợt chạy thu thập lịch sử sâu MT5 ngày `19/11/2026` đã sinh **`19` thư mục profile MT5 độc lập (`owned-*`)** — mỗi thư mục sao chép nguyên một bản cài `terminal64.exe` (`116,18 MB`) cùng cache lịch sử nhị phân `.hcc` của MT5!
- **Top thư mục con:**
  - `owned-history-deep-profile-0..11` (`12` thư mục): từ `425,79 MB` đến `902,26 MB`/thư mục → tổng **`9.729,55 MB`**.
  - `owned-history-profile-0..3` (`4` thư mục): `360,12–387,65 MB`/thư mục → tổng **`1.469,54 MB`**.
  - `owned-execution-profile` (`283,98 MB`), `owned-spread-profile` (`279,88 MB`), `owned-margin-profile` (`279,54 MB`) → tổng **`843,40 MB`**.
  - **Tổng `19` sandbox `owned-*`:** **`12.042,30 MB`** (`15.543` files).
  - **Phần dữ liệu kết quả sạch (giữ lại):** `native-deep-0..11` (`~29,7 MB`), `native-bars` (`2,90 MB`), `native-staged-0..3` (`2,85 MB`), `spread-london-smoke` (`0,03 MB`) và các file JSON/JSONL biên nhận → chỉ **`36,90 MB`** (`183` files)!
- **Phân bổ đuôi file chính:** `.hcc` (`6.289,33 MB` / `337` files), `.exe` (`4.718,30 MB` / `57` files), `.mqh` (`349,55 MB` / `4.750` files), không đuôi (`331,37 MB`), `.dll` (`171,38 MB`), `.ex5` (`74,86 MB`), trong khi `.parquet` thực chất chỉ **`36,30 MB`** (`79` files).
- **Đánh giá rủi ro:** **CỰC THẤP** nếu chỉ chuyển `owned-*` sang `E:` và giữ `36,90 MB` dữ liệu Parquet/JSON ở lại. Không có script hiện hành nào trong `tooling/` gọi tới `owned-*`.

### 2.2. `planning/trader/research/` (`3.142,07 MB`, `31.678` files)
- **CẢNH BÁO AN TOÀN GIT:** Thư mục có **`293` file đang Git-tracked** (`RESUME.md`, `STATE.json`, `RUN.json`, `artifacts/` `128` files, `work/` `16` files, `webgpt-native-v2/` `0,10 MB`). Tuyệt đối **KHÔNG** di chuyển thư mục gốc `planning/trader/research/` hay `20260921T115933Z-315e8ddd/` nguyên khối!
- **Top `5` thư mục con KHÔNG Git-tracked (`tracked_count = 0`) dưới `foundation-validation/20260921T115933Z-315e8ddd/`:**
  1. `pg-dist/` — **`1.703,67 MB`** (`20.433` files): chứa file cài `PostgreSQL 17_17.11-4...exe` (`391,94 MB`), `postgresql-17.11-4-windows-x64-binaries.zip` (`362,14 MB`), và toàn bộ `pgsql/pgAdmin 4` (`pgAdmin4.exe` `233,92 MB`).
  2. `f5-client-r2/` — **`782,66 MB`** (`1.694` files): chủ yếu là 2 trình duyệt Playwright Chromium (`chrome.dll` `287,17 MB`, `chrome-headless-shell.exe` `201,75 MB`).
  3. `.f5-venv/` — **`541,61 MB`** (`6.407` files): môi trường ảo Python cũ (chứa `nautilus_pyo3` `135,29 MB`, `engine.pyd` `78,33 MB`, `_duckdb.pyd` `35,64 MB`).
  4. `f5-fixtures/` — **`92,85 MB`** (`1.914` files): fixture chạy thử nghiệm cũ `21/09/2026`.
  5. `f5-fresh-r1/` — **`17,56 MB`** (`804` files): bản chạy thử `r1` cũ.
- **Phân bổ đuôi file chính:** `.exe` (`893,48 MB`), `.dll` (`549,33 MB`), `.pyd` (`408,18 MB`), `.zip` (`365,77 MB`), `.pak` (`173,99 MB`), `.json` (`107,12 MB`), `.py` (`106,73 MB`).
- **Đánh giá rủi ro:** **THẤP** khi chỉ di chuyển đúng `5` thư mục untracked nêu trên sang `E:`; `git status` giữ sạch `100%` và mọi checkpoint/evidence F5 (`STATE.json`, `RESUME.md`, `artifacts/`, `work/`) còn nguyên vẹn.

### 2.3. `tmp/` (`327,91 MB`, `2.814` files) + `.tmp/` (`284,39 MB`, `3.604` files) = `612,30 MB`
- **`tmp/`:**
  - `dubber-upstream/` (`304,22 MB`, `659` files): kho clone tham khảo cũ `audio-separator` (`.pack` `128,12 MB`, `.flac` `93,84 MB`) + `whisperX` (`pytorch_model.bin` `16,90 MB`). Không bị `tooling/` tham chiếu.
  - `yt-dlp/` (`20,59 MB`, `2.108` files): mã nguồn/cache tạm của `yt-dlp` (hiện đã cài chuẩn trong `.runtime/research-tools`).
  - Các thư mục nhỏ `story-*`, `r3b-qa-20260919`, `7` file root (`3,09 MB`).
- **`.tmp/`:**
  - `xerj-source/` (`278,15 MB`, `3.357` files): mã nguồn clone cũ của Xerj kèm dữ liệu feedback mẫu (`.jsonl` `84,39 MB`, `.pack` `66,52 MB`, `aise-demo.mp4` `14,02 MB`). Không bị `tooling/` tham chiếu.
  - `f5fresh-315e8ddd/` (`6,02 MB`, `226` files), `cleanup-docs/` (`0,10 MB`), `13` file root (`0,12 MB`).

### 2.4. `.artifacts/` (`848,14 MB`, `23.255` files, `83` thư mục con)
- **Ghi chú dung lượng:** Hiện lớn hơn mức ước tính cũ (`565 MB` → thực tế **`848,14 MB`**) và chứa tới **`23.255` file nhỏ** (làm chậm quét tìm kiếm toàn workspace).
- **Top thư mục con (toàn bộ từ đầu tháng `10/2026`):**
  - `workspace-cleanup-20261001/` (`392,05 MB`, `14.232` files — chứa `002a44fe.html` `53,02 MB` và `4` bản copy `node_modules/@esbuild/win32-x64/esbuild.exe` `11,15 MB` mỗi bản!).
  - `wm-all-plan-20261002/` (`208,90 MB`, `4.427` files — chứa `full-final.heapsnapshot` `38,36 MB` và `1` bản `esbuild.exe` nữa).
  - `wm-integration-20261002-resume/` (`32,34 MB`), `mt5-controls-20261003/` (`25,93 MB`), `wm-integration-quality-zoom-final/` (`24,20 MB`), `wm-integration-20261001/` (`22,69 MB`), cùng `77` thư mục QA UI tháng `10/2026` khác (`~142 MB`).
- **Phân bổ đuôi file chính:** `.js` (`206,72 MB` / `8.624` files), `.png` (`178,65 MB` / `3.732` files), không đuôi (`110,39 MB`), `.html` (`65,55 MB`), `.exe` (`55,76 MB`), `.map` (`47,17 MB`), `.zip` (`46,87 MB`), `.heapsnapshot` (`38,36 MB`).

---

## 3. Các Lệnh PowerShell 1 Dòng (Copy-Paste) Chờ Owner Duyệt Buổi Trưa

> **Nguyên tắc an toàn tuyệt đối trên Windows PowerShell 5.1:** Không dùng `Move-Item` cho thư mục xuyên ổ đĩa vì PowerShell 5.1 báo lỗi `IOException: Source and destination path must have identical roots` và kẹt đường dẫn dài `> 260` ký tự của `node_modules` trong `.artifacts/`. Toàn bộ lệnh dưới đây dùng **`robocopy <src> <dst> /E /MOVE /R:1 /W:1 /NFL /NDL`** của Windows — hỗ trợ chuyển xuyên ổ `D:` → `E:`, chịu được đường dẫn dài, **chỉ xóa nguồn sau khi đã sao chép xong đích trên `E:`**, và mã thoát `0–7` là thành công (`>= 8` mới là lỗi). Owner có thể chạy từng dòng độc lập theo thứ tự ưu tiên từ lớn nhất tới nhỏ nhất!

### Bước 0 — Tạo thư mục đích trên ổ `E:` (chạy 1 lần trước)
```powershell
New-Item -ItemType Directory -Force -Path 'E:\BACKUP-TRADINGWORKSPACE\storage-hygiene-20261124\ftmo-demo-full13-owned-profiles','E:\BACKUP-TRADINGWORKSPACE\storage-hygiene-20261124\foundation-validation-20260921-untracked','E:\BACKUP-TRADINGWORKSPACE\storage-hygiene-20261124\tmp-and-dottmp','E:\BACKUP-TRADINGWORKSPACE\storage-hygiene-20261124\dot-artifacts' | Out-Null
```

### Lệnh 1 — Thu hồi `12,04 GB` từ `19` sandbox MT5 `owned-*` (GIỮ nguyên `36,90 MB` Parquet/JSON sạch)
```powershell
Get-ChildItem -LiteralPath 'D:\ANNAM\TradingWorkspace\.runtime\ftmo-demo-full13-20261119' -Directory -Filter 'owned-*' | ForEach-Object { robocopy $_.FullName (Join-Path 'E:\BACKUP-TRADINGWORKSPACE\storage-hygiene-20261124\ftmo-demo-full13-owned-profiles' $_.Name) /E /MOVE /R:1 /W:1 /NFL /NDL }
```

### Lệnh 2 — Thu hồi `3,14 GB` từ đúng `5` thư mục untracked cũ dưới `foundation-validation` (GIỮ `100%` `293` file Git-tracked)
```powershell
'pg-dist','f5-client-r2','.f5-venv','f5-fixtures','f5-fresh-r1' | ForEach-Object { $s = Join-Path 'D:\ANNAM\TradingWorkspace\planning\trader\research\foundation-validation\20260921T115933Z-315e8ddd' $_; if (Test-Path -LiteralPath $s) { robocopy $s (Join-Path 'E:\BACKUP-TRADINGWORKSPACE\storage-hygiene-20261124\foundation-validation-20260921-untracked' $_) /E /MOVE /R:1 /W:1 /NFL /NDL } }
```

### Lệnh 3 — Thu hồi `848,14 MB` (`23.255` file QA cũ tháng `10/2026`, gồm đường dẫn dài `node_modules`) từ `.artifacts/`
```powershell
robocopy 'D:\ANNAM\TradingWorkspace\.artifacts' 'E:\BACKUP-TRADINGWORKSPACE\storage-hygiene-20261124\dot-artifacts' /E /MOVE /R:1 /W:1 /NFL /NDL
```

### Lệnh 4 — Thu hồi `612,30 MB` từ `tmp/` và `.tmp/`
```powershell
'tmp','.tmp' | ForEach-Object { $s = Join-Path 'D:\ANNAM\TradingWorkspace' $_; if (Test-Path -LiteralPath $s) { robocopy $s (Join-Path 'E:\BACKUP-TRADINGWORKSPACE\storage-hygiene-20261124\tmp-and-dottmp' $_) /E /MOVE /R:1 /W:1 /NFL /NDL } }
```

### Lệnh 5 (Tùy chọn sau khi chạy xong `1–4`) — Kiểm chứng Git sạch & dung lượng `D:` đã giải phóng
```powershell
git -C 'D:\ANNAM\TradingWorkspace' status --short; & 'D:\ANNAM\TradingWorkspace\.runtime\research-tools\Scripts\python.exe' -X utf8 'D:\ANNAM\TradingWorkspace\tooling\knowledge\brain_cli.py' audit-data
```

---

## 4. Xác nhận Bất biến An toàn của Đợt Kiểm toán này

- **Số file bị xóa/sửa/di chuyển bởi agent:** **`0`**.
- **Kho nóng quant quan trọng KHÔNG đụng vào:** `.runtime/hot-m1-cache/` (Dev `2018–2024`), `.runtime/holdout-m1-cache/` (Holdout `2025–2026`), `.runtime/quant-audit-v24/`, `.runtime/research-tools/`, `.runtime/knowledge/` — tất cả phải **GIỮ NGUYÊN** trên SSD `D:`.
