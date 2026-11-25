---
doc_type: sprint-plan
domain: prop-launch-acceleration
status: active
deadline_utc: "2026-11-30T09:00:00Z"
deadline_ict: "2026-11-30 16:00 ICT"
updated_utc: 2026-11-25
order_send_count: 0
holdout_rows_analysed: 0
sources:
  - "planning/research/ASTRA-ROUND3-FIRST-PRINCIPLES-ARCHITECTURE-AND-STRATEGY-20261125.md"
  - "planning/research/ROUND3-FRAME-COUNTERFACTUAL-BENCHMARK-20261125.md"
  - "tooling/ai-engines/configs/prop_contracts_v2.json"
  - "tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md"
---

# Mục Tiêu Hiện Hành — Sprint Kiểm Chứng 5 Ngày Trước Hạn Chót FTMO Black Friday (`25/11 -> 30/11/2026 16:00 ICT`)

> **Mục tiêu rõ ràng:** Nén trọn quy trình kiểm chứng thực thi và trượt giá xuống **5 ngày (`25/11 -> 30/11/2026 16:00 ICT`)** bằng cả đo thực địa tăng tốc lẫn mô phỏng tick thật trên máy chủ FTMO, để trước **`16:00` Thứ Hai `30/11/2026`** có đủ bằng chứng định lượng quyết định dứt khoát: **MUA vé FTMO dịp Black Friday hay BỎ QUA không FOMO**.
> **Ràng buộc bất biến:** Giữ niêm phong tuyệt đối `Holdout 2025+` (`holdout_rows_analysed = 0`), không làm nhiễu tài khoản Demo chính `1515343166`, không tự mua vé hay mở lệnh tiền thật khi chưa có lệnh duyệt trực tiếp của chủ sở hữu (`OrderSend = 0`).

---

## 1. Dữ Kiện FTMO Black Friday 2026 Đã Kiểm Chứng (Cần Xác Nhận Lại Ở Trang Checkout Trước Khi Bấm Mua)

1. **Hạn chót chính xác cho FTMO CFD:** **Thứ Hai `30/11/2026` lúc `10:00 CET` (`16:00` giờ Việt Nam)**. *(Đợt Cyber Monday `30/11 -> 02/12` áp dụng cho FTMO Futures, không phải CFD.)*
2. **Điểm quan trọng bắt buộc lưu ý cho Việt Nam — Giảm giá áp cho `FTMO Standard`, KHÔNG áp cho `FTMO Swing`:**
   - Theo điều khoản Black Friday CFD của FTMO ngoài Mỹ/Úc: mức giảm (lên tới **`-30%`** cho gói `10K`, **`-20%`** cho `25K–200K`) áp dụng cho tài khoản **`FTMO Standard`**; FTMO **không cho phép chuyển ngược từ `Standard` sang `Swing`**.
   - **Thời gian thi không giới hạn (`unlimited`) & đồng hồ tính từ lệnh đầu tiên:** Mua khóa giá sale trước `30/11 16:00 ICT` không bị ép phải thi đậu trong 30 ngày (tuy nhiên cần tránh bỏ tài khoản trống quá 30 ngày không giao dịch vì quy định tài khoản ngủ đông; có thể xin support đóng băng tạm nếu cần).
   - **Chính sách hoàn phí:** Gói **`2-Step`** hoàn **`100%`** phí vé ở lần rút thưởng đầu tiên (lưu ý gói `1-Step` KHÔNG hoàn phí -> **chỉ xét `2-Step`**).
