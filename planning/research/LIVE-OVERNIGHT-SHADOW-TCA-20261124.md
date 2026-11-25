---
doc_type: research-report
title: "Live Overnight Shadow TCA & FTMO-Demo 1515343166 Telemetry Harvest (2026-11-24)"
date: 2026-11-24
status: verified
order_send_live_money: 0
ftmo_demo_login: 1515343166
holdout_2025_sealed: true
---

# Báo Cáo Thu Hoạch Live Overnight Shadow TCA & FTMO-Demo 1515343166 (24/11/2026)

> **Phạm vi kiểm chứng:** Thu thập dữ liệu thị trường thật xuyên đêm (`00:38 -> 11:28` giờ VN, `~10,8` giờ liên tục) trên **3 daemon độc lập**: (1) **FTMO-Demo `1515343166`** sandbox cô lập với `9` chart `Naqex_FreeTrial` chạy thật (`ACCOUNT_TRADE_MODE_DEMO`, `0` chạm tới Exness Real, `0` mật khẩu lưu ổ đĩa), (2) **Binance Spot/Perp L2 Shadow** (`OrderSend = 0`, `0` API key), và (3) **Binance Maker Passive-Limit Fill Probe** cho ứng viên `M2B_BLEND_50_FUND_50_MOM` (`OrderSend = 0`, `0` API key). Điểm kiểm toán tổng thể `daily_ops_briefing.py` lúc `11:28`: **`100 / 100 GREEN_OPERATIONAL` (`PASS=6, WARN=0, PENDING=0, FAIL=0`)**.

---

## 1. Tóm Tắt 3 Luồng Telemetry Xuyên Đêm

| Luồng Live Overnight | Khung giờ UTC | Số chu kỳ | Trạng thái & Uptime | Kết quả TCA cốt lõi |
|---|---|---:|---|---|
| **FTMO-Demo `1515343166` (`9` chart `Naqex_FreeTrial`)** | `2026-11-23 19:59 -> 2026-11-24 04:27` (`~8,5` giờ) | **`509`** (mỗi `60s`) | **`100,0%` Heartbeat OK**, `0` crash, `0` `orphan_no_sl`, tự chuyển Access Server 1b (`203 ms`) qua rollover | `Balance = Equity = 10.000,00 USD`; `USDJPY` spread trung vị `4,0 pts` (`0,4 pip`), `EURUSD` `1,0 pt`, `US100.cash` `195 pts` |
| **Binance Spot & Carry L2 Shadow (`crypto_shadow_runner`)** | `2026-11-23 17:38 -> 2026-11-24 04:26` (`~10,8` giờ) | **`130`** (mỗi `300s`) | **`100,0%` trong ngân sách `<= 5,0 bps`** (`OrderSend = 0`) | Trượt giá sổ lệnh L2 `10k USD` trung vị **`1,825 bps`** (`P90 2,108 bps`, `Max 2,554 bps` << ngân sách `5,0 bps`); `50k USD` trung vị **`4,247 bps`** |
| **Binance Maker Passive-Limit Probe (`M2B_BLEND_50_FUND_50_MOM`)** | `2026-11-23 18:22 -> 2026-11-24 04:28` (`~10,1` giờ) | **`120`** (mỗi `300s`) | `OrderSend = 0`, `0` API key, rổ `13` chân trung tính (`net = 0,0`) | Khung **`15m`**: tỷ lệ khớp chạm xuyên trung vị **`97,44%`** (`P10 87,18%`), chi phí ròng trung vị **`3,106 bps <= 6,15 bps`** (**`80,0%`** chu kỳ đạt chuẩn `M2`) |

---

## 2. Phân Tích Chi Tiết FTMO-Demo `1515343166` (Live 9-Chart Sandbox)

