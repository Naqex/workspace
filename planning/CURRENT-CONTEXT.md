# Current context — Naqex Workspace

`24/11/2026` · `WORK: NODE1-24/7-LIVE + TOP1-MASTER-PLAN-LOCKED | REVIEW: VERIFIER-APPROVED | LIVE-OPS: 100/100 GREEN`

`LIVE-NODE1: FTMO-DEMO 1515343166 (9/9 EX5, A1_V1_LIVE8) + 2 CRYPTO SHADOWS + HEROKU EU DEADMAN + TELEGRAM @naqex_guard_bot | DEV-PC: 0 BACKGROUND JOBS | HOLDOUT 2025+ SEALED`

## 1. Mục tiêu & Ràng buộc bất biến

- **Kế hoạch chủ đạo (North Star đã chốt `2026-11-24`):** [TOP1-SOLO-QUANT-MASTER-PLAN.md](TOP1-SOLO-QUANT-MASTER-PLAN.md) — lộ trình 6 khía cạnh hướng tới chuẩn **Chuyên gia độc lập bậc nhất (Top 1%)**: độ đều thực chiến `2,0–3,0`, lãi/sụt giảm mức `1×` đạt `+18%..+30% / 6%–8%`, tốc độ đậu Prop 2 vòng `1,5–3,0 tháng`, tối ưu bằng **Tiền lời ròng kỳ vọng (EV)** ở vùng rớt vòng thi `22%–35%` (vừa lên Funded hạ cứng `1,0×` -> cháy `< 1%`), chẩn đoán rủi ro bắt buộc **`R4 -> R3 -> R2 -> R1`**, `4–6` nhánh độc lập (Pod v2 `NCO_CexCap25`, trần CEX `<= 25%`), và **chi phí hạ tầng/dữ liệu (`30–150 USD/tháng`) chỉ mở khi tự nuôi từ lãi thật**.
- **Ràng buộc an toàn bất biến:** [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json) khóa cứng (`holdout_rows_analysed = 0`); `OrderSend = 0` trên mọi công cụ nghiên cứu & mã nguồn `.mq5`; thử nghiệm MT5 chạy cô lập hoàn toàn trên Home-VPS `naqex-node1` (`FTMO-Demo 1515343166`), tuyệt đối không chạm `C:\Program Files\MetaTrader 5` (Exness Real), `projects/vi-dubber` hay global config; `0` mật khẩu/bí mật lưu trên đĩa, Git hay log.

## 2. Trạng Thái Đã Xác Minh (`Single Source:` [PORTFOLIO-REGISTRY.json](research/PORTFOLIO-REGISTRY.json))

