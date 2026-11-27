---
doc_type: external-prop-terms-and-promo-radar
fetched_utc: "2026-11-27T06:44:00Z"
untrusted_external_data: true
trust_tier: "T1_PRIMARY_OFFICIAL (tách bạch nguồn T2/T3 bên dưới)"
holdout_rows_analysed: 0
order_send_count: 0
spend_vnd: 0
bf_bill_lock_ict: "2026-11-30T16:00:00+07:00"
bf_14day_payment_cutoff_ict: "2026-12-14T16:00:00+07:00"
radar_script: "tooling/automation/prop_terms_radar.py"
radar_state_json: ".runtime/automation/prop_terms_radar_latest.json"
---

# Radar Điều Khoản Sống & Khuyến Mãi Black Friday 2026 — FTMO, The5ers & IC Funded (`27/11/2026`)

**Kết luận hành động ngay (`0 VND`, `OrderSend = 0`):** FTMO 2-Step Standard 10K giảm **`-30%`** còn **`68,70 USD`** (`~1,77 triệu VND`, hoặc `~1,81 triệu VND` gồm phí FX thẻ VN `2,5%`) đến **`Thứ Hai 30/11/2026 16:00 ICT`** (`10:00 CET`), **KHÔNG áp dụng cho Swing**. Về câu hỏi sống còn **giữ hóa đơn chưa thanh toán `14 ngày` (`30/11 -> 14/12`)**: điều khoản chính thức FTMO (`GTC Clause 3.4`) và The5ers **KHÔNG cam kết giữ giá khuyến mãi Black Friday sau giờ cắt (`NOT_DISCLOSED`)** — chỉ phương thức chuyển khoản ngân hàng mới phát hành `proforma invoice` (nhưng phí SWIFT từ VN tốn `15–40 USD`, ăn sạch khoản giảm `29,91 USD`). **Bước `< 2 phút` trước `30/11`:** nhắn Live Chat hoặc `support@ftmo.com` xác nhận bằng văn bản trước khi dựa vào cơ chế giữ bill `14 ngày`.

> **Hàng rào an toàn & nguồn tin (`Supply-Chain Guard`):** Toàn bộ dữ liệu bên ngoài gắn nhãn `untrusted_external_data: true`, `OrderSend = 0`, `spend_vnd = 0`, `Holdout 2025+ SEALED` (`holdout_rows_analysed = 0`). Mọi thu thập đều ở chế độ đọc công khai (không đăng nhập, không vượt CAPTCHA/anti-bot, không gửi biểu mẫu/đặt đơn). Tại máy Dev, kết nối HTTPS trực tiếp từ script Python bị quá thời gian bắt tay TLS, nên dữ liệu sống ngày `27/11/2026` được đối chiếu qua tìm kiếm web công khai và tách bạch rõ bậc tin cậy:
> - **`T1_PRIMARY_OFFICIAL`:** `ftmo.com`, `trader.ftmo.com`, `the5ers.com`, `icfunded.com`.
> - **`T2_TECHNICAL_COMMUNITY`:** trang phân tích tài chính độc lập (`fxstreet.com`).
> - **`T3_FORUM_EXPERIENCE` / `T3_GENERAL_WEB`:** `reddit.com`, `hocvientrader.com`, bản lưu điều khoản (`scribd.com`, `studocu.vn`), trang tổng hợp mã giảm giá (`propfirmcircle.com`, `propfirmdiscount.com`, `forexpropfirms.com`, `selectpropfirms.com`).

---

## 1. Giá Black Friday / Cyber Monday 2026 & Giờ Cắt Chính Xác (`30/11/2026`)

Tỷ giá tham chiếu trong sổ chuẩn [prop_pricing_catalog.json](../../tooling/ai-engines/configs/prop_pricing_catalog.json) (`26/11/2026`): **`25.765,94 VND/USD`** (`1,09595 USD/EUR`), phí FX thẻ VN dự tính **`2,5%`**.

