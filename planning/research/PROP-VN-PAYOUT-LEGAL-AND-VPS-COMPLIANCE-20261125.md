---
doc_type: primary-source-compliance-research
updated_utc: 2026-11-25
deadline_ict: "2026-11-30 16:00 ICT (10:00 CET)"
order_send_count: 0
holdout_rows_analysed: 0
---

# Mũi 5: Kênh Rút Tiền VN, Tuân Thủ EA/Home-VPS (FTMO & The5ers) & Nút Thắt Sổ Vốn Riêng (`IBKR` / `Crypto Spot`)

> **Nhãn nguồn:** `[Chính thức]` = trang gốc sàn/pháp quy (`25/11/2026`); `[Cộng đồng]` = kinh nghiệm trader VN; `[Kiểm Checkout]` = đối chiếu trực tiếp lúc thanh toán/Hub.
> **Khóa an toàn:** `OrderSend = 0`, `Holdout 2025+ SEALED`, `0` bí mật/IP nội bộ. Mục 3 là chuẩn bị vận hành & sổ sách, **KHÔNG phải tư vấn pháp lý/thuế có chứng chỉ**.

---

## 1. FTMO (2026): Black Friday, EA/Home-VPS, Tin Đỏ & Kênh Rút Việt Nam

### 1.1. Điều khoản Black Friday CFD, Hoàn Phí, Ngủ Đông & Tăng Vốn

| Hạng mục | Quy định `[Chính thức ftmo.com]` | Hành động thực chiến |
|---|---|---|
| **Hạn sale & Loại TK** | Giảm tới `-30%` CFD (hạn `30/11/2026 10:00 CET / 16:00 ICT`; Cyber Monday áp cho Futures) áp cho **`FTMO Standard`** ngoài Mỹ/Úc; **không cho đổi `Standard -> Swing`** sau mua. | `[Kiểm Checkout]` giá thật trên `trader.ftmo.com` (`62,30 EUR` hay `98,70 EUR` gói `10K`, mã sale không cộng dồn). |
| **`2-Step` vs `1-Step`** | **`2-Step` (`Standard`/`Swing`):** hoàn **`100%`** phí ở lần rút thưởng đầu, trả về **đúng phương thức thanh toán lúc mua**. **`1-Step` / `Instant`:** **KHÔNG hoàn phí** (và `1-Step` có thêm luật Best-Day). | **Chỉ chọn `2-Step`.** Dùng thẻ chính chủ còn hạn dài (tránh thẻ ảo 1 lần dễ kẹt hoàn phí). |
| **Quyền hủy `14` ngày** | Quyền rút lui `14` ngày (EU GTC) mất hiệu lực ngay khi mở lệnh đầu tiên. Đơn *chưa thanh toán* có thể bị hủy và không bảo đảm khóa giá sale sau `30/11 10:00 CET`. | Không dựa vào đơn chưa trả; tuyệt đối không spam đơn hay *chargeback*. |
| **Ngủ đông & Đóng băng** | Không mở lệnh **`30` ngày dương lịch liên tiếp** gây cảnh báo/rủi ro đóng tài khoản (chỉ login/đặt lệnh chờ không tính). Được xin **Account Freeze** (`7` ngày–`6` tháng). | Nếu tạm dừng bot quá `2` tuần, mở ticket xin **Account Freeze**. |
| **Trần `400K` & Scaling** | Trần vốn ban đầu **`400.000 USD`** / trader **hoặc / chiến lược giống nhau**. **Scaling Plan:** mỗi **`4` tháng**, lãi ròng `>= +10%`, đã rút `>= 2` lần và số dư dương -> tăng **`+25%`** vốn (tối đa `2.000.000 USD`), chia **`80% -> 90%`**. | Chạy chiến lược độc quyền riêng để không bị gộp hạn mức `400.000 USD` với người lạ. |

