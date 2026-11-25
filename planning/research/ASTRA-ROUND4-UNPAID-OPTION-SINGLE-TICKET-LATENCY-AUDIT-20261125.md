# Phán quyết Astra Vòng 4 (`UNPAID-OPTION — 0 USD`) & Kiểm định 1 Vé Không Retry + Độ Trễ Thực Đo (`v1.01`)

- **Ngày thực hiện:** `2026-11-25` (sau khi nhận phán quyết Astra Round 4).
- **Quyết định chính thức:** **`UNPAID-OPTION — 0 USD`** — giữ nguyên `Naqex_Master_Prop7E v1.01` (`sha16=2e0006ad786bdad6`) để tiếp tục kiểm chứng ngoại tuyến và **để ưu đãi FTMO Black Friday (`Thứ Hai 30/11/2026 16:00 ICT`) đi qua** (ghi nhận thêm điều kiện tham gia [đủ 18 tuổi của FTMO](https://ftmo.com/en/faq/who-can-join-ftmo/) để chủ sở hữu tự đối chiếu trước mọi kế hoạch tài khoản thật trong tương lai).
- **Ranh giới an toàn:** Dữ liệu phát triển kín `2018-01-02 .. 2024-12-31`, **`Holdout 2025+` NIÊM PHONG (`holdout_rows_analysed = 0`)**, `OrderSend = 0`, máy chủ sản xuất `naqex-node1` nguyên vẹn, Dev MT5 `0%` CPU sau chạy.
- **Tài liệu gốc thay thế kết luận cũ:** Cập nhật bổ sung cho [ASTRA-ROUND4-BLACKFRIDAY-GONOGO-DOSSIER-20261126.md](ASTRA-ROUND4-BLACKFRIDAY-GONOGO-DOSSIER-20261126.md) (bảng cũ tại mục 4 là mô phỏng nhiều lần mua lại `multi-retry`, không phải bài toán 1 vé duy nhất).

---

## 1. Ba con số cốt lõi cho bài toán ĐÚNG 1 VÉ — KHÔNG RETRY (`v1.01 REL+HEADROOM`)

Chạy trên `N = 10.000` đường bootstrap khối lịch thật (`block_len = 7`, `SEED = 20261125`, chân trời `1.095` ngày lịch = `36 tháng`, biên nhận Layer-2: `private_vault/strategies/wave2-overnight-rd-20261125/single_ticket_v101_audit/single_ticket_v101_summary.json`). **Quy tắc cứng:** mua đúng **1 vé** vào ngày 0 (`max_attempts = 1`, `retries = 0`); nếu vi phạm Daily DD hoặc Static DD ở P1, P2 hay Funded thì **dừng vĩnh viễn** (mất đúng 1 lần phí).

### 1A. Chế độ mặc định `GUARD_ALL_ON` (bật tin đỏ ở P1/P2/Funded) — `P1 Sprint 4x -> P2 2x -> Funded 1x`

So sánh ở **giá thường không khuyến mãi `155 EUR` (`165,08 USD` @ `1,065`)** và **giá Black Friday `98,70 EUR` (`105,12 USD`)**:

| Hệ số ma sát | `P(Payout 1)` 12m / 24m / 36m | Rơi ở P1 / P2 / Funded-trước-P1 | Ngày lịch chờ Payout 1 (24m: P25 / **P50** / P75 / P90; tách P1+P2+Fn) | Ròng 1 vé chỉ tới Payout 1 (24m, phí 155 EUR: Mean / Med) | Ròng 1 vé sống tiếp 12m (phí 155 EUR: Mean / Med) | **Ròng 1 vé sống tiếp 24m — Phí 155 EUR (Mean / Med / `P<=0`)** | **Ròng 1 vé 24m — Phí 98,70 EUR (Mean / Med)** |
|---|---:|---:|---|---:|---:|---:|---:|
| **`0,66x`** *(đo sống)* | `59,9%` / **`84,7%`** / `88,6%` | `9,1%` / `1,1%` / `0,0%` | `187` / **`273`** / `391` / `530` ngày (`112+87+25`) | `+59,6` / `+72,5 USD` | `+197,9` / `+146,2 USD` | **`+825,7` / `+815,9 USD` (`15,3%`)** | `+834,8` / `+815,9 USD` |
| **`0,75x`** | `56,7%` / **`81,7%`** / `86,5%` | `10,6%` / `1,3%` / `0,0%` | `192` / **`279`** / `400` / `535` ngày (`116+89+25`) | `+51,7` / `+71,0 USD` | `+167,3` / `+108,5 USD` | **`+744,2` / `+732,0 USD` (`18,3%`)** | `+755,1` / `+732,0 USD` |
| **`1,00x`** *(chuẩn Dev)* | `46,6%` / **`73,0%`** / `79,2%` | `15,4%` / `2,6%` / `0,0%` | `207` / **`300`** / `432` / `565` ngày (`124+96+26`) | `+26,7` / `+65,6 USD` | `+88,4` / `-165,1 USD` | **`+535,5` / `+490,5 USD` (`27,0%`)** | `+551,7` / `+490,5 USD` |
| **`1,25x`** | `37,8%` / **`62,6%`** / `69,8%` | `21,3%` / `4,7%` / `0,0%` | `216` / **`316`** / `455` / `584` ngày (`132+105+27`) | `-1,4` / `+58,3 USD` | `+26,2` / `-165,1 USD` | **`+363,8` / `+266,9 USD` (`37,4%`)** | `+386,2` / `+266,9 USD` |
| **`1,50x`** *(stress Astra)* | `29,3%` / **`51,2%`** / `58,3%` | `28,3%` / `7,1%` / `0,1%` | `224` / **`329`** / `472` / `597` ngày (`139+110+28`) | `-32,0` / `+50,5 USD` | `-25,5` / `-165,1 USD` | **`+216,3` / `+62,4 USD` (`48,8%`)** | `+245,5` / `+62,4 USD` |
| **`1,75x`** | `22,1%` / **`40,1%`** / `46,6%` | `36,2%` / `9,1%` / `0,2%` | `231` / **`339`** / `477` / `605` ngày (`143+112+30`) | `-61,5` / `-165,1 USD` | `-65,6` / `-165,1 USD` | **`+101,7` / `-165,1 USD` (`59,9%`)** | `+137,7` / `-105,1 USD` |
| **`2,00x`** *(đuôi nặng)* | `16,4%` / **`30,3%`** / `35,1%` | `44,9%` / `11,7%` / `0,4%` | `232` / **`342`** / `488` / `613` ngày (`146+111+30`) | `-86,9` / `-165,1 USD` | `-95,3` / `-165,1 USD` | **`+16,9` / `-165,1 USD` (`69,7%`)** | `+58,7` / `-105,1 USD` |

### 1B. Đối chiếu nhanh `P1 Balanced 3x` và `RULE_EXACT` (phí chuẩn `155 EUR = 165,08 USD`, 24 tháng)

| Cấu hình | Ma sát `0,66x` (`P(Pay1)` / Chờ P50 / Net Med) | Ma sát `1,00x` (`P(Pay1)` / Chờ P50 / Net Med) | Ma sát `1,50x` (`P(Pay1)` / Chờ P50 / Net Med / `P<=0`) |
|---|---|---|---|
| `GUARD_ALL_ON` · `P1_Sprint_4x` | `84,7%` / `273d` / `+815,9 USD` | `73,0%` / `300d` / `+490,5 USD` | `51,2%` / `329d` / `+62,4 USD` (`48,8%`) |
| `GUARD_ALL_ON` · `P1_Balanced_3x` | `85,7%` / `313,5d` / `+752,0 USD` | `73,6%` / `344d` / `+442,5 USD` | `49,9%` / `379d` / `-165,1 USD` (`50,1%`) |
| `RULE_EXACT` · `P1_Sprint_4x` | `84,9%` / `262d` / `+853,2 USD` | `74,4%` / `288d` / `+520,9 USD` | `53,9%` / `319d` / `+101,1 USD` (`46,1%`) |
| `RULE_EXACT` · `P1_Balanced_3x` | `86,9%` / `299d` / `+793,2 USD` | `76,1%` / `334d` / `+480,1 USD` | `53,7%` / `368d` / `+90,8 USD` (`46,3%`) |

### 1C. Ba kết luận kinh tế rút ra trực tiếp từ bảng 1 vé

1. **Multi-retry từng che giấu rủi ro của vé đầu tiên:** Ở ma sát `1,50x`, bảng multi-retry cũ báo `Pass24 = 78,2%`, nhưng khi chỉ mua đúng **1 vé và dừng hẳn nếu trượt**, xác suất nhận được payout đầu trong 24 tháng tụt xuống còn **`51,2%`** (chỉ **`29,3%`** trong 12 tháng), trung vị tiền ròng 24 tháng chỉ còn **`+62,4 USD`** (`48,8%` trường hợp hòa/lỗ trọn phí).
2. **Độ trễ dòng tiền 9–12,5 tháng chưa phù hợp mục tiêu thu nhập chính:** Ngay cả ở ma sát đo sống `0,66x`, trung vị phải chờ tới payout đầu vẫn là **`273 ngày` (~9 tháng)** (`300 ngày` ở `1,00x`, `329 ngày` ở `1,50x`); ở mốc **12 tháng**, trung vị tiền ròng của 1 vé vẫn âm (`-165,1 USD`) từ mức `1,00x` trở lên. Riêng khoản payout đầu tiên (chỉ 1 chu kỳ Funded 14 ngày) chỉ mang lại phần lãi chia trung vị **`~78–81 USD`** + hoàn phí, nên EV của riêng cột mốc `Pay1Only` chuyển âm ngay từ mức ma sát `1,25x` (`-1,4 USD`).
3. **Ưu đãi Black Friday không đáng để vội vàng:** Vì FTMO hoàn `100%` phí ở payout đầu tiên, toàn bộ người thắng có **trung vị lãi giống hệt nhau** giữa `155 EUR` và `98,70 EUR`. Giảm giá `~60 USD` chỉ tiết kiệm được trên các đường thua, tương đương chênh lệch EV vẻn vẹn **`+9,1 USD` (ở `0,66x`) tới `+29,2 USD` (ở `1,50x`)** — quá nhỏ để đổi lấy việc đi trước khi khép kín kiểm chứng.

---

## 2. Kiểm thử MT5 `Naqex_Master_Prop7E.ex5 v1.01` ở độ trễ thực đo (`500 ms` / `655 ms`) & Full-2024

Biên nhận gốc: `.runtime/mt5-realtick-results/v101_measured_latency_and_full2024_summary.json` (tất cả chạy trên `FTMO-Demo` portable, `1:100`, `492` tin đỏ nạp đủ, `swap = 0,00 USD`, `clean = True`, `0` lỗi, `holdout_rows_analysed = 0`).

| Kịch bản (`v1.01`, `sha16=2e0006ad786bdad6`) | Cửa sổ Dev (`<= 2024-12-31`) | Model & Tick | Độ trễ MT5 | Số lệnh (Win%) | Lãi ròng (`USD`) | PF | Sharpe | Bal DD / Eq DD | Worst Day (`USD`) | Quý dương & Cột mốc |
|---|---|---|---|---:|---:|---:|---:|---|---|---|
| Baseline cũ: `V101_2024Q4_P1_4X_50ms` | `2024.09.01–12.31` | `Model=4` (`20,02M` real ticks) | `50 ms` | `155` (`52,90%`) | **`+736,06`** | `1,23` | `1,98` | `4,92%` / `6,27%` | `-169,80` (`10-25`) | `PROFIT_LOCK` `11-15` |
| **Mới #1: `V101_2024Q4_P1_4X_500ms`** | `2024.09.01–12.31` | `Model=4` (`20,02M` real ticks) | **`500 ms` (P50 đo)** | `155` (`53,55%`) | **`+790,52`** | `1,25` | `2,13` | `4,90%` / `6,24%` | `-172,40` (`10-25`) | `Q4 +874,43` |
| **Mới #2: `V101_2024Q4_P1_4X_655ms`** | `2024.09.01–12.31` | `Model=4` (`20,02M` real ticks) | **`655 ms` (P90 đo)** | `155` (`53,55%`) | **`+799,56`** | `1,25` | `2,15` | `4,83%` / `6,17%` | `-172,15` (`10-25`) | `Q4 +876,87` |
| **Mới #3: `V101_FULL2024_FUNDED_1X_500ms`** | `2024.01.02–12.31` | `Model=1` (`1,46M` 1m-OHLC) | **`500 ms` (P50 đo)** | `469` (`50,75%`) | **`+613,64`** | `1,15` | `1,21` | `3,42%` / `4,06%` | `-148,12` (`05-31`) | **`4/4` quý dương** (`minBal 9.960,39`) |
| **Mới #4: `V101_FULL2024_P1_4X_500ms`** | `2024.01.02–12.31` | `Model=1` (`1,46M` 1m-OHLC) | **`500 ms` (P50 đo)** | `470` (`50,43%`) | **`+1.418,65`** | `1,15` | `1,26` | `8,00%` / `8,75%` | `-314,00` (`08-05`) | **`4/4` quý dương**; **đạt `+10%` ngày `2024-05-15`** (`134` ngày) |

### Đánh giá thẳng thắn các giới hạn còn lại

1. **Độ trễ `500–655 ms` không làm hỏng cấu trúc `7E` trong MT5 Real-Tick:** Cả `500 ms` lẫn `655 ms` giữ nguyên `155` lệnh trên `20,02 triệu` tick thực, `swap = 0,00 USD`, không suy giảm lợi nhuận (chênh `+54..+63 USD` là nhiễu lấy mẫu mở nến M5/M15, **không** xem là lợi thế). Bản `v1.01` Full-2024 `4,0x` tại `500 ms` đi qua cú sụp Yen Carry Trade `05/08/2024` với ngày tệ nhất `-3,14%` (`< -5%`), `minBal 9.595,79 USD`, và đạt mục tiêu P1 `+10%` ngày `15/05/2024` (`134` ngày lịch — khớp sát trung vị P1 `124–139` ngày của mô phỏng 1 vé).
2. **Phần đuôi sống vẫn chưa đủ dày:** MT5 `ExecutionMode` chỉ lùi khớp lệnh theo lịch sử tick chứ không mô phỏng trượt giá tác động thị trường khi thanh khoản mỏng; và `2` lần chạm SL sống trên `US100.cash` chưa đủ để kết luận `450 points` là trần trượt tối đa. Muốn khép điểm mù này cần thêm đo đạc đa phiên/đa tuần trên Demo (`0 USD`) thay vì mua vé vội.
3. **Điều kiện pháp lý & định hướng tiếp theo:** Giữ khóa **`0 USD`** với FTMO; tiếp tục theo dõi shadow `naqex-node1`, xác minh điều kiện tuổi/pháp lý trước khi mở bất kỳ tài khoản trả phí nào, và nghiên cứu rút ngắn thời gian chờ / tăng tỷ lệ thắng vé đầu tiên (hoặc nguồn thu song song ổn định hơn) trên Dev trước khi cân nhắc mở `Holdout 2025+`.
