---
doc_type: runbook
domain: deployment_kit
status: ready_to_send
updated_utc: 2026-11-24
order_send_count: 0
holdout_rows_analysed: 0
sources:
  - "planning/TOP1-SOLO-QUANT-MASTER-PLAN.md"
  - "tooling/ai-engines/exports/deployment_kit/the5ers_kit/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md"
  - "knowledge/playbooks/ftmo-the5ers-live-launch-sop.md"
  - "planning/research/LIVE-NODE1-TELEMETRY-AND-SHADOW-AUDIT-20261124.md"
  - ".agents/skills/naqex-node-ops/SKILL.md"
---

# Bộ Thư Xác Nhận EA Văn Bản (FTMO & The5ers) & Danh Mục Bảo Mật `naqex-node1`

> **Mục đích:** Gom trọn 2 mẫu email tiếng Anh chuẩn pháp lý sẵn sàng **copy-paste gửi ngay** cho **FTMO (`support@ftmo.com`)** và **The5ers (`help@the5ers.com`, Terms §11)**, kèm danh mục 5 bước thủ công kiểm tra/bật lại **Windows Defender** (`excl C:\Naqex`) và diễn tập cảnh báo **`@naqex_guard_bot`** trên `naqex-node1`.
> **Nguyên tắc khóa an toàn (`R4`):** Lưu nguyên bản email phản hồi kèm số Ticket ID (dạng PDF/EML) trước khi thanh toán bất kỳ vé thi nào (`OrderSend = 0`).

---

## 1. Email #1 — Gửi FTMO (`support@ftmo.com`) Cho Gói `FTMO 2-Step (Standard / Swing)`

- **Người nhận:** `support@ftmo.com` (gửi từ đúng địa chỉ email đăng ký tài khoản FTMO của bạn).
- **Lý do hỏi gộp cả `Standard` & `Swing`:** Dịp Black Friday (`-> 30/11/2026 16:00 ICT`), ưu đãi giảm giá ngoài Mỹ/Úc áp cho **`FTMO Standard`** (nên cần xác nhận luôn cho cả `Standard` có khóa tin đỏ `±5` phút lẫn `Swing` miễn luật tin đỏ).

```text
To: support@ftmo.com
Subject: Pre-Purchase Written Confirmation — 100% Proprietary White-Box MQL5 EA (FTMO 2-Step Standard / Swing)

Hello FTMO Support & Risk Team,

Before purchasing an FTMO 2-Step Challenge account (either Standard or Swing), I am writing to request written confirmation that running my strictly proprietary, self-developed MetaTrader 5 Expert Advisor complies fully with FTMO's Terms & Conditions and Prohibited Trading Practices.

Technical & Risk Profile of My Automated System (100% Owned Custom Source Code):
1. Exclusive Ownership & Zero Copy-Trading: Every MQL5 source file (.mq5) is written, compiled, and operated solely by me for my own personal account. No third-party, commercial, leased, shared, or signal-copied EAs are used, and no external users run the same parameters or entries.
2. Dedicated Clean Residential IP: The MT5 terminal runs continuously on my own dedicated personal Windows workstation at home (naqex-node1) over my private residential ISP connection (zero shared commercial VPS/VPN IP pools).
3. Architecture & Low-Frequency Cadence: The system runs 7 low-frequency intraday breakout and cross-asset momentum strategies (trading liquid FX majors USDJPY, GBPUSD, EURJPY and US100.cash). Typical activity is 0 to 3 trades per day across the entire portfolio (zero HFT, zero tick scalping, zero latency or demo-feed arbitrage, and zero order-modification spam).
4. Hard-Coded Risk & News Controls on Every Order:
   - Mandatory broker-side Stop Loss attached immediately at order entry (zero hidden/virtual stop-losses).
   - Strict intraday flat policy: all positions automatically close before daily rollover (prior to 20:55 UTC / 15:55 ET; zero overnight swap and zero weekend holding).
   - High-impact news protection for Standard FTMO Accounts: a built-in official calendar guard (USD/EUR/GBP/JPY/AUD/CAD including FOMC Rate & Minutes, NFP, CPI, GDP, BoE, ECB, BoJ) blocks all entries within ±5 minutes and pre-flattens any open affected position strictly before -2 minutes 15 seconds prior to Restricted releases (zero orders/SL/TP active inside the ±2-minute window).
   - Zero grid, zero martingale, zero averaging down, and zero cross-account hedging.
   - Portfolio-level per-symbol and directional currency-factor risk caps (USD/JPY/US100), automatic drawdown de-risking, and hard daily/overall kill switches synced to Europe/Prague daily reset.

Could you please confirm in writing that:
(a) Operating this strictly proprietary, self-coded MQL5 EA from my dedicated personal machine complies fully with FTMO 2-Step Standard and Swing Evaluation and FTMO Account rules; and
(b) Whether any additional disclosure or registration is required prior to starting the Challenge?

Thank you very much for your assistance.

Best regards,
[Your Full Name]
[Your Registered FTMO Email Address]
[Optional: FTMO Free Trial Account ID, e.g. 1515343166]
```

