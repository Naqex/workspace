# Kiểm toán Toàn diện Điểm mù Trước Holdout (`2025–2026`) & Đo chuẩn Quant Factory 4 Lớp

- **Ngày thực hiện:** `23/11/2026`
- **Biên nhận máy kiểm chứng (SHA-256 `342d124a06890a5e`):** [PRE-HOLDOUT-BLINDSPOT-AUDIT-20261123.json](PRE-HOLDOUT-BLINDSPOT-AUDIT-20261123.json)
- **Trạng thái bất biến an toàn:** `holdout_rows_analysed = 0` (`max_trade_day = 2024-12-31`, khóa [NATIVE_FTMO_HOLDOUT_LOCK.json](NATIVE_FTMO_HOLDOUT_LOCK.json) nguyên vẹn SHA `f0a6b43cb205`), `OrderSend = 0`, `weekend_violations = 0`, `post_21utc_exits = 0`.
- **Single Source of Truth danh mục:** [PORTFOLIO-REGISTRY.json](PORTFOLIO-REGISTRY.json) (`9` động cơ đóng băng, `parity_match_p28 = true`).

---

## 1. Đo chuẩn Hiệu năng & Parity Quant Factory 4 Lớp (`quant_factory/` + `configs/`)

Kiến trúc 4 lớp không gắn cứng (cấu hình JSON khai báo ở `tooling/ai-engines/configs/`, cache `.npz` zero-pickle trong `.runtime/hot-m1-cache/_derived/`, nhân thống kê/vòng đời Numba JIT, báo cáo & guard MQL5 dùng chung) đã được kiểm chứng khớp 1:1 với bản đóng băng Pass 28:

| Hạng mục đo kiểm | Trước nâng cấp | Sau nâng cấp | Mức tăng tốc / Kết quả |
|---|---:|---:|---|
| Nạp băng lệnh M1 `9` động cơ (`2018–2024`) | `16.34s` (dựng từ Parquet) | **`0.28s`** (`.npz` zero-pickle + SHA) | **`58.4×` nhanh hơn** |
| Mô phỏng vòng đời `N = 2.000 × 504` ngày (1 hồ sơ) | `~10–20s` (vòng lặp Python) | **`9.01 ms`** (`0.108s` cho cả `12` tổ hợp!) | **`> 1.000×` nhanh hơn** |
| Hồi quy toàn bộ `1.560+` bài test (`tooling/ai-engines/tests`) | `55.96s` (`unittest` 1 nhân) | **`~24s`** (`pytest -n 6` song song 6 nhân) | **`2.35×` nhanh hơn** |
| Đối chiếu Parity M1 Floating Equity `PORT_7E_P28_CORE` | `+7.73%/năm`, DD `6.36%`, Cal `1.21` | `+7.73%/năm`, DD `6.36%`, Cal `1.22` (`7.73/6.36`) | **Khớp 100%** (`0` lỗi margin) |
| Đối chiếu Parity M1 Floating Equity `PORT_9E_P28_TURBO` | `+8.83%/năm`, DD `6.37%`, Cal `1.39` | `+8.83%/năm`, DD `6.37%`, Cal `1.39` | **Khớp 100%** (`0` lỗi margin) |

---

## 2. Bốn Điểm mù Thống kê Đã Kiểm định Thực nghiệm (`2018–2024`)

### 2.1. Multiple-Testing tích lũy — Deflated Sharpe Ratio (DSR / PSR)

Để tránh ảo giác do đã chạy nhiều đợt nghiên cứu từ V1 đến Pass 28, ta tính **Probabilistic Sharpe Ratio (`PSR`)** và **Deflated Sharpe Ratio (`DSR`, Bailey & Lopez de Prado 2014)** có hiệu chỉnh độ lệch (`skew`) và đuôi dày (`kurtosis`) trên chuỗi lãi ngày thực tế dưới 4 giả định số phép thử độc lập `M`:

| Danh mục & Phân vùng | `SR_ann` | `Skew` | `Kurt` | `PSR (M=1)` | `DSR (M=40)` | `DSR (M=250)` | `DSR (M=600)` |
|---|---:|---:|---:|---:|---:|---:|---:|
| `PORT_7E` Toàn bộ (`2018–2024`, `1.564d`) | `1.301` | `+1.388` | `9.16` | **`99.97%`** | `86.59%` | `66.42%` | `55.58%` |
| `PORT_7E` Cụm B mù (`2021–2024`, `898d`) | `1.215` | `+1.269` | `9.32` | **`99.17%`** | `54.29%` | `28.44%` | `19.73%` |
| `PORT_9E` Toàn bộ (`2018–2024`, `1.564d`) | `1.357` | `+1.629` | `11.12` | **`99.98%`** | **`89.80%`** | `71.88%` | `61.49%` |
| `PORT_9E` Cụm B mù (`2021–2024`, `898d`) | `1.226` | `+1.355` | `10.87` | **`99.23%`** | `55.17%` | `29.40%` | `20.47%` |

