---
doc_type: evergreen
domain: knowledge
topic: market-microstructure-and-economic-edge-handbook
updated_utc: 2026-11-23
sources:
  - "T1: Evans & Lyons (1999, NBER w7317) — Order Flow and Exchange Rate Dynamics"
  - "T1: Melvin & Prins / Ito & Yamada (arXiv:1501.07778, JFDS 2016) — Foreign Exchange Market Microstructure and the WM/Reuters 4pm Fix"
  - "T1: arXiv:1504.04354 — The Long Memory of Order Flow in the Foreign Exchange Spot Market"
  - "T1: Ackerer, Hugonnier & Jermann (arXiv:2212.06888) & He, Manela, Ross & von Wachter (arXiv:2310.11771 / NBER w32936) — Perpetual Futures Pricing"
  - "T1: arXiv:2506.08573 (2025) — Designing Funding Rates for Perpetual Futures in Cryptocurrency Markets"
  - "T1 (Đo nội bộ): PASS24, PASS26, PASS28, HOLDOUT-2025-2026-ONE-TIME-VERDICT-20261123.md & ARCHIVE-INDEX-202611.md"
  - "T2: Quantpedia, LSEG WMR Benchmark Methodology, Binance Perpetual Mark Price / Liquidation Engine Docs"
---

# Sổ tay Vi cấu trúc Thị trường & Nguồn Lợi thế Kinh tế (Market Microstructure & Economic Edge)

> Tài liệu này được viết chuyên biệt để **đóng khoảng trống số 1 của owner so với nhóm Super-Indie** ([Bản đồ Cạnh tranh Quant 2026](solo-ai-quant-competitive-landscape.md)): thay vì nhìn biểu đồ như các đường hình học trừu tượng, mọi chiến lược quant bền vững đều phải trả lời được câu hỏi cốt lõi trước khi viết một dòng code nào: **"Ai đang là đối tác giao dịch chịu thiệt (hoặc buộc phải giao dịch bất chấp giá) để trả tiền cho mình?"**

---

## 1. Luật bất biến: Không có "mẫu hình ma thuật" — Chỉ có Đối tác Kinh tế (*Economic Counterparties*)

Trading ngắn hạn và trung hạn (trừ phần tăng trưởng kinh tế dài hạn của cổ phiếu và lãi suất danh nghĩa) là trò chơi có **tổng bằng `0` trước phí và tổng âm sau phí**. Do đó, nếu một thuật toán kiếm tiền đều đặn sau phí trên nhiều năm và nhiều chế độ thị trường, **bắt buộc phải tồn tại một nhóm người chơi khác đang chấp nhận trả phí thanh khoản hoặc giao dịch không tối ưu vì ràng buộc thể chế/tâm lý**.

Dưới đây là **5 nguồn đối tác kinh tế thực tế nhất** mà một cá nhân vốn nhỏ (`50k–3M USD`) có thể khai thác hợp pháp — kèm đối chiếu trực tiếp vào kho động cơ Naqex (`E1..E7`, `C1/C2`) và những bẫy chúng ta đã bác bỏ ở Pass 1–28:

### 1.1. Tái cân bằng theo Phiên & Dòng tiền Doanh nghiệp/Quỹ thụ động (*Session Rebalancing & Fixing Flows*)
- **Ai buộc phải giao dịch?**
  - **Tokyo Fix (`09:55 JST` = `00:55 UTC`):** Các tập đoàn xuất nhập khẩu Nhật Bản (*importers/exporters*), ngân hàng tín thác (*trust banks*) phải chốt tỷ giá `USDJPY` theo mốc thanh toán ngày (đặc biệt vào các ngày Gotobi: mùng `5, 10, 15, 20, 25, 30`). Họ không đầu cơ — họ cần đổi tiền để trả hóa đơn hàng hóa đúng hạn.
  - **WMR London Fix (`16:00 London`, cửa sổ 5 phút `15:57:30–16:02:30` — T1 `arXiv:1501.07778`):** Hàng nghìn tỷ USD quỹ chỉ số thụ động (MSCI, Bloomberg Bond) và quỹ hưu trí bắt buộc phải phòng hộ tỷ giá (*FX hedging*) đúng theo mốc giá chuẩn để giữ sai số bám sát (*tracking error*) bằng `0`.
  - **Mở cửa London (`07:00–08:00 UTC`) & Mở cửa cash Mỹ NYSE (`09:30–11:30 ET`):** Dòng lệnh tích tụ qua đêm của các quỹ cổ phiếu, quỹ ETF và ngân hàng thương mại đổ dồn vào sổ lệnh cùng lúc, tạo ra xung lực định giá lại (*price discovery impulse*) có tự tương quan dương kéo dài nhiều giờ (T1 Evans & Lyons 1999: *Order flow*, tức chênh lệch lệnh mua/bán chủ động, giải thích phần lớn biến động tỷ giá ngắn hạn tốt hơn mô hình kinh tế vĩ mô cổ điển).
