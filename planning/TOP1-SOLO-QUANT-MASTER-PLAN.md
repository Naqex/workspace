---
doc_type: plan
domain: strategy-and-operations
status: active
ssot_role: SINGLE_ROADMAP_OWNER
updated_utc: 2026-11-27
order_send_count: 0
holdout_rows_analysed: 0
holdout_v1_2025_2026: "CONSUMED (commit 521926f)"
holdout_v2_prospective: "SEALED (>= 2026-12-01)"
active_candidate: "C10_NEWS_ON"
master_ea: "tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5"
owner: "knowledge/owner/PROFILE.md"
---

# Kế Hoạch Tổng Thể Naqex — Nguồn Sự Thật Duy Nhất (Single Roadmap SSOT)

> **Quy tắc chủ quyền tài liệu:** Đây là **bản kế hoạch và lộ trình hành động duy nhất (Single Roadmap SSOT)** của Naqex Workspace. Mọi tài liệu lộ trình phụ ([PROP-SYSTEM-ROADMAP.md](research/PROP-SYSTEM-ROADMAP.md), [naqex-master-roadmap-2026-2027.md](../knowledge/playbooks/naqex-master-roadmap-2026-2027.md)) đều trỏ trực tiếp về đây; khi có khác biệt với các ghi chú lịch sử trước ngày `25/11/2026`, tài liệu này luôn có hiệu lực cao nhất.
>
> **Trạng thái hiện hành (`27/11/2026` — Chốt sau Vòng 3 & Bước 8):**
> - **Ứng viên duy nhất đang theo dõi:** **`C10_NEWS_ON`** chạy trên **`1` Master EA duy nhất** ([Naqex_Master_Prop7E.mq5](../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5), bản `v1.01`, đội hình cố định **`7E`** `E1..E7` xuyên cả 3 pha `P1 -> P2 -> Funded`, kèm lịch tin đỏ **`492` sự kiện** tại `naqex_red_news_utc.csv`).
> - **Tài chính & thực thi:** **`0 VND`** đã chi · **`OrderSend = 0`** trên toàn bộ công cụ nghiên cứu · **Năm 1 = `0 VND`** kỳ vọng thu nhập từ trading · `naqex-node1` chạy độc lập, chỉ đọc khi kiểm tra.
> - **Trạng thái Holdout trung thực (tách rõ 2 mốc):**
>   - **`holdout_v1` (`2025-01-02..2026-11-20`, commit `521926f`):** **`CONSUMED`** (đã mở 1 lần duy nhất cho bản nền v1 — [HOLDOUT-2025-2026-ONE-TIME-VERDICT-20261123.md](research/HOLDOUT-2025-2026-ONE-TIME-VERDICT-20261123.md)).
>   - **`holdout_v2_prospective` (`>= 2026-12-01`) & khóa Dev (`< 2025-01-01`):** **`SEALED`** (`holdout_rows_analysed = 0`, khóa SHA `f0a6b43cb205535b` trong [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json)).

---

## 1. Kiến Trúc & Ràng Buộc Đã Khóa Cứng (Vòng 3 + Bước 8)

Toàn bộ các giả định cũ trước Vòng 3 đã bị **gỡ bỏ vĩnh viễn** để loại bỏ hoàn toàn mâu thuẫn nội bộ:

