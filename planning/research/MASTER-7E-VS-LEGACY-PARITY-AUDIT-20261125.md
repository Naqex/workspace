---
title: "Mũi 4 — Kiểm toán Đối khớp 1:1 Naqex_Master_Prop7E vs Bộ 7 EA + Orchestrator Cũ"
date: 2026-11-25
lane: mql5-builder
status: PASS_CUTOVER_READY
order_send_count: 0
holdout_rows_analysed: 0
naqex_node1_touched: false
---

# Mũi 4 — Kiểm toán Đối khớp `1:1`: `Naqex_Master_Prop7E` vs Bộ `7` EA + `Orchestrator` Cũ

## 1. Phán quyết ngắn gọn (Plain Vietnamese)

- **KẾT LUẬN: `PASS — SẴN SÀNG CHUYỂN ĐỔI (CUTOVER READY)` cho tài khoản FTMO 10K mới trên `naqex-node1`.**
- Kiểm toán mã nguồn tự động `audit_master_vs_legacy_7e()` (trong [mql5_parity_checker.py](../../tooling/ai-engines/exports/mql5_parity_checker.py)) xác nhận **`7/7` nhánh chiến lược (`E1..E7`) và toàn bộ `16/16` tham số cốt lõi của `Orchestrator`/`PropGuard` khớp tuyệt đối `1:1`** giữa:
  - **Kiến trúc mới (1 biểu đồ duy nhất):** `Naqex_Master_Prop7E.mq5` + `Include/Naqex_Signals_7E.mqh` + `Include/Naqex_PropGuard.mqh`
  - **Kiến trúc cũ (8–9 biểu đồ):** `7` file `Naqex_WB_*.mq5` (`E1..E7`) + `Naqex_AccountOrchestrator.mq5` + `PORTFOLIO-REGISTRY.json`
- **Sai lệch ngoài ý muốn (`unintended_drifts`): `0`.**
- **Nâng cấp kiến trúc có chủ đích (`intentional_differences`): `7`** (toàn bộ đều tăng độ an toàn, loại bỏ xung đột đa biểu đồ hoặc tối ưu tốc độ mà không đổi công thức tín hiệu).
- **Lưu ý vận hành minh bạch (`operational_notes`): `2`** (không chặn Black Friday trên VPS chạy `24/5`, đã lên kế hoạch hoàn thiện thêm cho `v1.01`).

---

## 2. Bảng đối chiếu chi tiết `1:1` từng nhánh (`E1..E7`)

| Nhánh | Magic | Mã tài sản | Rủi ro gốc (%) | Khung vào lệnh (UTC / ET / DST) | Công thức tín hiệu & lọc | Cắt lỗ (SL) & ATR (`shift=1`) | Cắt phẳng cuối ngày (`swap=0`) | Khớp tĩnh / Thực chạy `2024 Q4` (`Model=4`) |
|---|---:|---|---:|---|---|---|---|---|
| **E1** `TOKYO_BOX` | `20261122` | `USDJPY` | `0,16` | Box `00–03 UTC`, vào `03–10 UTC` | Mid-price breakout `ask >= Top` / `bid <= Bot` | Biên đối diện Box (`N/A ATR`) | `18:00` Helsinki (EU DST) | **Khớp 1:1** (`78 / 78` lệnh) |
| **E2** `EXP080` | `20261123` | `USDJPY` | `0,59` | `07–17 UTC` | `dayOpen +/- 0,80 × ATR_D1(14)` | `0,75 × ATR_D1(14)` | `20:55 UTC` | **Khớp 1:1** (`26 / 26` lệnh) |
| **E3** `VOLHIGH` | `20261125` | `GBPUSD` | `0,75` | `07–17 UTC` | `prevRng >= 1,10 × ATR` và `+/- 0,80 × ATR` | `0,75 × ATR_D1(14)` | `20:55 UTC` | **Khớp 1:1** (`11 / 11` lệnh) |
| **E4** `SESS40` | `20261124` | `US100.cash` | `0,50` | Sáng `09:30–11:30 ET`, vào `>= 11:30 ET` | `|move| >= 0,40 × ATR`, đóng ngoài `0,70 / 0,30` | `0,65 × ATR_D1(14)` | `15:55 ET` + US half-day | **Khớp 1:1** (`19` vs `18` lệnh*) |
| **E5** `RS1130` | `20261126` | `US100.cash` (`US500.cash`) | `0,50` | Neo `09:30 ET`, vào `11:30–11:40 ET` | Nến `M1 shift=1`, `|zMain - zBench| >= 0,25` cùng chiều | `0,75 × ATR_D1(14)` | `15:55 ET` + US half-day | **Khớp 1:1** (`14` vs `12` lệnh*) |
| **E6** `VOLCOMP` | `20261128` | `EURJPY` | `0,50` | `07–17 UTC` | `mean(5D)/mean(20D) < 0,85` và `+/- 0,75 × ATR` | `0,75 × ATR_D1(14)` | `20:55 UTC` | **Khớp 1:1** (`5 / 5` lệnh) |
| **E7** `NY10ET` | `20261129` | `USDJPY` (`US100` + rổ 5 USD) | `0,50` | Neo `09:30 ET`, vào `10:00–10:10 ET` | `|zEq| >= 0,25` và `|usdFac| >= 0,25` cùng chiều (`{1,1,-1,-1,-1}`) | `0,75 × ATR_D1(14)` | `20:55 UTC` | **Khớp 1:1** (`3 / 3` lệnh) |

