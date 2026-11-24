# Current context — Naqex Workspace

`25/11/2026 02:50 ICT` · `WORK: ASTRA-REDTEAM-F01-F20-CLOSED | REVIEW: VERIFIED | LIVE-NODE1: UNTOUCHED-HEALTHY`

`NODE1: FTMO-DEMO 1515343166 + CRYPTO SHADOW + MAKER PROBE + HEROKU EU OK | DEV: 9/9 EX5 v3.0 + 436-ROW 6-CCY CSV + HARDENED OPS/SIMS READY FOR FLAT SYNC | HOLDOUT 2025+ SEALED`

## 1. Mục tiêu & Ràng buộc bất biến

- **Kế hoạch chủ đạo (North Star đã gia cố sau kiểm toán độc lập Astra `F01–F20`):** [TOP1-SOLO-QUANT-MASTER-PLAN.md](TOP1-SOLO-QUANT-MASTER-PLAN.md) · [Báo cáo Astra](research/ASTRA-INDEPENDENT-REDTEAM-AUDIT-20261125.md) — tối ưu bằng **EV trung thực** (`DEPLOYED_PRESET_EXACT` `4,0x/7E`: FTMO 10K `5,51×` / `3,84×` tổng phí ở `1,0×`, `4,10×` ở `1,25×`, `2,61×` ở `1,5×`; The5ers 5K có sàn rút `150 USD` đạt `10,40×` ở `1,0×`), thang **Smart-Tier (`5K -> 25K/50K/100K` + `50K 4%/8%`, Gate-42 có đệm `2×` phí)** nhân gấp `2,02×` cùng trần `100k` và đạt trung vị Vốn Riêng 4 nhánh thuần đầu tư (`S2+S3A+S3B+S4`, `0` trùng Prop) sau `60` tháng **`49,1k USD`** (`1,0×`) / **`31,6k USD`** (`1,25×`) / **`13,3k USD`** (`1,5×`) tại ngân sách phí `1,5k USD`, tự nuôi VPS từ Tháng `16`.
- **Ràng buộc an toàn bất biến:** [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json) khóa cứng (`holdout_rows_analysed = 0`); `OrderSend = 0` trên mọi công cụ nghiên cứu & mã nguồn `.mq5`; thử nghiệm MT5 chạy cô lập trên `naqex-node1`, tuyệt đối không chạm Exness Real (`C:\Program Files\MetaTrader 5`), `projects/vi-dubber` hay global config; `0` mật khẩu/bí mật trên đĩa hay Git.

## 2. Trạng Thái Đã Xác Minh (`Single Source:` [PORTFOLIO-REGISTRY.json](research/PORTFOLIO-REGISTRY.json))

