---
doc_type: evergreen
domain: knowledge
topic: capital-scaling-prop-to-own-book
updated_utc: 2026-11-23
sources:
  - "T1: FTMO Official Scaling & Payout Terms (ftmo.com) · The5ers High Stakes & Hyper Growth Rules (the5ers.com)"
  - "T1: Topstep Express Funded / Live Rules (topstep.com) · Apex Trader Funding Safety Net & Trailing Rules (apextraderfunding.com)"
  - "T1 (Đo nội bộ): PRE-HOLDOUT-READINESS-AND-BLINDSPOT-AUDIT-20261123.md, HOLDOUT-2025-2026-ONE-TIME-VERDICT-20261123.md, CRYPTO-SLEEVE2-AND-QUANT-POD-STUDY-20261123.md"
  - "T2/T3: Reddit r/Daytrading, r/Trading & r/algotrading — thực tế phễu pass/payout, bẫy intraday trailing drawdown và điểm hòa vốn vốn riêng vs prop"
---

# Toán học Tăng trưởng Vốn: Từ Prop Firm (Đa quỹ) đến Sổ Vốn Riêng 4-Sleeve Quant Pod

> Tài liệu giải bài toán tài chính thực dụng cho owner: **khi nào tiền thi Prop Firm sinh lời vượt trội so với vốn tự có, khi nào vốn riêng thắng áp đảo**, cách đa dạng hóa đa quỹ (`FTMO + The5ers + Futures props`) mà không dính bẫy luật ẩn, kỷ luật giữ đệm rút tiền, và lộ trình thực tế `24` tháng từ **`0` lịch sử live → Multi-Prop → Sổ vốn riêng 4 nhánh**.

---

## 1. Bản chất toán học của Prop Firm: Bạn KHÔNG sở hữu 100.000 USD — Bạn đang thuê 10.000 USD quỹ chịu lỗ

### 1.1. Khái niệm "Vốn Rủi Ro Hiệu Dụng" (*Effective Risk Capital*, `ERC`)
Một sai lầm phổ biến nhất của retail (T3 Reddit) là nhìn vào số dư danh nghĩa (`100.000 USD`). Về mặt toán học, một tài khoản FTMO `100.000 USD` có Max Loss tĩnh `10%` chỉ cho bạn đúng **`10.000 USD` vốn chịu lỗ thực (`ERC = 10.000 USD`)** — chạm `-10.000 USD` là mất trắng quyền giao dịch.

Tuy nhiên, **lợi thế bất đối xứng (asymmetric payoff)** của Prop Firm lại nằm ở **chi phí để thuê `ERC` đó**:
- **Với vốn cá nhân:** Để có `10.000 USD` chịu lỗ an toàn ở cùng mức rủi ro (`MaxDD 10%` của danh mục, hoặc ký quỹ đủ đòn bẩy thấp không bị margin call), bạn cần bỏ thật khoảng **`10.000–100.000 USD`** tiền túi (tùy đòn bẩy broker và độ chịu đau của owner theo [Hồ sơ Owner](../owner/PROFILE.md) — vốn lớn coi DD `15%–20%` là quá cao).
- **Với Prop Firm:** Bạn chỉ trả phí thi **`F`** (ví dụ FTMO `10.000 USD` phí `168 USD` cho `ERC = 1.000 USD`; FTMO `100.000 USD` phí `~580–600 USD` cho `ERC = 10.000 USD`; The5ers High Stakes `5.000 USD` phí `39 USD` cho `ERC = 500 USD`).

