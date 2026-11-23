---
doc_type: evergreen
domain: knowledge
topic: alpha-hypothesis-ledger
updated_utc: 2026-11-23
sources:
  - "T1 (Nội bộ): planning/research/README.md (Pass 23-28, Holdout 2025-2026, Crypto Sleeve #2)"
  - "T1 (Nội bộ): planning/research/ARCHIVE-INDEX-202611.md (Pass 1-22 & Chiến dịch V1-V26)"
  - "T1 (Nội bộ): planning/research/PORTFOLIO-REGISTRY.json (9 động cơ đóng băng)"
---

# Sổ cái Giả thuyết Alpha (`Pass 1 → Pass 32+` — Structured Experience Memory)

> Tài liệu này đóng vai trò **Bộ nhớ Kinh nghiệm có Cấu trúc (Experience Memory theo mẫu `FactorMiner` / `RD-Agent-Q`)** cho toàn bộ hệ thống Naqex: lưu lại **cả động cơ chiến thắng lẫn toàn bộ giả thuyết đã bị bác bỏ** từ chiến dịch V1–V26, Pass 1 → Pass 28, Holdout `2025–2026`, Nhánh #2 Crypto Spot và khung sẵn sàng cho Pass 29–32.
> **Luật bắt buộc trước mọi lượt R&D mới:** Mọi AI Agent phải tra sổ này trước khi đề xuất chiến lược mới để **tuyệt đối không lặp lại các họ giả thuyết đã chết**, tránh phình số phép thử `M` làm phạt nặng `DSR`.

---

## 1. Danh mục Động cơ Chiến thắng Đã Đóng băng (`PROMOTED / GO` — Holdout `2025–2026` `9/9` Dương)

Toàn bộ `9` động cơ Nhánh #1 đều tuân thủ **`swap = 0` intraday**, đo trên dữ liệu Native Tick M1 Bid/Ask (`2018–2024` Development → kiểm mù 1 lần duy nhất `2025–2026` Holdout không sửa tham số; [PORTFOLIO-REGISTRY.json](../../planning/research/PORTFOLIO-REGISTRY.json), [Phán quyết Holdout](../../planning/research/HOLDOUT-2025-2026-ONE-TIME-VERDICT-20261123.md)):

