---
doc_type: executive-briefing
title: "Bản Tin Sáng Wave-2 — Continuous Overnight Quant Factory (24/11/2026)"
date: 2026-11-24
status: complete-verified
health_score: 100
holdout_2025_sealed: true
order_send_live_money: 0
---

# Bản Tin Sáng Wave-2 — Toàn Cảnh Chiến Dịch Xuyên Đêm (`00:35 -> 11:30`, 24/11/2026)

> **Kết luận điều hành:** Toàn bộ kế hoạch **Wave-2 Continuous 5-Cycle Factory** (`11` checkpoint mã nguồn đã xác minh độc lập bởi `@verifier`, `0` lỗi tồn đọng + **5 mốc kiểm tra live xuyên đêm `02:30 -> 11:28`**) đã hoàn tất trọn vẹn với điểm vận hành **`100 / 100 GREEN_OPERATIONAL` (`PASS=6, WARN=0, PENDING=0, FAIL=0`)**. **Holdout `2025–2026`** giữ niêm phong 100% (`holdout_rows_analysed = 0`), **`0` mật khẩu/bí mật lọt vào Git/log/báo cáo**, và **`C:\Program Files\MetaTrader 5` (Exness Real)** hoàn toàn bất khả xâm phạm.

---

## 1. Bốn Đột Phá Lớn Nhất Của Đêm Qua

### 1.1. MT5 Real-Tick `Model=4` (`24/24` PASS) — Bắt Sống Lỗi Swap Thật Trên `FTMO-Demo`
- Trước khi nâng cấp, kiểm thử tick thật `Model=4` trên dữ liệu thật của **`FTMO-Demo 1515343166`** (`2024.09.01..2024.12.31`, đòn bẩy Swing `1:30`, 3 mức trễ `50 / 150 / 250 ms`) đã **phát hiện một lỗi thực chiến cực nguy hiểm** mà unit test thuần Python không thể thấy: `E4_US100_SESS40` dính **`swap = +12,69 USD`** đúng vào `2` ngày giao dịch rút ngắn (half-day `13:15 ET`) của NYSE là **Black Friday (`29/11/2024`, `+8,39 USD`)** và **Christmas Eve (`24/12/2024`, `+4,30 USD`)** do MT5 `SymbolInfoSessionTrade()` chỉ trả lịch tuần tĩnh, không biết ngày nghỉ nửa buổi; đồng thời phát hiện lệch `1` giờ múi NY+7 US DST (`UTC+3` vs `UTC+2`) trong `MQL_TESTER`.
- **Đã vá tận gốc** trong [Naqex_PropGuard.mqh](../tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh) (`IsUsEquityHalfDayNY` + NY+7 US DST cho tester) và `E4/E5`, biên dịch lại **`9/9` `.ex5` (`0 errors, 0 warnings`)**, chạy lại toàn bộ **`24/24` lượt Real-Tick `Model=4`**:
  - **`8/8` EA đạt `PASS`**, **`24/24` `swap == 0,00 USD`**, **`24/24` `log_clean == true`**.
  - `E4_US100_SESS40` đảo chiều từ `-36,83 USD / swap +12,69` thành **`+40,15 / +57,53 / +69,47 USD`, PF `1,36–1,65`, DD `0,70–0,83%`, `swap = 0,00`, khớp ngày Python tăng `58,3% -> 94,7%` (`18/18`)**.
  - Độ khớp tổng thể: `E1` khớp đúng `78 = 78` lệnh (`95,0%` Jaccard), `E3` lệch chỉ `0,84 USD`, `E6` `+92,77` vs `+90,08 USD`, `E7` `3 = 3`, `S6` `3 = 3`. Chi tiết: [MT5-REALTICK-RECONCILIATION-20261124.md](research/MT5-REALTICK-RECONCILIATION-20261124.md).

