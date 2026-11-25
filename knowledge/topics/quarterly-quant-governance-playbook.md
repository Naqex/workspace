---
doc_type: evergreen
domain: knowledge
topic: quarterly-quant-governance-playbook
updated_utc: 2026-11-24
sources:
  - "T1 (Nội bộ): planning/research/PASS32-PORTFOLIO-PRUNING-AND-REGIME-DEV-20261124.md — bằng chứng bẫy cắt tỉa LOO & V08_PORT9E_CAUSAL_ERC"
  - "T1 (Nội bộ): planning/research/SLEEVE3A-FUNDING-RATE-CARRY-20261124.md & SLEEVE3B-MACRO-ETF-TREND-18YR-20261124.md"
  - "T1 (Nội bộ): tooling/ai-engines/quant_factory/live_decay_monitor.py, treasury_ledger.py, ibkr_macro_rebalancer.py"
  - "T1 (Nội bộ): knowledge/owner/PROFILE.md & knowledge/topics/alpha-hypothesis-ledger.md"
  - "T2: Institutional Quant Pod Governance (Man AHL / Millennium / Two Sigma) — chu kỳ tái hiệu chuẩn, quy trình cho nghỉ hưu chiến lược & quản trị rủi ro đối tác"
---

# Quy trình Quản trị Quỹ Cá nhân Hàng quý: Tái hiệu chuẩn, Nghỉ hưu Alpha & Chống Đứt gãy Đa sàn

> Tài liệu vận hành cấp Giám đốc Hệ thống & Rủi ro dành cho **One-Person Quant Pod** (`PORT_7E` Prop + `Sleeve #2` Crypto Spot + `Sleeve #3A` Funding Carry + `Sleeve #3B` Macro ETF). Mục tiêu: thiết lập **kỷ luật quản trị theo quý** giống các quỹ đa chiến lược (*Multi-Manager Quant Pods*), đảm bảo hệ thống thích nghi dài hạn mà **không bao giờ tự phá hỏng lợi thế bằng việc tinh chỉnh tham số theo cảm tính**.

---

## 1. Chu kỳ Tái hiệu chuẩn Hàng quý (*Quarterly Re-Calibration Protocol*)

Mọi thay đổi kỹ thuật đối với danh mục sản xuất chỉ được thực hiện tại **Cửa sổ Kiểm toán Hàng quý** (tuần cuối các tháng `03`, `06`, `09`, `12` — khi toàn bộ vị thế intraday đã `hard flat` vào cuối tuần). Ngoài `4` mốc này, danh mục chạy khóa cứng `100%` (trừ 3 trường hợp khẩn cấp hạ tầng đã nêu tại [Playbook Tâm lý & Profit Giveback](trading-psychology-and-profit-giveback-playbook.md)).

### 1.1. Những gì ĐƯỢC PHÉP cập nhật hàng quý (Vệ sinh Hạ tầng & Thông số Sàn)
1. **Làm mới lịch tin đỏ (`naqex_red_news_utc.csv`) và ngày lễ đóng sớm (*US Half-Days*):** Đối chiếu lịch FOMC/NFP/CPI/ECB/BoE/BoJ mới công bố cho quý tiếp theo và kiểm chứng lại `manifest.sha256.json` qua `verify_deployment_kit.py`.
2. **Đo lại snapshot thông số sàn Read-Only (`SymbolInfo`):** Xác nhận spread trung vị/P95, commission, bước lot, `SYMBOL_FILLING_MODE`, và kiểm tra trần `InpGuardMaxSpreadPoints` (đặc biệt trên `US100.cash` và các mã chỉ số/vàng).
3. **Đối soát TCA tổng hợp quý (`tca_reconcile.py`):** So sánh trượt giá trung bình (`% R0`), độ trễ `p90`, tỷ lệ reject và xác nhận `swap_violations == 0` trên toàn bộ quý vừa kết thúc.
4. **Kiểm toán ngân quỹ & Điểm giao cắt (`treasury_ledger.py`):** Xuất **GIPS-Lite Monthly Fact Sheet** tách bạch tuyệt đối dữ liệu thực (`LIVE_VERIFIED`) với dữ liệu mô phỏng, kiểm tra độ đầy Quỹ Đệm Thi Quỹ (`Bucket 1 >= 5×` vé) và tiến độ giao cắt Prop → Sổ Vốn Riêng ([Toán học Tăng trưởng Vốn](capital-scaling-prop-to-own-book.md)).
5. **Tái cân bằng cấp Nhánh (*Sleeve-Level Allocation*) bằng trọng số nhân quả:** Chỉ cập nhật tỷ trọng giữa `4` nhánh (`ERC_Capped35` / `NCO`) khi có thêm ít nhất `1` quý dữ liệu mới, giữ trần cứng **`<= 15%–20%`** cho nhánh `Sleeve #3A` (Funding Carry) và bảo đảm tỷ lệ vốn cá nhân nằm trong vùng xanh của [Hồ sơ Owner](../owner/PROFILE.md).

