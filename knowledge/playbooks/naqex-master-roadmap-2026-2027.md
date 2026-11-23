---
doc_type: evergreen
domain: knowledge
topic: naqex-master-roadmap-2026-2027
updated_utc: 2026-11-24
order_send_count: 0
holdout_rows_analysed: 0
sources:
  - "knowledge/owner/PROFILE.md"
  - "knowledge/topics/alpha-hypothesis-ledger.md"
  - "knowledge/topics/capital-scaling-prop-to-own-book.md"
  - "knowledge/topics/quarterly-quant-governance-playbook.md"
  - "planning/research/PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md"
  - "planning/research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md"
  - "planning/research/QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md"
  - "planning/research/LAB4-40ETF-MULTIFACTOR-VRP-20261124.md"
  - "planning/research/LAB5-CME-FUTURES-PROP-STUDY-20261124.md"
  - "planning/research/LAB2B-CRYPTO-MAKER-STATARB-20261124.md"
  - "tooling/ai-engines/exports/deployment_kit/the5ers_kit/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md"
---

# Lộ Trình Tăng Trưởng Tổng Thể Naqex Quant Pod (`2026–2027`: `Phase 0 → Phase 5`)

> **Tuyên ngôn Vận hành (Calibrated to [PROFILE.md](../owner/PROFILE.md)):** Tài liệu này là bản đồ thực chiến duy nhất kết nối toàn bộ bằng chứng định lượng đã kiểm chứng qua **Wave-1 (Tier 1–8)** và **Wave-2 (Labs #1–#6, Pod v2 `NCO_CexCap25`, Multi-Prop Scaling & Black-Swan Stress)** thành **6 pha chuyển tiếp có cổng khóa định lượng (`Gate-Driven`)** — đi từ `0` lịch sử live hôm nay tới quỹ định lượng cá nhân đa nhánh `100k–200k+ USD` (`2,55–5,10 tỷ VND` @ `25.500 VND/USD`) với nguyên tắc bất di bất dịch: **fail-closed thực thi (`OrderSend = 0` khi chưa qua cổng), tách biệt tuyệt đối tâm lý giữa lệnh, và mọi rủi ro luôn quy đổi song song `%`, `USD` và `triệu VND`**.

---

## Bản Đồ Nhanh 6 Pha Tăng Trưởng (`2026–2027`)

| Pha | Khung thời gian | Mục tiêu Vốn / Quy mô | Cỗ máy Chủ lực Đã Xác minh | Cổng Chuyển Pha Bắt buộc (*Hard Gate*) |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | Ngày `1–14` *(Hiện tại)* | `0 USD` rủi ro thật (`FTMO-Demo 1515343166` + Shadow) | `PORT_7E` 9-chart (`swap = 0`) + Binance Spot/Maker Shadow + Email `The5ers Terms §11` | `14` ngày Free Trial: `0` lỗi `orphan_no_sl`, `swap == 0`, trượt giá thực `<= 1,5×` stress, nhận xác nhận `The5ers` |
| **Phase 1** | Tháng `1–4` | Ngân sách phí `500–1.500 USD` (`12,8–38,2 tr VND`) | **`DUAL_2FIRM_STAGGER_42D + P1_Balanced`** (`FTMO BF-25%` + `The5ers HS`), luật **3-Bucket** | Vượt ít nhất `1` vòng Funded & rút thành công `>= 2` lần payout ròng, lấp đủ quỹ dự phòng `5×` vé phí |
| **Phase 2** | Tháng `4–12` | Sổ Vốn Riêng `5k → 25k USD` (`128 → 638 tr VND`) | **Own-Book Pod v2 `NCO_CexCap25`** (`Monthly_1st`, **Tổng CEX `<= 25%`**): `S2 + S3A + S3B + S4` | Tái cân bằng đúng lịch `>= 6` tháng, không can thiệp tay giữa lệnh, `MaxDD` thực nằm trong nón MC |
| **Phase 3** | Tháng `12–24` | Sổ Vốn Riêng `25k → 100k USD` (`638 tr → 2,55 tỷ VND`) | **`LADDER_STAGGER_SCALE`** + IBKR Zero-Swap (`S3B + S4`) + Nhánh điều kiện (`M2B` Maker / CME-Native) | `M2B` chỉ bật khi 30d shadow `fill >= 70%` (`eff_cost <= 6,15 bps`); CME chỉ bật khi Lab #8 đỗ Hội đồng |
| **Phase 4** | Năm `2+` | Sổ Vốn Riêng `100k → 200k+ USD` (`2,55 → 5,10+ tỷ VND`) | **GIPS-Lite Audited Track Record** + Quản trị Quý + Khiên VND (`-50%` CEX tối đa `-12,89%`) | Own-Book tạo dòng tiền ròng vượt danh nghĩa Prop (`Crossover >= 100%`), giữ kiểm toán quý liên tục |
| **Phase 5** | Sau mốc kiểm chứng | Mở khóa 1 lần duy nhất **Holdout `2025–2026`** cho thế hệ v2 | Đánh giá ứng viên mới (vượt đủ 6 cổng Dev) trên tập Holdout niêm phong 1 lần duy nhất | Đóng băng `100%` mã nguồn & SHA-256 trước mở, owner ký duyệt, tuyệt đối không tái tối ưu ngược |

---

## Phase 0 — Khởi Chạy Kiểm Chứng Thực Địa & Tiền Khai Trương (Ngày `1–14`)

1. **Vận hành `FTMO-Demo 1515343166` (9 biểu đồ live & `Model=4` Real-Tick):**
   - Chạy đủ `14` ngày Free Trial với bộ 7 động cơ lõi `PORT_7E` (`E1..E7`) + vệ tinh `S6/S7` và `Naqex_AccountOrchestrator.mq5` (đã tích hợp `Naqex_PropGuard.mqh`: khóa tin đỏ `±5m`, `SYMCAP_100`, `swap = 0`, tự phát hiện vị thế mồ côi `orphan_no_sl`).
   - Đối soát hằng ngày bằng 1 lệnh [daily_ops_briefing.py](../../tooling/ai-engines/quant_factory/daily_ops_briefing.py) và Control Room cục bộ `127.0.0.1:8787` ([server.py](../../tooling/ai-engines/cockpit/server.py)): kiểm tra `naqex_heartbeat.json`, `naqex_exec_audit.csv`, và phân tách dứt khoát *lỗi sàn* vs *lỗi bot* theo [mt5-live-execution-gaps-and-tca.md](../topics/mt5-live-execution-gaps-and-tca.md).
2. **Thu thập Shadow Live Crypto (`OrderSend = 0`, 0 API key):**
   - Duy trì `crypto_shadow_runner.py` (đã đo live `10k USD` L2 slip `2,09 bps <= 5,0 bps` ngân sách backtest) và chạy `crypto_maker_shadow_probe.py` xuyên `30` ngày để kiểm chứng thực địa điều kiện mở khóa của `M2B_BLEND_50_FUND_50_MOM` ([LAB2B-CRYPTO-MAKER-STATARB-20261124.md](../../planning/research/LAB2B-CRYPTO-MAKER-STATARB-20261124.md)).
3. **Hoàn tất thủ tục `The5ers Terms §11` trước khi mua vé:**
   - Gửi đúng mẫu email xác nhận quyền chạy EA độc quyền (không copy-trade/HFT) và quy tắc tin đỏ `±2m` (bot giữ khóa chặt hơn là `±5m`) từ [THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md](../../tooling/ai-engines/exports/deployment_kit/the5ers_kit/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md). Lưu thư phản hồi bằng chứng trước khi nạp `39 USD`.

---

## Phase 1 — Khởi Động Đa Quỹ Prop An Toàn & Dòng Tiền 3-Bucket (Tháng `1–4`, Ngân Sách Phí `500–1.500 USD`)

- **Kiến trúc tối ưu đã chứng minh bằng 5.000 đường Monte Carlo ([MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md](../../planning/research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md)):**
  - **Cấm mở đồng bộ 2 quỹ cùng ngày + chạy `P1_Sprint`:** Trên ngân sách nhỏ `500 USD` (`12,8 tr VND`), `DUAL_2FIRM_SYNC + P1_Sprint` đẩy rủi ro **cháy đồng thời cả 2 tài khoản (`Double-Fail`) lên `24,1%`** và nguy cơ cháy quỹ phí lên `1,8%`.
  - **Cấu hình bắt buộc — `DUAL_2FIRM_STAGGER_42D + P1_Balanced`:** Khởi chạy `The5ers High Stakes 5K` (`39 USD`, `EV/USD phí = +7,17×`, `OOP95 = 74,1 USD`) trước, sau **`+42` phiên giao dịch (~2 tháng)** mới mở tiếp `FTMO Standard 10K BF-25%` (`~135–168 USD`, `EV/USD phí = +4,08×`) hoặc `FTMO Swing 10K` (`+3,25×`). Lệch pha thời điểm cắt **Double-Fail từ `19,8% → 3,0%`** và hạ xác suất cháy quỹ phí xuống **`0,4%`** (về **`0,0%`** ở ngân sách `1.500 USD`).
- **Quy tắc Tích lũy Tự động 3-Bucket ([treasury_ledger.py](../../tooling/ai-engines/quant_factory/treasury_ledger.py)):**
  - Mọi khoản payout ròng từ Prop Firm được chia cứng tự động: **`30%` Quỹ Dự phòng Phí** (khóa trần `5×` giá vé chuẩn; khi chạm trần, **`100%` phần dư từ payout mới tự động tràn thẳng sang Sổ Vốn Riêng**, nâng dòng chảy vào Own-Book lên `80%` mỗi lần rút!), **`50%` Sổ Vốn Riêng (Own-Book)**, và **`20%` Quỹ Vận hành / VPS / Dự phòng Thuế**.
- **Kỷ luật tâm lý chống Profit Giveback ([trading-psychology-and-profit-giveback-playbook.md](../topics/trading-psychology-and-profit-giveback-playbook.md)):** Tuyệt đối không nhìn PnL theo phút và không đóng tay giữa phiên; mọi can thiệp chỉ được thực hiện ở khung review cuối tuần hoặc khi `Naqex_PropGuard` bật Kill-Switch.

---

## Phase 2 — Kích Hoạt Own-Book Multi-Sleeve Quant Pod v2 (`5k → 25k USD`, Tháng `4–12`)

Khi Sổ Vốn Riêng tích lũy từ payout (hoặc kết hợp vốn mồi tự có) chạm mốc **`5.000–10.000 USD` (`128–255 triệu VND`)**, kích hoạt **Quant Pod v2 (`NCO_CexCap25` hoặc `ERC_LW_CexCap25`)** theo biên nhận [QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md](../../planning/research/QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md):

1. **4 Nhánh Own-Book Chính (không dùng đòn bẩy vay, tổng phơi nhiễm CEX `<= 25%`):**
   - **`S2_CRYPTO_SPOT` (`2,0%–4,9%` trong Pod v2 6 nhánh; nâng tỷ trọng tương ứng khi chưa có S5):** `F4_4H_EMA_24_120_BTC` không survivorship bias (nhánh mã sản xuất `feat/causal-top15-sleeve2`, Cl.B `+5,69%`, `MaxDD 9,72%` khi rổ đều giảm `-38,99%`, [CRYPTO-SLEEVE2-SURVIVORSHIP-FREE-20261124.md](../../planning/research/CRYPTO-SLEEVE2-SURVIVORSHIP-FREE-20261124.md)).
   - **`S3A_FUND_CARRY` (`20,1%–23,0%`, khóa cứng tổng `S2 + S3A <= 25,0%`):** `CARRY_BTC_ETH_CONS_2XBUF` đệm `2×` trên BTC/ETH (Cl.B `Sharpe 9,06`, FTX 11/2022 chỉ `-0,07%`, chỉ mở khi carry ròng vượt lãi suất T-Bill, [SLEEVE3A-FUNDING-RATE-CARRY-20261124.md](../../planning/research/SLEEVE3A-FUNDING-RATE-CARRY-20261124.md)).
   - **`S3B_MACRO_ETF` (`13,3%–15,9%` trên IBKR, `0` swap):** `M5_VOL_PARITY_TREND_GUARD` 12 ETF toàn cầu (Cl.B `+7,58%`, `Sharpe 1,063`, `MaxDD 7,77%`, `GFC -0,02%`, [SLEEVE3B-MACRO-ETF-TREND-18YR-20261124.md](../../planning/research/SLEEVE3B-MACRO-ETF-TREND-18YR-20261124.md)), xuất phiếu lệnh dry-run qua [ibkr_macro_rebalancer.py](../../tooling/ai-engines/quant_factory/ibkr_macro_rebalancer.py).
   - **`S4_ETF40_MULTIFACTOR` (`4,0%–11,1%` trên IBKR, `0` swap):** Tổ hợp 4 chiến lược `E40_APPROVED_EQW_ENSEMBLE` đã đỗ **`4/4 APPROVE_FOR_INCUBATION`** (`E40_VRP_VOL_CARRY`, `E40_CREDIT_HYG_IEF_REGIME`, `E40_XSEC_SECTOR_MOM_TOP4`, `E40_RSI2_CONNORS` — Cl.B mù **`CAGR +7,72%`, `Sharpe 0,992`, `MaxDD 15,66%`, `r(S1_7E) = -0,0155`**, `GFC -2,81%`, `COVID -3,22%`, [LAB4-40ETF-MULTIFACTOR-VRP-20261124.md](../../planning/research/LAB4-40ETF-MULTIFACTOR-VRP-20261124.md)). Tiền mặt nhàn rỗi giữ trong `SGOV`/`BIL`.
2. **Lịch tái cân bằng & Kỷ luật vận hành đơn giản (`KEEP_STATIC_CEXCAP25_DEFAULT`):**
   - Tái cân bằng đúng **`Monthly_1st`** (ngày giao dịch đầu tháng: phí chỉ **`0,45–0,60 bps/năm`**, Blind OOS `ERC_LW_CexCap25` `Sharpe 2,07` / `Calmar 2,48`; `NCO_CexCap25` `Sharpe 1,89` / `Calmar 2,21`). **Không gắn thêm overlay vĩ mô chồng chéo** vì Lab Cycle 4B chứng minh overlay làm tăng `18–34` lần chuyển trạng thái và giảm OOS Calmar `-0,04..-0,18`.
3. **Danh sách CẤM tuyệt đối từ Nghĩa trang Alpha ([alpha-hypothesis-ledger.md](../topics/alpha-hypothesis-ledger.md)):** Không mở Spot Crypto `< 4H` ở phí taker (Lab #1 `0/12`), không chạy Swing đa ngày chịu Swap âm trên FTMO Dầu/Vàng/Chỉ số (Lab #3A `0/12`, Lab #3B `0/9`), không gắn Meta-Labeler ML khi `Brier Skill <= 0` (Lab #6 `REJECT_KEEP_RAW_WHITEBOX`).

---

## Phase 3 — Nhân Thang Đa Quỹ & Mở Khóa Nhánh Có Điều Kiện (`25k → 100k USD`, Tháng `12–24`)

1. **Thang Nhân Danh Nghĩa `LADDER_STAGGER_SCALE` + Điểm Giao Cắt `50k / 100k USD`:**
   - Khi Quỹ Dự phòng Phí đạt `1.500–3.000 USD` từ chính lãi Prop, nâng dần thang đa quỹ (`FTMO + The5ers` lệch pha) lên tổng danh nghĩa `200k–350k USD` (`EV/Phí = +8,00×..+10,71×`, `Wipeout <= 0,1%`).
   - Dữ liệu thực đo từ [MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md](../../planning/research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md) cho thấy: Pure Prop Max Ladder (`3k` phí, `0` vốn mồi) đạt trung vị `45,2k USD` sau 60m (`42,5%` vượt `50k USD`), trong khi **Hybrid Seed `25k USD` + Ladder** đẩy xác suất vượt **`50k USD` (`1,275 tỷ VND`) lên `93,2%` (trung vị `35,2` tháng)** và Hybrid Seed `40k USD` đạt `100%` trong `18,1` tháng (`55,5%` vượt `100k USD`).
2. **Hai Cổng Mở Khóa Có Điều Kiện (Chỉ mở khi vượt Gate — tuyệt đối không nhảy cóc):**
   - **Cổng A — `M2B_BLEND_50_FUND_50_MOM` (Crypto Market-Neutral Maker Stat-Arb, Cl.B `+15,01%`, `r_S2 = -0,2358`):** Chỉ kích hoạt sau khi `crypto_maker_shadow_probe.py` chứng minh **`>= 30` ngày live** đạt tỷ lệ khớp passive-limit touch-through **`>= 70%`** và chi phí thực tế sau adverse selection **`<= 6,15 bps`/chiều/chân** (giữ tổng CEX Pod vẫn `<= 25%`!).
   - **Cổng B — CME Micro Futures Prop (`Topstep 50K`, [LAB5-CME-FUTURES-PROP-STUDY-20261124.md](../../planning/research/LAB5-CME-FUTURES-PROP-STUDY-20261124.md)):** Tuyệt đối **KHÔNG** mang `PORT_7E` chứa FX micro (`M6J` phí `9,810%` biên độ ngày -> EV âm `-0,65×`). Chỉ mở `Topstep 50K` khi hoàn thiện đủ `5–6` động cơ thuần **`MNQ + MES + MGC + MCL`** vượt toàn bộ 6 cổng Hội đồng Nghiên cứu (khi đó `EV/USD phí` đạt cận trên `+5,43×..+7,78×`).

---

## Phase 4 — Định Chế Hóa Sổ Vốn Riêng & Khiên Rủi Ro VND (`100k → 200k+ USD`, Năm `2+`)

1. **Vượt ngưỡng `Crossover` sang Sổ Vốn Riêng chủ đạo ([capital-scaling-prop-to-own-book.md](../topics/capital-scaling-prop-to-own-book.md)):**
   - Khi thu nhập kỳ vọng ròng từ Own-Book Pod vượt dòng tiền sau split/haircut của Prop Firm, giảm tỷ trọng phụ thuộc Prop Firm về vai trò dòng tiền bổ trợ không rủi ro vốn gốc; chuyển trọng tâm sang lãi kép bền vững trên IBKR (cổ phiếu/ETF/T-Bill lưu ký tách biệt) + lưu ký tối thiểu trên sàn CEX.
2. **Khiên Rủi Ro Tuyệt Đối Bằng `USD` & `VND` (`25.500 VND/USD`, Chuẩn [PROFILE.md](../owner/PROFILE.md) §3):**
   - Tại mốc **`200.000 USD` (`5,10 tỷ VND`)**, kịch bản sập sàn CEX mất **`-50%`**:
     - `HRP` không trần (phơi nhiễm CEX `83,0%`) mất **`-41,58%` = `-83.160 USD` (`-2.121 triệu VND`)** -> **CẤM SỬ DỤNG**.
     - `NCO_Capped35` (chỉ trần từng nhánh `35%`, CEX cộng dồn `41,5%`) mất **`-21,05%` = `-42.100 USD` (`-1.074 triệu VND`)** -> **QUÁ NGƯỠNG**.
     - **`NCO_CexCap25`** (trần nhóm CEX tổng **`<= 25,0%`**) khóa cứng thiệt hại ở **`-12,89%` = `-25.780 USD` (`-657 triệu VND`)** (và tại mốc `50k USD` chỉ còn **`-6.445 USD` = `-164,3 triệu VND`**, vùng `CAUTION_AMBER`; trong khủng hoảng tương quan `Corr = 0,85` P99 chỉ **`-8,81%`**).
3. **Báo cáo Kiểm toán Tháng & Quản trị Quý:**
   - Xuất báo cáo GIPS-Lite hằng tháng bằng [treasury_ledger.py](../../tooling/ai-engines/quant_factory/treasury_ledger.py) (tách bạch rõ lịch sử live thật với mô phỏng Dev) và tuân thủ lịch rà soát định kỳ 4 quý/năm trong [quarterly-quant-governance-playbook.md](../topics/quarterly-quant-governance-playbook.md).

---

## Phase 5 — Giao Thức Mở Khóa 1 Lần Duy Nhất Holdout `2025–2026` (Cho Thế Hệ Động Cơ v2)

`NATIVE_FTMO_HOLDOUT_LOCK.json` (`SHA-256: f0a6b43cb205535b...`) giữ niêm phong tuyệt đối **`holdout_rows_analysed = 0`** trong toàn bộ quá trình nghiên cứu v2 (như `V08_PORT9E_CAUSAL_ERC` có trần rủi ro `<= 0,75%` hoặc bộ động cơ thuần CME `MES/MCL`). Chỉ được phép mở **1 lần duy nhất không thể đảo ngược** khi thỏa đồng thời **tất cả 6 điều kiện khóa cứng**:

1. **Đủ thời lượng thực chiến v1:** Hệ thống lõi `PORT_7E` đã hoàn thành tối thiểu `90` ngày giao dịch forward (Demo/Live) với đối soát TCA đầy đủ.
2. **Đóng băng 100% mã nguồn & tham số:** Mọi ứng viên v2 đã vượt toàn bộ 6 cổng `SkepticalRedTeamCritic` trên Dev (`< 2025-01-01`), có mã nguồn & cấu hình đóng băng thành commit có SHA-256 ghi nhận trước trong `DECISIONS-JOURNAL.md`.
3. **Đặt tiêu chí Đạt/Trượt trước khi mở (*Pre-Registered Pass/Fail*):** Ghi rõ ngưỡng tối thiểu về `CAGR`, `Calmar`, `MaxDD`, `PF`, và `tỷ lệ động cơ dương` trước khi chạm bất kỳ dòng dữ liệu `2025+` nào.
4. **Xác nhận bằng lệnh trực tiếp của Owner:** AI không bao giờ tự quyền mở Holdout; phải có lệnh chấp thuận tường minh của chủ sở hữu trong phiên chạy.
5. **Một lần bắn duy nhất (*One-Shot Execution*):** Chạy đúng 1 lệnh kiểm toán độc lập sinh biên nhận bất biến; nếu trượt, **khai tử ứng viên ngay lập tức**, cấm tinh chỉnh tham số rồi chạy lại trên tập `2025–2026`.
6. **Chuyển mốc niêm phong mới:** Ngay sau lượt mở v2, khóa toàn bộ dữ liệu từ `2027+` làm Holdout niêm phong thế hệ tiếp theo.
