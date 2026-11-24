# Current context — Naqex Workspace

`25/11/2026 03:17 ICT` · `WORK: NODE1-V301-AND-HEROKU-V3-DEPLOYED | REVIEW: VERIFIED | LIVE-NODE1: FLAT-AWAITING-1X-GUI-LOGIN`

`NODE1: 9/9 EX5 v3.01 + 436-ROW CSV + DISKIDLE=0 + KEEPPRIVATE=1 + HEROKU EU v3 LIVE (TELEGRAM VERIFIED) | HOLDOUT 2025+ SEALED`

## 1. Mục tiêu & Ràng buộc bất biến

- **Kế hoạch chủ đạo (North Star đã gia cố sau kiểm toán độc lập Astra `F01–F20`):** [TOP1-SOLO-QUANT-MASTER-PLAN.md](TOP1-SOLO-QUANT-MASTER-PLAN.md) · [Báo cáo Astra](research/ASTRA-INDEPENDENT-REDTEAM-AUDIT-20261125.md) — tối ưu bằng **EV trung thực** (`DEPLOYED_PRESET_EXACT` `4,0x/7E`: FTMO 10K `5,51×` / `3,84×` tổng phí ở `1,0×`, `4,10×` ở `1,25×`, `2,61×` ở `1,5×`; The5ers 5K có sàn rút `150 USD` đạt `10,40×` ở `1,0×`), thang **Smart-Tier (`5K -> 25K/50K/100K` + `50K 4%/8%`, Gate-42 có đệm `2×` phí)** nhân gấp `2,02×` cùng trần `100k` và đạt trung vị Vốn Riêng 4 nhánh thuần đầu tư (`S2+S3A+S3B+S4`, `0` trùng Prop) sau `60` tháng **`49,1k USD`** (`1,0×`) / **`31,6k USD`** (`1,25×`) / **`13,3k USD`** (`1,5×`) tại ngân sách phí `1,5k USD`, tự nuôi VPS từ Tháng `16`.
- **Ràng buộc an toàn bất biến:** [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json) khóa cứng (`holdout_rows_analysed = 0`); `OrderSend = 0` trên mọi công cụ nghiên cứu & mã nguồn `.mq5`; thử nghiệm MT5 chạy cô lập trên `naqex-node1`, tuyệt đối không chạm Exness Real (`C:\Program Files\MetaTrader 5`), `projects/vi-dubber` hay global config; `0` mật khẩu/bí mật trên đĩa hay Git.

## 2. Trạng Thái Đã Xác Minh (`Single Source:` [PORTFOLIO-REGISTRY.json](research/PORTFOLIO-REGISTRY.json))

