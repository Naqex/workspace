# Checklist Kích Hoạt FTMO Standard 10K — Black Friday (`Naqex_Master_Prop7E.ex5`)

> **Phạm vi:** Hướng dẫn 1 trang cho chủ sở hữu khi mua và kích hoạt tài khoản **FTMO Standard `10.000 USD`** (khuyến mãi Black Friday) bằng **`1` EA gộp duy nhất `Naqex_Master_Prop7E.ex5`** trên máy chủ `naqex-node1`.
> **Nguyên tắc an toàn (Fail-Closed):** Cả `4` file `.set` vòng đời đều mặc định khóa an toàn (`InpDryRunLogOnly = true`, `InpGuardDryRunLogOnly = true`, `InpGuardEnableRedNews = true`, `OrderSend = 0`). Nạp nhầm file sẽ **không thể** bắn lệnh thật cho tới khi bạn tự tay mở khóa trên đúng tài khoản trả phí.

---

## 1. Hạn chót mua gói & Cổng kiểm tra trước khi thanh toán

- **Hạn chót ưu đãi Black Friday FTMO:** **Thứ Hai `30/11/2026` lúc `16:00` giờ VN (`09:00 UTC`)**. Nên chốt quyết định muộn nhất trước `12:00` giờ VN để tránh nghẽn cổng thanh toán hoặc hết suất.
- **Chỉ bấm thanh toán khi cả `3` cổng đều XANH:**
  1. **Mũi 1–2 (Ma sát thực địa):** Kết quả đo trượt giá & spread thực tế trên `FTMO-Demo` nằm trong ngưỡng an toàn (`swap = 0,00 USD`).
  2. **Mũi 5 (Pháp lý & Giá checkout thật):** Đã có phản hồi email chính thức từ FTMO xác nhận dùng EA cá nhân không copy trùng tín hiệu bên thứ ba và xác nhận mức giá thực thu tại màn hình thanh toán (tính bằng `USD` / `EUR`).
  3. **Mũi 6 (Phán quyết cuối):** Đã duyệt xong hồ sơ Go/No-Go cuối tối `29/11/2026`.

---

## 2. Bảng chọn `4` bộ Preset vòng đời (`deployment_kit/presets/`)

Cả `4` file đều đã khóa tin đỏ `492` dòng (`naqex_red_news_utc.csv`, chặn `±300s`, cấm cứng `±135s`), reset ngày theo giờ Prague (`InpDailyResetMode = 1`), trần spread chuẩn từng nhóm (`FX 35,0` / `EURJPY 45,0` / `US100 450,0` điểm) và **khóa ARM-LOCKED (`DryRun = true`)**:

| Giai đoạn | File `.set` trong `deployment_kit/presets/` | Hệ số rủi ro | Profit Lock | Trần mềm Ngày / Tĩnh | Trần rủi ro Mã / Tổng mở | Khi nào dùng |
|---|---|---:|---|---|---|---|
| **P1 Cân bằng** | `FTMO_Std10K_MasterProp7E_P1_Balanced_3x.set` | **`3,00×`** | `>= +5,0%` -> `1,50×` | `3,00%` / `7,50%` | `1,50%` / `2,50%` | Khuyến nghị nếu ưu tiên êm sóng, đệm DD rộng hơn |
| **P1 Tăng tốc** | `FTMO_Std10K_MasterProp7E_P1_Sprint_4x.set` | **`4,00×`** | `>= +5,0%` -> `2,01×` | `3,50%` / `8,00%` | `1,75%` / `3,00%` | Đã kiểm chứng `Model=4` (`+7,55%`, `PF 1,24`, `Sharpe 2,02`, miễn nhiễm `150 ms`) |
| **P2 Xác minh** | `FTMO_Std10K_MasterProp7E_P2_Verify_2x.set` | **`2,00×`** | `>= +2,5%` -> `1,00×` | `2,50%` / `7,50%` | `1,25%` / `2,25%` | Sau khi qua P1 (`+10%`), mục tiêu P2 chỉ cần `+5%` |
| **Funded An toàn** | `FTMO_Std10K_MasterProp7E_Funded_Safe_1x.set` | **`1,00×`** | Tắt (`0,00%`) | `2,50%` / `7,50%` | `1,00%` / `2,00%` | Tài khoản Funded lĩnh lương dài hạn (giữ vốn tối đa) |

---

## 3. Triển khai sạch lên `naqex-node1` (chỉ khi phẳng lệnh `100%`)

> **QUY TẮC VÀNG:** Không đè hoặc tắt bộ `9` EA trên tài khoản Demo cũ khi đang có lệnh mở. Tài khoản Challenge trả phí nên chạy trong **thư mục MT5 portable riêng** trên `naqex-node1` (hoặc chỉ đồng bộ khi `open_positions = 0`, `total_account_positions = 0`).

1. **Kiểm tra chữ ký SHA-256 trên máy Dev trước khi đưa lên `naqex-node1`:**
   ```powershell
   .\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\exports\verify_deployment_kit.py --require-ex5
   ```
   Xác nhận đầu ra **`Deployment Kit Verify: PASS`** (`master_presets=4`, `ex5_sha=10`, `0` lỗi).
