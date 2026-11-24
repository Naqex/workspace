---
doc_type: audit
domain: live-operations
status: active
captured_utc: "2026-11-24T11:03:02Z"
updated_utc: 2026-11-24
order_send_count: 0
holdout_rows_analysed: 0
sources:
  - "planning/TOP1-SOLO-QUANT-MASTER-PLAN.md"
  - ".agents/skills/naqex-node-ops/SKILL.md"
  - "knowledge/playbooks/ftmo-the5ers-live-launch-sop.md"
  - "tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md"
---

# Báo Cáo Kiểm Toán Trực Tiếp `naqex-node1` & Dữ Liệu Shadow (`2026-11-24`)

> **Phương pháp kiểm tra:** Đọc trực tiếp 100% **chỉ đọc (read-only)** qua mạng nội bộ LAN tới `naqex-node1` lúc **`2026-11-24 11:01–11:03 UTC` (`18:01–18:03` giờ Việt Nam)**. Không khởi động lại MT5, không sửa tệp hay tác vụ nào trên máy chủ, không ghi nhận hay in bất kỳ khóa API/mật khẩu/đường dẫn bí mật nào (`OrderSend = 0`, dữ liệu mật `Holdout 2025+` giữ niêm phong tuyệt đối).

---

## 1. Tóm Tắt Nhanh — Điểm Sẵn Sàng Cổng `Mốc 0`

Hệ thống hạ tầng `naqex-node1` + trạm giám sát mây Heroku EU + bộ gom dữ liệu Crypto đang chạy **ổn định 24/7 với `0` lỗi vận hành**, và **Windows Defender đã được bật lại sạch sẽ** với đúng 1 ngoại lệ thư mục `C:\Naqex`. Tuy nhiên hệ thống vẫn đang ở **Ngày 1/14 của vòng kiểm chứng Free Trial** nên cổng chuyển sang mua vé trả phí giữ cứng trạng thái **`HOLD_IN_MOC0` (chưa mở mua vé thật)**.

| Hạng mục Cổng `Mốc 0` | Ngưỡng Đạt (`Exit Gate`) | Thực đo trực tiếp (`2026-11-24 11:03 UTC`) | Trạng thái |
|---|---|---|---|
| **1. Hạ tầng `naqex-node1` + Heroku EU + NTP + Sao lưu `D:`** | Nhịp tim `< 120s`, NTP `< 1s`, `C:` trống `> 20 GB`, sao lưu ngày | Nhịp tim `9s` (`Heroku OK`), NTP lệch `< 0,1s` (`time.google.com`), `C:` trống `103,88 GB`, có bản sao lưu `20261124` | **ĐẠT (`PASS`)** |
| **2. Bảo mật Windows Defender & Tường lửa** | Defender BẬT thời gian thực, chỉ ngoại lệ `C:\Naqex`, Firewall BẬT | `RealTimeProtectionEnabled = True`, `Exclusions = C:\Naqex`, Firewall `3/3` hồ sơ BẬT | **ĐẠT (`PASS`)** |
| **3. Vòng Free Trial `14` ngày (`FTMO-Demo 1515343166`)** | `10–15` lệnh đóng khớp MetriX, `0` orphan, `0` swap, trượt giá `<= 1,5×` | **`0` lệnh đóng / `1` lệnh đang mở** (`E1_USDJPY_TOKYO`, lãi nổi `+7,52 USD`, `orphan_no_sl = 0`) — Ngày 1/14 | **ĐANG CHẠY (`IN_PROGRESS`)** |
| **4. Đồng bộ 4 bản vá Cycle 1 lên `naqex-node1`** | `9/9 .ex5` bản vá mới + lịch tin đỏ `418` dòng 4 đồng tiền | Đã biên dịch & kiểm định xong trên máy dev; `naqex-node1` đang mở `1` vị thế nên **chờ phẳng (`open_positions == 0`) mới chép** | **CHỜ PHẲNG (`PENDING_FLAT_SYNC`)** |
| **5. Thư xác nhận văn bản FTMO & The5ers (`Terms §11`)** | Có email phản hồi chấp thuận EA độc quyền từ cả 2 quỹ | Đã soạn sẵn bộ email copy-paste tại [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md) | **CHỜ CHỦ SỞ HỮU GỬI** |
| **6. Diễn tập mất kết nối `3` phút (`@naqex_guard_bot`)** | Điện thoại nhận đúng tin nhắn đỏ `🔴 MẤT KẾT NỐI` | Chưa ghi nhận biên bản diễn tập — chỉ làm khi `open_positions == 0` (sau `21:00 UTC` hoặc cuối tuần) | **CHỜ DIỄN TẬP** |
| **7. Cổng `30` ngày Crypto Maker (`M2B`)** | Đủ `30` ngày dữ liệu thật, khớp `>= 70%`, chi phí `<= 6,15 bps` | Đã gom **`0,70 / 30,00` ngày (`197` chu kỳ)**, còn **`~29,31` ngày**; sơ bộ `15m` rất tốt (`97,44%` khớp / `3,081 bps`) | **ĐANG GOM (`2,3%`)** |

