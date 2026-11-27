# Total Offensive #3 (v3.5) — Báo Cáo Tổng Kết Nhà Máy Alpha Thi Quỹ & `v1.03-Sprint`

> **Ngày chốt báo cáo:** `27/11/2026` (`campaign_run_id`: `off3-clb-20261127T140149Z-eb2b954d`, `git_sha`: `c290d6db146a`)
> **Ràng buộc an toàn đã xác minh:** `0 VND` đã chi · `OrderSend = 0` (`ORDER_SEND_CAPABLE = False`) · `MT5_PROCS = 0` · `Holdout 2025+ = 0` dòng (`holdout_lock_sha256 = f0a6b43c...8486`) · `ZERO` hạ chuẩn kiểm định · Tuân thủ tuyệt đối `G12` và cách ly OPSEC Lớp 1.
> **Biên nhận gốc đối chiếu trực tiếp:** [OFFENSIVE3-ALPHA-FUNNEL-20261127.json](OFFENSIVE3-ALPHA-FUNNEL-20261127.json) · `private_vault/strategies/offensive3_v3/prop_v3_metrics.json` · `private_vault/strategies/offensive3_v3/m1_v103_sprint_results.json` · `.runtime/offensive3/audits/dukascopy_waf_block_receipt.json` · `D:/ANNAM/strategy-intel/handoff/sanitized_offensive3_leads.json`.

---

## 1. Tóm Tắt Điều Hành (Kết Quả Thực Tế Trước Hết)

**Kết luận thẳng:** Chiến dịch Total Offensive #3 v3.5 đã kiểm định mù đúng `1` lần trên Cụm B (`2021–2024`) với tổng cộng **`1.137` ứng viên phi-breakout** thuộc `12` họ chiến lược (`F01..F12`, gồm `142` nhánh Chính và `995` nhánh Thăm dò bổ sung). Phễu phân tầng 3 lớp trả về kết quả trung thực tuyệt đối: **`0` `TIER_1_FTMO_READY`**, **`0` `TIER_2_PERSONAL_VAULT`**, **`1.137` `TIER_3_DEAD_NO_EDGE`** — không một nhánh mới nào vượt qua ngưỡng kiểm soát phát hiện giả toàn chiến dịch (`BH-FDR q <= 0,10`).

Theo cổng **`G09` (Accretion Gate)**, hệ thống **từ chối gắn thêm bất kỳ bot chưa đạt chuẩn nào** vào danh mục thi quỹ. Bản vô địch **Prop V3 Champion** tiếp tục giữ nguyên lõi bất biến **`PORT_7E v1.03`** (`Naqex_Master_Prop7E_v103.mq5`, SHA-256 `e6b1b88b...`) kết hợp nâng cấp thuần tệp tham số `.set` **`v1.03-Sprint` (`SPR09_M45_P2_35_B1` vòng thi + khóa cứng `Funded 1,0x`)**.

### 5 Thành Quả Thực Tế Đã Đo Kiểm & Bàn Giao

