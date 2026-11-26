# Báo Cáo Bước 1 — Nhật Ký Trạng Thái Trước Quyết Định (`v1.01`, Không Đổi Hành Vi) & Đối Khớp Công Thức Python Không Nhìn Trước

- **Ngày chốt:** `26/11/2026` · **Bối cảnh:** Triển khai đúng Bước 1 theo Phán quyết Astra Vòng 4 (`HALTED_AT_PARITY_GATE`, chưa đổi chính sách giao dịch `v1.01`, chưa mở lại mô phỏng kinh tế).
- **Khóa an toàn:** `Holdout 2025+ SEALED` (`holdout_rows_analysed = 0`, `ToDate <= 2024.12.31`, `max_deal_date = 2024-12-30`) · **`0` lệnh gửi tới broker** *(các lệnh `OrderSend` chỉ chạy mô phỏng nội bộ trong MT5 Strategy Tester)* · `naqex-node1` chỉ đọc nguyên vẹn · **quyết định tài chính giữ nguyên `0 VND`**.
- **Nhị phân & mã nguồn đã khóa:** `Naqex_Master_Prop7E.mq5` (`v1.01`, `sha16=19a38eddf51636e5`, mặc định `InpTesterEmitDecisionLog = false`, `InpDryRunLogOnly = true`) · `Naqex_Master_Prop7E.ex5` (`sha16=f395512e39508552`, biên dịch `0 errors, 0 warnings`).

> ## Phán Quyết Bước 1 (`PASS — ĐỦ LOG TỪ TÍN HIỆU ĐẾN EQUITY ĐỂ SANG BƯỚC 2 v1.02-A/B`)
> 1. **Gate A1 — Không có hiệu ứng quan sát (`ON == OFF`):** Bật và tắt `InpTesterEmitDecisionLog` trên cả **`4/4` ca** (`8` lượt chạy `Model=4` Real Ticks) cho ra **`100,00%` khớp tuyệt đối từng deal** (`640/640` deal, thời gian, giá vào/ra, lot, phí, `swap = 0,00`, lãi ròng chênh **`0,00 USD`**, khớp nguyên văn với bản `v1.01` chưa gắn log; các lượt `OFF` tạo đúng `0` tệp CSV).
> 2. **Gate A2 — Công thức Python không nhìn trước (`0` giá hậu-khớp, `0` giá đóng cửa `USDJPY D1` cuối ngày):** Đọc trực tiếp ảnh chụp trạng thái trước quyết định của EA, Python khớp **`100,00%`** trên **`320/320`** lệnh nhận (`INTENT_ACCEPT_FILL`), **`27.351/27.351`** dòng từ chối `INTENT_REJECT_LOT_MIN`, **`114/114`** dòng `LOT_TAPER`, và **`1/1`** `KILL_ACTIVATED`.
> 3. **Gate A3 — Khớp `1:1` deal & đường số dư:** Mọi deal vào lệnh trong báo cáo HTML gốc đều ánh xạ `1:1` với `INTENT_ACCEPT_FILL` (`320/320`), sai lệch số dư trước quyết định tối đa **`0,0000 USD`**, và toàn bộ lệnh đóng khẩn cấp trên `ADV_A` tách bạch sạch chuỗi `LOT_TAPER → KILL_ACTIVATED → CLOSE_REQUEST → CLOSE_FILL`.

---

## 1. Bảng Đối Chứng Ghép Cặp `ON` vs `OFF` & Khớp Công Thức (`4` Ca / `8` Lượt `Model=4`)

Kho bằng chứng gốc lưu tại Layer-2 `private_vault/strategies/step1-predecision-observability-20261126/raw_mt5_logs/` (`44` tệp gốc gồm `.htm`, `.csv.gz`, `.log`, `.set`, `.ini` kèm cả SHA-256 giải nén và nén trong `raw_logs_index.json`).

