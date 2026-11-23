# Protocol G0 — Mở khóa Holdout `2025–2026` Một Lần Duy Nhất (`ONE-TIME BLIND EVALUATION`)

- **Thời điểm niêm phong protocol (TRƯỚC khi tải bất kỳ nến `2025–2026` nào):** `23/11/2026`
- **Ủy quyền của owner:** Owner đã phê duyệt rõ lộ trình mở Holdout `2025–2026` một lần duy nhất sau khi hoàn tất [Kiểm toán điểm mù Pre-Holdout](PRE-HOLDOUT-READINESS-AND-BLINDSPOT-AUDIT-20261123.md).
- **Trạng thái kho Development gốc:** `.runtime/hot-m1-cache/` (`2018–2024`) và [NATIVE_FTMO_HOLDOUT_LOCK.json](NATIVE_FTMO_HOLDOUT_LOCK.json) giữ **nguyên vẹn bất biến**; dữ liệu Holdout M1 Bid/Ask (`2025-01-01` → `2026-11-20` UTC) được tải và niêm phong vào kho riêng `.runtime/holdout-m1-cache/`.

---

## 1. Danh mục & tham số ĐÓNG BĂNG 100% (cấm chỉnh sau khi xem kết quả)

Nguồn sự thật duy nhất: [PORTFOLIO-REGISTRY.json](PORTFOLIO-REGISTRY.json) (`9` động cơ, `swap = 0`, `M = 1` không còn tối ưu lại):

1. `E1_USDJPY_TOKYO` (`0.1606%`, `USDJPY` Tokyo Box `00:00–03:00` → `03:00–10:00 UTC`, flat `18:00 Europe/Helsinki`)
2. `E2_USDJPY_EXP80` (`0.5894%`, `USDJPY` Daily Open Exp `0.80 ATR`, SL `0.75 ATR`, `07:00–17:00 UTC`, flat `20:55 UTC`)
3. `E3_GBPUSD_VH` (`0.7500%`, `GBPUSD` Exp `0.80 ATR`, SL `0.75 ATR`, `prev_range/ATR >= 1.10`, `07:00–17:00 UTC`, flat `20:55 UTC`)
4. `E4_US100_SESS40` (`0.5000%`, `US100` NYSE Morning Cont `>= 0.40 ATR`, close in top/bot `30%`, SL `0.65 ATR`, flat `15:55 ET`)
5. `E5_US100_RS1130` (`0.5000%`, `US100 vs US500` RS `11:30 ET`, `thr = 0.25`, SL `0.75 ATR`, flat `15:55 ET`)
6. `E6_EURJPY_VOLCOMP` (`0.5000%`, `EURJPY` VolComp `R5/R20 < 0.85`, Exp `0.75 ATR`, SL `0.75 ATR`, flat `20:55 UTC`)
7. `E7_USDJPY_NY10ET` (`0.5000%`, `USDJPY` NY Risk Flow `10:00 ET`, `US100 + USD basket >= 0.25`, SL `0.75 ATR`, flat `20:55 UTC`)
8. `S6_FX_USD_BSK` (`0.5000%`, Vệ tinh P1 rổ USD `12:00 UTC`, `lb = 5h`, `|z| >= 0.35`, SL `0.75 ATR`, flat `20:55 UTC`)
9. `S7_XAU_EXP120` (`0.5000%`, Vệ tinh P1 `XAUUSD` Exp `1.20 ATR`, SL `0.75 ATR`, flat `20:55 UTC`)

**Các cấu hình danh mục được chấm điểm đúng 1 lần trên `2025-01-01` → `2026-11-20`:**
- `PORT_7E_P28_CORE` (`E1..E7`): Uncapped, `+ SYMCAP_100` (trần `1.00%`/mã), và `+ SYMCAP_100 + Red-News ±5m` (`2025–2026` FOMC/CPI/NFP chính thức).
- `PORT_9E_P28_TURBO` (`E1..E7 + S6 + S7`): Uncapped, `+ SYMCAP_100`, và `+ SYMCAP_100 + Red-News ±5m`.
- `PORT_9E_INVDD_BRAKE`: Trọng số `Cluster-A Inverse-DD` & `target_vol` đóng băng **tuyệt đối từ Cụm A `2018–2020`** + Phanh biến động 1 chiều `[0.55, 1.00]`.

**Điều kiện tiên quyết trước khi chạy Holdout (Parity Gate):**
Cùng bộ mã evaluator phải chạy lại `2018–2024` trước và khớp tuyệt đối với Pass 28 (`PORT_7E +7.73%/năm, DD 6.36%`; `PORT_9E +8.83%/năm, DD 6.37%, Calmar 1.39`, sai số `<= 0.02%`).

---

## 2. Nguồn dữ liệu & Chi phí khớp lệnh Holdout

- **Nguồn:** Dukascopy Native M1 Bid+Ask ghép cặp từng phút cho toàn bộ tài sản tham gia (`2025-01-01` → `2026-11-20` UTC), có đệm lịch sử cuối năm `2024` (`11–12/2024` từ `.runtime/hot-m1-cache/`) chỉ để tính nhân quả `ATR14 D1` và `R5/R20` ngày đầu tiên `2025-01-02`. **Không tính bất kỳ lệnh nào mở trước `2025-01-01T00:00:00Z`.**
- **Mô hình chi phí & Margin:** Giữ nguyên bậc **FTMO Stress** y hệt Development (Native M1 Bid/Ask spread thật + Stress slippage + Commission + Margin FTMO Swing/Standard `220b916e60a7`, `swap = 0`).

---

## 3. Tiêu chí phán quyết Go / Conditional / No-Go (khóa cứng trước kết quả)

| Phán quyết | Điều kiện trên `2025–2026` (`PORT_7E` & `PORT_9E` M1 Floating Equity) | Hành động sau Holdout |
|---|---|---|
| **GO** | Cả `PORT_7E` và `PORT_9E` đạt `Ann >= +4.0%/năm`, `Float Peak DD <= 7.5%`, `Daily DD <= 3.0%`, `Calmar >= 0.70`, `>= 5/7` động cơ lõi không gãy cấu trúc (`> -1.5R`), `0` lỗi margin/swap | Đóng gói `8` EA kèm `Naqex_PropGuard.mqh` + `AccountOrchestrator` → MT5 Real-Tick + FTMO Free Trial `14` ngày + The5ers Free Competition |
| **CONDITIONAL** | Danh mục dương `+1.0%..+4.0%/năm` hoặc `1–2` động cơ suy yếu nhưng lõi còn lại vẫn `Calmar >= 0.65`, `Peak DD <= 7.5%` | **Không chỉnh tham số để cứu**; kéo dài chạy shadow Demo `30–60` ngày + giám sát CUSUM trước khi nạp phí |
| **NO-GO** | Danh mục âm ròng trên `2025–2026` hoặc `Float Peak DD > 9.0%` / `Daily DD > 4.0%` | Ghi nhận failure receipt trung thực, dừng nạp tiền thi quỹ trên bộ chiến lược này |
