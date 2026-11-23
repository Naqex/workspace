---
doc_type: runbook
domain: deployment_kit
firm: The5ers
updated_utc: 2026-11-24
order_send_count: 0
status: ARM_LOCKED_PENDING_TERMS11_CLEARANCE
---

# Bộ Khởi Chạy The5ers High Stakes & Thư Xác Nhận EA Tự Viết (Terms §11)

> **Phạm vi:** Quy trình triển khai song song quỹ **The5ers High Stakes (`5.000 USD`, phí `39 USD`)** kế tiếp sau khi hoàn tất **FTMO Free Trial `14` ngày** với TCA `GREEN`. Toàn bộ preset The5ers (`The5ers_HighStakes_P1_Balanced`, `The5ers_HighStakes_P1_Sprint`, `The5ers_HighStakes_Funded`) hiện giữ cứng trạng thái **ARM-LOCKED** (`InpDryRunLogOnly = true`, `OrderSend = 0`).
> **Tham chiếu gốc:** [Hồ sơ The5ers](../../../../../planning/research/THE5ERS-PARALLEL-PROFILE-AND-SPEC-PLAN-20261123.md) · [Thẻ Kích Hoạt MT5 Local](../ACTIVATION-CARD-LOCAL-MT5.md) · [Lịch Tin Đỏ 2018–2027](../../Files/naqex_red_news_utc.csv).

---

## 1. Bốn Cổng Bắt Buộc Trước Khi Trả `39 USD` Mua Tài Khoản The5ers

