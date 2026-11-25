---
doc_type: evergreen
domain: knowledge
topic: trading-psychology-and-profit-giveback-playbook
updated_utc: 2026-11-23
sources:
  - "T1: Weber & Camerer (1998, JEBO, doi:10.1016/s0167-2681(97)00089-9) — The Disposition Effect in Securities Trading"
  - "T1: Kahneman & Tversky (Prospect Theory / Loss Aversion) & Odean (1998) — Are Investors Reluctant to Realize Their Losses?"
  - "T1 (Đo nội bộ): knowledge/owner/PROFILE.md, PRE-HOLDOUT-READINESS-AND-BLINDSPOT-AUDIT-20261123.md, tooling/ai-engines/quant_factory/live_decay_monitor.py"
  - "T2: Robert Carver — Systematic Trading & Leveraged Trading (quy tắc cấm override, volatility sizing, guard-dog principle)"
  - "T2: Dr. Brett Steenbarger — Enhancing Trader Performance & The Daily Trading Coach (tái khung drawdown, tách cảm xúc khỏi P&L, nghi thức review)"
---

# Playbook Tâm lý Giao dịch Định lượng & Kiểm soát "Profit Giveback"

> Tài liệu giải quyết **trực diện rủi ro hành vi đã xác nhận trong [Hồ sơ Owner](../owner/PROFILE.md)**: owner có lợi thế ít FOMO và phản xạ tốt là điều tra nguyên nhân khi gặp bất thường, nhưng có **điểm yếu tâm lý đặc trưng là khó chịu khi lợi nhuận đã có bị trả lại (*profit giveback*) và nảy sinh xung lực muốn can thiệp bằng tay giữa lệnh thay vì để luật cứng chạy hết chu kỳ**.

---

## 1. Giải phẫu khoa học: Tại sao não người lại cực ghét "Trả lại lãi" (*Profit Giveback*)?

### 1.1. Hiệu ứng Định vị (*Disposition Effect*) & Tính bất đối xứng của Nỗi đau (T1)
- Theo **Lý thuyết Triển vọng (Kahneman & Tversky)** và thực nghiệm kinh điển của **Weber & Camerer (`1998`, `1.135` trích dẫn)** cùng **Odean (`1998`)**:
  - Não bộ ngay lập tức cập nhật **điểm tham chiếu (*mental anchor*)** lên đỉnh lãi thả nổi cao nhất vừa nhìn thấy (`High-Water Mark`, ví dụ tài khoản vừa chạm `+2.000 USD` dù lệnh chưa đóng).
  - Khi giá hồi lại về `+1.200 USD`, về mặt kế toán bạn vẫn **lãi `+1.200 USD`**, nhưng hạch hạnh nhân (*amygdala*) của não bộ lại ghi nhận đó là một **khoản lỗ thật `-800 USD`** — mà nỗi đau mất tiền mạnh gấp **`~2×`** niềm vui kiếm được cùng số tiền đó!
  - Hệ quả tất yếu (hiệu ứng ngược của *Disposition Effect* ở trader hệ thống): **chốt non các lệnh thắng lớn** (*cutting winners early*) để "bảo vệ cảm giác an toàn", vô tình **chặt đứt phần đuôi dương (right tail)** vốn là thứ duy nhất trả tiền cho toàn bộ các lệnh cắt lỗ nhỏ trước đó!

### 1.2. Con số thực nghiệm từ chính danh mục Naqex (`PORT_7E` / `PORT_9E`)
- Trên dữ liệu `2018–2024`, toàn bộ lợi thế của `PORT_7E` đến từ **độ lệch dương (`skew = +1,39` đến `+1,63`)** — cắt lỗ cứng nhanh ở `-1R` và thả lãi tới cuối phiên (`20:55 UTC` / `15:55 ET`) để thu các ngày bùng nổ `+2R..+5R`.
- Trong các thử nghiệm nội bộ trước đây (V21 & Pass 27):
  - Chỉ cần bỏ lỡ `10` lệnh thắng lớn nhất, kết quả dài hạn tụt giảm cực mạnh.
  - Phanh chốt sớm theo cảm giác (ví dụ khóa lãi sớm ở `+7%` trong Challenge P1 ở Pass 27) **không hề làm giảm tỷ lệ cháy**, mà chỉ kéo chậm thêm `+1,8` tháng thời gian đậu quỹ.