### 1.2. Ba điều TUYỆT ĐỐI CẤM làm trong kỳ Review Hàng quý
1. **CẤM tối ưu lại tham số tín hiệu (`trig_atr`, `sl_atr`, khung giờ phiên) trên dữ liệu cũ hoặc trên Holdout `2025–2026`:** Holdout đã mở đúng `1` lần duy nhất; mọi thay đổi tham số tín hiệu biến kiểm định mù thành quá khớp (*data snooping*).
2. **CẤM cắt tỉa động cơ dựa trên hiệu suất 1–3 năm gần nhất (Bài học LOO Pruning Pass 32):** Kiểm định [Pass 32](../../planning/research/PASS32-PORTFOLIO-PRUNING-AND-REGIME-DEV-20261124.md) đã chứng minh cắt bỏ `3` động cơ chậm trên Cluster A (`E1`, `E6`, `S7`) làm Calmar quá khứ tăng vọt lên `2,045` nhưng **sụp xuống `0,387` ngoài mẫu (`CF24 = +88,4 USD`)** vì đúng `3` động cơ đó đảo chiều thành Top-3 đóng góp mạnh nhất giai đoạn tiếp theo!
3. **CẤM mở khóa nâng cấp v2 khi chưa đủ `90` ngày dữ liệu Forward thực tế:** Ví dụ ứng viên nghiên cứu **`V08_PORT9E_CAUSAL_ERC`** (đạt `Calmar Cl.B 1,596` trên Pass 32) chỉ được xem xét nâng cấp ở kỳ review sau ít nhất `90` ngày Demo/Live TCA sạch — và bắt buộc kèm trần rủi ro cơ sở **`<= 0,75%`/động cơ** theo khuyến nghị kiểm toán rủi ro để ngăn động cơ thưa lệnh (`E7`) bị khuếch đại quá mức khi nhân hệ số P1.

---

## 2. Giao thức Nghỉ hưu Động cơ & Ghế Dự bị (*Alpha Decay Retirement & Incubation Bench*)

Để không rơi vào hai sai lầm chết người — *tắt bot quá sớm trong năm thị trường ngủ yên* hoặc *ôm khư khư một chiến lược đã thực sự mất cạnh tranh* — mọi quyết định giảm cỡ hay cho nghỉ hưu phải đi qua **cây quyết định 3 tầng khách quan** của [live_decay_monitor.py](../../tooling/ai-engines/quant_factory/live_decay_monitor.py):