| Quỹ & Gói mục tiêu | Giá gốc (`USD`) | Giá Black Friday 2026 (`USD` / `VND` chưa & gồm `2,5%` FX) | Mức giảm & Mã | Giờ cắt (`30/11/2026`) | Bậc tin cậy & Ghi chú quan trọng |
|---|---:|---|---|---|---|
| **FTMO 2-Step Standard 10K** | `98,61` | **`68,70 USD`** (`1,77 tr` / **`1,81 tr VND`**) | **`-30%`** (tự động) | **`16:00 ICT`** (`10:00 CET`) *(1 nguồn T3 ghi `10:30 CET` -> giữ mốc sớm `16:00 ICT`)* | **`T1_PRIMARY_OFFICIAL`** (đã chốt từ checkout VN `26/11` & khớp sống `27/11`, tương đương `~62,30 EUR` từ `89 EUR`). `25K–200K` giảm **`-20%`**. |
| **FTMO 2-Step Swing 10K / 25K** | `109,69` / `309,14` | **`109,69`** / **`309,14 USD`** (không giảm) | **`0%`** | Không áp dụng BF ngoài Mỹ/Úc | **`T1_PRIMARY_OFFICIAL`** — Black Friday CFD bỏ qua Swing; tại VN gói Swing `50K/100K/200K` bị khóa và **không cho đổi `Standard -> Swing`** sau mua. |
| **FTMO 1-Step 10K / Instant 5K** | `87,53` / `187,25` | `60,94` / `130,75 USD` | **`-30%`** | `16:00 ICT` (`10:00 CET`) | **`T1_PRIMARY_OFFICIAL`** — **KHÔNG khuyến nghị** thay `2-Step Standard`: **`0%` hoàn phí**, Trailing DD `3%`/ngày, luật Best-Day `50%` / `30%`. |
| **The5ers High Stakes 5K Classic (`8%/5%`)** | `39,00` | List `39,00 USD` (`1,00 tr`) · Tín hiệu BF `-10%`: **`35,10 USD`** (`0,90 tr` / `0,93 tr VND`) | **`-10%`** *(chưa xác minh T1 checkout)* | **`NOT_DISCLOSED`** ở T1 | **Giá list: `T1_PRIMARY_OFFICIAL`** · **Sale `-10%`: `T2/T3`** (`fxstreet.com`, `forexpropfirms.com`). Phải tự kiểm banner trên `the5ers.com/high-stakes/` trước khi mua. |
| **The5ers High Stakes 5K New (`10%/5%`)** | `35,00` | List `35,00 USD` (`0,90 tr`) · Tín hiệu BF `-10%`: **`31,50 USD`** (`0,81 tr` / `0,83 tr VND`) | **`-10%`** *(chưa xác minh T1 checkout)* | **`NOT_DISCLOSED`** ở T1 | **Giá list: `T1_PRIMARY_OFFICIAL`** · **Sale `-10%`: `T2/T3`**. Có thêm tier nhỏ **`2,5K`** (`19–22 USD`, nguồn `T3`) chưa đưa vào SSOT. |
| **The5ers High Stakes `20K` -> `25K`** | **`20K` đã bỏ** · `25K Classic = 195` / `New = 176` | `25K` nếu `-10%`: **`175,50`** / **`158,40 USD`** (`4,52` / `4,08 tr VND`) | **`-10%`** *(chưa xác minh T1)* | **`NOT_DISCLOSED`** ở T1 | **`T1_PRIMARY_OFFICIAL`** xác nhận High Stakes đã bỏ SKU cũ `20K` & `60K`, thay bằng **`5K / 10K / 25K / 50K / 100K`** (`20K` chỉ còn ở chương trình **Bootcamp**). |
| **IC Funded 2-Step Pro `5K / 10K / 25K`** | `74` / `125` / `249` | List `74 / 125 / 249 USD` · Tín hiệu mã `BLACKIC45` (`-45%`): **`40,70 / 68,75 / 136,95 USD`** | **`BLACKIC45`** (`-45%`, **CHƯA xác minh T1**) | Ghi `30/11/2026` *(giờ cắt `NOT_DISCLOSED`)* | **Giá list: `T1_PRIMARY_OFFICIAL`** · **Mã `BLACKIC45`: `T3_GENERAL_WEB` thuần túy** (`propfirmdiscount.com`, `firmscopes.com`, YouTube). **Cấm coi là chắc chắn** nếu chưa nhập thử tại checkout `icfunded.com`. |

**Hai lưu ý kỷ luật về giờ cắt FTMO (`30/11/2026`):**
1. Phần lớn nguồn (`dealpropfirm.com`, `reddit.com`, `fxify.com` và bản ghi `25/11`) thống nhất hạn chót FTMO Black Friday CFD là **Thứ Hai `30/11/2026 10:00 CET = 16:00 ICT (09:00 UTC)`**. Một trang thứ cấp (`propfirmcircle.com`, `T3`) ghi `10:30 CET` (`16:30 ICT`), còn nhánh `FTMO Futures` kéo dài sang Cyber Monday (`~02/12`) với mã riêng.
2. Áp dụng nguyên tắc **an toàn đóng (`fail-closed`)**: chốt mốc sớm **`2026-11-30T16:00:00+07:00`** và kiểm đồng hồ đếm ngược trực tiếp trên `ftmo.com/en/black-friday/` **trước `15:00 ICT`** nếu có ý định thao tác.

