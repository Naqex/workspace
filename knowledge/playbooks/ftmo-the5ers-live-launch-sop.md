---
doc_type: evergreen
domain: knowledge
topic: ftmo-the5ers-live-launch-sop
updated_utc: 2026-11-24
order_send_count: 0
holdout_rows_analysed: 0
sources:
  - "planning/TOP1-SOLO-QUANT-MASTER-PLAN.md"
  - "tooling/ai-engines/exports/deployment_kit/ACTIVATION-CARD-LOCAL-MT5.md"
  - "tooling/ai-engines/exports/deployment_kit/the5ers_kit/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md"
  - "tooling/ai-engines/exports/deployment_kit/ops_watchdog/naqex_mt5_watchdog.ps1"
  - "tooling/ai-engines/quant_factory/build_red_news_calendar.py"
  - "tooling/ai-engines/configs/calendars/red_news_official_2026_2027_multi_ccy.json"
  - "tooling/ai-engines/quant_factory/prop_challenge_tracker.py"
  - "tooling/ai-engines/quant_factory/daily_ops_briefing.py"
  - "knowledge/topics/mt5-live-execution-gaps-and-tca.md"
  - "knowledge/playbooks/naqex-master-roadmap-2026-2027.md"
  - "planning/research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md"
  - ".agents/skills/naqex-node-ops/SKILL.md"
---

# Quy Trình Khai Trương Thực Chiến FTMO & The5ers (`Pre-Flight -> Day-1 -> Day-14` & Emergency Runbook)

> **Mục tiêu SOP:** Chuẩn hóa chuyển đổi từ **`FTMO-Demo 1515343166` (14 ngày Free Trial trên `naqex-node1`)** sang **tài khoản trả phí `The5ers High Stakes` + `FTMO Swing`** theo [TOP1-SOLO-QUANT-MASTER-PLAN.md](../../planning/TOP1-SOLO-QUANT-MASTER-PLAN.md), tuyệt đối **fail-closed**: chưa xong đủ 4 bản vá kỹ thuật, chưa có thư chấp thuận từ quỹ, hoặc chưa đạt `PASS_TO_PAID` trong [prop_challenge_tracker.py](../../tooling/ai-engines/quant_factory/prop_challenge_tracker.py) thì **KHÔNG** mua vé thật.

---

## 1. Kiểm Tra Trước Giờ G (`Pre-Flight Checklist`)

1. **Hạ tầng Cấp 1 — `naqex-node1` 24/7 + Heroku EU + Telegram `@naqex_guard_bot`:**
   - **Hiện tại (`~0 USD/tháng` tiền túi):** MT5 chạy riêng trên **`naqex-node1`** (`Windows 10 LTSC`, 3 ổ tách biệt, sao lưu `05:30`, đồng bộ NTP `< 1s`), đẩy nhịp tim lên **Heroku EU** (gói Student miễn phí tới `2028-09-30` — nhắc kiểm tra ngày `2028-09-25`) và cảnh báo tức thì qua **`@naqex_guard_bot`**.
   - **Khóa an toàn trước tiền thật:** Bật lại **Windows Defender** (chỉ đặt đúng 1 ngoại lệ `C:\Naqex`), giữ tường lửa BẬT, `0` mật khẩu trần trên ổ cứng; diễn tập ngắt mạng/MT5 `3` phút xác nhận nhận tin nhắn đỏ `🔴 MẤT KẾT NỐI` từ `@naqex_guard_bot`; duy trì tác vụ `5` phút [naqex_mt5_watchdog.ps1](../../tooling/ai-engines/exports/deployment_kit/ops_watchdog/naqex_mt5_watchdog.ps1) (`-StaleAfterSec 180`, báo động ngay nếu `HbAge > 180s` hoặc `orphan_no_sl > 0`). Bảo trì máy tuân theo [naqex-node-ops](../../.agents/skills/naqex-node-ops/SKILL.md).
   - **Hạ tầng Cấp 2 (VPS sát sàn LD4/NY4, `25–40 USD/tháng`):** **CHỈ** thuê khi đã rút lãi ròng đều **`>= 300 USD/tháng`** từ Prop (trích từ Ngăn 3, không móc tiền túi).