- **Đối chiếu Naqex (đã kiểm chứng thực nghiệm):**
  - `E1_USDJPY_TOKYO` (hộp Á `00:00–03:00 UTC` → phá vỡ phiên Âu `03:00–10:00 UTC`) và `E2_USDJPY_EXP80` khai thác chính sự giải phóng mất cân bằng dòng tiền phiên Á sang phiên Âu/Mỹ — tiếp tục lãi `+48,05R` và `+11,16R` trên Holdout `2025–2026`.
  - `E4_US100_SESS40` và `E5_US100_RS1130` (khung `09:30–11:30 ET` → giữ tới `15:55 ET`) khai thác đà dòng tiền tổ chức Mỹ (ETF/quỹ công nghệ đẩy Nasdaq vượt trội S&P 500 trong nửa đầu phiên và tiếp diễn sang phiên chiều).
  - **Cảnh báo thực nghiệm Pass 18:** Hiệu ứng đảo chiều ngay sau **WMR 16:00 Fix** có thật về mặt học thuật (`+17R` so với đánh ngược), nhưng trên tài khoản **CFD bán lẻ FTMO** biên lãi quá mỏng nên bị spread + commission `5 USD/lot` kéo xuống **`-48R`**. *Bài học:* Biết đối tác kinh tế là điều kiện **cần**, nhưng biên lợi nhuận phải lớn hơn ma sát phí của đúng loại tài khoản bạn giao dịch!

### 1.2. Cắt lỗ Cưỡng bức & Margin Call (*Forced Liquidations / Stop-Loss Cascades*)
- **Ai trả tiền cho bạn?** Người dùng đòn bẩy cao (retail FX/CFD, quỹ đòn bẩy, trader Crypto Perpetual) bị chạm ngưỡng **stop-loss cụm** hoặc **maintenance margin**. Khi chạm ngưỡng, sàn tự động tung **lệnh Market cùng chiều phá vỡ** để đóng vị thế bằng mọi giá, bất kể giá xấu tới đâu — đẩy đà giá đi xa thêm một đoạn rõ rệt (*momentum continuation*).
- **Tại sao chiến lược Breakout/Expansion có độ lệch dương (*positive skew*)?** Khi thị trường tích lũy hẹp (`E6_EURJPY_VOLCOMP` nén `R5/R20 < 0,85`) hoặc vừa trải qua ngày biến động mạnh (`E3_GBPUSD_VH`), lệnh cắt lỗ của 2 phe tập trung dày đặc ở rìa biên độ. Khi giá phá vượt `0,75–0,80 ATR`, làn sóng cắt lỗ cưỡng bức trở thành "nhiên liệu miễn phí" đẩy lệnh đi xa, giúp cắt lỗ nhỏ và ăn đuôi dài (`skew +1,27` tới `+1,63` trên `PORT_7E`).

### 1.3. Quét thanh khoản Retail (*Retail Liquidity Sweeps / Stop Hunts*) — Hiểu đúng bản chất, không thuyết âm mưu
- **Sự thật vi cấu trúc (không phải sàn "nhìn SL của riêng bạn để quét"):**
  - Các quỹ lớn và market maker muốn khớp một khối lượng hàng trăm triệu USD **không thể bấm Market một phát** vì sẽ tự làm giá chạy bất lợi cho chính họ. Họ buộc phải tìm nơi có **bể thanh khoản đối ứng lớn nhất** (*resting liquidity pool*).
  - Bể đó nằm ngay trên đỉnh/đáy gần nhất, mốc số tròn (`150.00`, `1.3000`), nơi hàng chục nghìn retail cùng đặt lệnh Stop-Loss (lệnh SL của phe Short = lệnh **Market BUY** chờ sẵn).
  - Khi giá được đẩy xuyên qua mốc đó, luồng lệnh Market BUY cưỡng bức bùng nổ cho phép tổ chức xả xong lệnh bán khổng lồ với trượt giá tối thiểu, rồi giá bật ngược trở lại vùng cân bằng.