---

## 2. Kiểm Toán Chi Tiết `FTMO-Demo 1515343166` & Hệ Điều Hành `naqex-node1`

### 2.1. Trạng thái MT5 & Vị thế Thực Chiến
- **Tiến trình MT5:** `terminal64.exe` (`PID 6552`) khởi chạy liên tục trên `naqex-node1` từ `2026-11-24T08:54:55Z` (`15:54:55` giờ Việt Nam), tiêu thụ bộ nhớ gọn `15,3 MB`.
- **Nhịp tim trực tiếp (`C:\Naqex\mt5\MQL5\Files\naqex_heartbeat.json`, cập nhật lúc `11:00:58Z`, độ tuổi `9` giây):**
  - Số dư (`balance`): **`9.999,82 USD`** · Tài sản ròng (`equity`): **`10.007,34 USD`** (lãi thả nổi **`+7,52 USD`**) · Mốc đầu ngày (`day_anchor_eq`): **`10.009,97 USD`**.
  - Sụt giảm ngày (`daily_dd_pct`): **`0,026%`** · Sụt giảm tổng (`static_dd_pct`): **`0,000%`** · Chế độ (`regime`): **`NORMAL`** (`risk_mult = 1,000`).
  - Công tắc khẩn (`kill_switch`): **`false`** · Vị thế đang mở (`open_positions`): **`1`** · Vị thế mồ côi thiếu cắt lỗ (`orphan_no_sl`): **`0`** · Chế độ chạy thử không gửi lệnh (`dry_run`): **`false`**.
- **Truy vết lệnh mở thực tế (`naqex_exec_audit.csv`):**
  - Trên `naqex-node1` chưa có lệnh mới kể từ lúc chuyển máy lúc `08:54:55Z` (`C:\Naqex\mt5\MQL5\Files\naqex_exec_audit.csv` chưa phát sinh dòng mới).
  - Đối chiếu bản ghi trước giờ chuyển máy trên PC dev (`.runtime/ftmo-demo-portable-1515343166/MQL5/Files/naqex_exec_audit.csv`) ghi nhận đúng **1 lệnh vào thực tế**:
    - Thời điểm: **`2026-11-24 05:17:54 UTC`** (`12:17:54` giờ Việt Nam).
    - Bot & sản phẩm: **`E1_USDJPY_TOKYO`** (`magic 20261122`), **`BUY USDJPY 0,07` lot**, giá tín hiệu **`159,096`**, cắt lỗ cứng trên sàn **`158,753`** (`34,3` pip), spread lúc khớp **`11,0` điểm (`1,1` pip)**, độ trễ **`556,87 ms`**, mã trả về **`10009` (`TRADE_RETCODE_DONE`)**.
    - Phần chênh lệch số dư `-0,18 USD` (`9.999,82 - 10.000,00 USD`) là phí hoa hồng mở lệnh của `0,07` lot `USDJPY`; vị thế đang có SL cứng (`orphan_no_sl = 0`), chưa có phí qua đêm (`swap = 0 USD`), và dự kiến tự đóng phẳng lúc `18:00` giờ Helsinki (`16:00 UTC` / `23:00` giờ Việt Nam) để giữ sạch `swap = 0`.
  - **2 điểm lệch phiên bản cần đồng bộ ngay khi phẳng (`open_positions == 0`):**
    1. Dòng `fill_price` của lệnh lúc `05:17 UTC` ghi `0,000000` (do chạy bản `.ex5` trước bản vá `ResolveExecutedFillPrice()`). Toàn bộ `9/9 .ex5` đang chạy trên `naqex-node1` là bản `05:52 UTC` (chưa chứa 4 bản vá Cycle 1: `NAS100`, tách vùng pre-flatten `±135s`, siết `SYMCAP`, `Dyn_ProfitLock` + giờ reset ngày).
    2. Tệp `C:\Naqex\mt5\MQL5\Files\naqex_red_news_utc.csv` trên `naqex-node1` vẫn là bản cũ **`343` dòng** (`SHA 5b151169...`), chưa có tin đỏ `US GDP + Core PCE` ngày mai (`2026-11-25 13:30 UTC`) và cụm tin `GBP/EUR/JPY/USD` tháng `12/2026`. Khi tài khoản phẳng tối nay, cần đồng bộ lên bản **`418` dòng** (`SHA 68663f62...`) cùng `9/9 .ex5` mới qua `sync_updated_ex5_when_flat.ps1`.