| Hạng mục | Quy chuẩn hiện hành (ĐANG HIỆU LỰC) | Quy chuẩn cũ đã gỡ bỏ (KHÔNG CÒN DÙNG) |
|---|---|---|
| **Đội hình động cơ** | Cố định **`7E` (`E1..E7`)** xuyên cả 3 pha `P1 / P2 / Funded` + khóa cụm hướng (`USD 2,25%` / `JPY 2,00%` / `US100 1,75%` / Tổng `3,00%`), mặc định `STATIC_LOCK`. | ~~Đội hình `8E` / `9E` ghép vệ tinh `S6/S7` cho P1~~ |
| **Kiến trúc thực thi MT5** | **`1` Master EA/tài khoản** (`Naqex_Master_Prop7E.mq5`, ứng viên **`C10_NEWS_ON`**, `492` sự kiện tin đỏ `6` đồng tiền `naqex_red_news_utc.csv`). | ~~Dàn `8` EA rời + `1` Orchestrator (`9` chart riêng)~~ |
| **Thước đo & mở rộng quy mô** | Tiền mặt thực thu đã về ví (**`Settled Cash`**) & ngày lịch thật; chỉ xét nâng bậc khi đủ **`>= 2` chu kỳ rút tiền thật** + **đã hoàn gốc 100%** + **còn đệm `>= 2×` giá vé mới** ([treasury_ledger.py](../tooling/ai-engines/quant_factory/treasury_ledger.py)); mốc `100K` chỉ là giả thuyết dài hạn. | ~~Thang `350K`~~ · ~~Cổng mua mù `Gate-42`~~ · ~~Mua thẳng `The5ers 20K`~~ · ~~Chia cứng `30/50/20` trước khi hoàn gốc~~ |
| **Phạm vi sản xuất & Own-Book** | Tập trung 1 bài toán chính (**FTMO 10K**; **The5ers HS 5K** chấm điểm song song từ cùng sổ hợp đồng [firms_catalog.json](../tooling/ai-engines/configs/ssot/firms_catalog.json)). Dưới **`10.000 USD`** vốn riêng chỉ giữ tiền mặt/T-Bill; **tác vụ Crypto Shadow/Maker trên `naqex-node1` đang TẮT**. | ~~Chạy Crypto Shadow/Maker 24/7 trên `naqex-node1` khi vốn riêng = `0 USD`~~ · ~~Mở Own-Book phức hợp ở vốn `5k USD`~~ |
| **Toán học báo cáo bắt buộc** | Mọi báo cáo xác suất tại mốc thời gian cố định phải tách rõ **3 trạng thái `Đậu + Rớt + Chờ = 100%`** (theo 1 vé không thử lại; đa vé tách riêng kèm trần phí). Đa dạng hóa nâng Sharpe/độ êm, **không tự nhân lãi năm không đòn bẩy `1×`**. | ~~Ghi đồng thời đậu `85%–95%` và rớt `22%–35%` trên cùng 1 vé~~ |
| **Kiểm toán nội bộ** | Đã khép lại chuỗi Astra bên ngoài (`Vòng 1–11`) và thay thế bằng quy trình **7 mũi phản biện nội bộ** ([adversarial-self-audit](../.agents/skills/adversarial-self-audit/SKILL.md)) + bộ cổng kiến trúc `check_architecture.py` (`ARCH-01..07`) + `Hypothesis`/`ruff`/`ty`. | ~~Chép prompt kiểm toán tay bên ngoài cho từng thay đổi nhỏ~~ |

---

## 2. Điểm Neo Hiện Tại & Khoảng Cách Tới Top 1% Thực Tế (Chuẩn Luật 15)

*Cấp độ bằng chứng: Backtest Dev `2018–2024` (`DAILY_APPROX`, `Cluster B` đã xem) + `holdout_v1` đã mở cho v1 nền (`521926f`) + `28` lệnh đo sống FTMO Demo (`0,66×`) — **CHƯA có Holdout `v2_prospective` cho `C10_NEWS_ON`, CHƯA có tháng tiền thật đã rút (`0 VND`)**.*
*Ví dụ quy đổi chuẩn (`FTMO 2-Step Standard 100K`, `C10_NEWS_ON`, ma sát `1,00×`, tỷ giá SSOT [fx_rates.json](../tooling/ai-engines/configs/ssot/fx_rates.json), `1 USD ~ 25.500–26.300 VND` tùy thời điểm):*

