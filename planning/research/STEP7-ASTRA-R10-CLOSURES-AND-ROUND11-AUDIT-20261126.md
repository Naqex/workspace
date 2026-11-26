# Báo Cáo Bước 7 (Đóng Trọn Bộ Phán Quyết Astra Vòng 10) & Prompt Kiểm Toán Astra Vòng 11 (`27/11/2026`)

- **Ngày chốt:** `27/11/2026 00:16 ICT` · **Khóa bất biến:** `Holdout 2025+ SEALED` (`holdout_rows_analysed = 0`, SHA `f0a6b43cb205535b`) · `OrderSend = 0` · **`0 VND`** · `#property version "1.01"` & `3` cờ mặc định `0` (`.ex5` `4c4b2262a0750524`, `3` tệp MQL5 gốc bất biến `9d7fb3c966688df9` / `2f5b7d7ccd7b8a88` / `6b7ea2ee0d5bfa12`) · `naqex-node1` và tài khoản broker `1515343166` không bị can thiệp (`MT5_PROCS = 0`).
- **Kiểm chứng độc lập (`step7-verifier` + hệ thống):** `60/60` pytest trọng điểm Bước 7 (`4,74s`) + `system_doctor.py --mode full` **`10/10 PASS` (`69,12s`, `1.870 passed, 417 subtests passed`)**, `0` lỗi OPSEC, `0` ký tự `$` trần trong báo cáo Markdown.
- **Cấp độ bằng chứng:** Tầng 1 (`7.1`) là đối chứng trực tiếp trên tệp `.htm` & `.csv.gz` MT5 `Model=4` Real-Tick Q4/2024 (`20,02M` tick thật, `swap = 0,00`); Tầng 2 (`6.2` & `Optimizer v2`) là **`DAILY_APPROX` trên Dev `2018–2024` (`CLUSTER_B_VIEWED_NOT_BLIND`)** — chưa mở Holdout mù `2025+`, chưa chạy tiền thật.

---

## 1. Làn 1 — Truy Gốc Sai Lệch Lot/Tiền `L0` (Astra Q1) & Khóa Bảng Phí `10K` (Q3/Q4)

- **Hồ sơ bằng chứng:**
  - `private_vault/strategies/step7-astra-r10-closures-20261126/step7_1_l0_lot_divergence_audit.py` (`SHA a2bf6acd729798bb`)
  - `private_vault/strategies/step7-astra-r10-closures-20261126/step7_1_l0_lot_divergence_report.json` (`SHA 6d84239a79ada36d`)
  - `step3_blind_multiday_replay.py` giữ nguyên **KHÔNG SỬA** (`SHA a3b6538016614e1d`) làm chuẩn `L0` nghiêm ngặt.
  - `private_vault/strategies/step6-c10-news-on-and-demo-ro-20261126/step6_1_c10_news_on_mt5_and_10k_fees.py` (`SHA 74a2c2d43276b650`) · `step6_2_10k_real_vn_fees_report.json` (`SHA bad9c9164deaa0f6`).

### 1.1. Ba Phát Hiện Nhân Quả Trên `S6_STD_P1_C10_NEWS_ON` & `S6_STD_P2_C10_NEWS_ON`
1. **Sai lệch tiền đầu tiên (cả `P1` & `P2`, `deal_idx = 3`, `2024-09-02 23:45:00`, `E6_EURJPY_VOLCOMP`, `0,20` lot, cùng giá mở `162,475` / đóng `162,618` / hoa hồng `-0,50 USD`):**
   - Lãi `2.860,0 JPY`: Python đổi theo giá `USDJPY` sống lúc `23:45:00` (`146,883`) → **`19,47 USD`**; MT5 Strategy Tester đóng băng lười tỷ giá quy đổi `EURJPY` ở mức `146,542/146,550` từ lệnh SL `USDJPY` buổi sáng (`11:07:48`) → **`19,52 USD`** (`-0,05 USD`).