3. **Luật tin đỏ của `FTMO Standard` vs bộ `7E` của Naqex (đã kiểm trên `ftmo.com`):**
   - Trong **Vòng 1 (Challenge) & Vòng 2 (Verification)**: `FTMO Standard` **KHÔNG cấm giao dịch tin đỏ**.
   - Chỉ khi sang **Tài khoản Funded (FTMO Account)**: cấm mở/đóng/khớp `SL/TP` trong khung **`±2` phút** quanh các sự kiện đánh dấu **`Restricted`** trên FTMO Economic Calendar, gồm:
     - `USD`: Federal Funds Rate & Statement, NFP, Unemployment Rate & Wages, Advance GDP, **FOMC Meeting Minutes**, CPI.
     - `EUR`: ECB Main Refinancing Rate.
     - `GBP`: BoE Official Bank Rate & MPC Votes, UK CPI.
     - `CAD`: BoC Overnight Rate & Statement, CAD CPI *(bộ `7E` không giao dịch cặp CAD)*.
   - **Lỗ hổng phát hiện ngay hôm nay (`25/11`):** Tệp `naqex_red_news_utc.csv` hiện có `477` mốc nhưng **chưa có `FOMC Meeting Minutes`** (công bố lúc `19:00/18:00 UTC` — đúng khung `7E` đang giữ lệnh trước `20:55 UTC`). **Bắt buộc bổ sung đủ `FOMC Minutes 2026–2027`** trong Sprint này nếu cân nhắc `FTMO Standard`.
   - Bộ `7E` của mình đã đóng phẳng `100%` trước `20:55 UTC` (`swap = 0`, không giữ qua cuối tuần) nên đáp ứng sẵn yêu cầu không giữ cuối tuần của `FTMO Standard`.
4. **Lịch nghỉ lễ Mỹ tuần này (lý do KHÔNG THỂ chỉ ngồi chờ dàn `7E` tự phát lệnh):**
   - **Thứ 4 (`25/11`):** Phiên đầy đủ.
   - **Thứ 5 (`26/11` — Thanksgiving):** NYSE & Nasdaq **đóng cửa cả ngày**, FX phiên Mỹ thanh khoản mỏng.
   - **Thứ 6 (`27/11` — Black Friday):** NYSE **đóng sớm `13:00 ET`**.
   - **Thứ 7 – Chủ Nhật (`28–29/11`):** Đóng cửa.
   - **Thứ 2 (`30/11`):** Chốt sale lúc **`16:00` ICT** -> từ nay tới hạn chót chỉ còn khoảng **`2` phiên bình thường**, nên nếu chỉ ngồi đợi `7E` tự chạy sẽ chỉ thu được khoảng `1–4` lệnh, không đủ đo trượt giá thực tế.

---

## 2. Toán Kinh Tế Thực Tế: `FTMO Standard BF` vs `FTMO Swing` Nguyên Giá (`N = 5.000` × `730` Ngày Lịch Thật)

Chạy đối chứng trực tiếp bằng `round3_frame_benchmark.py` (`7E` cố định + khóa cụm hướng, P1/P2 không vướng luật tin, Funded `Standard` bật khóa tin `±5` phút, tính đủ cuối tuần, trễ trả tiền `T+3`, phí rút `1%`):

| Bậc ma sát / trượt giá | Gói `10K 2-Step` | Phí giả định (USD) | Lãi ròng TB 24t (USD) | Trung vị 24t (USD) | `EV / Phí vé đầu` | `P(Lỗ ròng <= 0)` | Vốn ứng P95 (USD) | Trung vị ngày lịch tới payout 1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`1,00×`** | `Standard BF -30%` | `118` | `+609` | `+572` | **`+5,16×`** | `17,9%` | **`236`** | `308 ngày` |
| **`1,00×`** | `Standard BF -20%` | `134` | `+604` | `+571` | `+4,50×` | `18,2%` | `268` | `308 ngày` |
| **`1,00×`** | `Swing nguyên giá` | `168` | `+640` | `+613` | `+3,81×` | `17,8%` | `336` | `308 ngày` |
| **`1,25×`** | `Standard BF -30%` | `118` | `+439` | `+383` | **`+3,72×`** | `26,3%` | **`236`** | `335 ngày` |
| **`1,25×`** | `Standard BF -20%` | `134` | `+432` | `+381` | `+3,22×` | `26,5%` | `268` | `335 ngày` |
| **`1,25×`** | `Swing nguyên giá` | `168` | `+454` | `+411` | `+2,70×` | `26,2%` | `336` | `334 ngày` |
| **`1,50×`** | `Standard BF -30%` | `118` | **`+273`** | `+192` | **`+2,31×`** | `37,4%` | **`354`** | `359 ngày` |
| **`1,50×`** | `Standard BF -20%` | `134` | `+262` | `+189` | `+1,95×` | `37,9%` | `402` | `359 ngày` |
| **`1,50×`** | `Swing nguyên giá` | `168` | `+271` | `+204` | `+1,61×` | `37,1%` | `504` | `358 ngày` |
| **`2,00×`** | `Standard BF -30%` | `118` | `+35` | `-118` | `+0,29×` | `58,7%` | `354` | `390 ngày` |
| **`2,00×`** | `Swing nguyên giá` | `168` | `-8` | `-168` | `-0,05×` | `58,7%` | `504` | `390 ngày` |