- **Cảnh báo quan trọng từ bằng chứng Pass 13 & Pass 24 của Naqex:** Rất nhiều bài giảng YouTube/SMC ca ngợi việc đánh đảo chiều ngay sau *Liquidity Sweep* trên khung M15 (`M15_PDHL_SWEEP`, `GBPUSD/EURUSD Sweep`), nhưng khi kiểm định nhân quả trên dữ liệu tick Bid/Ask thật có phí stress, **toàn bộ họ đảo chiều quét thanh khoản ngắn hạn trên FX đều rớt thảm (`-275R` tới `-511R`)**! Lý do: cá nhân dùng nến OHLC/M1 CFD **không nhìn thấy L2 Order Book liên ngân hàng** nên không phân biệt được đâu là "quét giả để đảo chiều" và đâu là "phá vỡ thật do dòng tiền lớn mới bắt đầu". Ngược lại, **đi thuận chiều phá vỡ sau khi xác nhận biên độ lớn (`0,75–0,80 ATR`)** lại kiếm tiền bền vững vì chọn đúng các cú phá vỡ thật!

### 1.4. Mất cân bằng Funding Rate trên Crypto Perpetual Futures (*Crypto Perp Funding Imbalance*)
- **Cơ chế định giá (T1 `arXiv:2212.06888`, `arXiv:2310.11771`, `arXiv:2506.08573`):** Hợp đồng Vĩnh cửu (*Perpetual Futures*) không có ngày đáo hạn nên dùng **Funding Rate** thanh toán mỗi `8` giờ (hoặc `1` giờ) giữa phe Long và phe Short để neo giá Perp sát giá Spot:
  - Khi thị trường hưng phấn, đám đông đòn bẩy đổ xô Long đẩy giá Perp cao hơn Spot → **Funding dương mạnh** (có lúc tương đương `30%–100%+/năm`) → phe Long phải liên tục trả tiền mặt cho phe Short.
- **Ai trả tiền?** Nhà đầu cơ đòn bẩy thiếu kiên nhẫn sẵn sàng trả lãi suất cắt cổ để vay đòn bẩy `5×–50×` đặt cược tăng giá.
- **Hai cách khai thác và rủi ro ẩn:**
  1. **Delta-Neutral Cash-and-Carry (Mua Spot + Bán Perp cùng khối lượng):** Thu đều Funding dương với rủi ro hướng giá gần bằng `0`. *Rủi ro ẩn:* (a) Rủi ro sàn tập trung (sập sàn kiểu FTX), (b) Phí giao dịch vào/ra ăn mòn nếu Funding đảo chiều nhanh, (c) Rủi ro **auto-deleveraging (ADL)** hoặc **basis blowout** (chênh lệch Perp-Spot giãn đột ngột làm cháy chân Short Perp trước khi kịp chuyển ký quỹ).
  2. **Tín hiệu dòng tiền & Xu hướng (áp dụng an toàn ở Spot):** Dòng vốn đầu cơ đòn bẩy và xu hướng dòng tiền theo chuỗi tạo ra tính **xu hướng cực mạnh (Time-Series Momentum)** và **sự phân hóa dẫn dắt (Cross-Sectional Momentum)** trên Crypto — chính là lý do `C1_TSMOM_VOL20` và `C2_XSEC_TOP2_TREND` (chỉ Spot Long/Cash, `0` đòn bẩy) vẫn dương **`+5,98%..+8,98%/năm`** ngay trong mùa gấu `-53%` của BTC `2025–2026` ([Crypto Sleeve Study](../../planning/research/CRYPTO-SLEEVE2-AND-QUANT-POD-STUDY-20261123.md)).

### 1.5. Dòng tiền Chéo Vĩ mô (*Cross-Asset Risk-On / Risk-Off Transmission*)
- **Cơ chế:** Các quỹ đa tài sản (*Multi-Asset Macro Funds*) định giá lại rủi ro đồng thời trên cổ phiếu Mỹ (`US100`/`US500`), lãi suất trái phiếu Mỹ và đồng Yên tài trợ (*JPY carry funding*). Khi cổ phiếu công nghệ Mỹ bứt phá kết hợp đồng USD mạnh trên toàn rổ FX vào lúc `10:00 ET` (sau khi tin Mỹ `08:30 ET` đã tiêu hóa xong), dòng vốn xả Yên sang USD tạo đà rõ rệt trên `USDJPY` — đây chính là cơ chế kinh tế gốc của **Engine #7 `E7_USDJPY_NY10ET`** (`9/9` ô 2D dương, tương quan `r = -0,003` với các động cơ còn lại, Holdout `PF 1,70`).