1. **Mũi 1 — `v1.03-Sprint` (`.set`-only, không sửa `1` dòng mã nguồn `v103.mq5`):** Trên bộ mô phỏng `N = 10.000` đường ghép khối `5` ngày (`seed = 20261127`, `Dev 2018–2024`, nhãn `XẤP XỈ CẤP NGÀY` khớp cơ chế `v103.mq5`, nguồn sự thật thống nhất `InpKillStaticDdPct = 8,00%` khớp cổng `OPS-2`), gói tham số `SPR09_M45_P2_35_B1` nâng tỷ suất lãi kỳ vọng trên `1` đồng phí (`EV/Phí` NPV 24 tháng, `1` vé đơn) từ **`+7,58x` -> `+8,74x`** trên **FTMO Standard 10K Black Friday** (`+615,11 USD` / `+15,85 tr VND` trên phí `70,42 USD` / `1,81 tr VND`), đạt **`+13,38x`** trên **FTMO Standard 100K** (`+6.565,17 USD` / `+169,16 tr VND`) và **`+6,49x` / `+6,76x`** trên **The5ers High Stakes 5K Classic / New**. Trung vị thời gian không điều kiện **đậu đủ 2 vòng** rút từ `249,3` -> **`205,8` ngày (`-43,5` ngày)** và **lần rút thưởng đầu tiên (Payout #1)** rút từ `349,3` -> **`288,4` ngày (`-60,9` ngày)**. Khóa cứng **Funded `1,0x`** tại **`KS = 8,00%`** giữ tỷ lệ cháy Funded 12 tháng trên toàn bộ `7/7` gói SSOT trong vùng **`0,04%–0,50%`** (cận trên Wilson 95% **`0,12%–0,70% << 1,00%`**: FTMO 10K **`0,17%`**, FTMO 50K `0,46%`, FTMO 100K `0,50%`, The5ers 5K Classic `0,05%` / New `0,04%`), sốc trượt giá `1,25x` vòng thi giữ **`<= 3,75%`** (ngưỡng an toàn `<= 4,50%`), và xác suất cháy sạch `4` vé / `5` vé nối tiếp trên FTMO 10K chỉ còn **`0,51%` / `0,12%`**.
2. **Hạ tầng dữ liệu `28` mã Dev (`<= 2024-12-31`, `Holdout = 0` dòng):** Hoàn tất kho dữ liệu `28` mã chia rạch ròi `3` tầng mù trung thực — **`12` mã M1 Bid/Ask gốc** (`DEV_CLB_CONSUMED_12OLD`, đồng bộ xong **`85/85`** tệp = `84` Parquet + `manifest.json`, `626,8 MB`, `0` tệp cấm sang `<X13_WORKER>`), **`9` mã D1 Yahoo chuẩn** (`NEW9_D1_VIEWED_M1_UNSEEN`, cách ly sạch phiên dầu âm `USOIL 2020-04-20..21`), và **`7` cặp chéo mù hoàn toàn D1** (`TRUE_BLIND_CLB_NEW7_CROSSES`: `CADJPY, CHFJPY, EURAUD, EURCAD, EURGBP, GBPAUD, NZDJPY`), cùng bảng thông số chuẩn `tooling/ai-engines/configs/ssot/ftmo_specs_28.json` (vá đủ `16/28` mã thiếu `tick_val_loss`, đòn bẩy Swing thật và khóa Anti-Fake-Swap). Ghi nhận trung thực rào chắn **Dukascopy CloudFront AWS WAF** trả HTTP `403` / `202 challenge` tại `.runtime/offensive3/audits/dukascopy_waf_block_receipt.json` (`waf_bypass_attempted = false` — tuyệt đối không lách WAF, không bịa nến M1).
3. **Kho đặc tả Cleanroom 1 chiều (`115` ý tưởng sạch, `4/4` cổng sạch PASS):** Sàng lọc từ `131` nguồn thô qua `6` bộ quét đa nguồn (`arXiv/SSRN`, `Quantpedia/QC`, `MQL5`, `TradingView`, `GitHub`, cộng đồng `EN/RU/CN`), loại `16` trùng lặp ngữ nghĩa và `11` mẫu độc hại (`Grid/Martingale/Không SL/DLL/Rollover-Scalper`), xuất `115` đặc tả toán học sạch vào `D:/ANNAM/strategy-intel/handoff/sanitized_offensive3_leads.json` (`444.971 B`, `sha256 = 68b279dc962e015b`, `72` Swing / `36` Intraday / `7` cả hai; `57` tái lập trực tiếp / `15` bán phần / `43` khung ý tưởng; `0` token `2024..2029`/`oos2`; `0` byte ghi ngược).
4. **Mũi 3 — Bộ giáp Vận hành Thực chiến `OPS-1..OPS-6` (`100%` offline, Red-Team #3 `PASS` `P0 = 0, P1 = 0`):** Hoàn thiện trọn bộ `6` làn vận hành từ lịch tin đỏ `8-CCY + EIA` (`568` sự kiện, tách US vs EU DST, có dự phòng múi giờ chuẩn không phụ thuộc `tzdata`), khóa tài khoản & chặn nhầm `.set` vòng thi vào Funded (`OPS-2`), cứng hóa VPS + Công tắc dừng khẩn cấp có xác nhận ACK sau mốc ghi cờ `<= 10s` & `open_positions == 0` (`OPS-3`), đường ống đèn giao thông `Xanh/Vàng/Đỏ` hằng ngày (`OPS-4`), gói bằng chứng rút thưởng bất biến có chuỗi băm SHA-256 + Sổ tay Go-Live (`OPS-5`), đến Hộp đen quyết định `Naqex_DecisionBlackbox.mqh` (`FILE_ANSI` không BOM) & bộ mổ xẻ sai lệch `W1..L4` có khóa chống học vẹt `N_live >= 30` (`OPS-6`). Đạt **`95/95`** bài kiểm thử toàn cụm Mũi 3 & Cleanroom dưới cả `python` thường và `python -O`, **`Red-Team #3 PASS (P0 = 0, P1 = 0)`**, và **`3/3` file `.mqh` Layer 2 + `v103.mq5` biên dịch `MetaEditor64.exe` đạt `0 errors, 0 warnings`** (`0` tệp `.ex5` trong `private_vault/`).
5. **Sổ cái DuckDB bất biến (`1.279` dòng) & Bằng chứng Toán học cho lộ trình Top 1%:** Sổ cái kép `.runtime/experiments/experiments.duckdb` + `run_registry.sqlite3` ghi đủ `100%` thử nghiệm thắng và thua (`142` Chính + `1.137` Thăm dò = `1.279` dòng, `integrity_verified = true`, số phép thử độc lập hiệu dụng `N_eff = 72,00` nhánh Chính / `211,03` nhánh Thăm dò). Thực nghiệm chứng minh không gian CFD đơn lẻ sau ma sát `2x` + Swap thật gần như không còn biên lợi thế mới đủ mạnh; con đường thực tế nhất lên **Top 1%** là **Nhân rộng đa tài khoản quỹ bằng `PORT_7E v1.03-Sprint`** song song với **Đợt 4: Sổ vốn riêng đa nhánh lệch pha** (`Alpha #2` Crypto Spot nhân quả + Macro ETF / Frontier Carry).

---

## 2. Dữ Liệu 28 Mã Dev, Khóa Holdout & Cầu Sạch Cleanroom (`G01, G03, G04`)

| Tầng dữ liệu (Nhãn mù trung thực) | Số mã | Độ phân giải & nguồn | Danh sách mã (`<= 2024-12-31`, `Holdout = 0` dòng) | Kiểm soát vệ sinh dữ liệu |
|---|---:|---|---|---|
| `DEV_CLB_CONSUMED_12OLD` | `12` | `NATIVE_M1_BIDASK` (Dukascopy niêm phong cũ) | `AUDUSD, BTCUSD, EURJPY, EURUSD, GBPJPY, GBPUSD, GER40, US100, US500, USDCAD, USDJPY, XAUUSD` | Đã đồng bộ **`85/85`** tệp (`84` Parquet + `manifest.json`, `626,8 MB`, `0` tệp cấm) sang `<X13_WORKER>`; đã xem Cụm B ở các đợt trước. |
| `NEW9_D1_VIEWED_M1_UNSEEN` | `9` | `D1_YAHOO_SANCTIONED` (`.runtime/new-assets-10-cache/`) | `AUDJPY, JP225, NZDUSD, UK100, UKOIL, US30, USDCHF, USOIL, XAGUSD` | Khớp `9/9` SHA-256; cách ly cứng phiên dầu âm `USOIL 2020-04-20..21` (`open = -14,0`, `low = 1e-06`), sau cách ly `min_low = 10,07`. |
| `TRUE_BLIND_CLB_NEW7_CROSSES` | `7` | `D1_YAHOO_SANCTIONED` (`.runtime/offensive3-d1-cache/`) | `CADJPY, CHFJPY, EURAUD, EURCAD, EURGBP, GBPAUD, NZDJPY` | Mới tải lần đầu (`2017–2024`, `1.839–1.840` thanh/mã, `max_date = 2024-12-31`, `0` giá `<= 0`), hoàn toàn mù trên Cụm B `2021–2024`. |

- **Sổ thông số `ftmo_specs_28.json` (`28/28` mã, `0` trường rỗng):** Vá đủ `16/28` mã từng bị `tick_val_loss = 0` bằng công thức quy đổi nhân quả theo đồng tiền lợi nhuận; xác nhận `JP225.cash` có `contract_size = 10,0`, `BTCUSD` có `swap_mode = 5` (`-30%/năm`), nhân 3 ngày swap đúng ngày (`Thứ 4` cho FX/Kim loại, `Thứ 6` cho Chỉ số/Dầu/Crypto), đòn bẩy FTMO Swing thật (`FX 1:30`, `Chỉ số 1:15`, `Kim loại 1:9`, `Dầu 1:10`, `Crypto 1:1`), và bật **Anti-Fake-Swap Guard** chặn toàn bộ swap dương bất thường trên `US100, US500, UK100 (Short), USOIL (Long), UKOIL (Long)`.
- **Biên nhận chặn AWS WAF Dukascopy (`dukascopy_waf_block_receipt.json`, `sha256 = 8d5a944b...`):** Khi tải M1 mới qua `dukascopy-node@1.51.1`, máy chủ Dukascopy CloudFront trả `HTTP 403 (DUKASCOPY_ACCESS_DENIED)` và `HTTP 202 (x-amzn-waf-action: challenge)` trên toàn bộ `8/8` mã thử thăm dò (`waf_bypass_attempted = false`, `headless_browser_evasion_attempted = false`, `fake_m1_synthesized = false`). Lộ trình bổ sung M1 chính quy cho `16` mã mới là chủ sở hữu tự xuất lịch sử M1 Bid/Ask `< 2025-01-01` từ MT5 rồi niêm phong bằng `tooling/ai-engines/quant_factory/seal_asset_m1.py` (đã kiểm chứng khớp bit-for-bit `2.604.015` phút trên `AUDUSD`).
- **Kho Cleanroom 1 chiều (`D:/ANNAM/strategy-intel`):** Đạt `4/4` cổng kiểm soát (`repo_hygiene_check`, `verify_verbatim`, `holdout_sanitizer`, `test_guards.py`). Cầu đọc 1 chiều `strategy_intel_bridge.py --profile offensive3` nạp `114` ý tưởng hợp lệ và lọc `1` mẫu khỏi `115` đặc tả bàn giao, giữ nguyên `0` byte ghi ngược sang kho Cleanroom.

---

## 3. Bảng Cân Bằng Đầy Đủ Law 15 — Prop V3 Champion (`PORT_7E v1.03-Sprint`)

### 3.1. Phát Hiện Quan Trọng Về Đồng Bộ Mã `v103.mq5` (`G10`)

Báo cáo Khiên C trước đó (`+8,75x`) chạy Funded ở hệ số rủi ro `1,25x` và chưa mô phỏng cơ chế tự dừng vĩnh viễn khi lỗ tĩnh chạm ngưỡng `InpKillStaticDdPct` (`8,0%/7,5%` tại `v103.mq5:L996`). Khi tái lập chính xác từng dòng mã `v103.mq5` (Amber/Red tương đối, tự hạ lot nội ngày khi đệm lỗ ngày `< 2,0%`, trần tổng rủi ro mở `<= 3,00%`, chế độ reset ngày Mode `1` FTMO vs Mode `0` The5ers, kiểm tra `0/3.122` lệnh vắt qua mốc `00:00` Prague hay `17:00` NY DST):

- **Bản `BASE_V103_SHIELD_C_FN125` (`Funded 1,25x`, `KS 8,0/7,5%`):** `EV/Phí = +9,29x`, nhưng tỷ lệ **cháy tài khoản Funded trong 12 tháng lên tới `3,10%` — TRƯỢT cổng an toàn `< 1%`**.
- **Bản đối chứng chuẩn `BASE_V103_SHIELD_C_FN1X` (`Funded 1,0x`, `KS 8,0/7,5%`):** `EV/Phí = +7,58x` (`+534,08 USD` / `+13,76 tr VND`), cháy Funded `0,73%`, đậu 2 vòng `155,1 / 249,3` ngày (có điều kiện / không điều kiện), Payout #1 `216,0 / 349,3` ngày, cháy `4` vé nối tiếp `1,95%`.
- **Bản vô địch `.set`-only `SPR09_M45_P2_35_B1` (`Prop V3 Champion`):**
  - **`.set` Vòng thi (Eval):** Vòng 1 `4,50x` / Vòng 2 `3,50x`, `SymCap 2,25%`, cụm `USD/JPY/IDX = 2,75/2,50/2,25%`, `TotalOpenCap = 3,00%` (sốc gap `1,25x = 3,75% <= 4,50%`), `InpSizingMode = 1` (`BARRIER_HEADROOM_MIN`), `Amber 4,5% -> 0,60x`, `Red 7,0% -> 0,30x`, `DailyStop 4,25%/4,00%`, `StaticKill 9,50%`, tắt `ProfitLock`, bật `SpreadGuard` + tin đỏ `6-CCY +-10m`.
  - **`.set` Tài khoản Cấp vốn (Funded):** Khóa cứng **`1,00x`**, `SymCap 1,00%`, `TotalOpenCap = 2,00%` (sốc gap `1,25x = 2,50%`), `Amber 3,5% -> 0,65x`, `Red 6,0% -> 0,40x`, `DailyStop 2,50%`, và **nguồn sự thật thống nhất `InpKillStaticDdPct = 8,00%`** xuyên suốt `SprintCandidate`, `m1_v103_sprint_results.json`, `prop_v3_metrics.json`, và toàn bộ tệp `.set` Funded xuất ra (khớp trực tiếp trần cứng `<= 8,00%` của `OPS-2 account_phase_preflight.py`, đối khớp `100%` SHA-256 trên đĩa). Trên đủ `10.000` đường (`seed = 20261127`), toàn bộ `7/7` gói SSOT đều có cháy Funded 12 tháng **`0,04%–0,50%`** (cận trên Wilson 95% **`0,12%–0,70% << 1,00%`**).

### 3.2. Thông Số Cốt Lõi Danh Mục `PORT_7E` (`Dev 2018–2024`, Đã Trừ Phí Thực)

| Chế độ vận hành | Số lệnh | Tỷ lệ thắng (`Winrate`) | Tỷ lệ ăn/thua (`RR`) | Kỳ vọng mỗi lệnh (`EV/lệnh`) | Hệ số sinh lời (`PF`) | Lãi năm TB (`Cụm A / Cụm B`) | Sụt giảm sâu nhất (`Max DD`) | Sụt ngày lớn nhất | Chuỗi thua dài nhất | `Calmar` | `Sharpe` | Sốc gap `1,25x` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Funded `1,0x`** *(quy chuẩn `100K USD`)* | `2.827` | `48,85%` | `1,261` | `+0,0455R` (`+17,74 USD` / `+457.088 VND`) | `1,204` | `+7,17%` (`+8,56% / +6,12%`) | `6,82%` *(trần `10%`)* | `1,52%` *(trần `5%`)* | `12` lệnh | `1,051` | `1,250` | `2,50%` |
| **Eval Sprint Vòng 1 `4,5x`** *(`10K USD`, chỉ dùng vòng thi)* | `2.683` | `48,42%` | `1,272` | `+0,0450R` (`+6,04 USD` / `+155.626 VND`) | `1,194` | `+23,16%` (`+26,98% / +20,29%`) | `25,09%` *(cắt `StaticKill 9,5%`)* | `4,45%` | `11` lệnh | `0,923` | `1,246` | `3,75%` |

*(Mô phỏng trực tiếp Funded `1,0x` từng gói theo vốn thực, đòn bẩy thực và sàn làm tròn `0,01` lot — KHÔNG nội suy tuyến tính từ `100K`: gói `50K` đạt `2.829` lệnh, `EV/lệnh = +8,81 USD` / `+226.998 VND`, `Sharpe 1,248`, `Calmar 1,049`, `DD 6,79%`, `PF 1,204`; gói `25K` đạt `2.829` lệnh, `EV/lệnh = +4,37 USD` / `+112.597 VND`, `Sharpe 1,251`, `Calmar 1,056`, `DD 6,68%`, `PF 1,205`; gói `10K` đạt `2.825` lệnh, `EV/lệnh = +1,69 USD` / `+43.544 VND`, `Sharpe 1,250`, `Calmar 1,046`, `DD 6,51%`, `PF 1,205`; gói `5K` The5ers rơi `28` lệnh rủi ro nhỏ dưới sàn `0,01` lot còn `2.799` lệnh, `EV/lệnh = +0,79 USD` / `+20.355 VND`, `Sharpe 1,217`, `Calmar 1,009`, `DD 6,22%`, `PF 1,200`.)*

### 3.3. Bảng 2A — Toàn Cảnh `7` Gói Quỹ SSOT Hợp Lệ Tại Việt Nam (`available_vn = true`, Thống Nhất `KS = 8,00%`)

> **Nhãn bắt buộc:** `XẤP XỈ CẤP NGÀY` (`DAILY_APPROX_V103_PARITY`), `N = 10.000` đường, `seed = 20261127`, `1` vé đơn không thử lại, tỷ giá quy đổi `25.765,94 VND/USD`, thống nhất `InpKillStaticDdPct = 8,00%` trên toàn bộ `7/7` gói. Gói `FTMO` đã đo thông số Demo (`MEASURED_DEMO_EXECUTION`); `2` gói `The5ers` mang nhãn **`TERMS_VERIFIED_EXECUTION_UNMEASURED`** — các tệp `.set` The5ers hiện dùng bí danh tạm `US100.cash` / `US500.cash` theo thông số FTMO cho kiểm tra offline `OPS-2` (`symbol_aliases_provisional = true`) và **bị khóa chạy tiền thật/tắt DryRun cho tới khi chụp xong thông số MarketWatch Demo thực tế của The5ers (`the5ers_specs.json`)**.

| Gói quỹ SSOT (`available_vn = true`) | Phí hiệu dụng (`USD` / `tr VND`) | `EV` NPV 24t (`USD` / `tr VND`) | Trung vị 24t (`USD` / `tr VND`) | `EV/Phí` Sprint (vs Nền `1x`) | `EV/lệnh` Funded `1x` (`0,01`-lot) | Đậu 2 vòng `C / U` (ngày) | Payout #1 `C / U` (ngày) | Cháy Funded 12t `KS 8,0%` (`W95 UB`) | Tháng đói Funded | Cháy `4T / 5T` nối tiếp | Best-Day P1 / P2 (Trung vị) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **FTMO Std 10K** *(BF / gốc `+5,98x`)* | `70,42` (`1,81`) | `+615,11` (`+15,85`) | `+560,39` (`+14,44`) | **`+8,74x`** (`+7,58x`) | `+1,69 USD` (`2.825`) | `140,6 / 205,8` | `201,5 / 288,4` | **`0,17%`** (`0,30%`) | `66,41%` | `0,51% / 0,12%` | `44,1% / 70,4%` |
| **FTMO Std 50K** *(BF / gốc `+8,17x`)* | `313,48` (`8,08`) | `+3.229,99` (`+83,22`) | `+2.934,40` (`+75,61`) | **`+10,30x`** (`+8,97x`) | `+8,81 USD` (`2.829`) | `139,1 / 204,4` | `182,6 / 262,3` | **`0,46%`** (`0,65%`) | `58,30%` | `0,76% / 0,16%` | `44,3% / 71,0%` |
| **FTMO Std 100K** *(BF / gốc `+10,63x`)* | `490,65` (`12,64`) | `+6.565,17` (`+169,16`) | `+5.969,98` (`+153,82`) | **`+13,38x`** (`+11,64x`) | `+17,74 USD` (`2.827`) | `139,1 / 204,4` | `181,2 / 260,9` | **`0,50%`** (`0,70%`) | `57,11%` | `0,74% / 0,15%` | `44,3% / 71,3%` |
| **FTMO Swing 10K** *(giá gốc)* | `112,43` (`2,90`) | `+600,06` (`+15,46`) | `+557,68` (`+14,37`) | **`+5,34x`** (`+4,59x`) | `+1,69 USD` (`2.825`) | `140,6 / 205,8` | `201,5 / 288,4` | **`0,17%`** (`0,30%`) | `66,41%` | `0,51% / 0,12%` | `44,1% / 70,4%` |
| **FTMO Swing 25K** *(giá gốc)* | `316,87` (`8,16`) | `+1.546,06` (`+39,84`) | `+1.440,30` (`+37,11`) | **`+4,88x`** (`+4,18x`) | `+4,37 USD` (`2.829`) | `139,1 / 204,4` | `187,0 / 268,1` | **`0,43%`** (`0,61%`) | `60,47%` | `0,66% / 0,15%` | `44,2% / 70,9%` |
| **The5ers HS 5K Classic** *(8%/5%, unmeasured)* | `39,97` (`1,03`) | `+259,29` (`+6,68`) | `+260,77` (`+6,72`) | **`+6,49x`** (`+5,55x`) | `+0,79 USD` (`2.799`) | `123,9 / 175,4` | `321,8 / 446,4` | **`0,05%`** (`0,14%`) | `87,69%` | `0,41% / 0,06%` | `51,8% / 70,0%` |
| **The5ers HS 5K New** *(10%/5%, unmeasured)* | `35,88` (`0,92`) | `+242,48` (`+6,25`) | `+177,94` (`+4,58`) | **`+6,76x`** (`+5,80x`) | `+0,79 USD` (`2.799`) | `147,8 / 208,7` | `344,2 / 489,9` | **`0,04%`** (`0,12%`) | `87,64%` | `0,51% / 0,10%` | `44,1% / 69,9%` |

*(Ghi chú đệm 4 vé nối tiếp trên FTMO Std 10K BF tại `KS = 8,00%`: tỷ lệ đậu trong 24 tháng đạt **`96,31%`**, `EV` NPV 24t `+755,16 USD` / `+19,46 tr VND`, dùng trung bình `1,424` vé, cháy sạch cả 4 vé chỉ **`0,51%`**, `P(NPV <= 0)` cho `1` vé đơn là `31,74%` trên FTMO 10K, `31,68%` trên 50K, `31,48%` trên 100K, `35,04%` trên The5ers 5K Classic và `37,42%` trên The5ers 5K New.)*

### 3.4. Bảng 2B — Tỷ Lệ `Đậu / Rớt / Chờ` Theo Mốc Thời Gian (Mỗi Ô Luôn Tổng `= 100,0%`)

| Gói quỹ SSOT | Mốc `3` tháng (`Đậu / Rớt / Chờ`) | Mốc `6` tháng (`Đậu / Rớt / Chờ`) | Mốc `12` tháng (`Đậu / Rớt / Chờ`) | Mốc `24` tháng (`Đậu / Rớt / Chờ`) |
|---|---|---|---|---|
| **FTMO Std 10K** | `18,37% / 6,82% / 74,81%` | `45,49% / 17,10% / 37,41%` | `65,34% / 26,57% / 8,09%` | `70,15% / 29,54% / 0,31%` |
| **FTMO Std 50K** | `18,82% / 7,29% / 73,89%` | `45,70% / 17,92% / 36,38%` | `64,98% / 27,48% / 7,54%` | `69,60% / 30,16% / 0,24%` |
| **FTMO Std 100K** | `18,86% / 7,37% / 73,77%` | `45,80% / 17,97% / 36,23%` | `65,23% / 27,43% / 7,34%` | `69,71% / 30,02% / 0,27%` |
| **FTMO Swing 10K** | `18,37% / 6,82% / 74,81%` | `45,49% / 17,10% / 37,41%` | `65,34% / 26,57% / 8,09%` | `70,15% / 29,54% / 0,31%` |
| **FTMO Swing 25K** | `18,67% / 7,16% / 74,17%` | `45,63% / 17,85% / 36,52%` | `65,19% / 27,12% / 7,69%` | `69,87% / 29,83% / 0,30%` |
| **The5ers HS 5K Classic** | `24,25% / 6,32% / 69,43%` | `51,70% / 16,07% / 32,23%` | `68,96% / 24,26% / 6,78%` | `73,10% / 26,72% / 0,18%` |
| **The5ers HS 5K New** | `16,92% / 6,35% / 76,73%` | `44,60% / 16,20% / 39,20%` | `65,62% / 25,38% / 9,00%` | `71,06% / 28,61% / 0,33%` |

*(Công khai biên rớt vòng thi 24 tháng: dải chọn `20%–30%` được neo trên gói chuẩn **`ftmo_standard_10k` (`29,54%`)**; các gói lớn hơn có bước lot `0,01` mịn hơn ít bị làm tròn xuống nên tỷ lệ rớt Eval 24t nhỉnh nhẹ trên mốc `30,00%`: **`ftmo_standard_50k = 30,16%` (`+0,16%`)** và **`ftmo_standard_100k = 30,02%` (`+0,02%`)**, trong khi `5/7` gói còn lại nằm trong `26,72%–29,83%`.)*

### 3.5. Ngưỡng Gãy, Độ Nhạy Ma Sát & Ổn Định 2 Cụm (FTMO Std 10K BF, Thống Nhất `KS = 8,00%`)

- **Cấp độ bằng chứng (điểm neo trung thực):** `DEV_BACKTEST_2018_2024_CLUSTER_B_VIEWED_NOT_BLIND_DAILY_APPROX_V103_PARITY` — dữ liệu `Dev 2018–2024` đã được xem ở các đợt trước; **`Holdout 2025+` chưa mở** cho `v1.03-Sprint`; **chưa có kiểm chứng Demo/Live thực tế** (`demo_live_verified = false`).
- **Tách riêng Bot tự phanh vs Vi phạm cứng của quỹ (tại ma sát `1,00x`, `KS = 8,00%`):** `BOT_AUTO_KILL = 32,19%` (trong đó tự phanh tĩnh `StaticKill = 28,61%`), `FIRM_HARD_BREACH = 2,31%` (chủ yếu do khoảng nhảy giá vòng thi; cần xác minh chặt trên MT5 Real-Tick Tester Dev).
- **Ổn định trên cả `2` cụm thời gian (đều thắng nền `Funded 1,0x`):** Cụm A (`2018–2020`, `666` ngày): **`+11,73x`** (`+825,73 USD`, cháy Funded `0,22%`) so với nền `+9,85x`; Cụm B (`2021–2024`, `898` ngày): **`+6,78x`** (`+477,32 USD`, cháy Funded `0,12%`) so với nền `+6,12x`.
- **Ngưỡng gãy theo hệ số trượt giá / phí thực thi (FTMO Std 10K BF, `KS = 8,00%`):**
  - `0,66x` (phí thuận lợi): `EV/Phí = +13,16x` (`+926,57 USD`), Rớt `19,26%`, Cháy Funded `0,06%`.
  - `1,00x` (chuẩn đo Demo): `EV/Phí = +8,74x` (`+615,11 USD`), Rớt `29,54%`, Trung vị `+560,39 USD`, `P(<=0) = 31,74%`, Cháy Funded `0,17%`.
  - **`1,50x` (NGƯỠNG GÃY TRUNG VỊ):** `EV/Phí` còn `+4,01x` (`+282,58 USD`), nhưng **Trung vị 24t rơi xuống âm `-70,42 USD` (`-1,81 tr VND`)**, `P(<=0) = 51,43%`, Rớt `46,88%`, cháy `4` vé tăng lên `4,83%`.
  - `1,75x` (suy thoái nặng): `EV/Phí = +2,47x` (`+173,99 USD`), Rớt `55,53%`, `P(<=0) = 60,72%`, cháy `4` vé vọt lên `9,51%`.

### 3.6. Thang Điểm Dọc Law 15 (`🔴 Xấu` · `🟡 Đủ dùng` · `🟢 Tốt` · `🏆 Top 1% thực tế`)

- **1. Kỳ vọng mỗi lệnh (`EV/lệnh` sau phí — Funded `1,0x`: `+0,0455R`):**
  - 🔴 Xấu: `<= 0,00R`
  - 🟡 Đủ dùng: `+0,03R .. +0,06R` *(cần tần suất lệnh cao)* — **VỊ TRÍ HIỆN TẠI (`+0,0455R`, ~`404` lệnh/năm)**
  - 🟢 Tốt: `+0,07R .. +0,15R`
  - 🏆 Top 1% thực tế: `> +0,15R` bền trên tiền thật *(hoặc `+0,06R+` kèm độ êm rất cao)*
  - *Khoảng cách tới Top 1%:* Biên từng lệnh còn mỏng nên nhạy với trượt giá `>= 1,5x`; cần kiểm soát trượt giá chặt bằng `OPS-4`/`OPS-6` và mở rộng thêm nhánh mới ở Đợt 4.
- **2. Hệ số sinh lời (`Profit Factor` nhiều năm sau phí — Funded `1,0x`: `1,204`):**
  - 🔴 Xấu: `< 1,05`
  - 🟡 Đủ dùng: `1,05 .. 1,20`
  - 🟢 Tốt: `1,15 .. 1,35` (chuẩn mục tiêu Law 15: `1,25 .. 1,50`) — **VỊ TRÍ HIỆN TẠI (`1,204`, ranh giới Đủ dùng -> Tốt)**
  - 🏆 Top 1% thực tế: `>= 1,35 .. 1,50+` bền trên tiền thật `>= 12` tháng
  - *Khoảng cách tới Top 1%:* Thiếu khoảng `+0,15 .. +0,30` điểm `PF`; không thể nâng bằng cách tăng đòn bẩy mà phải tăng chất lượng danh mục đa nguồn.
- **3. Sụt giảm sâu nhất (`Max DD` ở mức an toàn `1,0x` so với trần quỹ `10%` — Hiện tại: `6,82%`):**
  - 🔴 Xấu: `> 10,0%`
  - 🟡 Đủ dùng: `7,5% .. 9,0%`
  - 🟢 Tốt: `5,0% .. 7,0%` — **VỊ TRÍ HIỆN TẠI (`6,82%`, sụt ngày lớn nhất `1,52%`)**
  - 🏆 Top 1% thực tế: `4,0% .. 7,0%` đi cùng tỷ lệ tháng có lãi cao và ít tháng đói
  - *Khoảng cách tới Top 1%:* Độ sâu DD đã nằm vùng tốt, nhưng tỷ lệ tháng không có payout trên `1` tài khoản FTMO còn cao (`57,1%–66,4%`).
- **4. Độ êm lợi nhuận (`Calmar` & `Sharpe` Funded `1,0x` — Hiện tại: `Calmar 1,051`, `Sharpe 1,250`):**
  - 🔴 Xấu: `Calmar < 0,4` · `Sharpe < 0,5`
  - 🟡 Đủ dùng: `Calmar 0,4 .. 0,8` · `Sharpe 0,5 .. 1,0`
  - 🟢 Tốt: `Calmar 0,8 .. 1,5` · `Sharpe 1,0 .. 1,5` — **VỊ TRÍ HIỆN TẠI (`Calmar 1,051`, `Sharpe 1,250`)**
  - 🏆 Top 1% thực tế: `Calmar >= 1,5 .. 2,0` · `Sharpe >= 1,5 .. 2,0` trên tiền thật `>= 12` tháng từ nhiều nguồn độc lập
  - *Khoảng cách tới Top 1%:* Cần thêm `+0,45` Calmar và `+0,25..0,75` Sharpe từ nhánh lệch pha ngoài CFD (Crypto Spot nhân quả + Macro ETF ở Đợt 4).
- **5. Hiệu quả thi quỹ (`EV/Phí` & An toàn Funded — Hiện tại: `+8,74x` FTMO 10K BF / `+13,38x` 100K, cháy Funded `0,04%–0,50%` tại `KS = 8,00%`, chờ Payout #1 `6,7–9,5` tháng):**
  - 🔴 Xấu: `<= 1,0x` hoặc cháy Funded `> 5%`
  - 🟡 Đủ dùng: `+1,0x .. +3,0x`
  - 🟢 Tốt: `+3,0x .. +8,0x`, cháy Funded `< 1%`, chờ Payout #1 `5..10` tháng — **ĐỊNH VỊ TỔNG THỂ HIỆN TẠI (`🟢 Tốt trên Dev, chờ xác minh thực địa`)**
  - 🏆 Top 1% thực tế: `>= +8,0x`, cháy Funded `< 1%`, cháy `4` vé `< 1%`, rút tiền về `2..4` tháng và **đã chứng minh trên tiền thật / Demo**
  - *Khoảng cách tới Top 1%:* Chỉ số `EV/Phí` (`+8,74x..+13,38x`) và an toàn Funded (`0,04%–0,50%`, Wilson 95% UB `0,12%–0,70% << 1,00%`) đã đạt chuẩn Top 1% trên mô phỏng Dev, nhưng còn **2 khoảng trống thật**: (a) chưa qua cổng kiểm chứng MT5 Strategy Tester `>= 98%` + Demo/Live thực tế, và (b) thời gian chờ Payout #1 (`6,7–9,5` tháng) vẫn chậm hơn ngưỡng `2–4` tháng do mới có `1` cụm động cơ CFD.

---

## 4. Giải Phẫu Khoa Học `12` Họ Chiến Lược (`1.137` Phép Thử Cụm B `2021–2024`)

### 4.1. Chứng Minh Toán Học Về Giả Thuyết Không (Vì Sao `0 / 1.137` Là Kết Quả Đúng)

- Toàn bộ `1.137` ứng viên (`142` Chính + `995` Thăm dò bổ sung) được chọn hoàn toàn mù trên Cụm A (`2018–2020`), chạy đúng `1` lần trên Cụm B (`2021–2024`), lưu đầy đủ `1.279` dòng vào sổ cái kép DuckDB/SQLite (`142` `offensive3_primary_m200` + `1.137` `offensive3_exploratory_m1200`), chạy đủ `G7_pbo_cscv` (`S = 16`, `12.870` tổ hợp) trên `1.137/1.137` (`100%`) và kiểm định dấu `50.000` lần (`sign_flip_p_numba`).
- Phân bổ chuẩn hóa `evaluated_by_blindness_tier` tính gộp cả mã dẫn (`leader`) lẫn mã mục tiêu (`target`) trong [OFFENSIVE3-ALPHA-FUNNEL-20261127.json](OFFENSIVE3-ALPHA-FUNNEL-20261127.json) (`sha256 = 465211ea...`): `DEV_CLB_CONSUMED_12OLD = 534` · `MIXED_12OLD_AND_NEW9 = 206` · `TRUE_BLIND_CLB_NEW7_CROSSES = 172` · `NEW9_D1_VIEWED_M1_UNSEEN = 111` · `MIXED_ALL_3_TIERS = 82` · `MIXED_NEW9_AND_TRUE_BLIND_7 = 29` · `MIXED_12OLD_AND_TRUE_BLIND_7 = 3` (tổng đúng **`1.137`**).
- Trên `142` ứng viên Chính: chỉ `44` (`31,0%`) dương sau phí `1x`, `31` (`21,8%`) dương sau phí `2x`, `18` (`12,7%`) qua `MC >= 90%`, và chỉ **`4` ứng viên (`2,82%`)** có `p_sign_flip_50k <= 0,05` — **thấp hơn cả kỳ vọng nhiễu ngẫu nhiên `5%`** (`7,1` trên `M = 142` và `3,6` trên `N_eff = 72,00`).
- Để đứng hạng `#1` vượt ngưỡng `BH-FDR q <= 0,10` trên `M = 142`, ứng viên cần `p <= 0,000704` (tương ứng `Sharpe` mù 4 năm `>= ~1,60`). Ứng viên tốt nhất nhánh Chính chỉ đạt `p = 0,003520` -> `q_primary = 0,49983 > 0,10`; kể cả điều chỉnh theo số phép thử độc lập hiệu dụng (`N_eff = 72,00`) vẫn cho `p * N_eff = 0,2534 > 0,10` (không phân biệt được với nhiễu đa kiểm định).

### 4.2. Bảng Tổng Hợp Đủ `12` Họ Chiến Lược (`F01..F12` — Cụm B `2021–2024`)

| Họ chiến lược | Chính / Thăm dò bổ sung (Tổng) | Chính: `1x>0 / 2x>0 / MC90 / p<=0,05` | Toàn bộ: `1x>0 / 2x>0 / MC90 / p<=0,05` | `PBO (CSCV)` | `N_eff` | `Sharpe` Cl.B cao nhất | Nhận xét mổ xẻ ngắn |
|---|---:|---:|---:|---:|---:|---:|---|
| `F01_LOWFREQ_CAT` | `13 / 83 (96)` | `7 / 5 / 4 / 1` | `37 / 25 / 13 / 5` | `0,1603` | `24,41` | `1,399` | Mạnh nhất chiến dịch (US100 M1 `swap = 0`), PBO thấp, nhưng vẫn trượt `BH-FDR`. |
| `F02_IDX_SWEEP_REV` | `13 / 85 (98)` | `5 / 4 / 2 / 1` | `44 / 29 / 12 / 3` | `0,4693` | `35,91` | `1,031` | Sát ngưỡng PBO `0,50`; có ứng viên GER40/USDJPY dương `2x` nhưng không qua FDR. |
| `F03_FX_FIX_FLOW` | `9 / 84 (93)` | `0 / 0 / 0 / 0` | `15 / 4 / 29 / 0` | `0,4057` | `19,48` | `0,499` | Sụp đổ hoàn toàn trên Cụm B (`0/9` Chính dương `1x`, `0/93` có `p <= 0,05`). |
| `F04_ENERGY_METAL` | `14 / 66 (80)` | `3 / 2 / 2 / 0` | `18 / 14 / 11 / 2` | `0,2470` | `23,34` | `1,013` | Lead-lag `XAU -> XAG` có tín hiệu D1 nhưng cỡ mẫu nhỏ (`n = 14–36`), trượt FDR. |
| `F05_INTERMARKET` | `10 / 85 (95)` | `3 / 1 / 1 / 1` | `18 / 14 / 12 / 1` | `0,3639` | `28,78` | `0,862` | Lan truyền `US100 -> JP225` đạt `n = 208` trên D1, nhưng `p = 0,0386` -> `q = 1,00`. |
| `F06_SWING_TSMOM` | `16 / 84 (100)` | `5 / 4 / 1 / 0` | `14 / 11 / 2 / 0` | `0,3466` | `25,28` | `0,785` | Bị swap + kiểm định timing ngẫu nhiên loại sạch (`0/100` đạt `p <= 0,05`). |
| `F07_SWING_XSEC` | `16 / 84 (100)` | `3 / 1 / 4 / 0` | `6 / 1 / 11 / 0` | **`0,5190`** *(Overfit)* | `30,23` | `0,534` | Học vẹt nặng (`PBO > 0,50`), chỉ `1/100` sống sót ở phí `2x`. |
| `F08_SWING_PULLBACK` | `13 / 87 (100)` | `4 / 3 / 1 / 0` | `27 / 19 / 3 / 1` | **`0,6756`** *(Overfit)* | `46,14` | `0,805` | Học vẹt rất nặng (`PBO = 0,68`), nhánh RSI2 US100 trượt MC cùng chiều (`85,5%`). |
| `F09_SWING_CALENDAR` | `16 / 76 (92)` | `10 / 8 / 0 / 0` | `43 / 30 / 1 / 0` | **`0,7201`** *(Overfit)* | `18,20` | `0,731` | Bẫy Beta kinh điển: `10/16` dương `1x` nhưng **`0/16` thắng nổi MC ngẫu nhiên**! |
| `F10_TRUE_BLIND_CROSS7` | `6 / 86 (92)` | `1 / 1 / 1 / 0` | `10 / 8 / 19 / 1` | `0,1868` | `29,26` | `1,261` | Tập mù hoàn toàn sạch PBO; `EURGBP` thăm dò đạt `Sh = 1,26` nhưng `n = 36`, `q = 1,00`. |
| `F11_PAIRS_STATARB` | `6 / 89 (95)` | `2 / 2 / 2 / 1` | `10 / 7 / 3 / 1` | `0,1066` | `37,25` | `0,824` *(ảo giác `UK100` -> `-0,388`)* | PBO thấp nhất (`0,11`), nhưng nhánh top `GER40/UK100` bị Red-Team #1 bóc trần ảo giác `UK100` zero-gap (sập về `-0,388` khi thêm trễ `+1`). |
| `F12_CLEANROOM_TOP` | `10 / 86 (96)` | `1 / 0 / 0 / 0` | `19 / 10 / 4 / 1` | `0,1159` | `46,65` | `1,356` | Đa dạng nhất (`N_eff = 46,65`); ý tưởng `ER+ATR-Z` US100 tốt ở nhánh thăm dò (`q = 1,00`). |
| **TỔNG `12` HỌ** | **`142 / 995 (1.137)`** | **`44 / 31 / 18 / 4`** | **`261 / 172 / 120 / 15`** | **`0,3308` / `0,2659`** | **`72,00` / `211,03`** | **`1,399`** | **`0` `TIER_1`, `0` `TIER_2`, `1.137` `TIER_3` (`ZERO` hạ chuẩn).** |

### 4.3. Giải Phẫu `7` Cổng Loại Chính (Core Gates) & Các Cổng Prop

- **7 cổng lõi (Core Gates — trên `1.137` ứng viên, một ứng viên có thể trượt nhiều cổng cùng lúc):**
  1. `CORE_BH_FDR_GT_010` — **`1.137 / 1.137` (`100,0%`):** Không đạt kiểm soát phát hiện giả toàn chiến dịch `q <= 0,10`.
  2. `CORE_TRIM5_WINNERS_PF_LE_1` — **`1.044 / 1.137` (`91,8%`):** `PF <= 1,0` ngay khi cắt `5%` lệnh thắng lớn nhất.
  3. `CORE_RANDOM_ENTRY_MC_LT_90` — **`1.017 / 1.137` (`89,4%`):** Không thắng `90%` điểm vào ngẫu nhiên cùng thời gian giữ lệnh và phí/swap.
  4. `CORE_COST_2X_FAIL` — **`965 / 1.137` (`84,9%`):** Bị ma sát `2x` ăn mòn thành âm.
  5. `CORE_SAMPLE_OR_SIGN_FAIL` — **`905 / 1.137` (`79,6%`):** Thiếu cỡ mẫu tối thiểu (`30` Swing / `50` Intraday) hoặc dấu lợi nhuận không đạt.
  6. `CORE_ZERO_POS_SWAP_FAIL` — **`613 / 1.137` (`53,9%`):** Gãy khi khóa không cho ăn swap dương ảo.
  7. `CORE_FADE_BEAT_FAIL` — **`570 / 1.137` (`50,1%`):** Không thắng được đối chứng đánh ngược chiều (`Fade`).
- **Các cổng Prop bổ sung:** `PROP_COUNCIL_REJECT_KILLED` (`1.137`), `PROP_PRIMARY_M200_BH_FDR` (`1.137`), `PROP_DSR_OR_SHARPE_FLOOR` (`1.136`), `PROP_MATCHED_HOLD_TIMING_P_GE_005` (`1.123`), `PROP_ROBUSTNESS_FAIL_FRAGILE` (`1.093`, thêm `19` cảnh báo `WARN`), `PROP_G7_PBO_GT_050` (`292` — tập trung ở 3 họ `F07/F08/F09`), `PROP_FTMO_DD_LIMIT_BREACH` (`141`), `PROP_PORT7E_ORTHOGONALITY` (`43`), `PROP_CRISIS_3WIN_FAIL` (`27`).

### 4.4. Ghi Nhận Minh Bạch `4` Ứng Viên Sát Nút (`KHÔNG THĂNG HẠNG`)

Bốn ứng viên nổi bật nhất dưới đây đều bị gắn nhãn **`TIER_3_DEAD_NO_EDGE — KHÔNG THĂNG HẠNG`** và **tuyệt đối không đưa vào `Prop V3`** vì trượt cổng `BH-FDR` (chỉ được phép xem xét như giả thuyết mới nếu đăng ký theo dõi tiền cứu không dùng tiền thật trong chiến dịch tương lai):

| Ứng viên sát nút (`KHÔNG THĂNG HẠNG`) | Nhóm & Tầng mù | Độ phân giải | `n` lệnh | `1x / 2x / Fade` (`R`) | `Sharpe` | `MC` (Unb/Same) | `Trim5 PF` | `r / tail` vs `7E` | `PBO` | Lý do loại cứng (`G08 / G09`) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **`F01_US100_NY30_STOP_COIL`** | `PRIMARY #1` · `DEV_CLB_CONSUMED_12OLD` | M1 `swap = 0` | `216` | `+18,11 / +16,59 / -29,11` | `1,325` | `99,9% / 99,8%` | `1,36` | `+0,05 / +0,14` | `0,160` | Trượt `BH-FDR` (`p_50k = 0,00352`, `q_prim = 0,4998 > 0,10`, `p*N_eff = 0,253 > 0,10`), `DSR thực nghiệm = 0,374 < 0,50`, dữ liệu đã xem cũ. |
| **`F02_GER40_PDAY_SW20_R45_FLAT`** | `PRIMARY #2` · `DEV_CLB_CONSUMED_12OLD` | M1 `swap = 0` | `111` | `+12,03 / +10,90 / -15,44` | `0,981` | `99,4% / 99,4%` | `1,33` | `+0,01 / -0,08` | `0,469` | Trượt `BH-FDR` (`p_50k = 0,02308`, `q_prim = 1,00`), `DSR thực nghiệm = 0,142 < 0,50`, `PBO` sát trần `0,50`. |
| **`F05B_TZ_US100_to_JP225_cont_1d_z10_h3`** | `PRIMARY #3` · `MIXED_12OLD_AND_NEW9` *(mã dẫn `US100` `12OLD` -> `JP225` `NEW9`)* | D1 Swing | `208` | `+22,44 / +17,76 / -42,58` | `0,862` | `99,3% / 99,2%` | `1,17` | `+0,04 / -0,20` | `0,364` | Trượt `BH-FDR` (`p_50k = 0,03856`, `q_prim = 1,00`), `DSR thực nghiệm = 0,093 < 0,50`, mới ở D1 chưa có M1 Bid/Ask. |
| **`F10_B_PB_EURGBP_Z125_S100_H4_TP15`** | `EXPLORATORY` · `TRUE_BLIND_CLB_NEW7_CROSSES` | D1 Swing | `36` | `+7,55 / +6,50 / -8,53` | `1,261` | `99,8% / 99,8%` | `2,71` | `-0,04 / +0,00` | `0,187` | Thuộc nhóm Thăm dò (`M = 1.137`, `p_50k = 0,00466`, `q_expl = 1,00`), `DSR thực nghiệm = 0,027`, cỡ mẫu nhỏ (`36` lệnh D1). |

> **Cảnh báo ảo giác đã bị Kiểm Toán Độc Lập #1 bóc trần (`#742`, `P0-01` — ĐÃ VÁ DỨT ĐIỂM ở `#750`, KHÔNG phải ứng viên sát nút thật):** Ứng viên `F11_SW_GER40_UK100_KALMAN_Z200_H8` từng ghi `Sharpe Cl.B = +0,824` (`n = 32`, `1x = +1,26R`, bị loại ở `q_prim = 1,00`) đã bị **Red-Team #1** chứng minh là **ảo giác chồng lấn cùng ngày từ dữ liệu Yahoo `UK100`** (`zero_gap_frac = 99,66%`, `open[t] == close[t-1]` lúc `16:30 UTC` sớm hơn `5,5–7,5` giờ so với phiên đóng `GER40` M1): khi làn `g06-causality-fixer` bổ sung rào chắn trễ nhân quả `+1` thanh trên `fam11`, `fam12`, `fam08` (`#750`), `Sharpe` Cụm A của mã này sập từ `+0,416` xuống **`-0,594`** và `Sharpe` Cụm B sập từ `+0,824` xuống **`-0,386`** (`Winrate 43,8%`); toàn bộ `14/14` biến thể F11 `UK100` đều có `Sharpe Cl.B <= -0,315`. Biên nhận `prop_v3_metrics.json` chỉ ghi thẻ đối chứng `DIAG_COUNTERFACTUAL_NOT_PROMOTED` cho ứng viên `#1` (`F01_US100_NY30_STOP_COIL`) để giải trình toán học vì sao vẫn bị loại.

---

## 5. Mũi 3 (`OPS-1..OPS-6`), Xuất Gói Layer 2 & Nợ Kỹ Thuật `P1` Từ Kiểm Toán Độc Lập

### 5.1. Bảng Tổng Hợp Trọn Bộ Mũi 3 (`OPS-1..OPS-6` — `100%` Offline, `0` Ghi Live)

| Làn | Sản phẩm chính (`Layer 1` / `Layer 2`) | Phạm vi bảo vệ thực chiến | Kiểm thử & Biên dịch |
|---|---|---|---|
| **`OPS-1`** Feed, DST & Tin đỏ `8-CCY+EIA` | `live_ops/feed_dst_news_guard.py`, `configs/calendars/red_news_extended_off3_8ccy_eia.json` (`568` mốc: `441` Dev + `127` Live 2026–2027), `Naqex_ExtendedGuardV3.mqh` | Tách US (`17:00 NY`) vs EU (`Prague/London/Athens`) DST, cảnh báo hết hạn lịch TTL (`>14d / <=14d / <=3d`), khớp mã tin cho `USOIL/UKOIL/JP225/CHF/NZD`, phát hiện tick đứng giá & dãn spread. | `18/18` lượt làn (`6` bài riêng) · `.mqh` `0e/0w` |
| **`OPS-2`** Khóa tài khoản & Eval-vs-Funded | `live_ops/account_phase_preflight.py`, `Naqex_AccountPhaseGuard.mqh` | Khóa `login`/`DEMO-REAL`, **chặn cứng `.set` vòng thi gắn vào Funded** (`8` mã từ chối), kiểm đòn bẩy theo lớp tài sản, MarketWatch/Spec parity, chống trùng Magic/đối lệnh cùng hãng, cảnh báo `Inactivity 21/27/30d`, `Best-Day >45/50%`, bắt buộc `InpAllowManualHaltFile=true` & `InpWritePrimaryHeartbeat=true`. | `22/22` lượt làn (`16` bài riêng) · `.mqh` `0e/0w` |
| **`OPS-3`** Cứng hóa VPS, Kill-Switch & Chaos | `5` kịch bản PowerShell trong `vps_kit/hardening_v3/` (`audit_firewall_minimal`, `rotate_mt5_logs`, `fim_sha256_daily`, `emergency_killswitch_guard`, `sync_live_vault_readonly`) + `CHAOS-DRILL-PLAYBOOK.md` | Kiểm tra tường lửa tối thiểu, xoay vòng log MT5 (`C: > 20 GB`), giám sát băm SHA-256 hằng ngày, **Công tắc dừng khẩn cấp kiểm tra `manual_halt_ack` trong `<= 10s`** (thất bại thoát mã `2` báo đỏ), kéo băng log 1 chiều (`0` ghi ngược VPS), diễn tập `5` kịch bản sự cố. | `13/13` lượt làn (`7` bài riêng, `5/5` AST `.ps1` sạch) |
| **`OPS-4`** Đường ống Vận hành Hằng ngày | `live_ops/daily_live_ops_pipeline.py` | Một lệnh tổng hợp đối soát sao kê, TCA, suy giảm alpha, nhịp tim VPS và `OPS-1/2/6` -> xuất đèn giao thông **`Xanh (1,0x) / Vàng (0,5x) / Đỏ (0,0x + DryRun)`** kèm bản tin ẩn danh OPSEC gửi Telegram và biên nhận SHA-256. | `15/15` lượt làn (`9` bài riêng) |
| **`OPS-5`** Hồ sơ Rút thưởng & Sổ tay Go-Live | `live_ops/payout_audit_packager.py`, `exports/deployment_kit/GO-LIVE-END-TO-END-RUNBOOK.md` | Đóng gói bằng chứng bất biến kèm chuỗi băm SHA-256, tự động chứng nhận hộp trắng (`100%` Hard SL, `0` Grid/Martingale/HFT `<60s`, `0` khớp trong vùng cấm tin đỏ `+-120s`, `0` lệnh mồ côi), ẩn danh Layer 1; sổ tay Go-Live đầu-cuối tuân thủ nghiêm `G12`. | `17/17` lượt làn (`11` bài riêng) |
| **`OPS-6`** Hộp đen `FILE_ANSI` & Mổ xẻ `W1..L4` | `live_ops/live_broker_tape_ingestor.py`, `live_ops/live_parity_forensics.py`, `Naqex_DecisionBlackbox.mqh` | Kho băng quote riêng `.runtime/live-vault/` cách ly tuyệt đối với Dev/Holdout; hộp đen `FILE_ANSI` không UTF-16 BOM; phân loại `5` nhóm sai lệch + tách riêng `LEGITIMATE_GUARD_BLOCK`; phân loại lệnh `W1..L4` kèm **khóa chống học vẹt `N_live >= 30`** (`auto_tune_permitted = false`). | `17/17` lượt làn (`11` bài riêng) · `.mqh` `0e/0w` |

- **Tổng hợp kiểm chứng Mũi 3 & Gói Layer 2 (`private_vault/presets/offensive3_v3/`):**
  - Toàn bộ **`95/95`** bài kiểm thử Mũi 3 & Cleanroom (`71` Live-Ops + OPSEC + kiểm chứng chuỗi) PASS trên cả `python` thường và `python -O`, cộng **`43/43`** bài stdlib chạy sạch trên Windows Python 3.12 không cài `tzdata`; **`Red-Team #3 PASS (P0 = 0, P1 = 0)`**.
  - Biên dịch cô lập `MetaEditor64.exe` trong `.tmp/` (đã xóa sạch thư mục tạm sau khi kiểm tra, **`0` file `.ex5` trong `private_vault/`**): `Naqex_Master_Prop7E_v103.mq5` (`0 errors, 0 warnings`, `2.629 ms`) và harness tích hợp đủ **`3/3` file `.mqh` mới** (`Naqex_ExtendedGuardV3.mqh`, `Naqex_AccountPhaseGuard.mqh`, `Naqex_DecisionBlackbox.mqh` -> `0 errors, 0 warnings`, `1.598 ms`).
  - Xuất đủ `4/4` preset `.set` (`FTMO_Std10K_v103_Sprint_Eval.set`, `FTMO_Std10K_v103_Funded_1x.set`, `The5ers_HS5K_v103_Sprint_Eval.set`, `The5ers_HS5K_v103_Funded_1x.set` — khớp `69/69` khóa `v103.mq5`, LF không BOM, mặc định `DryRun` an toàn, thống nhất `KS = 8,00%` Funded khớp `100%` SHA-256 giữa `m1_v103_sprint_results.json` / `prop_v3_metrics.json` / đĩa, `4/4` PASS `OPS-2` đúng pha và bị TỪ CHỐI CỨNG khi thử gắn Eval vào Funded; riêng `2` tệp The5ers gắn rõ cảnh báo `; PROVISIONAL_SYMBOL_ALIASES` & `TERMS_VERIFIED_EXECUTION_UNMEASURED`, chặn bỏ DryRun tới khi có `the5ers_specs.json`) cùng `2` file `.ini` Strategy Tester Dev (`FromDate = 2018.01.02`, `ToDate = 2024.12.31`, `Model = 4`, `AllowLiveTrading = 0`).

### 5.2. Trạng Thái Đóng Lỗi `P0/P1` Từ Kiểm Toán Độc Lập (Red-Team #1..#4)

- **Kiểm Toán Độc Lập #1 — Holdout, Dữ liệu 28 mã & Nhân quả (`.runtime/offensive3/audits/redteam_1_holdout_data.json`, `verdict = PASS`, `P0 = 0`, `P1 = 0`, `#753`, `sha256 = 3c9e54ee...`, `G01/G03/G06/G07 PASS`, `48/48` pytest `-O` PASS):**
  1. **`P0-01` (ĐÃ VÁ — không làm đổi kết luận `0/0/1.137` hay `Prop V3 Champion`):** Đã bổ sung lớp trễ nhân quả `+1` thanh `_causal_zero_gap_lag_mask` cho `UK100` Yahoo (`zero_gap_frac = 99,66%`) trong `fam11`, `fam12`, `fam08` (`F11_SW_GER40_UK100_KALMAN_Z200_H8` sập về Cl.B `-0,386`; toàn bộ `14` biến thể F11 `<= -0,315`, `7` biến thể F12 `<= -1,196`, `12` biến thể F08 `<= +0,344`).
  2. **`P1-01` (ĐÃ VÁ — `fam06`):** Loại bỏ `np.nanmedian(prev_c)` toàn mảng & bảng swap 2026 khỏi `swap_filter = True` (`32/100` biến thể F06 chạy lại max Cl.B Sharpe `= +0,468`, toàn bộ `TIER_3`).
  3. **`P1-02` & `P1-03` (ĐÃ VÁ — `fam04/05/06/08/11/12`, `stage3_pipeline.py`):** Chuẩn hóa nhãn `blindness_tier` gộp cả mã dẫn lẫn mã mục tiêu về đúng `7` nhãn enum chuẩn (`0` chuỗi nối lỗi) và lưu `evaluated_by_blindness_tier` (`534 / 206 / 172 / 111 / 82 / 29 / 3 = 1.137`) vào `OFFENSIVE3-ALPHA-FUNNEL-20261127.json` (`sha256 = 465211ea...`); `31/31` bài kiểm thử PASS dưới `-O`.
- **Kiểm Toán Độc Lập #2 — Thống kê & Sổ cái (`.runtime/offensive3/audits/redteam_2_stats_fdr.json`, `verdict = PASS`, `P0 = 0`, `P1 = 3` — không làm đổi kết quả `0/0/1.137`):**
  1. **`P1-01` (Tồn đọng trước Đợt 4):** Cổng `G2` trong `research_council.py` dùng công thức `DSR` xấp xỉ cũ `1/(T-1)` (`dsr_council = 0,5174` cho `F01_US100_NY30_STOP_COIL`) thay vì `DSR` thực nghiệm đã ghi vào DuckDB (`dsr_empirical = 0,3740`).
  2. **`P1-02` (Tồn đọng trước Đợt 4):** Ký hiệu cặp `SYM_A/SYM_B` của họ `F11_PAIRS_STATARB` không nằm trong từ điển đơn mã `universe['assets']`, làm `95/95` ứng viên F11 tự rơi về cơ chế `sign_flip_fallback` khi chạy MC và hoán vị thời điểm.
  3. **`P1-03` (`ĐÃ VÁ XONG TRONG ĐỢT NÀY`):** Tệp `tooling/ai-engines/configs/offensive3/preregistration_m1200.json` đã đồng bộ đúng chuẩn `2018–2020` / `2021–2024` và `0,40`.
- **Kiểm Toán Độc Lập #3 — Mũi 3 & Cleanroom (`.runtime/offensive3/audits/redteam_3_ops_cleanroom.json`, `verdict = PASS`, `P0 = 0`, `P1 = 0`, `#749`, `sha256 = c8fa72d0...`):**
  Đóng sạch `5/5` lỗi `P1` + `INFO-01/02`: (`P1-01`/`P1-02`) siết kiểm tra `heartbeat.utc_ts >= flag_write_utc_ts`, xác nhận `open_positions == 0` với `FLATTEN_ALL` và bỏ ép kiểu chuỗi trong `emergency_killswitch_guard.ps1`; (`P1-03`) chặn `NaN`/`Inf`/`bool` ở tham số trần `account_phase_preflight.py`; (`P1-04`) fail-closed khi thiếu/sai `inputs.audit_csv_sha256` trong `payout_audit_packager.py`; (`P1-05`) bổ sung dự phòng múi giờ chuẩn khớp `233.760/233.760` điểm `2018–2027` không phụ thuộc `tzdata` cho `feed_dst_news_guard.py`; (`INFO-01/02`) fail-closed JSONL lỗi & strict-int trong `live_parity_forensics.py`. Toàn bộ `G02/G04/G11/G12/G13/G16` PASS (`95/95` pytest dưới cả thường & `-O`, `0` lỗi `ruff` & `check_architecture --strict`).
- **Kiểm Toán Độc Lập #4 — Toán học M1 Sprint, G09 & B8 Presets (`.runtime/offensive3/audits/redteam_4_accretion_math.json`, `verdict = PASS`, `P0 = 0`, `P1 = 0`, `#755`, `sha256 = e58c1bff...`, `G09/G10/G11/B8 PASS`, `22/22` pytest `-O` PASS):**
  Đóng sạch `4/4` lỗi `P1` + `INFO-01`: (`P1-01`) thống nhất `KS = 8,00%` một nguồn sự thật từ `SprintCandidate` -> `m1_v103_sprint_results.json` (`cd1eea35...`) -> `prop_v3_metrics.json` (`fa1ab9b4...`, đồng bộ `stage3_alpha_funnel_sha256 = 465211ea...`) -> `.set` trên đĩa, bỏ bảng cứng `3` gói cũ và xuất động đủ `7/7` gói; (`P1-02`) rào chắn Vector V1 từ chối `NaN`/`+Inf`/`-Inf`/`bool` tại mọi hàm kiểm soát rủi ro M1 & `enforce_g09_accretion_gate`; (`P1-03`) tính trực tiếp Law-15 Funded `1,0x` từng gói ở vốn/đòn bẩy thực (sàn `0,01` lot: `5K USD` sửa về `+0,79 USD`, `10K USD` sửa về `+1,69 USD`) và công khai minh bạch tỷ lệ rớt Eval `50K = 30,16%` / `100K = 30,02%`; (`P1-04`) gắn cảnh báo `; PROVISIONAL_SYMBOL_ALIASES` + thẻ `TERMS_VERIFIED_EXECUTION_UNMEASURED` / `live_non_dryrun_blocked_until = "the5ers_specs.json"` cho `2` tệp The5ers; (`INFO-01`) sửa chú thích `ftmo_standard_25k` chính xác. Đạt `16/16` bài kiểm thử dưới cả `python` thường & `python -O`, `0` lỗi `ruff` & `check_architecture --strict`.

---

## 6. Lộ Trình Thực Tế Lên Top 1% & Hành Động Kế Tiếp

1. **Tận dụng ngay Mũi 1 (`PORT_7E v1.03-Sprint`) theo mô hình Đa Tài Khoản Quỹ:** Không gắn thêm bot CFD yếu; triển khai đúng kỷ luật `4–5` vé đệm (`ruin < 0,5%`), khóa cứng Funded `1,0x` (đổi `.set` ngay sau khi đậu vòng thi), hoàn phí ở Payout #1 trước khi mở rộng sang `FTMO 50K/100K` và `The5ers 5K` (sau khi đo thực địa Demo).
2. **Dồn lực R&D Đợt 4 sang Sổ Vốn Riêng Đa Nhánh Lệch Pha:** Thay vì tiếp tục quét thêm các biến thể CFD đã cạn biên lợi thế sau ma sát `2x`, kết hợp dòng tiền rút từ Quỹ để xây dựng danh mục đa lớp tài sản (`Alpha #2` Crypto Spot nhân quả + Macro ETF / Frontier Carry) nhằm kéo `Sharpe` hợp nhất lên `>= 1,5–2,0`, `Calmar >= 1,5–2,0` và giảm tỷ lệ tháng đói về vùng **Top 1% thực tế**.
3. **Bước kiểm chứng kế tiếp (`< 2` phút khởi chạy, `0 VND`, `AllowLiveTrading = 0`):** Chạy bài đối chiếu MT5 Strategy Tester Dev (`2018.01.02–2024.12.31`) bằng tệp `private_vault/presets/offensive3_v3/v103_Sprint_Eval_tester_dev.ini` (và sau đó `v103_Funded_1x_tester_dev.ini`) để xác nhận độ khớp lệnh `>= 98%` với Python trước khi chuyển sang Demo Burn-In theo đúng Sổ tay Go-Live `OPS-5`.