| Mã động cơ | Vai trò | Tài sản | Nguồn Pass | Cơ chế kinh tế cốt lõi | Dev (`2018–2024`) | **Holdout mù (`2025–2026`)** | Trạng thái |
|---|---|---|---|---|---|---|---|
| **`E1_USDJPY_TOKYO`** | `CORE` | `USDJPY` | Pass `5/6/7B/23` | Phá vỡ hộp phiên Á (`00:00–03:00 UTC`) sang phiên Âu (`03:00–10:00 UTC`), đóng `18:00 Helsinki` | `+10,92R/năm` Stress (`+0,50 pip`) | **`+48,05R`**, `PF 1,22`, `n=465` | `GO / FTMO_DEMO_SPEC_BOUND` |
| **`E2_USDJPY_EXP80`** | `CORE` | `USDJPY` | Pass `16/17` | Mở rộng động lượng `0,80 ATR` từ giá mở ngày (`07:00–17:00 UTC`), `SL 0,75 ATR` | `+34,75R` Stress (`7/7` năm, `12/12` ô 2D) | **`+11,16R`**, `PF 1,33`, `n=141` | `GO / FTMO_DEMO_SPEC_BOUND` |
| **`E3_GBPUSD_VH`** | `CORE` | `GBPUSD` | Pass `21/22` | Mở rộng `0,80 ATR` trên `GBPUSD` sau ngày biến động cao (`PrevRange >= 1,10 ATR`) | `+14,19R` Stress (`8/9` ô 2D, `rJPY=0,017`) | **`+0,28R`**, `PF 1,02`, `n=53` | `GO / FTMO_DEMO_SPEC_BOUND` |
| **`E4_US100_SESS40`** | `CORE` | `US100.cash` | Pass `24/27` | Tiếp diễn đà phiên sáng NYSE (`09:30–11:30 ET`, move `>= 0,40 ATR`) → đóng `15:55 ET` | `+14,14R` Stress (`9/12` ô 2D, `r3E=-0,004`) | **`+9,47R`**, **`PF 1,57`**, `n=101` | `GO / FTMO_DEMO_SPEC_BOUND` |
| **`E5_US100_RS1130`** | `CORE` | `US100.cash` vs `US500.cash` | Pass `26/27` | Sức mạnh tương đối Tech (`US100` dẫn dắt `US500`) tại `11:30 ET`, `SL 0,75 ATR` | `+12,20R` Stress (`6/7` năm, `BUY/SELL` cân bằng) | **`+7,39R`**, **`PF 2,87`**, `n=42` | `GO / FTMO_DEMO_SPEC_BOUND` |
| **`E6_EURJPY_VOLCOMP`** | `CORE` | `EURJPY` | Pass `28` | Nén biến động (`R5/R20 < 0,85`) → bung `0,75 ATR` (`07:00–17:00 UTC`) | `+13,2R` (A `+6,0` / B `+7,2`, `r5E=+0,085`) | **`+0,25R`**, `PF 1,02`, `n=47` | `GO / FTMO_DEMO_SPEC_BOUND` |
| **`E7_USDJPY_NY10ET`** | `CORE` | `USDJPY` (`US100`+USD) | Pass `28` | Đồng thuận liên thị trường `US100 + rổ USD` lúc `10:00 ET` (né hoàn toàn tin `08:30 ET`) | `+7,3R` (`6/7` năm, **`9/9` ô 2D**, `r5E=-0,003`) | **`+2,61R`**, **`PF 1,70`**, `n=32` | `GO / FTMO_DEMO_SPEC_BOUND` |
| **`S6_FX_USD_BSK`** | `SATELLITE_P1` | `MULTI_FX` | Pass `26` | Rổ USD vĩ mô lúc `12:00 UTC` chọn cặp mạnh nhất ngoài Yên (`min_z 0,35`) | `+9,99R` Stress (`5/7` năm, lệch chiều SELL) | **`+1,60R`**, `PF 1,11`, `n=51` | `GO (Bật P1, tắt ở Funded)` |
| **`S7_XAU_EXP120`** | `SATELLITE_P1` | `XAUUSD` | Pass `15/16/23` | Mở rộng biến động `1,20 ATR` trên Vàng (`swap = 0`, `07:00–17:00 UTC`) | `+11,83R` Stress (`r3E=0,092`, lot sàn hạn ở 10k) | **`+11,48R`**, **`PF 2,58`**, `n=52` | `GO (Vệ tinh P1 / Personal)` |
| **`C1_TSMOM_VOL20`** | `SLEEVE_2` | Crypto Spot (`5` coin) | Study `23/11` | Xu hướng chuỗi thời gian đa coin + Vol-Target `15%` (`t → t+1`, `0` đòn bẩy) | `CAGR +14,98%`, `MaxDD 11,04%`, `Sharpe 1,66` | **OOS `2025–2026`: `+5,98%/năm`**, `MaxDD 6,46%` | `CONDITIONAL` *(chờ bỏ survivorship bias)* |
| **`C2_XSEC_TOP2_TREND`** | `SLEEVE_2` | Crypto Spot (`5` coin) | Study `23/11` | Top-2 coin dẫn dắt + lọc xu hướng `BTC SMA100` (`t → t+1`, `0` đòn bẩy) | `CAGR +20,34%`, `MaxDD 13,87%`, `Sharpe 1,67` | **OOS `2025–2026`: `+8,98%/năm`**, `MaxDD 8,21%` | `CONDITIONAL` *(chờ bỏ survivorship bias)* |

**Tổng hợp cấp Danh mục đã xác minh:**
- **`PORT_7E + SYMCAP_100 + Red-News ±5m`:** Holdout `2025–2026` đạt **`+12,70%/năm`, `PeakDD 6,55%`, `DailyDD 1,48%`, `Calmar 1,94`** (`GO`).
- **`PORT_9E_INVDD_SYMCAP_100`:** Holdout `2025–2026` đạt **`+12,28%/năm`, `PeakDD 7,46%`, `DailyDD 1,18%`, `Calmar 1,65`** (`GO`).
- **One-Person Quant Pod (`FX7E 1,5×` + `C1/C2 0,75×`):** Tương quan `r = +0,016..+0,021`, đạt **`Sharpe 1,91–1,99`, `Calmar 2,09–2,36`** ([Crypto Sleeve Study](../../planning/research/CRYPTO-SLEEVE2-AND-QUANT-POD-STUDY-20261123.md)).

---

