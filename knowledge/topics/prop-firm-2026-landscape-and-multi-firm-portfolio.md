---
doc_type: evergreen
domain: knowledge
topic: prop-firm-2026-landscape-and-multi-firm-portfolio
updated_utc: 2026-11-25
holdout_rows_analysed: 0
order_send_count: 0
sources:
  - "T1 (Chính thức 2026): Darwinex Zero (darwinexzero.com, darwinex.com — FCA FRN 586466); FTMO CFD & Futures (ftmo.com); The5ers (the5ers.com, help.the5ers.com); Topstep (topstep.com, help.topstep.com); Tradeify (tradeify.co); Riseworks (riseworks.io)"
  - "T1 (Nội bộ < 2025-01-01): LAB5-CME-FUTURES-PROP-STUDY-20261124.md, PROP-VN-PAYOUT-LEGAL-AND-VPS-COMPLIANCE-20261125.md, MUI3-MASTER-PROP7E-REALTICK-2024-20261125.md"
  - "T2/T3 (Cộng đồng VN 2026): Phí điện trung gian SWIFT ngân hàng VN, tính khả dụng Wise VN, phản ánh triển khai NinjaTrader/TopstepX"
---

# Bức tranh Quỹ Prop `2026` & Chiến lược Đa dạng Hóa Đa Quỹ cho Algo Trader Việt Nam

> **Kỷ luật Bằng chứng:** Phân tách rõ **`T1`** (tài liệu chính thức hãng `2026` & kiểm định nội bộ `< 2025-01-01`, `holdout_rows_analysed = 0`, `OrderSend = 0`) với **`T2/T3`** (kinh nghiệm rút tiền ngân hàng VN & vận hành cộng đồng). Mục tiêu: thiết kế **kiềng 3 chân đối tác `2026–2027`** cho `PORT_7E` (`Sharpe ~1,2–1,5`, `MaxDD ~4%–6,5%`, `swap = 0`), không bao giờ đặt `100%` rủi ro đối tác vào một hãng duy nhất.

## Bảng Xếp hạng & Phán quyết Đa Quỹ `2026–2027`

| Hạng | Hãng / Mô hình | Phán quyết | Thời điểm & Điều kiện Mở | Vai trò trong Danh mục Naqex | Lý do Cốt lõi |
|---:|---|---|---|---|---|
| **#1** | **FTMO CFD `2-Step`** (`Standard`/`Swing`) | **`GO_PRIMARY`** | **Hiện tại (`Q4/2026`)** sau cổng Mũi 1–2 & Astra | **Động cơ in tiền mặt chính** (`80%->90%`, trần `400K->2M USD`) | Native MT5 EA, Static DD `10%`, hoàn phí `100%`, **`0%` phí rút** (`SWIFT 0,8%–2,5%` all-in) |
| **#2** | **Darwinex Zero** (`FCA/CNMV` ecosystem) | **`GO_FIRM_2_POST_PAYOUT1`** | **Tháng `4–6`** (chỉ trả phí `35–45 EUR/tháng` bằng **lãi FTMO**) | **Đối tác pháp lý thực + Track record vĩnh viễn** (`0` cháy DD) | Hệ sinh thái quản lý tài sản FCA/CNMV, native MT5 EA, **`0%` phí rút SWIFT**, `0` luật tin đỏ, VaR Engine nâng `7E` lên `~14%–18%/năm` |
| **#3** | **The5ers `High Stakes`** (`2-Step` CFD) | **`SECONDARY_RESERVE`** | **Tháng `6–9`** sau `>= 2` payout FTMO + **email duyệt EA §11** | **Bổ sung dòng tiền CFD vé siêu rẻ** (`39 USD` gói `5K`) | Static DD `10%`, native MT5 EA, `EV/phí` gộp cao, **nhưng bị trừ điểm mạnh vì phí rút `3,5%` + Rise (`5,0%–8,0%` all-in VN)** & `30%` hoàn bằng Hub Credit |
| **#4** | **Futures Props** (`FTMO Futures`, `Topstep`, `Tradeify`) | **`DEFER_TO_2027`** *(và **`KILL`** cho porting `7E` FX)* | **Chỉ mở `H2/2027+`** khi có đủ `5–6` engine thuần `MNQ/MES/MGC/MCL` | **Nhánh CME minh bạch sau này** *(bỏ qua Cyber Monday `30/11`)* | Phí FX Micro (`M6J 47 USD/lot`) giết sạch `7E`; không có MT5 (phải viết lại NinjaScript); **Topstep cấm VPS & cấm bot API trên Live Funded!** |

