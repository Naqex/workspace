# Hồ Sơ Kiểm Toán Sprint 6 Giờ — FTMO Standard 10K, Đối Chiếu 7 Mắt Xích Python↔MT5 & C00 vs C10

- **Ngày chốt:** `26/11/2026` · **Chuẩn:** `PLAN v3.1` (Astra Vòng 3) · **Mã chạy:** `Naqex_Master_Prop7E.ex5` (`v1.01`, `sha16=2e0006ad786bdad6`, không sửa logic giao dịch)
- **Khóa an toàn:** `Holdout 2025+ SEALED` (`holdout_rows_analysed = 0`, [NATIVE_FTMO_HOLDOUT_LOCK.json](NATIVE_FTMO_HOLDOUT_LOCK.json) `f0a6b43cb205535b...`) · **`0` lệnh gửi tới broker** *(nhật ký Strategy Tester có các lệnh `OrderSend` mô phỏng nội bộ)* · `naqex-node1` nguyên vẹn · `0` lệnh thử nghiệm mới.

> ## Phán Quyết Đầu Trang
> - **CHẶNG 3 KINH TẾ = `DỪNG TẠI CỔNG PARITY` (`HALTED_AT_PARITY_GATE` theo luật Astra v3.1):** Không chạy Monte Carlo chấm điểm kinh tế Chặng 3 vì Chặng 2 phát hiện **sai lệch thực thi thực chất ở cả `C00` lẫn `C10`** (nhảy lot `1,77×–2,00×` do `ProfitLock` theo equity nổi, `E6` vào trễ `8` tiếng sau khi bị chặn cụm, tự cắt lệnh mở khi chạm trần lỗ ngày) **và thiếu khả năng quan sát trong MT5 Tester** (`Link #2/#5 = UNOBSERVABLE_IN_TESTER`; `R1/R2 = SKIPPED_IN_TESTER`).
> - **`C10` CHƯA THĂNG HẠNG** (`3` preset khóa cứng `DryRun = true`); **`C00` KHÔNG TỰ ĐỘNG ĐƯỢC CÔNG NHẬN CÓ EDGE** (chính `C00` cũng dính lệch `Link #2/#4/#5` và thiếu đo sống đa phiên); **quyết định tài chính: `0 VND`**.

---

## 1. Hợp Đồng `ftmo_standard_10k`, Preset & Công Khai Quản Trị

- **Hợp đồng chính thức ([prop_contracts_v2.json](../../tooling/ai-engines/configs/prop_contracts_v2.json)):** Đã thêm `ftmo_standard_10k` (`profile_mode = "Standard"`, đòn bẩy `1:100` FX / `1:50` Chỉ số / `1:30` Kim loại, mục tiêu `10% / 5%`, luật chính thức FTMO lỗ ngày `5%` & tĩnh `10%` dấu `<` nghiêm ngặt so với `<=` của runner, reset `00:00` Prague, P1/P2 cho phép tin đỏ có cảnh báo chi phí trượt giá, Funded cấm `±2m` / khiên bot `±5m`). Phí `98,70 EUR` (`105,12 USD`) và hạn giữ hóa đơn `14` ngày gắn nhãn **`MODEL_ASSUMPTION`**.
- **Preset `C10` mới (`DryRun = true`, giữ nguyên `4` preset `C00` v1.01):** [C10_P1_4x_L70.set](../../tooling/ai-engines/exports/deployment_kit/presets/FTMO_Std10K_MasterProp7E_C10_P1_4x_L70.set), [C10_P2_35x.set](../../tooling/ai-engines/exports/deployment_kit/presets/FTMO_Std10K_MasterProp7E_C10_P2_35x.set), [C10_Funded_125x.set](../../tooling/ai-engines/exports/deployment_kit/presets/FTMO_Std10K_MasterProp7E_C10_Funded_125x.set).
- **Công khai quản trị & kho bằng chứng gốc Layer-2 (`private_vault/strategies/sprint-6h-standard-parity-20261126/`):**
  - `Cluster B` (`2021–2024`) đã xem trên `C00..C15` -> **`VIEWED_NOT_BLIND`** (không gắn nhãn `BLIND`).
  - `S7_XAU_EXP120` từng chạm `2025–2026` -> loại vĩnh viễn khỏi lõi `7E`.
  - Đã lưu trọn `manifest_locked.json`, `step2a_profile_ablation.json`, `first_divergence_report.json`, `tick_and_28fills_forensics.json` và **`raw_mt5_logs/` (`18` lượt chạy / `90` tệp `.htm`/`.log`/`.set`/`.ini` gốc, `14,27 MB`, mỗi tệp `<= 390 KB`, kèm `raw_logs_index.json` khóa SHA-256)** để kiểm toán viên độc lập tính lại toàn bộ từ log thô.