---

## 2. Câu Hỏi Trọng Tâm Chủ Sở Hữu: Quy Tắc Giữ Hóa Đơn Chưa Thanh Toán `14 Ngày` (`30/11 -> 14/12`)

**Phán quyết ngắn gọn, trung thực 100%:** **KHÔNG CÓ CAM KẾT HỢP ĐỒNG NÀO** trong điều khoản công khai của FTMO hay The5ers bảo đảm rằng hóa đơn tạo ngày `30/11` để chưa thanh toán đến `11–13/12` (sau NFP `04/12`, hết Free Trial `08/12`, CPI `10/12`) sẽ giữ được giá Black Friday `-30%`. Trạng thái pháp lý chuẩn là **`NOT_DISCLOSED` — bắt buộc xác nhận với Support FTMO**.

### 2.1. Tách bạch tuyệt đối giữa Điều khoản Chính thức (`T1`) và Kinh nghiệm Cộng đồng (`T3`)

1. **Những gì ĐÃ xác minh trong Điều khoản Chính thức (`T1_PRIMARY_OFFICIAL`):**
   - **FTMO General Terms & Conditions — Clause 3.4 (Hóa đơn tạm tính & hủy đơn):** Khi chọn **chuyển khoản ngân hàng (`bank transfer`)**, FTMO gửi **hóa đơn tạm tính điện tử (`electronic proforma invoice`)** ghi số tiền và thời hạn thanh toán cụ thể trên hóa đơn đó (*"within the period specified in the proforma invoice"*). Phí chỉ tính là đã thanh toán khi tiền vào đủ tài khoản FTMO. **Nếu không thanh toán đúng hạn, FTMO có toàn quyền hủy đơn hàng (`entitled to cancel your order`).**
   - **Con số `14 ngày` chính thức trong FTMO GTC thuộc về 3 quy định khác, KHÔNG phải cam kết treo đơn Black Friday:**
     - **Quyền rút khỏi hợp đồng `14 ngày` (EU Consumer Withdrawal Right):** Áp dụng cho khách hàng **ĐÃ thanh toán** gửi yêu cầu về `support@ftmo.com` trong `14 ngày`, **VỚI ĐIỀU KIỆN CHƯA ĐẶT BẤT KỲ LỆNH NÀO** trên tài khoản demo (mở lệnh đầu tiên sẽ làm mất quyền hoàn tiền ngay lập tức).
     - **Mốc rút thưởng đầu tiên (`14 ngày`):** Tối thiểu `14 ngày` lịch từ lệnh đầu tiên trên Funded Account.
     - **Đáo hạn hóa đơn rút thưởng & thời gian chờ duyệt hoa hồng affiliate (`14 ngày`).**
   - **FTMO quy đổi tiền tệ:** Giá gốc neo theo EUR; ngoại tệ khác quy đổi theo tỷ giá thị trường tại thời điểm xử lý thanh toán.
   - **The5ers Terms & Conditions (`T1_PRIMARY_OFFICIAL`):** Cơ chế tương tự — chỉ phát hành `electronic proforma invoice` khi thanh toán kiểu chuyển khoản ngân hàng và công ty có quyền hủy đơn nếu không thanh toán đúng hạn; **KHÔNG có điều khoản giữ giá Black Friday `14 ngày` (`NOT_DISCLOSED`)**.

2. **Những gì là `NOT_DISCLOSED` ở `T1` và đang có bằng chứng mâu thuẫn ở `T3`:**
   - **Thời hạn treo hóa đơn `~14 ngày` trên `trader.ftmo.com/billing`:** Chỉ được ghi nhận bởi **cộng đồng trader Việt Nam (`T3_FORUM_EXPERIENCE`, `hocvientrader.com`)**, không được công bố thành điều khoản cố định trong GTC của FTMO.
   - **Thanh toán SAU `30/11 10:00 CET` có giữ được giá `-30%` hay bị hủy/quay về `98,61 USD`?** **Trạng thái: `NOT_DISCLOSED` / Rủi ro hết hạn cao (`HIGH_EXPIRY_RISK`).** Các nguồn quốc tế (`T3`: `fxify.com`, `propfirmtrader.com`) cảnh báo giá khuyến mãi gắn với phiên thanh toán và khung chương trình — khi hóa đơn/link thanh toán hết hạn sau ngày `30/11`, đơn giảm giá bị vô hiệu và phải mua lại ở giá gốc.