**Kết luận thẳng thắn:**
- Tín hiệu có **độ lệch dương rất đẹp (`skew +1.27` tới `+1.63`)** — đặc trưng lành mạnh của hệ cắt lỗ cứng, thả lãi theo xu hướng (`PSR > 99.1%` cả trên Cụm B mù).
- **Cảnh báo quan trọng:** Nếu phạt ở mức cực đoan `M = 600` phép thử hoàn toàn độc lập (thực tế số phép thử độc lập hiệu dụng `M_eff` nhỏ hơn nhiều vì các biến thể trong cùng 1 họ tương quan chặt, cỡ `30–60` họ độc lập), ngưỡng khấu trừ Sharpe `SR0` đã lên tới `1.25–1.65`. Điều này chứng minh **phải DỪNG khám phá/tinh chỉnh trên dữ liệu `2018–2024` ngay bây giờ**: mỗi Pass đào thêm chỉ làm nặng thêm hình phạt chọn lọc, trong khi một lần mở **Holdout `2025–2026` duy nhất với danh mục đã đóng băng (`M = 1`)** mới là bằng chứng không thiên lệch thực sự.

### 2.2. Tương quan đuôi trong ngày khủng hoảng (`Worst-5% Tail Correlation`)

Một điểm mù kinh điển của danh mục đa bot là các bot tưởng chừng độc lập lúc bình thường nhưng **cùng dính SL một ngày** khi thị trường sập (tương quan nhảy lên `+0.6`–`+0.8`). Kết quả đo trên `1.564` ngày giao dịch và **79 ngày lỗ nặng nhất (top 5% đuôi xấu)**:

| Danh mục | Tương quan TB mọi ngày | Cặp cao nhất mọi ngày | Tương quan TB **79 ngày xấu nhất** | Cặp cao nhất ngày xấu |
|---|---:|---|---:|---|
| `PORT_7E` | `+0.0411` | `+0.314` (`E4 × E5` US100) | **`-0.1144`** | `+0.2247` (`E4 × E5` US100) |
| `PORT_9E` | `+0.0410` | `+0.330` (`E3 × S6` FX) | **`-0.0774`** | `+0.2542` (`E4 × E5` US100) |

**Kết luận:** **ĐẠT XUẤT SẮC.** Tương quan trong đuôi lỗ nặng chuyển sang **âm (`-0.08` đến `-0.11`)**, không có hiện tượng cộng hưởng sập đồng loạt giữa FX, US100 và Vàng.

### 2.3. Kiểm tra suy giảm Alpha theo từng năm (`2018 → 2024`)

- **`PORT_7E`:** `2018: +11.42%` · `2019: -0.23%` · `2020: +13.53%` · `2021: +1.94%` · `2022: +18.41%` · `2023: +2.07%` · `2024: +7.00%` (dương `6/7` năm, độ dốc tuyến tính `-0.135%/năm`).
- **`PORT_9E`:** `2018: +11.81%` · `2019: -0.32%` · `2020: +18.45%` · `2021: +2.40%` · `2022: +19.58%` · `2023: +3.30%` · `2024: +6.60%` (dương `6/7` năm, độ dốc `-0.259%/năm`).
- **Điểm cần chấp nhận trước về mặt tâm lý:** Hệ thống ăn mạnh ở các năm có sóng xu hướng/biến động vĩ mô (`2018`, `2020`, `2022`, `2024`) và đi ngang nhẹ (`0%` đến `+3%`) ở các năm thị trường ngủ yên (`2019`, `2021`, `2023`). Không có dấu hiệu "chết alpha" ở `2024`, nhưng nếu gặp năm đi ngang phải kiên trì không tắt bot giữa chừng.

### 2.4. Phân bổ nhân quả `Cluster-A Inverse-DD` & Phanh biến động 1 chiều (`Downside Vol Brake`)

So sánh phân bổ cơ sở với `Inverse-DD` (chỉ fit trên Cụm A `< 2021-01-01`) và 2 kiểu điều tiết biến động 20 ngày trên `PORT_9E`:

