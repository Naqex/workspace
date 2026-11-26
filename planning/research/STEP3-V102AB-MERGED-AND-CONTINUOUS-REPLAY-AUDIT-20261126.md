# Báo Cáo Kiểm Toán Bước 3: Vá 2 Lỗi Nền, Hợp Nhất `v1.02 (A + B)` & Phát Lại Mù Liên Tục 4 Tháng (`01/09–31/12/2024`)

- **Ngày chốt:** `26/11/2026` · **Trạng thái kỹ thuật:** `STEP3_COMPLETE_AWAITING_ASTRA_ROUND7`
- **Cổng kinh tế:** **VẪN DỪNG (`HALTED_AT_PARITY_GATE`) · Quyết định tài chính: `0 VND`**
- **An toàn bắt buộc:** `Holdout 2025+ SEALED` (`holdout_rows_analysed = 0`, toàn bộ lượt kiểm toán kết thúc `<= 2024-12-31`) · **`0` lệnh gửi tới broker** (toàn bộ `OrderSend` đều là mô phỏng trong MT5 Strategy Tester cục bộ) · **`naqex-node1` (`1515343166`) chỉ đọc, không chạm** (`ONLINE GREEN`, `open_positions = 0`, `order_send_count = 0`, `NTP -0,054s`, Heroku EU `OK`) · **`InpSizingMode = 0` xuyên suốt Bước 3** · **`#property version "1.01"` giữ nguyên với hai cờ `InpProfitLockBasisMode = 0` và `InpOpportunityLifecycleMode = 0` tắt mặc định** cho tới khi Astra Vòng 7 duyệt thăng hạng `v1.02`.

---

## 0. Tóm Tắt Nhanh Cho Chủ Sở Hữu & Kiểm Toán Viên

Toàn bộ lộ trình Bước 3 theo phán quyết **GPT-6.2 Astra Vòng 6** đã chạy trọn (`3.1 → 3.2 → 3.3`):

1. **Bước 3.1 — Vá dứt điểm `2` lỗi nền, hoàn thiện bộ đếm `v1.02-B` & bổ sung các phép thử âm/biên:**
   - **Vá lỗi nhìn trước mốc `09:30` New York trong Python:** Hàm dựng cửa sổ M1 và đọc nến M1 lùi (`shift >= 1`) đã cấm tuyệt đối việc đọc bất kỳ nến M1 CSV nào có `bar_time >= cur_min`; phút đang hình thành (`bar_time == cur_min`) chỉ được dựng nhân quả từ báo giá `bid` thực quan sát `<= now_srv_ts`. Trên `2024-10-23`, Python chốt đúng `US100 = 20.280,45` và `US500 = 5.830,05` (bỏ hẳn giá đóng cửa tương lai `20.292,35`) — **khớp `0,00000`** với mốc `NY_ANCHOR_LOCKED` thật do EA ghi trong MT5 Tester, và **đạt `100%` phép thử bất biến tương lai** (đẩy toàn bộ nến/báo giá sau `09:30:00` thêm `+1,0` và `+100,0` điểm không làm xê dịch `0,00000` mốc `09:30:00` hay bất kỳ sự kiện nào `<= 09:30:00`).
   - **Vá lỗi fail-open ở bộ so sánh & runner Bước 2:** Thay cặp vòng lặp tách rời (`min(...)`, `return 0`) bằng **một luồng sự kiện hợp nhất duy nhất** sắp theo `(server_ts, same_sec_order)` duyệt trọn `range(max(len(py), len(gt)))` và trả mã thoát khác `0` (`exit 2`) khi có bất kỳ sai lệch nào. Kết quả trên ngày `23/10`: **`24.646/24.646` khớp**, `0` sai lệch, **chặn đúng cả `3/3` đột biến âm** (*xóa sự kiện cuối*, *đổi chỗ 2 sự kiện cùng giây `18:00:00`*, *đổi `engine_id`*). Đồng thời siết `step2_v102ab_isolated_runner.py` buộc cả `3/3` lượt `v1.02-B` khớp từng deal với `v1.01` trong `overall_pass` (`--reverify-existing` xác minh `48/48` tệp Bước 2 trong `5,21s`, bảo toàn nguyên vẹn mã băm `.ex5` gốc `e82056a748b193b6` đã sinh gói Bước 2).
   - **Giữ minh bạch lệch vi mô `E1` & kiểm độ nhạy biên `vol_step`:** Giữ rõ sai lệch `raw_lots` `+0,00074855` lot tại `E1 23/10 06:04:46` (`0,13907905` vs `0,13833050`, lot làm tròn vẫn `0,13 == 0,13`) do bộ đệm `tick_value_loss` trước vị thế đầu tiên của MT5 Tester (`0,66234816` vs thực tế `0,65878323`, lệch `0,5382%`). Quét `201` mức số dư (`9.500..11.500 USD`) chứng minh độ lệch `0,54%` này làm nhảy `0,01` lot tại biên `vol_step` ở **`12/201` điểm (`5,97%`)** — và Bước 3.3 ghi nhận chính hiện tượng này xảy ra thật ngoài dữ liệu ngày `06/09 18:00:17`.
   - **Hoàn thiện hạch toán `v1.02-B` theo từng nguyên nhân trong MQL5:** Mở rộng `Naqex_Signals_7E.mqh` (`057f5b7243f72487`) và `Naqex_Master_Prop7E.mq5` (`388464380ae4c1b6`) để **mọi nhánh từ chối** (`NEWS`, `SPREAD`, `BAD_SL`, `STOPS`, `CAP`, `BAD_SPEC`, `LOT_MIN`, `MARGIN_CALC`, `MARGIN_LOT_MIN`, `BROKER`, `OPEN_OR_INFLIGHT`) đều cộng vào `block_count` và bộ đếm riêng `blk_by=lmin:...,cap:...,spread:...,news:...,other:...`, đồng thời ghi `1` dòng chẩn đoán chỉ đọc `NY_ANCHOR_LOCKED` khi `MQL_TESTER && InpTesterEmitDecisionLog`. Biên dịch MetaEditor64: **`0 errors, 0 warnings`** (`.ex5` SHA-256 `af2ad46b1f430ba8`), `mql5_parity_checker --require-ex5` **PASS (`8/8` EA, `0` drift)**, `verify_deployment_kit --require-ex5` **PASS (`130` SHA, `10` EX5)**.

