# US500 M15 · Kiểm khả năng chuyển mô hình S-Sign từ SPY

**Gác trước khi xây runner.** Chưa xác minh được chuỗi dự báo hoặc bộ
trọng số đúng bản để chạy replay. Phí stress của US500 quanh các mốc M15
là **2,77 bp bình quân mỗi đơn vị thay đổi vị thế**. So sơ bộ với SPY,
khoản chênh phí đủ lớn để ăn hết lợi nhuận công bố nếu giữ nguyên tốc độ
đổi vị thế gần 20% mỗi M15 và mọi yếu tố khác. Lợi nhuận và độ nhạy trễ
của mô hình trên US500 vẫn chưa đo được. BASE_GUARD giữ NOT_QUALIFIED.

## Mô hình và kết quả gốc

Phạm vi duy nhất là (Cts, All)–Ensemble–S-Sign, phương trình (6). Mô hình
dự báo phần lợi suất liên tục của danh mục thị trường Fama–French trong
15 phút tiếp theo. Nó kết hợp chín mô hình có trọng số bằng nhau, dùng
816 đầu vào từ các mức trễ 15 phút, một giờ và một ngày của 272 danh mục.
Tín hiệu trên ngưỡng nửa spread trễ đặt vị thế +1, tín hiệu dưới ngưỡng âm
đặt −1, vùng giữa giữ trạng thái. Turnover là |w mới − w cũ|. Mở flat → +1
tính một phía, đảo +1 → −1 tính hai phía, giữ nguyên tính không phí giao dịch.
Ngưỡng của tác giả và chi phí thực khớp là hai đại lượng riêng.