- **Winrate / RR / EV mỗi lệnh:** `48,6%` · `1,27×` · **`+0,049R`** (`2.882` lệnh Dev) -> **`🟡 Đủ dùng`** *(Thang: `🔴 <= 0R` · `🟡 +0,03..+0,06R` · `🟢 +0,07..+0,15R` · `🏆 > +0,15R` tiền thật)*
- **Profit Factor:** **`1,20`** -> **`🟡 Đủ dùng`** *(Thang: `🔴 < 1,05` · `🟡 1,10..1,20` · `🟢 1,25..1,50` · `🏆 1,50..2,00+` tiền thật `>= 12T`)*
- **Max DD (`1,0×`) / Calmar / Sharpe:** `8,62%` · `Calmar 0,86` · `Sharpe 1,23` (`+7,41%/năm` Dev) -> **`🟡 Đủ dùng` (DD/Calmar)** · **`🟢 Tốt` (Sharpe quá khứ)** *(Thang Calmar: `🔴 < 0,5` · `🟡 0,6..1,0` · `🟢 1,2..2,0` · `🏆 > 2,0..3,0` tiền thật)*
- **Xác suất 1 vé không thử lại (`Đậu / Rớt / Chờ = 100%`):**
  - `3` tháng: `14,7% / 2,4% / 83,0%` (`100%`)
  - `6` tháng: `32,6% / 3,3% / 64,1%` (`100%`)
  - `12` tháng: `47,4% / 4,4% / 48,2%` (`100%`)
  - `24` tháng: **`62,7% / 6,1% / 31,2%` (`100%`)** · `NPV 24T`: TB `+161,9 tr VND` (`+12,81×` phí), trung vị `+85,9 tr VND`, `P(<=0) = 40,2%` (tại ma sát `1,50×`, trung vị tụt về `-12,6 tr VND`, `P(<=0) = 62,2%`).
- **Điểm nghẽn cấu trúc & ngưỡng gãy:** **`60%`** tháng Funded không có payout (`P50 = 8` tháng đói, chờ lần rút đầu trung vị `265` ngày) do 7 động cơ cùng 1 họ intraday CFD. **Ngưỡng gãy trượt giá:** hòa vốn kỳ vọng ở **`2,31×`**, cắt cứng dừng mua vé mới ở **`> 1,75×`** (chỉ xem xét khi ma sát thực đo `<= 1,50×`).
- **Khoảng cách tới `🏆 Top 1%`:** (1) Chưa có **`>= 12` tháng tiền thật đã rút**; (2) Chưa có nhánh lợi nhuận lệch pha thứ 2 (`|r| < 0,15`) vận hành song song để kéo tháng đói từ `60%` về `< 35%`; (3) Mới đo `28` lệnh Demo FTMO, `0` lệnh sống trên The5ers/IC Funded (`TERMS_VERIFIED_EXECUTION_UNMEASURED`).

---

## 3. Khung Quản Trị 4 Trụ Cột Thực Thi

### 3.1. Phân loại sự cố 4 tầng bắt buộc (`R4 -> R3 -> R2 -> R1`)
Mọi sai lệch số liệu hoặc chuỗi lỗ đều chẩn đoán ngược từ ngoài vào trong — cấm vội sửa tham số bot khi chưa loại sạch `R4/R3/R2`:
1. **`R4` — Luật quỹ, Sàn & Tâm lý con người:** Tin đỏ `±2p` (bot khóa rộng hơn `±5p`), thư xác nhận EA bằng văn bản, IP sạch cố định, và kỷ luật không bấm tay đóng lệnh giữa phiên.
2. **`R3` — Khớp lệnh, Trượt giá & Hạ tầng:** Đối chiếu tự động hàng ngày (`daily_statement_reconciler.py`) giữa sao kê MT5, `naqex_exec_audit.csv`, và đường cong Markout (`+1s/+10s/+60s/+5m`, `quant_core/tca.py`), kiểm `swap_usd == 0,00` fail-closed, đồng hồ NTP `< 1.000 ms`.
3. **`R2` — Rủi ro Danh mục & Phơi nhiễm Cụm:** Khóa cụm hướng `7E` (`USD 2,25% / JPY 2,00% / US100 1,75% / Tổng 3,00%`), `SYMCAP`, và khi có Own-Book sau này giữ trần tổng sàn tập trung CEX **`<= 25%`**.
4. **`R1` — Suy giảm Lợi thế Thật của Chiến lược:** Chỉ xử lý khi `R4/R3/R2` sạch hoàn toàn, dựa trên giám sát thống kê (`CUSUM/SPRT` tại `live_decay_monitor.py`) và bộ kiểm định chống overfit (`DSR + PBO/CSCV + CPCV + Hansen SPA` tại `quant_core/metrics.py`).