**Ý nghĩa rõ ràng từ bảng số:**
- Nhờ giảm `30%` phí đầu vào (`168 -> 118 USD`), **`FTMO Standard BF -30%` cắt giảm `30%` vốn ứng tối đa P95 (`504 -> 354 USD` ở `1,50×`) và đẩy hiệu quả đồng phí lên `+2,31×` (từ `+1,61×`)**, ngang ngửa lợi nhuận tuyệt đối với `Swing` — với **điều kiện bắt buộc** phải vá đủ `FOMC Minutes` vào lịch tin đỏ và kiểm chứng trượt giá thực tế nằm trong vùng `<= 1,50×`.
- Ngược lại, **tuyệt đối không mua vì tiếc `50 USD` tiền sale** nếu kết quả đo thực địa cho thấy trượt giá gần `2,00×`.

---

## 3. Chiến Dịch Tăng Tốc 6 Mũi (`25/11 -> 30/11 16:00 ICT`) — Không Ngồi Đợi Thụ Động

Vì lợi thế tín hiệu đã có kiểm chứng lịch sử nhiều năm, ẩn số duy nhất quyết định **MUA hay BỎ** là **vật lý khớp lệnh thật trên máy chủ FTMO (spread, trượt giá vào/SL/thoát, hoa hồng, swap, độ trễ Master EA, luật tin đỏ Standard & pháp lý EA)**. Ta nén `2–4` tuần xuống `5` ngày bằng **6 mũi chạy song song**:

| Mũi tăng tốc | Mục tiêu cụ thể | Cách làm (an toàn, `Holdout 2025+` khóa cứng) | Hạn hoàn thành |
|---|---|---|---|
| **Mũi 1 — Đo trượt giá thật tốc độ cao (`20–40` lệnh trong `48` giờ)** | Biết chính xác phân phối trượt giá thật (`P50/P90`, lệnh thị trường + lệnh dừng + quét SL + hoa hồng + `swap = 0`) trên `USDJPY, GBPUSD, EURJPY, US100.cash` | Mở `1` tài khoản **FTMO Free Trial phụ (`0 USD`)** hoàn toàn tách biệt khỏi `1515343166`, chạy EA thăm dò siêu nhỏ **`0,01` lot** vào các khung giờ Âu (`07–10 UTC`), Mỹ (`13:30–16:00 UTC`), đóng ngày (`20:55 UTC`) để lấy `20–40` khớp lệnh thật trên máy chủ FTMO mà không làm bẩn sổ `7E`. | Tối Thứ 6 `27/11` |
| **Mũi 2 — Đo tỷ số Spread sống 24/7 vs Backtest (`OrderSend = 0`)** | Biết chính xác `FTMO Live Spread / Backtest M1 Spread` theo từng giờ giao dịch | Chạy bộ ghi chỉ đọc Bid/Ask mỗi `5` giây trên `naqex-node1` xuyên Thứ 4 -> sáng Thứ 2 cho cả `4` mã chính (`USDJPY, GBPUSD, EURJPY, US100.cash`) rồi đối chiếu trực tiếp với spread Dukascopy `1,00×` trong `.runtime/hot-m1-cache`. | Sáng Chủ Nhật `29/11` |
| **Mũi 3 — Kiểm định `Model=4` Real-Tick `2024` trên máy chủ FTMO (`200+` lệnh trong `15` phút)** | Chứng minh `Naqex_Master_Prop7E.ex5` khớp `1:1` với dàn `7E`, khóa cụm hướng chạy đúng, `0` lỗi tin đỏ `±2m` và `0` swap trên dữ liệu tick thật của FTMO | Chạy MT5 Strategy Tester **`Model = 4`** (Every tick based on real ticks) trên dữ liệu **năm `2024` (chỉ `< 2025-01-01`, `holdout_rows_analysed = 0`)** cho `Naqex_Master_Prop7E.ex5` và dàn `7E` v3.10. | Thứ 5 `26/11` |
| **Mũi 4 — Vá đủ `FOMC Minutes 2026–2027` + Gắn Shadow `Naqex_Master_Prop7E` trên `naqex-node1`** | Đóng sạch lỗ hổng lịch tin đỏ cho `FTMO Standard Funded` & đo độ trễ tín hiệu thật `p50/p95` của `1` Master EA | Cập nhật lịch `FOMC Minutes` chính thức của Fed vào `red_news_official_2026_2027_multi_ccy.json`, dựng lại `naqex_red_news_utc.csv`, đồng bộ phẳng lên `naqex-node1` và gắn `Naqex_Master_Prop7E.ex5` (`DryRun=true, ShadowCompare=true`) chạy bóng song song. | Hôm nay `25/11` – Thứ 5 `26/11` |
| **Mũi 5 — Pháp lý EA, Giá Checkout thật & Test đối soát sao kê sàn** | Loại sạch rủi ro `R4` (luật sàn, thanh toán & rút tiền Việt Nam) trước khi bấm mua | Gửi email xin xác nhận chạy EA tới `support@ftmo.com` hôm nay (hỏi rõ cả **Standard & Swing**), chụp giá checkout thực tế tại Việt Nam, kiểm tra đường nạp/rút (Bank Wire / Crypto / Skrill / Rise), và test chạy thật `prop_challenge_tracker.py --statement-csv --strict-exit` trên file sao kê xuất từ `FTMO-Demo 1515343166`. | Thứ 6 `27/11` |
| **Mũi 6 — Phán quyết Go/No-Go độc lập với GPT-6.2 Astra (Vòng 4)** | Chống thiên kiến FOMO trước giờ đóng sale | Tổng hợp toàn bộ số liệu thực đo của Mũi 1–5 vào `1` gói bằng chứng duy nhất và nhờ **GPT-6.2 Astra** phản biện dứt điểm: **`MUA Standard BF` / `MUA Swing` / `HOÃN`**. | Tối Chủ Nhật `29/11` *(trước `16:00 ICT` Thứ 2 `30/11`)* |