## 2. Nhóm Dự trữ Cá nhân (`TIER_2_PERSONAL_VAULT` — Có Edge thật nhưng KHÔNG hợp luật FTMO)

Giữ lại cho giai đoạn **Sổ Vốn Riêng (Pha 4)** với broker **Swap-Free** hoặc không bị trần margin/swap của FTMO:

| Giả thuyết / Mã | Pass | Bằng chứng thực nghiệm | Lý do không đưa vào lõi FTMO |
|---|---|---|---|
| **`NEN006 XAUUSD`** (strategy-intel) | Pass `14/23` | Native M1 thật: Exness Swap-Free **`+28,18R`**, FTMO sau `-16.286 USD/lot` Swap còn `+15,66R`, `r3E = -0,052` | Swap `3×` FTMO ăn gần nửa lợi nhuận; hợp sổ cá nhân Swap-Free hơn |
| **`IND026 XAUUSD`** (strategy-intel) | Pass `14/23` | Native M1 thật: FTMO `+10,62R`, Exness Swap-Free `+19,70R`, `3/3` ô ±30% dương | `FDR q = 0,416` và không nâng Calmar FTMO đủ mạnh |
| **`US500_IBS_OVERNIGHT_LONG` & `OVERNIGHT_DRIFT`** | Pass `19` | Trên **Exness Swap-Free**: `+9,40R` và `+8,02R` | Trên **FTMO Swing**, Swap chỉ số `-138,03` (`3×` thứ Sáu) ăn `-596` đến `-2.003 USD` → kéo sang âm `-6,42R`! |
| **`EXP_DAILY_OPEN_120 GBPUSD`** & **`VIR024 USDJPY`** | Pass `16/17` | `+4,95R` (`5/7` năm) và `+16,27R` (`p=0,049`) | Yếu hơn hoặc trùng vai trò với `E2/E3`; giữ làm tham chiếu phụ |

---

## 3. Nghĩa trang Giả thuyết Đã Bác bỏ (`KILLED / EXHAUSTED` — TUYỆT ĐỐI KHÔNG LẶP LẠI)

Bảng tổng hợp đầy đủ toàn bộ các họ giả thuyết đã bị khai tử một cách khoa học từ **V1–V26** và **Pass 1 → Pass 28** ([ARCHIVE-INDEX-202611.md](../../planning/research/ARCHIVE-INDEX-202611.md)):

