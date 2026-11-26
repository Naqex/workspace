# Báo Cáo Bước 6 (`C10_NEWS_ON` Real-Tick + Phí Thực VN 10K + Demo RO & QUOTE_ONLY) & Prompt Kiểm Toán Astra Vòng 10 (`26/11/2026`)

- **Ngày chốt:** `26/11/2026 22:30 ICT` · **Khóa bất biến:** `Holdout 2025+ SEALED` (`holdout_rows_analysed = 0`, SHA `f0a6b43cb205535b`) · `OrderSend = 0` · **`0 VND`** · `#property version "1.01"` & `3` cờ mặc định `0` (`.ex5` SHA `4c4b2262a0750524`) · `naqex-node1` & `1515343166` nguyên vẹn `UNTOUCHED`.
- **Cấp độ bằng chứng:** Tầng 1 (`6.1`) là **MT5 `Model=4` Real-Tick Q4/2024** (`20.022.579` tick thật, `swap = 0,00`, `max_deal_date = 2024-12-30`) + đối chiếu mù `L0` bộ so sánh `v3`; Tầng 2 (`6.2` & Bộ Tối Ưu 4 Quỹ) là **`DAILY_APPROX` trên Dev `2018–2024` (`CLUSTER_B_VIEWED_NOT_BLIND`)** — chưa mở Holdout mù `2025+`, chưa có giao dịch tiền thật.
- **Kiểm chứng hệ thống:** `31/31` test Bước 6 + Bộ Tối Ưu + OPSEC (`4,93s`) + `system_doctor.py --mode fast` **`9/9 PASS` (`12,05s`)**.

---

## 1. Bước 6.1 — Tách Nhân Quả `2` Lượt MT5 `Model=4` Cho `C10_NEWS_ON` (Chỉ Bật Khiên Tin Đỏ `±5m`, `refresh_mode = 0`)

- **Hồ sơ bằng chứng:** `private_vault/strategies/step6-c10-news-on-and-demo-ro-20261126/step6_1_c10_news_on_mt5_report.json` (`SHA 24d6afcad68b8331`) · `raw_mt5_logs/raw_logs_index.json` (`SHA 9bdfcbb0152b0a29`, `12/12` tệp gốc kèm SHA CSV sau giải nén).
- **Thiết kế thử nghiệm đúng yêu cầu Astra Vòng 9:** Sao chép nguyên văn preset `S5_STD_P1_C10` và `S5_STD_P2_C10` (`FTMO_STD 10K 1:100`, `2024.09.01..2024.12.31`, `InpPostCloseRefreshMode = 0`), chỉ đổi đúng **1 cờ duy nhất** `InpGuardEnableRedNews = True` (`±5m` / pad `300s` / hard-ban `135s`). Pha `Funded` dùng lại `S5_STD_FUNDED_C10` (đã bật tin đỏ từ Bước 5).

### Bảng Đối Chiếu 3 Cấu Hình Trên Cùng `20,02M` Tick Thật (`swap = 0,00 USD`)