### 1.2. Chạy Thật 3 Luồng Live Overnight (`~8,5–10,8` Giờ Liên Tục, `100/100`)
- **Live 9-Chart `FTMO-Demo 1515343166` (sandbox cô lập):** Đã chạy liên tục **`509` chu kỳ (`~8,5` giờ)** xuyên qua rollover hàng ngày (`22:00 UTC`), tự định tuyến sang `Access Server 1b` (`203 ms`), **`100,0%` Heartbeat OK (`HbAge <= 6s`)**, `0` `orphan_no_sl`, `0` lỗi. Spread thực tế đo được cực chặt (`USDJPY 4 pts`, `EURUSD 1 pt`, `US100.cash 195 pts` chặt hơn cả lịch sử Dukascopy).
- **Live Binance Spot/Perp L2 Shadow:** **`130` chu kỳ (`~10,8` giờ)**, `100,0%` nằm dưới ngân sách trượt giá `5,0 bps` (trung vị `10k USD = 1,825 bps`, `50k USD = 4,247 bps`).
- **Live Binance Maker Passive-Limit Probe (`M2B`):** **`120` chu kỳ (`~10,1` giờ)** — khung `15m` đạt tỷ lệ khớp chạm xuyên trung vị **`97,44%`** và chi phí ròng trung vị **`3,106 bps <= 6,15 bps`** (`80,0%` chu kỳ đạt chuẩn `M2`). Chi tiết: [LIVE-OVERNIGHT-SHADOW-TCA-20261124.md](research/LIVE-OVERNIGHT-SHADOW-TCA-20261124.md).

### 1.3. Mở Rộng **11 Phòng Thí Nghiệm Dữ Liệu Mới (`Labs #1–#9` + `2B` + `3A/3B`)** — Không Đào Lại FX Dev Cũ