2. **Sandbox Portable & Đủ 4 Bản Vá Kỹ Thuật Bắt Buộc:**
   - Dùng đúng thư mục portable `.runtime/ftmo-demo-portable-1515343166`, profile **`Naqex_FreeTrial`** gồm `9` biểu đồ (`E1..E7`, `S6`, `Naqex_AccountOrchestrator`), `KeepPrivate = 0`, `Leverage = 1:30`, tuân thủ [ACTIVATION-CARD-LOCAL-MT5.md](../../tooling/ai-engines/exports/deployment_kit/ACTIVATION-CARD-LOCAL-MT5.md) (mặc định nguồn `.mq5` luôn `InpDryRunLogOnly = true`).
   - **Vá #1 (`NAS100` & broker alias):** `Naqex_PropGuard.mqh` nhận đủ `US100/NAS100/NDX/USTEC/US500/SPX/US30/XAU/BTC` (`USD`), `GER40/DE40/DAX` (`EUR`), `UK100/FTSE` (`GBP`); preset The5ers gắn đúng `NAS100`.
   - **Vá #2 (Lịch tin đỏ 4 đồng tiền & tách vùng đóng trước tin):** [naqex_red_news_utc.csv](../../tooling/ai-engines/exports/Files/naqex_red_news_utc.csv) được dựng xác định bằng [build_red_news_calendar.py](../../tooling/ai-engines/quant_factory/build_red_news_calendar.py) từ [red_news_official_2026_2027_multi_ccy.json](../../tooling/ai-engines/configs/calendars/red_news_official_2026_2027_multi_ccy.json) (`418` dòng đến hết `2027`, phủ đủ **`USD, GBP, EUR, JPY`**: `FOMC + Press Conf`, `US NFP`, `US CPI`, `US PPI`, `US Retail Sales`, `US Core PCE/GDP`, `BoE Rate`, `UK CPI`, `ECB Rate + Press Conf`, `BoJ Rate ~03:00 UTC _EST03UTC`). Bộ lọc tách rõ vùng **đóng trước tin** (`-5p` tới `-2p15s`) với **vùng cấm cứng `±2p15s`** (`InpGuardNewsHardBanSec = 135`) để khởi động lại giữa tin không tự bấm đóng vi phạm luật `±2p`. *Bảo trì quý:* ngày `25` các tháng `3, 6, 9, 12`, chạy `--verify` và đồng bộ lên `naqex-node1` khi tài khoản phẳng.
   - **Vá #3 (Siết `SYMCAP` Vòng 1/2):** `P1_Balanced <= 1,75%`, `P1_Sprint <= 2,00%`, `P2_Verify <= 1,50%`, `FreeTrial / Funded = 1,00%` (`SYMCAP_100`).
   - **Vá #4 (`Dyn_ProfitLock`, giờ reset ngày & đếm `3` ngày lãi):** Bật `Dyn_ProfitLock` (`+5%` P1 / `+3%` P2), đặt `InpDailyResetMode = 1` (`Europe/Prague`) cho FTMO và `0` (`MT5 Server Midnight`) cho The5ers, đếm đúng **`3` ngày lãi `>= +0,50%`** trên Control Room.
3. **Cổng Pháp Lý Văn Bản (FTMO & The5ers Terms §11):**
   - Gửi email xin xác nhận chạy EA white-box độc quyền tới `support@ftmo.com` và `help@the5ers.com` theo mẫu [THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md](../../tooling/ai-engines/exports/deployment_kit/the5ers_kit/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md) và lưu thư chấp thuận trước khi trả phí.

---

## 2. Giám Sát 14 Ngày Free Trial (`Day-1 -> Day-14`)

- **Ngày 1:** Xác nhận `9` biểu đồ `Naqex_FreeTrial` trên `naqex-node1` đẩy nhịp tim `<= 60s` lên Heroku EU, `kill_switch = false`, `orphan_no_sl = 0`, không lỗi `4756 / 10018 / 10019`.
- **Ngày 2 -> 13 (5 phút/ngày — cấm canh từng nến):** Xem Control Room tối đa `1–2` lần/ngày; sau `21:55 UTC` chạy [daily_ops_briefing.py](../../tooling/ai-engines/quant_factory/daily_ops_briefing.py) và [prop_challenge_tracker.py](../../tooling/ai-engines/quant_factory/prop_challenge_tracker.py) (`--profile ftmo_swing_10k`). Lệch khớp lệnh tra [mt5-live-execution-gaps-and-tca.md](../topics/mt5-live-execution-gaps-and-tca.md); **cấm bấm đóng tay vì xót lãi** (*profit giveback*).
- **Ngày 14 (Cổng Quyết Định `PASS_TO_PAID` vs `HALT_AND_FIX`):** Chỉ nâng sang trả phí khi đạt đồng thời: `10–15` lệnh đóng khớp MetriX, `>= 4` ngày giao dịch, `0` vi phạm Daily (`< 3,5%`) / Max Loss (`< 7,0%`), `swap == 0`, `0` giữ qua đêm / vi phạm tin đỏ / thiếu SL, trượt giá mọi động cơ `<= 1,5×` M1, đủ 4 bản vá + diễn tập Telegram + thư xác nhận quỹ.