### 2.1. Kiểm chứng thực thi & sống sót qua Daily Rollover (`21:55–23:00 UTC`)
- **Kiến trúc an toàn:** Chạy hoàn toàn trong sandbox cô lập `.runtime/ftmo-demo-portable-1515343166/` (`FTMO-Demo`, `10.000 USD`, đòn bẩy Swing `1:30`, `hedging mode`, `AllowLiveTrading = 1`, `AllowDllImport = 0`). Không chạm tới cài đặt `C:\Program Files\MetaTrader 5` (Exness Real).
- **Khởi tải `9/9` EA thành công:** `Naqex_AccountOrchestrator` + `8` EA trắng (`E1..E7, S6`) đều nạp sạch `0` lỗi và đồng bộ lại sạch sau khi terminal tự chuyển từ `Access Server 1a` sang `Access Server 1b` (`65%` chất lượng, ping `203,14 ms`) vào lúc `05:01:50` giờ VN (`22:01:50 UTC`).
- **Heartbeat & An toàn vị thế:** Trong toàn bộ `509` chu kỳ chụp mỗi phút, `naqex_heartbeat.json` giữ **`100,0%` trạng thái `OK`** (`HbAge <= 6s`), `max_orphan_no_sl = 0`, `kill_switch = false`. Trong phiên Á-Tokyo sáng 24/11, thị trường đi trong biên độ gọn nên bộ lọc tín hiệu trắng kỷ luật giữ trạng thái phẳng (`0` lệnh sai/nhiễu), chờ phiên Âu (`14:00+ VN`) và phiên Mỹ (`20:30+ VN`) nơi `E2..E7` và `S6` hoạt động chính.

### 2.2. Thống Kê Spread Thật Theo Thời Gian Thực (509 mẫu, gồm cả Rollover)

| Mã FTMO-Demo | Min (`pts`) | Trung vị (`pts`) | P90 (`pts`) | Max (`pts`, đỉnh rollover) | So với giả định backtest M1 |
|---|---:|---:|---:|---:|---|
| `USDJPY` | `2,0` | **`4,0`** (`0,4 pip`) | `15,0` | `130,0` | Chặt hơn backtest trong phiên chính; đỉnh `130 pts` rơi đúng rollover (nơi hệ thống đã ép phẳng `swap = 0`) |
| `GBPUSD` | `2,0` | **`5,0`** (`0,5 pip`) | `58,0` | `142,0` | Rất chặt trong phiên chính; tránh giao dịch sát `22:00 UTC` là hoàn toàn chuẩn xác |
| `EURUSD` | `0,0` | **`1,0`** (`0,1 pip`) | `21,0` | `46,0` | Cực chặt (`0,1 pip` trung vị) |
| `EURJPY` | `6,0` | **`10,0`** (`1,0 pip`) | `87,0` | `155,0` | Khớp sát biên độ lịch sử Dukascopy |
| `US100.cash` | `145,0` | **`195,0`** (`1,95 điểm`) | `213,0` | `213,0` | **Chặt hơn dữ liệu lịch sử Dukascopy** (`2,88–3,41 điểm` ở Pass 23) |
| `US500.cash` | `60,0` | **`60,0`** (`0,60 điểm`) | `63,0` | `63,0` | Rất ổn định xuyên đêm |
| `XAUUSD` | `0,0` | **`45,0`** (`0,45 USD/oz`) | `48,0` | `51,0` | Tương đương sát biên độ Bid/Ask lịch sử |

---

## 3. Phân Tích Live Binance Spot/Perp L2 Shadow (130 chu kỳ)

- **Độ sâu sổ lệnh thật Top-15 Causal Universe (`BTC, ETH, SOL, ZEC, XRP, BNB, NEAR, UNI, DOGE, TRX, SUI, LINK, ADA, AVAX, AAVE`):**
  - Spread trung vị: **`1,388 bps`**.
  - Trượt giá một chiều quy mô **`10.000 USD`**: trung vị **`1,825 bps`**, `P90 = 2,108 bps`, đỉnh cao nhất suốt `10,8` giờ là **`2,554 bps`** — **`130/130` chu kỳ (`100,0%`) nằm sâu dưới ngưỡng giả định backtest `5,0 bps`**.
  - Trượt giá một chiều quy mô **`50.000 USD`**: trung vị **`4,247 bps`** (vẫn dưới ngân sách `5,0 bps` của backtest!).
- **Tín hiệu chế độ thị trường thật (`24/11/2026`):**
  - Giá cuối phiên đo: `BTC = 60.514,36 USD`, `ETH = 1.699,51 USD`.
  - **Nhánh #2 `S2_CRYPTO_SPOT` (`F4_4H_EMA`):** `BTC EMA60 < EMA300` (`btc_regime_bull = false`) -> hệ thống kỷ luật giữ `0%` phơi nhiễm tiền mặt, bảo toàn vốn trong pha điều chỉnh.
  - **Nhánh #3A `S3A_FUND_CARRY`:** Funding năm hóa thực tế dao động `BTC [-2,08% .. +8,90%]`, `ETH [-7,63% .. +0,57%]` -> chưa vượt ngưỡng kích hoạt dương bền vững (`> +12%/năm` hoặc chuỗi 7 ngày dương cao), tiếp tục đứng ngoài an toàn.