---

## 2. Cơ chế Sổ Lệnh & Spread qua 4 Loại Sân Chơi (Order Book & Spread Mechanics)

Hiểu cấu trúc nơi lệnh của bạn được khớp giúp bạn biết ngay **chiến lược nào khả thi và chiến lược nào chắc chắn chết vì ma sát**:

| Đặc tính Vi cấu trúc | **FX ECN Liên ngân hàng** | **CFD FX / Chỉ số (FTMO, The5ers, Broker lẻ)** | **Crypto Spot CLOB (Binance, Coinbase)** | **Crypto Perpetuals (Binance, Bybit, Hyperliquid)** |
|---|---|---|---|---|
| **Cấu trúc sổ lệnh** | Mạng ECN tập hợp báo giá L2 từ nhiều ngân hàng Tier-1 & non-bank MM (XTX, Jump, Citadel Sec) | **OTC tổng hợp** — không có sổ lệnh tập trung công khai; sàn lấy giá từ LP hoặc nội bộ hóa (B-Book/Hybrid) | Sổ lệnh giới hạn trung tâm công khai (**CLOB**), ưu tiên Giá–Thời gian | CLOB công khai + cơ chế **2 giá**: *Last Price* (khớp lệnh) và **Mark Price** (tính thanh lý chống thao túng) |
| **Cấu trúc chi phí thật** | Spread thô gần `0` + Commission tổ chức rất thấp + độ trễ micro-giây | Spread thả nổi + Commission (`4–5 USD/lot` FX, `0` chỉ số) + **Swap qua đêm rất nặng** (`3×` thứ Tư/Sáu) | Phí Maker/Taker (`~2–10 bps` mỗi chiều) + trượt giá độ sâu sổ lệnh (rất rõ ở altcoin) | Phí Maker/Taker thấp hơn Spot (`~1–5 bps`) + **Funding Rate mỗi 8h** + rủi ro thanh lý |
| **Đặc điểm Spread theo giờ** | Mở rộng mạnh quanh tin Mỹ và rollover `21:55–22:15 UTC` | Giãn mạnh hơn ECN gốc ở rollover; `US100.cash` đóng cửa/giãn mạnh ngoài giờ cash NYSE | Giao dịch `24/7`, thanh khoản mỏng hơn vào cuối tuần UTC đêm | Giao dịch `24/7`, spread giãn đột biến khi xảy ra chuỗi thanh lý (*liquidation cascade*) |
| **Nhóm chiến lược PHÙ HỢP cho cá nhân** | Không tiếp cận trực tiếp ở vốn nhỏ | **Intraday Breakout/Momentum `swap = 0` khung `H1/M15–D1`** (giữ vài giờ, dừng lỗ `>= 0,65–0,75 ATR` để tỷ lệ `Phí/SL < 5%–8%`) | **Xu hướng khung ngày (`D1`) + Xoay vòng thanh khoản trượt** (`turnover` thấp, chịu được `15–30 bps` phí) | **Funding Cash-and-Carry** (nếu chấp nhận rủi ro sàn) hoặc Trend khung ngày đòn bẩy thấp (`<= 1–2×`) |
| **Nhóm chiến lược CHẮC CHẮN CHẾT** | — | Scalping 3–5 pip, Mean-reversion siêu ngắn (Pass 13/18), giữ Swing trả Swap âm nặng (Pass 19 `US500` Swap ăn `-2.000 USD`) | High-frequency arbitrage đua tốc độ với market maker VIP0/VIP9 | Dùng đòn bẩy `> 5×` không có phanh vol → bị quét bởi liquidation wick |

---

## 3. Cụm Biến động (*Volatility Clustering*) — Quy luật thống kê mạnh nhất trong Tài chính

### 3.1. Định luật Mandelbrot & Engle (GARCH)
Lợi nhuận ngày rất khó dự báo (gần nhiễu trắng), **nhưng biến động (volatility) lại có tính dự báo cực cao**: *"những ngày biến động lớn thường kéo theo những ngày biến động lớn, và những ngày êm đềm thường kéo theo những ngày êm đềm"*.