### 1.2. Công thức điểm hòa vốn: Khi nào Vốn Cá Nhân thắng Prop Firm?
Gọi:
- `C_own`: vốn tiền mặt tự có dùng cho nhánh FX/Index (USD).
- `r_ann`: lợi suất ròng hàng năm của hệ thống ở mức rủi ro chuẩn (với `PORT_7E`: `~8%–12%/năm` ở `PeakDD 6,5%`, hoặc gấp `k×` trên vốn riêng nếu chấp nhận `PeakDD` lớn hơn).
- `N_prop`: tổng danh nghĩa các tài khoản Prop đã Funded (USD), chia lợi nhuận `s` (thường `0,80–0,90`).
- `E_fee`: tổng chi phí thi/thi lại kỳ vọng mỗi năm (kể cả xác suất rớt vòng và thời gian chờ trung vị `T_pass`, cộng rủi ro bị từ chối payout / đổi luật quỹ `p_firm`).
- `drag_rule`: chi phí ẩn do ràng buộc quỹ (trần `1%/mã`, khóa tin đỏ `±5m`, không được giữ swap dương dài ngày hoặc phải chia lợi nhuận `10%–20%`).

So sánh lợi nhuận ròng sau 1 năm:
- **Sổ vốn riêng (100% quyền giữ lãi, không chia `s`, không giới hạn rút):**
  `Net_Own = C_own * r_own`
- **Sổ Prop Funded (sau chia lợi nhuận, trừ phí thi kỳ vọng và thời gian chết chưa Funded):**
  `Net_Prop = N_prop * r_prop * s * (1 - p_firm) - E_fee`

**Bảng quy đổi trực tiếp (lấy mức lợi suất thực chứng `PORT_7E` = `10%/năm` bảo thủ giữa Dev `7,7%` và Holdout `12,7%`, chia `80%`, phí thi hiệu dụng bình quân `1,25×` vé):**

| Quy mô danh nghĩa / Vốn thật | Chi phí tiền túi tối đa (`OOP95`) | Lãi ròng kỳ vọng/năm (USD) | Tỷ suất trên tiền túi (`ROI/OOP`) | Nhận xét chiến lược |
|---|---:|---:|---:|---|
| **The5ers HS `5.000 USD`** (Prop 2-Step) | `39 USD` | `~320–400 USD/năm` *(sau khi Funded)* | **`~800%+`** | Rẻ nhất để mua dữ liệu thực chiến + xác minh quy trình rút tiền |
| **FTMO `10.000 USD`** (Prop 2-Step) | `168 USD` | `~640–960 USD/năm` *(sau khi Funded)* | **`~380%–570%`** | Điểm vào chuẩn đầu tiên sau Free Trial; `CF24` đo thực nghiệm `+642..+647 USD` ([Pre-Holdout Audit](../../planning/research/PRE-HOLDOUT-READINESS-AND-BLINDSPOT-AUDIT-20261123.md)) |
| **Multi-Prop `150.000 USD`** (vd FTMO `100k` + The5ers `50k`) | `~850–1.200 USD` | **`~10.000–13.500 USD/năm`** | **`> 800%`** | **Đỉnh hiệu quả vốn cho giai đoạn tích lũy `6–18` tháng đầu** |
| **Vốn cá nhân `10.000 USD`** (chạy `PORT_7E @ 1,5×`, DD ~`9%–10%`) | `10.000 USD` | `~1.200–1.800 USD/năm` | `12%–18%` | Kém hiệu quả vốn hơn Prop nếu phải khóa `10k` tiền mặt |
| **Vốn cá nhân `50.000 USD`** (ghép **Quant Pod**: FX `1,5×` + Crypto Spot `0,75×`, CAGR ~`23%`, DD ~`10%`) | `50.000 USD` | **`~10.000–11.500 USD/năm`** | **`20%–23%`** | **Ngưỡng hòa vốn quan trọng:** ngang Multi-Prop `150k` về tiền mặt tuyệt đối nhưng **`0` rủi ro khóa tài khoản quỹ** và mở được nhánh Crypto Spot! |
| **Vốn cá nhân `100.000+ USD`** (4-Sleeve Quant Pod) | `100.000+ USD` | **`~20.000–25.000+ USD/năm`** | **`20%–25%`** | **Vốn cá nhân thắng tuyệt đối:** giữ `100%` lãi, không bị trần `1%`/mã, dùng được chiến lược giữ qua đêm/swap-free/Crypto/Options, tự do rút tiền mọi lúc. |

