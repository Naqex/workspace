# Current context — Naqex Workspace

`25/11/2026 23:24 ICT` · `WORK: READY-FOR-ASTRA-R5-BANKROLL-12-15M-RECHECK | LIVE-NODE1: ONLINE-CONNECTED-FLAT | HOLDOUT 2025+ SEALED`

`GOAL-NOW: TÁI THẨM ĐỊNH ASTRA VÒNG 5 (ĐỦ 18+, VỐN 12–15 TR VND, BẢNG 1/2/3 VÉ VÉ #1 BF + LỊCH SALE THẬT, 2 CASE 30/11 VS GIỮ BILL 14 NGÀY, MT5 v1.01 500/655ms & FULL-2024)`

## 0. Hồ Sơ Tái Thẩm Định Astra Vòng 5 (Cập Nhật Đủ 4 Điểm Mù Vòng 4)

- **Hồ sơ chính & Prompt sẵn dán gửi Astra Vòng 5:** [ASTRA-ROUND5-BANKROLL-12-15M-BF-AND-14D-BILL-DOSSIER-20261125.md](research/ASTRA-ROUND5-BANKROLL-12-15M-BF-AND-14D-BILL-DOSSIER-20261125.md) *(phản biện Vòng 4 lưu đối chiếu: [ASTRA-ROUND4-UNPAID-OPTION-SINGLE-TICKET-LATENCY-AUDIT-20261125.md](research/ASTRA-ROUND4-UNPAID-OPTION-SINGLE-TICKET-LATENCY-AUDIT-20261125.md))*.
- **Cập nhật điều kiện & khung vốn:** Chủ sở hữu xác nhận **đủ điều kiện `>= 18` tuổi**; khung vốn rủi ro **`12–15 triệu VND`** (`~462–577 USD` @ `26.000 VND/USD`); so sánh song song **2 case thời hạn** (**Case 1**: trả trước `30/11 16:00 ICT`, có biến thể giữ `0` lệnh `10–12 ngày` theo quyền hoàn `14 ngày` GTC; **Case 2**: tạo đơn giữ bill `Đang chờ ~14 ngày` sáng `30/11` tốn **`0 VND`**, đo thêm đuôi SL `US100.cash` xuyên NFP `04/12` + CPI `10/12`).
- **Tóm tắt bộ bảng `N = 10.000 × 36m` (`v1.01 REL+HEADROOM`, `GUARD_ALL_ON`, `P1 Sprint 4x`, vé #1 BF `98,70 EUR = 2,73 tr`, vé #2/#3 tính đúng lịch sale thật `155 EUR / -20% Xmas / -30% BF`):**
  - **Điểm ngọt trong vốn `12–15 tr` = `BF98 · Trần 2 vé` (Max `7,02 tr VND`, giữ lại `5–8 tr` tiền mặt):**
    - `0,66×` (đo sống): `P(Pay1 24m) = 91,9%` · chờ `284d` · ròng 24m Mean **`+22,97 tr`** / Med **`+22,27 tr`** · `Ruin 1,2%` · `EV/OOP +7,25×`.
    - `1,00×` (chuẩn Dev): `P(Pay1 24m) = 83,0%` · chờ `319d` · ròng 24m Mean **`+15,56 tr`** / Med **`+14,44 tr`** · `Ruin 3,1%` · `EV/OOP +4,45×` (vs Bỏ BF `+2,99×`, OOP Max `8,58 tr`).
    - `1,50×` (stress Astra): `P(Pay1 24m) = 63,2%` (vs `51,2%` 1 vé) · chờ `362d` · ròng 24m Mean **`+6,83 tr`** / Med **`+4,81 tr`** (`3×` trung vị 1 vé) · `Ruin 11,5%` (vs `35,8%` 1 vé) · `EV/OOP +1,61×` (vs Bỏ BF `+1,05×`). Thêm vé #3 (`11,32 tr`) làm giảm nhẹ Mean (`+258,9` vs `+262,7 USD`); chờ đợt sale mua vé #2 cũng bị tụt trung vị (`+131` vs `+185 USD`).
    - *Độ nhạy bill VN `62,30 EUR` (`1,73 tr`, gốc `89 EUR = 2,46 tr`):* `BF62 · Trần 2 vé` Max chỉ **`4,19 tr`**, tại `1,50×` đạt Mean `+7,70 tr` / Med `+5,07 tr` (`EV/OOP +2,97×`).
- **Kiểm thử MT5 `v1.01` ở đúng độ trễ đo được (`500 ms` P50 / `655 ms` P90) & Full-2024 (`swap = 0,00 USD`, `492` tin đỏ, `clean = True`, `holdout = 0`):**
  - **`Q4 2024 Model=4 Real-Tick (20,02M ticks, P1 4x)`:** `50 ms` `+736,06 USD` (`PF 1,23, Sh 1,98`) -> **`500 ms` `+790,52 USD` (`PF 1,25, Sh 2,13, EqDD 6,24%`)** -> **`655 ms` `+799,56 USD` (`PF 1,25, Sh 2,15, EqDD 6,17%`)** — không suy giảm cấu trúc (chênh `+54..+63 USD` là nhiễu mở nến, không tính là lợi thế).
  - **`Full-2024 Model=1 @ 500 ms`:** `Funded 1x` **`+613,64 USD`** (`4/4` quý dương, `EqDD 4,06%`); `P1 4x` **`+1.418,65 USD`** (`4/4` quý dương, `minBal 9.595,79`, ngày sụp Yên `05/08/2024` `-3,14%`, đạt `+10%` ngày `2024-05-15` sau `134` ngày) ([Mũi 3 Receipt](research/MUI3-MASTER-PROP7E-REALTICK-2024-20261125.md)).
- **Điểm mù còn mở:** Mới đo `1` phiên sống (`28/28` RT, `2` lệnh chạm SL trên `US100.cash`); **Case 2 (giữ bill `14` ngày, `0 VND`)** hoặc **Case 1B (giữ `0` lệnh `10–12` ngày)** cho phép đo thêm xuyên NFP `04/12` + CPI `10/12` trước khi đặt lệnh thật #1.

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

## 3. Bước Kế Tiếp Ở Chế Độ Ngoại Tuyến (`UNPAID-OPTION — 0 USD`)

1. **Giữ khóa `0 USD` và đối chiếu điều kiện tham gia:** Để hạn Black Friday `30/11/2026` trôi qua; kiểm tra rõ điều kiện đủ `18` tuổi & pháp lý trước khi lên bất kỳ kế hoạch mua vé Prop trả phí nào.
2. **Đóng nốt điểm mù phần đuôi trên Demo (`0 USD`, không đụng `Holdout 2025+`):** Tiếp tục giữ `naqex-node1` chạy shadow/Free Trial và đo thêm trượt giá SL thực tế trên `US100.cash` qua nhiều phiên/tuần (đặc biệt ngày tin đỏ & mở cửa Mỹ) thay vì dựa vào 1 phiên duy nhất.
3. **Giải bài toán thu nhập & thời gian chờ:** Nghiên cứu hướng rút ngắn thời gian chờ payout đầu dưới `9–11` tháng (hoặc nguồn thu song song không lệ thuộc chu kỳ 2-Step `10K`) trước khi cân nhắc bất kỳ lệnh mua vé nào.
4. **Dữ liệu đã lưu sạch trên Git:** `Naqex/workspace` `main @ 959597f` (PR `#109`, `3/3` CI PASS) + bổ sung báo cáo `UNPAID-OPTION`; `Miikey24s/naqex-private-vault` + `D:\NaqexBackup\naqex-private-vault.bundle` đã đồng bộ cùng bộ mô phỏng 1 vé `single_ticket_v101_audit/`.