---

## 2. Bước 2A — Chứng Minh Đổi Hồ Sơ `Swing -> Standard` & Lỗi Rơi Ngầm

Tại `tooling/ai-engines/pass27_portfolio_m1_phase_audit.py:318`, mã nguồn kiểm tra cứng `is_std = (profile_mode == "Standard")`. Truyền `"ftmo_standard_10k"` sẽ **âm thầm rơi về ký quỹ Swing (`1:30`/`1:15`)**.

| Mã (`symbol`) | Tín hiệu chuẩn (`<= 2024`) | Giá vào | `Swing` (USD/lot) | `Standard` (USD/lot) | Tỷ lệ giảm | Truyền `"ftmo_standard_10k"` |
|---|---|---:|---:|---:|---:|---:|
| `USDJPY` | `E1` (`2024-09-02`) | `145,906` | `3.333,33` | `1.000,00` | `3,3333×` (`-70%`) | `3.333,33` *(rơi về Swing)* |
| `GBPUSD` | `E3` (`2024-09-09`) | `1,306982` | `4.356,61` | `1.306,98` | `3,3333×` (`-70%`) | `4.356,61` *(rơi về Swing)* |
| `EURJPY` | `E6` (`2024-09-03`) | `161,079515` | `3.833,33` | `1.150,00` | `3,3333×` (`-70%`) | `3.833,33` *(rơi về Swing)* |
| `US100.cash` | `E4` (`2024-09-03`) | `19.105,121` | `1.273,67` | `382,10` | `3,3333×` (`-70%`) | `1.273,67` *(rơi về Swing)* |

Trên toàn Dev `2018–2024` (đổi thuần hồ sơ, giữ nguyên công thức lot): đỉnh ký quỹ P1 giảm từ `37,00% -> 11,10%` (`1,00×`) và `34,67% / 35,00% -> 10,40% / 10,50%` (`1,50×`); `margin_rejects = 0` ở cả hai chế độ nên chênh thuần `dPay1_12m = +0,00%` và `dNet24Med = +0,00 USD`.

---

## 3. Chặng 2 — Ma Trận 7 Mắt Xích & Điểm Lệch Đầu Tiên (`C00` & `C10`, `0 ms`)

Chạy thật `Naqex_Master_Prop7E.ex5` (`v1.01`) trong MT5 Tester (`Model=4` Real Ticks, `2024.09.01..2024.12.31`, `20.022.579` tick, `L1:100`, `ToDate=2024.12.31`) cho đủ `6` cấu hình pha (`C00` & `C10` × `P1/P2/Funded`) + `6` kịch bản đối kháng (`ADV_A`, `ADV_B1`, `ADV_B2`).

### Bảng 3.1 — Đối chiếu Python Step 2A (cũ) vs Step 2B (bám EA) trên cùng dòng lệnh MT5 (`0 ms`)

| Pha (`0 ms`, Q4) | MT5 Lệnh / Lãi / BalDD / EqDD | S2A Khớp cứng / `<=0,01` / Lệch số dư | S2B Khớp cứng / `<=0,01` / Lệch số dư | Điểm lệch đầu tiên S2A (`MT5 vs S2A`) | Điểm lệch đầu tiên S2B (`MT5 vs S2B`) & `>0,01` |
|---|---|---|---|---|---|
| **`C00` P1** (`4x, L50`) | `155` / `+730,55` / `4,90%` / `6,25%` | `46,45%` / `84,52%` / `-5,80` | `94,84%` / `98,06%` / `-14,86` | `#1` (`02/09 06:19 E1`): `0,13 vs 0,14` (`+7,69%`) | `#9` (`06/09 18:00 E2`): `0,18 vs 0,17` (`-5,56%`); **`3` lệnh** (max `0,37`) |
| **`C00` P2** (`2x, L50`) | `157` / `+371,00` / `3,18%` / `3,73%` | `66,24%` / `89,17%` / `+33,25` | `93,63%` / `98,73%` / `+11,86` | `#1` (`02/09 06:19 E1`): `0,06 vs 0,07` (`+16,67%`) | `#10` (`06/09 18:00 E2`): `0,12 vs 0,11` (`-8,33%`); **`2` lệnh** (max `0,21`) |
| **`C00` Funded** (`1x`) | `156` / `+119,53` / `2,43%` / `2,84%` | `67,31%` / `94,87%` / `-19,19` | `97,44%` / `99,36%` / `+1,31` | `#2` (`02/09 11:17 E6`): `0,05 vs 0,06` (`+20,0%`) | `#10` (`06/09 18:00 E2`): `0,06 vs 0,05` (`-16,67%`); **`1` lệnh** (max `0,02`) |
| **`C10` P1** (`4x, L70`) | `155` / `+371,25` / `7,34%` / `8,82%` | `43,23%` / `76,77%` / `+72,45` | `92,90%` / `99,35%` / `+7,49` | `#1` (`02/09 06:19 E1`): `0,13 vs 0,14` (`+7,69%`) | `#9` (`06/09 18:00 E2`): `0,18 vs 0,17` (`-5,56%`); **`1` lệnh** (max `0,03`) |
| **`C10` P2** (`3,5x, L35`) | `156` / `+461,44` / `6,28%` / `7,61%` | `39,10%` / `75,00%` / `-39,96` | `85,26%` / `94,23%` / `+37,85` | `#1` (`02/09 06:19 E1`): `0,11 vs 0,12` (`+9,09%`) | `#10` (`06/09 18:00 E2`): `0,18 vs 0,17` (`-5,56%`); **`9` lệnh** (max **`0,54`**) |
| **`C10` Funded** (`1,25x`) | `157` / `+161,83` / `3,02%` / `3,58%` | `63,69%` / `90,45%` / `+8,28` | `96,18%` / `98,09%` / `-2,57` | `#6` (`03/09 18:56 E4`): `0,28 vs 0,29` (`+3,57%`) | `#76` (`31/10 17:05 E3`): `0,16 vs 0,15` (`-6,25%`); **`3` lệnh** (max `0,04`) |