| Lab | Vũ trụ & Mục tiêu | Kết quả Research Council | Bài học chiến lược hành động ngay | Báo cáo |
|---|---|---|---|---|
| **Lab #1** | Crypto `100` coin `1H/15m` Intraday | `0/12` (thua phí taker `15 bps`) | Khai tử khung `< 4H` taker; giữ `S2` khung `4H` (`feat/causal-top15-sleeve2`) | [Lab #1](research/LAB1-CRYPTO-1H-INTRADAY-20261124.md) |
| **Lab #2** | Crypto `100` coin + `20` perp Stat-Arb (`15 bps`) | `0/12` taker | Phát hiện alpha thô thật ở `S3_FUND_DISLOC` & `S4_MKT_NEUT_MOM` | [Lab #2](research/LAB2-CRYPTO-STATARB-NEUTRAL-20261124.md) |
| **Lab #2B** | Crypto Stat-Arb Limit/Maker + Hysteresis (`N=20`) | `0/8` ngay · **`1` `CONDITIONAL_RETEST`** | **`M2B_BLEND_50_FUND_50_MOM`** (`+15,01%` Cl.B, `BE 4,51×`, `r vs S2 = -0,236`) -> đã chạy live shadow đạt `97,4%` fill / `3,11 bps`! | [Lab #2B](research/LAB2B-CRYPTO-MAKER-STATARB-20261124.md) |
| **Lab #3A** | FTMO Swing đa ngày dùng Swap thật FTMO (`Dev < 2025`) | `0/12` | Swap qua đêm CFD ăn `-4,5%..-14,4%`, xác nhận `PORT_7E` intraday `swap = 0` là tối ưu toán học trên FTMO | [Lab #3A](research/LAB3A-FTMO-SWING-REAL-SWAP-DEV-20261124.md) |
| **Lab #3B** | `10` tài sản FTMO mới (`USOIL/UKOIL/XAG/US30/JP225/...`) | `0/9` | Swap CFD `-8,6%..-30,1%` giết sạch `+17,75%` alpha xoay vòng -> phải chuyển xoay vòng sang **ETF/Futures không swap** | [Lab #3B](research/LAB3B-10NEW-ASSETS-DEV-20261124.md) |
| **Lab #4** | **40-ETF Multi-Factor + RSI(2) + Credit + VRP (`2005–2026`)** | **`4/4 APPROVE_FOR_INCUBATION`** | **Đột phá Own-Book (`Sleeve #4`):** `E40_APPROVED_EQW_ENSEMBLE` Cl.B **`+7,72%`, Sharpe `0,992`, MaxDD `15,66%`**, `GFC -2,8% / COVID -3,2%`, `r(S1) = -0,0155` | [Lab #4](research/LAB4-40ETF-MULTIFACTOR-VRP-20261124.md) |
| **Lab #5** | CME Micro Futures Prop (`Topstep 50K` / `Tradeify` vs FTMO/The5ers) | Phân rã `3` kịch bản (`5.000` nhánh MC) | Phanh phui bẫy phí `M6J` (`9,81%` D1 range) & lô `MNQ` tại `200 USD/R`; `PORT_7E` đi **FTMO + The5ers**, mở Topstep khi có bộ engine thuần CME | [Lab #5](research/LAB5-CME-FUTURES-PROP-STUDY-20261124.md) |
| **Lab #6** | Purged Embargo WF Meta-Labeling (AFML Ch. 3/7/10) | `REJECT_KEEP_RAW_WHITEBOX` | AUC `0,501–0,508`, Brier `< 0` -> giữ tín hiệu trắng nguyên bản, không nhồi ML thừa | [Lab #6](research/LAB6-META-LABELING-AUDIT-20261124.md) |
| **Lab #7** | RD-Agent-Q Tự Động (`auto_research_loop.py`) trên 40-ETF (`21` năm) | **`5/10 APPROVE_FOR_INCUBATION`** | **`L7_B1_MACRO_QUAD`** (`+12,74%`, Sh `1,062`) & **`L7_C3_MM17_VAR_CORE`** (`MaxDD 7,34%`, `GFC +6,64% / COVID +2,27% / 2022 -0,62%`); khai tử `4/4` Overnight Drift | [Lab #7](research/LAB7-OVERNIGHT-DRIFT-AND-RD-LOOP-20261124.md) |
| **Lab #8** | CME-Native Zero-Swap Futures (`ES/NQ/GC/CL/ZN/6E`, `2015–2026`) | `0/9` ngay (`L8_C3` qua `5/6` cổng) | Topstep `15:10 CT` cấm swing; lô 1 hợp đồng CME chỉ vừa vốn IBKR **`>= 100k USD`** -> ETF thắng tuyệt đối ở mức `< 100k USD` | [Lab #8](research/LAB8-CME-NATIVE-FUTURES-STRATEGY-LAB-20261124.md) |
| **Lab #9** | Multi-Coin Funding Carry v2 (`20` perp Binance) | `KEEP_S3A_V1` (`2/8` đỗ, `0/7` vượt v1) | Altcoin dính bẫy short-squeeze (`DOGE +405%`) & vòng quay phí; giữ **`BTC+ETH` (`S3A v1` Cl.B Sh `8,83`)** | [Lab #9](research/LAB9-MULTICOIN-FUNDING-CARRY-V2-20261124.md) |