2. **Sai lệch lot đầu tiên (cả `P1` `deal_idx = 16` & `P2` `deal_idx = 18`, `2024-09-06 18:00:17`, `E2_USDJPY_EXP80`, `USDJPY SELL`):**
   - Bộ đệm `SYMBOL_TRADE_TICK_VALUE_LOSS` khi tài khoản phẳng của MT5 Tester bị đóng băng ở `0,69858746` (`USDJPY = 143,146` từ lúc đóng lệnh `15:25:00`, lệch `+1,220 JPY` so với giá sống `141,926` `tv = 0,70459253`), đẩy `raw_lots` vượt ngưỡng `0,1800` → MT5 vào **`0,18` lot** trong khi Python tính `0,1795` → **`0,17` lot**.
   - Kiểm chứng phản thực `2×2` chứng minh độ lệch số dư trước đó (`-0,05 USD` P1 / `-0,02 USD` P2) **KHÔNG gây lật lot** — nguyên nhân duy nhất là bộ đệm `tv_loss` đóng băng của MT5 Tester.
3. **Giải thích `92` deal lệch lot ở `P1` & tác động thực lên đường vốn / `Max DD`:**
   - Ở `P1`, Python bỏ qua đúng `1` lệnh `0,01` lot (`E7_USDJPY_NY10ET`, `2024-11-27 17:00:04`, `raw_lots = 0,00433 < 0,01` vs MT5 `0,01137 -> 0,01`, tạo `310` vs `312` deal). Vì bộ so sánh `step3` khớp theo chỉ số mảng vị trí, `1` lệnh thiếu đẩy lệch toàn bộ phần đuôi đi `2` chỉ số → sinh ra **`56` lỗi giả do lệch chỉ số** + chỉ **`36` deal lệch lot thực theo dấu thời gian** (`18` vào + `18` ra).
   - **Tác động thực lên vốn & `Max DD`:** Lệch số dư tối đa theo dấu thời gian chỉ là **`50,10 USD`** ở `P1` (thay vì ảo `309,01 USD`) và **`19,58 USD`** ở `P2`. **`BalDD` MT5 vs Python gần như trùng khớp:** `P1` **`4,90% (504,94 USD)` vs `4,87% (501,18 USD)`**; `P2` **`4,61% (475,48 USD)` vs `4,61% (476,79 USD)`**; **`0` ảnh hưởng tới bất kỳ ngưỡng vi phạm `5%` ngày / `10%` tổng nào** và `P2` đạt `+5%` tại **cùng đúng giây `2024-11-15 18:00:00`**.
   - **Khử từng nhân tố chỉ đọc (`DIAG_A..D`, không sửa `step3`):** Khi khử đủ 3 đặc thù MT5 Tester (`tv_loss` + `EURJPY conv` + `SL gap`, tầng `L4`), sai lệch lot giảm **`92/36 -> 0` (`P1`)** và **`22 -> 0` (`P2`)**, lệch số dư cuối còn **`-0,01 USD`**, `max_bal_err = 0,01 USD` (`311/312` P1 & `313/314` P2 deal khớp tuyệt đối).