*Nguồn:* [2-Step](https://ftmo.com/en/2-step-challenge/) · [Swing](https://ftmo.com/en/faq/ftmo-swing-account-type/) · [Black Friday](https://ftmo.com/en/black-friday/) · [Scaling](https://ftmo.com/en/scaling-plan/) · [FAQ](https://ftmo.com/en/faq/) · [Terms](https://ftmo.com/en/terms/).

### 1.2. Tuân Thủ EA Tự Viết, Home-VPS & IP Việt Nam

- **`[Chính thức]`:** FTMO **cho phép EA / algo** trên MT5, không bắt nộp mã nguồn trước. Ranh giới cấm: (1) **Quá tải (*Hyperactivity*):** tối đa `200` lệnh mở cùng lúc và **`2.000` vị thế/yêu cầu máy chủ/ngày** (`Naqex_Master_Prop7E` chỉ phát `0–3` lệnh/ngày, `< 20` req/ngày); (2) **Copy / EA bên thứ ba / nhóm:** được copy giữa các tài khoản **chính chủ**, cấm tín hiệu công khai, quản lý hộ hoặc EA thương mại trùng dấu vết (vướng trần `400.000 USD`); (3) **IP/VPS:** cho phép VPS/VPN nhưng **CẤM IP/VPS tại Mỹ (US)** và cấm chia sẻ VPS/đăng nhập.
- **Cờ đỏ VN — CGNAT (`100.64.0.0/10`):** Nhiều gói cáp quang dân dụng VN dùng CGNAT gộp nhiều hộ chung 1 IPv4 công cộng (`[Cộng đồng]`: dễ bị quét liên đới nếu người khác trên cùng IP vi phạm). **Phòng ngừa (`naqex-node1`):** kiểm WAN IP router không thuộc `100.64.0.0/10` (nếu dính, xin ISP cấp IPv4 công cộng riêng hoặc thuê VPS IPv4 tĩnh Singapore/EU, không chọn Mỹ); tắt VPN chia sẻ; lưu mã `.mq5`, lịch sử git, hóa đơn mạng và ticket FTMO.

*Nguồn:* [FTMO Forbidden Trading Practices](https://ftmo.com/en/forbidden-trading-practices/).

### 1.3. Danh Sách Tin Đỏ Hạn Chế (`Restricted News`): `Standard Funded` vs `Swing`

- **`[Chính thức]`:** **Vòng 1–2 (`Challenge/Verification`)** và **`Swing Funded`** được **MIỄN** luật tin đỏ `±2` phút. Riêng **`Standard Funded`** cấm mọi thực thi lệnh — **gồm mở, đóng, lệnh chờ và cả `SL`/`TP` tự khớp** — trong **`±2` phút** quanh tin đánh dấu `Restricted event` trên [FTMO Calendar](https://ftmo.com/en/calendar/):
  - **`USD`** *(cặp USD, `XAUUSD`, `US100/500/30/2000.cash`, `DXY`)*: Federal Funds Rate & Statement, NFP + Unemployment & Wages, Advance GDP q/q, **FOMC Meeting Minutes**, CPI y/y.
  - **`EUR`:** ECB Main Refinancing Rate · **`GBP`:** BoE Bank Rate & MPC Votes, UK CPI y/y.
  - **`CAD`:** BoC Rate/Statement, CAD CPI m/m *(kiểm thêm việc làm CAD trên lịch tuần)* · **`AUD`:** RBA Cash Rate & Statement.
- **Khớp kỹ thuật Naqex:** Bộ `7E` đóng phẳng `100%` trước `20:55 UTC` (`swap = 0`, không giữ cuối tuần) và `naqex_red_news_utc.csv` (`492` dòng, đã vá đủ `16` mốc `FOMC Minutes 2026–2027`) tự đóng phẳng trước `-2m15s`, khóa cứng `±5m`. Nguồn: [Can I trade news?](https://ftmo.com/en/faq/can-i-trade-news/).

### 1.4. Kênh Rút Tiền Việt Nam (`2026`), KYC & Thời Gian Xử Lý

- **VN được hỗ trợ.** Sau đậu Vòng 2, xác minh **FTMO Identity** theo diện **Cá nhân (`Natural Person / KYC`)** (không cần lập công ty): Hộ chiếu hoặc CCCD gắn chip + Sao kê ngân hàng xác nhận địa chỉ khớp tên đăng ký -> ký điện tử **FTMO Account Agreement** (FTMO Trading Global s.r.o.).
- **Chu kỳ & Phí `[Chính thức]`:** Rút đầu tiên sau ngày lịch thứ **`14`** từ lệnh đầu trên Funded (vị thế phải phẳng); duyệt `1–2` ngày làm việc, giải ngân `1–2` ngày làm việc. **FTMO thu `0%` hoa hồng rút thưởng** và **không dùng Riseworks** làm kênh chính. Nguồn: [How do I withdraw my reward?](https://ftmo.com/en/faq/how-do-i-withdraw-my-reward/).

| Kênh FTMO | Ngưỡng / Trần `[Chính thức]` | Tốc độ & Chi phí thực tế | Lưu ý cư dân Việt Nam |
|---|---|---|---|
| **Bank Wire (SWIFT)** | Min `20 USD` | `2–5` ngày; phí điện trung gian + ngân hàng VN ~`15–40 USD` `[Cộng đồng]` | **Ưu tiên cho dòng tiền sạch/lớn:** ngân hàng VN (VCB/TCB/ACB) yêu cầu Hợp đồng FTMO + Hóa đơn payout; chứng từ chuẩn cho thuế. |
| **Crypto** (`USDT TRC20`, `USDC ERC20`, `BTC`, `ETH`, `LTC`) | Min `50 USD` | Gửi trước **`12:00` CET/CEST** thường xử lý cùng ngày (sau trưa T6 -> T2 xử lý); chịu tỷ giá/phí mạng | `[Cộng đồng]`: nhanh, phổ biến nhất (`USDT TRC20`), nhưng có **rủi ro khóa TK ngân hàng nếu P2P dính tiền bẩn** & chịu khung pháp lý CASP mới (Mục 3.2). |
| **Visa Direct / MC Send** | Min `20 USD`, trần `20.000 USD` | Vài giờ–`1` ngày sau duyệt | `[Kiểm Checkout/Client Area]`: tùy ngân hàng phát hành thẻ VN có mở chiều nhận hay không. |
| **Skrill** | Trần `3.000 USD` | Về ví ~`1` ngày, nhưng rút về ngân hàng VN phí cao & hay bị từ chối `[Cộng đồng]` | **Không khuyến nghị** làm kênh chính tại VN. |

---

## 2. The5ers (`High Stakes 5K` — Theo Dõi Ngoài Lề, Không Mở Tuần BF)

### 2.1. Quy Tắc EA (`Terms §11`), IP/VPS, Tin Đỏ & Ngủ Đông `[Chính thức]`

- **EA & Mã nguồn:** Cho phép EA nếu **sở hữu `100%` mã nguồn**; cấm EA mua/thuê/chia sẻ, SL ẩn (*stealth SL*), emulator, HFT/tick scalping/rollover scalping, arbitrage, bulk trading và kẹp lệnh chờ tin (*news bracketing*). *Lưu ý:* nhãn mục `Section 11` có thể thay đổi theo bản web của [Terms & Conditions](https://the5ers.com/en/terms-and-conditions/) -> email xin xác nhận phải nêu kèm tên chính sách EA/Prohibited Practices.
- **IP / VPS:** Cho phép VPS riêng; giám sát log IP/thiết bị để bắt chia sẻ tài khoản hoặc lệch vị trí địa lý bất thường.
- **Tin đỏ & Ngày giao dịch High Stakes CFD:** Giữ lệnh qua tin được phép, nhưng cấm thực thi lệnh trong **`±2` phút** quanh tin đỏ Forex Factory (**trừ sạch lãi, giữ nguyên lỗ**). **KHÔNG có luật Best-Day `50%`** trên High Stakes CFD (luật đó áp cho gói khác), mà yêu cầu **`>= 3` ngày lãi `>= +0,5%`** số dư gốc/vòng. Ngủ đông: **`30` ngày** (Eval) / **`60` ngày** (Pro).

### 2.2. Kênh Rút Tiền Việt Nam, Phí `3,5%`, Hoàn Phí & Scaling

| Hạng mục | Quy định `[Chính thức the5ers.com & riseworks.io]` | Tác động thực tế VN |
|---|---|---|
| **Min rút & Chu kỳ** | Min **`150 USD`** sau chia *(kiểm thẻ Hub trước mua vì một số gói có mức sàn riêng)*. Chu kỳ **`14` ngày** từ khi kích hoạt Pro; **Cờ đỏ: đồng hồ `14` ngày bị reset mỗi lần scale-up!** Duyệt `24–48h`, trả trong `3` ngày làm việc. | Thời gian hoàn vốn lâu (`~432` ngày ở `1,50×` trong mô phỏng Vòng 4). |
| **Phí rút (Cờ đỏ)** | **Rise, Crypto và Bank Transfer đều bị thu `3,5%`/lần rút** (`Hub Credits = 0%`, không rút tiền mặt). | Đắt hơn rõ rệt so với `0%` phía FTMO. |
| **Hoàn phí** | `10%` Hub Credit (P1) + `20%` Hub Credit (P2, không rút tiền mặt) + `70%` tiền mặt ở payout đầu. | `30%` kẹt thành tín dụng nội bộ, không tính vào `Settled Cash`. |
| **Rise (`riseworks.io`)** | Hỗ trợ VN (`190+` nước), bắt buộc KYC (**Rise ID**) & email trùng The5ers. Rút tiếp từ Rise: **USDC Arbitrum `1,00 USD`**, USDC chuỗi khác `2,50 USD` + gas, VND ngân hàng VN **`10 USD` + `1,13%–1,90%` FX**, SWIFT USD **`25 USD`**. | Chịu **2 tầng phí** (`3,5%` The5ers + phí Rise). |
| **Crypto trực tiếp / Bank** | Crypto: `USDT TRC20`, `USDC ERC20`, `ETH`, `LTC`, **trần `1.500 USD`/lần**, phí `3,5%`. Bank Transfer: `3,5%` + phí ngân hàng trung gian. | Cân nhắc so sánh tổng phí với Rise nếu sau này chạy The5ers. |
| **Scaling Plan** | Chia **`80% -> 100%`**, nâng vốn mỗi mốc **`+10%`** lãi tích lũy tới trần **`500.000 USD`**. | Chỉ xét sau khi đã có `>= 2` kỳ payout tiền mặt từ FTMO. |

*Nguồn:* [The5ers High Stakes](https://the5ers.com/high-stakes/) · [Help Center](https://help.the5ers.com/) · [Riseworks](https://www.riseworks.io/).

---

## 3. Sổ Vốn Riêng VN (`IBKR` + `Crypto Spot B06/B02`), Nút Thắt Ngân Hàng & Sổ Sách

> **Miễn trừ:** Thông tin tổng hợp quy định công khai phục vụ quản trị vận hành và lưu hồ sơ, **KHÔNG phải tư vấn pháp lý/thuế có chứng chỉ**.

### 3.1. Cờ Đỏ Nạp Rút `IBKR` Cho Cư Dân Việt Nam

1. **Cấm nạp bên thứ ba `[Chính thức interactivebrokers.com]`:** Cư dân VN mở được TK cá nhân IBKR (`1` lần rút miễn phí/tháng dương lịch; lần sau ~`10 USD` điện USD + phí trung gian), nhưng **khoản nạp phải từ TK ngân hàng đúng tên chủ IBKR** -> **KHÔNG THỂ rút thẳng từ FTMO, The5ers hay Riseworks vào IBKR**.
2. **Nút thắt ngoại hối (`Thông tư 20/2022/TT-NHNN`, `Nghị định 70/2014/NĐ-CP`) `[Chính thức]`:** Cá nhân cư trú chỉ được chuyển tiền ra nước ngoài cho các mục đích liệt kê (du học, chữa bệnh, công tác/du lịch, lệ phí, trợ cấp thân nhân, thừa kế, định cư) — **tự chuyển tiền từ ngân hàng VN sang IBKR mua chứng khoán/ETF (`SGOV/BIL`) KHÔNG thuộc diện được phép**.
3. **Hạn chế Wise VN `[Chính thức wise.com]`:** Wise cá nhân cư trú VN **không được mở đủ số dư đa tiền tệ / TK nhận USD** để nối sang IBKR (cấm khai gian địa chỉ nước ngoài vì rủi ro đóng băng AML).
4. **Hệ quả Naqex:** Củng cố quyết định **hoãn Own-Book IBKR `< 25.000 USD`**, tuyệt đối không dùng kênh chuyển chui/P2P lách ngoại hối; tiền về ngân hàng VN tạm giữ kênh hợp pháp trong nước tới khi tham vấn xong lộ trình quy mô lớn.

*Nguồn:* [Interactive Brokers](https://www.interactivebrokers.com/) · [Wise](https://wise.com/).

### 3.2. Pháp Lý & Thuế Crypto VN (`2025–2026`) Cho `B06/B02`

- **Luật Công nghiệp công nghệ số** công nhận tài sản số; **Nghị quyết `05/2025/NQ-CP`** (`09/09/2025`) thí điểm thị trường tài sản mã hóa `5` năm qua **CASP** được Bộ Tài chính cấp phép (giai đoạn chuyển tiếp `6` tháng từ khi CASP đầu tiên được cấp phép trước khi xử phạt giao dịch ngoài kênh cấp phép).
- **Thông tư `32/2026/TT-BTC`** (`27/03/2026`): chuyển nhượng tài sản mã hóa **miễn VAT**, áp **thuế TNCN `0,1%`/lần chuyển nhượng** với cá nhân (CASP cấp phép khấu trừ tại nguồn).
- **Hệ quả:** Giữ `B06/B02` chạy bóng (`OrderSend = 0`) tới khi rà soát danh sách CASP cấp phép; cân nhắc ưu tiên **SWIFT ngân hàng VN** cho khoản payout lớn để tránh rủi ro khóa TK do P2P.

### 3.3. Sổ Sách & Lưu Chứng Từ (`treasury_ledger.py`)

Cá nhân cư trú thuế VN (`>= 183` ngày/năm) chịu thuế thu nhập toàn cầu (payout prop firm là thu nhập dịch vụ nước ngoài, **không phải kiều hối miễn thuế**). Giữ `20%` dự phòng vận hành/thuế và ghi [`treasury_ledger.py`](../../tooling/ai-engines/quant_factory/treasury_ledger.py) (`SettledCashEvent`):
- Tách bạch `OUT_OF_POCKET_FEE`, `EXTERNAL_CASH_REFUND` (hoàn gốc, không phải lãi), `HUB_CREDIT_GRANT` (không tính tiền mặt), `PAYOUT_APPROVED` vs `PAYOUT_SETTLED` (`settled_date`, `withdrawal_fee_usd`, `fx_bank_fee_usd`), `OPS_CASH_OUT`, `TAX_PAID`.
- Lưu theo năm tại `E:\BACKUP-TRADINGWORKSPACE\compliance\YYYY\`: hóa đơn mua vé + sao kê thẻ `VND`; hợp đồng đã ký; email xác nhận EA + Ticket ID; Reward Invoice / Rise Statement; giấy báo có SWIFT (hoặc `txid` + chứng từ quy đổi); lịch rà soát thuế quý/năm với đại lý thuế.

---

## 4. Điểm Cần Bổ Sung Cho 2 Thư Xác Nhận EA Hiện Có

Đã rà soát [`FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md`](../../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md) (đã đủ quyền sở hữu mã, SL cứng, đóng `20:55 UTC`, khóa tin `±5m` gồm `FOMC Minutes`). Nên chèn thêm trước khi gửi:
1. **`support@ftmo.com`:** (i) cập nhật kiến trúc sang **`1` Master EA (`Naqex_Master_Prop7E`)** `< 20` req/ngày; (ii) thêm câu hỏi `(c)` về **IPv4 động/CGNAT cáp quang VN** (không VPN Mỹ); (iii) thêm `(d)` xác nhận **kênh rút VN** (`SWIFT`, `USDT TRC20 / USDC ERC20`, `Visa Direct / MC Send`) & hoàn phí `100%` gói `2-Step` về đúng thẻ VN đã thanh toán.
2. **`help@the5ers.com` (chỉ gửi khi mở The5ers):** (i) ghi rõ *"Terms & Conditions (Automated Trading / EA Policy, Section 11) and Prohibited Trading Practices"* và đồng bộ số EA thực triển khai; (ii) hỏi rõ xử lý khi `SL/TP` của lệnh mở trước `-2m` bị quét trong `±2m` tin đỏ High Stakes, cùng phí rút (`3,5%`?) và sàn rút tối thiểu cho VN qua `Rise` / `Crypto`.

---

## 5. Checklist 5 Phút Trước Thanh Toán (`30/11/2026`, Trước `16:00 ICT`)

Chỉ bấm mua **`1` vé `FTMO 10K`** khi đạt **5/5**:
1. **Astra Vòng 4:** Kiểm [`ASTRA-ROUND4-BLACKFRIDAY-GONOGO-DOSSIER-20261126.md`](ASTRA-ROUND4-BLACKFRIDAY-GONOGO-DOSSIER-20261126.md) -> ma sát Mũi 1–2 **`<= 1,50×`** và Astra **`GO`** (`> 1,50×` hoặc `NO-GO`: **DỪNG, bỏ sale**).
2. **Màn hình Checkout (`trader.ftmo.com`):** Đúng **`2-Step`** (KHÔNG `1-Step`), **`10.000 USD`** (đúng `USD`), **`Standard`** (chấp nhận không đổi sang `Swing`), xác nhận giá cuối (`62,30 EUR` hay `98,70 EUR`), họ tên/địa chỉ khớp **100%** Hộ chiếu/CCCD + sao kê.
3. **Thẻ & Bằng chứng:** Quẹt **thẻ Visa/Mastercard chính chủ còn hạn dài** (để nhận hoàn phí `100%` ở payout đầu); chụp màn hình checkout, lưu PDF hóa đơn + Ticket `support@ftmo.com` vào `compliance/2026/`.
4. **IP & `naqex-node1`:** WAN IP ở VN (**không** VPN Mỹ), kiểm không dính CGNAT `100.64.0.0/10` (nếu dính, xin IP công cộng trước khi sang Funded), lịch tin `492` dòng (`FOMC Minutes`) & Heroku đều xanh.
5. **Sổ sách & Kích hoạt:** Ghi ngay `OUT_OF_POCKET_FEE` (`VND` thực trừ) vào `treasury_ledger.py`. Mở lệnh #1 sẽ mất quyền hủy `14` ngày -> chỉ tắt `InpDryRunLogOnly` sau khi kiểm khớp số TK MT5, `US100.cash`, `1:100` và hồ sơ P1 được Astra duyệt.
