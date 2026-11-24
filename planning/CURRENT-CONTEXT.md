# Current context — Naqex Workspace

`24/11/2026 18:15 ICT` · `WORK: WAVE-3-TOP1-PATCHES-COMPLETE | REVIEW: VERIFIER-APPROVED | LIVE-NODE1: HEALTHY + DEFENDER-ON`

`NODE1: FTMO-DEMO 1515343166 (open=1 E1 +7.52 USD, orphan=0, HbAge 9s) + CRYPTO SHADOW (208c, 1.789 bps) + MAKER PROBE (197c, 97.44% / 3.081 bps) + HEROKU EU OK | DEV: 9/9 EX5 + 418-ROW 4-CCY CSV READY FOR FLAT SYNC | HOLDOUT 2025+ SEALED`

## 1. Mục tiêu & Ràng buộc bất biến

- **Kế hoạch chủ đạo (North Star đã cập nhật Wave-3):** [TOP1-SOLO-QUANT-MASTER-PLAN.md](TOP1-SOLO-QUANT-MASTER-PLAN.md) — lộ trình 6 khía cạnh chạm chuẩn **Chuyên gia độc lập bậc nhất (Top 1%)**: tối ưu bằng **Tiền lời ròng kỳ vọng (EV)**, nhảy bậc **Smart-Tier (`5K -> 25K/50K/100K` + `60K 4%/8%`)** đẩy Sổ Vốn Riêng 5 năm gấp **`2,52×`** (`11,1k -> 28,0k USD` @ `1,5k` phí; `78,3k USD` ~ `2,0 tỷ VND` w/ vốn mồi `25k`), chẩn đoán bắt buộc **`R4 -> R3 -> R2 -> R1`**, Pod v2 trần CEX `<= 25%` (`NCO_CexCap25`), và hạ tầng tự nuôi từ lãi thật (tự trả VPS `35 USD/tháng` từ Tháng `20`, tránh mất `> 25k USD` trượt giá `1,5×`).
- **Ràng buộc an toàn bất biến:** [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json) khóa cứng (`holdout_rows_analysed = 0`); `OrderSend = 0` trên mọi công cụ nghiên cứu & mã nguồn `.mq5`; thử nghiệm MT5 chạy cô lập trên `naqex-node1`, tuyệt đối không chạm Exness Real (`C:\Program Files\MetaTrader 5`), `projects/vi-dubber` hay global config; `0` mật khẩu/bí mật trên đĩa hay Git.

## 2. Trạng Thái Đã Xác Minh (`Single Source:` [PORTFOLIO-REGISTRY.json](research/PORTFOLIO-REGISTRY.json))