### 2.2. Đối chiếu theo từng Phương thức Thanh toán

| Phương thức thanh toán trên FTMO | Có phát hành Proforma Invoice `14 ngày` theo GTC? | Thời gian sống thực tế của phiên/hóa đơn | Khả năng dùng tại Việt Nam để giữ giá `30/11 -> 13/12` |
|---|---|---|---|
| **Chuyển khoản ngân hàng (`Bank Wire / SWIFT`)** | **Có phát hành `proforma invoice` (GTC Clause 3.4)**; hạn thanh toán ghi trực tiếp trên bill (không cam kết cứng `14 ngày` hay giữ giá BF sau `30/11`). | Theo ngày đáo hạn ghi trên proforma invoice (FTMO có quyền hủy nếu quá hạn). | **KHÔNG khuyến nghị cho gói 10K (`68,70 USD`):** phí điện SWIFT + ngân hàng trung gian từ VN tốn **`15–40 USD`** (xóa sạch khoản tiết kiệm `29,91 USD` của Black Friday) và vướng thủ tục ngoại hối cá nhân. |
| **Thẻ Visa / Mastercard / Apple Pay / Google Pay / PayPal / Revolut** | **Không** (thanh toán tức thì; không nêu proforma invoice trong GTC). | Phiên cổng thanh toán hết hạn sau vài phút; lớp giỏ hàng `Đang chờ` trên `trader.ftmo.com/billing` là **`NOT_DISCLOSED`** trong GTC. | **Chỉ khả thi nếu Support xác nhận bằng văn bản** đơn `Đang chờ` tạo trước `30/11 16:00 ICT` vẫn bấm trả bằng thẻ được ngày `11–13/12` ở giá `68,70 USD`. |
| **Tiền mã hóa (`Crypto`: BTC/ETH/USDT/USDC/LTC)** | **Không.** | Bộ đếm tỷ giá cổng crypto hết hạn nhanh (**`15` phút đến vài giờ**). | **TUYỆT ĐỐI KHÔNG dùng để treo bill 14 ngày** — gửi coin sau khi link hết hạn sẽ kẹt tiền và không được giữ giá sale. |
| **Skrill** | **Không.** | Xử lý ví tức thì. | **Không khuyến nghị tại VN** (phí nạp/rút cao, hay bị ngân hàng VN từ chối). |

### 2.3. Phán quyết thực chiến cho Chủ sở hữu (`30/11 -> NFP 04/12 -> Trial 08/12 -> CPI 10/12 -> 14/12`)

1. **Không đánh cược vào giả định "chắc chắn giữ được bill 14 ngày":** Nếu dựa vào giữ bill chưa trả mà không hỏi Support trước, bạn phải coi xác suất đơn bị FTMO hủy sau `30/11 16:00 ICT` là **có thật**. Điểm sáng duy nhất là **thiệt hại tiền mặt ở kịch bản xấu nhất = `0 VND`** (chỉ mất khoản giảm `29,91 USD ≈ 770k VND`, vẫn còn cửa đợt sale Giáng Sinh/Năm Mới `20/12–07/01` hoặc giá thường `98,61 USD`).
2. **Hai câu hỏi `< 2 phút` gửi Live Chat / `support@ftmo.com` TRƯỚC `30/11`:**
   - *Câu 1:* "Nếu tôi tạo đơn FTMO 2-Step Standard 10K USD trước `30/11/2026 10:00 CET` nhưng để trạng thái chưa thanh toán (`unpaid / pending`) trên Client Area Billing, tôi có thể thanh toán bằng thẻ Visa/Mastercard vào ngày `11–13/12/2026` và vẫn giữ nguyên giá Black Friday `-30%` không, hay đơn sẽ tự hủy / đổi về giá gốc?"
   - *Câu 2:* "Nếu tôi thanh toán bằng thẻ trước `30/11/2026 10:00 CET` nhưng **không đặt bất kỳ lệnh giao dịch nào** trong `10–12` ngày, quyền rút khỏi hợp đồng hoàn `100%` phí trong `14` ngày theo GTC có áp dụng cho đơn Black Friday tại Việt Nam không?"