---

## 1. Thẩm định Chuyên sâu Darwinex Zero (`2026`) — Có Hợp với `PORT_7E`?

### 1.1. Cơ chế, Phí `2026`, Quy định Pháp lý & Rút tiền Việt Nam (`T1`)
Khác hoàn toàn prop firm CFD truyền thống, **Darwinex Zero** ([darwinexzero.com](https://www.darwinexzero.com)) là nền tảng thuê bao xây dựng lịch sử giao dịch ảo tạo thành chỉ số **DARWIN** đầu tư được, vận hành bởi *Tradeslide Trading Tech Ltd* gắn với hệ sinh thái quản lý tài sản được cấp phép **FCA Anh (`FRN 586466`) / CNMV châu Âu** ([darwinex.com](https://www.darwinex.com)):
- **Bảng giá cập nhật `2025–2026` (`T1`):** Gói CFD/FX trả tháng **`45 EUR/tháng`** (`540 EUR/năm`, khoảng `50 USD/tháng`; trước đây từng là `38 EUR`), gói **`1` năm trả trước `420 EUR` (`35 EUR/tháng`)**, gói `3` năm `1.080 EUR` (`30 EUR/tháng`). **Không phí thi lại nhiều vòng**, hủy bất kỳ lúc nào.
- **Việt Nam & MT5 EA (`T1`):** Chấp nhận trader Việt Nam hoàn tất KYC cá nhân; **hỗ trợ MT5 & EA tự động `100%`** — `Naqex_Master_Prop7E.ex5` chạy trực tiếp không cần sửa ngôn ngữ. **Không có trần lỗ ngày `5%`, không cháy tài khoản ở `-10%` Static DD, không cấm tin đỏ `±2m`, không yêu cầu ngày tối thiểu.**
- **Kênh rút tiền VN (`T1` + `T2/T3`):** Darwinex **thu `0%` phí rút qua chuyển khoản ngân hàng SWIFT** về tài khoản chính chủ khớp KYC (cần sao kê ngân hàng xác minh). Phí ngân hàng trung gian/VN khoảng `~25 USD/lần` (`2,5%` ở mốc `1.000 USD`, chỉ **`0,83%`** ở mốc `3.000 USD`). *(Lưu ý `[#234]`: Wise cá nhân VN không mở đủ TK nhận USD/EUR, nên dùng thẳng **SWIFT USD về ngân hàng VN**.)*

### 1.2. Toán học Khớp `PORT_7E` với Risk Engine VaR & Điểm Hòa vốn Thuê bao
- **Lợi thế chuẩn hóa VaR (`T1`):** Darwinex Risk Engine tự co giãn vị thế mọi chiến lược về dải **VaR tháng `95%` = `3,25%–6,50%`** (`6,5%` mVaR tương đương độ biến động năm **`~13,69%`**). Trên sổ `2024` nội bộ (`< 2025-01-01`), `PORT_7E` (`1,0x`) có lãi `+7,55%`, độ biến động năm chỉ `5,66%`, `Sharpe 1,31` → Risk Engine tự khuếch đại **`~2,0×–2,4×`** thành DARWIN có lợi suất kỳ vọng **`~14%–18%/năm`** mà **không bị rủi ro cháy tài khoản**!
- **Cơ chế phân bổ vốn `DarwinIA` (`T1`):** Sau giai đoạn hiệu chuẩn (`~10–15` ngày giao dịch / `25` quyết định rủi ro), DARWIN vào **DarwinIA SILVER**. Cuối mỗi tháng, đạt **Rating `>= 75`** (tính `67%` lãi tích lũy `6` tháng + `22%` lãi tháng hiện tại + `11%` MaxDD `6` tháng) được **cam kết tối thiểu `30.000 EUR` (tới `375.000 EUR`) trong `3` tháng liên tiếp** và **cộng dồn qua các tháng**. Đủ thâm niên `> 8` tháng và tỷ lệ Lãi/DD tốt sẽ lên **DarwinIA GOLD** (cấp vốn `6` tháng tới `500.000 EUR`) + gọi vốn **nhà đầu tư thực không giới hạn**. Trader hưởng **`15%` phí hiệu suất** (theo *High-Water Mark*, trả theo quý).

| Lợi suất DARWIN kỳ vọng (`PORT_7E` chuẩn hóa VaR `6,5%`) | **Vốn phân bổ hòa vốn** (Gói `45 EUR/th` · `540 EUR/năm`) | **Vốn phân bổ hòa vốn** (Gói năm `420 EUR/năm`) | Lãi ròng sau phí ở **`60K EUR`** *(2 tháng Silver tối thiểu)* | Lãi ròng ở **`90K EUR`** *(3 tháng Silver tối thiểu)* | Lãi ròng ở **`200K–350K EUR`** *(Silver+Gold/Investor)* |
|---:|---:|---:|---:|---:|---:|
| **`+10%/năm`** *(thận trọng)* | `36.000 EUR` | `28.000 EUR` | `+360 EUR/năm` | `+810 EUR/năm` | `+2.460 .. +4.710 EUR/năm` |
| **`+14%/năm`** *(kỳ vọng gốc)* | **`25.714 EUR`** | **`20.000 EUR`** | **`+720 EUR/năm`** | **`+1.350 EUR/năm`** | **`+3.660 .. +6.810 EUR/năm`** |
| **`+18%/năm`** *(thuận lợi)* | `20.000 EUR` | `15.556 EUR` | `+1.080 EUR/năm` | `+1.890 EUR/năm` | `+4.860 .. +8.910 EUR/năm` |

**Đánh giá trung thực (Ưu & Nhược):** Điểm hòa vốn chỉ **`~20K–26K EUR`** (thấp hơn cả `1` suất Silver tối thiểu `30K EUR`!). Tuy nhiên, **nhược điểm lớn là tốc độ ra tiền chậm (`6–9` tháng nuôi tài khoản ≈ `270–405 EUR` chi phí chìm ban đầu)** do cần `6` tháng lịch sử cho trọng số `67%` của Rating `75` và trả thưởng theo quý; ngoài ra mức chia `15%` đòi hỏi `~300K EUR` AUM mới sánh ngang dòng tiền của FTMO `100K`. **Kết luận:** Tuyệt đối **không đốt tiền túi ban đầu** — kích hoạt Darwinex Zero làm **Hãng #2 ngay sau khi có Payout #1–#2 từ FTMO**, dùng lãi FTMO nuôi thuê bao để đổi lấy **bảo hiểm đối tác chuẩn FCA/CNMV và lịch sử kiểm toán trọn đời**.

---

## 2. Thẩm định FTMO Futures (`Cyber Monday 2026`) & Topstep / Tradeify

### 2.1. Thực tế `FTMO Futures` (Ra mắt cuối `2026`, Sale `23/11–02/12/2026`) (`T1`)
FTMO đã mở nhánh **FTMO Futures** ([ftmo.com](https://ftmo.com)) với 2 gói `Growth` & `Pro` (`50K / 100K / 150K USD`), `1` vòng thi, **EOD Trailing Drawdown** (khóa ở số dư gốc khi tạo đệm), **`0 USD` phí kích hoạt**, chia **`90/10`**, nhận khách Việt Nam. Tuy nhiên, có **4 lý do bác bỏ việc mở ngay tuần Cyber Monday**:
1. **Không đa dạng hóa rủi ro đối tác:** Vẫn thuộc cùng pháp nhân/hệ sinh thái FTMO — nếu FTMO đổi chính sách hay siết rủi ro vùng, cả hai nhánh chịu ảnh hưởng cùng lúc.
2. **KHÔNG hỗ trợ MT5:** Chạy qua **Tradovate / NinjaTrader / TradingView** → phải viết lại toàn bộ code MQL5 sang NinjaScript hoặc cầu nối webhook (phát sinh rủi ro lỗi kỹ thuật & phí dữ liệu/API Tradovate).
3. **Phí thuê bao tháng cao giống bẫy Tradeify (`T1`):** Gói `50K Growth = 119 USD/tháng` (`Pro = 139 USD/tháng`; `100K = 169–199 USD/tháng`, giảm `10%–30%` tháng đầu dịp Cyber Monday) kèm luật **Consistency `40%–50%`** vòng thi (bỏ khi Funded). Như đã chứng minh trong [LAB5-CME-FUTURES-PROP-STUDY-20261124.md](../../planning/research/LAB5-CME-FUTURES-PROP-STUDY-20261124.md), bot định lượng kỷ luật cần `3–6` tháng để vượt vòng an toàn sẽ bị thuê bao `119–139 USD/tháng` ăn mòn mạnh EV.
4. **Cấu trúc phí CME Micro FX giết chết `70%` danh mục `PORT_7E` (`T1` Lab #5):** Ánh xạ `PORT_7E` sang `M6J/M6B` khiến phí lên tới **`39,8–47 USD/lot`** (`9,81%` biên độ ngày trên `M6J`), kéo `EV/USD phí` rơi sâu xuống **`-0,29× .. -0,86×`**. Chỉ riêng `MNQ + MGC` (`E4/E5/S7`) rẻ hơn CFD (`-77%` phí `MNQ`), nhưng `3` động cơ không đủ đánh bại FTMO CFD.

### 2.2. Cờ đỏ Nghiêm trọng trên `Topstep` & Đánh giá `Tradeify` (`2026`, `T1`)
- **Topstep (`49 USD/tháng` + `149 USD` kích hoạt, [help.topstep.com](https://help.topstep.com)):** Tuy chi phí thuê bao rẻ nhất trong nhóm Futures và đạt cận trên `+5,43×..+7,78×` trong Lab #5 (nếu có đủ `5–6` engine thuần `MNQ/MES/MGC/MCL`), cuộc kiểm tra tài liệu `2026` phát hiện **2 rào cản chết người cho algo trader**: (a) **CẤM tuyệt đối chạy bot/gửi lệnh qua VPS, VPN hay máy chủ từ xa** (mọi lệnh phải xuất phát từ máy cá nhân tại nhà); (b) **CẤM giao dịch tự động qua `TopstepX / ProjectX API` khi lên tài khoản tiền thật (`Live Funded Account — LFA`)!** Nghĩa là dù bot vượt Combine + XFA, bạn vẫn bị tước quyền chạy tự động ở chặng lớn nhất. Cộng thêm phí rút SWIFT `30 USD` của Topstep (`5,5%` ở `1K USD`, `1,83%` ở `3K USD`; Wise cho VN không ổn định).
- **Tradeify (`139 USD/tháng`, `0 USD` kích hoạt, `90/10`, [tradeify.co](https://tradeify.co)):** Cho phép tự động hóa qua NinjaTrader / Tradovate / TradingView, EOD Trailing DD, gói `Select` bỏ luật Consistency khi Funded, hỗ trợ VN qua **Rise / Plane** (`USDC` / Wire). Tuy vậy, phí thuê bao `139 USD/tháng` vẫn khiến nhánh `MNQ+MGC` chỉ đạt `+0,17×` EV/phí (`OOP95 = 3.197 USD`).

**Phán quyết mục 2 (Futures Props):** **`DEFER_TO_2027`** cho toàn bộ nhóm Futures (`FTMO Futures`, `Tradeify`, `Topstep`) và **`KILL`** ý định chuyển `PORT_7E` FX sang CME. Chỉ mở lại vào **`H2/2027`** sau khi xây đủ `5–6` engine thuần **`MNQ / MES / MGC / MCL`**, viết xong bản **NinjaScript** kiểm thử đầy đủ — khi đó ưu tiên đối chiếu **`Tradeify Select`** (không cấm bot ở Funded) hoặc **`FTMO Futures`** (nếu không cần tách đối tác FTMO) hơn là `Topstep` (trừ khi Topstep gỡ lệnh cấm API trên LFA).

---

## 3. Ma trận Đối đầu `2026–2027` cho Algo Trader Solo tại Việt Nam

| Tiêu chí sống còn (`T1` + `[#234]`) | **#1 FTMO CFD (`2-Step`)** | **#2 Darwinex Zero** | **#3 The5ers (`High Stakes`)** | **#4 Futures (`FTMO Fut` / `Topstep` / `Tradeify`)** |
|---|---|---|---|---|
| **Hợp pháp EA MT5 (`PORT_7E`)** | **Đạt `100%`** (tự viết, `< 2.000` req/ngày; cấm IP Mỹ/CGNAT) | **Đạt `100%`** (native MT5 EA, không cần nộp mã) | **Đạt có điều kiện** (sở hữu `100%` mã, **xin email §11**) | **KHÔNG có MT5** (phải viết lại NinjaScript/API; **Topstep cấm VPS & cấm API ở LFA**) |
| **Cấu trúc phí đầu vào** | `1` lần (`~168–600 USD`), **hoàn `100%` tiền mặt** ở payout #1 | Thuê bao **`45 EUR/th`** (gói năm **`35 EUR/th`**), không phí thi | `1` lần siêu rẻ (**`39 USD`** gói `5K`), hoàn `70%` tiền + `30%` Hub Credit | Thuê bao tháng **`49–139 USD/th`** (`Topstep +149 USD` kích hoạt) |
| **Tổng phí rút tiền về VN** *(ở `1.000 / 3.000 USD`)* | **Rẻ nhất:** `0%` phí hãng · **SWIFT `2,50% / 0,83%`** · Crypto `~0,30% / 0,17%` | **Rẻ ngang FTMO:** `0%` phí hãng · **SWIFT `2,50% / 0,83%`** | **Đắt nhất:** `3,5%` phí hãng + Rise (**USDC `3,60% / 3,53%`**, **VND `5,95% / 5,28%`**, **SWIFT `8,0% / 5,0%`**) | `FTMO Fut`: như FTMO · `Topstep SWIFT`: **`5,50% / 1,83%`** · `Tradeify` (Rise): phí Rise `1–25 USD` + FX |
| **Độ tin cậy đối tác & Pháp lý** | **Rất cao** (đầu ngành CFD prop, mô phỏng nội bộ, trụ sở Séc) | **Cao nhất** (gắn hệ sinh thái **FCA UK / CNMV EU**, tách biệt CFD prop) | **Cao** (uy tín lâu năm Israel/UK, mô phỏng CFD prop) | Cao (`CME` minh bạch), nhưng `FTMO Fut` **trùng đối tác FTMO** |
| **Độ tương thích DD & Luật với `7E`** | **Rất cao:** Static `10%`, Daily `5%`; `Standard Funded` khóa tin `±2m` (đã khóa `±5m`) | **Hoàn hảo:** **0% cháy DD**, **0% cấm tin**, VaR tự chuẩn hóa `~14%–18%/năm` | **Khá:** Static `10%`, `>= 3` ngày `+0,5%`, tin đỏ `±2m` **trừ lãi giữ lỗ**, reset `14d` khi scale | **Thấp cho `7E`:** EOD Trailing chặt (`1,5×` Target/DD) + **phí FX Micro giết `7E`** |
| **Tốc độ ra tiền & Vai trò** | **Nhanh (`3–6` tháng):** Máy in tiền mặt chủ lực | **Chậm (`6–12` tháng):** Khiên đối tác FCA + tài sản AUM dài hạn | **Trung bình:** Đệm đa dạng hóa CFD vốn nhỏ sau FTMO | **Hoãn `H2/2027`:** Mở sau khi có bộ `5–6` engine thuần `MNQ/MES/MGC/MCL` |

### Lộ trình Triển khai Thứ tự `1 -> 2 -> 3` (`2026–2027`, Gắn Cổng Bằng chứng)
1. **Chặng 1 (`Q4/2026 – Q1/2027` — Chỉ 1 mặt trận):** Vượt cổng Mũi 1–2 & Astra → triển khai **Firm #1 `FTMO 2-Step`** (`10K` rồi nâng `25K–100K` bằng tiền lãi theo [capital-scaling-prop-to-own-book.md](capital-scaling-prop-to-own-book.md), giữ `naqex-node1` `0 USD` dưới `50K` theo [ownbook-merger-arb-and-vps-scaling-2026.md](ownbook-merger-arb-and-vps-scaling-2026.md)).
2. **Chặng 2 (`Tháng 4–6/2027` — Tách rủi ro đối tác ngay khi FTMO có Payout #1–#2):** Trích `45 EUR/tháng` (hoặc gói năm `420 EUR`) **từ lãi FTMO** để kích hoạt **Firm #2 `Darwinex Zero`** gắn thẳng `Naqex_Master_Prop7E.ex5` → khởi chạy đồng hồ tích lũy lịch sử `6–12` tháng chuẩn **FCA/CNMV** song song với việc nhân vốn FTMO.
3. **Chặng 3 (`Tháng 6–9/2027` — Sau `>= 2` Payout tiền mặt FTMO + Email duyệt EA §11):** Bổ sung **Firm #3 `The5ers High Stakes`** (`5K–20K`, rút dồn lô lớn `>= 1.500–3.000 USD` qua kênh rẻ nhất để nén tầng phí `3,5%` + Rise). Toàn bộ nhánh **Futures (`Tradeify` / `FTMO Futures`)** giữ đóng băng tới **`H2/2027`** khi hoàn thiện đủ bộ động cơ thuần `MNQ/MES/MGC/MCL`.
