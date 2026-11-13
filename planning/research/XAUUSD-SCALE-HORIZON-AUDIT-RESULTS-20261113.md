# XAUUSD B0 — chẩn đoán quy mô và thời gian giữ

**Khuyến nghị No-Go cho quyền thử XAUUSD B1 trong chiến dịch hiện tại.** Chỉ kéo hạn giữ tới 18:00 chưa cứu được 37 lệnh đã nhận và không tăng số cơ hội qua phí. Chưa đủ cơ sở cho một B1 đồng thời sửa được cả tần suất và kỳ vọng. Đây là đề xuất cho owner, chưa ghi nhận owner đã hủy B1.

Một kết luận cần giữ đúng mức: **chưa chứng minh toàn bộ tín hiệu H1 → M15 không có lợi thế định hướng**. Toàn bộ raw signals có markout sau phí stress đến 18:00 hơi dương, nhưng khoảng bất định còn bao gồm số âm và hai năm khác nhau. Bằng chứng bác cách triển khai B0 hiện tại mạnh hơn bằng chứng bác mọi phiên bản có thể nghĩ ra.

PR #73 đã merge vào main tại `f1fa995`; nhánh `codex/xauusd-intraday-b0` đã xóa local/remote. B0 giữ `ECONOMIC_FAIL` + `CADENCE_OR_SAMPLE_SHORTFALL`, prop vẫn `PROP_UNMEASURED`. Chỉ giá Development 2022–2023 dùng trong diagnostic; không dùng 2024 để thiết kế, không mở 2025–2026, không chạy B1/account/broker. [Protocol đóng trước outcome](XAUUSD-SCALE-HORIZON-AUDIT-PROTOCOL-20261113.md); [B0 gốc](XAUUSD-INTRADAY-B0-RESULTS-20261113.md) giữ nguyên số liệu.

## 1. Định nghĩa và cohort

- 813 tín hiệu thô trên 360 ngày có tín hiệu; 772 bị loại phí, tức 94,96%. Có 38 qua phí, 37 vào lệnh; một tín hiệu bị chặn vì đang giữ vị thế, ba SL không hợp lệ.
- Trong 37 fills, chỉ **14 lệnh** có SL từ 6,5 đến 8 USD/oz: 11 lệnh năm 2022 và 3 lệnh năm 2023. Cỡ mẫu này không đủ chứng minh một quy luật phổ quát.
- Quan sát đúng ba mốc đã khóa: 2 giờ, 18:00 và 20:30 UTC. Mốc 20:30 chỉ là cửa sổ diagnostic owner yêu cầu, chưa chứng nhận là giờ nghỉ/safe cutoff của đúng CFD/CME/account.
- Markout đo giá cuối cửa sổ, không áp SL/TP. First passage đo biên nào chạm trước khi còn giữ SL/TP bảo vệ. Hai metric trả lời hai câu hỏi khác nhau. Tín hiệu chồng lấn không phải các khoản PnL có thể cộng vào một tài khoản.

## 2. Ma sát mỗi vòng lệnh

Các số dưới là trung vị trên **37 lệnh thực vào**, USD/oz. Spread cả vòng đo theo benchmark mid: nửa spread entry cộng nửa spread exit. Commission lấy số tiền hai leg đã ghi sổ, chia số ounces. Slippage là giả định stress, chưa phải mức trượt giá broker đã đo.

| Năm | Lệnh | Spread | Commission | Slippage chuẩn/stress | Tổng chuẩn | Tổng stress | Tỷ trọng slip stress¹ |
|---|---|---|---|---|---|---|---|
| 2022 | 24 | 0,3257 | 0,0259 | 0 / 0,4000 | 0,3523 | 0,7523 | 53,17% |
| 2023 | 13 | 0,3185 | 0,0276 | 0 / 0,4000 | 0,3442 | 0,7442 | 53,75% |
| development | 37 | 0,3225 | 0,0264 | 0 / 0,4000 | 0,3486 | 0,7486 | 53,43% |