---

## 2. Email #2 — Gửi The5ers (`help@the5ers.com`) Theo `Terms §11` Cho `High Stakes 5K / 20K`

- **Người nhận:** `help@the5ers.com` (hoặc cổng Ticket chính thức trong The5ers Hub, gửi từ email đăng ký The5ers).
- **Tham chiếu bổ sung:** Kèm đầy đủ 4 cổng kiểm tra & mẫu nhật ký lưu trữ tại [THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md](the5ers_kit/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md).

```text
To: help@the5ers.com
Subject: Pre-Purchase Written Confirmation Request — 100% Proprietary MQL5 EA (Terms §11 / High Stakes 5K & 20K)

Hello The5ers Support & Compliance Team,

Before purchasing a High Stakes (5K / 20K) Evaluation account, I am writing to request written confirmation under your Terms & Conditions (Section 11) and EA Policy that my strictly proprietary, self-developed MetaTrader 5 Expert Advisors are fully permitted on High Stakes Evaluation and Funded accounts.

Technical & Compliance Summary (100% Self-Authored Custom Source Code):
1. Sole Ownership & Uniqueness: All MQL5 source files (.mq5) are written, compiled, and exclusively operated by me for my own personal account from my dedicated private residential workstation (zero third-party/commercial/rented EAs, zero copy-trading, zero shared signals).
2. Symbols & Low-Frequency Intraday Strategy: 8 low-frequency intraday breakout and cross-asset momentum EAs trading liquid FX majors (USDJPY, GBPUSD, EURJPY, EURUSD, AUDUSD, USDCAD) and NAS100 index (verified against your MT5 Market Watch symbol naming), supervised by 1 local Account Orchestrator EA. Typical cadence is 0 to 3 trades per day (zero HFT, zero tick scalping, zero latency arbitrage).
3. High-Impact News Compliance (Strict Pre-Flatten Outside ±2-Minute Ban):
   - Built-in 4-currency official calendar guard (USD, GBP, EUR, JPY: FOMC, NFP, CPI, PPI, Retail Sales, Core PCE/GDP, BoE, UK CPI, ECB, BoJ) blocks all new entries within ±5 minutes around high-impact releases.
   - Any open position on an affected currency is pre-flattened strictly between -5 minutes and -2 minutes 15 seconds BEFORE the scheduled release, and all automated opens/closes are hard-blocked inside the ±2 minute 15 second no-execution zone (strictly outside The5ers' ±2-minute restriction, with zero news bracketing).
4. Mandatory Risk Controls:
   - Server-side Stop Loss attached immediately at order entry on 100% of orders (zero hidden SL).
   - Zero grid, zero martingale, zero averaging down, and zero hedging across accounts.
   - Intraday flat before daily rollover (prior to 20:55 UTC; zero overnight swap / weekend holding), per-symbol risk cap (<= 1.75% Evaluation / <= 1.00% Funded), and automatic daily/overall kill switches synced to MT5 Server Midnight.

Could you please confirm in writing that:
(a) Running these strictly proprietary, self-coded MQL5 EAs on my personal High Stakes (5K / 20K) Evaluation and Funded accounts complies fully with Terms §11 and your Prohibited Practices policy; and
(b) Confirm the exact Market Watch symbol names for Nasdaq-100 (e.g., NAS100) and S&P 500 (e.g., SPX500 / US500) on High Stakes MT5 servers, plus whether any IP or EA pre-registration is needed?

Thank you for your time and clear guidance.

Best regards,
[Your Full Name]
[Your Registered The5ers Email Address]
[Optional: The5ers Hub User ID]
```

---

## 3. Danh Mục 5 Bước Thủ Công Cho Chủ Sở Hữu: Bảo Mật Windows Defender & Diễn Tập Telegram Trên `naqex-node1`

> **Lưu ý từ kiểm toán trực tiếp (`2026-11-24 11:01 UTC`):** Kiểm tra read-only cho thấy **Windows Defender trên `naqex-node1` hiện ĐÃ BẬT (`RealTimeProtectionEnabled = True`) với duy nhất ngoại lệ `C:\Naqex`** và Tường lửa BẬT `3/3` hồ sơ. Tuy nhiên vẫn giữ đầy đủ 5 bước bên dưới để chủ sở hữu tự xác minh chéo và thực hiện **diễn tập ngắt mạng 3 phút kiểm tra `@naqex_guard_bot`** (chỉ làm khi tài khoản **phẳng `open_positions == 0`**!).