| Hạng mục / Nhánh | Bằng chứng đã xác minh (Wave-3 + Đợt vá Astra `F01–F20`) | Quyết định Hiện hành |
|---|---|---|
| **Home-VPS `naqex-node1` & Bảo mật** | Giữ nguyên vận hành không gián đoạn: `FTMO-Demo 1515343166`, **Windows Defender BẬT (`RealTime=True, excl C:\Naqex`, Firewall `3/3`)**, NTP `< 0,1s`, `C:` trống `103,88 GB`, sao lưu `D:`, Heroku EU `OK` | **LIVE 24/7 — CHỜ PHẲNG ĐỂ ĐỒNG BỘ** ([Live Audit](research/LIVE-NODE1-TELEMETRY-AND-SHADOW-AUDIT-20261124.md)) |
| **MQL5 v3.0 (`9/9 .ex5`) & Lịch `436` Dòng `6` Đồng Tiền** | Biên dịch sạch `9/9 .ex5` (`0` lỗi/cảnh báo) + `90` preset SHA-256: tách GV theo `ACCOUNT_LOGIN`, khóa đặt chỗ `SYMCAP` nguyên tử, `OrderCalcMargin <= 85%`, đệm `5%`, `STOPS_LEVEL`, fail-closed tin đỏ `436` dòng **`USD/GBP/EUR/JPY/AUD/CAD`** (đã sửa 4 ngày BLS 2026 + thêm RBA/BoC), `ClosePositionChecked` + `OnTimer(15s)` cả 8 EA, `S6` mark-traded sau khớp, FTMO Prague `Balance` vs The5ers `max(Bal,Eq)`, The5ers ProfitLock `+4%` + `SPX500` | **READY FOR FLAT SYNC** ([Astra Audit](research/ASTRA-INDEPENDENT-REDTEAM-AUDIT-20261125.md) · [Tier & SYMCAP](research/PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.md)) |
| **Vận Hành & Giám Sát Hardened (`F13, F17–F20`)** | Watchdog bắt clock skew tương lai & `terminal_connected=false`; `sync_updated_ex5_when_flat.ps1` chặn heartbeat cũ/lệch giờ + kiểm manifest + rollback; Heroku Deadman khóa `VIEW_TOKEN` fail-closed + retry Telegram khi lỗi + kiểm stale inner `utc_ts`; Control Room sửa `equity==0.0` & rõ trạng thái cầu nối; TCA Tracker đo adverse-only/`P90` + chặn `FILL_UNRESOLVED`/thiếu `swap_usd` | **VERIFIED IN PYTEST** ([Launch SOP](../knowledge/playbooks/ftmo-the5ers-live-launch-sop.md)) |
| **Prop (`A1_V1_LIVE8`) & Own-Book 4 Nhánh Thuần** | `A1_V1_LIVE8` biên Pareto của `36` biến thể CFD intraday đã thử; Vốn Riêng thuần `4` nhánh `NCO_CexCap25` (`S2+S3A+S3B+S4`, `0` trùng Prop, `0` lookahead, đủ 2 chiều phí) đạt `2020–2024` `CAGR +5,62%`, `Sharpe 1,18` (`OOS 2023–2024` `Sharpe 1,47`, `MaxDD 3,27%`); ghi nhận 2 ứng viên Own-Book `F15/F16` (`Cash Merger Arb`, `CME Corn Spread`) vào sổ cái | **Gate-Driven / GO** ([Quỹ đạo 60m](research/TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.md) · [Alpha Ledger](../knowledge/topics/alpha-hypothesis-ledger.md)) |

## 3. Công Cụ Vận Hành & Pháp Lý Sẵn Sàng

- **Control Room (`127.0.0.1:8787`, `OrderSend = 0`):** Đã vá `equity==0.0`, hiển thị rõ trạng thái cầu nối khẩn cấp, đủ bậc `25K/50K/100K` + `The5ers 20K`, đếm `3` ngày lãi `>= +0,50%`, và dải **`R4 -> R3 -> R2 -> R1`** đồng bộ `prop_challenge_tracker.py`.
- **Tri thức & Pháp lý:** [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md), [ftmo-the5ers-live-launch-sop.md](../knowledge/playbooks/ftmo-the5ers-live-launch-sop.md), [alpha-hypothesis-ledger.md](../knowledge/topics/alpha-hypothesis-ledger.md).

## 4. Bước Kế Tiếp Ngay Cho Chủ Sở Hữu (`Mốc 0`)

1. **Chờ tài khoản trên `naqex-node1` phẳng (`open_positions == 0`):** Chạy `sync_updated_ex5_when_flat.ps1` đẩy `9/9 .ex5` v3.0 + lịch tin đỏ `436` dòng `6` đồng tiền (đã tự kiểm nhịp tim tươi `<= 180s`, manifest & rollback).
2. **Gửi 2 email xin xác nhận chạy EA độc quyền** tới `support@ftmo.com` (FTMO Swing 2-Step) và `help@the5ers.com` (Terms §11 High Stakes `5K/20K`) từ [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md).
3. **Cập nhật Heroku config `NAQEX_VIEW_TOKEN` (bắt buộc sau bản vá `F20`)** khi triển khai bản Deadman mới, diễn tập mất kết nối `3` phút kiểm tra `@naqex_guard_bot`, rồi tích lũy đủ `10–15` lệnh đóng Free Trial `14` ngày & `30` ngày Crypto Maker `M2B` trước khi mở vé `The5ers High Stakes 5K`.