---

## 4. Cổng Quyết Định Cứng (`GO / NO-GO`) Trước `30/11/2026 16:00 ICT`

- **ĐƯỢC PHÉP MUA (`1` vé `FTMO 10K` trong ngân sách `1.500 USD`) CHỈ KHI ĐẠT ĐỦ 4 ĐIỀU KIỆN:**
  1. **Chi phí khớp lệnh thực đo (Spread sống + Trượt giá calibration `20–40` lệnh)** quy đổi nằm gọn ở mức **`<= 1,50×`** ngân sách M1 (đẹp nhất `<= 1,25×`).
  2. **Kiểm định kỹ thuật sạch tuyệt đối (`Model=4` Real-Tick `2024` + live Demo):** `0` lệnh thiếu SL (`orphan_no_sl = 0`), `0` phí swap qua đêm, `0` vi phạm tin đỏ `±2m` (đã vá đủ `FOMC Minutes`), đối soát sao kê khớp `100%`.
  3. **Pháp lý & Thanh toán rõ ràng:** Đã kiểm tra trực tiếp giá checkout thật tại Việt Nam (chỉ chọn `2-Step`, kiểm tra loại `Standard` vs `Swing`), xác nhận kênh rút tiền về Việt Nam và có email xác nhận (hoặc phản hồi) từ `support@ftmo.com` về EA độc quyền.
  4. **Astra Vòng 4 (tối `29/11`) không phát hiện lỗi chặn (`CRITICAL`) mới.**
- **TỪ CHỐI MUA (Bỏ qua đợt sale, giữ nguyên `1.500 USD`) NẾU:**
  - Trượt giá + spread đo thật tiệm cận **`>= 1,80× – 2,00×`** (vượt vùng kỳ vọng dương bền vững); **HOẶC**
  - Xuất hiện lỗi kỹ thuật chưa vá dứt điểm trên MT5 / lịch tin đỏ `Standard`; **HOẶC**
  - Điều khoản checkout/EA không khớp. *(Chấp nhận bỏ qua `50 USD` ưu đãi còn hơn đốt tiền vào hệ thống chưa đạt chuẩn.)*