| Pha (`FTMO_STD 10K`) | `C00` (`News=ON`) | `C10` (`News=OFF`) | **`C10_NEWS_ON` (`News=ON`)** | **Hiệu ứng thuần Tin Đỏ (`C10_ON - C10_OFF`)** | **Hiệu ứng thuần Cỡ Lệnh + ProfitLock (`C10_ON - C00`)** |
|---|---|---|---|---:|---:|
| **`P1`** | `155` lệnh · **`+708,89 USD`**<br>`PF 1,22` · `EqDD 6,25%` · `SL 35 (gap 19)` | `155` lệnh · `+371,25 USD`<br>`PF 1,10` · `EqDD 8,82%` · `SL 40 (gap 22)` | **`156` lệnh · `+809,26 USD`**<br>**`PF 1,23` · `EqDD 6,25%` · `SL 35 (gap 19)`**<br>*(WR `53,21%`, RR `1,081`, EV `+5,19 USD`, Sharpe `2,03`)* | **`+438,01 USD`**<br>`EqDD -2,57 đ%`<br>`-5 SL`, `-3 SL gap` | **`+100,37 USD`**<br>*(cùng `EqDD 6,25%`, `0` SL thừa)* |
| **`P2`** | `157` lệnh · `+381,62 USD`<br>`PF 1,22` · `EqDD 3,73%` | `156` lệnh · `+462,38 USD`<br>`PF 1,14` · `EqDD 7,61%` | **`157` lệnh · `+665,84 USD`**<br>**`PF 1,23` · `EqDD 5,75%` · `SL 35 (gap 19)`**<br>*(WR `52,87%`, RR `1,098`, EV `+4,24 USD`, Sharpe `1,92`)* | **`+203,46 USD`**<br>`EqDD -1,86 đ%` | **`+284,22 USD`** |
| **`FUNDED`** *(tái dùng Step 5)* | `156` lệnh · `+119,53 USD`<br>`PF 1,10` · `EqDD 2,84%` | *(đã `News=ON`)* | **`157` lệnh · `+161,83 USD`**<br>**`PF 1,11` · `EqDD 3,58%`** | *(cả hai cùng `News=ON`)* | **`+42,30 USD`** |

- **Đối chiếu mù `L0` (`step3` comparator `v3`):**
  - `S6_STD_P1_C10_NEWS_ON`: `py_end = 10.813,17` vs `gt_end = 10.809,26` (`diff = +3,91 USD`, `< 0,04%` vốn), `0` lỗi cộng dồn số dư, `0` lỗi hữu hạn; `lot_mismatch_count = 92` (do biên làm tròn `0,01` lot intraday khi `refresh_mode = 0`).
  - `S6_STD_P2_C10_NEWS_ON`: `py_end = 10.684,27` vs `gt_end = 10.665,84` (`diff = +18,43 USD`, `< 0,18%` vốn), `0` lỗi cộng dồn số dư, `0` lỗi hữu hạn; `lot_mismatch_count = 22`.
- **Kết luận nhân quả Bước 6.1:** Toàn bộ khoản thua `-337,64 USD` của `C10` ở `P1` Bước 5 đến từ việc **tắt khiên tin đỏ** (`+438,01 USD` & `-2,57% EqDD` ngay khi bật lại). **`C10_NEWS_ON` thắng tuyệt đối cả `C00` lẫn `C10 (News=OFF)` ở cả `3/3` pha trên tick thật MT5 `Model=4`**.

---

## 2. Bước 6.2 — Bảng `1` Vé & `2` Vé `FTMO Standard 10K` Theo Giá Thanh Toán Thực Việt Nam (`7` Năm Dev, `DAILY_APPROX`)

- **Hồ sơ bằng chứng:** `private_vault/strategies/step6-c10-news-on-and-demo-ro-20261126/step6_2_10k_real_vn_fees_report.json` (`SHA cfb800e49f5e1b7f`).
- **Xác nhận đếm lại Bước 5 theo Astra Vòng 9:**
  - Trên bảng tổng hợp đầy đủ `full_lifecycle_results` (`2` hợp đồng × `5` ma sát gồm `1,75×` × `2` biên × `2` chế độ vé × `3` chỉ số = `120` ô): **`112` ô `C10` thắng, `8` ô hòa** *(cả `8` đều là trung vị tại `1,75×`, nơi cả hai mất trọn phí vé)*, **`0` ô `C00` thắng**.
  - Trên lưới `1,00×..1,50×` (`detailed_perturbation_checks`): `120/120` ô `C10 > C00`.