Bảng 4 và OA.11 báo SPY nội phiên 2004–2020 đạt **19,889%/năm sau
phí**, Sharpe 1,367, alpha FF6 20,828%/năm. Tác giả dùng nửa quoted spread
theo NYSE TAQ tại mỗi lần đổi vị thế và giả định phí vay short 2%/năm.
Bảng 4 giữ +1 qua đêm, nên turnover lúc mở và chuyển sang vị thế qua đêm
phụ thuộc vị thế +1. Lợi suất qua đêm bị loại khỏi cột nội phiên. Phụ lục
OA.12, Panel A, thử flat qua đêm và cho return/Sharpe làm tròn giống
19,89%/1,37, alpha 19,98%. Đó vẫn là kinh tế SPY theo giả định của bài.
[Bài gốc, §3, §5 và Bảng 4](https://public.econ.duke.edu/~boller/Papers/MS_2025.pdf) ·
[Phụ lục OA.11–12](https://public.econ.duke.edu/~boller/Papers/HFML_Sup_App.pdf).

## Chi phí so trên cùng đơn vị

Một bp là 0,01% trên giá trị vị thế. Phép đo US500 dùng Open M1 Bid/Ask
của Dukascopy USA500.IDX/USD từ các phân vùng V11 năm 2018–2023. Chọn
mỗi Open M1 sau biên M15 nội phiên một phút, cộng Open phút cash cuối
để đại diện cửa sổ thanh lý. Lịch NYSE tính giờ New York, có DST và phiên
rút ngắn. Thiếu đúng phút cần đo để thiếu. Mỗi lần khớp tính
10.000 × (nửa spread + 0,75 điểm trượt) / giá giữa.

| Năm | Mốc định giá / lịch | Nửa spread trung vị, bp | Stress bình quân, bp | Stress trung vị, bp |
| --- | ---: | ---: | ---: | ---: |
| 2018 | 6.410 / 6.490 | 0,82 | 3,44 | 3,49 |
| 2019 | 6.454 / 6.516 | 0,45 | 3,18 | 3,08 |
| 2020 | 6.469 / 6.554 | 0,62 | 3,03 | 2,91 |
| 2021 | 6.532 / 6.540 | 0,54 | 2,26 | 2,23 |
| 2022 | 6.513 / 6.514 | 0,57 | 2,36 | 2,34 |
| 2023 | 6.469 / 6.476 | 0,59 | 2,35 | 2,34 |
| **Cả kỳ** | **38.847 / 39.090 (99,38%)** | **0,58** | **2,77** | **2,63** |

Khoảng phân vị 10–90 của stress là 2,14–3,58 bp/phía. Đảo chiều tại
mốc có phí trung vị tốn 5,26 bp cho 2 đơn vị thay đổi vị thế. Đối chứng
độc lập theo giờ vào/ra gần trọn phiên cho 3.004 quotes từ 1.502 cặp
giá, bình quân 2,79 bp/phía và trung vị 2,65 bp. Số mốc có giá đo ở đây
là độ phủ lịch báo giá. Chi phí theo tín hiệu cần gia quyền bằng turnover
thực tế tại đúng các mốc khớp. Đây là phí proxy gồm spread và giả định
trượt, chưa có dữ liệu fill hoặc biểu phí lịch sử tài khoản FTMO.
[Sổ cash-session](PROP-US500-CASH-SESSION-20261119.md).

**Phí hòa vốn chính xác chưa xác minh.** Cần gross return và tổng
|Δw| cùng sổ hoặc chuỗi vị thế, spread và borrow có timestamp. OA.11
cho tỷ lệ alpha sau/trước phí. Alpha là lợi suất đã điều chỉnh theo
nhân tố, nên dùng return sau phí làm phần còn dư cho phép tính sau.

- Hình 5 và §5.5 mô tả turnover khoảng 20% mỗi M15 trong phần lớn mẫu.
  Lấy 111.280 slot OOS / 17 năm × 20% thì ra khoảng 1.309 đơn vị
  turnover/năm. Với +1.988,9 bp/năm sau phí SPY, dư địa phí **bổ sung**
  ước tính là **1,52 bp/đơn vị**. Nếu turnover bình quân là 15% hoặc
  25%, con số tương ứng là 2,03 hoặc 1,22 bp. Đây là các giả định từ
  đồ thị, với cách tính vị thế qua đêm của bài gốc.
- Nửa spread SPY tham chiếu từ số bình quân không gia quyền của tác giả
  là 0,335 bp. Dùng số này minh họa và giữ các thành phần khác cố định,
  trần thay thế phần spread ước tính khoảng **1,85 bp** (1,52 + 0,335).
  Chênh lệch giữa proxy US500 stress bình quân và nửa spread tham chiếu
  là khoảng **2,43 bp**, cao hơn mức dư 1,52 bp. Nếu chỉ tính spread,
  US500 bình quân 0,60 bp. Bài gốc có thể giao dịch nhiều hơn ở mốc
  spread rộng. Phép tính chưa biết spread SPY gia quyền theo turnover,
  chênh phí vay, thay đổi vòng quay khi flat qua đêm, tracking khác SPY
  hoặc phần edge mất do trễ một phút. Vì vậy hai số trên dùng để lượng
  hóa mức ma sát cần kiểm lại, chưa đủ để phán quyết PnL.
  [Bài gốc §3.4, §5.5 và chú thích 14, 21](https://public.econ.duke.edu/~boller/Papers/MS_2025.pdf).

## Khả năng tái tạo và điều kiện mở lại

| Kiểm tra | Bằng chứng và phần còn thiếu |
| --- | --- |
| Có đầu vào nghiên cứu | Trang tác giả mô tả parquet lợi suất 1 phút của 272 danh mục, có lợi suất qua đêm điều chỉnh. Metadata Drive thực tế dẫn đến data/proc/factor_returns_1min/all/by_date. Đã thấy trang đầu chứa 50 tên parquet và thư mục docs chứa bảng mã factor. Các mục đã xem mô tả lợi suất và tài liệu. |
| Có forecast/trọng số đúng bản | Chưa xác minh được forecast, chuỗi w, model pack hoặc ngày phát hành theo phiên bản. INFORMS trỏ tới trang supplement, nhưng endpoint không trả danh mục tệp trong lần kiểm này (HTTP 403 khi truy cập trực tiếp). Phụ lục Duke đọc được, mô tả cách fit và bảng tổng hợp. |
| Có dữ liệu đúng thời điểm | Bài dùng features từ các lợi suất trễ. Với Cts, All, tách jump áp dụng cho nhãn thị trường, còn feature lấy lợi suất toàn phần. Phụ lục A.1 ghi EWMA dùng dữ liệu trước mốc xét jump và OA.3.2 ghi scaler chỉ học trên train. Chưa kiểm được thời điểm chốt thành phần danh mục từng ngày, timestamp công bố, quy tắc điều chỉnh overnight, dữ liệu sửa lại hoặc độ trễ cấp đầu vào trong ngày thực. |
| Có kỳ độc lập và nguồn vận hành | 2018–2020 trùng giai đoạn kết quả đã công bố. Chưa xác minh có forecast đúng model cho 2021–2023 hoặc nguồn cập nhật đủ nhanh. Quyền dùng thương mại/runtime, chi phí duy trì 272 danh mục và phương án đo thời gian nhận đủ dữ liệu cho một người vận hành còn chưa xác minh. |

[Nguồn tác giả](https://www.sakethaleti.com/data) ·
[Metadata Drive](https://drive.google.com/drive/folders/1TuTvWP79IkcrBRoj2iCsHB_2Lj5wGDzm) ·
[INFORMS](https://pubsonline.informs.org/doi/suppl/10.1287/mnsc.2023.01657).

Để mở lại phép thử, cần forecast hoặc model pack đúng phiên bản có
timestamp và cutoff kiểm được, nguồn hợp lệ và cách tính ngưỡng tác giả.
Khi đó mới khóa một bản flat cuối phiên trước khi xem PnL. Dùng thời
điểm quyết định sau khi M15 hoàn tất, khớp sớm nhất tại M1 Open kế tiếp,
giữ đúng thay đổi vị thế, chấm lần lượt midpoint, Bid/Ask và stress với
đối chứng cash và always-long cùng cửa sổ. Giá và tín hiệu của dự án
chỉ được xét 2018–2023 trong lượt này. Mô hình chưa có trade ledger, nên
không suy Sharpe SPY thành đường vốn Challenge hay khả năng payout.

Bằng chứng local tại ai-engine-jobs/prop-spy-s-sign-us500-20261119 trên ổ E:
measure_quote_cost.py, quote-cost.json.zst và manifest SHA256. Script dùng
lại bộ đọc V11, lịch NYSE và sổ cash-session 383b7d0. Kết quả endpoint
được tái tính độc lập từ sổ đã niêm phong. Không tải dữ liệu nhân tố,
đọc giá ngoài phạm vi đã duyệt, fit mô hình hoặc chạy broker.