---

## 3. Nâng Cấp Trả Phí (`DUAL_2FIRM_STAGGER_42D`), Ưu Tiên `FTMO Swing` & Nhảy Bậc `25K/50K/100K`

Bám sát kết quả mô phỏng [MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md](../../planning/research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md) và [naqex-master-roadmap-2026-2027.md](naqex-master-roadmap-2026-2027.md):

1. **Ngày `T = 0` — Vé Chứng Minh #1 (`The5ers High Stakes 5K`, `~39–52 USD`):**
   - Kiểm tra rõ trên dashboard là gói `8%+5%` hay `10%+5%`. Dùng **`The5ers_HighStakes_P1_Balanced`** (`SYMCAP <= 1,75%`, `Dyn_ProfitLock +5%`, `InpDailyResetMode = 0`), hạ cứng về **`1,0×` Funded** ngay khi đậu; theo dõi đủ **`3` ngày lãi `>= +0,50%`** (`>= +25 USD` trên `5k USD`).
2. **Ngày `T + 42` Phiên (~2 Tháng Sau) — Mở Tài Khoản #2 Ưu Tiên **`FTMO Swing`** Hơn `FTMO Standard`:**
   - **Ưu tiên `FTMO Swing`:** Trên **`FTMO Standard` (Funded)**, giá giật tin đỏ quét trúng **SL/TP trong khung `±2 phút`** vẫn có thể bị xử vi phạm luật tin đỏ và khóa tài khoản (`R4`). **`FTMO Swing` (2-Step)** miễn hoàn toàn luật cấm tin đỏ cả lúc thi lẫn Funded, đòn bẩy `1:30` dư sức cho bộ 8 bot. Chỉ chọn Standard khi có mã giảm giá sâu *và* bật đủ 4 bản vá.
   - **Tại sao bắt buộc `DUAL_2FIRM_STAGGER_42D + P1_Balanced`?** Mở cùng ngày bằng `Sprint` đẩy cháy kép (`Double-Fail`) lên **`24,1%`** (`1,8%` cháy quỹ phí ở `500 USD`); giữ lệch pha **`+42` phiên + `P1_Balanced`** cắt Double-Fail còn **`3,0%`** và cháy quỹ phí còn **`0,4%`** (`0,0%` ở `1.500 USD`).
3. **Nhảy Bậc `25K / 50K / 100K` Sau Khi Chứng Minh Trên `5K` (Né Phí Đắt Vé `10K`):**
   - Vé **`FTMO 10K`** tốn `~168–192 USD` (`~1,7%–1,9%` vốn — đắt nhất bảng giá, trừ khi săn khuyến mãi `~95 USD`), trong khi **`25K`** (`~1,1%`), **`50K`** (`~0,75%`), **`100K`** (`~0,55%`, rẻ hơn `3,1×` mỗi USD vốn). Vì vậy **KHÔNG mua lặp nhiều vé `10K`**: sau khi `The5ers 5K` chứng minh rút lãi thật và Ngăn 1 (`30%` quỹ dự phòng trong [treasury_ledger.py](../../tooling/ai-engines/quant_factory/treasury_ledger.py)) đủ `3–5×` vé, **nhảy bậc sang `FTMO Swing 25K -> 50K -> 100K`** (và `The5ers 20K`). Khi Ngăn 1 đầy trần `5×`, `100%` phần thừa tràn sang Ngăn 2 (Own-Book lên `80%`).
4. **CẢNH BÁO ĐỎ — Bậc `The5ers 50K / 100K` Trần Lỗ Chặt Hơn (`4%` Ngày / `8%` Tổng):**
   - **TUYỆT ĐỐI KHÔNG bê nguyên preset `5K` (`5%/10%`) sang `The5ers 50K / 100K`!** Phải xác nhận điều khoản trên dashboard và hạ cứng `InpMaxDailyLossPct <= 2,0%`, `SYMCAP <= 1,25%–1,50%` (P1) / `<= 0,80%` (Funded), và kéo phanh `AMBER/RED` theo tỷ lệ `4/5` trước khi chạy.