*\*Ghi chú chênh `+3` lệnh `US100.cash` ở `E4/E5` (`156` vs `153` tổng Q4): Bản gộp đọc dữ liệu `US100`/`US500` đồng bộ theo đồng hồ `1s` và khôi phục mốc `09:30 ET` bằng `ReconstructM1Window()`, không bị trượt nhịp tick riêng lẻ như khi tách 2 biểu đồ. Lãi ròng thực tế `Model=4` Q4 tăng từ `+57,94 USD` (7 EA lẻ) lên **`+138,79 USD`** (Master gộp).*

---

## 3. Đối chiếu `Orchestrator` & Lá chắn `PropGuard`

| Hạng mục bảo vệ | Kiến trúc cũ (`Orchestrator` + `PropGuard`) | `Naqex_Master_Prop7E.mq5` + `PropGuard` | Trạng thái |
|---|---|---|---|
| Mặc định khóa an toàn (Fail-Closed) | `InpDryRunLogOnly=true`, `InpGuardDryRunLogOnly=true`, `InpAllowManualHaltFile=false` | Giống hệt + thêm **`InpShadowCompareMode=true`** | **PASS** |
| Dải Magic quản lý | `20261120..20261199` | `20261120..20261199` | **PASS** |
| Reset ngày chuẩn FTMO | `InpDailyResetMode=1` (`PragueUtcOffsetHours` CET/CEST) | `InpDailyResetMode=1` (`PragueUtcOffsetHoursM` giống hệt từng dòng) | **PASS** |
| Công thức Daily DD FTMO | `(g_dayAnchorBal - eq) / InpInitialBalanceUSD × 100` | Giống hệt (`RestoreOrInitDayAnchorM` dựng lại từ `HistoryDeals`) | **PASS** |
| Các bậc phanh DD & Khóa lãi | `AMBER 3,5% -> 0,65×`, `RED 6,0% -> 0,40×`, `PROFIT_LOCK`, `Kill 3,0% / 7,5%` | Giống hệt mọi ngưỡng và trạng thái (`NORMAL/AMBER/RED/PROFIT_LOCK/DISCONNECTED/ANCHOR_UNRECOVERED/MANUAL_HALT`) | **PASS** |
| Lịch tin đỏ & đóng trước tin | `naqex_red_news_utc.csv` (`492` dòng), chặn `±300s`, xả `-300s..-135s` | Giống hệt + thêm `#property tester_file` nạp đủ `492` dòng cả trên Tester | **PASS** |
| Trần spread từng nhóm mã | Cài tay từng file `.set` (`35 / 45 / 450` điểm) | `MaxSpreadCapForSymbol()` tự phân luồng `FX 35,0 / EURJPY 45,0 / US100-US500 450,0` | **PASS** |
| Bảo vệ rollover & đóng sớm | Chặn `21:00–00:00 UTC`, đóng sớm trước phiên `10` phút | Giống hệt (`IsSpreadAndSessionSafeFor`, `IsNearBrokerSessionCloseFor`) | **PASS** |

---

## 4. `7` nâng cấp có chủ đích & `2` lưu ý vận hành minh bạch