| Hạng mục / Nhánh | Bằng chứng đã xác minh (Wave-3 + Đợt vá Astra `F01–F20`) | Quyết định Hiện hành |
|---|---|---|
| **Home-VPS `naqex-node1` & Bảo mật** | Đã bảo trì lúc phẳng (`open_positions = 0`, `E1` đóng phẳng `9.998,88 USD`, `0` swap): **đồng bộ xong `9/9 .ex5` v3.01 + CSV `436` dòng `6` đồng tiền + Watchdog/Sync mới + `DISKIDLE = 0` + `KeepPrivate = 1` + Heroku EU v3 (Telegram alert đã kiểm chứng sống!)**; Defender `RealTime=True` (`excl C:\Naqex`), NTP `< 0,1s`, `C:` trống `103,86 GB`, Crypto Shadow `318` / Maker `307` chu kỳ | **DEPLOYED — CHỜ ĐĂNG NHẬP 1 LẦN `FTMO-Demo` (Save password)** ([Live Audit](research/LIVE-NODE1-TELEMETRY-AND-SHADOW-AUDIT-20261124.md)) |
| **MQL5 v3.01 (`9/9 .ex5`) & Lịch `436` Dòng `6` Đồng Tiền** | Biên dịch sạch `9/9 .ex5` (`0` lỗi/cảnh báo) + `90` preset SHA-256: toàn bộ bản vá Astra `F01–F06` + `3` bản vá thực địa VPS (`FILE_SHARE_READ` + retry mở CSV tin đỏ khi `9` bot chạy song song, `IsAccountSynced` chặn khóa nhầm `kill_switch` lúc chưa đăng nhập, `Get-AncestorPath` sửa script sync trên đường dẫn nông) | **LIVE ON NODE1 (9/9 SHA MATCH)** ([Astra Audit](research/ASTRA-INDEPENDENT-REDTEAM-AUDIT-20261125.md) · [Tier & SYMCAP](research/PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.md)) |
| **Vận Hành & Giám Sát Hardened (`F13, F17–F20`)** | Watchdog bắt clock skew tương lai & `terminal_connected=false`; `sync_updated_ex5_when_flat.ps1` chặn heartbeat cũ/lệch giờ + kiểm manifest + rollback; Heroku Deadman khóa `VIEW_TOKEN` fail-closed + retry Telegram khi lỗi + kiểm stale inner `utc_ts`; Control Room sửa `equity==0.0` & rõ trạng thái cầu nối; TCA Tracker đo adverse-only/`P90` + chặn `FILL_UNRESOLVED`/thiếu `swap_usd` | **VERIFIED IN PYTEST** ([Launch SOP](../knowledge/playbooks/ftmo-the5ers-live-launch-sop.md)) |
| **Prop (`A1_V1_LIVE8`) & Own-Book 4 Nhánh Thuần** | `A1_V1_LIVE8` biên Pareto của `36` biến thể CFD intraday đã thử; Vốn Riêng thuần `4` nhánh `NCO_CexCap25` (`S2+S3A+S3B+S4`, `0` trùng Prop, `0` lookahead, đủ 2 chiều phí) đạt `2020–2024` `CAGR +5,62%`, `Sharpe 1,18` (`OOS 2023–2024` `Sharpe 1,47`, `MaxDD 3,27%`); ghi nhận 2 ứng viên Own-Book `F15/F16` (`Cash Merger Arb`, `CME Corn Spread`) vào sổ cái | **Gate-Driven / GO** ([Quỹ đạo 60m](research/TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.md) · [Alpha Ledger](../knowledge/topics/alpha-hypothesis-ledger.md)) |

## 3. Công Cụ Vận Hành & Pháp Lý Sẵn Sàng

- **Control Room (`127.0.0.1:8787`, `OrderSend = 0`):** Đã vá `equity==0.0`, hiển thị rõ trạng thái cầu nối khẩn cấp, đủ bậc `25K/50K/100K` + `The5ers 20K`, đếm `3` ngày lãi `>= +0,50%`, và dải **`R4 -> R3 -> R2 -> R1`** đồng bộ `prop_challenge_tracker.py`.
- **Tri thức & Pháp lý:** [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md), [ftmo-the5ers-live-launch-sop.md](../knowledge/playbooks/ftmo-the5ers-live-launch-sop.md), [alpha-hypothesis-ledger.md](../knowledge/topics/alpha-hypothesis-ledger.md).

## 4. Bước Kế Tiếp Ngay Cho Chủ Sở Hữu (`Mốc 0`)

1. **Đăng nhập lại `1` lần duy nhất vào `FTMO-Demo 1515343166` trên `naqex-node1` (RDP `192.168.1.28` / `100.72.70.18`) và tích `Save password`:** Bản `connector.ini` cũ đặt `KeepPrivate=0` nên chưa lưu mật khẩu sau khi khởi động lại; giờ đã sửa thành `KeepPrivate=1` nên sau 1 lần đăng nhập này mọi lần cúp điện/reboot về sau sẽ tự kết nối lại 100% tự động (và Heroku + Watchdog sẽ lập tức chuyển xanh `OK`).
2. **Gửi 2 email xin xác nhận chạy EA độc quyền** tới `support@ftmo.com` (FTMO Swing 2-Step) và `help@the5ers.com` (Terms §11 High Stakes `5K/20K`) từ [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md).
3. **Tiếp tục gom đủ `10–15` lệnh đóng Free Trial `14` ngày & `30` ngày Crypto Maker `M2B`** *(Heroku EU v3 + `NAQEX_VIEW_TOKEN` + cảnh báo Telegram `@naqex_guard_bot` đã kiểm chứng hoạt động thật!)* trước khi mở vé `The5ers High Stakes 5K`.