### 3.2. Kỷ luật vốn & Quy tắc chia tiền sau hoàn gốc (`Settled Cash`)
- **Trước khi hoàn 100% vốn gốc đã chi:** Không phân bổ phức hợp; ưu tiên tích lũy tiền mặt rút về cho tới khi hoàn đủ `100%` chi phí vé đã bỏ ra + dự phòng tối thiểu `2×` giá vé kế tiếp.
- **Sau khi hoàn gốc + đạt `>= 2` kỳ payout thật:** Mọi quyết định nâng quy mô hoặc mở nhánh Own-Book được ghi sổ bắt buộc qua [treasury_ledger.py](../tooling/ai-engines/quant_factory/treasury_ledger.py) theo ngưỡng vốn thực tế:
  - **`< 10.000 USD` vốn riêng:** Giữ tiền mặt / T-Bill ngắn hạn (không mở Own-Book đa nhánh phức hợp để tránh bẫy phí tối thiểu).
  - **`10.000 – 25.000 USD`:** Xem xét ETF gọn ít lệnh (`S3B` / `L7_TOP2`, `0` swap).
  - **`25.000 – 50.000 USD`:** Xem xét mở thêm Crypto Spot nhân quả (`S2`) và Funding Carry (`S3A`, giữ trần tổng CEX `<= 25%`).
  - **`>= 50.000 USD`:** Xem xét rổ ETF đầy đủ lô nguyên (`S4`); **`>= 100.000 USD`** mới xét CME Micro Futures.
- **Tự nuôi hạ tầng (`0 USD` -> trích `<= 10%` lãi ròng thật):** Giữ Home-VPS `naqex-node1` + Heroku Deadman (`12 USD/tháng <= 13 USD/tháng` gói Student đến `2028-09-30`, nhắc kiểm tra `2028-09-25`). Chỉ thuê VPS sát sàn LD4/NY4 (`25–40 USD/tháng`) khi lãi rút ổn định **`>= 300 USD/tháng`**.

### 3.3. Kiến trúc điện toán 3 máy (Star Topology — OPSEC 2 lớp)
Theo [THREE-NODE-COMPUTE-ORCHESTRATION-AND-SYNC-BLUEPRINT-20261127.md](research/THREE-NODE-COMPUTE-ORCHESTRATION-AND-SYNC-BLUEPRINT-20261127.md) (IP thật nằm riêng trong `private_vault/ops/`):
- **`<DEV_PC>`:** Trung tâm duy nhất cho Git, kiểm định, và giữ khóa `Holdout`; điều phối việc offline `<= 60` phút qua `compute_router.py` (`Mode A`: `2–3` nhân `BelowNormal` `0%` GPU khi dùng máy/chơi game; `Mode B`: `5/6` nhân + chia tải khi rảnh).
- **`<X13_WORKER>`:** Máy tính toán CPU Dev-only (`<= 2024`, `0` Holdout, `0` bí mật), bắt buộc cắm sạc AC (`ACLineStatus == 1`), tự lùi êm về `<DEV_PC>` nếu tắt/rút sạc/lệch NTP `>= 1.000 ms`.
- **`naqex-node1`:** Tầng thực thi 24/5 cô lập tuyệt đối (`OrderSend = 0` trên mọi script quản trị, `node_ctl.py` chỉ đọc, cấm cài AI CLI/Node/Docker, cấm chạy backtest, cấm nối trực tiếp sang `<X13_WORKER>`).

### 3.4. Danh sách CẤM tuyệt đối (đã chứng minh thất bại — không làm lại)
- Không chạy Crypto Spot khung `< 4H` chịu phí Taker (`Lab #1: 0/12`).
- Không giữ lệnh CFD Vàng/Dầu/Chỉ số qua đêm chịu Swap âm trên tài khoản quỹ (`Labs #3A/#3B: 0/21`).
- Không cày thêm biến thể CFD intraday `swap = 0` trong không gian đã bão hòa (`Labs #11–#12: 0/36`, `Pass 29–31: 0/66`).
- Không dùng lưới gồng lỗ (`grid`), gấp thếp (`martingale`), hoặc chèn bộ lọc ML lên chiến lược trắng khi `Brier Skill <= 0` (`Lab #6`).

---

## 4. Lộ Trình Thực Thi 4 Mốc Theo Cổng Bằng Chứng (`Mốc 0 -> Mốc 3`)

Không chờ đợi thụ động — luôn giữ khóa cổng tiền thật/Holdout trong khi đẩy song song hạ tầng kiểm chứng, đối soát TCA, nhánh Alpha #2 trên Dev, và sản phẩm tạo dòng tiền trong `projects/`.

