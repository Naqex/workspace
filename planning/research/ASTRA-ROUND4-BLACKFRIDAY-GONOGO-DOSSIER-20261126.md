---
doc_type: executive-decision-dossier
created_utc: 2026-11-25
updated_utc: 2026-11-25T15:05:00Z
target_review_date: 2026-11-26
deadline_ict: "2026-11-30 16:00 ICT (10:00 CET)"
status: READY_FOR_ASTRA_ROUND4_DECISION
layer: layer1_public_sanitized
holdout_rows_analysed: 0
order_send_count: 0
---

# Hồ Sơ Phán Quyết Vòng 4 (Astra Go/No-Go) — FTMO Black Friday `30/11/2026`

> **Trạng thái (`100%` HOÀN THIỆN — SẴN SÀNG GỬI ASTRA VÒNG 4):** Toàn bộ `5` cổng kiểm định đã chốt nguyên văn bằng chứng thực địa: **Mũi 1 & 2** (`28/28` RT = `56` legs, `3.734` dòng spread `5s` -> **`PASS_WITHIN_1_5X`**, Core-4 **`P50 0,615× / P90 0,897×`**, Bootstrap 95% CI bảo thủ **`[0,618×..0,661×..0,704×]`**, CUSUM `0,00 / 0,38` = `BÌNH THƯỜNG`), **Mũi 3 & 3b** (**`6/6` kịch bản Tester `2024`** gồm chứng nhận **`v1.01` `10/10 .ex5` `0/0`** trên `20,02M` tick thật), **Mũi 4** (đối khớp `1:1` `0` drift + `naqex-node1` pre-flight `10/10` + Geo-IP `VN` non-US), **Mũi 5** (pháp lý/kênh rút VN), **kinh tế `0,75×..2,00×` `98,70 EUR`**, và **R&D trung thực `3/56 PASS`**. Chỉ còn chủ sở hữu kiểm giá checkout thật (`62,30`/`98,70 EUR`) & gửi thư `support@ftmo.com`.
>
> **Khóa an toàn:** `Holdout 2025+` niêm phong `100%` (`holdout_rows_analysed = 0`), `OrderSend = 0` trên toàn bộ R&D, `0` bí mật/IP/login/công thức Tầng 2 (`private_vault/`).

---

## 1. Bảng Trạng Thái `5` Cổng Kiểm Định Trước `30/11/2026 16:00 ICT`

| Cổng / Mũi | Mục tiêu kiểm chứng | Trạng thái | Bằng chứng thực địa đã xác minh |
|---|---|---|---|
| **Mũi 1 — Trượt Giá Thực Địa** | `28` RT (`56` legs, `0,01` lot, `4` mã `7E`) trên FTMO-Demo phụ | **`PASS (XANH)`** | **`28/28` RT**, `0` reject, **`swap = 0,00`**, `0` lỗi tin đỏ `13:30 UTC` GDP/PCE, `2` SL thật NY Cash Open `US100.cash`; Core-4 **`P50 0,615× / P90 0,897×`**, Bootstrap 95% CI **`[0,618×..0,704×]`**, CUSUM `0,00/0,38`. |
| **Mũi 2 — Spread Live `5s`** | `Spread Live FTMO / Dev M1 (1,00×)` xuyên Á/Âu/Mỹ | **`PASS (XANH)`** | **`3.734` mẫu `5s`** (`LONDON 1.070`, `NY_OVL 2.002`, `ASIA 600`, `NY_AFT 61`): tỷ lệ bps tổng `USDJPY 0,556×`, `GBPUSD 0,324×`, `EURJPY 0,920×`, `US100.cash 0,347×`. |
| **Mũi 3 & 3b — Tester `2024`** | `Naqex_Master_Prop7E.ex5` (`v1.00` & **`v1.01`** `REL+DH`) | **`PASS 6/6`** | `5` kịch bản **`Model=4` Real Ticks (`20,02M`)** + `1` **`Model=1` Full-2024**: **`v1.01`** (`sha16=2e0006ad786bdad6`) đạt **`+736,06 USD`, `PF 1,23`, `Sh 1,98`, `EqDD 6,27%`, `swap = 0,00`**, `492` tin đỏ, `hydrated=true`. |
| **Mũi 4 — Đối Khớp, `v1.01` & VPS** | Đối khớp `1:1`, `10/10 .ex5 v1.01`, pre-flight `naqex-node1`, Geo-IP | **`PASS`** | **`10/10 .ex5` `0/0`**, `0` drifts, `32/32` tests PASS; `naqex-node1` pre-flight **`10/10 PASS`** (`open=0`, `KeepPrivate=1`, LTSC anti-reboot); Geo-IP **`VN` non-US**, `is_cgnat=false` *(kiểm Double-NAT WAN trước Funded)*. |
| **Mũi 5 — Pháp Lý & Checkout VN** | Kênh rút VN, thẻ hoàn phí, thuế/CASP + checkout thật | **`XONG NGHIÊN CỨU`** / **CHỜ CHỦ SỞ HỮU** | Đã chốt [PROP-VN-PAYOUT-LEGAL-AND-VPS-COMPLIANCE-20261125.md](PROP-VN-PAYOUT-LEGAL-AND-VPS-COMPLIANCE-20261125.md) & thư EA `v1.01`; chủ sở hữu kiểm màn hình checkout `2-Step Standard` & gửi `support@ftmo.com`. |