| Kiểu phân bổ (`PORT_9E`, 100% nhân quả) | All `Ann%` | All `PeakDD` | All `Calmar` | Blind B `Calmar` | Blind B `UW` | Nhận xét |
|---|---:|---:|---:|---:|---:|---|
| Cơ sở (`Raw 9E`) | `+8.83%` | `6.25%` | `1.41` | `1.28` | `6.5m` (`12.6m` All) | Tốc độ cao, vùng chìm dài |
| **`Cluster-A Inverse-DD` thuần** | `+7.32%` | `5.09%` | **`1.44`** | `1.34` | **`5.4m`** (`6.0m` All) | Cắt đôi thời gian chìm |
| **`Inverse-DD + Downside Vol Brake [0.55, 1.00]`** | `+6.69%` | **`4.89%`** | `1.37` | **`1.39`** | **`5.4m`** (`5.8m` All) | **Đạt đỉnh Calmar mù Cụm B, DD < 5%** |
| `Inverse-DD + Vol-Target 2 chiều [0.55, 1.35]` | `+7.88%` | `6.57%` | `1.20` | `1.20` | `5.4m` | **Bị loại:** đòn bẩy ngược `1.35×` lúc thị trường êm làm tăng Daily DD (`1.77% → 2.39%`) |

Khi chạy mô phỏng Numba `N = 2.000` (504 ngày) so sánh 3 hồ sơ trên 4 tài khoản quỹ:

| Quỹ | Hồ sơ | `Pass 6m` | `Pass 12m` | `Pass 24m` | `Br1%` | `Med Pass` | `CF12` | `CF24` | `OOP95` |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **FTMO 10k** (Swing/Std) | `P1_SPRINT_25X` (`2.5×`) | `27.4%` | `55.2%` | `77.3%` | `0.8%` | `8.1m` | `+125 USD` | **`+647 USD`** | `168 USD` |
| **FTMO 10k** (Swing/Std) | `P1_SPRINT_30X` (`3.0×`) | **`31.8%`** | `53.0%` | `72.2%` | `1.6%` | **`6.9m`** | **`+140 USD`** | `+620 USD` | `168 USD` |
| **FTMO 10k** (Swing/Std) | **`P1_SMOOTH_INVDD_VT`** (`InvDD+Brake 3.0×`) | `25.9%` | **`55.9%`** | **`78.2%`** | **`0.4%`** | `8.3m` | `+118 USD` | `+642 USD` | `168 USD` |
| **The5ers HS 5k** | `P1_SPRINT_25X` (`2.5×`) | `27.4%` | `55.2%` | `77.3%` | `0.8%` | `8.1m` | `+80 USD` | **`+327 USD`** | `39 USD` |
| **The5ers HS 5k** | `P1_SPRINT_30X` (`3.0×`) | **`31.7%`** | `53.0%` | `72.2%` | `1.6%` | **`6.9m`** | **`+87 USD`** | `+316 USD` | `39 USD` |
| **The5ers HS 5k** | **`P1_SMOOTH_INVDD_VT`** (`InvDD+Brake 3.0×`) | `25.9%` | **`55.9%`** | **`78.2%`** | **`0.4%`** | `8.3m` | `+77 USD` | `+324 USD` | `39 USD` |
| **The5ers HG 5k (1-Step)** | `P1_SPRINT_25X` (`2.5×`) | `66.0%` | `88.4%` | `98.2%` | `31.4%` | `3.9m` | `-11 USD` | `+442 USD` | `780 USD` |

*(Ghi chú: Trên Hyper Growth 1-Step với Static DD chỉ `6%`, hệ số `2.5×–3.0×` là quá lớn gây `Br1 = 31%–43%`, `OOP95 = 780 USD`; đúng như Pass 28 đã chốt, nhánh 1-Step chỉ hợp nếu giữ `<= 1.5×–2.0×`, và 2-Step vẫn vượt trội tuyệt đối về tỷ suất dòng tiền trên vốn bỏ ra).*

---

## 3. Năm Điểm mù Vận hành Prop Firm & MT5 Backtest-to-Live Parity (Cộng đồng Thực chiến)

Tổng hợp từ các sự cố mất payout / lệch backtest phổ biến nhất trên cộng đồng MQL5, FTMO và The5ers — kèm kiểm định thực nghiệm và lớp phòng thủ đã tích hợp sẵn vào [Naqex_PropGuard.mqh](../../tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh):