### 2.2. Sức Khỏe Hạ Tầng, Đồng Hồ NTP, Lưu Trữ & Tác Vụ Tự Động

| Thành phần `naqex-node1` | Kết quả đo thực tế (`2026-11-24 11:01–11:02 UTC`) | Đánh giá |
|---|---|---|
| **Thời gian hoạt động (Uptime)** | Khởi động lần cuối `2026-11-24T08:25:48Z` (`~2,6` giờ sạch) | Khỏe |
| **Lưu trữ 3 ổ tách riêng** | `C:` trống **`103,88 GB`** (`14,75 GB` đã dùng) · `D:` trống **`465,65 GB`** · `E:` trống `111,69 GB` | Khỏe (`C: >> 20 GB`) |
| **Sao lưu ngày `D:\NaqexBackup\daily\`** | Đã tạo thư mục **`20261124`** (tác vụ `Naqex_Daily_Backup_D` `LastRes = 0`, lịch kế `2026-11-25 05:30`) | Khỏe |
| **Đồng bộ đồng hồ NTP (`w32tm`)** | `Stratum 2` · `time.google.com,0x8` · `Root Delay 0,046s` · `Root Dispersion 0,092s` · Sync lúc `17:44:20` ICT | Rất chuẩn (`< 0,1s`) |
| **Trạm giám sát mây Heroku EU** | `Naqex_Heroku_Heartbeat_NODE1` `LastRes = 0` · Trạm trả lời `ok=true, persistence=postgres, status=OK, reasons=[], order_send_count=0` | Khỏe 100% |
| **Windows Defender & Firewall** | `Antivirus=True`, `RealTimeProtection=True`, `DisableRealtimeMonitoring=False`, ngoại lệ duy nhất **`C:\Naqex`** · Firewall `3/3` BẬT | **Đạt chuẩn bảo mật** |
| **Tác vụ `SYSTEM` (`Naqex_*`)** | `4/4` tác vụ (`Heroku_Heartbeat_1m`, `Daily_Backup_D`, `Crypto_Shadow_5m`, `Crypto_Maker_Probe_5m`) đều `Ready` & **`LastRes = 0`** | Khỏe *(xem ghi chú nhỏ)* |

> **Ghi chú vận hành nhỏ:** Kịch bản `C:\Naqex\ops\naqex_mt5_watchdog.ps1` đã chép sẵn trên đĩa nhưng chưa đăng ký tác vụ định kỳ cục bộ riêng (`Naqex_MT5_Watchdog_NODE1`). Hiện trạm Heroku EU (1 phút/lần) + `@naqex_guard_bot` đã đảm nhiệm giám sát sống từ xa rất tốt; có thể đăng ký thêm watchdog cục bộ trong khung bảo trì cuối tuần để có lớp bảo vệ thứ 2.

---

## 3. Kiểm Toán Bộ Gom Dữ Liệu Crypto Shadow & Maker (`C:\Naqex\crypto-shadow\`)

Toàn bộ bộ gom dữ liệu chạy hoàn toàn **chỉ đọc (`OrderSend = 0`, `api_keys_used = 0`)** mỗi `5` phút bằng dữ liệu sổ lệnh sống công khai của Binance.

### 3.1. Nhánh Crypto Spot (`S2`) & Funding Carry (`S3A`) — `crypto_shadow_latest.json`
- **Độ dài mẫu đã gom:** **`208` chu kỳ** (`2026-11-23T17:38:57Z -> 2026-11-24T11:03:02Z`, tổng **`17,40` giờ = `0,725` ngày**).
- **Kiểm định trượt giá sổ lệnh thật (Top-15 nhân quả):**
  - Lệnh **`10.000 USD`:** Trung vị toàn chuỗi **`1,789 bps`** (`min 1,233` · `max 2,554` · chu kỳ mới nhất **`1,625 bps`**) — **ĐẠT `208/208` chu kỳ (`100,0%`)** dưới ngân sách backtest **`<= 5,0 bps`** (dư biên an toàn hơn `2,7×`!).
  - Lệnh **`50.000 USD`:** Trung vị toàn chuỗi **`4,278 bps`** (mới nhất `4,969 bps`; `15/15` cặp đều đủ thanh khoản sâu `depth_50k_ok = true`).
  - Spread mua/bán trung vị Top-15 mới nhất: **`1,42 bps`** (`BTCUSDT 0,002 bps`, `ETHUSDT 0,059 bps`).
- **Tín hiệu giấy sống hiện tại:**
  - **Nhánh `S2` (Spot Momentum `4H`):** Đang ở chế độ phòng thủ tiền mặt (`btc_regime_bull = false`, `EMA60 63.312 USD < EMA300 73.712 USD`, tỷ trọng đầu tư `0%`, vốn giấy giữ nguyên `10.000 USD`).
  - **Nhánh `S3A` (Carry `BTC+ETH` đệm `2×`):** Đang mở vị thế giấy `BTCUSDT` (`25%` danh nghĩa, funding 7 ngày `3,09%/năm`, kỳ kế tiếp `4,24%/năm`, basis `+0,24 bps`) và tạm đứng ngoài `ETHUSDT` (`1,29%/năm`, thấp hơn ngưỡng kích hoạt).

### 3.2. Nhánh Điều Kiện Crypto Maker (`M2B`) — Tiến Độ Cổng `30` Ngày Bắt Buộc

- **Độ dài mẫu đã gom:** **`197` chu kỳ** (`2026-11-23T18:22:32Z -> 2026-11-24T11:03:02Z`, tổng **`16,67` giờ = `0,695` ngày**).
- **Ước tính thời gian chạm cổng `30` ngày:** Đã hoàn thành **`0,70` ngày (`2,3%`)** -> **còn lại `~29,31` ngày** (mốc dự kiến hoàn tất: **`2026-12-23`** nếu giữ uptime liên tục).
- **Bảng đối chiếu `197` chu kỳ thực tế với 2 ngưỡng mở khóa `M2B` (`khớp >= 70%` & `chi phí <= 6,15 bps`):**

| Khung đặt lệnh thụ động (Rổ `Active Basket` `14` cặp Long/Short) | Tỷ lệ khớp mới nhất | Trung vị khớp (`197` chu kỳ) | Chi phí hiệu dụng mới nhất | Trung vị chi phí (`197` chu kỳ) | Chu kỳ đạt ngưỡng `<= 6,15 bps` | Đánh giá sơ bộ |
|---|---:|---:|---:|---:|---:|---|
| **`5` phút (`5m`)** | `85,71%` (`48/56`) | **`92,31%`** *(min `67,31%`)* | `4,087 bps` | **`3,256 bps`** *(max `15,249`)* | `159/197` (`80,7%`) | Khả quan, hơi nhạy lúc giật phiên Á |
| **`15` phút (`15m` — Chuẩn chính)** | **`92,86%`** (`39/42`) | **`97,44%`** *(min `74,36%`)* | **`3,195 bps`** | **`3,081 bps`** *(max `17,191`)* | **`163/197` (`82,7%`)** | **Tốt nhất — vượt xa cả 2 ngưỡng** |
| **`60` phút (`60m`)** | `92,86%` (`13/14`) | **`100,00%`** *(min `46,15%`)* | `2,571 bps` | **`2,725 bps`** *(max `28,928`)* | `142/197` (`72,1%`) | Chi phí trung vị thấp nhưng đuôi rủi ro rộng hơn |
| *Đối chứng `All-20` (`15m`)* | `92,50%` (`111/120`) | `97,50%` *(min `75,00%`)* | `3,259 bps` | `2,477 bps` *(max `12,092`)* | `170/197` (`86,3%`) | Xác nhận nhất quán trên cả 20 cặp |

> **Phán quyết trung thực cho `M2B`:** Số liệu `16,7` giờ đầu tiên rất tích cực (khung `15m` đạt trung vị khớp `97,44% >> 70%` và chi phí `3,081 bps << 6,15 bps`), nhưng **tuyệt đối không mở tiền thật sớm** trước khi đủ `30` ngày liên tục (`~29,3` ngày nữa) để đi qua đủ biến động ngày cuối tuần, các kỳ tin đỏ Mỹ và nhịp giật phiên Á (đã thấy vài chu kỳ cực đại lên `17,19 bps`).

---

## 4. Hành Động Tiếp Theo Theo Thứ Tự Ưu Tiên (Không Phá Trạng Thái Sống)

1. **Giữ nguyên `naqex-node1` chạy yên ngay bây giờ (`open_positions == 1`):** Không bấm đóng tay lệnh `E1_USDJPY_TOKYO` và không khởi động lại MT5.
2. **Chờ phẳng (`open_positions == 0`, dự kiến sau `16:00 UTC` / `23:00` ICT tối nay) rồi đồng bộ 1 lần:** Đẩy `9/9 .ex5` đã vá đủ 4 bản vá Cycle 1 + tệp lịch tin đỏ mới **`418` dòng** (`naqex_red_news_utc.csv`) sang `naqex-node1` bằng `sync_updated_ex5_when_flat.ps1` trước khi tin đỏ `US GDP + Core PCE` ra lúc `2026-11-25 13:30 UTC`.
3. **Gửi ngay 2 email xin xác nhận chạy EA độc quyền:** Dùng đúng mẫu sẵn sàng copy-paste tại [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md) gửi `support@ftmo.com` và `help@the5ers.com`.
4. **Diễn tập cảnh báo mất kết nối `3` phút khi tài khoản phẳng:** Kiểm tra điện thoại nhận đúng tin nhắn đỏ `🔴 MẤT KẾT NỐI` từ `@naqex_guard_bot` (xem hướng dẫn 5 bước trong tài liệu trên).
5. **Tiếp tục tích lũy đủ `10–15` lệnh đóng Free Trial (`14` ngày) và `30` ngày Crypto Maker** — chỉ mở mua vé `The5ers High Stakes 5K` sau khi toàn bộ bảng cổng Mục 1 chuyển sang **`PASS`**.

---

## 5. Nhật Ký Bảo Trì & Nâng Cấp Thực Địa `naqex-node1` + Heroku EU (`2026-11-25 02:57–03:17 ICT`)

Sau khi lệnh `E1_USDJPY_TOKYO` (`#591010790`) tự đóng phẳng sạch lúc `23:00:00.714 ICT` (`16:00:00 UTC`, `0 USD` swap, số dư chốt `9.998,88 USD`, `open_positions = 0`), cửa sổ bảo trì phẳng đã mở và hoàn tất toàn bộ các hạng mục nâng cấp sau:

