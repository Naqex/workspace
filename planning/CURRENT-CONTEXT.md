# Current context — Naqex Workspace

`25/11/2026 22:05 ICT` · `WORK: WAVE3-FINALIZED-READY-FOR-ASTRA-R4 | REVIEW: PENDING-VERIFIER-6GATES | LIVE-NODE1: ONLINE-CONNECTED-FLAT`

`GOAL-NOW: FTMO BLACK FRIDAY GO/NO-GO (MON 30/11/2026 16:00 ICT / 10:00 CET) | LIVE FRICTION 28/28 PASS (P50 0.615x, 95% CI 0.618-0.704x) | MASTER_PROP7E v1.01 10/10 EX5 + MODEL=4 VERIFIED | HOLDOUT 2025+ SEALED`

## 0. Hồ Sơ Phán Quyết Chính (Astra Vòng 4 — Đã Hoàn Thiện `100%`)

- **Hồ sơ tổng hợp duy nhất để gửi GPT-6.2 Astra Vòng 4:** [ASTRA-ROUND4-BLACKFRIDAY-GONOGO-DOSSIER-20261126.md](research/ASTRA-ROUND4-BLACKFRIDAY-GONOGO-DOSSIER-20261126.md) (`READY_FOR_ASTRA_ROUND4_DECISION`, `0` ô chờ, kèm Prompt dán thẳng).
- **Hạn chót FTMO Black Friday CFD (`-30%` cho `FTMO 2-Step Standard`):** **Thứ Hai `30/11/2026` lúc `16:00 ICT` (`10:00 CET`)** (Mỹ nghỉ Lễ Tạ Ơn `26/11` & đóng sớm `27/11`, `v1.01` đã khóa lịch NYSE `23` ngày lễ/nửa phiên `2026–2027`).
- **Kết quả đo thực địa Mũi 1 & 2 (`28/28` RT = `56` legs, `3.734` dòng spread `5s` xuyên London + NY Overlap + `14:30 UTC` NY Cash Open):**
  - **`PASS_WITHIN_1_5X`** (`0` reject, `swap = 0,00 USD`, `0` vi phạm tin đỏ `13:30 UTC` `US_GDP_AND_CORE_PCE`, đã đo `2` lệnh SL cứng thật trên `US100.cash` lúc NY mở cửa).
  - **Hệ số Ma Sát Thực Core-4 (`7E`):** **`P50 = 0,615×` / `P90 = 0,897×`**; **10k Stratified Bootstrap 95% CI bảo thủ `[0,618× .. 0,661× .. 0,704×]`** (toàn bộ KTC 95% `< 0,75×`!); Page's CUSUM `0,00 / đỉnh 0,38` -> **`BÌNH THƯỜNG`**.
- **Chứng nhận `Naqex_Master_Prop7E.ex5 v1.01` (`sha16=2e0006ad786bdad6`):**
  - Biên dịch sạch **`10/10 .ex5` (`0 errors, 0 warnings`)**, vá trọn `V101-01..V101-07` ([Spec v1.01](research/MASTER-PROP7E-V101-RESTART-HYDRATION-SPEC-20261125.md) · [Đối khớp 1:1](research/MASTER-7E-VS-LEGACY-PARITY-AUDIT-20261125.md): **`0` drifts**, `32/32` tests PASS) — đặc biệt `V101-07` (`REL+HEADROOM`) xóa bẫy cát lún AMBER giúp `FTMO Std 98,70 EUR` đạt **`+844,9 USD` (`EV +8,04×`, `P<=0 8,7%`) ở `0,75×`** và **`+306,6 / Med +235,7 USD` ở `1,50×`** (`0,0%` cháy ngày).
  - **`Model=4` Real Ticks (`20,02M` ticks, `2024 Q4`, `1:100`, `4,0×` P1 + `PROFIT_LOCK`, `50 ms`, `slippage 35 FX / 450 US100`):** **`155` lệnh khớp 100%, `+736,06 USD (+7,36%)`, `PF 1,23`, `Sharpe 1,98`, `EqDD 6,27%`, `swap = 0,00`**, `492` tin đỏ, `hydrated=true` ([Mũi 3 Receipt](research/MUI3-MASTER-PROP7E-REALTICK-2024-20261125.md)).