| Hạng mục / Nhánh | Bằng chứng đã xác minh (Wave-2 & Wave-3) | Quyết định Hiện hành |
|---|---|---|
| **Home-VPS `naqex-node1` & Bảo mật** | Kiểm toán chỉ đọc `11:03 UTC`: `FTMO-Demo 1515343166` đang mở `1` lệnh `E1_USDJPY_TOKYO` (`+7,52 USD`, `orphan=0`, `HbAge 9s`), **Windows Defender ĐÃ BẬT (`RealTime=True, excl C:\Naqex`, Firewall `3/3`)**, NTP `< 0,1s`, `C:` trống `103,88 GB`, sao lưu `D:` `20261124`, `4/4` SYSTEM tasks `LastRes=0`, Heroku EU `OK` | **LIVE 24/7 — CHỜ PHẲNG ĐỂ ĐỒNG BỘ** ([Live Audit](research/LIVE-NODE1-TELEMETRY-AND-SHADOW-AUDIT-20261124.md)) |
| **4 Bản Vá Prop & Bộ Kit `9/9 .ex5`** | **HOÀN TẤT `9/9 .ex5` (`0` lỗi) + `418` dòng lịch tin đỏ `USD/GBP/EUR/JPY` đến `2027` (`build_red_news_calendar.py`)**: alias `NAS100`, pre-flatten `-5p..-2p15s` ngoài cấm cứng `±135s`, siết `SYMCAP 1,75%/2,00%/1,50%` (cắt cháy ngày `25,5% -> 4,7%`), `Dyn_ProfitLock` + reset Prague/Server, bộ fail-closed `4%/8%` cho The5ers `>= 50K`, `sync_updated_ex5_when_flat.ps1` tự kiểm phẳng + SHA-256 | **READY FOR FLAT SYNC** ([Tier & SYMCAP](research/PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.md)) |
| **Prop FX/Index (`A1_V1_LIVE8`)** | `24/24` Real-Tick PASS (`swap = 0`); **Labs #11 & #12 (`0/36` đỗ)** chứng minh `A1_V1_LIVE8` là **biên Pareto của CFD intraday `swap = 0`** → khóa dứt điểm săn bot CFD trong ngày, giữ dự phòng `A5` nếu trượt giá `>= 1,5×` | **PARETO FRONTIER LOCKED** ([Lab #11](research/LAB11-ORTHOGONAL-PROP-V2-DISCOVERY-20261124.md) · [Lab #12](research/LAB12-ORTHOGONAL-MOMENTUM-V2-DISCOVERY-20261124.md)) |
| **Crypto Shadow, Maker & Own-Book** | `crypto_shadow` `208/208` chu kỳ đạt `1,789 <= 5,0 bps`; `Maker M2B` `197` chu kỳ (`0,70/30` ngày, `15m` khớp **`97,44%`**, chi phí **`3,081 <= 6,15 bps`** — chờ đủ `30` ngày ~`2026-12-23`); `S2` sạch (`264/264 PASS`), `KEEP_S3A_V1` BTC+ETH, ETF IBKR (`< 25k` `L7_TOP2`/`S3B`, `>= 50k` `SUPER_ETF_6ENG`), Pod v2 `NCO_CexCap25` (`CEX <= 25%`) | **Gate-Driven / GO** ([Quỹ đạo 60m](research/TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.md) · [Pod v2](research/QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md)) |

## 3. Công Cụ Vận Hành & Pháp Lý Sẵn Sàng

- **Control Room (`127.0.0.1:8787`, `OrderSend = 0`):** Đã nâng cấp đủ bậc `25K/50K/100K` + `The5ers 20K`, đếm chính xác `3` ngày lãi `>= +0,50%`, và hiển thị dải chẩn đoán ngược **`R4 -> R3 -> R2 -> R1`** (đồng bộ cùng `prop_challenge_tracker.py`); kèm `treasury_ledger.py` (3-Bucket), `ibkr_macro_rebalancer.py` (BasketTrader CSV), `daily_ops_briefing.py`.
- **Tri thức & Pháp lý:** [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md) (bộ 2 email copy-paste + 5 bước diễn tập), [ftmo-the5ers-live-launch-sop.md](../knowledge/playbooks/ftmo-the5ers-live-launch-sop.md), [alpha-hypothesis-ledger.md](../knowledge/topics/alpha-hypothesis-ledger.md).

## 4. Bước Kế Tiếp Ngay Cho Chủ Sở Hữu (`Mốc 0`)

1. **Chờ tài khoản trên `naqex-node1` phẳng (`open_positions == 0`, tối nay sau `16:00–21:00 UTC`):** Chạy `sync_updated_ex5_when_flat.ps1` đẩy `9/9 .ex5` mới + lịch tin đỏ `418` dòng trước tin `US GDP + Core PCE` (`2026-11-25 13:30 UTC`).
2. **Gửi 2 email xin xác nhận chạy EA độc quyền** tới `support@ftmo.com` (FTMO Swing 2-Step) và `help@the5ers.com` (Terms §11 High Stakes `5K/20K`) từ [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md).
3. **Diễn tập mất kết nối `3` phút kiểm tra `@naqex_guard_bot`** ngay khi `open_positions == 0` *(Defender đã bật sẵn)*, rồi tiếp tục tích lũy đủ `10–15` lệnh đóng Free Trial `14` ngày & `30` ngày Crypto Maker `M2B` trước khi mở vé `The5ers High Stakes 5K`.