2. **Bước 3.2 — Kiểm định hợp nhất `v1.02 (A + B)` (`pl_mode = 1, opp_mode = 1, InpSizingMode = 0`):**
   - Chạy `6` lượt `Model=4` Real-Tick (`36` tệp gốc trong `private_vault/strategies/step3-v102ab-merged-and-replay-20261126/raw_mt5_logs/`), **`overall_step3_2_pass = True`**.
   - **Toàn bộ `5/5` lượt hợp nhất `A + B` khớp nguyên văn `100,00%` từng deal, lot, hoa hồng, swap (`0,00`) và mức sụt giảm vốn với bản `v1.02-A` thuần** (`0` dòng deal khác biệt, `Δnet = +0,00 USD`):
     - `V102AB_ADV_B2` vs `V102A_ADV_B2`: `+216,84 USD`, `5` vào / `5` ra, `eqDD 1,06%`.
     - `V102AB_ADV_PL_LT_AMBER` (`InpInitialBalanceUSD = 9.920 USD`, `9.935,45 = +0,156%` so với `9.920 USD`): `-115,28 USD`, `AMBER_BRAKE+PROFIT_LOCK = 1,75× < 2,60×` + `KILL` theo `equity`, khớp `100%` Bước 2 `A`.
     - `V102AB_ADV_RED_LT_PL` (`InpInitialBalanceUSD = 9.920 USD`): `-115,80 USD`, `RED_BRAKE+PROFIT_LOCK = 1,60× < 2,50×` + `KILL` theo `equity`, khớp `100%` Bước 2 `A`.
     - `V102AB_C10_P2_20240912`: `+462,38 USD`, `156` vào / `156` ra, `eqDD 7,61%`, khớp `100%` Bước 2 `A`.
     - `V102AB_C00_P1_20240912` (`RedNews=ON`): `+708,89 USD`, `155` vào / `155` ra, `eqDD 6,25%`, khớp `100%` Bước 2 `A`.
   - **Hạch toán cơ hội `eval == accepted + sum(blk_by)` đạt `100%` trên mọi cơ hội ở cả `5/5` lượt `A + B` (`0` cơ hội treo, `0` kết thúc mồ côi):**
     - Giải quyết trọn vẹn câu hỏi `E7` của Astra Vòng 6: trên `V102AB_C10_P2`, cơ hội `OPP_E7_1732665600_1` ghi rõ **`eval=601 | blk=601 | blk_by=lmin:596;spread:5`** (`596 + 5 = 601`, `100%` khớp).
     - Trên `V102AB_C00_P1`, toàn bộ `196` cơ hội (`155` nhận + `41` hết hiệu lực) khớp `100%` với tổng các sự kiện chặn thô (`lmin: 2.120`, `spread: 12`, `news: 22`).
   - **Phát hiện phụ trung thực trên `ADV_B2 18:00:00`:** Tại cùng giây `18:00:00` khi `E1` vừa đóng lãi `+103,31 USD` rồi `E6` vào lệnh ngay sau đó, `RunMasterCycle()` tính `g_curProfitPct` ở đầu chu kỳ (trước `ClosePositionsByReason`, bằng `0,2085%` theo số dư `10.020,85 USD`) trong khi cột `balance` lúc đặt `E6` đã là số dư sau đóng `10.124,16 USD` (`1,2416%`). Với `ADV_B2` (`ProfitLock = 7,00%`) điều này không đổi `risk_mult` hay lot, nhưng cần đặt thành câu hỏi thiết kế cho Astra Vòng 7 xem có nên làm mới `realizedProfitPct`/`riskMult` ngay sau `ClosePositionsByReason()` khi số dư vừa đổi trong cùng giây hay không.