3. **Phương án hành động sau khi có câu trả lời Support (hiện giữ cứng `0 VND`):**
   - Nếu Support xác nhận **CÓ** ở Câu 1 -> giữ nguyên lộ trình **`0 VND` ngày `30/11`**, gom trọn dữ liệu sống qua NFP `04/12`, Free Trial `08/12`, CPI `10/12` rồi mới bấm trả tiền ngày `11–13/12`.
   - Nếu Support trả lời **KHÔNG** ở Câu 1 -> hoặc (a) chấp nhận bỏ sale Black Friday (`0 VND`, giữ kỷ luật đo xong Demo rồi mới mua), hoặc (b) chỉ cân nhắc phương án trả thẻ trước `30/11` + giữ `0` lệnh chờ đến `11–13/12` **KHI VÀ CHỈ KHI** Support xác nhận rõ **CÓ** ở Câu 2 (vẫn lưu ý ngân hàng VN có thể không hoàn `~2,5%` phí FX `~45k VND` nếu hủy đơn) và có phán quyết GO của chủ sở hữu.

---

## 3. Bảng Sai Lệch Chính Xác (`Exact Diff Table`) So Với Sổ Chuẩn SSOT

Đã đối soát tự động bằng [prop_terms_radar.py](../../tooling/automation/prop_terms_radar.py) giữa 2 tệp SSOT ([firms_catalog.json](../../tooling/ai-engines/configs/ssot/firms_catalog.json) & [prop_pricing_catalog.json](../../tooling/ai-engines/configs/prop_pricing_catalog.json)) và dữ liệu sống ngày `27/11/2026`.

- **Kiểm tra khớp nội bộ giữa 2 tệp SSOT (`17/17` hợp đồng trùng nhau: `5` FTMO Standard + `5` FTMO Swing + `2` The5ers + `5` IC Funded):** **`0` sai lệch** (giá gốc, giá BF, mục tiêu P1/P2, Daily/Max DD, cửa sổ tin, chia lãi, min payout khớp 100%).
- **Tổng số sai lệch / cảnh báo mới phát hiện so với thực tế sống (`27/11/2026`):** **`17` mục** (`0 CRITICAL`, `4 HIGH`, `11 MEDIUM`, `2 LOW` — trong đó `6` mục The5ers promo `5K/10K/25K` Classic+New và `3` mục IC Funded promo `5K/10K/25K` được gộp gọn thành 2 dòng bảng dưới để dễ đọc).