### 3.2. Hai hệ quả trực tiếp làm thay đổi hoàn toàn thiết kế hệ thống Quant
1. **Lọc chế độ vào lệnh (Entry Volatility Conditioning):**
   - Trong `E6_EURJPY_VOLCOMP`, ta tìm trạng thái **nén biến động ngắn so với dài** (`Range_5 / Range_20 < 0,85`) để đón cú bung lò xo đầu tiên khi biến động chuyển từ thấp sang cao.
   - Trong `E3_GBPUSD_VH`, ta lại đòi hỏi **ngày hôm trước đã có biên độ cao (`>= 1,10 ATR`)** để xác nhận dòng tiền lớn đã thức dậy và tiếp diễn theo cụm biến động.
2. **Phanh biến động 1 chiều (*Downside Volatility Brake*) — Bài học sống còn từ Pre-Holdout Audit:**
   - Trong lý thuyết cổ điển (Carver / Man AHL), *Volatility Targeting* 2 chiều sẽ **tăng đòn bẩy lên `1,35×–1,5×` khi thị trường êm** và **giảm xuống `0,55×` khi thị trường bão**.
   - **Kiểm định thực nghiệm Naqex đã chứng minh sự khác biệt cốt tử trên Prop Firm:** Tăng đòn bẩy lên `1,35×` lúc thị trường êm làm **tăng vọt Daily DD (`1,77% → 2,39%`)** ngay ngày đầu tiên biến động quay trở lại đột ngột (*volatility jump*). Ngược lại, **Phanh 1 chiều `[0,55, 1,00]`** (chỉ giảm cỡ lệnh khi biến động tăng, KHÔNG tăng quá `1,00×` lúc êm) đã kéo `PeakDD` của `PORT_9E` xuống **`4,89%`** và đưa xác suất cháy P1 xuống **`0,4%`** ([Pre-Holdout Audit §2.4](../../planning/research/PRE-HOLDOUT-READINESS-AND-BLINDSPOT-AUDIT-20261123.md)).

---

## 4. Nhận diện Chuyển đổi Chế độ Vĩ mô (*Macro Regime-Shift Detection*)

Một chiến lược không bao giờ "kiếm tiền đều mọi tháng". Trên dữ liệu `2018–2024`, chính `PORT_7E` lãi cực mạnh ở các năm có sóng vĩ mô (`2018: +11,4%`, `2020: +13,5%`, `2022: +18,4%`, `2024: +7,0%`, `2025–2026: +12,1%/năm`) và **đi ngang quanh `0%` đến `+2%` ở các năm thị trường ngủ yên (`2019: -0,2%`, `2021: +1,9%`, `2023: +2,1%`)**.

### 4.1. Bốn chế độ vĩ mô chính & Tác động lên danh mục Naqex

| Chế độ Vĩ mô (*Macro Regime*) | Đặc trưng thị trường dễ quan sát | Hành vi kỳ vọng của **Nhánh #1 (`PORT_7E` FX/Index Breakout)** | Hành vi kỳ vọng của **Nhánh #2 (`C1/C2` Crypto Spot)** |
|---|---|---|---|
| **1. Xu hướng Vĩ mô / Lệch lãi suất mạnh** *(vd 2022 Fed tăng lãi suất, 2024–2026)* | Chênh lệch lãi suất NHTW giãn rộng, `ATR` trung bình–cao, breakout đi liền mạch | **Ăn mạnh nhất (`+10%..+18%/năm`)**, đặc biệt `USDJPY` và `US100` | Nếu tiền chặt (2022): nằm im ở **Cash** bảo toàn vốn (`MaxDD < 10%`); nếu thanh khoản nới: ăn xu hướng tăng |
| **2. Ngủ yên / Nén biên độ (*Low-Vol Chop*)** *(vd 2019, nửa đầu 2021, 2023)* | NHTW giữ nguyên lãi suất, biên độ ngày thu hẹp, phá vỡ giả liên tục | **Đi ngang (`-1%` đến `+3%/năm`)** — không phải chiến lược hỏng, chỉ là thiếu nhiên liệu biến động | Thường tích lũy chậm hoặc ăn sóng riêng của altcoin dẫn dắt (`C2_XSEC`) |
| **3. Sốc Khủng hoảng / Hoảng loạn (*Crisis Shock*)** *(vd COVID 03/2020, Gilt 09/2022)* | VIX vọt `> 30–40`, tương quan các tài sản rủi ro dồn về `+1`, spread giãn | Nhờ `Worst-5% Tail Correlation = -0,11` và `Downside Vol Brake`, `PORT_7E` sống khỏe và ăn mạnh các cú mở rộng 1 chiều | Tự động rút về Cash khi giá gãy dưới xu hướng (`SMA100` / `TSMOM < 0`) |
| **4. Đảo chiều cấu trúc / Bẫy gấu kéo dài (*Grinding Bear*)** *(vd Crypto 2025–2026)* | Giá giảm từng bậc xen kẽ cú hồi gắt (`dead cat bounce`) | Không ảnh hưởng trực tiếp tới FX/Index (`r = 0,02`) | Lãi mỏng hơn bull market nhưng vẫn bảo vệ vốn + ăn nhịp hồi có chọn lọc (`+6%..+9%/năm` trên OOS `2025–2026`) |