| Mốc | Trạng thái & Trọng tâm | Trần chi phí | Cổng qua cửa bắt buộc (Exit Gate) | Điểm dừng cứng (Kill Criteria) |
|---|---|---|---|---|
| **Mốc 0 — Xác Minh Thực Địa & Đồng Bộ** *(Hiện tại)* | 1. Hoàn tất đồng bộ kỹ thuật `C10_NEWS_ON` trên `Naqex_Master_Prop7E.mq5` (`v1.01/v1.02` đã chốt parity) + lịch tin đỏ `492` dòng.<br>2. Đồng bộ NTP `< 1.000 ms` trên `<DEV_PC>` & `<X13_WORKER>` trước thu thập `QUOTE_ONLY` quanh **NFP `04/12/2026`** & **CPI `10/12/2026`**.<br>3. Thu đủ bằng chứng Demo đọc-thuần & đối soát tự động hàng ngày (`daily_statement_reconciler.py`, Markout `+1s..+5m`, `swap == 0`).<br>4. Nhận & lưu thư xác nhận EA bằng văn bản từ FTMO / The5ers (`Terms §11`). | **`0 VND`** | - `0` lỗi parity/restart, `0` lệnh thiếu SL, `0` `FILL_UNRESOLVED`, `swap_usd == 0,00`.<br>- Trượt giá bất lợi thực `<= 1,50×` giả định.<br>- Có thư xác nhận bằng văn bản từ quỹ.<br>- `check_workspace`, `check_architecture --strict`, `system_doctor --mode full` xanh 100%. | Trượt giá thực `> 1,75×`, phát sinh lỗi `R3` mất cắt lỗ, hoặc chưa có thư xác nhận quỹ -> **chặn tuyệt đối không chi tiền**. |
| **Mốc 1 — Thí Điểm Tài Khoản Quỹ Kỷ Luật (`Settled Cash`)** | 1. Chỉ khởi động khi chủ sở hữu phê duyệt tường minh cổng `G6` sau khi Mốc 0 xanh toàn bộ.<br>2. Chạy cố định `7E` (`C10_NEWS_ON`) trên `1` Master EA (`Naqex_Master_Prop7E.mq5`), tập trung bài toán chính `FTMO 10K` (so sánh song song `The5ers HS 5K` theo bộ tối ưu `prop_capital_promo_optimizer`).<br>3. Ghi sổ 100% dòng tiền vào `treasury_ledger.py`; **không nâng bậc** trước khi hoàn gốc. | Trong ngân sách chủ sở hữu phê duyệt (`Năm 1 = 0 VND` kỳ vọng thu nhập) | - Đạt **`>= 2` kỳ payout thực nhận về ví (`Settled Cash`)**.<br>- Đã **hoàn 100% vốn gốc** + còn đệm **`>= 2×`** giá vé kế tiếp.<br>- `0` vi phạm kỷ luật can thiệp tay; trượt giá thực ổn định `<= 1,50×`. | Chuỗi `3` vé rớt liên tiếp hoặc trượt giá thực `> 1,75×` hoặc `CUSUM` báo suy giảm `R1` -> **dừng mua vé mới**, chạy kiểm toán `R4 -> R1`. |
| **Mốc 2 — Nhánh Alpha #2 Lệch Pha & Dòng Tiền Kép** *(Chạy song song trên Dev)* | 1. Chuẩn hóa nhánh ngoài MT5 (`projects/quant-trading` Crypto Spot / Funding Carry) chạy **1 động cơ duy nhất** (Backtest ↔ Paper/Shadow) có đủ cổng `DSR + PBO <= 0,50 + CPCV + Hansen SPA` và sổ thí nghiệm `experiment_ledger.py` (`DuckDB + run_registry`).<br>2. Đẩy 1 sản phẩm tạo dòng tiền độc lập (`projects/vi-dubber` sau khi xử lý giấy phép `diffq-fixed` hoặc module `projects/trader`) để giảm áp lực tâm lý trong chuỗi tháng đói. | **`0 USD`** cho R&D offline | - Nhánh #2 chứng minh `|r| < 0,15` với `PORT_7E`, vượt đủ 6 cổng Dev (`< 2025-01-01`) + `PBO <= 0,50`, giảm tháng đói danh mục về `< 35%`.<br>- Có lịch sử Shadow khớp 100% với replay. | `PBO > 0,50` hoặc `|r| >= 0,30` với `7E` -> **loại thẳng ứng viên**, không ghép. |
| **Mốc 3 — Holdout `v2_prospective` (`>= 2026-12-01`) & Own-Book `10k+`** | 1. Chỉ mở **`holdout_v2_prospective` (`>= 2026-12-01`)** đúng **1 lần duy nhất** khi đủ `>= 90` ngày chạy thực địa v1, mã v2 đóng băng có SHA-256 + tiêu chí Đạt/Trượt đăng ký trước, và có lệnh duyệt trực tiếp của chủ sở hữu.<br>2. Kích hoạt Own-Book theo bậc vốn thực (`10k+` ETF gọn -> `25k+` thêm Crypto/Carry `CEX <= 25%` -> `50k+` ETF đầy đủ).<br>3. Thuê VPS sát sàn khi lãi rút ổn định `>= 300 USD/tháng`. | Hạ tầng `<= 10%` lãi ròng thực (`25–40 USD/tháng` từ lãi) | - Vượt trọn tiêu chí đã đăng ký trên `holdout_v2_prospective`.<br>- Đạt `>= 12` tháng lịch sử tiền thật kiểm toán GIPS-Lite, `>= 2–3` nhánh lệch pha chạy song song. | Trượt `holdout_v2_prospective` -> **khai tử ứng viên v2 ngay**, tuyệt đối không chỉnh tham số để chạy lại. |