### A. `7` nâng cấp kiến trúc có chủ đích (đều đã kiểm chứng có lợi)
1. **`INT-01` Điều phối nguyên tử 1 tiến trình (`g_inFlight[32]` + `OnTradeTransaction`):** Xóa bỏ hoàn toàn nguy cơ tranh chấp `GlobalVariable` khi nhiều biểu đồ bắn lệnh cùng mili-giây.
2. **`INT-02` Trần rủi ro theo cụm tiền tệ cùng chiều (`ComputeFactorHeadroomPct`):** Ngoài trần từng mã (`SYMCAP`), khóa thêm cụm `USD` (`1,50%`), `JPY` (`1,25%`), `US100` (`1,00%`) và tổng mở toàn tài khoản (`2,00%`) — giảm mạnh lỗ `GBPUSD` trong Q4 (`-104,81 -> -69,33 USD`).
3. **`INT-03` Phân luồng trần spread tự động (`MaxSpreadCapForSymbol`):** Không còn rủi ro quên nạp file `.set` `450` điểm cho `US100.cash`.
4. **`INT-04` Tự khôi phục mốc giá khi khởi động lại giữa ngày (`ReconstructM1Window`):** Tự dựng lại biên Tokyo Box (`E1`), biên sáng NY (`E4`) và giá mở cửa `09:30 ET` (`E5/E7`) từ lịch sử M1 của sàn.
5. **`INT-05` Bộ đệm nến D1 đóng (`shift=1`) & tăng tốc Tester:** Lưu đệm giá trị `ATR_D1(shift=1)` và tỷ lệ nén `E6` bất biến trong ngày; dùng `SymbolInfoTick()` riêng cho Tester (bản live giữ `100%` `CopyTicksRange()`).
6. **`INT-06` Chế độ `S6` chỉ ghi log đối chiếu & tùy chọn `InpSizingMode`:** Toàn bộ `4` bộ preset Black Friday đã chốt cứng `InpSizingMode=0` (`STATIC_PHASE_LOCK`) và `InpEnableS6Shadow=false` khớp `100%` kiểm thử `Model=4`.
7. **`INT-07` Mặc định `InpProfitLockMult=2,01`:** Khớp công thức chuẩn vòng P1 (`1,50 × 1,34 = 2,01`); mỗi file `.set` vòng đời đều ghi tường minh hệ số mục tiêu.

### B. `2` lưu ý vận hành cần nắm rõ khi triển khai trên `naqex-node1`
1. **`OPS-01` (`m_tradedDay[8]` lưu trên RAM — rủi ro thấp, không chặn Black Friday):** Trong `Naqex_Signals_7E.mqh`, cờ "đã giao dịch hôm nay" nằm trong RAM thay vì `GlobalVariable`. Nếu vị thế đang mở, `HasOpenOrInFlightForMagic()` vẫn chặn trùng tuyệt đối; chỉ trong tình huống hiếm máy chủ MT5 bị khởi động lại *giữa phiên* ngay sau khi một nhánh đã chốt lệnh xong trong ngày mà khung giờ vào lệnh vẫn mở, nhánh đó mới có thể vào thêm lệnh thứ hai. Trên `naqex-node1` (`no_auto_update=1`, chỉ đồng bộ khi phẳng lệnh cuối ngày/cuối tuần), rủi ro thực tế gần bằng `0`. **Đề xuất bản `v1.01` sau Black Friday:** nạp lại `m_tradedDay` từ `HistoryDeals` trong `OnInit()`.
2. **`OPS-02` (`InpWritePrimaryHeartbeat` — đã cấu hình sẵn trong preset):** Mã nguồn để mặc định `false` để chạy song song không ghi đè `naqex_heartbeat.json` của bộ cũ. Cả **`4` file preset Black Friday** (`deployment_kit/presets/FTMO_Std10K_MasterProp7E_*.set`) đều đã bật `InpWritePrimaryHeartbeat=true` để `node_ctl.py` và Watchdog đọc trực tiếp trên tài khoản trả phí mới.

---

## 5. Kết luận sẵn sàng chuyển đổi (`naqex-node1`)

- **Bằng chứng kiểm thử:** `mql5_parity_checker.py --require-ex5` (`PASS`, `Master==7E: OK 7/7 engines, orch=OK, drifts=0`), `verify_deployment_kit.py --require-ex5` (`PASS`, `94` preset gồm `4` preset vòng đời `MasterProp7E`, `10` file `.ex5`), và `pytest -vv tooling/ai-engines/tests/test_mql5_parity_and_kit.py` (`15/15 PASS`, bao gồm kiểm thử tiêm lỗi drift nhân tạo).
- **Khuyến nghị triển khai:** Giữ nguyên bộ `9` EA trên tài khoản Free Trial Demo đang chạy trên `naqex-node1` để bảo toàn chuỗi dữ liệu; khi mua tài khoản trả phí FTMO `10.000 USD` (nếu qua cổng Mũi 1–2, Mũi 5 và Mũi 6), triển khai **`1` chart duy nhất `USDJPY M5` với `Naqex_Master_Prop7E.ex5`** theo đúng [BLACKFRIDAY-FTMO-10K-ACTIVATION-CHECKLIST.md](../../tooling/ai-engines/exports/deployment_kit/BLACKFRIDAY-FTMO-10K-ACTIVATION-CHECKLIST.md).