¹ Trung vị của tỷ số trên từng lệnh. Median tổng không nhất thiết bằng tổng median các thành phần. Theo tổng USD của cohort: spread benchmark 226,0435 USD + commission 18,33 USD + slippage stress 279,60 USD; slippage chiếm **53,36%** tổng ma sát stress. Không chia cho khoản net loss.

Commission 0,0007% notional/side = 0,000007 × giá mỗi oz mỗi chiều, đúng contract B0; không nhầm thành 0,0007 dạng thập phân. Biểu phí là giả định đã duyệt. Nguồn FTMO từng kiểm ở PR #73; lượt này URL cũ trả 404, chưa xác minh lại điều khoản tài khoản hiện hành và không đổi mô hình phí. Slippage 0,40 USD/oz chiếm khoảng 53,43% tổng ma sát trung vị; tỷ trọng lớn chưa chứng minh stress thiếu thực tế hoặc cho phép hạ phí để cứu B0.

Cổng admission dùng spread tại entry, trung vị 0,324 USD/oz trên fills; benchmark mid cả vòng có trung vị 0,3225 nhưng là đại lượng khác. Tách thêm 3,299 USD do TP limit không nhận giá cải thiện: khoản này thuộc cách fill bảo thủ, không gộp vào spread hoặc commission. Phép tính biến động mid theo hướng lệnh − spread − phần TP không nhận giá cải thiện khớp gross Bid/Ask đến cent trên đủ 37 lệnh.

Về cách gọi pip: nên dùng USD/oz để tránh nhầm. 0,40 USD/oz là 40 đơn vị 0,01; trong InstrumentSpec khai báo của B0, pip_size = 0,1 nên tương đương 4 pip. Cách gọi pip/point theo nền tảng không đổi khoản phí 0,40 USD/oz.

## 3. SL ngắn xuất phát từ đâu?

BUY: `SL = low nến M15 xác nhận − 0,10 × ATR14 M15 trước nến`; SELL đối xứng với high. SMA20 là vùng tạo tín hiệu, **không phải mốc SL**. ATR của đệm lấy M15, chưa lấy ATR H1. H1 chỉ quyết định hướng. Vì vậy SL chủ yếu là khoảng từ giá vào tới extreme của **một nến M15**, cộng đệm nhỏ.

| Nhóm | N | SL | Close→extreme | Entry drift² | Đệm ATR | ATR M15 | Range nến / ATR | Sàn phí xấp xỉ |
|---|---|---|---|---|---|---|---|---|
| raw | 813 | 1,958 | 1,560 | 0,066 | 0,225 | 2,253 | 1,166 | 5,935 |
| friction_rejected | 772 | 1,881 | 1,492 | 0,064 | 0,223 | 2,227 | 1,138 | 5,940 |
| cost_pass | 38 | 7,040 | 6,484 | 0,251 | 0,331 | 3,305 | 2,258 | 5,844 |
| fills | 37 | 7,020 | 6,462 | 0,224 | 0,326 | 3,256 | 2,271 | 5,832 |

² Khoảng giá entry so với close nến setup, có thể chứa spread ở BUY. Mỗi SL được đối soát chính xác bằng tổng khoảng close tới extreme + lệch giá entry + đệm ATR + làm tròn ra ngoài. Không cộng các trung vị để giả một lệnh điển hình. Đệm trung vị chỉ 0,223 USD/oz ở nhóm bị loại, không thể tự biến stop 1,88 USD thành 7 USD.

**Có chọn lọc quy mô lớn:** nhóm bị loại có range nến trung vị 1,14 ATR, nhóm fills 2,27 ATR. Nhưng chưa thể suy ra “đã chạy hết đà” chỉ từ kích thước nến. Markout ở phần 5 mới kiểm phần định hướng.

