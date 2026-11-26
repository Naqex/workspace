---
doc_type: storage-decision
domain: workspace
topic: tier-c-storage-decision-20261127
updated_utc: 2026-11-27
status: PENDING_OWNER_DECISION
deletions_performed: 0
tier: C
---

# Quyết Định Dọn Dẹp Lưu Trữ Tầng C (`2026-11-27`) — ~51,94 GiB (`53.186 MiB` / `55,77 GB`)

> **Trạng thái:** **CHƯA XÓA BẤT KỲ MỤC NÀO TRONG TẦNG C (`0` byte bị đụng).**
> Toàn bộ 6 hạng mục dưới đây đều có liên kết hệ thống (Windows Junction sang `E:`, WSL2 VHDX, hoặc chứa file Git-tracked) nên **bắt buộc có quyết định trực tiếp của chủ sở hữu** và **chỉ chạy đúng lệnh an toàn bên dưới** (tuyệt đối không xóa bằng `Remove-Item -Recurse` thuần trên PowerShell 5.1).

---

## 1. Bảng Tổng Hợp 6 Hạng Mục Tầng C (Đo Trực Tiếp Không Đi Qua Junction)

| # | Đường dẫn trên `D:\ANNAM\TradingWorkspace\` | Dung lượng thật trên `D:` | Số file | Git-tracked | Junction nội bộ | Mức rủi ro & Ghi chú chính |
|---|---|---:|---:|---:|---:|---|
| **1** | `projects/mt5-tradingview-backtester/` | **`41,75 GiB`** (`42.749,17 MiB`) | `100.666` | `0` | **`145`** (trỏ sang `E:`) | **RẤT CAO nếu xóa nguyên thư mục.** Chứa `foundation_v2/.runtime/` (`30,02 GiB`, **`130` junction** + `quantdatamanager/` bị `prop_v5_data.py`/`prop_v6_data.py` tham chiếu). Phần dễ thu hồi an toàn nhất là `foundation_v2/api-rust/target/` (`8,86 GiB`, `10` junction). |
| **2** | `.runtime/linux/` | **`6,72 GiB`** (`6.883,50 MiB`) | `37` | `0` | `0` | **CAO nếu xóa thẳng file.** Chứa đĩa ảo WSL2 `NaqexResearch\ext4.vhdx` (`6,72 GiB`, trạng thái `Stopped`, WSL v2, dùng cho `RD-Agent`/Docker pilot ngày `26/11`). **BẮT BUỘC chạy `wsl --unregister NaqexResearch` trước khi xóa thư mục!** |
| **3** | `.runtime/strategy-references/` | **`1,58 GiB`** (`1.621,45 MiB`) | `14.681` | `0` | `0` | **THẤP.** Kho mã nguồn/tài liệu tham khảo cũ, `0` file Git-tracked, `0` tham chiếu trong `tooling/`. An toàn chuyển lạnh sang `E:` hoặc xóa sau khi đối chiếu. |
| **4** | `education/research/br01-screen/` | **`1,08 GiB`** (`1.104,23 MiB`) | `6.696` | **`61`** | `0` | **CAO nếu xóa nguyên thư mục (sẽ mất `61` file Git-tracked!).** `99,1%` dung lượng (`1.094,36 MiB`) nằm ở đúng `2` thư mục tick thô **untracked**: `quality-data/ftmo/` (`844,15 MiB`) và `quality-data/histdata/` (`250,21 MiB`). **GIỮ NGUYÊN** toàn bộ script `.py`/`.md` và `quality-data/br01-engine/`. |
| **5** | `tooling/strategy-engines/*/.venv` (`4` venv) | **`0,79 GiB`** (`811,70 MiB`) | `29.266` | `0` | `0` | **RẤT THẤP.** `4` môi trường ảo Python tách biệt (`vectorbt` `477,39 MiB`, `observer` `131,86 MiB`, `backtesting` `125,92 MiB`, `backtrader` `76,53 MiB`). Dễ cài lại khi cần; các gói copyleft/Commons-Clause bị cấm import vào lõi Naqex. |
| **6** | `projects/app.fxreplay.com.zip` | **`0,02 GiB`** (`16,00 MiB`) | `1` | `0` | `0` | **RẤT THẤP.** Gói nén tham khảo giao diện cũ (`16.773.098 B`), `0` file Git-tracked. |
| | **TỔNG TẦNG C (`6` mục)** | **`51,94 GiB`** (`53.186,05 MiB` / `55,77 GB`) | **`151.347`** | **`61`** | **`145`** | Khuyến nghị thực hiện theo **3 đợt từ thấp đến cao rủi ro** ở Mục 3. |