| Ca kiểm định (`Model=4`, `L1:100`, `0 ms`) | `OFF` vs `ON` (`lệnh` / `lãi USD` / `lệch`) | `Gate A1` (`ON==OFF`) | `Gate A2` (`Accept` / `RejectLotMin` / `Taper` / `Kill`) | `Gate A3` (`1:1 Deal` / `Max ΔBal`) | Các sự kiện từ chối mới phát hiện trong log |
|---|---|---:|---|---|---|
| **`ADV_A_KILL_080`** (`18–20/11/2024`, `kill=0,80%`) | `4` / `-115,06` vs `4` / `-115,06` (`0` lệch) | **PASS** | `4/4` · `0/0` · `4/4` · `1/1` | **PASS** · `0,00 USD` | `LOT_TAPER=4`, `KILL_ACTIVATED=1`, `CLOSE_REQ=3`, `CLOSE_FILL=3` |
| **`ADV_B2_JPY_CAP_080`** (`22–24/10/2024`, `JPY=0,80%`) | `5` / `+216,84` vs `5` / `+216,84` (`0` lệch) | **PASS** | `5/5` · `24.635/24.635` · `3/3` · `0/0` | **PASS** · `0,00 USD` | **`INTENT_REJECT_LOT_MIN = 24.635`** (`0` `REJECT_CAP`!) |
| **`C10_P2_35X`** (`01/09–31/12/2024`, `20,02M` tick) | `156` / `+461,44` vs `156` / `+461,44` (`0` lệch) | **PASS** | `156/156` · `596/596` · `51/51` · `0/0` | **PASS** · `0,00 USD` | **`INTENT_REJECT_LOT_MIN = 596`**, `SPREAD = 9`, `LOT_TAPER = 51` |
| **`C00_P1_4X`** (`01/09–31/12/2024`, `20,02M` tick) | `155` / `+730,55` vs `155` / `+730,55` (`0` lệch) | **PASS** | `155/155` · `2.120/2.120` · `56/56` · `0/0` | **PASS** · `0,00 USD` | **`INTENT_REJECT_LOT_MIN = 2.120`**, `SPREAD = 12`, `NEWS = 22` |

---

## 2. Bốn Bằng Chứng Trực Tiếp Từ Ảnh Chụp Trước Quyết Định (Không Còn Suy Đoán)

1. **Phát hiện lớn chưa từng biết ở `ADV_B2` (`23/10/2024` `E6 EURJPY`):**
   - `E6` **KHÔNG** bị chặn ở dòng `allowedRiskPct <= 0,01` (`ORDER_BLOCKED_FACTOR`) như phỏng đoán trước đây. Do đệm `0,95` và làm tròn lot của `E1 + E2`, hạn mức cụm JPY còn dư đúng **`0,050486% .. 0,054086%`** (`> 0,01%`), nên `E6` lọt qua cổng `L631`, tính ra `raw_lots < 0,01` (`volMin`), rồi **rơi vào lệnh `return;` im lặng tại `Naqex_Master_Prop7E.mq5:653` (`INTENT_REJECT_LOT_MIN:RAW_LOTS_BELOW_VOLMIN`) đúng `24.635` lần** từ `10:00:00` (`server_ts=1729677600`, `signal_price=164,367`) đến `17:59:59` (`1729706399`, `164,883`).
   - Đúng `1` giây sau tại `18:00:00` (`seq=24646`), khi `E1` đóng, `factor_headroom` nhảy từ `0,054086%` lên `0,619717%` và `E6` vào `0,10` lot tại `164,882` (trượt `+51,5` pip so với giá phá vỡ lúc `10:00`).
   - **Điểm mù sống lớn vừa lộ ra:** Dòng `L653` (`lots < volMin`) trước đây **không gọi `LogMasterShadowRow()` ở cả chế độ Live lẫn Tester** — ngay trên 2 lượt chạy thường `4` tháng, `INTENT_REJECT_LOT_MIN` đã xảy ra `596` lần (`C10 P2`) và `2.120` lần (`C00 P1`) hoàn toàn không để lại dấu vết!
2. **Xác nhận dứt điểm nguyên nhân nhảy `ProfitLock` `2,00×` ở `C10 P2` (`02/12/2024 18:30:00`, `seq=69973`):**
   - Ảnh chụp ngay trước khi gửi lệnh `E5 US100.cash` (`deal=247`): `balance = 10.380,28 USD` (`+3,80% >= +3,50%`), **`equity = 10.316,93 USD`** (lỗ thả nổi `-63,35 USD` từ `E7`), **`profit_pct = 3,1693%` (`< 3,50%`)**, `regime = NORMAL`, `risk_mult = 3,5000`, `final_lots = 0,80`. Điều này xác nhận trực tiếp lỗ thả nổi kéo equity xuống dưới `10.350 USD` là nguyên nhân duy nhất khiến EA thoát `PROFIT_LOCK` về `3,50×`.