**Hiệu chỉnh sàn phí:** 6,7–8,0USD là median SL của fills theo từng năm, không phải một ngưỡng chung. Nếu bỏ qua lot floor/cent reserve, đặt `s=entry spread`, `c=commission reserve + stress slip` trên mỗi oz, size xấp xỉ `R0/(d+c)`, thì `F/R0≈(s+c)/(d+c)≤0,12` đòi `d≥(s+0,88c)/0,12`. Sàn liên tục trung vị của raw signals khoảng **5,93 USD/oz**, thay đổi theo từng intent; native lot floor và reserve mới là quyết định thực. Không dùng phép tính này để nới SL nhân tạo.

## 4. First-passage time của nhóm SL 6,5–8 USD/oz

Bảng chính giữ nguyên SL/TP tự nhiên của 14 lệnh. “Chưa chạm” khác “thiếu đường giá”. Trung vị thời gian tính trên những lệnh đã chạm **một trong hai biên**, đa số là SL; không phải thời gian chờ để được TP. Các biên −1R/+2R ở đây là khoảng cách giá, khác ngân sách R0 = 150 USD có dự phòng phí.

| Cutoff | N | TP trước | SL trước | Chưa chạm, path đủ | Path thiếu | Median giờ: đã chạm | Median toàn nhóm |
|---|---|---|---|---|---|---|---|
| 2h | 14 | 0 | 4 | 10 | 0 | 0,796 | chưa xác định |
| 1800 | 14 | 1 | 6 | 7 | 0 | 0,990 | chưa xác định |
| 2030 | 14 | 1 | 7 | 5 | 1 | 1,516 | chưa xác định |

Đến 18:00: chỉ 1 TP và 6 SL; 7 lệnh còn chưa chạm biên. Lệnh TP duy nhất cần **3,028 giờ**; trung vị của 7 lệnh đã chạm là 0,990 giờ do 6 lệnh SL chi phối. Trung vị toàn bộ 14 lệnh chưa xác định; khoảng nhận dạng chỉ cho biết ít nhất 2,889 giờ, chưa có cận trên hữu hạn trong cửa sổ này. Không lấy 0,990 giờ rồi kết luận 2 giờ là đủ.

Đến 20:30 có 1 TP, 7 SL, 5 chưa chạm trên đường giá đủ và 1 đường giá thiếu; trung vị trên nhóm đã chạm là 1,516 giờ. Khoảng nhận dạng trung vị toàn cohort khoảng 2,793–4,372 giờ, chưa có một ước lượng điểm duy nhất. Gap 64,164 giây tại 2022-10-28 được giữ nguyên.

Benchmark cố định −7,5/+15 USD/oz trên **cùng 14 điểm vào** cho cùng số TP/SL/chưa chạm ở các cutoff; TP duy nhất mất 3,020 giờ tới 18:00. Đây là kiểm mốc quãng giá được yêu cầu, không chạy một chiến lược stop cố định mới hoặc sizing lại.