## 1. Kiến Trúc Đã Khóa & Sổ R&D Trung Thực (`3 / 56 PASS`)

- **Kiến trúc `2` trụ cột gọn sạch (chấm dứt săn nhánh phụ sau `56` giả thuyết phi-CFD, `OrderSend = 0`, `< 2025-01-01`):**
  1. **Trụ cột 1 — Prop Cash-Flow (`PORT_7E` cố định `E1..E7`, `swap = 0`, khóa cụm hướng `USD/JPY/US100`):** Thứ tự đa quỹ `2026–2027` ([Prop Landscape 2026](../knowledge/topics/prop-firm-2026-landscape-and-multi-firm-portfolio.md)): **`#1 FTMO CFD 2-Step Standard`** (`0%` phí rút) -> **`#2 Darwinex Zero`** (Tháng `4–6` từ tiền rút FTMO, FCA/CNMV, native MT5) -> **`#3 The5ers High Stakes`** (Tháng `6–9`). Bỏ qua FTMO Futures Cyber Monday & Topstep (cấm bot Live/VPS).
  2. **Trụ cột 2 — Own-Book (`75% SGOV/IB01 + 25% Crypto Spot B06/B02 Shadow`, trần `CEX <= 25%`):**
     - Sổ cái trung thực ([Alpha Ledger](../knowledge/topics/alpha-hypothesis-ledger.md)): ETF `< 25K` (`0/10`), CME/ToM/Overnight (`0/10`), Macro ETF & `ETH/BTC` (`0/10`), Wave-3A Crypto Panic MR & Idle Rotation (`0/16`), Cash Merger Arb `< 100K` (`KILL`) -> giữ duy nhất **`B06/B02` Crypto Spot Breakout** (`3/10`, mã kín tại Layer 2 `private_vault/`).
     - Đo L2 Binance live `2026` (`0` API key, `3.000 USD`/coin) xác nhận Pool-50 Top-10 chỉ tốn **`16,41 / P90 18,79 bps` (BNB `-25%`) <= `20 bps`**; bộ collector bóng đã pass live smoke & idempotency (`OrderSend = 0`), **giữ shadow hậu-Black-Friday chờ sàn CASP VN (`05/2025/NQ-CP` & `32/2026/TT-BTC`)**.
     - Neo `75%` ([Own-Book & LD4 VPS](../knowledge/topics/ownbook-merger-arb-and-vps-scaling-2026.md)): `100% SGOV` (`< 50K`, QII `~0%`) -> `IB01` UCITS (`>= 50K–60K`, né Estate Tax `60K`; loại `UUP` do IRC `1446(f)` `10%` PTP). Giữ `naqex-node1` (`0 USD/tháng`) dưới `50K` Funded; chỉ lên Equinix LD4 (`32–45 USD/tháng`) từ `>= 75K–100K` Funded.
- **Bảo mật 2 tầng & Khóa an toàn bất biến:** [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json) niêm phong (`holdout_rows_analysed = 0`); Layer-2 Private Vault (`private_vault/` đồng bộ repo Private GitHub & bundle offline dự phòng) tách hoàn toàn khỏi Layer-1 Public (PR `#107` merged `main`, có chốt chặn CI `test_layer1_opsec_guard.py` + `workspace.yml` hardened).

## 2. Trạng Thái Hạ Tầng `naqex-node1` & `3` Repo Sản Phẩm (`projects/`)