1. **Đã xử lý `7` điểm lệch trực tiếp trên `naqex-node1` và `naqex-deadman-eu`:**
   - **Tắt ngủ ổ cứng (`DISKIDLE`):** Chỉnh `powercfg /change disk-timeout-ac 0` (từ `900s` về `0`), khóa `STANDBY = 0`, `HIBERNATE = 0`.
   - **Nâng cấp Heroku Dead-Man's-Switch (`naqex-deadman-eu`, build `7513a106` `v3-astra-f17-f20-hardened`):** Triển khai thành công bản vá `F17/F20` (`GET /health` `200`, `GET /` chưa xác thực trả `401`, giữ nguyên ngân sách `12 USD/tháng <= 13 USD/tháng` và Postgres `709` dòng). Đã **kiểm chứng sống** luồng cảnh báo Telegram `@naqex_guard_bot` khi trạm tự phát hiện `INNER_HEARTBEAT_STALE` và gửi tin nhắn thành công (`sent: ["telegram"], errors: []`).
   - **Đồng bộ sạch `9/9 .ex5` MQL5 v3.01 + lịch tin đỏ `436` dòng `6` đồng tiền (`AUD/CAD/EUR/GBP/JPY/USD`, `sha=419b005e...`)** + cập nhật `naqex_mt5_watchdog.ps1`, `sync_updated_ex5_when_flat.ps1`, `ex5_expected_sha256.json`, `manifest.sha256.json` và bộ preset The5ers (`ProfitLock +4%`, `SPX500`) sang `C:\Naqex\ops\` và `C:\Naqex\mt5\`. Khớp SHA-256 tuyệt đối `9/9`.
   - **Cập nhật bộ gom Crypto Shadow (`OrderSend = 0`):** Đạt **`318` chu kỳ** Crypto Shadow và **`307` chu kỳ** Crypto Maker (`LastRes = 0`).
2. **3 lỗi thực chiến nghiêm trọng phát hiện trực tiếp khi vận hành trên VPS và đã vá dứt điểm + biên dịch lại `9/9 .ex5` (`0` lỗi/cảnh báo):**
   - **Lỗi `sync_updated_ex5_when_flat.ps1` sập trên đường dẫn nông VPS (`C:\Naqex\ops\vps_kit`):** 5 lần `Split-Path -Parent` lồng nhau vọt quá gốc `C:\` thành chuỗi rỗng -> đã thay bằng `Get-AncestorPath` an toàn và kiểm chứng chạy thành công (`SYNC RC: 0`) ngay trên `naqex-node1`.
   - **Lỗi tranh chấp mở tệp lịch tin đỏ khi `9` bot khởi động song song (`Naqex_PropGuard.mqh`):** `LoadRedNewsCsv` thiếu cờ `FILE_SHARE_READ | FILE_SHARE_WRITE`, khiến `E1` và `E2` mở cùng mili-giây bị từ chối và tự khóa fail-closed (`loaded=0`) -> đã thêm `FILE_SHARE_READ | FILE_SHARE_WRITE` + thử lại `10` lần (`LoadRedNewsCsv`) & `8` lần (`LogExecAuditFor`).
   - **Lỗi `Naqex_AccountOrchestrator` khóa nhầm `kill_switch` cả ngày trước lúc đăng nhập (`v2.01`):** Khi MT5 mới khởi động chưa kết nối sàn (`equity = 0`), bản cũ tính nhầm `static_dd_pct = 100%` và khóa cứng `g_autoKillActive` -> đã thêm `IsAccountSynced(bal, eq)` chuyển tạm sang `regime = "DISCONNECTED"` không chốt khóa cứng.
   - **Lỗi `KeepPrivate=0` trong `C:\Naqex\mt5\connector.ini`:** Là nguyên nhân khiến MT5 không lưu mật khẩu phiên cũ khi khởi động lại (nếu cúp điện sau này cũng sẽ mất kết nối). Đã đổi sang **`KeepPrivate=1`** (không chứa mật khẩu trần).
3. **1 bước thủ công 30 giây duy nhất còn lại cho chủ sở hữu:**
   - Truy cập RDP vào `naqex-node1` (`192.168.1.28` hoặc Tailscale `100.72.70.18`), đăng nhập lại `1` lần duy nhất vào tài khoản `FTMO-Demo 1515343166` trong cửa sổ MT5 đang mở và **tích chọn `Save password`** — từ đó về sau nhờ `KeepPrivate=1`, mọi lần khởi động lại hoặc cúp điện MT5 sẽ tự đăng nhập lại hoàn toàn tự động.