---

## 2. Phân Tích Rủi Ro Bắt Buộc Đọc Trước Khi Chạy Lệnh

1. **Cảnh báo Junction (`projects/mt5-tradingview-backtester/`):**
   - Trong `projects/mt5-tradingview-backtester/` có **`145` Windows Junction** (riêng `foundation_v2/.runtime/` có `130` junction và `foundation_v2/api-rust/target/` có `10` junction) trỏ trực tiếp sang ổ `E:\BACKUP-TRADINGWORKSPACE\...`.
   - **Tuyệt đối KHÔNG chạy `Remove-Item -Recurse -Force` của Windows PowerShell 5.1** lên thư mục có junction vì PowerShell 5.1 có thể chui qua junction và **xóa nhầm dữ liệu sao lưu trên ổ `E:`**.
   - Ngoài ra `projects/mt5-tradingview-backtester/foundation_v2/.runtime/quantdatamanager/` (`~24 GiB`) còn được tham chiếu bởi `prop_v5_data.py` và `prop_v6_data.py`. Trước khi dời hoặc xóa nguyên thư mục cũ này, cần xác nhận không còn chạy các script legacy đó hoặc cập nhật đường dẫn dữ liệu sang `E:`.
2. **Cảnh báo WSL2 (`.runtime/linux/` — `6,72 GiB` / `6.883,50 MiB`):**
   - Thư mục `.runtime/linux/NaqexResearch/ext4.vhdx` đang được Windows WSL2 đăng ký làm distro mặc định **`NaqexResearch`** (`Version 2`).
   - Nếu xóa trực tiếp file `ext4.vhdx` mà chưa gỡ đăng ký, WSL registry sẽ bị lỗi hỏng distro mồ côi. **Bắt buộc** xuất bản sao lưu (nếu muốn giữ) bằng `wsl --export`, sau đó chạy `wsl --shutdown` và **`wsl --unregister NaqexResearch`** rồi mới xóa `.runtime/linux/`.
3. **Cảnh báo Git-Tracked (`education/research/br01-screen/`):**
   - Có **`61` file Git-tracked** nằm ngay trong `education/research/br01-screen/` (kể cả `quality-data/br01-engine/`). Chỉ được phép chuyển/xóa đúng `2` thư mục dữ liệu tick thô untracked là `quality-data\ftmo` (`844,15 MiB`) và `quality-data\histdata` (`250,21 MiB`).

---

## 3. Lệnh PowerShell An Toàn Sẵn Sàng Chạy (Chủ Sở Hữu Chọn Từng Mục)

> **Quy tắc chung:** Mọi lệnh sao lưu sang `E:` dùng `robocopy ... /E /XJ /COPY:DAT` (`/XJ` = bỏ qua junction, không làm hỏng dữ liệu trên `E:`, **chỉ chép, chưa xóa**). Mọi lệnh xóa thư mục có junction dùng Python `os.scandir(..., follow_symlinks=False)` hoặc `cmd /c rmdir` để chỉ gỡ con trỏ junction mà không bao giờ đụng vào đích trên `E:`.

### Bước 0 — Tạo thư mục lưu trữ lạnh trên ổ `E:` (nếu muốn sao lưu trước khi xóa)

```powershell
Set-Location 'D:\ANNAM\TradingWorkspace'
New-Item -ItemType Directory -Force -Path 'E:\BACKUP-TRADINGWORKSPACE\tier-c-20261127' | Out-Null
```

---