- **Kết luận toán học (Robert Carver — T2):** Trong một hệ thống theo xu hướng/breakout, **trả lại một phần lãi thả nổi (*giveback*) KHÔNG phải lỗi cần sửa — nó chính là cái giá bắt buộc phải trả để mua vé lên các con sóng `+3R..+5R`**. Nếu bạn can thiệp tay để "không bao giờ bị trả lại lãi", bạn đang phá hủy chính kỳ vọng dương (`EV > 0`) của toàn hệ thống!

---

## 2. Giao thức Tách biệt Thực thi Cứng (*Hard Execution Separation*) — Học từ Quỹ Lớn & Robert Carver

Robert Carver có câu châm ngôn nổi tiếng của các quỹ Systematic (Man AHL): *"Một phòng giao dịch định lượng hoàn hảo chỉ cần 3 thứ: một chiếc máy tính chạy thuật toán, một con người để bảo trì máy tính, và một con chó giữ nhà — nhiệm vụ duy nhất của con chó là **cắn con người nếu họ định chạm tay vào bàn phím để sửa lệnh đang chạy**."*

Để biến lời khuyên này thành **kiến trúc kỹ thuật thực tế** cho owner (không dựa vào "ý chí chịu đựng" mong manh):

### 2.1. Tách tuyệt đối 2 chiếc mũ: *Nhà Nghiên Cứu (Researcher)* vs *Người Thực Thi (Operator)*
- **Chiếc mũ Researcher (được mở mọi lúc vào cuối tuần):** Toàn quyền nghi ngờ, soi số liệu, mổ xẻ xem trailing stop hay partial take-profit có thật sự cải thiện Calmar trên dữ liệu lịch sử hay không. Mọi ý tưởng chống giveback (nếu có) **chỉ được phép đi vào code qua quy trình kiểm định thống kê đầy đủ**, không bao giờ được áp dụng ngẫu hứng lúc thị trường đang chạy.
- **Chiếc mũ Operator (Thứ Hai → Thứ Sáu):** **KHÔNG có quyền ra quyết định giao dịch.** Vai trò duy nhất trong tuần là xác nhận hạ tầng còn sống (`heartbeat` xanh, kết nối VPS ổn định, không có lệnh mồ côi).

### 2.2. Bốn hàng rào vật lý chống xung lực can thiệp giữa lệnh (*Friction Engineering*)
1. **Cấm cài MT5 tài khoản giao dịch chính lên điện thoại cá nhân (hoặc chỉ đăng nhập bằng *Investor Password — Read-Only*):** Nếu không có nút "Close Position" trong túi quần, `90%` xung lực chốt non lúc giá giật ngược sẽ tự tiêu tan sau `15` phút.
2. **Ẩn P&L thả nổi theo tiền tuyệt đối trong giờ giao dịch:** Chỉ xem báo cáo tóm tắt cuối ngày hoặc cuối tuần sau khi toàn bộ lệnh intraday đã tự `hard flat` (`20:55 UTC`). Với hệ intraday `swap = 0` của Naqex, bạn hoàn toàn không cần nhìn bảng giá theo phút!
3. **Khóa "Quy tắc 3 trường hợp duy nhất được chạm tay" (*Emergency Override Charter*):** Chỉ cho phép can thiệp thủ công vào tài khoản live trong đúng **3 tình huống lỗi kỹ thuật**:
   - **(a)** Mất kết nối/treo VPS khiến lệnh không đóng được trước giờ rollover/cuối tuần hoặc không có SL trên server.
   - **(b)** Sàn/broker lỗi hiển thị giá bất thường (*bad tick / feed freeze*) hoặc lệnh bị nhân đôi (*double-fill bug*).
   - **(c)** Sự kiện bất khả kháng toàn hệ thống (*force majeure*: sàn thông báo ngừng hoạt động, chiến tranh/đóng cửa sàn đột xuất).
   - **Mọi lý do khác ("thấy giá chạm kháng cự", "đang lãi 800 USD sợ mất", "nghe tin đồn vĩ mô") đều bị xếp loại VI PHẠM KỶ LUẬT.**
