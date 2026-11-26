# Báo Cáo Bước 5 — Đóng Toàn Bộ Blocker Astra Vòng 8, Đối Chiếu Kinh Tế Cùng Pha `C00` vs `C10` & Kho Giá/Tối Ưu Vốn 4 Hãng Quỹ (`26/11/2026`)

- **Trạng thái:** **`STEP5_COMPLETE_VERIFIED_BY_INDEPENDENT_RAW_AUDITOR | 0-VND | HOLDOUT 2025+ SEALED | READY_FOR_ASTRA_ROUND9`**
- **An toàn bất biến:** `holdout_rows_analysed = 0` ([NATIVE_FTMO_HOLDOUT_LOCK.json](NATIVE_FTMO_HOLDOUT_LOCK.json) SHA `f0a6b43cb205535b`), `OrderSend = 0`, `#property version "1.01"`, cả `3` cờ thử nghiệm (`InpProfitLockBasisMode`, `InpOpportunityLifecycleMode`, `InpPostCloseRefreshMode`) giữ mặc định `= 0`, `MT5_PROCS = 0`, `naqex-node1` nguyên vẹn không đụng chạm.
- **Kiểm chứng tổng thể (`raw-verifier` độc lập, chỉ đọc từ log gốc):** `mql5_parity_checker.py --require-ex5` (`8/8 PASS, 7/7 Master==7E, 0 drifts, 10 EX5`), `verify_deployment_kit.py --require-ex5` (`130 SHA, 10 EX5`), `pytest` mới (`37/37` + `16/16` OPSEC/catalog/optimizer), `system_doctor.py --mode full` (**`10/10 PASS`, `1.838 passed, 417 subtests passed`**).

---

## 1. Đóng Sạch `3/3` Điểm Kỹ Thuật Chặn Phát Hành Từ Astra Vòng 8

| Hạng mục Astra Vòng 8 | Cách vá đã triển khai | Bằng chứng kiểm toán độc lập (SHA-16) |
|---|---|---|
| **4.1 · 3 lỗ hổng PASS giả của bộ so sánh (`NaN`, sửa `commission`, sửa `end_balance`)** | Nâng [step3_blind_multiday_replay.py](../../private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_blind_multiday_replay.py) lên `v3`: ép `math.isfinite` mọi trường số bắt buộc, tự tính lại tích lũy `balance = prev_bal + profit + commission + swap` (`tol = 0,02 USD`) trên cả 2 sổ deal, và đưa khớp `end_balance_usd` vào `strict_zero_divergence_pass`. | Receipt `389a54cdd0827f0e`: `VERIFY_STRICT RC=0` (`edge_holiday` `638/638`, `edge_dst` `60/60`); chạy độc lập **toàn bộ `8/8` đột biến âm** (`mut1..mut5` + 3 ca Astra: `NaN equity`, `comm -100`, `end_balance 1.00`) đều trả **`exit code 2`** (+ `7/7` đột biến đối kháng phụ bị chặn). |
| **4.2 · Đa lệnh đóng chờ, `DONE_PARTIAL`, ghi file nguyên tử & diễn tập restart mở rộng** | Thay `g_pendingClosePosId` đơn bằng mảng `NAQEX_MAX_PENDING_CLOSES = 16` + `ApplyCloseOutcomeToPendingTable` (`DONE_PARTIAL` cộng phần đã khớp vào `closedConfirmedCount` nhưng giữ nguyên theo dõi phần khối lượng còn mở cho tới `DONE`) trong [Naqex_PropGuard.mqh](../../tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh) (`9d7fb3c966688df9`) & [Naqex_Master_Prop7E.mq5](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5) (`6b7ea2ee0d5bfa12`); ghi nguyên tử `.tmp -> END_SCHEMA -> FileMove FILE_REWRITE` trong cả `PersistOppState` ([Naqex_Signals_7E.mqh](../../tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh) `2f5b7d7ccd7b8a88`) & `PendingClose`. Biên dịch MetaEditor **`0 errors, 0 warnings`** (`.ex5` `4c4b2262a0750524` khớp cả `3` bản sao). | Receipt `e514b395e3d78dba` (`12/12` SHA PASS, `PID 31316 -> 39880`, `is_tester=false`, `conn=false`, `OrderSend=0`): đạt **6/6** kiểm tra offline gồm (1) Prague anchor + 4-deal fixture + `autoKill`, (2) `HydrateTradedDays` giờ hợp lệ lỗi tải lịch sử -> thử lại thành công, (3) `OPP_E6 12->13` kèm `.tmp` hỏng, (4) `2` đóng chờ cùng lúc qua restart, (5) `DONE_PARTIAL` `0,20->0,12->0,07->0,00`, (6) từ chối file thiếu `END_SCHEMA`. *(Lưu ý: theo phạm vi 100% offline, nhánh đọc lịch sử từ máy chủ Demo sống vẫn chưa chạm — để dành khi mở cổng Demo.)* |
| **4.3A · Ô đối chứng thứ 4 của `Q2` & khóa `622/622` trong `q2a_pass`** | Chạy lại trọn bộ `6/6` lượt `Model=4` trên `.ex5` mới `4c4b2262a0750524`, bổ sung **`Q2_CTRL_PL070_MULT020_REFRESH0`** (`refresh=0, ProfitLockMult=0,20`) và đưa `both_4m_identical` vào chính biểu thức `q2a_pass`. | Receipt `cf87f5af3be5e27f` (`36/36` SHA PASS, `swap = 0,00` cả 6 lượt): lúc `18:00:00` (`server_ts=1729706400`), `REFRESH0/M020` giữ `NORMAL@4,00, 0,10 lot` (`pcr=0`) trong khi `REFRESH1/M020` hạ `PROFIT_LOCK@0,20, 0,01 lot` (`pcr=1`); 4 tháng khớp **`622/622` deal (`312 + 310`, `0` sai khác)**. |