### Đợt 1 — Rủi ro thấp nhất (Thu hồi ngay **`~3,46 GiB` / `3.543,51 MiB`**, `0` rủi ro Git/WSL/Junction)

#### 1A. Xóa 4 `.venv` engine bên thứ ba (`811,70 MiB`, tái tạo được bất cứ lúc nào)
```powershell
'backtesting','backtrader','observer','vectorbt' | ForEach-Object {
  $v = Join-Path 'D:\ANNAM\TradingWorkspace\tooling\strategy-engines' "$_\.venv"
  if (Test-Path -LiteralPath $v) { cmd /c rmdir /s /q "$v" }
}
```

#### 1B. Chuyển lạnh `.runtime/strategy-references/` (`1.621,45 MiB`) sang `E:`
```powershell
# Bước 1: Sao chép sang E: (chưa xóa trên D:)
robocopy 'D:\ANNAM\TradingWorkspace\.runtime\strategy-references' 'E:\BACKUP-TRADINGWORKSPACE\tier-c-20261127\strategy-references' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
# Bước 2 (chỉ chạy sau khi kiểm tra đích trên E: đủ file): Xóa bản trên D:
# cmd /c rmdir /s /q 'D:\ANNAM\TradingWorkspace\.runtime\strategy-references'
```

#### 1C. Chuyển lạnh CHỈ 2 thư mục tick thô untracked trong `education/research/br01-screen/` (`1.094,36 MiB`, GIỮ 100% `61` file Git-tracked)
```powershell
# Bước 1: Sao chép sang E: (chưa xóa trên D:)
robocopy 'D:\ANNAM\TradingWorkspace\education\research\br01-screen\quality-data\ftmo' 'E:\BACKUP-TRADINGWORKSPACE\tier-c-20261127\br01-quality-data\ftmo' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
robocopy 'D:\ANNAM\TradingWorkspace\education\research\br01-screen\quality-data\histdata' 'E:\BACKUP-TRADINGWORKSPACE\tier-c-20261127\br01-quality-data\histdata' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
# Bước 2 (chỉ chạy sau khi kiểm tra đích trên E: đủ file): Xóa đúng 2 thư mục untracked này
# cmd /c rmdir /s /q 'D:\ANNAM\TradingWorkspace\education\research\br01-screen\quality-data\ftmo'
# cmd /c rmdir /s /q 'D:\ANNAM\TradingWorkspace\education\research\br01-screen\quality-data\histdata'
```

#### 1D. Chuyển lạnh hoặc xóa `projects/app.fxreplay.com.zip` (`16,00 MiB`)
```powershell
Copy-Item -LiteralPath 'D:\ANNAM\TradingWorkspace\projects\app.fxreplay.com.zip' -Destination 'E:\BACKUP-TRADINGWORKSPACE\tier-c-20261127\app.fxreplay.com.zip'
# Sau khi kiểm tra bản trên E:, xóa trên D::
# Remove-Item -LiteralPath 'D:\ANNAM\TradingWorkspace\projects\app.fxreplay.com.zip'
```

---

### Đợt 2 — Rủi ro trung bình: `.runtime/linux/` (`6,72 GiB` / `6.883,50 MiB` — WSL2 `NaqexResearch`)

> **CẢNH BÁO BẮT BUỘC:** Phải chạy `wsl --unregister NaqexResearch` **TRƯỚC** khi xóa `.runtime/linux/`. Chỉ chạy nếu hiện tại bạn không cần dùng `RD-Agent` trên WSL2.

```powershell
# 1. Tắt WSL2 sạch trước khi xuất/gỡ
wsl --shutdown
wsl --list --verbose

# 2. (Khuyến nghị) Sao lưu toàn bộ distro ra file .tar trên ổ E: để có thể `wsl --import` lại sau
wsl --export NaqexResearch 'E:\BACKUP-TRADINGWORKSPACE\tier-c-20261127\NaqexResearch.tar'

# 3. Gỡ đăng ký distro khỏi Windows WSL registry (BẮT BUỘC trước khi xóa thư mục!)
wsl --unregister NaqexResearch

# 4. Kiểm tra NaqexResearch không còn trong danh sách, rồi mới xóa .runtime\linux
wsl --list --verbose
# cmd /c rmdir /s /q 'D:\ANNAM\TradingWorkspace\.runtime\linux'
```