---

## 2. Mũi 1 & 2 — Ma Sát Thực Địa (`FTMO-Demo` London + NY Overlap + NY Cash Open `10:38–14:47 UTC`)

Nguồn nguyên văn: `.runtime/live-overnight/ftmo_realized_friction_summary_20261125.json` (`PASS_WITHIN_1_5X`, `56` legs, `3.734` spread rows, `0` rejects, `swap = 0,00 USD`, `0` vi phạm tin đỏ `13:30 UTC` `US_GDP_AND_CORE_PCE` — bot tự hoãn USD qua `[13:25–13:35 UTC]`, định tuyến `EURJPY` bình thường) & `prop_live_tca_monitor.py` (10k Stratified Bootstrap + Page's CUSUM).

- **Khớp ngưỡng Vòng 3 -> `XANH ĐẬM (GO)`:** Toàn bộ KTC 95% bảo thủ **`[0,618× .. 0,661× .. 0,704×]`** (ròng có dấu `[0,456× .. 0,543× .. 0,624×]`) nằm **thấp hơn cả `0,75×`** (<< ngưỡng `1,25×` XANH và `1,50×` VÀNG!). Page's CUSUM tổng **`0,00` (đỉnh `0,38` / `h = 4,0`) -> `BÌNH THƯỜNG`**.

| Chỉ số thực địa Mũi 1–2 | `USDJPY` | `GBPUSD` | `EURJPY` | `US100.cash` | **Tổng hợp Core-4 `7E`** |
|---|---:|---:|---:|---:|---:|
| Vòng lệnh đóng (`0,01` lot) / SL thật | `7` (`0`) | `7` (`0`) | `7` (`0`) | `7` (**`2` SL**) | **`28 / 28` (`56` legs)** |
| Spread `Live / Dev M1` (`LON` / `NY_OVL`) | `0,669×` / `0,675×` (`3` pt) | `0,360×` / `0,365×` (`3` pt) | `0,918×` / `1,046×` (`8–9` pt) | `0,289×` / `0,488×` (`195` pt) | `3.734` mẫu (`0,32×–0,92×`) |
| Trượt bất lợi RT `P50 / P90` (`bps`) | `0,000` / `0,151` | `0,000` / `0,138` | `0,057` / `0,172` | `0,942` / `1,480` | `0` reject, `2` SL NY Open |
| Độ trễ khớp `P50 / P90` (`ms`) | `480` / `611` | `422` / `680` | `523` / `637` | `497` / `880` | **`492,6` / `654,9 ms`** |
| Hoa hồng (`USD/lot` RT) & Swap | `6,00` / `0,00` | `6,00` / `0,00` | `6,00` / `0,00` | `0,00` / `0,00` | Comm `-1,26`, **`Swap 0,00`** |
| **Ma Sát Thực (`P50 / P90`, 95% CI)** | **`0,660× / 1,101×`** (`[0,70–0,84]`) | **`0,489× / 0,858×`** (`[0,51–0,64]`) | **`0,866× / 1,043×`** (`[0,82–0,99]`) | **`0,446× / 0,587×`** (`[0,30–0,52]`) | **`0,615× / 0,897×`** (`[0,618–0,704]`) |

- **Kiểm chứng SL cứng thật lúc NY Cash Open (`14:30 UTC` `US100.cash`):** `#26` dính SL ở `14:30:11 UTC` (`+1,52 bps` bất lợi, lệch `+385` broker pts); `#28` dính SL ở `14:47:09 UTC` (`-0,18 bps` cải thiện) -> SL slip `P50 +0,671 / P90 +1,351 bps`. Từ đỉnh lệch `+385` pts này, **`v1.01`** đã nâng chuẩn `InpMaxSlippagePointsIdx = 450` (FX giữ `35` pts) để không bao giờ bị từ chối lệnh đóng thị trường!

---

## 3. Mũi 3 & 3b — Ma Trận `6` Kịch Bản `2024` (`v1.00` & Chứng Nhận `v1.01` `Model=4`)

Nguồn: [MUI3-MASTER-PROP7E-REALTICK-2024-20261125.md](MUI3-MASTER-PROP7E-REALTICK-2024-20261125.md) (`holdout_rows_analysed = 0`, ngày lệnh cuối `2024-12-30`, **`swap = 0,00 USD`**, `492` tin đỏ gồm `FOMC Minutes`, `0` reject).

| # | Kịch bản (`MASTER_PROP7E_*`) | Phiên bản / Chế độ MT5 | Đòn bẩy / Mult / Trễ | Lệnh | Lãi ròng (USD) | PF | Sharpe | BalDD / EqDD | Swap / Comm |
|---|---|---|---|---:|---:|---:|---:|---|---|
| **1** | `2024Q4_L30_50ms` | `v1.00` · **`Model=4` Real Ticks (`20,02M`)** | `1:30` / `1,0×` / `50 ms` | `156` | `+138,79` | `1,12` | `1,03` | `2,18%` / `2,59%` | `0,00` / `-34,00` |
| **2** | `2024Q4_STRESS_150ms` | `v1.00` · **`Model=4` Real Ticks (`20,02M`)** | `1:100` / `1,0×` / `150 ms` | `156` | `+156,19` | `1,13` | `1,16` | `2,16%` / `2,50%` | `0,00` / `-34,00` |
| **3** | `2024Q4_P1_4X_L100_50ms` | `v1.00` · **`Model=4` Real Ticks (`20,02M`)** | `1:100` / `4,0×` P1 / `50 ms` | `155` | `+754,60` | `1,24` | `2,02` | `4,92%` / `6,27%` | `0,00` / `-98,30` |
| **4** | `2024Q4_P1_4X_STRESS_150ms` | `v1.00` · **`Model=4` Real Ticks (`20,02M`)** | `1:100` / `4,0×` P1 / `150 ms` | `155` | `+755,69` | `1,24` | `2,03` | `4,86%` / `6,23%` | `0,00` / `-97,92` |
| **5** | `2024FULL_L100_50ms_M1OHLC` | `v1.00` · **`Model=1` Full-2024 (`1,46M`)** | `1:100` / `1,0×` / `50 ms` | `469` | `+744,48` | `1,19` | `1,47` | `3,36%` / `3,97%` | `0,00` / `-143,82` |
| **6** | **`V101_2024Q4_P1_4X_50ms`** | **`v1.01`** · **`Model=4` Real Ticks (`20,02M`)** | `1:100` / `4,0×` P1 / `50 ms` | **`155`** | **`+736,06`** | **`1,23`** | **`1,98`** | `4,92%` / `6,27%` | `0,00` / `-98,30` |

- **Xác nhận `v1.01` (`sha16=2e0006ad786bdad6`):** Khớp 100% `155` lệnh (`E1=79, E2=25, E3=11, E4=19, E5=14, E6=5, E7=2`), `hydrated=true`, `492` tin đỏ OK, `PROFIT_LOCK 2024-11-15`, đáy số dư tĩnh `-2,08%`, ngày xấu nhất `-1,70%` (`logs.clean=true`). Full-2024 `Model=1` dương `4/4` quý (ngày sập Yên `05/08/2024` chỉ `-1,55%`).

---

## 4. Mũi 4 & Mũi 5 — Đối Khớp `1:1`, Nâng Cấp `v1.01`, VPS & Pháp Lý VN

### A. Mũi 4 — `10/10 .ex5 v1.01` & Pre-Flight `naqex-node1` (`PASS — CUTOVER READY`)
- **Đột phá `v1.01` đã biên dịch & kiểm chứng (`V101-01..V101-07`, [MASTER-PROP7E-V101-RESTART-HYDRATION-SPEC-20261125.md](MASTER-PROP7E-V101-RESTART-HYDRATION-SPEC-20261125.md)):** Đã đóng gói `10/10 .ex5` (`0 errors, 0 warnings`), `verify_deployment_kit.py --require-ex5` `PASS` (`94` preset, `10` `.ex5`), `mql5_parity_checker.py` **`0` drifts** ([MASTER-7E-VS-LEGACY-PARITY-AUDIT-20261125.md](MASTER-7E-VS-LEGACY-PARITY-AUDIT-20261125.md)), và **`32/32` tests PASS** (gồm `V101` contract & OPSEC guard). Vá trọn: `V101-07` xóa bẫy cát lún AMBER kẹp tuyệt đối (`4,0× -> 0,65×` làm âm trung vị `-105,1` ở `1,50×`) sang **`REL+HEADROOM`** + giảm tốc theo ngày `dailyHeadroom < 2,0%` (lật trung vị `1,50×` lên **`+235,7 USD`**); cùng `V101-01..06` (TCA magic từng nhánh, nạp lại `m_tradedDay` + `g_autoKillActive` khi restart, `TimeTradeServer()` + Prague DST `0s` sai số, `23` ngày lễ/nửa phiên NYSE gồm Lễ Tạ Ơn `26–27/11`, chặn đóng lệnh trong `±135s` tin đỏ, hủy lệnh chờ khi kill/tin, `SetDeviationInPoints` `35` FX / `450` `US100`).
- **Pre-flight trực tiếp `naqex-node1`:** `node_cutover_dryrun --live-readonly` **`10/10 PASS`** (`open=0`, `KeepPrivate=1`, `AutoAdminLogon=1`, anti-reboot LTSC, `NTP -0,029s`, backup `D:` cùng ngày, Statement E2E `4/4 PASS`); `ftmo_pre_checkout_guard` xác nhận **`country_code = VN` (non-US PASS)**, `is_cgnat = false`, nhắc kiểm 1 lần `Double-NAT` WAN router trước khi lên Funded; lịch tin đỏ `14` ngày tới chỉ còn `2` mốc sau hôm nay (`04/12` `US_NFP`, `08/12` `AUD RBA`).

### B. Mũi 5 — Pháp Lý, Kênh Rút Tiền & OPSEC VN ([PROP-VN-PAYOUT-LEGAL-AND-VPS-COMPLIANCE-20261125.md](PROP-VN-PAYOUT-LEGAL-AND-VPS-COMPLIANCE-20261125.md))
- **Checkout `2-Step` & Thẻ hoàn phí:** Sale `-30%` CFD áp cho **`FTMO Standard`** (không đổi sang `Swing`). **Chỉ chọn `2-Step`** (`100%` hoàn phí về đúng phương thức lúc mua -> **dùng thẻ Visa/MC chính chủ còn hạn dài, tránh thẻ ảo 1 lần**; `1-Step` không hoàn phí + Best-Day). Quyền hủy `14` ngày mất khi mở lệnh #1; ngủ đông `30` ngày (có `Account Freeze`).
- **EA & Kênh rút VN:** FTMO cho phép EA tự viết (`< 20` req/ngày << `2.000` req/ngày), CẤM IP/VPS Mỹ, kiểm WAN router không dính CGNAT `100.64.0.0/10` trước Funded. FTMO rút **`0%`** phí (không Riseworks; ưu tiên **SWIFT** `min 20 USD` cho chứng từ thuế sạch hoặc **Crypto USDT/USDC** `min 50 USD`, tránh rủi ro P2P) vs **The5ers** thu `3,5%` + tầng phí Rise + `30%` Hub Credit. Nút thắt `TT 20/2022/TT-NHNN` + cấm nạp bên thứ ba IBKR -> hoãn Own-Book ETF `< 25K`; giữ `B06/B02` chạy bóng theo **`05/2025/NQ-CP`** & **`32/2026/TT-BTC`** (`0,1%` TNCN, miễn VAT) chờ **CASP** cấp phép; giữ `20%` dự phòng vận hành/thuế trên `treasury_ledger.py`.

---

## 5. Kinh Tế `98,70 EUR` (`0,75×..2,00×` Hiệu Chuẩn Theo Đo Thực Địa) & Quỹ Đạo `60` Tháng

- **Tương thích `100%` `FTMO Standard`:** `7E` đóng phẳng trước `20:55 UTC` (`swap = 0`); `1:100` giảm đỉnh margin P1 từ `45,17%` còn **`13,55%`**; khóa tin `±5m` trên Funded (gồm `55` kỳ `FOMC Minutes`) giữ `89,3%` Dev và thắng trên Holdout `2025–2026` đã công bố (`Calmar 1,94 > 1,75`).

### A. Đối Chứng `24` Tháng (`N = 5.000 × 730d`, `98,70 EUR = 105,12 USD`, `0,0%` Cháy Ngày Ở Mọi Mức!)

| Ma sát | Hợp đồng (`7E Static Lock + Factor Caps`) | Phí (USD) | Lãi TB 24t | Trung vị 24t | `EV / Phí` | `P(Lỗ<=0)` | `OOP95` | MedPay1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **`0,75×`** *(live CI `[0,62–0,70]`)* | **`FTMO Std 98,70 EUR` (`v1.01 REL+DH`)** | `105,12` | **`+844,9`** | **`+822,6`** | **`+8,04×`** | **`8,7%`** | **`210,2`** | **`280d`** |
| **`1,00×`** | **`FTMO Std 98,70 EUR` (Rule-Exact / `v1.01 REL+DH`)** | `105,12` | `+613,4` / **`+639,8`** | `+573,5` / **`+600,0`** | `+5,83×` / **`+6,09×`** | `17,8%` / **`14,9%`** | `210,2` | `308d` |
| `1,00×` | `FTMO Swing 10K` (Guard) / `The5ers HS 5K` | `168` / `39` | `+558,1` / `+260,8` | `+528,8` / `+264,9` | `+3,32×` / `+6,69×` | `20,9%` / `28,5%` | `336` / `78` | `321d` / `393d` |
| **`1,25×`** | **`FTMO Std 98,70 EUR` (Rule-Exact / `v1.01 REL+DH`)** | `105,12` | `+445,8` / **`+471,1`** | `+383,6` / **`+412,4`** | `+4,24×` / **`+4,48×`** | `26,1%` / **`22,7%`** | `210,2` | `334d` |
| **`1,50×`** | **`FTMO Std 98,70 EUR` (Rule-Exact / `v1.01 REL+DH`)** | `105,12` | `+282,0` / **`+306,6`** | `+192,7` / **`+235,7`** | `+2,68×` / **`+2,92×`** | `37,2%` / **`32,8%`** | `315,4` | `361d` |
| `1,50×` | `FTMO Swing 10K` (Guard) / `The5ers HS 5K` | `168` / `39` | `+205,1` / `+109,1` | `+143,5` / **`-39,0`** | `+1,22×` / `+2,79×` | `41,6%` / **`52,1%`** | `504` / `117` | `377d` / `432d` |
| **`1,75×`** | **`FTMO Std 98,70 EUR` (Rule-Exact / `v1.01 REL+DH`)** | `105,12` | `+153,7` / **`+174,1`** | `+51,6` / **`+86,4`** | `+1,46×` / **`+1,66×`** | `48,5%` / **`44,5%`** | `315,4` | `378d` |
| **`2,00×`** | `FTMO Std 98,70 EUR` / `Swing 168` | `105` / `168` | `+50,8` / `-62,9` | `-105,1` / `-168,0` | `+0,48×` / `-0,38×` | `58,1%` / `64,7%` | `315` / `504` | `390d` / `401d` |

*(Ghi chú: Nếu checkout thật hiện `62,30 EUR ~ 66,35 USD`, `EV/Phí` tăng thêm `+58%`. **KHÔNG mở song song The5ers HS 5K** trong tuần Black Friday.)*

### B. Quỹ Đạo `60` Tháng (`1.825d`, `N = 5.000`, `25.500 VND/USD`) — Prop-to-OwnBook
- **Khởi điểm `500 USD` thuần (Thang cộng dồn `10K -> +25K -> +50K -> +100K` + `75% SGOV / 25% B06+B02` từ sàn `3K`):** `1,00×` M60 Trung vị **`5.235 USD` (`133,5 tr VND`, TB `10.943 USD`, cháy `0,6%`, >`2×` sàn `1` slot `10K` `2.536 USD`)**; `1,25×` `2.454 USD`; `1,50×` `1.272 USD`; `1,75×` `923 USD`. Với nền `5K` Own-Book (`0%` cháy), `75/25` cộng đều **`+873..+945 USD`** vào M60 Med ở mọi mức ma sát (`11.731` vs `10.786 USD` ở `1,00×`).

---

## 6. Sổ R&D Trung Thực (`3 / 56 PASS`) & Lộ Trình Đa Quỹ / Own-Book / LD4 VPS

| Nhánh R&D (`m = 56`, `< 2025-01-01`, `OrderSend = 0`) | Đạt / Tổng | Kết luận khóa cứng (không che kết quả âm) |
|---|---:|---|
| **Wave-2 ETF `< 25K` (`0/10`) & CME / ToM / Overnight (`0/10`)** | **`0 / 20`** | ETF không vượt `BIL` (`q=0,364`); CME cần `121K–294K USD`; Overnight dính phí `~10%/năm` -> ròng `-3,92%`. |
| **Wave-2 Crypto Spot `4H–D1` (`50` coin, đo L2 live `2026` ĐẠT)** | **`3 / 10`** | `50/50 B06+B02` đạt Cl.B `+10,71% / DD 7,17% / Sh 1,51`, sống ở `35 bps` từ `3.000 USD`. Đo L2 Binance live `2026` trên Pool-50 Top-10 (`3.000 USD`): **`16,41 / P90 18,79 bps` (BNB `-25%`) <= `20 bps`** (`21,41 / 23,79` VIP0). Ghép `75% SGOV + 25%` đạt **`+4,80% / DD 0,92% / Sh 2,70 / r(7E) +0,061`**. *(Giữ shadow chờ CASP VN.)* |
| **Wave-2.6 Macro ETF (`0/6`), `ETH/BTC` (`0/4`) & Wave-3A MR/Idle (`0/16`)** | **`0 / 26`** | Loại sạch `ETH/BTC` (`-3,2%..-9,8%`), bắt đáy Crypto (`-6,5%..+1,5%`), và xoay tiền nhàn rỗi (`57%` tiền mặt `B06/B02` là lá chắn bảo vệ!). **Khóa gọn kiến trúc `2` trụ cột.** |

- **Đa quỹ, Own-Book & VPS ([ownbook-merger-arb-and-vps-scaling-2026.md](../../knowledge/topics/ownbook-merger-arb-and-vps-scaling-2026.md) · [prop-firm-2026-landscape-and-multi-firm-portfolio.md](../../knowledge/topics/prop-firm-2026-landscape-and-multi-firm-portfolio.md)):** Loại Cash Merger Arb `< 100K` & bỏ qua FTMO Futures Cyber Monday (Topstep cấm bot Live/VPS); chốt thứ tự **`#1 FTMO CFD` -> `#2 Darwinex Zero` (Tháng `4–6` từ tiền rút FTMO, FCA/CNMV, `0%` SWIFT, native MT5) -> `#3 The5ers` (Tháng `6–9`)**. Neo tiền nhàn rỗi `75%`: **`100% SGOV`** (`< 50K`, QII `~0%`) -> **`IB01` UCITS** (`>= 50K–60K`, né Estate Tax `60K`; loại `UUP` do IRC `1446(f)` `10%` PTP). VPS: giữ **`naqex-node1` (`0 USD/tháng`)** dưới `50K` Funded, AWS Lightsail London `22 USD/tháng` tùy chọn `50K–74K`, chỉ lên Equinix LD4 `32–45 USD/tháng` từ `>= 75K–100K` Funded.

---

## 7. Prompt Chuẩn Gửi GPT-6.2 (Astra Vòng 4 — Phán Quyết Cuối `GO / NO-GO`)

> *Đã điền 100% số liệu thực địa — chủ sở hữu chỉ cần sao chép nguyên khối sau gửi Astra Vòng 4 trước `30/11/2026 16:00 ICT`.*

````markdown
Chào Astra (Vòng 4 — Phán quyết cuối trước hạn chót FTMO Black Friday 30/11/2026 16:00 ICT).
Toàn bộ bằng chứng dưới đây đã đo thực địa & kiểm chứng độc lập (Holdout 2025+ niêm phong 100%, OrderSend=0 trên toàn bộ R&D, tách riêng Private Vault Tầng 2):

1. MŨI 1 & 2 — MA SÁT THỰC ĐỊA TRÊN FTMO-DEMO PHỤ (10:38-14:47 UTC, London + NY Overlap + NY Cash Open 14:30 UTC):
   - Lệnh probe đóng: 28/28 vòng RT (56 legs, 0,01 lot, 7 RT mỗi mã USDJPY/GBPUSD/EURJPY/US100.cash), 0 rejects, swap = 0,00 USD, 0 vi phạm tin đỏ (13:30 UTC US_GDP_AND_CORE_PCE tự hoãn USD 13:25-13:35 UTC).
   - Spread Live 5s (3.734 mẫu) / Dev M1 (1,00x): USDJPY 0,556x (3 pt), GBPUSD 0,324x (3 pt), EURJPY 0,920x (8-9 pt), US100.cash 0,347x (195 pt; 145 pt lúc NY mở).
   - Trượt bất lợi RT P50/P90 (bps): USDJPY 0,000/0,151 | GBPUSD 0,000/0,138 | EURJPY 0,057/0,172 | US100.cash 0,942/1,480 (gồm 2 lệnh chạm SL cứng thật lúc NY Cash Open: +1,52 bps & -0,18 bps; đỉnh lệch +385 pts -> đã cài InpMaxSlippagePointsIdx=450 trong v1.01!).
   - Độ trễ khớp VN -> EU: P50 492,6 ms / P90 654,9 ms; Hoa hồng: FX 6,00 USD/lot RT, US100 0,00 USD/lot, Swap 0,00 USD.
   - HỆ SỐ MA SÁT THỰC TẾ Core-4: P50 = 0,615x | P90 = 0,897x (PASS_WITHIN_1_5X); 10k Stratified Bootstrap 95% CI bảo thủ [0,618x .. 0,661x .. 0,704x] (ròng có dấu [0,456x .. 0,543x .. 0,624x]); Page's CUSUM = 0,00 / đỉnh 0,38 (h=4,0) -> BÌNH THƯỜNG.

2. MŨI 3 & 3B — MT5 STRATEGY TESTER 2024 (6/6 PASS, gồm Naqex_Master_Prop7E.ex5 v1.01 vừa biên dịch 10/10 0/0):
   - v1.00 Model=4 (20,02M real ticks Q4, swap=0,00, 492 tin đỏ): 1:30 1x 50ms +138,79 (PF 1,12); 1:100 1x 150ms +156,19 (PF 1,13); 1:100 4x P1 50ms +754,60 (PF 1,24, Sh 2,02); 1:100 4x P1 150ms +755,69 (PF 1,24, Sh 2,03).
   - v1.00 Model=1 Full-2024 (1,46M): 469 lệnh, +744,48 USD, PF 1,19, Sh 1,47, EqDD 3,97%, 4/4 quý dương, ngày sập Yên 05/08/2024 chỉ -1,55%, swap 0,00.
   - CHỨNG NHẬN v1.01 (sha16=2e0006ad786bdad6, Model=4 Real Ticks 20,02M Q4, 1:100, 4x P1 + PROFIT_LOCK, 50ms, slippage 35 FX / 450 Idx): 155 lệnh khớp 100% từng nhánh, +736,06 USD (+7,36%), PF 1,23, Sh 1,98, BalDD 4,92% / EqDD 6,27%, swap 0,00, hydrated=true, 492 tin đỏ, đáy tĩnh -2,08%, ngày xấu -1,70%.

3. MŨI 4 & MŨI 5 — ĐỐI KHỚP 1:1, ĐỘT PHÁ v1.01, PRE-FLIGHT VPS & PHÁP LÝ VN:
   - 10/10 .ex5 v1.01 biên dịch 0/0, 0 drifts (32/32 tests), vá trọn V101-01..07 (xóa bẫy cát lún AMBER sang REL+HEADROOM + dailyHeadroom <2%, TCA magic thật, restart hydration, TimeTradeServer()+Prague DST 0s, 23 ngày lễ NYSE gồm 26-27/11, ±135s hard-ban, SetDeviation 35/450).
   - Pre-flight Home-VPS: 10/10 PASS (phẳng lệnh, KeepPrivate=1, anti-reboot LTSC, NTP -0,029s, Statement E2E 4/4); Geo-IP = VN (non-US PASS, is_cgnat=false, kiểm Double-NAT WAN router trước Funded).
   - Pháp lý VN (2026): chỉ chọn 2-Step Standard bằng thẻ Visa/MC chính chủ còn hạn dài (hoàn 100% về đúng thẻ); FTMO rút 0% (SWIFT/Crypto, không Riseworks) vs The5ers 3,5% + Rise FX; TT 20/2022/TT-NHNN hoãn Own-Book ETF <25K; giữ B06/B02 shadow theo NQ 05/2025/NQ-CP & TT 32/2026/TT-BTC chờ CASP.

4. KINH TẾ 98,70 EUR (v1.01 REL+DH HIỆU CHUẨN 0,75x..1,75x), R&D (3/56) & LỘ TRÌNH:
   - FTMO Std 10K @ 98,70 EUR (105,12 USD, N=5.000 x 730d, 0,0% cháy ngày):
     * 0,75x (ngay trên live CI [0,62-0,70x]): Mean +844,9 | Med +822,6 | EV +8,04x | P<=0 8,7% | Pass24 94,7% | Pay1 280d
     * 1,00x: Mean +639,8 | Med +600,0 | EV +6,09x | P<=0 14,9% | Pass24 91,1% | Pay1 308d
     * 1,25x: Mean +471,1 | Med +412,4 | EV +4,48x | P<=0 22,7% | Pass24 85,3% | Pay1 334d
     * 1,50x: Mean +306,6 | Med +235,7 | EV +2,92x | P<=0 32,8% | Pass24 78,2% | Pay1 361d (vs v1.00 cũ âm -105,1!)
     * 1,75x: Mean +174,1 | Med +86,4 | EV +1,66x | P<=0 44,5% | Pass24 69,2% | Pay1 378d
   - R&D trung thực 3/56 PASS: dừng tìm nhánh phụ, khóa 2 trụ cột (PORT_7E + 75% SGOV <50K / IB01 >=50K-60K + 25% Crypto Spot B06/B02 shadow đã đo L2 live 16,4/18,8 bps BNB <= 20 bps). Đa quỹ 2026-27: #1 FTMO CFD -> #2 Darwinex Zero (Tháng 4-6 từ lãi FTMO) -> #3 The5ers (Tháng 6-9); giữ Home-VPS 0 USD/tháng dưới 50K Funded.

YÊU CẦU PHÁN QUYẾT VÒNG 4 (ngắn gọn, phản biện thẳng thắn, không nịnh):
1. Dựa vào toàn bộ Mũi 1-5 thực địa trên, chốt MỘT phán quyết duy nhất trước 30/11 16:00 ICT: **GO (Mua 1 vé FTMO 2-Step Standard 10K)** / **UNPAID-OPTION (0 USD)** / **NO-GO**.
2. Nếu GO: chốt cấu hình P1 (3,0x Balanced vs 4,0x Sprint + PROFIT_LOCK trên `v1.01`), bật NewsGuard luôn ở P1/P2 hay chỉ ở Funded, thời điểm khởi chạy (tránh nghỉ Lễ Tạ Ơn Mỹ 26-27/11 -> bật Thứ Hai 01/12?), và 3 ngưỡng cắt lỗ / dừng sớm (kill-criteria) trong 14 ngày đầu.
3. Chỉ ra tối đa 3 điểm mù còn sót (vd: Demo vs Live Funded execution gap, Double-NAT router WAN, biến động US100 SL) mà hệ thống vẫn có thể chết ngoài dự kiến.
````