| Mã sai lệch (`drift_id`) | Mức độ | Quỹ / Gói | Giá trị trong SSOT (`26/11`) | Thực tế sống (`27/11`) | Bậc nguồn | Tác động & Đề xuất cập nhật (không tự sửa SSOT trong lane này) |
|---|---|---|---|---|---|---|
| `EXT_IC_FUNDED_2STEP_PRO_NEWS_WINDOW_SEC` | **HIGH** | IC Funded `2-Step Pro` | `news_window_sec = 600` (`±10` phút) | **`180` giây (`±3` phút)** cho 2-Step Funded (`600s` chỉ áp cho một số gói Instant) | `T1_PRIMARY_OFFICIAL` | SSOT đang bảo thủ rộng hơn (an toàn cho EA), nhưng cần tách `180s` (2-Step) vs `600s` (Instant) khi mô phỏng. |
| `EXT_IC_FUNDED_2STEP_PRO_QUALITATIVE_CONSISTENCY` | **HIGH** | IC Funded `2-Step Pro` | `best_day_cap_pct = null`, không có cờ consistency | **Terms Section 12 ("Inconsistent Trading"):** cấm đổi mạnh lot size, tần suất, chiến lược, mức rủi ro giữa Eval và Funded | `T1_PRIMARY_OFFICIAL` | **Cờ đỏ lớn cho `Master_Prop7E`:** KHÔNG chạy giảm lot đột ngột `P1 4x -> Funded 1x` trên IC Funded nếu chưa có xác nhận văn bản từ Support! |
| `EXT_FTMO_14D_INVOICE_LOCK_UNVERIFIED` | **HIGH** | FTMO (`bf_14day_payment_cutoff`) | Mốc hợp đồng `2026-12-14 16:00 ICT` | **`NOT_DISCLOSED`** trong GTC (Clause 3.4 cho FTMO quyền hủy đơn chưa trả) | `T1_PRIMARY_OFFICIAL` | Gắn cờ bắt buộc xác nhận `support@ftmo.com` trước khi coi mốc `14/12` là khóa giá an toàn. |
| `EXT_THE5ERS_14D_INVOICE_LOCK_UNVERIFIED` | **HIGH** | The5ers (Unpaid Invoice) | Chưa ghi quy tắc treo hóa đơn | **`NOT_DISCLOSED`** (chỉ có proforma invoice bank wire; quyền hủy đơn quá hạn) | `T1_PRIMARY_OFFICIAL` | Không giả định giữ giá Black Friday bằng hóa đơn chưa thanh toán trên The5ers. |
| `EXT_FTMO_2STEP_STANDARD_MIN_PAYOUT_CHANNEL` | **MEDIUM** | FTMO `2-Step Standard` | `min_payout_usd = 50,0` | **`20 USD`** (Bank Wire & Visa Direct / MC Send) · **`50 USD`** (Crypto) | `T1_PRIMARY_OFFICIAL` | SSOT bảo thủ theo mức Crypto; nên tách rõ `20 USD` vs `50 USD` theo kênh rút. |
| `EXT_FTMO_BF_CUTOFF_DISCREPANCY` | **MEDIUM** | FTMO Black Friday 2026 | `2026-11-30 16:00 ICT` (`10:00 CET`) | Đa số nguồn `10:00 CET`; `1` nguồn `T3` (`propfirmcircle.com`) ghi `10:30 CET` | `T3_GENERAL_WEB` | Giữ mốc bảo thủ sớm nhất `16:00 ICT` (`10:00 CET`), kiểm đồng hồ web trước `15:00 ICT`. |
| `EXT_THE5ERS_HIGH_STAKES_*_PROMO_USD` *(6 gói `5K/10K/25K` Classic & New)* | **MEDIUM** | The5ers High Stakes | `promo_discount_frac = 0,0` (`LIST_PUBLIC_TERMS`) | Tín hiệu BF 2026 **`-10%` toàn trang** (`35,10 / 31,50 USD` cho 5K; `175,50 / 158,40 USD` cho 25K) | `T3_GENERAL_WEB` (`T2/T3`) | Giữ nguyên giá list trong SSOT cho tới khi chủ sở hữu kiểm tra trực tiếp trên `the5ers.com/high-stakes/`. |
| `EXT_IC_FUNDED_2STEP_PRO_*_PROMO_USD` *(3 gói `5K/10K/25K`)* | **MEDIUM** | IC Funded `2-Step Pro` | `promo_discount_frac = 0,0` (`LIST_PUBLIC_TERMS`) | Mã **`BLACKIC45` (`-45%`)** tới `30/11/2026` (`40,70 / 68,75 / 136,95 USD`) | `T3_GENERAL_WEB` | **Chưa xác minh T1** — không nạp vào bộ tối ưu vốn trước khi thử trực tiếp trên checkout `icfunded.com`. |
| `EXT_THE5ERS_EXTRA_TIERS` | **LOW** | The5ers High Stakes | Chỉ liệt kê `5K/10K/25K/50K/100K` | Báo cáo thêm tier nhỏ **`2,5K`** (`19 USD New / 22 USD Classic`) | `T3_GENERAL_WEB` | Cân nhắc bổ sung `2,5K` nếu xác minh trên checkout; **`20K` xác nhận đã bỏ khỏi High Stakes**. |
| `EXT_IC_FUNDED_2STEP_PRO_PROFIT_SPLIT_START` | **LOW** | IC Funded `2-Step Pro` | `profit_split_pct = 80,0` | Trang `icfunded.com` nêu chia lãi từ **`75%` đến `90%`** tùy gói/chu kỳ | `T1_PRIMARY_OFFICIAL` | Kiểm tra đúng tỷ lệ chia khởi điểm (`75%` hay `80%`) trên màn hình chọn gói `2-Step Pro` trước khi mua. |

---

## 4. Rà Soát 6 Nhóm Quy Tắc Quan Trọng Nhất Cho `Naqex_Master_Prop7E` (`27/11/2026`)