---

## 4. Phân Tích Live Binance Maker Passive-Limit Probe (`M2B_BLEND_50_FUND_50_MOM`, 120 chu kỳ)

Lab #2B ([LAB2B-CRYPTO-MAKER-STATARB-20261124.md](LAB2B-CRYPTO-MAKER-STATARB-20261124.md)) xếp `M2B_BLEND_50_FUND_50_MOM` (`+15,01%` Cl.B, `BE 4,51×`, `r vs S2 = -0,2358`) vào trạng thái `CONDITIONAL_RETEST` với điều kiện kiểm chứng trực tiếp tỷ lệ khớp lệnh limit thụ động và lựa chọn bất lợi (adverse selection) so với ngưỡng `M2 = 6,15 bps`. Kết quả đo thực tế xuyên đêm (`120` chu kỳ, chạm xuyên bảo thủ `low < bid` / `high > ask`):

| Khung treo lệnh Limit | Số chu kỳ | Tỷ lệ khớp trung vị | Tỷ lệ khớp P10 | Adverse Sel `5m` (trung vị) | Adverse Sel `15m` (trung vị) | Chi phí ròng trung vị (`bps`) | Chi phí ròng P90 (`bps`) | Tỷ lệ chu kỳ PASS `<= 6,15 bps` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`5m` timeout** | `120` | **`92,31%`** | `82,69%` | `+0,669 bps` | `-0,712 bps` | **`3,325 bps`** | `8,132 bps` | **`78,33%`** |
| **`15m` timeout (Khuyến nghị)** | `120` | **`97,44%`** | `87,18%` | `+0,821 bps` | `-1,188 bps` | **`3,106 bps`** | `8,594 bps` | **`80,00%`** |
| **`60m` timeout** | `120` | **`100,00%`** | `92,31%` | `-0,266 bps` | `-2,580 bps` | **`2,615 bps`** | `10,383 bps` | **`74,17%`** |

**Nhận định thực chiến:**
- **Tín hiệu rất tích cực cho `M2B`:** Trên khung **`15m`**, lệnh limit thụ động đạt tỷ lệ khớp trung vị **`97,44%`** (vượt xa giả định `70%` của kịch bản `M2`!) với chi phí ròng trung vị chỉ **`3,106 bps`** (bằng một nửa ngưỡng `6,15 bps`).
- **Lưu ý đuôi biến động (`P90`):** Ở giờ mở cửa phiên Á biến động mạnh (`01:20 UTC`), adverse selection làm chi phí ròng nhảy lên `8,59–10,38 bps` (`20%` số chu kỳ vượt `6,15 bps`). Do đó cần giữ đúng kỷ luật **30 ngày shadow** trước khi xem xét đưa `M2B` vào vốn thật, và cân nhắc né đặt lệnh tái cân bằng đúng phút mở cửa phiên biến động đột biến.

---

## 5. Tài Nguyên Đối Chiếu & Bước Kế Tiếp

- Đối chiếu Real-Tick `24/24` (`8/8 PASS`, `swap = 0,00 USD`): [MT5-REALTICK-RECONCILIATION-20261124.md](MT5-REALTICK-RECONCILIATION-20261124.md).
- Bản tin tổng hợp toàn chiến dịch Wave-2: [MORNING-BRIEFING-WAVE2-20261124.md](../MORNING-BRIEFING-WAVE2-20261124.md).
- Cả `3` daemon nền (Live `FTMO-Demo 1515343166`, Binance Spot/Perp Shadow, Binance Maker Probe) hiện đang vận hành ổn định `100 / 100 GREEN_OPERATIONAL` — chủ nhân có thể giữ chạy tiếp sang phiên Âu/Mỹ chiều tối 24/11 để bắt những lệnh demo thật đầu tiên của `E2..E7` và kiểm tra cuối ngày bằng `prop_challenge_tracker.py` và `daily_ops_briefing.py`.