| Trạng thái kiểm định quý | Ngưỡng thống kê khách quan | Chẩn đoán bắt buộc (3 nhánh) | Hành động quản trị |
|---|---|---|---|
| **Tầng 1 — Bình thường (`GREEN_WITHIN_EXPECTATION`)** | Đường cong lãi nằm trên bách phân vị `p05` của Bootstrap Cone; `CUSUM > -4,5σ`; `SPRT` chưa bác bỏ `H0`; `tca_reconcile = GREEN` | Lợi thế còn nguyên vẹn (kể cả khi đang đi ngang `3–6` tháng như `2019`/`2021`) | **Giữ nguyên 100%** tỷ trọng và tham số. Không can thiệp. |
| **Tầng 2 — Cảnh báo Suy giảm (`AMBER_WATCH_REDUCE_SIZE`)** | `CUSUM <= -4,5σ` **HOẶC** tổng lãi dưới `p05` **HOẶC** `SPRT = REJECT_EDGE_DECAYED` **HOẶC** trượt giá TCA vào vùng `12%–25% R0` | Phân tách rõ: *(a)* Lỗi khớp lệnh/spread giãn (so sánh với `MT5 Real-Tick` & bảng [Chẩn đoán Free Trial](mt5-live-execution-gaps-and-tca.md)); *(b)* Đổi chế độ biến động tạm thời (`Vol_20d / Vol_120d < 0,75`); *(c)* Suy giảm tín hiệu thật. | Hạ rủi ro nhánh/động cơ xuống **`0,50×–0,65×`** trong `1` quý kế tiếp (chế độ *Probation*), tiếp tục thu thập mẫu thực tế để xác nhận hay bác bỏ. |
| **Tầng 3 — Cho Nghỉ Hưu (`RED_HALT_ALPHA_DECAY`)** | **`CUSUM <= -4,5σ` ĐỒNG THỜI `SPRT = REJECT_EDGE_DECAYED` hoặc dưới `p05`**, kéo dài vượt `1` quý (hoặc TCA vi phạm `>= 25% R0` / `swap != 0` không thể khắc phục bằng đổi sàn) | Lợi thế kinh tế đã bị bào mòn vĩnh viễn hoặc cấu trúc phí sàn đã giết biên lãi | **Tắt hẳn động cơ (`weight = 0`)**, chuyển sang chạy **Shadow-Only (`OrderSend = 0`)** tối thiểu `6` tháng, ghi biên bản vào [Sổ cái Giả thuyết Alpha](alpha-hypothesis-ledger.md) kèm nguyên nhân gốc (*Blameless Postmortem*). |

