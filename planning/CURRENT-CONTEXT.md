# Current context — Naqex Workspace

`25/11/2026 22:58 ICT` · `WORK: ASTRA-R4-UNPAID-OPTION-0USD-LOCKED | LIVE-NODE1: ONLINE-CONNECTED-FLAT | HOLDOUT 2025+ SEALED`

`GOAL-NOW: UNPAID-OPTION (0 USD) — BỎ QUA BLACK FRIDAY 30/11, GIỮ v1.01 KIỂM CHỨNG NGOẠI TUYẾN | SINGLE-TICKET ZERO-RETRY + MT5 v1.01 500ms/655ms & FULL-2024 ĐÃ CHỐT | LƯU Ý ĐIỀU KIỆN ĐỦ 18 TUỔI FTMO`

## 0. Phán Quyết Astra Vòng 4 (`UNPAID-OPTION — 0 USD`) & Kiểm Định Đúng 1 Vé

- **Phán quyết chính thức (đã áp dụng):** **`UNPAID-OPTION — 0 USD`** — giữ bản **`Naqex_Master_Prop7E.ex5 v1.01`** (`sha16=2e0006ad786bdad6`) để tiếp tục kiểm chứng ngoại tuyến trên Dev kín và **để ưu đãi FTMO Black Friday (`Thứ Hai 30/11/2026 16:00 ICT`) đi qua**. Ghi nhận điều kiện [đủ 18 tuổi của FTMO](https://ftmo.com/en/faq/who-can-join-ftmo/) để chủ sở hữu tự đối chiếu trước mọi kế hoạch trả phí trong tương lai.
- **Báo cáo kiểm định mới theo đúng yêu cầu Astra Vòng 4 (thay thế góc nhìn multi-retry cũ):** [ASTRA-ROUND4-UNPAID-OPTION-SINGLE-TICKET-LATENCY-AUDIT-20261125.md](research/ASTRA-ROUND4-UNPAID-OPTION-SINGLE-TICKET-LATENCY-AUDIT-20261125.md) *(hồ sơ vòng 4 cũ lưu đối chiếu: [ASTRA-ROUND4-BLACKFRIDAY-GONOGO-DOSSIER-20261126.md](research/ASTRA-ROUND4-BLACKFRIDAY-GONOGO-DOSSIER-20261126.md))*.
- **3 con số chốt cho ĐÚNG 1 VÉ — KHÔNG RETRY (`N = 10.000`, `v1.01 REL+HEADROOM`, `GUARD_ALL_ON`, `P1 Sprint 4x`, phí chuẩn `155 EUR = 165,08 USD`):**
  - **Ma sát `0,66×` (đo sống 28/28 lệnh):** `P(Payout 1)` 12m/24m/36m = `59,9% / 84,7% / 88,6%` · chờ trung vị **`273 ngày` (~9 tháng)** · tiền ròng 24m **`+825,7 USD` (Med `+815,9 USD`, `P<=0 = 15,3%`)**.
  - **Ma sát `1,00×` (chuẩn Dev):** `P(Payout 1)` = `46,6% / 73,0% / 79,2%` · chờ trung vị **`300 ngày` (~10 tháng)** · tiền ròng 24m **`+535,5 USD` (Med `+490,5 USD`, `P<=0 = 27,0%`)**.
  - **Ma sát `1,50×` (stress Astra):** `P(Payout 1)` = **`29,3%` (12m) / `51,2%` (24m) / `58,3%` (36m)** · chờ trung vị **`329 ngày` (~11 tháng)** · tiền ròng 24m **`+216,3 USD` (Med `+62,4 USD`, `P<=0 = 48,8%`)**.
  - **Chênh lệch Black Friday (`98,70 EUR`) vs Giá thường (`155 EUR`) trên 1 vé:** Vì FTMO hoàn `100%` phí ở payout đầu, trung vị người thắng bằng nhau; giảm giá chỉ tăng EV đúng **`+9,1 .. +29,2 USD`** — xác nhận hoàn toàn quyết định không vội mua.
- **Kiểm thử MT5 `v1.01` ở đúng độ trễ đo được (`500 ms` P50 / `655 ms` P90) & Full-2024 (`swap = 0,00 USD`, `492` tin đỏ, `clean = True`, `holdout = 0`):**
  - **`Q4 2024 Model=4 Real-Tick (20,02M ticks, P1 4x)`:** `50 ms` `+736,06 USD` (`PF 1,23, Sh 1,98`) -> **`500 ms` `+790,52 USD` (`PF 1,25, Sh 2,13, EqDD 6,24%`)** -> **`655 ms` `+799,56 USD` (`PF 1,25, Sh 2,15, EqDD 6,17%`)** — không suy giảm cấu trúc (chênh `+54..+63 USD` là nhiễu mở nến, không tính là lợi thế).
  - **`Full-2024 Model=1 @ 500 ms`:** `Funded 1x` **`+613,64 USD`** (`4/4` quý dương, `EqDD 4,06%`); `P1 4x` **`+1.418,65 USD`** (`4/4` quý dương, `minBal 9.595,79`, ngày sụp Yên `05/08/2024` `-3,14%`, đạt `+10%` ngày `2024-05-15` sau `134` ngày) ([Mũi 3 Receipt](research/MUI3-MASTER-PROP7E-REALTICK-2024-20261125.md)).
- **Điểm mù vẫn còn mở (`0 USD`):** Mới đo `1` phiên sống (`28/28` RT, P50 `0,615×` / P90 `0,897×`, Bootstrap 95% CI `[0,618×..0,704×]`), mới có `2` lệnh chạm SL sống trên `US100.cash` (chưa đủ chốt `450 pts` là trần đuôi tuyệt đối), và thời gian chờ payout đầu `9–11 tháng` còn dài cho mục tiêu thu nhập chính.

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