3. **Bước 3.3 — Kiểm định `3` cửa sổ biên trước → Phát lại mù liên tục cả `4` tháng (`5.347.386` chu kỳ/kịch bản, `v1.02 A+B`, `InpSizingMode = 0`):**
   - Xuất dữ liệu thị trường thuần bằng `Naqex_MarketFeedDumpRange.mq5` (`0` logic chiến lược, `0 OrderSend`, `0` cột tài khoản, đầy đủ lịch đóng phiên `MON..FRI` từ `SymbolInfoSessionTrade`, `m1_mask` nhân quả 8-bit, cực trị nội giây quy đúng về `prev_srv_ts` cho độ trễ SL `0s`) thành `7` gói (`3` cửa sổ biên + `4` mảnh tháng `33–41 MB/mảnh`, tổng `28` tệp trong `market_feeds/`).
   - **Cả `3` cửa sổ biên (chạy TRƯỚC lượt 4 tháng) đều rõ ràng, không che giấu:**
     - **Nghỉ lễ/đóng sớm Mỹ (`27–30/11`, Lễ Tạ Ơn + Black Friday):** khớp tuyệt đối **`16/16` deal**, **`638/638` sự kiện luồng** (gồm đúng `E7`: `596 lmin + 5 spread`), **`3/3` mốc `09:30` NY**, số dư cuối **`10.404,81 == 10.404,81 USD` (`+0,00 USD`)**.
     - **Chuyển giờ DST EU (`27/10`) & Mỹ (`03/11`) (`25/10–05/11`, `8` ngày giao dịch, `6` chạm SL):** khớp tuyệt đối **`30/30` deal** (`0s` cả `6/6` SL), **`60/60` sự kiện luồng**, **`8/8` mốc `09:30` NY**, số dư cuối **`9.685,36 == 9.685,36 USD` (`+0,00 USD`)**.
     - **Tuần chạm SL + trượt giá NFP (`02–06/09`, gồm Labor Day `02/09`, `3` chạm SL):** khớp **`22/22` mốc giây/mã/chiều (`0s` cả `3/3` SL)**, **`5/5` mốc `09:30` NY**, ghi nhận minh bạch `3` sai lệch vật lý đầu tiên: `+0,05 USD` quy đổi chéo `EURJPY` ngày `02/09 23:45:00`, trượt giá qua SL dưới `1` giây `9` điểm lúc NFP `06/09 15:30:00` (`sl 143,423 → khớp 143,432`, `-1,44 USD`), và cú nhảy `0,01` lot tại biên `vol_step` ngày `06/09 18:00:17` (`E2` `raw_lots_gt = 0,180445` từ `tick_value_loss` đệm `0,697496` → `0,18` vs Python `0,17`, kéo theo `E4` `0,59` vs `0,56`, tổng lệch tuần `+4,05 USD`).
   - **Phát lại mù liên tục trọn `4` tháng (`01/09–31/12/2024`, từ `10.000,00 USD`, KHÔNG đặt lại số dư giữa kỳ):**