| Đợt / Pass | Họ giả thuyết đã thử | Quy mô quét & Dữ liệu | Kết quả thực đo | Nguyên nhân gốc bị khai tử (*Kill Reason*) |
|---|---|---|---|---|
| **V1–V26 & Pre-Pass Stage-0** | `EURUSD RSI37` (H1/tick), `EURUSD F2` đảo hướng, `US500 VIX Divergence`, `US500 LETF AUM`, `EURUSD COT`, `EURUSD US 2Y Rates`, `Oil/WTI → USDCAD`, `WTI EIA 5m Fade`, `EURUSD Pre-ECB R056`, `EURUSD Treasury Auction`, `XAU Real Yield London`, `AUD Fixing`, `US500 Calendar 60/40`, `US500 Cash Session BUY`, `DAX/Nikkei Close`, `BTCUSD Daily Momentum`, `BTCUSD Low-Funding Tail`, `R029 FX Carry`, `Stock ORB 5m (TSLA/KO/TWTR)`, `V4_Harvest / V16-V26 BASE_GUARD` | Hàng trăm ô Stage-0 + replay tick + `120.000` MC ledgers (`2018–2024`) | `0` chiến lược đủ tốc độ vượt Challenge 2 vòng với DD an toàn (median V16 `47,08` tháng; hầu hết Stage-0 âm sau stress phí) | Ma sát phí CFD + biên lãi quá nhỏ (`< 1.000 USD/năm`), thiếu tần suất hoặc âm 1 trong 2 cụm A/B; **kích hoạt `OHLC_STANDARD_SEARCH_EXHAUSTED`**. |
| **Pass 1–4 & Pass 8–9** *(Bot Lab MQL5)* | Sàng lọc & audit thực chứng `63+` tín hiệu MQL5 công khai (`8` CSV Pass 3 = `24.725` lệnh; `6` CSV Pass 9 = `3.304` lệnh) | Dữ liệu lịch sử giao dịch thật từ MQL5 | `7/8` (Pass 3) và `5/6` (Pass 9) có hành vi **thêm lệnh khi lỗ (grid/martingale/thiếu SL)**; `0` hồ sơ đủ chuẩn FTMO trực tiếp (chỉ chắt lọc được DNA hộp Breakout `USDJPY` ở Pass 4 → sinh ra `E1`) | Rủi ro ẩn grid/martingale/thiếu SL phá luật DD cứng prop firm. **Không bao giờ tìm chiến lược mới bằng cách copy mù tín hiệu MQL5 top leaderboard.** |
| **Pass 6–7** | `XAUUSD` Tokyo-Box & `EURJPY/EURUSD/GBPUSD` Tokyo-Box H1 | H1 native FTMO `2018–2024` | Rớt toàn bộ Stage-0 (`0/4` ngoài `USDJPY`) | Hiệu ứng Tokyo-Box gắn chặt với dòng tiền thanh toán đồng Yên tại `USDJPY`, không dịch chuyển cơ học sang EUR/GBP/XAU. |
| **Pass 10–13** | **Toàn bộ họ ORB** (`GBPUSD London ORB`, `EURUSD London ORB`, `US500 NY ORB` explicit M1 `1.316` lệnh) | Tick M1 Bid/Ask (`204M+` tick) | `GBPUSD` âm Cụm B ở `+0,50 pip`; `US500 NY ORB` `-46,66R..-58,89R` (`1/7` năm dương) | **Đóng vĩnh viễn dòng ORB (`ORB_ENGINE2_SEARCH_EXHAUSTED`)**: trên CFD có spread/slippage, nhiễu quét 2 đầu quanh giờ mở cửa giết sạch ORB khung ngắn. |
| **Pass 12** | Bộ lọc `USDJPY Cost Hygiene` (chặn phí/hộp `<= 12%`) | `1.228/1.437` lệnh M1 `USDJPY` | Kéo Cụm A giảm `+6,50 → +1,47R/năm` và tăng DD | **Bác bỏ (`USDJPY_COST_HYGIENE_NOT_RETAINED`):** hộp nhỏ thường lại là ngày nén biến động tạo breakout lớn nhất. |
| **Pass 13** | `GBPUSD/EURUSD` **M15/M1 Liquidity Sweep** + `NEN022 Fakey H4` + `SEA003 XAU Turn-of-Month` | Native M1 Bid/Ask `2018–2024` | Sweep `-275R..-511R` (`p=0,42–0,78`); Fakey `-25,6R..-74,9R`; `SEA003` Swap 3× ăn `60,1%` lãi (`p=0,279`) | Cá nhân không có sổ lệnh L2 để đánh đảo chiều Liquidity Sweep trên FX; Fakey/SMC thuần nến không có edge; TOM vàng là *drift illusion* bị Swap ăn sạch. |
| **Pass 14 & 16 (Track 2)** | Toàn bộ `15/15` Top Leads + `8` mã H1 từ kho `strategy-intel` (`52 + 24 = 76` cặp tài sản) | Hot M1 Cache SSD (`249 MB`, `52.000` MC) | `0/76` đạt `TIER_1_FTMO_READY` (`73/76` vào `TIER_3_DEAD_NO_EDGE`, chỉ `3` vào `TIER_2`) | Đa số chiến lược retail phổ biến gãy dưới kiểm định Null Test + Stress Bid/Ask + Swap FTMO. **Đóng sổ 100% `strategy-intel`.** |
| **Pass 15** | `XAUUSD` Intraday tần suất cao (`1.235` lệnh) & `USDJPY/EURUSD` Carry Long/Short | Hot M1 Cache (`m=7`) | `0/7` sống sót (`XAU` gross `+29.484 USD` nhưng phí ăn `-64.803 USD` → `-38,2R`; `USDJPY` Carry âm Cụm A, `p=0,37–0,70`) | **Tần suất cao bị ma sát giết** (chứng minh phải nâng ngưỡng trigger lên `0,80–1,20 ATR` để lọc lệnh chất lượng); Carry FX thuần chỉ ăn theo trend lãi suất `2021–2024`. |
| **Pass 17 (Track 2)** | `US500` `EXP_DAILY_OPEN` (`4` cấu hình) | Native M1 Bid/Ask | Rớt `4/4` (`-10,1R..-18,0R`) | `US500` có đặc tính kéo ngược/đảo chiều trong ngày cao hơn FX; chỉ hợp động lượng **theo phiên cash NYSE** (`E4/E5` trên `US100`), không hợp mở rộng từ `00:00 UTC`. |
| **Pass 18** | `14` chiến lược học thuật & mã nguồn mở ngoài `USDJPY` (`WMR Post-Fix`, `GHLZ Last 30m`, `US500 Gap Fade NY`, `Intraday IBS`, `MQL5 NR4`, `XAU LBMA PM Drift`) | `4` tài sản (`US500`, `EURUSD`, `GBPUSD`, `XAUUSD`), BH-FDR `m=14` | **`0/14` Tier 1, `0/14` Tier 2, `14/14` DEAD** (`WMR` `-48R..-50R`, `GHLZ` `-55,2R`, `Gap Fade` `-76,6R`, `IBS` `-49,7R`) | Hiệu ứng vi mô học thuật trên thị trường tổ chức (phí gần `0`) **chết hoàn toàn dưới spread/commission CFD bán lẻ** (`ALL_14_REJECTED`). |
| **Pass 19** | `US500` Overnight (`m=6`, Swap FTMO) + **Clean-Room `SuperTrend(10, 3.0)`** (`m=5`) | Native M1 Bid/Ask | `US500` FTMO `0/6` (Swap ăn `-2.003 USD`); `SuperTrend` rớt `5/5` (`-41,1R..-76,7R`) | **Khai tử hoàn toàn `SuperTrend` retracement** (quá trễ, bị quét 2 chiều) và xác nhận cấm giữ Swing chỉ số chịu Swap âm trên FTMO. |
| **Pass 20** | **Positive-Swap Carry-Trend (`DON20_POS`)** trên `8` cặp FX dương Swap | H4 đối chiếu Native M1 + Prague floating equity | **`0/12` ô 2D** dương cả 2 cụm (`p_timing = 0,14–0,97`), ghép 3E hạ Calmar `0,65 → 0,57` | Lãi H4 ở Pass 19 chỉ là ăn may theo chuỗi xu hướng `2021–2024` và thu Swap không bù nổi drawdown giá. **Đóng nhánh FX Carry-Trend.** |
| **Pass 21 (Track A)** | **`GBPJPY` Native M1** (`EXP_DAILY_OPEN_080` & `30` spec) | `2,61M` phút Bid/Ask thật | Rơi từ `+9,28R` (ảo giác H4) xuống **`-9,52R` Stress (`0/12` ô 2D, `0/30` qua Cụm B)** | **Bài học vàng chống ảo giác H4:** Spread thực `1,4–2,4 pip` + nhiễu râu M1 của `GBPJPY` phá vỡ hoàn toàn tín hiệu từng nhìn đẹp trên nến H4. **Loại vĩnh viễn `GBPJPY` intraday.** |
| **Pass 23 (Track D)** | `78` cấu hình trên `US100` / `GER40` (sau khi vá bug khớp lệnh stop cùng phút ở `sim_index_trade`) | Native M1 Bid/Ask | `0/78` `TIER_1` (`GER40: 0/24` qua Cụm A) | Xác nhận bug giá `ask_open`/`bid_open` từng gây ảo giác `+42,97R`; `GER40` intraday breakout rất yếu. |
| **Pass 24 (Mean-Reversion)** | `M15_PDHL_SWEEP`, `M15_TWAP_PULLBACK`, `H1_VOL_SQUEEZE` (`m=128` đa khung) | `8` tài sản Native M1 | `0` ứng viên mean-reversion ngắn hạn qua cổng pháp y | Toàn bộ họ đảo chiều ngắn hạn (`M15/H1`) thất bại nhất quán trên CFD FX/Chỉ số. |
| **Pass 25** | Quét `136` cấu hình Single-Asset Breakout trên `4` tài sản mới (`AUDUSD`, `USDCAD`, `EURJPY`, `BTCUSD`) | `12` tài sản M1 Bid/Ask (`626,8 MB`) | **`0/136` `TIER_1`** (`USDCAD 0/34`, `AUDUSD 0/34`, `BTCUSD 0/34` vì spread CFD `68–120 USD` ăn sạch biên độ ngày) | **Đóng dòng Breakout đơn lẻ trên FX/BTC CFD:** Muốn tìm thêm động cơ mới phải chuyển sang tín hiệu **đa tài sản (Cross-Asset)** hoặc **điều kiện nén biến động** (và Pass 26/28 đã thành công rực rỡ nhờ bài học này!). |
| **Pass 27–28 & Pre-Holdout** *(Quản trị vốn/Hồ sơ)* | (a) Phanh chốt sớm `+7%` ở Challenge P1; (b) Giữ đệm `2%` trong Funded FTMO; (c) **Vol-Targeting 2 chiều `[0,55, 1,35]`**; (d) Hyper Growth 1-Step ở mức `2,5×–3,0×` | Numba `N=2.000` trên M1 thật | (a) Chậm thêm `+1,8m`, không giảm cháy; (b) Mất `-88 USD` vô ích; (c) Tăng Daily DD `1,77% → 2,39%`; (d) Cháy P1 `31%–43%`, `OOP95 = 780 USD` | Bác bỏ bằng số liệu thực nghiệm — chỉ giữ **Phanh Vol 1 chiều `[0,55, 1,00]`**, **`AMBER/RED` DD brake**, **`SYMCAP_100`**, và ưu tiên **2-Step** hơn 1-Step. |