### Bảng 3.2 — Pháp y đủ 7 mắt xích (tái lập 100% từ log thô)

| Mắt xích | Trạng thái | Bằng chứng trạng thái trước -> sau & biên độ tác động |
|---|---|---|
| **1. Tín hiệu** | `LỆCH NGUỒN GIÁ` | Jaccard đo trên **tập ngày có deal** (Dukascopy M1 vs FTMO-Demo tháng `9–12/2024`; tín hiệu hợp lệ bị chặn sẽ biến mất khỏi tập này — kiểm chuẩn Link #1 cần so tín hiệu trước bộ lọc trên cùng nguồn giá/giờ): **`62,1%–100,0%`** (`C00`, đã lọc Red-News) và **`65,5%–100,0%`** (thô trên cả `C00` & `C10`); lệch đầu tiên ngày `2024-09-02` (`E6_EURJPY_VOLCOMP` chỉ có deal trên MT5). |
| **2. Nhận / Từ chối** | **`UNOBSERVABLE_IN_TESTER` + LỆCH CẤU TRÚC** | `LogMasterShadowRow()` (`L373`) và `LogExecAuditFor()` (`PropGuard:993`) thoát sớm trong `MQL_TESTER`; `lots < volMin` (`L653/L667`) thoát im -> **`0` dòng log / `0` tệp sandbox**.<br>- **`ADV_B2` (`23/10`, trần JPY `0,80%`):** Bản đối chứng vào `E6` lúc `10:00` (`0,21` lot). Ở bản siết trần, `E1 (0,13)` + `E2 (0,36 -> 0,03)` lấp trần -> `E6` chỉ vào lúc `18:00:00` (`0,10` lot) đúng giây `E1` đóng theo giờ báo cáo MT5 (khoảng cách **`8` giờ** là quan sát được; số lần từ chối thực tế chưa biết do `0` log; ngược Python bỏ qua cả ngày).<br>- **`ADV_B1` (`11/12`, trần `1,00%`):** Đệm `0,95` (`L651`) của `E4` chừa `~0,05%` cho `E5` lọt khe `0,02` lot (`0,81 -> 0,02`). |
| **3. Khối lượng** | `S2A LỆCH / S2B GẦN KHỚP` | S2A dùng vốn cố định `10k`, bỏ đệm `0,95`, chia `stop_risk_with_cost` -> sai ngay Lệnh `#1`. S2B theo `ACCOUNT_BALANCE * risk * 0,95` khớp `<=0,01` đạt `94,2%–99,4%` trên tập lệnh đã khớp *(chưa loại sạch đầu vào hậu-khớp & giá đóng cửa `USDJPY D1` cuối ngày ở Python — cần nhật ký trạng thái trước quyết định để đối chiếu chuẩn)*. |
| **4. Đổi chế độ trong ngày** | **`LỆCH LỚN Ở CẢ C00 & C10`** | EA kiểm tra **`ACCOUNT_EQUITY` nổi từng giây (`L772–779`)**:<br>- **`C10` P2 (`02/12 18:30`):** Số dư chốt `10.380,28 >= 10.350`, nhưng `E7` lỗ nổi `~-43 USD` kéo `Equity < 10.350` -> MT5 nhảy từ `1,75×` về `3,50×`, vào `E5` **`0,80` lot (gấp `2,00×` mức `0,40` của S2B)** *(chờ log trước quyết định xác nhận là nguyên nhân duy nhất)*.<br>- **`C00` P1 (`15/11` & `19/11`):** `15/11` chốt `10.496,54 < 10.500` nhưng lãi nổi đẩy MT5 vào `PROFIT_LOCK` sớm (`0,51 vs 0,88`); `19/11` chốt `10.505,85 >= 10.500` nhưng lỗ nổi kéo MT5 văng về `4,00×` (`E4 0,83 vs 0,47`, **`1,77×`**).<br>- **`C00` P2 (`15/11` & `19/11`):** `19/11` chốt `10.280,35 >= 10.250` nhưng lỗ nổi kéo MT5 văng từ `1,00×` về `2,00×` (`E4 0,44 vs 0,23`, **`1,91×`**).<br>- **`C10` P1 (`05/11`):** `AMBER` bật lúc `11:36` -> `E4 0,63` (MT5/S2B) vs S2A khóa đầu ngày `0,94` (`+49,2%`). |
| **5. Thoát & Tự ngắt** | **`LỆCH S2A + MÙ LOG + LỌT < 1s`** | **`ADV_A` (`19/11`, `kill=0,80%` vs `3,50%`):** MT5 `g_autoKillActive` cắt đồng loạt `E2` (sớm `1h`) & `E4` (sớm `4h19m`) lúc `18:36:02` (`-181,03 -> -84,56 USD`, `EqDD 3,03% -> 1,19%`), S2A để lệnh sống; `kill_reason = UNOBSERVABLE_IN_TESTER` (`L993`). **Fixture chứng minh cơ chế `<1s` (`L879`):** Fixture Python giả lập (`1725364801350 ms`, equity `9.498,50 USD` — *không phải vi phạm thật trong 18 lượt chạy*) chứng minh `OnTick` `1s` có thể bỏ lọt xuyên sàn nội giây (`observed = null`). Toàn bộ `12/12` lượt chạy pha đều `swap = 0,00 USD`. |
| **6. Đường vốn** | `ĐÃ ĐO ĐỘ LỆCH` | Lệch cuối Q4 (`S2B - MT5`): `C00` `-14,86 / +11,86 / +1,31 USD`; `C10` `+7,49 / +37,85 / -2,57 USD` (`S2A` lệch tới `+72,45` & `-39,96 USD`). |
| **7. Chuyển pha** | `ĐÃ KIỂM BIÊN` | Đỉnh số dư chốt (`82` ngày): `C00` `10.788,93 / 10.402,03 / 10.150,56`; `C10` `10.469,02 / 10.512,97 / 10.199,00`; unit test chặn chuyển pha khi còn lệnh mở. |

- **Hồi phục khởi động lại (`R1/R2`):** Cả `R1` (`Naqex_Signals_7E.mqh:320-326`) và `R2` (`Naqex_Master_Prop7E.mq5:170,197,229`) đều **`SKIPPED_IN_TESTER`** (tuyệt đối không viện dẫn `hydrated=true` trong Tester). Kiểm thử ngoại tuyến trong [test_standard_parity_and_boundaries.py](../../tooling/ai-engines/tests/test_standard_parity_and_boundaries.py) đạt `100%` nhưng gắn cứng nhãn **`PYTHON_LOGIC_VERIFIED_MQL_BRANCH_UNEXECUTED / UNTESTED_ON_LIVE_RESTART`**.
- **Biên 2 phía & DST (`test_standard_parity_and_boundaries.py`):** Đạt `100%` tại `+0,01 / 0,00 (< vs <=) / -0,01 / gap-through` cho cả `5%` ngày & `10%` tĩnh (tách cột `BOT_AUTO_KILL` vs `FIRM_HARD_BREACH`), Prague DST Xuân `23h` & Thu `25h`, giữ pha khi còn lệnh mở.
- **Lưu ý đối chiếu độc lập (`#370`):** (a) Trong `ADV_A` (`2024-11-19`), đặt `InpKillDailyDdPct=0,80% < 2,0%` cũng kích hoạt `Naqex_Master_Prop7E.mq5:417-424` (taper `dailyHeadroom < 2,0%`) ngay từ lệnh `#1` (`0,78->0,35`, `0,20->0,08`, `0,62->0,22`), nên mức chênh `-181,03 -> -84,56 USD` phản ánh **cả** thu nhỏ lot sớm lẫn lệnh tự ngắt `18:36:02` (`E2` sớm `1h01m`, `E4` sớm `4h19m`, `0` dòng log lý do kill); (b) Ở Link #1, Jaccard Dukascopy thô chưa lọc tin vs MT5 Q4 là `65,5%–100,0%` trên cả `C00` & `C10`, còn mức `62,1%` trên `C00 P1 E2` phản ánh bộ lọc Red-News áp trên Dukascopy (`News=ON`).
- **Biên nhận kiểm chứng độc lập từ log thô (`#370`):** `90/90` mã băm SHA-256 tệp thô khớp tuyệt đối, `18/18` báo cáo `.htm` gốc xác minh nguyên văn, `system_doctor --mode full` đạt `10/10` (`1.812 passed` — *chỉ là sức khỏe phần mềm*), `naqex-node1` trực tuyến chỉ đọc `open=0`, `0%` CPU Dev MT5.

---

## 4. Độ Phủ `.tkc` 2024, Chẩn Đoán Tháng `9–12/2024` (`0 ms` & `500 ms`) & Pháp Y 28 Lệnh Sống

- **Kiểm kê `.tkc` 2024 trên `8/8` mã bắt buộc (`Naqex_Signals_7E.mqh::Init()` fail-closed nếu thiếu 1 mã):** Có **`49/96` tháng-mã**, **thiếu đúng `47` tháng-mã**:
  - Đủ `12/12`: `USDJPY`, `EURUSD` (`0` thiếu).
  - Thiếu `7`: `GBPUSD` (`202401..202407`).
  - Thiếu `8` mỗi mã (`5 × 8 = 40`): `EURJPY`, `US100.cash`, `US500.cash`, `AUDUSD`, `USDCAD` (đều thiếu `202401..202408`).
  - **Giao điểm tick thực `8/8` mã = `2024-09-01 .. 2024-12-31` (`4/12` tháng `9–12/2024`)**; `2022–2024.hcc` đủ làm nóng (`20` D1 của `E6`, `>=15` Wilder `ATR(14)`, `490` M1 của `E7`); cả `8/8` mã đều có `2025+` `.tkc` trên đĩa (`0` byte đọc) -> bắt buộc `ToDate=2024.12.31` (`max_deal_date = 2024-12-30`).

### Bảng 4.1 — Chẩn đoán theo cặp tháng `9–12/2024` (`VERIFIED_INTERSECTION_2024_09_12_DIAGNOSTIC_ONLY` — KHÔNG phải Full-2024, KHÔNG thăng hạng)

| Nhánh / Pha (`20,02M` tick, `L1:100`) | Trễ | Lệnh | Lãi ròng (USD) | `500 - 0ms` | `PF` | `Sharpe` | `BalDD` | `EqDD` | `Comm` | `Swap` |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`C00` P1** (`4x, L50, News=ON`) | `0 ms` | `155` | `+730,55` | — | `1,23` | `1,97` | `4,90%` | `6,25%` | `-98,18` | `0,00` |
| **`C00` P1** (`4x, L50, News=ON`) | `500 ms` | `155` | `+790,52` | `+59,97` | `1,25` | `2,13` | `4,90%` | `6,24%` | `-98,36` | `0,00` |
| **`C10` P1** (`4x, L70, News=OFF`) | `0 ms` | `155` | `+371,25` | — | `1,10` | `0,92` | `7,34%` | `8,82%` | `-109,36` | `0,00` |
| **`C10` P1** (`4x, L70, News=OFF`) | `500 ms` | `155` | `+419,41` | `+48,16` | `1,11` | `1,04` | `7,25%` | `8,72%` | `-109,42` | `0,00` |
| **`C00` P2** (`2x, L50, News=ON`) | `0 ms` | `157` | `+371,00` | — | `1,21` | `1,69` | `3,18%` | `3,73%` | `-54,58` | `0,00` |
| **`C00` P2** (`2x, L50, News=ON`) | `500 ms` | `157` | `+404,99` | `+33,99` | `1,23` | `1,86` | `3,14%` | `3,72%` | `-53,98` | `0,00` |
| **`C10` P2** (`3,5x, L35, News=OFF`) | `0 ms` | `156` | `+461,44` | — | `1,14` | `1,25` | `6,28%` | `7,61%` | `-92,94` | `0,00` |
| **`C10` P2** (`3,5x, L35, News=OFF`) | `500 ms` | `156` | `+517,31` | `+55,87` | `1,16` | `1,42` | `6,16%` | `7,48%` | `-91,70` | `0,00` |
| **`C00` Funded** (`1x, News=ON`) | `0 ms` | `156` | `+119,53` | — | `1,10` | `0,88` | `2,43%` | `2,84%` | `-34,16` | `0,00` |
| **`C00` Funded** (`1x, News=ON`) | `500 ms` | `156` | `+144,97` | `+25,44` | `1,12` | `1,07` | `2,35%` | `2,75%` | `-34,20` | `0,00` |
| **`C10` Funded** (`1,25x, News=ON`) | `0 ms` | `157` | `+161,83` | — | `1,11` | `0,94` | `3,02%` | `3,58%` | `-43,32` | `0,00` |
| **`C10` Funded** (`1,25x, News=ON`) | `500 ms` | `157` | `+194,94` | `+33,11` | `1,13` | `1,13` | `2,94%` | `3,46%` | `-43,36` | `0,00` |

*Chẩn đoán ngắn gọn:* Trên riêng Q4, `C10 P1` (tắt tin đỏ, dời `L70`) kém hẳn `C00 P1` (`+371/+419` vs `+731/+791 USD`, `EqDD 8,82/8,72%` vs `6,25/6,24%`) và `C10 P2` nhân đôi `EqDD` (`7,61%` vs `3,73%`). Mức tăng nhẹ ở `500 ms` (`+25..+60 USD`) là nhiễu `ExecutionMode`, không phải lợi thế.

- **Pháp y `28` lệnh đo sống `25/11` (`56` chân, `0` từ chối, `swap = 0,00`):** Có đúng **`2` lệnh chạm SL thật `US100.cash`** (`#26` BUY SL `25.316,28 -> 25.312,43`, **`+385,0` pts / `+1,5208 bps`**; `#28` SELL SL `25.087,73 -> 25.087,28`, **`-45,0` pts / `-0,1794 bps`**). Phán quyết tách overshoot vs trượt khớp = **`KHÔNG TÁCH ĐƯỢC` (`UNSEPARABLE_MISSING_TRIGGER_QUOTE`)** do khoảng mù poll `5.000 ms` & thiếu `DEAL_TIME_MSC`. Trung vị SL Dev M1: `E4 = 140,65` (`n=414`), `E5 = 153,57` (`n=261`) điểm chỉ số; sốc `750 / 1.000` broker pts (`4,88%–7,11%` trung vị SL) gắn nhãn **`STRESS_ASSUMPTION`**. Mẫu thu thập chỉ đọc `QUOTE_ONLY` (`OrderSend = 0`) cho **NFP `04/12`** và **CPI `10/12`** đặt tại [NFP-CPI-READONLY-CAPTURE-TEMPLATE.md](../../tooling/ai-engines/exports/deployment_kit/NFP-CPI-READONLY-CAPTURE-TEMPLATE.md).

---

## 5. Bảng Trạng Thái 4 Cổng Kiểm Định (`PLAN v3.1`)

| Cổng | Trạng thái chốt | Bằng chứng tóm tắt |
|---|---|---|
| **Gate 1 — Phạm vi & Biên hợp đồng** | **`PASS_SCOPE_AND_BOUNDARIES`** | `Holdout = 0`, `OrderSend = 0`, `swap = 0,00`, `Step 2A` `3,3333×` + chứng minh rơi ngầm, bộ kiểm thử biên 2 phía & DST đạt `100%`. |
| **Gate 2 — Đồng bộ 7 mắt xích & Quan sát** | **`HALTED / DIVERGENCES_FOUND`** | Nhảy `ProfitLock` `1,77×–2,00×` trên cả `C00` & `C10`; `E6` vào trễ `8h` (`ADV_B2`); cắt mở giữa ngày (`ADV_A`); `Link #2/#5 = UNOBSERVABLE_IN_TESTER`; `R1/R2 = SKIPPED_IN_TESTER`. |
| **Gate 3 — Độ phủ 2024 & Chặng 3** | **`PARTIAL_4M_Q4_DIAGNOSTIC / CHẶNG 3 HALTED`** | Chỉ `49/96` tháng-mã 2024 có `.tkc` (thiếu `47`), giao điểm `4/12` tháng Q4; Chặng 3 kinh tế dừng hoàn toàn. |
| **Gate 4 — Thăng hạng & Chi tiêu** | **`HALTED / CHƯA ĐỦ BẰNG CHỨNG`** | **Phạm vi phán quyết (nguyên văn):** *"Phán quyết này chỉ khẳng định quy trình kiểm định parity đã chặn đúng lúc trước các sai lệch thực thi và lỗ hổng quan sát của bản `v1.01`: `C10` KHÔNG được thăng hạng, `C00` KHÔNG tự động được công nhận có lợi thế (edge) thực chiến, kết quả tháng `9–12/2024` chỉ mang tính chẩn đoán trên giao điểm `4/12` tháng có tick thực, dữ liệu `Holdout 2025+` giữ nguyên niêm phong (`holdout_rows_analysed = 0`), và quyết định tài chính giữ cứng ở mức `0 VND` (`0` lệnh gửi tới broker)."* |

---

## 6. Kế Hoạch Kỹ Thuật Kế Tiếp (`v1.02` — Đúng 4 Bản Vá Gốc Trước Mọi Lượt Kiểm Lại)

1. **Bật cờ nhật ký chẩn đoán Tester (`InpTesterEmitAuditLogs`):** Cho `LogMasterShadowRow()` (`L373`), `LogExecAuditFor()` (`PropGuard:993`) và `lots < volMin` (`L653/L667`) ghi đủ lý do từ chối / tự ngắt trong Tester, xóa điểm mù `UNOBSERVABLE_IN_TESTER`.
2. **Thống nhất `ProfitLock` MQL5 ↔ Python (`Link #4`):** Chọn cứng 1 chuẩn duy nhất (`ACCOUNT_BALANCE` chốt lãi hoặc `ACCOUNT_EQUITY` nổi có hysteresis + phản chiếu M1 trong Python) để triệt tiêu cú nhảy lot `1,77×–2,00×` trên cả `C00` và `C10`.
3. **Thống nhất quy tắc tín hiệu bị chặn cụm/margin (`Link #2`):** Quyết định rõ khóa cả ngày sau lần từ chối đầu hay chỉ thử lại trong cửa sổ hẹp, chặn triệt để `E6` vào trễ `8` tiếng (`ADV_B2`).
4. **Đồng bộ tự ngắt giữa ngày & diễn tập `R1/R2` ngoài Tester (`Link #5`):** Đưa cắt vị thế mở khi chạm `g_autoKillActive` vào Python (`Step 2B`), diễn tập tắt/bật lại MT5 trên Demo thật cho `R1/R2`, và tách riêng ảnh hưởng `OnTick` `1` giây. Song song chạy đo chỉ đọc `QUOTE_ONLY` quanh NFP `04/12` & CPI `10/12`.

---

## 7. Phụ Lục Lịch Sử (Đã Được Thay Thế) — Prompt Vòng 4 Gốc Trước Đính Chính

> **CẢNH BÁO — PROMPT LỊCH SỬ ĐÃ ĐƯỢC THAY THẾ (`26/11/2026`):** Khung dưới đây chỉ lưu nguyên văn prompt đã gửi Astra ở Vòng 4 để giữ dấu vết kiểm toán. Các điểm chưa chuẩn trong khung cũ (`OrderSend = 0` chưa tách rõ Tester vs broker, ước lượng `~28.800 tick` ở `ADV_B2`, mốc `1725364801350 ms` là fixture cơ chế, dải tháng `9–12/2024`) **đã được đính chính ở phần thân báo cáo trên và kiểm chứng lại bằng ảnh chụp trước quyết định tại [STEP1-V101-PREDECISION-OBSERVABILITY-AND-FORMULA-PARITY-20261126.md](STEP1-V101-PREDECISION-OBSERVABILITY-AND-FORMULA-PARITY-20261126.md)**. Agent mới **KHÔNG** dùng khung cũ này làm đầu vào chạy tác vụ.

```text
Xin Astra kiểm toán Vòng 4 (hậu thực thi Sprint 6 giờ theo PLAN v3.1) dựa trên gói log thô MT5 (18 lượt Model=4 / 90 tệp gốc) và báo cáo đối chiếu vừa chốt (`Holdout 2025+ SEALED`, `holdout_rows_analysed = 0`, `OrderSend = 0`, `naqex-node1` untouched, `0 VND`):

1) QUYẾT ĐỊNH DỪNG & KỶ LUẬT:
- Đã DỪNG Chặng 3 kinh tế (`HALTED_AT_PARITY_GATE`), KHÔNG chạy Monte Carlo thăng hạng, KHÔNG thăng hạng C10, KHÔNG tự động công nhận C00 có edge thực chiến, giữ 0 VND.
- Đã đính chính 2 mâu thuẫn toán học đầu trang TOP1-SOLO-QUANT-MASTER-PLAN.md (Đậu+Rớt+Chờ Ngày 180 = 100%; 4 nhánh +7,3% không nhân lãi 1x lên 18–30%; Năm 1 = 0 VND thu nhập trading).

2) BƯỚC 2A (SWING -> STANDARD):
- Xác nhận lỗi rơi ngầm `pass27_portfolio_m1_phase_audit.py:318`: truyền `"ftmo_standard_10k"` trả ký quỹ Swing; truyền `"Standard"` giảm ký quỹ 1 lot đúng 3,3333x (-70%) trên cả 4 mã lõi (USDJPY 3333,33->1000; GBPUSD 4356,61->1306,98; EURJPY 3833,33->1150; US100 1273,67->382,10 USD). Đỉnh ký quỹ P1 giảm 37,0%->11,1% (1x), margin_rejects=0, dPay1=0,00%.

3) CHẶNG 2 (7 MẮT XÍCH CẢ C00 & C10 + 6 KỊCH BẢN ĐỐI KHÁNG):
- Link #1: Jaccard Dukascopy thô chưa lọc tin vs FTMO-Demo Q4 = 65,5%–100% trên cả C00 & C10 (mức 62,1% trên C00 P1 E2 do lọc Red-News trên Dukascopy khi News=ON); lệch đầu tiên 2024-09-02 (E6).
- Link #2: UNOBSERVABLE_IN_TESTER (L373/L993/L653/L667 -> 0 dòng log). ADV_B2 (23/10, JPY cap 0,80%): E6 bị chặn ~28.800 tick từ 10:00 (0 log) rồi vào trễ 8h lúc 18:00 (0,10 lot) khi E1 đóng.
- Link #3: S2A khớp cứng 39,1%–67,3% (sai ngay Lệnh #1); S2B đạt 85,3%–97,4% cứng (<=0,01: 94,2%–99,4%).
- Link #4: Nhảy ProfitLock theo live Equity xảy ra trên CẢ C00 lẫn C10: C10 P2 02/12 nhảy 2,00x (0,40->0,80); C00 P1 19/11 nhảy 1,77x (0,47->0,83); C00 P2 19/11 nhảy 1,91x (0,23->0,44); C10 P1 05/11 AMBER bật giữa ngày khiến S2A đánh lố +49,2%.
- Link #5: ADV_A (19/11, kill 0,80% < 2,0%) vừa kích hoạt taper dailyHeadroom < 2,0% (Naqex_Master_Prop7E.mq5:417-424) từ lệnh #1 (0,78->0,35; 0,20->0,08; 0,62->0,22) vừa cắt sớm E2 (1h01m) & E4 (4h19m) lúc 18:36:02 (-181,03->-84,56 USD phản ánh cả 2 hiệu ứng, 0 dòng log kill_reason, S2A để sống); OnTick 1s (L879) bỏ lọt xuyên sàn <1s tại 1725364801350 ms; 12/12 lượt pha swap=0,00.
- R1/R2: SKIPPED_IN_TESTER; kiểm thử Python gắn nhãn PYTHON_LOGIC_VERIFIED_MQL_BRANCH_UNEXECUTED / UNTESTED_ON_LIVE_RESTART. Biên 2 phía (`+0,01/0,00 (< vs <=)/-0,01/gap`, Prague DST 23h/25h, chặn chuyển pha khi mở lệnh): 100% PASS.

4) CHẨN ĐOÁN Q4 (CHỈ 4/12 THÁNG) & 28 LỆNH SỐNG:
- .tkc 2024: 49/96 tháng-mã (thiếu 47 trên 6 mã); giao điểm 8/8 mã = 2024.09.01..2024.12.31 (20,02M tick).
- Q4 (0ms/500ms): C00 P1 +730,55/+790,52 (EqDD 6,25/6,24%) vs C10 P1 +371,25/+419,41 (8,82/8,72%); C00 P2 +371,00/+404,99 (3,73/3,72%) vs C10 P2 +461,44/+517,31 (7,61/7,48%); C00 Funded +119,53/+144,97 vs C10 Funded +161,83/+194,94.
- 28 lệnh sống (2 SL US100 #26 +385 pts / #28 -45 pts): KHÔNG TÁCH ĐƯỢC (khoảng mù poll 5.000 ms & thiếu DEAL_TIME_MSC); 750/1000 pts = STRESS_ASSUMPTION (~4,9%–7,1% trung vị SL Dev E4=140,65 / E5=153,57); đã khóa mẫu đo chỉ đọc QUOTE_ONLY cho NFP 04/12 & CPI 10/12.

CÂU HỎI CHO ASTRA VÒNG 4:
1. Gói dừng tại cổng Parity và 4 bản vá gốc v1.02 (cờ log Tester, chốt ProfitLock balance vs equity, khóa cùng ngày khi bị chặn cụm, đồng bộ intraday kill-close + diễn tập R1/R2 ngoài Tester) đã kín chưa hay còn điểm mù nào?
2. Với Link #4 ProfitLock, nên chọn (A) chốt theo ACCOUNT_BALANCE (giữ live Equity cho riêng phanh DD/kill) hay (B) giữ live Equity + hysteresis?
3. Với ADV_B2 (E6 vào trễ 8h), khóa cả ngày sau lần từ chối cụm đầu tiên có rủi ro thực chiến nào cần lưu ý không?
```