1. **Bước 1 — Khóa điều kiện phẳng trước khi thao tác (`open_positions == 0`):**
   - Kiểm tra nhanh qua SSH hoặc Control Room (`http://127.0.0.1:8787`) bảo đảm `C:\Naqex\mt5\MQL5\Files\naqex_heartbeat.json` đang báo **`"open_positions": 0`** (sau `21:00 UTC` hoặc ngày cuối tuần). **Tuyệt đối không diễn tập ngắt mạng khi đang có lệnh mở.**
2. **Bước 2 — Xác minh (hoặc bật lại nếu tắt) Windows Defender bảo vệ thời gian thực & đúng 1 ngoại lệ `C:\Naqex`:**
   - Mở PowerShell (Run as Administrator) trên `naqex-node1` và chạy lệnh kiểm tra/khóa cấu hình:
     ```powershell
     Set-MpPreference -DisableRealtimeMonitoring ([bool]0)
     Set-MpPreference -ExclusionPath @("C:\Naqex")
     Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled, AMServiceEnabled
     Get-MpPreference | Select-Object DisableRealtimeMonitoring, ExclusionPath
     ```
   - Yêu cầu kết quả: `AntivirusEnabled = True`, `RealTimeProtectionEnabled = True`, `DisableRealtimeMonitoring = False`, và `ExclusionPath` **chỉ chứa duy nhất `C:\Naqex`** (không đặt ngoại lệ cho toàn ổ `C:\`).
3. **Bước 3 — Xác nhận Tường lửa Windows (`mpssvc`) & `0` mật khẩu lưu trần:**
   - Chạy `Get-NetFirewallProfile | Select-Object Name, Enabled` -> xác nhận cả `Domain`, `Private`, `Public` đều `True`. Không lưu mật khẩu sàn MT5 trong tệp `.ini`, `.ps1`, hay ghi chú trên màn hình.
4. **Bước 4 — Diễn tập sự cố ngắt kết nối `3` phút kiểm tra `@naqex_guard_bot`:**
   - Khi `open_positions == 0`, tạm tắt tác vụ `Naqex_Heroku_Heartbeat_NODE1` trong `3` phút (hoặc tạm đóng MT5 trong `3` phút) bằng lệnh:
     ```powershell
     Disable-ScheduledTask -TaskName "Naqex_Heroku_Heartbeat_NODE1"
     ```
   - Chờ `2–3` phút và xác nhận điện thoại **nhận đúng tin nhắn đỏ `🔴 MẤT KẾT NỐI` / `STALE`** từ bot Telegram **`@naqex_guard_bot`** (trạm Heroku EU).
5. **Bước 5 — Bật lại & Xác nhận tin nhắn hồi phục `🟢 OK`:**
   - Chạy ngay:
     ```powershell
     Enable-ScheduledTask -TaskName "Naqex_Heroku_Heartbeat_NODE1"
     Start-ScheduledTask -TaskName "Naqex_Heroku_Heartbeat_NODE1"
     ```
   - Xác nhận điện thoại nhận lại trạng thái phục hồi bình thường, Control Room hiển thị `HbAge < 60s`, và ghi ngày diễn tập đạt vào nhật ký lưu trữ bên dưới.

---

## 4. Nhật Ký Lưu Trữ Pháp Lý & Diễn Tập (Chủ Sở Hữu Điền Khi Hoàn Tất)

| Hạng mục | Ngày thực hiện | Mã Ticket / Kết quả xác nhận | Đường dẫn lưu bằng chứng |
|---|---|---|---|
| **Email xác nhận FTMO Swing (`support@ftmo.com`)** | `[YYYY-MM-DD]` | `[Ticket #... / APPROVED]` | `[E:\BACKUP-TRADINGWORKSPACE\compliance\ftmo-swing-clearance.pdf]` |
| **Email xác nhận The5ers (`help@the5ers.com`, Terms §11)** | `[YYYY-MM-DD]` | `[Ticket #... / APPROVED]` | `[E:\BACKUP-TRADINGWORKSPACE\compliance\the5ers-terms11-clearance.pdf]` |
| **Xác minh Windows Defender (`excl C:\Naqex`) trên `naqex-node1`** | `2026-11-24` *(đã đo sống)* | `RealTime=True, Excl=C:\Naqex, FW=3/3` | [LIVE-NODE1-TELEMETRY-AND-SHADOW-AUDIT-20261124.md](../../../../planning/research/LIVE-NODE1-TELEMETRY-AND-SHADOW-AUDIT-20261124.md) |
| **Diễn tập ngắt kết nối `3` phút `@naqex_guard_bot`** | `[YYYY-MM-DD]` | `[PASS — nhận tin nhắn đỏ & phục hồi]` | `[Ảnh chụp màn hình Telegram lưu nội bộ]` |