---

## 4. Bản tóm tắt Quy luật Đúc kết (*Distilled Priors* cho AI Agents)

1. **Những gì THẮNG lặp lại trên dữ liệu M1 Bid/Ask thật:**
   - Động lượng/Mở rộng biên độ chọn lọc (`0,75–1,20 ATR`) gắn đúng cửa sổ dòng tiền tổ chức (`Tokyo→London`, `London→NY`, `NYSE Cash 09:30–15:55 ET`, `NY 10:00 ET`), `swap = 0`, cắt lỗ cứng `0,65–0,75 ATR`, thả lãi theo phiên.
   - Tín hiệu **liên thị trường (Cross-Asset Relative Strength / Risk-Flow)** ghép từ các tài sản đã đồng bộ (`US100/US500`, `US100+USD→USDJPY`).
   - Lọc chế độ biến động (`Vol-High` hoặc `Vol-Compression`) giúp nâng chất lượng lệnh mà không tăng tần suất.
   - Ở lớp tài sản thứ 2: **Crypto Spot khung ngày (`D1`, `0` đòn bẩy, Vol-Managed Trend / XSec)** gần như trực giao tuyệt đối (`r = 0,02`) với FX/Index Intraday.
2. **Những gì THUA lặp lại (cấm AI tốn công thử lại trên CFD Prop):**
   - Mọi dạng **Mean-Reversion / Liquidity Sweep / Fakey / ORB 5–15m / SuperTrend / WMR Post-Fix** trên CFD FX/Index.
   - Mọi chiến lược giữ qua đêm chịu **Swap âm 3× FTMO** (đặc biệt chỉ số Mỹ và Vàng).
   - Giao dịch intraday trên **BTC CFD** (spread `68–120 USD`) hoặc **`GBPJPY` M1** (spread `1,4–2,4 pip` + nhiễu râu).
   - Tin vào kết quả H4 khi chưa xác minh bằng M1 Bid/Ask thật (bài học `GBPJPY` Pass 21).