| Cổng | Nội dung bắt buộc | Cách xác minh cụ thể | Trạng thái khóa |
|---|---|---|---|
| **G1 — Lấy `SymbolInfo` thật ở mức `0 USD`** | The5ers không có Free Trial công khai như FTMO; phải lấy thông số thật (`spread`, `commission`, `swap`, `stops_level`, `filling_mode`, múi giờ server) từ máy chủ MT5 thật của The5ers | Đăng ký **The5ers Free Monthly Trading Competition (`0 USD`)** → chạy script đo Read-Only `SymbolInfo` (`OrderSend = 0`) trên `USDJPY`, `GBPUSD`, `EURUSD`, `EURJPY`, `US100.cash` (hoặc ký hiệu chỉ số thực của The5ers), `US500.cash`, `XAUUSD`. | Bắt buộc trước khi mua vé |
| **G2 — Email xác nhận EA tự viết (Terms §11)** | FAQ công khai cho phép EA tự sở hữu mã nguồn, nhưng Terms §11 giữ điều khoản rộng về phần mềm tự động → bắt buộc xin xác nhận bằng văn bản trước khi nạp tiền | Gửi đúng mẫu thư chính thức ở **Mục 4** bên dưới tới bộ phận Support của The5ers, lưu bản PDF/EML phản hồi cùng số Ticket ID vào hồ sơ lưu trữ cá nhân. | **HARD GATE — Cấm mở khóa ARM-LOCKED nếu chưa có email xác nhận** |
| **G3 — Luật `>= 3` Ngày Lãi `>= +0,5%` / Vòng** | High Stakes yêu cầu tối thiểu **`3` ngày giao dịch có lãi ròng `>= +0,5%` số dư gốc** (đo theo `min(balance, equity)` lúc `00:00` giờ server MT5!) | Kiểm tra xác suất tự nhiên của `PORT_7E`/`PORT_9E`: ở hồ sơ `P1_Balanced (4,0×)` và `P2_Verify (2,5×)`, trung vị số ngày `>= +0,5%` vượt chuẩn mà không cần đánh thêm lệnh giả tạo; **tuyệt đối không mở lệnh rác `0,01` lot hay chia nhỏ lệnh nhân tạo** để lách luật. | Kiểm tra trên bảng thống kê Hub trước khi chốt vòng |
| **G4 — Khóa Tin Đỏ `±2 phút` (Áp Bảo Thủ `±5 phút`)** | High Stakes **cấm mở lệnh, đóng lệnh, hoặc khớp SL/TP trong cửa sổ `±2 phút`** quanh tin đỏ Forex Factory (lãi bị xóa, lỗ giữ nguyên!) | Nạp file **`naqex_red_news_utc.csv`** (`343` dòng chính thức `2018–2027` gồm `USD`, `EUR`, `GBP`, `JPY` — FOMC, NFP, CPI, ECB, BoE, BoJ) vào `<MT5 Data Folder>\MQL5\Files\`, bật **`InpGuardEnableRedNews = true`** và **`InpGuardNewsPadSec = 300`** (`300` giây = `±5` phút) trên 100% preset The5ers (gấp `2,5×` biên an toàn `±2m` của hãng!). | Đã bật sẵn trong 100% preset `The5ers_*` |

---

## 2. Danh Sách Kiểm Tra Tuân Thủ Tuyệt Đối Trên The5ers (Chống Ban & Từ Chối Payout)

1. **100% Mã nguồn tự viết & độc quyền sở hữu:** Toàn bộ `8` EA `Naqex_WB_*` và `Naqex_AccountOrchestrator` là mã nguồn `.mq5` trắng hoàn toàn do chủ tài khoản sở hữu; không dùng bot mua/thuê/chia sẻ/Telegram copy.
2. **Hard Server-Side Stop Loss trên 100% lệnh:** Không bao giờ dùng SL ẩn (*stealth/virtual SL*). `Naqex_PropGuard.mqh` bắt buộc gắn mức `SL` cứng ngay trong yêu cầu `OrderSend` và `Naqex_AccountOrchestrator` quét liên tục `orphan_no_sl == 0`.
3. **Không Grid / Không Martingale / Không News Bracketing:** Tối đa `1` lệnh/động cơ/ngày, cắt lỗ cứng theo `ATR`, không trung bình giá lỗ, không đặt cặp lệnh chờ Buy-Stop/Sell-Stop kẹp tin.
4. **Đóng vị thế trong ngày (`swap = 0`, `weekend_violations = 0`):** Toàn bộ vị thế tự đóng trước `20:55 UTC` (`US100` đóng `15:55 ET`, `E1 USDJPY` đóng `18:00 Helsinki`) để tránh phí swap qua đêm và khoảng trống cuối tuần.
5. **Kiểm tra tên ký hiệu chỉ số trên The5ers MT5:** Trước khi gắn `E4` (`US100`) và `E5` (`US100` vs `US500`), xác minh tên mã chính xác trên máy chủ The5ers (ví dụ `NAS100` / `NDX100` / `US100.cash` và `SPX500` / `US500.cash`), đồng bộ đúng `InpBenchmarkSymbol` và đo lại `InpGuardMaxSpreadPoints` từ snapshot G1.
6. **Cơ chế hoàn phí & ngưỡng rút tiền cần biết trước:**
   - Hoàn phí High Stakes: `10%` Hub Credit (qua P1) + `20%` Hub Credit (qua P2, không rút tiền mặt) + `70%` tiền mặt ở lần payout Funded đầu tiên.
   - Rút tiền tối thiểu sau chia lợi nhuận: **`150 USD`** (chu kỳ `14` ngày); kiểm tra thêm thẻ giá & quy định không hoạt động (`30` ngày) ngay tại màn hình checkout trước khi thanh toán.

---

## 3. Bảng Preset The5ers Sẵn Sàng (Đồng Bộ M2.2 `seed = 20261124`)

| Bộ Preset (`presets/<Profile>/`) | Hệ số hiệu dụng (`EA × Orch`) | Amber / Red Brake | Kill Daily / Static | MaxSymRisk | RedNews `±5m` | S6 | Khi nào mở khóa ARM-LOCKED |
|---|---:|---|---|---|---|---|---|
| `The5ers_HighStakes_P1_Balanced` | `4,00×` (`1,50 × 2,67`) | `7,5% / 1,00×`, `9,0% / 0,75×` | `4,2%` / `9,2%` | `3,00%` | **ON** | ON | Sau khi đạt đủ G1 + G2 + FTMO Free Trial TCA `GREEN` |
| `The5ers_HighStakes_P1_Sprint` | `4,75×` (`1,50 × 3,17`) | `9,9% / 1,00×`, `9,9% / 1,00×` | `4,3%` / `9,5%` | `3,50%` | **ON** | ON | Tùy chọn chỉ khi đã có quỹ đệm `Challenge Reserve >= 5×` vé (`195 USD`) |
| `The5ers_HighStakes_Funded` | `1,00×` (`1,00 × 1,00`) | `3,5% / 0,65×`, `6,0% / 0,40×` | `2,5%` / `7,5%` | **`1,00%`** | **ON** | **OFF** | Ngay khi chuyển sang tài khoản Funded (luôn tắt S6, giữ `SYMCAP 1%`) |

---

## 4. Mẫu Thư Chính Thức Gửi Support The5ers (Terms §11 Written EA Clearance)

> **Hướng dẫn gửi:** Gửi qua email đăng ký tài khoản The5ers tới **`help@the5ers.com`** (hoặc cổng Ticket chính thức trong The5ers Hub). Điền lại phần trong ngoặc vuông `[...]` trước khi bấm gửi, và lưu nguyên bản email trả lời xác nhận của hãng trước khi mua bất kỳ gói High Stakes nào.

```text
Subject: Pre-Deployment Confirmation Request — 100% Proprietary White-Box MQL5 EA (Terms §11 / High Stakes)