### 1.4. Kiến Trúc Rủi Ro, Tiền Tệ VND & Hạ Tầng Thực Chiến Hoàn Chỉnh
- **Trần Phơi Nhiễm Nhóm CEX (`NCO_CexCap25 <= 25%`):** Kiểm thử sụp đổ sàn CEX `-50%` phát hiện `HRP` không trần sập **`-41,58%`** (`-2.121 tr VND` ở `200k USD`) và ngay cả trần đơn `35%` vẫn để `S3A + S2 = 41,5%` (`-21,05%`). Áp trần nhóm **`NCO_CexCap25`** kéo cú sốc `-50%` CEX xuống **`-12,89%`** (`-164,3 tr VND` @ `50k USD`, `-657 tr VND` @ `200k USD`), tái cân bằng **`Monthly_1st`** chỉ tốn `0,45–0,60 bps/năm` (`ERC_LW_CexCap25` OOS Sharpe `2,07`, Calmar `2,48`). Chi tiết: [QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md](research/QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md) · [MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md](research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md).
- **Kỹ Thuật Xếp Lệch Pha 2 Quỹ (`DUAL_2FIRM_STAGGER_42D + P1_Balanced`):** Với ngân sách phí khởi đầu chặt `500 USD`, xếp lệch `42` ngày giữa FTMO + The5ers cắt xác suất trượt kép cùng lúc từ **`19,8% -> 3,0%`** và xác suất cháy ngân sách phí từ **`24,1%` (`Sync + Sprint`) xuống `0,4%`**.
- **Bẫy Phí Tối Thiểu IBKR `0,35 USD`/lệnh & Công Cụ BasketTrader:** Dưới `25k USD`, rổ 38 ETF tốn `451–474 bps/năm` phí lệnh nhỏ -> dùng **`L7_TOP2_MACRO_VAR_EQW`** (`Cl.B +7,91%, Sh 1,03, 2022 -4,6%`) hoặc `S3B` + cổ phiếu lẻ (`--fractional on`); từ **`50.000 USD`** trở lên chuyển mượt sang lô nguyên `SUPER_ETF_6ENG_EQW` (`TE 18,1 bps/năm`, `15,2 bps/năm` phí). Xem [OWNBOOK-ETF-SUPER-SLEEVE-AND-IBKR-LOT-AUDIT-20261124.md](research/OWNBOOK-ETF-SUPER-SLEEVE-AND-IBKR-LOT-AUDIT-20261124.md) và `tooling/ai-engines/quant_factory/ibkr_macro_rebalancer.py`.
- **Hệ Sinh Thái Công Cụ Vận Hành 1 Lệnh (`OrderSend = 0`):**
  - **Local Web Control Room v2 (`127.0.0.1:8787`, `0` CDN):** `.\tooling\ai-engines\cockpit\launch_cockpit.ps1` (hiển thị live 3 daemon, Real-Tick `Model=4`, thanh trượt vốn `10k/50k/200k USD` tính ngay rủi ro Black-Swan bằng **triệu VND**, và sổ quỹ 3 ngăn `treasury_ledger.py` + báo cáo GIPS-lite).
  - **Điểm kiểm tra sức khỏe 1 lệnh:** `daily_ops_briefing.py` (`100/100`) & bảng điểm thi quỹ `prop_challenge_tracker.py`.
  - **Khuyến nghị nâng cấp Crypto repo:** Nhánh `feat/causal-top15-sleeve2` (`a72421b`, `264/264 PASS`) đã hoàn tất sạch trong `projects/quant-trading` (chưa push — chờ chủ nhân review/duyệt).
  - **2 Cẩm Nang Thực Chiến Tiếng Việt:** [Lộ trình Tăng trưởng 2026–2027 (`Phase 0 -> 5`)](../knowledge/playbooks/naqex-master-roadmap-2026-2027.md) · [SOP Triển Khai FTMO & The5ers](../knowledge/playbooks/ftmo-the5ers-live-launch-sop.md).

---

## 2. Ba Việc Chủ Nhân Làm Ngay Chiều Nay (10 Phút)

1. **Mở Control Room cục bộ để xem toàn bộ số liệu trực quan:**
   ```powershell
   .\tooling\ai-engines\cockpit\launch_cockpit.ps1
   ```
   Mở `http://127.0.0.1:8787` để kiểm tra telemetry trực tiếp của `FTMO-Demo 1515343166`, Binance Spot/Maker Shadow, phân bổ `NCO_CexCap25` và thanh trượt rủi ro VND.
2. **Giữ `FTMO-Demo 1515343166` tiếp tục chạy đủ `14` ngày Free Trial (đang chạy sẵn ở phiên nền):** Chiều/tối nay phiên Âu (`14:00+`) và phiên Mỹ (`20:30+`) là khung giờ `E2..E7` và `S6` phát lệnh chính; mỗi sáng chạy `daily_ops_briefing.py` và `prop_challenge_tracker.py --profile ftmo_swing_10k` để chấm điểm tự động.
3. **Gửi email xác nhận `The5ers Terms §11` (`0 USD`):** Dùng mẫu thư soạn sẵn trong [THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md](research/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md) gửi trước cho Support The5ers trong lúc chờ đủ 14 ngày Free Trial FTMO, sẵn sàng kích hoạt kế hoạch **`DUAL_2FIRM_STAGGER_42D + P1_Balanced`** (`0,4%` rủi ro cháy quỹ).