### Quy tắc Ghế Dự bị (*Incubation Bench*)
- Chiến lược mới (từ các đợt nghiên cứu được `@verifier` & `SkepticalRedTeamCritic` phê duyệt) **không bao giờ nhảy thẳng vào vốn chính**: phải nằm trên ghế dự bị tối thiểu `30–60` ngày Shadow/Paper (hoặc `90` ngày với bản nâng cấp phân bổ v2) với đầy đủ nhật ký TCA trước khi được cấp `25%–50%` suất vốn khởi điểm.
- Đối với **`Sleeve #3A` (Funding-Rate Carry)** — đây là nhánh **phụ thuộc chế độ (*regime-dependent*)** ([Báo cáo Sleeve #3A](../../planning/research/SLEEVE3A-FUNDING-RATE-CARRY-20261124.md)): không coi giai đoạn funding nén `2,5%–3,0%/năm` là "chết alpha", mà áp luật **công tắc kinh tế cứng** — chỉ giải ngân khi lợi suất funding ròng 7 ngày trượt (sau phí) cao hơn lãi suất phi rủi ro (`T-Bill` USD / tiền gửi VND quy đổi) tối thiểu `+2,0` điểm %/năm; dưới ngưỡng đó tự động nằm tiền mặt an toàn.

---

## 3. Sổ tay Chống Đứt gãy Đa Sàn & Đa Đối Tác (*Multi-Broker & Counterparty Resilience Runbook*)

Một hệ thống định lượng có Sharpe `2,0` vẫn có thể mất trắng nếu **1 đối tác nắm toàn bộ tiền mặt bị sập** (bài học FTX `11/2022` và MyForexFunds `2023`). Toàn bộ Quant Pod phải duy trì **4 tường lửa đối tác độc lập**:

### 3.1. Lớp 1 — Quỹ Cấp Vốn Prop Firm (`Sleeve #1`: FTMO + The5ers)
- **Giới hạn tập trung:** Không để quá `50%–60%` tổng danh nghĩa Funded nằm ở duy nhất `1` prop firm khi quy mô vượt `50.000 USD`.
- **Giới hạn lãi giữ lại trong tài khoản quỹ:** Rút định kỳ mỗi `14` ngày; không để quá `3%–4%` lợi nhuận chưa rút nằm trong tài khoản prop (tránh rủi ro thay đổi điều khoản bất ngờ).
- **Kịch bản dự phòng sự cố (`Firm Disruption Drill`):** Nếu `1` quỹ tạm dừng payout hoặc đổi luật bất lợi → dừng mua thêm vé mới tại quỹ đó, rút toàn bộ lãi khả dụng, giữ nguyên `Bucket 1 (Challenge Reserve)` để kích hoạt vé thay thế tại quỹ đối ứng (hoặc chuyển sang tài khoản Futures CME / broker cá nhân).

### 3.2. Lớp 2 — Sàn Tiền Mã Hóa (`Sleeve #2` Spot & `Sleeve #3A` Funding Carry)
- **Giới hạn rủi ro sàn tập trung (CEX Tail Risk):**
  - Không bao giờ để quá `<= 15%–20%` tổng tài sản Quant Pod trên sàn phái sinh cho `Sleeve #3A` Funding Carry; dùng **đệm ký quỹ `2,0×`** (`50%` Spot + `50%` ký quỹ cho `1×` Perp Short) và chỉ chạy `BTC + ETH` để tránh short-squeeze altcoin (`DOGE +405%`).
  - Khi vốn `Sleeve #2` (Crypto Spot) vượt `25.000 USD`, chia tối thiểu qua **`2` sàn Tier-1 độc lập** (ví dụ Binance + OKX/Bybit/Kraken) hoặc rút phần tiền mặt nhàn rỗi (`Cash`) về ví/tài khoản ngân hàng riêng khi tín hiệu `BTC < SMA100` chuyển về phòng thủ.
- **Tín hiệu rút khẩn cấp CEX (*CEX Red-Alert Kill*):** Nếu chênh lệch giá USDT/USD lệch `> 1,5%`, sàn chậm rút tiền quá `24` giờ bất thường, hoặc xuất hiện điều tra phong tỏa thanh khoản → kích hoạt quy trình đóng vị thế phái sinh và rút tài sản về ví lạnh/tiền pháp định ngay lập tức (thuộc trường hợp khẩn cấp *force majeure* được phép can thiệp tay!).

### 3.3. Lớp 3 — Tài Khoản ETF Vĩ Mô (`Sleeve #3B` qua IBKR Cash Account)
- Sử dụng **tài khoản Tiền mặt thuần (`Cash-Only`, không vay Margin)** tại broker cấp tổ chức có tách biệt tài sản khách hàng và bảo hiểm SIPC (như Interactive Brokers) cho nhánh `M5_VOL_PARITY_TREND_GUARD`.
- Tái cân bằng đúng **`1` lần/tháng** bằng công cụ khô [ibkr_macro_rebalancer.py](../../tooling/ai-engines/quant_factory/ibkr_macro_rebalancer.py) (`OrderSend = 0` xuất file CSV BasketTrader) → owner duyệt mắt `5` phút và nhập lệnh giới hạn (`LMT ±0,30%`) thủ công trên TWS/Client Portal, loại bỏ hoàn toàn rủi ro bug API tự đặt lệnh sai.

### 3.4. Lớp 4 — Dự phòng Hạ tầng VPS, Dữ liệu & Khôi phục `30` Phút (*Disaster Recovery Drill*)
Mỗi quý diễn tập kiểm tra nhanh (`15` phút vào cuối tuần) `4` hạng mục hạ tầng:
1. **Giám sát sống (`naqex_mt5_watchdog.ps1`):** Xác nhận cảnh báo hoạt động khi giả lập dừng cập nhật `naqex_heartbeat.json` quá ngưỡng mặc định **`180` giây** (`-StaleAfterSec 180`, hoặc rút ngắn `-StaleAfterSec 60` khi kiểm thử nhanh).
2. **Trạng thái bền vững sau khởi động lại:** Xác nhận `GlobalVariables` (`F3` trên MT5) giữ đúng `g_dayStartEquity` và `g_lastTradedDay` sau khi tắt/mở lại MT5 Terminal.
3. **Bản sao lưu lạnh ngoại tuyến (`E:\BACKUP-TRADINGWORKSPACE\` + Git remote):** Toàn bộ `.mq5`, `deployment_kit/presets/`, `manifest.sha256.json`, `naqex_red_news_utc.csv`, sổ quỹ `treasury_ledger` JSON và kho tri thức `knowledge/` đều có bản sao mới nhất — đảm bảo nếu VPS chính sập hoàn toàn, có thể dựng lại toàn bộ `9` chart MT5 trên máy mới trong **`<= 30` phút** theo đúng Thẻ Kích Hoạt 5 Bước.
4. **Kiểm toán vệ sinh bộ nhớ AI (`brain_cli.py audit-data`):** Xác nhận `broken_knowledge_links_count = 0`, `near_duplicate_topic_headings_count = 0`, và không để thư mục `.runtime/` hay `.artifacts/` phình rác vượt mức kiểm soát.