### 3.1. Luật gộp *"1% Trade Idea Bundle"* khi FTMO duyệt Payout tài khoản Funded
- **Rủi ro thực tế:** FTMO không cấm mở nhiều lệnh, nhưng khi xét duyệt payout trên tài khoản Funded, bộ phận Risk có thể gộp các lệnh mở gần nhau trên **cùng một mã** (ví dụ `E4 + E5` cùng đánh `US100`, hoặc `E1 + E2 + E7` cùng đánh `USDJPY`) thành **1 ý tưởng giao dịch duy nhất**; nếu tổng rủi ro vượt ngưỡng `1%–1.5%` có thể bị cảnh báo hạ vốn hoặc từ chối payout.
- **Bằng chứng thực nghiệm trên dữ liệu M1 thật (`2018–2024`):**

| Kịch bản kiểm thử | `Ann%` | `PeakDD` | `DailyDD` | `Calmar` | Số lần chạm trần (`7` năm) |
|---|---:|---:|---:|---:|---:|
| Funded `PORT_7E` (không trần) | `+7.73%` | `6.36%` | `1.95%` | `1.22` | `0` |
| **Funded `PORT_7E` + Trần `1.00%`/mã (`SYMCAP_100`)** | **`+7.79%`** | **`6.36%`** | `1.95%` | **`1.23`** | `39` |
| **Funded `PORT_7E` + Trần `1.00%`/mã + Tin đỏ `±5m`** | `+7.11%` | `8.19%` | `1.95%` | `0.87` | `37` |
| `PORT_9E` `1×` + Trần `1.00%`/mã (`SYMCAP_100`) | `+8.67%` | `6.49%` | `2.24%` | `1.34` | `57` |
| `PORT_9E` `1×` + Trần `1.00%`/mã + Tin đỏ `±5m` | `+8.03%` | `8.19%` | `2.24%` | `0.98` | `55` |
| Challenge P1 `PORT_9E 2.5×` + Trần `2.00%`/mã (`SYMCAP_200`) | `+21.73%` | `17.81%` | `5.90%` | `1.22` | `138` |

- **Quyết định kỹ thuật:** Bật cứng `InpGuardMaxSymbolRiskPct = 1.00` trên tài khoản **Funded** (`PORT_7E` thậm chí **tăng nhẹ lãi và Calmar** trong khi tuyệt đối không bao giờ vượt `1.00%` trên một mã!). Tại P1 Sprint `2.5×`, đặt trần `2.00%`/mã để tránh `E4+E5` chồng thành `2.50%` cùng lúc trên `US100`.

### 3.2. Bẫy `TimeGMT()` trong MT5 Strategy Tester & Đóng cửa sớm ngày lễ Mỹ (`US Half-Days`)
- **Rủi ro:** Trong MT5 Strategy Tester, hàm `TimeGMT()` **trả về giờ Server (`TimeCurrent()`) chứ KHÔNG phải UTC**, khiến mọi lọc phiên UTC/ET bị lệch `2–3` tiếng nếu backtest trực tiếp trên MT5 mà không bù lệch. Ngoài ra, các ngày lễ nửa phiên Mỹ (Thanksgiving, ngày 4/7, đêm Giáng sinh) đóng cửa `US100.cash` lúc `13:00 ET` — sớm hơn mốc đóng bắt buộc `15:55 ET`, dễ khiến EA vô tình giữ lệnh qua đêm/cuối tuần!
- **Đã vá trong `Naqex_PropGuard.mqh`:** Hàm `NowUTC()` tự phát hiện `MQLInfoInteger(MQL_TESTER)` để trừ `InpGuardTesterUtcOffsetH`, và `IsNearBrokerSessionClose()` đọc trực tiếp lịch phiên thực từ sàn qua `SymbolInfoSessionTrade()` để đóng lệnh sớm `10` phút trước giờ đóng cửa thực tế của sàn.

### 3.3. Bẫy `ORDER_FILLING_*` (Lỗi `10030`), `TICK_VALUE_LOSS` và xác nhận `TRADE_RETCODE_DONE`
- **Rủi ro:** FTMO, The5ers và Exness dùng chính sách khớp lệnh khác nhau (`FOK` vs `IOC` vs `RETURN`); dùng cứng một kiểu gây từ chối lệnh `10030`. Đồng thời `SYMBOL_TRADE_TICK_VALUE` trên cặp chéo/chỉ số có thể lệch vài % so với `SYMBOL_TRADE_TICK_VALUE_LOSS` khi tính lot dừng lỗ.
- **Đã vá trong `Naqex_PropGuard.mqh`:** `ConfigureFillingMode()` tự đọc bit cờ `SYMBOL_FILLING_MODE`; `ComputeSafeLots()` ưu tiên `SYMBOL_TRADE_TICK_VALUE_LOSS`; `ExecuteChecked()` kiểm rõ `TRADE_RETCODE_DONE` và mặc định `InpGuardDryRunLogOnly = true`.