3. **Xác nhận đối xứng trên đối chứng `C00 P1` (`15/11` & `19/11/2024`):**
   - `15/11` (`seq=6377`, `E4`, `deal=203`): `balance = 10.496,54` (`< 10.500`), **`equity = 10.536,50`** (`profit_pct = 5,3650% >= 5,00%`), `regime = PROFIT_LOCK`, `risk_mult = 2,01`, `final_lots = 0,51`.
   - `19/11` (`seq=6395`, `E4`, `deal=211`): `balance = 10.505,85` (`>= 10.500`), **`equity = 10.411,24`** (`profit_pct = 4,1124% < 5,00%`), `regime = NORMAL`, `risk_mult = 4,00`, `final_lots = 0,83`.
4. **Chuỗi sự kiện tách bạch `LOT_TAPER → KILL_ACTIVATED → CLOSE_REQUEST → CLOSE_FILL` trên `ADV_A` (`18–19/11/2024`):**
   - `LOT_TAPER` ghi riêng cho đủ `4/4` lệnh (`daily_headroom`: `0,80% → scale 0,40 → 1,60×`; `0,5882% → scale 0,2941 → 1,1764×`; `0,0456% → scale 0,25 → 1,00×`).
   - `KILL_ACTIVATED` tại `seq=14042` (`1732041362`, `18:36:02`): `day_anchor_bal = 9.965,14`, `balance = 9.943,76`, `equity = 9.885,14`, `daily_dd_pct = 0,800000%`, `reason = MASTER_KILL_DAILY_DD`.
   - Đóng cả `2` vị thế mở ngay tại `1732041362`: `E4` (`pos=7`, `0,22` lot): `seq=14043 CLOSE_REQUEST → seq=14044 CLOSE_FILL` (`deal=8`, `fill=20.596,95`, `profit=+0,84`, `bal=9.944,60`, `ret=10009`); `E2` (`pos=6`, `0,08` lot): `seq=14045 CLOSE_REQUEST → seq=14046 CLOSE_FILL` (`deal=9`, `fill=154,448`, `profit=-59,66`, `bal=9.884,94`, `ret=10009`).

---

## 3. Trạng Thái `R1/R2` & Ghi Chú Đính Chính Hồ Sơ Vòng 4

- **Nhánh khởi động lại `R1/R2`:** Giữ nguyên nhãn **`chưa kiểm nhánh MQL khi restart` (`SKIPPED_IN_TESTER`)** cho tới khi có bằng chứng chạy qua nhánh `!MQL_TESTER` trong môi trường cô lập.
- **Đã đính chính đủ 3 câu chữ ở [SPRINT-6H-STANDARD-PARITY-AND-C00-VS-C10-AUDIT-20261126.md](SPRINT-6H-STANDARD-PARITY-AND-C00-VS-C10-AUDIT-20261126.md):** ghi rõ `0` lệnh gửi tới broker, bỏ ước lượng `~28.800 lần` ở `ADV_B2`, làm rõ `1725364801350` là fixture giả lập cơ chế, ghi đúng dải **tháng `9–12/2024`** và làm rõ `Jaccard` đo trên tập ngày có deal.

---

## 4. Prompt Sẵn Dán Gửi GPT-6.2 Astra (Vòng 5 — Duyệt Bước 1 & Mở Khóa Bước 2 `v1.02-A` / `v1.02-B`)