4. **Quy đổi song song `%` và Tiền tuyệt đối (`USD / VND`) trước khi nạp tiền (đúng nguyên tắc [PROFILE.md](../owner/PROFILE.md)):**
   - Ví dụ trên sổ vốn thật `10.000 USD` (`~255 triệu VND`), `PeakDD 7%` nghĩa là bạn **phải chấp nhận ký trước vào giấy** rằng sẽ có lúc tài khoản tụt `-700 USD` (`~18 triệu VND`) hoặc một lệnh đang lãi `+250 USD` (`~6,4 triệu VND`) quay đầu về `+50 USD` (`~1,3 triệu VND`) mà **không chớp mắt**. Nếu con số tuyệt đối bằng VND làm bạn mất ngủ, **hạ quy mô vốn/lot xuống một nửa trước khi bật bot**, tuyệt đối không để cỡ lớn rồi định "canh tay để cắt cho đỡ đau".

---

## 3. Giao thức Drawdown Khóa Trước (*Pre-Committed Drawdown & Alpha-Decay Protocol*)

Đây là điểm mạnh nhất khi bạn kết hợp kiến trúc của **Quỹ lớn (Millennium / Man AHL)** với bộ công cụ Naqex đã lập trình sẵn — chuyển mọi nỗi lo cảm tính sang **đèn giao thông định lượng 3 màu**:

| Trạng thái Đèn | Điều kiện kích hoạt tự động (Khóa trước — không bàn cãi) | Hành động bắt buộc của Hệ thống (`Naqex_AccountOrchestrator`) | Quyền của Con người (Owner) |
|---|---|---|---|
| **XANH (`GREEN`)** | Drawdown tài khoản `> -3,5%`; `tca_reconcile` = `GREEN`; `live_decay_monitor` = `GREEN_WITHIN_EXPECTATION` (trên `p05` cone, `CUSUM > -4,5σ`) | Chạy đúng `1,00×` rủi ro hồ sơ đã chọn (`PORT_7E + SYMCAP_100 + Red-News ±5m` trên Funded; `Downside Vol Brake [0,55, 1,00]` tự lo biến động) | **CẤM can thiệp.** Chỉ đọc báo cáo tổng kết cuối tuần (`15` phút). |
| **VÀNG (`AMBER`)** | Drawdown chạm **`-3,5%`** từ đỉnh **HOẶC** `live_decay_monitor` báo `AMBER_WATCH_REDUCE_SIZE` (`CUSUM <= -4,5σ` hoặc tổng lãi rơi dưới bách phân vị `p05`) **HOẶC** `tca_reconcile` báo `AMBER_WATCH` | Tự động cắt quy mô rủi ro về **`0,65×`** (chế độ phòng thủ tự động trong `AccountOrchestrator`, giữ hệ sống sót mà vẫn thu dữ liệu) | Bắt đầu chạy **Kiểm toán 3 nhánh** vào cuối tuần: *(1) Lỗi TCA/khớp lệnh? (2) Thị trường đang ở năm ngủ yên như `2019/2021`? (3) Có lỗi code/feed không?* Vẫn **không sửa lệnh bằng tay** trong tuần. |
| **ĐỎ (`RED`)** | Drawdown chạm **`-6,0%`** (bảo vệ sàn `10%` quỹ) **HOẶC** `live_decay_monitor` báo **`RED_HALT_ALPHA_DECAY`** (`CUSUM <= -4,5σ` **VÀ** `SPRT` bác bỏ `H0` / dưới `p05`) **HOẶC** `tca_reconcile` báo `RED_*` (`swap != 0`, trượt `>= 25% R0`) | Hạ cỡ về **`0,40×`** (nếu chỉ chạm DD kỹ thuật `-6%` nhưng chưa lỗi TCA) **HOẶC dừng mở lệnh mới hoàn toàn (`HALT`)** nếu vi phạm `RED_HALT_ALPHA_DECAY` / `RED_SWAP_VIOLATION` | Kích hoạt **Nghi thức Hậu kiểm không đổ lỗi (Blameless Postmortem)** cùng AI Red-Team Auditor. Chỉ được bật lại sau khi xác định đúng nguyên nhân gốc và có biên bản kiểm chứng. |

> **Cột mốc tâm lý cực kỳ quan trọng cần nhớ trước khi chạy thật:**
> Trên dữ liệu kiểm chứng `2018–2024`, ngay cả một danh mục xuất sắc như `PORT_7E` cũng có **những pha đi ngang kéo dài `4–6` tháng** (như `2019` và `2021`, với chuỗi ngày đỏ liên tiếp). Biết trước điều này giúp bạn phân biệt rõ **"nỗi đau bình thường của phân phối xác suất"** với **"chiến lược bị hỏng"**.