---

## 5. Tài Liệu & Mã Nguồn Cốt Lõi Liên Kết

- **Điều hướng nhanh & trạng thái hiện tại:** [CURRENT-CONTEXT.md](CURRENT-CONTEXT.md) · [REPO-MAP.md](../docs/REPO-MAP.md) · [PORTFOLIO-REGISTRY.json](research/PORTFOLIO-REGISTRY.json) · [Chỉ mục Research](research/README.md)
- **Hợp đồng SSOT & bộ cổng tự động:** [firms_catalog.json](../tooling/ai-engines/configs/ssot/firms_catalog.json) · [risk_profiles.json](../tooling/ai-engines/configs/ssot/risk_profiles.json) · [fx_rates.json](../tooling/ai-engines/configs/ssot/fx_rates.json) · [check_architecture.py](../tooling/check_architecture.py)
- **Kiểm toán & kiến trúc nền tảng (`25–27/11/2026`):**
  - [TOP1-PCT-QUANT-SYSTEMS-AND-AI-AGENT-GAP-AUDIT-20261127.md](research/TOP1-PCT-QUANT-SYSTEMS-AND-AI-AGENT-GAP-AUDIT-20261127.md)
  - [THREE-NODE-COMPUTE-ORCHESTRATION-AND-SYNC-BLUEPRINT-20261127.md](research/THREE-NODE-COMPUTE-ORCHESTRATION-AND-SYNC-BLUEPRINT-20261127.md)
  - [MULTI-FIRM-CAPITAL-PROMO-OPTIMIZER-20261126.md](research/MULTI-FIRM-CAPITAL-PROMO-OPTIMIZER-20261126.md)
  - [STEP7-ASTRA-R10-CLOSURES-AND-ROUND11-AUDIT-20261126.md](research/STEP7-ASTRA-R10-CLOSURES-AND-ROUND11-AUDIT-20261126.md)
  - [ASTRA-ROUND3-FIRST-PRINCIPLES-ARCHITECTURE-AND-STRATEGY-20261125.md](research/ASTRA-ROUND3-FIRST-PRINCIPLES-ARCHITECTURE-AND-STRATEGY-20261125.md)
  - [ROUND3-FRAME-COUNTERFACTUAL-BENCHMARK-20261125.md](research/ROUND3-FRAME-COUNTERFACTUAL-BENCHMARK-20261125.md)
  - [RED-NEWS-2025-ERRATA-AND-6CCY-SOURCES-20261127.md](research/RED-NEWS-2025-ERRATA-AND-6CCY-SOURCES-20261127.md)
  - [ECOSYSTEM-SECURITY-LICENSE-AUDIT-20261127.md](research/ECOSYSTEM-SECURITY-LICENSE-AUDIT-20261127.md)
- **Vận hành, Pháp lý & Niêm phong:** [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md) · [naqex-node-ops](../.agents/skills/naqex-node-ops/SKILL.md) · [adversarial-self-audit](../.agents/skills/adversarial-self-audit/SKILL.md) · [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json)