- **Khớp chuẩn đối chứng `105,12 USD` (trùng khít từng cent với số Astra Vòng 9):** Tại `1,00×` (`1` vé): `C00 +526,01 USD`, `C10 +735,95 USD`, `C10_NEWS_ON +716,12 USD`; tại `1,50×`: `C00 +225,79 USD`, `C10 +356,69 USD`, `C10_NEWS_ON +333,57 USD` (`P(net <= 0) = 49,05%`).
- **Tỷ lệ hoàn phí khi tính phí thẻ VN `+2,5%`:** Mô phỏng dùng đúng `ext_refund_pct = net / card` (`68,70 / 70,42 = 0,975575` cho Black Friday; `98,61 / 101,08 = 0,975564` cho giá gốc) vì FTMO chỉ hoàn đúng số tiền checkout net, **không hoàn** `2,5%` phí chuyển đổi ngoại tệ của ngân hàng VN (`1,72–2,47 USD`).

### Bảng `1` Vé Không Thử Lại — `FTMO Standard 10K` (`24` Tháng, `25.765,94 VND/USD`, `DAILY_APPROX`)

| Ma sát | Biến thể | Mức phí (`USD` / `tr VND`) | Lãi ròng TB `24T` (`USD` / `tr VND`) | Trung vị `24T` | `EV / Phí` | `P(Lỗ/Hòa <= 0)` | `24T` Đậu / Rớt / Chờ (`100%`) | Cháy Funded `12T` / Tháng đói |
|---|---|---|---|---:|---:|---:|---|---|
| **`0,66×`** *(Demo)* | **`C10_NEWS_ON`** | BF thẻ `70,42` (`1,81 tr`) | **`+1.070,75`** (`+27,59 tr`) | `+1.065,54` | **`+15,21×`** | `18,33%` | `81,7% / 16,4% / 1,9%` | `0,04%` / `54,8%` |
| **`1,00×`** *(Nền)* | `C00` | BF thẻ `70,42` (`1,81 tr`) | `+534,20` (`+13,76 tr`) | `+462,93` | `+7,59×` | `27,21%` | `72,8% / 17,2% / 10,1%` | `0,00%` / `62,9%` |
| **`1,00×`** *(Nền)* | `C10` *(News OFF)* | BF thẻ `70,42` (`1,81 tr`) | `+744,63` (`+19,19 tr`) | `+667,88` | `+10,57×` | `28,54%` | `71,5% / 25,1% / 3,5%` | `0,15%` / `62,8%` |
| **`1,00×`** *(Nền)* | **`C10_NEWS_ON`** | BF net `68,70` (`1,77 tr`) | **`+726,63`** (`+18,72 tr`) | `+639,19` | **`+10,58×`** | `28,86%` | `71,1% / 25,2% / 3,6%` | `0,19%` / `62,6%` |
| **`1,00×`** *(Nền)* | **`C10_NEWS_ON`** | **BF thẻ `70,42` (`1,81 tr`)** | **`+724,91`** (`+18,68 tr`) | `+637,47` | **`+10,29×`** | `28,86%` | `71,1% / 25,2% / 3,6%` | `0,19%` / `62,6%` |
| **`1,00×`** *(Nền)* | **`C10_NEWS_ON`** | Gốc net `98,61` (`2,54 tr`) | `+718,00` (`+18,50 tr`) | `+639,19` | `+7,28×` | `28,86%` | `71,1% / 25,2% / 3,6%` | `0,19%` / `62,6%` |
| **`1,00×`** *(Nền)* | **`C10_NEWS_ON`** | Gốc thẻ `101,08` (`2,60 tr`) | `+715,53` (`+18,44 tr`) | `+636,72` | `+7,08×` | `28,86%` | `71,1% / 25,2% / 3,6%` | `0,19%` / `62,6%` |
| **`1,50×`** *(Stress)* | `C00` | BF thẻ `70,42` (`1,81 tr`) | `+242,06` (`+6,24 tr`) | `+52,50` | `+3,44×` | `49,39%` | `50,6% / 32,1% / 17,3%` | `0,02%` / `73,1%` |
| **`1,50×`** *(Stress)* | **`C10_NEWS_ON`** | **BF thẻ `70,42` (`1,81 tr`)** | **`+349,71`** (`+9,01 tr`) | `+59,55` | **`+4,97×`** | **`49,05%`** | `51,0% / 42,1% / 6,9%` | `0,31%` / `73,2%` |
| **`1,50×`** *(Stress)* | **`C10_NEWS_ON`** | Gốc thẻ `101,08` (`2,60 tr`) | `+334,29` (`+8,61 tr`) | `+58,80` | `+3,31×` | **`49,05%`** | `51,0% / 42,1% / 6,9%` | `0,31%` / `73,2%` |
| **`1,75×`** *(Đỏ)* | **`C10_NEWS_ON`** | BF thẻ `70,42` (`1,81 tr`) | `+214,16` (`+5,52 tr`) | `-70,42` | `+3,04×` | `59,32%` | `40,7%` đậu | — |