### 1.2. Khóa Bộ Đếm Bước 6.2 (`112/8/0`) & Gói `2` Vé Hỗn Hợp (`BF #1 + Gốc #2`)
- Bộ đếm `step5_recount_audit` đọc trực tiếp giá trị số từ `full_lifecycle_results` (`0,66×..1,75×`, `tol = 1e-9`): **`112` thắng `C10` / `8` hòa (toàn bộ `8` trung vị tại `1,75×`) / `0` thắng `C00`** (cùng `120` ở lưới `1,00×..1,50×`).
- Bổ sung hạt nhân hỗn hợp `_sim_lifecycle_mixed_tickets_numba` (`VN_BF_T1_ORIG_T2_CARD_FX`: vé #1 `70,42 USD` hoàn `68,70 USD`, vé #2 `101,08 USD` hoàn `98,61 USD`): tại `1,50×` `C10_NEWS_ON` `2` vé đạt **`avg_fee = 113,39 USD`**, **`mean_net = +420,50 USD` (`+10,83 tr`)**, **`median_net = +297,84 USD`**, **`EV/Phí = +3,708×`**, **`P(net <= 0) = 32,57%`** — trùng khít 100% tính độc lập của Astra Vòng 10!

---

## 2. Làn 2 — Siết Chặt `QUOTE_ONLY` & Probe Đọc Lịch Sử Demo (Astra Q2)

- **Hồ sơ bằng chứng:**
  - [nfp_cpi_quote_collector.py](../../tooling/ai-engines/ops_cloud/nfp_cpi_quote_collector.py) (`SHA 2038fc7c56a4495c`)
  - [test_nfp_cpi_quote_collector.py](../../tooling/ai-engines/tests/test_nfp_cpi_quote_collector.py) (`SHA 5acecbe634564461`, **`33/33` test đạt**)
  - `private_vault/strategies/step7-astra-r10-closures-20261126/step7_2_demo_ro_hydration_probe.py` (`SHA 04678855a4c590a8`).
- **Tất cả lỗ hổng Astra Q2 đã đóng:**
  1. **Khớp chính xác mã tin:** Bỏ `startswith`, kiểm tuyệt đối `f"{ts},USD,{csv_code}"` -> `OTHER_EVENT` / `US_NFP_FAKE` tại cùng giây đều bị chặn (`ok = False`).
  2. **Tự dừng fail-closed:** Kiểm đúng `--expected-login` & `--expected-server`, `ti.connected == True`, trạng thái lệnh mở/chờ không `None` và phẳng `0/0`, chặn ngay khi `abs(ntp_offset_ms) >= 1.000 ms` hoặc `None` (kiểm sống trên PC Dev trả `RC = 2` ở mức lệch `-1.410,37 ms`), và trả `status = "INCOMPLETE_MISSING_DATA"` (`RC = 2`) nếu thiếu mã lõi hoặc thiếu `IMPACT_CORE` trong cửa sổ sự kiện.
  3. **Khắc phục rớt tick cùng mili-giây (`SameMsTickCursor`):** Truy vấn từ `last_msc` bao hàm và lọc đúng tiền tố `(time_msc, bid, ask, flags)` đã ghi — kiểm thử `3` cú nhảy giá trong cùng `1 ms` ghi đủ `3/3` tick (`inter_tick_gap_ms = 0`, `0` mất, `0` trùng).
  4. **Mặc định cửa sổ đúng sự kiện:** `1.200s` (`20:25–20:45 ICT`) cho `US_NFP_20261204` & `US_CPI_20261210`; `5,0s` chỉ cho `SMOKE_PREFLIGHT`.
  5. **Probe Demo `step7_2_demo_ro_hydration_probe.py`:** Không có `OrderSend`/`OrderCheck`/`CTrade`, không có `#property script_show_inputs`; đối chiếu đủ **`(ticket, magic, symbol, deal_time, entry, type)`** và **ngày phiên riêng của từng động cơ (`UTC`: E1/S6; `Broker D1`: E2/E3/E6; `NY` kèm DST: E4/E5/E7)** khớp nguyên văn `Naqex_Signals_7E.mqh:325-336,504-515,758-840`. *(Ghi chú trung thực: khi triển khai chạy thật trên Demo mới, cần lọc cửa sổ 48h đồng bộ theo giờ server để tránh lệch biên 2–3h UTC/server.)*

---

## 3. Làn 3 — Bộ Tối Ưu Vốn 4 Quỹ `v2` (`C10_NEWS_ON`, Đóng Trọn 10 Mục B1–B6 + 3 Lỗi Xuyên Suốt)

- **Hồ sơ bằng chứng:**
  - [prop_capital_promo_optimizer.py](../../tooling/ai-engines/quant_factory/prop_capital_promo_optimizer.py) (`SHA 1e90465c252f85a9`)
  - [test_prop_capital_promo_optimizer.py](../../tooling/ai-engines/tests/test_prop_capital_promo_optimizer.py) (`SHA 99f7aaca706ec5a5`)
  - `private_vault/strategies/step7-astra-r10-closures-20261126/optimizer_v2_results.json` & `step5-capital-optimizer-20261126/optimizer_results.json` (`SHA d2afebd2f35d42db`)
  - [MULTI-FIRM-CAPITAL-PROMO-OPTIMIZER-20261126.md](MULTI-FIRM-CAPITAL-PROMO-OPTIMIZER-20261126.md) (`SHA 5ae4914017ca6a4f`, `0` bare `$`, `420/420` `Pass+Fail+Pending == 100%`).
  - [prop_pricing_catalog.json](../../tooling/ai-engines/configs/prop_pricing_catalog.json) bất biến (`SHA 10b05130d06df8a3`).

### Tóm Tắt 10 Bản Vá Đã Kiểm Chứng Độc Lập Trên `Optimizer v2`
| Mục Astra Q3 | Trạng thái trong `Optimizer v2` (`d2afebd2f35d42db`) |
|---|---|
| **1. Ứng viên chính** | Chuyển 100% sang **`C10_NEWS_ON`** (`C00` đối chứng; `C10` tắt tin chỉ giữ đối chứng). FTMO Std `100K` `1,00×` BF Ngày 0: `NPV24` TB `+161,9 tr` · trung vị `+85,9 tr` · `P<=0 = 40,2%` · `EV/Phí +12,81×`. |
| **2. Nạp giá fail-closed** | `load_pricing_catalog(allow_fallback=False)` báo lỗi ngay khi thiếu/hỏng catalog + kiểm hạn `verified_utc` từng gói (`42` gói `FRESH`, tối đa `0,22d / 7d`; quá hạn bắn `STALE_CATALOG_ERROR`). |
| **3. Giá theo ngày mua** | Tách `fee_day0_usd` (BF ngày 0) vs `fee_regular_usd` (giá gốc cho mọi vé retry & mua về sau); công bố cả bảng `BF Ngày 0 + Retry Gốc` lẫn `100% Giá Gốc`. |
| **4. Mốc DD ngày từng hãng** | Đọc `daily_dd_anchor` từ catalog: `initial_balance` (FTMO, E8 -> `s_bal - cap * daily_lim`) vs `prev_day_balance` (The5ers, IC Funded -> `s_bal * (1 - daily_lim)`). |
| **5. B3 — Tắt `own_book`** | `own_book_overflow_mult = 0.0` toàn cục (`OWN_BOOK_NONZERO = 0` trên mọi bảng xếp hạng chiến lược quỹ). |
| **6. B4 — Loại `E8 Pro`** | Loại hoàn toàn `E8 Pro` khỏi danh mục rủi ro thấp `P5/P5B` (chỉ giữ `3` hãng `FTMO + The5ers + IC Funded`, gắn rõ `TERMS_VERIFIED_EXECUTION_UNMEASURED` cho The5ers/IC); giữ `E8 Pro` ở Mục 4 như bảng cảnh báo bẫy + kiểm đệm `+8%/+10%` vẫn cháy `12,9–34,2%`. |
| **7. B2 — Thêm `P4A_WAIT` & Trung vị** | Thêm `P4A_WAIT_FOR_100K` đơn điệu tuyệt đối `15->80tr` (`+111,5 -> +120,5 -> +125,3 -> +129,8 -> +137,7 tr`); công bố đủ `TB / Trung vị / P(NPV24 <= 0)` ở `300/300` ô (phơi bày rõ `35tr @ 1,50× P4B`: TB `+79,2 tr`, **trung vị `-12,6 tr`**, **`P<=0 = 61,9%`**). |
| **8. B5 — Lịch sale 2 chân trời** | Quét lưới chính xác `Y = 0..180` (bỏ tìm kiếm nhị phân & bỏ mẹo `2 × d7`), công bố đồng thời **Hạn chót cố định** (`10K 1,00×`: `10 / 12 / 15d`) và **Đủ 24T từ ngày mua** (công thức `50,3 / 100,2 / 149,7d`, MC `80 / 122 / 152d`) kèm công khai giả định *sale chắc chắn xảy ra*. |
| **9. B6 — Tách phí & `2×100K` song song** | Tách phí thẻ mua (`+2,5%` không hoàn), phí hoàn về thẻ FTMO (`0,0%` vs độ nhạy `1,5%` lệch `+4,11 USD` trên `100K`), phí rút (`1,5–4,0%`); thêm **`P4B_PARALLEL_2X100K`** (`50tr`: cháy `0,63%` / `NPV +314,8 tr` vs `1×200K` cháy `13,85%` / `+308,7 tr`; `80tr`: song song `+320,2 tr` sát `1×200K +322,3 tr`) kèm công khai `simultaneous_fail_pct` (`7,5% / 13,3%`). |
| **10. B1 — Công khai sai khác sizing** | Ghi rõ trong Mục 3 & Mục 8: `get_exact_tier_stage` dùng vốn đầu kỳ & từ chối lệnh thiếu margin, khác với EA (`balance × risk × 0,95` + co lot theo `85%` free margin) -> các tỷ lệ `5K/10K` là `DAILY_APPROX` chờ đối chiếu MT5 `Model=4`. |

---

## 4. Prompt Kiểm Toán Sẵn Sàng Gửi GPT-6.2 Astra — Vòng 11 (Nghiệm Thu Đóng Toàn Bộ Vòng 10)

```text
Bạn là GPT-6.2 Astra — kiểm toán viên kỹ thuật và kinh tế độc lập (fail-closed) của Naqex Workspace.
Hãy kiểm toán Vòng 11 (hoàn toàn offline, KHÔNG chạy MT5, KHÔNG chạm naqex-node1, KHÔNG mở Holdout 2025+, giữ 0 VND) để nghiệm thu toàn bộ các bản vá cho phán quyết Vòng 10 của bạn:

=== KHÓA BẤT BIẾN ===
- Holdout 2025+ SEALED (holdout_rows_analysed = 0, SHA f0a6b43cb205535b).
- OrderSend = 0, 0 VND, #property version "1.01", 3 cờ opt-in mặc định 0 (MQL5 headers/EA bất biến: 9d7fb3c966688df9 / 2f5b7d7ccd7b8a88 / 6b7ea2ee0d5bfa12; .ex5 4c4b2262a0750524).
- step3_blind_multiday_replay.py KHÔNG bị sửa (SHA a3b6538016614e1d); prop_pricing_catalog.json KHÔNG bị sửa (SHA 10b05130d06df8a3).
- Kết quả kiểm thử hiện tại: 60/60 pytest Bước 7 (4.74s) + system_doctor --mode full 10/10 PASS (1,870 passed, 417 subtests passed), MT5_PROCS = 0.

=== 1. KIỂM TOÁN Q1 — TRUY GỐC LỆCH LOT/TIỀN L0 & BẢNG PHÍ 10K ===
- Tệp cần kiểm:
  * private_vault/strategies/step7-astra-r10-closures-20261126/step7_1_l0_lot_divergence_audit.py (SHA a2bf6acd729798bb)
  * private_vault/strategies/step7-astra-r10-closures-20261126/step7_1_l0_lot_divergence_report.json (SHA 6d84239a79ada36d)
  * private_vault/strategies/step6-c10-news-on-and-demo-ro-20261126/step6_1_c10_news_on_mt5_and_10k_fees.py (SHA 74a2c2d43276b650)
  * private_vault/strategies/step6-c10-news-on-and-demo-ro-20261126/step6_2_10k_real_vn_fees_report.json (SHA bad9c9164deaa0f6)
- Xác minh:
  (a) Lệnh lệch tiền đầu tiên 2024-09-02 23:45:00 E6 EURJPY (-$0.05) do MT5 Tester đóng băng tỷ giá EURJPY tại 146.542/146.550 vs live 146.883.
  (b) Lệnh lệch lot đầu tiên 2024-09-06 18:00:17 E2 USDJPY SELL (MT5 0.18 vs Python 0.17) do bộ đệm tv_loss khi phẳng của MT5 Tester (143.146 vs live 141.926), phản thực 2x2 chứng minh không do lệch số dư.
  (c) P1 92 deal lệch lot vị trí = 36 lệch thực theo thời gian + 56 lỗi dịch chỉ số do 1 lệnh E7 0.01 lot bị Python bỏ qua ngày 2024-11-27 17:00:04 (310 vs 312 deal); max_abs_bal_diff thực: P1 $50.10 / P2 $19.58; BalDD MT5 vs Py: P1 4.90% vs 4.87%, P2 4.61% vs 4.61%; 0 tác động lên ngưỡng 5%/10%; khử 3 đặc thù Tester (L4) đưa lệch lot về 0 ở cả P1 & P2 (end_diff -$0.01).
  (d) Step 6.2 đã sửa bộ đếm về đúng 112 thắng / 8 hòa / 0 thua và gói 2 vé hỗn hợp BF#1 ($70.42) + Gốc#2 ($101.08) tại 1.50x C10_NEWS_ON tái lập đúng avg_fee $113.39, mean +$420.50, P(net<=0) 32.57%.

=== 2. KIỂM TOÁN Q2 — QUOTE_ONLY & PROBE DEMO RESTART ===
- Tệp cần kiểm:
  * tooling/ai-engines/ops_cloud/nfp_cpi_quote_collector.py (SHA 2038fc7c56a4495c)
  * tooling/ai-engines/tests/test_nfp_cpi_quote_collector.py (SHA 5acecbe634564461)
  * private_vault/strategies/step7-astra-r10-closures-20261126/step7_2_demo_ro_hydration_probe.py (SHA 04678855a4c590a8)
- Xác minh: chặn OTHER_EVENT/US_NFP_FAKE, tự dừng khi abs(NTP)>=1000ms (hiện PC Dev lệch -1410ms trả RC=2) / sai login-server / non-flat / thiếu IMPACT_CORE, bảo toàn nhiều tick trong cùng 1ms (SameMsTickCursor), mặc định 1200s cho NFP/CPI, và probe Demo đối chiếu ticket+magic+ngày phiên (UTC/Broker D1/NY khớp Naqex_Signals_7E.mqh) với 0 OrderSend/CTrade. Lưu ý thành thật: khi chạy live trên Demo thật, cần đồng bộ lọc biên 48h giữa giờ UTC và giờ server.

=== 3. KIỂM TOÁN Q3 — BỘ TỐI ƯU 4 QUỸ V2 (ĐÓNG B1–B6 + 3 LỖI XUYÊN SUỐT) ===
- Tệp cần kiểm:
  * tooling/ai-engines/quant_factory/prop_capital_promo_optimizer.py (SHA 1e90465c252f85a9)
  * tooling/ai-engines/tests/test_prop_capital_promo_optimizer.py (SHA 99f7aaca706ec5a5)
  * private_vault/strategies/step7-astra-r10-closures-20261126/optimizer_v2_results.json (SHA d2afebd2f35d42db)
  * planning/research/MULTI-FIRM-CAPITAL-PROMO-OPTIMIZER-20261126.md (SHA 5ae4914017ca6a4f)
- Kiểm tra toàn bộ 10 điểm: (1) ứng viên C10_NEWS_ON toàn cục; (2) fail-closed catalog & per-tier staleness; (3) giá BF ngày 0 vs giá gốc retry; (4) daily_dd_anchor theo từng hãng; (5) own_book=0.0 toàn cục; (6) loại E8 Pro khỏi P5/P5B (3 hãng FTMO/The5ers/IC); (7) P4A_WAIT_FOR_100K đơn điệu + công bố trung vị & P(NPV<=0) ở 300/300 ô (35tr @ 1.50x P4B trung vị -12.64tr, P<=0 61.92%); (8) lịch sale 2 chân trời quét chính xác Y=0..180 (không nhị phân, không 2*d7); (9) tách phí mua/hoàn/rút + P4B_PARALLEL_2X100K vs tuần tự vs 1x200K; (10) công khai giới hạn B1 sizing DAILY_APPROX.

=== PHÁN QUYẾT VÒNG 11 YÊU CẦU ===
Chốt ngắn gọn, rõ ràng 4 quyết định:
- Q1: Giải thích sai lệch lot L0 (P1 92->36->0, P2 22->0, BalDD 4.90%/4.87% & 4.61%/4.61%) đã đủ đóng blocker đối chiếu sizing/DD chưa?
- Q2: nfp_cpi_quote_collector.py & step7_2_demo_ro_hydration_probe.py đã đạt chuẩn sẵn sàng cho lượt thử chỉ đọc trên Demo được duyệt & NFP 04/12 + CPI 10/12 (sau khi đồng bộ NTP < 1s) chưa?
- Q3: Bộ tối ưu vốn v2 đã đóng đủ các lỗi toán học Vòng 10 để làm bản đồ tham khảo phân bổ vốn (giữ nhãn DAILY_APPROX & UNMEASURED cho hãng phụ) chưa, hay còn blocker nào?
- Q4: Quyết định tài chính (tiếp tục giữ 0 VND) & đúng 1–2 điều kiện thực địa tối thiểu còn lại trước khi bàn một vé Standard 10K.
```