Hello The5ers Support & Compliance Team,

Before purchasing a High Stakes Evaluation account, I am writing to request written confirmation under your Terms & Conditions (Section 11) and EA Policy that my proprietary, self-developed MetaTrader 5 Expert Advisors are fully permitted on High Stakes Evaluation and Funded accounts.

Summary of my automated trading system (100% owned custom source code):
1. Sole Ownership & Uniqueness: All MQL5 source files (.mq5) are written, compiled, and exclusively operated by me for my own personal account. No third-party, commercial, leased, shared, or copy-traded EAs or external signal services are used.
2. Strategy Profile: Low-frequency intraday breakout and cross-asset momentum across liquid FX majors (USDJPY, GBPUSD, EURJPY, EURUSD) and US100 index. Typical cadence is 0 to 3 trades per trading day across the portfolio (no tick scalping, no latency/feed arbitrage, no HFT order spam).
3. Strict Risk & Compliance Controls (hard-coded on every order):
   - Mandatory server-side Stop Loss attached immediately upon order execution (zero stealth/hidden stop-losses).
   - Zero grid, zero martingale, zero averaging down, and zero hedging across accounts.
   - Intraday flat before daily rollover (all positions closed prior to 20:55 UTC; zero weekend holding).
   - Built-in High-Impact News Guard blocking order openings, manual/automated closes, and risk entries within ±5 minutes around high-impact USD/EUR/GBP/JPY macro releases (stricter than the ±2-minute High Stakes restriction), with zero news bracketing.
   - Portfolio-level risk cap enforced via a dedicated local Risk Orchestrator EA (<= 1.0% risk per symbol on Funded accounts, automatic drawdown de-risking, and hard daily/overall kill switches).

Could you please confirm in writing that:
(a) Running these strictly proprietary, self-coded MQL5 EAs on my personal High Stakes Evaluation and Funded accounts complies fully with your Terms & Conditions and Prohibited Practices policy; and
(b) Whether any additional registration, VPS IP disclosure, or compliance step is required before activation?

Thank you for your time and clarification.

Best regards,
[Your Full Name]
[Your Registered The5ers Email Address]
[Optional: The5ers Hub User ID]
```

---

## 5. Nhật Ký Lưu Trữ Phản Hồi Xác Nhận (Điền Sau Khi Nhận Email)

- **Ngày gửi email:** `[YYYY-MM-DD]`
- **Mã Ticket / Người phản hồi The5ers:** `[Ticket #...]`
- **Tóm tắt phán quyết văn bản:** `[APPROVED / CONDITIONS_NOTED]`
- **Đường dẫn lưu bản sao PDF/EML:** `[E:\BACKUP-TRADINGWORKSPACE\compliance\the5ers-terms11-clearance.pdf]`
- **Ngày chụp snapshot `SymbolInfo` MT5 Competition (`0 USD`):** `[YYYY-MM-DD]` · **SHA-256:** `[PENDING_COMPETITION_CAPTURE]`