> **Quy tắc điểm chuyển pha (Breakeven Rule):**
> - **Khi vốn dành riêng cho trading `< 30.000 USD`:** **Prop Firm thắng áp đảo** nhờ đòn bẩy chi phí (`OOP` nhỏ, lỗ tối đa khóa cứng bằng vé thi). Nhiệm vụ của Prop là **bộ máy in vốn mồi** (cashflow generator) để đổ vào sổ cá nhân.
> - **Khi vốn tự có cho trading đạt `50.000–100.000 USD`:** **Vốn cá nhân bắt đầu thắng về chất lượng dòng tiền** vì bạn giữ `100%` lợi nhuận, không chịu rủi ro đối tác (*counterparty / payout denial risk*), và chạy được các nhánh không hợp luật Prop (Crypto Spot, Carry/Swing, Volatility Selling).
> - **Chiến lược tối ưu (`Hybrid Barbell`):** Không bỏ hoàn toàn Prop ngay ở `50k`, mà giữ **Multi-Prop làm động cơ dòng tiền không tốn vốn gốc**, rút `100%` lợi nhuận Prop đổ sang **Sổ Vốn Riêng (Crypto Spot + Personal FX/Index + Treasury/Tiền gửi phòng thủ)**.

---

## 2. Playbook Đa dạng hóa Đa quỹ (Multi-Prop Diversification)

### 2.1. Tại sao không bao giờ "All-in" vào 1 quỹ duy nhất?
Lịch sử ngành prop `2023–2026` (MyForexFunds bị CFTC đóng cửa, hàng loạt quỹ nhỏ mất thanh khoản hoặc đột ngột đổi luật *consistency* / *copy-trading*) chứng minh **rủi ro đối tác (Firm Counterparty Risk)** là có thật (T1/T3). Đa dạng hóa qua `2–3` quỹ uy tín khác cấu trúc pháp lý và loại sản phẩm giúp:
- Không bao giờ mất quá `35%–50%` dòng tiền nếu `1` quỹ thay đổi điều khoản hoặc đóng băng payout.
- Tận dụng điểm mạnh bổ trợ nhau về phí thi, đòn bẩy và cấu trúc drawdown.

### 2.2. Ma trận 4 đại diện tiêu biểu: CFD Prop (`FTMO`, `The5ers`) vs Futures Prop (`Topstep`, `Apex`)