| Hạng mục / Nhánh | Bằng chứng đã xác minh | Quyết định Hiện hành |
|---|---|---|
| **Home-VPS `naqex-node1` 24/7 & Cloud Guard** | Đã chuyển sạch 3 tác vụ nền khỏi máy dev sang `naqex-node1` (`FTMO-Demo 1515343166` 9 biểu đồ `Session 1`, `Naqex_Crypto_Shadow_5m`, `Naqex_Crypto_Maker_Probe_5m`, sao lưu ngày `05:30`, đồng bộ giờ NTP `< 1s`). Heroku EU `naqex-deadman-eu` (`12 USD/tháng <= 13 USD` Student tới `2028-09-30`, `NAQEX_NODE1 = OK`) + Telegram `@naqex_guard_bot` live | **LIVE 24/7** ([naqex-node-ops](../.agents/skills/naqex-node-ops/SKILL.md)) |
| **Prop FX/Index (`A1_V1_LIVE8` vs v2)** | `24/24` Real-Tick `Model=4` PASS (`swap == 0,00 USD`); nghiên cứu v1 vs v2 chứng minh giữ `A1_V1_LIVE8` làm đội hình #1 (`+8,28%/năm` Dev, `7/7` năm dương, `EV/Phí +3,63×` FTMO / `+8,06×` The5ers, `Dyn_ProfitLock` cắt trung vị đậu `127d -> 113d`); loại `A3_PRUNE_6E`; giữ `A5_V2_ROBUST_TIER_9E_EUR` làm dự phòng khi trượt giá `>= 1,5×` | **KEEP `A1_V1_LIVE8`** ([v1 vs v2](research/PORTFOLIO-V1-VS-V2-ARCHITECTURE-STUDY-20261124.md) · [Real-Tick](research/MT5-REALTICK-RECONCILIATION-20261124.md)) |
| **Own-Book ETF (`Labs #4, #7` & IBKR)** | Lab #4 `4/4 APPROVE` (`E40_EQW` Cl.B `+7,72%`, Sh `0,992`, `r(S1) = -0,0155`); `< 25k USD` dùng `L7_TOP2`/`S3B` + cổ phiếu lẻ tránh bẫy phí `0,35 USD/lệnh`; `>= 50k USD` lô nguyên `SUPER_ETF_6ENG` | **GO — Own-Book Core** ([Lab #4](research/LAB4-40ETF-MULTIFACTOR-VRP-20261124.md) · [IBKR Audit](research/OWNBOOK-ETF-SUPER-SLEEVE-AND-IBKR-LOT-AUDIT-20261124.md)) |
| **Crypto & Futures (`S2, S3A, M2B, CME`)** | `S2` sạch không survivorship bias trên `projects/quant-trading:feat/causal-top15-sleeve2` (`264/264 PASS`); `KEEP_S3A_V1` BTC+ETH; `M2B` đang gom 30d shadow trên `naqex-node1` (chỉ mở khi `fill >= 70%`, `chi phí <= 6,15 bps`); CME Micros chỉ mở IBKR từ `>= 100k USD` | **Gate-Driven** ([Lab #2B](research/LAB2B-CRYPTO-MAKER-STATARB-20261124.md) · [Lab #8](research/LAB8-CME-NATIVE-FUTURES-STRATEGY-LAB-20261124.md)) |
| **Pod v2 `NCO_CexCap25` & Đa Quỹ Lệch Pha** | Trần nhóm **CEX `<= 25%`** khóa cú sốc `-50%` CEX ở `-12,89%`, tái cân bằng `Monthly_1st` (`ERC_LW_CexCap25` OOS Sh `2,07` / Cal `2,48`); `DUAL_2FIRM_STAGGER_42D + P1_Balanced` cắt double-fail còn `3,0%` và cháy quỹ phí `0,4%` | **GO** ([Pod v2](research/QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md) · [Multi-Prop](research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md)) |

## 3. Công Cụ Vận Hành & Tri Thức Đã Nâng Cấp

- **Control Room MetriX (`127.0.0.1:8787`, `OrderSend = 0`):** `tooling/ai-engines/cockpit/` đã nâng cấp đủ 4 khối chuẩn FTMO Account MetriX (`GET /api/prop-metrix`, kéo số sống từ `NAQEX_NODE1` qua Heroku, 3 khoảng đệm lỗ, 5 quy tắc quỹ, `MAE/MFE` từng lệnh, lịch PnL ngày và tin đỏ giờ Việt Nam `ICT` + `CẤM ±5m`); kèm `treasury_ledger.py` (3-Bucket), `ibkr_macro_rebalancer.py`, `daily_ops_briefing.py`.
- **Tri thức & Quy chuẩn Workspace:** [PROFILE.md](../knowledge/owner/PROFILE.md) + [DECISIONS-JOURNAL.md](../knowledge/owner/DECISIONS-JOURNAL.md) + [Lộ trình 2026–2027](../knowledge/playbooks/naqex-master-roadmap-2026-2027.md) + luật trình bày tiếng Việt đơn giản, dễ hiểu trong [.agents/rules/trading-workspace.md](../.agents/rules/trading-workspace.md).

## 4. Bước Kế Tiếp Ngay (Mốc 0 của [TOP1-SOLO-QUANT-MASTER-PLAN.md](TOP1-SOLO-QUANT-MASTER-PLAN.md))

1. Duy trì `naqex-node1` chạy yên 24/7 hết `14` ngày Free Trial `FTMO-Demo 1515343166` (đủ `10–15` lệnh đóng đối chiếu MetriX) và theo dõi qua Control Room (`.\tooling\ai-engines\cockpit\launch_cockpit.ps1`) + Telegram `@naqex_guard_bot`.
2. Gửi & lưu email xác nhận chạy EA độc quyền tới **FTMO (`support@ftmo.com`)** và **The5ers (`help@the5ers.com`, Terms §11)** theo mẫu [THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md](../tooling/ai-engines/exports/deployment_kit/the5ers_kit/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md).
3. Bật lại Windows Defender (`excl C:\Naqex`) trên `naqex-node1`, diễn tập 1 lần cảnh báo mất kết nối Telegram, rồi chuẩn bị bản đăng ký nghiên cứu **Nhánh Prop v2 khác kiểu phá vỡ** (dữ liệu `2018–2024`, giữ niêm phong `2025+`).