### 4.2. Ba công cụ phát hiện Regime Shift thực dụng (tránh overfit HMM phức tạp)
Các quỹ lớn thường dùng **Hidden Markov Model (HMM)** để suy đoán trạng thái ẩn (T1), nhưng với cá nhân chạy chuỗi giá ngắn, HMM nhiều tham số dễ **nhạy khởi tạo và chậm trễ (*label switching / look-ahead nếu không lọc causal*)**. Thay vào đó, hãy dùng **3 thước đo 100% nhân quả, dễ kiểm toán**:
1. **Tỷ số Biến động Nhanh/Chậm (`Vol_20d / Vol_120d`):** Nhận diện tức thời khi thị trường bước vào pha bão biến động (`> 1,3×`) để kích hoạt `Downside Vol Brake` hoặc nhận diện pha ngủ yên (`< 0,75×`) để quản trị kỳ vọng.
2. **Tương quan Trượt 60 ngày giữa các Nhánh (`Rolling 60d Corr`):** Nếu tương quan trung bình giữa các động cơ FX và US100 bất ngờ nhảy từ `~0,04` lên `> 0,40` kéo dài, đó là dấu hiệu một nhân tố vĩ mô duy nhất (ví dụ cú sốc USD toàn cầu) đang chi phối mọi tài sản → cần giảm rủi ro tổng danh mục.
3. **Bộ giám sát Thống kê Hậu kiểm (`CUSUM + Wald SPRT + Bootstrap Cone` trong [live_decay_monitor.py](../../tooling/ai-engines/quant_factory/live_decay_monitor.py)):** Đây là ranh giới khách quan duy nhất để phân biệt *"đang gặp năm ngủ yên 2019"* (`GREEN_WITHIN_EXPECTATION`) với *"lợi thế kinh tế đã thật sự biến mất"* (`RED_HALT_ALPHA_DECAY` khi `CUSUM <= -4,5σ` đồng thời `SPRT` bác bỏ `H0` hoặc rơi dưới bách phân vị `p05`).

---

## 5. Checklist 5 câu hỏi Kinh tế Bắt buộc trước khi cho AI viết bất kỳ chiến lược mới nào

1. **Đối tác chịu thiệt là ai?** (Quỹ tái cân bằng phiên, lệnh cắt lỗ cụm, người vay funding đòn bẩy, hay dòng vốn vĩ mô chậm?) — *Nếu câu trả lời là "chỉ báo RSI/MACD cắt nhau đẹp", HỦY NGAY!*
2. **Tại sao lợi thế chưa bị HFT quỹ tỷ đô xóa sạch?** (Do dung lượng nhỏ `< vài triệu USD`, hay khung giữ nhiều giờ mà HFT micro-giây không nắm giữ tồn kho?)
3. **Biên lãi kỳ vọng có lớn hơn ít nhất `3×` ma sát của đúng sàn đích không?** (Spread + Commission + Slippage Stress + Swap).
4. **Nó kiếm tiền ở chế độ thị trường nào và chấp nhận mất tiền ở chế độ nào?** (Ghi sẵn trước khi chạy backtest để khỏi sốc khi gặp pha đi ngang).
5. **Nó có trực giao (`r < 0,15`) với `PORT_7E` và `C1/C2` hiện có không?** — Nếu chỉ là bản sao đổi tham số của `USDJPY Breakout`, dừng ngay để tránh phình đa phép thử (`DSR` bị phạt nặng).