---

## 5. Vùng Chờ Cập nhật: Nhánh Alpha Tier 3–4 & Chiến dịch `Pass 29 → Pass 32` (`@quant-rnd`)

> **Lưu ý tính toàn vẹn:** Các mục dưới đây là khung đăng ký sẵn khớp đúng phạm vi làn `@quant-rnd` (tách biệt hoàn toàn với Holdout FX/Gold/Index `2025+` đã niêm phong `NATIVE_FTMO_HOLDOUT_LOCK.json`). **Chưa ghi số liệu cho tới khi hoàn tất biên nhận kiểm chứng và có phê duyệt của `@verifier`.**

### Tier 3 & Tier 4 — Các Nhánh Alpha Đa Tài Sản Mới (`Sleeve #2`, `Sleeve #3A`, `Sleeve #3B`)
- **`Sleeve #2` — Crypto Spot Không Survivorship Bias (`M3.1–M3.2`):**
  - **Trạng thái:** `PENDING_VERIFICATION`
  - **Phạm vi:** Rổ `40–50` đồng lịch sử Binance Spot (`D1` & `4H`, `2019–2026`, gồm cả coin từng lớn sau suy giảm) với bộ lọc thanh khoản trượt `30` ngày Top-N 100% nhân quả (`<= t` → `t+1`), kiểm `5` họ chiến lược (`TSMOM Vol-Targeted`, `Cross-Sectional Top-K + BTC Regime`, `Donchian Vol Breakout`, `4H Trend`, `Liquidity-Filtered Panic Reversion`) theo Cụm A (`2019–2023`) → Cụm B mù (`2024–2026`), phí `1×/2×`, `BH-FDR` & `DSR`.
  - **Biên nhận đích:** `CRYPTO-SLEEVE2-SURVIVORSHIP-FREE-20261124.md` *(chờ `@verifier` duyệt)*.