### 3.4. Bẫy Windows VPS tự Restart giữa phiên
- **Rủi ro:** Nếu VPS cài bản vá Windows và khởi động lại giữa phiên giao dịch, toàn bộ biến RAM (`g_dayStartEquity`, `g_lastTradedDay`) bị xóa về `0`, làm hỏng cầu chì lỗ ngày hoặc khiến EA vào thêm lệnh thứ 2 trong cùng một ngày.
- **Đã vá trong `Naqex_PropGuard.mqh`:** Lưu và khôi phục trạng thái bền vững qua `GlobalVariableSet/Get` theo khóa `(Magic, Symbol)`.

### 3.5. Lỗ hổng Spec The5ers & Khoảng cách Python ↔ MT5 Thực tế
- **Còn thiếu trước khi nạp tiền The5ers:** Chưa có snapshot `SymbolInfo` thật của máy chủ MT5 The5ers (spread thực `US100`/`EURJPY`/`GBPUSD`, commission chính xác, `stops_level`) và chưa có email xác nhận từ Support The5ers cho EA tự viết theo Terms §11. Kế hoạch lấy miễn phí `0 USD` qua **The5ers Free Monthly Competition** đã ghi tại [THE5ERS-PARALLEL-PROFILE-AND-SPEC-PLAN-20261123.md](THE5ERS-PARALLEL-PROFILE-AND-SPEC-PLAN-20261123.md).
- **Kỷ luật chuyển giao từ Python sang tiền thật:** Tuyệt đối không nhảy thẳng từ Holdout Python sang tài khoản thật. Bắt buộc đi đủ 3 bước: (1) Mở Holdout Python `2025–2026` **đúng 1 lần**; (2) Chạy MT5 Strategy Tester chế độ **"Every tick based on real ticks"** + độ trễ giả lập `150–250 ms` trên FTMO Demo; (3) Chạy forward **FTMO Free Trial `14` ngày** đối chiếu từng lệnh khớp (entry price, spread, slippage, hard flat `swap = 0`).

---

## 4. Cổng Go / No-Go Khóa Trước Khi Mở Holdout `2025–2026` (G0 Preregistration)

Holdout `2025–2026` **HIỆN VẪN ĐANG KHÓA CỨNG (`holdout_rows = 0`)**. Khi owner ra lệnh mở khóa một lần duy nhất trong phiên sau, đánh giá trung thực theo 3 bậc đã khóa sẵn dưới đây (không tinh chỉnh tham số sau khi xem kết quả):

| Mức phán quyết trên Holdout `2025–2026` (M1 Bid/Ask thật) | Điều kiện bắt buộc | Hành động tiếp theo |
|---|---|---|
| **GO (Đủ điều kiện sang MT5 Real-Tick + Free Trial)** | `PORT_7E` & `PORT_9E` đều dương ròng (`Ann >= +4.0%`), `Float Peak DD <= 7.5%`, `Daily DD <= 3.0%`, `Calmar >= 0.70`, `>= 5/7` động cơ cốt lõi không gãy cấu trúc (`> -1.5R`), `0` lỗi margin/swap | Triển khai đồng bộ `Naqex_PropGuard.mqh` vào `8` EA `.mq5` → MT5 Real-Tick + FTMO Free Trial `14` ngày → The5ers Free Competition |
| **CONDITIONAL (Giảm trọng số / chỉ chạy nhóm vững)** | Tổng danh mục dương nhẹ (`+1%..+4%/năm`) hoặc `1–2` động cơ bị gãy chế độ rõ rệt nhưng lõi còn lại vẫn `Calmar >= 0.65` và `DD <= 7.5%` | Không sửa tham số để cứu; chạy forward shadow dài hơn (`30–60` ngày Demo) để thu thập mẫu live mới trước khi vào tiền |
| **NO-GO (Dừng nạp tiền quỹ)** | Danh mục âm ròng trên `2025–2026` hoặc `Float Peak DD > 9.0%` / `Daily DD > 4.0%` | Đóng chiến dịch hiện tại, ghi nhận failure receipt trung thực, không mua Challenge |