---

## 4. Chẩn Đoán Ngược `R4 -> R3 -> R2 -> R1` & Sổ Tay Ứng Cứu Khẩn Cấp

Khi gặp lỗ hoặc lệch số, **KHÔNG vội sửa bot** — luôn kiểm tra đúng thứ tự ngược **`R4 -> R3 -> R2 -> R1`**:

| Thứ tự | Nhãn | Bản chất | Hành động đúng tầng |
| :--- | :--- | :--- | :--- |
| **1** | **`R4`** | Luật quỹ, Sàn & Con người | Soi luật tin đỏ `±2p/±5p`, loại tài khoản (`Swing` vs `Standard`), IP cố định `naqex-node1`, thư xác nhận EA, dấu hiệu bấm tay can thiệp. **Không đụng code bot.** |
| **2** | **`R3`** | Khớp lệnh, Trượt giá & Máy móc | Đối chiếu `naqex_exec_audit.csv` với MetriX, NTP `< 1s`, `HbAge <= 180s`, cảnh báo `@naqex_guard_bot`, `swap == 0`, trượt giá `<= 1,5×`. **Không sửa logic vào lệnh.** |
| **3** | **`R2`** | Trùng lặp Danh mục & Tập trung | Soi `SYMCAP` trên 1 mã (`<= 1,75%` P1 / `<= 1,00%` Funded), tránh mở 2 quỹ cùng ngày `Sprint`, giữ tổng CEX `<= 25%` (`NCO_CexCap25`) ở Own-Book. **Không sửa từng bot lẻ.** |
| **4** | **`R1`** | Suy giảm lợi thế THẬT | Chỉ khi `R4/R3/R2` đều sạch mới để `CUSUM/SPRT` và `AccountOrchestrator` tự hạ ga / tạm dừng nhánh hỏng đưa về nghiên cứu. |

### 4 Sự Cố ĐỎ Được Phép Can Thiệp Tay Ngay (`Emergency Runbook` — Fail-Closed)

| Sự cố (Nhãn) | Dấu hiệu | Thao tác tức thì | Điều kiện mở lại |
| :--- | :--- | :--- | :--- |
| **1. Vị thế Mồ côi Không SL (`R3` — `orphan_no_sl > 0`)** | `@naqex_guard_bot` / `[ORCH-ALERT]` / `daily_ops_briefing` `FAIL` | (1) Tắt `Algo Trading`; (2) Gắn SL `0,75 ATR` (hoặc đóng ngay nếu lỗ `> 1,0R`); (3) Lưu log `Experts`/`Journal`. | Rõ nguyên nhân gốc, vá & test sạch trên Demo. |
| **2. Mất Kết nối `naqex-node1` (`R3` — `HbAge > 180s`)** | Tin nhắn đỏ `🔴 MẤT KẾT NỐI` từ `@naqex_guard_bot` (Heroku EU) / watchdog `-StaleAfterSec 180` | (1) Mở MT5 Mobile (chỉ xem/đóng, **cấm vào lệnh**); (2) Đóng phẳng trước rollover `21:55 UTC` hoặc tin đỏ nếu `naqex-node1` chưa hồi phục. | Khởi động lại MT5, xác nhận nhịp tim nhảy đều, NTP `< 1s`, `DAYEQ` đúng. |
| **3. Global Kill-Switch (`R2/R1` — `kill_switch = true`)** | Chạm phanh ngày `2,5%–3,5%` hoặc phanh Đỏ `7,0%` | **CẤM tắt Kill-Switch đánh gỡ!** Xác nhận phẳng toàn bộ qua `prop_challenge_tracker.py`; nghỉ hết phiên/tuần và kiểm toán `R4 -> R3 -> R2 -> R1`. | Sang phiên mới sau biên bản kiểm toán; không nâng lot gỡ lỗ. |
| **4. Vi phạm Swap, Tin Đỏ hoặc Trượt Giá `> 1,5×` (`R4/R3`)** | `prop_challenge_tracker.py` trả về **`HALT_AND_FIX`** | (1) Tắt riêng EA lỗi; (2) Kiểm tra `naqex_red_news_utc.csv`, mã `NAS100`, DST máy chủ & half-day Mỹ; (3) Soi spread lúc khớp. | Vá đúng tầng, chạy `build_red_news_calendar.py --verify`, test `0` lỗi trên Demo. |