| Hạng mục kiểm tra | FTMO (`T1`) | The5ers High Stakes (`T1`) | IC Funded (`T1`) | Khớp với `Naqex_Master_Prop7E`? |
|---|---|---|---|---|
| **1. EA tự viết & EA bên thứ ba** | Cho phép cả EA tự viết & bên thứ ba trên MT5; **cảnh báo rủi ro EA bên thứ ba trùng lệnh sẽ đụng trần vốn `400.000 USD` chung chiến lược**. Trần **`2.000`** server msg/ngày & `200` lệnh mở. | Cho phép EA tự viết sở hữu `100%` mã nguồn; **cấm tuyệt đối** EA bên thứ ba/công khai, copy trade bên ngoài, HFT, arbitrage, rollover scalping, kẹp tin (`news bracketing`). Nên xin xác nhận văn bản trước Funded. | Cho phép EA tự viết kiểm soát mã nguồn, trần **`3.000`** msg/ngày; cấm EA thương mại/thuê, copy trade nhóm, HFT, martingale, grid, khai thác độ trễ. | **Khớp sạch 100%** (mã độc quyền `.mq5`, `0–3` lệnh/ngày, `< 20` msg/ngày, không grid/martingale). |
| **2. Tin đỏ (`Restricted News`)** | Eval (P1/P2) & Swing: **miễn**. Standard Funded & Instant: **cấm `±2` phút** quanh tin Restricted (gồm mở, đóng, pending, **cả `SL`/`TP` tự khớp**). | Cả **Eval & Funded** High Stakes: **cấm thực thi lệnh `±2` phút** quanh tin đỏ (vi phạm bị **soft breach — xóa sạch lãi, giữ nguyên lỗ**). | Eval: cho phép. Funded 2-Step: **cấm `±3` phút** quanh tin đỏ (`±10` phút trên một số gói Instant). | **Khớp an toàn** với `PropGuard ±5m` + tự đóng phẳng trước `-2m15s` (bao trọn cả `±2m` và `±3m`). |
| **3. Luật nhất quán (`Consistency`)** | **Không có** Best-Day Cap trên `2-Step Standard/Swing` (`1-Step` có `50%`, `Instant` có `30%`). | **Không có** Best-Day Cap trên High Stakes CFD; yêu cầu **`>= 3` ngày lãi `>= +0,5%`** mỗi vòng (`min(Midnight Bal, Midnight Eq) - Prev Day Bal`). | **CỜ ĐỎ (Section 12):** Luật nhất quán định tính về **lot size, tần suất, chiến lược, mức rủi ro** giữa Eval và Funded + `5` ngày lãi `>= 0,5%` cho payout đầu. | **FTMO 2-Step khớp nhất**; trên IC Funded phải tắt chế độ nhảy lot `4x -> 1x`. |
| **4. Rút thưởng & Hoàn phí** | Chu kỳ **`14` ngày**, chia `80% -> 90%`, **phí phía FTMO `0%`**, hoàn **`100%` tiền mặt** ở payout đầu (`2-Step`). Min **`20 USD`** (Wire/Card), **`50 USD`** (Crypto). | Chu kỳ **`14` ngày**, min **`150 USD`**, chia `80% -> 100%`, **phí rút `3,5%`** (Rise/Crypto/Bank; `0%` chỉ cho Hub Credits). Hoàn phí tách `30%` Hub Credit + `70%` tiền mặt payout đầu. | Chu kỳ **`14` ngày**, chia `75–80% -> 90%`, hoàn phí **chậm ở payout thứ `3`**. | **FTMO vượt trội về dòng tiền thực (`Settled Cash`)** và tốc độ hoàn phí. |
| **5. Điều kiện Việt Nam** | **Hợp lệ (`true`).** Hỗ trợ KYC cá nhân VN, Bank Wire, Crypto (`USDT/USDC/BTC/ETH/LTC`), Visa Direct / MC Send, Skrill. | **Hợp lệ (`true`).** Việt Nam không nằm trong Forbidden Territories; hỗ trợ MT5 & Riseworks VN. | **Hợp lệ (`true`)** (có tiếng Việt & lịch sử payout trader VN), nhưng điều khoản lưu ý người dùng tự chịu trách nhiệm pháp luật địa phương. | Cả 3 quỹ đều mở cho Việt Nam (không thuộc danh sách cấm như FundedNext/FundingPips). |
| **6. IP, VPS & CGNAT (RFC 6598)** | Cho phép VPS riêng; **cấm IP/VPS Mỹ**, cấm chia sẻ VPS/VPN đổi quốc gia liên tục. | Cho phép VPS riêng; giám sát log IP/thiết bị chống dùng chung tài khoản và cấm Forbidden Territories. | Cấm chia sẻ IP/VPS/proxy liên kết nhiều tài khoản; giữ quyền kiểm tra lưu lượng bất thường. | **Cảnh báo VN:** Tránh IP dùng chung dải **CGNAT (RFC 6598)** trên mạng gia đình; ưu tiên IPv4 tĩnh hoặc VPS riêng Singapore/EU. |

