# Current context — Naqex Workspace

`24/11/2026` · `WORK: WAVE1(26/26)+WAVE2(CP1-CP12)-COMPLETE | REVIEW: VERIFIER-APPROVED-ALL-LANES | LIVE-OPS: 100/100 GREEN`

`RESEARCH: 9/9 EX5 (24/24 MODEL=4 REAL-TICK PASS, SWAP=0) · 11 NEW WAVE-2 LABS (LAB4 4/4 ETF + LAB7 5/10 RD-LOOP + LAB2B MAKER LIVE 97.4%/3.11bps) · POD V2 NCO_CEXCAP25 (-50% CEX -12.89%) · MULTI-PROP STAGGER 0.4% WIPEOUT · HOLDOUT 2025+ SEALED`

## 1. Mục tiêu & Ràng buộc bất biến

- **North Star:** Hệ thống **One-Person Quant Pod v2 (`NCO_CexCap25`, trần nhóm CEX `<= 25%`, tái cân bằng `Monthly_1st`)** kết hợp (1) **Prop FX/Index Intraday** (`PORT_7E`, `swap = 0`, Holdout `2025–2026` GO, `24/24` Real-Tick `Model=4` PASS), (2) **Crypto Spot sạch** (`feat/causal-top15-sleeve2`), (3) **Funding Carry `BTC+ETH`** (`KEEP_S3A_V1`), và (4) **Own-Book Zero-Swap ETF** (`S3B + S4 Lab #4` & `L7_TOP2` cho bậc `< 25k USD`, `SUPER_ETF_6ENG` lô nguyên từ `50k USD`) — vận hành qua Control Room cục bộ `127.0.0.1:8787` và [Bản tin sáng Wave-2](MORNING-BRIEFING-WAVE2-20261124.md).
- **Ràng buộc an toàn bất biến:** [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json) khóa cứng (`holdout_rows_analysed = 0`); `OrderSend = 0` trên mọi công cụ nghiên cứu & mã nguồn `.mq5` (`InpDryRunLogOnly = true`); chỉ chạy thử nghiệm MT5 trong sandbox Demo cô lập `.runtime/ftmo-demo-portable-1515343166/` (`FTMO-Demo 1515343166`, `ACCOUNT_TRADE_MODE_DEMO`), tuyệt đối không chạm `C:\Program Files\MetaTrader 5` (Exness Real), `projects/vi-dubber` hay global config; `0` mật khẩu/bí mật lưu trong Git/log/báo cáo.

## 2. Kết Quả Đã Xác Minh (`Wave-1 + Wave-2`, Single Source: [PORTFOLIO-REGISTRY.json](research/PORTFOLIO-REGISTRY.json))

