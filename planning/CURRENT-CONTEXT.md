# Current context — Naqex Workspace

`25/11/2026 23:46 ICT` · `WORK: OWNER-DIRECTED-18D-SPRINT-TO-DEC13 | BILL-HOLD-NOV30 | LIVE-NODE1: ONLINE-CONNECTED-FLAT | HOLDOUT 2025+ SEALED`

`GOAL-NOW: QUYẾT ĐỊNH OWNER — TẠO ĐƠN GIỮ BILL BLACK FRIDAY NGÀY 30/11 (14 NGÀY -> HẠN ~13/12/2026) | DÙNG 18 NGÀY (26/11->13/12) TỐI ƯU HỆ THỐNG/CHIẾN LƯỢC CHO BÀI TOÁN 1 VÉ + ĐO ĐUÔI SL US100.cash XUYÊN NFP 04/12 & CPI 10/12 -> TỚI 12–13/12 MỚI CHỐT THANH TOÁN`

## 0. Quyết Định Chính Thức Của Chủ Sở Hữu & Lộ Trình Sprint `18 Ngày` (`26/11 -> 13/12/2026`)

- **Quyết định của chủ sở hữu (điều chỉnh đúng trọng tâm sau Astra Vòng 5):**
  - **KHÔNG** lấy trạng thái hôm nay (`25/11`) làm điểm chốt dừng sớm. Phản biện Astra Vòng 5 ([Hồ sơ Vòng 5](research/ASTRA-ROUND5-BANKROLL-12-15M-BF-AND-14D-BILL-DOSSIER-20261125.md)) được dùng làm **danh sách mục tiêu kỹ thuật phải giải xong trước ngày `13/12/2026`**.
  - **Mốc Thứ Hai `30/11/2026` (trước `16:00 ICT`):** Chủ sở hữu tạo đơn giữ bill Black Friday (`14 ngày`, hạn thanh toán `~13–14/12/2026`, `0 VND` bỏ ra ngay ngày `30/11`; hành động đặt đơn & thanh toán thuộc toàn quyền chủ sở hữu, AI giữ `OrderSend = 0`).
  - **Mốc quyết định thanh toán thật:** **`12–13/12/2026`** — chỉ chốt bấm trả tiền bill sau khi đã hoàn tất 3 mũi tăng tốc dưới đây trên Dev kín (`Holdout 2025+` NIÊM PHONG) + đo sống xuyên NFP & CPI.
- **3 mũi tăng tốc bắt buộc trong `18 ngày` (`26/11 -> 13/12/2026`):**
  1. **Mũi A — Đóng điểm mù trượt giá cắt lỗ (`SL`) của `US100.cash` trên Demo miễn phí (`0 VND`):** Lên lịch chạy `ftmo_demo_calibration_probe.py` trên Demo phụ xuyên nhiều phiên mở cửa Mỹ (`14:30 UTC`), trọng tâm **NFP `04/12`** và **CPI `10/12`** để thu tối thiểu **`>= 15–20` lần chạm SL thật trên `US100.cash`** (thay vì `2` lần) và chốt chính xác phân vị trượt giá P95/P99.
  2. **Mũi B — Tối ưu hóa chiến lược & tốc độ pha cho mục tiêu ĐÚNG 1 VÉ (`v1.01 -> v1.02`, Dev `2018–2024` kín):** Tấn công thẳng vào 2 con số Astra chê (`P(Pay1 12m) = 29,3%`, chờ `300–329d`, `P(net<=0 24m) = 48,8%` ở `1,50×`) — đặc biệt rà soát nút thắt **`P2` đang chạy quá chậm (`96–110` ngày chỉ để ăn `+5%` với cháy P2 chỉ `2,6%`!)**, tối ưu hóa tham số `P1/P2/ProfitLock/Funded` và kiểm định trên `Model=4` Real-Tick `500/655 ms` + Full-2024.
  3. **Mũi C — Cổng kiểm định chốt trước hạn bill (`12–13/12/2026`):** Chấm lại toàn bộ gói bằng chứng mới (`v1.02` + bộ đo SL `US100.cash` xuyên NFP/CPI) để chủ sở hữu quyết định thanh toán bill Black Friday (`62,30` hoặc `98,70 EUR`) hay bỏ bill (`0 VND`).
- **Nền kỹ thuật đã có sẵn (`v1.01`, `sha16=2e0006ad786bdad6`):** `10/10 .ex5` sạch `0/0`; `Q4 Model=4` `20,02M` tick thực dương ở `50/500/655 ms` (`+736 / +791 / +800 USD`); `Full-2024 Model=1 @ 500 ms` `4/4` quý dương (`Funded 1x +613,64 USD`, `P1 4x +1.418,65 USD`, vượt ngày sụp Yên `05/08` `-3,14%`, đạt `+10%` ngày `2024-05-15`) ([Mũi 3 Receipt](research/MUI3-MASTER-PROP7E-REALTICK-2024-20261125.md)).

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