2. **Đồng bộ `.ex5` + lịch tin đỏ bằng script chặn phẳng lệnh (`-DryRun` trước, bỏ `-DryRun` sau):**
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\tooling\ai-engines\exports\deployment_kit\vps_kit\sync_updated_ex5_when_flat.ps1 `
     -TargetMt5Root "<DUONG_DAN_MT5_TREN_NODE1>" -IncludeMasterEx5 -RequireManifest -DryRun
   ```
   Script sẽ tự chối (`exit 2`) nếu heartbeat cũ `> 180s`, mất kết nối broker hoặc còn bất kỳ vị thế/lệnh chờ nào. Khi trạng thái sạch, chạy lại không có `-DryRun` và copy file `.set` đã chọn vào `<MT5>\MQL5\Presets\`.
3. **Gắn đúng `1` biểu đồ duy nhất trên tài khoản trả phí:**
   - Mở **Market Watch -> Show All**, kiểm tra hiện đủ `8` mã: `USDJPY`, `GBPUSD`, `EURJPY`, `US100.cash`, `US500.cash`, `EURUSD`, `AUDUSD`, `USDCAD`.
   - Mở **duy nhất `1` chart `USDJPY` khung `M5`** -> kéo thả `Naqex\Naqex_Master_Prop7E.ex5` -> tab **Inputs** -> bấm **Load** chọn file `.set` đúng giai đoạn (ví dụ `FTMO_Std10K_MasterProp7E_P1_Balanced_3x.set` hoặc `P1_Sprint_4x.set`).
   - **Tuyệt đối không gắn thêm `Naqex_AccountOrchestrator` hay `8` EA lẻ trên cùng tài khoản này** (`Naqex_Master_Prop7E` là đơn vị điều phối duy nhất).

---

## 4. Mở khóa `DryRun = false` (CHỈ trên tài khoản trả phí đã xác nhận)

1. Kiểm tra lại góc trên bên trái MT5: đúng **Số Login tài khoản FTMO trả phí mới mua** và đúng máy chủ FTMO cấp (tuyệt đối không nhầm với tài khoản Demo thử nghiệm hay sàn cá nhân).
2. Giữ chế độ khóa (`DryRun = true`) khoảng `5–10` phút đầu sau khi gắn chart để kiểm tra tab **Experts**:
   - Thấy dòng `[PROPGUARD-OK] Loaded 492 red-news events from 'naqex_red_news_utc.csv'`.
   - Thấy file `MQL5\Files\naqex_heartbeat.json` cập nhật mỗi `15` giây (`terminal_connected = true`, `orphan_no_sl = 0`, `kill_switch = false`).
   - Không có lỗi `INIT_FAILED`, không thiếu symbol.
3. Mở lại tab **Inputs** của `Naqex_Master_Prop7E` và **đổi đúng `2` dòng sau sang `false`**:
   - `InpDryRunLogOnly = false`
   - `InpGuardDryRunLogOnly = false`
   *(Kiểm tra `InpShadowCompareMode = false` và `InpWritePrimaryHeartbeat = true` đã sẵn sàng trong file `.set`.)*
4. Bấm **OK** và đảm bảo nút **Algo Trading** trên thanh công cụ chuyển xanh.

---

## 5. Kiểm tra Ngày 1 (`Day-1`) bằng `node_ctl.py` (chỉ đọc, `OrderSend = 0`)

Chạy từ máy Dev sau khi mở khóa `15` phút và cuối phiên Mỹ ngày đầu tiên:

```powershell
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\node_ctl.py status
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\node_ctl.py integrity
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\node_ctl.py audit
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\node_ctl.py logs --scope mql5 --days 1 --errors-only
```

- **Đạt chuẩn Day-1 khi:** `terminal_connected = true`, `dry_run = false`, `age_sec < 60`, `orphan_no_sl = 0`, `propguard_warn_count = 0`, `integrity` khớp SHA-256, `logs --errors-only` trống lỗi nghiêm trọng, và mọi lệnh trong `audit` đều có `SL` ngay lúc khớp với `swap = 0,00 USD`.

---

## 6. Quy trình Dừng Khẩn Cấp (Emergency Halt)

Kích hoạt ngay khi thấy bất kỳ dấu hiệu nào sau đây: trượt giá bất thường lặp lại, `orphan_no_sl > 0`, lỗi lịch tin đỏ, hoặc `daily_dd_pct` tiệm cận ngưỡng phanh mềm mà EA không tự ngắt:

1. **Ngắt quyền vào lệnh tức thì:** Vào MT5 trên `naqex-node1`, bấm tắt nút **Algo Trading** (chuyển sang đỏ) hoặc gỡ `Naqex_Master_Prop7E` khỏi chart `USDJPY M5`.
2. **Đóng phẳng toàn bộ vị thế & lệnh chờ:** Kiểm tra tab **Trade** -> đóng tay toàn bộ vị thế đang mở và hủy lệnh chờ (chú ý tránh thao tác trong vùng cấm tin đỏ `±2` phút của FTMO trừ khi khẩn cấp bảo vệ DD).
3. **Xác nhận phẳng lệnh & lưu bằng chứng:** Chạy `node_ctl.py status` và `node_ctl.py logs --scope mql5 --days 1` để lưu log gốc. **Không bật lại EA** cho tới khi xác định rõ nguyên nhân gốc và kiểm chứng lại ở chế độ `DryRun = true`.