Cách xử lý trường hợp chưa chạm là [right censoring theo NIST](https://www.itl.nist.gov/div898/handbook/apr/section1/apr131.htm). Không giả chúng đã chạm tại cutoff; không ép Kaplan–Meier vì giờ vào quyết định thời gian còn lại trong phiên, giả định censoring độc lập chưa được kiểm.

## 5. Giữ đến cuối phiên có cứu cơ chế không?

**Cùng 37 fills, cùng khối lượng và SL/TP bảo vệ:** bảng dưới chỉ cộng diagnostic theo từng lệnh, chưa replay account; có thể chồng lấn và không chứng nhận tần suất hoặc portfolio của B1.

| Năm | Cutoff | Path đủ/N | NetUSD chuẩn | NetUSD stress | Phạm vi |
|---|---|---|---|---|---|
| 2022 | 2h | 24/24 | 347,33 | 156,13 | đủ observed path |
| 2022 | 1800 | 24/24 | 179,81 | -11,39 | đủ observed path |
| 2022 | 2030 | 23/24 | 21,05 | -162,15 | partial |
| 2023 | 2h | 13/13 | -337,53 | -425,93 | đủ observed path |
| 2023 | 1800 | 13/13 | -112,07 | -200,47 | đủ observed path |
| 2023 | 2030 | 12/13 | -69,22 | -151,22 | partial |
| development | 2h | 37/37 | 9,80 | -269,80 | đủ observed path |
| development | 1800 | 37/37 | 67,74 | -211,86 | đủ observed path |
| development | 2030 | 35/37 | -48,17 | -313,37 | partial |

Kéo từ 2 giờ tới 18:00 cải thiện tổng stress từ −269,80 lên −211,86 USD, nhưng **cả hai năm vẫn âm**, số lệnh không tự tăng. Với 37 fills, TP tăng 2→3, SL tăng 11→13, chưa chạm 24→21. Đến 20:30 có 2 khoảng trống trên path: 2022-10-28 (64,164 giây), 2023-10-02 (121,764 giây). Tổng của 35 path chỉ là phần đã đo được, không so như kết quả đầy đủ 37 lệnh.

**Kiểm định hướng trên toàn bộ tín hiệu thô:** giá thanh lý đúng Bid/Ask ở cuối cửa sổ, bỏ SL/TP chỉ để đo markout, không coi là bot bỏ SL. Net tính trên một oz, commission chưa làm tròn theo lot, trừ thêm0,40 USD/oz stress. Không phải Mean Net R hoặc portfolio return.

| Năm | Cutoff | Có quote/N | Mean gross USD/oz | Mean net chuẩn | Mean net stress | Bootstrap95% stress³ |
|---|---|---|---|---|---|---|
| 2022 | 2h | 399/399 | -0,129 | -0,154 | -0,554 | -1,540 → 0,345 |
| 2022 | 1800 | 399/399 | 0,202 | 0,177 | -0,223 | -1,636 → 1,197 |
| 2022 | 2030 | 381/399 | 0,299 | 0,274 | -0,126 | -2,099 → 1,704 |
| 2023 | 2h | 413/414 | -0,450 | -0,478 | -0,878 | -1,738 → -0,048 |
| 2023 | 1800 | 410/414 | 1,364 | 1,337 | 0,937 | -1,090 → 2,885 |
| 2023 | 2030 | 399/414 | 1,816 | 1,789 | 1,389 | -0,773 → 3,609 |
| development | 2h | 812/813 | -0,293 | -0,319 | -0,719 | -1,367 → -0,063 |
| development | 1800 | 809/813 | 0,791 | 0,765 | 0,365 | -0,845 → 1,731 |
| development | 2030 | 780/813 | 1,075 | 1,049 | 0,649 | -0,893 → 2,083 |

³ Cụm theo ngày,2.000 lần,seed20261113. Chỉ xử lý phụ thuộc trong ngày; chưa hiệu chỉnh nhiều lần thử, phụ thuộc liên ngày hoặc chứng nhận edge tương lai. Bốn markout thiếu tại18:00 thuộc2023-11-24;20:30 thiếu33/813. Không loại ngày sau khi nhìn outcome rồi gọi là kết quả đủ mẫu.

Tín hiệu thô đến 18:00 có mean net stress **+0,365 USD/oz**, nhưng CI [−0,845; +1,731], năm 2022 âm và 2023 dương. Có dấu hiệu đáng ghi nhận về horizon dài hơn, **chưa đủ xác nhận edge**. Nhóm bị loại phí có markout 18:00 +0,553 USD/oz, trong khi fills có −2,518 USD/oz nếu chỉ giữ đến cutoff mà không SL/TP. Đây là khác biệt giữa các nhóm đã bị chọn, hỗ trợ lo ngại chọn lọc ngược; chưa chứng minh nguyên nhân hết đà hoặc một filter mới có thể giao dịch lời. Mean markout cũng chưa được so với benchmark/control để chứng minh excess alpha.

## 6. Phán quyết B1 và hồ sơ B0

- **Giữ B0 gác:** `ECONOMIC_FAIL` + `CADENCE_OR_SAMPLE_SHORTFALL`. Ghi nguyên nhân cơ học: stop tự nhiên M15 khoảng2USD/oz, sàn phí stress xấp xỉ6USD/oz, fills khoảng7 USD/oz, TP khoảng14USD/oz trong2 giờ. Đây là bất tương thích đã đo; chưa chứng minh là nguyên nhân duy nhất gây lỗ.
- **Đề xuất No-Go/hủy lượt B1 trên nhánh M15 này trong chiến dịch:** thay một exit sang18:00 vẫn âm và không sửa cadence. Chuyển sang stop ATR H1 đồng thời đổi horizon là nhiều thay đổi chưa được đo, không được quảng bá như một bản vá đã có edge. Chưa chạy hoặc ghi owner đã hủy B1.
- **Không kết luận thị trường/signal hoàn toàn vô ích:** markout raw đến 18:00 hơi dương nhưng còn yếu/không đều. Nếu sau này mở lại cần hypothesis mới và bằng chứng tiền nghiệm cụ thể; không tự tìm thêm cutoff/ATR/side để cứu bản hiện tại.
- Không tự hạ slippage, tăng risk, bỏ SELL, đọc2024 để tune hoặc mở2025–2026. Chưa có bằng chứng calibration broker đủ để chọn một mức slip nhẹ hơn.

## 7. Đối soát, thời gian và tái hiện

9 fixtures trước run, 10 fixtures sau hardening: first-passage/censoring/missingquote/side/same-ms/stop decomposition/midspreadbridge đạt. Hai negative source guards xác nhận chặn giờ năm2024 và parenthash sai trước fetch. Chính xác **797 giờ mới + 1.514 giờ dùng lại**,2.311 giờ/23.829.464 ticks Development. Không dùng sourceM1price2024.

Self-audit bằng phép tính riêng đạt:813 entry-prefix và74 scenario-trade net khớp B0;2.401 markout đối chiếu Decimal,38 missing giữ nguyên;153 first-passage đối chiếu hai barrier độc lập theo chỉ số quote; ba nhóm median ma sát khớp. Đây là self-audit, không phải review độc lập của agent khác.

| Phase | Thời gian đo được |
|---|---|
| Download797 giờ mới, reuse1514 giờ | 301,30s |
| Chuẩn bị/kiểm tick | 24,14s |
| Tổng diagnostic gồm chuẩn bị | 39,55s |
| CPU diagnostic | 32,27s |
| Viết code/phân tích/review thủ công | chưa đo đủ; không suy từ CPU |

Private evidence: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\xauusd-scale-horizon-audit-20261113`. `registration.json` + `source-snapshot-v1` đóng băng trước outcome; `attempt-1/result.json`, `details.json`, `tick-view-seal.json`, `diagnostic-review.json`; reviewer `review-equations-v1.py`. [JSON dossier](XAUUSD-SCALE-HORIZON-AUDIT-RESULTS-20261113.json) giữ số liệu, hashes và giới hạn.

Tái hiện bằng source trong `source-snapshot-v1`: tạo bản config mới trỏ `workspace` tới snapshot này, giữ nguyên data/cohort pins và chọn output mới; chạy `python <snapshot>/tooling/ai-engines/xau_scale_horizon_audit.py --config <config-mới.json>`. Giữ registration gốc. Code xuất bản sau run chỉ thêm guard chặn Python `-O` và một regression test, không đổi phép tính; `postrun-hardening.json` ghi delta này. Không chạy đè attempt hoặc chuyển dữ liệu sang 2024. Hash protocol lúc census và protocol bổ sung bootstrap trong registration được giữ riêng; amendment trước mọi outcome mới, không đổi cohort hay giờ.

Hậu kiểm kỹ thuật: dùng lại decoder/provider và tick đã seal; thêm guard scope Development và output directory không ghi đè ở collector. Không cần thêm framework/skill: workflow hiện có đã yêu cầu tách data/cost/signal/horizon và giữ outcome âm; fixtures cụ thể giữ bài học censoring. Không claim speedup giữa hai workload khác nhau, không mở thêm batch tối ưu.