---

## 2. Kết Quả Nghiên Cứu Kinh Tế Cùng Pha, Cùng Hợp Đồng `C00` vs `C10` (Bước 5)

- **Biên nhận tổng hợp:** `private_vault/strategies/step5-c00-vs-c10-economic-20261126/step5_c00_vs_c10_economic_report.json` (`5e3b65e00f5ef567`) · Chỉ mục log gốc MT5 `36/36` tệp: `raw_logs_index.json` (`214a4f098e19df53`).

### 2.1. Đối Chứng MT5 `Model=4` Real-Tick Q4/2024 (`20.022.579` tick thật, `FTMO_STD 10K 1:100`, `swap = 0,00`)

| Ca MT5 (`ex5=4c4b2262...`) | Pha | Ứng viên | Tin đỏ | Số lệnh | Win% | `RR` | `PF` | Lãi ròng (USD) | `BalDD` | `EqDD` | `Sharpe` | Lệch `L0` mù (`cum_err`) | Dư chẩn đoán `L4` (`lệch lot`) |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `S5_STD_P1_C00` | P1 | `C00` | ON | `155` | `52,90%` | `1,089` | **`1,22`** | **`+708,89`** | `4,90%` | **`6,25%`** | **`1,91`** | `+18,14` (`0/0`) | `+0,00` (`0`, `309/310`) |
| `S5_STD_P1_C10` | P1 | `C10` | OFF | `155` | `51,61%` | `1,028` | `1,10` | `+371,25` | `7,34%` | `8,82%` | `0,92` | `+27,33` (`0/0`) | `-0,01` (`0`, `309/310`) |
| `S5_STD_P2_C00` | P2 | `C00` | ON | `157` | `52,87%` | `1,086` | **`1,22`** | `+381,62` | `3,18%` | **`3,73%`** | **`1,73`** | `+6,07` (`0/0`) | `-0,01` (`0`, `313/314`) |
| `S5_STD_P2_C10` | P2 | `C10` | OFF | `156` | `51,28%` | `1,083` | `1,14` | **`+462,38`** | `6,28%` | `7,61%` | `1,25` | `+38,11` (`0/0`) | `+0,00` (`0`, `311/312`) |
| `S5_STD_FUNDED_C00` | Funded | `C00` | ON | `156` | `52,56%` | `0,993` | `1,10` | `+119,53` | `2,43%` | `2,84%` | `0,88` | `+5,50` (`0/0`) | `+0,00` (`0`, `311/312`) |
| `S5_STD_FUNDED_C10` | Funded | `C10` | ON | `157` | `52,87%` | `0,988` | **`1,11`** | **`+161,83`** | `3,02%` | `3,58%` | **`0,94`** | `+3,21` (`0/0`) | `+0,00` (`0`, `313/314`) |