| Kịch bản (`v1.02 A+B`) | Chu kỳ `1s` | Mốc `09:30` NY | Deal PY / GT | Khớp giây `0s` / mã / chiều | Số lần SL (`0s` lag) | SL không trượt (`Δ USD`) | SL trượt qua mức dưới `1s` (`Δ USD`) | Số dư cuối PY / GT (`Δ USD`) | Đếm sự kiện luồng (`OPP/FILL/CLOSE/REJ`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **`C10_P2_V102AB`** (`RedNews=OFF`) | `5.347.386` | **`85 / 85`** | **`312 / 312`** | **`311 / 312`** (`99,68%`) | **`40 / 40`** | `18` (`0,00 USD`) | `22` (`+31,46 USD`) | `10.500,66` / `10.462,38` (`+38,28`) | `OPP_START 157==157`, `FILL 156==156`, `CLOSE 116==116`, `SPREAD 9==9`, `LMIN 596==596`, `EXP 1==1` (`TAPER 50 vs 52`) |
| **`C00_P1_V102AB`** (`RedNews=ON`) | `5.347.386` | **`85 / 85`** | **`310 / 310`** | **`309 / 310`** (`99,68%`) | **`35 / 35`** | `16` (`0,00 USD`) | `19` (`+16,85 USD`) | `10.727,08` / `10.708,89` (`+18,19`) | `OPP_START 196==196`, `FILL 155==155`, `CLOSE 120==120`, `EXP 41==41`, `LMIN 2.120==2.120`, `SPREAD 12==12`, **`NEWS 22==22`** (`TAPER 55 vs 56`) |

- **Giải phẫu minh bạch sai lệch còn lại sau 4 tháng cộng dồn (KHÔNG có lỗi logic tín hiệu hay trạng thái):**
  - Toàn bộ **`34 / 34`** lần chạm SL không trượt giá (`18` ở `C10 P2` + `16` ở `C00 P1`) đều khớp **`0,00 USD`** và **`0s`**!
  - Toàn bộ phần chênh số dư cuối kỳ chủ yếu đến từ **`41` lần giá nhảy gáp qua mức SL ở thang dưới `1` giây** trong `Model=4` Real Ticks (mà bộ mẫu `1s` không có sổ lệnh từng mili-giây nên giả định khớp đúng giá SL): riêng phần trượt giá SL chiếm **`+31,46 / +38,28 USD` (`82,2%`)** ở `C10 P2` (trong đó tại deal `259`, số dư Python vượt ngưỡng bước nhảy `ProfitLock +3,50% = 10.350 USD` sớm hơn MT5 nên vào `1,75×` thay vì `3,50×`, đóng góp `+29,19 USD` chỉ riêng `1` lệnh đó) và **`+16,85 / +18,19 USD` (`92,6%`)** ở `C00 P1` (phần cộng dồn còn lại qua `310` deal chỉ là **`+1,34 USD`**!).
  - **Nhánh chưa kiểm giữ nguyên nhãn trung thực:** Nhánh `R1/R2` (`HydrateTradedDaysFromHistory`, khôi phục `GlobalVariable`, mất kết nối/trễ mạng thật) và việc giữ `opportunity_id` qua restart ngoài Tester **vẫn là `chưa kiểm` (`UNTESTED_ON_LIVE_RESTART`)**.

---

## 1. Bảng Chi Tiết Các Tệp Bằng Chứng & Mã Băm

| Hạng mục | Đường dẫn | Quy mô / Ghi chú xác minh |
|---|---|---|
| **EA Master v1.01 (+ counters & NY anchor)** | [Naqex_Master_Prop7E.mq5](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5) | SHA-256 `388464380ae4c1b6...` · `InpProfitLockBasisMode = 0`, `InpOpportunityLifecycleMode = 0` |
| **Tín hiệu 7E (+ `blk_by` & getter 09:30)** | [Naqex_Signals_7E.mqh](../../tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh) | SHA-256 `057f5b7243f72487...` · `0` `OrderSend`, giữ nguyên `prevRng >= 1.10 * atrD1` |
| **Tệp biên dịch `.ex5`** | `.runtime/mt5-compiled-ex5/Naqex_Master_Prop7E.ex5` | SHA-256 `af2ad46b1f430ba8...` · `0 errors, 0 warnings` · `manifest.sha256.json` đồng bộ (`130` SHA, `10` EX5) |
| **Kiểm thử hợp đồng MQL5** | [test_mql5_v101_contract.py](../../tooling/ai-engines/tests/test_mql5_v101_contract.py) | Đã thêm kiểm `blk_by=`, `NY_ANCHOR_LOCKED`, `eval == accepted + sum(blk_by)` |
| **Bước 3.1 Replay nhân quả 23/10 + 3 kiểm định** | `private_vault/strategies/step2-v102ab-and-replay-20261126/step2_python_self_reconstruct_20241023.py` · [JSON](../../private_vault/strategies/step2-v102ab-and-replay-20261126/step2_1_python_self_reconstruction_20241023.json) | `OVERALL_PASS = True`, `24.646/24.646` luồng hợp nhất, `future_invariance = True`, `3/3` đột biến âm bị chặn, `vol_step` `5,97%` |
| **Bước 3.1 Siết runner Bước 2 (`3/3 B == v1.01`)** | `private_vault/strategies/step2-v102ab-and-replay-20261126/step2_v102ab_isolated_runner.py` · [JSON](../../private_vault/strategies/step2-v102ab-and-replay-20261126/step2_v102ab_isolated_report.json) | `v102b_all3_runs_deal_identical_to_v101 = True`, bảo toàn SHA `.ex5` Bước 2 `e82056a748b193b6` |
| **Bước 3.2 Hợp nhất `v1.02 (A + B)` (`6` lượt)** | `private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_v102ab_merged_runner.py` · [JSON](../../private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_2_v102ab_merged_report.json) · [Index `36` tệp gốc](../../private_vault/strategies/step3-v102ab-merged-and-replay-20261126/raw_mt5_logs/raw_logs_index.json) | `overall_step3_2_pass = True`, `5/5` `A+B == A` nguyên văn, `100%` `eval == acc + blk` (`E7 601 = 596 + 5`) |
| **Bước 3.3 Bộ xuất thuần & Phát lại mù `4` tháng** | `private_vault/strategies/step3-v102ab-merged-and-replay-20261126/Naqex_MarketFeedDumpRange.mq5` · `step3_export_market_feeds.py` · `step3_blind_multiday_replay.py` · [Feed Index `28` tệp](../../private_vault/strategies/step3-v102ab-merged-and-replay-20261126/market_feeds/feed_index.json) · [JSON 3 cửa sổ biên](../../private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_3_edge_cases_report.json) · [JSON 4 tháng liên tục](../../private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_3_blind_multiday_replay_report.json) | `85/85` NY anchor, `312/312` `C10 P2` (`40/40` SL `0s`, `+38,28`), `310/310` `C00 P1` (`35/35` SL `0s`, `22/22` NEWS, `+18,19`) |

---

## 2. Prompt Sẵn Dán Cho GPT-6.2 Astra — Kiểm Toán Độc Lập Vòng 7

```text
Bạn là kiểm toán viên độc lập (GPT-6.2 Astra — Vòng 7). Hãy đọc trực tiếp mã nguồn, tệp JSON và các gói log gốc đã lưu trong kho (KHÔNG tin tóm tắt trước khi tự đối chiếu mã băm và tính lại). Toàn bộ Bước 3 đã chạy offline hoàn toàn: 0 lệnh gửi tới broker (OrderSend trong log chỉ là mô phỏng của MT5 Strategy Tester), Holdout 2025+ giữ niêm phong (holdout_rows_analysed = 0), naqex-node1 chỉ đọc chưa chạm, InpSizingMode = 0, cổng kinh tế vẫn dừng (0 VND).

Các nguồn gốc cần kiểm trực tiếp:
1. Mã nguồn MQL5 (vẫn giữ #property version "1.01", hai cờ v1.02 mặc định = 0):
   - D:/ANNAM/TradingWorkspace/tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5 (SHA256: 388464380ae4c1b6...)
   - D:/ANNAM/TradingWorkspace/tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh (SHA256: 057f5b7243f72487...)
   - D:/ANNAM/TradingWorkspace/tooling/ai-engines/tests/test_mql5_v101_contract.py
2. Bước 3.1 (vá lookahead 09:30 NY, vá comparator fail-open, siết runner Bước 2, kiểm vol_step):
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step2-v102ab-and-replay-20261126/step2_python_self_reconstruct_20241023.py
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step2-v102ab-and-replay-20261126/step2_1_python_self_reconstruction_20241023.json
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step2-v102ab-and-replay-20261126/step2_v102ab_isolated_runner.py
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step2-v102ab-and-replay-20261126/step2_v102ab_isolated_report.json
3. Bước 3.2 (hợp nhất v1.02 A + B trên 6 lượt Model=4 Real-Tick, InpSizingMode = 0):
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_v102ab_merged_runner.py
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_2_v102ab_merged_report.json
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step3-v102ab-merged-and-replay-20261126/raw_mt5_logs/raw_logs_index.json (36 tệp gốc)
4. Bước 3.3 (xuất dữ liệu thị trường thuần + 3 cửa sổ biên + phát lại mù liên tục 4 tháng 01/09–31/12/2024):
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step3-v102ab-merged-and-replay-20261126/Naqex_MarketFeedDumpRange.mq5
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_blind_multiday_replay.py
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step3-v102ab-merged-and-replay-20261126/market_feeds/feed_index.json (7 cửa sổ, 28 tệp thuần)
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_3_edge_cases_report.json
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_3_blind_multiday_replay_report.json
5. Báo cáo tổng hợp:
   - D:/ANNAM/TradingWorkspace/planning/research/STEP3-V102AB-MERGED-AND-CONTINUOUS-REPLAY-AUDIT-20261126.md

Yêu cầu kiểm toán và ra phán quyết Vòng 7 bằng tiếng Việt rõ ràng, chặt chẽ:
1. Kiểm độc lập toàn bộ SHA-256 (36 tệp Bước 3.2 + 28 tệp thị trường thuần Bước 3.3 + tệp Bước 2) và xác minh lại:
   - Lookahead mốc 09:30 NY đã bị loại bỏ thật sự hay chưa (tự thử làm nhiễu dữ liệu tương lai và đối chiếu với 85/85 mốc NY_ANCHOR_LOCKED của MT5)?
   - Bộ so sánh luồng sự kiện hợp nhất đã fail-closed thật sự (exit code != 0, chặn đúng 3/3 đột biến âm)?
   - Hợp nhất v1.02 (A + B) có thật sự khớp nguyên văn 5/5 với v1.02-A thuần và đạt 100% eval == accepted + sum(blk_by) (kể cả E7 = 601 = 596 lmin + 5 spread và C00 P1 gồm 22 news + 12 spread + 2.120 lmin)?
   - Phát lại mù liên tục 4 tháng (C10 P2: 312/312 deal, +38,28 USD trong đó +31,46 USD là 22 lần trượt giá qua SL dưới 1s; C00 P1: 310/310 deal, +18,19 USD trong đó +16,85 USD là 19 lần trượt giá qua SL dưới 1s; 34/34 SL không trượt lệch 0,00 USD) có bị rò rỉ đáp án nào không, và còn điểm yếu cấu trúc nào cần vá thêm không?
2. Trả lời thẳng 4 câu hỏi quyết định cho Bước 4:
   - (Q1) Có duyệt thăng hạng v1.02 (A + B) lên chính thức (#property version "1.02", bật mặc định InpProfitLockBasisMode = 1 và InpOpportunityLifecycleMode = 1) hay còn lỗi chặn nào?
   - (Q2) Với hiện tượng cùng giây 18:00:00 trên ADV_B2 (ClosePositionsByReason đóng E1 lãi +103,31 USD trước khi ProcessIntentAtomically chạy E6 trong cùng một RunMasterCycle, khiến g_curProfitPct giữ mức đầu chu kỳ 0,2085% thay vì 1,2416%): nên vá RunMasterCycle() làm mới realizedProfitPct/riskMult ngay khi số dư đổi sau đóng vị thế, hay giữ nguyên tính 1 lần đầu chu kỳ?
   - (Q3) Độ khớp Python <-> MT5 trên phát lại mù liên tục 4 tháng đã đủ để chuyển sang Bước 4: (a) diễn tập R1/R2 restart & giữ ID ngoài Strategy Tester, và/hoặc (b) mở lại so sánh kinh tế C00 vs C10 trên Dev (có tính nhạy trượt giá qua SL dưới 1s, vẫn giữ Holdout 2025+ SEALED & 0 VND) chưa?
   - (Q4) Giữ hay thay đổi phán quyết tài chính 0 VND ở thời điểm hiện tại?
```