| Hạng mục / Nhánh | Bằng chứng đã xác minh | Quyết định Hiện hành |
|---|---|---|
| **MT5 `9/9` `.ex5` & Real-Tick `Model=4`** | `24/24` (`8` EA × `50/150/250ms`) trên tick thật `FTMO-Demo 1515343166`: **`8/8 PASS`**, **`24/24 swap == 0,00 USD`** sau khi vá lỗi ngày lễ nửa buổi NYSE (`IsUsEquityHalfDayNY` — Black Friday & Xmas Eve) + NY+7 US DST (`E4` lật `-36,83 -> +40,15..+69,47 USD`, Jaccard `94,7%`) | **GO** ([Real-Tick Audit](research/MT5-REALTICK-RECONCILIATION-20261124.md)) |
| **Live Overnight Shadow (`~8,5–10,8h`)** | `FTMO-Demo 1515343166` (`509` chu kỳ, `100%` HB OK, `0` orphan, sống sót rollover); Binance L2 (`130` chu kỳ, `10k` slip `1,825 <= 5,0 bps`); Maker Probe `M2B` (`120` chu kỳ, `15m` fill `97,44%`, chi phí ròng `3,106 <= 6,15 bps`) | **100/100 GREEN** ([Overnight TCA](research/LIVE-OVERNIGHT-SHADOW-TCA-20261124.md)) |
| **Own-Book ETF (`Labs #4, #7` & IBKR Audit)** | Lab #4 `4/4 APPROVE` (`E40_EQW` Cl.B `+7,72%`, Sh `0,992`, `r(S1) = -0,0155`); Lab #7 `5/10` (`L7_B1 +12,74%`, `L7_C3` dương cả GFC/COVID, `2022 -0,62%`); IBKR `< 25k USD` dùng `L7_TOP2`/`S3B` + fractional (né bẫy phí `0,35 USD`), `>= 50k USD` lô nguyên `SUPER_ETF_6ENG` | **GO — Own-Book Core** ([Lab #4](research/LAB4-40ETF-MULTIFACTOR-VRP-20261124.md) · [ETF Super-Sleeve](research/OWNBOOK-ETF-SUPER-SLEEVE-AND-IBKR-LOT-AUDIT-20261124.md)) |
| **Crypto & Futures (`Labs #1, #2, #2B, #5, #8, #9`)** | `S2` promoted sạch trên nhánh local `projects/quant-trading:feat/causal-top15-sleeve2` (`264/264 PASS`); `KEEP_S3A_V1` BTC+ETH (Lab #9); `M2B` đang chạy 30d Maker shadow; CME Micros (`Lab #5/#8`) chỉ mở IBKR từ `>= 100k USD` (Topstep `15:10 CT` cấm swing) | **Disciplined Gating** ([Lab #2B](research/LAB2B-CRYPTO-MAKER-STATARB-20261124.md) · [Lab #8](research/LAB8-CME-NATIVE-FUTURES-STRATEGY-LAB-20261124.md)) |
| **Pod v2 `NCO_CexCap25` & Multi-Prop Scaling** | Trần nhóm **CEX `<= 25%`** kéo sốc `-50%` CEX từ `-41,58%` (`HRP`) xuống **`-12,89%`** (`-164,3 tr VND` @ `50k USD`), `Monthly_1st` (`0,45–0,60 bps/năm`, `ERC_LW_CexCap25` OOS Sh `2,07` / Cal `2,48`); `DUAL_2FIRM_STAGGER_42D + P1_Balanced` hạ cháy quỹ còn **`0,4%`** (double-fail `3,0%`) | **GO** ([Pod v2](research/QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md) · [Multi-Prop](research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md)) |

## 3. Hạ tầng, Công Cụ Vận Hành & Tri Thức Đã Nâng Cấp

- **Control Room & Treasury (`OrderSend = 0`):** `tooling/ai-engines/cockpit/` (`127.0.0.1:8787`, `0` CDN, tích hợp live 3 daemon + thanh trượt VND Black-Swan), `treasury_ledger.py` (3-Bucket + GIPS-lite), `ibkr_macro_rebalancer.py` (4 chế độ + xuất TWS BasketTrader CSV), `daily_ops_briefing.py`, `prop_challenge_tracker.py`, `auto_research_loop.py`.
- **MT5 Production Kit & Test Suite:** `9/9 .ex5` + `90 .set` (`10` hồ sơ) + lịch tin đỏ `2018–2027` + `Naqex_FreeTrial` 9-chart profile + `mt5_realtick_runner.py` + `mt5_live_monitor.py`; `conftest.py` tối ưu `xdist worksteal`.
- **Knowledge Vault (`knowledge/`):** `alpha-hypothesis-ledger.md` (14 mục Wave-2), [Lộ trình 2026–2027](../knowledge/playbooks/naqex-master-roadmap-2026-2027.md), [SOP FTMO/The5ers](../knowledge/playbooks/ftmo-the5ers-live-launch-sop.md), `brain_cli.py audit-data` (`0` broken links).

## 4. Bước Kế Tiếp Cho Chủ Nhân

1. Mở [MORNING-BRIEFING-WAVE2-20261124.md](MORNING-BRIEFING-WAVE2-20261124.md) và chạy `.\tooling\ai-engines\cockpit\launch_cockpit.ps1` (`http://127.0.0.1:8787`).
2. Theo dõi `FTMO-Demo 1515343166` đủ `14` ngày Free Trial qua phiên Âu/Mỹ và chạy `daily_ops_briefing.py` + `prop_challenge_tracker.py` hằng ngày.
3. Gửi email xác nhận `The5ers Terms §11` ([THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md](research/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md)) và xem xét merge/push nhánh `feat/causal-top15-sleeve2` trong `projects/quant-trading`.