---

## 4. Nghi thức Review Cuối Tuần 30 phút (Systematic PM Weekly Ritual — Steenbarger + Institutional Risk Desk)

Dr. Brett Steenbarger (huấn luyện viên tâm lý cho các PM quỹ đầu cơ) nhấn mạnh: **tâm lý ổn định không đến từ việc tự nhủ "đừng sợ nữa", mà đến từ một quy trình phản hồi có cấu trúc chuyển trọng tâm từ P&L sang Chất lượng Quy trình (*Process Score*)**.

Mỗi **Thứ Bảy hoặc Chủ Nhật (`30` phút cố định, khi thị trường đóng cửa 100%)**, owner chạy đúng 4 bước sau:

### Bước 1 — Chấm điểm Kỷ luật Vận hành (`5` phút, *Process > P&L*)
Trả lời nhị phân (`Đạt / Không đạt`) cho 4 câu hỏi:
1. Số lần can thiệp đóng/sửa lệnh bằng tay ngoài 3 trường hợp khẩn cấp kỹ thuật = **`0`**?
2. Số lần mở app xem P&L thả nổi trong giờ giao dịch `<= 1` lần/ngày (lý tưởng = `0`)?
3. Toàn bộ lệnh đã `hard flat` với `swap = 0` và `0` lệnh mồ côi?
4. Có tuân thủ đúng cỡ rủi ro đã ký trước không?
- *Nguyên tắc thưởng/phạt tâm lý:* Một tuần **lỗ `-1,5%` nhưng đạt `4/4` điểm quy trình = TUẦN THÀNH CÔNG**. Một tuần **lãi `+2%` nhưng chốt tay non làm sai luật = TUẦN LỖI KỶ LUẬT** (ghi cảnh báo đỏ vào nhật ký!).

### Bước 2 — Chạy Tự động 3 Công cụ Đo lường Khách quan (`10` phút)
Chạy 3 lệnh kiểm tra không cảm tính của Naqex:
- `tca_reconcile.py` → kiểm tra trượt giá `% R0`, `p90 latency`, tỷ lệ reject, `swap = 0`.
- `live_decay_monitor.py` → kiểm tra vị trí đường cong lãi thực tế trên **Bootstrap Confidence Cone (`p05 / p50 / p90`)**, chỉ số `CUSUM` và trạng thái `Wald SPRT`.
- `ops_monitor.py` → kiểm tra uptime VPS, log lỗi MT5 (`Journal/Experts`), lịch tin đỏ `naqex_red_news_utc.csv` và ngày lễ tuần tới.

### Bước 3 — Mổ xẻ *Profit Giveback* bằng Số liệu MFE (`10` phút)
- Thay vì buồn bực trong bụng vì *"lệnh hôm thứ Tư đang lời +2R cuối cùng về +0,4R"*, hãy ghi chép ngắn gọn vào Nhật ký tuần chỉ số **MFE Realization Ratio** (tỷ lệ lãi thực nhận trên đỉnh lãi thả nổi *Maximum Favorable Excursion*) cho nhóm lệnh tuần qua, rồi **đối chiếu ngay với phân phối MFE của 7 năm backtest**.
- Khi thấy bằng mắt mình rằng *"trong backtest 7 năm, trung bình các lệnh thắng cũng trả lại `25%–40%` MFE nhưng vẫn tạo ra `Calmar 1,75` trên Holdout"*, phần não phân tích (System 2 — thế mạnh IQ `115–120` của owner) sẽ **vô hiệu hóa hoàn toàn nỗi khó chịu cảm tính (System 1)**.

### Bước 4 — Ghi 3 dòng Chốt Tuần & Khóa Hệ Thống cho Thứ Hai (`5` phút)
- **1 điều chạy tốt** (để củng cố thói quen đúng).
- **1 ma sát/lỗi kỹ thuật hoặc cảm xúc nổi lên** (nếu có xung lực muốn can thiệp, ghi rõ *giờ nào, mức giveback bao nhiêu USD/VND* đã kích hoạt nó — biến cảm xúc thành dữ liệu khoa học để hiểu ngưỡng chịu đau thật của bản thân).
- **1 hành động duy nhất cho tuần sau** (ví dụ: *"giữ nguyên 100%, không sửa bất cứ dòng code nào"* — trong phần lớn các tuần bình thường, **không làm gì cả chính là hành động đẳng cấp nhất của một Systematic PM**).