- **`Sleeve #3A` — Crypto Delta-Neutral Funding-Rate Carry (`M3.3`):**
  - **Trạng thái:** `PENDING_VERIFICATION`
  - **Phạm vi:** `Spot Long + 1× Perp Short` trên top `15–20` perpetual thanh khoản cao (`2020–2026`), trừ đủ phí vào/ra + turnover + luật thoát funding âm + đệm ký quỹ `2×` chống thanh lý, stress qua cú sốc `2021` & `2022 FTX`.
  - **Biên nhận đích:** `SLEEVE3A-FUNDING-RATE-CARRY-20261124.md` *(chờ `@verifier` duyệt)*.
- **`Sleeve #3B` — Macro ETF Trend & Risk Parity `18` Năm (`M4.3`):**
  - **Trạng thái:** `PENDING_VERIFICATION`
  - **Phạm vi:** `12` ETF vĩ mô toàn cầu (`SPY, QQQ, IWM, TLT, IEF, GLD, SLV, USO, UUP, EFA, EEM, DBC`, `2007–2026`) kiểm `TSMOM`, `Dual Momentum` và `Volatility-Parity All-Weather` theo Cụm A (`2007–2018`) → Cụm B mù (`2019–2026`), đo crisis alpha `2020` & `2022`.
  - **Biên nhận đích:** `SLEEVE3B-MACRO-ETF-TREND-18YR-20261124.md` *(chờ `@verifier` duyệt)*.

### Pass 29 (`M4.1`) — Khám phá Trực giao Vàng (`XAUUSD`) & Chỉ số Toàn cầu (`US500`, `US100`, `GER40`)
- **Trạng thái:** `PENDING` *(nghiêm ngặt chỉ trên Development `< 2025-01-01`, Holdout `2025+` SEALED)*
- **Phạm vi:** Kiểm `4` giả thuyết kinh tế intraday `swap = 0` (`London/NY Fix Drift`, `Opening-Range Vol Squeeze`, `Gold Asian->London Reversion`, `Index Auction Momentum`) trên Cụm A (`2018–2021`) → Cụm B mù (`2022–2024`), `BH-FDR` trên tổng `m_total`, Matched-Hold Timing Null, mục tiêu tương quan `r < 0,15` vs `PORT_7E`.
- **Biên nhận đích:** `PASS29-GOLD-INDEX-ORTHOGONAL-DEV-20261124.md` *(giữ nguyên cả kết quả âm nếu `0` ứng viên đạt)*.

### Pass 30 (`M4.2`) — Khám phá Mở rộng FX Intraday (`AUDUSD`, `USDCAD`, `EURJPY`, `GBPJPY`)
- **Trạng thái:** `PENDING` *(nghiêm ngặt chỉ trên Development `< 2025-01-01`, Holdout `2025+` SEALED)*
- **Phạm vi:** Kiểm `3` họ kinh tế (`Overnight Gap Fade`, `London Open Range Breakout + Vol Filter`, `Cross-Currency Relative-Strength Intraday`) trên Cụm A (`2018–2021`) → Cụm B mù (`2022–2024`), `BH-FDR`, Matched-Hold Timing Null, đo tác động lên thời gian đậu P1 & Calmar Cụm B.
- **Biên nhận đích:** `PASS30-FX-EXTENDED-ORTHOGONAL-DEV-20261124.md` *(giữ nguyên toàn bộ kết quả âm trung thực)*.

### Pass 31–32 (Tier 8) — Khám phá Chuyên sâu Tiếp nối Sau Tier 1–7
- **Trạng thái:** `PENDING`
- **Phạm vi:** Các đợt đào sâu kế tiếp được kích hoạt sau khi toàn bộ Tier 1–7 đã hạ cánh và được kiểm toán; kết quả dương lẫn kết quả âm sẽ được chưng cất thẳng vào mục 1–3 của sổ này và lập lại chỉ mục qua `brain_cli.py index`.
- **Biên nhận & Phán quyết:** *(Chờ hoàn tất Tier 1–7 & phê duyệt `@verifier`)*.