---

### Đợt 3 — Rủi ro cao nhất: `projects/mt5-tradingview-backtester/` (`41,75 GiB` / `42.749,17 MiB`, `145` Junctions)

#### Tùy chọn 3A (An toàn cao — Thu hồi ngay `8,86 GiB` / `9.070,10 MiB` Rust build cache, KHÔNG đụng `.runtime/`)
`foundation_v2/api-rust/target/` chứa `10` junction nội bộ và có thể biên dịch lại hoàn toàn nếu cần. Dùng đoạn Python an toàn dưới đây để gỡ con trỏ junction trước rồi mới xóa file trên `D:` (tuyệt đối không đi qua junction):

```powershell
& 'D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe' -c "
import os, stat, pathlib
def safe_rmtree(p):
    s = str(p)
    lp = s if s.startswith('\\\\?\\') else '\\\\?\\' + os.path.abspath(s)
    st = os.lstat(lp)
    if bool(getattr(st, 'st_reparse_tag', 0)) or stat.S_ISLNK(st.st_mode):
        os.rmdir(lp) if stat.S_ISDIR(st.st_mode) else os.unlink(lp); return
    if not stat.S_ISDIR(st.st_mode):
        os.chmod(lp, stat.S_IWRITE | stat.S_IREAD); os.unlink(lp); return
    for e in list(os.scandir(lp)):
        safe_rmtree(os.path.join(lp, e.name))
    os.chmod(lp, stat.S_IWRITE | stat.S_IREAD)
    os.rmdir(lp)
target = pathlib.Path(r'D:\ANNAM\TradingWorkspace\projects\mt5-tradingview-backtester\foundation_v2\api-rust\target')
if target.exists():
    safe_rmtree(target)
    print('DONE: removed api-rust/target safely without following junctions')
"
```

#### Tùy chọn 3B (Thu hồi toàn bộ `41,75 GiB` — CHỈ chạy khi đã dứt điểm không cần `quantdatamanager/` & legacy repo)
1. Kiểm tra trước xem còn script nào đang đọc `projects/mt5-tradingview-backtester`:
   ```powershell
   git -C 'D:\ANNAM\TradingWorkspace' grep -n 'mt5-tradingview-backtester' -- 'tooling/' 'projects/'
   ```
2. Sao lưu lạnh phần dữ liệu thật trên `D:` sang `E:` **với cờ `/XJ`** (bỏ qua toàn bộ `145` junction):
   ```powershell
   robocopy 'D:\ANNAM\TradingWorkspace\projects\mt5-tradingview-backtester' 'E:\BACKUP-TRADINGWORKSPACE\tier-c-20261127\mt5-tradingview-backtester' /E /XJ /COPY:DAT /R:1 /W:1 /NFL /NDL
   ```
3. Chỉ sau khi xác nhận bản sao trên `E:` đầy đủ và không còn phụ thuộc `prop_v5_data.py`/`prop_v6_data.py`, dùng hàm Python `safe_rmtree` (như Tùy chọn 3A, đổi `target` sang `D:\ANNAM\TradingWorkspace\projects\mt5-tradingview-backtester`) để gỡ bỏ an toàn trên `D:` mà **không bao giờ xóa dữ liệu đích trên `E:`**.

---

## 4. Lệnh Kiểm Chứng Sau Khi Thực Hiện Bất Kỳ Đợt Nào

```powershell
Set-Location 'D:\ANNAM\TradingWorkspace'
git status --short
& '.runtime\quant-audit-v24\Scripts\python.exe' 'tooling\check_workspace.py'
& '.runtime\quant-audit-v24\Scripts\python.exe' 'education\check_setup.py'
Get-PSDrive D | Select-Object Name, @{n='Free_GiB';e={[math]::Round($_.Free/1GB,2)}}, @{n='Used_GiB';e={[math]::Round($_.Used/1GB,2)}}
```