---

## 5. Danh Mục Nguồn Đối Chiếu (`untrusted_external_data: true`, `2026-11-27`)

- **`T1_PRIMARY_OFFICIAL`:**
  - `https://ftmo.com/en/black-friday/`
  - `https://ftmo.com/en/terms-and-conditions/`
  - `https://ftmo.com/en/faq/trading-objectives/`
  - `https://ftmo.com/en/faq/can-i-trade-news/`
  - `https://ftmo.com/en/faq/how-can-i-pay-for-the-ftmo-challenge/`
  - `https://ftmo.com/en/faq/how-do-i-withdraw-my-reward/`
  - `https://ftmo.com/en/forbidden-trading-practices/`
  - `https://trader.ftmo.com/start-challenge`
  - `https://the5ers.com/high-stakes/`
  - `https://the5ers.com/terms-and-conditions/`
  - `https://the5ers.com/faqs/`
  - `https://icfunded.com/`
  - `https://icfunded.com/terms-and-conditions/`
- **`T2_TECHNICAL_COMMUNITY`:** `https://www.fxstreet.com/` (tín hiệu ưu đãi Black Friday & quy tắc rút tiền The5ers/IC Funded).
- **`T3_FORUM_EXPERIENCE` / `T3_GENERAL_WEB`:** `reddit.com` (giờ cắt `10:00 CET`), `hocvientrader.com` (quan sát giữ bill `14 ngày` trên billing VN & bảng High Stakes Classic/New), `propfirmcircle.com` (giờ `10:30 CET` & cấu trúc 30%/20%), `forexpropfirms.com` (The5ers BF `-10%`), `propfirmdiscount.com` & `firmscopes.com` (mã `BLACKIC45` chưa xác minh T1), `selectpropfirms.com` (bảng phí High Stakes `2,5K–100K`), `scribd.com` / `studocu.vn` (bản lưu trích dẫn FTMO GTC Clause 3.4).

---

## 6. Công Cụ Theo Dõi Tự Động (`tooling/automation/prop_terms_radar.py`)

Đã hoàn thiện script kiểm tra lệch định kỳ [prop_terms_radar.py](../../tooling/automation/prop_terms_radar.py) và bộ kiểm thử ngoại tuyến [test_prop_terms_radar.py](../../tooling/ai-engines/tests/test_prop_terms_radar.py):

1. **Chế độ ngoại tuyến chuẩn CI (`--offline`, `0` gọi mạng):** so khớp nội bộ 2 tệp SSOT, kiểm độ tươi dữ liệu (`<= 7` ngày), đối chiếu bảng điều khoản/khuyến mãi đã xác minh và ghi nguyên tử ra `.runtime/automation/prop_terms_radar_latest.json`.
2. **Chế độ chạy thử không ghi đĩa (`--dry-run`):** in báo cáo + JSON nhưng giữ nguyên hệ thống tệp.
3. **Chế độ kiểm tra công khai trực tiếp (`--live`):** chỉ gọi HTTPS GET đọc công khai vào 7 URL `T1_PRIMARY_OFFICIAL`, tự dừng ngay khi gặp cổng anti-bot/CAPTCHA (`ANTI_BOT_BLOCKED_STOPPED`) hoặc quá thời gian TLS (`UNREACHABLE_OR_TIMEOUT`), không bao giờ đăng nhập hay đặt lệnh (`ORDER_SEND_COUNT = 0`).
4. **Theo dõi song song cả 2 mốc thời hạn Black Friday:** `2026-11-30T16:00:00+07:00` (`bf_bill_lock`) và `2026-12-14T16:00:00+07:00` (`bf_14day_payment_cutoff`), cùng 4 mốc trung gian (`Holdout v2 Lock 01/12`, `NFP 04/12`, `Free Trial End 08/12`, `CPI 10/12`).

**Bước tiếp theo (`< 2 phút`):** Gửi 2 câu hỏi ở Mục `2.3` tới Live Chat FTMO / `support@ftmo.com` trước ngày `30/11/2026`, lưu Ticket ID vào hồ sơ tuân thủ, và giữ nguyên `0 VND` cho tới khi nhận xác nhận chính thức.