### 2.2. Nghiên Cứu `7` Năm Dev (`2018–2024`, `DAILY_APPROX`, `CLUSTER_B_VIEWED_NOT_BLIND`, Trượt SL Tính Đúng 1 Lần)
- **Độ ổn định thứ hạng (Quy tắc dừng Astra Vòng 8):** **`C10_DOMINATES_ECONOMIC_ZERO_FLIP`** — `C10` đứng trên `C00` ở **`120/120`** ô kinh tế (`0` lần đảo thứ hạng qua `0,66×..1,75×`, `<` vs `<=`, CBB `10.000` vs Rolling `1.462` cửa sổ, `Standard 1:100` vs `Swing 1:30`, `Cluster A` vs `Cluster B`).
- **Phát hiện thực nghiệm cực quan trọng (Tách nhân tố Tin Đỏ vs Cỡ Lệnh):**
  - Khoảng **`~90%`** lợi thế 7 năm của `C10` (`+190,1` trong `+210,0 USD` ở `10K`) đến từ **cỡ lệnh `P2/Funded` + `ProfitLock`**, **KHÔNG phải từ việc tắt khiên tin đỏ (`+20 USD`)**.
  - Trên tick thật Q4/2024 MT5 `Model=4`, `S5_STD_P1_C10 (News=OFF)` thua `C00 (News=ON)` tới **`-337,64 USD`** (`EqDD 8,82%` vs `6,25%`) vì dính thêm `3` lệnh quét SL quanh NFP/CPI, trong khi ở Funded (cả hai bật tin đỏ) `C10` thắng rõ (`+161,83` vs `+119,53 USD`).
  - Đối chiếu mở rộng tại [MULTI-FIRM-CAPITAL-PROMO-OPTIMIZER-20261126.md](MULTI-FIRM-CAPITAL-PROMO-OPTIMIZER-20261126.md) xác nhận biến thể **`C10_NEWS_ON`** (giữ cỡ lệnh `C10` nhưng **BẬT khiên tin đỏ ở cả 3 pha**) đạt `NPV 24T` cao nhất trên `100K` (`+161,8 tr` vs `C10 +157,5 tr` vs `C00 +138,2 tr`), đồng thời giữ rủi ro cháy Funded 12T ở mức cực thấp (`0,03%`–`0,35%`, lưu ý `C00` còn thấp hơn ở `0,00%`–`0,02%` và vẫn cần `N~299` quan sát độc lập theo Luật 13).

---

## 3. Tóm Tắt Làn 2 — Kho Giá Thực 4 Hãng Quỹ & Tối Ưu Vốn 2 Mục Tiêu

- **Kho giá 4 hãng (`prop_pricing_catalog.json` `10b05130d06df8a3`, `FRESH`, `USD/VND = 25.765,94`):** Khóa `20/20` giá checkout VN thật ngày `26/11/2026` cho FTMO (`MEASURED_DEMO_EXECUTION`, xác nhận `Swing 50K/100K/200K` bị khóa tại VN) + `3` hãng cho phép cư dân VN & EA tự viết trên MT5 (`The5ers`, `IC Funded`, `E8 Markets`, tất cả gắn nhãn **`TERMS_VERIFIED_EXECUTION_UNMEASURED`**); ghi nhận loại các hãng cấm VN/EA (`FundedNext`, `FundingPips`, `Alpha Capital`, `Maven`, `FXIFY`, `BrightFunded`, `Fintokei`, `Hantec`).
- **Bộ tối ưu toán học (`MULTI-FIRM-CAPITAL-PROMO-OPTIMIZER-20261126.md` `1f023ff785e484d1`):** Chạy làm tròn `0,01` lot thật riêng từng bậc `5K → 200K`, chiết khấu `NPV 6%/năm` + phí thẻ `+2,5%` + phí rút `1,5%–4,0%`, lịch sale động (*Mua hôm nay vs Chờ `Y` ngày*), cắt phí chìm tại `> 1,75×` (ngưỡng hòa vốn `2,31×`), và xuất đủ ma trận `15 / 25 / 35 / 50 / 80 tr VND × 0 / 3 / 5 tr/tháng` cho cả `Hồ sơ A (NPV, Cháy <= 5%)` lẫn `Hồ sơ B (Nhanh rút, Cháy <= 10%)`.