- **So sánh nhanh với chế độ `2` vé (`C10_NEWS_ON`, BF thẻ `70,42 USD`):**
  - `1,00×`: Lãi TB **`+827,70 USD` (`+21,33 tr`)**, `EV/Phí +9,38×`, **`P(net <= 0)` giảm một nửa từ `28,86%` xuống `14,51%`**.
  - `1,50×`: Lãi TB **`+428,28 USD` (`+11,04 tr`)**, `EV/Phí +4,27×`, **`P(net <= 0)` giảm từ `49,05%` xuống `32,54%`**.
- **Lưu ý tài chính quan trọng:** Giá Black Friday `70,42 USD` (thay cho `105,12 USD`) tăng `EV/Phí` thêm **`+51%..+57%`** (`6,81× -> 10,29×` tại `1,00×`; `3,17× -> 4,97×` tại `1,50×`) và cắt lỗ khi rớt từ `-2,71 tr` xuống `-1,81 tr`, **nhưng KHÔNG đổi `P(net <= 0) = 49,05%` trên 1 vé ở `1,50×`** (vì đường chưa tới Payout #1 vẫn lỗ trọn 1 vé). Do đó giữ nguyên **`0 VND`** cho đến khi có dữ liệu thực địa & phán quyết Vòng 10.

---

## 3. Bước 6.3 & 6.4 — Trạng Thái Demo Chỉ Đọc `1515343318` & Chuẩn Bị `QUOTE_ONLY` Tháng 12/2026

- **Bước 6.3 (`step6_3_demo_ro_status_report.json`, SHA `96c16a58ef2ebae3`):**
  - **Trạng thái:** **`DEFERRED_SECONDARY_DEMO_1515343318_REVOKED_BY_FTMO_POLICY`**.
  - **Bằng chứng thực tế:** Đã biên dịch sạch script đọc thuần `Naqex_Step6_DemoRO_HydrationProbe.ex5` (`0` lỗi, `0` cảnh báo, `0` gọi `CTrade`/`OrderSend`, SHA `984cee777ec04d9b`). Khi kết nối chỉ đọc tới Demo phụ `1515343318`, terminal mở sạch (`build 6230`) nhưng không được cấp phép mạng (`-10005 IPC timeout`, `0` dòng `Network authorized`). Chủ sở hữu xác nhận FTMO đã khóa đăng nhập tài khoản Demo thứ 2 theo chính sách **1 Free Trial / khu vực / người dùng**, và yêu cầu xóa bỏ thư mục `.runtime/ftmo-demo-portable-1515343318` (đã xóa sạch; `1515343166` và `naqex-node1` hoàn toàn nguyên vẹn `UNTOUCHED`).
- **Bước 6.4 (`step6_4_quote_only_preflight_report.json`, SHA `b98b326a4691bbca`):**
  - Đã hoàn thiện công cụ thu thập chỉ đọc [nfp_cpi_quote_collector.py](../../tooling/ai-engines/ops_cloud/nfp_cpi_quote_collector.py) (`SHA 1209070616ef5623`, `3/3` test đơn vị đạt `8edb1105236f6de6`, đúng schema `23` cột, `record_tier = QUOTE_ONLY`, `OrderSend = 0`).
  - Lịch tin đỏ [naqex_red_news_utc.csv](../../tooling/ai-engines/exports/Files/naqex_red_news_utc.csv) đã xác minh có đủ cả **US NFP `04/12/2026 20:30 ICT` (`1796391000`)** và **US CPI `10/12/2026 20:30 ICT` (`1796909400`)**.
  - **Phát hiện lệch đồng hồ thực tế trên PC Dev:** `w32tm /stripchart` đo thấy PC chính đang lệch **`-1.363,62 ms`** so với `time.cloudflare.com` (vượt ngưỡng `< 1.000 ms`) — bắt buộc chạy `w32tm /resync` trước cửa sổ `20:25 ICT` ngày `04/12` (hoặc chạy trên `naqex-node1` nơi NTP `< 100 ms` nếu Astra + chủ sở hữu duyệt).
  - Live 5s smoke capture tạm hoãn đồng thời với Bước 6.3 do không còn Demo thứ 2.

---

## 4. Prompt Kiểm Toán Sẵn Sàng Gửi GPT-6.2 Astra — Vòng 10 (Bước 6 + Kiểm Toán Toàn Diện Bộ Tối Ưu Vốn 4 Quỹ)

```text
Bạn là GPT-6.2 Astra — kiểm toán viên kỹ thuật và kinh tế độc lập (fail-closed) của Naqex Workspace.
Hãy kiểm toán toàn diện Vòng 10 gồm HAI PHẦN (hoàn toàn offline, KHÔNG khởi chạy MT5, KHÔNG mở Holdout 2025+, giữ 0 VND):

=== KHÓA BẤT BIẾN HIỆN TẠI ===
- Holdout 2025+ SEALED (holdout_rows_analysed = 0, SHA f0a6b43cb205535b).
- OrderSend = 0, tài chính giữ 0 VND, #property version "1.01", 3 cờ opt-in mặc định 0 (.ex5 SHA 4c4b2262a0750524).
- Home-VPS naqex-node1 và Demo chính 1515343166 hoàn toàn UNTOUCHED.
- System Doctor [FAST]: 9/9 PASS (12.05s); pytest bước 6 + optimizer + OPSEC: 31/31 PASS.

=== PHẦN A — KIỂM TOÁN BƯỚC 6 (C10_NEWS_ON REAL-TICK, PHÍ THỰC VN 10K, DEMO RO & QUOTE_ONLY) ===
1. Đối chiếu Bước 6.1 (2 lượt MT5 Model=4 Q4/2024 cho C10_NEWS_ON, refresh_mode=0, CHỈ bật InpGuardEnableRedNews=True):
   - Tệp chính:
     * private_vault/strategies/step6-c10-news-on-and-demo-ro-20261126/step6_1_c10_news_on_mt5_report.json (SHA 24d6afcad68b8331)
     * private_vault/strategies/step6-c10-news-on-and-demo-ro-20261126/raw_mt5_logs/raw_logs_index.json (SHA 9bdfcbb0152b0a29, 12/12 tệp)
   - Kết quả tuyên bố cần bạn tự kiểm tra lại từ .htm và .csv.gz gốc:
     * P1 (S6_STD_P1_C10_NEWS_ON): 156 lệnh, +809.26 USD, PF 1.23, EqDD 6.25%, SL=35 (gap=19), swap=0.00 -> tăng +438.01 USD & giảm -2.57% EqDD so với S5_STD_P1_C10 (+371.25), và thắng S5_STD_P1_C00 (+708.89) thêm +100.37 USD ở cùng mức EqDD 6.25%.
     * P2 (S6_STD_P2_C10_NEWS_ON): 157 lệnh, +665.84 USD, PF 1.23, EqDD 5.75%, SL=35 (gap=19), swap=0.00 -> tăng +203.46 USD & giảm -1.86% EqDD so với S5_STD_P2_C10 (+462.38), thắng S5_STD_P2_C00 (+381.62) thêm +284.22 USD.
     * L0 blind replay v3: P1 diff +3.91 USD (lot_mismatch_count=92), P2 diff +18.43 USD (lot_mismatch_count=22), 0 lỗi cộng dồn số dư, 0 lỗi non-finite. Hãy đánh giá xem lot_mismatch_count 92/22 ở L0 có làm lung lay kết luận chọn C10_NEWS_ON hay không.
2. Đối chiếu Bước 6.2 (Bảng 1 vé & 2 vé Standard 10K theo giá thanh toán thực VN):
   - Tệp chính: private_vault/strategies/step6-c10-news-on-and-demo-ro-20261126/step6_2_10k_real_vn_fees_report.json (SHA cfb800e49f5e1b7f).
   - Kiểm tra công thức hoàn phí ext_refund_pct = net / card (0.975575 cho BF $68.70/$70.42; 0.975564 cho giá gốc $98.61/$101.08), kiểm khớp mốc $105.12 (+526.01 / +735.95 / +716.12 tại 1.00x; P(net<=0)=49.05% tại 1.50x), và đánh giá ý nghĩa việc P(net<=0) vẫn giữ 49.05% trên 1 vé ở 1.50x (nhưng giảm xuống 32.54% ở 2 vé).
3. Đối chiếu Bước 6.3 & 6.4 (Demo phụ 1515343318 bị FTMO thu hồi theo luật 1 Free Trial/khu vực & công cụ QUOTE_ONLY):
   - Tệp: step6_3_demo_ro_status_report.json (SHA 96c16a58ef2ebae3), step6_4_quote_only_preflight_report.json (SHA b98b326a4691bbca), tooling/ai-engines/ops_cloud/nfp_cpi_quote_collector.py (SHA 1209070616ef5623).
   - Xác định đường đi được phép để: (a) kiểm tra đọc lịch sử máy chủ + restart trên Demo thật, và (b) thu thập QUOTE_ONLY (OrderSend=0) quanh NFP 04/12 & CPI 10/12 (20:30 ICT) khi chỉ còn duy nhất Demo 1515343166 trên naqex-node1 (ví dụ: chạy có kiểm soát vào cuối tuần/khi phẳng trên 1515343166, hay đợi chu kỳ Free Trial mới).

=== PHẦN B — KIỂM TOÁN TOÁN HỌC & MÃ NGUỒN BỘ TỐI ƯU VỐN 4 QUỸ & LỊCH SALE (YÊU CẦU TRỰC TIẾP TỪ CHỦ SỞ HỮU) ===
Hãy kiểm toán sâu toàn bộ logic toán học, giả định tài chính và mã nguồn của hệ thống kho giá + tối ưu hóa vốn 4 hãng:
- tooling/ai-engines/configs/prop_pricing_catalog.json (SHA 10b05130d06df8a3)
- tooling/ai-engines/quant_factory/prop_pricing_refresh.py (SHA 8b209510f10e8e8c)
- tooling/ai-engines/quant_factory/prop_capital_promo_optimizer.py (SHA 19c1eb0259ba24c9)
- private_vault/strategies/step5-capital-optimizer-20261126/optimizer_results.json (SHA 70401f6bfb74e820)
- planning/research/MULTI-FIRM-CAPITAL-PROMO-OPTIMIZER-20261126.md (SHA 1f023ff785e484d1)

Kiểm tra cụ thể 6 câu hỏi toán học (đã chủ động tự soi 5 điểm nghi vấn trong code để bạn phản biện thẳng):
B1. Làm tròn 0.01 lot thực tế (floor_lot_step / simulate_exact_lot_rounding_on_trade_list, dòng 878–1014): mức suy giảm -10.64% ở 5K (-31.65% Red Brake) và -4.36% ở 10K có đúng chuẩn M1 từng lệnh không, hay có sai lệch nào so với MT5?
B2. Lỗi phi đơn điệu / khóa khe tham lam ở P4A_DIRECT_50K (dòng 2212–2263): vì sao ở vốn 35tr+0tr/T NPV24 (+104.6tr) lại THẤP HƠN 25tr+0tr/T (+114.2tr)? Có đúng do 35tr lấp slot 1 bằng 50K thứ hai (khóa trần 50K+50K=100K), trong khi 25tr đợi payout đẩy tiền vượt ngưỡng mua 100K (50K+100K=150K) không? Nên sửa logic phân bổ thế nào?
B3. Thiên lệch so sánh từ Own-Book (dòng 2468–2485 & 3898–3921): own_book sinh lời đều 8%/năm không biến động trong khi chiết khấu 6%/năm (+2%/năm lợi nhuận phi rủi ro), và chỉ bật (4.0) cho P3/P4/P5 mà tắt (0.0) cho P1/P2. Mức sai lệch NPV từ đây là bao nhiêu và có cần tắt hoặc chuẩn hóa đồng đều cho mọi chính sách không?
B4. Bẫy E8 Pro trong P5/P5B (dòng 2331–2335 & 3868–3892): P5B đang đưa E8 Pro 50K vào danh mục với cơ chế rút sớm tại +1% làm khóa sàn DD về vốn gốc (cháy Funded 93.3%/12T). Đánh giá tác động của điểm này lên bảng P5/P5B và khuyến nghị loại E8 Pro hoặc thêm quy tắc tích đệm 8–10% trước lần rút đầu.
B5. Công thức Lịch Sale Động (evaluate_wait_vs_buy_npv & solve_max_wait_days_worth_it, dòng 1759–1962): việc dịch start_day_offset trong cửa sổ cố định 504 phiên làm cắt bớt số ngày cuối chân trời 24T (gây bước nhảy gắt giữa 7d và 14d qua chu kỳ payout 10 phiên) có làm đánh giá quá thấp số ngày đáng chờ sale (6–15 ngày) không? Nếu dùng chân trời trượt (shifting horizon + chiết khấu thuần) thì số ngày tối đa đáng chờ thay đổi ra sao?
B6. Hạch toán phí & đối chiếu 2x 100K vs 1x 200K: (a) khoản hoàn phí FTMO đang bị trừ withdrawal_fee_pct (dòng 1498 & 2433) có hợp lý không; (b) so sánh 2x 100K mở tuần tự vs 1x 200K có bị lệch khi 2x 100K chưa được phép mở song song 2 vé ở vốn 80tr; (c) tổng thể các kết luận chính (bỏ 25K, bỏ Instant/E8 Pro, điểm ngọt 35tr+ vào thẳng 100K sau khi mở cổng) còn đứng vững bao nhiêu phần trăm?

=== ĐỊNH DẠNG PHÁN QUYẾT YÊU CẦU ===
Trả lời trực diện, không vòng vo, chốt rõ 4 quyết định:
- Q1: Chính thức chọn C10_NEWS_ON làm ứng viên duy nhất cho giai đoạn kế tiếp (chưa đổi default v1.01)?
- Q2: Lộ trình được phép cho bài kiểm lịch sử máy chủ + thu thập QUOTE_ONLY 04/12 & 10/12 khi chỉ còn 1 Demo 1515343166?
- Q3: Danh sách lỗi toán học bắt buộc phải vá (blocking) vs khuyến nghị cải tiến (advisory) trên bộ tối ưu vốn 4 quỹ trước khi dùng làm bản đồ phân bổ vốn thật?
- Q4: Quyết định tài chính hiện tại (tiếp tục giữ 0 VND + điều kiện tối thiểu để bàn mở cổng).
```