```text
Xin Astra kiểm toán Bước 1 (bật log trạng thái trước quyết định trên bản giữ nguyên 100% hành vi v1.01 + kiểm khớp Python không nhìn trước + đính chính 3 câu chữ hồ sơ Vòng 4) trước khi chúng tôi triển khai tách từng thay đổi v1.02-A (ProfitLock balance + MathMin) và v1.02-B (mã cơ hội ổn định + hết hiệu lực theo setup):

1) AN TOÀN & ĐÍNH CHÍNH:
- Holdout 2025+ SEALED (holdout_rows_analysed=0, ToDate<=2024.12.31), 0 lệnh gửi tới broker (OrderSend chỉ mô phỏng nội bộ trong MT5 Tester), naqex-node1 chỉ đọc nguyên vẹn, 0 VND.
- Đã đính chính đủ 3 chỗ trong SPRINT-6H-STANDARD-PARITY-AND-C00-VS-C10-AUDIT-20261126.md (0 lệnh gửi tới broker; bỏ ước lượng ~28.800 lần; làm rõ 1725364801350 là fixture cơ chế; gọi đúng dải tháng 9–12/2024 và làm rõ Jaccard đo trên tập ngày có deal).
- R1/R2 vẫn giữ nguyên nhãn: chưa kiểm nhánh MQL khi restart (SKIPPED_IN_TESTER).

2) KẾT QUẢ BƯỚC 1 (`step1_predecision_parity_report.json` + 44 tệp log thô có SHA-256 trong `private_vault/strategies/step1-predecision-observability-20261126/raw_mt5_logs/`):
- Gate A1 (Bật vs Tắt log trên v1.01, 4 ca / 8 lượt Model=4): ON == OFF KHỚP 100% TỪNG DEAL & LOT (640/640 deal, 0 lệch, 0,00 USD chênh, swap=0,00, khớp nguyên văn bản v1.01 chưa gắn log: ADV_A -115,06; ADV_B2 +216,84; C10 P2 +461,44; C00 P1 +730,55 USD). Lượt OFF xuất đúng 0 tệp CSV.
- Gate A2 (Python đọc trực tiếp ảnh chụp trước quyết định — bỏ giá hậu-khớp & giá đóng USDJPY D1):
  * INTENT_ACCEPT_FILL: 320/320 KHỚP 100,00% (4/4 ADV_A, 5/5 ADV_B2, 156/156 C10 P2, 155/155 C00 P1).
  * INTENT_REJECT_LOT_MIN: 27.351/27.351 KHỚP 100,00% (24.635 ADV_B2, 596 C10 P2, 2.120 C00 P1).
  * LOT_TAPER: 114/114 KHỚP 100,00% (4 ADV_A, 3 ADV_B2, 51 C10 P2, 56 C00 P1).
  * KILL_ACTIVATED: 1/1 KHỚP 100,00% (ADV_A seq=14042, 18:36:02, daily_dd=0,800000%).
- Gate A3 (1:1 deal & số dư): 320/320 deal vào khớp 1:1 với INTENT_ACCEPT_FILL, max_balance_diff = 0,0000 USD; ADV_A ghi tách bạch đủ chuỗi LOT_TAPER -> KILL_ACTIVATED -> CLOSE_REQUEST -> CLOSE_FILL cho cả E4 (deal 8, +0,84) và E2 (deal 9, -59,66).

3) BẰNG CHỨNG MỚI RÚT RA TỪ LOG TRƯỚC QUYẾT ĐỊNH:
- C10 P2 02/12 18:30 (seq=69973, E5): balance=10.380,28, equity=10.316,93 (lỗ nổi -63,35 từ E7), profit_pct=3,1693% (<3,50%) -> NORMAL 3,50x -> 0,80 lot. Xác nhận lỗ nổi là nguyên nhân duy nhất.
- C00 P1 15/11 (seq=6377): bal=10.496,54, eq=10.536,50 (5,365%) -> PROFIT_LOCK 2,01x (0,51 lot); 19/11 (seq=6395): bal=10.505,85, eq=10.411,24 (4,112%) -> NORMAL 4,00x (0,83 lot).
- PHÁT HIỆN MỚI Ở ADV_B2 (23/10 E6): E6 KHÔNG bị chặn ở dòng allowedRiskPct<=0,01 (ORDER_BLOCKED_FACTOR) mà do hạn mức cụm JPY còn dư 0,0505%..0,0541% (>0,01%) khiến raw_lots < volMin (0,01) và rơi vào nhánh thoát im `if(lots < volMin) return;` tại L653 đúng 24.635 lần (10:00:00 -> 17:59:59) rồi vào 0,10 lot lúc 18:00:00 (giá 164,882 vs 164,367 lúc 10:00). L653 cũng đã im lặng 596 lần ở C10 P2 & 2.120 lần ở C00 P1 (trước đây tàng hình cả ở Live lẫn Tester!).

CÂU HỎI CHO ASTRA VÒNG 5:
1. Bước 1 (zero observer effect + 100% đối khớp công thức từ ảnh chụp trước quyết định) đã đạt chuẩn để chuyển sang Bước 2 (thử riêng v1.02-A ProfitLock balance+MathMin, rồi v1.02-B mã cơ hội ổn định + ghi nhận L653 `INTENT_REJECT_LOT_MIN` cả ở Live) chưa?
2. Trước khi viết v1.02-B cho E6 (và các nhánh khác khi rơi vào L653/L631), Astra có lưu ý gì thêm về cách định nghĩa "hết hiệu lực theo cơ hội" (nhất là với phát hiện L653 residual headroom < volMin) và bước kiểm Python tự dựng lại trạng thái từ chuỗi giá?
```