---

## 4. Prompt Sẵn Dán Gửi GPT-6.2 Astra (Vòng 9 — Thẩm Định Đóng Blocker Vòng 8 & Phán Quyết `C00 / C10 / C10_NEWS_ON`)

> *Sao chép nguyên khối dưới đây gửi trực tiếp cho Astra.*

```text
Xin Astra thẩm định Vòng 9 dựa trên bằng chứng Bước 5 đã đóng đủ 3 blocker Vòng 8 và chạy đối chứng kinh tế cùng pha/cùng hợp đồng C00 vs C10 (100% offline, Holdout 2025+ NIÊM PHONG f0a6b43cb205535b, holdout_rows_analysed=0, OrderSend=0, 0 VND, #property version "1.01", cả 3 cờ opt-in giữ mặc định 0, naqex-node1 nguyên vẹn):

1) ĐÓNG 3 BLOCKER KỸ THUẬT VÒNG 8 (có kiểm toán độc lập từ log gốc):
- Mục 4.1 (3 lỗ hổng PASS giả bộ so sánh): Đã nâng `private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_blind_multiday_replay.py` lên `v3` (`a3b6538016614e1d`): ép `math.isfinite` mọi trường số bắt buộc, tự cộng kiểm chéo `balance = prev_bal + profit + commission + swap` từng deal, đưa khớp `end_balance_usd` vào `strict_zero_divergence_pass`. Receipt `private_vault/strategies/step4-hardening-restart-q2-20261126/step4_1_hardened_comparator_report.json` (`389a54cdd0827f0e`): `VERIFY_STRICT RC=0` (`edge_holiday 638/638`, `edge_dst 60/60`); chạy CLI `NEGATIVE_SELF_TEST` trên đủ 8/8 đột biến âm (gồm 3 ca Vòng 8: `NaN equity`, `commission -0.38 -> -100.00`, `end_balance -> 1.00`) đều trả `exit code 2` (+ 7 ca đối kháng phụ).
- Mục 4.2 (Multi-pending-close, DONE_PARTIAL, ghi nguyên tử & diễn tập offline mở rộng): Đã nâng cấp `Naqex_PropGuard.mqh` (`9d7fb3c966688df9`), `Naqex_Signals_7E.mqh` (`2f5b7d7ccd7b8a88`), `Naqex_Master_Prop7E.mq5` (`6b7ea2ee0d5bfa12`) -> biên dịch MetaEditor `0 errors, 0 warnings`, `.ex5` SHA `4c4b2262a0750524` khớp cả 3 bản sao (`8/8` parity, `130` SHA kit). Diễn tập 2 tiến trình OS cô lập (`PID 31316 -> 39880`, `is_tester=false`, `conn=false`, `OrderSend=0`, receipt `e514b395e3d78dba`, 12/12 SHA): đạt 6/6 kiểm tra (Prague anchor + 4-deal fixture + autoKill; `HydrateTradedDays` giờ hợp lệ tải lịch sử lỗi -> thử lại thành công; `OPP_E6 12->13` kèm `.tmp` hỏng; 2 pending-close đồng thời qua restart; `DONE_PARTIAL` `0.20->0.12->0.07->0.00` cập nhật risk nhưng giữ theo dõi khối lượng còn lại; từ chối file thiếu `END_SCHEMA`). Lưu ý trung thực: nhánh kết nối máy chủ Demo sống đọc lịch sử thật cố ý chưa chạy ở đợt 100% offline này.
- Mục 4.3A (Ô đối chứng Q2 thứ 4 + gộp 622/622 vào `q2a_pass`): Đã chạy lại toàn bộ 6/6 lượt MT5 Model=4 trên `.ex5` mới `4c4b2262a0750524` (receipt `cf87f5af3be5e27f`, 36/36 SHA, `swap=0.00` cả 6). Tại `2024-10-23 18:00:00`: `Q2_CTRL_PL070_MULT020_REFRESH0` giữ `NORMAL@4.00, 0.10 lot` (`pcr=0`) vs `Q2_TREAT_PL070_MULT020_REFRESH1` hạ `PROFIT_LOCK@0.20, 0.01 lot` (`pcr=1`). Hai lượt 4 tháng khớp `622/622` deal (`0` sai khác) và đã được khóa trực tiếp vào `q2a_pass`.

2) KẾT QUẢ BƯỚC 5 — SO SÁNH KINH TẾ CÙNG PHA, CÙNG HỢP ĐỒNG C00 vs C10:
- Hồ sơ: `private_vault/strategies/step5-c00-vs-c10-economic-20261126/step5_c00_vs_c10_economic_report.json` (`5e3b65e00f5ef567`) và 36/36 raw logs (`214a4f098e19df53`).
- Đối chứng MT5 Model=4 (Q4/2024, 20.02M tick thật, `FTMO_STD 10K 1:100`, `swap=0.00`, `L0` mù `0/0 cum_err`, `L4` chẩn đoán dư `0.00/-0.01 USD`, `0` lệch lot):
  * `P1`: `C00 (News=ON)` +$708.89 (`EqDD 6.25%, PF 1.22`) vs `C10 (News=OFF)` +$371.25 (`EqDD 8.82%, PF 1.10`) -> `C10` kém `-$337.64` do thêm 3 SL gap-slip quanh NFP/CPI.
  * `P2`: `C00 (News=ON)` +$381.62 (`EqDD 3.73%, PF 1.22`) vs `C10 (News=OFF)` +$462.38 (`EqDD 7.61%, PF 1.14`).
  * `FUNDED`: `C00 (News=ON)` +$119.53 (`EqDD 2.84%, PF 1.10`) vs `C10 (News=ON)` +$161.83 (`EqDD 3.58%, PF 1.11`).
- 7 năm Dev (`2018-2024`, `DAILY_APPROX`, `CLUSTER_B_VIEWED_NOT_BLIND`, trượt SL tính đúng 1 lần, kiểm cả `<` vs `<=`, CBB 10K vs Rolling 1,462 cửa sổ, Standard 1:100 vs Swing 1:30):
  * Thứ hạng kinh tế: `C10_DOMINATES_ECONOMIC_ZERO_FLIP` (120/120 ô kinh tế `C10 > C00`, 0 đảo thứ hạng từ `0.66x..1.75x`).
  * Nhưng tách nhân tố cho thấy `~90%` lợi thế của `C10` đến từ cỡ lệnh P2/Funded + ProfitLock, KHÔNG phải tắt tin đỏ; trên bộ tối ưu Làn 2 (`MULTI-FIRM-CAPITAL-PROMO-OPTIMIZER-20261126.md`), biến thể `C10_NEWS_ON` (giữ cỡ lệnh `C10`, bật tin đỏ `±5m` mọi pha) đạt `NPV 24T` cao nhất trên `FTMO Std 100K` (`+161.8tr` vs `C10 +157.5tr` vs `C00 +138.2tr`), trong khi `C00` vẫn có cháy Funded 12T thấp hơn (`0.00-0.02%` vs `C10 0.04-0.35%`).
- `system_doctor.py --mode full`: `10/10 PASS` (`1,838 passed, 417 subtests passed`).

CÂU HỎI CHỐT VÒNG 9 CHO ASTRA (TRẢ LỜI NGẮN GỌN, THẲNG THẮN):
1. Với 4.1 (`8/8` đột biến RC=2), 4.2 (multi-pending + `DONE_PARTIAL` + ghi nguyên tử + 6/6 diễn tập offline), và 4.3A (đủ 4 ô Q2 + `622/622` trong `q2a_pass`): còn điều kiện kỹ thuật nào trước khi chạy bài kiểm Demo chỉ đọc (`OrderSend=0`) cho nhánh đọc lịch sử thật của EA chính?
2. Giữa `C00`, `C10 (News=OFF ở P1/P2)` và `C10_NEWS_ON (cỡ lệnh C10 + bật tin đỏ ±5m ở mọi pha)`: Astra khuyến nghị chốt ứng viên nào (có cần chạy thêm đúng 2 lượt MT5 Model=4 Q4/2024 cho `C10_NEWS_ON` P1/P2 để xác minh thực nghiệm không)?
3. Về tài chính (`0 VND`): với bảng giá VN thật mới khóa (`FTMO Std 10K BF $68.70 / gốc $98.61`, `Swing` chỉ có `10K/25K`, `25K` là bẫy giá) và lịch đo NFP `04/12` + CPI `10/12`, tiếp tục giữ `0 VND` hay mở bước chuẩn bị nào tiếp theo?
```