| Thành phần | Trạng thái xác minh (`25/11/2026 22:05 ICT`) | Ghi chú & Điểm kiểm soát |
|---|---|---|
| **Home-VPS `naqex-node1`** | **`ONLINE GREEN / READY_FOR_CUTOVER (10/10)`** | Free Trial Demo phẳng (`open=0`, `orphan=0`, `KeepPrivate=1`, `AutoAdminLogon=1`, anti-reboot LTSC, `NTP -0,029s`, Heroku EU Deadman v4 `OK`, backup `D:` cùng ngày); Geo-IP **`VN` non-US**, `is_cgnat=false` *(nhắc kiểm 1 lần Double-NAT WAN router trước khi lên Funded)*. |
| **`projects/trader` (`Naqex/trader`)** | **5/5 PR tính năng (`#35–#39`) + Dependabot merged `main`** (`local c5a44c4f`, `15/15` CI PASS) | Vá TypeSafe Jev-1.14, overlay focus trap, auth `local-capability`, i18n/replay churn; báo cáo triage PR mở tại [TRADER-OPEN-PRS-TRIAGE-20261125.md](research/TRADER-OPEN-PRS-TRIAGE-20261125.md). |
| **`projects/quant-trading` (`Naqex/quant-trading`)** | **`master @ 25fc67d`** (`PR #2, #3, #4, #5` merged, `0` PR mở) | Có đủ `{download, backtest, soak-check, data-audit, stress-report}`, `ruff 0`, `pytest` 100% PASS, clean git. |
| **`projects/vi-dubber` (`Naqex/vi-dubber`)** | **`origin/main @ 5da3c65`** (`PR #2–#5` merged, **TẠM DỪNG theo chủ sở hữu**) | 4 file WIP cục bộ của chủ sở hữu & `work/job-8dc51f8a892aba21/` giữ nguyên 100% không chạm; worktree tạm đã dọn sạch. |
| **Giáo dục (`education/`)** | **`check_setup.py` exit `0`** | Đã thêm bộ sinh bài tập `education/tools/drill_generator.py` luyện kỹ năng `leverage_margin_vs_pnl` (`1:30` vs `1:100`) theo tiến độ thực. |

## 3. Bước Kế Tiếp Ngay Cho Chủ Sở Hữu (`26–30/11/2026`)

1. **Gửi Prompt Mục 7 trong [ASTRA-ROUND4-BLACKFRIDAY-GONOGO-DOSSIER-20261126.md](research/ASTRA-ROUND4-BLACKFRIDAY-GONOGO-DOSSIER-20261126.md) cho GPT-6.2 Astra Vòng 4** chốt phán quyết `GO / NO-GO`, cấu hình P1 (`4,0× Sprint` vs `3,0× Balanced` trên `v1.01`) và lịch kích hoạt sau Lễ Tạ Ơn Mỹ (`01/12/2026`).
2. **Gửi thư xác nhận EA `v1.01` tới `support@ftmo.com`** từ [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md) & kiểm màn hình checkout thật (`trader.ftmo.com`: đúng **`2-Step`**, **`10.000 USD`**, **`Standard`**, giá `62,30`/`98,70 EUR`, thẻ Visa/MC chính chủ còn hạn dài không phải thẻ ảo) theo Checklist 5 phút trong [Mũi 5 Pháp Lý VN](research/PROP-VN-PAYOUT-LEGAL-AND-VPS-COMPLIANCE-20261125.md).
3. **Nếu Astra chốt `GO` & chủ sở hữu mua vé trước `30/11 16:00 ICT`:** Đồng bộ phẳng bản **`v1.01`** (`10/10 .ex5` + `492` dòng CSV) lên `naqex-node1`, gắn duy nhất `1` chart `USDJPY M5` với preset `FTMO_Std10K_MasterProp7E_P1_*.set` theo [BLACKFRIDAY-FTMO-10K-ACTIVATION-CHECKLIST.md](../tooling/ai-engines/exports/deployment_kit/BLACKFRIDAY-FTMO-10K-ACTIVATION-CHECKLIST.md), kiểm WAN IP router sạch CGNAT trước khi lên Funded, và ghi ngay `OUT_OF_POCKET_FEE` vào `treasury_ledger.py`.