| Tiêu chí sống còn | **FTMO 2-Step (Swing / Std)** *(T1 đã đo Demo)* | **The5ers High Stakes (2-Step)** *(T1 công bố)* | **Topstep (Futures — CME)** *(T1/T3)* | **Apex Trader Funding (Futures — CME)** *(T1/T3)* |
|---|---|---|---|---|
| **Sản phẩm & Sàn** | CFD FX, Vàng, Chỉ số trên MT5 | CFD FX, Vàng, Chỉ số trên MT5 | Hợp đồng tương lai thật CME (`ES`, `NQ`, `GC`, `6J`) | Hợp đồng tương lai thật CME (`ES`, `NQ`, `GC`, `6J`) |
| **Cơ chế Drawdown** | **Static `10%`** + Daily `5%` (Prague `00:00`) | **Static `10%`** + Daily `5%` (`4%` ở cỡ lớn) | **EOD Trailing** (chốt cuối ngày), khóa ở số dư gốc sau khi tạo đệm | **Intraday Real-Time Trailing** (bám đỉnh lãi thả nổi từng giây!) |
| **Độ tương thích với `PORT_7E` (Trend/Breakout thả lãi)** | **Rất cao (Ưu tiên #1):** Static DD không phạt profit giveback trong ngày | **Cao (Ưu tiên #2):** Phí rẻ (`39 USD` cho `5k`), comm FX `4 USD/lot`; cần khóa tin đỏ `±5m` và luật `3` ngày `>= 0,5%` | **Khá (Giai đoạn mở rộng năm 2):** EOD Trailing hợp lý, dữ liệu CME minh bạch không bị broker đẩy spread; cần chuyển đổi code sang NinjaTrader/Quantower/API | **KHÔNG khuyến nghị cho hệ Naqex:** **Intraday Trailing DD trừng phạt trực tiếp chiến lược thả lãi theo xu hướng** (giá chạy `+2R` rồi quay về `+0,5R` vẫn đẩy trần lỗ sát cổ!) + quy định Safety Net & trần rút phức tạp |
| **Yêu cầu đệm rút tiền (*Payout Buffer*)** | Không ép đệm bắt buộc; nên tự giữ đệm `2%–3%` nếu muốn tăng quy mô, nhưng với `PORT_7E` (`BrF = 0,0%`) rút đều `14` ngày tối ưu dòng tiền hơn ([Pass 27](../../planning/research/PASS27-DEMO-SPEC-M1-AUDIT-AND-PHASE-PROFILES-RESULTS-20261123.md)) | Min payout `150 USD` sau chia; hoàn phí `10% + 20%` Hub Credit + `70%` tiền mặt | Cần giữ đệm lợi nhuận đủ an toàn trên sàn EOD mới mở rút mạnh; giới hạn số hợp đồng theo bậc | Bắt buộc giữ **Safety Net** cố định trên tài khoản trước khi rút vượt ngưỡng; áp trần rút các chu kỳ đầu + luật Consistency `30%` |
| **Rủi ro luật ẩn cần lưu ý** | Luật gộp *"1% Trade Idea Bundle"* trên Funded (đã khóa bằng `SYMCAP_100`) | Terms §11 cần email xác nhận EA tự viết; cấm khớp `±2m` quanh tin đỏ | Phí dữ liệu hàng tháng + phí kích hoạt XFA; luật Consistency | Luật Consistency `30%`, kiểm tra chặt phong cách DCA/hedging, rủi ro hủy payout nhiều phản ánh hơn trên Reddit |

**Kết luận chọn quỹ thực tế cho Naqex:**
- **Ưu tiên ngay (`0–12` tháng):** **FTMO 2-Step** (đã đo Demo thật, thanh khoản tốt, Static DD) + **The5ers High Stakes** (vé siêu rẻ `39 USD`, đòn bẩy `1:100`, đa dạng hóa hãng).
- **Mở rộng tùy chọn (`12–24` tháng):** Nếu muốn thêm nhánh **Futures thật CME** (thoát rủi ro CFD broker và tăng tính minh bạch khớp lệnh), ưu tiên **Topstep** (EOD Trailing) hơn **Apex** (Intraday Trailing xung khắc với bản chất thả lãi của hệ breakout).

---

## 3. Kỷ luật Đệm Rút Tiền (*Payout Withdrawal Buffer*) & Quỹ Dự Phòng Drawdown

### 3.1. Bài học định lượng nội bộ (tránh 2 cực đoan sai lầm)
1. **Cực đoan #1 — Để dồn toàn bộ lãi trong tài khoản Prop để "lãi kép nhanh":** **SAI LẦM.** Tiền nằm trong tài khoản Prop **không phải tiền của bạn** (chịu rủi ro đóng quỹ, rủi ro vi phạm kỹ thuật/tin đỏ ngoài ý muốn). Ngoài ra, mô phỏng thực nghiệm **Pass 27** trên `PORT_5E`/`PORT_7E` cho thấy: khi xác suất cháy Funded đã ở mức `0,0%–0,1%` nhờ phanh `AMBER/RED`, việc cố tình giữ lại đệm `2%` trong tài khoản FTMO không làm giảm cháy mà chỉ làm mất **`-88 USD`** dòng tiền kỳ vọng trên vé `10k`.
2. **Cực đoan #2 — Tiêu hết tiền rút được mà không có quỹ dự phòng mua lại vé thi:** **SAI LẦM.** Dù xác suất cháy rất nhỏ, vẫn luôn tồn tại rủi ro đuôi (*tail event*: lỗi VPS, tin sốc cực đoan, thay đổi chính sách).

### 3.2. Công thức phân bổ 3 ngăn cho MỌI lần Payout từ Prop Firm (`50 / 30 / 20` hoặc `70 / 20 / 10`)
Ngay khi tiền payout về tài khoản ngân hàng / ví cá nhân, chia cứng theo luật sau **trước khi làm bất kỳ việc gì khác**:

| Ngăn phân bổ | Tỷ lệ chuẩn (Giai đoạn `0–12` tháng) | Tỷ lệ chuẩn (Giai đoạn `12–24` tháng) | Mục đích & Giới hạn cứng |
|---|---:|---:|---|
| **Ngăn 1 — Quỹ Đệm Dự Phòng Thi Quỹ (*Challenge Reserve*)** | **`30%`** *(đến khi đầy `5×` phí thi hiện hành)* | **`10%`** *(chỉ bù khi sụt dưới mức trần)* | Tiền mặt riêng chỉ dùng mua lại vé thi nếu có sự cố kỹ thuật/cháy tài khoản, **không bao giờ phải rút tiền tiết kiệm gia đình**. |
| **Ngăn 2 — Sổ Vốn Riêng Quant Pod (*Own Book Seed*)** | **`50%`** | **`70%`** | Chuyển thẳng vào tài khoản vốn riêng để chạy **Nhánh #2 Crypto Spot (`C1/C2`)** + sau đó là **Nhánh #1 Personal FX/Index** (lãi kép thật 100% thuộc sở hữu owner). |
| **Ngăn 3 — Ngân sách Hạ tầng & Thuế / Thưởng (*Ops & Tax*)** | **`20%`** | **`20%`** | Chi trả VPS, data feed, API AI Agents, dự phòng thuế thu nhập cá nhân theo quy định hiện hành. |

> **Kỷ luật về Đệm trong Tài khoản Prop (In-Account Cushion):**
> - Với **FTMO / The5ers (Static DD `10%`, phanh `AMBER/RED`):** Rút đều **mỗi `14` ngày** khi lãi dương đạt ngưỡng tối thiểu (`>= 1%–2%` trên FTMO, `>= 150 USD` sau chia trên The5ers). **Không để quá `3%–4%` lãi chưa rút nằm lại trên tài khoản Prop** (trừ trường hợp chủ động tích mốc `+10%` trong 4 tháng để kích hoạt kế hoạch Scaling của hãng — nhưng chỉ nên làm khi đã có ít nhất `2` tài khoản Funded đang trả dòng tiền).
> - Với **Futures Prop (Topstep EOD Trailing):** Bắt buộc giữ nguyên đệm bằng đúng mức `Trailing Buffer` (ví dụ `2.000–3.000 USD` tùy cỡ tài khoản) cho tới khi sàn khóa vĩnh viễn tại số dư ban đầu; chỉ rút phần vượt trên đệm an toàn.

---

## 4. Lộ trình 24 tháng Thực chiến: Từ `0` Live Track Record → Multi-Prop → Own 4-Sleeve Quant Pod

Lộ trình thiết kế theo nguyên tắc **Cổng Bằng Chứng (Evidence-Gated Scaling)** — không bao giờ nâng quy mô tiền theo lịch dương nếu cổng TCA/Live của pha trước chưa đạt:

| Giai đoạn | Mốc thời gian | Vốn túi tối đa (`OOP`) | Mục tiêu vận hành cụ thể | Cổng bắt buộc để sang pha kế tiếp |
|---|---|---:|---|---|
| **Pha 0: Xác minh Khớp Lệnh (`0 USD` rủi ro)** | Tháng `1` (`2–4` tuần) | `0 USD` | Chạy MT5 Real-Tick Stress + **FTMO Free Trial `14` ngày** cho `PORT_7E` + đăng ký **The5ers Free Monthly Competition (`0 USD`)** đo `SymbolInfo` + lấy email xác nhận EA Terms §11. | `tca_reconcile` = `GREEN`, `0` lỗi `swap`/`10030`/orphan, tỷ lệ khớp tín hiệu MT5 vs Python đạt chuẩn. |
| **Pha 1: Thực chiến Vé Nhỏ (*Micro-Live Proof*)** | Tháng `2–4` | `~210 USD` | Mua song song **1 vé The5ers High Stakes `5.000 USD` (`39 USD`)** + **1 vé FTMO `10.000 USD` (`168 USD`)** chạy hồ sơ `P1_SMOOTH_INVDD_VT` / `P1_SPRINT_25X`. Song song bỏ vốn thử nghiệm nhỏ (`500–1.000 USD` nếu đã duyệt riêng) chạy giấy/nhỏ **Nhánh #2 Crypto Spot** (chờ hoàn tất sửa survivorship bias). | Hoàn thành ít nhất `30–50` lệnh live thật; `live_decay_monitor` = `GREEN`; **chứng minh owner không can thiệp tay vào lệnh giữa chừng**. |
| **Pha 2: Payout Đầu Tiên & Nhân bản Đa quỹ (*Self-Funded Scaling*)** | Tháng `5–10` | `0 USD` mới *(dùng lãi Payout)* | Sau khi Funded vòng nhỏ và nhận **2 lần payout thật đầu tiên**, trích từ Ngăn 1 (`Challenge Reserve`) mua nâng bậc lên **FTMO `25k–50k`** và **The5ers `20k–25k`** (tổng danh nghĩa `50k–100k USD`). Tắt vệ tinh ở Funded (`PORT_7E + SYMCAP_100 + Red-News ±5m`). | Tổng `>= 4` lần payout thành công từ `2` quỹ khác nhau; `Challenge Reserve` đầy `5×` vé; không vi phạm bất kỳ quy tắc nào của quỹ. |
| **Pha 3: Multi-Prop Đỉnh điểm & Bơm Sổ Cá Nhân** | Tháng `11–18` | `0 USD` mới *(tự nuôi 100%)* | Mở rộng Multi-Prop lên mức ngọt **`150.000–250.000 USD`** danh nghĩa (FTMO + The5ers, tùy chọn thêm `1` tài khoản Topstep Futures `50k`). Rút `100%` lợi nhuận định kỳ mỗi `14` ngày, bơm `50%–70%` thẳng vào **Sổ Vốn Riêng** xây dựng danh mục **Crypto Spot Vol-Managed** (`C1/C2`) + tài khoản broker cá nhân (Exness/IBKR/OANDA). | Sổ Vốn Riêng vượt **`25.000–50.000 USD`** hoàn toàn từ lãi tích lũy (hoặc kết hợp phần vốn đầu tư tự nguyện trong giới hạn chịu lỗ tuyệt đối của owner). |
| **Pha 4: Own 4-Sleeve Quant Pod Độc lập** | Tháng `19–24+` | Tự chủ hoàn toàn | Vận hành **Sổ Vốn Riêng 4 Nhánh Trực Giao**: **(1)** Intraday FX/Index Breakout (`PORT_7E/9E` trên broker cá nhân, không còn trần luật quỹ), **(2)** Crypto Spot Trend/XSec (`C1/C2`, `r = 0,02`), **(3)** Nhánh thứ 3 (Swing Swap-Free / Vàng `NEN006/S7` hoặc Crypto Basis/Funding trung hòa sau khi kiểm định riêng), **(4)** Nhánh phòng thủ/lãi suất không rủi ro (Treasury/Chứng chỉ quỹ/Tiền gửi sẵn có của owner). Giữ Multi-Prop làm nguồn phụ nếu vẫn có EV cao. | `Sharpe live` toàn Pod `>= 1,5`, `PeakDD <= 10%` (khớp đúng trần chịu đau tuyệt đối bằng USD/VND của [Hồ sơ Owner](../owner/PROFILE.md)), độc lập 100% với bất kỳ prop firm đơn lẻ nào. |
